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
TERMINAL_STATUSES = {"complete", "blocked", "needs_user_decision", "failed"}


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
    *,
    allow_stall_for_adjudication: bool = False,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "latest_open": set(),
        "latest_round": 0,
        "stalled_sets": [],
    }
    require(isinstance(history, list), f"{label} must be a list", errors)
    if not isinstance(history, list):
        return summary

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
            if current_open == previous_open and current_open:
                if allow_stall_for_adjudication:
                    summary["stalled_sets"].append(frozenset(current_open))
                else:
                    errors.append(f"{label} stalled with an unchanged open fingerprint set")
            newly_open = current_open - previous_open
            actually_closed = previous_open - current_open
            if newly_open and actually_closed and len(current_open) >= len(previous_open):
                errors.append(f"{label} churned blockers without net reduction")
        previous_open = current_open

        if isinstance(round_number, int) and round_number > summary["latest_round"]:
            summary["latest_round"] = round_number
            summary["latest_open"] = current_open

    return summary


def validate_adjudication_history(
    history: Any,
    max_protocol_rounds: int,
    run_status: Any,
    errors: list[str],
) -> set[frozenset[str]]:
    label = "convergence.adjudication_history"
    require(isinstance(history, list), f"{label} must be a list", errors)
    if not isinstance(history, list):
        return set()

    covered: set[frozenset[str]] = set()
    protocol_counts: dict[frozenset[str], int] = {}
    user_authorized: set[frozenset[str]] = set()
    failed_protocol: set[frozenset[str]] = set()
    seen_ids: set[str] = set()

    for index, record in enumerate(history):
        prefix = f"{label}[{index}]"
        require(isinstance(record, dict), f"{prefix} must be an object", errors)
        if not isinstance(record, dict):
            continue

        adjudication_id = record.get("id")
        require(isinstance(adjudication_id, str) and bool(adjudication_id), f"{prefix} has invalid id", errors)
        if isinstance(adjudication_id, str) and adjudication_id:
            require(adjudication_id not in seen_ids, f"{label} repeats id {adjudication_id!r}", errors)
            seen_ids.add(adjudication_id)

        require(record.get("kind") == "repair", f"{prefix}.kind must be 'repair'", errors)
        fingerprints = record.get("fingerprints")
        require(
            isinstance(fingerprints, list)
            and bool(fingerprints)
            and all(isinstance(value, str) and value for value in fingerprints),
            f"{prefix} has invalid fingerprints",
            errors,
        )
        if not isinstance(fingerprints, list) or not fingerprints:
            continue
        fingerprint_set = frozenset(value for value in fingerprints if isinstance(value, str) and value)
        require(len(fingerprint_set) == len(fingerprints), f"{prefix} duplicates fingerprints", errors)

        authority = record.get("authority")
        decision = record.get("decision")
        status = record.get("status")
        require(authority in {"protocol", "user"}, f"{prefix} has invalid authority", errors)
        require(
            decision
            in {
                "pending",
                "authorize_root_cause_repair",
                "needs_user_decision",
                "blocked",
                "failed",
            },
            f"{prefix} has invalid decision",
            errors,
        )
        require(
            status in {"in_progress", "authorized", "fixed_pending_reverify", "passed", "failed"},
            f"{prefix} has invalid status",
            errors,
        )
        attempt = record.get("attempt")
        require(isinstance(attempt, int) and attempt > 0, f"{prefix} has invalid attempt", errors)

        if decision == "pending":
            require(status == "in_progress", f"{prefix} pending decision must be in_progress", errors)

        if authority == "protocol":
            protocol_counts[fingerprint_set] = protocol_counts.get(fingerprint_set, 0) + 1
            require(
                protocol_counts[fingerprint_set] <= max_protocol_rounds,
                f"{prefix} exceeds protocol-funded repair budget for its fingerprint set",
                errors,
            )
            require(
                isinstance(attempt, int) and attempt <= max_protocol_rounds,
                f"{prefix} attempt exceeds protocol-funded repair budget",
                errors,
            )
            if decision == "authorize_root_cause_repair":
                require(record.get("scope_unchanged") is True, f"{prefix} changes approved scope", errors)
                require(record.get("acceptance_unchanged") is True, f"{prefix} changes acceptance contract", errors)
                require(record.get("new_authority_required") is False, f"{prefix} requires new user authority", errors)
                for field in (
                    "work_item_id",
                    "adjudicator_target",
                    "root_cause_evidence",
                    "failing_regression",
                    "reacceptance_matrix",
                    "owner_target",
                    "finder_target",
                ):
                    require(bool(record.get(field)), f"{prefix} is missing {field}", errors)
                if record.get("adjudicator_target"):
                    require(
                        record.get("adjudicator_target")
                        not in {record.get("owner_target"), record.get("finder_target")},
                        f"{prefix} adjudicator must be independent from owner and finder",
                        errors,
                    )
            if decision in {"pending", "authorize_root_cause_repair"}:
                covered.add(fingerprint_set)
            if status == "failed":
                failed_protocol.add(fingerprint_set)
        elif authority == "user" and decision == "authorize_root_cause_repair":
            require(bool(record.get("scope")), f"{prefix} user exception lacks exact scope", errors)
            user_authorized.add(fingerprint_set)
            covered.add(fingerprint_set)

    if run_status not in TERMINAL_STATUSES:
        for fingerprint_set in failed_protocol - user_authorized:
            errors.append(
                f"{label} has a failed protocol-funded repair without terminal status or explicit user exception: "
                f"{sorted(fingerprint_set)!r}"
            )

    return covered


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
    schema_version = state.get("schema_version")
    require(schema_version in {1, 2}, "schema_version must be 1 or 2", errors)
    require(state.get("skill") == "multi-agent-delivery", "skill name mismatch", errors)
    require(bool(str(state.get("objective", "")).strip()), "objective is empty", errors)
    require(state.get("phase") in PHASES, "invalid phase", errors)
    require(state.get("status") in STATUSES, "invalid status", errors)

    plan = state.get("plan")
    require(isinstance(plan, dict), "plan must be an object", errors)
    if isinstance(plan, dict):
        require(isinstance(plan.get("version"), int), "plan.version must be an integer", errors)
        if schema_version == 2:
            review_round = plan.get("review_round")
            max_review_rounds = plan.get("max_review_rounds")
            amendment_round = plan.get("amendment_round")
            max_amendment_rounds = plan.get("max_amendment_rounds")
            require(
                isinstance(review_round, int) and review_round >= 0,
                "plan.review_round must be a non-negative integer",
                errors,
            )
            require(
                isinstance(max_review_rounds, int) and max_review_rounds > 0,
                "plan.max_review_rounds must be positive",
                errors,
            )
            if isinstance(review_round, int) and isinstance(max_review_rounds, int):
                require(review_round <= max_review_rounds, "plan review round budget exceeded", errors)
            require(
                isinstance(amendment_round, int) and amendment_round >= 0,
                "plan.amendment_round must be a non-negative integer",
                errors,
            )
            require(
                isinstance(max_amendment_rounds, int) and max_amendment_rounds >= 0,
                "plan.max_amendment_rounds must be a non-negative integer",
                errors,
            )
            if isinstance(amendment_round, int) and isinstance(max_amendment_rounds, int):
                require(amendment_round <= max_amendment_rounds, "plan amendment round budget exceeded", errors)
        else:
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
    if schema_version == 2 and isinstance(implementation, dict):
        max_adjudicated = implementation.get("max_adjudicated_repair_rounds")
        require(
            isinstance(max_adjudicated, int) and max_adjudicated >= 0,
            "implementation.max_adjudicated_repair_rounds must be a non-negative integer",
            errors,
        )

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
            if schema_version == 2 and isinstance(plan, dict):
                plan_round_limit_value = plan.get("max_review_rounds", 3)
                amendment_round_limit_value = plan.get("max_amendment_rounds", 3)
            else:
                plan_round_limit_value = plan.get("max_rounds", 3) if isinstance(plan, dict) else 3
                amendment_round_limit_value = 0
            repair_round_limit_value = (
                implementation.get("max_repair_rounds", 3)
                if isinstance(implementation, dict)
                else 3
            )
            plan_round_limit = plan_round_limit_value if isinstance(plan_round_limit_value, int) else 0
            amendment_round_limit = (
                amendment_round_limit_value if isinstance(amendment_round_limit_value, int) else 0
            )
            repair_round_limit = repair_round_limit_value if isinstance(repair_round_limit_value, int) else 0
            validate_review_history(
                convergence.get("plan_review_history", []),
                "convergence.plan_review_history",
                plan_round_limit,
                errors,
            )
            if schema_version == 2:
                validate_review_history(
                    convergence.get("plan_amendment_history", []),
                    "convergence.plan_amendment_history",
                    amendment_round_limit,
                    errors,
                )
            repair_summary = validate_review_history(
                convergence.get("repair_review_history", []),
                "convergence.repair_review_history",
                repair_round_limit,
                errors,
                allow_stall_for_adjudication=schema_version == 2,
            )
            if schema_version == 2:
                max_adjudicated_value = (
                    implementation.get("max_adjudicated_repair_rounds", 1)
                    if isinstance(implementation, dict)
                    else 1
                )
                max_adjudicated = max_adjudicated_value if isinstance(max_adjudicated_value, int) else 0
                covered = validate_adjudication_history(
                    convergence.get("adjudication_history", []),
                    max_adjudicated,
                    state.get("status"),
                    errors,
                )
                latest_open = frozenset(repair_summary["latest_open"])
                reached_limit = (
                    bool(latest_open)
                    and repair_summary["latest_round"] >= repair_round_limit
                )
                stalled = bool(repair_summary["stalled_sets"])
                if (reached_limit or stalled) and state.get("status") not in TERMINAL_STATUSES:
                    require(
                        latest_open in covered,
                        "repair convergence stop lacks a matching adjudication record",
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
