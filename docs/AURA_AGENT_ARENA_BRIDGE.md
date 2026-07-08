# Aura Agent Arena Bridge

## What Problem This Solves

External coding agents (Codex CLI, GitHub Codespaces, Cursor, Antigravity, OpenHands, GitHub Copilot-like agents, Fireworks-backed local workers) waste tokens by reading full files, grepping blindly, and reasoning over raw repository text. Aura already has a token-sparing repo topology system and Coding Arena that can give agents only the exact micro-context needed.

The **Aura Agent Arena Bridge** lets external agents "drive through Aura" instead of operating directly on raw files. It exposes Aura's complete coding pipeline:

- CODEMAP navigation
- Topology/symbol lookup
- Micro-arena selection
- Action capsule compilation
- Context compression / Context Crusher
- ST3GG egress/retrieval
- JSpace advisory route state
- FST/Coding Arena routing
- Liquid Planning Arena leases
- Boundary contracts
- Patch staging
- Verifier/test execution
- Compressed repair packets
- Ledger/ICM export
- No direct production mutation

## Supported Modes

### 1. MCP Mode (`aura_agent_arena_mcp.py`)

A stdio JSON-RPC-compatible MCP server that exposes all bridge tools. Can later be swapped for the official MCP Python SDK.

```bash
python -m aura_agent_arena_mcp
```

The server reads JSON-RPC 2.0 requests from stdin and writes responses to stdout. Supports `initialize`, `tools/list`, and `tools/call`.

### 2. CLI Mode (`aura_agent_arena_cli.py`)

For agents without MCP support, a CLI wrapper is provided:

```bash
scripts/aura-agent-arena digest
scripts/aura-agent-arena prepare --objective "..." --target-file aura_fst_routing.py --target-symbol AuraCodingArenaRouter
scripts/aura-agent-arena context --task-id A1 --format both
scripts/aura-agent-arena stage-patch --task-id A1 --diff-file patch.diff
scripts/aura-agent-arena verify --scope declared
scripts/aura-agent-arena repair-packet --task-id A1
scripts/aura-agent-arena status
scripts/aura-agent-arena export-icm
```

### 3. Codespaces Mode (`.devcontainer/devcontainer.json`)

When GitHub Codespaces or other cloud dev environments boot the repo, the Aura Agent Arena Bridge is ready. The devcontainer config sets `AURA_AGENT_ARENA_MODE=codespaces` and `AURA_AGENT_ARENA_PATCH_AUTHORITY=exact_source_spans_and_hashes_only`.

### 4. Fireworks Worker Mode (`aura_agent_arena_fireworks.py`)

External agents can ask Aura to call a Fireworks model for a compressed micro-patch. This uses the user's Fireworks credits and stable prompt caching.

Environment variables:
- `FIREWORKS_API_KEY` — required for Fireworks calls
- `AURA_FIREWORKS_MODEL_FAST` — model for fast tier
- `AURA_FIREWORKS_MODEL_CODE` — model for code tier
- `AURA_FIREWORKS_MODEL_JUDGE` — model for judge tier
- `AURA_FIREWORKS_SESSION_ID` — stable session affinity key

**Do not store API keys in the repo.** Fireworks keys must be injected as secrets/environment variables.

## Safety Model

- No tool may mutate production files directly.
- Patches must be staged first through `aura_stage_patch`.
- Verifier must run before hotswap (`aura_verify_arena`).
- Human review remains required before promotion.
- No raw private memory export.
- No raw sidecar dump.
- No hidden Unicode/ST3GG carrier tricks.
- ST3GG is visible ASCII only.
- JSpace/VSA/ST3GG are advisory, not patch authority.
- Large file reads must be refused or compressed.
- Full `aura_node.py` reads are blocked by default.
- All paths must resolve inside repo root.
- Absolute paths are rejected unless explicitly safe.
- Secrets must never be returned in tool output.

## Tool List

