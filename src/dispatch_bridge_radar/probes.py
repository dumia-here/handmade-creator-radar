from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from .contract import ContentCandidate, Platform, ProbeRequest, RadarTask


@dataclass(frozen=True)
class ProbeBatch:
    platform: Platform
    source_kind: str
    candidates: tuple[ContentCandidate, ...]


class PlatformProbe(Protocol):
    platform: Platform

    def scan(self, request: ProbeRequest, task: RadarTask) -> ProbeBatch:
        """Return candidates only; filtering and later scoring stay platform-neutral."""


class ProbeRegistry:
    def __init__(self) -> None:
        self._probes: dict[Platform, PlatformProbe] = {}

    def register(self, probe: PlatformProbe, *, replace: bool = False) -> None:
        if probe.platform in self._probes and not replace:
            raise ValueError(f"probe already registered for {probe.platform}")
        self._probes[probe.platform] = probe

    def get(self, platform: Platform) -> PlatformProbe:
        try:
            return self._probes[platform]
        except KeyError as exc:
            raise LookupError(f"no probe registered for {platform}") from exc

    def dispatch(self, task: RadarTask) -> tuple[ProbeBatch, ...]:
        return tuple(self.get(request.platform).scan(request, task) for request in task.probes)


class ReplayProbe:
    def __init__(self, platform: Platform, candidates: Iterable[ContentCandidate]):
        self.platform = platform
        self._candidates = tuple(item for item in candidates if item.platform == platform)

    def scan(self, request: ProbeRequest, task: RadarTask) -> ProbeBatch:
        if request.platform != self.platform:
            raise ValueError("probe request platform does not match replay probe")
        return ProbeBatch(
            platform=self.platform,
            source_kind="replay",
            candidates=self._candidates,
        )

