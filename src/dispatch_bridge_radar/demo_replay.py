from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .contract import ContentCandidate, Platform
from .evidence import EvidenceItem
from .filter import TrackFilter
from .live_baseline import default_task
from .scoring import rank_platforms, score_platform


DEFAULT_GOLDEN = Path(__file__).resolve().parents[2] / "samples/golden-replay.v0.1.json"


def generate_demo(path: Path = DEFAULT_GOLDEN) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("source_kind") != "replay_golden":
        raise ValueError("golden replay must be marked replay_golden")
    candidates = tuple(ContentCandidate.from_dict(item) for item in raw["candidates"])
    evidence = tuple(EvidenceItem.from_dict(item) for item in raw["evidence"])
    track_filter = TrackFilter(default_task().track_scope)
    rows = []
    accepted: dict[Platform, set[str]] = {}
    for item in candidates:
        result = track_filter.evaluate(item)
        rows.append({"candidate_id": item.candidate_id, "platform": item.platform.value, "decision": result.decision.value, "reason_code": result.reason_code, "source_kind": item.source_kind})
        if result.decision.value == "accepted":
            accepted.setdefault(item.platform, set()).add(item.candidate_id)
    scores = rank_platforms(score_platform(platform, evidence, accepted_candidate_ids=ids) for platform, ids in sorted(accepted.items(), key=lambda pair: pair[0].value))
    return {
        "schema_version": "radar.golden-demo-result.v0.1",
        "source_kind": "replay_golden",
        "observation_window": raw["observation_window"],
        "candidates": rows,
        "evidence": [item.to_dict() for item in evidence],
        "platform_scores": [item.to_dict() for item in scores],
        "portable_patterns": ["成品特写后回到制作过程", "固定机位记录材料到成形", "角色名加鲜明动作形成系列"],
        "gungun_topics": ["麻到功的表情针脚转折", "多耳滚的多耳定位与翻面", "笑天犬从纸样到笑脸成形"],
        "low_cost_script": "成品近景 2 秒 + 当前工作台三段手部素材 + 同机位结果揭晓",
        "confidence_note": "first window remains insufficient_evidence; replay is never counted as live",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline deterministic golden radar replay")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    args = parser.parse_args()
    print(json.dumps(generate_demo(args.golden), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
