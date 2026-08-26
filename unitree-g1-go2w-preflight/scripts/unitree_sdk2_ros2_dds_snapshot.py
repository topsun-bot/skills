#!/usr/bin/env python3
"""Collect a read-only Unitree SDK2 + ROS 2 DDS compatibility snapshot.

The collector does not import ROS, CycloneDDS, or Unitree SDK modules; create a
DDS participant; open a network socket; or send a robot command.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import socket
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
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


class InputError(ValueError):
    pass


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


def library_record(path: Path, home: str, source: str) -> dict[str, Any]:
    try:
        resolved = path.resolve(strict=False)
        size = resolved.stat().st_size if resolved.is_file() else None
    except OSError:
        resolved, size = path, None
    return {
        "kind": library_kind(path.name),
        "path": redact_path(str(resolved), home),
        "size_bytes": size,
        "sha256": sha256_file(resolved),
        "source": source,
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


def scan_libraries(prefixes: Iterable[Path], home: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prefix in prefixes:
        for directory in (prefix, prefix / "lib", prefix / "lib64"):
            if not directory.is_dir():
                continue
            for pattern in LIB_PATTERNS:
                for path in directory.glob(pattern):
                    key = str(path.resolve(strict=False))
                    if key not in seen:
                        seen.add(key)
                        records.append(library_record(path, home, "configured_prefix"))
    return records


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
                loaded.append(library_record(Path(path_text), target_home, "process_maps"))
    except OSError:
        pass

    return {
        "status": "proved" if loaded else "not_proved",
        "command_basename": command,
        "safe_environment": safe_env_snapshot(env, target_home),
        "_raw_environment": env,
        "_environment_status": environment_status,
        "_environment_reason": environment_reason,
        "_redaction_home": target_home,
        "loaded_libraries": loaded,
        "reason": None if loaded else "process exists but no DDS/Unitree library path was readable from maps",
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
        config = cyclonedds_config_snapshot(args.cyclonedds_uri, redaction_home)
    elif environment_evidence["status"] == "proved":
        config = cyclonedds_config_snapshot(evidence_env.get("CYCLONEDDS_URI"), redaction_home)
    else:
        config = {
            "status": "not_proved",
            "reason": "target process environment unreadable and --cyclonedds-uri not supplied",
        }
    prefixes = candidate_prefixes(evidence_env, args.search_prefix)
    library_candidates = scan_libraries(prefixes, redaction_home)

    return {
        "schema_version": 2,
        "collector": {
            "version": "1.1.0",
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
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "'")


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
