from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class _StringEnum(str, Enum):
    """String enum compatible with the Mac bridge's system Python 3.9."""

    def __str__(self) -> str:
        return self.value


class Platform(_StringEnum):
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    WEIBO = "weibo"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    PINTEREST = "pinterest"


class ProbeMode(_StringEnum):
    PUBLIC = "public"
    AUTHORIZED_IMPORT = "authorized_import"
    REPLAY = "replay"


@dataclass(frozen=True)
class ProbeRequest:
    platform: Platform
    mode: ProbeMode = ProbeMode.PUBLIC
    locale: str | None = None
    queries: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ProbeRequest":
        queries = tuple(_nonempty_strings(raw.get("queries", []), "queries"))
        return cls(
            platform=Platform(raw["platform"]),
            mode=ProbeMode(raw.get("mode", ProbeMode.PUBLIC)),
            locale=_optional_string(raw.get("locale"), "locale"),
            queries=queries,
        )


@dataclass(frozen=True)
class TrackScope:
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    portable_methods: tuple[str, ...]
    cross_track_requires_note: bool = True

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "TrackScope":
        include = tuple(_nonempty_strings(raw.get("include", []), "track_scope.include"))
        exclude = tuple(_nonempty_strings(raw.get("exclude", []), "track_scope.exclude"))
        portable = tuple(
            _nonempty_strings(raw.get("portable_methods", []), "track_scope.portable_methods")
        )
        if not include:
            raise ValueError("track_scope.include must contain at least one lane")
        if not exclude:
            raise ValueError("track_scope.exclude must contain at least one lane")
        return cls(
            include=include,
            exclude=exclude,
            portable_methods=portable,
            cross_track_requires_note=bool(raw.get("cross_track_requires_note", True)),
        )


@dataclass(frozen=True)
class SafetyPolicy:
    read_only: bool = True
    forbidden_actions: tuple[str, ...] = (
        "delete",
        "overwrite",
        "send",
        "publish",
        "share",
        "pay",
        "contact_external",
        "reply",
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> "SafetyPolicy":
        raw = raw or {}
        policy = cls(
            read_only=bool(raw.get("read_only", True)),
            forbidden_actions=tuple(
                _nonempty_strings(raw.get("forbidden_actions", cls.forbidden_actions), "forbidden_actions")
            ),
        )
        if not policy.read_only:
            raise ValueError("radar.task.v0.1 only supports read-only tasks")
        return policy


@dataclass(frozen=True)
class RadarTask:
    task_id: str
    title: str
    probes: tuple[ProbeRequest, ...]
    track_scope: TrackScope
    safety: SafetyPolicy = field(default_factory=SafetyPolicy)
    observation_signals: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    deliverables: tuple[str, ...] = ()
    schema_version: str = "radar.task.v0.1"

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RadarTask":
        version = raw.get("schema_version")
        if version != "radar.task.v0.1":
            raise ValueError(f"unsupported schema_version: {version!r}")
        probes = tuple(ProbeRequest.from_dict(item) for item in raw.get("probes", []))
        if not probes:
            raise ValueError("probes must contain at least one platform request")
        platforms = [probe.platform for probe in probes]
        if len(platforms) != len(set(platforms)):
            raise ValueError("each platform may appear only once in probes")
        return cls(
            task_id=_required_string(raw.get("task_id"), "task_id"),
            title=_required_string(raw.get("title"), "title"),
            probes=probes,
            track_scope=TrackScope.from_dict(raw.get("track_scope", {})),
            safety=SafetyPolicy.from_dict(raw.get("safety")),
            observation_signals=tuple(
                _nonempty_strings(raw.get("observation_signals", []), "observation_signals")
            ),
            acceptance_criteria=tuple(
                _nonempty_strings(raw.get("acceptance_criteria", []), "acceptance_criteria")
            ),
            deliverables=tuple(_nonempty_strings(raw.get("deliverables", []), "deliverables")),
            schema_version=version,
        )


@dataclass(frozen=True)
class ContentCandidate:
    candidate_id: str
    platform: Platform
    title: str
    description: str = ""
    creator: str | None = None
    url: str | None = None
    declared_lane: str | None = None
    tags: tuple[str, ...] = ()
    migration_note: str | None = None
    migration_methods: tuple[str, ...] = ()
    source_kind: str = "replay"

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ContentCandidate":
        return cls(
            candidate_id=_required_string(raw.get("candidate_id"), "candidate_id"),
            platform=Platform(raw["platform"]),
            title=_required_string(raw.get("title"), "title"),
            description=str(raw.get("description", "")).strip(),
            creator=_optional_string(raw.get("creator"), "creator"),
            url=_optional_string(raw.get("url"), "url"),
            declared_lane=_optional_string(raw.get("declared_lane"), "declared_lane"),
            tags=tuple(_nonempty_strings(raw.get("tags", []), "tags")),
            migration_note=_optional_string(raw.get("migration_note"), "migration_note"),
            migration_methods=tuple(
                _nonempty_strings(raw.get("migration_methods", []), "migration_methods")
            ),
            source_kind=str(raw.get("source_kind", "replay")).strip() or "replay",
        )

    @property
    def searchable_text(self) -> str:
        return " ".join((self.title, self.description, *self.tags)).casefold()


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


def _nonempty_strings(values: Sequence[Any], field_name: str) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{field_name} must be an array of strings")
    output: list[str] = []
    for value in values:
        output.append(_required_string(value, field_name))
    return output
