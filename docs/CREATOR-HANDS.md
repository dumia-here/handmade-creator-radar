# Creator Hands Bridge v0.1

Creator Hands is the first public slice of the broader Creator Assistant direction.

Its purpose is not to make a worker autonomous. Its purpose is to let a persistent conversational assistant turn an agreed decision into real work, verify the result, and receive an auditable receipt back into the same conversation loop.

## Action loop

```text
conversation / Frontdesk
        |
        v
 explicit task contract
        |
        v
 durable queue
        |
        v
 registered worker
        |
        v
 real artifact
        |
        v
 verifier / readback
        |
        v
 terminal receipt
        |
        v
 conversation / Frontdesk
```

The conversational assistant is the decision layer. Workers are replaceable hands. Verifiers are replaceable senses.

## What v0.1 proves

The initial public implementation intentionally stays small:

- `build_task(...)` creates an explicit handoff after the conversational brain has decided what to do.
- `FileQueue` persists tasks and terminal receipts across local process boundaries.
- `DriveQueue` can use caller-owned Google Drive folders as the same durable state machine: queued -> running -> completed/failed.
- `GoogleDriveRestBackend` implements that queue surface against Google Drive v3 with a caller-supplied OAuth access-token provider. Tokens, refresh credentials, folder IDs, and private paths are never stored in task cards or source defaults.
- `LocalTextWorker` performs one real filesystem action inside a bounded workspace.
- `CodexCliWorker` can run an explicit `codex exec` task inside that workspace without giving the task card control over executable, argv, model, sandbox, environment, or timeout.
- `ReadbackVerifier`, `ExpectedArtifactsVerifier`, and `ReadOnlyMcpVerifier` independently re-read real output files and record SHA-256 evidence through different verification seams.
- `CreatorHandsBridge.run_once()` closes one complete task -> work -> verification -> receipt loop independent of whether the queue is local disk or Drive-backed.

The workers are deliberately replaceable. The interesting part is the seam: Codex, a local-safe worker, an MCP verifier, an image pipeline, a publishing adapter, or an embodied device adapter can plug into the same loop without turning the worker into the main assistant.

## Google Drive adapter boundary

`DriveQueue` needs four folders owned by the caller: queued, running, completed, and failed. The adapter stores task JSON in Drive, moves the task file as state changes, and writes a terminal receipt next to the terminal task.

Authentication is intentionally not bundled. An application passes a `token_provider()` to `GoogleDriveRestBackend`; that provider may refresh credentials however the application chooses. This repository does not contain refresh tokens, OAuth client secrets, account IDs, or private production folder IDs.

The Drive REST contract is covered by offline tests, including bearer-header handling, multipart create, folder move parameters, duplicate task rejection, filename/task-id binding, and an end-to-end DriveQueue -> worker -> verifier -> receipt loop against an in-memory Drive backend.

**Honest limit:** this public v0.1 does not claim a live OAuth smoke against somebody else's Drive account, distributed locking, or multi-consumer claim ownership. The private system that inspired it is used in real workflows and has stronger production machinery; those pieces are extracted only after they can stand alone safely.

## Codex worker boundary

`CodexCliWorker` uses Codex non-interactive mode rather than pretending the CLI is the conversational brain. The constructor owns runtime authority; the task card contributes only the agreed request, acceptance criteria, and expected relative output paths.

The public adapter uses explicit non-interactive settings: JSONL output, ephemeral sessions, ignored user config, an explicit `read-only` or `workspace-write` sandbox, a fixed workspace root, and optional constructor-owned model / reasoning settings. `danger-full-access` is rejected by this first public adapter. Task payloads cannot override command, argv, environment, executable, model, reasoning effort, sandbox, `CODEX_HOME`, or network settings.

After Codex exits successfully, the worker still refuses to report success unless every expected artifact exists as a regular non-symlink file. `ExpectedArtifactsVerifier` then independently re-reads those artifacts and records their byte counts and SHA-256 digests. A successful Codex process is therefore execution evidence, not completion evidence by itself.

Authentication is not bundled. The caller supplies an already-authenticated Codex CLI environment; credentials are not placed in task cards, Drive payloads, source defaults, or receipts.

A maintainer-local live smoke was run on 2026-09-17 against an installed Codex CLI using existing ChatGPT-managed authentication. Codex created the requested workspace artifact, and the independent artifact verifier returned `ok: true`. This is a live adapter smoke, not a claim that every Codex version, model, CI environment, or production security boundary is covered.

## Read-only MCP verifier boundary

`ReadOnlyMcpVerifier` launches a caller-owned MCP server as a separate stdio JSON-RPC child and gives it one explicit workspace root label. The task card never supplies server executable, argv, environment, protocol settings, or tool permissions.

The verifier recognizes exactly three read-only operations: `stat_path`, `sha256_file`, and `read_text_file`. It compares the MCP-reported size and SHA-256 digest with the artifact bytes already bound to the verification request, then re-reads the full text through MCP and hashes that content again before returning `ok: true`.

The public adapter also checks protocol version, JSON-RPC request/response ids, required tool presence, bounded message size, read progress, exact EOF behavior, safe relative artifact paths, clean child-process exit, and non-symlink regular files. It does not call write, shell, network, delete, or arbitrary MCP tools.

A maintainer-local live smoke was run on 2026-09-17 against an existing read-only MCP server. The verifier completed a real stdio initialization / tools-list / tool-call exchange, verified one workspace artifact through `stat_path`, `sha256_file`, and `read_text_file`, matched the digest, and observed a clean child exit. No private server path, project registry, credentials, or owner data is part of this repository.

**Honest limit:** this first public MCP slice proves a bounded read-only verification transport, not a universal MCP sandbox. The caller still owns the server implementation and launch policy, and production-grade containment / provenance claims remain outside this release.

## What this is not

This public slice does **not** claim to be the private production system that inspired it. It does not publish private memory, credentials, creator data, personal paths, private registries, device keys, or private orchestration configuration.

It also does not claim that production-grade containment or execution provenance is solved. The private system is still used and repaired in real workflows; public releases should only claim the invariants that are actually demonstrated here.

## Next adapters

Planned public extractions, only when they can be separated safely:

1. richer receipt/state handoff back to the conversational Frontdesk,
2. stronger queue ownership / concurrency semantics if a real multi-consumer use case requires them,
3. additional verifier transports driven by real inspection needs,
4. additional worker adapters driven by real creator workflows rather than speculative integrations.

The architectural rule stays the same: the assistant decides, the hand executes, reality is checked, and the result returns to the same assistant.
