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
  "MISTRAL_API_KEY": "your-mistral-key",
  "GROQ_API_KEY": "your-groq-key",
  "GITHUB_TOKEN": "your-github-token"
}
```

AuraOS works offline with the local LLM server if no cloud keys are provided.

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
- **ST3GG**: Steganographic glyph system — thermal/moral/friction categorization embedded in all operations
- **DIKWP**: Data → Information → Knowledge → Wisdom → Purpose — cognitive hierarchy
- **PWFST**: Ojibwe governance principles enforced across all modules
- **Hyperdimensional (HDC)**: 10,000-bit binary vectors provide noise-tolerant associative memory

---

## 4. REPL Commands Reference

### Topology & Analysis

| Command | Description |
|---------|-------------|
| `!topology` | Standard AST scan → `Aura_Memory/live_topology_ast.json` |
| `!topology deep` | Deep scan with hub diagnostics, isolated nodes, dangling edges |
| `!catalyze` | Validate pending patches against the live topology graph |
| `!evolve_reasoning` | Crystallise topology into hypertruth manifold |
| `!meta_analyze` | Meta-learning crystallization audit |
| `!meta_reason` | Recursive VSA truth resonance verification (triggers recalibration if < 0.85) |
| `!reason` | Neuro-symbolic exhaustive omnipath sweep |
| `!fast_path <query>` | O(1) associative intent lookup in hypervector matrix |

### Self-Modification

| Command | Description |
|---------|-------------|
| `!self_reflect` | Deep VSA resonance analysis + cloud architect diagnosis |
| `!self_optimize` | Audit friction → generate optimized patch → stage in Aura_Staging/ |
| `!stage` | Preview the currently staged patch |
| `!stage_merge` | Merge staged patch after safety sentinel + human alignment scoring |
| `!stage_purge` | Reject staged patch, log as negative anti-pattern |
| `!approve <method>` | Graft a function from `aura_incubator.py` into `aura_node.py` |
| `!saturn` | Full NESY curriculum training cycle |
| `!saturn_heal` | Auto-repair logic fractures from NESY state log |
| `architect <intent>` | Generate a Python tool for your intent using cloud LLM + topology |

### LLM Routing

| Command | Description |
|---------|-------------|
| `!calibrate` | Run full (provider × style × mode) benchmark matrix |
| `!route <task> [--model M]` | Auto-route to optimal model; `--model` forces priority |
| `!savings` | Show cumulative token + cost savings per provider |
| `!converse <text>` | Polysynthetic conversation (compress → LLM → interpret) |
| `!contingency_spawn` | Thermal spike handling + cold-cache pressure report |

### Knowledge & Research

| Command | Description |
|---------|-------------|
| `!forage <topic>` | Crawl arXiv for papers on topic |
| `!backtrack` | Chronological arXiv backlog crawl (20 papers) |
| `!research <concept>` | Query ingested papers → synthesize Python helper |
| `!curiosity_tree <seed>` | DFS over GitHub + arXiv from seed concept |
| `!forage_on` | Enable background foraging daemons |
| `!forage_off` | Disable foraging to conserve CPU/RAM |
| `!synthesize` | Run cognitive synthesizer lifecycle pass |
| `!indus_decrypt` | Batch resonance decryption of Indus Valley script corpus |

### Networking

| Command | Description |
|---------|-------------|
| `!ping_mesh` | Broadcast encrypted DSEKP handshake on UDP 4444 |
| `!mesh_status` | Show node identity, active peers, DSEKP entropy index |
| `!export [tree]` | Export data to ~/aura_exports/ |
| `!push <message>` | Zero-trust verify all .py files → git add/commit/push |

### System Management

| Command | Description |
|---------|-------------|
| `!settings` | Print the full manifest (this list) |
| `!benchmark` | CPU temp, RAM, disk, inference throughput |
| `!system_audit` | Layer 5 OS executive audit |
| `!voice` | Start vocal executive loop (requires termux-api) |
| `!db_repair` | Check + auto-rebuild all SQLite databases |
| `!markov [N]` | Markovian workspace reconstruction over N logs (default 256) |
| `!rollback <root>` | Phase-conjugate rollback to Q-SYS root token |
| `STOP` | Immediately cancel any active inference |
| `exit` | Graceful shutdown |

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

WebSocket server on port 8081 that bridges the cognitive engine to the AR visualization deck (index.html).

| Function | Description |
|----------|-------------|
| `bridge_handler(websocket)` | Handle AR client connections; process commands through LiquidKernel |
| `watch_memory()` | Background loop: detect new .st3 engram files → broadcast glyphs |
| `main()` | Bind WebSocket server on 0.0.0.0:8081 |

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

### 8.9 `aura_pricing.py` — Price Book

Class: `PriceBook` — maintains per-model pricing ($/1M tokens) for accurate savings calculation. `get_pricebook()` returns the current snapshot.

### 8.10 `aura_proxy_benchmark.py` — Quality Scoring

Class: `QualityScorer` — validates LLM output quality by diff, token count, and structural compliance.

### 8.11 `aura_token_economics.py` — Token Economics

Class: `TokenEconomics` — `compute_delta(model, raw_in, raw_out, aura_in, aura_out)` — computes cost savings from Aura's compression. `log_call(delta, task, provider)` — records in ledger.

### 8.12 `aura_self_optimize.py` — Autonomous Self-Optimization

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

### 11.1 `aura_topological_scanner.py` — Topology Scanner

| Function | Description |
|----------|-------------|
| `extract_ast_calls(file_content, filename)` | Extract function-level call graphs via AST |
| `scan_regex_signatures(file_content)` | Detect shared SQLite tables, ports, filesystem paths |
| `compile_unified_graph()` | Full scan: spatial_mapper → AST calls → regex signatures → shared-resource edges |
| `compile_topology_map(deep=False)` | Fast or deep scan mode |

### 11.2 `aura_topology_ws_bridge.py` — Topology WebSocket Bridge

Class: `TopologyBroadcastHub` — pure-asyncio bridge between `live_topology_ast.json` and connected WebSocket clients.

| Method | Description |
|--------|-------------|
| `register_client()` | Create per-client bounded asyncio.Queue |
| `unregister_client(q)` | Remove client, drain queue, gc.collect() |
| `start()` | Launch background broadcast + watch tasks |
| `stop()` | Graceful shutdown |
| `broadcast_topology_now()` | Force immediate re-read + broadcast |

Functions: `_chunk_json_fixed_frame(payload)` — split JSON into 4KB frames with sequence metadata. `stream_to_clients(ws_handler_coro, host, port)` — combined WebSocket server entry point.

### 11.3 `aura_topology_manager.py` — Deep Topology Manager

Class: `TopologyBuilder(root)` — `run()` produces enriched topology payload with: proper node IDs (no '?' orphans), deduplication, import-level edges, per-file metrics, hub diagnostics.

### 11.4 `aura_topology_analyzer.py` — Fracture Analysis

Function: `diagnose_fractures()` — returns dict with total fracture count and by-kind breakdown.

### 11.5 `spatial_mapper.py` — Spatial Mapper

| Class/Function | Purpose |
|----------------|---------|
| `CodeTopologyMapper` | AST visitor that maps classes/functions to 3D nodes |
| `DirectoryCache` | Filesystem traversal cache with invalidation |
| `scan_and_vectorize(root_dir)` | Full directory scan returning node topology list |
| `aura_tmm_server(websocket)` | WebSocket server for Topology Map Manager (port 8000) |

### 11.6 `index.html` — 3D/AR Visualizer

Client-side WebGL visualizer that connects to WebSocket on port 8765. Renders the topology graph as interactive 3D nodes (Spheres, Cubes, Tetrahedrons, Icosahedrons) with AR-style color coding.

### 11.7 `liquid_kernel.py` — Liquid Kernel

Class: `LiquidWebSocket` — WebSocket-based liquid state machine with Maxwell-corrected physics and ternary stochastic computation.

### 11.8 `liquid_fhrr.py` — Liquid FHRR

Class: `LiquidFHRR(dim)` — Fractional Holographic Reduced Representation engine.

| Method | Description |
|--------|-------------|
| `generate_phasor()` | Generate complex exponential phasor |
| `bind(v1, v2)` | Circular convolution binding |
| `unbind(v1, v2)` | Circular correlation unbinding |
| `bundle(vectors)` | Element-wise mean superposition |
| `similarity(v1, v2)` | Cosine similarity in complex space |
| `fractional_bind(phasor, t)` | Bind at continuous real-valued time t |

### 11.9 `vsa_resonator.py` — VSA Resonator

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
- AR WebSocket server on port 8765
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

### AR Visualization Workflow

```
# In Termux:
[Dallas] > !topology
  # Generates 3D graph

# Open index.html in Chrome on the same device
  # Auto-connects to ws://127.0.0.1:8765
  # Shows interactive 3D dependency graph

[Dallas] > !topology deep
  # Adds hub diagnostics, fracture detection
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

### General Diagnostics
```
!benchmark                     # CPU temp, RAM, disk, inference throughput
!system_audit                  # Full ecosystem audit
python3 systems_check.py       # Standalone verification
```

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

---

*"You are now an architect of your own future."* — AuraOS System Prime