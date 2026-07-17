# 平台评分五组回放结果 V0.1

生成方式：读取 `evidence-replay.v0.1.json`，逐组调用 `score_platform`，再统一调用 `rank_platforms`。全程只使用稳定回放样本，无网络访问。

| 回放组 | 平台 | 总分 | 总置信度 | 层级 | 结论与理由 |
|---|---|---:|---:|---|---|
| 多创作者、多窗口 | xiaohongshu | 76.33 | 0.684 | main | 3 位独立创作者、2 个窗口且六项信号齐全，通过证据门槛。 |
| 单条爆款 | instagram | 85.83 | 0.716 | insufficient_evidence | 只有 1 位创作者、1 条内容、1 个窗口；高表现贡献已封顶并标记 `outlier_capped`，必须确认。 |
| 正反证据冲突 | youtube | 66.83 | 0.631 | observe | 创作者密度同时出现 82 与 20，保留 `conflicting_evidence`，该信号置信度降至 0.437，必须确认。 |
| 大量缺失 | pinterest | 60.00 | 0.025 | insufficient_evidence | 5 个显式缺失项未按 0 计分，也不帮助通过证据门槛；仅内容寿命可计分，必须确认。 |
| 高维护成本 | tiktok | 68.33 | 0.679 | experiment | 其余五项强，但维护成本 95 按负向项只得 5 分，总分被拉低。 |

层级计数：`main=1`、`experiment=1`、`observe=1`、`insufficient_evidence=2`。需要人工确认：单条爆款、正反冲突、大量缺失三组。
