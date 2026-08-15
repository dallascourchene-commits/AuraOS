# CapCut Desktop Project Templates — War Capsule 02 / Triad 2

**Coordinate:** `AD:DISTRIBUTION:MEDIA-MATERIALIZE:002`  
**Workers:** W4 / W5 / W6  
**Source:** `docs/staging/ready_review/TIKTOK_CAMPAIGN_SCRIPTS.md` from branch `staging/wo-triad2-tiktok-campaign-004`  
**Source Git blob:** `6bb505276b0b34a3daf8a0424f186be22ad3421e`  
**State:** `MATERIALIZED / DRAFT ASSETS / NOT PUBLISHED`

> Claim boundary inherited from the source campaign: hooks may be provocative, but the spoken body and visible proof labels must preserve the evidence state. Do not replace a target, proxy, bounded test, or economic model with a broader measured claim during editing.

## Global CapCut desktop project preset

Use this preset for all ten projects unless the per-project blueprint overrides it.

- Canvas: `1080 × 1920`, 9:16 vertical.
- Frame rate: `30 fps`.
- Audio: `48 kHz`, voice centered, music ducked under speech.
- Safe zone: keep essential text inside x=`90..990`, y=`150..1580`; keep CTA above y=`1520`.
- Track map:
  - `V1` — A-roll / face camera.
  - `V2` — B-roll / screen recording / whiteboard.
  - `V3` — transparent PNG diagram layers.
  - `V4` — proof cards / callouts.
  - `V5` — burned-in captions.
  - `A1` — voiceover / production dialogue.
  - `A2` — music bed.
  - `A3` — clicks, ticks, stamps, keyboard, paper, transition SFX.
- Captions: sentence case, two lines maximum, high contrast, word-level emphasis only for proof terms.
- PNG standard: export transparent PNG at `2160 × 2160` or larger; import at 100% quality; never bake unsupported benchmark numbers into reusable PNGs.
- Default PNG animation: 4-frame opacity ease-in, 6-frame ease-out. For stamps: scale `118% → 100%` over 6 frames.
- Default A-roll crop: chest-up, eyes near y=`520`; punch-ins to `108–115%` only on emphasis.
- Music target: approximately `-26 to -22 LUFS` under voice; drop 2–4 dB for CTA and all claim-boundary sentences.
- Export master: H.264, 1080×1920, 30 fps, high bitrate, AAC 48 kHz; make clean master without platform watermark.

---

# PROJECT 01 — THE CLOUD AI TRAP

**Source part:** 1 — “Why cloud AI pricing becomes a trap”  
**Target duration:** `30.0 s`  
**Cover:** `THE CLOUD AI TRAP`

## Voiceover master

> “Cloud AI gets expensive for one stupid reason: we keep paying a giant model to make tiny decisions. Most AI systems send everything upward: routing, lookup, classification, memory retrieval, even questions the software could answer deterministically. That means every little decision can become another metered model call. Aura flips that order. First: route locally. Then: resolve the smallest source neighborhood. Then: call a heavyweight model only when the problem is actually unresolved. The goal isn’t ‘never use the cloud.’ The goal is: don’t rent intelligence for work a deterministic substrate can already do. If you build agents, follow this series. I’m going to show the pieces one by one.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:02.5 | V1 face camera; phone enters frame | `THE CLOUD AI TRAP` | `p01_api_bill_arrow.png`: upper-right, 74% scale, red arrow only, no real vendor logo | VO hook starts immediately; no music |
| 00:02.5–00:05.0 | Smash cut V2 simple flow | `EVERYTHING → BIG MODEL` | `p01_big_model_flow.png`: centered y=760, 88% width | Hit SFX at cut; music pulse enters |
| 00:05.0–00:09.5 | V2 screen/graphic; counter rises | `routing • lookup • classify • memory` | `p01_meter_counter.png`: right edge, 42% scale; generic `$ / tokens` only | VO lists decisions; ticking SFX |
| 00:09.5–00:12.5 | V1 punch-in | `ANOTHER METERED CALL` | `p01_meter_stamp.png`: center, 58% scale, stamp animation | Music low; stamp hit |
| 00:12.5–00:17.5 | V2 pipeline redraw | `ROUTE → SOURCE → LOCAL RULE` | `p01_local_pipeline.png`: full-width lower third, nodes separated; green/neutral only | One click per stage |
| 00:17.5–00:21.0 | Add escalation branch | `MODEL IF NEEDED` | `p01_model_if_needed.png`: cloud node at upper-right, dotted arrow from local pipeline | Airy transition only on escalation |
| 00:21.0–00:25.5 | Whiteboard / handwritten card | `SMALLEST SUFFICIENT WORLD` | `p01_smallest_world_ring.png`: translucent ring around one relevant node | VO “don’t rent intelligence…”; music ducks |
| 00:25.5–00:30.0 | V1 face CTA | `BUILD AGENTS? FOLLOW THE SERIES.` | `p01_follow_arrow.png`: lower-right, safe-zone compliant | CTA; music -3 dB then clean stop |

