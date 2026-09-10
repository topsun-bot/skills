#!/usr/bin/env python3
"""Fail closed on skill-pack structure, manifests, JSON, and relative Markdown links."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_MARKDOWN = "SKILL.md"
AGENT_MANIFEST = Path("agents") / "openai.yaml"
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
README_SKILL_LINK = re.compile(r"\[`([^`]+)`\]\(([^)]+)\)")
SKIP_LINK_SCHEMES = ("http://", "https://", "mailto:")
SKIP_LINK_PREFIXES = ("<", ".agent-delivery/")

INTERFACE_KEYS = ("display_name", "short_description", "default_prompt")


def discover_skills(root: Path) -> list[Path]:
    skills = sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and (path / SKILL_MARKDOWN).is_file()
    )
    if not skills:
        raise SystemExit("ERROR: no skill directories with SKILL.md found")
    return skills


def parse_frontmatter_scalars(text: str) -> dict[str, str]:
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("missing YAML frontmatter delimited by ---")
    values: dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        values[key.strip()] = unquote_scalar(value.strip())
    return values


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_nested_yaml_map(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current: str | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") and not raw.startswith("  "):
            raise ValueError(f"line {lineno}: use 2-space indent")
        if raw.startswith("  "):
            if current is None or not isinstance(result.get(current), dict):
                raise ValueError(f"line {lineno}: indented key without a mapping parent")
            if ":" not in raw:
                raise ValueError(f"line {lineno}: expected key: value")
            key, _, value = raw.strip().partition(":")
            result[current][key.strip()] = coerce_scalar(unquote_scalar(value.strip()))
            continue
        if ":" not in raw:
            raise ValueError(f"line {lineno}: expected key: or key: value")
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            result[key] = coerce_scalar(unquote_scalar(value))
            current = None
        else:
            result[key] = {}
            current = key
    return result


def coerce_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~", ""}:
        return None
    return value


def cataloged_skills(readme: str) -> list[str]:
    names: list[str] = []
    in_table = False
    for line in readme.splitlines():
        if line.startswith("| Skill |"):
            in_table = True
            continue
        if in_table and line.startswith("| ---"):
            continue
        if in_table and line.startswith("|"):
            match = README_SKILL_LINK.search(line)
            if not match:
                raise ValueError(f"skill table row is missing a `name` link: {line}")
            name, target = match.groups()
            expected = f"{name}/"
            if target.rstrip("/") + "/" != expected:
                raise ValueError(f"README skill {name} links to {target!r}, expected {expected!r}")
            names.append(name)
            continue
        if in_table:
            break
    if not names:
        raise ValueError("README is missing a Skill table")
    return names


def is_skippable_link(target: str) -> bool:
    stripped = target.strip()
    if not stripped or stripped.startswith("#"):
        return True
    lowered = stripped.lower()
    if lowered.startswith(SKIP_LINK_SCHEMES):
        return True
    return any(stripped.startswith(prefix) for prefix in SKIP_LINK_PREFIXES)


def relative_link_target(source: Path, target: str) -> Path:
    path_part = target.split("#", 1)[0].split("?", 1)[0]
    return (source.parent / path_part).resolve()


def collect_markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if ".git" not in path.parts
    )


def collect_json_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.json")
        if ".git" not in path.parts
    )


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_name = skill_dir.name
    skill_md = skill_dir / SKILL_MARKDOWN
    try:
        frontmatter = parse_frontmatter_scalars(skill_md.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{skill_md.relative_to(skill_dir.parent)}: {exc}"]

    if frontmatter.get("name") != skill_name:
        errors.append(
            f"{skill_md.relative_to(skill_dir.parent)}: frontmatter name "
            f"{frontmatter.get('name')!r} must match directory {skill_name!r}"
        )
    if not str(frontmatter.get("description", "")).strip():
        errors.append(f"{skill_md.relative_to(skill_dir.parent)}: description is required")

    manifest_path = skill_dir / AGENT_MANIFEST
    if not manifest_path.is_file():
        errors.append(f"{manifest_path.relative_to(skill_dir.parent)}: missing agent manifest")
        return errors
    try:
        manifest = parse_nested_yaml_map(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        errors.append(f"{manifest_path.relative_to(skill_dir.parent)}: {exc}")
        return errors

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append(f"{manifest_path.relative_to(skill_dir.parent)}: interface mapping is required")
        return errors
    for key in INTERFACE_KEYS:
        value = interface.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{manifest_path.relative_to(skill_dir.parent)}: interface.{key} must be a non-empty string")
    prompt = interface.get("default_prompt")
    if isinstance(prompt, str) and f"${skill_name}" not in prompt:
        errors.append(
            f"{manifest_path.relative_to(skill_dir.parent)}: default_prompt must mention ${skill_name}"
        )
    return errors


def validate_json_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path in collect_json_paths(root):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root)}: invalid JSON ({exc})")
    return errors


def validate_relative_links(root: Path) -> list[str]:
    errors: list[str] = []
    root_resolved = root.resolve()
    for path in collect_markdown_paths(root):
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if is_skippable_link(target):
                continue
            destination = relative_link_target(path, target)
            try:
                destination.relative_to(root_resolved)
            except ValueError:
                errors.append(f"{path.relative_to(root)}: link escapes the repository: {target}")
                continue
            if not destination.exists():
                errors.append(f"{path.relative_to(root)}: broken relative link: {target}")
    return errors


def validate_catalog(root: Path, skills: list[Path]) -> list[str]:
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md: missing"]
    try:
        listed = cataloged_skills(readme.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"README.md: {exc}"]
    found = [path.name for path in skills]
    errors: list[str] = []
    if sorted(listed) != found:
        errors.append(
            "README.md skill table must list each skill directory exactly once: "
            f"table={listed} dirs={found}"
        )
    if len(listed) != len(set(listed)):
        errors.append(f"README.md skill table has duplicate entries: {listed}")
    return errors


def validate_repo(root: Path) -> list[str]:
    skills = discover_skills(root)
    errors = validate_catalog(root, skills)
    for skill in skills:
        errors.extend(validate_skill(skill))
    errors.extend(validate_json_files(root))
    errors.extend(validate_relative_links(root))
    return errors


def main() -> int:
    root = ROOT if len(sys.argv) == 1 else Path(sys.argv[1]).resolve()
    errors = validate_repo(root)
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors))
        return 1
    skills = discover_skills(root)
    print(
        f"OK: {len(skills)} skills, "
        f"{len(collect_json_paths(root))} JSON files, "
        f"{len(collect_markdown_paths(root))} Markdown files"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
