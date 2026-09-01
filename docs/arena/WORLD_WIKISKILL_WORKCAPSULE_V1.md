# Aura WorldWiki / GPS / WorkCapsule Skill Compiler V1

Status: **D0 / HS1 / NONPROMOTING / STACKED ON EKI-1**

## Objective

Compile Aura's external World map and accumulated agent experience into a small, job-specific WorkCapsule:

```text
Human Intent / Objective
  -> World L0 GPS route
  -> candidate Skill/Capability neighborhood
  -> validation + model/tool compatibility
  -> minimum skill bundle
  -> minimum L0-L4 hydration plan
  -> WorkCapsule hot boundary
  -> execution by a separately authorized owner
  -> immutable experience/evidence
  -> World Wiki pattern consolidation
  -> skill proposal
  -> validation / rollback
  -> persistent skill-impact lineage
```

The compiler is a planning membrane. It does not own source truth, currentness,
skill acceptance, tool admission, WorkCapsule execution, or Gate-10 promotion.

## Two Aura parent surfaces

### EKI-1 / PR #731

External Knowledge Ingress already owns stable external subject identity, mutable
source/evidence generation, official-source resolution, L0-L4 hydration,
K27/coordinate projections, change-driven refresh, and a read-only claim ceiling.

### WorkCapsule current/exact source-binding lineage / PR #562

WorkCapsule already owns a small execution-context projection with exact source
reopenability and explicit CURRENT/STALE/UNKNOWN handling.  This compiler emits a
WorkCapsule skill/hydration manifest; it does not redefine WorkCapsule.

