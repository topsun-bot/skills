# Implementation Issue Contract

Every failed verification finding must contain:

```markdown
### ISSUE-<work-item>-<number>
- Fingerprint: <requirement>|<component>|<failure mode>
- Finder target: <verifier target>
- Owner target: <implementer target>
- Severity: blocking | major | minor
- Status: open | fixed_pending_reverify | closed | disputed
- Requirement: <requirement ID>
- Files or component: <scope>
- Reproduction command or steps: <exact action>
- Expected result: <observable result>
- Actual result: <observable result>
- Evidence: <log, screenshot, output, or artifact path>
- Safety impact: <none or specific risk>
- Required repair: <behavioral requirement, not a speculative rewrite>
- Re-acceptance condition: <exact check>
```

## Routing

1. During the first comprehensive verification, keep findings staged in an `IN_PROGRESS` report. The orchestrator must not route ordinary findings for repair yet.
2. The verifier must attempt every required acceptance surface, mark each `PASS`, `FAIL`, or `BLOCKED` with evidence, then mark the report `COMPLETE` and freeze the full ID/fingerprint set. Any required surface labeled `pending`, `deferred`, or `not counted` keeps the report `IN_PROGRESS`.
3. Route the complete frozen issue batch to the implementation owner that introduced or owns the affected behavior.
4. Reuse the same implementation agent when available.
5. Keep the repair inside the owned scope unless the plan is formally revised.
6. Route `fixed_pending_reverify` to the original finder.
7. Let only the original finder close the issue when available.

An immediate safety/security/data-loss finding may stop a hazardous action before the comprehensive pass ends, but it still does not authorize piecemeal repair while the remaining ledger is open.

If one prerequisite defect makes later checks impossible or meaningless, the verifier may request one staged prerequisite repair. Keep the report in `comprehensive` mode and `IN_PROGRESS`; do not freeze the ledger or call the next pass closure review. After the prerequisite repair, attempt every remaining surface, add any distinct findings with distinct fingerprints, then freeze once. This staged exception must not become an open-ended repair loop.

## Closure

Close an issue only when its re-acceptance check passes against current artifacts. Re-run relevant regression checks. A changed file, an implementer's assurance, or a passing unrelated test is not closure evidence.

If a repair needs a plan or interface change, return to plan review before editing dependent scopes.

## Repair convergence

- The first verifier pass for an acceptance surface must report its complete known issue set.
- Do not start repair while that first report is `IN_PROGRESS`. Early piecemeal repair lets the verifier keep adding unrelated issues against a moving diff and creates false churn.
- A staged prerequisite exception does not permit fingerprint laundering. A different requirement/component/failure mode receives a new ID while the comprehensive ledger is still open.
- Re-verification is closure-only for existing IDs and fingerprints.
- Add a later blocking issue only when the repair introduced a regression; cite the causal diff and fresh reproduction evidence.
- Deduplicate equivalent symptoms with the same requirement, component, failure mode, and re-acceptance condition.
- If the open fingerprint set is unchanged for two rounds, stop blind edits and perform root-cause analysis.
- If issues close but unrelated new issues keep replacing them without net reduction, freeze the scope and return `NEEDS_USER_DECISION` or run one independent adjudication. Do not continue an unbounded worker-verifier loop.
