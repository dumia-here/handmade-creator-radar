from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from .models import HandsTask, Receipt


class FileQueue:
    """A tiny durable queue backed by JSON files on disk."""

    STATES = ("queued", "running", "completed", "failed")

    def __init__(self, root: Path | str):
        self.root = Path(root)
        for state in self.STATES:
            (self.root / state).mkdir(parents=True, exist_ok=True)

    def enqueue(self, task: HandsTask) -> Path:
        target = self.root / "queued" / f"{task.task_id}.json"
        if any((self.root / state / f"{task.task_id}.json").exists() for state in self.STATES):
            raise ValueError(f"task_id already exists: {task.task_id}")
        self._atomic_json(target, task.to_dict())
        return target

    def claim_next(self) -> Optional[Tuple[HandsTask, Path]]:
        candidates = sorted((self.root / "queued").glob("*.json"))
        if not candidates:
            return None
        source = candidates[0]
        target = self.root / "running" / source.name
        source.replace(target)
        data = json.loads(target.read_text(encoding="utf-8"))
        return HandsTask.from_dict(data), target

    def finish(self, running_path: Path, receipt: Receipt) -> Path:
        state = "completed" if receipt.status == "completed" else "failed"
        task_target = self.root / state / running_path.name
        running_path.replace(task_target)
        receipt_path = self.root / state / f"{receipt.task_id}.receipt.json"
        self._atomic_json(receipt_path, receipt.to_dict())
        return receipt_path

    @staticmethod
    def _atomic_json(path: Path, data: object) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(path)
