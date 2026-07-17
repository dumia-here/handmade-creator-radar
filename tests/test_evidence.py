import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.evidence import EvidenceItem, StatementKind


class EvidenceItemTests(unittest.TestCase):
    def base(self):
        return {
            "evidence_id": "e1",
            "platform": "xiaohongshu",
            "candidate_id": "candidate-1",
            "source_url": "https://example.invalid/e1",
            "observed_at": "2026-07-01T00:00:00Z",
            "observation_window": "w1",
            "source_type": "replay",
            "signal": "expression_fit",
            "value": 0,
            "statement_kind": "fact",
            "directness": 1,
            "freshness": 1,
            "confidence": 1,
        }

    def test_zero_is_a_fact_not_missing(self):
        item = EvidenceItem.from_dict(self.base())
        self.assertEqual(item.value, 0)
        self.assertEqual(item.statement_kind, StatementKind.FACT)

    def test_missing_value_stays_none(self):
        raw = self.base()
        raw.update({"value": None, "statement_kind": "missing"})
        item = EvidenceItem.from_dict(raw)
        self.assertIsNone(item.value)
        self.assertEqual(item.statement_kind, StatementKind.MISSING)

    def test_candidate_and_creator_cannot_both_be_missing(self):
        raw = self.base()
        raw.pop("candidate_id")
        with self.assertRaisesRegex(ValueError, "cannot both be missing"):
            EvidenceItem.from_dict(raw)

    def test_fact_inference_and_missing_are_unambiguous(self):
        kinds = []
        for index, kind in enumerate(("fact", "inference", "missing"), 1):
            raw = self.base()
            raw["evidence_id"] = f"e{index}"
            raw["statement_kind"] = kind
            raw["value"] = None if kind == "missing" else 50
            kinds.append(EvidenceItem.from_dict(raw).statement_kind)
        self.assertEqual(kinds, [StatementKind.FACT, StatementKind.INFERENCE, StatementKind.MISSING])


if __name__ == "__main__":
    unittest.main()
