from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .approvals import consume_confirmation
from .atomic import ArtifactWriteError, atomic_write_json_new, atomic_write_new
from .errors import ErrorCode, ErrorReceipt


STATE_DIRS = ("00-待执行", "01-执行中", "02-已完成", "03-需确认", "04-失败")


@dataclass(frozen=True)
class WorkflowResult:
    status: str
    task_path: str
    error: ErrorReceipt | None = None


class OfflineBridgeWorkflow:
    """Offline-only state transition harness; production notification stays injected."""

    def __init__(self, root: Path, notifier: Callable[[str, str], None], *, mover: Callable[[str, str], None] = os.replace):
        self.root = root
        self.notifier = notifier
        self.mover = mover

    def complete(self, *, task_path: Path, task_id: str, report_path: Path, report_text: str, receipt_path: Path, receipt_text: str, occurred_at: str) -> WorkflowResult:
        try:
            atomic_write_new(report_path, report_text)
            atomic_write_new(receipt_path, receipt_text)
        except ArtifactWriteError as exc:
            receipt = ErrorReceipt.create(task_id=task_id, stage="artifact_write", reason_code=exc.reason_code, occurred_at=occurred_at, preserved_outputs=tuple(str(path) for path in (report_path, receipt_path) if path.exists()))
            return WorkflowResult("failed", str(task_path), receipt)
        destination = self.root / "02-已完成" / task_path.name
        try:
            self.mover(str(task_path), str(destination))
        except Exception:
            receipt = ErrorReceipt.create(task_id=task_id, stage="task_move", reason_code=ErrorCode.INTERNAL_ERROR, occurred_at=occurred_at, preserved_outputs=(str(report_path), str(receipt_path), str(task_path)))
            return WorkflowResult("recoverable_error", str(task_path), receipt)
        self.notifier(task_id, "completed")
        return WorkflowResult("completed", str(destination))

    def fail(self, *, task_path: Path, task_id: str, error: ErrorReceipt) -> WorkflowResult:
        error_path = self.root / "04-失败" / f"{task_path.stem}_error.json"
        atomic_write_json_new(error_path, error.to_dict())
        destination = self.root / "04-失败" / task_path.name
        self.mover(str(task_path), str(destination))
        self.notifier(task_id, "failed")
        return WorkflowResult("failed", str(destination), error)

    def resume(self, *, confirmation_path: Path, task_path: Path, task_id: str, resume_token: str, requested_change: str, now: str, action: Callable[[Path], WorkflowResult]) -> WorkflowResult:
        outcome = consume_confirmation(confirmation_path, task_id=task_id, resume_token=resume_token, requested_change=requested_change, now=now)
        if outcome != "consumed":
            return WorkflowResult(outcome, str(task_path))
        running = self.root / "01-执行中" / task_path.name
        try:
            self.mover(str(task_path), str(running))
            return action(running)
        except Exception:
            error = ErrorReceipt.create(task_id=task_id, stage="resume", reason_code=ErrorCode.INTERNAL_ERROR, occurred_at=now, preserved_outputs=(str(running if running.exists() else task_path),))
            active = running if running.exists() else task_path
            return self.fail(task_path=active, task_id=task_id, error=error)


def create_state_dirs(root: Path) -> None:
    for name in STATE_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)


def find_stale_tasks(running_dir: Path, *, older_than_seconds: float, now_timestamp: float) -> tuple[Path, ...]:
    return tuple(sorted((path for path in running_dir.iterdir() if path.is_file() and now_timestamp - path.stat().st_mtime >= older_than_seconds), key=lambda path: path.name))
