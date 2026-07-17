from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

from .contract import Platform
from .evidence import EvidenceItem, SIGNALS, SignalName, StatementKind


@dataclass(frozen=True)
class SignalScore:
    signal: SignalName
    score: float | None
    confidence: float
    evidence_count: int
    missing_count: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.value,
            "score": self.score,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "missing_count": self.missing_count,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class PlatformScore:
    platform: Platform
    score: float | None
    confidence: float
    tier: str
    signals: tuple[SignalScore, ...]
    facts: tuple[str, ...]
    inferences: tuple[str, ...]
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]
    reason_codes: tuple[str, ...]
    needs_confirmation: bool
    evidence_threshold_met: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform.value,
            "score": self.score,
            "confidence": self.confidence,
            "tier": self.tier,
            "signals": [item.to_dict() for item in self.signals],
            "facts": list(self.facts),
            "inferences": list(self.inferences),
            "missing": list(self.missing),
            "conflicts": list(self.conflicts),
            "reason_codes": list(self.reason_codes),
            "needs_confirmation": self.needs_confirmation,
            "evidence_threshold_met": self.evidence_threshold_met,
        }


def score_platform(
    platform: Platform,
    evidence: Iterable[EvidenceItem],
    *,
    accepted_candidate_ids: set[str] | None = None,
) -> PlatformScore:
    """Score one platform after the TrackFilter gate.

    Values are normalized 0..100. Missing statements never enter a numeric
    denominator. maintenance_cost is inverted because it is the sole negative
    signal.
    """
    items = tuple(
        item
        for item in evidence
        if item.platform == platform
        and (
            accepted_candidate_ids is None
            or item.candidate_id is None
            or item.candidate_id in accepted_candidate_ids
        )
    )
    usable_items = tuple(item for item in items if item.statement_kind != StatementKind.MISSING)
    creators = {item.creator_id for item in usable_items if item.creator_id}
    contents = {item.candidate_id for item in usable_items if item.candidate_id}
    windows = {item.observation_window for item in usable_items}
    threshold_met = len(windows) >= 2 and (len(creators) >= 3 or len(contents) >= 5)

    signal_scores = tuple(_score_signal(signal, items) for signal in SIGNALS)
    available = tuple(item for item in signal_scores if item.score is not None)
    if available:
        score = round(sum(item.score for item in available if item.score is not None) / len(available), 2)
        confidence = round(
            (sum(item.confidence for item in available) / len(available))
            * (len(available) / len(SIGNALS)),
            3,
        )
    else:
        score = None
        confidence = 0.0

    conflicts = tuple(
        f"{item.signal.value}:conflicting_evidence"
        for item in signal_scores
        if "conflicting_evidence" in item.reasons
    )
    facts = tuple(item.evidence_id for item in items if item.statement_kind == StatementKind.FACT)
    inferences = tuple(
        item.evidence_id for item in items if item.statement_kind == StatementKind.INFERENCE
    )
    missing = tuple(item.evidence_id for item in items if item.statement_kind == StatementKind.MISSING)

    reason_codes: list[str] = []
    if not threshold_met:
        reason_codes.append("insufficient_independent_evidence")
    if len(available) < len(SIGNALS):
        reason_codes.append("signals_missing")
    if conflicts:
        reason_codes.append("conflicting_evidence")
    if confidence < 0.5:
        reason_codes.append("low_confidence")
    if any("outlier_capped" in item.reasons for item in signal_scores):
        reason_codes.append("outlier_capped")

    needs_confirmation = not threshold_met or bool(conflicts) or confidence < 0.5 or len(available) < len(SIGNALS)
    tier = "insufficient_evidence" if not threshold_met else "observe"
    return PlatformScore(
        platform=platform,
        score=score,
        confidence=confidence,
        tier=tier,
        signals=signal_scores,
        facts=facts,
        inferences=inferences,
        missing=missing,
        conflicts=conflicts,
        reason_codes=tuple(reason_codes),
        needs_confirmation=needs_confirmation,
        evidence_threshold_met=threshold_met,
    )


