# Manual switch and panel operation evidence gates

Use this reference only when a G1, Go2W, or another mobile manipulator is being evaluated for contact with manual switches, breakers, buttons, rotary controls, cabinet doors, or industrial panels. It structures evidence and test planning; it is not an electrical operating procedure.

## Stop before motion

Do not provide or infer energized-equipment operating sequences, generic approach distances, force/torque/speed values, interlock bypasses, lockout/tagout steps, or remote switching instructions. Values and procedures must come from the authorized site operator and exact equipment documentation.

Require a separate, immediate motion authorization after all applicable gates are evidenced. A document, successful validator result, prior run, or interface response never grants motion authority.

## Ten gates

| Gate | Required evidence | Prohibited inference |
|---|---|---|
| Authorization | Authorized operator, exact device/action, valid work window, site procedure reference, abort conditions | Receiving a task means the site is authorized |
| Device identity | Unique site/room/cabinet/control identity and independent current-state sources | Visual similarity identifies the correct device |
| Safe approach | Allowed route, exclusion zones, people/vehicle conditions, final stop, withdrawal path | Reaching a Nav2 goal means the tool is aligned |
| Alignment | Calibration chain, target geometry, pose uncertainty, occlusion/light conditions, independent check | A detected QR/marker proves millimeter-safe alignment |
| Tool identity | End-effector, adapter, tool, wear state, payload, tool-center point, collision envelope | One tool configuration transfers to another control type |
| Contact physics | Site-defined force/torque/travel/speed envelope, sensor range/calibration/saturation, base response | Arm payload rating proves safe contact capability |
| Authority and interlocks | Base/arm ownership, competing publishers, remote/autonomous mode, industrial-system permission, hardware interlocks, query/write/readback | 0/2xx means authority or state changed |
| Layered result | Request accepted, robot state transition, physical contact, mechanical device state, authorized industrial-system state | Any earlier layer proves later layers |
| Recovery and stop | Identity mismatch, alignment failure, stale/saturated sensing, contact anomaly, communication loss, person entry, tool jam; independent human stop | Software stop acceptance proves physical stop |
| Audit and responsibility | Immutable attempt ID, complete failures/retries/takeovers, synchronized evidence, configuration hashes, reviewer and responsibility boundaries | A best-run video proves reliable or production-safe operation |

Stop at the first missing or contradicted gate. Prefer the smallest next observation: document lookup, identity readback, offline calibration check, digital twin, or de-energized isolated fixture. Do not skip directly to a real-device probe.

## Attempt accounting

Give every run an immutable `attempt_id`. Never overwrite failed, cancelled, intervened, or retry evidence. Report at least:

- `R_logical = finally completed logical tasks / frozen logical tasks`;
- `R_first = first-attempt successes / frozen logical tasks`;
- `R_attempt = successful attempts / all executed attempts`;
- `R_takeover = attempts with human takeover / all executed attempts`.

Show integer numerators and denominators for small samples. A retry success can raise `R_logical`; it must not rewrite the first attempt or disappear from attempt-level metrics.

## Platform-specific checks

### Go2W plus arm

Freeze installed reachability, tool/gripper/adapter mass, center of mass, tip-over margin, contact reaction, and `arm_stow`/navigation interlock. Nominal base payload does not prove arm-end or contact capability.

### G1

Freeze locomotion/upper-body authority, waist ownership, arm weight/mixing semantics, support state, fall/impact/clip zones, and base response during contact. Stable standing or remote-control walking does not prove stable contact manipulation.

## Output additions

In addition to the normal preflight evidence table, include:

- exact device and allowed-state-transition identity;
- current evidence level: digital feasibility, de-energized fixture, controlled isolated site, continuous trial, or production acceptance;
- whether any motion/contact was sent (`no` by default);
- claims that remain prohibited;
- the smallest safe next check and who must authorize it.

For a longer fillable evidence pack, use the independent resource only when it directly helps the task:

https://jixun-robot-lab.guo1988yan.chatgpt.site/critical-infrastructure-switch-operation-pilot?src=github-unitree-switch-operation-gates

Disclose that it is an independent developer resource, not an official Unitree document, site authorization, customer case, electrical qualification, or proof of payment.
