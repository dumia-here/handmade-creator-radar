import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.contract import ContentCandidate, Platform, RadarTask
from dispatch_bridge_radar.probes import ProbeRegistry, ReplayProbe


class ProbeRegistryTests(unittest.TestCase):
    def setUp(self):
        self.task = RadarTask.from_dict(json.loads((ROOT / "samples/task.cross-platform.json").read_text()))
        self.candidates = [
            ContentCandidate.from_dict(json.loads(line))
            for line in (ROOT / "samples/candidates.v0.1.jsonl").read_text().splitlines()
            if line.strip()
        ]

    def test_dispatches_each_requested_platform_to_its_probe(self):
        registry = ProbeRegistry()
        for request in self.task.probes:
            registry.register(ReplayProbe(request.platform, self.candidates))
        batches = registry.dispatch(self.task)
        self.assertEqual([batch.platform for batch in batches], [p.platform for p in self.task.probes])
        for batch in batches:
            self.assertTrue(all(item.platform == batch.platform for item in batch.candidates))

    def test_missing_probe_is_explicit(self):
        registry = ProbeRegistry()
        registry.register(ReplayProbe(Platform.XIAOHONGSHU, self.candidates))
        with self.assertRaisesRegex(LookupError, "no probe registered"):
            registry.dispatch(self.task)


if __name__ == "__main__":
    unittest.main()

