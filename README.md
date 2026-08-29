# AuraOS vNext

> [!IMPORTANT]
> **Current convergence branch — 2026-08-29.** This branch is a source-preserving
> fork-and-trim of the historical AuraOS repository. Paper X and its dated
> lineage remain the architectural authority; the repo is being reduced to a
> smaller runtime that can actually enforce the source/currentness/authority,
> regenerative-memory, Arena and proof/receipt laws described there.
>
> Nothing in this branch self-promotes Gate 10. Published bytes and historical
> implementations remain provenance. The branch is meant to be challenged,
> tested and independently reviewed before merge/promotion.

## What AuraOS is now converging toward

AuraOS is a **resident, model-orthogonal guarded consequence compiler** around a
host computer and an inference/model path. It preserves durable semantic state
outside any one model, compiles the smallest lawful world needed for an
objective, performs deterministic/reusable work below the model layer, and wakes
models or swarms only for unresolved reasoning.

```text
Human / Agent Intent
        ↓
source + generation + currentness + authority + success/falsifier
        ↓
Coordinate Memory / LifeOS / Places / current affected cone
        ↓
Resident Cognitive Fabric
exact lookup · FST route · hashes · lineage · tests · cache · R03DD/D2RM paging
        ↓
minimum consequence-complete ReasoningPacket
        ↓
NO MODEL | local model | remote model | tool | peer | earned swarm
        ↓
Construct → Challenge → Verify / Crucible proposal path
        ↓
gated atomic consequence commit
        ↓
ArtifactIntegrationReceipt + HyperDrive SuccessorFrame + exact reopen
```

The high-level law is:

> **Keep the model's attention on the unresolved residual. Let Aura carry the
> bookkeeping, source resolution, compression, testing, coordination and exact
> reconstruction.**

---

# Current architecture in one page

## 1. One Arena substrate, many Arena realizations

There is one governed Arena Engine / consequence plane. Coding, construction,
science, learning, LifeOS, visitor, marketplace and other Arenas are ephemeral
Recipes/realizations over the same source/currentness/authority/receipt laws.
They are not separate brains or truth databases.

A running Arena can dissolve while its accepted artifacts, lineage, receipts,
Coordinate Cognition, dissent, residuals and reopen routes persist.

## 2. Resident Cognitive Fabric

Aura is intended to remain resident on the user's laptop/host **without keeping a
large model permanently hot**. Workspace/local events wake the resident; change
cursors reconcile after downtime; accepted artifacts are automatically routed,
FST-tagged, coordinated, hashed, linked, timestamped and compiled into L0→L4
Coordinate Cognition.

```text
change/event
→ durable idempotent ingress
→ source identity/generation/currentness/authority
→ AutoLineage/AutoRoute + FST + JID/W0 + provenance
→ semantic coordinate + L0→L4 reopen
→ QDKT epistemic state + memory residency
→ timeline/relations/cache/affected cone
→ HyperDrive collapse
→ ArtifactIntegrationReceipt
```

A file existing in Drive is not the same thing as being cognitively integrated.
A cache hit is not truth. A coordinate is not authority.

See [`docs/runtime/RESIDENT_COGNITIVE_FABRIC.md`](docs/runtime/RESIDENT_COGNITIVE_FABRIC.md).

## 3. LifeOS, Place, Space, Visit, Arena, World

Current separation:

```text
AURAOS = source/currentness/authority/routing/proof/runtime constitution
AURA   = conversational/spatial intelligence and interface
LIFEOS = private user-owned continuity graph
PLACE  = persistent governed semantic identity/environment
SPACE  = permission-governed region; child may be delegated without parent disclosure
VISIT  = ephemeral audience/purpose/device realization of a Place
ARENA  = ephemeral objective-specific execution environment
WORLD  = current objective-conditioned semantic + interactive projection
APP    = disposable realization of the World
```