**Edit emphasis:** punch in on “tiny decisions,” “route locally,” and “only when unresolved.”  
**Claim gate:** do not add vendor pricing or a savings percentage to any text card unless an audited current cost comparison is attached.

---

# PROJECT 02 — 9 WORKERS / OLD LAPTOP / PENNIES?

**Source part:** 2 — “Nine AI workers. One old laptop. Pennies?”  
**Target duration:** `32.0 s`  
**Cover:** `9 AGENTS. OLD LAPTOP?`

## Voiceover master

> “Nine AI workers. One old laptop. Pennies. Sounds fake—so here’s the rule: don’t claim it until the telemetry proves it. What we’re actually building is a local-first orchestration layer where workers don’t each need to carry the whole world. They get a coordinate, a bounded job, the smallest relevant context, and a receipt. The cheap part should be deterministic routing, state tracking, source lookup, and local housekeeping. The expensive model call becomes the exception. We already have staged evidence for that architecture. What we do not have in this work order is a source-bound proof that nine concurrent workers on an old laptop cost ‘pennies.’ So that number stays a benchmark target until CPU, RAM, model, wall-time, and actual provider spend are captured. Want the benchmark when it’s real? Comment `9X` and I’ll post the exact test design.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Old laptop + nine W1–W9 sticky notes | `9 WORKERS / OLD LAPTOP / PENNIES?` | `p02_worker_ring.png`: nine numbered transparent nodes around laptop | Laptop fan + keyboard; VO hook |
| 00:03.0–00:06.0 | Freeze + stamp | `CLAIM ≠ PROOF` | `p02_claim_not_proof_stamp.png`: center, 70% | Beat enters after “sounds fake” |
| 00:06.0–00:12.0 | Nine workers receive capsules | `COORDINATE • BOUNDED JOB • CONTEXT • RECEIPT` | `p02_capsule_w1_w9.png`: nine small capsule cards; animate sequentially | Nine click ticks |
| 00:12.0–00:17.5 | Local utility functions appear | `ROUTING / STATE / LOOKUP / HOUSEKEEPING` | `p02_local_cheap_stack.png`: 4-layer transparent stack | Dry clicks; no dollar claim |
| 00:17.5–00:21.5 | One branch rises to cloud/model | `EXPENSIVE MODEL = EXCEPTION` | `p02_exception_escalation.png`: dotted upward branch only | One airy escalation SFX |
| 00:21.5–00:27.5 | Telemetry dashboard placeholder | `RSS / CPU / TOKENS / $ / WALL TIME` | `p02_telemetry_empty.png`: gauges with blank values; 85% width | Music ducks; voice states missing proof |
| 00:27.5–00:30.0 | Face camera | `BENCHMARK TARGET — NOT MARKETING FACT` | `p02_target_badge.png`: lower third | End dry on “captured” |
| 00:30.0–00:32.0 | CTA card | `COMMENT 9X FOR TEST DESIGN` | `p02_9x_cta.png`: center | Single clean CTA hit |

**Claim gate:** never replace the blank telemetry with “pennies” until exact hardware, models, concurrency, wall time, energy/provider costs, and memory are captured in a reproducible run.

---

# PROJECT 03 — INDIGENOUS IDEAS → ARCHITECTURE

**Source part:** 3 — “Indigenous innovation can challenge the default AI stack”  
**Target duration:** `35.0 s`  
**Cover:** `INDIGENOUS IDEAS → ARCHITECTURE`

## Voiceover master

