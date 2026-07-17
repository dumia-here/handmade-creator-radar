import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.contract import ContentCandidate, RadarTask
from dispatch_bridge_radar.filter import FilterDecision, TrackFilter


def load_candidates():
    return [
        ContentCandidate.from_dict(json.loads(line))
        for line in (ROOT / "samples/candidates.v0.1.jsonl").read_text().splitlines()
        if line.strip()
    ]


class TrackFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = RadarTask.from_dict(json.loads((ROOT / "samples/task.cross-platform.json").read_text()))
        cls.filter = TrackFilter(cls.task.track_scope)

    def test_replay_sample_matches_expected_decisions(self):
        expected = json.loads((ROOT / "samples/expected-filter-results.json").read_text())
        actual = {item.candidate_id: self.filter.evaluate(item).decision for item in load_candidates()}
        self.assertEqual(actual, {key: FilterDecision(value) for key, value in expected.items()})

    def test_cross_track_without_note_is_rejected(self):
        item = ContentCandidate.from_dict(
            {
                "candidate_id": "cross-no-note",
                "platform": "youtube",
                "title": "A reveal format",
                "declared_lane": "cross_track",
                "migration_methods": ["result_reveal"],
            }
        )
        result = self.filter.evaluate(item)
        self.assertEqual(result.decision, FilterDecision.REJECTED)
        self.assertEqual(result.reason_code, "cross_track_note_missing")

    def test_unknown_case_is_held_for_review(self):
        item = ContentCandidate.from_dict(
            {"candidate_id": "unknown", "platform": "weibo", "title": "今天做了一件新东西"}
        )
        result = self.filter.evaluate(item)
        self.assertEqual(result.decision, FilterDecision.REVIEW)

    def test_compound_making_and_doll_terms_are_accepted(self):
        item = ContentCandidate.from_dict(
            {
                "candidate_id": "compound-positive",
                "platform": "bilibili",
                "title": "不织布教程｜自己动手做一只超可爱的不织布娃娃吧！",
            }
        )
        result = self.filter.evaluate(item)
        self.assertEqual(result.decision, FilterDecision.ACCEPTED)
        self.assertEqual(result.reason_code, "matched_compound_making_object_terms")
        self.assertEqual(result.matched_terms, ("making:不织布", "object:娃娃"))

    def test_making_term_without_doll_object_stays_in_review(self):
        item = ContentCandidate.from_dict(
            {"candidate_id": "making-only", "platform": "bilibili", "title": "手工制作陶瓷杯"}
        )
        self.assertEqual(self.filter.evaluate(item).decision, FilterDecision.REVIEW)

    def test_doll_object_without_making_term_stays_in_review(self):
        item = ContentCandidate.from_dict(
            {"candidate_id": "object-only", "platform": "bilibili", "title": "可爱娃娃开箱分享"}
        )
        self.assertEqual(self.filter.evaluate(item).decision, FilterDecision.REVIEW)

    def test_excluded_lane_beats_new_compound_rule(self):
        item = ContentCandidate.from_dict(
            {
                "candidate_id": "compound-beauty",
                "platform": "bilibili",
                "title": "美妆教程：手工制作娃娃妆容",
            }
        )
        result = self.filter.evaluate(item)
        self.assertEqual(result.decision, FilterDecision.REJECTED)
        self.assertEqual(result.reason_code, "matched_excluded_terms")


if __name__ == "__main__":
    unittest.main()
