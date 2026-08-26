# Workflow and State Machine

## Contents

1. Roles and ownership
2. Phases and gates
3. Agent continuity
4. Concurrency
5. Status and recovery

## Roles and ownership

- **Orchestrator:** Own objective, phase, routing, state, authorization, and final communication. Do not implement or independently waive a failed gate.
- **Discovery agent:** Gather current facts and unknowns without editing project artifacts outside its report.
- **Planner:** Own the plan artifact. Do not implement application code.
- **Plan reviewer:** Independently approve or reject the plan. Do not edit the plan.
- **Implementer:** Own one bounded write scope and its repairs.
- **Verifier:** Inspect and execute checks independently. Write only evidence and reports.
- **Final acceptance agent:** Reconcile the whole objective against current artifacts and evidence.

## Phases and gates

Use these phases in order:

1. `discovery`
2. `planning`
3. `plan_review`
4. `implementation`
5. `verification`
6. `final_acceptance`
7. `complete`

Allowed terminal statuses are `complete`, `blocked`, `needs_user_decision`, and `failed`.

### Plan Gate

Open implementation only when all are true:

- A current plan version exists.
- A different agent reviewed it.
- Review verdict is `PASS`.
- Blocking finding count is zero.
- Every work item has executable acceptance checks and an evidence target.
- Safety, rollback, and authorization boundaries are explicit where applicable.

### Implementation Gate

Open verification for a work item only when its owner reports the intended artifacts and self-check outputs. Self-checks do not equal independent acceptance.

Allow one recorded mechanical-fallout scope amendment when a compiler, generator, or invariant exposes an omitted test/reference/generated/aggregate file and the change cannot alter application behavior. All other scope expansion returns to Plan Gate.

### Verification Gate

Mark a work item complete only after all selected independent verifiers pass and every blocking issue is closed by its original verifier.

### Completion Gate

Mark the run complete only after final acceptance independently reconciles every requirement and the deterministic state validator passes with `--require-complete`.

## Agent continuity

Store the stable target returned when each agent is created. Use a follow-up task to continue the same planner, implementer, or verifier thread.

If the target cannot be resumed:

1. Record the loss of continuity.
2. Start a replacement only when work can continue safely.
3. Require the replacement to read the current authoritative plan, owned artifacts, prior reports, and unresolved issues.
4. Do not describe rehydration as preserved conversational context.

## Concurrency

- Respect the current session's agent limit.
- Run independent, read-heavy discovery or verification work in parallel.
- Never let two agents edit overlapping files concurrently.
- Keep dependent work sequential.
- Give each verifier a distinct report path.
- Wait for every requested verifier before consolidating the gate result.

## Status and recovery

Use bounded rounds, defaulting to three plan-review rounds and three repair rounds. Also bound agent attempts per phase: one original agent and at most one replacement by default. A resume or replacement that produces no required artifact counts as an attempt; replacements do not reset budgets.

Require artifact-first work. Discovery, planning, review, implementation, and verification agents must create or update their required status artifact before broad exploration, then refine it in place. Commentary, tool activity, or an active thread without a changed artifact hash is not progress.

Freeze review scope after the first comprehensive report. Subsequent rounds close stable fingerprints. Do not permit a reviewer to continually discover unrelated blockers, turn suggestions into blockers, or expand the user's acceptance contract. See `convergence.md`.

Repeated identical failure, an unchanged open-fingerprint set, or blocker churn without net reduction is a signal to stop editing and inspect root cause, assumptions, environment, reviewer scope, and plan validity.

Use `BLOCKED` for an external condition that prevents progress, `NEEDS_USER_DECISION` for an unresolved choice or authority boundary, and `FAILED` when attempts are exhausted without a viable path. Never relabel these states as success.
