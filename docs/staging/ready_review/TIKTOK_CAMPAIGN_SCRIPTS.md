# TikTok / Reels Campaign Scripts — WO-TRIAD2-TIKTOK-CAMPAIGN-004

**Worker:** W4  
**State:** STAGING / READY_REVIEW / HUMAN GATE 1 REQUIRED  
**File target:** `docs/staging/ready_review/TIKTOK_CAMPAIGN_SCRIPTS.md`  
**Audience:** AI builders, tech enthusiasts, underrepresented founders  
**Format:** 10-part vertical short-form campaign, cross-postable to TikTok and Instagram/Facebook Reels

> **Claim boundary:** This package is written for attention and clarity, not to convert hypotheses into facts. Hooks may be provocative, but the spoken body must preserve the evidence state. Where an exact cost, hardware, agent-count, or performance result is not source-bound, the script presents it as an experiment, design target, or question rather than a completed result.

---

## Platform production contract

Use these rules across all ten videos:

- Shoot **9:16 vertical**, at least **720p**, and keep faces, captions, numbers, and CTAs inside UI-safe zones.
- Deliver the proposition in the **first ~3 seconds** and make the opening hook work inside the first **3–6 seconds**.
- Use a real human voice/face whenever possible. Prefer native, direct, slightly rough creator footage over glossy corporate production.
- Keep sound intentional: voice first, low-volume music bed second, sound effects only where they reinforce cuts or proof moments.
- Burn in captions. For large on-screen copy, keep the reading load roughly in the range of **5–10 words per second**.
- Use quick scene changes, punch-ins, screen recordings, physical props, and text emphasis to reset attention without turning the video into visual noise.
- End with one clear CTA. Do not stack “follow / comment / share / visit / subscribe” into one closing.
- Treat “algorithm optimization” as **test-and-learn**, not certainty. Produce alternate hooks/covers for the strongest concepts and compare retention, rewatches, shares, saves, profile taps, and qualified comments.
- For Reels, preserve 9:16, audio, captions, and safe-zone placement rather than exporting a TikTok UI recording with embedded watermarks.

Official creative guidance used for this staging draft:
- TikTok for Business — Creative best practices: https://ads.tiktok.com/help/article/creative-best-practices?lang=en
- TikTok Creative Codes: https://ads.tiktok.com/business/en/creative-codes
- Meta for Business — Reels ads creative guidance: https://www.facebook.com/business/ads/facebook-instagram-reels-ads

### Campaign pacing target

Default runtime: **22–35 seconds**.  
Default beat pattern:
1. **0:00–0:03 — Hook**
2. **0:03–0:18 — Story / tension**
3. **0:18–0:28 — Proof / mechanism**
4. **0:28–0:35 — Offer / CTA**

Not every clip must use every second. If the story lands in 18–22 seconds, stop.

---

# PART 1 — “Why cloud AI pricing becomes a trap”

**Primary audience:** AI builders / indie developers  
**Goal:** Establish the problem: paying a hosted model to make every tiny decision is an architectural choice, not an inevitability.  
**Runtime:** 25–30s  
**H-S-O:** Hook → Cost architecture story → Follow for the local-first series

### Hook
**Spoken:**  
“Cloud AI gets expensive for one stupid reason: we keep paying a giant model to make tiny decisions.”

**On-screen text:**  
`THE CLOUD AI TRAP: paying premium inference for cheap decisions`

### Story / script
“Most AI systems send everything upward: routing, lookup, classification, memory retrieval, even questions the software could answer deterministically.

That means every little decision can become another metered model call.

Aura flips that order.

First: route locally.  
Then: resolve the smallest source neighborhood.  
Then: call a heavyweight model only when the problem is actually unresolved.

The goal isn’t ‘never use the cloud.’ The goal is: **don’t rent intelligence for work a deterministic substrate can already do.**”

### Offer / CTA
“If you build agents, follow this series. I’m going to show the pieces one by one.”