LifeOS can contain goals, commitments, memories, preferences, routines,
relationships, possessions, projects, calendars/plans and private cognitive
coordinates. It is **not a public profile** and is never exposed merely because a
visitor can enter one Space.

## 4. Visitors never mount your Aura Drive

A visitor comes to the AuraOS Front Door and presents an identity/authorization
claim. Aura evaluates the current permission/purpose/audience/generation/expiry
state and, if admitted, compiles a least-disclosure **L0 visitor capsule**.

```text
VISITOR != DRIVE USER
VISIT != MOUNT
PLACE ADDRESS != STORAGE HANDLE
AUTHORIZATION CLAIM != CREDENTIAL DISCLOSURE
L0 CAPSULE != SOURCE CORPUS
PROPOSAL != COMMIT
RENDERING != TRUTH
```

The visitor reconstructs the authorized semantic view **inside an isolated Visit
Arena/sandbox**. They do not receive owner OAuth tokens, local paths, raw source
mounts or direct write authority. Visitor-created work returns as a proposal;
the owner side sanitizes/challenges/tests/verifies it and may then commit or
reject it.

This prevents “visiting a Place” from meaning “write arbitrary files into the
owner's Drive/device.” The branch includes a fail-closed reference validator and
tests in [`aura_vnext/visitor_capsule.py`](aura_vnext/visitor_capsule.py).

Full boundary: [`docs/security/VISITOR_L0_SANDBOX_AND_PLACE_GATE.md`](docs/security/VISITOR_L0_SANDBOX_AND_PLACE_GATE.md).

## 5. Regenerative memory: source once, views regenerate

```text
SOURCE ONCE → COORDINATE ONCE → MANY REGENERABLE VIEWS
```

Aura does not need every byte of history hot in model context.

- **L0→L4 Coordinate Cognition** keeps compact identity/structure/synthesis and
  exact-source reopen layers distinct.
- **R03DD / CapsuleSpec** contributes deterministic compact decision/navigation
  state; the capsule is a projection and source remains canonical.
- **P0-D2RM** keeps both a decision-sufficient basis and an independently rooted
  challenge/defeat basis; HOT/WARM/COLD are residency states, not deletion.
- **Context Crusher/cache machinery** can reduce payload size but is an
  accelerator, not proof that a residual was discharged.
- **HyperDrive** collapses accepted consequence, dissent, residuals and reopen
  handles into a compact successor state without pretending unresolved state
  disappeared.

The model-facing target is minimum **consequence-complete** context, not minimum
tokens at any cost.

## 6. QDKT — Quantum Deep Knowledge Tracing

Aura uses the project term **QDKT / Quantum Deep Knowledge Tracing** for its
knowledge-state tracing and routing lineage. Current software evidence is
classical unless a separately evidenced quantum backend is introduced.

QDKT's vNext role is epistemic:

- what does this worker/model appear to know for this objective?
- what evidence/source generation produced that estimate?
- how uncertain is it?
- what information/skill should be hydrated next?
- which work would be duplicate/correlated rather than independent?

QDKT is **not truth or authority**. Repeated success, numeric symmetry, a high
readiness score or a large worker count cannot authorize crystallization or an
effect.

The historical `aura_qdkt.py` contains an automatic threshold crystallization
path. vNext explicitly does **not** adopt that behavior as constitutional. The
new guarded projection hard-codes `authority=false`, `crystallized=false` and
`promotion_allowed=false`.

See [`docs/research/QDKT_CRUCIBLE_MEMORY_INTEGRATION.md`](docs/research/QDKT_CRUCIBLE_MEMORY_INTEGRATION.md).

## 7. Crucible

The current Arena Crucible implementation is useful and already points in the
right direction: completed experiences are mined for candidates, validated on
independent validation/shadow data and stored only as
`CRYSTALLIZATION_PROPOSED`. It exposes no automatic apply/push/merge authority.

That proposal-only boundary is retained. Crucible proposals still require the
applicable source/currentness/verifier/human gate.

## 8. Long-horizon C81 swarm

