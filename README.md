# Handmade Creator Radar V0.1

Handmade Creator Radar turns a natural-language research brief into an auditable, safety-first comparison of public creator evidence across Bilibili and YouTube.

手作创作者雷达把自然语言调研任务转成可审计、重安全的跨平台公开证据比较；当前 V0.1 支持 Bilibili 与 YouTube。

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
src/       radar implementation
tests/     offline regression and safety tests
samples/   synthetic and golden replay data
schemas/   versioned task, evidence, and score schemas
docs/      submission materials and disclosure boundaries
```

## Honest limits

- V0.1 connects only Bilibili and YouTube public-source probes.
- The bundled demo is replay data, never live evidence.
- The first observation window is insufficient for a long-term platform conclusion.
- No login, posting, upload, payment, private API, or account automation is included.
- This package contains the radar module only; it does not contain the private orchestration system that originally invoked it.

## License and dependencies

MIT License. Runtime dependencies: none beyond Python 3.9+ standard library. Build tooling is optional and listed in `pyproject.toml`.