### Visual storyboard
- **0:00–0:02:** Face camera. Hold up a phone with a fake “API BILL ↑” graphic.
- **0:02–0:05:** Smash cut to simple flow: `EVERYTHING → BIG MODEL`.
- **0:05–0:10:** Red dollar/tokens counter ticking upward.
- **0:10–0:16:** Replace with Aura flow: `ROUTE → SOURCE → LOCAL RULE → MODEL IF NEEDED`.
- **0:16–0:24:** Screen capture / handwritten whiteboard showing “smallest sufficient world.”
- **0:24–0:30:** Face camera + CTA.

### Audio pacing
- 0–3s: no intro music; voice hits immediately.
- 3–12s: restrained percussive pulse at low volume.
- 12–20s: one “click” sound per pipeline stage.
- Final CTA: drop music 2–3 dB so the voice lands cleanly.

### Edit notes
Punch in on “tiny decisions,” “route locally,” and “only when unresolved.”

### A/B hook
A: “Your AI bill isn’t just a pricing problem. It’s an architecture problem.”  
B: “If every decision hits an LLM, you built a meter—not an operating system.”

### Claim guardrail
Do not quote a vendor price or a savings percentage unless a current audited cost comparison is attached to the post.

---

# PART 2 — “Nine AI workers. One old laptop. Pennies?”

**Primary audience:** AI builders / tech enthusiasts  
**Goal:** Turn the requested “9 agents on an old laptop for pennies” angle into a falsifiable build target instead of an unsupported result.  
**Runtime:** 24–32s

### Hook
**Spoken:**  
“Nine AI workers. One old laptop. Pennies. Sounds fake—so here’s the rule: don’t claim it until the telemetry proves it.”

**On-screen text:**  
`9 WORKERS / OLD LAPTOP / PENNIES? → TEST IT, DON'T HYPE IT`

### Story / script
“What we’re actually building is a local-first orchestration layer where workers don’t each need to carry the whole world.

They get a coordinate, a bounded job, the smallest relevant context, and a receipt.

The cheap part should be deterministic routing, state tracking, source lookup, and local housekeeping.

The expensive model call becomes the exception.

We already have staged evidence for that architecture. What we do **not** have in this work order is a source-bound proof that nine concurrent workers on an old laptop cost ‘pennies.’

So that number stays a benchmark target until CPU, RAM, model, wall-time, and actual provider spend are captured.”

### Offer / CTA
“Want the benchmark when it’s real? Comment `9X` and I’ll post the exact test design.”

### Visual storyboard
- **0:00–0:03:** Old laptop on desk; nine sticky notes labeled W1–W9.
- **0:03–0:07:** Text stamp: `CLAIM ≠ PROOF`.
- **0:07–0:15:** Animate each worker receiving a tiny capsule instead of a huge document stack.
- **0:15–0:23:** Overlay telemetry placeholders: `RSS / CPU / TOKENS / $ / WALL TIME`.
- **0:23–0:30:** Face camera: “benchmark target, not marketing fact.”

### Audio pacing
- Open with laptop fan / keyboard sound.
- Beat enters only after “sounds fake.”
- Use nine fast click ticks as W1–W9 appear.
- End dry/no music on “until the telemetry proves it.”

### A/B hook
A: “Could nine AI agents run on hardware you already own?”  
B: “I don’t want nine AI agents in nine clouds. I want nine bounded workers on one cheap machine.”

### Claim guardrail
Never publish “nine agents for pennies” as a completed result until a reproducible run captures exact hardware, models, concurrency, wall time, energy/provider costs, and memory.

---

# PART 3 — “Indigenous innovation can challenge the default AI stack”

**Primary audience:** Underrepresented founders / builders / tech culture audience  
**Goal:** Make the cultural origin a technical story, not decoration.  
**Runtime:** 28–35s

