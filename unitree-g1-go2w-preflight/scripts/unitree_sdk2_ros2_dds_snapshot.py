#!/usr/bin/env python3
"""Collect a read-only Unitree SDK2 + ROS 2 DDS compatibility snapshot.

The collector does not import ROS, CycloneDDS, or Unitree SDK modules; create a
DDS participant; open a network socket; or send a robot command.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import fnmatch
import hashlib
import html
import importlib.metadata
import json
import os
import platform
import re
import socket
import stat
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote, urlparse


SAFE_ENV = (
    "ROS_DISTRO", "ROS_VERSION", "ROS_PYTHON_VERSION", "ROS_DOMAIN_ID",
    "RMW_IMPLEMENTATION", "CYCLONEDDS_HOME", "AMENT_PREFIX_PATH",
    "COLCON_PREFIX_PATH", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH", "PYTHONPATH",
)
PATH_ENV = {"CYCLONEDDS_HOME", "AMENT_PREFIX_PATH", "COLCON_PREFIX_PATH", "CMAKE_PREFIX_PATH", "LD_LIBRARY_PATH", "PYTHONPATH"}
PACKAGES = ("cyclonedds", "unitree-sdk2py", "rclpy")
LIB_PATTERNS = ("libddsc*.so*", "librmw_cyclonedds_cpp*.so*", "libunitree_sdk2*.so*", "libunitree_sdk2*.a")
MAX_HASH_BYTES = 256 * 1024 * 1024
OPENAT2_SYSCALL = 437
RESOLVE_NO_MAGICLINKS = 0x02
RESOLVE_IN_ROOT = 0x10


class InputError(ValueError):
    pass


class TargetPathError(OSError):
    pass


class OpenHow(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_ulonglong), ("mode", ctypes.c_ulonglong), ("resolve", ctypes.c_ulonglong)]


def redact_path(value: str, home: str) -> str:
    if not value:
        return value
    normalized_home = home.rstrip(os.sep)
    if normalized_home and (value == normalized_home or value.startswith(normalized_home + os.sep)):
        return "$HOME" + value[len(normalized_home):]
    return value


def safe_env_snapshot(env: dict[str, str], home: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in SAFE_ENV:
        value = env.get(key)
        if value is None:
            continue
        if key in PATH_ENV:
            value = os.pathsep.join(redact_path(item, home) for item in value.split(os.pathsep))
        result[key] = value
    return result


def sha256_file(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_HASH_BYTES:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def sha256_fd(fd: int) -> str | None:
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_HASH_BYTES:
            return None
        os.lseek(fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def library_kind(name: str) -> str:
    lowered = name.lower()
    if "rmw_cyclonedds" in lowered:
        return "rmw_cyclonedds"
    if "ddscxx" in lowered:
        return "ddscxx"
    if re.search(r"libddsc(?:\.|$)", lowered):
        return "ddsc"
    if "unitree_sdk2" in lowered:
        return "unitree_sdk2"
    if "cyclonedds" in lowered:
        return "cyclonedds"
    return "other_dds"


def library_record(
    path: Path,
    home: str,
    source: str,
    display_path: Path | PurePosixPath | None = None,
    filesystem_scope: str = "collector_process_namespace",
) -> dict[str, Any]:
    try:
        resolved = path.resolve(strict=False)
        size = resolved.stat().st_size if resolved.is_file() else None
    except OSError:
        resolved, size = path, None
    return {
        "kind": library_kind(path.name),
        "path": redact_path(str(display_path if display_path is not None else resolved), home),
        "size_bytes": size,
        "sha256": sha256_file(resolved),
        "source": source,
        "filesystem_scope": filesystem_scope,
    }


def library_record_fd(fd: int, display_path: PurePosixPath, source: str) -> dict[str, Any]:
    try:
        metadata = os.fstat(fd)
        size = metadata.st_size if stat.S_ISREG(metadata.st_mode) else None
    except OSError:
        size = None
    return {
        "kind": library_kind(display_path.name),
        "path": str(display_path),
        "size_bytes": size,
        "sha256": sha256_fd(fd),
        "source": source,
        "filesystem_scope": "target_process_namespace",
    }


def candidate_prefixes(env: dict[str, str], explicit: Iterable[Path]) -> list[Path]:
    values = [Path(item) for item in explicit]
    for key in ("LD_LIBRARY_PATH", "AMENT_PREFIX_PATH", "COLCON_PREFIX_PATH", "CMAKE_PREFIX_PATH"):
        for item in env.get(key, "").split(os.pathsep):
            if item:
                values.append(Path(item))
    distro = env.get("ROS_DISTRO", "")
    if distro and re.fullmatch(r"[a-zA-Z0-9_-]+", distro):
        values.append(Path("/opt/ros") / distro)
    unique: list[Path] = []
    seen: set[str] = set()
    for value in values:
        key = str(value)
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def _normalize_target_parts(parts: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for part in parts:
        if part in ("", ".", "/"):
            continue
        if part == "..":
            if not normalized:
                raise TargetPathError("target path escapes process root")
            normalized.pop()
        else:
            normalized.append(part)
    return normalized


def target_logical_path(
    raw_path: str,
    pid: int,
    proc_root: Path,
    target_home: str | None,
) -> tuple[PurePosixPath | None, PurePosixPath | None, str | None]:
    if not raw_path:
        return None, None, "target path is empty"
    if raw_path == "~" or raw_path.startswith("~/"):
        if not target_home or not PurePosixPath(target_home).is_absolute():
            return None, None, "target HOME unavailable for tilde path"
        suffix = raw_path[2:] if raw_path.startswith("~/") else ""
        display = PurePosixPath(target_home) / suffix
    elif raw_path.startswith("~"):
        return None, None, "named-user tilde paths are not resolved"
    else:
        display = PurePosixPath(raw_path)
    if ".." in display.parts:
        return None, display, "parent traversal in target path was not resolved"
    if display.is_absolute():
        return PurePosixPath("/") / str(display).lstrip("/"), display, None
    try:
        cwd_target = os.readlink(proc_root / str(pid) / "cwd")
    except OSError:
        return None, display, "target cwd was not readable"
    if cwd_target.endswith(" (deleted)"):
        return None, display, "target cwd was deleted"
    cwd = PurePosixPath(cwd_target)
    if not cwd.is_absolute():
        return None, display, "target cwd was not absolute"
    try:
        parts = _normalize_target_parts((*cwd.parts, *display.parts))
    except TargetPathError as exc:
        return None, display, str(exc)
    return PurePosixPath("/").joinpath(*parts), display, None


def target_path_label(logical: PurePosixPath, target_home: str | None, redaction_home: str) -> str:
    if logical.is_absolute():
        return redact_path(str(logical), target_home or redaction_home)
    return f"target_cwd:{logical}"


def _open_target_fallback(root_fd: int, logical: PurePosixPath, flags: int) -> int:
    queue = _normalize_target_parts(logical.parts)
    resolved: list[str] = []
    symlinks = 0
    current = os.dup(root_fd)
    try:
        if not queue:
            return os.dup(root_fd)
        while queue:
            name = queue.pop(0)
            try:
                metadata = os.stat(name, dir_fd=current, follow_symlinks=False)
            except OSError:
                raise
            if stat.S_ISLNK(metadata.st_mode):
                symlinks += 1
                if symlinks > 40:
                    raise TargetPathError("too many symlinks in target path")
                target = PurePosixPath(os.readlink(name, dir_fd=current))
                combined = list(target.parts) + queue if target.is_absolute() else resolved + list(target.parts) + queue
                queue = _normalize_target_parts(combined)
                resolved = []
                os.close(current)
                current = os.dup(root_fd)
                continue
            open_flags = flags if not queue else os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            open_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            opened = os.open(name, open_flags, dir_fd=current)
            if queue:
                os.close(current)
                current = opened
                resolved.append(name)
            else:
                return opened
        raise TargetPathError("target path resolution produced no file")
    finally:
        os.close(current)


def open_target_fd(
    logical: PurePosixPath,
    pid: int,
    proc_root: Path,
    *,
    directory: bool = False,
) -> int:
    if not logical.is_absolute():
        raise TargetPathError("target logical path was not absolute")
    root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    root_fd = os.open(proc_root / str(pid) / "root", root_flags)
    requested_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if directory:
        requested_flags |= getattr(os, "O_DIRECTORY", 0)
    try:
        if platform.system() == "Linux":
            libc = ctypes.CDLL(None, use_errno=True)
            libc.syscall.restype = ctypes.c_long
            how = OpenHow(requested_flags, 0, RESOLVE_IN_ROOT | RESOLVE_NO_MAGICLINKS)
            path_bytes = str(logical).lstrip("/").encode() or b"."
            fd = libc.syscall(OPENAT2_SYSCALL, root_fd, path_bytes, ctypes.byref(how), ctypes.sizeof(how))
            if fd < 0:
                error_number = ctypes.get_errno()
                if error_number == errno.ENOSYS:
                    raise TargetPathError("openat2 unavailable; target path not proved")
                raise OSError(error_number, os.strerror(error_number), str(logical))
            return int(fd)
        return _open_target_fallback(root_fd, logical, requested_flags)
    finally:
        os.close(root_fd)


def scan_libraries(
    prefixes: Iterable[Path],
    home: str,
    process_pid: int | None = None,
    proc_root: Path = Path("/proc"),
    target_home: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    prefix_evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prefix in prefixes:
        if process_pid is not None:
            logical_prefix, display_logical, error = target_logical_path(str(prefix), process_pid, proc_root, target_home)
            scope = "target_process_namespace"
            if error or logical_prefix is None or display_logical is None:
                prefix_evidence.append({"path": str(prefix), "status": "not_proved", "filesystem_scope": scope, "reason": error})
                continue
            display_prefix = target_path_label(display_logical, target_home, home)
        else:
            access_prefix = prefix.expanduser()
            logical_prefix = PurePosixPath(str(prefix))
            display_prefix = redact_path(str(access_prefix), home)
            scope = "collector_process_namespace"
        enumerated_directory = False
        scan_errors: list[str] = []
        for suffix in ("", "lib", "lib64"):
            display_directory = PurePosixPath(display_prefix) / suffix if suffix else PurePosixPath(display_prefix)
            if process_pid is not None:
                target_directory = logical_prefix / suffix if suffix else logical_prefix
                try:
                    directory_fd = open_target_fd(target_directory, process_pid, proc_root, directory=True)
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    scan_errors.append(f"{display_directory}: {exc.strerror or type(exc).__name__}")
                    continue
                try:
                    names = os.listdir(directory_fd)
                    enumerated_directory = True
                except OSError as exc:
                    scan_errors.append(f"{display_directory}: {exc.strerror or type(exc).__name__}")
                    names = []
                finally:
                    os.close(directory_fd)
                for name in names:
                    if not any(fnmatch.fnmatch(name, pattern) for pattern in LIB_PATTERNS):
                        continue
                    key = str(target_directory / name)
                    if key in seen:
                        continue
                    try:
                        file_fd = open_target_fd(target_directory / name, process_pid, proc_root)
                    except OSError as exc:
                        scan_errors.append(f"{display_directory / name}: {exc.strerror or type(exc).__name__}")
                        continue
                    try:
                        seen.add(key)
                        records.append(library_record_fd(file_fd, display_directory / name, "configured_prefix"))
                    finally:
                        os.close(file_fd)
            else:
                directory = access_prefix / suffix if suffix else access_prefix
                try:
                    metadata = directory.stat()
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    scan_errors.append(f"{display_directory}: {exc.strerror or type(exc).__name__}")
                    continue
                if not stat.S_ISDIR(metadata.st_mode):
                    continue
                try:
                    with os.scandir(directory) as entries:
                        paths = [directory / entry.name for entry in entries if any(fnmatch.fnmatch(entry.name, pattern) for pattern in LIB_PATTERNS)]
                except OSError as exc:
                    scan_errors.append(f"{display_directory}: {exc.strerror or type(exc).__name__}")
                    continue
                enumerated_directory = True
                for path in paths:
                    key = str(path.resolve(strict=False))
                    if key not in seen:
                        seen.add(key)
                        records.append(library_record(path, home, "configured_prefix", display_directory / path.name, scope))
        proved = enumerated_directory and not scan_errors
        prefix_evidence.append({
            "path": display_prefix,
            "status": "proved" if proved else "not_proved",
            "filesystem_scope": scope,
            "reason": None if proved else "; ".join(scan_errors) or "configured prefix was not enumerable in the selected namespace",
        })
    return records, prefix_evidence


def process_snapshot(pid: int | None, proc_root: Path, home: str) -> dict[str, Any]:
    if pid is None:
        return {"status": "not_proved", "reason": "no --process-pid supplied", "loaded_libraries": []}
    base = proc_root / str(pid)
    if not base.is_dir():
        raise InputError(f"process directory not found: {base}")

    env: dict[str, str] = {}
    environment_status = "proved"
    environment_reason = None
    try:
        raw = (base / "environ").read_bytes()
        for item in raw.split(b"\0"):
            if b"=" in item:
                key, value = item.split(b"=", 1)
                decoded_key = key.decode("utf-8", "replace")
                if decoded_key in SAFE_ENV or decoded_key in {"CYCLONEDDS_URI", "HOME"}:
                    env[decoded_key] = value.decode("utf-8", "replace")
    except OSError:
        environment_status = "not_proved"
        environment_reason = "target process environment was not readable"

    target_home = env.get("HOME", home)

    command = None
    try:
        raw_cmd = (base / "cmdline").read_bytes().split(b"\0")[0]
        command = Path(raw_cmd.decode("utf-8", "replace")).name if raw_cmd else None
    except OSError:
        pass

    loaded: list[dict[str, Any]] = []
    map_failures: list[dict[str, str]] = []
    seen: set[str] = set()
    try:
        for line in (base / "maps").read_text(encoding="utf-8", errors="replace").splitlines():
            if "/" not in line:
                continue
            path_text = line[line.find("/"):].removesuffix(" (deleted)")
            if not re.search(r"ddsc|cyclonedds|rmw_|unitree_sdk2", path_text, re.IGNORECASE):
                continue
            if path_text not in seen:
                seen.add(path_text)
                logical_path, display_path, error = target_logical_path(path_text, pid, proc_root, env.get("HOME"))
                if logical_path is not None and display_path is not None:
                    try:
                        file_fd = open_target_fd(logical_path, pid, proc_root)
                    except OSError as exc:
                        error = exc.strerror or type(exc).__name__
                    else:
                        try:
                            loaded.append(library_record_fd(file_fd, display_path, "process_maps"))
                        finally:
                            os.close(file_fd)
                        continue
                if error:
                    map_failures.append({"path": redact_path(path_text, target_home), "reason": error})
                    loaded.append({
                        "kind": library_kind(Path(path_text).name), "path": redact_path(path_text, target_home),
                        "size_bytes": None, "sha256": None, "source": "process_maps",
                        "filesystem_scope": "target_process_namespace", "reason": error,
                    })
    except OSError:
        pass

    complete_libraries = [item for item in loaded if item.get("sha256")]
    library_status = "proved" if loaded and len(complete_libraries) == len(loaded) and not map_failures else "not_proved"
    if map_failures:
        library_reason = "one or more relevant process map files could not be opened and hashed in the target namespace"
    elif loaded and len(complete_libraries) != len(loaded):
        library_reason = "one or more opened process libraries lacked a bounded SHA-256 observation"
    elif loaded:
        library_reason = None
    else:
        library_reason = "process exists but no DDS/Unitree library path was readable from maps"
    return {
        "status": library_status,
        "command_basename": command,
        "safe_environment": safe_env_snapshot(env, target_home),
        "_raw_environment": env,
        "_environment_status": environment_status,
        "_environment_reason": environment_reason,
        "_redaction_home": target_home,
        "_target_home": env.get("HOME"),
        "loaded_libraries": loaded,
        "map_open_failures": map_failures,
        "reason": library_reason,
    }


def parse_domain(value: Any, label: str) -> tuple[int | None, str | None]:
    if value is None or value == "":
        return None, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{label} is not an integer"
    if parsed < 0 or parsed > 0xFFFFFFFF:
        return None, f"{label} is outside the DDS uint32 range"
    return parsed, None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_cyclonedds_xml(xml_text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"status": "contradicted", "error": f"invalid XML: {exc}"}
    domains: list[str] = []
    interfaces: list[dict[str, Any]] = []
    address_present = False
    for element in root.iter():
        name = _local_name(element.tag)
        if name == "Domain" and "Id" in element.attrib:
            domains.append(element.attrib["Id"])
        if name == "NetworkInterface":
            record = {key: value for key, value in element.attrib.items() if key in {"name", "autodetermine", "priority", "multicast"}}
            if "address" in element.attrib:
                address_present = True
            interfaces.append(record)
        if name in {"NetworkInterfaceAddress", "Peer"} and ((element.text or "").strip() or element.attrib):
            address_present = True
    return {"status": "proved", "domain_ids": domains, "interfaces": interfaces, "address_values_redacted": address_present}


def cyclonedds_config_snapshot(uri: str | None, home: str) -> dict[str, Any]:
    if not uri:
        return {"status": "not_proved", "reason": "CYCLONEDDS_URI not set or supplied"}
    text: str
    source: str
    if uri.lstrip().startswith("<"):
        text, source = uri, "inline_xml"
    else:
        parsed = urlparse(uri)
        if parsed.scheme not in ("", "file"):
            return {"status": "not_proved", "source": parsed.scheme, "reason": "non-file URI was not fetched"}
        path = Path(unquote(parsed.path) if parsed.scheme == "file" else uri).expanduser()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return {"status": "contradicted", "source": redact_path(str(path), home), "error": str(exc)}
        source = redact_path(str(path.resolve(strict=False)), home)
    result = parse_cyclonedds_xml(text)
    result.update({"source": source, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
    return result


def target_cyclonedds_config_snapshot(
    uri: str | None,
    pid: int,
    proc_root: Path,
    target_home: str | None,
    redaction_home: str,
) -> dict[str, Any]:
    if not uri:
        return {"status": "not_proved", "reason": "CYCLONEDDS_URI not set or supplied"}
    if uri.lstrip().startswith("<"):
        return cyclonedds_config_snapshot(uri, redaction_home)

    parsed = urlparse(uri)
    if parsed.scheme not in ("", "file"):
        return {"status": "not_proved", "source": parsed.scheme, "reason": "non-file URI was not fetched"}
    if parsed.netloc not in ("", "localhost"):
        return {"status": "not_proved", "reason": "non-local file URI was not read"}
    raw_path = unquote(parsed.path) if parsed.scheme == "file" else uri
    if not raw_path:
        return {"status": "not_proved", "reason": "target configuration path is empty"}

    logical, display_logical, error = target_logical_path(raw_path, pid, proc_root, target_home)
    if error or logical is None or display_logical is None:
        return {"status": "not_proved", "reason": error}
    source = target_path_label(display_logical, target_home, redaction_home)
    try:
        file_fd = open_target_fd(logical, pid, proc_root)
        with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return {"status": "not_proved", "source": source, "reason": "target configuration file was not readable through proc root/cwd"}
    result = parse_cyclonedds_xml(text)
    result.update({"source": source, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "filesystem_scope": "target_process_namespace"})
    return result


def package_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for package in PACKAGES:
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = None
    return result


def duplicate_binary_findings(libraries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, set[str]] = {}
    for record in libraries:
        digest = record.get("sha256")
        if digest:
            grouped.setdefault(record["kind"], set()).add(digest)
    findings = []
    for kind, hashes in sorted(grouped.items()):
        findings.append({
            "kind": kind,
            "distinct_hashes": len(hashes),
            "status": "contradicted" if len(hashes) > 1 else "proved",
            "scope": "target_process_loaded_libraries",
            "meaning": "multiple binary builds loaded in the target process" if len(hashes) > 1 else "one binary build loaded in the target process",
        })
    return findings


def build_report(args: argparse.Namespace, env: dict[str, str]) -> dict[str, Any]:
    home = env.get("HOME", str(Path.home()))
    process = process_snapshot(args.process_pid, args.proc_root, home)
    process_env = process.pop("_raw_environment", {})
    process_env_status = process.pop("_environment_status", "not_applicable")
    process_env_reason = process.pop("_environment_reason", None)
    redaction_home = process.pop("_redaction_home", home)
    target_home = process.pop("_target_home", None)

    if args.process_pid is None:
        evidence_env = dict(env)
        environment_evidence = {
            "scope": "collector_process",
            "status": "proved",
            "reason": "no target PID supplied; configuration-only snapshot uses the collector environment",
        }
    else:
        evidence_env = dict(process_env)
        environment_evidence = {
            "scope": "target_process",
            "status": process_env_status,
            "reason": process_env_reason,
        }

    ros_error = None
    if args.ros_domain is not None:
        ros_raw = args.ros_domain
    elif environment_evidence["status"] == "proved":
        ros_raw = evidence_env.get("ROS_DOMAIN_ID", 0)
    else:
        ros_raw = None
        ros_error = "target process environment unreadable and --ros-domain not supplied"
    ros_domain, parsed_ros_error = parse_domain(ros_raw, "ROS domain")
    ros_error = ros_error or parsed_ros_error
    unitree_domain, unitree_error = parse_domain(args.unitree_domain, "Unitree ChannelFactory domain")
    domain_relation = "not_proved"
    if ros_domain is not None and unitree_domain is not None:
        domain_relation = "same" if ros_domain == unitree_domain else "different"

    if args.cyclonedds_uri is not None:
        uri = args.cyclonedds_uri
    elif environment_evidence["status"] == "proved":
        uri = evidence_env.get("CYCLONEDDS_URI")
    else:
        uri = None
    if uri is not None and args.process_pid is not None:
        config = target_cyclonedds_config_snapshot(uri, args.process_pid, args.proc_root, target_home, redaction_home)
    elif uri is not None:
        config = cyclonedds_config_snapshot(uri, redaction_home)
    elif environment_evidence["status"] != "proved":
        config = {
            "status": "not_proved",
            "reason": "target process environment unreadable and --cyclonedds-uri not supplied",
        }
    else:
        config = cyclonedds_config_snapshot(None, redaction_home)
    prefixes = candidate_prefixes(evidence_env, args.search_prefix)
    library_candidates, library_candidate_prefixes = scan_libraries(
        prefixes, redaction_home, args.process_pid, args.proc_root, target_home,
    )

    return {
        "schema_version": 2,
        "collector": {
            "version": "1.4.0",
            "network_packets_sent": "no",
            "dds_participant_created": "no",
            "robot_commands_sent": "no",
            "imports_ros_or_unitree": "no",
        },
        "system": {
            "os": platform.system(), "release": platform.release(), "machine": platform.machine(),
            "python": platform.python_version(), "network_interfaces_names_only": [name for _, name in socket.if_nameindex()],
        },
        "environment_evidence": environment_evidence,
        "safe_environment": safe_env_snapshot(evidence_env, redaction_home),
        "python_packages_scope": "collector_process",
        "python_packages": package_versions(),
        "domains": {
            "ros_domain": ros_domain, "unitree_channel_factory_domain": unitree_domain,
            "relationship": domain_relation, "errors": [item for item in (ros_error, unitree_error) if item],
            "boundary": "different domains isolate discovery; same domain enables discovery but does not prove binary/config compatibility or RPC success",
        },
        "cyclonedds_config": config,
        "process": process,
        "library_candidate_prefixes": library_candidate_prefixes,
        "library_candidates": library_candidates,
        "binary_findings": duplicate_binary_findings(process["loaded_libraries"]),
        "interpretation_gates": [
            {"gate": "configuration_loaded", "status": "not_proved", "evidence_needed": "current process log or trace"},
            {"gate": "participant_created", "status": "not_proved", "evidence_needed": "return/exception plus current process evidence"},
            {"gate": "topic_discovery", "status": "not_proved", "evidence_needed": "matched endpoint evidence on the intended domain"},
            {"gate": "data_freshness", "status": "not_proved", "evidence_needed": "monotonic timestamps and bounded age"},
            {"gate": "rpc_response", "status": "not_proved", "evidence_needed": "request id, response code, latency and server identity"},
            {"gate": "physical_result", "status": "not_proved", "evidence_needed": "separately authorized observation; this collector sends no motion"},
        ],
        "limits": [
            "A duplicate or mismatched DDS binary is a risk signal, not proof of the root cause.",
            "Changing a domain ID may avoid one initialization conflict while isolating required endpoints or leaving RPC unavailable.",
            "Initialization success does not prove discovery, fresh data, RPC response, or physical robot behavior.",
            "The report intentionally omits hostnames, IP addresses, peer addresses, and non-whitelisted environment variables.",
        ],
    }


def markdown_cell(value: Any) -> str:
    if value is None or value == "":
        return "not_proved"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = html.escape(text, quote=False).replace("\\", "\\\\")
    for character in ("|", "*", "[", "]"):
        text = text.replace(character, "\\" + character)
    return text.replace("`", "'")


def markdown(report: dict[str, Any]) -> str:
    environment = report["environment_evidence"]
    process = report["process"]
    config = report["cyclonedds_config"]
    lines = [
        "# Unitree SDK2 + ROS 2 DDS read-only snapshot", "",
        f"- Collector version: `{markdown_cell(report['collector'].get('version'))}`",
        f"- ROS domain: `{report['domains']['ros_domain']}`",
        f"- Unitree ChannelFactory domain: `{report['domains']['unitree_channel_factory_domain']}`",
        f"- Relationship: **{report['domains']['relationship']}**",
        "- Network packets sent: **no**", "- DDS participant created: **no**", "- Robot commands sent: **no**", "",
        "## Environment evidence", "",
        f"- Scope: **{markdown_cell(environment.get('scope'))}**",
        f"- Status: **{markdown_cell(environment.get('status'))}**",
        f"- Reason: {markdown_cell(environment.get('reason'))}", "",
        "| Variable | Value |", "|---|---|",
    ]
    for key, value in sorted(report["safe_environment"].items()):
        lines.append(f"| {markdown_cell(key)} | {markdown_cell(value)} |")
    if not report["safe_environment"]:
        lines.append("| none observed | not_proved |")

    lines += ["", "## Target process", "",
              f"- Library evidence status: **{markdown_cell(process.get('status'))}**",
              f"- Command basename: `{markdown_cell(process.get('command_basename'))}`",
              f"- Reason: {markdown_cell(process.get('reason'))}", "",
              "### Loaded libraries", "",
              "| Kind | Path | Size bytes | SHA-256 |", "|---|---|---:|---|"]
    for item in process["loaded_libraries"]:
        lines.append(f"| {markdown_cell(item.get('kind'))} | {markdown_cell(item.get('path'))} | {markdown_cell(item.get('size_bytes'))} | {markdown_cell(item.get('sha256'))} |")
    if not process["loaded_libraries"]:
        lines.append("| none observed | not_proved | not_proved | not_proved |")

    lines += ["", "## Configured library candidates", "",
              "Installed candidates are reported separately and are not treated as loaded-process conflicts.", "",
              "### Prefix evidence", "", "| Prefix | Status | Filesystem scope | Reason |", "|---|---|---|---|"]
    for item in report.get("library_candidate_prefixes", []):
        lines.append(f"| {markdown_cell(item.get('path'))} | {markdown_cell(item.get('status'))} | {markdown_cell(item.get('filesystem_scope'))} | {markdown_cell(item.get('reason'))} |")
    if not report.get("library_candidate_prefixes"):
        lines.append("| none configured | not_proved | not_proved | not_proved |")
    lines += ["", "### Candidate libraries", "",
              "| Kind | Path | Size bytes | SHA-256 |", "|---|---|---:|---|"]
    for item in report["library_candidates"]:
        lines.append(f"| {markdown_cell(item.get('kind'))} | {markdown_cell(item.get('path'))} | {markdown_cell(item.get('size_bytes'))} | {markdown_cell(item.get('sha256'))} |")
    if not report["library_candidates"]:
        lines.append("| none observed | not_proved | not_proved | not_proved |")

    lines += ["", "## Python packages", "",
              f"- Scope: **{markdown_cell(report.get('python_packages_scope'))}** (the collector runtime; not automatically the target process)", "",
              "| Package | Version |", "|---|---|"]
    for package, version in sorted(report["python_packages"].items()):
        lines.append(f"| {markdown_cell(package)} | {markdown_cell(version)} |")

    lines += ["", "## CycloneDDS configuration", "",
              f"- Status: **{markdown_cell(config.get('status'))}**",
              f"- Filesystem scope: **{markdown_cell(config.get('filesystem_scope'))}**",
              f"- Source: `{markdown_cell(config.get('source'))}`",
              f"- SHA-256: `{markdown_cell(config.get('sha256'))}`",
              f"- Domain IDs: `{markdown_cell(config.get('domain_ids'))}`",
              f"- Address values redacted: **{markdown_cell(config.get('address_values_redacted'))}**",
              f"- Reason/error: {markdown_cell(config.get('reason') or config.get('error'))}", ""]
    if config.get("interfaces"):
        lines += ["| Interface attributes (addresses omitted) |", "|---|"]
        for item in config["interfaces"]:
            lines.append(f"| {markdown_cell(item)} |")

    lines += ["", "## Loaded-binary findings", "", "| Kind | Distinct hashes | Status | Scope |", "|---|---:|---|---|"]
    for item in report["binary_findings"]:
        lines.append(f"| {markdown_cell(item['kind'])} | {item['distinct_hashes']} | {item['status']} | {markdown_cell(item.get('scope'))} |")
    if not report["binary_findings"]:
        lines.append("| none observed | 0 | not_proved | target_process_loaded_libraries |")
    lines += ["", "## Interpretation gates", "", "| Gate | Status | Evidence needed |", "|---|---|---|"]
    lines.extend(f"| {item['gate']} | {item['status']} | {item['evidence_needed']} |" for item in report["interpretation_gates"])
    lines += ["", "## Limits", ""]
    lines.extend(f"- {item}" for item in report["limits"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process-pid", type=int, help="read only this Linux /proc PID")
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"), help=argparse.SUPPRESS)
    parser.add_argument("--unitree-domain", type=int, help="domain passed to ChannelFactory::Init/ChannelFactoryInitialize")
    parser.add_argument("--ros-domain", type=int, help="override ROS_DOMAIN_ID for the report")
    parser.add_argument("--cyclonedds-uri", help="inline XML or a local file/file:// URI; never fetched from the network")
    parser.add_argument("--search-prefix", type=Path, action="append", default=[], help="additional exact prefix to inspect for DDS libraries")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args, dict(os.environ))
        rendered = markdown(report) if args.format == "markdown" else json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (InputError, OSError) as exc:
        sys.stderr.write(json.dumps({"status": "invalid_input", "error": str(exc)}, ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
