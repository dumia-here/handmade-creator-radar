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
- `FileQueue` persists tasks and terminal receipts across process boundaries.
- `LocalTextWorker` performs one real filesystem action inside a bounded workspace.
- `ReadbackVerifier` reads the artifact back, compares the bytes, and records a SHA-256 digest.
- `CreatorHandsBridge.run_once()` closes one complete task -> work -> verification -> receipt loop.

The demo worker is deliberately boring. The interesting part is the seam: a future Codex worker, Google Drive queue, MCP verifier, image pipeline, publishing adapter, or embodied device adapter can plug into the same loop without turning the worker into the main assistant.

## What this is not

This public slice does **not** claim to be the private production system that inspired it. It does not publish private memory, credentials, creator data, personal paths, private registries, device keys, or private orchestration configuration.

It also does not claim that production-grade containment or execution provenance is solved. The private system is still used and repaired in real workflows; public releases should only claim the invariants that are actually demonstrated here.

## Next adapters

Planned public extractions, only when they can be separated safely:

1. a Google Drive durable-queue adapter,
2. a Codex worker adapter,
3. a generic read-only MCP verifier adapter,
4. richer receipt/state handoff back to the conversational Frontdesk.

The architectural rule stays the same: the assistant decides, the hand executes, reality is checked, and the result returns to the same assistant.