### Hook
**Spoken:**  
“What if one of the most interesting attacks on centralized AI infrastructure comes from an Indigenous way of thinking about relationships?”

**On-screen text:**  
`INDIGENOUS INNOVATION ≠ BRANDING. IT CHANGED THE ARCHITECTURE.`

### Story / script
“Aura’s history starts with Indigenous language work and the structure of polysynthetic language—where meaning is built through relationships, roles, and composition.

That pushed a different engineering question:

Why keep throwing giant blobs of context at a model when the system can compile the relationships that matter for one objective?

That becomes routing.  
Bounded hydration.  
Source lineage.  
Negative space—what must *not* be activated.  
And human authority that cannot be invented by the machine.

For underrepresented founders, that matters: your worldview doesn’t have to be the ‘story around’ the technology.

It can shape the technology itself.”

### Offer / CTA
“If you’re building from a worldview the industry usually ignores, follow. I want to see what architecture comes out of it.”

### Visual storyboard
- **0:00–0:03:** Face camera, quiet background.
- **0:03–0:08:** Handwritten word fragments / morphology blocks joining into one structured unit.
- **0:08–0:15:** Morphology blocks morph into software nodes/relations.
- **0:15–0:23:** Four words appear one at a time: `ROUTING / LINEAGE / NEGATIVE SPACE / HUMAN GATE`.
- **0:23–0:32:** Return to face, direct delivery.

### Audio pacing
- Warm, minimal pulse. No “tribal” stock music.
- Let voice carry the cultural material.
- Use subtle percussive clicks only for architecture terms.

### A/B hook
A: “My Indigenous background didn’t become a logo on the AI. It changed how I designed the AI.”  
B: “Diversity in tech gets real when worldview changes architecture—not just the founder photo.”

### Claim guardrail
Do not claim any Indigenous language community formally endorses Aura. Distinguish historical inspiration and documented design genealogy from linguistic validation or community authorization.

---

# PART 4 — “The 3-6-9 rhythm of edge computing”

**Primary audience:** Tech enthusiasts / systems builders  
**Goal:** Make the numeric motif memorable while explicitly de-mystifying it.  
**Runtime:** 24–30s

### Hook
**Spoken:**  
“3-6-9 sounds like numerology. In our router, it’s much less mystical—and much more useful.”

**On-screen text:**  
`3 → 6 → 9 = ROUTING LABEL, NOT MAGIC`

### Story / script
“In one staged Aura router, the normal path takes six logical transitions.

A guarded diagonal path can collapse that to one transition—but only when every required guard is already verified and the negative-space boundaries are conflict-free.

So the memorable part is ‘3-6-9.’

The engineering part is this:

**six logical steps versus one eligible rebase.**

And here’s the honesty clause: that is a **6:1 transition-count ratio**, not a 6× speed claim.

The recorded local wall-clock run was only about **1.279×** faster.

Structure first. Measurement second. Myth never.”

### Offer / CTA
“Follow for the actual state machine behind the shortcut.”

### Visual storyboard
- **0:00–0:03:** Large `3 6 9 ?` fills screen.
- **0:03–0:06:** Red stamp `NOT NUMEROLOGY`.
- **0:06–0:13:** Animate six nodes in a line.
- **0:13–0:18:** Diagonal arrow jumps to destination.
- **0:18–0:23:** Split-screen numbers: `LOGICAL 6:1` vs `LOCAL WALL CLOCK ~1.279×`.
- **0:23–0:30:** Face camera: “Structure first. Measurement second.”

### Audio pacing
- Six evenly spaced ticks for the linear path.
- One bass click for the diagonal.
- Silence under the “not a 6× speed claim” line.

### A/B hook
A: “Here’s the 3-6-9 thing without the mystical nonsense.”  
B: “A six-step state path became one step—but only under hard guards.”

### Claim guardrail
Keep “3-6-9” explicitly framed as a generation-specific routing/dispatch label. Do not call it a universal law.

---

