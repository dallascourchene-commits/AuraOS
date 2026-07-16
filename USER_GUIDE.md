# AuraOS User Guide

> **Operator guide for the Arena-based AuraOS architecture**

**Operator documentation audit:** June 14–July 16, 2026 (through draft PR #131)
**Validated CODEMAP:** regenerate from the current tree with `python aura_codebase_navigator.py`; require non-zero indexes and `compiled_deep_topology`

AuraOS is local-first and can run many deterministic functions without a hosted model. External models are optional workers operating through controlled egress and Arena boundaries.

---

## Contents

1. [How to Use This Guide](#1-how-to-use-this-guide)
2. [Installation](#2-installation)
3. [First-Run Validation](#3-first-run-validation)
4. [Choose an Interface](#4-choose-an-interface)
4A. [Refactor Code-Quality Benchmarking](#4a-refactor-code-quality-benchmarking)
5. [Repository Orientation](#5-repository-orientation)
6. [Native Cockpit](#6-native-cockpit)
7. [Agent Arena CLI](#7-agent-arena-cli)
8. [Coding Workbench](#8-coding-workbench)
9. [Coding Arena](#9-coding-arena)
10. [Human Agent Arena](#10-human-agent-arena)
11. [Ephemeral Organ Runtime](#11-ephemeral-organ-runtime)
12. [Civic Commons Arena](#12-civic-commons-arena)
13. [Anishinaabemowin Tutor](#13-anishinaabemowin-tutor)
13A. [Model Cognome and Adaptive Routing](#13a-model-cognome-and-adaptive-routing)
14. [Legacy REPL](#14-legacy-repl)
15. [Cost and Efficiency](#15-cost-and-efficiency)
16. [Common Workflows](#16-common-workflows)
17. [Safety and Data Governance](#17-safety-and-data-governance)
18. [Testing](#18-testing)
19. [Troubleshooting](#19-troubleshooting)
20. [Documentation Maintenance](#20-documentation-maintenance)

---

## 1. How to Use This Guide

Aura has several interfaces because different actors need different levels of control.

### Recommended default

For new code work:

```text
topology health
→ repository digest
→ capability resolution
→ CODEMAP search
→ exact source slices
→ prepared Arena task
→ external worker if needed
→ staged patch
→ tests and verifiers
→ human review
```

### Do not start by

- loading all of `aura_node.py`;
- opening all of `.aura/CODEMAP.json`;
- asking a model to grep the repository blindly;
- treating a visual graph as exact truth;
- allowing an external worker to write production files directly;
- creating a new module before checking existing capabilities.

---

## 2. Installation

### 2.1 Requirements

Core:

- Python 3;
- Git;
- Linux, Windows, macOS, or Android/Termux;
- sufficient storage for the repository and generated maps.

Optional:

- Rust for native context-crush helpers;
- Wasmtime/WASI for properly restricted arbitrary ephemeral components;
- Docker for containerized demonstrations;
- provider API keys for optional external workers.

Aura remains CPU-first. A GPU is not required for deterministic routing, CODEMAP, topology, local Arenas, or many diagnostics.

### 2.2 Clone and install

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS

bash setup.sh
python3 -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
git clone https://github.com/dallascourchene-commits/AuraOS.git
Set-Location AuraOS

python -m pip install -r requirements.txt
```

### 2.3 Optional Rust context-crush accelerator

```bash
rustc -O aura_crush_core.rs -o Aura_Memory/aura_crush_core
export AURA_CRUSH_ACCELERATOR_PATH=Aura_Memory/aura_crush_core
```

WASI build:

```bash
rustc --target wasm32-wasip1 -O aura_crush_core.rs \
  -o Aura_Memory/aura_crush_core.wasm

export AURA_CRUSH_ACCELERATOR_PATH=Aura_Memory/aura_crush_core.wasm
```

### 2.4 Secrets

Use environment variables or ignored local configuration.

Examples:

```bash
export FIREWORKS_API_KEY="..."
export AURA_HOSTED_MODEL_API_KEY="..."
export AURA_HOSTED_MODEL_API_BASE="..."
export AURA_HOSTED_MODEL="..."
```

Never commit:

- API keys;
- learner data;
- community-only language data;
- private memory;
- raw provider prompts containing secrets;
- local databases containing personal information.

---

## 3. First-Run Validation

### 3.1 Build the architecture map

```bash
python3 aura_codebase_navigator.py
```

Expected properties:

- non-zero file count;
- non-zero topology nodes;
- non-zero topology edges;
- non-empty symbol index;
- non-empty command index;
- topology source such as `compiled_deep_topology`.

### 3.2 Check topology health

```bash
python3 -m aura_agent_arena_cli topology-health
```

### 3.3 Check system stabilization

```bash
python3 -m aura_agent_arena_cli stabilization-status
```

### 3.4 Get a compact repository digest

```bash
python3 -m aura_agent_arena_cli digest
```

A healthy current checkout should be comparable to:

```text
files: 602
topology_nodes: 5,881
topology_edges: 12,168
topology_source: compiled_deep_topology
```

Counts naturally change as files and symbols change. The important condition is that graph and indexes remain healthy.

---

## 4. Choose an Interface

| Interface | Best use | Launch |
|---|---|---|
| Native Cockpit | Human-first intent ingestion, capability paths, route grounding, and handoff preparation | `python3 -m aura_native_cockpit_server` |
| Agent Arena CLI | Full machine/human coding workflow, staging, verification, cost, ephemeral, and Civic commands | `python3 -m aura_agent_arena_cli` |
| Coding Arena | Local visual topology selection and capsule simulation | `python3 aura_coding_arena_server.py` |
| Human Agent Arena | Human/Aura/agent concept workspaces, Node Inspector, hypotheses, Civic UI | `python3 aura_human_agent_arena_server.py --repo-root .` |
| Agent Arena MCP | MCP-compatible tool surface for external agents | `python3 -m aura_agent_arena_mcp` |
| Model Cognome router | Governed legacy, no-call shadow planning, or explicitly authorized paired-live comparison | `python aura_router.py route --help` |
| Legacy REPL | Existing `!commands`, research, mesh, reasoning, and compatibility workflows | `python3 aura_node.py` |
| Python APIs | Tutor and domain-specific integration | import the relevant module |

---

<!-- AURA_REFACTOR_CODE_QUALITY:START -->
## 4A. Refactor Code-Quality Benchmarking

Use this workflow when comparing engineering quality from broad context, Aura slices, Council-guided execution, or another refactoring method.

### Interpret the result

Aura records **working behavior** separately from **acceptance**:

| Disposition | Meaning |
|---|---|
| `ACCEPTED` | Every required gate passed |
| `WORKED_BUT_NOT_ACCEPTABLE` | Functional behavior passed, but scope, API, security, regression, or another required gate failed |
| `PARTIAL` | Some measured functional behavior passed and some failed |
| `FAILED` | Patch application, compilation, or measured functionality failed completely |
| `CODE_QUALITY_UNAVAILABLE` | The arm produced only a plan or synthetic control-flow result |

Do not discard a rejected patch's passing evidence. Inspect `failed_required_gates`, exact test counts, and per-gate evidence.

### Run focused tests

```bash
python -m pytest -q \
  tests/test_aura_refactor_output_quality.py \
  tests/test_aura_architect_council_v3.py
```

### Reproduce the executable comparison

```bash
python aura_codebase_navigator.py

python aura_architect_consolidation_benchmark_v2.py prepare \
  --repo-root . \
  --output-dir benchmark-output

python benchmarks/architect_consolidation/generate_gpt56_pilot_fixture.py \
  --output benchmark-output/responses.gpt-5.6-thinking.json

python aura_architect_consolidation_benchmark_v2.py score \
  --repo-root . \
  --output-dir benchmark-output \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --input-rate 1.0 \
  --output-rate 3.0

python aura_architect_council_calling_benchmark.py \
  --repo-root . \
  --responses benchmark-output/responses.gpt-5.6-thinking.json \
  --output-dir benchmark-output/council-calling

python benchmarks/refactor_code_quality/generate_fixture.py \
  --output-dir benchmark-output/executable-fixture \
  --planning-report benchmark-output/architect_consolidation_benchmark.json \
  --calling-ablation benchmark-output/council-calling/council_calling_ablation.json

python aura_executable_refactor_benchmark.py \
  --fixture-dir benchmark-output/executable-fixture \
  --output-dir benchmark-output/executable-quality
```

### Read the records

```text
benchmark-output/executable-quality/executable_refactor_benchmark.json
benchmark-output/executable-quality/*.refactor-output.json
benchmark-output/executable-quality/refactor_output_records.jsonl
```

Persistent summaries default to:

```text
Aura_Memory/benchmarks/refactor_output_records.jsonl
```

Each record stores estimated and provider-reported input/output tokens separately. Provider fields remain null when the provider did not report them.

### Required engineering evidence

A serious executable comparison should include:

1. clean patch application;
2. compilation or repository-native build;
3. visible tests;
4. hidden tests unavailable to the coding method;
5. regression tests;
6. public API compatibility unless change is authorized;
7. authorized-file scope and blast radius;
8. security checks;
9. maintainability and repository-native static analysis;
10. performance, portability, coverage, mutation, type, and dependency checks when relevant.

### Selective Council V3

Council V3 always reviews scope and tests. It adds sequence, continuity, rollback, and cost critics only when plan length, dependency edges, large tasks, risk, or rollback evidence justify them.

The first controlled result retained Council V2's accepted patch and 100.00 observed code-quality score while reducing Council calls from 18 to 12 and total token proxy from 158,545 to 106,494.

See:

- `docs/AURA_EXECUTABLE_REFACTOR_BENCHMARK.md`
- `docs/AURA_REFACTOR_CODE_QUALITY_STANDARD.md`
- `schemas/aura_refactor_output_record.schema.json`
<!-- AURA_REFACTOR_CODE_QUALITY:END -->

## 5. Repository Orientation

### 5.1 Required reading order

1. `README.md`
2. `.aura/ARCHITECTURE.md`
3. `.aura/CODEMAP.md`
4. relevant current subsystem guide under `docs/`
5. exact source slices returned by Aura tools

### 5.2 Source-of-truth order

When sources conflict:

1. exact source and schemas;
2. tests and verifier artifacts;
3. healthy current CODEMAP/topology;
4. exact source snapshots, sidecars, and ledgers;
5. manifests and boundary contracts;
6. current subsystem documentation;
7. README/architecture summaries;
8. old reports, digests, and extracted text.

### 5.3 Query CODEMAP

```bash
python3 aura_codebase_navigator.py --query "civic ephemeral runtime"
```

Through the Agent Arena:

```bash
python3 -m aura_agent_arena_cli search \
  --query "run_civic_organ" \
  --kind symbol
```

Search kinds:

- `symbol`
- `file`
- `text`
- `command`

### 5.4 Read an exact source slice

```bash
python3 -m aura_agent_arena_cli read-slice \
  --file aura_civic_runtime.py \
  --symbol run_civic_organ
```

Line-bounded alternative:

```bash
python3 -m aura_agent_arena_cli read-slice \
  --file aura_fst_routing.py \
  --line-start 390 \
  --line-end 470 \
  --max-lines 120
```

### 5.5 Resolve existing capabilities

```bash
python3 -m aura_agent_arena_cli resolve-capabilities \
  --objective "Add a governed local marketplace matching Arena"
```

Optional exact targets:

```bash
python3 -m aura_agent_arena_cli resolve-capabilities \
  --objective "Extend civic resource matching" \
  --target-files aura_civic_resources.py,aura_civic_organs.py \
  --target-symbols match_resources
```

---

## 6. Native Cockpit

The Native Cockpit is Aura's human-first intent and orientation interface. It is read-only and prepares work for the Agent Arena.

### 6.1 Show commands

```bash
python3 -m aura_native_cockpit_server --help
```

### 6.2 Ingest an intent document

Create a file under `.aura/intents/`, for example:

```markdown
# Objective
Improve Civic resource matching without changing consent behavior.

## Constraints
- Reuse current capability lanes.
- No production mutation.
- Preserve exact-source patch authority.
- Run focused Civic tests.

## Acceptance criteria
- Existing matches remain deterministic.
- New ranking is explained.
- Cost telemetry remains available.
```

Ingest:

```bash
python3 -m aura_native_cockpit_server \
  ingest-intent \
  --file .aura/intents/civic_resource_matching.aura.md \
  --json
```

### 6.3 Native Cockpit commands

| Command | Purpose |
|---|---|
| `ingest-intent --file <path>` | Parse an intent document into a structured packet |
| `contract --objective "<text>"` | Generate a Native Cockpit operating contract |
| `validate-lexc --file <path>` | Validate the six-slot semantic route |
| `connectome` | Build the capability connectome |
| `capability-path --objective "<text>"` | Find a likely capability path |
| `explain-capability --id <id>` | Explain one capability |
| `token-economy --objective "<text>" --files a.py,b.py` | Estimate or measure context-saving sources |
| `gates` | Display workflow checkpoint states |
| `evaluate-gate --state <state> --evidence '<json>'` | Evaluate one workflow gate |
| `ground --objective "<text>" [--target-symbol <symbol>]` | Ground an intent in repository facts |
| `handoff --intent-file <path> --agent hermes` | Prepare an external-agent handoff |
| `diagnose --node-id <file::symbol>` | Diagnose a topology node |
| `emergent-audit --objective "<text>"` | Run a report-only emergent capability audit |

---

## 7. Agent Arena CLI

The Agent Arena CLI is the broadest operational surface.

Show help:

```bash
python3 -m aura_agent_arena_cli --help
```

### 7.1 Core Agent Arena commands

| Command | Purpose |
|---|---|
| `digest` | Return a compact repository orientation packet |
| `prepare` | Prepare a grounded coding task and Act Capsules |
| `search` | Search CODEMAP by symbol, file, text, or command |
| `context` | Return bounded capsule/ST3GG context for one task |
| `read-slice` | Read an authorized source slice |
| `fireworks-patch` | Request a candidate diff from a configured Fireworks worker |
| `stage-patch` | Stage a candidate patch through Arena boundaries |
| `verify` | Run focused, declared, or all tests/verifiers |
| `repair-packet` | Return minimal context for a failed patch |
| `status` | Show hotswap/promotion readiness |
| `export-icm` | Export the transaction to an ICM review workspace |
| `find-affordances` | Find internal Aura tools for an objective |

### 7.2 Prepare a task

```bash
python3 -m aura_agent_arena_cli prepare \
  --objective "Improve the Civic scenario verifier" \
  --target-file aura_civic_scenarios.py \
  --acceptance-criteria "preserve schema,pass focused tests,no direct production mutation" \
  --constraints "reuse existing verifier,keep fixture mode deterministic"
```

### 7.3 Get worker context

```bash
python3 -m aura_agent_arena_cli context \
  --task-id A1 \
  --format both \
  --depth 1 \
  --max-tokens 2000
```

Formats:

- `capsule`
- `st3gg`
- `both`

### 7.4 Stage a patch

```bash
python3 -m aura_agent_arena_cli stage-patch \
  --task-id A1 \
  --diff-file /tmp/aura_patch.diff \
  --affected-files aura_civic_scenarios.py \
  --tests tests/test_aura_civic_commons_arena.py \
  --owner hermes
```

### 7.5 Verify

```bash
python3 -m aura_agent_arena_cli verify --scope declared
```

Scopes:

- `focused`
- `declared`
- `all`

### 7.6 Repair after failure

```bash
python3 -m aura_agent_arena_cli repair-packet \
  --task-id A1 \
  --max-tokens 1500
```

Do not silently broaden scope after repeated failure. Escalate to human review.

---

## 8. Coding Workbench

The Coding Workbench turns the Native Cockpit into a checkpointed software-engineering workflow.

```text
OPEN_WORKSPACE
→ SCOPE_TASK
→ FILTER_CONTEXT
→ LOCALIZE_CODE
→ RANK_CODE_REGIONS
→ SLICE_CONTEXT
→ BUILD_CHANGE_GRAPH
→ DETECT_REFACTOR_CANDIDATES
→ SPLIT_WORK
→ CREATE_ACT_CAPSULES
→ PREPARE_AGENT_HANDOFF
→ STAGE_PATCH
→ RUN_TESTS
→ VERIFY_PATCH
→ HUMAN_REVIEW
→ PR_READY
```

Exceptional states:

- `NEED_TOPOLOGY_REPAIR`
- `BLOCKED_SECURITY_RISK`

### 8.1 Workbench commands

| Command | Purpose |
|---|---|
| `topology-health` | Validate CODEMAP graph health |
| `open-workspace` | Open a new coding workspace |
| `scope-task` | Define a bounded objective |
| `filter-context` | Remove irrelevant context |
| `localize-code` | Find exact CODEMAP regions |
| `rank-code-regions` | Rank regions within a line budget |
| `slice-context` | Create bounded context from a ranking |
| `change-graph` | Build affected-file/symbol relationships |
| `refactor-candidates` | Detect grounded refactor candidates |
| `split-work` | Split work into child tasks |
| `command-risk` | Classify a command's risk |
| `agent-workbench-contract` | Generate rules for an external worker |
| `prepare-agent-work` | Prepare a handoff for a candidate |

Example:

```bash
python3 -m aura_agent_arena_cli topology-health

python3 -m aura_agent_arena_cli open-workspace \
  --objective "Refactor Civic model brokering"

python3 -m aura_agent_arena_cli localize-code \
  --objective "Refactor Civic model brokering"

python3 -m aura_agent_arena_cli rank-code-regions \
  --objective "Refactor Civic model brokering" \
  --max-lines 400

python3 -m aura_agent_arena_cli change-graph \
  --objective "Refactor Civic model brokering"
```

---

## 9. Coding Arena

The Coding Arena is a local visual control deck for topology selection and route simulation.

### 9.1 Launch

```bash
python3 aura_coding_arena_server.py \
  --host 127.0.0.1 \
  --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

Demo mode:

```bash
python3 aura_coding_arena_server.py \
  --host 127.0.0.1 \
  --port 8080 \
  --demo
```

### 9.2 Typical operations

- select a node;
- isolate a depth-bounded micro-arena;
- show dependencies;
- compile an Action Capsule;
- mark a missing route;
- simulate route selection;
- inspect exact file/symbol/test facts;
- compare raw context to compact worker context.

### 9.3 Safety

The Coding Arena:

- does not grant patch authority;
- does not infer exact identifiers from pixels;
- does not automatically call external providers;
- treats ST3GG, JSpace, and visualization as advisory;
- requires exact source spans, hashes, tests, verifiers, and human review.

---

## 10. Human Agent Arena

The Human Agent Arena is the human/Aura/agent command centre.

### 10.1 Launch

```bash
python3 aura_human_agent_arena_server.py --repo-root .
```

Open:

```text
http://127.0.0.1:8090
```

Demo:

```bash
python3 aura_human_agent_arena_server.py --demo
```

The server is local stdlib HTTP and polls rather than using WebSockets.

### 10.2 Core commands

| Command | Result |
|---|---|
| `show ST3GG` | Build a concept workspace around ST3GG |
| `show JSpace` | Show JSpace-related nodes |
| `show Coding Arena` | Show files, symbols, tests, docs, and neighbors |
| `show Agent Arena Bridge` | Show the machine-agent interface |
| `show all functions related to <concept>` | Return function/symbol nodes |
| `show everything connected to <concept>` | Expand files, symbols, docs, tests, and neighbors |
| `isolate selected` | Build a micro-arena around the current selection |
| `expand depth 2` | Expand selected topology depth |
| `inspect selected` | Produce a NodeIntelligencePacket |
| `why is this node here` | Explain the node's grounding path |
| `show exact source for selected` | Return file, symbol, lines, digest, and read-slice command |
| `show callers` | Show incoming relationships |
| `show callees` | Show outgoing relationships |
| `show tests for selected` | Show related tests |
| `show docs for selected` | Show related documentation |
| `show risks` | Show missing tests, hub risk, fan-in/out, and grounding risk |
| `what would break if this changed` | Show impact analysis |
| `show unwired connections here` | Run a scoped report-only emergent audit |
| `hypothesize connection` | Add a session-local ghost edge |
| `diagnose selection` | Run read-only diagnostics |
| `prepare agent task` | Prepare an Agent Arena handoff |
| `export handoff packet` | Export the current workspace and prepared tasks |

### 10.3 Node origins

- `exact_topology_node`
- `codemap_projected_node`
- `inferred_relationship_edge`
- `ghost_hypothesis_edge`
- `unresolved_candidate`

A projected node may refer to a real CODEMAP entity while remaining a visual projection. A ghost edge is a human hypothesis, not a repository fact.

### 10.4 Human Agent API

Core:

```text
GET  /api/human-agent/state
GET  /api/human-agent/events?since=N
GET  /api/human-agent/topology
POST /api/human-agent/command
GET  /api/human-agent/cost-telemetry
GET  /api/human-agent/cost-events
```

The Human Agent server also exposes Civic Commons routes under `/api/civic`.

---

## 11. Ephemeral Organ Runtime

An ephemeral organ is a temporary, capability-bounded application.

### 11.1 Lifecycle commands

Plan:

```bash
python3 -m aura_agent_arena_cli ephemeral-plan \
  --objective "Investigate the dependencies of Civic result projection" \
  --ttl 300
```

Validate:

```bash
python3 -m aura_agent_arena_cli ephemeral-validate \
  --organ-id <id> \
  --human-approval
```

Run:

```bash
python3 -m aura_agent_arena_cli ephemeral-run --organ-id <id>
```

Status:

```bash
python3 -m aura_agent_arena_cli ephemeral-status --organ-id <id>
```

Dissolve:

```bash
python3 -m aura_agent_arena_cli ephemeral-dissolve --organ-id <id>
```

Receipt:

```bash
python3 -m aura_agent_arena_cli ephemeral-receipt --organ-id <id>
```

### 11.2 MVP permissions

The read-only investigation organ may:

- inspect CODEMAP;
- inspect manifests and affordances;
- resolve capabilities;
- read authorized slices;
- compute in memory;
- write audit artifacts inside its own temporary directory;
- emit a declarative UI/result schema;
- dissolve.

It may not:

- use the network without an explicit permitted adapter;
- install packages;
- read secrets;
- execute arbitrary native code;
- mutate production;
- commit, push, or open a PR;
- become permanent automatically.

### 11.3 Security reminder

FST validation is necessary but not a sandbox. Arbitrary components require restricted Wasmtime/WASI. If that sandbox is unavailable, execution must fail closed.

---

## 12. Civic Commons Arena

The Civic Commons Arena supports transparent, non-binding community planning.

### 12.1 Run a complete fixture demo

```bash
python3 -m aura_agent_arena_cli civic-demo --story hairstylist
python3 -m aura_agent_arena_cli civic-demo --story youth_centre
python3 -m aura_agent_arena_cli civic-demo --story council_pulse
```

### 12.2 Create a session

```bash
python3 -m aura_agent_arena_cli civic-create \
  --objective "Our community needs a youth-led learning and cultural centre"
```

Save the returned `session_id`.

### 12.3 Civic commands

| Command | Purpose |
|---|---|
| `civic-demo` | Run the complete fixture lifecycle |
| `civic-create` | Create a persistent Civic session |
| `civic-status` | Read current session state |
| `civic-profiles` | Show explicitly active profiles |
| `civic-add-contribution` | Add a structured contribution from JSON |
| `civic-match-resources` | Match needs and offers |
| `civic-mitosis` | Decompose the objective into workstreams |
| `civic-scenarios` | Run MUSIC scenario comparison |
| `civic-respond` | Record a structured response/consent record |
| `civic-consent` | Generate or retrieve the Consent Arc |
| `civic-what-if` | Run a structured What-If simulation |
| `civic-pilot` | Create a bounded pilot packet |
| `civic-issue-pulse` | Produce a council-issue view |
| `civic-export` | Export the non-binding decision packet |
| `civic-close` | Close and govern/archive the session |

### 12.4 Example sequence

```bash
python3 -m aura_agent_arena_cli civic-status --session-id <id>

python3 -m aura_agent_arena_cli civic-mitosis --session-id <id>

python3 -m aura_agent_arena_cli civic-match-resources --session-id <id>

python3 -m aura_agent_arena_cli civic-scenarios --session-id <id>

python3 -m aura_agent_arena_cli civic-consent --session-id <id>

python3 -m aura_agent_arena_cli civic-pilot \
  --session-id <id> \
  --scenario-id <scenario>

python3 -m aura_agent_arena_cli civic-export --session-id <id>
```

### 12.5 Civic authority rules

Aura must not:

- infer or auto-activate cultural profiles;
- erase dissent or representation gaps;
- treat scenarios as binding;
- present snapshots as current legal advice;
- claim legal approval;
- submit decisions to government automatically;
- transfer final authority to a model.

---

## 13. Anishinaabemowin Tutor

The tutor uses vetted sources, dialect notes, governance gates, confidence labels, and review queues.

### 13.1 Basic Python use

```python
from aura_ojibwe_tutor_engine import OjibweTutorEngine, TutorMode

tutor = OjibweTutorEngine()

response = tutor.respond(
    "boozhoo",
    mode=TutorMode.WORD_LOOKUP,
    session_id="local-demo",
)

print(response.display())
```

### 13.2 Response expectations

A tutor response may include:

- normalized input;
- translation or lesson output;
- confidence;
- source references;
- dialect notes;
- morphology;
- pronunciation guidance;
- caution labels;
- teacher-review status.

Confidence classes:

- `VERIFIED`
- `CANDIDATE_NEEDS_REVIEW`
- `BLOCKED`

### 13.3 Governance levels

- `PUBLIC`
- `COMMUNITY_ONLY`
- `TEACHER_REVIEW`
- `RESTRICTED`
- `CEREMONIAL_PRIVATE`

Restricted and ceremonial-private records must never be sent to external models.

### 13.4 Dialect behavior

The default project profile is Treaty 1 Plains Ojibwe. External resources may support analysis, but dialect differences must be disclosed rather than flattened.

### 13.5 Third-party morphology licence

The integrated OjibweMorph resource is under `CC BY-NC-SA 4.0`.

Do not assume commercial use is permitted. Obtain separate permission, isolate the component, or replace it with a properly authorized alternative before commercial deployment.

---

<!-- PR92:USER_ADAPTIVE_ROUTER:START -->
## 13A. Model Cognome and Adaptive Routing

Use the adaptive compatibility router only after topology health, capability resolution, and purpose are explicit.

### Public modes

| Mode | Provider calls | Required authority | Use |
|---|---:|---|---|
| `LEGACY` | Existing behavior | Existing router controls | Default and rollback path |
| `SHADOW` | No | Purpose digest and current graph-bound context | Compare plans and collect evidence without egress |
| `PAIRED_LIVE` | Yes | Reviewed authorization JSON, named verifier, current graph digest, approved purpose, and explicit data-egress approval | One bounded live comparison |

Execution plans may select `ZERO_MODEL`, `DIRECT`, `CASCADE`, or `PANEL`. A forced model must still be admitted and cannot replace a required high-risk panel.

### Legacy commands

```powershell
python aura_router.py route --task mesh_offload --mock
python aura_router.py fusion --task "Analyze this architecture" --mock
```

### Shadow planning

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode shadow `
  --purpose-digest PURPOSE_DIGEST
```

`SHADOW` records the governed plan and evidence but must never call a provider.

### Authorized paired-live comparison

```powershell
python aura_router.py route `
  --task mesh_offload `
  --routing-mode paired_live `
  --purpose-digest PURPOSE_DIGEST `
  --authorization-file .\approved-experiment.json `
  --allow-data-egress
```

Before using `PAIRED_LIVE`, verify that the authorization names the human approver and verifier, matches the current purpose and Capability Connectome graph digest, permits the selected route/profile, has an unused nonce, has not expired, and has sufficient remaining calls.

### Non-goals and rollback

- `AURA_ADAPTIVE_ROUTER_MODE` defaults to `LEGACY`.
- `SHADOW` and `PAIRED_LIVE` do not promote policy.
- No adaptive route may automatically mutate source, commit, push, merge, or activate a learned procedure.
- Exact source spans and hashes remain patch authority.
- Return to `LEGACY` when evidence, authorization, topology freshness, endpoint lifecycle, verifier identity, or egress approval is uncertain.

See `docs/AURA_MODEL_COGNOME_ADAPTIVE_ROUTER.md` for the complete contract.
<!-- PR92:USER_ADAPTIVE_ROUTER:END -->

## 14. Legacy REPL

Launch:

```bash
python3 aura_node.py
```

The REPL remains available for compatibility, research, mesh, diagnostics, reasoning, and existing workflows. New coding-agent work should generally begin through the Native Cockpit or Agent Arena.

### 14.1 Navigation and topology

| Command | Purpose |
|---|---|
| `!settings`, `!manifest`, `!help` | Show live command/module information |
| `!ai_route <task>` | Locate relevant files and symbols |
| `!ai_router_regen` | Rebuild the AI router index |
| `!topology`, `!scan_topology` | Build current topology |
| `!topology deep`, `!topology_deep` | Run deeper topology diagnostics |
| `!simulate <target>` | Simulate a route through topology |
| `!fast_path <query>` | Run fast associative lookup |
| `!cognitive_search` | Search cognitive logs |
| `!attention` | Preserve the current thought vector in working memory |

### 14.2 Reasoning and audit

| Command | Purpose |
|---|---|
| `!reason` | Run neuro-symbolic consistency reasoning |
| `!coordinated_reason <query>` | Run coordinated multi-strategy reasoning |
| `!strategy_buffer_stats` | Show reasoning-strategy metrics |
| `!evolve_reasoning` | Crystallize a reasoning manifold |
| `!meta_analyze` | Run structural meta-analysis |
| `!meta_reason` | Check recursive resonance |
| `!saturn` | Run the NESY curriculum/sweep |
| `!saturn_heal` | Run non-destructive Saturn/NESY repair |
| `!benchmark` | Show device/runtime diagnostics |
| `!system_audit`, `!audit` | Run ecosystem audit |
| `emerge`, `emergent`, `future`, `potential` | Run the report-only emergent capability audit |
| `!test_airlock` | Test isolated WASM/tensor execution |

### 14.3 Planning, staging, and review

| Command | Purpose |
|---|---|
| `architect <intent>`, `code <intent>` | Plan a bounded refactor through Architect/Arena workflow |
| `!empirical_lab <mode>` | Define and score an experimental software task |
| `!self_reflect` | Run introspection before change |
| `!self_optimize`, `!optimize` | Create a staged optimization candidate |
| `!stage`, `!stage_review`, `!review` | Review staged work |
| `!stage_merge` | Merge only after required gates |
| `!stage_purge` | Remove staged candidates |
| `!rollback` | Restore through the rollback path |
| `!approve` | Record approval at the appropriate gate |
| `!catalyze` | Validate staged patches structurally |

### 14.4 Research and memory

| Command | Purpose |
|---|---|
| `!forage <query>` | Search/ingest research |
| `!backtrack` | Run bounded chronological research backtracking |
| `!research <query>` | Query research memory |
| `!search_similar <query>` | Find similar stored items |
| `!timeline` | Show memory/research chronology |
| `!curiosity_tree` | Explore related questions |
| `!forage_on`, `!forage_off` | Control background foraging |
| `!crystallize` | Crystallize approved learning |
| `!synthesize` | Run associative synthesis |

### 14.5 Models, routing, and savings

| Command | Purpose |
|---|---|
| `!route <task>` | Route a task |
| `!fusion <query>` | Run configured deliberation panel |
| `!calibrate` | Calibrate available providers |
| `!converse` | Run conversation mode |
| `!savings` | Show savings telemetry |
| `!mesh_status` | Show mesh status |
| `!ping_mesh` | Ping peers |

### 14.6 Interface and maintenance

| Command | Purpose |
|---|---|
| `!ar_start`, `!ar_server_start` | Start AR/topology server |
| `!ar_stop`, `!ar_server_stop` | Stop AR/topology server |
| `!export` | Export supported artifacts |
| `!push` | Use the governed push path |
| `!db_repair`, `!repair_db` | Repair supported local databases |
| `!markov` | Run Markov workspace reconstruction |
| `!voice` | Use voice input where configured |

Use `!help` for the current live set. CODEMAP and source remain authoritative when old prose differs.

---

## 15. Cost and Efficiency

### 15.1 Cost commands

| Command | Purpose |
|---|---|
| `cost-status` | Show observatory status |
| `cost-run` | Record an Aura or raw experiment |
| `cost-baseline` | Create a shadow baseline |
| `cost-compare` | Compare runs |
| `cost-report` | Produce JSON or Markdown report |
| `cost-attribution` | Show stage-level attribution |
| `cost-history` | Show recent runs |

Examples:

```bash
python3 -m aura_agent_arena_cli cost-status

python3 -m aura_agent_arena_cli cost-run \
  --objective "Refactor Civic source validation" \
  --mode aura

python3 -m aura_agent_arena_cli cost-baseline \
  --objective "Refactor Civic source validation" \
  --mode shadow

python3 -m aura_agent_arena_cli cost-report \
  --comparison-id <id> \
  --format markdown
```

### 15.2 Measurement classes

- `MEASURED`
- `TOKENIZER_EXACT`
- `DERIVED`
- `ESTIMATED`
- `UNAVAILABLE`

### 15.3 Savings states

- `SAVINGS_VERIFIED`
- `SAVINGS_PROVISIONAL`
- `SAVINGS_INVALIDATED_BY_QUALITY`
- `SAVINGS_INCONCLUSIVE`
- `NO_COMPARABLE_BASELINE`

Estimated values must not be presented as exact. Cheaper failed runs do not qualify as verified savings.

---

## 16. Common Workflows

### 16.1 Orient another AI

```bash
python3 -m aura_agent_arena_cli topology-health
python3 -m aura_agent_arena_cli digest

python3 -m aura_agent_arena_cli resolve-capabilities \
  --objective "<objective>"

python3 -m aura_agent_arena_cli search \
  --query "<concept>" \
  --kind symbol
```

Then provide only exact slices and the relevant subsystem guide.

### 16.2 Hermes through Aura

```bash
python3 -m aura_agent_arena_cli hermes-contract \
  --objective "Improve ephemeral lifecycle verification" \
  --mode pr

python3 -m aura_agent_arena_cli preflight \
  --objective "Improve ephemeral lifecycle verification" \
  --target-files aura_ephemeral_verifier.py

python3 -m aura_agent_arena_cli pr-runbook \
  --objective "Improve ephemeral lifecycle verification" \
  --branch feature/ephemeral-verifier \
  --files aura_ephemeral_verifier.py
```

Related commands:

- `token-report`
- `write-rules`

### 16.3 Capability orchestration

| Command | Purpose |
|---|---|
| `capability-lanes` | List routed lanes |
| `route-lanes` | Route an objective to lanes |
| `music-rank` | Rank candidate files/symbols |
| `mitosis-split` | Split an objective |
| `research-evidence` | Search research evidence |
| `skillweave` | Discover applicable skills |
| `goap-plan` | Build a GOAP plan |
| `swarm-plan` | Build a multi-agent plan |
| `phase-capsules` | Create phase capsules |
| `live-stage-plan` | Create a Live Architect stage plan |
| `cockpit-audit` | Export a Cockpit audit packet |

### 16.4 Safe code-change workflow

```text
topology-health
→ resolve-capabilities
→ prepare
→ context/read-slice
→ worker candidate
→ stage-patch
→ verify
→ repair-packet if required
→ status
→ human review
→ PR
→ CODEMAP refresh
```

### 16.5 Emergent architecture review

Use:

```bash
python3 -m aura_native_cockpit_server emergent-audit \
  --objective "Find latent marketplace and social matching capabilities"
```

Treat results as report-only hypotheses. A separate grounded task is required before implementation.

---

## 17. Safety and Data Governance

### 17.1 Universal rules

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
unknown_route_policy: deny
ambient_authority: forbidden
human_approval_for_consequential_effects: required
ephemeral_capabilities: explicit_and_expiring
dissolution: mandatory
```

### 17.2 External model boundaries

Before egress:

- minimize context;
- remove secrets;
- enforce data classifications;
- sanitize tokenizer channels;
- preserve source provenance;
- record provider/model/usage where permitted;
- reject restricted language or community data.

### 17.3 Human and community authority

Human or community approval is required before:

- production mutation;
- commit, push, or PR;
- live/high-risk execution;
- crystallizing a temporary organ;
- activating a cultural/governance profile;
- publishing or training on governed language data;
- converting Civic scenarios into real decisions.

### 17.4 Visual and generated surfaces

Visual topology, generated UIs, and summaries are orientation layers. They must always resolve back to exact files, sidecars, evidence, or snapshots.

---

## 18. Testing

Run focused tests for the subsystem changed.

### Coding and Agent Arenas

```bash
python3 -m pytest \
  tests/test_aura_coding_arena_3d.py \
  tests/test_aura_coding_arena_grounding.py \
  test_aura_coding_arena_workflow.py \
  -q
```

### Human Agent Arena

```bash
python3 -m pytest \
  tests/test_aura_human_agent_concepts.py \
  tests/test_aura_node_inspector.py \
  -q
```

### Ephemeral runtime

```bash
python3 -m pytest \
  tests/test_aura_ephemeral_fst.py \
  tests/test_aura_ephemeral_lifecycle.py \
  tests/test_aura_ephemeral_manifest.py \
  tests/test_aura_ephemeral_runtime.py \
  tests/test_aura_ephemeral_sandbox.py \
  -q
```

### Civic Commons

```bash
python3 -m pytest \
  tests/test_aura_civic_commons_arena.py \
  tests/test_aura_civic_completion.py \
  tests/test_aura_civic_snapshots_and_store.py \
  -q
```

### Anishinaabemowin tutor

```bash
python3 -m pytest test_aura_ojibwe_tutor.py -q
```

### FST and provenance

```bash
python3 -m pytest \
  tests/test_aura_fst_provenance.py \
  tests/test_aura_jspace_codec.py \
  -q
```

Record the exact command and commit when publishing test counts.

---

## 19. Troubleshooting

### CODEMAP has zero nodes

Run a full rebuild:

```bash
python3 aura_codebase_navigator.py
python3 -m aura_agent_arena_cli topology-health
```

Do not use change graphs or topology impact analysis until nodes and edges are non-zero.

### CODEMAP changed after one file edit

Refresh the touched path and topology:

```bash
python3 aura_codebase_navigator.py \
  --refresh path/to/changed_file.py \
  --refresh-topology
```

### Agent wants a full hub file

Use:

```bash
python3 -m aura_agent_arena_cli search --query "<symbol>" --kind symbol
python3 -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>
```

Do not dump `aura_node.py`, `aura_agent_arena_cli.py`, or other major hubs.

### No prepared Arena session

Run `prepare` before `context`, `stage-patch`, or a worker call.

### Fireworks worker skipped

Set `FIREWORKS_API_KEY` in the environment. Never place it in the repository.

### Patch fails verification

Use `repair-packet`. Do not automatically broaden scope or bypass tests.

### Ephemeral organ denied

Check:

- complete route;
- accepted machine route;
- active lease;
- requested capability subset;
- manifest digest;
- TTL;
- path policy;
- sandbox availability;
- required human approval.

### Civic evidence looks current but is a fixture

Check the source metadata and snapshot date. Fixture and snapshot data are demonstrations, not live legal advice.

### Tutor returns `CANDIDATE_NEEDS_REVIEW`

Send it through the language review workflow. Do not display it as verified community language.

### UI cannot connect

Confirm:

- correct host and port;
- local firewall;
- server is running;
- trusted LAN only when binding `0.0.0.0`;
- no expectation that the MVP provides public authentication.

---

<!-- PR92:RECENT_OPERATOR_SURFACES:START -->
### Recent operator surfaces (June 14–July 14, 2026)

The current checkout also includes guarded WFST/Experience/Crucible workflows, C1/C2/C3 evidence gates, the Model Cognome and policy-observation stores, unified cost telemetry, the Human Agent/Coding Workbench improvements, and the unified Showcase/deployment surfaces. Treat these as coordinated views over the same authority model—not independent bypasses.

For any unfamiliar surface, follow the standard sequence: topology health → digest → capability resolution → exact slices → subsystem guide → staged execution → verifier → human review.
<!-- PR92:RECENT_OPERATOR_SURFACES:END -->

## 20. Documentation Maintenance

After accepted code changes:

1. update or add focused tests;
2. update the relevant subsystem guide;
3. update this guide when commands or operator workflows change;
4. update `.aura/ARCHITECTURE.md` when architectural boundaries change;
5. update `README.md` when the public system model changes;
6. rebuild or refresh CODEMAP;
7. verify non-zero topology;
8. remove obsolete claims from old reports or move them to an archive.

Full rebuild:

```bash
python3 aura_codebase_navigator.py
```

Incremental refresh:

```bash
python3 aura_codebase_navigator.py \
  --refresh path/to/changed_file.py \
  --refresh-topology
```

Final health check:

```bash
python3 -m aura_agent_arena_cli stabilization-status
```

---

## Compact Operator Checklist

```text
[ ] topology healthy
[ ] objective bounded
[ ] existing capabilities resolved
[ ] exact files/symbols identified
[ ] context sliced
[ ] advisory layers labelled
[ ] secrets and governed data excluded
[ ] worker lease bounded
[ ] candidate staged, not promoted
[ ] focused tests run
[ ] verifier passed
[ ] human/community approval recorded
[ ] CODEMAP refreshed
[ ] documentation updated
```
