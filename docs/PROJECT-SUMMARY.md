# Project summary

## English

Handmade Creator Radar V0.1 is a safety-first research module for comparing public creator evidence across Bilibili and YouTube. It converts a natural-language brief into a versioned task contract, filters for the intended handmade-doll track, keeps facts separate from inference and missing data, and produces conservative platform tiers. Its offline golden replay and terminal-path demo make the system reproducible without credentials or network access.

## 中文

手作创作者雷达 V0.1 是一个重安全的跨平台公开证据研究模块，面向 Bilibili 与 YouTube。它把自然语言需求转成版本化任务契约，通过“制作词 + 娃娃对象词”的组合门筛选赛道，严格区分事实、推断与缺失值，并输出保守的平台层级结论。离线 golden replay 与终态工作流演示无需凭证或网络即可复现。

## Highlights

1. Conservative filtering with positive, negative, and false-positive regressions.
2. Auditable evidence semantics: fact, inference, and missing never collapse together.
3. Anti-viral-bias scoring and non-forced ranking.
4. Safe terminal paths for completion, confirmation/resume, and failure.
5. Reproducible offline demo with zero runtime dependencies.

## Real limitations

- Two platforms only.
- Replay evidence is not presented as live evidence.
- One observation window cannot establish a long-term trend.
- No external posting, private data collection, or account automation.
