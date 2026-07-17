from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .contract import Platform, ProbeMode, ProbeRequest, RadarTask, SafetyPolicy, TrackScope
from .evidence import EvidenceItem, SignalName, StatementKind
from .filter import FilterDecision, TrackFilter
from .probes import ProbeRegistry
from .public_probes import (
    BILIBILI_HOSTS,
    YOUTUBE_HOSTS,
    BilibiliPublicProbe,
    LiveContentCandidate,
    ProbeDiagnostics,
    SafePublicHttpClient,
    YouTubePublicProbe,
)
from .scoring import PlatformScore, rank_platforms, score_platform


BILIBILI_QUERIES = ("手作娃娃", "艺术玩偶", "毛绒制作过程", "独立角色")
YOUTUBE_QUERIES = ("handmade doll", "art doll making", "plush making", "indie character")
WINDOW = "live-window-001"


@dataclass(frozen=True)
class PlatformRun:
    platform: Platform
    queries: tuple[str, ...]
    candidates: tuple[LiveContentCandidate, ...]
    accepted: tuple[LiveContentCandidate, ...]
    filter_rows: tuple[dict[str, str], ...]
    evidence: tuple[EvidenceItem, ...]
    diagnostics: ProbeDiagnostics
    score: PlatformScore


def default_task() -> RadarTask:
    return RadarTask(
        task_id="live-baseline-window-001",
        title="Bilibili and YouTube public baseline window 001",
        probes=(
            ProbeRequest(Platform.BILIBILI, ProbeMode.PUBLIC, "zh-CN", BILIBILI_QUERIES),
            ProbeRequest(Platform.YOUTUBE, ProbeMode.PUBLIC, "en", YOUTUBE_QUERIES),
        ),
        track_scope=TrackScope(
            include=("handmade_dolls", "art_dolls", "textile_plush", "original_characters", "making_process", "doll_events", "small_creator_business"),
            exclude=("beauty", "generic_ecommerce", "saas", "celebrity_trends"),
            portable_methods=("hook", "shot_structure", "result_reveal", "hands_in_frame", "voiceover", "search_lifecycle"),
        ),
        safety=SafetyPolicy(),
        observation_signals=tuple(signal.value for signal in SignalName),
    )


def build_live_evidence(
    platform: Platform,
    candidates: Iterable[LiveContentCandidate],
    accepted_ids: set[str],
) -> tuple[EvidenceItem, ...]:
    live = tuple(
        item for item in candidates
        if item.source_kind == "live_public" and item.candidate_id in accepted_ids
    )[:10]
    if not live:
        return ()
    anchor = live[0]
    observed_at = max(item.fetched_at for item in live)
    source_url = anchor.source_url or anchor.url or "https://example.invalid/missing-source"
    creator_id = anchor.creator_id or anchor.creator_name or "creator-unavailable"
    ratio = min(100.0, len(live) / max(1, len(tuple(candidates))) * 100.0)
    items: list[EvidenceItem] = []

    def add(
        evidence_id: str,
        signal: SignalName,
        kind: StatementKind,
        value: float | None,
        *,
        confidence: float,
        directness: float,
        notes: str,
    ) -> None:
        items.append(EvidenceItem(
            evidence_id=evidence_id,
            platform=platform,
            candidate_id=anchor.candidate_id,
            creator_id=creator_id,
            source_url=source_url,
            observed_at=observed_at,
            observation_window=WINDOW,
            source_type="live_public",
            signal=signal,
            value=value,
            statement_kind=kind,
            directness=directness,
            freshness=1.0,
            confidence=confidence,
            notes=notes,
        ))

    add("live-density-" + platform.value, SignalName.RELEVANT_CREATOR_DENSITY, StatementKind.INFERENCE, ratio, confidence=0.45, directness=0.55, notes="accepted live candidates divided by parsed live candidates")
    add("live-growth-" + platform.value, SignalName.SMALL_ACCOUNT_RELATIVE_GROWTH, StatementKind.MISSING, None, confidence=0.0, directness=0.0, notes="requires at least two observation windows")

    engagement_values: list[float] = []
    for item in live:
        metrics = item.metrics
        if metrics.get("views", 0) > 0 and "comments" in metrics:
            engagement_values.append(min(100.0, metrics["comments"] / metrics["views"] * 10_000.0))
    if engagement_values:
        add("live-engagement-" + platform.value, SignalName.STRANGER_ENGAGEMENT, StatementKind.INFERENCE, sum(engagement_values) / len(engagement_values), confidence=0.4, directness=0.55, notes="comments-to-views ratio from public facts; stranger identity is not observable")
    else:
        add("live-engagement-" + platform.value, SignalName.STRANGER_ENGAGEMENT, StatementKind.MISSING, None, confidence=0.0, directness=0.0, notes="public comments and views were not both visible")
    add("live-lifetime-" + platform.value, SignalName.CONTENT_LIFETIME, StatementKind.MISSING, None, confidence=0.0, directness=0.0, notes="one window cannot establish content lifetime")
    add("live-fit-" + platform.value, SignalName.EXPRESSION_FIT, StatementKind.INFERENCE, min(85.0, 60.0 + ratio * 0.25), confidence=0.5, directness=0.6, notes="derived only from TrackFilter accepted public title and description")
    maintenance = 45.0 if platform == Platform.BILIBILI else 55.0
    add("live-cost-" + platform.value, SignalName.MAINTENANCE_COST, StatementKind.INFERENCE, maintenance, confidence=0.3, directness=0.3, notes="operational inference, not a platform page field")
    return tuple(items)


