# Inspection robot integration and acceptance gates

Use these gates for inspection-robot system integration, including HTTP APIs, ROS 2 bridges, telemetry, alarms, maps, media, work orders, charging, and fleet dashboards. They define evidence and test structure, not site-specific operating instructions.

## Ten gates

| Gate | Required evidence | Prohibited inference |
|---|---|---|
| Scope identity | Site, route/task, robot, sensors, charger, consuming system, contract and version identities | A similar deployment transfers without revalidation |
| Network and security | Zones, allowed flows, authentication, authorization, certificate lifecycle, remote-access policy, logging and secret handling | Network reachability grants business or motion authority |
| API and schema | Versioned endpoint/topic inventory, direction, units, enums, nullability, limits, pagination, error contract and sample fixtures | One successful payload proves the whole contract |
| Time and freshness | Clock source, timestamp meaning, time zone, maximum age, ordering and duplicate policy | Arrival time equals measurement time |
| Delivery semantics | Idempotency key, retry/backoff, timeout, deduplication, rate limit and replay behavior | Retrying a write is harmless by default |
| Layered result | Request acceptance, schema validation, semantic mapping, robot state, physical result, downstream system state and human acceptance | HTTP 2xx or DDS publish proves physical completion |
| Measurement truth | Sensor identity, calibration, range, uncertainty, ground-truth protocol and label responsibility | Datasheet accuracy equals installed accuracy |
| Fault and recovery | Offline queue, stale data, packet loss, restart, partial dependency, charger failure, manual takeover, rollback and safe degradation | A happy-path demo proves recoverability |
| Audit and privacy | Immutable attempt ID, synchronized logs, configuration hashes, redaction, retention, access and reviewer responsibility | A screenshot or edited video is a complete audit record |
| Operations and handoff | Drawings, interface docs, source/build artifacts when contracted, training, spares, maintenance SLA, upgrade/rollback and signed acceptance | Delivery of hardware alone completes the system |

Stop at the first missing or contradicted gate. Prefer a redacted schema review, mock server, recorded replay, read-only production observation, or isolated staging test as the next check.

## Result layers

Report these separately when applicable:

1. `L1 transport`: request or message reached the endpoint;
2. `L2 protocol`: authentication and protocol validation succeeded;
3. `L3 schema`: the payload matched the frozen schema;
4. `L4 semantic`: identity, unit, state and timestamp mapped correctly;
5. `L5 robot state`: the robot state changed as independently observed;
6. `L6 physical outcome`: the physical task outcome was independently observed;
7. `L7 business system`: the authorized downstream system recorded the correct state;
8. `L8 acceptance`: an authorized acceptance artifact covers this exact scope and time.

An earlier layer never proves a later one.

## Metrics without denominator tricks

Freeze the eligible population before testing and show integer numerators and denominators:

- message completeness = eligible messages received / eligible messages expected;
- fresh-data ratio = messages within the approved freshness window / eligible messages received;
- first-attempt completion = first-attempt completed tasks / frozen logical tasks;
- attempt completion = completed attempts / all executed attempts;
- takeover ratio = attempts with manual intervention / all executed attempts;
- alarm precision and recall from an authorized ground-truth set, when labels exist;
- latency distribution with sample count and clock method, not a single best value.

If an eligible denominator is zero, report `not applicable (0/0)` and no percentage. A retry completion must not overwrite the failed first attempt. Do not calculate recognition accuracy without an authorized ground-truth definition and labelled denominator.

## Minimum handoff record

- frozen scope and exclusions;
- requirements-to-evidence matrix;
- versioned endpoint/topic and field dictionary;
- identity, unit, timestamp and state mapping table;
- synthetic fixtures and expected results;
- immutable attempts with complete failures and retries;
- fault, rollback and recovery evidence;
- cybersecurity and privacy responsibility boundaries;
- operator/maintainer training record;
- open defects, workarounds and upgrade constraints;
- authorized acceptance artifact or `production acceptance not established`.

No document generated from this reference authorizes robot motion, industrial-control writes, alarm closure, or production deployment.
