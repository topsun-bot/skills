#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill_pack import discover_skills, validate_repo


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def valid_skill(root: Path, name: str) -> None:
    write(
        root / name / "SKILL.md",
        (
            f"---\nname: {name}\ndescription: A real skill used by CI fixtures.\n---\n\n"
            f"# {name}\n\nSee [notes](references/notes.md).\n"
        ),
    )
    write(root / name / "references" / "notes.md", "fixture\n")
    write(
        root / name / "agents" / "openai.yaml",
        (
            "interface:\n"
            f'  display_name: "{name}"\n'
            "  short_description: fixture skill\n"
            f'  default_prompt: "Use ${name} on this fixture."\n'
        ),
    )


def valid_readme(root: Path, names: list[str]) -> None:
    rows = "\n".join(f"| [`{name}`]({name}/) | fixture | explicit |" for name in names)
    write(
        root / "README.md",
        (
            "# Skills\n\n"
            "## Skill 列表\n\n"
            "| Skill | 作用 | 触发方式 |\n"
            "| --- | --- | --- |\n"
            f"{rows}\n"
        ),
    )


class SkillPackValidatorTests(unittest.TestCase):
    def test_discover_skills_uses_skill_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "demo-skill")
            self.assertEqual(discover_skills(root), [root / "demo-skill"])

    def test_valid_pack_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "demo-skill")
            valid_readme(root, ["demo-skill"])
            write(root / "demo-skill" / "assets" / "state.json", json.dumps({"ok": True}))
            self.assertEqual(validate_repo(root), [])

    def test_missing_frontmatter_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "demo-skill")
            valid_readme(root, ["demo-skill"])
            write(root / "demo-skill" / "SKILL.md", "---\ndescription: no name\n---\n\n# Demo\n")
            errors = validate_repo(root)
            self.assertTrue(any("frontmatter name" in item for item in errors), errors)

    def test_broken_relative_link_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "demo-skill")
            valid_readme(root, ["demo-skill"])
            write(root / "demo-skill" / "SKILL.md", (
                "---\nname: demo-skill\ndescription: broken link fixture.\n---\n\n"
                "[missing](references/does-not-exist.md)\n"
            ))
            errors = validate_repo(root)
            self.assertTrue(any("broken relative link" in item for item in errors), errors)

    def test_invalid_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "demo-skill")
            valid_readme(root, ["demo-skill"])
            write(root / "demo-skill" / "assets" / "bad.json", "{not json")
            errors = validate_repo(root)
            self.assertTrue(any("invalid JSON" in item for item in errors), errors)

    def test_readme_must_catalog_every_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_skill(root, "alpha-skill")
            valid_skill(root, "beta-skill")
            valid_readme(root, ["alpha-skill"])
            errors = validate_repo(root)
            self.assertTrue(any("skill table" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
