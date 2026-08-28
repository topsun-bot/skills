---
name: multi-agent-delivery
description: Orchestrate explicitly requested multi-agent delivery through evidence discovery, independently reviewed planning, scoped implementation, specialized verification, same-agent repair, and final acceptance. Use only when the user explicitly invokes `$multi-agent-delivery` in the current request or explicitly attaches/selects this Skill in the UI. Do not invoke it implicitly from task complexity, robotics work, requests for parallel agents, long-running work, plan/review/test language, or any other inferred fit.
---

# Multi-Agent Delivery

Deliver complex work through explicit ownership and evidence gates. Keep the main agent focused on requirements, decisions, status, and acceptance while bounded agents perform discovery, planning, implementation, and verification.

## Invocation gate

Before loading or executing this protocol, confirm that the current user request explicitly contains `$multi-agent-delivery` or includes an explicit UI attachment/selection of this Skill. Otherwise do not initialize a run, create `.agent-delivery` artifacts, or spawn agents under this protocol. A matching domain, an existing unrelated delivery directory, an earlier invocation in the conversation, or wording about robots, complexity, planning, review, parallelism, autonomy, or testing is not consent to invoke this Skill.

## Non-negotiable invariants

1. Do not start implementation before an independent plan reviewer returns `PASS` with zero blocking findings.
2. Send plan findings back to the same planner and implementation findings back to the same implementer whenever that agent remains available.
3. Send a repaired defect back to the verifier that originally found it. Require regression checks when the fix can affect adjacent behavior.
4. Give exactly one agent write ownership for an application file or overlapping scope at a time. Parallelize independent reads, tests, and distinct report writes.
5. Keep verifiers independent. They may run tests and write reports, but must not edit application source or silently fix defects.
6. Never convert a failed gate into a low-quality success. End as `PASS`, `BLOCKED`, `NEEDS_USER_DECISION`, or `FAILED`.
7. Label evidence honestly. Static review, unit tests, simulation, real services, real models, browsers, and real robots are different evidence levels.
8. Obtain explicit authorization immediately before hazardous hardware motion, production changes, credential transmission, or another consequential action not already authorized.

## Load the protocol

Before spawning any agent, read these files completely:

- [workflow.md](references/workflow.md) for phases, state transitions, continuity, and concurrency.
- [plan-contract.md](references/plan-contract.md) for the plan and review gate.
- [issue-contract.md](references/issue-contract.md) for defect routing and closure.
- [evidence-gates.md](references/evidence-gates.md) for proof levels and completion rules.
- [convergence.md](references/convergence.md) for artifact deadlines, stable findings, attempt budgets, and loop termination.

Read every role file that will govern an agent before spawning that agent. Do not delegate interpretation of a role contract you have not read yourself.

## Initialize a run

Inspect the current workspace and applicable instructions first. Reuse an existing `.agent-delivery/run.json` only when it describes the same objective and is not terminal. Otherwise run:

```bash
python3 <SKILL_ROOT>/scripts/init_run.py \
  --root <PROJECT_ROOT> \
  --objective "<USER_OBJECTIVE>" \
  --requirements <REQUIREMENTS_PATH> \
  --domain <DOMAIN>
```

Use `general` when no domain is known. Never overwrite an existing run implicitly.

New runs use state schema v2 with separate review, amendment, ordinary-repair, and adjudicated-repair counters. Keep an active legacy schema v1 run intact rather than partially renaming its fields; the validator remains backward compatible.

## Execute the workflow

### 1. Discover evidence

Read [discovery-agent.md](references/discovery-agent.md), then delegate a read-only discovery task. Require facts, sources, unknowns, constraints, acceptance surfaces, and authorization boundaries in `.agent-delivery/discovery.md`.

Do not let recommendations masquerade as facts. If an unstable external fact controls the plan, verify it from an authoritative current source.

### 2. Draft and approve the plan

Read [planner.md](references/planner.md) and delegate the first plan draft to one planner. The planner must use the discovery artifact and write `.agent-delivery/plan.md` according to the plan contract.

Read [plan-reviewer.md](references/plan-reviewer.md) and delegate an independent review to a different agent. Store the report in `.agent-delivery/plan-review.md`.

If review fails:

1. Route the report to the same planner with a follow-up task.
2. Require a finding-disposition table and a new plan version.
3. Route the revision to the same plan reviewer.
4. Repeat until `PASS` or the bounded plan round limit is reached.

