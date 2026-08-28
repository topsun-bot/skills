from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class TriggerPolicyTests(unittest.TestCase):
    def test_frontmatter_requires_current_explicit_invocation(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n", skill_text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group("frontmatter") if match else ""

        self.assertIn("$multi-agent-delivery", frontmatter)
        self.assertIn("Use only when", frontmatter)
        self.assertIn("current request", frontmatter)
        for forbidden in (
            "Use when the user asks for multi-agent collaboration",
            "long-running autonomous delivery",
            "robotics development",
        ):
            self.assertNotIn(forbidden, frontmatter)

    def test_machine_policy_disables_implicit_invocation(self) -> None:
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertNotIn("allow_implicit_invocation: true", metadata)
        self.assertIn("$multi-agent-delivery", metadata)

    def test_body_does_not_reenable_implicit_invocation(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Invocation gate", skill_text)
        self.assertIn("Keep implicit invocation disabled", skill_text)
        self.assertNotIn("Keep implicit invocation enabled", skill_text)


if __name__ == "__main__":
    unittest.main()