> “What if one of the most interesting attacks on centralized AI infrastructure comes from an Indigenous way of thinking about relationships? Aura’s history starts with Indigenous language work and the structure of polysynthetic language—where meaning is built through relationships, roles, and composition. That pushed a different engineering question: Why keep throwing giant blobs of context at a model when the system can compile the relationships that matter for one objective? That becomes routing. Bounded hydration. Source lineage. Negative space—what must not be activated. And human authority that cannot be invented by the machine. For underrepresented founders, that matters: your worldview doesn’t have to be the ‘story around’ the technology. It can shape the technology itself. If you’re building from a worldview the industry usually ignores, follow. I want to see what architecture comes out of it.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.5 | Face camera, quiet background | `INDIGENOUS INNOVATION ≠ BRANDING` | none | Dry voice, no stock “tribal” music |
| 00:03.5–00:08.0 | Handwritten morphology fragments | `RELATIONSHIPS • ROLES • COMPOSITION` | `p03_morph_blocks.png`: neutral linguistic blocks, no sacred motifs | Warm minimal pulse enters |
| 00:08.0–00:13.5 | Blocks morph into graph nodes | `WORLDVIEW → ENGINEERING QUESTION` | `p03_morph_to_graph.png`: nodes and arrows only | Soft click per relation |
| 00:13.5–00:18.5 | Blob graphic shrinks into bounded subgraph | `WHY THROW THE WHOLE CONTEXT?` | `p03_blob_to_relation.png`: large translucent blob → selected nodes | VO engineering question |
| 00:18.5–00:26.0 | Four architecture cards one per cut | `ROUTING` → `LINEAGE` → `NEGATIVE SPACE` → `HUMAN GATE` | `p03_four_terms.png`: separate transparent icons, one visible at a time | Four restrained clicks |
| 00:26.0–00:31.5 | Face camera | `WORLDVIEW CAN SHAPE THE TECHNOLOGY` | `p03_worldview_arch.png`: faint relational mesh behind subject | Music ducks |
| 00:31.5–00:35.0 | CTA | `BUILD FROM WHAT THE INDUSTRY IGNORES` | `p03_follow_cta.png`: lower third | Voice leads; music resolves |

**Cultural guardrail:** no generic “tribal” music, regalia, sacred motifs, or implied community endorsement. Present documented inspiration/design genealogy, not linguistic validation or authorization by an Indigenous nation/community.

---

# PROJECT 04 — 3-6-9 WITHOUT THE MYTH

**Source part:** 4 — “The 3-6-9 rhythm of edge computing”  
**Target duration:** `30.0 s`  
**Cover:** `3-6-9 WITHOUT THE MYTH`

## Voiceover master

> “3-6-9 sounds like numerology. In our router, it’s much less mystical—and much more useful. In one staged Aura router, the normal path takes six logical transitions. A guarded diagonal path can collapse that to one transition—but only when every required guard is already verified and the negative-space boundaries are conflict-free. So the memorable part is ‘3-6-9.’ The engineering part is this: six logical steps versus one eligible rebase. And here’s the honesty clause: that is a 6:1 transition-count ratio, not a 6× speed claim. The recorded local wall-clock run was only about 1.279× faster. Structure first. Measurement second. Myth never. Follow for the actual state machine behind the shortcut.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Big numerals | `3  →  6  →  9 ?` | `p04_369_numbers.png`: centered, 92% width | VO hook |
| 00:03.0–00:05.0 | Stamp | `ROUTING LABEL, NOT MAGIC` | `p04_not_numerology_stamp.png`: 68% center | Stamp SFX |
| 00:05.0–00:12.5 | Six-node linear state path | `NORMAL PATH = 6 LOGICAL TRANSITIONS` | `p04_six_node_path.png`: horizontal/diagonal vertical-safe layout | Six evenly spaced ticks |
| 00:12.5–00:17.5 | Diagonal shortcut appears | `ELIGIBLE REBASE = 1 TRANSITION` | `p04_diagonal_rebase.png`: bright diagonal arrow; guard icons above | One bass click |
| 00:17.5–00:22.0 | Guard chips fill | `ONLY IF GUARDS ARE VERIFIED` | `p04_guard_chips.png`: `SOURCE / CURRENT / CONFLICT-FREE` | Quiet pulse |
| 00:22.0–00:26.5 | Split proof card | `LOGICAL 6:1` / `LOCAL WALL CLOCK ≈ 1.279×` | `p04_ratio_vs_time.png`: two-column transparent card | Music cuts under “not a 6× speed claim” |
| 00:26.5–00:30.0 | Face/CTA | `STRUCTURE FIRST. MEASUREMENT SECOND.` | `p04_structure_measurement.png`: lower third | Three final beats; CTA |

