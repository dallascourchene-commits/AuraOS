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
| Code navigation | Maintains `.aura/CODEMAP.md` / `.aura/CODEMAP.json` and spectral topology maps so humans and AI agents can traverse the repo without reading the whole monolith. |
| Reasoning | Runs topology scans, neuro-symbolic omnipath sweeps, meta-resonance checks, coordinated Pass@K reasoning, and Markovian workspace reconstruction. |
| Self-healing | Uses holographic headers, resonant test oracles, staged patch review, Saturn/NESY repair, database repair, and rollback primitives. |
| LLM orchestration | Calibrates providers, routes tasks by quality/cost, logs token and dollar savings, runs AuraFusion deliberation, applies reversible Headroom-style context crushing, and injects compact RAEC research context with cached single-seed lift profiles before egress. |
| Research ingestion | Forages arXiv, parses PDFs, stores paper-memory VSA ledgers with 1.2KB headers, three-point capsules, chunk vectors, and single-seed trace dispatch profiles, then gates synthesis through SkillWeaver. |
| Mesh and overlays | Provides encrypted peer discovery, VSA-addressed liquid routing/naming, swarm collective learning, RAM-staked ledger concepts, and local compute-mesh hooks. |
| AR and rendering | Builds live spectral 3D topology maps, exposes WebSocket AR controls, maps structural health to luminance/phase warnings, and implements VSA-addressed decoupled rendering at 80 bytes/object. |

## Metrics and Benchmarks

These are repo-local measurements, demos, or complexity bounds documented in code, tests, and implementation notes. Re-run on target hardware with `!benchmark` and the listed tests for current numbers.

| Subsystem | Result |
|-----------|--------|
| Intent parsing | 6-slot intent parsing target: `<0.05 ms`; 10,000-D RAM recall target: `<0.01 ms`. |
| Device diagnostics | `!benchmark` reports CPU temperature, RAM, disk, Python/NumPy, LLM server, AR clients, memory-palace status, and 10K-dot latency. |
| Holographic integrity | 1.2KB global/codebase fingerprint; O(1) verification by cosine resonance; threshold `R < 0.95` triggers healing. |
| RAEC paper memory | arXiv PDFs are chunked before VSA encoding, then lifted through a cached single-seed context profile, 10,000-D complex document vector, 1.2KB holographic header, and three-point capsule. Egress scans the local JSONL ledger and injects only the top 2 bracket slots. |
| Single-seed context lift | Adapts the cache-once/dispatch pattern from arXiv:2606.20633. The source paper reports `O(m^2)` per precision layer and a `33.5x` high-precision lift speedup; Aura applies the transferable pattern to VSA context as `O(C*D + e*D)` local vector work. |
| Context crushing | Adapts the deterministic, local-first parts of Headroom: content routing, JSON/log/search/code compression, CCR retrieval markers, and detector-only cache-prefix metrics. Headroom reports real workload savings from `47%` to `92%`; Aura stores originals locally and logs actual savings per egress call. |
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

## Operator Docs

- [USER_GUIDE.md](USER_GUIDE.md): command-by-command operation guide, module reference, workflow patterns, troubleshooting, and WebSocket/AR protocol details.
- [.aura/CODEMAP.md](.aura/CODEMAP.md): compact map of commands, symbols, high-value modules, navigation rings, and file ownership.
- [AURA_FINAL_REPORT.md](AURA_FINAL_REPORT.md): current system report and AuraFusion/native routing addendum.

## Development Potential

AuraOS is a substrate, not a single app. Current high-value directions include:

- mobile sovereign AI nodes that run useful cognition on low-cost hardware;
- interactive films/games where FST constraints keep stories coherent while dialogue changes per viewer;
- AR/VR worlds that send VSA addresses and poses instead of heavy scene assets;
- local compute swarms that route work by resonance, thermal load, and trust;
- resonant test suites and self-healing codebases with measurable partial failure instead of binary pass/fail;
- thermal/cost-aware LLM routing that treats money, latency, and device health as first-class constraints.

## License

AuraOS is released under the GNU Affero General Public License v3.0. If you run a modified AuraOS as a network service, AGPLv3 Section 13 requires you to publish the corresponding source.

Contact: aura.os.q@gmail.com