# PART 5 — “Stop feeding AI the whole world”

**Primary audience:** AI builders / RAG and agent developers  
**Goal:** Introduce Aura’s compact L0 operating law.  
**Runtime:** 22–28s

### Hook
**Spoken:**  
“Most AI context engineering starts with the wrong instinct: ‘give the model everything.’”

**On-screen text:**  
`DON'T FEED THE SYSTEM THE WORLD`

### Story / script
“Our operating rule is almost the opposite:

**Compile the smallest source-resolvable relational world sufficient for the objective.**

If the job is one file, don’t hydrate the repository.

If the answer is in metadata, don’t load the body.

If a deterministic route resolves the next step, don’t call a model.

And if the source is missing, stop UNKNOWN instead of hallucinating a bridge.

Smaller context isn’t the goal by itself.

**Sufficient context with exact source descent is the goal.**”

### Offer / CTA
“Save this if you build RAG or agents. It’s a better design question than ‘how big is my context window?’”

### Visual storyboard
- **0:00–0:03:** Dump a huge stack of paper onto desk.
- **0:03–0:06:** Push 95% aside.
- **0:06–0:12:** Keep one card labeled `OBJECTIVE`.
- **0:12–0:20:** Animate `metadata → L0 → L1 → source only if needed`.
- **0:20–0:27:** On-screen quote of the operating law.

### Audio pacing
- Loud paper thump at open.
- Sparse click track.
- Slight pause before the full operating law.

### A/B hook
A: “Your context window is not a garbage truck.”  
B: “The best RAG optimization might be deciding what never gets retrieved.”

### Claim guardrail
Do not convert this architectural principle into a universal token-savings percentage unless the specific benchmark is attached.

---

# PART 6 — “An 8-byte handle can lead back to exact source”

**Primary audience:** Systems / database / AI infrastructure audience  
**Goal:** Explain lossless hydration without implying arbitrary data compression into eight bytes.  
**Runtime:** 25–32s

### Hook
**Spoken:**  
“No, we did not compress 256 kilobytes of arbitrary data into eight magic bytes.”

**On-screen text:**  
`8 BYTES ≠ MAGIC COMPRESSION`

### Story / script
“We built a staged hydration transducer where L0 is an **8-byte record handle**.

That handle resolves through a source-bound hierarchy back to exact L4 bytes, and SHA-256 verifies recovery.

In the repaired N2 generation, **25 of 25 tests passed**, including the zero-byte eviction edge case.

Across local sandbox fixtures, hot L0-to-L4 median recovery landed around **50.79 to 65.88 microseconds**.

The important distinction:

the eight bytes are a **handle into a verified source system**.

They are not a claim that arbitrary source content lives inside eight bytes.”

### Offer / CTA
“If you care about AI memory without hand-wavy compression claims, follow the hydration series.”

### Visual storyboard
- **0:00–0:03:** Hold tiny index card labeled `8 bytes`.
- **0:03–0:08:** Draw arrow from card to a file cabinet / content-addressed store.
- **0:08–0:15:** Overlay `L0 → L1 → L2 → L3 → L4 exact bytes`.
- **0:15–0:21:** `25/25 PASS` flashes.
- **0:21–0:27:** `50.79–65.88 µs LOCAL SANDBOX` in safe zone.
- **0:27–0:32:** Face camera: “handle, not magic compression.”

### Audio pacing
- Tiny “ping” on the 8-byte card.
- Rising clicks through L0–L4.
- Stop music briefly on “not a claim.”

### A/B hook
A: “Eight bytes can find the exact source—without pretending eight bytes *are* the source.”  
B: “This is what ‘lossless hydration’ means when you remove the marketing language.”

### Claim guardrail
Always retain “local sandbox microbenchmark” next to the microsecond figures. Do not present them as production, mobile, Drive, or provider latency.

---

# PART 7 — “Routing is not truth”

