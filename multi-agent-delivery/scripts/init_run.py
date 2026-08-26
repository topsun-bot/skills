#!/usr/bin/env python3
"""Initialize a non-destructive multi-agent delivery run directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ASSETS = SKILL_ROOT / "assets"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Existing project root")
    parser.add_argument("--objective", required=True, help="Full user objective")
    parser.add_argument("--requirements", default="", help="Requirements file path")
    parser.add_argument("--domain", default="general", help="Task domain")
    parser.add_argument("--max-plan-rounds", type=int, default=3)
    parser.add_argument("--max-repair-rounds", type=int, default=3)
    return parser.parse_args()


def copy_template(name: str, destination: Path) -> None:
    shutil.copyfile(ASSETS / name, destination)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(f"error: project root does not exist: {root}", file=sys.stderr)
        return 2
    if not args.objective.strip():
        print("error: objective must not be empty", file=sys.stderr)
        return 2
    if args.max_plan_rounds < 1 or args.max_repair_rounds < 1:
        print("error: round limits must be positive", file=sys.stderr)
        return 2

    run_dir = root / ".agent-delivery"
    state_path = run_dir / "run.json"
    if state_path.exists():
        print(f"error: run already exists: {state_path}", file=sys.stderr)
        return 3

    run_dir.mkdir(parents=True, exist_ok=True)
    for relative in ("issues", "test-reports", "logs", "evidence"):
        (run_dir / relative).mkdir(exist_ok=True)

    with (ASSETS / "run-state.template.json").open(encoding="utf-8") as handle:
        state = json.load(handle)

    now = utc_now()
    requirements_path = ""
    if args.requirements:
        candidate = Path(args.requirements).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        requirements_path = str(candidate.resolve())

    state.update(
        objective=args.objective.strip(),
        domain=args.domain.strip() or "general",
        requirements_path=requirements_path,
        created_at=now,
        updated_at=now,
    )
    state["plan"]["max_rounds"] = args.max_plan_rounds
    state["implementation"]["max_repair_rounds"] = args.max_repair_rounds
    state["convergence"]["last_progress_at"] = now
    state["audit_log"].append(
        {"at": now, "event": "run_initialized", "phase": "discovery"}
    )

    temporary = state_path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(state_path)

    copy_template("discovery.template.md", run_dir / "discovery.md")
    copy_template("plan.template.md", run_dir / "plan.md")
    copy_template("plan-review.template.md", run_dir / "plan-review.md")
    copy_template("lessons-learned.template.md", run_dir / "lessons-learned.md")
    (run_dir / "logs" / "main-log.md").write_text(
        f"# Delivery Log\n\n- {now} run initialized in discovery phase\n",
        encoding="utf-8",
    )

    print(state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
