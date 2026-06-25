# 🌌 AuraOS — Sovereign Edge Cognitive Substrate

## Complete User Guide & API Reference

**Version**: 4.01 QSPT  
**Target**: Android Termux / 4GB RAM / Pure CPU (0 GPU)  
**Author**: Dallas Fabian Courchene-Martin

---

## Table of Contents

1. [What Is AuraOS?](#1-what-is-auraos)
2. [System Requirements & Setup](#2-system-requirements--setup)
3. [Architecture Overview](#3-architecture-overview)
4. [REPL Commands Reference](#4-repl-commands-reference)
5. [Core Engine Module Reference](#5-core-engine-module-reference)
6. [Memory & Cognition Modules](#6-memory--cognition-modules)
7. [Networking & Mesh Modules](#7-networking--mesh-modules)
8. [AI/LLM Routing Modules](#8-aillm-routing-modules)
9. [Self-Healing & Evolution Modules](#9-self-healing--evolution-modules)
10. [Security & Integrity Modules](#10-security--integrity-modules)
11. [Visualization & AR Modules](#11-visualization--ar-modules)
12. [Infrastructure & Utility Modules](#12-infrastructure--utility-modules)
13. [Workflow Patterns](#13-workflow-patterns)
14. [Troubleshooting](#14-troubleshooting)
15. [WebSocket & AR Command Reference](#15-websocket--ar-command-reference)

---

## 1. What Is AuraOS?

AuraOS is a **polysynthetic cognitive substrate** — an autonomous, self-repairing operating system kernel written in Python for sovereign edge execution. It runs entirely on-device (Android/Termux, 4GB RAM, no GPU) and provides:

- **Hyperdimensional vector memory** — 10,000-dimensional binary vectors for associative reasoning
- **Autonomous code evolution** — self-modifying architecture with sandboxed mutation control
- **3D/AR topology visualization** — real-time dependency graph of the entire codebase
- **Multi-provider LLM routing** — intelligent failover across Gemini, Mistral, Groq, Anthropic, and local models
- **UDP mesh networking** — peer discovery and compute offloading via encrypted DSEKP packets

AuraOS is governed by **Ojibwe PWFST alignment principles** — GIZAAGI'IN (Mutual Benefit), GIDINAWENDIMIN (Swarm Synergy), GWAYAKWAADIZIWIN (Integrity).

---

## 2. System Requirements & Setup

### Hardware
- **4GB RAM minimum** (PVM_RAM_CEILING_MB = 4096)
- **0 GPU required** — pure CPU computation
- Android device with Termux installed

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

# 2. Run the setup script (installs Termux dependencies)
bash setup.sh

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Optional: Build aria2c + wasmtime native accelerators
bash build_aura.sh

# 4b. Optional: build the Rust context-crush accelerator
rustc -O aura_crush_core.rs -o Aura_Memory/aura_crush_core
export AURA_CRUSH_ACCELERATOR_PATH=Aura_Memory/aura_crush_core

# 5. Generate the genesis block (IP minting)
python3 mint_genesis.py

# 6. Launch AuraOS
python3 aura_node.py
```

### Configuration Files

| File | Purpose |
|------|---------|
| `aura_secrets.json` | API keys for cloud LLM providers |
| `aura_lexicon.json` | Technical (Python) hemisphere — keyword-to-syntax mapping |
| `english_lexicon.json` | Conversational (English) hemisphere — word associations |
| `aura.lexc` | Finite-state transducer blueprint for intent routing |
| `AURA_GENESIS_BLOCK.json` | Immutable genesis block with cryptographic IP signature |

### API Keys (optional)

Create `aura_secrets.json`:

```json
{
  "GEMINI_API_KEY": "your-gemini-key",
  "OPEN_ROUTER_API_KEY": "your-openrouter-key",
  "MISTRAL_API_KEY": "your-mistral-key",
  "GROQ_API_KEY": "your-groq-key",
  "GITHUB_TOKEN": "your-github-token",
  "AURA_FUSION_PANEL": [
    {
      "name": "thinker_openrouter",
      "role": "THINKER",
      "provider": "openrouter",
      "base_url": "https://openrouter.ai/api/v1/chat/completions",
      "api_key_name": "OPEN_ROUTER_API_KEY",
      "model": "anthropic/claude-sonnet-4.5",
      "max_tokens": 900
    }
  ],
  "AURA_FUSION_JUDGE": {
    "name": "judge_openrouter",
    "role": "JUDGE",
    "provider": "openrouter",
    "base_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key_name": "OPEN_ROUTER_API_KEY",
    "model": "openai/gpt-4o-mini",
    "max_tokens": 1200
  }
}
```

AuraOS works offline for deterministic substrate functions. Native AuraFusion
uses only explicitly configured external provider APIs and can be dry-run with
`python3 aura_fusion.py --mock "Compare these approaches"`.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  [Dallas] > prompt        REPL loop with !commands               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    AuraSovereignNode (aura_node.py)              │
│  • SovereignEngine — intent → vector → action mapping           │
│  • CognitiveGateway — protocol routing + ST3GG holography       │
│  • AuraHyperdimensionalCore — 10,000-D VSA operations           │
│  • AsyncMemoryPalace — SQLite WAL persistence                   │
│  • LiquidFlashEvolve — sandboxed self-mutation                  │
│  • 15+ Layer 7 engines (QFCS, DIKWP, LNN, PVM, etc.)           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Memory Layer  │   │  Network Layer │   │  Visual Layer │
│ .mempalace/   │   │  UDP 4444     │   │  WS 8765      │
│ SQLite WAL    │   │  Mesh Swarm   │   │  3D AR Graph  │
│ Aura_Memory/  │   │  Pulse 8081   │   │  index.html   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### Key Concepts

- **Polysynthetic**: Input is decomposed into 6 morphemic slots (SPATIAL, ASPECT, CLASS, SUBJECT, VOICE, STEM) before routing
- **ST3GG**: Holographic glyph/stamp system — thermal/moral/friction categorization plus visible DASH recall pointers. Aura's egress-memory path uses auditable ST3GG capsules and strips hidden tokenizer carriers before outbound calls.
- **DIKWP**: Data → Information → Knowledge → Wisdom → Purpose — cognitive hierarchy
- **PWFST**: Ojibwe governance principles enforced across all modules
- **Hyperdimensional (HDC)**: 10,000-bit binary vectors provide noise-tolerant associative memory

---

## 4. REPL Commands Reference

Type commands at the `[Dallas] >` prompt after `python3 aura_node.py` starts.
Run `!settings`, `!manifest`, or `!help` at any time for the live manifest.
The live manifest is generated from `aura_node.py` and includes a bottom
function index from `[AURA_MASTER_KEY]` headers. For implementation lookup,
read `.aura/CODEMAP.md` first, then use `!ai_route <task>` to find the
smallest useful file/symbol path.

### Navigation, Topology, and Code Search

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `!settings` / `!manifest` / `!help` | You need the live command map or bottom function index. | Prints command usage, polysynthetic slots, module metadata, and a function-to-module quick index. |
| `!ai_route <task>` | You know the job but not the file to open. | Queries `aura_ai_router.py` for CODEMAP-grounded file and symbol candidates. |
| `!ai_router_regen` | CODEMAP/topology changed after edits. | Rebuilds the AI router index from current topology data. |
| `!topology` / `!scan_topology` | You need the current code graph before analysis, AR viewing, or patch validation. | Scans Python AST/import/resource edges, augments the graph with Laplacian eigenmap coordinates and luminance health fields, and writes `Aura_Memory/live_topology_ast.json`. |
| `!topology deep` / `!topology_deep` | You need hub diagnostics or fracture clues. | Runs the deeper topology builder and reports isolated nodes, dead ends, dangling edges, top hubs, spectral sparsity, cycle warnings, and global structural health. |
| `!catalyze` | A staged patch exists and needs structural proof. | Reads `Aura_Staging/pending_patches.json` plus live topology and validates proposed patches with mutation guards. |
| `!simulate <target>` | You want to test a route through the live topology. | Sends a target path into the SPVM/Rust simulator and reports bridges, fractures, and coherence drops. |
| `!fast_path <query>` | You want a very fast associative intent lookup. | Performs O(1)-style hypervector lookup in the RAM matrix and stores the query as a future probe. |
| `!cognitive_search` | You need semantic search over holographic DKT logs. | Builds a 10,000-D query vector and runs the WASM cognitive search module over recent log history. |
| `!attention` | You want the current thought vector kept in working memory. | Stores the active vector in the dual-attention buffer and reports occupancy/link count. |

### Reasoning and Verification

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `!reason` | You need a full neuro-symbolic consistency sweep. | Runs the NESY omnipath verifier and prints the symbolic logic result. |
| `!coordinated_reason <query>` | A hard query needs parallel Pass@K reasoning. | Runs four coordinated strategies, then reports success, throughput, latency, top rewards, and buffer health. |
| `!strategy_buffer_stats` | You need solver readiness/quality metrics. | Prints strategy capacity, valid entries, mean reward, best reward, and active-strategy state. |
| `!evolve_reasoning` | The topology should become a stronger reasoning manifold. | Crystallizes nodes into a hypertruth manifold and reports whether constraints held. |
| `!meta_analyze` | You want a structural integrity audit of the active manifold. | Runs meta-learning crystallization with constraints and prints the integrity result. |
| `!meta_reason` | Truth resonance may be unstable. | Verifies recursive VSA resonance; if resonance is below 0.85, triggers symbolic recalibration. |
| `!saturn` | You need the full NESY curriculum/training cycle. | Runs the exhaustive omnipath sweep and records state for later healing. |
| `!saturn_heal` | Saturn/NESY logs show fractures or boot drift was detected. | Reads `Aura_Memory/nesy_sat_reasoner_state.json`, applies non-destructive repair stubs where needed, and regenerates topology. |
| `!benchmark` | You need device/runtime health. | Reports CPU temperature, RAM, CPU count, Python/NumPy, disk, 10K-dot latency, LLM server, AR clients, and memory-palace status. |
| `!system_audit` / `!audit` | You need an ecosystem audit. | Runs the Layer 5 auditor and prints the unified health/report output. |
| `!test_airlock` | You need to test isolated WASM/tensor execution. | Runs `quantum_tensor_sandbox`; offloads to a cooler mesh peer if one is available. |

### Self-Modification and Staging

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `architect <intent>` / `code <intent>` | You want Aura to plan and stage a bounded refactor. | Runs the live Architect bridge: local/free plan fallback, multiple premium plan candidates, cheap Shadow critics, premium Judge selection, bounded Act workers, Refactor Arena staging projected into the Liquid Planning Arena substrate, temp-workspace patch application, topology/world-state delta capture, verifier-gated hot-swap/rollback capsules, and a JSONL ledger row. It stages the transaction in `Aura_Staging/architect_live_transaction.json` instead of writing model output to `aura_incubator.py`. |
| `!self_reflect` | You want introspection before changing code. | Runs VSA resonance analysis, WASM/offload metrics, and cloud architect diagnosis. |
| `!self_optimize` / `!optimize` | You want a staged optimization patch. | Audits runtime friction, asks the selected model for one optimized patch, sanitizes it, and writes `Aura_Staging/pending_patches.json`. |
| `!stage` / `!stage_review` / `!review` | You need to inspect pending code before merge. | For live Architect transactions, prints status, selected council candidate, Judge path, hot-swap phase hash, topology-delta stats, staged patches, and blockers from `Aura_Staging/architect_live_transaction.json`. Legacy pending patches still show the older timestamp, target, confidence, and proposed-code preview. |
| `!stage_merge` | You approve staged work. | For live Architect transactions, records human alignment and promotes the verified hot-swap capsule into `Aura_Staging/approved_hotswap_capsule.json` without production writes. Legacy pending patches still use the older incubator quarantine path. |
| `!stage_purge` | The staged patch is wrong or unsafe. | Deletes the pending patch and logs the rejection as an anti-pattern for future routing. |
| `!approve <method>` | A function in `aura_incubator.py` should become live. | Grafts the named function into `aura_node.py` through AST surgery. |
| `!rollback <root>` | You need to neutralize a bad cognitive trajectory. | Applies phase-conjugate rollback to the supplied Q-SYS root token. |

### LLM Routing and Conversation

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `!calibrate` | Provider keys changed or routing quality is stale. | Runs the provider x packet-style x output-mode benchmark matrix and updates the calibration ledger. |
| `!route <task> [--model M]` | You want Aura to pick the cheapest/highest-fit model path. | Sends the task through `aura_router.py`; `--model` forces priority while preserving fallback behavior. |
| `!fusion <task>` | A task benefits from panel deliberation. | Runs AuraFusion: SkillWeaver gate, compact capsule, Thinker/Worker/Verifier panel, and judge synthesis. |
| `!savings` | You want token/cost accounting. | Reads router logs and `aura_savings.db`, prints provider/aspect totals, and refreshes `Aura_Memory/aura_savings_total.json`. |
| `!converse <text>` | You want normal conversation with compact memory logging. | Compresses input, calls the configured external/local route, interprets the compact reply, and learns style over time. |
| `!contingency_spawn` | The device feels hot, cache pressure is high, or staging state is unclear. | Reports thermal load, cache evictions, staged-patch status, and applies safe immediate mitigations. |

### Universal LLM Savings Ledger

Every external LLM call that passes through Aura's API helpers is logged to
`Aura_Memory/aura_savings.db`, including `!route`, `!converse`, AuraFusion
panel/judge calls, direct Gemini/OpenAI-compatible helper calls, and the
Anthropic-first router path. When a raw/no-Aura baseline is known, the row
records token and dollar savings; when no baseline is known, the row still
records spend, latency, provider, model, and a zero-savings baseline so metrics
remain honest.

Start the live dashboard:

```bash
python3 aura_savings_dashboard.py
```

Then open `http://localhost:8700` to watch rolling call logs, token savings,
cost savings, latency, provider breakdowns, and recent-call feed updates.

### Native AuraFusion

AuraFusion is Aura's internal panel-plus-judge deliberation path. It does not
depend on OpenRouter's hosted Fusion router as the primary solution. Instead it
uses Aura's own compact task capsule, CODEMAP epoch, SkillWeaver mutation gate,
user-owned provider keys, configured model pool, and a compact spectral topology
snapshot when a target file or symbol is known. The snapshot includes target
coordinates, immediate graph neighbors, luminance health, spectral sparsity, and
cycle counts so panel agents stay close to the relevant code geometry instead of
inventing distant paths.

`aura_architect_loop.py` adds the deterministic Plan/Act shell around that
deliberation path. It turns an Architect objective into a Fractal Plan Capsule,
pre-shards the work into bounded Act Capsules, grounds each capsule against
CODEMAP files and symbols, emits Shadow findings for fake files, fake symbols,
missing nearby tests, or oversized work packets, and then creates a Refactor
Arena transaction. Builder and Incubator layers should consume that arena only
after the Shadow gate permits it. The complete transaction path can then stage
owned Builder diffs through `stage_arena_patch`, verify boundaries, conflicts,
working-tree files, and tests through `verify_refactor_arena`, produce a
hot-swap capsule with rollback digests, and append an Architect JSONL ledger row
with `ArchitectFusionLoop.execute`.

`aura_liquid_planning_arena.py` generalizes that Refactor Arena into a bounded
Liquid Planning Arena. In code mode, the current files/symbols/diffs/tests flow
is preserved and projected into domain-neutral Action Capsules, first-class
BoundaryContract placeholders, scoped agent leases, and a shared action queue.
The invariant is the same for future domains: models propose, the Arena stages,
Shadow critiques, Judge decides, verifier proves, human approves, and the ledger
remembers. The initial adapters define code, civic, and travel domain objects so
later planners can stage civic interventions or travel options without pretending
those domains are code patches.

`aura_live_architect.py` is the live command bridge for that substrate. The REPL
`architect <intent>` and `code <intent>` paths now call it instead of writing
cloud output to `aura_incubator.py`. The bridge starts with a local CODEMAP plan
candidate, escalates to multiple premium planner candidates when the budget route
allows it, runs cheap Shadow critic lanes across each candidate, and calls the
premium Judge to select the safest plan and review the staged patch bundle. It
then asks bounded Act workers for unified diffs, stages those diffs in the
Refactor Arena, copies the repo into a temporary workspace, applies the staged
patches there, records AST topology plus generic world-state deltas for affected
Python files, runs local verification commands, and writes
`Aura_Staging/architect_live_transaction.json` plus the Architect ledger record.
The existing `!stage` / `!stage_merge` UX now reviews and approves that verified
hot-swap capsule without production writes. `aura_incubator.py` remains only as a
valid legacy quarantine stub.

Each task capsule also carries a compact single-seed context-lift profile from
`aura_single_seed_lift.py`. This borrows the transferable idea from
arXiv:2606.20633: choose one seed, cache its inverse/profile once, and dispatch
trace metadata to the consumers that need it. In AuraFusion this gives panel
agents a bounded context anchor for the task/topology capsule without expanding
the prompt into a long narrative.

AuraFusion and direct OpenAI-compatible calls also pass mutable user/tool
payloads through `aura_context_crusher.py`. The system-prompt prefix is never
compressed; Aura records a stable prefix hash and volatile-content findings so
cache drift is observable. Hidden tokenizer-survival carriers are stripped at
the outbound boundary, including when context crushing is disabled. Large JSON,
logs, search results, diffs, code, or plain text are compressed locally and
their originals are stored in `Aura_Memory/context_crush_ledger.jsonl` behind
`AURA_CCR` retrieval markers plus visible `ST3GG-L2` recall pointers.

Run it directly:

```bash
python3 aura_fusion.py "Compare router and SkillWeaver integration risks"
python3 aura_fusion.py --mock "Compare router and SkillWeaver integration risks"
python3 aura_router.py fusion --task "Compare router and SkillWeaver integration risks" --mock
```

Run it in the REPL:

```text
[Dallas] > !fusion Compare router and SkillWeaver integration risks
```

Runtime logs are appended to `Aura_Memory/aura_fusion_runs.jsonl` and remain
gitignored. Code-mutation requests are refused when no CODEMAP-grounded
`target_file` is present; grounded mutation plans still require human review
before anything is applied.

### Spectral AR Topology

`aura_spectral_topology.py` augments topology payloads with a local graph
Laplacian (`L = D - A`) and projects the dependency graph into 3-D coordinates.
The AR WebSocket bridge consumes those coordinates directly, so nearby shapes
represent nearby dependency structure instead of arbitrary layout noise.

Each node receives:

- `position`: 3-D spectral coordinate for AR rendering.
- `luminance` / `structural_health`: brighter means cleaner local structure.
- `phaseShiftWarning`: true when the node participates in a directed cycle.
- `validationState`: `clean_luminous`, `coupled_watch`, `dim_architectural_debt`, or `phase_shift_warning`.

The browser renderer pulses phase-shift warning nodes, dims high-friction
modules, and displays spectral sparsity/global health in the HUD. WebSocket
clients receive the same fields through `TOPOLOGY_UPDATE`, so external AR clients
can use the health state without recomputing the graph.

### Knowledge and Research

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `!forage <topic>` | You need a new arXiv source on one topic. | Fetches the latest matching paper, parses the PDF when available, stores a compact scientific trace, writes a paper-memory VSA ledger record, and prints title/abstract plus three main points. |
| `!backtrack` | The research memory needs a wider seed set. | Crawls chronological arXiv CS papers, updates the ingestion offset, stores legacy scientific vectors for search, and refreshes a bounded number of full PDF VSA records per run. |
| `!research <concept>` | You want source-grounded code synthesis. | Searches ingested papers, runs the SkillWeaver relevance gate, and only stages synthesis when sources pass. It benefits from `!forage` and `!backtrack` records. |
| `!search_similar <query>` | You need nearest ingested papers without mutation. | Searches the structured scientific SQLite index and prints top paper matches with relevance scores. |
| `!curiosity_tree <seed>` | You want autonomous discovery from one concept. | Runs bounded DFS over GitHub and arXiv and prints the discovery tree as JSON. |
| `!forage_on` / `!forager_on` | You want background curiosity enabled. | Starts background foraging daemons. |
| `!forage_off` / `!forager_off` | You need to conserve CPU/RAM/heat. | Suspends background foraging daemons. |
| `!timeline` | You want the recent epistemic ledger. | Reads `aura_quantum_memory.db` and prints recent FORAGED/GAP roots. |
| `!crystallize` | You want to start permanent knowledge crystallization. | Initializes the epistemic ingest gateway for unified crystallization. |
| `!synthesize` | You want a cognitive synthesizer lifecycle pass. | Runs `AuraCognitiveSynthesizer.execution_lifecycle_pass()` and prints the summary. |
| `!indus_decrypt` | You want the Indus script resonance demo. | Generates a synthetic 3,700-glyph corpus, runs resonance decryption, and prints hypothesis weights. |

### Paper Memory and RAEC Recall

Aura now keeps two coordinated memories for arXiv papers:

- SQLite scientific traces in `.mempalace/`, keyed as `ARXIV_<paper_id>` when arXiv provides an ID. These keep the existing int8 scientific vectors used by `!research` and `!search_similar`.
- The paper-memory ledger at `Aura_Memory/paper_memory_ledger.jsonl`. Each row stores metadata, a deterministic three-point capsule, a 1.2KB holographic header, a 10,000-D complex document vector, chunk-level VSA vectors, and a compact single-seed lift profile.

The PDF path is intentionally chunked. Aura does not unroll an entire raw PDF into one giant matrix slice; `aura_paper_memory.py` extracts text, chunks it, encodes each chunk as a complex phasor, chooses a deterministic seed chunk, caches the inverse seed profile once, and lifts that seed through bounded residual layers into the document vector. This keeps ingestion compatible with the existing edge-memory architecture while preserving deeper recall hooks.

The single-seed lift is an Aura VSA adaptation, not a claim that Aura performs
literal polynomial factorization over `Z_p^e`. The source paper's useful
engineering pattern is separation of seed discovery, cached inverse lifting, and
trace dispatch. Aura uses that pattern for paper chunks, RAEC slots, and
AuraFusion capsules so later egress calls can reuse compact trace metadata
instead of rebuilding global context.

`!forage <topic>` is best when you need one targeted source right now. It attempts the PDF, writes the paper-memory ledger, updates the SQLite scientific trace, and returns the three extracted points for quick inspection.

`!backtrack` is best when Aura needs a broader research substrate. It crawls by date window, keeps arXiv pacing, and stores every returned paper as a searchable scientific trace. Full PDF VSA ingestion is budgeted by `AURA_BACKTRACK_PDF_LIMIT` and defaults to `3` fetch attempts per run, so large backtracks do not overheat or flood storage.

`!research <concept>` and `!search_similar <query>` continue to use the fast SQLite scientific index. External LLM egress automatically uses RAEC when a paper-memory ledger exists: `aura_llm_egress.py` scans the ledger, selects the top two resonant paper capsules, verifies the `root ::= ...` contract, and injects compact `[ANCHOR_ID:...][CONSTRAINTS:...]` slots before provider egress. When available, those constraints include `LIFT=SEED=...` trace metadata from the cached single-seed profile, and the LLM savings log records the lift dispatch count.

Set `AURA_PAPER_MEMORY_LEDGER=/path/to/paper_memory_ledger.jsonl` to point RAEC at another ledger. Use `python3 extract_pdf_text.py <paper.pdf>` when you want the standalone PDF text-extraction compatibility CLI.


### Headroom-Style Context Crushing

Aura adapts the lightweight ideas from `headroomlabs-ai/headroom` without
importing its heavy proxy/Rust/ML stack. The accepted pieces are deterministic
content routing, schema-aware JSON compaction, log/search/code sketches, local
CCR storage, and detector-only cache-prefix reporting. The rejected pieces are
prompt padding, cache-hot system prompt rewrites, background proxying, and
optional ML compressors that would violate Aura's low-dependency edge profile.

Where it operates:

- `ExternalLLM.generate()` crushes the mutable prompt before network egress, but
  keeps the original prompt for RAEC resonance scoring.
- `generate_openai_compatible_payload()` crushes non-system messages before
  AuraFusion panel/judge calls.
- Savings metadata records `context_crush` summaries beside provider, RAEC, and
  response-schema fields.
- Originals are retrievable locally with
  `retrieve_context_crush(hash, query=None)`.

The cache-prefix rule is strict: system prompts are treated as cache-hot and
never modified. If Aura sees volatile UUIDs, timestamps, JWT-shaped tokens, or
hex digests inside system text, it records an alignment warning instead of
rewriting the prompt.

### SkillWeaver Research Relevance Gate

The `!research` command now includes a **SkillWeaver Relevance Gate** that intercepts the pipeline before the Cloud Synthesizer. This prevents ungrounded code mutations from semantically resonant but conceptually irrelevant research matches.

**How it works:**

1. **Query Decomposition**: Your research query is broken into atomic subtasks.
2. **Anchor Extraction**: Required conceptual anchors are derived from the query (e.g., "Hopfield networks" → hopfield, associative memory, attractor, energy function).
3. **Candidate Scoring**: Each retrieved paper is scored on four axes:
   - VSA resonance (40%): Hyperdimensional cosine similarity
   - Lexical anchor coverage (35%): Do required terms appear in the paper?
   - Title/abstract match (15%): Direct query term presence
   - Domain match (10%): Is the paper in a relevant field?
4. **Gate Decision**:
   - `ALLOW_MUTATION`: Sources pass and target modules found → synthesis proceeds
   - `REFUSE_MUTATION`: Sources fail relevance → synthesis blocked with explanation
   - `NEED_MORE_SOURCES`: Partial evidence → user advised to ingest more papers
5. **DAG Plan**: When allowed, a staged mutation plan is composed with target files, security validation, tests, and rollback paths.

**Example refusal output:**
```
[RESEARCH_GATE]
QUERY: Hopfield networks
DECISION: REFUSE_MUTATION
REASON: Retrieved papers failed lexical anchor coverage.
TOP_MATCHES:
  - [REJECTED] Bell-State Loop-Back: resonance=0.0012, anchors=0.000
NEXT: Ingest source-sufficient papers before attempting mutation.
[/RESEARCH_GATE]
```

**Module**: `aura_skillweaver.py` (see CODEMAP for full API)

### Mesh, AR, Export, and System Control

| Command | Use when | Operation and output |
|---------|----------|----------------------|
| `!ping_mesh` | You want to discover or wake peers. | Broadcasts an encrypted DSEKP handshake packet on UDP 4444. |
| `!mesh_status` | You need mesh identity and peer state. | Prints local mesh identity, active peer IPs, and DSEKP entropy index. |
| `!ar_start` / `!ar_server_start` | You want interactive 3D topology controls. | Starts `AuraARWebSocketServer` on port 8765 for topology, shape interaction, add-shape, and hotswap messages. |
| `!ar_stop` / `!ar_server_stop` | You need to restart or free the AR port. | Stops the AR WebSocket server and disconnects clients cleanly. |
| `!export [tree]` | You need a local export artifact. | Writes export output to `~/aura_exports/`; `!export tree` emits the dependency tree. |
| `!push <message>` | You want zero-trust GitHub backup from inside Aura. | Verifies Python files, attempts healing on failure, then runs git add/commit/push with the message. |
| `!db_repair` / `!repair_db` | SQLite databases are corrupt or malformed. | Checks known Aura databases and rebuilds any malformed files. |
| `!markov [N]` | You need to reconstruct state from logs. | Runs Markovian workspace reconstruction over the last N raw logs, default 256. |
| `!voice` | You want the Termux vocal executive loop. | Starts voice/TTS control; requires `termux-api`. |
| `STOP` | A long inference needs to end now. | Sets the stop flag and cancels active inference watchers. |
| `exit` / `quit` | You are done with the node. | Gracefully shuts down kernels and exits the REPL. |

---

## 5. Core Engine Module Reference

### 5.1 `aura_core.py` — Sovereign Logic Fabric

**Purpose**: The foundational intent-processing engine. Converts natural language intents into 10,000-D hypervectors, maps them against a Vector Self-Organizing Map (VSOM), and routes to physical actions.

**Class: `SovereignEngine`**

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `()` | Loads lexicons, initializes VSOM codebook (10×10 grid), seeds RNG |
| `continuous_tda_filtration` | `(intent_str) → ndarray(10000,)` | Hashes intent string → seed → generates ±1 binary vector |
| `match_vsom` | `(intent_vector) → ((row, col), fidelity)` | Dot-product similarity across VSOM grid, returns best matching unit |
| `bind_intent_to_action` | `(intent_str, target_action) → coordinate` | Permanently binds a natural language intent to an AR action code |
| `music_inversion` | `(coordinate, intent_vector, mode) → str` | 384-bit interference pattern → symbolic token generation |
| `vocalize` | `(text)` | Fire-and-forget TTS via `termux-tts-speak` (non-blocking) |
| `ingest_intent` | `(intent_str, force_mode) → dict` | Full pipeline: TDA filtration → VSOM → action routing → code/speech generation |

**Class: `AuraOrchestrationLobe`**

| Method | Signature | Description |
|--------|-----------|-------------|
| `backward_chain_manifest` | `(goal_vector, current_vector) → ndarray` | Pure numpy state-delta calculation (no PyTorch) |

### 5.2 `aura_node.py` — Sovereign Runtime Kernel

**Purpose**: The main 7,000-line runtime. Contains the REPL loop, all Layer 7 engines, and the primary AuraSovereignNode class that binds everything together.

**Class: `AuraSovereignNode`** (partial listing of key methods)

| Method | Description |
|--------|-------------|
| `polysynthetic_vram_compress` | Zero-copy universal compressor: any object → 10,000-D complex phasor wave |
| `invoke_engine` | Stateless cognition: local LLM → server proxy → Groq → Gemini → Mistral fallback chain |
| `invoke_cloud_engine` | Expert-domain routing matrix with circuit breakers per provider |
| `invoke_active_inference` | Abductive inference loop with thermal look-ahead simulation (T+1, T+2, T+3) |
| `abductive_inference` | Hypothesis generation from SQLite causal ledger + VSA resonance |
| `execute_dag_plan` | Deterministic finite-state DAG routing (bypasses autoregressive LLM) |
| `mint_trace` | Fire-and-forget memory trace storage with plasticity fallback |
| `ast_surgical_graft` | Live AST node replacement for hot-swapping methods |
| `night_cycle_evolution` | Background code evolution with QNRL lateral concept tunneling |
| `emergent_curiosity_daemon` | Topology-aware autonomous discovery and staging pipeline |

**Layer 7 Engine Classes** (all defined within `aura_node.py`):

| Class | Purpose |
|-------|---------|
| `AuraHyperdimensionalCore` | 10,000-D VSA: bind, permute, encode_text, quanvolutional filter |
| `AuraSpikingGovernor` | Leaky integrate-and-fire neuron model for thermal/load management |
| `AuraCompilerParser` | Bifurcated decoder: polysynthetic opcodes vs natural speech |
| `AuraNativePFST` | Lexical finite-state transducer → vector symbolic routes |
| `AuraSafetySentinel` | In-memory mutation airlock: AST isolation + speculative execution |
| `SovereignQFCS` | 12-bit Quantum Finite Automaton for token sequence validation |
| `AuraSuperpositionEngine` | Token-superposition training for categorical log blending |
| `AuraQFSTEngine` | Non-abelian SU(2) unitary group transitions |
| `AStarQuantumStateCompressor` | A*-guided Markovian state compression |
| `AuraContinuousTrajectoryEngine` | Fractional-power continuous vector binding |
| `AuraGameTheoreticContainmentEngine` | AGI containment via strategic friction evaluation |
| `AuraStateCoherenceProjector` | Algebraic minimization + Watrous QFA projection |
| `AuraCognitiveSolvencyAuditor` | Real-time computing resource balance sheet |
| `AuraDIKWPSemanticFieldEngine` | DIKWP tier transformation via orbital phase shifts |
| `AuraPolysyntheticLNNEngine` | Łukasiewicz t-norm neural network for logical inference |
| `AuraFrictionOptimizationLoop` | High-friction path detection + neuro-symbolic caching |
| `AuraPolysyntheticCompilerGate` | GBNF grammar → isolated memory page → trajectory compilation |
| `AuraPolysyntheticVirtualMachine` | Bare-metal instruction word dispatch (opcodes 101-404) |
| `AuraMorphemicModelBootstrapScanner` | LLM tensor shape distillation |
| `AuraLexiconDecompositionEngine` | English → polysynthetic decomposition |
| `AuraAsynchronousMorphemicAirlock` | Address-space isolated page multiplexing |
| `AuraZeroDiskIOCache` | Async coroutine-safe filesystem cache with mtime/size validation |
| `ZeroCopyMemoryOrchestrator` | WebAssembly shared memory 128-bit SIMD frame management |
| `TraceBatchRouter` | Unified async batch cursor for shared_table_traces |
| `AuraEcosystemAuditor` | Full codebase AST audit + holographic master-key stamping |
| `AuraCritic` | Meta-cognitive verification layer (System 2) |

### 5.3 `gateway.py` — Cognitive Gateway

**Purpose**: Protocol translation and holographic tracing. Converts between symbolic vectors, binary representations, and ST3GG glyphs. Routes cognitive load between quantum and classical pathways.

**Class: `CognitiveGateway`**

| Method | Description |
|--------|-------------|
| `generate_st3gg_glyph` | Generate thermal/moral/friction categorization hex stamp |
| `_generate_dash_kv_hash` | DASH key-value hashing for holographic log entries |
| `_extract_dikwp_heuristics` | Extract DIKWP tier from telemetry (Data → Wisdom → Purpose) |
| `route_to_quantum` | Vector routing: classical → quantum pathway |
| `route_to_binary` | Vector routing: quantum → binary (classical) pathway |
| `semantic_plasticity_bridge` | Rescue failed PFST routes by inferring intent from vector space |
| `qnrl_dynamic_risk_policy` | Adaptive risk modifier for quantum tunneling operations |
| `quantum_tunneling_concept_bridge` | Lateral concept association forging |
| `log_dkt_commit` | Write holographic binary blob to DKT log |

---

## 6. Memory & Cognition Modules

### 6.1 `async_palace.py` — Async Memory Palace

**Purpose**: Sovereign persistent memory engine. Implements compactionless WAL (Write-Ahead Log) SQLite storage with background consolidation and thermal-aware stone crawler.

**Class: `AsyncMemoryPalace`**

| Method | Description |
|--------|-------------|
| `__aenter__` | Initialize SQLite with WAL mode, create all tables, start background tasks |
| `__aexit__` | Graceful shutdown: flush all buffers, cancel tasks, close connection |
| `enqueue_holographic_trace` | Route through gateway → pack holographic BLOB → buffer for async flush |
| `enqueue_morphemic_root_trace` | Buffer morphemic slot records in numpy ring buffer |
| `stream_vectors` | Yield (id, tier, vector_blob) tuples from traces table |
| `lock_atomic_spin_state` | Convert FHRR phase wave to permanent float32 spin-state matrix |
| `get_all_crystallized_phases` | Extract all CRYSTAL/WISDOM/HYPERTRUTH vector matrices |
| `verify_incremental_frontier` | Merkle frontier verification O(log N) |
| `check_audit_cache` | Embedded audit cache lookup by (filepath, mtime, size) |
| `update_audit_cache` | Update audit cache entry with current hardware profile |
| `_stone_crawler` | Thermal-gated (≤38.0°C) WAL checkpoint + QRW entropy reserve generation |
| `_auto_flush_morphemic_pool` | Adaptive-interval auto-flush: 0.2s under load, 2.0s idle |

**Class: `MorphemicBatchQueue`**

| Method | Description |
|--------|-------------|
| `append_record` | Write (slots, compliance) directly into pre-allocated numpy buffer (O(1)) |
| `flush_and_clear` | Drain all records → list of 7-tuples (legacy bridge) |
| `flush_np` | Drain → numpy structured array (zero-copy fast path) |
| `compile_bftree_matrix_view` | Return shape (N,6) uint16 array — native or legacy decode paths |

**Class: `TransactionalBatchWriter`**

| Method | Description |
|--------|-------------|
| `append_record` | Append (timestamp, module, payload) to deque |
| `flush` | Bulk INSERT into SQLite traces table |
| `start_background_task` | Launch autonomous flush loop |

### 6.2 `cognitive_router.py` — Cognitive Router

Class: `CognitiveRouter` — `wave_scan(prompt_hv, limit)` retrieves Tier-2 holographic context from the memory palace by vector similarity.

### 6.3 `aura_associative_core.py` — Associative Core

Class: `AuraAssociativeCore(dim=10000)`

| Method | Description |
|--------|-------------|
| `store(probe, vector, label)` | Store (probe → vector) association |
| `query(probe, top_k)` | Retrieve top-k similar stored vectors |
| `fast_path_lookup(query, vectorizer_fn)` | O(1) intent match via cosine similarity |
| `force_decay()` / `get_stats()` / `reset()` | Memory management utilities |

### 6.4 `aura_attention_palace.py` — Attention Palace

Class: `AttentionPalace(capacity=1024)` — dual-attention working-memory buffer with BFTree matrix view. Stores (thought_id → vector) with positive/negative relation links for contrastive recall.

### 6.5 `aura_rosetta_memory.py` — Rosetta Memory

Class: `RosettaMemoryBuffer(capacity=500, dimension=10000)` — high-speed polarized memory pool for caching transformed phase vectors.

| Method | Description |
|--------|-------------|
| `adaptive_write(phasor, content, tier)` | Store with automatic eviction |
| `query_contrastive(probe_phasor, k)` | Contrastive retrieval |

### 6.6 `aura_crystallization.py` — Hypertruth Crystallization

Function: `hypertruth_crystallization_loop(node_topology, shared_edges, constraints)` — projects topology into 10,000-D complex VSA phase space, crystallising invariant structural truths.

### 6.7 `aura_dream_engine.py` — Dream Engine

Function: `homeostatic_decay_pass(node)` — runs a single homeostatic decay cycle over spectral memory, triggering reconsolidation of low-resonance memories.

### 6.8 `aura_spectral_memory.py` — Spectral Memory

Stores and retrieves memories as spectral (frequency-domain) representations for efficient similarity search.

### 6.9 `aura_qdkt.py` — Unified Quantum Deep Knowledge Tracing

**Class: `UnifiedQDKT`**

| Method | Description |
|--------|-------------|
| `observe(event_type, payload, *, rationale, concept, confidence, subsystem, node_ref)` | Route knowledge event to all 7 DKT storage subsystems |
| `query(concept, *, top_k, include_binary)` | Search ALL DKT stores for knowledge |
| `crystallize(concept, recommended_action, *, confidence, source)` | Promote concept→action to permanent crystal cache |
| `fast_path(concept)` | O(1) crystal cache lookup |
| `learning_summary()` | Human-readable consolidated report |

### 6.10 `aura_hv_cache.py` — HV Cache

**Classes**: `HVCacheSubstrate` — stores hypervector-indexed change logs. `ChangeLogStore` — logs file mutations with rationale. `RationaleQueryEngine` — semantic search over change history.

### 6.11 `aura_governor.py` — Spiking Governor

| Method | Description |
|--------|-------------|
| `stimulate_and_leak` | Process text stream through spiking neuron network |
| `evaluate_payload_confidence` | Unused — reserved |
| `calculate_ephaptic_resonance` | Field coupling between memory oscillators |
| `apply_mental_entanglement` | Apply entanglement coefficients to routing decisions |
| `evaluate_energy_ceiling` | Check if energy budget allows execution |

---

## 7. Networking & Mesh Modules

### 7.1 `aura_mesh.py` — Mesh Swarm

**Class: `AuraMeshSwarm`**

| Method | Description |
|--------|-------------|
| `__init__` | Initialize UDP socket on port 4444, start beacon daemon |
| `start_udp_beacon` | Broadcast encrypted DSEKP handshake packets |
| `pack_secure_polysynthetic_packet` | Pack slots + compliance into binary network frame |
| `unpack_secure_polysynthetic_packet` | Decode received binary frame |
| `generate_polysynthetic_proof` | Generate proof-of-computation token |
| `verify_dsekp_shield` | Verify DSEKP cryptographic shield |
| `broadcast_upgrade` | Broadcast upgrade command to all peers |
| `offload_compute` | Route heavy computation to coolest mesh peer |
| `_listen_beacons_async` | Async UDP listener for peer discovery |

### 7.2 `pulse.py` — AR Pulse Bridge

WebSocket server on port 8081 that bridges the cognitive engine to the AR visualization deck.

| Function | Description |
|----------|-------------|
| `bridge_handler(websocket)` | Handle AR client connections; process JSON commands through LiquidKernel (LiquidStateMachine + LiquidTimeConstant), inject ST3GG steganography stamps from latest `.st3` engram file, broadcast processed payload to all connected clients |
| `watch_memory()` | Background loop: detect new `.st3` engram files in `Aura_Memory/` → broadcast `HolographicEngram` glyph payloads to all connected AR clients |
| `main()` | Bind WebSocket server on `0.0.0.0:8081` |

See [§15 WebSocket & AR Command Reference](#15-websocket--ar-command-reference) for full message formats.

### 7.3 `aura_privacy_io.py` — Privacy IO

Class: `AuraPrivacyGuard` — adds differential privacy noise to output vectors before transmission, maintaining ε-differential privacy when broadcasting sensitive cognitive state.

---

## 8. AI/LLM Routing Modules

### 8.1 `aura_router.py` — Self-Optimising Provider Router

| Class | Purpose |
|-------|---------|
| `CalibrationLedger` | Append-only JSONL ledger of (provider × style × mode) benchmark results |
| `AutoRouter` | `best_candidates()` returns ordered provider list by overall_score |
| `ExecutionLog` | Tracks actual token usage, cost, quality per execution |

Score formula: `overall_score = 0.55·q_aura + 0.15·Δq + 0.15·latency_score + 0.15·cost_score`

### 8.2 `aura_llm_egress.py` — External LLM Egress

Class: `ExternalLLM` — `generate(prompt)` and `interpret(reply)` — the single point where paid API calls occur. Everything else in AuraOS is LLM-free.

### 8.3 `aura_substrate.py` — Polysynthetic Substrate

Class: `AuraSubstrate` — `compile(text, style, output_mode)` — compresses text into optimized LLM prompts using bracket, polysynthetic, or standard styles. Saves 80%+ on input tokens.

### 8.4 `aura_API_rotator.py` — API Key Rotator

| Function | Description |
|----------|-------------|
| `load_secrets(path)` | Load API keys from aura_secrets.json |
| `gemini_key_pool(secrets)` | Extract all valid Gemini keys |
| `gemini_generate(prompt, secrets, rotator)` | Gemini API call with rotating key pool |
| `openai_compatible_generate(url, key, payload)` | Generic OpenAI-compatible API call |
| `get_gemini_rotator(secrets)` | Return GeminiRotator instance |

### 8.5 `aura_anthropic_router.py` — Anthropic-First Router

Class: `AnthropicRouter` — `generate(prompt, timeout)` — routes through Anthropic → Sambanova → OpenAI-compatible chain with full failover.

### 8.6 `aura_benchmark_sandbox.py` — Benchmark Sandbox

Class: `BenchmarkSandbox` — `scan_and_run()` — detects new/updated API keys and runs multi-stage benchmark (indexing + recursive MAS) against all configured providers.

### 8.7 `aura_matrix_benchmark.py` — Matrix Benchmark

| Class | Purpose |
|-------|---------|
| `MockEgress` | Returns deterministic valid JSON edit plan (no API cost) |
| Run matrix across all (provider × packet_style × output_mode) combinations |

### 8.8 `aura_converse.py` — Polysynthetic Conversation

| Class | Purpose |
|-------|---------|
| `CommProfile` | User communication style tracking |
| `ConversationLog` | Polysynthetic turn logging |
| `Conversationalist` | Main conversation engine: compress → LLM → interpret |

### 8.9 `aura_single_seed_lift.py` - Single-Seed Context Lift

Portable context-lift primitive inspired by arXiv:2606.20633. The paper reports
a cofactor-free lift with one cached inverse, `O(m^2)` per precision layer, and
`33.5x` speedup in a high-precision benchmark. Aura adapts the pattern to local
VSA context as one deterministic seed vector, one cached inverse digest, bounded
residual lift layers, and compact trace dispatch.

| Function | Description |
|----------|-------------|
| `compile_single_seed_lift(label, vectors, base_vector)` | Selects the best local seed vector, caches its inverse profile, lifts it through bounded residual layers, and returns a lifted 10,000-D phasor plus metadata. |
| `compile_text_single_seed_lift(label, text_blocks)` | Builds the same profile from text blocks for Fusion capsules or other local summaries. |
| `compact_lift_capsule(profile)` | Converts the profile to a short `SEED=...\|TRACE=...` capsule suitable for RAEC slots and task capsules. |

### 8.10 `aura_context_crusher.py` - Reversible Context Crushing

Headroom-inspired, Aura-native compression before LLM egress. It is
dependency-free, local-first, reversible through the CCR ledger, and can
optionally hand JSON/log/text byte sweeps to `aura_crush_core.rs` through the
Rust/WASI bridge. If no accelerator is present, Aura stays on the Python path.
GLOSSOPETRAE-inspired ST3GG logic is used only as visible, signed recall
metadata: no invisible Unicode carriers, no covert payloads, and no guardrail
evasion machinery.

| Function | Description |
|----------|-------------|
| `apply_context_crush_to_prompt(prompt)` | Strips tokenizer-survival carriers, routes one prompt through JSON/log/search/code/text compression, and stores the original when the compressed form wins. |
| `apply_context_crush_to_messages(messages)` | Sanitizes all string messages, compresses non-system messages, and preserves normal system prompt bytes for cache stability. |
| `compute_cache_prefix_report(messages)` | Emits stable prefix hash, byte/token estimate, and volatile-content findings. |
| `retrieve_context_crush(hash, query)` | Retrieves the full original or query-matching lines from the visible ST3GG sidecar index first, then falls back to the local CCR ledger. |

Related modules:

| Module | Function | When needed |
|--------|----------|-------------|
| `aura_st3gg_recall.py` | `compile_st3gg_pointer(content)` | Generates a deterministic visible `ST3GG-L2::<namespace>:<glyph>:<dash>` pointer and holographic header for local recall. |
| `aura_st3gg_recall.py` | `compile_visible_st3gg_capsule(data)` | Converts compact JSON-like rows or dictionaries into a visible ASCII machine capsule when that is shorter than normal JSON sketches. |
| `aura_st3gg_recall.py` | `upsert_st3gg_recall(...)` / `lookup_st3gg_recall(key)` | Maintains `.st3gg_hash.bin`, `.st3gg_store.jsonl`, and `.st3gg_index.json` sidecars so Aura can recall a compressed original by CCR hash, ST3GG pointer, or DASH key without scanning or loading the JSONL ledger first. |
| `aura_st3gg_recall.py` | `st3gg_recall_index_stats(ledger_path)` | Reports active sidecar capacity, load factor, bits/key, byte footprint, and whether the ledger is large enough to justify a future frozen PtrHash/perfect-hash segment. |
| `aura_st3gg_recall.py` | `compute_compaction_efficiency(keys, bytes, latency)` | Scores a recall index against the 1.44 bits/key MPHF lower-bound target while labeling the current Python path as bounded active hashing, not frozen perfect hashing. |
| `aura_st3gg_compact.rs` | `rustc -O aura_st3gg_compact.rs -o Aura_Memory/st3gg_compact` | Builds the zero-dependency Stage 2 pilot compiler. It reads newline-separated unique CCR/ST3GG/DASH keys from stdin and writes a versioned binary header (`AST3CMP1`, version, key count, table size, table scale, hash profile) plus `N` pilot bytes to stdout. |
| `aura_st3gg_recall.py` | `decode_st3gg_compaction_blob(blob)` | Validates the Stage 2 compactor header before Aura accepts frozen pilot bytes. Rejects bad magic, unsupported versions, table-scale/hash-profile mismatches, and pilot-count mismatches. |
| `aura_tokenizer_guard.py` | `sanitize_tokenizer_channels(text)` | Removes tag chars, private-use chars, variation selectors, bidi controls, and hidden format controls before LLM egress. |
| `aura_tokenizer_guard.py` | `sanitize_message_payloads(messages)` | Applies the same guard to OpenAI-compatible message lists while leaving non-string structured content alone. |

### 8.11 `aura_wasm_bridge.py` - Rust/WASI Accelerator Bridge

Optional no-daemon native bridge for Rust accelerators. It reads
`AURA_CRUSH_ACCELERATOR_PATH`, supports native binaries plus `.wasm` / `.cwasm`
through the `wasmtime` CLI, and returns `None` when unavailable so callers can
fall back cleanly.

| Function | Description |
|----------|-------------|
| `AuraRustWasmBridge.from_env()` | Discovers an explicit or repo-local context-crush accelerator without forcing a dependency. |
| `AuraRustWasmBridge.accelerate(raw, content_type)` | Sends a hex-encoded payload over stdin and reads a compressed hex result over stdout. |
| `accelerator_runtime_status(root)` | Reports whether Aura is using native/WASM acceleration or the Python fallback. |

`aura_crush_core.rs` is the matching Rust source. Build it as either a native
binary or a WASI module:

```bash
rustc -O aura_crush_core.rs -o Aura_Memory/aura_crush_core
rustc --target wasm32-wasip1 -O aura_crush_core.rs -o Aura_Memory/aura_crush_core.wasm
```

### 8.12 `aura_pricing.py` — Price Book

Class: `PriceBook` — maintains per-model pricing ($/1M tokens) for accurate savings calculation. `get_pricebook()` returns the current snapshot.

### 8.13 `aura_proxy_benchmark.py` — Quality Scoring

Class: `QualityScorer` — validates LLM output quality by diff, token count, and structural compliance.

### 8.14 `aura_token_economics.py` — Token Economics

Class: `TokenEconomics` — `compute_delta(model, raw_in, raw_out, aura_in, aura_out)` — computes cost savings from Aura's compression. `log_call(delta, task, provider)` — records in ledger.

### 8.15 `aura_self_optimize.py` — Autonomous Self-Optimization

| Function | Description |
|----------|-------------|
| Main pipeline | Substrate → best model → json_edit_plan → ASCII-sanitize → verify → retry |

---

## 9. Self-Healing & Evolution Modules

### 9.1 `aura_evolve.py` — LiquidFlashEvolve (HARDENED)

**Class: `LiquidFlashEvolve`**

| Method | Description |
|--------|-------------|
| `_generate_process_glyph` | Synthesize ST3GG categorization hex stamp |
| `_extract_code_block` | Parse [CODE] blocks from LLM output |
| `_invoke_patch_engine` | GBNF-constrained code generation |
| `sandbox_and_evaluate` | Full sandbox cycle: generate → AST parse → security verify → mutation validate → retry |
| `execute_hot_swap` | Write approved mutation to disk with final path-traversal + AST security checks |

**Security Walls** (see §10):
- `_verify_ast_security(tree)` — banned functions/imports, infinite-loop detection, AST node cap
- `_validate_file_write_path(target_file)` — path-traversal guard
- `SandboxViolation` — raised on any security breach

### 9.2 `aura_heal.py` — Autoimmune Healer

| Function | Description |
|----------|-------------|
| `compute_rubric_reward(code, temp, w_ram, w_thermal, w_sat)` | Multi-tier reward: F_RAM + F_thermal + F_SAT → score ∈ [0,1] |
| `map_neural_architecture(filepath, code)` | Generate 3D AST skeleton with decorators/args |
| `agentic_optimization(filename, original_code, external_knowledge)` | 3-stage workflow: plan → weave → test |
| `forage_knowledge_from_links(link_file_path)` | Crawl URLs, extract text/PDF, build knowledge cache |
| `heal_system()` | Scan all .py files, apply agentic optimization with external knowledge |

### 9.3 `aura_self_reflect.py` — Self-Reflection Engine

Class: `SelfReflectEngine(node_ref)` — `execute_cycle(compile_unified_graph, invoke_cloud, cloud_engine)` — runs VSA resonance analysis, WASM offload metrics, cloud architect diagnosis, and outputs an actionable patch recommendation.

### 9.4 `aura_evolution_bridge.py` — Evolution Bridge

| Function | Description |
|----------|-------------|
| `validate_proposed_mutation(code, module_name, baseline_friction, proposed_friction, check_topology)` | Returns MutationVerdict dataclass with `approved` bool + `human_report()` string |
| `speculative_topology_check(module_name, proposed_ast)` | Pre-check topological impact of proposed mutation |

### 9.5 `aura_patcher.py` — Sovereign Patcher

Class: `AuraSovereignPatcher(node_ref)` — `execute_patch_swap(file_path, start_anchor, end_anchor, replacement_block, st3gg_synopsis)` — surgically replaces code blocks between anchor markers.

### 9.6 `aura_namespace_sanitizer.py` — Namespace Sanitizer

| Function | Description |
|----------|-------------|
| `strip_redundant_imports(source_code)` | Remove duplicate stdlib imports from local scopes |
| `hoist_imports_to_top(source_code)` | Move remaining required namespaces to module top |
| `sanitize_module(file_path)` | Full pass: strip → hoist → AST-validate → write |
| `sanitize_all_modules(root_dir)` | Batch sanitize all .py files in directory |
| `_verify_ast_security(tree)` | AST security check for banned patterns |
| `_validate_file_write_path(target_file)` | Path-traversal validation |

### 9.7 `aura_mitosis.py` — Mitosis Engine

Class: `AuraMitosisEngine(dimension=10000, threshold=2.5)`

| Method | Description |
|--------|-------------|
| `calculate_energy_landscape(active_wave, crystal_list)` | Compute energy vs crystallized truths |
| `process_ledger_update(real_part, continuous_physics_error)` | Update manifold tension; return (tension, avalanche_ready) |
| `execute_music_inversion(active_wave)` | Frequency-domain music inversion for truth crystallization |
| `execute_morphemic_mitosis(conn)` | Purge low-resonance records → SQLite VACUUM |

---

## 10. Security & Integrity Modules

### 10.1 `pvm_memory_guard.py` — PVM Memory Guard

| Function | Description |
|----------|-------------|
| `sample_rss_mb()` | Return current process RSS in MB |
| `heap_snapshot()` | Return dict of type → object count |
| `assert_zero_copy(arr, name)` | Validate numpy array meets zero-copy discipline |
| `zero_copy_zeros(shape, dtype, order)` | Safe wrapper: zeros + validate |
| `zero_copy_frombuffer(buf, dtype)` | Safe wrapper: frombuffer + validate |

Class: `MemoryBudget` — context manager enforcing RAM ceiling (default 4096 MB). Pure-asyncio async monitor with sync fallback.

### 10.2 `symbolic_shield.py` — Symbolic Shield

Function: `verify_structural_truth(code_string)` — runs 5 AST gates checking structural integrity, returns True/False.

### 10.3 `aura_crypto_puf.py` — Thermodynamic PUF

Class: `AuraThermodynamicPUF(dimension=10000)` — `distill_liquid_key(system_tension, physics_error)` — generates cryptographic key from system entropy.

### 10.4 `aura_privacy_io.py` — Differential Privacy

Class: `MetaTelemetryIngestor` — applies differential privacy noise to telemetry vectors with configurable ε.

---

## 11. Visualization & AR Modules

### Overview

AuraOS operates **four distinct WebSocket servers** and **one WebSocket client bridge** to provide a layered AR visualization stack. Understanding the relationship between them is critical.

```
┌─────────────────────────────────────────────────────────────────┐
│                   AURAOS WEBSOCKET AR ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐     ws://127.0.0.1:8765    ┌────────────────┐  │
│  │  index.html  │ ◄────────────────────────── │  aura_node.py  │  │
│  │ (AR Viewer)  │     Simple text pulses      │ ar_server()    │  │
│  │              │     AR shape morphing        │ broadcast_ar   │  │
│  │              │                              │ _pulse()       │  │
│  └──────┬───────┘                              └───────┬────────┘  │
│         │                                              │           │
│         │  ws://127.0.0.1:8765                         │ fires     │
│         │  (when !ar_start is run)                     │ JSON      │
│         ▼                                              │ pulses    │
│  ┌──────────────────────┐                     ┌────────▼────────┐  │
│  │ AuraARWebSocketServer│                     │   pulse.py      │  │
│  │ (topology_ws_bridge) │                     │ Port 8081       │  │
│  │                      │                     │                 │  │
│  │ Shape interaction:   │                     │ LiquidWebSocket │  │
│  │ • TOPOLOGY_REQUEST   │                     │ ST3GG stamps    │  │
│  │ • SHAPE_INTERACTION  │                     │ Memory watcher  │  │
│  │ • ADD_SHAPE          │                     └────────┬────────┘  │
│  │ • HOTSWAP_REQUEST    │                              │           │
│  │ • SUBSCRIBE/UNSUB    │                              │ Internal  │
│  │ • PING/PONG          │                              │ routing   │
│  └──────────────────────┘                     ┌────────▼────────┐  │
│                                                │ aura_node.py   │  │
│  ┌──────────────────────┐                     │ (outgoing WS    │  │
│  │ spatial_mapper.py    │                     │  client to      │  │
│  │ aura_tmm_server()    │                     │  pulse 8081)    │  │
│  │ Port 8000            │                     └────────────────┘  │
│  │ Topology Map Manager │                                         │
│  └──────────────────────┘                                         │
│                                                                   │
│  ┌──────────────────────┐                                         │
│  │ TopologyBroadcastHub │  Internal 4KB chunked broadcast         │
│  │ (topology_ws_bridge) │  Used by stream_to_clients()            │
│  └──────────────────────┘                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 11.1 Port 8765 — Simple AR Visual Cortex Server (aura_node.py)

**Auto-started at boot** by `aura_node.py`. This is the simplest WebSocket server — it just tracks connected clients and broadcasts plain-text pulses.

**Code location**: `aura_node.py` lines ~6600-6620

```python
connected_ar_clients = set()

async def ar_server(websocket):
    connected_ar_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_ar_clients.remove(websocket)

async def broadcast_ar_pulse(intent_string):
    if connected_ar_clients:
        websockets.broadcast(connected_ar_clients, intent_string)
```

**Startup**:
```python
await websockets.serve(ar_server, "127.0.0.1", 8765)
```

**What it does**: Any module in `aura_node.py` can call `broadcast_ar_pulse(text)` to send a plain-text message to all connected AR viewers. The `index.html` client connects to this port and watches for these text messages to morph its 3D avatar.

### 11.2 Port 8765 — Interactive AR Topology Server (aura_topology_ws_bridge.py)

**Started on-demand** via REPL command `!ar_start` (or `!ar_server_start`). This is a full-featured interactive AR WebSocket server (`AuraARWebSocketServer`) that exposes the code topology as interactive 3D shapes.

**Start/Stop**:
```
!ar_start    → Starts AuraARWebSocketServer on ws://0.0.0.0:8765
!ar_stop     → Graceful shutdown, disconnects all clients
```

**Feature summary**:
- Auto-refreshes topology from `Aura_Memory/live_topology_ast.json` every 1.0 second
- Maps AST node types to 3D shapes with color coding
- Accepts interactive shape commands (expand, contract, select, deselect)
- Supports adding custom shapes, topic subscriptions, and hotswap requests

**Node Type → Shape Mapping**:

| AST Node Type | 3D Shape | Color |
|---------------|----------|-------|
| `class` | Sphere | Cyan `#00E5FF` |
| `async_method` | Icosahedron | Neon Pink `#FF007F` |
| `function` | Tetrahedron | Purple `#E040FB` |
| `method` | Tetrahedron | Blue `#2196F3` |
| `module` | Cube | Green `#4CAF50` |
| `helper` | Cube | Gray `#9E9E9E` |

**Client → Server Messages**:

| Message Type | Fields | Description |
|-------------|--------|-------------|
| `TOPOLOGY_REQUEST` | `{"type": "TOPOLOGY_REQUEST"}` | Request current topology snapshot |
| `SHAPE_INTERACTION` | `{"type": "SHAPE_INTERACTION", "shapeId": "...", "action": "expand|contract|select|deselect"}` | Modify a shape: expand (scale×1.5, max 3.0), contract (scale×0.7, min 0.3), select (yellow highlight), deselect (restore original color) |
| `ADD_SHAPE` | `{"type": "ADD_SHAPE", "functionData": {"name": "...", "type": "...", "position": [x,y,z], "scale": 1.0}}` | Add a new shape to the topology |
| `HOTSWAP_REQUEST` | `{"type": "HOTSWAP_REQUEST", "targetId": "...", "newFunction": "..."}` | Request AST surgical graft (queues hotswap) |
| `SUBSCRIBE` | `{"type": "SUBSCRIBE", "topic": "topic_name"}` | Subscribe to a named event topic |
| `UNSUBSCRIBE` | `{"type": "UNSUBSCRIBE", "topic": "topic_name"}` | Unsubscribe from a topic |
| `PING` | `{"type": "PING"}` | Health check |

**Server → Client Messages**:

| Message Type | Fields | Description |
|-------------|--------|-------------|
| `TOPOLOGY_UPDATE` | `{"type": "TOPOLOGY_UPDATE", "data": {"nodes": [...], "edges": [...], "metadata": {...}}}` | Full topology snapshot sent on connect and after each refresh |
| `SHAPE_UPDATE` | `{"type": "SHAPE_UPDATE", "shapeId": "...", "state": {"scale": 1.5, "color": "#FFFF00"}}` | Broadcast after a shape is modified |
| `SHAPE_ADDED` | `{"type": "SHAPE_ADDED", "shape": {"id": "...", "type": "...", ...}}` | Broadcast when a new shape is added |
| `HOTSWAP_COMPLETE` | `{"type": "HOTSWAP_COMPLETE", "targetId": "...", "result": {...}}` | Broadcast after a hotswap is queued |
| `PONG` | `{"type": "PONG"}` | Response to PING |
| `ERROR` | `{"type": "ERROR", "message": "..."}` | Error response |

### 11.3 Port 8081 — Aura Sovereign Mesh Bridge (pulse.py)

**Purpose**: The cognitive bridge between AuraOS's internal reasoning and the AR visual deck. Processes incoming JSON commands through a liquid neural kernel (`LiquidWebSocket`), injects ST3GG steganography stamps from the latest `.st3` engram file, and broadcasts processed payloads to all connected AR clients.

**Start**: `python3 pulse.py` (standalone) or integrated into `aura_node.py` flow.

**Core processing pipeline** (for each message received):
1. Parse JSON from client
2. Process through `LiquidWebSocket.process_command()` → runs through `LiquidStateMachine` + `AdaptiveLiquidTimeConstant` + Maxwell physics correction + ternary quantization
3. Find latest `.st3` engram from `Aura_Memory/`
4. Inject `__st3gg__` holographic stamp into payload
5. Broadcast processed payload to all connected clients

**Background `watch_memory()` loop**: Polls `Aura_Memory/` every 1 second for new `.st3` engram files. When detected, broadcasts:
```json
{
  "shape": "HolographicEngram",
  "lum": "MAX",
  "temp": "HOT",
  "mutation_id": "<engram_name>",
  "status": "SYS_HEAL_COMPLETE"
}
```

**Outgoing AR pulses from aura_node.py**: `aura_node.py` internally connects as a WebSocket client to `ws://127.0.0.1:8081` to fire AR pulses during key events:

| Trigger | JSON Payload |
|---------|-------------|
| SIMD consolidation success | `{"shape": "SPHERE_COLD", "consolidation": "simd_complete"}` |
| Quantum breakthrough | `{"shape": "ICOSAHEDRON_HOT", "breakthrough": "quantum_tunneling"}` |
| AST tree graft complete | `{"shape": "TETRAHEDRON_HOT", "graft": "ast_surgery"}` |
| Self-optimization staged | `{"shape": "TETRAHEDRON_HOT", "optimization": "staged"}` |

### 11.4 Port 8081 — Topology Chunked Broadcast (aura_topology_ws_bridge.py)

The `TopologyBroadcastHub` class in `aura_topology_ws_bridge.py` provides an alternative topology streaming mechanism on port 8081 (via `stream_to_clients()`). It:

- Reads `Aura_Memory/live_topology_ast.json`
- Chunks the JSON into **4KB fixed-frame packets** with sequence metadata
- Broadcasts to all connected WebSocket clients with backpressure control
- Polls file mtime every 0.5s and auto-broadcasts on change

**Chunk frame format**:
```json
{
  "type": "topology_frame",
  "seq": 0,
  "total": 5,
  "payload": "partial_json_string_here..."
}
```

### 11.5 Port 8000 — Topology Map Manager (spatial_mapper.py)

**Function**: `aura_tmm_server(websocket)` — WebSocket handler for the Topology Map Manager on port 8000. Provides 3D spatial vector representations of Python source code nodes.

### 11.6 `index.html` — 3D/AR Visualizer

Client-side WebGL visualizer using Three.js r128 that connects to `ws://127.0.0.1:8765`.

**Connection**: Auto-connects on page load to `ws://127.0.0.1:8765`

**Visualization Modes** (triggered by text messages from the server):

| Message Text | Resulting Geometry | Color | Wireframe |
|-------------|-------------------|-------|-----------|
| Contains `"TETRAHEDRON_HOT"` | TetrahedronGeometry(2) | Red `#ff1100` | Yes |
| Contains `"SPHERE_COLD"` | SphereGeometry(1.5) | Blue `#0088ff` | Yes |
| Contains `"ICOSAHEDRON_HOT"` | IcosahedronGeometry(1.3) | Pink `#ff0077` | Yes |
| Contains `"WIPE"` | SphereGeometry(1.5) (default) | Cyan `#00ffff` | Yes |
| Contains `"TOPOLOGY_UPDATED"` | IcosahedronGeometry(2) | Gold `#ffaa00` | Yes |
| Any other message | Current geometry stays | Cyan default | Yes |

**UI Elements**: Status indicator (`WebSocket: CONNECTED/DISCONNECTED`), Cognitive State display (updates with message content).

**Controls**: None. This is a pure display — the 3D avatar morphs automatically based on server-sent text messages.

### 11.7 `aura_topological_scanner.py` — Topology Scanner

| Function | Description |
|----------|-------------|
| `extract_ast_calls(file_content, filename)` | Extract function-level call graphs via AST |
| `scan_regex_signatures(file_content)` | Detect shared SQLite tables, ports, filesystem paths |
| `compile_unified_graph()` | Full scan: spatial_mapper → AST calls → regex signatures → shared-resource edges |
| `compile_topology_map(deep=False)` | Fast or deep scan mode |

### 11.8 `aura_topology_manager.py` — Deep Topology Manager

Class: `TopologyBuilder(root)` — `run()` produces enriched topology payload with: proper node IDs (no '?' orphans), deduplication, import-level edges, per-file metrics, hub diagnostics.

### 11.9 `aura_topology_analyzer.py` — Fracture Analysis

Function: `diagnose_fractures()` — returns dict with total fracture count and by-kind breakdown.

### 11.10 `spatial_mapper.py` — Spatial Mapper

| Class/Function | Purpose |
|----------------|---------|
| `CodeTopologyMapper` | AST visitor that maps classes/functions to 3D nodes |
| `DirectoryCache` | Filesystem traversal cache with invalidation |
| `scan_and_vectorize(root_dir)` | Full directory scan returning node topology list |
| `aura_tmm_server(websocket)` | WebSocket server for Topology Map Manager (port 8000) |

### 11.11 `liquid_kernel.py` — Liquid Kernel

Class: `LiquidWebSocket` — WebSocket-connectable liquid state machine implementing:
- `LiquidStateMachine` with 3 `LiquidNeuron` instances, ternary quantization, excitatory/inhibitory pathways
- `AdaptiveLiquidTimeConstant` — LTC-NDE solver with configurable τ
- `PhysicsInformedCorrection` — Maxwell damping correction
- `TernaryQuantizer` — 1.58-bit ternary quantization
- `mLSTMCell` — Extended LSTM Matrix Memory Cell (NeurIPS 2024)

| Method | Description |
|--------|-------------|
| `process_command(command: dict) → dict` | Full pipeline: LiquidState update → quantize → return state (non-string values quantized to ternary) |

### 11.12 `liquid_fhrr.py` — Liquid FHRR

Class: `LiquidFHRR(dim)` — Fractional Holographic Reduced Representation engine.

| Method | Description |
|--------|-------------|
| `generate_phasor()` | Generate complex exponential phasor |
| `bind(v1, v2)` | Circular convolution binding |
| `unbind(v1, v2)` | Circular correlation unbinding |
| `bundle(vectors)` | Element-wise mean superposition |
| `similarity(v1, v2)` | Cosine similarity in complex space |
| `fractional_bind(phasor, t)` | Bind at continuous real-valued time t |

### 11.13 `vsa_resonator.py` — VSA Resonator

Class: `VSAResonator(dim)` — GSB (Gold-Silver-Bronze) quantized vector resonator.

| Method | Description |
|--------|-------------|
| `gsb_quantize(vector)` | Decompose into 3-tier quantized representation |
| `sampled_similarity(g1,s1,b1, g2,s2,b2)` | Fast approximate similarity from quantized state |

---

## 12. Infrastructure & Utility Modules

### 12.1 `logging_kit.py` — Logging Kit

| Function | Description |
|----------|-------------|
| `setup_sqlite_logging()` | Initialize structured SQLite logging with log_report + log_error |
| `log_error(tag, message)` | Record error event |
| `log_report(report_type, content, metadata)` | Record structured report |

### 12.2 `mint_genesis.py` — Genesis Block Minting

| Function | Description |
|----------|-------------|
| `generate_genesis_block_async()` | Async genesis block mint with memory-buffered atomic write |
| `generate_genesis_block()` | Synchronous CLI wrapper |

### 12.3 `systems_check.py` — System Verification

Verifies all subsystems are operational: LLM server, memory palace, topology scanner, WebSocket servers.

### 12.4 `fix_db.py` — Database Repair Utility

Standalone script to check and rebuild corrupted SQLite databases in ~/.mempalace/.

### 12.5 `verify_os.py` — OS Verification

Checks the operating system environment for AuraOS compatibility.

### 12.6 `llama_server_manager.py` — LLM Server Manager

Class: `LlamaServerManager(model_path, port, context_limit, batch_size)` — manages the llama.cpp server subprocess lifecycle.

### 12.7 `apply_graft.py` — Manual Graft Tool

Function: `execute_manual_graft(target_module, incubator_module, target_function)` — standalone AST surgical graft tool.

### 12.8 Support Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Install Termux packages (python, cmake, git, etc.) |
| `setup_aura.sh` | Full AuraOS environment bootstrap |
| `build_aura.sh` | Build native accelerators and WASM modules |
| `aura_unifier.sh` | Unify split/broken module states |

### 12.9 Non-Python Modules

| File | Language | Purpose |
|------|----------|---------|
| `cognitive_search.rs` | Rust | ST3GG-secure holographic DKT search |
| `dag_executor.rs` | Rust | Deterministic DAG execution engine |
| `quantum_dag.py` | Python | Quantum Merkle-DAG state management |
| `universal_decipher.rs` | Rust | Universal script decipherment |
| `bus_init.cpp` | C++ | System bus initialization |

### 12.10 `aura_gbnf_profiles.py` — Grammar Profiles

| Profile | Use Case |
|---------|----------|
| `PROFILE_POLYSYNTHETIC` | Standard polysynthetic code generation |
| `PROFILE_PYTHON_PATCH` | Constrained Python code patches |
| `PROFILE_UNIT_INTERVAL` | Numeric [0,1] confidence scores |
| `PROFILE_MC_LETTER` | Single-letter multiple-choice responses |

---

## 13. Workflow Patterns

### Starting AuraOS

```bash
python3 aura_node.py
```

You'll see boot messages as the system initializes:
- Memory Palace (SQLite WAL)
- VSFT Matrix compilation (lexicon → vector routes)
- Ecosystem Audit (all .py files scanned and stamped)
- LLM server startup (if configured)
- Simple AR WebSocket server on ws://127.0.0.1:8765
- Background daemons (memory condenser, meta-learning, DAG walker)

The prompt `[Dallas] >` is where you type commands.

### Basic Workflow: Conversation

```
[Dallas] > Hello Aura, can you explain what you are?
[Aura] > I am AuraOS, a sovereign edge cognitive substrate running entirely on this device...
```

### Research Workflow

```
[Dallas] > !topology
  # Scans all .py files → Aura_Memory/live_topology_ast.json

[Dallas] > !backtrack
  # Fetches 20 recent arXiv papers

[Dallas] > !research vector symbolic architecture
  # Queries ingested papers, synthesizes Python helper into aura_incubator.py

[Dallas] > !stage
  # Preview the staged code

[Dallas] > !stage_merge
  # Safety review → merge into aura_incubator.py
```

### Self-Improvement Workflow

```
[Dallas] > !self_reflect
  # Aura analyzes itself, finds friction points, proposes patches

[Dallas] > !self_optimize
  # Full optimization cycle: audit → patch → verify → stage

[Dallas] > !stage
  # Review the patch

[Dallas] > !stage_merge
  # Approve and merge
```

### LLM Calibration Workflow

```bash
# Set up API keys in aura_secrets.json first

[Dallas] > !calibrate
  # Runs full (provider × style × mode) benchmark matrix

[Dallas] > !route mesh_offload
  # Auto-routes to best provider from calibration results

[Dallas] > !savings
  # See cumulative token + cost savings
```

### AR Visualization Workflow — Quick Start

```
# Step 1: Run topology scan
[Dallas] > !topology

# Step 2: Start the interactive AR server
[Dallas] > !ar_start

# Step 3: Open index.html in Chrome on the same device
#         The page auto-connects to ws://127.0.0.1:8765 and displays
#         the codebase as interactive 3D shapes.

# Step 4: Interact via WebSocket (see §15 for full message reference)
#         Connect any WebSocket client to ws://127.0.0.1:8765
#         and send JSON commands to manipulate the topology view.
```

### AR Visualization Workflow — Advanced Shape Interaction

```
# After !ar_start is running, connect a WebSocket client to ws://127.0.0.1:8765:

# Get the current topology
→ {"type": "TOPOLOGY_REQUEST"}

# Expand a shape (zoom in on a function)
→ {"type": "SHAPE_INTERACTION", "shapeId": "my_function", "action": "expand"}

# Select a shape (highlight it yellow)
→ {"type": "SHAPE_INTERACTION", "shapeId": "my_function", "action": "select"}

# Contract a shape
→ {"type": "SHAPE_INTERACTION", "shapeId": "my_function", "action": "contract"}

# Deselect (restore original color)
→ {"type": "SHAPE_INTERACTION", "shapeId": "my_function", "action": "deselect"}

# Add a custom shape
→ {"type": "ADD_SHAPE", "functionData": {"name": "new_fn", "type": "function", "position": [1.0, 2.0, 0.0], "scale": 1.5}}

# Subscribe to event topics
→ {"type": "SUBSCRIBE", "topic": "topology_updates"}

# Health check
→ {"type": "PING"}
```

### Standalone AR Bridge Workflow

```bash
# Start the AR pulse bridge independently
python3 pulse.py

# This runs on ws://0.0.0.0:8081
# Connect any WebSocket client to send JSON commands through the
# LiquidKernel neural processor. Commands are processed, stamped
# with ST3GG holographic signatures, and broadcast to all clients.
```

---

## 14. Troubleshooting

### Database Corruption
```bash
python3 fix_db.py              # Check + repair all DBs
# OR from within AuraOS:
!db_repair                     # Interactive repair
```

### LLM Server Issues
```
!benchmark                     # Check LLM server status
python3 llama_server_manager.py --start  # Manually start
```

### Memory Pressure
```bash
python3 test_memory_guard_leak.py  # Run memory diagnostics
# AuraOS auto-throttles: foraging suspended at 52°C, WAL checkpoint at ≤38°C
```

### API Key Issues
```bash
python3 aura_router.py list-providers  # Check which keys are detected
# Edit aura_secrets.json, then:
!calibrate                     # Re-run calibration
```

### AR / WebSocket Issues

| Symptom | Solution |
|---------|----------|
| index.html shows "DISCONNECTED" | Ensure `aura_node.py` is running (starts the simple AR server automatically). Check that `!ar_start` has been run if you want interactive shapes. |
| `!ar_start` says server already running | Use `!ar_stop` first, then `!ar_start` to restart. |
| `!topology` says "No AR viewers connected" | Open `index.html` in a browser on the same device. The page auto-connects to `ws://127.0.0.1:8765`. |
| AR shapes don't update after `!topology` | Run `!ar_start` to enable the interactive topology server that auto-refreshes every 1 second. The simple AR server only gets updates when `broadcast_ar_pulse()` is explicitly called. |
| pulse.py won't bind to port 8081 | Check if another process is using port 8081: `lsof -i :8081`. The LLM server also uses port 8081 for its HTTP API — ensure `pulse.py` and `llama_server_manager.py` aren't both trying to bind the same port. |
| WebSocket connection refused | Verify the port: simple AR = `8765`, AR shape server = `8765` (same port, different server instance), pulse bridge = `8081`, TMM = `8000`. |
| Shapes are all gray cubes | The topology JSON at `Aura_Memory/live_topology_ast.json` may be missing or malformed. Run `!topology` to regenerate it. |

### AR WebSocket Port Summary

| Port | Server | Bind Address | Started By | Purpose |
|------|--------|-------------|-----------|---------|
| 8765 | Simple AR (`ar_server`) | `127.0.0.1` | Auto at boot | Receives text pulses → 3D avatar morphing |
| 8765 | Interactive AR (`AuraARWebSocketServer`) | `0.0.0.0` | `!ar_start` | Shape interaction, topology browsing, hotswap |
| 8081 | AR Pulse Bridge (`pulse.py`) | `0.0.0.0` | Standalone / integrated | LiquidKernel processing, ST3GG stamps, memory watching |
| 8000 | Topology Map Manager (`spatial_mapper.py`) | unspecified | On-demand | 3D spatial vector topology mapping |

### General Diagnostics
```
!benchmark                     # CPU temp, RAM, disk, inference throughput
!system_audit                  # Full ecosystem audit
python3 systems_check.py       # Standalone verification
```

---

## 15. WebSocket & AR Command Reference

This section is the definitive reference for all WebSocket-based AR communication in AuraOS.

### 15.1 Simple AR Server (Port 8765, auto-started)

**Connect**: `ws://127.0.0.1:8765`

**Protocol**: Plain-text messages. No JSON structure required.

**Server → Client** (messages from `broadcast_ar_pulse()`):

| Message Text | Trigger | Effect in index.html |
|-------------|---------|---------------------|
| `TETRAHEDRON_HOT` | Quantum/evolution hot event | Red wireframe tetrahedron |
| `SPHERE_COLD` | SIMD consolidation success | Blue wireframe sphere |
| `ICOSAHEDRON_HOT` | Quantum breakthrough | Pink wireframe icosahedron |
| `WIPE` | AR display reset | Default cyan sphere |
| `TOPOLOGY_UPDATED:123nodes:456edges` | After `!topology` scan | Gold icosahedron + status text update |

**Client → Server**: Not applicable. This server only broadcasts — it does not read client messages (`wait_closed()` only).

### 15.2 Interactive AR Shape Server (Port 8765, !ar_start)

**Connect**: `ws://0.0.0.0:8765` (after running `!ar_start`)

**Protocol**: JSON messages with `"type"` field.

#### Server → Client Messages

##### TOPOLOGY_UPDATE (sent on connect and every 1s refresh)
```json
{
  "type": "TOPOLOGY_UPDATE",
  "data": {
    "nodes": [
      {
        "id": "aura_node:main_loop",
        "type": "Sphere",
        "label": "main_loop",
        "position": [1.5, 2.0, 0.0],
        "scale": 1.0,
        "color": "#00E5FF",
        "metadata": {"ast_data": {...}}
      }
    ],
    "edges": [
      {
        "id": "edge_001",
        "sourceId": "aura_node:main_loop",
        "targetId": "aura_node:invoke_engine",
        "color": "#FFFFFF",
        "width": 0.1
      }
    ],
    "metadata": {
      "node_count": 247,
      "edge_count": 831,
      "source": "live_topology_ast.json"
    }
  }
}
```

##### SHAPE_UPDATE
```json
{
  "type": "SHAPE_UPDATE",
  "shapeId": "aura_node:my_function",
  "state": {"scale": 1.5, "color": "#FFFF00"}
}
```

##### SHAPE_ADDED
```json
{
  "type": "SHAPE_ADDED",
  "shape": {
    "id": "uuid-...",
    "type": "Tetrahedron",
    "label": "new_function",
    "position": [1.0, 2.0, 0.0],
    "scale": 1.0,
    "color": "#E040FB",
    "metadata": {"function_data": {...}}
  }
}
```

##### HOTSWAP_COMPLETE
```json
{
  "type": "HOTSWAP_COMPLETE",
  "targetId": "aura_node:some_function",
  "result": {"status": "success", "message": "Hotswap queued"}
}
```

##### PONG
```json
{"type": "PONG"}
```

##### ERROR
```json
{"type": "ERROR", "message": "Shape 'unknown_fn' not found"}
```

#### Client → Server Messages

##### TOPOLOGY_REQUEST
```json
{"type": "TOPOLOGY_REQUEST"}
```
→ Server responds with `TOPOLOGY_UPDATE`

##### SHAPE_INTERACTION
```json
{
  "type": "SHAPE_INTERACTION",
  "shapeId": "aura_node:my_function",
  "action": "expand"
}
```
**Valid actions**:
- `expand` — increase scale by 1.5× (max 3.0)
- `contract` — decrease scale by 0.7× (min 0.3)
- `select` — change color to yellow `#FFFF00`
- `deselect` — restore original color based on node type

→ Server responds with `SHAPE_UPDATE` broadcast

##### ADD_SHAPE
```json
{
  "type": "ADD_SHAPE",
  "functionData": {
    "name": "my_custom_fn",
    "type": "function",
    "position": [1.0, 2.0, 3.0],
    "scale": 1.0
  }
}
```
`type` is mapped to shape: `class`→Sphere, `async_method`→Icosahedron, `function`/`method`→Tetrahedron, other→Tetrahedron (purple `#E040FB`)

→ Server responds with `SHAPE_ADDED` broadcast

##### HOTSWAP_REQUEST
```json
{
  "type": "HOTSWAP_REQUEST",
  "targetId": "aura_node:some_function",
  "newFunction": "def new_impl(): pass"
}
```
→ Server responds with `HOTSWAP_COMPLETE` broadcast

##### SUBSCRIBE / UNSUBSCRIBE
```json
{"type": "SUBSCRIBE", "topic": "topology_updates"}
{"type": "UNSUBSCRIBE", "topic": "topology_updates"}
```

##### PING
```json
{"type": "PING"}
```
→ Server responds with `PONG`

### 15.3 AR Pulse Bridge (Port 8081, pulse.py)

**Connect**: `ws://0.0.0.0:8081`

**Protocol**: JSON in, processed-JSON out (broadcast to all clients).

**Processing pipeline**:
1. JSON payload received
2. Processed through `LiquidWebSocket.process_command()`:
   - Encoded into float values → 3-element numpy array
   - Runs through `LiquidStateMachine` (3-layer ternary-quantized network with excitatory/inhibitory paths)
   - `AdaptiveLiquidTimeConstant` temporal evolution
   - `PhysicsInformedCorrection.maxwell_correction()` damping
   - `TernaryQuantizer` quantizes numeric values to [-1.58, 0, +1.58]
   - String values preserved as-is
3. ST3GG stamp injected: scans `Aura_Memory/` for latest `.st3` engram file → adds `"__st3gg__": "<engram_name>"` to payload
4. Broadcast to all connected clients

**Example**:
```
Client sends:  {"intent": "analyze_module", "target": "aura_core.py", "priority": 0.9}
Server broadcasts: {"intent": "analyze_module", "target": "aura_core.py", "priority": 1.58, "__st3gg__": "thought_20260612_engram"}
```

**Memory watcher auto-broadcasts** (every 1s, on new `.st3` files):
```json
{
  "shape": "HolographicEngram",
  "lum": "MAX",
  "temp": "HOT",
  "mutation_id": "thought_20260612_005342_engram",
  "status": "SYS_HEAL_COMPLETE"
}
```

### 15.4 Topology Chunked Broadcast (Port 8081, stream_to_clients)

**Connect**: `ws://0.0.0.0:8081` (via `stream_to_clients()`)

**Protocol**: 4KB fixed-frame JSON chunks.

**Frame format**:
```json
{
  "type": "topology_frame",
  "seq": 0,
  "total": 5,
  "payload": "{\"nodes\":[{\"id\":\"..."
}
```

**Reassembly**: Concatenate all `payload` strings in `seq` order (0 to total-1), then `JSON.parse` the result.

---

## Appendix A: PWFST Alignment Principles

| Alignment | Ojibwe Meaning | Application |
|-----------|----------------|-------------|
| GIZAAGI'IN | Mutual Benefit | Default for core modules |
| GIDINAWENDIMIN | Swarm Synergy | Mesh networking, healing |
| GWAYAKWAADIZIWIN | Integrity | Measurement, accounting, routing |
| MIIGWECH | Extension-Based Storage | Memory palace, attention buffers |
| MINWAAJIMO | Respectful Transmission | API routing, caching |
| GIWAABAMIN | Transparency & Privacy | Cryptographic modules |

## Appendix B: Data Flow

```
User Input
    │
    ▼
Polysynthetic Decomposition (6 slots)
    │
    ▼
HDC Encoding (10,000-D vector)
    │
    ▼
QFCS Security Screening
    │
    ▼
DIKWP Tier Transformation (Data → Information → Knowledge → Wisdom → Purpose)
    │
    ▼
Cognitive Solvency Audit
    │
    ▼
Game-Theoretic Containment Check
    │
    ▼
Active Inference (Abduction → Simulation → Revision)
    │
    ▼
LLM Generation (local / cloud fallback chain)
    │
    ▼
Holographic DKT Trace Commit
    │
    ▼
Response Output
```

## Appendix C: File Directory Structure

```
~/.mempalace/aura_memory.db     — Primary SQLite database
Aura_Memory/                    — Runtime artifacts
  live_topology_ast.json        — Latest topology scan
  qdkt_index.db                 — QDKT workspace mirror
  qdkt_crystal_cache.json       — Crystallized knowledge
  *.st3 / *.gge                 — Thought engram files
Aura_Staging/                   — Mutation staging area
  pending_patches.json          — Current staged patch
  patch_history.json            — Compounding patch history
Knowledge_Ingest/               — External knowledge sources
aura_exports/                   — !export output directory
```

## Appendix D: WebSocket Port Map

```
PORT  PROTOCOL  BIND         SERVER                    START TRIGGER
────  ────────  ───────────  ────────────────────────  ─────────────
4444  UDP       *            AuraMeshSwarm             Auto at boot
8000  WS        *            spatial_mapper.aura_tmm   On demand
8081  WS        0.0.0.0      pulse.py main()           Standalone
8081  HTTP      127.0.0.1    llama.cpp LLM server      Auto at boot
8765  WS        127.0.0.1    ar_server() (simple)      Auto at boot
8765  WS        0.0.0.0      AuraARWebSocketServer     !ar_start
```

---

*"You are now an architect of your own future."* — AuraOS System Prime