**Primary audience:** Agent builders / AI safety / infrastructure  
**Goal:** Turn Aura’s governance separation into a memorable builder rule.  
**Runtime:** 22–28s

### Hook
**Spoken:**  
“An AI can know where to go and still have zero authority to act.”

**On-screen text:**  
`ROUTE ≠ TRUTH ≠ AUTHORITY`

### Story / script
“This is one of the rules I wish every agent framework enforced.

A coordinate can tell you where something is.

A router can tell you which path is valid.

A receipt can tell you what ran.

None of those things automatically make the result true.

And none of them give the worker permission to promote, deploy, publish, or spend.

Aura separates addressability, source, currentness, verification, and human disposition.

That sounds bureaucratic—until your agent confidently does the wrong thing at machine speed.”

### Offer / CTA
“Send this to someone building ‘fully autonomous’ agents.”

### Visual storyboard
- **0:00–0:03:** Map pin appears, then giant `≠ PERMISSION`.
- **0:03–0:11:** Rapid cards: `ROUTE`, `SOURCE`, `VERIFY`, `AUTHORITY`.
- **0:11–0:18:** Red X over `receipt → truth`.
- **0:18–0:25:** Human Gate graphic with lock icon.

### Audio pacing
- Four distinct clicks for the four cards.
- Alarm chirp on “wrong thing at machine speed.”
- Calm finish.

### A/B hook
A: “Your agent found the file. Congratulations. That still doesn’t mean it can touch it.”  
B: “Capability is not authorization. Agent frameworks keep confusing the two.”

### Claim guardrail
This video is architecture/governance explanation, not a claim that Aura eliminates all unsafe agent behavior.

---

# PART 8 — “28/28 passed—and we still refused to call it done”

**Primary audience:** Builders / security-minded developers  
**Goal:** Demonstrate fail-closed culture and adversarial testing.  
**Runtime:** 26–34s

### Hook
**Spoken:**  
“Our arena harness went 28 for 28. Then another worker audited it and found four things we still had to harden.”

**On-screen text:**  
`28/28 PASS ≠ "WE'RE DONE"`

### Story / script
“The first executable Arena-of-Arenas surface passed all **28 implemented falsification checks**.

It also ran **50 recursive handoffs with zero declared-state drift** in that bounded test.

Easy marketing move? Say ‘100% secure.’

We didn’t.

A separate Different-J audit preserved the 28/28 result and still found four material gaps: typed authority/effect validation, identity-currentness binding, sparse-versus-rich materiality, and staleness cross-testing.

That is what fail-closed development looks like:

**keep the pass, keep the counterevidence, narrow the claim.**”

### Offer / CTA
“If your benchmark never tells you what it *didn’t* test, it isn’t finished.”

### Visual storyboard
- **0:00–0:03:** `28/28 ✅` fills screen.
- **0:03–0:05:** Freeze frame; add `...AND?`
- **0:05–0:12:** `50 handoffs / 0 declared-state drift` appears.
- **0:12–0:22:** Four hardening gaps appear one per cut.
- **0:22–0:30:** Three-line close: `KEEP PASS / KEEP COUNTEREVIDENCE / NARROW CLAIM`.

### Audio pacing
- Triumphant sting for first second only, then hard cut to silence at “then.”
- Low investigative pulse during four gaps.
- Three drum hits on final three-line close.

### A/B hook
A: “The most important result after 28/28 PASS was the audit that said ‘not enough.’”  
B: “A 100% pass rate can still be an incomplete test.”

### Claim guardrail
Say “28/28 implemented checks,” not “100% coverage,” “100% secure,” or “all invariants proven.”

---

# PART 9 — “Edge AI does not mean ‘no cloud’”

**Primary audience:** Builders skeptical of local/edge absolutism  
**Goal:** Present the hybrid operating model.  
**Runtime:** 24–30s

### Hook
**Spoken:**  
“Edge AI doesn’t mean banning the cloud. It means earning the cloud call.”

