from __future__ import annotations

from typing import Any, Mapping

from .contract import RadarTask


class LegacyXiaohongshuTaskAdapter:
    """Lift a legacy Xiaohongshu-only task without rebuilding its probe."""

    @staticmethod
    def adapt(raw: Mapping[str, Any]) -> RadarTask:
        queries = raw.get("queries") or raw.get("keywords") or ["手作娃娃", "艺术玩偶"]
        lifted = {
            "schema_version": "radar.task.v0.1",
            "task_id": raw.get("task_id", "legacy-xhs-task"),
            "title": raw.get("title", "小红书巡店兼容任务"),
            "probes": [
                {
                    "platform": "xiaohongshu",
                    "mode": raw.get("mode", "public"),
                    "locale": raw.get("locale", "zh-CN"),
                    "queries": queries,
                }
            ],
            "track_scope": raw.get("track_scope") or _default_track_scope(),
            "safety": raw.get("safety")
            or {
                "read_only": True,
                "forbidden_actions": [
                    "delete",
                    "overwrite",
                    "send",
                    "publish",
                    "share",
                    "pay",
                    "contact_external",
                    "reply",
                ],
            },
            "observation_signals": raw.get("observation_signals", []),
            "acceptance_criteria": raw.get("acceptance_criteria", []),
            "deliverables": raw.get("deliverables", []),
        }
        return RadarTask.from_dict(lifted)


def _default_track_scope() -> dict[str, Any]:
    return {
        "include": [
            "handmade_dolls",
            "art_dolls",
            "textile_plush",
            "original_characters",
            "making_process",
            "doll_events",
            "small_creator_business",
        ],
        "exclude": ["beauty", "generic_ecommerce", "saas", "celebrity_trends"],
        "portable_methods": [
            "hook",
            "shot_structure",
            "result_reveal",
            "hands_in_frame",
            "voiceover",
            "search_lifecycle",
        ],
        "cross_track_requires_note": True,
    }