def run_live_scan(
    *,
    bilibili_smoke_urls: Iterable[str] = (),
    youtube_smoke_urls: Iterable[str] = (),
) -> tuple[PlatformRun, ...]:
    task = default_task()
    probes = {
        Platform.BILIBILI: BilibiliPublicProbe(SafePublicHttpClient(BILIBILI_HOSTS), smoke_urls=bilibili_smoke_urls),
        Platform.YOUTUBE: YouTubePublicProbe(SafePublicHttpClient(YOUTUBE_HOSTS), smoke_urls=youtube_smoke_urls),
    }
    registry = ProbeRegistry()
    for probe in probes.values():
        registry.register(probe)
    track_filter = TrackFilter(task.track_scope)
    preliminary: list[tuple[Platform, tuple[str, ...], tuple[LiveContentCandidate, ...], tuple[LiveContentCandidate, ...], tuple[dict[str, str], ...], tuple[EvidenceItem, ...], ProbeDiagnostics, PlatformScore]] = []
    for request, batch in zip(task.probes, registry.dispatch(task)):
        candidates = tuple(item for item in batch.candidates if isinstance(item, LiveContentCandidate))
        rows: list[dict[str, str]] = []
        accepted: list[LiveContentCandidate] = []
        for candidate in candidates:
            result = track_filter.evaluate(candidate)
            rows.append({
                "candidate_id": candidate.candidate_id,
                "decision": result.decision.value,
                "reason_code": result.reason_code,
                "reason": result.reason,
            })
            if result.decision == FilterDecision.ACCEPTED and len(accepted) < 10:
                accepted.append(candidate)
        accepted_ids = {item.candidate_id for item in accepted}
        evidence = build_live_evidence(request.platform, candidates, accepted_ids)
        score = score_platform(request.platform, evidence, accepted_candidate_ids=accepted_ids)
        preliminary.append((request.platform, request.queries, candidates, tuple(accepted), tuple(rows), evidence, probes[request.platform].last_diagnostics, score))
    ranked = {item.platform: item for item in rank_platforms(item[-1] for item in preliminary)}
    return tuple(PlatformRun(*item[:-1], ranked[item[0]]) for item in preliminary)


def overall_status(runs: Iterable[PlatformRun]) -> str:
    return "completed" if all(run.accepted for run in runs) else "needs_confirmation"