Merged SkillWeaver/Capability Cockpit (PR #58) is inherited implementation
substrate, not a third semantic parent.

## External method pressure: WikiSkill

WikiSkill's useful architectural contribution is the separation of:

1. immutable raw execution experience;
2. persistent, compounding structured knowledge;
3. reusable procedural skills with validation/rollback.

For Aura, there is a fourth runtime projection:

4. **WorkCapsule** — the small hot job context compiled from the larger World.

The important adaptation is that an executing worker does not need the whole
persistent wiki. The Wiki Maintainer / Skill Proposer can inspect broad history;
the worker gets selected skills + L0 route + earned deeper evidence only.

## Four-plane Aura adaptation

### Plane R — Raw / exact experience

Append-only/exact observations and execution evidence:

- arXiv Atom/API responses and exact publication versions;
- GitHub commits/blobs/workflow receipts;
- Hugging Face revisions;
- OpenAlex/Crossref/Semantic Scholar records;
- coding-tool inputs/outputs and exact repository state;
- benchmark traces and negative results;
- community/reddit observations as explicitly lower-authority evidence.

Raw evidence is retained by identity. `Raw != WikiPattern != Skill`.

### Plane W — World Wiki / Atlas

Persistent structured knowledge compiled from raw evidence:

- stable subjects and typed relations;
- version/supersession/currentness lineage;
- patterns, recurrent failures and successful strategies;
- provider/tool capability and failure patterns;
- skill-impact history (proposed / accepted / rejected / superseded);
- negative-space records;
- exact L4 reopen doors;
- K27 / semantic address indexes.

The World Wiki compounds. It may be corrected or superseded, but source history
is not silently destroyed.

### Plane S — Skill / capability registry

Reusable procedural cards:

```text
SkillRouteCard = <
  SkillID,
  SkillGeneration,
  PurposePatternIDs,
  Capabilities,
  RequiredTools,
  SourceKinds,
  MinHydrationLevel,
  CompatibleModelFamilies,
  ValidationGeneration,
  Currentness,
  ProvenanceRefs,
  CostProfile
>
```

Model compatibility is explicit because a useful procedure can transfer across
models while model-specific workarounds can also cause negative transfer.

### Plane C — WorkCapsule hot boundary

A job receives only:

- objective / world identity;
- selected skill identities + procedures;
- required tools;
- bounded World route cards;
- hydration obligations;
- exact reopen refs;
- currentness/validation generations;
- unresolved negative space;
- authority ceiling.

The full wiki and full skill registry stay cold/reopenable.

`LargeReconstructibleWorld + SmallActiveBoundary`.

## World GPS: L0 -> L4

The Google-Maps analogy is operational, not semantic authority.

### L0 — map tile / POI / route door

Enough to answer:

- does a typed object have a known indexed record here?
- what is its stable subject identity?
- which provider/source owns the record?
- what generation is observed?
- where is its K27/address neighborhood?
- what relations/skills/providers are adjacent?
- what L1-L4 doors exist?
- what currentness/authority debt remains?

L0 stays cheap/hot.

### L1 — place card / typed neighborhood

Compact meaning, immediate relations, owner/status, applicability and reason to
hydrate further.

### L2 — route briefing / bounded working context

Objective-conditioned claims, APIs, equations, implementation constraints,
known alternatives and contradictions.

### L3 — rich neighborhood / genealogy / capsule

Detailed synthesis, lineage, dissent, dependencies, security/license concerns,
skill-impact history and exact reopen map.

### L4 — territory / exact evidence

Exact official source, commit/blob/line, publication span, raw experiment,
dataset revision or explicit owner/human disposition.

`L0Pointer != L4Truth`.
`CoordinateResolution != HydrationDepth`.

## Source adapters

Every World provider should implement the same conceptual adapter:

```text
Discover -> StableSubject -> SourceGeneration -> L0 card
         -> cheap currentness check
         -> demand hydrate L1/L2/L3/L4
         -> exact reopen receipt
         -> invalidate only affected generations
```

### arXiv

- L0: normalized arXiv subject/version metadata and API/source doors.
- L1: title/authors/abstract/categories/version relations.
- L2: objective-bounded technical claims/equations/APIs.
- L3: methods/results/limitations/citations/falsifiers.
- L4: exact versioned source/PDF span + digest.

### GitHub

- L0: repository identity, exact current revision, key topology/search doors.
- L1: repo/module purpose and immediate dependency relations.
- L2: objective-bounded files/symbols/diffs/tests.
- L3: rich code/provenance/review/workflow capsule.
- L4: exact commit/blob/file/span/run/job receipt.

### Google Scholar

Google Scholar is a discovery/cross-check surface, not an automated source owner
in EKI-1 because no official ingestion API is admitted there. Scheduled scholarly
World ingestion should prefer provider-supported surfaces such as arXiv,
OpenAlex, Crossref and Semantic Scholar, then resolve to the official source.

`DiscoveryIndex != L4SourceAuthority`.

### Coding tools / agent harnesses

Tool traces enter Raw. Recurrent debugging/build/review patterns enter World
Wiki. Procedures that survive validation become Skill cards. A future
WorkCapsule can retrieve the procedure without replaying the entire old session.

## Negative-space grammar

Aura must know the difference between "not found" and "does not exist".

Recommended dispositions:

```text
KNOWN_PRESENT
KNOWN_ABSENT_AT_SOURCE_GENERATION
UNKNOWN
NOT_INDEXED
NO_ELIGIBLE_SKILL_IN_REGISTRY_GENERATION
STALE_REVERIFY_REQUIRED
SUPERSEDED
```

Hard law:

`SearchMiss != KnownAbsent`.

An absence claim requires a source/generation whose contract can establish that
absence. Otherwise Aura records UNKNOWN/NOT_INDEXED/NO_ELIGIBLE_IN_SNAPSHOT.

## Skill GPS / selection

The D0 implementation uses exact deterministic set cover for at most 20 eligible
skill cards. That is deliberate HyperScale discipline: first contract the
frontier, then solve exactly.

A skill is routable into the capsule only when:

```text
status in {EXISTING, EVOLVED_ACCEPTED}
AND skill currentness == CURRENT
AND model compatibility established
AND required tools exist in the supplied tool-registry generation
AND capability overlap exists
```

The smallest skill-card set that covers the objective is selected; cost is a
deterministic tiebreaker. If the bounded frontier exceeds 20, the compiler fails
with `EXACT_SKILL_FRONTIER_TOO_LARGE_REQUIRES_HYPERSCALE_REDUCTION` instead of
silently switching to a weaker heuristic.

`SkillDiscovery != SkillAcceptance != SkillUseAuthority`.

## Hydration planner

Each selected skill states a minimum evidence depth. Per World subject:

```text
required_level(subject) = max(min_hydration(skill_i))
                          for selected skills applicable to subject.kind
```

If source currentness is not established, currentness revalidation precedes
deeper active hydration.

```text
STALE/UNKNOWN -> REVERIFY_CURRENTNESS
CURRENT + current_level < required_level -> HYDRATE
CURRENT + current_level >= required_level -> REUSE
```

## Logical reusable cognition / route cache

The logical cache key binds full identities, not coordinate shortcuts:

```text
WorldRouteKey = H(
  ObjectiveID || WorldID || RequiredCapabilities || ModelFamily ||
  AvailableTools || SkillRegistryGeneration || ToolRegistryGeneration ||
  AuthorityScope ||
  [(SubjectKey, EvidenceGenerationKey)] ||
  [(SkillID, SkillGeneration, ValidationGeneration)] ||
  HydrationPolicyVersion
)
```

K27 is a neighborhood/index field used to find candidate routes cheaply. It is
not sufficient to validate cache reuse.

Invalidators include:

- source/evidence generation movement;
- skill generation or validation generation movement;
- skill/tool registry movement;
- model family/environment movement;
- authority-scope movement;
- hydration policy movement;
- contradiction/revocation/currentness movement.

`CacheHit != CurrentnessWitness`.
`PersistentCoordinateMemory != NativeTransformerKV`.

## WikiSkill evolution loop inside AuraOS

After separately authorized WorkCapsule execution:

```text
1. Persist exact execution/tool/source evidence in Raw.
2. Wiki Maintainer root-cause analyzes success/failure.
3. Patch World Wiki pattern pages and evolution log.
4. Skill Proposer reads index + relevant patterns + selected raw evidence.
5. Propose one atomic Skill/PURPOSE change.
6. Validate on a bounded task/evidence set.
7. Accept or roll back Skill Layer.
8. Always retain skill-impact outcome in Wiki history.
9. Increment SkillRegistryGeneration only for a material accepted/superseding state.
10. Future WorkCapsules route through the new generation.
```

A rejected skill proposal remains useful Wiki knowledge; it simply does not
become active procedural state.

## Ω8 / eight crystalline lenses

- **W0 provenance:** exact EKI, WorkCapsule, skill/wiki generations.
- **W1 order:** objective -> route -> select -> hydrate -> capsule -> execute -> learn.
- **W2 substitutions:** cache/K27/similarity/wiki detail cannot replace source/currentness/acceptance.
- **W3 contradiction:** registry-order skill injection is falsified; objective-routed selection required.
- **W4 factorization:** identity/currentness/hydration/skill validation/model compatibility/tool admission/effect authority remain separate.
- **W5 synthesis:** WikiSkill persistent learning × Aura GPS/hydration × WorkCapsule hot boundary.
- **W6 quotient:** duplicate patterns/skills collapse by explicit lineage without erasing evidence identity.
- **W7 temporal:** source/skill/tool generation changes invalidate only affected route/capsule state.
- **W8 effect:** execution, mutation, deployment and Gate-10 remain separately authorized.

## Creation Process

GROUND exact parents -> EXPAND provider/skill surfaces -> BIND non-aliasing
schemas -> DISTRIBUTE raw/wiki/skill/capsule planes -> GOVERN currentness and
authority -> PIVOT from giant knowledge store to small job route -> CONTRACT via
exact skill cover and demand hydration -> VERIFY adversarially -> COHERE into a
WorkCapsule route receipt -> SOVEREIGN GATE remains external.

## HyperScale

Scale **addressability**, not hot context.

```text
WorldScale can grow independently of WorkCapsuleSize.
```

The planner should spend more work only when a consequence-bearing unknown is
unresolved. It should not re-embed/re-read the entire World merely because one
source or skill generation changed.

## Current D0 implementation

- `tools/aura_world_skill_workcapsule.py`
- `tests/test_aura_world_skill_workcapsule.py`
- repair to `aura_skill_cockpit_adapter.py` so it returns SkillWeaver's actual
  `find_target_modules()` result instead of the first ten registry entries.

## Claim ceiling

No source truth/currentness, skill acceptance, tool availability authority,
code/model execution, network/provider effect, semantic K27 authority,
native/private transformer KV access, WorkCapsule execution, Gate-10 promotion,
merge/deploy/spend or public/financial/human effect is granted by this compiler.