**Claim gate:** keep `3→6→9` generation-specific and conditional. Never replace `1.279×` wall-clock with `6×` speed.

---

# PROJECT 05 — DON’T FEED AI THE WORLD

**Source part:** 5 — “Stop feeding AI the whole world”  
**Target duration:** `28.0 s`  
**Cover:** `DON'T FEED AI THE WORLD`

## Voiceover master

> “Most AI context engineering starts with the wrong instinct: ‘give the model everything.’ Our operating rule is almost the opposite: Compile the smallest source-resolvable relational world sufficient for the objective. If the job is one file, don’t hydrate the repository. If the answer is in metadata, don’t load the body. If a deterministic route resolves the next step, don’t call a model. And if the source is missing, stop UNKNOWN instead of hallucinating a bridge. Smaller context isn’t the goal by itself. Sufficient context with exact source descent is the goal. Save this if you build RAG or agents. It’s a better design question than ‘how big is my context window?’”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Huge paper stack hits desk | `DON'T FEED THE SYSTEM THE WORLD` | none | Loud paper thump; VO hook |
| 00:03.0–00:06.0 | Push most stack aside | `OBJECTIVE FIRST` | `p05_objective_card.png`: center card | Sparse click track |
| 00:06.0–00:12.5 | One card becomes relational subgraph | `SMALLEST SOURCE-RESOLVABLE WORLD` | `p05_small_world_graph.png`: selected nodes only | Pause before operating law |
| 00:12.5–00:17.5 | Metadata/file/body hierarchy | `METADATA → L0 → SOURCE IF NEEDED` | `p05_hydration_ladder.png`: vertical ladder | One click per descent |
| 00:17.5–00:21.5 | Deterministic route bypasses model | `ROUTE RESOLVED? DON'T CALL A MODEL.` | `p05_bypass_model.png`: local route + dim cloud | Dry voice |
| 00:21.5–00:24.5 | Hard stop card | `SOURCE MISSING → UNKNOWN` | `p05_unknown_stop.png`: stop octagon, neutral not alarmist | Single stop SFX |
| 00:24.5–00:28.0 | CTA | `SUFFICIENT CONTEXT > BIG CONTEXT` | `p05_save_cta.png`: lower third | CTA; music resolves |

**Claim gate:** do not add a universal token-savings percentage to this video without the specific benchmark artifact attached.

---

# PROJECT 06 — 8 BYTES → EXACT SOURCE

**Source part:** 6 — “An 8-byte handle can lead back to exact source”  
**Target duration:** `32.0 s`  
**Cover:** `8 BYTES → EXACT SOURCE`

## Voiceover master

> “No, we did not compress 256 kilobytes of arbitrary data into eight magic bytes. We built a staged hydration transducer where L0 is an 8-byte record handle. That handle resolves through a source-bound hierarchy back to exact L4 bytes, and SHA-256 verifies recovery. In the repaired N2 generation, 25 of 25 tests passed, including the zero-byte eviction edge case. Across local sandbox fixtures, hot L0-to-L4 median recovery landed around 50.79 to 65.88 microseconds. The important distinction: the eight bytes are a handle into a verified source system. They are not a claim that arbitrary source content lives inside eight bytes. If you care about AI memory without hand-wavy compression claims, follow the hydration series.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Tiny `8 bytes` index card | `8 BYTES ≠ MAGIC COMPRESSION` | `p06_8byte_card.png`: center, 50% | Tiny ping |
| 00:03.0–00:07.0 | Arrow to file cabinet/store | `L0 = RECORD HANDLE` | `p06_handle_to_store.png`: card + content-addressed store | Low click |
| 00:07.0–00:14.0 | L0→L4 ladder | `L0 → L1 → L2 → L3 → L4 EXACT BYTES` | `p06_l0_l4_ladder.png`: vertical center | Rising clicks through levels |
| 00:14.0–00:17.0 | Hash seal | `SHA-256 VERIFY` | `p06_sha_seal.png`: 42% lower-center | Seal SFX |
| 00:17.0–00:21.5 | Test card | `25 / 25 PASS` | `p06_25of25.png`: full center | Short positive chime |
| 00:21.5–00:26.5 | Benchmark card | `50.79–65.88 µs` / `LOCAL SANDBOX` | `p06_local_latency.png`: two-line card; “LOCAL SANDBOX” same prominence | Music ducks |
| 00:26.5–00:30.0 | Return to handle diagram | `HANDLE INTO SOURCE ≠ SOURCE INSIDE HANDLE` | `p06_handle_not_payload.png`: side-by-side comparison | Silence briefly on “not a claim” |
| 00:30.0–00:32.0 | CTA | `FOLLOW THE HYDRATION SERIES` | `p06_follow.png` | Clean finish |

