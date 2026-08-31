# Aura External Knowledge Ingress V1

Status: D0 / HS1 / NONPROMOTING

## Objective EKI-1

Mission: make external research, repositories, models, datasets, tools, benchmark suites, documentation, and practitioner evidence cheap to discover and reuse while preserving exact source identity, currentness, verification, license/security state, and effect authority.

Residual:

`ExternalSourceSnapshot + PolysyntheticHydration != LawfulReusableKnowledgeUntil StableSubjectIdentity + EvidenceGeneration + SourceCurrentness + ValidationFingerprint + HydrationLevel + ExactSourceHandle + CapabilityUseCeiling + CoordinateProjection Commute`.

This work operationalizes the earlier Aura idea of shallow L0/L1/L2 research cards with exact source pointers, but does not treat an automatically generated summary as verified source truth. Discovery, hydration, verification, currentness, and tool execution are distinct state planes.

## Existing Aura owners consumed rather than duplicated

This membrane composes with, rather than replaces, existing Aura laws:

- A2 dual-key evidence generation: stable semantic consequence identity and mutable evidence/currentness generation are separate.
- A5 semantic-generation freshness: observation/materialization time cannot reset the semantic source clock.
- O62/lifecycle/currentness work: source freshness and effect authority must be revalidated at the use boundary.
- HyperDrive: coordinates link to source-resolvable records; coordinates never duplicate truth or mint authority.

## Provider matrix

| Provider | Discovery generation | Currentness/reopen anchor | Default use |
| --- | --- | --- | --- |
| arXiv | exact version ID | exact version URL + metadata digest | research reference |
| GitHub | exact commit SHA | immutable tree URL + repo metadata | repository/tool discovery |
| Hugging Face | exact repo SHA | immutable repo tree URL + Hub metadata | model/dataset/Space discovery |
| OpenAlex | provider updated timestamp | OpenAlex work ID + metadata digest | scholarly discovery/crosswalk |
| Crossref | provider index/deposit timestamp | DOI + metadata digest | DOI/current metadata crosswalk |
| Semantic Scholar | metadata-generation digest when no native update generation is exposed | paper ID + exact source URL | scholarly discovery/cross-check |
| Google Scholar | no automated adapter | manual/discovery cross-check only | no scraping / no currentness authority |
| Reddit/web | advisory observation | exact URL + observation/content digest | practitioner/falsification pressure |

Google Scholar is deliberately not scraped by the PowerShell/Python adapter. It has no first-party public automation API suitable for this ingestion owner. Aura should use provider-supported scholarly APIs for scheduled ingestion and use Scholar only as an optional human/search cross-check.

## L0 -> L4 demand-paged hydration

Hydration is a cost/resolution choice, not a truth rank.

- **L0 Orientation:** title, provider, kind, stable subject ID, exact provider generation, exact source handle, one short source-bound thesis if available.
- **L1 Purpose:** problem, domain, intended capability, project relevance. Derived summaries remain explicitly derived.
- **L2 Technical synthesis:** core claims, equations, APIs, interfaces, empirical deltas, compatibility surface. L2 is not automatically verified merely because it is detailed.
- **L3 Dependencies/falsifiers:** citations, dependency versions, license/security constraints, invalidators, known contradictions, currentness owners.
- **L4 Exact source:** immutable/versioned repository tree, paper/version URL, DOI/source object, source digest, or other exact reopenable source handle.

The minimal-hydration rule is:

`HydrateTo(L_n) iff ExpectedDecisionValue(L_n) > FetchCost + VerificationCost + StalenessRisk + ReworkRisk`.

The rule is typed: token cost, network cost, time, and effect risk are not added as if they were one physical unit. Implementations may use normalized planning weights, but raw measurements remain separate evidence dimensions.

## State machine

Provider discovery is intentionally weaker than current read-only reuse:

1. `DISCOVERED_UNVERIFIED`
2. `SOURCE_RESOLVED`
3. `METADATA_VERIFIED`
4. `CONTENT_VERIFIED`
5. `CURRENT_REFERENCE`
6. `STALE_REVERIFY_REQUIRED`
7. `INVALIDATED`

