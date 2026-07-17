import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.bridge import BridgeStatus, load_candidates, load_task_card, run_replay, write_report
from dispatch_bridge_radar.contract import ContentCandidate, RadarTask


class OriginalBridgeGlueTests(unittest.TestCase):
    def setUp(self):
        self.task = RadarTask.from_dict(json.loads((ROOT / "samples/task.cross-platform.json").read_text()))
        self.candidates = load_candidates(ROOT / "samples/candidates.v0.1.jsonl")

    def test_replay_result_routes_to_existing_completed_directory(self):
        report = run_replay(self.task, self.candidates)
        self.assertEqual(report["bridge_status"], BridgeStatus.COMPLETED.value)
        self.assertEqual(report["target_state_directory"], "02-已完成")
        self.assertEqual(report["summary"], {"accepted": 6, "review": 0, "rejected": 4})
        self.assertFalse(report["safety"]["external_actions_executed"])

    def test_review_routes_to_existing_confirmation_gate(self):
        raw = json.loads((ROOT / "samples/task.cross-platform.json").read_text())
        raw["probes"] = [raw["probes"][0]]
        task = RadarTask.from_dict(raw)
        unknown = ContentCandidate.from_dict(
            {"candidate_id": "xhs-review", "platform": "xiaohongshu", "title": "今天做了一件新东西"}
        )
        report = run_replay(task, [unknown])
        self.assertEqual(report["bridge_status"], BridgeStatus.NEEDS_CONFIRMATION.value)
        self.assertEqual(report["target_state_directory"], "03-需确认")

    def test_marked_markdown_task_card_loads(self):
        task_json = (ROOT / "samples/task.cross-platform.json").read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.md"
            path.write_text(
                "# task\n<!-- RADAR_TASK_JSON_BEGIN -->\n```json\n"
                + task_json
                + "\n```\n<!-- RADAR_TASK_JSON_END -->\n",
                encoding="utf-8",
            )
            self.assertEqual(load_task_card(path).task_id, self.task.task_id)

    def test_report_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_report(path, {"status": "new"})


if __name__ == "__main__":
    unittest.main()