**Claim gate:** `LOCAL SANDBOX` must remain visible whenever the microsecond result is visible. Do not label this production/mobile/Drive/provider latency.

---

# PROJECT 07 — ROUTING IS NOT TRUTH

**Source part:** 7 — “Routing is not truth”  
**Target duration:** `28.0 s`  
**Cover:** `ROUTING IS NOT TRUTH`

## Voiceover master

> “An AI can know where to go and still have zero authority to act. This is one of the rules I wish every agent framework enforced. A coordinate can tell you where something is. A router can tell you which path is valid. A receipt can tell you what ran. None of those things automatically make the result true. And none of them give the worker permission to promote, deploy, publish, or spend. Aura separates addressability, source, currentness, verification, and human disposition. That sounds bureaucratic—until your agent confidently does the wrong thing at machine speed. Send this to someone building ‘fully autonomous’ agents.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Map pin lands | `ROUTE ≠ TRUTH ≠ AUTHORITY` | `p07_map_pin.png`: center-left, 38% | VO hook |
| 00:03.0–00:09.0 | Four cards advance | `ROUTE` → `SOURCE` → `VERIFY` → `AUTHORITY` | `p07_four_cards.png`: cards separated, never merged | Four distinct clicks |
| 00:09.0–00:13.0 | Receipt icon appears | `RECEIPT = WHAT RAN` | `p07_receipt.png`: 50% center | Paper/seal SFX |
| 00:13.0–00:17.0 | Red X between receipt and truth | `RECEIPT ≠ TRUTH` | `p07_receipt_not_truth.png`: exact visual inequality | Music drops |
| 00:17.0–00:22.0 | Permission actions line | `PROMOTE • DEPLOY • PUBLISH • SPEND` | `p07_effects_locked.png`: four dim icons behind lock | Subtle alarm chirp |
| 00:22.0–00:26.0 | Human gate fills screen | `HUMAN DISPOSITION` | `p07_human_gate.png`: visible hand/consent gate, no AI crown | Calm finish |
| 00:26.0–00:28.0 | CTA | `CAPABILITY ≠ AUTHORIZATION` | `p07_share_cta.png` | CTA |

**Claim gate:** governance architecture only; do not imply Aura eliminates all unsafe agent behavior.

---

# PROJECT 08 — 28/28 — STILL NOT DONE

**Source part:** 8 — “28/28 passed—and we still refused to call it done”  
**Target duration:** `34.0 s`  
**Cover:** `28/28 — STILL NOT DONE`

## Voiceover master

> “Our arena harness went 28 for 28. Then another worker audited it and found four things we still had to harden. The first executable Arena-of-Arenas surface passed all 28 implemented falsification checks. It also ran 50 recursive handoffs with zero declared-state drift in that bounded test. Easy marketing move? Say ‘100% secure.’ We didn’t. A separate Different-J audit preserved the 28/28 result and still found four material gaps: typed authority/effect validation, identity-currentness binding, sparse-versus-rich materiality, and staleness cross-testing. That is what fail-closed development looks like: keep the pass, keep the counterevidence, narrow the claim. If your benchmark never tells you what it didn’t test, it isn’t finished.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Full-screen result | `28 / 28 ✅` | `p08_28of28.png`: center | One-second triumphant sting |
| 00:03.0–00:05.0 | Freeze; zoom out | `...AND?` | `p08_and_question.png`: center | Hard silence at “then” |
| 00:05.0–00:10.0 | Harness diagram | `28 IMPLEMENTED FALSIFICATION CHECKS` | `p08_check_grid.png`: 28 small checks | Investigative pulse begins |
| 00:10.0–00:14.0 | Handoff loop | `50 HANDOFFS / 0 DECLARED-STATE DRIFT` | `p08_50_handoffs.png`: loop arrows; `BOUNDED TEST` footer | Low ticks |
| 00:14.0–00:17.0 | Marketing temptation card | `NOT “100% SECURE”` | `p08_not_secure_claim.png`: crossed-out marketing badge | Music ducks |
| 00:17.0–00:26.0 | Four gap cards | `AUTHORITY/EFFECT TYPES` / `IDENTITY-CURRENTNESS` / `MATERIALITY` / `STALENESS CROSS-TESTING` | `p08_four_gaps.png`: four separate cards, one per cut | One click per gap |
| 00:26.0–00:31.0 | Three-line close | `KEEP PASS` / `KEEP COUNTEREVIDENCE` / `NARROW CLAIM` | `p08_three_line_rule.png`: center stack | Three drum hits |
| 00:31.0–00:34.0 | CTA | `WHAT DIDN'T YOUR BENCHMARK TEST?` | `p08_benchmark_question.png` | Voice only at end |

