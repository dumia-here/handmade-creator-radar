from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class HandsTask:
    """A durable handoff from the conversational brain to an executor."""

    task_id: str
    project_id: str
    action: str
    request: str
    acceptance: List[str]
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandsTask":
        return cls(
            task_id=str(data["task_id"]),
            project_id=str(data["project_id"]),
            action=str(data["action"]),
            request=str(data["request"]),
            acceptance=[str(x) for x in data.get("acceptance", [])],
            payload=dict(data.get("payload", {})),
        )


@dataclass(frozen=True)
class Verification:
    ok: bool
    verifier: str
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Receipt:
    task_id: str
    status: str
    worker: str
    artifacts: List[str]
    verification: Verification
    message: str
    frontdesk_handoff: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["verification"] = self.verification.to_dict()
        data["frontdesk_handoff"] = dict(self.frontdesk_handoff)
        return data
