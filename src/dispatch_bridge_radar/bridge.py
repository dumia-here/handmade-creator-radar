from __future__ import annotations

import argparse
import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .contract import ContentCandidate, ProbeMode, RadarTask
from .filter import FilterDecision, TrackFilter
from .probes import ProbeRegistry, ReplayProbe


TASK_JSON_BEGIN = "<!-- RADAR_TASK_JSON_BEGIN -->"
TASK_JSON_END = "<!-- RADAR_TASK_JSON_END -->"


class BridgeStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_CONFIRMATION = "needs_confirmation"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


def load_task_card(path: Path) -> RadarTask:
    """Load a JSON contract directly or from a marked block in an md/txt task card."""
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.casefold() == ".json":
        raw = json.loads(text)
    else:
        pattern = re.compile(
            re.escape(TASK_JSON_BEGIN) + r"\s*(?:```json\s*)?(.*?)(?:\s*```)?\s*" + re.escape(TASK_JSON_END),
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            raise ValueError("radar task card is missing the marked JSON contract block")
        raw = json.loads(match.group(1))
    return RadarTask.from_dict(raw)


def load_candidates(path: Path) -> tuple[ContentCandidate, ...]:
    candidates = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            candidates.append(ContentCandidate.from_dict(json.loads(line)))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid candidate at line {line_number}: {exc}") from exc
    return tuple(candidates)


def run_replay(task: RadarTask, candidates: Iterable[ContentCandidate]) -> dict[str, Any]:
    """Run stable replay probes and return a result for the original bridge router."""
    candidate_pool = tuple(candidates)
    non_replay = [request.platform.value for request in task.probes if request.mode != ProbeMode.REPLAY]
    if non_replay:
        raise ValueError(f"no real probe adapter registered for: {', '.join(non_replay)}")

    registry = ProbeRegistry()
    for request in task.probes:
        registry.register(ReplayProbe(request.platform, candidate_pool))

    track_filter = TrackFilter(task.track_scope)
    rows: list[dict[str, Any]] = []
    for batch in registry.dispatch(task):
        for candidate in batch.candidates:
            result = track_filter.evaluate(candidate)
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "platform": candidate.platform.value,
                    "source_kind": batch.source_kind,
                    "decision": result.decision.value,
                    "reason_code": result.reason_code,
                    "reason": result.reason,
                    "matched_terms": list(result.matched_terms),
                }
            )

    counts = {
        decision.value: sum(row["decision"] == decision.value for row in rows)
        for decision in FilterDecision
    }
    has_review = counts[FilterDecision.REVIEW.value] > 0
    status = BridgeStatus.NEEDS_CONFIRMATION if has_review else BridgeStatus.COMPLETED
    return {
        "schema_version": "radar.result.v0.1",
        "task_id": task.task_id,
        "title": task.title,
        "bridge_status": status.value,
        "target_state_directory": "03-需确认" if has_review else "02-已完成",
        "source_mode": "replay",
        "summary": counts,
        "results": rows,
        "safety": {
            "read_only": task.safety.read_only,
            "forbidden_actions": list(task.safety.forbidden_actions),
            "external_actions_executed": False,
        },
    }


def failure_report(task_path: Path, error: Exception) -> dict[str, Any]:
    return {
        "schema_version": "radar.result.v0.1",
        "task_file": str(task_path),
        "bridge_status": BridgeStatus.FAILED.value,
        "target_state_directory": "04-失败",
        "error_type": type(error).__name__,
        "error": str(error),
        "external_actions_executed": False,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {path}")
    if not path.parent.is_dir():
        raise FileNotFoundError(f"report parent directory does not exist: {path.parent}")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Original Dispatch Bridge radar-task glue")
    parser.add_argument("--task", type=Path, required=True, help="md/txt task card or JSON contract")
    parser.add_argument("--candidates", type=Path, required=True, help="replay candidates JSONL")
    parser.add_argument("--output", type=Path, required=True, help="new result JSON path")
    args = parser.parse_args()

    try:
        task = load_task_card(args.task)
        report = run_replay(task, load_candidates(args.candidates))
        write_report(args.output, report)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:
        report = failure_report(args.task, exc)
        try:
            write_report(args.output, report)
        except FileExistsError:
            pass
        print(json.dumps(report, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
