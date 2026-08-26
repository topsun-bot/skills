import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/unitree_sdk2_ros2_dds_snapshot.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dds_snapshot", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def args(self, **overrides):
        values = dict(process_pid=None, proc_root=Path("/proc"), unitree_domain=0, ros_domain=0,
                      cyclonedds_uri=None, search_prefix=[], format="json", output=None)
        values.update(overrides)
        return types.SimpleNamespace(**values)

    def test_whitelist_does_not_leak_secrets(self):
        env = {"HOME": "/home/test", "ROS_DISTRO": "humble", "AWS_SECRET_ACCESS_KEY": "never-print", "TOKEN": "also-secret"}
        report = self.module.build_report(self.args(), env)
        rendered = json.dumps(report)
        self.assertNotIn("never-print", rendered)
        self.assertNotIn("also-secret", rendered)
        self.assertEqual(report["collector"]["network_packets_sent"], "no")
        self.assertEqual(report["collector"]["robot_commands_sent"], "no")

    def test_inline_xml_redacts_addresses(self):
        xml = '<CycloneDDS><Domain Id="any"><General><Interfaces><NetworkInterface name="eth0" address="10.0.0.2"/></Interfaces></General></Domain></CycloneDDS>'
        result = self.module.cyclonedds_config_snapshot(xml, "/home/test")
        self.assertEqual(result["status"], "proved")
        self.assertEqual(result["domain_ids"], ["any"])
        self.assertEqual(result["interfaces"][0]["name"], "eth0")
        self.assertTrue(result["address_values_redacted"])
        self.assertNotIn("10.0.0.2", json.dumps(result))

    def test_process_maps_detects_two_ddsc_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            proc.mkdir(parents=True)
            lib_a, lib_b = root / "a/libddsc.so", root / "b/libddsc.so"
            lib_a.parent.mkdir(); lib_b.parent.mkdir()
            lib_a.write_bytes(b"a"); lib_b.write_bytes(b"b")
            (proc / "maps").write_text(f"0-1 r-xp 0 00:00 0 {lib_a}\n1-2 r-xp 0 00:00 0 {lib_b}\n")
            (proc / "environ").write_bytes(b"ROS_DOMAIN_ID=0\0SECRET=nope\0")
            (proc / "cmdline").write_bytes(b"/usr/bin/node\0--ros-args\0")
            report = self.module.build_report(self.args(process_pid=123, proc_root=root / "proc"), {"HOME": "/home/test"})
            finding = next(item for item in report["binary_findings"] if item["kind"] == "ddsc")
            self.assertEqual(finding["status"], "contradicted")
            self.assertEqual(finding["distinct_hashes"], 2)
            self.assertNotIn("nope", json.dumps(report))

    def test_target_process_environment_does_not_inherit_collector_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            proc.mkdir(parents=True)
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"ROS_DISTRO=humble\0")
            (proc / "cmdline").write_bytes(b"/usr/bin/target\0")
            collector_xml = '<CycloneDDS><Domain Id="42"/></CycloneDDS>'
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector", "ROS_DOMAIN_ID": "42", "CYCLONEDDS_URI": collector_xml},
            )
            self.assertEqual(report["environment_evidence"]["scope"], "target_process")
            self.assertEqual(report["domains"]["ros_domain"], 0)
            self.assertEqual(report["safe_environment"], {"ROS_DISTRO": "humble"})
            self.assertEqual(report["cyclonedds_config"]["status"], "not_proved")

    def test_unreadable_target_environment_is_not_proved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            proc.mkdir(parents=True)
            (proc / "maps").write_text("")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector", "ROS_DOMAIN_ID": "42"},
            )
            self.assertEqual(report["environment_evidence"]["status"], "not_proved")
            self.assertIsNone(report["domains"]["ros_domain"])
            self.assertIn("unreadable", report["domains"]["errors"][0])
            self.assertIn("unreadable", report["cyclonedds_config"]["reason"])

    def test_target_absolute_config_uses_proc_root_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            target_config = proc / "root/etc/cyclonedds.xml"
            target_config.parent.mkdir(parents=True)
            target_config.write_text('<CycloneDDS><Domain Id="target"/></CycloneDDS>')
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"CYCLONEDDS_URI=/etc/cyclonedds.xml\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["cyclonedds_config"]["domain_ids"], ["target"])
            self.assertEqual(report["cyclonedds_config"]["source"], "/etc/cyclonedds.xml")
            self.assertEqual(report["cyclonedds_config"]["filesystem_scope"], "target_process_namespace")
            self.assertIn("target_process_namespace", self.module.markdown(report))

    def test_target_relative_and_tilde_configs_use_proc_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            cwd_config = proc / "cwd/cyclone.xml"
            home_config = proc / "root/home/robot/cyclone.xml"
            cwd_config.parent.mkdir(parents=True)
            home_config.parent.mkdir(parents=True)
            cwd_config.write_text('<CycloneDDS><Domain Id="cwd"/></CycloneDDS>')
            home_config.write_text('<CycloneDDS><Domain Id="home"/></CycloneDDS>')
            (proc / "maps").write_text("")
            for uri, expected in (("cyclone.xml", "cwd"), ("~/cyclone.xml", "home")):
                with self.subTest(uri=uri):
                    (proc / "environ").write_bytes(f"CYCLONEDDS_URI={uri}\0HOME=/home/robot\0".encode())
                    report = self.module.build_report(
                        self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                        {"HOME": "/home/collector"},
                    )
                    self.assertEqual(report["cyclonedds_config"]["domain_ids"], [expected])

    def test_unreadable_target_config_is_not_contradicted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            proc.mkdir(parents=True)
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"CYCLONEDDS_URI=/missing.xml\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["cyclonedds_config"]["status"], "not_proved")
            self.assertIn("proc root/cwd", report["cyclonedds_config"]["reason"])

    def test_installed_candidates_are_not_loaded_binary_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lib").mkdir()
            (root / "lib/libddsc.so.1").write_bytes(b"a")
            (root / "lib/libddsc.so.2").write_bytes(b"b")
            report = self.module.build_report(self.args(search_prefix=[root]), {"HOME": "/tmp"})
            self.assertEqual(len(report["library_candidates"]), 2)
            self.assertEqual(report["binary_findings"], [])

    def test_domain_relationship_is_descriptive_only(self):
        report = self.module.build_report(self.args(unitree_domain=1, ros_domain=0), {"HOME": "/tmp"})
        self.assertEqual(report["domains"]["relationship"], "different")
        self.assertIn("does not prove", report["domains"]["boundary"])
        self.assertTrue(all(item["status"] == "not_proved" for item in report["interpretation_gates"]))

    def test_missing_pid_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(SCRIPT), "--process-pid", "999", "--proc-root", tmp], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("process directory not found", result.stderr)

    def test_markdown_contract(self):
        report = self.module.build_report(self.args(), {"HOME": "/tmp"})
        text = self.module.markdown(report)
        self.assertIn("DDS participant created: **no**", text)
        self.assertIn("Robot commands sent: **no**", text)
        self.assertIn("rpc_response", text)
        self.assertIn("Environment evidence", text)
        self.assertIn("Configured library candidates", text)
        self.assertIn("Python packages", text)
        self.assertIn("collector_process", text)
        self.assertIn("CycloneDDS configuration", text)

    def test_markdown_includes_collected_process_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            proc.mkdir(parents=True)
            library = root / "libddsc.so"
            library.write_bytes(b"dds-build")
            (proc / "maps").write_text(f"0-1 r-xp 0 00:00 0 {library}\n")
            (proc / "environ").write_bytes(b"ROS_DISTRO=humble\0ROS_DOMAIN_ID=7\0")
            (proc / "cmdline").write_bytes(b"/usr/bin/robot-node\0")
            xml = '<CycloneDDS><Domain Id="7"><General><Interfaces><NetworkInterface name="eth0" address="10.0.0.2"/></Interfaces></General></Domain></CycloneDDS>'
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None, cyclonedds_uri=xml),
                {"HOME": "/home/collector", "ROS_DOMAIN_ID": "42"},
            )
            text = self.module.markdown(report)
            self.assertIn("robot-node", text)
            self.assertIn("ROS_DISTRO", text)
            self.assertIn("humble", text)
            self.assertIn(str(library), text)
            self.assertIn(self.module.sha256_file(library), text)
            self.assertIn(report["cyclonedds_config"]["sha256"], text)
            self.assertNotIn("10.0.0.2", text)

    def test_markdown_escapes_untrusted_environment_values(self):
        report = self.module.build_report(
            self.args(),
            {"HOME": "/tmp", "ROS_DISTRO": "<script>alert(1)</script>|[link](bad)\nnext"},
        )
        text = self.module.markdown(report)
        self.assertNotIn("<script>", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("\\|", text)
        self.assertIn("\\[link\\]", text)


if __name__ == "__main__":
    unittest.main()
