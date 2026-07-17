from __future__ import annotations

import json
from pathlib import Path

from .contract import ContentCandidate, RadarTask
from .filter import TrackFilter
from .probes import ProbeRegistry, ReplayProbe


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    task = RadarTask.from_dict(json.loads((root / "samples/task.cross-platform.json").read_text()))
    candidates = [
        ContentCandidate.from_dict(json.loads(line))
        for line in (root / "samples/candidates.v0.1.jsonl").read_text().splitlines()
        if line.strip()
    ]

    registry = ProbeRegistry()
    for request in task.probes:
        registry.register(ReplayProbe(request.platform, candidates))

    track_filter = TrackFilter(task.track_scope)
    for batch in registry.dispatch(task):
        print(f"[{batch.platform}] source={batch.source_kind}")
        for candidate in batch.candidates:
            result = track_filter.evaluate(candidate)
            print(f"  {candidate.candidate_id}: {result.decision} ({result.reason_code})")


if __name__ == "__main__":
    main()