def rank_platforms(scores: Iterable[PlatformScore]) -> tuple[PlatformScore, ...]:
    """Assign at most one main and one experiment tier without forced winners."""
    ranked = [
        replace(item, tier="insufficient_evidence" if not item.evidence_threshold_met else "observe")
        for item in scores
    ]
    eligible = sorted(
        (item for item in ranked if not item.needs_confirmation and item.score is not None),
        key=lambda item: (-float(item.score), item.platform.value),
    )

    main = _clear_winner([item for item in eligible if item.score >= 70 and item.confidence >= 0.55])
    if main is not None:
        ranked = [replace(item, tier="main") if item.platform == main.platform else item for item in ranked]

    remaining = [item for item in eligible if main is None or item.platform != main.platform]
    experiment = _clear_winner(
        [item for item in remaining if item.score >= 55 and item.confidence >= 0.45]
    )
    if experiment is not None:
        ranked = [
            replace(item, tier="experiment") if item.platform == experiment.platform else item
            for item in ranked
        ]
    return tuple(sorted(ranked, key=lambda item: item.platform.value))


def score_platforms(
    evidence: Iterable[EvidenceItem],
    *,
    accepted_candidate_ids: Mapping[Platform, set[str]] | None = None,
) -> tuple[PlatformScore, ...]:
    items = tuple(evidence)
    platforms = sorted({item.platform for item in items}, key=lambda item: item.value)
    scores = [
        score_platform(
            platform,
            items,
            accepted_candidate_ids=(accepted_candidate_ids or {}).get(platform),
        )
        for platform in platforms
    ]
    return rank_platforms(scores)


def _score_signal(signal: SignalName, evidence: tuple[EvidenceItem, ...]) -> SignalScore:
    relevant = tuple(item for item in evidence if item.signal == signal)
    missing_count = sum(item.statement_kind == StatementKind.MISSING for item in relevant)
    usable = tuple(item for item in relevant if item.statement_kind != StatementKind.MISSING)
    reasons: list[str] = []
    if not usable:
        return SignalScore(signal, None, 0.0, 0, missing_count, ("no_usable_evidence",))

    weighted_total = 0.0
    total_weight = 0.0
    effective_values: list[float] = []
    for item in usable:
        value = float(item.value)
        effective_values.append(value)
        contribution = 100.0 - value if signal == SignalName.MAINTENANCE_COST else value
        if contribution > 85.0:
            contribution = 85.0
            if "outlier_capped" not in reasons:
                reasons.append("outlier_capped")
        kind_weight = 1.0 if item.statement_kind == StatementKind.FACT else 0.75
        weight = max(0.01, item.confidence * item.directness * item.freshness * kind_weight)
        weighted_total += contribution * weight
        total_weight += weight

    score = round(weighted_total / total_weight, 2)
    confidence = sum(
        item.confidence * item.directness * item.freshness
        * (1.0 if item.statement_kind == StatementKind.FACT else 0.75)
        for item in usable
    ) / len(usable)
    confidence *= len(usable) / (len(usable) + missing_count)

    if min(effective_values) <= 35.0 and max(effective_values) >= 65.0:
        reasons.append("conflicting_evidence")
        confidence *= 0.6
    if signal == SignalName.MAINTENANCE_COST:
        reasons.append("negative_cost_inverted")
    if missing_count:
        reasons.append("missing_excluded_from_numeric_score")
    if not reasons:
        reasons.append("weighted_evidence")
    return SignalScore(
        signal=signal,
        score=score,
        confidence=round(confidence, 3),
        evidence_count=len(usable),
        missing_count=missing_count,
        reasons=tuple(reasons),
    )


def _clear_winner(items: list[PlatformScore]) -> PlatformScore | None:
    if not items:
        return None
    ordered = sorted(items, key=lambda item: (-float(item.score), item.platform.value))
    if len(ordered) == 1:
        return ordered[0]
    if float(ordered[0].score) - float(ordered[1].score) < 2.0:
        return None
    return ordered[0]