**On-screen text:**  
`LOCAL FIRST. CLOUD WHEN NECESSARY.`

### Story / script
“The cheap work belongs close to the machine:

event intake, state, deterministic routing, metadata checks, bounded hydration, retries, receipts.

Then you escalate.

If the local substrate can resolve the job, stop there.

If it can’t, compile the smallest unresolved question and send **that** to a specialist model.

That gives you a hybrid system:

local for repetition and structure, hosted intelligence for real ambiguity.

The design target is not ‘zero cloud.’

It’s **zero unnecessary cloud.**”

### Offer / CTA
“Follow if you want the architecture diagram and the failure-recovery path.”

### Visual storyboard
- **0:00–0:03:** Split screen `EDGE` / `CLOUD`; X over “VERSUS.”
- **0:03–0:12:** Local pipeline cards.
- **0:12–0:18:** One unresolved card rises to cloud icon.
- **0:18–0:25:** Cloud returns bounded answer/receipt.
- **0:25–0:30:** Text: `ZERO UNNECESSARY CLOUD`.

### Audio pacing
- Local sequence uses fast dry clicks.
- One airy transition when escalation occurs.
- Close with firm bass stop.

### A/B hook
A: “Local AI versus cloud AI is the wrong fight.”  
B: “Don’t ask ‘cloud or edge?’ Ask ‘what deserves an expensive model call?’”

### Claim guardrail
Do not state a verified offload percentage. Existing local-runtime work defines how to measure offload but does not prove a universal percentage.

---

# PART 10 — “You do not need permission to invent a different computing model”

**Primary audience:** Underrepresented founders / open-source builders / broad audience  
**Goal:** Close the campaign with identity, invitation, and a clear offer.  
**Runtime:** 28–35s

### Hook
**Spoken:**  
“If the dominant AI stack was designed by companies with billion-dollar compute budgets, why would you assume their architecture is the only architecture?”

**On-screen text:**  
`YOU CAN BUILD A DIFFERENT COMPUTING MODEL`

### Story / script
“I’m building Aura from a different starting point:

relationships before blobs,  
source before confidence,  
local structure before expensive inference,  
negative space before activation,  
and human authority at the final gate.

Some parts are verified.

Some are staged.

Some are still hypotheses that deserve to be attacked.

That’s the point.

A founder without a hyperscaler budget can still ask a better systems question.

And a worldview the tech industry underestimates can still produce a serious technical architecture.”

### Offer / CTA
“If you’re a builder, researcher, or founder who wants to challenge the default stack, follow the project and test the claims—not the mythology.”

### Visual storyboard
- **0:00–0:03:** Face camera, direct eye contact.
- **0:03–0:10:** B-roll of old laptop, code, whiteboard, handwritten graph.
- **0:10–0:22:** Five principles appear one per cut.
- **0:22–0:28:** `VERIFIED / STAGED / HYPOTHESIS` three-column overlay.
- **0:28–0:35:** Face camera CTA.

### Audio pacing
- Start dry.
- Slow build under principles.
- Remove music on “test the claims—not the mythology.”

### A/B hook
A: “You don’t need a data center to challenge a data-center architecture.”  
B: “The next computing model does not have to come from the richest lab.”

### Claim guardrail
Keep this as founder perspective and invitation. Do not imply market dominance, monopoly displacement, or industry adoption has already occurred.

---

# Campaign sequencing and testing plan

## Release order
Recommended order:
1. Cloud pricing architecture
2. Nine-worker benchmark target
3. Stop feeding AI the whole world
4. 3-6-9 routing
5. 8-byte hydration
6. Routing is not truth
7. 28/28 + counterevidence
8. Edge ≠ no cloud
9. Indigenous innovation changes architecture
10. Different computing model / invitation

This sequencing alternates broad pain points with proof-oriented technical pieces so the feed does not become ten consecutive jargon explainers.

