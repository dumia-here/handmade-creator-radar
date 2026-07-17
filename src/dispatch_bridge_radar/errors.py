from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    NETWORK_TIMEOUT = "network_timeout"
    HTTP_STATUS_ERROR = "http_status_error"
    RATE_LIMITED = "rate_limited"
    UNSAFE_REDIRECT = "unsafe_redirect"
    RESPONSE_TOO_LARGE = "response_too_large"
    PARSE_ERROR = "parse_error"
    NO_CANDIDATES = "no_candidates"
    ALL_CANDIDATES_FILTERED = "all_candidates_filtered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    OUTPUT_ALREADY_EXISTS = "output_already_exists"
    UNSAFE_ACTION_REJECTED = "unsafe_action_rejected"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class _ErrorSpec:
    summary: str
    retryable: bool
    next_step: str


ERROR_SPECS = {
    ErrorCode.NETWORK_TIMEOUT: _ErrorSpec("public source timed out after limited retries", True, "retry the same read-only task later"),
    ErrorCode.HTTP_STATUS_ERROR: _ErrorSpec("public source returned an unsuccessful HTTP status", True, "retry later or confirm another allowlisted public source"),
    ErrorCode.RATE_LIMITED: _ErrorSpec("public source rate limit was reached", True, "wait before retrying without increasing request volume"),
    ErrorCode.UNSAFE_REDIRECT: _ErrorSpec("redirect target was outside the approved host allowlist", False, "confirm a different official public URL"),
    ErrorCode.RESPONSE_TOO_LARGE: _ErrorSpec("public response exceeded the configured size limit", False, "use a smaller official metadata page or approve a bounded parser change"),
    ErrorCode.PARSE_ERROR: _ErrorSpec("allowed public metadata could not be parsed", True, "inspect the frozen structure and make a bounded parser fix"),
    ErrorCode.NO_CANDIDATES: _ErrorSpec("the approved discovery source returned no candidates", True, "retry later or provide an allowlisted smoke URL"),
    ErrorCode.ALL_CANDIDATES_FILTERED: _ErrorSpec("all candidates were held or rejected by the track gate", False, "review reason codes before approving any minimal rule change"),
    ErrorCode.INSUFFICIENT_EVIDENCE: _ErrorSpec("the report is honest but evidence is below the task acceptance threshold", True, "collect the next observation window or confirm delivery as insufficient evidence"),
    ErrorCode.OUTPUT_ALREADY_EXISTS: _ErrorSpec("the requested output already exists and was not overwritten", False, "use a new versioned output path"),
    ErrorCode.UNSAFE_ACTION_REJECTED: _ErrorSpec("the requested action conflicts with the global safety boundary", False, "remove the unsafe action; global safety cannot be relaxed"),
    ErrorCode.INTERNAL_ERROR: _ErrorSpec("an internal offline step failed", True, "inspect the local traceback outside the user-facing receipt and fix the code"),
}


@dataclass(frozen=True)
class ErrorReceipt:
    task_id: str
    stage: str
    platform: str | None
    reason_code: ErrorCode
    occurred_at: str
    summary: str
    retryable: bool
    next_step: str
    preserved_outputs: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        task_id: str,
        stage: str,
        reason_code: ErrorCode,
        occurred_at: str,
        platform: str | None = None,
        preserved_outputs: tuple[str, ...] = (),
    ) -> "ErrorReceipt":
        spec = ERROR_SPECS[reason_code]
        return cls(task_id, stage, platform, reason_code, occurred_at, spec.summary, spec.retryable, spec.next_step, preserved_outputs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "radar.error-receipt.v0.1",
            "task_id": self.task_id,
            "stage": self.stage,
            "platform": self.platform,
            "reason_code": self.reason_code.value,
            "occurred_at": self.occurred_at,
            "summary": self.summary,
            "retryable": self.retryable,
            "next_step": self.next_step,
            "preserved_outputs": list(self.preserved_outputs),
        }


def task_route_for_error(code: ErrorCode, *, acceptance_requires_sufficient: bool = True) -> str:
    if code in {ErrorCode.NO_CANDIDATES, ErrorCode.ALL_CANDIDATES_FILTERED}:
        return "needs_confirmation"
    if code == ErrorCode.INSUFFICIENT_EVIDENCE:
        return "needs_confirmation" if acceptance_requires_sufficient else "completed"
    return "failed"