“Minimal worker task” means **minimal context and authority**, not one tiny step
per worker. A worker may stay useful across a bounded end-to-end mission:

```text
PLAN → BUILD → TEST → CHALLENGE → REPAIR → RETEST → CHECKPOINT → CONTINUE
```

It stops on success, falsification, genuine human/effect gate, budget,
unrecoverable blocker or a material source/authority/objective invalidator.
Checkpoints and Coordinate Cognition allow a replacement worker to resume without
replaying whole chats.

Physical scale is earned by the independent frontier. The current C81 ceiling is
81 provider workers; calibration sizes such as 1/3/9/27/81 are routing targets,
not proof that those workers are live. AuraOS remains the scheduler.

## 9. Host + inference wrappers

Aura can optimize both the computer path and the model path.

**Host/Substrate Wrapper** chooses among local deterministic code, SQLite,
indexes, CPU/GPU/NPU, storage, network, ephemeral venv/container, model paging,
peer execution and sleeping expensive resources.

**LLM/Inference Wrapper** chooses among exact reuse, direct coordinate hop,
affected-cone hydration, local model, remote model, independent backends or no
model at all.

Both share one Coordinate/source fabric. Model cache, semantic memory and source
truth are separate planes.

## 10. HyperDrive / HyperScale

HyperDrive and HyperScale are bounded semantic/mathematical navigation,
decomposition, collapse and rebase machinery. Their large symbolic horizons are
addresses/stress bounds, not literal worker counts or physical computation
claims. Scale is earned by consequence-changing need.

---

# Cryptography and encryption

Aura's security architecture is **crypto-agile but not homebrew cryptography**.
The staged ARCE lineage explicitly separates architectural provenance from
cryptographic proof and retires the idea that triadic geometry, lattices,
coordinates, interlacing or symbolic complexity provide cryptographic hardness.

```text
AURA GEOMETRY != CIPHER
COORDINATE != SECRET
HASH != AUTHORITY
STANDARD ALGORITHM NAME != CORRECT IMPLEMENTATION
```

Production confidentiality/authentication/signature/key-agreement/storage
profiles must use current reviewed standard primitives through replaceable
adapters, with explicit key custody, generation, rotation, expiry, revocation,
replay protection and migration receipts. The current standards-alignment lineage
includes NIST post-quantum ML-KEM / ML-DSA families and standardized AEAD/hash
primitives where appropriate; exact library/profile selection remains separately
reviewed and benchmarked.

The vNext visitor reference uses SHA-256 only for canonical integrity IDs. It
does not pretend to implement encryption or signatures itself.

---

# Source, timestamp, lineage and currentness law

Every consequence-bearing artifact should be reconstructible as:

```text
source owner
+ provider/immutable locator
+ observed/event time and record time
+ source generation/revision
+ digest / W0 / content identity where applicable
+ FST/semantic coordinate
+ derives_from / supersedes / amends / challenges / verifies relations
+ evidence status + claim ceiling
+ currentness invalidators
+ authority/human gate
+ exact reopen route
+ receipt lineage
```

Historical states remain addressable. A newer rendition does not erase an older
one. Mirrors are typed projections. Currentness is earned at use time.

The vNext Papers I–X registry is in
[`docs/lineage/PAPER_I_X_SOURCE_REGISTRY_2026-08-29.md`](docs/lineage/PAPER_I_X_SOURCE_REGISTRY_2026-08-29.md).
It records the public Papers I–IX and Paper X Rev.3 lineage plus discovered
same-day Paper X successor branches, while explicitly marking variant discovery
as incomplete until provider history/hash reconciliation is exhaustive.

---

# Source-preserving fork-and-trim

The current repository has more than a thousand implementation/support files and
large historical/domain surfaces. Earlier Aura work already produced a bloat
inventory and a Stage-06 four-primitive candidate. vNext uses that work instead
of pretending the repo must be rewritten from zero.

