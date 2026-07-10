# Aura Native Cockpit

## What This Is

The **Aura Native Cockpit** is Aura's primary human coding interface. A human interacts with Aura first — feeding it structured Markdown intent documents instead of giant raw prompts. Aura compresses the intent polysynthetically, routes it through her FST architecture, localizes relevant code through CODEMAP, ranks context with DREAM-lite, compresses with Context Crusher/ST3GG, and sends approved work to Hermes/Codex/Agent Arena as compact, verifiable packets.

## What It Is Not

- **Not a replacement for Hermes.** Hermes remains an external coding worker. Aura is the cockpit, substrate, router, compressor, context selector, and human checkpoint authority.
- **Not a model.** Aura's deterministic substrate remains LLM-free. External LLM calls go through the egress boundary only.
- **Not a generic UI wrapper.** This is built in Aura's own architecture — FST routing, polysynthetic compression, CODEMAP grounding, and checkpoint gates.
- **Not patch authority.** JSpace, VSA, ST3GG, DREAM-lite, QDKT, visual topology, and summaries are advisory only.

## How It Works

```
Human writes .aura/intents/*.aura.md
         │
         ▼
    Aura Native Cockpit
         │
    ┌────┴────────────────────────────────┐
    │ 1. Parse intent document             │
    │ 2. Compress polysynthetically        │
    │ 3. Validate LEXC six-slot route      │
    │ 4. Route through FST                 │
    │ 5. Localize via CODEMAP/AI Router    │
    │ 6. Rank with DREAM-lite              │
    │ 7. Compress with Context Crusher     │
    │ 8. ST3GG egress decision             │
    │ 9. Ground through Coding Arena       │
    │ 10. Checkpoint gates + human approval│
    └────┬────────────────────────────────┘
         │
         ▼
    Agent Handoff Packet (compact)
         │
         ▼
    Hermes / Codex / Agent Arena Bridge
```

## Quickstart

```powershell
# Launch the cockpit CLI
python -m aura_native_cockpit_server --repo-root .

# Ingest an intent document
python -m aura_native_cockpit_server ingest-intent --file .aura/intents/example.aura.md

# Generate a cockpit contract for an objective
python -m aura_native_cockpit_server contract --objective "Refactor Fireworks egress"

# Build the capability connectome
python -m aura_native_cockpit_server connectome

# Compute token economy
python -m aura_native_cockpit_server token-economy --objective "Refactor Fireworks egress" --files aura_llm_egress.py

# Show workflow gates
python -m aura_native_cockpit_server gates

# Prepare agent handoff
python -m aura_native_cockpit_server handoff --intent-file .aura/intents/example.aura.md --agent hermes
```

## CLI Commands (via aura_agent_arena_cli)

| Command | Purpose |
|---------|---------|
| `ingest-intent` | Ingest an intent document and compile an IntentPacket |
| `validate-lexc-route` | Validate the LEXC route from an intent document |
| `capability-connectome` | Build the full capability connectome graph |
| `capability-path` | Find the capability path for an objective |
| `token-economy` | Compute a token economy report with savings sources |
| `workflow-gates` | Show the 18-state workflow checkpoint machine |
| `native-cockpit-contract` | Generate a cockpit contract for an objective |
| `prepare-native-handoff` | Prepare an agent handoff packet from an intent document |

## Safety Model

### Patch Authority
- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`

### Advisory-Only Layers
VSA, JSpace, ST3GG, DREAM-lite, QDKT, visual topology, screenshots, summaries, fuzzy similarity, emergent potential reports.

### No Production Mutation
The cockpit never mutates production code. All mutations go through the Agent Arena Bridge staging pipeline.

### Human Approval Gates
- HUMAN_APPROVED_FOR_AGENT — before sending work to an agent
- HUMAN_APPROVED_FOR_COMMIT — before committing
- PR_READY — before opening a PR

## Modules

| Module | Role |
|--------|------|
| `aura_native_cockpit.py` | Cockpit orchestrator — unifies all Aura systems |
| `aura_native_cockpit_server.py` | CLI entry point for the cockpit |
| `aura_intent_ingestion.py` | Intent document parser and polysynthetic compiler |
| `aura_capability_connectome.py` | Living graph of Aura's capabilities |
| `aura_workflow_gates.py` | 18-state checkpoint machine |
| `aura_token_economy_orchestrator.py` | Token savings measurement across all layers |