def render_report(runs: tuple[PlatformRun, ...], scanned_at: str) -> str:
    status = overall_status(runs)
    lines = [
        "# 跨平台手作创作者雷达｜真实基线 Window 001",
        "",
        f"- 扫描时间：{scanned_at}",
        f"- 任务状态：`{status}`",
        "- 来源模式：`live_public`；回放夹具未计入本报告",
        "- 安全边界：仅 HTTPS 官方白名单；未登录、未读取 Cookie、未下载媒体、未执行页面文字指令",
        "- 结论边界：**只有第一观察窗口，尚不能判断迁徙趋势。**",
        "",
        "## 平台扫描概览",
        "",
        "| 平台 | 关键词 | 搜索页 | 搜索候选 | 详情读取 | 解析候选 | 赛道通过 | 待复核 | 排除 | 层级 | 置信度 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for run in runs:
        counts = {decision.value: sum(row["decision"] == decision.value for row in run.filter_rows) for decision in FilterDecision}
        d = run.diagnostics
        lines.append(
            f"| {run.platform.value} | {'、'.join(run.queries)} | {d.search_pages_read} | {d.search_candidates_found} | {d.detail_pages_read} | {d.parsed_candidates} | {counts['accepted']} | {counts['review']} | {counts['rejected']} | {run.score.tier} | {run.score.confidence:.3f} |"
        )

    for run in runs:
        lines.extend(["", f"## {run.platform.value}", "", "### 真实候选与赛道门", ""])
        if not run.candidates:
            lines.append("- 未取得可解析的真实候选。")
        for candidate in run.candidates:
            row = next(item for item in run.filter_rows if item["candidate_id"] == candidate.candidate_id)
            metrics = ", ".join(f"{key}={value}" for key, value in candidate.public_metrics) or "无可见数值"
            missing = ", ".join(candidate.missing_fields) or "无"
            lines.append(f"- [{candidate.title}]({candidate.source_url}) — `{row['decision']}` / `{row['reason_code']}`；creator={candidate.creator_name or '缺失'}；published_at={candidate.published_at or '缺失'}；metrics={metrics}；missing={missing}；fetched_at={candidate.fetched_at}")
        lines.extend(["", "### HTTP／解析状态", ""])
        if run.diagnostics.errors:
            lines.extend(f"- `{error}`" for error in run.diagnostics.errors)
        else:
            lines.append("- 无 HTTP／解析异常。")
        lines.extend(["", "### 证据分栏", ""])
        for kind in StatementKind:
            selected = [item for item in run.evidence if item.statement_kind == kind]
            lines.append(f"- {kind.value}: " + ("；".join(f"{item.signal.value}={item.value if item.value is not None else 'missing'} ({item.notes})" for item in selected) or "无"))
        lines.extend(["", "### 六项信号与层级", ""])
        for signal in run.score.signals:
            lines.append(f"- `{signal.signal.value}`：score={signal.score if signal.score is not None else 'missing'}，confidence={signal.confidence:.3f}，evidence={signal.evidence_count}，missing={signal.missing_count}，reason={','.join(signal.reasons)}")
        lines.append(f"- 平台层级：`{run.score.tier}`；总分={run.score.score if run.score.score is not None else 'missing'}；总置信度={run.score.confidence:.3f}；needs_confirmation={str(run.score.needs_confirmation).lower()}。第一窗口不产生 main／experiment。")

    next_window = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()
    lines.extend([
        "",
        "## 可迁移内容做法",
        "",
        "1. 用 2 秒成品特写开场，再回到手部制作过程，形成结果倒叙。",
        "2. 固定同一机位记录材料到角色成形，减少重拍并利于跨窗口比较。",
        "3. 用角色名与一个鲜明动作做连续标题，让独立角色形成可追踪系列。",
        "",
        "## 当前制作现场可拍选题",
        "",
        "1. 麻到功：一团材料怎样长出标志性表情，突出针脚和表情转折。",
        "2. 多耳滚：多只耳朵的翻面与定位过程，用俯拍表现结构难点。",
        "3. 笑天犬：笑脸从纸样到立体成形，做一次成品／制作中的对照揭晓。",
        "",
        "## 本周低成本脚本",
        "",
        "- 0–2 秒：现有成品近景，字幕“它最难做的不是脸”。",
        "- 2–10 秒：直接使用当前工作台的三段手部素材：定位、缝合、翻面。",
        "- 10–15 秒：成品回到同一机位，字幕点出一个结构选择；无需补拍环境或口播。",
        "",
        "## 下一窗口",
        "",
        f"- 建议时间：{next_window}（约 7 天后）。",
        "- 需要累积：同候选的播放／点赞／评论公开值、发布时间、再次抓取时间、是否仍可发现、创作者公开标识；缺失继续记 missing，不记 0。",
        "- 只有跨至少两个观察窗口后，才评估相对增长、内容寿命与迁徙趋势。",
    ])
    if status != "completed":
        missing_platforms = "、".join(run.platform.value for run in runs if not run.accepted)
        lines.extend(["", "## 需要确认", "", f"- {missing_platforms} 未取得至少一条真实且赛道通过的候选。请确认是否允许下一步采用最小依赖的公开元数据解析方案；不需要账号或密码。"])
    return "\n".join(lines) + "\n"


def unique_report_path(requested: Path) -> Path:
    if not requested.exists():
        return requested
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return requested.with_name(f"{requested.stem}-{stamp}{requested.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bilibili and YouTube public baseline window 001")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bilibili-smoke-url", action="append", default=[])
    parser.add_argument("--youtube-smoke-url", action="append", default=[])
    args = parser.parse_args()
    output = unique_report_path(args.output)
    if not output.parent.is_dir():
        raise SystemExit("report parent directory does not exist")
    runs = run_live_scan(bilibili_smoke_urls=args.bilibili_smoke_url, youtube_smoke_urls=args.youtube_smoke_url)
    scanned_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    output.write_text(render_report(runs, scanned_at), encoding="utf-8")
    status = overall_status(runs)
    print(json.dumps({"status": status, "output": str(output), "platforms": {run.platform.value: len(run.accepted) for run in runs}}, ensure_ascii=False))
    return 0 if status == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
