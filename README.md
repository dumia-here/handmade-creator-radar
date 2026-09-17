# Handmade Creator Radar V0.1

Handmade Creator Radar turns a natural-language research brief into an auditable, safety-first comparison of public creator evidence across Bilibili and YouTube.

手作创作者雷达把自然语言调研任务转成可审计、重安全的跨平台公开证据比较；当前 V0.1 支持 Bilibili 与 YouTube。

## Project direction: from Radar to a long-term Creator Assistant

This repository began as Handmade Creator Radar, a bounded research module built from a real independent handmade creator workflow.

Since V0.1, the private system around it has grown into a broader experiment: one long-term assistant that can stay continuous with a creator, carry real work through specialized tools, and eventually accompany the creator into public-facing work through a physical StackChan body.

The public direction is to extract reusable, privacy-safe pieces of that system without pretending unfinished research is finished.

The project now has three pillars:

| Pillar | Status | Purpose |
| --- | --- | --- |
| **Self / Continuity** | **IN DEVELOPMENT** | Preserve the same assistant identity, working context, open loops, corrections, and useful long-term memory across chats, workspaces, model changes, and future surfaces. |
| **Hands / Action** | **RUNNABLE / TESTED** | Turn an agreed decision into real work through a durable queue, specialized worker, independent verification, and a receipt returned to the conversational layer. |
| **Embodiment / StackChan** | **EARLY BUILD / BLUEPRINT** | Let the same Adam eventually inhabit a physical body for exhibition reception, translation, bounded observation/recording, and post-event review without creating a second persona or memory system. |

See [`docs/CREATOR-ASSISTANT-ARCHITECTURE.md`](docs/CREATOR-ASSISTANT-ARCHITECTURE.md), [`docs/CONTINUITY-ROADMAP.md`](docs/CONTINUITY-ROADMAP.md), and [`docs/EMBODIMENT-BLUEPRINT.md`](docs/EMBODIMENT-BLUEPRINT.md).

## Why this is useful to an independent creator

A solo handmade creator is rarely doing only one job. The same person may be designing, making, photographing, planning releases, maintaining project systems, researching, posting to social platforms, preparing exhibitions, answering visitors, translating, documenting what happened, and remembering what still needs to be done.

The system is intended to divide that load without splitting the relationship into unrelated tools.

**At home / in the studio**, continuity is the center. The assistant should help carry creative context across days and weeks, maintain systems and commitments, support brainstorming and reflection, assist with research and planning, and help with social-platform maintenance without making the creator repeatedly reconstruct the same background.

**When real work must be executed**, Hands is the action layer. The conversational assistant can turn an agreed decision into an explicit task, dispatch it to a specialized worker such as Codex, verify the real result through readback or MCP, and receive a bounded receipt back into the same conversation.

**Outside the studio**, embodiment becomes useful. The same assistant should eventually help with exhibition reception, translation, guest-facing support, visible and consent-aware field recording, observations the creator cannot easily capture while busy, and post-event review.

The important claim is not "one AI can do everything." The important design choice is that these capabilities belong to the **same long-term assistant**, with explicit boundaries between memory, action, verification, and physical capability.

## Self / Continuity: active research

The continuity system is the core of the long-term assistant and is still under construction.

The active private architecture includes an Identity Kernel, a time-ordered Live Ledger, rolling open loops, durable frontdesk memory, domain truthbooks, boot/retrieval rules, commit rules, and promotion/supersession rules. The goal is not to save every conversation. It is to preserve what should remain true, expire what should not, surface gaps honestly, and keep corrections explicit.

This repository does **not** claim that perfect retrieval, automatic consolidation, proactive memory use, cross-runtime recovery, or long-horizon personality continuity is solved. Those are ongoing research areas.

Public extractions will use schemas, synthetic fixtures, replay tests, and privacy-safe examples rather than real personal memory.

See [`docs/CONTINUITY-ROADMAP.md`](docs/CONTINUITY-ROADMAP.md).

## First runnable public module: Creator Hands Bridge

The `creator-assistant-v0.2` branch contains the first runnable slice of the broader assistant: a conversational Frontdesk hands an explicit task to a durable queue, a registered worker performs real work, a verifier reads reality back, and a terminal receipt returns the result to the same action loop.

The queue seam has two implementations. `FileQueue` proves the loop locally. `DriveQueue` uses caller-owned Google Drive folders for queued/running/completed/failed state, while `GoogleDriveRestBackend` speaks the Drive v3 REST API with an injected OAuth token provider. Credentials and private folder IDs are not stored in this repository.

The worker seam includes `CodexCliWorker`. It runs explicit `codex exec` work inside the caller-owned workspace while runtime authority stays outside the task card: executable, argv, model, reasoning, sandbox, environment, and timeout cannot be overridden by the dispatched payload. Expected artifacts must exist after Codex exits, then `ExpectedArtifactsVerifier` independently re-reads and hashes them. A maintainer-local live smoke using existing ChatGPT-managed Codex authentication successfully created and verified a requested artifact.