## Packaging
For each post:
- cover = 3–6 words, large type, high contrast;
- first spoken sentence starts immediately;
- captions always on;
- one proof number maximum in the first half unless the video is explicitly benchmark-focused;
- one CTA only;
- description: 1–3 short lines, then a few topic-relevant tags rather than a keyword wall;
- pin a correction/source note if a posted claim is later superseded.

## Suggested covers
1. `THE CLOUD AI TRAP`
2. `9 AGENTS. OLD LAPTOP?`
3. `DON'T FEED AI THE WORLD`
4. `3-6-9 WITHOUT THE MYTH`
5. `8 BYTES → EXACT SOURCE`
6. `ROUTING IS NOT TRUTH`
7. `28/28 — STILL NOT DONE`
8. `EDGE ≠ NO CLOUD`
9. `INDIGENOUS IDEAS → ARCHITECTURE`
10. `BUILD A DIFFERENT STACK`

## Metric interpretation
Prioritize:
- 3-second hold / early retention;
- average watch time and completion;
- rewatches;
- saves and shares;
- profile taps;
- qualified comments from builders;
- follows attributable to the series.

Do not chase raw views at the expense of claim quality. If a high-performing hook produces repeated misunderstanding, rewrite the hook.

## Creative test matrix
For Parts 1, 2, 4, 8, and 10:
- Variant A: face-first / direct claim.
- Variant B: prop or screen-first / curiosity.
- Keep the body materially identical.
- Change only hook and opening visual for the first test.
- If a winner emerges, then test CTA separately.

---

# Evidence / non-claim ledger for Human Gate 1

| Campaign element | Staging treatment |
|---|---|
| “Cloud AI pricing is a trap” | Rhetorical framing about architecture; no vendor pricing or universal savings claim. |
| “9 agents on an old laptop for pennies” | **Not source-bound as completed result.** Reframed as benchmark target/experiment. |
| Local-first routing / bounded hydration | Supported as Aura design and staged implementation direction. |
| W2 FST | Source-bound staging evidence: 20/20 original tests; successor 35/35 total. |
| 3-6-9 diagonal | Source-bound as a routing label with 6:1 logical transition-count ratio under guards; not a universal law. |
| 3-6-9 speed | Recorded local wall-clock ratio ~1.279×; do not say 6× speed. |
| W3 hydration | N2 25/25 staged tests; local hot medians 50.79–65.88 µs over recorded fixtures. |
| 8-byte L0 | Record handle resolving source-backed L4; not arbitrary 8-byte compression. |
| W4 Arena | Historical 28/28 implemented checks; 50 recursive handoffs with 0 declared-state drift in bounded test; later audit found four material hardening gaps. |
| Indigenous innovation | Present as documented design genealogy/founder perspective; no community endorsement or linguistic-validation claim. |
| Edge/mobile economics | Architectural target; exact “pennies,” safe concurrency, energy, and total cost require runtime telemetry. |
| Human-gated governance | Architectural rule; no claim that it makes all agent actions safe. |

---

# Human Gate 1 checklist

Before approval for production/publication:

- [ ] Confirm founder voice and cultural framing.
- [ ] Confirm whether “9 workers / old laptop / pennies” remains benchmark framing or has new telemetry that upgrades it.
- [ ] Confirm every displayed benchmark number against its current source generation.
- [ ] Confirm W4 hardening status has not superseded the historical 28/28 wording.
- [ ] Confirm current repo/license/public-link language if any link is added to captions.
- [ ] Choose whether the CTA points to follow, GitHub, Paper X, email list, or another approved destination.
- [ ] Recheck TikTok/Reels UI safe zones in the current editing tool.
- [ ] Choose platform-licensed / commercially permitted audio at publishing time.
- [ ] Approve final captions, hashtags, thumbnails, and posting order.
- [ ] Human Gate 1 disposition recorded before public distribution.

**PROMOTION STATE:** `READY_REVIEW / NOT APPROVED / NOT PUBLISHED`
