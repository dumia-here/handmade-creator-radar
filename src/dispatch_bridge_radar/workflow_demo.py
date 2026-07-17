from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .approvals import create_confirmation, decide_confirmation
from .errors import ErrorCode, ErrorReceipt
from .offline_workflow import OfflineBridgeWorkflow, WorkflowResult, create_state_dirs


def run_workflow_demo() -> dict[str, Any]:
    notifications: list[tuple[str, str]] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        create_state_dirs(root)
        reports = root / "reports"
        reports.mkdir()
        workflow = OfflineBridgeWorkflow(root, lambda task_id, status: notifications.append((task_id, status)))
        now = "2026-07-17T00:00:00Z"

        success_task = root / "01-执行中/success.md"
        success_task.write_text("success", encoding="utf-8")
        success = workflow.complete(task_path=success_task, task_id="success", report_path=reports / "success.md", report_text="complete\n", receipt_path=root / "02-已完成/success_receipt.md", receipt_text="receipt\n", occurred_at=now)

        resume_task = root / "03-需确认/resume.md"
        resume_task.write_text("resume", encoding="utf-8")
        confirmation_path = root / "03-需确认/resume_confirmation.json"
        record = create_confirmation(confirmation_path, task_id="resume", original_filename=resume_task.name, allowed_change="track_filter:compound_making_object_terms", created_at=now, expires_at="2026-07-18T00:00:00Z")
        decide_confirmation(confirmation_path, "approved", "2026-07-17T00:01:00Z")
        notifications.append(("resume", "needs_confirmation"))

        def resume_action(active_task: Path) -> WorkflowResult:
            return workflow.complete(task_path=active_task, task_id="resume", report_path=reports / "resume.md", report_text="resumed\n", receipt_path=root / "02-已完成/resume_receipt.md", receipt_text="receipt\n", occurred_at="2026-07-17T00:02:00Z")

        resumed = workflow.resume(confirmation_path=confirmation_path, task_path=resume_task, task_id="resume", resume_token=record.resume_token, requested_change=record.allowed_change, now="2026-07-17T00:02:00Z", action=resume_action)

        failed_task = root / "01-执行中/failed.md"
        failed_task.write_text("failed", encoding="utf-8")
        error = ErrorReceipt.create(task_id="failed", stage="parse", reason_code=ErrorCode.PARSE_ERROR, occurred_at=now)
        failed = workflow.fail(task_path=failed_task, task_id="failed", error=error)
        return {
            "schema_version": "radar.workflow-demo.v0.1",
            "success_path": success.status,
            "confirmation_resume_path": resumed.status,
            "failure_path": failed.status,
            "notifications": [list(item) for item in notifications],
            "all_paths_terminal": success.status == "completed" and resumed.status == "completed" and failed.status == "failed",
        }


def main() -> int:
    result = run_workflow_demo()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["all_paths_terminal"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
