# Build Week 录屏单 V1

目标成片：约 82 秒；画面只出现脱敏提交包，旁白使用英文。无需联网，也不要打开账号页面。

## 录屏前一次性准备

1. 在 Finder 中进入 `radar-v0.1-submission-v1`，从该文件夹打开一个新的终端窗口。
2. 把终端字体调到至少 18 pt，窗口设为约 16:9；隐藏标签栏、侧边栏和终端标题中的完整路径。
3. 在终端执行以下两行，隐藏用户名提示符并清屏：

```bash
export PS1='$ '
clear
```

4. 关闭通知预览、邮件、聊天软件和云盘同步弹窗。
5. 不执行 `pwd`、`ls -la` 或任何会显示本机路径的命令。
6. 先完整跑一次下面三个演示命令；只有都成功才开始录制。

```bash
python3 demo_v0_1.py
python3 demo_v0_1.py --workflow
python3 demo_v0_1.py --tests
```

## 分秒镜头表与英文旁白／字幕

| 时间 | 画面与操作 | 应出现的安全输出 | 英文旁白或字幕 |
|---|---|---|---|
| 0–7s | 打开 `README.md` 顶部，只显示项目名与一句话说明。 | `Handmade Creator Radar V0.1` | “Handmade Creator Radar turns a natural-language brief into an auditable cross-platform evidence decision for independent handmade creators.” |
| 7–18s | 打开 `tests/test_filter.py`，框选组合门的正例、制作词缺对象词、对象词缺制作词三项测试名；不要展示编辑器侧边栏。 | 三类边界测试名 | “The track gate is intentionally narrow: a making term and a doll or toy term must appear together. Generic craft content is not accepted.” |
| 18–39s | 回到干净终端，输入并运行 `python3 demo_v0_1.py`。停在 JSON 输出。 | `preflight`=`ready`、`source_kind`=`replay_golden`、accepted/review/rejected 计数 | “The default demo is offline and reproducible. Replay evidence is labeled explicitly, facts stay separate from inference and missing data, and both platforms remain insufficient in the first window.” |
| 39–56s | 清屏，运行 `python3 demo_v0_1.py --workflow`。 | `all_paths_terminal`=`true`；completed、confirmation/resume、failed | “The workflow gives success, human confirmation and resume, and failure their own terminal states. Human approval never relaxes the safety rules.” |
| 56–70s | 清屏，运行 `python3 demo_v0_1.py --tests`。 | `status`=`passed`、`test_count`=`58` | “Fifty-eight offline tests cover filtering, evidence, scoring, public-probe safety, idempotency, recovery, and privacy boundaries.” |
| 70–82s | 打开 README 的 `Honest limits` 段落，缓慢框选前 3 条。 | two platforms、replay not live、one window insufficient | “V0.1 connects Bilibili and YouTube only. Long-term trends need another observation window. The system would rather say ‘not enough evidence’ than invent confidence.” |

## 剪辑检查

- 总时长控制在 60–90 秒，建议保留 2 秒片头、78 秒主体、2 秒片尾。
- 命令可提前输入后再开始录屏，但不要伪造输出或剪掉失败后重跑的痕迹；失败就停止并重新录一遍。
- 英文旁白来不及录时，直接把上表英文逐段做成字幕；背景音乐不是必需品。
- 画面中不得出现用户名、邮箱、Finder 侧栏、完整本机路径、云盘名称、通知地址、设备 Key、私有编排系统目录、真实任务卡、回执或真实报告。
- 不打开 Bilibili、YouTube、GitHub、Devpost 或 Codex 账号页面；录屏只证明离线包可复现。

## 3:2 英文封面图需求

- 画布：1800 × 1200 px，3:2。
- 主标题：`Handmade Creator Radar`。
- 副标题：`Evidence before platform hype`。
- 三个短标签：`Bilibili + YouTube`、`Safety-first`、`58 offline tests`。
- 视觉：深蓝或炭黑背景，中央用两列简化卡片汇入一个清晰的 `insufficient evidence` 判定；不要使用平台商标，只用纯文字标签。
- 禁止内容：人物账号头像、真实视频缩略图、浏览器账号栏、用户名、邮箱、路径、Drive、通知地址、私有编排系统画面。

### 不为美术延误的安全截图方法

若没有时间制作封面，使用默认演示的安全终端输出即可：隐藏终端标题和提示符路径，执行 `python3 demo_v0_1.py`，只截取 JSON 中的 `ready`、`replay_golden`、两平台 `insufficient_evidence` 与三类候选计数；在系统截图工具中裁成 3:2，再加上英文主标题。截图前后都不要显示 `pwd` 或 Finder 侧栏。

## 录完后的唯一人工检查

从头播放一次，逐帧确认没有私人路径或通知弹窗；确认无误后再进入下一单的上传步骤。本单不上传视频。
