# Convergence and Anti-Loop Rules

## Artifact-first checkpoints

An active agent thread is not evidence of progress. Each phase must first land a minimal valid artifact, then refine it:

- Discovery: `discovery.md` with `IN_PROGRESS`, sources, known facts, and unknown sections.
- Planning: `plan.md` with version, objective, requirements, candidate work items, and unresolved sections.
- Plan review: `plan-review.md` with plan version, reviewer target, review mode, `IN_PROGRESS`, and an initially empty finding ledger.
- Implementation: a scoped diff or explicit blocker record.
- Verification: a report header with acceptance surface, commands to run, and `IN_PROGRESS`.

If a role performs broad exploration but its required artifact hash does not change, treat the attempt as stalled.

Use a default 10-minute no-artifact window for local coding tasks unless the approved plan justifies a longer bounded command. Send at most one nudge asking the agent to stop exploration and land the checkpoint. If the next agent turn still changes no required artifact, interrupt it and consume the attempt. Repeated nudges are not progress.

Long-running commands use their declared command budget instead of the agent no-artifact window. Before launch, record the exact command, expected output/evidence, timeout, resource ceiling, and cleanup owner. While the supervised command is still inside that budget, waiting is not a stalled agent. On timeout or resource failure, record the exit evidence and allow at most one retry with a changed, evidence-based hypothesis; increasing time or memory alone is not a new hypothesis.

## Attempt budgets

- Default maximum: two agent attempts per phase, meaning one original and one replacement.
- A failed resume, timeout, interrupted turn, or replacement with no required artifact counts as an attempt.
- Never reset the counter when changing agent targets.
- At the attempt limit, write the evidence and return `NEEDS_USER_DECISION` or `BLOCKED`; do not spawn a third agent.

## Stable findings

Use one fingerprint per distinct failure mode:

```text
<requirement-id>|<artifact-or-section>|<failure-mode>
```

Wording, severity explanation, or suggested implementation may change without creating a new fingerprint. Preserve IDs and fingerprints through every revision.

## Review scope freeze

1. Round 1 is comprehensive and freezes the known blocker set.
2. Round 2+ are closure-only.
3. A later new blocker is allowed only when the revision introduced it. Require `introduced_by_revision: true`, exact diff evidence, and a reproduction or contradiction.
4. A reviewer omission from round 1 is normally a suggestion, not a reason to restart the plan loop. Only newly introduced safety, security, data-loss, or explicit-requirement violations may block.
5. Suggestions never keep a gate closed.

Freeze before repair: a comprehensive reviewer or verifier must attempt every required surface, mark its report `COMPLETE`, and publish the full fingerprint set before the orchestrator sends ordinary repair work. A report with required `pending`, `deferred`, or `not counted` surfaces is not complete. Never let review and repair run against the same moving artifact.

When a prerequisite defect genuinely prevents later checks from producing meaningful evidence, allow one staged prerequisite repair while the report remains `IN_PROGRESS` and mode remains `comprehensive`. Resume the remaining first-pass checks afterward and freeze once. Never relabel a different later failure under the prerequisite fingerprint.

Every blocking fingerprint must cite its authority: an explicit user requirement, an applicable repository instruction, an existing public/runtime contract, or a mandatory safety/security/data-loss invariant. A guarantee invented by the plan itself is not independent authority; the planner may remove or downgrade it instead of implementing speculative hardening.

## Progress and churn

Progress means at least one of:

- The required artifact hash changed materially.
- The open fingerprint set shrank.
- A disputed fingerprint gained decisive evidence.
- The phase advanced.

For implementation, checkpoint latency matters. If one work item must cross multiple independently testable subsystems before any self-check can run, return to the plan and split it into dependency-ordered work items. The same implementer may retain overlapping ownership, but each slice needs its own artifact checkpoint and focused command result.

Stop and escalate when:

- Two consecutive rounds have the same open fingerprint set.
- Closed fingerprints are replaced by unrelated new fingerprints and the open count does not shrink.
- A role exhausts its attempt budget.
- The round limit is reached.

At escalation, do one bounded root-cause or adjudication pass. The adjudicator may choose `PASS` with residual suggestions, `NEEDS_USER_DECISION`, `BLOCKED`, or `FAILED`; it may not request another ordinary rewrite round.

## State recording

Record phase attempts, last progress time, last artifact hash, and review history in `run.json`. Each review history entry should include:

```json
{
  "round": 1,
  "artifact_version": 1,
  "open_fingerprints": ["R1|section-5|missing-contract"],
  "closed_fingerprints": [],
  "new_findings": [
    {
      "fingerprint": "R1|section-5|missing-contract",
      "introduced_by_revision": false,
      "evidence": "requirements.md:R1"
    }
  ]
}
```
