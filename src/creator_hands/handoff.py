from __future__ import annotations

from typing import Any, Dict, List

from .models import HandsTask, Verification


FRONTDESK_HANDOFF_SCHEMA_VERSION = 1


def build_frontdesk_handoff(
    task: HandsTask,
    *,
    status: str,
    worker: str,
    artifacts: List[str],
    verification: Verification,
    message: str,
) -> Dict[str, Any]:
    """Build the minimal terminal state the conversational Frontdesk needs.

    The handoff intentionally excludes ``task.payload``. Runtime credentials,
    private paths, worker configuration, and arbitrary payload data belong to
    the execution layer unless a higher layer explicitly decides to surface them.
    """

    may_claim_complete = status == "completed" and verification.ok
    return {
        "schema_version": FRONTDESK_HANDOFF_SCHEMA_VERSION,
        "task": {
            "task_id": task.task_id,
            "project_id": task.project_id,
            "action": task.action,
            "request": task.request,
            "acceptance": list(task.acceptance),
        },
        "outcome": {
            "terminal_status": status,
            "worker": worker,
            "artifacts": list(artifacts),
            "message": message,
        },
        "verification": verification.to_dict(),
        "frontdesk_state": {
            "may_claim_complete": may_claim_complete,
            "requires_frontdesk_review": not may_claim_complete,
        },
    }
