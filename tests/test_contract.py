import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.contract import Platform, RadarTask
from dispatch_bridge_radar.legacy import LegacyXiaohongshuTaskAdapter


class RadarTaskContractTests(unittest.TestCase):
    def test_cross_platform_sample_loads(self):
        task = RadarTask.from_dict(json.loads((ROOT / "samples/task.cross-platform.json").read_text()))
        self.assertEqual(len(task.probes), 4)
        self.assertEqual(
            {probe.platform for probe in task.probes},
            {Platform.XIAOHONGSHU, Platform.DOUYIN, Platform.INSTAGRAM, Platform.YOUTUBE},
        )
        self.assertTrue(task.safety.read_only)
        self.assertIn("small_account_relative_growth", task.observation_signals)
        self.assertIn("only_accepted_candidates_enter_later_scoring", task.acceptance_criteria)

    def test_duplicate_platform_is_rejected(self):
        raw = json.loads((ROOT / "samples/task.cross-platform.json").read_text())
        raw["probes"].append(raw["probes"][0])
        with self.assertRaisesRegex(ValueError, "only once"):
            RadarTask.from_dict(raw)

    def test_write_task_is_rejected(self):
        raw = json.loads((ROOT / "samples/task.cross-platform.json").read_text())
        raw["safety"]["read_only"] = False
        with self.assertRaisesRegex(ValueError, "read-only"):
            RadarTask.from_dict(raw)

    def test_legacy_xiaohongshu_task_is_lifted(self):
        task = LegacyXiaohongshuTaskAdapter.adapt(
            {"task_id": "old-1", "keywords": ["手作娃娃"], "title": "旧巡店任务"}
        )
        self.assertEqual(task.schema_version, "radar.task.v0.1")
        self.assertEqual(task.probes[0].platform, Platform.XIAOHONGSHU)
        self.assertTrue(task.safety.read_only)


if __name__ == "__main__":
    unittest.main()
