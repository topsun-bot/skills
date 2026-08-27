# Plan Contract and Review Gate

## Required plan sections

The planner must write `.agent-delivery/plan.md` with:

1. Objective and explicit non-goals.
2. Verified facts with source paths or commands.
3. Unknowns, assumptions, and validation actions.
4. Requirements traceability matrix.
5. Architecture options considered, tradeoffs, and selected approach.
6. Work items in dependency order.
7. One write owner and bounded file scope per work item.
8. Acceptance commands or observations for every work item.
9. Required evidence level for every acceptance condition.
10. Safety, authorization, rollback, and recovery constraints.
11. Completion conditions and stop conditions.
12. Plan version and finding-disposition table after revision.

Each work item must be independently implementable and verifiable. Reject vague tasks such as "finish integration" or acceptance such as "looks correct".

Split a work item when it crosses more than two independently testable subsystem boundaries, requires several package families plus bundle/docs work before any check can run, or cannot produce a focused self-check checkpoint before the full feature is assembled. Sequential work items may keep the same implementer when file ownership overlaps; split the checkpoints, not the ownership. Prefer dependency-ordered slices such as contract → Host capability → client package → assembly → browser evidence over one giant work item.

### Mechanical fallout amendment

After implementation starts, one bounded adjudication may add an exact test fixture, generated artifact, aggregate registration, documentation pairing, or mechanical reference update that an executable compiler/generator exposed as a direct consequence of the approved change. Record the file, failing command, authority, and proof that behavior and acceptance scope do not expand. Keep the same implementer. Do not restart full plan review for this mechanical fallout. Any new application behavior, public contract decision, security model change, or independent feature still requires plan review.

Every requirement and acceptance condition must record provenance: `user`, `repository_instruction`, `existing_contract`, or `mandatory_safety_security`. Keep optional hardening and design preferences labeled as recommendations. Do not silently promote them into delivery blockers.

Treat `.agent-delivery/run.json` as the only authority for mutable approval status. Do not add `DRAFT`, `PENDING_REVIEW`, `APPROVED`, or another mutable gate status to `plan.md`; duplicating it creates stale state after review.

Count the initial Plan Gate and post-approval targeted amendments separately. `plan.review_round` covers only the initial comprehensive/closure sequence. `plan.amendment_round` covers a later implementation-discovered contract or scope amendment. Increment `plan.version` for either, but never use the version number as a round budget and never reset one counter by moving work to the other.

## Review dimensions

The plan reviewer must independently check:

- Requirement coverage and contradictions.
- Reliance on unverified assumptions.
- Architectural feasibility in the current workspace.
- Dependency order and interface ownership.
- Task granularity and overlapping writes.
- Executability of acceptance checks.
- Evidence strength relative to the claim.
- Failure recovery, rollback, and safe-state behavior.
- Real service, model, browser, simulation, or robot requirements.
- Missing authority for consequential actions.

## Review report

Write `.agent-delivery/plan-review.md` with:

```markdown
# Plan Review

- Plan version: <N>
- Reviewer target: <target>
- Verdict: PASS | FAIL
- Blocking findings: <N>

## Findings

### PLAN-001
- Fingerprint: <requirement>|<plan section>|<failure mode>
- Authority: user | repository_instruction | existing_contract | mandatory_safety_security
- Authority evidence: <exact source>
- Severity: blocking | major | minor
- Plan section: <section>
- Evidence: <source>
- Problem: <specific defect>
- Required change: <observable revision>
- Re-review condition: <how closure is proven>
```

Only `PASS` with zero blocking findings opens implementation. The orchestrator cannot waive a blocking finding. The same reviewer must re-evaluate revised versions when available.

## Review convergence

- Round 1 is the only comprehensive review. It must enumerate the full known blocker set and freeze one stable fingerprint per distinct failure mode.
- Round 2 and later are closure reviews. Preserve IDs and fingerprints; report each as `open`, `closed`, `disputed`, or `needs_user_decision`.
- Deduplicate findings that share a requirement, plan section, failure mode, reproduction, and re-review condition even when wording differs.
- A later new blocker is valid only when the plan revision introduced it. Mark it `introduced_by_revision: true` and cite the exact revision diff plus evidence. Otherwise record it as a non-blocking suggestion or reviewer omission; do not restart the loop.
- Do not expand requirements, demand implementation detail that belongs in a work item, or raise evidence levels beyond the frozen user/plan contract.
- Do not use a guarantee invented by the plan as independent blocking authority. The planner may remove or downgrade speculative guarantees when they are not required by the user, repository, an existing contract, or a mandatory safety/security/data-loss invariant.
- If the open fingerprint set is unchanged for two consecutive reviews, or closed blockers are replaced by unrelated new blockers with no net reduction, stop revision and return `NEEDS_USER_DECISION`.
- `PASS` may include non-blocking suggestions. Suggestions never keep the Plan Gate closed.

## Planner revision

The same planner must update the plan and add:

```markdown
## Finding disposition for version <N>

| Finding | Disposition | Plan change | Evidence |
|---|---|---|---|
| PLAN-001 | fixed / disputed / needs decision | section | source |
```

Disputed blocking findings require the reviewer to accept the evidence or the run to become `NEEDS_USER_DECISION`.
