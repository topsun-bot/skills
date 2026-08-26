# Evidence Levels and Acceptance

## Evidence levels

- **E0 — inference:** prose, source inspection, or predicted behavior only.
- **E1 — isolated checks:** lint, type checks, unit tests, or deterministic local checks with controlled substitutes.
- **E2 — integrated substitute:** integration tests, simulation, recorded data, or a non-production dependency chain.
- **E3 — real software chain:** real service, real model, real database, real browser, or real external dependency as required.
- **E4 — real hardware chain:** real robot, sensors, actuators, network, environment, and recovery behavior.

Higher levels do not automatically include all lower-level checks. Record the actual command, environment, time, artifact, and result.

## Rules

1. Set the required evidence level in the approved plan before implementation.
2. Never use E0/E1 to claim E2, E3, or E4 behavior.
3. Label mocks, skips, xfails, simulations, replays, and stubs explicitly.
4. Treat missing dependencies and unavailable hardware as blockers or unverified boundaries, not passes.
5. For recovery claims, induce or reproduce the relevant failure and prove restoration.
6. For safety claims, prove entry to a safe state and safe recovery; absence of observed motion is not sufficient by itself.
7. For real robot checks, record authorization, robot identity, software version, test envelope, stop method, and observer evidence.
8. A snapshot refresh is not passing evidence. Review the diff, refresh one intentional change set once, then run a read-only replay. Repeated snapshot refreshes cannot close a regression.

## Final evidence matrix

The final acceptance report must include:

| Requirement | Required level | Actual level | Command or steps | Evidence path | Verdict |
|---|---:|---:|---|---|---|

Any required level above the actual level keeps the requirement unverified and prevents completion unless the user explicitly changes the acceptance contract.
