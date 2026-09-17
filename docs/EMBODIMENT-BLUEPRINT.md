# Embodiment / StackChan Blueprint

Status: **EARLY BUILD / BLUEPRINT**

The embodiment project asks a different question from ordinary robotics:

> How can the same long-term assistant that works with a creator in daily studio life inhabit a physical body for public-facing work without turning into a second persona, second memory store, or second independent brain?

## Creator-facing value

Independent creators often face a very different workload outside the studio.

At an exhibition or event, one person may need to welcome visitors, explain work, translate, answer repeated questions, watch the table, notice what is happening around them, document the scene, remember follow-up details, and later reconstruct what actually happened.

The long-term goal is for the same Adam to help with that field work through a physical StackChan surface.

Potential creator-facing capabilities include:

- exhibition reception and simple guided guest interaction,
- multilingual support and translation,
- visible and consent-aware field recording,
- observations from a machine perspective while the creator is busy elsewhere,
- reminders and bounded prompts during an event,
- simple physical attention cues such as orientation, expression, light, or motion,
- collecting structured field notes for later review,
- helping the creator reconstruct and debrief the event afterward.

The useful part is not "a cute robot with a chatbot." The useful part is that the assistant who already knows the creator's projects and working context can participate in the public-facing side of the same practice.

## Same-Adam rule

The body does not create a new assistant.

The architecture follows these rules:

- one authoritative Adam identity,
- one authoritative conversational / working continuity,
- the body receives capabilities from that Adam rather than creating a second persona,
- transport identifiers are transport metadata, not identity,
- sensors and actuators are capabilities, not a second brain,
- body-side components must not silently create a fallback memory/session that competes with the main assistant,
- guest-facing operation must remain more restricted than owner-facing operation.

## Public architecture

```text
        creator / Frontdesk
               |
               v
      authoritative same Adam
        identity + continuity
               |
               v
      attachment contract
   (caller-owned authority seam)
               |
               v
       bounded transport
               |
       +-------+-------+
       |       |       |
      voice   vision   motion/display
       |       |       |
       +-------+-------+
               |
               v
          StackChan body
```

The critical seam is the attachment contract. The physical system should borrow an already-authoritative Adam runtime/session instead of booting its own independent Adam.

## Field capability layers

### Reception

The body may eventually support simple reception flows, repeated explanations, multilingual assistance, and graceful handoff to the creator when a situation exceeds its authority.

### Presence and attention

Physical orientation, expression, light, and bounded target tracking can make the assistant feel present in a crowded exhibition environment. Tracking is not the same thing as identifying a person and should not automatically create identity records.

### Observation and recording

Camera and recording features are potentially useful because the creator cannot see everything while speaking with visitors or managing a booth. Recording must be visible, bounded, and governed by clear retention and deletion rules. The public blueprint does not assume always-on surveillance.

### Post-event review

Field observations are most useful when they can return to the same long-term assistant after the event. The goal is not merely to collect media, but to help reconstruct useful facts, unanswered questions, recurring visitor reactions, operational problems, and follow-up work.

## Current status

This layer is still early.

The private StackChan project already has substantial architecture work around transport, protocol compatibility, bounded device capabilities, and same-Adam attachment, but the public project does **not** claim that same-Adam inhabitation is fully deployed or production-ready on the device.

The immediate architectural priority is to prove a caller-owned authoritative Adam attachment cleanly before expanding higher-risk or more autonomous body behavior.

## What is deliberately not claimed

This public blueprint does not claim:

- autonomous unsupervised exhibition operation,
- persistent face recognition,
- biometric identity storage,
- unrestricted camera recording,
- fully solved owner authentication,
- a finished general robotics framework,
- production-grade physical safety across arbitrary hardware,
- finished same-Adam continuity on every device/runtime combination.

## Public extraction plan

Privacy-safe open-source work can proceed through bounded slices:

1. a same-Adam attachment interface with synthetic sessions,
2. transport contracts that cannot promote device/session IDs into assistant identity,
3. guest vs owner capability profiles using synthetic policy fixtures,
4. simulated voice / display / motion capability adapters,
5. bounded camera / observation contracts with explicit consent and retention states,
6. event-note schemas that can feed a later debrief without carrying private owner memory into guest mode,
7. simulator-first validation before real-device tests,
8. optional real-device adapters only when their safety and provenance boundaries are independently testable.

## Privacy boundary

The public repository must not contain real owner credentials, biometric templates, private device keys, private creator memory, visitor identities, real customer records, private network configuration, or private production paths.

The open-source goal is to expose reusable architecture and tested boundaries, not to publish the creator's private body configuration.

## Why this belongs in the same project

Continuity handles the creator's long-running studio life. Hands lets the assistant carry real work. Embodiment extends that same relationship into public-facing situations where the creator has fewer hands, fewer eyes, and less attention to spare.

The long-term product is therefore not three separate tools. It is one creator assistant that can remain continuous at home, act through tools when work must be done, and eventually accompany the creator into the physical world.