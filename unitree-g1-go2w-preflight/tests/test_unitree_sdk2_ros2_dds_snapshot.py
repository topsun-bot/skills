import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


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
            lib_a, lib_b = proc / "root/a/libddsc.so", proc / "root/b/libddsc.so"
            lib_a.parent.mkdir(parents=True); lib_b.parent.mkdir(parents=True)
            lib_a.write_bytes(b"a"); lib_b.write_bytes(b"b")
            (proc / "maps").write_text("0-1 r-xp 0 00:00 0 /a/libddsc.so\n1-2 r-xp 0 00:00 0 /b/libddsc.so\n")
            (proc / "environ").write_bytes(b"ROS_DOMAIN_ID=0\0SECRET=nope\0")
            (proc / "cmdline").write_bytes(b"/usr/bin/node\0--ros-args\0")
            report = self.module.build_report(self.args(process_pid=123, proc_root=root / "proc"), {"HOME": "/home/test"})
            finding = next(item for item in report["binary_findings"] if item["kind"] == "ddsc")
            self.assertEqual(finding["status"], "contradicted")
            self.assertEqual(finding["distinct_hashes"], 2)
            self.assertEqual(report["process"]["loaded_libraries"][0]["path"], "/a/libddsc.so")
            self.assertNotIn("nope", json.dumps(report))

    def test_failed_map_open_keeps_process_evidence_not_proved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            (proc / "root").mkdir(parents=True)
            (proc / "maps").write_text("0-1 r-xp 0 00:00 0 /libddsc.so\n")
            (proc / "environ").write_bytes(b"HOME=/home/robot\0")
            with mock.patch.object(self.module, "open_target_fd", side_effect=PermissionError("denied")):
                report = self.module.build_report(
                    self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                    {"HOME": "/home/collector"},
                )
            self.assertEqual(report["process"]["status"], "not_proved")
            self.assertEqual(report["process"]["loaded_libraries"][0]["sha256"], None)
            self.assertEqual(len(report["process"]["map_open_failures"]), 1)
            self.assertIn("could not be opened", report["process"]["reason"])

    def test_partial_map_evidence_cannot_prove_one_binary_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            library = proc / "root/a/libddsc.so"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"one-readable-build")
            (proc / "maps").write_text("0-1 r-xp 0 00:00 0 /a/libddsc.so\n1-2 r-xp 0 00:00 0 /missing/libddsc.so\n")
            (proc / "environ").write_bytes(b"HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            finding = next(item for item in report["binary_findings"] if item["kind"] == "ddsc")
            self.assertEqual(report["process"]["status"], "not_proved")
            self.assertEqual(finding["distinct_hashes"], 1)
            self.assertEqual(finding["status"], "not_proved")
            self.assertIn("incomplete", finding["meaning"])

    def test_fifo_replacing_deleted_map_path_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            fifo = proc / "root/libddsc.so"
            fifo.parent.mkdir(parents=True)
            os.mkfifo(fifo)
            (proc / "maps").write_text("0-1 r-xp 0 00:00 0 /libddsc.so (deleted)\n")
            (proc / "environ").write_bytes(b"HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["process"]["status"], "not_proved")
            self.assertEqual(report["process"]["loaded_libraries"][0]["sha256"], None)
            self.assertIn("not a regular file", report["process"]["map_open_failures"][0]["reason"])

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
            cwd_config = proc / "root/work/cyclone.xml"
            home_config = proc / "root/home/robot/cyclone.xml"
            cwd_config.parent.mkdir(parents=True)
            home_config.parent.mkdir(parents=True)
            (proc / "cwd").symlink_to("/work")
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

    def test_target_absolute_symlink_stays_inside_target_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            target_config = proc / "root/real/cyclone.xml"
            link = proc / "root/etc/cyclone.xml"
            target_config.parent.mkdir(parents=True)
            link.parent.mkdir(parents=True)
            target_config.write_text('<CycloneDDS><Domain Id="target-symlink"/></CycloneDDS>')
            link.symlink_to("/real/cyclone.xml")
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"CYCLONEDDS_URI=/etc/cyclone.xml\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["cyclonedds_config"]["domain_ids"], ["target-symlink"])

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

    def test_target_candidate_prefixes_use_target_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            target_lib = proc / "root/opt/robot/lib/libddsc.so"
            target_lib.parent.mkdir(parents=True)
            target_lib.write_bytes(b"target-dds")
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(len(report["library_candidates"]), 1)
            self.assertEqual(report["library_candidates"][0]["path"], "/opt/robot/lib/libddsc.so")
            self.assertEqual(report["library_candidates"][0]["sha256"], self.module.sha256_file(target_lib))
            self.assertEqual(report["library_candidate_prefixes"][0]["filesystem_scope"], "target_process_namespace")
            self.assertEqual(report["binary_findings"], [])

    def test_target_library_absolute_symlink_stays_inside_target_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            real_lib = proc / "root/real/libddsc.so"
            linked_lib = proc / "root/opt/robot/lib/libddsc.so"
            real_lib.parent.mkdir(parents=True)
            linked_lib.parent.mkdir(parents=True)
            real_lib.write_bytes(b"target-symlink-dds")
            linked_lib.symlink_to("/real/libddsc.so")
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["library_candidates"][0]["sha256"], self.module.sha256_file(real_lib))

    def test_unenumerable_target_prefix_is_not_proved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            (proc / "root/opt/robot").mkdir(parents=True)
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            with mock.patch.object(self.module.os, "listdir", side_effect=PermissionError("denied")):
                report = self.module.build_report(
                    self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                    {"HOME": "/home/collector"},
                )
            self.assertEqual(report["library_candidate_prefixes"][0]["status"], "not_proved")
            self.assertIn("PermissionError", report["library_candidate_prefixes"][0]["reason"])

    def test_fifo_candidate_does_not_block_and_is_not_proved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            fifo = proc / "root/opt/robot/lib/libddsc.so"
            fifo.parent.mkdir(parents=True)
            os.mkfifo(fifo)
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["library_candidates"], [])
            self.assertEqual(report["library_candidate_prefixes"][0]["status"], "not_proved")
            self.assertIn("not a regular file", report["library_candidate_prefixes"][0]["reason"])

    def test_non_utf8_candidate_filename_is_escaped_and_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            directory = proc / "root/opt/robot/lib"
            directory.mkdir(parents=True)
            backing_file = root / "backing-libddsc.so"
            backing_file.write_bytes(b"non-utf8-name")
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            real_open_target_fd = self.module.open_target_fd

            def open_target(logical, pid, proc_root, *, directory=False, nonblocking=False):
                if "\udcff" in str(logical):
                    return os.open(backing_file, os.O_RDONLY)
                return real_open_target_fd(logical, pid, proc_root, directory=directory, nonblocking=nonblocking)

            with mock.patch.object(self.module.os, "listdir", return_value=["libddsc\udcff.so"]), \
                 mock.patch.object(self.module, "open_target_fd", side_effect=open_target):
                report = self.module.build_report(
                    self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                    {"HOME": "/home/collector"},
                )
            self.assertEqual(report["library_candidate_prefixes"][0]["status"], "proved")
            self.assertIn("\\xff", report["library_candidates"][0]["path"])
            self.assertIsNotNone(report["library_candidates"][0]["sha256"])
            json.dumps(report, ensure_ascii=False).encode("utf-8")

    def test_non_utf8_candidate_open_failure_is_serializable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            (proc / "root/opt/robot").mkdir(parents=True)
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=/opt/robot\0HOME=/home/robot\0")
            real_open_target_fd = self.module.open_target_fd

            def open_target(logical, pid, proc_root, *, directory=False, nonblocking=False):
                if "\udcff" in str(logical):
                    raise PermissionError("denied")
                return real_open_target_fd(logical, pid, proc_root, directory=directory, nonblocking=nonblocking)

            with mock.patch.object(self.module.os, "listdir", return_value=["libddsc\udcff.so"]), \
                 mock.patch.object(self.module, "open_target_fd", side_effect=open_target):
                report = self.module.build_report(
                    self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                    {"HOME": "/home/collector"},
                )
            reason = report["library_candidate_prefixes"][0]["reason"]
            self.assertIn("\\xff", reason)
            json.dumps(report, ensure_ascii=False).encode("utf-8")

    def test_unenumerable_collector_prefix_is_not_proved(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            with mock.patch.object(self.module.os, "scandir", side_effect=PermissionError("denied")):
                report = self.module.build_report(self.args(search_prefix=[prefix]), {"HOME": "/home/collector"})
            self.assertEqual(report["library_candidate_prefixes"][0]["status"], "not_proved")
            self.assertIn("PermissionError", report["library_candidate_prefixes"][0]["reason"])

    def test_relative_target_candidate_prefix_uses_target_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proc = root / "proc/123"
            target_lib = proc / "root/work/vendor/lib/libddsc.so"
            target_lib.parent.mkdir(parents=True)
            target_lib.write_bytes(b"relative-target-dds")
            (proc / "cwd").symlink_to("/work")
            (proc / "maps").write_text("")
            (proc / "environ").write_bytes(b"LD_LIBRARY_PATH=vendor\0HOME=/home/robot\0")
            report = self.module.build_report(
                self.args(process_pid=123, proc_root=root / "proc", ros_domain=None),
                {"HOME": "/home/collector"},
            )
            self.assertEqual(report["library_candidates"][0]["path"], "target_cwd:vendor/lib/libddsc.so")
            self.assertEqual(report["library_candidates"][0]["sha256"], self.module.sha256_file(target_lib))

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
            library = proc / "root/libddsc.so"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"dds-build")
            (proc / "maps").write_text("0-1 r-xp 0 00:00 0 /libddsc.so\n")
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
            self.assertIn("/libddsc.so", text)
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
