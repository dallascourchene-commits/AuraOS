# AWJ-021 — Gemini Creator Studio Delta: Admit / Repair / Falsify / Integrate

**Status:** staged / nonpromoting / D0 implementation campaign  
**Source:** owner-supplied Gemini Creator Studio conversation, 2026-08-30.  
**Purpose:** absorb useful Creator Studio implementation ideas while refusing shortcuts that violate Aura source, rights, authority, currentness, reproducibility, or effect laws.

## Newly admitted implementation surfaces

- Kinetic Caption Engine: word-boundary timed ASS captions with active-word scale pop, glow/halo, vector pill and safe-zone layout.
- Procedural SFX Engine bound to caption/music/edit events.
- `AudioIntentGraph`: voice, music, SFX and source ambience remain separate governed tracks.
- declarative `aura-studio` CLI and recipe schema.
- isolated batch-render queue with deterministic receipts and resource-aware leases.
- source/currentness-bound Fact Dossier and ClaimGraph compiler.
- Gate-10 publication adapter layer behind Project-006.
- metadata/SEO *candidate* generation, not unsupported ranking claims.
- thumbnail compiler with safe zones, subject segmentation/depth sandwich and claim-state badges.
- rights-aware Trend Scout that stages edit-pattern candidates rather than copying source media into the Commons.
- portable Template Commons recipes and attribution/fork DAG, with economics kept separate until explicitly governed.

## REF-01–06 integration

Trend deconstruction and generated recipes compile into Creator Studio's existing editorial vocabulary:

`NarrativePhase`, `MusicPhase`, `EnergyCurve`, `OnsetGrid`, `MotionSignature`, `TransitionIntent`, `CutDensityCurve`, `VisualRefrain`, `HistoricalCallback`, `ProofReveal`, `IdentityState`, `RightsState`, and `CulturalGovernance`.

The reference videos provide editorial semantics; the Gemini delta contributes candidate implementation surfaces.

## Audit result

The supplied candidate code was not trusted as production source. A clean-room audit produced a 24-item repair register. Reproduced examples include:

1. FFmpeg SFX input-index inference selects input 3 when the actual SFX input is 2.
2. `amix=duration=first` plus `-shortest` can truncate a 2.0-second video to 0.5 seconds when narration is 0.5 seconds.
3. treating arbitrary inline script text as `Path(script).exists()` can raise `ENAMETOOLONG`.
4. the Trend Scout's FFmpeg metadata filter writes `pts_time` to stdout while the candidate parser reads stderr.
5. HTTP 200 is incorrectly labelled VERIFIED evidence.
6. an extended lifecycle creates a topic/time mock hash while describing it as a verified master-render receipt.
7. publication approval is insufficiently bound to the exact artifact, account, destination, schedule, rights manifest, expiry and nonce.
8. attribution is incorrectly treated as sufficient reuse permission in source-ingest examples.
9. Commons examples assign licenses and 70/20/10 economic splits without source-rights or owner/community disposition.

The staged clean-room reference passed **35/35** deterministic tests. FFmpeg 7.1.5 synthetic regression tests reproduced the index, duration and scene-stream bugs and validated the corrected timeline behavior.

## Successor path

```text
Objective
→ Arena / rights / claim sources
→ FactDossier when evidence is required
→ CampaignGraph / StoryGraph
↔ MusicIntentGraph / AudioIntentGraph
↔ EditIntentGraph
→ ShotGraph / ThumbnailIntent
→ Capability Compiler / ExpertBundle
→ local/provider asset attempts
→ deterministic compositor / batch queue
→ quality + source + rights + technical verification
→ Gate-10 publication packet
→ HUMAN DECISION
→ effect adapter
→ platform result receipt
→ analytics observation
→ ChannelRecipe / TemplateCommons candidate
→ HyperDrive collapse
```

## Hard laws

`FETCHED != VERIFIED`  
`ATTRIBUTION != LICENSE`  
`RECIPE LICENSE != SOURCE MEDIA RIGHTS`  
`UPLOAD INITIALIZED != PUBLISHED`  
`MOCK HASH != ARTIFACT RECEIPT`  
`SEO CANDIDATE != HIGH-RANKING PROOF`  
`TREND DISCOVERY != COMMONS ADMISSION`  
`GATE10 APPROVAL MUST BIND THE EXACT EFFECT`  
`EDGE-TTS != OFFLINE`  
`QUEUE != EXECUTION`

## Gate 10

AWJ-021 is organized into three Triads: render-core repair; research/growth/Commons; effect/swarm/independent verification. Gate 10 is the owner decision surface and cannot automatically authorize merge, publication, account mutation, uncontrolled provider spend, rights-sensitive reuse or D1+ effects.
