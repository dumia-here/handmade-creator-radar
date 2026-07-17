from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .atomic import atomic_replace_json, atomic_write_json_new
from .errors import ErrorCode


FORBIDDEN_RELAXATIONS = ("allow_http", "disable_allowlist", "login", "cookie", "publish", "send", "contact_external", "payment")


@dataclass(frozen=True)
class ConfirmationRecord:
    task_id: str
    original_filename: str
    resume_token: str
    allowed_change: str
    created_at: str
    expires_at: str
    decision: str = "pending"
    decided_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "radar.confirmation.v0.1",
            "task_id": self.task_id,
            "original_filename": self.original_filename,
            "resume_token": self.resume_token,
            "allowed_change": self.allowed_change,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "decision": self.decision,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ConfirmationRecord":
        return cls(**{key: raw[key] for key in ("task_id", "original_filename", "resume_token", "allowed_change", "created_at", "expires_at", "decision", "decided_at")})


def create_confirmation(path: Path, *, task_id: str, original_filename: str, allowed_change: str, created_at: str, expires_at: str) -> ConfirmationRecord:
    if not _safe_minimal_change(allowed_change):
        raise ValueError(ErrorCode.UNSAFE_ACTION_REJECTED.value)
    token = hashlib.sha256(f"{task_id}\0{original_filename}\0{allowed_change}\0{created_at}".encode("utf-8")).hexdigest()
    record = ConfirmationRecord(task_id, original_filename, token, allowed_change, created_at, expires_at)
    atomic_write_json_new(path, record.to_dict())
    return record


def decide_confirmation(path: Path, decision: str, decided_at: str) -> ConfirmationRecord:
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    record = load_confirmation(path)
    if record.decision != "pending":
        return record
    updated = replace(record, decision=decision, decided_at=decided_at)
    atomic_replace_json(path, updated.to_dict())
    return updated


def consume_confirmation(path: Path, *, task_id: str, resume_token: str, requested_change: str, now: str) -> str:
    record = load_confirmation(path)
    if record.task_id != task_id or record.resume_token != resume_token:
        return "mismatch"
    if record.decision == "rejected":
        return "rejected"
    if record.decision != "approved":
        return "not_approved"
    if _parse_time(now) > _parse_time(record.expires_at):
        return "expired"
    if requested_change != record.allowed_change or not _safe_minimal_change(requested_change):
        return "unsafe_change"
    marker = path.with_suffix(path.suffix + ".consumed")
    try:
        descriptor = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return "already_consumed"
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"task_id": task_id, "consumed_at": now}, ensure_ascii=False) + "\n")
    return "consumed"


def load_confirmation(path: Path) -> ConfirmationRecord:
    return ConfirmationRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _safe_minimal_change(change: str) -> bool:
    lowered = change.casefold()
    return bool(change.strip()) and not any(term in lowered for term in FORBIDDEN_RELAXATIONS)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
