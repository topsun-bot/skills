# Input contract

This skill targets the split CSV logger in NVIDIA `GR00T-WholeBodyControl` at commit `a0732b642c0333077e127a2f56ab0014c196bca4`.

Primary implementation evidence:

- [`file_sink.cpp`](https://github.com/NVlabs/GR00T-WholeBodyControl/blob/a0732b642c0333077e127a2f56ab0014c196bca4/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/file_sink.cpp)
- [`state_logger.cpp`](https://github.com/NVlabs/GR00T-WholeBodyControl/blob/a0732b642c0333077e127a2f56ab0014c196bca4/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/state_logger.cpp)
- [`g1_deploy_onnx_ref.cpp`](https://github.com/NVlabs/GR00T-WholeBodyControl/blob/a0732b642c0333077e127a2f56ab0014c196bca4/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/src/g1_deploy_onnx_ref.cpp)

## Required files per run

- `motor_temperature.csv`: common columns plus `temp_0 ... temp_(2N-1)`; each pair is winding then driver temperature for one hardware motor.
- `motor_torque.csv`: common columns plus `tau_0 ... tau_(N-1)` in hardware order.
- `dq.csv`: common columns plus `dq_0 ... dq_(N-1)` in hardware order.

Common columns must be exactly:

`index,time_ms,time_realtime_ms,time_monotonic_ms,ros_timestamp`

The required files must have identical indexes, at least three rows, finite values, strictly increasing indexes and monotonic timestamps, and at least one second of duration. The analyzer accepts only sequential signal headers.

## Optional files

- `action.csv`: `act_0 ... act_(M-1)`. These are reported as policy columns. Do not align them to hardware motor columns by index.
- `metadata.json`: emitted by the upstream logger. The analyzer checks joint count and compares stable logging/robot configuration fields when both runs provide it.
- `experiment.json`: operator-supplied provenance. Recommended fields:

```json
{
  "robot_id": "asset-tag-or-pseudonym",
  "software_commit": "full-commit-sha",
  "checkpoint_sha256": "64-hex",
  "config_sha256": "64-hex",
  "task": "fixed-protocol-name",
  "ambient_c": 24.0,
  "payload_kg": 0.0
}
```

Do not put secrets, customer names, personal data, access tokens, or network credentials in these files.

## Comparability gate

The analyzer marks the overall gate `proved` only when every implemented check passes, `not_proved` when provenance is missing without a contradiction, and `contradicted` when at least one measured or declared condition conflicts. Passing supports comparison of these logs; it does not prove causality, safety, repair, or production readiness.
