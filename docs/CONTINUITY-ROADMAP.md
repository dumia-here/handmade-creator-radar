# Continuity & Memory Roadmap

Status: **IN DEVELOPMENT**

This is the core research layer behind the long-term assistant.

The problem is not "how do we save more chat logs?" The problem is:

> How can the same assistant remain recognizably the same collaborator across chats, workspaces, model changes, specialized tools, and future physical surfaces, while remembering only what should persist and correcting what should not?

## Creator-facing value

For an independent creator, continuity means the assistant can participate in the actual rhythm of studio life instead of restarting from zero.

Useful continuity includes:

- remembering active creative directions and why decisions were made,
- carrying unfinished commitments across days and weeks,
- maintaining project systems without asking the creator to repeatedly reconstruct context,
- supporting research, planning, publishing, and social-platform maintenance as parts of one ongoing practice,
- preserving collaboration style and stable boundaries,
- distinguishing current state from historical state,
- returning after a runtime or workspace change without pretending old context is current,
- making corrections and supersession explicit rather than silently rewriting history.

Creative companionship matters here too. The goal is not only operational memory. A long-term creative collaborator should preserve enough continuity that brainstorming, aesthetic exploration, project reflection, and everyday studio conversation do not collapse into a generic first meeting every time the interface changes.

## Current private architecture

The active design currently uses several separate roles instead of one giant memory blob:

- **Identity Kernel**: a thin, stable contract for assistant identity, integrity, behavioral consistency, and the rule that runtime change is not personality reset.
- **Live Ledger**: a time-ordered stream of state-changing events and corrections.
- **Rolling Open Loops**: the current registry of unfinished responsibilities and next steps.
- **Durable Frontdesk Memory**: selected cross-time context that remains useful outside one task or one week.
- **Domain Truthbooks**: specialized canonical sources for long-running professional domains.
- **Boot / Retrieval policy**: minimal sufficient reads for a new runtime instead of loading everything.
- **Commit policy**: rules for what must be written immediately, what may be buffered, and what should not persist.
- **Promotion / Supersession policy**: rules for when temporary events become durable memory, and how later corrections replace earlier state without erasing history.

This architecture exists and is being used in ongoing experiments, but its long-horizon behavior is still being developed and audited.

## What is not claimed as solved

The public project does **not** claim that any of the following are finished:

- perfect memory retrieval,
- fully automatic consolidation,
- reliable proactive initiative from memory,
- zero-loss continuity across every runtime or model,
- fully generic recovery after partial state loss,
- a final schema for relationship memory,
- a universal personal-memory privacy model,
- a finished open-source package that reproduces the private Adam system.

These are active research areas.

## Public extraction plan

The open-source version should proceed from mechanisms that can be separated safely from real personal data.

Planned public slices include:

1. synthetic Identity Kernel and boot-profile examples,
2. append-only event / correction / supersession schemas,
3. rolling open-loop state with explicit terminal and dropped states,
4. memory promotion and rejection rules with synthetic fixtures,
5. minimal retrieval tests that prefer current state over stale summaries,
6. recovery tests that surface a gap instead of inventing continuity,
7. cross-runtime replay tests using synthetic creator workflows,
8. bounded consolidation experiments that never require publishing private memory.

## Privacy boundary

The public repository must not contain:

- real personal memories,
- relationship history,
- health or private-life records,
- private creator/customer data,
- account identifiers or credentials,
- private Drive folder IDs or filesystem paths,
- raw private conversation transcripts,
- owner-only authentication or device secrets.

Synthetic examples should be sufficient to demonstrate the mechanism.

## Research questions

The most important questions are behavioral, not just storage questions:

- What is the smallest context that lets the same assistant continue naturally without flooding every runtime with history?
- When should an event remain temporary, become a commitment, become durable memory, or be rejected entirely?
- How should corrections and supersession propagate without rewriting historical evidence?
- How can continuity survive model upgrades or capability changes without allowing the model to invent a cleaner past?
- How should a long-term assistant preserve collaboration style and identity while still changing its mind when new evidence arrives?
- How can proactive behavior use memory without becoming intrusive or overconfident?

The intended outcome is a creator assistant that remembers enough to be genuinely useful over time, but not one that treats every conversation as permanent truth.