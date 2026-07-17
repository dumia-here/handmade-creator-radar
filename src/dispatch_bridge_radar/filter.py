from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contract import ContentCandidate, TrackScope


class FilterDecision(str, Enum):
    ACCEPTED = "accepted"
    REVIEW = "review"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FilterResult:
    candidate_id: str
    decision: FilterDecision
    reason_code: str
    reason: str
    matched_terms: tuple[str, ...] = ()


class TrackFilter:
    """Conservative gate before evidence collection and platform scoring."""

    INCLUDE_TERMS = {
        "handmade_dolls": ("手作娃娃", "手作娃", "handmade doll", "cloth doll"),
        "art_dolls": ("艺术玩偶", "藝術玩偶", "art doll", "artist doll"),
        "textile_plush": ("布艺", "布藝", "毛绒手作", "毛絨手作", "plush making", "textile craft"),
        "original_characters": ("独立角色", "獨立角色", "原创角色", "原創角色", "original character", "indie character"),
        "making_process": ("制作过程", "製作過程", "缝制", "縫製", "making process", "work in progress"),
        "doll_events": ("娃展", "玩偶展", "doll show", "doll fair"),
        "small_creator_business": ("小型创作者", "小型創作者", "独立创作者", "獨立創作者", "small creator", "independent creator"),
    }
    EXCLUDE_TERMS = {
        "beauty": ("美妆", "美妝", "护肤", "護膚", "beauty tutorial", "skincare"),
        "generic_ecommerce": ("泛电商", "爆单选品", "爆單選品", "dropshipping", "generic ecommerce"),
        "saas": ("saas", "企业软件", "企業軟體", "b2b software"),
        "celebrity_trends": ("明星热点", "明星熱點", "celebrity gossip", "fan war"),
    }
    PRODUCTION_TERMS = ("手工", "手作", "不织布", "不織布", "缝制", "縫製", "制作", "製作")
    DOLL_OBJECT_TERMS = ("娃娃", "玩偶")

    def __init__(self, scope: TrackScope):
        self.scope = scope
        self.include_lanes = {lane.casefold() for lane in scope.include}
        self.exclude_lanes = {lane.casefold() for lane in scope.exclude}
        self.portable_methods = {method.casefold() for method in scope.portable_methods}

    def evaluate(self, candidate: ContentCandidate) -> FilterResult:
        lane = candidate.declared_lane.casefold() if candidate.declared_lane else None

        if lane == "cross_track":
            return self._evaluate_cross_track(candidate)

        if lane in self.include_lanes:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.ACCEPTED,
                "declared_in_scope",
                f"declared lane {candidate.declared_lane!r} is in scope",
                (candidate.declared_lane or "",),
            )

        if lane in self.exclude_lanes:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.REJECTED,
                "declared_excluded",
                f"declared lane {candidate.declared_lane!r} is excluded",
                (candidate.declared_lane or "",),
            )

        include_matches = self._term_matches(candidate.searchable_text, self.INCLUDE_TERMS)
        exclude_matches = self._term_matches(candidate.searchable_text, self.EXCLUDE_TERMS)
        compound_matches = self._compound_making_object_matches(candidate.searchable_text)

        if include_matches:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.ACCEPTED,
                "matched_in_scope_terms",
                "candidate contains an in-scope handmade creator signal",
                include_matches,
            )

        if exclude_matches:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.REJECTED,
                "matched_excluded_terms",
                "candidate matches an excluded lane and has no in-scope signal",
                exclude_matches,
            )

        if compound_matches:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.ACCEPTED,
                "matched_compound_making_object_terms",
                "candidate contains both an approved making term and a doll/object term",
                compound_matches,
            )

        return FilterResult(
            candidate.candidate_id,
            FilterDecision.REVIEW,
            "insufficient_track_signal",
            "no reliable in-scope or excluded signal; hold for human review",
        )

    def _evaluate_cross_track(self, candidate: ContentCandidate) -> FilterResult:
        methods = {method.casefold() for method in candidate.migration_methods}
        allowed = tuple(sorted(methods & self.portable_methods))
        if self.scope.cross_track_requires_note and not candidate.migration_note:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.REJECTED,
                "cross_track_note_missing",
                "cross-track cases require a concrete migration note",
            )
        if not allowed:
            return FilterResult(
                candidate.candidate_id,
                FilterDecision.REJECTED,
                "cross_track_method_missing",
                "cross-track cases require at least one approved portable method",
                tuple(sorted(methods)),
            )
        return FilterResult(
            candidate.candidate_id,
            FilterDecision.ACCEPTED,
            "cross_track_migration_explicit",
            "cross-track case states how its expression method transfers to Gungun World",
            allowed,
        )

    @staticmethod
    def _term_matches(text: str, term_map: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
        matched: list[str] = []
        for lane, terms in term_map.items():
            if any(term.casefold() in text for term in terms):
                matched.append(lane)
        return tuple(matched)

    @classmethod
    def _compound_making_object_matches(cls, text: str) -> tuple[str, ...]:
        making = next((term for term in cls.PRODUCTION_TERMS if term.casefold() in text), None)
        object_term = next((term for term in cls.DOLL_OBJECT_TERMS if term.casefold() in text), None)
        if not making or not object_term:
            return ()
        return (f"making:{making}", f"object:{object_term}")