The selection map is [`.aura/VNEXT_CORE_MANIFEST.json`](.aura/VNEXT_CORE_MANIFEST.json):

```text
CORE      — minimal consequence primitives and new security/QDKT guards
ADAPTER   — useful current owners wired around the core
EVIDENCE  — tests/workflows/receipts/benchmarks, not kernel code
RESEARCH  — staged candidates such as R03DD/P0-D2RM/ARCE
LEGACY    — historical implementation not adopted as current constitutional owner
FROZEN    — dated papers/receipts/publication lineage
```

**Classification is not deletion authority.** Git history and source lineage are
preserved. Useful functions are extracted only after tests prove the new seam.

---

# Paper lineage

Current public/citable anchor:

- **Paper X Rev.3** — Zenodo record **22134815**
- DOI: **10.5281/zenodo.22134815**

Current Drive work also contains staged later Paper X successor candidates,
including Rev.4/Rev.4.1 and a same-day `PAPER-X-OMNI-COMPLETE` consolidation.
Those are not silently backdated into Rev.3. Publication status, measured
runtime evidence, exact mathematics, staged research and deployed behavior remain
separate evidence classes.

Papers I–IX remain part of the dated prior-art/architecture lineage and are
allocated in the source registry rather than summarized away.

---

# Gate 10

This branch is intended to move the architecture **up to the Gate-10 boundary**,
not declare Gate 10 by fiat. Current readiness and owed evidence are tracked in
[`docs/gate10/GATE10_READINESS.md`](docs/gate10/GATE10_READINESS.md).

Required high-value live trials include:

1. source change → automatic integration receipt → stale-cache refusal → minimal
   regeneration;
2. resident restart/offline backlog reconciliation;
3. exact ChatGPT → Aura → worker → command-bound ACK/RESULT loop;
4. long-horizon worker defect injection → repair/retest/checkpoint → replacement
   worker exact resume;
5. independent visitor-sandbox and crypto threat review;
6. fresh Paper/claim/source-currentness collision audit;
7. different-agent review and human disposition where required.

A pass count, QDKT readiness score, coordinate, symbolic horizon or swarm size is
never a substitute for those gates.

---

# Repository entry points for vNext work

- `06_refactor/aura_os_minimal.py` — existing Stage-06 four-primitive candidate
- `aura_vnext/visitor_capsule.py` — tested no-mount visitor boundary
- `aura_vnext/qdkt_guard.py` — non-authoritative/no-auto-crystallization QDKT projection
- `aura_arena_crucible.py` — proposal-only current Crucible owner
- `.aura/VNEXT_CORE_MANIFEST.json` — fork/trim selection map
- `docs/architecture/AURAOS_VNEXT_CONVERGENCE_2026-08-29.md`
- `docs/runtime/RESIDENT_COGNITIVE_FABRIC.md`
- `docs/security/VISITOR_L0_SANDBOX_AND_PLACE_GATE.md`
- `docs/research/QDKT_CRUCIBLE_MEMORY_INTEGRATION.md`
- `docs/lineage/PAPER_I_X_SOURCE_REGISTRY_2026-08-29.md`
- `docs/gate10/GATE10_READINESS.md`

## Design shorthand

```text
SOURCE ONCE → COORDINATE ONCE → MANY REGENERABLE VIEWS
MINIMAL CONTEXT → MAXIMAL USEFUL HORIZON → DURABLE CHECKPOINTS → EXACT REOPEN
EVENTS WAKE → CURSORS RECONCILE → CURRENTNESS IS EARNED
VISITORS RECONSTRUCT AUTHORIZED VIEWS → THEY DO NOT MOUNT OWNER STORAGE
QDKT ROUTES LEARNING → CRUCIBLE PROPOSES → VERIFICATION/AUTHORITY DECIDE
```

## Founder & contact

**Dallas Fabian Courchene-Martin**  
Founder, AuraOS  
Long Plain First Nation, Treaty 1 Territory, Manitoba, Canada  
Contact: aura.os.q@gmail.com
