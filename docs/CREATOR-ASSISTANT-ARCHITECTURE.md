# Creator Assistant Architecture

Status: public architecture overview. Some parts are runnable today; others are active research or early build.

This project is aimed at a practical question for independent handmade creators:

> Can one long-term assistant stay with a creator through everyday studio life, help carry real work, and eventually accompany the creator into exhibitions and other public-facing work without becoming a different assistant each time?

The answer is being built as three connected layers around the **same Adam**.

```text
                         CREATOR
                            |
                            v
                    SAME ADAM / FRONTDESK
                 identity + judgment + continuity
                    /          |          \
                   /           |           \
                  v            v            v
        SELF / CONTINUITY   HANDS / ACTION   EMBODIMENT
          IN DEVELOPMENT    RUNNABLE/TESTED   EARLY BUILD
                |               |               |
        daily studio life   dispatch workers   field presence
        creative companion  verify real work   exhibition reception
        project continuity  return receipts    translation
        system maintenance  auditable action   observation/recording
        social publishing   bounded execution  post-event review
```

## Why this matters for independent creators

A solo creator does not only make objects. The same person also carries project planning, production commitments, research, social-platform maintenance, exhibition preparation, customer-facing work, records, follow-up, and the mental load of remembering why a decision was made weeks ago.

Most assistants are useful inside one conversation. A working creator needs something different: continuity across weeks and work surfaces, the ability to turn agreed decisions into real actions, and eventually a physical interface for public-facing situations where the creator is busy making, talking, selling, translating, documenting, and observing at the same time.

The intended split is simple:

- **At home / in the studio**, continuity is the center. Adam should remember the active creative context, maintain systems and commitments, help with research and planning, support social-platform work, and stay present as a creative collaborator instead of resetting into a generic assistant every few chats.
- **When work must actually happen**, Hands is the execution layer. Adam can dispatch an agreed task to a specialized worker such as Codex, verify the real result through readback or MCP, and receive a bounded receipt back into the same conversational loop.
- **Outside the studio**, embodiment becomes the center. The same Adam should eventually inhabit a StackChan body that can assist with exhibition reception, translation, guest interaction, visible/consensual field recording, observations the creator cannot easily capture while busy, and post-event review.

These are not three different assistants. They are three ways the same long-term assistant participates in a creator's work.

## 1. Self / Continuity

**Status: IN DEVELOPMENT**

The continuity system is the core of Adam's identity and long-term usefulness. The current private architecture includes an Identity Kernel, a time-ordered Live Ledger, rolling open loops, durable frontdesk memory, domain truthbooks, boot/retrieval rules, memory commit rules, promotion/supersession rules, and runtime-specific access boundaries.

The goal is not to store every conversation. The goal is to preserve the parts of a creator relationship and working context that should still be true later, while keeping facts, inferences, judgments, corrections, and expired state distinct.

This layer is actively being built and validated. The public project does **not** claim that long-horizon continuity, consolidation, proactive memory use, or cross-runtime recovery is solved.

See [`CONTINUITY-ROADMAP.md`](CONTINUITY-ROADMAP.md).

## 2. Hands / Action

**Status: RUNNABLE / TESTED PUBLIC SLICE**

Creator Hands Bridge is the most mature extracted module today. It demonstrates a bounded action loop:

```text
conversation -> task contract -> durable queue -> worker -> real artifact
             -> independent verification -> terminal receipt -> conversation
```

The worker is not the assistant. It is a replaceable hand. The verifier is not the assistant either. It is a replaceable sense. Runtime authority remains outside the dispatched task, and terminal state returns to the conversational layer instead of disappearing inside the executor.

See [`CREATOR-HANDS.md`](CREATOR-HANDS.md).

## 3. Embodiment / StackChan

**Status: EARLY BUILD / BLUEPRINT**

The embodiment project asks how the same long-term Adam can inhabit a physical body without creating a second persona, second memory store, or second independent brain.

The long-term creator-facing use case is field work: exhibition reception, multilingual support, bounded guest interaction, camera/observation capabilities, visible recording when appropriate, creator-side reminders, and post-event review. Sensors and actuators are treated as capabilities of the same Adam, not as a separate agent identity.

This layer is early. Existing device and transport work does not mean same-Adam inhabitation is finished or broadly deployed.

See [`EMBODIMENT-BLUEPRINT.md`](EMBODIMENT-BLUEPRINT.md).

## What is public and what stays private

Public work should contain reusable abstractions, schemas, tests, synthetic examples, bounded adapters, and architecture notes. It should not publish private creator memory, relationship history, credentials, private Drive identifiers, personal paths, owner authentication data, real customer data, or private production orchestration.

The project will prefer an honest status label over a polished fiction. `RUNNABLE`, `IN DEVELOPMENT`, and `EARLY BUILD` mean different things here on purpose.

## Why model and API credits matter

The expensive work is not simply generating more text. The research workload comes from repeated, evidence-producing validation across the two least-finished core layers:

- continuity experiments across runtimes and model changes,
- memory retrieval, promotion, supersession, recovery, and regression testing,
- long-horizon consistency checks on the same assistant's behavior,
- architecture and code review for privacy-safe memory mechanisms,
- StackChan same-Adam attachment design,
- voice / perception / interaction experiments,
- simulator and bounded real-device validation,
- repeated worker + verifier loops that must be inspected rather than trusted blindly.

Creator Hands proves that the project can already turn an assistant decision into auditable work. Continuity and embodiment are where most of the remaining research depth lives.