The current implementation performs a low-friction two-observation transition for exact provider revisions:

`ExactDiscovery -> METADATA_VERIFIED`

then:

`SecondMatchingExactGeneration -> CURRENT_REFERENCE`

A different evidence generation produces `STALE_REVERIFY_REQUIRED`; a different stable subject produces `INVALIDATED`.

`CURRENT_REFERENCE` grants only read-only reference reuse. It does not grant code execution, repository checkout effects, model download, remote code, network writes, provider calls with side effects, deployment, spend, or other external effects.

## Identity and currentness

Each external object has independent identities:

- `ExternalSubjectKey`: stable provider + kind + canonical subject ID.
- `ExternalEvidenceGenerationKey`: subject key + exact provider revision + content/metadata digest + source generation + verifier generation + verified fields + security/license metadata.
- `ValidationFingerprint`: evidence generation + state + hydration digests + validator generation + read-only authority ceiling.

Therefore:

`SameSubject + NewRevision => SameSubjectKey + NewEvidenceGenerationKey`.

`VerifierRefreshWithoutContentChange => NewEvidenceGenerationKey, Not NewSubject`.

`ArtifactObservedAt != SourceGeneratedAt`.

This preserves A2/A5 novelty accounting and allows change-driven refresh rather than full rescans.

## 13D, K27, toroidal, tesseract, and crystalline use

The coordinate system is an index over exact identities, not a replacement for them.

### 13D ternary projection

Aura derives 13 base-3 digits from the full subject SHA and another 13 from the evidence-generation SHA. A 13-trit projection has `3^13 = 1,594,323` possible cells and can be used for deterministic partitioning/locality while the full SHA remains canonical.

`13DCoordinateCollision => ResolveWithFullSubjectKeyAndEvidenceGenerationKey`.

### K27 projection

A coarse `(x,y,z)` with each axis modulo 27 provides `27^3 = 19,683` coarse cells for sharding, neighborhood indexing, or bounded scan routing.

`K27Coordinate != SubjectIdentity != EvidenceTruth != Authority`.

### Toroidal projection

The implementation mixes subject and evidence K27 coordinates modulo 27. This creates a wraparound neighborhood suitable for version/currentness-local cache routing without allowing coordinate motion to change semantic identity.

Useful interpretation:

`Torus(subject,evidence) = ((Sx+Ex) mod 27, (Sy+Ey) mod 27, (Sz+Ez) mod 27)`.

### 4D tesseract state projection

The current V1 tesseract vertex is four explicit state bits:

`[source_verified, source_current, exact_source_resolvable, effect_authorized]`.

External ingress always sets the effect bit to `0`. A typical current read-only reference is therefore `(1,1,1,0)`.

This makes state topology inspectable without converting geometry into authority.

### Eight crystalline / Omega8 axes

The eight-lattice idea is safest and most useful here as independent validation projections, not eight competing truth stores:

- W0 source/provenance identity
- W1 hydration/derivation order
- W2 substitution and falsifier attacks
- W3 contradiction repair / smallest invalidated cone
- W4 independent currentness, license, security, source, tool/effect leaves
- W5 cross-source synthesis and relation proof
- W6 duplicate/collision quotient and corroboration
- W7 temporal supersession/currentness
- W8 effect-authority boundary

A future physical lattice implementation may optimize placement, but must preserve these logical independence laws.

## Change-driven HyperDrive ingestion

The lowest-friction steady state is not periodic full re-embedding. It is:

`StableSubject -> CheapProviderCurrentnessCheck -> ChangedGeneration? -> RehydrateAffectedLevelsOnly -> RecomputeEvidenceCoordinate -> PreserveUnchangedSemanticSubject`.

Provider-specific tactics:

- GitHub: conditional REST requests / ETags and exact commit SHA resolution.
- Hugging Face: repo SHA/last-modified metadata and Hub event/webhook surfaces when available.
- arXiv: version-aware Atom/API discovery.
- OpenAlex/Crossref: updated/indexed timestamp based incremental synchronization.
- Semantic Scholar: paper IDs and metadata hashes where a native updated-generation field is not exposed by the selected endpoint.

