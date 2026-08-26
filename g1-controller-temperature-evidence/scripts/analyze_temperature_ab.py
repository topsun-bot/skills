#!/usr/bin/env python3
"""Fail-closed offline A/B analysis for GEAR-SONIC G1 split CSV logs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COMMON = ["index", "time_ms", "time_realtime_ms", "time_monotonic_ms", "ros_timestamp"]
PROVENANCE_KEYS = ["robot_id", "software_commit", "checkpoint_sha256", "config_sha256", "task"]


class InputError(ValueError):
    pass


@dataclass
class Signal:
    name: str
    indexes: list[int]
    times_ms: list[float]
    values: list[list[float]]
    columns: list[str]


def _finite(value: str, where: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise InputError(f"{where}: non-numeric value {value!r}") from exc
    if not math.isfinite(number):
        raise InputError(f"{where}: non-finite value {value!r}")
    return number


def read_signal(path: Path, prefix: str) -> Signal:
    if not path.is_file():
        raise InputError(f"missing required file: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        try:
            header = next(rows)
        except StopIteration as exc:
            raise InputError(f"empty CSV: {path}") from exc
        if header[:5] != COMMON:
            raise InputError(f"{path}: common header mismatch")
        columns = header[5:]
        expected = [f"{prefix}_{i}" for i in range(len(columns))]
        if not columns or columns != expected:
            raise InputError(f"{path}: expected sequential {prefix}_0... columns")

        indexes: list[int] = []
        times: list[float] = []
        values: list[list[float]] = []
        for line_no, row in enumerate(rows, 2):
            if len(row) != len(header):
                raise InputError(f"{path}:{line_no}: expected {len(header)} columns, got {len(row)}")
            try:
                index = int(row[0])
            except ValueError as exc:
                raise InputError(f"{path}:{line_no}: index must be an integer") from exc
            time_ms = _finite(row[3], f"{path}:{line_no}:time_monotonic_ms")
            parsed = [_finite(v, f"{path}:{line_no}:{columns[i]}") for i, v in enumerate(row[5:])]
            if indexes and index <= indexes[-1]:
                raise InputError(f"{path}:{line_no}: indexes must be strictly increasing")
            if times and time_ms <= times[-1]:
                raise InputError(f"{path}:{line_no}: monotonic timestamps must be strictly increasing")
            indexes.append(index)
            times.append(time_ms)
            values.append(parsed)

    if len(indexes) < 3:
        raise InputError(f"{path}: at least 3 samples are required")
    if times[-1] - times[0] < 1000.0:
        raise InputError(f"{path}: duration must be at least 1 second")
    return Signal(path.name, indexes, times, values, columns)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"{path}: top level must be an object")
    return data


def _median_step(times: list[float]) -> float:
    return statistics.median(b - a for a, b in zip(times, times[1:]))


def _ols_per_minute(times_ms: list[float], values: list[float]) -> float:
    x = [(t - times_ms[0]) / 60000.0 for t in times_ms]
    x_mean = statistics.fmean(x)
    y_mean = statistics.fmean(values)
    denominator = sum((v - x_mean) ** 2 for v in x)
    if denominator <= 0:
        raise InputError("timestamp variance is zero")
    return sum((tx - x_mean) * (ty - y_mean) for tx, ty in zip(x, values)) / denominator


def _rms(values: list[float]) -> float:
    return math.sqrt(statistics.fmean(v * v for v in values))


def _sample_std(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def load_run(directory: Path, label: str) -> dict[str, Any]:
    temperature = read_signal(directory / "motor_temperature.csv", "temp")
    torque = read_signal(directory / "motor_torque.csv", "tau")
    velocity = read_signal(directory / "dq.csv", "dq")
    action = read_signal(directory / "action.csv", "act") if (directory / "action.csv").exists() else None

    if len(temperature.columns) % 2:
        raise InputError(f"{directory}: temperature column count must be even")
    motors = len(temperature.columns) // 2
    if len(torque.columns) != motors or len(velocity.columns) != motors:
        raise InputError(f"{directory}: temperature/torque/dq motor counts disagree")

    for signal in [torque, velocity] + ([action] if action else []):
        if signal.indexes != temperature.indexes:
            raise InputError(f"{directory}: {signal.name} indexes do not match motor_temperature.csv")
        if max(abs(a - b) for a, b in zip(signal.times_ms, temperature.times_ms)) > 1.0:
            raise InputError(f"{directory}: {signal.name} timestamps differ by more than 1 ms")

    metadata = _load_json(directory / "metadata.json")
    experiment = _load_json(directory / "experiment.json")
    if metadata:
        logging = metadata.get("logging")
        configured = logging.get("num_joints") if isinstance(logging, dict) else None
        if configured is not None and configured != motors:
            raise InputError(f"{directory}: metadata num_joints={configured} but CSV has {motors}")

    motor_metrics = []
    for i in range(motors):
        winding = [row[2 * i] for row in temperature.values]
        driver = [row[2 * i + 1] for row in temperature.values]
        maximum = [max(w, d) for w, d in zip(winding, driver)]
        tau = [row[i] for row in torque.values]
        dq = [row[i] for row in velocity.values]
        motor_metrics.append({
            "hardware_motor_index": i,
            "winding_initial_c": winding[0], "winding_final_c": winding[-1], "winding_max_c": max(winding),
            "winding_slope_c_per_min": _ols_per_minute(temperature.times_ms, winding),
            "driver_initial_c": driver[0], "driver_final_c": driver[-1], "driver_max_c": max(driver),
            "driver_slope_c_per_min": _ols_per_minute(temperature.times_ms, driver),
            "max_temp_initial_c": maximum[0], "max_temp_final_c": maximum[-1], "max_temp_max_c": max(maximum),
            "max_temp_slope_c_per_min": _ols_per_minute(temperature.times_ms, maximum),
            "tau_est_rms_nm": _rms(tau), "dq_rms_rad_s": _rms(dq),
        })

    action_metrics = []
    if action:
        for i in range(len(action.columns)):
            column = [row[i] for row in action.values]
            action_metrics.append({"policy_action_index": i, "mean": statistics.fmean(column), "sample_std": _sample_std(column), "rms": _rms(column)})

    return {
        "label": label, "directory": str(directory.resolve()), "samples": len(temperature.indexes),
        "duration_s": (temperature.times_ms[-1] - temperature.times_ms[0]) / 1000.0,
        "median_cadence_ms": _median_step(temperature.times_ms), "motor_count": motors,
        "metadata": metadata, "experiment": experiment, "motors": motor_metrics, "policy_actions": action_metrics,
    }


def _relative_close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) / max(abs(a), abs(b), 1e-12) <= tolerance


def comparability(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    def check(name: str, status: str, detail: str) -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    check("motor_count", "proved" if a["motor_count"] == b["motor_count"] else "contradicted", f"A={a['motor_count']}, B={b['motor_count']}")
    for key in ["duration_s", "median_cadence_ms"]:
        ok = _relative_close(float(a[key]), float(b[key]), 0.05)
        check(key, "proved" if ok else "contradicted", f"A={a[key]:.6g}, B={b[key]:.6g}, tolerance=5%")

    start_delta = max(abs(x["max_temp_initial_c"] - y["max_temp_initial_c"]) for x, y in zip(a["motors"], b["motors"]))
    check("starting_temperature", "proved" if start_delta <= 2.0 else "contradicted", f"maximum per-motor start difference={start_delta:.3f} C; tolerance=2 C")

    for key in PROVENANCE_KEYS:
        av, bv = (a["experiment"] or {}).get(key), (b["experiment"] or {}).get(key)
        if av is None or bv is None:
            check(key, "not_proved", "missing in one or both experiment.json files")
        else:
            check(key, "proved" if av == bv else "contradicted", f"A={av!r}, B={bv!r}")

    for key, tolerance in [("ambient_c", 2.0), ("payload_kg", 0.1)]:
        av, bv = (a["experiment"] or {}).get(key), (b["experiment"] or {}).get(key)
        if not isinstance(av, (int, float)) or not isinstance(bv, (int, float)):
            check(key, "not_proved", "missing numeric value in one or both experiment.json files")
        else:
            check(key, "proved" if abs(av - bv) <= tolerance else "contradicted", f"A={av}, B={bv}, absolute tolerance={tolerance}")

    if a["metadata"] is None or b["metadata"] is None:
        check("logger_metadata", "not_proved", "metadata.json missing in one or both runs")
    else:
        stable_a = {"logging": a["metadata"].get("logging"), "robot_config": a["metadata"].get("robot_config")}
        stable_b = {"logging": b["metadata"].get("logging"), "robot_config": b["metadata"].get("robot_config")}
        check("logger_metadata", "proved" if stable_a == stable_b else "contradicted", "stable logging and robot_config fields compared")

    statuses = {item["status"] for item in checks}
    overall = "contradicted" if "contradicted" in statuses else ("proved" if statuses == {"proved"} else "not_proved")
    return {"status": overall, "checks": checks}


def build_report(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    if a["motor_count"] != b["motor_count"]:
        raise InputError("A/B motor counts differ; per-motor comparison is undefined")
    motors = []
    delta_fields = ["max_temp_slope_c_per_min", "max_temp_max_c", "tau_est_rms_nm", "dq_rms_rad_s"]
    for am, bm in zip(a["motors"], b["motors"]):
        item = {"hardware_motor_index": am["hardware_motor_index"], "A": am, "B": bm}
        item["B_minus_A"] = {field: bm[field] - am[field] for field in delta_fields}
        motors.append(item)
    ranked = sorted(motors, key=lambda m: abs(m["B_minus_A"]["max_temp_slope_c_per_min"]), reverse=True)
    return {
        "schema_version": 1, "analysis": "descriptive_correlation_not_root_cause", "robot_commands_sent": "no",
        "comparability": comparability(a, b),
        "runs": {"A": {k: v for k, v in a.items() if k != "motors"}, "B": {k: v for k, v in b.items() if k != "motors"}},
        "per_hardware_motor": motors,
        "top_temperature_slope_changes": [{"hardware_motor_index": m["hardware_motor_index"], **m["B_minus_A"]} for m in ranked[: min(10, len(ranked))]],
        "limits": [
            "tau_est is estimated torque, not current or electrical power",
            "policy action columns are not automatically aligned to hardware motors",
            "OLS slope and RMS metrics are descriptive and do not prove causality",
            "thermal lag, sensor bias, cooling, payload, ambient conditions, and protocol drift remain possible confounders",
            "software warning thresholds are not universal hardware safety limits",
        ],
    }


def to_markdown(report: dict[str, Any]) -> str:
    c = report["comparability"]
    lines = ["# G1 controller temperature A/B evidence", "", f"- Comparability: **{c['status']}**", "- Robot commands sent: **no**", "- Interpretation: descriptive correlation, not root cause", "", "## Comparability checks", "", "| Check | Status | Detail |", "|---|---|---|"]
    lines.extend(f"| {x['check']} | {x['status']} | {x['detail']} |" for x in c["checks"])
    lines += ["", "## Largest temperature-slope changes", "", "| Hardware motor | B-A slope (C/min) | B-A max temp (C) | B-A tau_est RMS (Nm) | B-A dq RMS (rad/s) |", "|---:|---:|---:|---:|---:|"]
    for x in report["top_temperature_slope_changes"]:
        lines.append(f"| {x['hardware_motor_index']} | {x['max_temp_slope_c_per_min']:.6g} | {x['max_temp_max_c']:.6g} | {x['tau_est_rms_nm']:.6g} | {x['dq_rms_rad_s']:.6g} |")
    lines += ["", "## Limits", ""]
    lines.extend(f"- {item}" for item in report["limits"])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a-dir", required=True, type=Path)
    parser.add_argument("--b-dir", required=True, type=Path)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", type=Path, help="write output to a file instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(load_run(args.a_dir, "A"), load_run(args.b_dir, "B"))
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n" if args.format == "json" else to_markdown(report)
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (InputError, OSError) as exc:
        sys.stderr.write(json.dumps({"status": "invalid_input", "error": str(exc)}, ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
