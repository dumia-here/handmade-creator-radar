# Devpost direct-paste package V1

## About the project

### Inspiration

Independent handmade creators often have to decide where to publish with very little time and very noisy evidence. A single viral post can look persuasive, while missing metrics, recycled content, and platform-specific presentation styles make direct comparisons unreliable. I wanted a small research tool that could answer a more useful question: what can we responsibly infer from the public evidence we actually have, and what must remain unknown?

### What it does

Handmade Creator Radar V0.1 turns a natural-language research brief into an auditable cross-platform evidence workflow for independent handmade-doll creators.

It converts the brief into a versioned task contract, dispatches only the requested read-only probes, and applies a deliberately narrow track filter. A candidate enters `accepted` only when a making term and a doll or toy object term appear together; generic craft content and object-only mentions stay out of the accepted lane. Positive, negative, and false-positive regression tests protect that boundary.

For every candidate, the radar keeps facts, inferences, and missing values separate. Missing data remains missing instead of becoming zero. It scores six signals, caps the influence of a single viral item, and permits at most one `main` platform and one `experiment`. When evidence is weak or tied, it refuses to force a winner.

V0.1 has real public-source probes for Bilibili and YouTube. Its platform request structure is extensible, but this submission does not claim that other platforms are already connected. The first real observation window completed successfully, yet both platforms remained `insufficient_evidence`; one window is not enough to establish long-term growth, content lifetime, or creator migration.

The submission also includes a fully offline golden replay, a three-path workflow demo, versioned JSON schemas, and 58 standard-library tests. The replay is always labeled `replay_golden` and is never presented as live evidence.

### How we built it

The project is implemented in Python 3.9+ with no runtime dependencies outside the standard library. A versioned JSON task contract defines platform probes, safety mode, observation window, and completion criteria. A probe registry isolates platform adapters, while HTTPS allowlists, redirect checks, response-size limits, finite retries, and page-instruction isolation constrain public fetching.

The TrackFilter produces `accepted`, `review`, or `rejected` decisions before evidence can enter scoring. Evidence records encode statement kind, directness, freshness, confidence, and missingness. The scoring layer aggregates signals conservatively, exposes conflicts, caps outliers, penalizes maintenance cost, and downgrades uncertain or tied results.

For reproducibility, the independent demo creates temporary state, runs an offline preflight, loads a frozen golden replay, prints a path-free JSON summary, and removes its temporary state. A separate workflow demo exercises completion, human confirmation and resume, and failure without contacting external services.

OpenAI Codex was used to turn staged task cards into implementation increments, add regression tests, run acceptance checks, prepare the public boundary, and package a privacy-scanned submission without copying the private orchestration system.

### Challenges we ran into

Public platform pages expose uneven metadata. In the first observation window, some candidates had visible engagement facts while others lacked creator identifiers or comparable metrics. Treating those gaps as zero would have created false certainty, so the data model and tests had to make missingness explicit throughout the pipeline.

Track precision was another challenge. Broad handmade keywords admitted unrelated craft content, while doll-only mentions did not prove a making process. The final rule requires both a making signal and a doll or toy object signal, with exclusions taking priority.

The final challenge was separating a demonstrable module from its private operating environment. The submission package had to run independently while excluding real task cards, receipts, reports, notification credentials, account data, and local paths.

### Accomplishments that we're proud of

- Connected read-only public probes for one domestic platform, Bilibili, and one global platform, YouTube.
- Completed a real first observation window without presenting weak evidence as a strategic recommendation.
- Preserved fact, inference, and missing as distinct evidence states.
- Prevented a single viral post from deciding a platform strategy.
- Added explicit terminal behavior for success, human confirmation and resume, and failure.
- Reached 58 passing offline tests with zero runtime dependencies.
- Produced an independent, privacy-scanned submission package and a reproducible three-command demo.

### What we learned

The most valuable output of a research tool is sometimes a disciplined refusal to conclude. Evidence quality, source diversity, and observation time matter more than an attractive score. A visible metric is not automatically comparable, an inference should never masquerade as a fact, and replay data must be visibly separated from live data.

We also learned that human confirmation works best as a narrow, explicit state transition rather than a general escape hatch. Approval can resume a business decision, but it cannot relax global safety rules.

### What's next

The next research step is a second observation window after roughly one week, using the same candidates and the same missing-data rules. Only then can the radar begin to evaluate relative growth and content lifetime. After the event, additional platform probes can be added through the existing versioned task structure, one read-only adapter at a time, with the same evidence and safety contract. The immediate product goal remains modest: help independent handmade creators make smaller, better-supported publishing experiments instead of chasing noisy platform hype.

## Built with

Add these tags individually, in this order:

1. Python
2. OpenAI Codex
3. JSON
4. JSON Schema
5. Python unittest
6. HTML
7. Bilibili
8. YouTube

## Links and media status

- Try it out link: add the independent public repository URL only after the repository has been created and reviewed by the project owner.
- Video demo link: add the uploaded 60–90 second video URL only after the project owner has reviewed the final cut.
- Image gallery: optional; use the safe 3:2 cover method in `DEMO-录屏单-v1.md` if time permits.

No repository, video, gallery image, or Devpost submission was published while preparing this text.
