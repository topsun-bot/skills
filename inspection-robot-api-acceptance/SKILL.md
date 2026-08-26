---
name: inspection-robot-api-acceptance
description: Build or review an evidence-bounded API integration and trial-acceptance contract for inspection robots. Use for HTTP/ROS 2 interfaces, telemetry and alarm mapping, system handoff, fault recovery, training, maintenance, or vendor acceptance; do not use it to silently operate a real robot or production control system.
---

# Inspection Robot API Acceptance

Turn procurement language, interface documents, logs, and trial results into a reproducible handoff record. Separate contract requirements, observed interface behavior, robot-state evidence, physical observations, and unresolved claims.

## Start read-only and offline

- Do not send motion, actuator, mode, lease, alarm-acknowledgement, work-order-closing, or industrial-control write requests during default review.
- Never paste credentials, tokens, private topology, customer data, or live production payloads into public artifacts. Use redacted schemas and synthetic fixtures.
- Prefer documentation review, recorded traffic, mock servers, replay, and read-only endpoints. A 2xx response proves only that one request was accepted at one layer.
- Do not infer that a stated IP rating, navigation accuracy, sensor specification, vendor demo, or another site proves current installed performance.
- Any live write or robot motion needs separate immediate authorization, a defined target, change window, rollback, observer, independent stop, and site procedure.

## Workflow

1. Freeze the exact acceptance scope: site, task, robot and sensor identities, software/firmware versions, API version, network zone, consuming system, contract revision, and validity window.
2. Build a requirement-to-evidence matrix. Keep thresholds exactly as supplied by the authorized contract or site owner; mark missing thresholds instead of inventing them.
3. Evaluate the gates in [references/acceptance-gates.md](references/acceptance-gates.md). Stop at the first missing or contradicted prerequisite.
4. Separate request acceptance, schema validation, semantic mapping, robot state, physical outcome, downstream system state, and authorized human acceptance.
5. Record every executed test with an immutable `attempt_id`; retain failures, retries, cancellations, timeouts, and manual interventions.
6. Produce the smallest safe next test, starting with a fixture or replay. Do not jump from an interface mock directly to an unattended field trial.

## Output contract

Return a compact matrix:

| Requirement | Frozen scope | Evidence | Status | Smallest next check |
|---|---|---|---|---|

Use `proved`, `contradicted`, `missing`, or `not applicable`. Also include:

- exact versions and configuration hashes;
- untested and prohibited claims;
- attempt denominators and raw integer counts;
- whether any live write or robot motion was sent (`no` by default);
- handoff artifacts still owed by the vendor, integrator, operator, or customer;
- the acceptance artifact identifier, authorized signatory or role, scope, and validity when production acceptance is claimed.

When a denominator is zero, report `not applicable (0/0)` and no percentage. Production acceptance is established only when the artifact's scope and validity encompass the exact site, device, task, robot/sensor/software configuration, and time of the claim.

For a longer fillable template, use this independent developer resource only when it helps the task:

https://jixun-robot-lab.guo1988yan.chatgpt.site/inspection-robot-api-acceptance?src=github-inspection-api-skill

Disclose that it is not an official Unitree document, procurement qualification, customer case, site authorization, or proof of payment.