The first review must be comprehensive and freeze stable finding fingerprints. Later reviews are closure-only: re-evaluate existing fingerprints and add a new blocking finding only when the revision introduced it and the report proves that causal diff. Do not raise the acceptance bar, rename an old finding into a new one, or block on suggestions.

Do not create implementation tasks while the plan gate is closed. Count original agents, resumes that fail to land, and replacements against the phase attempt budget. At either the round or attempt limit, return `NEEDS_USER_DECISION` with unresolved fingerprints instead of spawning another agent.

After implementation starts, count targeted plan amendments separately from the initial plan-review rounds. An amendment does not reset either counter or reopen the comprehensive plan review.

### 3. Implement by ownership unit

Read [implementer.md](references/implementer.md). Assign each plan work item to one implementation owner. Keep dependent work sequential; parallelize only scopes with disjoint write ownership and stable interfaces.

Record the agent target, owned scope, files, and acceptance checks in run state or the main log. Require the implementer to run proportionate self-checks, but do not treat self-checks as independent acceptance.

### 4. Select robot verification roles

For robot-related work, read [robot-verifier-selection.md](references/robot-verifier-selection.md) and select the smallest set that covers the plan's risks:

- [verifier-logic.md](references/verifier-logic.md): algorithms, state machines, concurrency, boundaries.
- [verifier-integration.md](references/verifier-integration.md): ROS/DDS/API contracts, frames, units, timing, configuration.
- [verifier-runtime.md](references/verifier-runtime.md): build, tests, service startup, simulation, performance, recovery, real dependency evidence.
- [verifier-safety.md](references/verifier-safety.md): command ownership, limits, watchdogs, safe stop, fault recovery, hardware boundaries.

For non-robot work, derive verifiers from the plan's acceptance surfaces using the same independence and evidence rules. Do not invent generic cosmetic reviewers when they do not match the product.

### 5. Repair and reverify

For every failed verifier report:

1. Wait until the verifier has attempted every required acceptance surface, marks its first comprehensive report `COMPLETE`, and freezes the full finding ledger. A report containing `pending`, `deferred`, or `not counted` required surfaces is not complete.
2. Normalize every frozen finding using the issue contract.
3. Send the complete report path and all issue IDs as one batch to the same implementation owner.
4. Require the smallest defensible repairs within the owned scope.
5. Send the repair batch back to the original verifier.
6. Re-run the failed checks and relevant regression gates in closure-only mode.

If the same open fingerprint set repeats or the ordinary repair-round limit is reached, stop ordinary edits. Read [adjudicator.md](references/adjudicator.md) and delegate one independent root-cause adjudication. Do not ask the user merely because a counter reached its limit.

The adjudicator may authorize exactly one automatic root-cause repair for the frozen fingerprint set only when it provides a failing regression and decisive root cause, keeps the original owner, verifier, file scope, and acceptance contract, and requires no new consequential authority. Record `AUTO_ROOT_CAUSE_REPAIR` in `.agent-delivery/adjudication.md` and `run.json` before editing. Route that repair to the same implementer and its closure check to the same verifier.

If the automatic root-cause repair fails, or adjudication finds a real product choice, scope expansion, disputed acceptance contract, hazardous action, credential/privacy boundary, production change, or unavailable external dependency, return `NEEDS_USER_DECISION`, `BLOCKED`, or `FAILED` as appropriate. Never force pass or create a second protocol-funded exception for the same fingerprint set.

The first verifier pass must report the complete issue set and a re-acceptance matrix for its assigned surface. Include positive, delay/timeout, concurrency, invalid-input, and failure-injection cases that are relevant to the frozen invariant. Re-verification is closure-only. A later counterexample may refine the same invariant but may not raise the acceptance bar; label it explicitly. A new blocking issue is allowed only when the repair introduced a regression and the verifier cites the causal diff and reproduction evidence.

### 6. Audit final acceptance

Read [final-acceptance.md](references/final-acceptance.md) and delegate an independent system-level audit after all module verifiers pass. The auditor must re-read the current plan, reports, artifacts, and runtime evidence rather than trusting status fields.

Before claiming completion, run:

```bash
python3 <SKILL_ROOT>/scripts/validate_run.py --root <PROJECT_ROOT> --require-complete
```

Completion requires plan approval, all required work items complete, zero open blocking issues, required evidence levels met, and final acceptance `PASS`.

## Communicate with the user

Report phase transitions, material blockers, authorization requests, and final evidence. Avoid narrating every agent message. Distinguish verified facts, recommendations, inferences, and unverified boundaries.

Treat `$multi-agent-delivery` or an explicit UI Skill attachment in the current request as the only invocation signal. Keep implicit invocation disabled.