**Claim gate:** say `28/28 implemented checks`; never `100% coverage`, `100% secure`, or `all invariants proven`.

---

# PROJECT 09 — EDGE ≠ NO CLOUD

**Source part:** 9 — “Edge AI does not mean ‘no cloud’”  
**Target duration:** `30.0 s`  
**Cover:** `EDGE ≠ NO CLOUD`

## Voiceover master

> “Edge AI doesn’t mean banning the cloud. It means earning the cloud call. The cheap work belongs close to the machine: event intake, state, deterministic routing, metadata checks, bounded hydration, retries, receipts. Then you escalate. If the local substrate can resolve the job, stop there. If it can’t, compile the smallest unresolved question and send that to a specialist model. That gives you a hybrid system: local for repetition and structure, hosted intelligence for real ambiguity. The design target is not ‘zero cloud.’ It’s zero unnecessary cloud. Follow if you want the architecture diagram and the failure-recovery path.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.0 | Split `EDGE` / `CLOUD` | `EDGE ≠ NO CLOUD` | `p09_edge_cloud_split.png`: equal columns; no “versus” | VO hook |
| 00:03.0–00:10.0 | Local cards flow | `EVENTS / STATE / ROUTING / METADATA / HYDRATION / RECEIPTS` | `p09_local_cards.png`: six local cards | Fast dry clicks |
| 00:10.0–00:14.0 | Resolved job terminates locally | `RESOLVED? STOP LOCAL.` | `p09_local_stop.png`: check + stop node | Firm click |
| 00:14.0–00:19.0 | One unresolved card rises | `SMALLEST UNRESOLVED QUESTION` | `p09_unresolved_card.png`: one card, dotted path upward | Airy escalation |
| 00:19.0–00:24.0 | Specialist cloud/model returns bounded answer | `SPECIALIST MODEL FOR REAL AMBIGUITY` | `p09_specialist_return.png`: cloud node + bounded return capsule | Soft return chime |
| 00:24.0–00:27.0 | Hybrid diagram | `LOCAL FOR STRUCTURE / HOSTED FOR AMBIGUITY` | `p09_hybrid.png`: balanced arrows | Music builds slightly |
| 00:27.0–00:30.0 | Close | `ZERO UNNECESSARY CLOUD` | `p09_zero_unnecessary_cloud.png`: center | Firm bass stop; CTA |

**Claim gate:** do not add a verified cloud-offload percentage. The architecture defines how to measure offload; it does not establish a universal percentage.

---

# PROJECT 10 — BUILD A DIFFERENT STACK

**Source part:** 10 — “You do not need permission to invent a different computing model”  
**Target duration:** `35.0 s`  
**Cover:** `BUILD A DIFFERENT STACK`

## Voiceover master

> “If the dominant AI stack was designed by companies with billion-dollar compute budgets, why would you assume their architecture is the only architecture? I’m building Aura from a different starting point: relationships before blobs, source before confidence, local structure before expensive inference, negative space before activation, and human authority at the final gate. Some parts are verified. Some are staged. Some are still hypotheses that deserve to be attacked. That’s the point. A founder without a hyperscaler budget can still ask a better systems question. And a worldview the tech industry underestimates can still produce a serious technical architecture. If you’re a builder, researcher, or founder who wants to challenge the default stack, follow the project and test the claims—not the mythology.”

## Exact edit blueprint