| Tool | Purpose |
|------|---------|
| `aura_repo_digest` | Return a tiny, token-sparing repo orientation packet |
| `aura_prepare_arena` | Run Aura's prepare pipeline for a coding task |
| `aura_get_micro_context` | Return exact compressed context for one Act Capsule |
| `aura_search_code` | Search CODEMAP without dumping files |
| `aura_read_slice` | Read only authorized slices from source files |
| `aura_stage_patch` | Stage a patch through Refactor Arena boundary logic |
| `aura_verify_arena` | Run verifiers/tests and return compressed result |
| `aura_repair_packet` | Return minimum context needed to repair a failed patch |
| `aura_hotswap_status` | Return whether staged transaction is ready for promotion |
| `aura_export_icm` | Export arena transaction into ICM audit workspace |
| `aura_fireworks_patch_worker` | Call Fireworks model for a compressed micro-patch |

## Example Codex CLI Workflow

```bash
# 1. Get repo orientation
scripts/aura-agent-arena digest

# 2. Prepare a coding task
scripts/aura-agent-arena prepare \
  --objective "Add ST3GG egress benchmark gate to Coding Arena capsules" \
  --target-file aura_coding_arena_3d.py \
  --target-symbol compile_action_capsule

# 3. Get compressed micro-context
scripts/aura-agent-arena context --task-id A1 --format both

# 4. Read a specific symbol slice
scripts/aura-agent-arena read-slice --file aura_fst_routing.py --symbol AuraCodingArenaRouter

# 5. Stage a patch
scripts/aura-agent-arena stage-patch --task-id A1 --diff-file /tmp/aura_patch.diff

# 6. Verify
scripts/aura-agent-arena verify --scope declared

# 7. Check status
scripts/aura-agent-arena status

# 8. Export to ICM
scripts/aura-agent-arena export-icm
```

## Example Codespaces Workflow

When a Codespace boots, the devcontainer automatically:
1. Installs dependencies from `requirements.txt`
2. Makes `scripts/aura-agent-arena` executable
3. Runs `digest` to verify CODEMAP is active

The agent can then use the CLI or MCP server directly.

## Example Fireworks Worker Workflow

```bash
# Set Fireworks API key as environment variable (never in repo)
export FIREWORKS_API_KEY="fw-..."

# Prepare and get context
scripts/aura-agent-arena prepare --objective "Fix routing bug" --target-file aura_fst_routing.py
scripts/aura-agent-arena context --task-id A1

# Call Fireworks for a candidate diff
scripts/aura-agent-arena fireworks-patch \
  --task-id A1 \
  --instruction "Return a unified diff only. Preserve patch authority and fallback behavior."

# Stage and verify the Fireworks output
scripts/aura-agent-arena stage-patch --task-id A1 --diff-file /tmp/aura_patch.diff
scripts/aura-agent-arena verify --scope declared
```

## Why Agents Should Use Aura Tools Instead of Raw File Reads

1. **Token savings**: Aura's CODEMAP and Context Crusher compress context to only what's needed.
2. **Accuracy**: Grounded capsules reference exact source spans, not fuzzy matches.
3. **Safety**: Boundary contracts and lease scopes prevent cross-boundary edits.
4. **Verifiability**: Every patch goes through verifier gates before promotion.
5. **Repair**: Structured error packets tell the agent exactly what to fix.

## Patch Authority Policy

**Patch authority is exact source spans, hashes, tests, and verifier gates.**

- VSA, JSpace, ST3GG, screenshots, summaries, and fuzzy similarity are **advisory only**.
- They may guide retrieval and reduce context, but they are **not** the source of truth.
- Every tool output includes `patch_authority: "exact_source_spans_and_hashes_only"` and `vsa_patch_authority: false`.

## Troubleshooting

### CODEMAP.json is missing
Run CODEMAP generation first. The bridge requires `.aura/CODEMAP.json` to function.

### "No prepared arena session" error
Call `aura_prepare_arena` first. The bridge stores sessions by `plan_phase_hash`.

### Fireworks worker skipped
Set `FIREWORKS_API_KEY` environment variable. The worker skips safely when the key is absent.

### Large hub file read blocked
Use `aura_search_code` with `search_kind=symbol` to find symbols, then use `aura_read_slice` with `--symbol` to read specific slices.

### Tests fail twice
Escalate instead of broadening scope. Call `aura_repair_packet` for minimal repair context.

### Absolute paths rejected
Use repo-relative paths only. The bridge rejects absolute paths for security.