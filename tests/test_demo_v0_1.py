import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "demo_v0_1.py"
spec = importlib.util.spec_from_file_location("demo_v0_1_test", ENTRYPOINT)
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

from dispatch_bridge_radar.offline_workflow import create_state_dirs


class DemoEntrypointTests(unittest.TestCase):
    def test_default_runs_preflight_then_golden_summary_without_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_dirs(root)
            reports = root / "reports"
            reports.mkdir()
            config = root / "notification-config"
            config.touch()
            result = demo.run_default(bridge_root=root, report_dir=reports, notification_config=config)
            self.assertEqual(result["preflight"]["status"], "ready")
            self.assertEqual(result["golden"]["source_kind"], "replay_golden")
            private_home_prefix = "/" + "Users" + "/"
            self.assertNotIn(private_home_prefix, str(result))

    def test_tests_wrapper_returns_safe_summary(self):
        class Result:
            returncode = 0
            stdout = ""
            stderr = "Ran 56 tests in 0.1s\nOK"

        payload, code = demo.run_tests(runner=lambda *args, **kwargs: Result())
        self.assertEqual((payload["status"], payload["test_count"], code), ("passed", 56, 0))
        self.assertNotIn("cwd", payload)

    def test_workflow_mode_uses_existing_offline_demo(self):
        result = demo.run_workflow_demo()
        self.assertTrue(result["all_paths_terminal"])


if __name__ == "__main__":
    unittest.main()
