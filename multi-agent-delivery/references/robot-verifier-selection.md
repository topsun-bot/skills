# Robot Verifier Selection

Select verifiers from the approved plan's risks. Use the smallest set that covers every acceptance surface.

| Work type | Required starting set | Add when relevant |
|---|---|---|
| Algorithms or state machines | logic, runtime | integration for external data contracts; safety for motion consequences |
| ROS/DDS nodes | logic, integration, runtime | safety for command or actuator paths |
| Navigation or motion control | logic, runtime, safety | integration for frames, localization, mapping, or middleware |
| Perception and sensor fusion | logic, integration, runtime | safety when outputs gate motion |
| Robot model/VLM service | logic, integration, runtime | safety when model output can command the robot |
| Deployment or remote operation | integration, runtime, safety | logic for new orchestration code |
| Robot web/backend product | logic, integration, runtime | browser-specific verifier if UI behavior is an acceptance surface |

With limited concurrency, run the highest-risk three first and schedule the remaining verifier next. Never omit safety merely to fit a concurrency limit.

## Evidence targets

- Pure library behavior may stop at E1 only when the approved contract requires no integration claim.
- ROS integration normally requires at least E2.
- Real services, models, databases, or browsers require E3 when named by the objective.
- Real robot behavior requires E4. Simulation cannot close E4 requirements.
