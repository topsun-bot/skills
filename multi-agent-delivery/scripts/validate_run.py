#!/usr/bin/env python3
"""Validate multi-agent delivery state and completion invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PHASES = {
    "discovery",
    "planning",
    "plan_review",
    "implementation",
    "verification",
    "final_acceptance",
    "complete",
}
STATUSES = {"active", "complete", "blocked", "needs_user_decision", "failed"}
LEVELS = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Project root")
    parser.add_argument("--require-complete", action="store_true")
    return parser.parse_args()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def is_blocking_open(issue: dict[str, Any]) -> bool:
    return issue.get("severity") == "blocking" and issue.get("status") != "closed"


def validate_review_history(
    history: Any,
    label: str,
    max_rounds: int,
    errors: list[str],
) -> None:
    require(isinstance(history, list), f"{label} must be a list", errors)
    if not isinstance(history, list):
        return

    known: set[str] = set()
    previous_open: set[str] | None = None
    seen_rounds: set[int] = set()

    for index, record in enumerate(history):
        require(isinstance(record, dict), f"{label}[{index}] must be an object", errors)
        if not isinstance(record, dict):
            continue

        round_number = record.get("round")
        require(isinstance(round_number, int) and round_number > 0, f"{label}[{index}] has invalid round", errors)
        if isinstance(round_number, int):
            require(round_number not in seen_rounds, f"{label} repeats round {round_number}", errors)
            require(round_number <= max_rounds, f"{label} exceeds round budget", errors)
            seen_rounds.add(round_number)

        open_items = record.get("open_fingerprints", [])
        closed_items = record.get("closed_fingerprints", [])
        new_findings = record.get("new_findings", [])
        require(isinstance(open_items, list), f"{label}[{index}].open_fingerprints must be a list", errors)
        require(isinstance(closed_items, list), f"{label}[{index}].closed_fingerprints must be a list", errors)
        require(isinstance(new_findings, list), f"{label}[{index}].new_findings must be a list", errors)
        if not all(isinstance(value, str) and value for value in open_items):
            errors.append(f"{label}[{index}] has invalid open fingerprint")
        if not all(isinstance(value, str) and value for value in closed_items):
            errors.append(f"{label}[{index}] has invalid closed fingerprint")

        current_open = set(open_items) if isinstance(open_items, list) else set()
        current_closed = set(closed_items) if isinstance(closed_items, list) else set()
        require(len(current_open) == len(open_items), f"{label}[{index}] duplicates open fingerprints", errors)
        require(len(current_closed) == len(closed_items), f"{label}[{index}] duplicates closed fingerprints", errors)
        require(not current_open.intersection(current_closed), f"{label}[{index}] marks fingerprints both open and closed", errors)

        unseen_this_round: set[str] = set()
        if isinstance(new_findings, list):
            for finding_index, finding in enumerate(new_findings):
                require(
                    isinstance(finding, dict),
                    f"{label}[{index}].new_findings[{finding_index}] must be an object",
                    errors,
                )
                if not isinstance(finding, dict):
                    continue
                fingerprint = finding.get("fingerprint")
                require(
                    isinstance(fingerprint, str) and bool(fingerprint),
                    f"{label}[{index}].new_findings[{finding_index}] has invalid fingerprint",
                    errors,
                )
                if not isinstance(fingerprint, str) or not fingerprint:
                    continue
                require(
                    fingerprint not in unseen_this_round,
                    f"{label}[{index}] duplicates new finding {fingerprint!r}",
                    errors,
                )
                unseen_this_round.add(fingerprint)
                if index > 0 and fingerprint not in known:
                    require(
                        finding.get("introduced_by_revision") is True,
                        f"{label}[{index}] adds late blocker {fingerprint!r} without revision causality",
                        errors,
                    )
                    require(
                        bool(finding.get("evidence")),
                        f"{label}[{index}] late blocker {fingerprint!r} lacks evidence",
                        errors,
                    )

        require(
            current_open.issubset(known.union(unseen_this_round)),
            f"{label}[{index}] has open fingerprints absent from the finding ledger",
            errors,
        )
        known.update(unseen_this_round)

        if previous_open is not None:
            require(current_open != previous_open, f"{label} stalled with an unchanged open fingerprint set", errors)
            newly_open = current_open - previous_open
            actually_closed = previous_open - current_open
            if newly_open and actually_closed and len(current_open) >= len(previous_open):
                errors.append(f"{label} churned blockers without net reduction")
        previous_open = current_open


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    state_path = root / ".agent-delivery" / "run.json"
    if not state_path.is_file():
        print(f"error: missing state file: {state_path}", file=sys.stderr)
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read state: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    require(state.get("schema_version") == 1, "schema_version must be 1", errors)
    require(state.get("skill") == "multi-agent-delivery", "skill name mismatch", errors)
    require(bool(str(state.get("objective", "")).strip()), "objective is empty", errors)
    require(state.get("phase") in PHASES, "invalid phase", errors)
    require(state.get("status") in STATUSES, "invalid status", errors)

    plan = state.get("plan")
    require(isinstance(plan, dict), "plan must be an object", errors)
    if isinstance(plan, dict):
        require(isinstance(plan.get("version"), int), "plan.version must be an integer", errors)
        require(isinstance(plan.get("round"), int), "plan.round must be an integer", errors)
        require(
            isinstance(plan.get("max_rounds"), int) and plan.get("max_rounds", 0) > 0,
            "plan.max_rounds must be positive",
            errors,
        )
        if state.get("phase") in {"implementation", "verification", "final_acceptance", "complete"}:
            require(plan.get("status") == "approved", "implementation started before plan approval", errors)
            require(plan.get("review_verdict") == "PASS", "plan review verdict is not PASS", errors)
            require(not plan.get("blocking_findings"), "plan still has blocking findings", errors)
            require(bool(plan.get("author_target")), "missing planner target", errors)
            require(bool(plan.get("reviewer_target")), "missing plan reviewer target", errors)
            require(
                plan.get("author_target") != plan.get("reviewer_target"),
                "planner and reviewer must be different agents",
                errors,
            )

    implementation = state.get("implementation")
    require(isinstance(implementation, dict), "implementation must be an object", errors)
    work_items = implementation.get("work_items", []) if isinstance(implementation, dict) else []
    require(isinstance(work_items, list), "implementation.work_items must be a list", errors)

    verification = state.get("verification")
    require(isinstance(verification, dict), "verification must be an object", errors)
    selected_roles = verification.get("selected_roles", []) if isinstance(verification, dict) else []
    reports = verification.get("reports", []) if isinstance(verification, dict) else []
    require(isinstance(selected_roles, list), "verification.selected_roles must be a list", errors)
    require(isinstance(reports, list), "verification.reports must be a list", errors)

    issues = state.get("issues")
    require(isinstance(issues, list), "issues must be a list", errors)
    if not isinstance(issues, list):
        issues = []

    requirements = state.get("requirements")
    require(isinstance(requirements, list), "requirements must be a list", errors)
    if not isinstance(requirements, list):
        requirements = []

    convergence = state.get("convergence")
    if convergence is not None:
        require(isinstance(convergence, dict), "convergence must be an object", errors)
        if isinstance(convergence, dict):
            max_attempts = convergence.get("max_agent_attempts_per_phase")
            require(
                isinstance(max_attempts, int) and max_attempts > 0,
                "convergence.max_agent_attempts_per_phase must be positive",
                errors,
            )
            attempts = convergence.get("phase_attempts")
            require(isinstance(attempts, dict), "convergence.phase_attempts must be an object", errors)
            if isinstance(attempts, dict) and isinstance(max_attempts, int):
                for phase_name, attempt_count in attempts.items():
                    require(phase_name in PHASES - {"complete"}, f"invalid attempt phase {phase_name!r}", errors)
                    require(
                        isinstance(attempt_count, int) and attempt_count >= 0,
                        f"attempt count for {phase_name!r} must be a non-negative integer",
                        errors,
                    )
                    if isinstance(attempt_count, int):
                        require(
                            attempt_count <= max_attempts,
                            f"attempt budget exceeded for phase {phase_name!r}",
                            errors,
                        )
            require(
                isinstance(convergence.get("last_progress_at"), str),
                "convergence.last_progress_at must be a string",
                errors,
            )
            plan_round_limit = plan.get("max_rounds", 3) if isinstance(plan, dict) else 3
            repair_round_limit = implementation.get("max_repair_rounds", 3) if isinstance(implementation, dict) else 3
            validate_review_history(
                convergence.get("plan_review_history", []),
                "convergence.plan_review_history",
                plan_round_limit,
                errors,
            )
            validate_review_history(
                convergence.get("repair_review_history", []),
                "convergence.repair_review_history",
                repair_round_limit,
                errors,
            )

    for index, requirement in enumerate(requirements):
        required = requirement.get("required_level")
        actual = requirement.get("actual_level")
        require(required in LEVELS, f"requirements[{index}] has invalid required_level", errors)
        require(actual in LEVELS, f"requirements[{index}] has invalid actual_level", errors)
        if required in LEVELS and actual in LEVELS:
            require(
                LEVELS[actual] >= LEVELS[required],
                f"requirements[{index}] evidence is below required level",
                errors,
            )

    if args.require_complete:
        require(state.get("phase") == "complete", "phase is not complete", errors)
        require(state.get("status") == "complete", "status is not complete", errors)
        require(bool(implementation.get("started")), "implementation never started", errors)
        require(bool(work_items), "no implementation work items recorded", errors)
        owner_targets: set[str] = set()
        for index, item in enumerate(work_items):
            require(item.get("status") == "accepted", f"work item {index} is not accepted", errors)
            require(bool(item.get("owner_target")), f"work item {index} has no owner target", errors)
            if item.get("owner_target"):
                owner_targets.add(item["owner_target"])
        require(bool(selected_roles), "no independent verifier roles selected", errors)
        passed_roles = {
            report.get("role")
            for report in reports
            if isinstance(report, dict) and report.get("verdict") == "PASS"
        }
        for role in selected_roles:
            require(role in passed_roles, f"selected verifier role {role!r} has no PASS report", errors)
        require(bool(requirements), "no requirements recorded for completion", errors)
        for index, requirement in enumerate(requirements):
            require(requirement.get("verdict") == "PASS", f"requirement {index} did not pass", errors)
            require(bool(requirement.get("evidence")), f"requirement {index} has no evidence", errors)
        require(not any(is_blocking_open(issue) for issue in issues), "open blocking issues remain", errors)
        final = state.get("final_acceptance", {})
        require(final.get("status") == "PASS", "final acceptance did not pass", errors)
        require(bool(final.get("reviewer_target")), "final acceptance reviewer target is missing", errors)
        require(
            final.get("reviewer_target") not in owner_targets,
            "final acceptance reviewer must be independent from implementers",
            errors,
        )
        report_path = final.get("report_path")
        require(bool(report_path), "final acceptance report path is missing", errors)
        if report_path:
            report = Path(report_path)
            if not report.is_absolute():
                report = root / report
            require(report.is_file(), "final acceptance report does not exist", errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: run state satisfies requested invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
