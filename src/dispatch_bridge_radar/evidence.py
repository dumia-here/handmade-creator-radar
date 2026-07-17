from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .contract import Platform


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class StatementKind(_StringEnum):
    FACT = "fact"
    INFERENCE = "inference"
    MISSING = "missing"


class SignalName(_StringEnum):
    RELEVANT_CREATOR_DENSITY = "relevant_creator_density"
    SMALL_ACCOUNT_RELATIVE_GROWTH = "small_account_relative_growth"
    STRANGER_ENGAGEMENT = "stranger_engagement"
    CONTENT_LIFETIME = "content_lifetime"
    EXPRESSION_FIT = "expression_fit"
    MAINTENANCE_COST = "maintenance_cost"


SIGNALS = tuple(SignalName)


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    platform: Platform
    source_url: str
    observed_at: str
    observation_window: str
    source_type: str
    signal: SignalName
    statement_kind: StatementKind
    directness: float
    freshness: float
    confidence: float
    candidate_id: str | None = None
    creator_id: str | None = None
    value: float | None = None
    baseline: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.candidate_id and not self.creator_id:
            raise ValueError("candidate_id and creator_id cannot both be missing")
        for field_name in ("evidence_id", "source_url", "observed_at", "observation_window", "source_type"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("directness", "freshness", "confidence"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if self.statement_kind == StatementKind.MISSING:
            if self.value is not None:
                raise ValueError("missing evidence must not carry a value")
        elif self.value is None:
            raise ValueError("fact and inference evidence require a value")
        if self.value is not None and not 0.0 <= self.value <= 100.0:
            raise ValueError("value must be normalized to the 0..100 range")
        if self.baseline is not None and not 0.0 <= self.baseline <= 100.0:
            raise ValueError("baseline must be normalized to the 0..100 range")

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EvidenceItem":
        return cls(
            evidence_id=_required_string(raw.get("evidence_id"), "evidence_id"),
            platform=Platform(raw["platform"]),
            candidate_id=_optional_string(raw.get("candidate_id"), "candidate_id"),
            creator_id=_optional_string(raw.get("creator_id"), "creator_id"),
            source_url=_required_string(raw.get("source_url"), "source_url"),
            observed_at=_required_string(raw.get("observed_at"), "observed_at"),
            observation_window=_required_string(raw.get("observation_window"), "observation_window"),
            source_type=_required_string(raw.get("source_type"), "source_type"),
            signal=SignalName(raw["signal"]),
            value=_optional_number(raw.get("value"), "value"),
            baseline=_optional_number(raw.get("baseline"), "baseline"),
            statement_kind=StatementKind(raw["statement_kind"]),
            directness=_number(raw.get("directness"), "directness"),
            freshness=_number(raw.get("freshness"), "freshness"),
            confidence=_number(raw.get("confidence"), "confidence"),
            notes=str(raw.get("notes", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "platform": self.platform.value,
            "candidate_id": self.candidate_id,
            "creator_id": self.creator_id,
            "source_url": self.source_url,
            "observed_at": self.observed_at,
            "observation_window": self.observation_window,
            "source_type": self.source_type,
            "signal": self.signal.value,
            "value": self.value,
            "baseline": self.baseline,
            "statement_kind": self.statement_kind.value,
            "directness": self.directness,
            "freshness": self.freshness,
            "confidence": self.confidence,
            "notes": self.notes,
        }


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    return value.strip() or None


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number")
    return float(value)


def _optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    return _number(value, field_name)
