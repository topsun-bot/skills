# Evidence gates

Read this reference when deciding how far a G1, Go2, or Go2W diagnosis or test may safely progress.

## Gate 0: scope and identity

Required evidence:

- exact model and hardware configuration;
- firmware/software version as read from the scoped robot or its exported log;
- SDK/ROS/application commit or package version;
- tested host, interface, time, and evidence location.

User statements may populate a `reported` field but do not count as observed identity.

## Gate 1: local network configuration

Required evidence:

- intended physical interface exists and is up;
- its local address and route are known;
- RMW and CycloneDDS/FastDDS configuration point to the intended interface;
- any configuration change has a backup and rollback path.

Do not replace this gate with a broad subnet scan.

## Gate 2: discovery and fresh state

Required evidence:

- expected robot state endpoints/topics are discovered;
- messages advance over a bounded observation window;
- timestamps or sequence numbers are fresh and monotonic enough for the task;
- robot identity in the stream matches Gate 0 when such a field exists.

One received sample or successful ping is insufficient.

## Gate 3: mode and authority

Required evidence:

- current mode/service/FSM is read, not inferred from a button sequence;
- the command owner is identified;
- lease/authority status is positive or explicitly not applicable;
- competing command publishers are absent or bounded;
- requested changes are read back before being treated as changed.

Return code 0 proves only that a request reached one API layer.

## Gate 4: motion safety

All must be independently observed immediately before a motion step:

- user explicitly authorized the specific motion;
- authorized site and accurate robot/configuration;
- cleared and isolated motion envelope;
- trained observer and manual takeover;
- independent stop reachable and tested under the site's procedure;
- approved speed, posture, payload, tool, route, timeout, and retry bound;
- current logs and clocks ready.

This gate authorizes nothing by itself. The user/site authority makes the decision.

## Gate 5: physical outcome

Record separately:

1. request sent;
2. API response;
3. state readback;
4. body/arm physical response;
5. task completion;
6. stop request, zero command, measured zero band, stop distance, and stable posture.

Do not infer physical stop from an accepted zero command.

## Cross-disciplinary review

- **Physics:** mass, center of mass, inertia, friction, contact, payload, stopping distance, support polygon, and sensor geometry.
- **Mathematics:** frozen denominator, sample size, failure/timeout/intervention retention, missing data, and uncertainty.
- **Logic:** request acceptance, state change, physical response, and task completion are distinct propositions.
- **Biology/human factors:** people entering the envelope, attention, fatigue, startle, observer workload, and emergency takeover.
- **Psychology:** confirmation bias, demo selection bias, threshold changes after seeing results, and pressure to call one success production-ready.