The verifier seam also includes `ReadOnlyMcpVerifier`. It launches a caller-owned MCP server over stdio JSON-RPC and only calls `stat_path`, `sha256_file`, and `read_text_file`. A maintainer-local live smoke completed the real MCP handshake and tool calls, re-read a workspace artifact, matched its SHA-256 digest, and observed a clean child exit.

Terminal receipts now include a versioned `frontdesk_handoff`. It returns task identity, the agreed request and acceptance criteria, terminal outcome, artifacts, and verifier evidence to the conversational layer, plus bounded flags for whether completion may be claimed or Frontdesk review is still required. Arbitrary `task.payload` data is deliberately excluded from this handoff.

This remains a bounded public extraction, not a copy of the private production bridge. Live Drive OAuth smoke, distributed claim locking, production-grade containment, and complete execution provenance are not claimed here.

See [`docs/CREATOR-HANDS.md`](docs/CREATOR-HANDS.md). The focused tests run with:

```bash
PYTHONPATH=src python3 -m unittest tests.test_creator_hands tests.test_creator_hands_drive tests.test_creator_hands_codex tests.test_creator_hands_mcp tests.test_creator_hands_handoff
```

## Embodiment / StackChan: early build

The StackChan project is the public-facing body direction for the same Adam.

The architectural priority is **same-Adam inhabitation first**. The device should receive an already-authoritative assistant identity/session instead of booting a second persona, second memory store, or fallback brain. Voice, camera, motion, display, tracking, and other device functions are capabilities of the same assistant.

The long-term creator use case is field work: exhibition reception, multilingual support, bounded guest interaction, visible and consent-aware recording, observations from a machine perspective, creator-side reminders, and post-event review.

This layer is early. Existing protocol, transport, and device work does not mean same-Adam inhabitation is finished or production-ready.

See [`docs/EMBODIMENT-BLUEPRINT.md`](docs/EMBODIMENT-BLUEPRINT.md).

## Why model and API credits matter

Creator Hands demonstrates a working action loop. The heavier remaining research sits in Continuity and Embodiment.

Credits would support repeated evidence-producing experiments such as continuity across model/runtime changes, memory retrieval and supersession tests, recovery and regression suites, architecture review for privacy-safe memory mechanisms, same-Adam attachment work for StackChan, voice/perception/interaction experiments, simulator-first validation, and bounded real-device testing.

The goal is not simply more generations. The goal is to test whether a long-term assistant can remain coherent, auditable, privacy-bounded, and useful across months of creator work and across digital and physical surfaces.

## What this submission proves

- A strict track filter accepts a candidate only when a making term and a doll/object term appear together.
- Facts, inferences, and missing values remain separate; missing data is never treated as zero.
- A single viral post cannot decide a platform strategy.
- Ranking allows at most one `main` and one `experiment`, and refuses to force a winner when evidence is insufficient.
- Golden replay, three terminal workflow paths, and the full suite run offline with Python 3.9+ standard library only.
- Creator Hands provides a runnable, tested action-loop slice while the continuity and embodiment layers are explicitly documented as unfinished research.

## Three commands

```bash
python3 demo_v0_1.py
python3 demo_v0_1.py --workflow
python3 demo_v0_1.py --tests
```

The default command creates only temporary demo state, prints a path-free JSON summary, and removes that state automatically.

## Expected outcome

- Default: `preflight.status` is `ready`; source is `replay_golden`; both platforms remain `insufficient_evidence` in the first window.
- Workflow: success, confirmation/resume, and failure paths all reach explicit terminal states.
- Tests: all bundled tests pass without network access.

## Repository layout

```text
src/       radar implementation + Creator Hands action-loop slice
tests/     offline regression and safety tests
samples/   synthetic and golden replay data
schemas/   versioned task, evidence, and score schemas
docs/      architecture, continuity roadmap, embodiment blueprint, and disclosure boundaries
```

## Honest limits

- V0.1 connects only Bilibili and YouTube public-source probes.
- The bundled demo is replay data, never live evidence.
- The first observation window is insufficient for a long-term platform conclusion.
- No login, posting, upload, payment, private API, or account automation is included.
- This repository does not publish the private orchestration system, private creator memory, relationship history, credentials, personal paths, owner data, or private device configuration.
- Creator Hands v0.1 does not claim production-grade containment, distributed queue ownership, live Drive OAuth validation, universal MCP sandboxing, or complete execution provenance is solved.
- Continuity is active research, not a finished memory product.
- StackChan embodiment is an early build and blueprint, not a claim of finished same-Adam physical deployment.

## License and dependencies

MIT License. Runtime dependencies: none beyond Python 3.9+ standard library. Build tooling is optional and listed in `pyproject.toml`.
