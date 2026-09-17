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
- `ReadbackVerifier` reads the artifact back, compares the bytes, and records a SHA-256 digest.
- `CreatorHandsBridge.run_once()` closes one complete task -> work -> verification -> receipt loop independent of whether the queue is local disk or Drive-backed.

The demo worker is deliberately boring. The interesting part is the seam: a future Codex worker, MCP verifier, image pipeline, publishing adapter, or embodied device adapter can plug into the same loop without turning the worker into the main assistant.

## Google Drive adapter boundary

`DriveQueue` needs four folders owned by the caller: queued, running, completed, and failed. The adapter stores task JSON in Drive, moves the task file as state changes, and writes a terminal receipt next to the terminal task.

Authentication is intentionally not bundled. An application passes a `token_provider()` to `GoogleDriveRestBackend`; that provider may refresh credentials however the application chooses. This repository does not contain refresh tokens, OAuth client secrets, account IDs, or private production folder IDs.

The Drive REST contract is covered by offline tests, including bearer-header handling, multipart create, folder move parameters, duplicate task rejection, filename/task-id binding, and an end-to-end DriveQueue -> worker -> verifier -> receipt loop against an in-memory Drive backend.

**Honest limit:** this public v0.1 does not claim a live OAuth smoke against somebody else's Drive account, distributed locking, or multi-consumer claim ownership. The private system that inspired it is used in real workflows and has stronger production machinery; those pieces are extracted only after they can stand alone safely.

## What this is not

This public slice does **not** claim to be the private production system that inspired it. It does not publish private memory, credentials, creator data, personal paths, private registries, device keys, or private orchestration configuration.

It also does not claim that production-grade containment or execution provenance is solved. The private system is still used and repaired in real workflows; public releases should only claim the invariants that are actually demonstrated here.

## Next adapters

Planned public extractions, only when they can be separated safely:

1. a Codex worker adapter,
2. a generic read-only MCP verifier adapter,
3. richer receipt/state handoff back to the conversational Frontdesk,
4. stronger queue ownership / concurrency semantics if a real multi-consumer use case requires them.

The architectural rule stays the same: the assistant decides, the hand executes, reality is checked, and the result returns to the same assistant.
