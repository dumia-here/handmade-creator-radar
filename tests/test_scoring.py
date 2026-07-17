import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.contract import Platform
from dispatch_bridge_radar.evidence import EvidenceItem, SignalName
from dispatch_bridge_radar.scoring import rank_platforms, score_platform


def load_cases():
    raw = json.loads((ROOT / "samples/evidence-replay.v0.1.json").read_text())
    return {
        case["case_id"]: [EvidenceItem.from_dict(item) for item in case["evidence"]]
        for case in raw["cases"]
    }


class PlatformScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_single_viral_post_is_capped_and_insufficient(self):
        result = score_platform(Platform.INSTAGRAM, self.cases["single_viral_post"])
        self.assertEqual(result.tier, "insufficient_evidence")
        self.assertTrue(result.needs_confirmation)
        self.assertIn("outlier_capped", result.reason_codes)

    def test_missing_values_are_not_scored_as_zero(self):
        result = score_platform(Platform.PINTEREST, self.cases["mostly_missing"])
        content_lifetime = next(item for item in result.signals if item.signal == SignalName.CONTENT_LIFETIME)
        density = next(item for item in result.signals if item.signal == SignalName.RELEVANT_CREATOR_DENSITY)
        self.assertEqual(content_lifetime.score, 60)
        self.assertIsNone(density.score)
        self.assertEqual(len(result.missing), 5)
        self.assertEqual(result.tier, "insufficient_evidence")
        self.assertFalse(result.evidence_threshold_met)

    def test_conflict_is_exposed_and_lowers_confidence(self):
        items = self.cases["conflicting_evidence"]
        conflict = score_platform(Platform.YOUTUBE, items)
        density = next(item for item in conflict.signals if item.signal == SignalName.RELEVANT_CREATOR_DENSITY)
        self.assertIn("conflicting_evidence", density.reasons)
        self.assertTrue(conflict.conflicts)
        clean_items = [replace(item, value=80) if item.evidence_id == "c2" else item for item in items]
        clean = score_platform(Platform.YOUTUBE, clean_items)
        clean_density = next(item for item in clean.signals if item.signal == SignalName.RELEVANT_CREATOR_DENSITY)
        self.assertLess(density.confidence, clean_density.confidence)

    def test_maintenance_cost_is_a_negative_signal(self):
        items = self.cases["high_maintenance_cost"]
        high_cost = score_platform(Platform.TIKTOK, items)
        low_cost_items = [replace(item, value=10) if item.signal == SignalName.MAINTENANCE_COST else item for item in items]
        low_cost = score_platform(Platform.TIKTOK, low_cost_items)
        high_cost_signal = next(item for item in high_cost.signals if item.signal == SignalName.MAINTENANCE_COST)
        self.assertIn("negative_cost_inverted", high_cost_signal.reasons)
        self.assertEqual(high_cost_signal.score, 5)
        self.assertLess(high_cost.score, low_cost.score)

    def test_sufficient_case_can_be_main(self):
        result = score_platform(Platform.XIAOHONGSHU, self.cases["sufficient_multi_creator_multi_window"])
        ranked = rank_platforms([result])
        self.assertTrue(result.evidence_threshold_met)
        self.assertFalse(result.needs_confirmation)
        self.assertEqual(ranked[0].tier, "main")

    def test_at_most_one_main_and_one_experiment(self):
        base = score_platform(Platform.XIAOHONGSHU, self.cases["sufficient_multi_creator_multi_window"])
        candidates = [
            replace(base, platform=Platform.XIAOHONGSHU, score=82),
            replace(base, platform=Platform.YOUTUBE, score=72),
            replace(base, platform=Platform.TIKTOK, score=61),
        ]
        ranked = rank_platforms(candidates)
        self.assertEqual(sum(item.tier == "main" for item in ranked), 1)
        self.assertEqual(sum(item.tier == "experiment" for item in ranked), 1)

    def test_tied_platforms_are_not_forced_into_a_winner(self):
        base = score_platform(Platform.XIAOHONGSHU, self.cases["sufficient_multi_creator_multi_window"])
        ranked = rank_platforms([
            replace(base, platform=Platform.XIAOHONGSHU, score=80),
            replace(base, platform=Platform.YOUTUBE, score=79.5),
        ])
        self.assertEqual(sum(item.tier == "main" for item in ranked), 0)

    def test_track_filter_rejected_candidate_does_not_enter_scoring(self):
        items = self.cases["sufficient_multi_creator_multi_window"]
        rejected = replace(items[0], evidence_id="rejected", candidate_id="blocked", value=100)
        accepted_ids = {item.candidate_id for item in items if item.candidate_id}
        result = score_platform(Platform.XIAOHONGSHU, [*items, rejected], accepted_candidate_ids=accepted_ids)
        self.assertNotIn("rejected", result.facts)


if __name__ == "__main__":
    unittest.main()
