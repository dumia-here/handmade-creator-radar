from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from .models import HandsTask


def build_task(
    *,
    request: str,
    project_id: str,
    action: str,
    acceptance: Iterable[str],
    payload: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> HandsTask:
    """Build the explicit contract after the conversational brain has decided what to do.

    This function deliberately does not pretend to understand arbitrary natural language.
    The Frontdesk/assistant remains responsible for turning the conversation into explicit
    project, action, acceptance criteria, and payload before the task enters the bridge.
    """

    request = request.strip()
    project_id = project_id.strip()
    action = action.strip()
    criteria = [item.strip() for item in acceptance if item.strip()]
    if not request:
        raise ValueError("request must not be empty")
    if not project_id:
        raise ValueError("project_id must not be empty")
    if not action:
        raise ValueError("action must not be empty")
    if not criteria:
        raise ValueError("at least one acceptance criterion is required")

    return HandsTask(
        task_id=task_id or f"hands-{uuid4().hex[:12]}",
        project_id=project_id,
        action=action,
        request=request,
        acceptance=criteria,
        payload=dict(payload or {}),
    )