| Time | Picture / cut | Timed text overlay | Transparent PNG layers | Voice / sound |
|---|---|---|---|---|
| 00:00.0–00:03.5 | Face camera, direct | `YOU CAN BUILD A DIFFERENT COMPUTING MODEL` | none | Dry voice |
| 00:03.5–00:09.0 | Old laptop / code / whiteboard montage | `WHY ASSUME THEIR STACK IS THE ONLY STACK?` | `p10_budget_cloud_silhouette.png`: distant cloud/data-center silhouettes | Slow music build begins |
| 00:09.0–00:22.0 | Five principle cards, one per cut | `RELATIONSHIPS > BLOBS` / `SOURCE > CONFIDENCE` / `LOCAL STRUCTURE FIRST` / `NEGATIVE SPACE FIRST` / `HUMAN AUTHORITY FINAL` | `p10_five_principles.png`: five separate transparent cards | One soft hit per principle |
| 00:22.0–00:27.0 | Three columns | `VERIFIED` / `STAGED` / `HYPOTHESIS` | `p10_evidence_states.png`: equal-width columns; no hierarchy | Music ducks; deliberate pacing |
| 00:27.0–00:31.5 | Face camera | `A BETTER SYSTEMS QUESTION DOESN'T REQUIRE A HYPERSCALER BUDGET` | `p10_small_builder.png`: subtle laptop/graph lower-third | Voice leads |
| 00:31.5–00:35.0 | Final CTA | `TEST THE CLAIMS — NOT THE MYTHOLOGY` | `p10_final_cta.png`: center, 82% width | Music removed on final line |

**Claim gate:** founder perspective and invitation only. Do not imply market dominance, monopoly displacement, or existing industry adoption.

---

# Shared transparent PNG production manifest

Create these as **transparent-background** assets. Text-heavy claims should remain editable CapCut text whenever possible; PNGs should carry shapes, icons, arrows, grids, and stable labels only.

| Prefix | Asset family | Transparency / export instruction |
|---|---|---|
| `p01_*` | API meter, local pipeline, model escalation | transparent RGBA; no vendor logos/prices |
| `p02_*` | W1–W9 nodes, capsule cards, telemetry dashboard | gauges blank by default; values added only from receipts |
| `p03_*` | morphology blocks, relational graph | abstract linguistic/system geometry; no sacred/cultural motifs |
| `p04_*` | 3→6→9 path, guard chips, rebase arrow | keep `6:1` and `1.279×` on editable text, not baked PNG |
| `p05_*` | objective card, hydration ladder, UNKNOWN stop | source/hydration structure only |
| `p06_*` | 8-byte handle, L0→L4 hierarchy, SHA seal | benchmark number and `LOCAL SANDBOX` remain editable linked text |
| `p07_*` | route/source/verify/authority cards, human gate | no autonomous-authority symbolism |
| `p08_*` | check grid, handoff loop, gap cards | `BOUNDED TEST` label always paired with handoff metric |
| `p09_*` | edge/cloud split, local cards, escalation | neutral hybrid architecture; no anti-cloud absolute symbol |
| `p10_*` | five principles, evidence-state columns | equal `VERIFIED/STAGED/HYPOTHESIS` columns |

## Layer naming inside CapCut

For every project, rename tracks/clips rather than leaving `Video 1`, `Sticker 2`, etc.:

- `AROLL_<part>_<take>`
- `BROLL_<part>_<scene>`
- `PNG_<part>_<asset>`
- `TXT_<part>_<claim_or_caption>`
- `SFX_<part>_<event>`
- `MUSIC_<part>_<bed>`
- `VO_<part>_MASTER`

This makes later claim corrections surgical: a superseded metric can be replaced without rebuilding the whole edit.

## Human release gate

Before any export is posted publicly:

1. Re-read the source campaign claim guardrail for that part.
2. Confirm every visible number still matches the current evidence artifact.
3. Confirm any target/model/proxy label is visible in the same frame as the number.
4. Confirm the clean export contains no TikTok/Reels watermark.
5. Confirm one CTA only.
6. Confirm cultural material in Project 03 has not acquired generic “tribal” music, sacred imagery, or implied endorsement.
7. If a metric has been superseded, update the editable text layer and leave the underlying reusable PNG neutral.

**FINAL MATERIALIZATION STATE:** `10 CAPCUT BLUEPRINTS COMPLETE / TRANSPARENT PNG LAYER MANIFEST COMPLETE / VOICEOVER MASTERS SOURCE-BOUND / NOT PUBLISHED`
