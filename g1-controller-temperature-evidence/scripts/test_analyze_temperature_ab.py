#!/usr/bin/env python3

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("analyze_temperature_ab.py")
COMMON = ["index", "time_ms", "time_realtime_ms", "time_monotonic_ms", "ros_timestamp"]


def write_signal(path: Path, prefix: str, rows: list[tuple[int, float, list[float]]]) -> None:
    width = len(rows[0][2])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(COMMON + [f"{prefix}_{i}" for i in range(width)])
        for index, time_ms, values in rows:
            writer.writerow([index, time_ms, 1_000_000 + time_ms, 2_000_000 + time_ms, time_ms / 1000] + values)


def make_run(root: Path, name: str, slope_c_per_s: float = 1.0) -> Path:
    run = root / name
    run.mkdir()
    times = [0.0, 1000.0, 2000.0]
    write_signal(run / "motor_temperature.csv", "temp", [
        (i, t, [30 + slope_c_per_s * t / 1000, 31 + slope_c_per_s * t / 1000, 32, 33]) for i, t in enumerate(times)
    ])
    write_signal(run / "motor_torque.csv", "tau", [(i, t, [1, 2]) for i, t in enumerate(times)])
    write_signal(run / "dq.csv", "dq", [(i, t, [0.1, 0.2]) for i, t in enumerate(times)])
    write_signal(run / "action.csv", "act", [(i, t, [0.0, float(i)]) for i, t in enumerate(times)])
    (run / "metadata.json").write_text(json.dumps({"logging": {"num_joints": 2, "num_actions": 2, "dt": 1.0}, "robot_config": {"model": "test"}}))
    (run / "experiment.json").write_text(json.dumps({
        "robot_id": "fixture", "software_commit": "abc", "checkpoint_sha256": "0" * 64,
        "config_sha256": "1" * 64, "task": "stand", "ambient_c": 24.0, "payload_kg": 0.0,
    }))
    return run


class AnalyzerTests(unittest.TestCase):
    def run_tool(self, a: Path, b: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "--a-dir", str(a), "--b-dir", str(b), *extra], text=True, capture_output=True, check=False)

    def test_valid_report_and_expected_slope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = make_run(root, "A", 1.0)
            b = make_run(root, "B", 2.0)
            result = self.run_tool(a, b)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["comparability"]["status"], "proved")
            self.assertEqual(report["robot_commands_sent"], "no")
            delta = report["per_hardware_motor"][0]["B_minus_A"]["max_temp_slope_c_per_min"]
            self.assertAlmostEqual(delta, 60.0)
            self.assertEqual(report["runs"]["A"]["policy_actions"][1]["sample_std"], 1.0)

    def test_markdown_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_tool(make_run(root, "A"), make_run(root, "B"), "--format", "markdown")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Comparability: **proved**", result.stdout)
            self.assertIn("Robot commands sent: **no**", result.stdout)

    def test_non_monotonic_time_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = make_run(root, "A"), make_run(root, "B")
            write_signal(b / "dq.csv", "dq", [(0, 0, [0, 0]), (1, 1000, [0, 0]), (2, 900, [0, 0])])
            result = self.run_tool(a, b)
            self.assertEqual(result.returncode, 2)
            self.assertIn("strictly increasing", result.stderr)

    def test_non_finite_value_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = make_run(root, "A"), make_run(root, "B")
            write_signal(b / "motor_torque.csv", "tau", [(0, 0, [1, 2]), (1, 1000, [float("nan"), 2]), (2, 2000, [1, 2])])
            result = self.run_tool(a, b)
            self.assertEqual(result.returncode, 2)
            self.assertIn("non-finite", result.stderr)

    def test_mismatched_indexes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = make_run(root, "A"), make_run(root, "B")
            write_signal(b / "dq.csv", "dq", [(0, 0, [0, 0]), (1, 1000, [0, 0]), (3, 2000, [0, 0])])
            result = self.run_tool(a, b)
            self.assertEqual(result.returncode, 2)
            self.assertIn("indexes do not match", result.stderr)

    def test_missing_provenance_is_not_proved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = make_run(root, "A"), make_run(root, "B")
            (b / "experiment.json").unlink()
            result = self.run_tool(a, b)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["comparability"]["status"], "not_proved")


if __name__ == "__main__":
    unittest.main()
