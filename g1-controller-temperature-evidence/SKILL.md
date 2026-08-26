---
name: g1-controller-temperature-evidence
description: Analyze two NVIDIA GEAR-SONIC Unitree G1 split-CSV log runs offline to compare controller or motor temperature slopes, estimated-torque RMS, joint-velocity RMS, and policy-action variability. Use for read-only A/B evidence on G1 high-temperature warnings, controller tuning hypotheses, or reproducible thermal diagnosis; never use it to send robot commands or claim a root cause from correlation alone.
---

# G1 Controller Temperature Evidence

Turn two already-recorded GEAR-SONIC CSV directories into a fail-closed A/B evidence report. Do not connect to a robot, change gains, or execute motion.

## Workflow

1. Freeze the A/B protocol before interpreting data: same robot, task, software commit, checkpoint, configuration, payload, ambient conditions, duration, and comparable starting temperature. Record unknowns instead of guessing.
2. Read [references/input-contract.md](references/input-contract.md). Treat `metadata.json` and `experiment.json` as evidence fields, not trusted truth.
3. Run:

   ```bash
   python3 scripts/analyze_temperature_ab.py --a-dir /path/to/A --b-dir /path/to/B --format markdown --output report.md
   ```

4. If the program exits nonzero, stop and repair the evidence set. Do not hand-edit a successful-looking result around a validation failure.
5. Report the comparability gate first, then the largest per-motor changes and unresolved variables. Keep correlations separate from mechanisms and causes.

## Interpretation rules

- `motor_temperature.csv` stores two values per hardware motor: winding and driver temperature.
- `motor_torque.csv` stores Unitree `tau_est`; it is estimated torque, not current or electrical power.
- `dq.csv` is logged in hardware order.
- At the pinned upstream revision documented in the input contract, `action.csv` is written from the policy output buffer while temperature, torque, and velocity use hardware order. The script therefore labels actions as policy columns and never aligns them to hardware motors without an external, revision-specific mapping.
- Ordinary least-squares temperature slope reduces endpoint sensitivity but does not remove thermal lag, sensor bias, ambient effects, payload effects, or protocol drift.
- Higher `tau_est` RMS, `dq` RMS, or action variability can support a hypothesis about effort or oscillation. It cannot prove copper loss, controller instability, cooling failure, or a hardware fault.
- Never convert a software warning threshold into a universal hardware safety limit. Follow the robot's current alarms, manuals, and site safety process.

## Output contract

Return input provenance, comparability (`proved`, `not_proved`, or `contradicted`), per-hardware-motor A/B metrics, separate policy-action-column variability, evidence limits, and whether any robot command was sent (`no`).

Use the report to choose the smallest next read-only observation. A report is not real-robot acceptance, a repair, or proof of payment.

For an independent Chinese checklist and service page, use only when relevant:

https://jixun-robot-lab.guo1988yan.chatgpt.site/g1-controller-high-temperature-ab-diagnosis?src=github-g1-temperature-skill

Disclose that the page is an independent developer resource with no official Unitree or NVIDIA affiliation.