This keeps the persistent external atlas small at L0/L1 while L2-L4 are hydrated only when an objective enters the relevant affected cone.

## PowerShell use

The PowerShell surface is intentionally thin; provider logic remains in one Python owner.

```powershell
.\tools\Invoke-AuraExternalDiscovery.ps1 `
  -Provider ARXIV `
  -Query "agent memory temporal provenance" `
  -Limit 5 `
  -Output .\out\arxiv.json
```

GitHub with a token stored in an environment variable:

```powershell
.\tools\Invoke-AuraExternalDiscovery.ps1 `
  -Provider GITHUB `
  -Query "agent framework" `
  -Limit 10 `
  -TokenEnv GITHUB_TOKEN `
  -Output .\out\github.json
```

Hugging Face:

```powershell
.\tools\Invoke-AuraExternalDiscovery.ps1 `
  -Provider HUGGING_FACE `
  -Query "agent memory" `
  -RepoType model `
  -TokenEnv HF_TOKEN `
  -Output .\out\hf-models.json
```

Google Scholar intentionally returns `GOOGLE_SCHOLAR_AUTOMATION_NOT_ADMITTED_NO_OFFICIAL_API`; use arXiv/OpenAlex/Crossref/Semantic Scholar for scheduled scholarly ingestion.

## Security and capability ceiling

Every ingress node permanently starts with:

- `code_execution_authorized = false`
- `model_download_authorized = false`
- `remote_code_authorized = false`
- `network_write_authorized = false`
- `provider_effect_authorized = false`
- `semantic_k27_authority = false`
- `native_private_transformer_kv_accessed = false`
- `tool_use_requires_separate_admission = true`

A repository/tool/model may therefore be *known and current* without being *available for effect*. Tool availability requires its own owner-resolved policy/security/runtime/currentness transition.

## HyperDrive laws

`ExternalSubjectIdentity != ExternalEvidenceGeneration`.

`ArtifactObservedAt != SourceSemanticGeneration`.

`HydrationLevel != VerificationLevel != ToolUseAuthority`.

`CoordinateProjection != SemanticIdentity != EvidenceTruth`.

`CacheHit != Currentness != Authority`.

`ReadOnlyReference != CodeExecution != ModelDownload != ProviderEffect`.

`CoordinateCollisionMustResolveThroughFullSubjectAndEvidenceKeys`.

`StaleSourceRemainsHistoricalButIsNotCurrentUseAdmissible`.

`Discovery != CurrentReference`.

`ToolUseRequiresSeparateOwnerAdmission`.

`NativePrivateTransformerKVAccessed = false`.

## External research pressure

This design is consistent with current external systems and research:

- GitHub REST supports conditional requests with ETags for low-cost change detection.
- Hugging Face Hub repository metadata exposes revision SHA and update/security metadata; event/webhook surfaces can support incremental refresh.
- OpenAlex and Crossref expose update/index generations useful for incremental synchronization.
- Semantic Scholar exposes a public Academic Graph API for paper discovery and metadata retrieval.
- arXiv explicitly offers public API access for interoperability.
- recent temporal-memory work shows pure similarity retrieval cannot reliably distinguish superseded from current facts, motivating explicit temporal/currentness metadata.
- versioned/content-addressed retrieval work supports synchronizing changed chunks rather than rebuilding a complete knowledge store.

External sources are methodology and falsification pressure only. They do not grant Aura semantic or effect authority.

## Creation / Triadic / HyperScale

Triadic:

`ExternalSourceDiscovery thesis + Aura A2/A5 currentness/identity thesis -> challenge summary/cache/coordinate laundering -> source-resolvable staged-ingress synthesis`.

Creation:

`discover -> normalize -> exact-source resolve -> metadata verify -> currentness recheck -> L0 admission -> demand-hydrate L1/L2/L3/L4 -> validate -> coordinate-project -> cache -> invalidate/reverify on provider change -> separate tool admission`.

HyperScale remains HS1 for this objective. Additional fanout is justified only by a genuinely independent provider/currentness/security consequence, not by multiplying copies of the same ingestion semantics.
