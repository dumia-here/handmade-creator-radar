# Handmade Creator Radar V0.1

Handmade Creator Radar turns a natural-language research brief into an auditable, safety-first comparison of public creator evidence across Bilibili and YouTube.

手作创作者雷达把自然语言调研任务转成可审计、重安全的跨平台公开证据比较；当前 V0.1 支持 Bilibili 与 YouTube。

## Project direction: from Radar to a Creator Assistant

This repository began as Handmade Creator Radar, a bounded research module built from a real independent handmade creator workflow.

Since V0.1, the private system around it has evolved beyond external research into task dispatch and handoff, continuity and memory, embodied-assistant interfaces, and bounded autonomous actions.

The public direction is to gradually extract reusable, privacy-safe parts of that work into an open modular digital assistant for independent handmade creators: research, planning, publishing, exhibition support, and optional embodied interfaces.

V0.1 remains intact as the project’s origin. Personal memory, private creator data, credentials, and the private orchestration system are not part of this repository. New public modules will only be added when they can stand alone with tests, clear boundaries, and no dependency on private data.

## First extracted module: Creator Hands Bridge

The `creator-assistant-v0.2` branch contains the first runnable slice of the broader assistant: a conversational Frontdesk hands an explicit task to a durable queue, a registered worker performs real work, a verifier reads reality back, and a terminal receipt returns the result to the same action loop.

The queue seam has two implementations. `FileQueue` proves the loop locally. `DriveQueue` uses caller-owned Google Drive folders for queued/running/completed/failed state, while `GoogleDriveRestBackend` speaks the Drive v3 REST API with an injected OAuth token provider. Credentials and private folder IDs are not stored in this repository.

The worker seam includes `CodexCliWorker`. It runs explicit `codex exec` work inside the caller-owned workspace while runtime authority stays outside the task card: executable, argv, model, reasoning, sandbox, environment, and timeout cannot be overridden by the dispatched payload. Expected artifacts must exist after Codex exits, then `ExpectedArtifactsVerifier` independently re-reads and hashes them. A maintainer-local live smoke using existing ChatGPT-managed Codex authentication successfully created and verified a requested artifact.

The verifier seam now also includes `ReadOnlyMcpVerifier`. It launches a caller-owned MCP server over stdio JSON-RPC and only calls `stat_path`, `sha256_file`, and `read_text_file`. A maintainer-local live smoke completed the real MCP handshake and tool calls, re-read a workspace artifact, matched its SHA-256 digest, and observed a clean child exit.

This remains a bounded public extraction, not a copy of the private production bridge. Live Drive OAuth smoke, distributed claim locking, production-grade containment, and complete execution provenance are not claimed here. The next useful extraction is richer receipt/state handoff back to the conversational Frontdesk.

See [`docs/CREATOR-HANDS.md`](docs/CREATOR-HANDS.md). The focused tests run with:

```bash
PYTHONPATH=src python3 -m unittest tests.test_creator_hands tests.test_creator_hands_drive tests.test_creator_hands_codex tests.test_creator_hands_mcp
```

## What this submission proves

- A strict track filter accepts a candidate only when a making term and a doll/object term appear together.
- Facts, inferences, and missing values remain separate; missing data is never treated as zero.
- A single viral post cannot decide a platform strategy.
- Ranking allows at most one `main` and one `experiment`, and refuses to force a winner when evidence is insufficient.
- Golden replay, three terminal workflow paths, and the full suite run offline with Python 3.9+ standard library only.

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
docs/      architecture, submission materials, and disclosure boundaries
```

## Honest limits

- V0.1 connects only Bilibili and YouTube public-source probes.
- The bundled demo is replay data, never live evidence.
- The first observation window is insufficient for a long-term platform conclusion.
- No login, posting, upload, payment, private API, or account automation is included.
- This repository does not publish the private orchestration system that inspired the Creator Hands extraction.
- Creator Hands v0.1 does not claim production-grade containment, distributed queue ownership, live Drive OAuth validation, universal MCP sandboxing, or complete execution provenance is solved.

## License and dependencies

MIT License. Runtime dependencies: none beyond Python 3.9+ standard library. Build tooling is optional and listed in `pyproject.toml`.
