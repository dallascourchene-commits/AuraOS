# AuraOS

**A sovereign edge cognitive substrate for polysynthetic intent routing, 10,000-D vector memory, self-healing code, mesh coordination, AR topology, and cost-aware LLM orchestration.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Prior Art Stack](https://img.shields.io/badge/Prior_Art-7_papers-black)](#seven-paper-prior-art)
[![Target](https://img.shields.io/badge/Target-Android_Termux_4GB_RAM-green)](#quick-start)

AuraOS is built to run on-device first: Android/Termux, Linux, CPU-only, and a 4GB RAM discipline. It combines finite-state linguistic routing, hyperdimensional memory, self-documenting CODEMAP navigation, zero-trust mutation staging, and provider-agnostic LLM routing into one operator-facing REPL.

## What Aura Can Do

| Area | Capability |
|------|------------|
| Cognitive substrate | Compresses language into polysynthetic slot packets and 10,000-D VSA/FHRR vectors for routing, recall, and reasoning. |
| Code navigation | Maintains `.aura/CODEMAP.md` / `.aura/CODEMAP.json`, Understand Graph dashboards, guided tours, typed Graphify exports, Obsidian review vaults, and spectral topology maps so humans and AI agents can traverse the repo without reading the whole monolith. |
| Reasoning | Runs topology scans, neuro-symbolic omnipath sweeps, meta-resonance checks, coordinated Pass@K reasoning, Markovian workspace reconstruction, and Aura-native meta-harness audits. |
| Self-healing | Uses holographic headers, resonant test oracles, staged patch review, Saturn/NESY repair, database repair, and rollback primitives. |
| LLM orchestration | Calibrates providers, routes tasks by quality/cost, logs token and dollar savings, runs AuraFusion deliberation, shards Architect plans into grounded Act Capsules, applies reversible Headroom-style context crushing with optional Rust/WASI acceleration, strips tokenizer-survival carriers before egress, and injects compact RAEC research context with cached single-seed lift profiles. |
| Research ingestion | Forages arXiv, backtracks chronological CS windows with legacy DB schema migration, parses bounded PDFs, stores paper-memory VSA ledgers with 1.2KB headers, three-point capsules, chunk vectors, and single-seed trace dispatch profiles, then gates synthesis through SkillWeaver. |
| Arena workspaces | Stages refactors and domain plans through Liquid Planning Arena capsules, Boundary Contracts, scoped leases, ICM audit/edit/review workspaces, DREAM-lite usefulness rows, and verifier-ledger handoffs. |
| Empirical software lab | Defines ERA-style scorable Aura tasks for patch repair, repo localization, context compression, hotswap safety, and research retrieval utility; scores local verifier artifacts; records a candidate tree; and recommends promotion only through existing verifier/human gates. |
| Mesh and overlays | Provides encrypted peer discovery, VSA-addressed liquid routing/naming, visible ST3GG/DASH recall pointers, swarm collective learning, sovereignty-first capsule federation, RAM-staked ledger concepts, and local compute-mesh hooks. |
| AR and rendering | Builds live spectral 3D topology maps, exposes WebSocket AR controls, maps structural health to luminance/phase warnings, and implements VSA-addressed decoupled rendering at 80 bytes/object. |
| Human-first coding arena | Serves a local browser-based 3D micro-arena that lets a human select CODEMAP/topology nodes, inspect exact file/symbol/test facts, detect candidate wiring faults, compile deterministic action capsules, and simulate route scorecards before any worker model acts. |

## Recent Upgrade Snapshot

Recent commits expanded Aura from a REPL-centered substrate into a more portable agent-workspace system:

- **Backtrack reliability**: `!backtrack` now verifies and migrates the `traces` schema before ingesting arXiv rows, so older memory palaces missing `vector_blob` can recover in place.
- **Obsidian + Graphify bridge**: `aura_obsidian_graph_bridge.py` exports authoritative Aura sidecars into a human-reviewable Obsidian vault and a typed Graphify JSON graph. Obsidian is explicitly an export surface; source of truth remains in files, sidecars, CODEMAP, QDKT, tests, and verifier reports.
- **Understanding layer**: `aura_understand_graph_bridge.py` builds layered graph packets from CODEMAP, topology, tests, sidecars, verifiers, Arena metadata, QDKT events, DREAM scores, and domain flows, then exports dashboard JSON, guided tours, and diff-impact reports.
- **ICM workspaces**: `aura_icm_workspace.py` and `aura_icm_cli.py` export Arena transactions into numbered audit/edit/review folders with `AURA.md`, `CONTEXT.md`, stage files, boundary contracts, DREAM scores, and QDKT event hooks.
- **Aura-native meta-harness**: `aura_metaharness.py` composes the MCP gateway, plugin registry, GOAP planner, background worker supervisor, audit scorer, and federation layer under one invariant: VSA maps meaning, sidecars store exact truth, Arena stages actions, verifiers prove, humans/governance approve, and QDKT remembers.
- **Human-first 3D Coding Arena**: `aura_coding_arena_3d.py`, `aura_coding_arena_server.py`, and `aura_coding_arena/` add a dependency-free local Canvas control deck for topology selection, capsule compilation, fault detection, route simulation, LAN/phone demo mode, and Docker packaging.

## Metrics and Benchmarks

These are repo-local measurements, demos, or complexity bounds documented in code, tests, and implementation notes. Re-run on target hardware with `!benchmark` and the listed tests for current numbers.

### Local Diagnostics Snapshot

Measured on this checkout on 2026-06-30 with Aura's own `char/4` token estimator. These runs are deterministic/offline unless noted; the mock matrix benchmark measures packaging, validation, and token shape, not real provider latency.

Commands and harness used:

```bash
python3 aura_matrix_benchmark.py --mock --providers mock --styles bracket,json,hybrid --output-modes unified_diff,json_edit_plan --trials 1 --task mesh_offload
```

The substrate, HV cache, context-crush, and Understand Graph rows were measured by an in-process diagnostic harness using `AuraSubstrate`, `HVCacheSubstrate`, `AuraContextCrusher`, and `build_graph_packet(".")` to avoid mutating tracked graph export artifacts during the README refresh.

| Diagnostic | Raw / baseline | Aura method | Estimated token reduction | Input shrink | Local latency |
|------------|----------------|-------------|---------------------------|--------------|---------------|
| Human-first 3D Coding Arena, real CODEMAP load | Existing `.aura/CODEMAP.json` | Browser/API topology packet built from local CODEMAP | N/A; this is topology loading, not compression | 600 nodes, 1,225 links | 334.382 ms load |
| Human-first 3D Coding Arena, demo capsule | 50,000-token raw demo baseline | Deterministic action capsule with exact selected node facts, constraints, faults, and route scorecard | 97.6% using the complete emitted capsule; 99.3% for the compact context nucleus | 5-node/4-link demo graph to 1,163-token worker capsule | 2.529 ms compile; 0.039 ms route scorecard |
| Human-first 3D Coding Arena, browser/mobile smoke | Local demo server and dependency-free Canvas UI | Desktop screenshot rendered 1,278 sampled colors; mobile 390x844 viewport stacked canvas/panel with no horizontal overflow | N/A | Selected node facts visible on desktop and mobile | API/UI smoke passed; route simulation kept `network_calls_made=false` |
| Human-first 3D Coding Arena, tests | New arena tests plus existing `tests/` package | Capsule, fault detector, route, no-secret, fallback, frontend fixture, related topology tests, and current PR #44 grounding/auditor regressions | N/A | 61 tests in `tests/` | 61 passed in 1.98 s |
| Substrate surgical context for the `!backtrack` fix | `arxiv_forager.py` + `test_scientific_memory.py`: 3,208 lines, ~30,492 tokens | Targeted `upgraded_arxiv_backtracker` context: 341 lines, ~4,383 tokens; full guardrailed egress prompt: ~6,097 tokens | 85.6% for code context; 80.0% including guardrails | 7.0x context shrink; 5.0x full prompt shrink | median 28.862 ms compile, min 18.239 ms |
| HV cache projection for the same two files | ~30,492 raw context tokens | 10,000-D local vector plus 52-token manifest summary | 99.8% | 586.4x | 339.250 ms project-context run |
| Context crush, code sketch | `aura_liquid_planning_arena.py`: ~6,075 tokens | AST symbol/import sketch: ~235 tokens | 96.1% | 25.9x | median 102.265 ms |
| Context crush, diff sketch | Backtrack-fix diff: ~1,780 tokens | Diff skeleton: ~820 tokens | 53.9% | 2.2x | median 19.679 ms |
| Context crush, JSON matrix | Synthetic graph-like JSON: ~2,441 tokens | ST3GG/JSON matrix capsule: ~167 tokens | 93.2% | 14.6x | median 27.604 ms |
| Context crush, log trace | Synthetic 143-line log/traceback: ~1,542 tokens | Error-focused log capsule: ~130 tokens | 91.6% | 11.9x | median 17.524 ms |
| Understand Graph build | Repo sidecars, CODEMAP, tests, topology, Arena/QDKT/DREAM metadata | 2,077 nodes, 3,821 edges, 4 guided tours | Not a token compressor by itself; it creates reusable navigation state for later low-context tasks | N/A | median 87.182 ms build |
| Mock model/protocol matrix | Raw mesh-offload benchmark prompt | Aura substrate packets across bracket/json/hybrid and unified diff/json edit-plan modes | Avg input reduction 83.2%; guardrail-amortized 93.8%; avg output reduction 53.1%; context-leak reduction 96.0% | 6.0x raw input shrink; 16.1x amortized shrink; 2.1x output shrink | mock cells reported 0.001 s Aura latency |

Interpretation: for tiny one-file bug fixes, direct `rg` + patch may still be the fastest human/operator workflow. For multi-file or repeated agent work, Aura's substrate, Arena, HV cache, and context-crush layers replace full-file prompt dumps with scoped capsules, manifests, vectors, and verifier-friendly sketches. That is where cheaper models and external agents get the largest practical gain.

| Subsystem | Result |
|-----------|--------|
| Intent parsing | 6-slot intent parsing target: `<0.05 ms`; 10,000-D RAM recall target: `<0.01 ms`. |
| Device diagnostics | `!benchmark` reports CPU temperature, RAM, disk, Python/NumPy, LLM server, AR clients, memory-palace status, and 10K-dot latency. |
| Holographic integrity | 1.2KB global/codebase fingerprint; O(1) verification by cosine resonance; threshold `R < 0.95` triggers healing. |
| RAEC paper memory | arXiv PDFs are chunked before VSA encoding, then lifted through a cached single-seed context profile, 10,000-D complex document vector, 1.2KB holographic header, and three-point capsule. Egress scans the local JSONL ledger and injects only the top 2 bracket slots. |
| Single-seed context lift | Adapts the cache-once/dispatch pattern from arXiv:2606.20633. The source paper reports `O(m^2)` per precision layer and a `33.5x` high-precision lift speedup; Aura applies the transferable pattern to VSA context as `O(C*D + e*D)` local vector work. |
| Context crushing | Adapts the deterministic, local-first parts of Headroom: content routing, JSON/log/search/code compression, CCR retrieval markers, detector-only cache-prefix metrics, and a no-daemon Rust/WASI accelerator bridge. Headroom reports real workload savings from `47%` to `92%`; Aura stores originals locally and logs actual savings per egress call. |
| Architect Fusion Loop | `aura_architect_loop.py` builds Fractal Plan Capsules, CODEMAP-grounded Act Capsules, Shadow reports, intensity routing, phase continuity capsules, Refactor Arena transactions, verifier-gated hot-swap capsules, rollback digests, and append-only Architect ledger rows before patch promotion. `aura_live_architect.py` wires live `architect <intent>` work through a local/free candidate first, multiple premium planner candidates, cheap Shadow critics, premium Judge selection, bounded Act workers, temp-workspace patch application, AST plus world-state topology delta capture, and ledgered hot-swap staging instead of direct incubator writes. `aura_liquid_planning_arena.py` generalizes the Refactor Arena into a Liquid Planning Arena with domain-neutral Action Capsules, first-class Boundary Contracts, scoped agent leases, a shared action queue, and code/civic/travel adapters. |
| Empirical software lab | `aura_empirical_software_lab.py` turns Aura subsystems into scorable tasks. It uses CODEMAP, MODULE_MANIFEST, repair KG, harness metrics, and verifier artifacts to score bounded candidate improvements, select next candidates with a compact UCB rule, and append results to `Aura_Staging/empirical_candidate_tree.jsonl`. It never promotes or writes production code. |
| ICM workspace export | Arena transactions can be exported into numbered ICM workspaces with `AURA.md`, `CONTEXT.md`, stage-specific Markdown, `boundary_contracts.jsonl`, `transaction.json`, QDKT export events, human-edit events, DREAM-lite rows, and round-trip import support. |
| Understand Graph | Builds layered repo graph packets from CODEMAP, topology, tests, sidecars, verifiers, Arena metadata, QDKT events, DREAM scores, and domain flows. Exports `.aura/understand_graph.json`, `.aura/understand_graph_tour.json`, and `.aura/understand_graph_diff.json` for dashboards, guided tours, and changed-file risk analysis. |
| Obsidian + Graphify | Exports Aura truth into `Aura_Vault/` Markdown notes with YAML frontmatter/Wikilinks plus `.aura/graphify_graph.json` using typed node/edge schemas. Incremental sync state is tracked in `.aura/obsidian_graph_sync_state.json`, and validation issues are written before broken graph output is accepted. |
| Meta-harness | `aura_metaharness.py` wires six subsystems: MCP gateway, plugin registry, GOAP planner, background workers, audit scorer, and federation. It supports snapshots, invariant checks, dry audits, plugin install observations, worker outcomes, and signed/redacted capsule federation with QDKT memory hooks. |
| Travel sidecar arena | `travel_scraper_core.py` ingests local Option B scraper JSON/JSONL, preserves immutable raw snapshots, normalizes TripAdvisor/Expedia-style records, writes exact price/date/currency truth to `travel_price_sidecar.py`, writes semantic metadata JSONL for VSA, and builds `travel_vsa_pointer_index.py` pointers that never store exact prices. `travel_package_arena.py` resolves VSA pointers back to exact sidecar rows and `travel_price_verifier.py` blocks stale, missing, unverified, or vector-only prices before package display. |
| arXiv backtracker resilience | The chronological arXiv crawler uses bounded one-day windows, paced requests, OAI-PMH fallback, configurable PDF fetch limits through `AURA_BACKTRACK_PDF_LIMIT`, and now repairs legacy `traces` schemas before writing `Scientific VSA v1` rows. |
| Defensive ST3GG recall | Adapts GLOSSOPETRAE's seeded-symbol insight without covert carriers: compressed originals get visible `ST3GG-L2` pointers, DASH keys, holographic headers, a persistent hash sidecar, and a JSON compatibility sidecar for bounded O(1)-style keyed recall by hash, pointer, or DASH key. |
| ST3GG compaction analytics | Reports active hash load, bits/key, sidecar byte footprint, and a frozen-segment recommendation. `aura_st3gg_compact.rs` provides the zero-dependency Stage 2 Rust pilot compiler for immutable key segments. |
| Tokenizer-boundary guard | Applies NFKC normalization and strips tag chars, private-use chars, variation selectors, bidi controls, and non-allowlisted format controls before network egress. The guard is active even when context crushing is disabled. |
| VSA rendering | 80 bytes/object; 100 objects demo: `7.8 KB` vs `5600 KB`, `99.9%` bandwidth reduction, `716.8x` transfer reduction. |
| Fractal ledger | `test_fractal_ledger.py`: 9 tests passed in `0.45s` in the implementation report. |
| W4A4 quantization | N16 tests require `>3.5x` compression and `>70%` memory reduction for float32 -> int8 activation paths. |
| Thermal-cost routing | N27 TCWAA routing is O(`|P| * D`) for up to 8 providers with documented typical decision latency `<10 ms`. |
| FST routing | N18/N21 reduce routing complexity from ad-hoc O(N^2) graphs toward O(E)/O(L), with paper examples from `>1300` edges to about `200`. |
| Spectral topology | `!topology` and `!topology deep` augment dependency graphs with Laplacian eigenmap coordinates, spectral sparsity, global health, cycle warning nodes, and AR luminance fields. |
| LLM savings | Aura logs actual provider/model/token/cost rows; documented compression target is `60-90%` token reduction when compact packets replace raw prompts. |
| Liquid routing | N14 uses 10,000-D addresses and resonance next-hop selection without DNS/BGP tables; 1.2KB quantized address transport form. |

## Seven-Paper Prior Art

AuraOS now carries the fulfilled seven-paper prior-art stack in the repository and maps those claims into source modules, tests, and development tracks. The papers are published as defensive prior art under AGPLv3 Section 13.

| Paper | Claims | Record |
|-------|--------|--------|
| Protocol-layer innovations | N24-N30: HIVP, micro-module crystallization, resonant tests, thermal-cost API arbitration, deterministic compression, local VSA compute mesh, bounded self-healing | [Zenodo 20695562](https://zenodo.org/records/20695562) |
| Enhanced FST and topology | N21-N23: FST lexicon, resonance topology, FST impact analysis | [Zenodo 20682051](https://zenodo.org/records/20682051) |
| FST routing and self-refactoring | N18-N20: routing core, 3D topology resonance, self-refactoring incubator | [Zenodo 20681601](https://zenodo.org/records/20681601) |
| Memristive/rendering upgrades | N15-N17: memristive hyper-epochs, timestep-aware SVD quantization, Gaussian/VSA rendering dynamics | [Zenodo 20673206](https://zenodo.org/records/20673206) |
| Liquid Internet | N14: VSA-addressed routing and naming without IP/DNS dependency at the cognitive layer | [Zenodo 20659314](https://zenodo.org/records/20659314) |
| Holographic swarm systems | N9-N13: headers, gas-free fractal ledger, swarm learning, VSA rendering, FST narrative | [Zenodo 20657391](https://zenodo.org/records/20657391) |
| Foundation | N1-N8: polysynthetic LLM egress, dual linguistic cortex, sparse sweeps, QDKT, topology, hot-swap, 4GB edge design | [Zenodo 20635424](https://zenodo.org/records/20635424) |

## Quick Start

```bash
# Android Termux
pkg install python git cmake

# Linux
# sudo apt-get install python3 python3-pip git cmake

git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
bash setup.sh
pip install -r requirements.txt
python3 aura_node.py
```

Optional native context-crush acceleration:

```bash
rustc -O aura_crush_core.rs -o Aura_Memory/aura_crush_core
export AURA_CRUSH_ACCELERATOR_PATH=Aura_Memory/aura_crush_core

# Or build a WASI module when wasm32-wasip1 + wasmtime CLI are available:
rustc --target wasm32-wasip1 -O aura_crush_core.rs -o Aura_Memory/aura_crush_core.wasm
export AURA_CRUSH_ACCELERATOR_PATH=Aura_Memory/aura_crush_core.wasm
```

At the prompt:

```text
[Dallas] > !settings
[Dallas] > !topology
[Dallas] > !benchmark
[Dallas] > !calibrate
[Dallas] > !backtrack
[Dallas] > !research resonance egress
[Dallas] > !route summarize-this-task
```

Optional API keys live in `aura_secrets.json`; see `aura_secrets.example.json`. Aura's deterministic substrate, topology, local memory, and many diagnostics run without external providers.

Useful bridge and workspace utilities:

```bash
# Build the layered Understand Graph dashboard and guided tours
python3 aura_understand_graph_bridge.py --build --export --tours

# Export a typed Graphify JSON graph, or a full Obsidian review vault
python3 aura_obsidian_graph_bridge.py --graph-only --full
python3 aura_obsidian_graph_bridge.py --full

# Inspect the Aura-native meta-harness
python3 aura_metaharness.py --snapshot
python3 aura_metaharness.py --check-invariants

# Work with ICM audit/edit/review workspaces
python3 aura_icm_cli.py list Aura_Memory/icm_workspaces
python3 aura_icm_cli.py export Aura_Staging/architect_live_transaction.json Aura_Memory/icm_workspaces --qdkt

# Run the Human-First 3D Coding Arena locally
python3 aura_coding_arena_server.py --host 127.0.0.1 --port 8080
python3 aura_coding_arena_server.py --host 127.0.0.1 --port 8080 --demo
```

## Operator Docs

- [USER_GUIDE.md](USER_GUIDE.md): command-by-command operation guide, module reference, workflow patterns, troubleshooting, and WebSocket/AR protocol details.
- [.aura/CODEMAP.md](.aura/CODEMAP.md): compact map of commands, symbols, high-value modules, navigation rings, and file ownership.
- [AURA_CODING_ARENA_README.md](AURA_CODING_ARENA_README.md): local 3D Coding Arena runbook, API behavior, route simulation notes, benchmarks, and LAN/phone demo guidance.
- [ICM_WORKSPACE_README.md](ICM_WORKSPACE_README.md): ICM workspace folder contract for Arena audit/edit/review handoffs.
- [AURA_FINAL_REPORT.md](AURA_FINAL_REPORT.md): current system report and AuraFusion/native routing addendum.

## Development Potential

AuraOS is a substrate, not a single app. Current high-value directions include:

- mobile sovereign AI nodes that run useful cognition on low-cost hardware;
- interactive films/games where FST constraints keep stories coherent while dialogue changes per viewer;
- AR/VR worlds that send VSA addresses and poses instead of heavy scene assets;
- local compute swarms that route work by resonance, thermal load, and trust;
- interoperable agent workspaces where cheaper or specialized models operate inside Arena capsules instead of reading the whole repository;
- resonant test suites and self-healing codebases with measurable partial failure instead of binary pass/fail;
- thermal/cost-aware LLM routing that treats money, latency, and device health as first-class constraints.

## License

AuraOS is released under the GNU Affero General Public License v3.0. If you run a modified AuraOS as a network service, AGPLv3 Section 13 requires you to publish the corresponding source.

Contact: aura.os.q@gmail.com
