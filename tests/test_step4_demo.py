import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.demo_replay import generate_demo
from dispatch_bridge_radar.offline_workflow import create_state_dirs
from dispatch_bridge_radar.preflight import check_preflight
from dispatch_bridge_radar.workflow_demo import run_workflow_demo


class Step4DemoTests(unittest.TestCase):
    def test_golden_replay_is_stable_and_never_live(self):
        first = generate_demo()
        second = generate_demo()
        self.assertEqual(first, second)
        self.assertEqual(first["source_kind"], "replay_golden")
        self.assertTrue(all(row["source_kind"] == "replay_golden" for row in first["candidates"]))
        self.assertTrue(all(score["tier"] == "insufficient_evidence" for score in first["platform_scores"]))
        self.assertEqual({row["decision"] for row in first["candidates"]}, {"accepted", "review", "rejected"})

    def test_preflight_is_offline_and_reports_single_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_dirs(root)
            reports = root / "reports"
            reports.mkdir()
            config = root / "bark-url"
            config.write_text("not-read-by-preflight", encoding="utf-8")
            result = check_preflight(bridge_root=root, report_dir=reports, golden_path=ROOT / "samples/golden-replay.v0.1.json", notification_config=config, tests_passed=True)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["reason_codes"], [])

    def test_private_notification_helper_is_not_bundled(self):
        self.assertEqual(list(ROOT.rglob("dispatch_bridge_notify.py")), [])

    def test_temporary_end_to_end_three_paths_reach_terminal_states(self):
        result = run_workflow_demo()
        self.assertTrue(result["all_paths_terminal"])
        self.assertEqual(result["success_path"], "completed")
        self.assertEqual(result["confirmation_resume_path"], "completed")
        self.assertEqual(result["failure_path"], "failed")
