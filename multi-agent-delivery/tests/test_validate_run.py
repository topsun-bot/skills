from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "run-state.template.json"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_run.py"
INITIALIZER = SKILL_ROOT / "scripts" / "init_run.py"


def load_state() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def repair_history() -> list[dict]:
    fingerprint_a = "R1|runtime|freshness"
    fingerprint_b = "R2|runtime|storage"
    return [
        {
            "round": 1,
            "artifact_version": 1,
            "open_fingerprints": [fingerprint_a, fingerprint_b],
            "closed_fingerprints": [],
            "new_findings": [
                {
                    "fingerprint": fingerprint_a,
                    "introduced_by_revision": False,
                    "evidence": "report.md#A",
                },
                {
                    "fingerprint": fingerprint_b,
                    "introduced_by_revision": False,
                    "evidence": "report.md#B",
                },
            ],
        },
        {
            "round": 2,
            "artifact_version": 2,
            "open_fingerprints": [fingerprint_a],
            "closed_fingerprints": [fingerprint_b],
            "new_findings": [],
        },
        {
            "round": 3,
            "artifact_version": 3,
            "open_fingerprints": [fingerprint_a],
            "closed_fingerprints": [],
            "new_findings": [],
        },
    ]


def protocol_adjudication(**overrides: object) -> dict:
    record: dict = {
        "id": "ADJ-WI-01-001",
        "kind": "repair",
        "trigger": "repair_round_limit",
        "work_item_id": "WI-01",
        "adjudicator_target": "adjudicator",
        "fingerprints": ["R1|runtime|freshness"],
        "authority": "protocol",
        "decision": "authorize_root_cause_repair",
        "attempt": 1,
        "scope_unchanged": True,
        "acceptance_unchanged": True,
        "new_authority_required": False,
        "root_cause_evidence": ".agent-delivery/report.md#root-cause",
        "failing_regression": "pytest -q tests/test_freshness.py",
        "reacceptance_matrix": ".agent-delivery/adjudication.md",
        "owner_target": "impl-core",
        "finder_target": "verify-runtime",
        "status": "authorized",
    }
    record.update(overrides)
    return record


class ValidateRunTests(unittest.TestCase):
    def run_validator(self, state: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / ".agent-delivery"
            run_dir.mkdir()
            (run_dir / "run.json").write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(VALIDATOR), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

    def implementation_state(self) -> dict:
        state = load_state()
        state["objective"] = "exercise convergence"
        state["phase"] = "implementation"
        state["plan"].update(
            {
                "version": 1,
                "status": "approved",
                "review_round": 1,
                "author_target": "planner",
                "reviewer_target": "reviewer",
                "review_verdict": "PASS",
            }
        )
        state["implementation"]["started"] = True
        state["convergence"]["repair_review_history"] = repair_history()
        return state

    def test_template_state_is_valid(self) -> None:
        state = load_state()
        state["objective"] = "validate template"
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_split_plan_counter_overflow_is_rejected(self) -> None:
        state = load_state()
        state["objective"] = "reject overflow"
        state["plan"]["review_round"] = 4
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plan review round budget exceeded", result.stdout)

    def test_repair_limit_requires_matching_adjudication(self) -> None:
        result = self.run_validator(self.implementation_state())
        self.assertEqual(result.returncode, 1)
        self.assertIn("repair convergence stop lacks a matching adjudication record", result.stdout)

    def test_one_protocol_funded_root_cause_repair_is_valid(self) -> None:
        state = self.implementation_state()
        state["convergence"]["adjudication_history"] = [protocol_adjudication()]
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_protocol_adjudication_requires_decisive_evidence(self) -> None:
        state = self.implementation_state()
        state["convergence"]["adjudication_history"] = [
            protocol_adjudication(root_cause_evidence="", failing_regression="")
        ]
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 1)
        self.assertIn("is missing root_cause_evidence", result.stdout)
        self.assertIn("is missing failing_regression", result.stdout)

    def test_second_protocol_exception_for_same_set_is_rejected(self) -> None:
        state = self.implementation_state()
        second = copy.deepcopy(protocol_adjudication())
        second.update({"id": "ADJ-WI-01-002", "attempt": 2})
        state["convergence"]["adjudication_history"] = [protocol_adjudication(), second]
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 1)
        self.assertIn("exceeds protocol-funded repair budget", result.stdout)

    def test_failed_protocol_repair_cannot_remain_active(self) -> None:
        state = self.implementation_state()
        state["convergence"]["adjudication_history"] = [
            protocol_adjudication(status="failed")
        ]
        result = self.run_validator(state)
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed protocol-funded repair without terminal status", result.stdout)

    def test_initializer_creates_split_counters_and_adjudication_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = subprocess.run(
                [
                    sys.executable,
                    str(INITIALIZER),
                    "--root",
                    str(root),
                    "--objective",
                    "initialize v2 state",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((root / ".agent-delivery" / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(state["schema_version"], 2)
            self.assertEqual(state["plan"]["review_round"], 0)
            self.assertEqual(state["plan"]["amendment_round"], 0)
            self.assertEqual(state["implementation"]["max_adjudicated_repair_rounds"], 1)
            self.assertTrue((root / ".agent-delivery" / "adjudication.md").is_file())


if __name__ == "__main__":
    unittest.main()
