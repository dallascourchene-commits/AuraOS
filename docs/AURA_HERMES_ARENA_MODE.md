# Aura Hermes Arena Mode

## What This Is

**Hermes through Aura** is a first-class operating mode that lets an external coding agent such as Hermes receive a normal user objective like *"refactor X and open a PR,"* but forces it to execute through Aura's token-saving Agent Arena architecture before reading, editing, testing, committing, or opening a pull request.

Hermes remains the external coding agent. Aura provides the substrate, guardrails, context reduction, exact grounding, micro-context, verification, and handoff packets.

This is **not** a new model provider. It is an Aura-native agent workflow layer.

## What It Is Not

- **Not a model provider.** No API keys, no provider calls (unless an explicit Fireworks worker command is requested).
- **Not a replacement for the Coding Arena, Agent Arena Bridge, Human Agent Arena, or Fireworks worker.** This is additive and backward compatible.
- **Not patch authority.** JSpace, VSA, ST3GG, screenshots, visual topology, and summaries remain advisory only.
- **Not a Git auto-pilot.** Human approval gates are respected. No `git add .`, no commits to main.

## How Hermes Uses Aura

The workflow transforms a normal objective into an Aura-first pipeline:

1. **Confirm clean Git state.**
2. **Create feature branch** from `origin/main`.
3. **Run Aura repo digest** — compact orientation packet.
4. **Run affordance preflight** — which internal Aura tools to reuse.
5. **Search CODEMAP** for relevant files/symbols.
6. **Refuse broad hub-file reads** — use `read-slice` with `--symbol` or `--line-start/--line-end`.
7. **Use read-slice and micro-context only** — no wholesale file reads.
8. **Produce Token Savings Report** before editing.
9. **Prepare arena task** — `aura_prepare_arena`.
10. **Get micro-context packet** — `aura_get_micro_context`.
11. **Edit only localized files** — those identified by CODEMAP and micro-context.
12. **Stage patch through Aura boundary** — `aura_stage_patch`.
13. **Run verifier/focused tests** — `aura_verify_arena`.
14. **Produce repair packet** if tests fail — `aura_repair_packet`.
15. **Wait for human approval** before final commit/push if configured.
16. **Commit only scoped files** — never `git add .`.
17. **Push feature branch.**
18. **Open a PR** with `gh` CLI if available, otherwise print the exact command and compare URL.

## Quickstart for Windows PowerShell

All commands use `python -m aura_agent_arena_cli` (not bash-only scripts):

```powershell
# 1. Generate the Hermes operating contract for your objective
python -m aura_agent_arena_cli hermes-contract --objective "Refactor Aura's LLM egress to support Fireworks and open a PR." --mode pr

# 2. Generate the preflight packet
python -m aura_agent_arena_cli preflight --objective "Refactor Fireworks egress provider"

# 3. Generate the token savings report
python -m aura_agent_arena_cli token-report --objective "Refactor Fireworks egress" --files aura_llm_egress.py,aura_agent_arena_bridge.py --include-preflight

# 4. Generate the PR-safe runbook
python -m aura_agent_arena_cli pr-runbook --objective "Refactor Fireworks egress" --branch feature/fireworks-egress-refactor

# 5. Write the guard rules file
python -m aura_agent_arena_cli write-rules
```

## Example Normal Objective

> "Refactor Aura's LLM egress to support Fireworks and open a PR."

## Example Hermes Prompt

Paste the output of `hermes-contract` into Hermes as its system/operator prompt:

```powershell
python -m aura_agent_arena_cli hermes-contract --objective "Refactor Aura's LLM egress to support Fireworks and open a PR." --mode pr
```

This produces a markdown contract with:
- Mandatory Aura-first workflow rules
- Exact commands Hermes should run (in order)
- Git safety rules
- Token savings report requirement
- Approval gate requirement
- PR creation rules
- No broad file reads
- No `git add .`
- Use `read-slice` / `context` before edits

You can also get the full JSON packet:

```powershell
python -m aura_agent_arena_cli hermes-contract --objective "..." --mode pr --json
```

## Example Preflight Output

```powershell
python -m aura_agent_arena_cli preflight --objective "Refactor Fireworks egress provider"
```

```json
{
  "ok": true,
  "version": "AURA_HERMES_ARENA_MODE_V1",
  "objective": "Refactor Fireworks egress provider",
  "repo_digest": {
    "codemap_status": "AURA_CODEMAP_ACTIVE",
    "file_count": 314,
    "symbol_count": 1200,
    "topology_nodes": 80,
    "topology_edges": 120
  },
  "recommended_affordances": [
    {
      "id": "aura.llm_egress",
      "name": "LLM Egress",
      "description": "Manages LLM egress — pre-egress interception, token economics...",
      "when_to_use": "When you need to manage LLM egress...",
      "score": 8.5,
      "patch_authority": false,
      "vsa_patch_authority": false
    }
  ],
  "prompt_cards": [
    "Use LLM Egress to manage and optimize output before sending to external models."
  ],
  "likely_files": ["aura_llm_egress.py", "aura_agent_arena_bridge.py", "aura_api_rotator.py"],
  "likely_symbols": ["AuraLLMEgress", "generate_openai_compatible_payload"],
  "suggested_searches": [
    "python -m aura_agent_arena_cli search --query \"fireworks\" --kind symbol",
    "python -m aura_agent_arena_cli search --query \"egress\" --kind symbol"
  ],
  "suggested_read_slices": [
    "python -m aura_agent_arena_cli read-slice --file aura_llm_egress.py --symbol AuraLLMEgress"
  ],
  "suggested_prepare_command": "python -m aura_agent_arena_cli prepare --objective \"...\" --target-file aura_llm_egress.py --target-symbol AuraLLMEgress",
  "safety_rules": [
    "You are inside AuraOS.",
    "You must use the Aura Agent Arena Bridge before direct file reads.",
    "..."
  ],
  "patch_authority": "exact_source_spans_and_hashes_only",
  "vsa_patch_authority": false,
  "estimated_token_baseline": 5000
}
```

## Example Token Savings Report

```powershell
python -m aura_agent_arena_cli token-report --objective "Refactor Fireworks egress" --files aura_llm_egress.py,aura_agent_arena_bridge.py --include-preflight
```

```json
{
  "ok": true,
  "version": "AURA_HERMES_ARENA_MODE_V1",
  "objective": "Refactor Fireworks egress",
  "raw_files_considered": ["aura_llm_egress.py", "aura_agent_arena_bridge.py"],
  "raw_char_count": 82000,
  "raw_token_estimate": 20500,
  "aura_digest_token_estimate": 300,
  "aura_search_token_estimate": 600,
  "aura_read_slice_token_estimate": 1200,
  "aura_micro_context_token_estimate": 500,
  "total_aura_token_estimate": 2600,
  "estimated_tokens_saved": 17900,
  "estimated_percent_saved": 87.3,
  "files_avoided": [],
  "method": "local_chars_div_4_estimate",
  "warning": "This is a local estimate using chars / 4, NOT provider billing telemetry. Actual token usage depends on the model tokenizer and prompt structure.",
  "patch_authority": "exact_source_spans_and_hashes_only",
  "vsa_patch_authority": false
}
```

Markdown format is also available:

```powershell
python -m aura_agent_arena_cli token-report --objective "..." --files aura_llm_egress.py --format markdown
```

## Example PR Workflow

```powershell
# 1. Generate the runbook
python -m aura_agent_arena_cli pr-runbook --objective "Refactor Fireworks egress" --branch feature/fireworks-egress-refactor
```

The runbook prints the exact sequence:

```bash
# Git setup
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/fireworks-egress-refactor

# Aura preflight
python -m aura_agent_arena_cli digest
python -m aura_agent_arena_cli find-affordances --objective "Refactor Fireworks egress"
python -m aura_agent_arena_cli preflight --objective "Refactor Fireworks egress"

# Aura read-slice / context
python -m aura_agent_arena_cli read-slice --file aura_llm_egress.py
python -m aura_agent_arena_cli search --query "fireworks" --kind symbol

# Token savings report (before editing)
python -m aura_agent_arena_cli token-report --objective "Refactor Fireworks egress" --files aura_llm_egress.py --include-preflight

# Prepare arena task
python -m aura_agent_arena_cli prepare --objective "Refactor Fireworks egress" --target-file aura_llm_egress.py
python -m aura_agent_arena_cli context --task-id A1 --format both

# Edit (localized files only)
# ... make changes ...

# Stage patch through Aura
python -m aura_agent_arena_cli stage-patch --task-id A1 --diff-file patch.diff --affected-files aura_llm_egress.py

# Run tests
python -m aura_agent_arena_cli verify --scope focused

# Commit (scoped files only — NEVER git add .)
git diff --stat
git add aura_llm_egress.py
git commit -m "Refactor Fireworks egress"

# Push
git push -u origin feature/fireworks-egress-refactor

# Open PR
gh pr create --title "Refactor Fireworks egress" --body "..." --base main
```

If `gh` CLI is not available, the runbook prints the compare URL:
```
https://github.com/dallascourchene-commits/AuraOS/compare/main...feature/fireworks-egress-refactor
```

## Guard File

The `.aura/HERMES_AURA_RULES.md` file is a concise, copyable ruleset that Hermes can be told to obey. Generate it with:

```powershell
python -m aura_agent_arena_cli write-rules
```

Contents:

```markdown
# Hermes → Aura Rules

You are inside AuraOS.

## Mandatory Rules

1. You must use the Aura Agent Arena Bridge before direct file reads.
2. You must call digest first: `python -m aura_agent_arena_cli digest`
3. You must call find-affordances before planning.
4. You must use CODEMAP search before opening files.
5. You must use read-slice for exact source.
6. You must produce token savings evidence before editing.
7. You must use a feature branch and PR workflow. Never commit directly to main.
8. You must NOT use `git add .` — stage only specific scoped files.
9. You must NOT read hub files directly. Use read-slice with `--symbol`.
10. You must NOT treat advisory layers as patch authority.
11. You must NOT read .venv, node_modules, __pycache__, build artifacts, or generated files.
12. All paths must remain repo-relative inside AuraOS.
13. On Windows, use: `python -m aura_agent_arena_cli <subcommand>`.
```

## CLI Commands Added

| Command | Purpose |
|---------|---------|
| `hermes-contract` | Generate a ready-to-paste Hermes system/operator prompt |
| `preflight` | Generate a compact JSON preflight packet for a coding objective |
| `token-report` | Generate a token savings report comparing raw vs Aura context usage |
| `pr-runbook` | Generate a PR-safe Git/Hermes workflow runbook for a task |
| `write-rules` | Write `.aura/HERMES_AURA_RULES.md` guard file |

All commands use `python -m aura_agent_arena_cli <subcommand>` for Windows compatibility.

## Troubleshooting

### CODEMAP.json is missing
Run CODEMAP generation first. The preflight and contract generators require `.aura/CODEMAP.json`.

### "Hermes Arena Mode is not available"
Ensure `aura_hermes_arena_mode.py` is in the repo root and importable. The CLI import is wrapped in a try/except so existing commands still work even if the new module has an import error.

### Affordance lookup failed
The preflight packet includes an `affordance_warning` field if the affordance directory lookup fails. The rest of the packet is still valid — only the `recommended_affordances` list will be empty.

### Hub file read blocked
Use `python -m aura_agent_arena_cli search --query "symbol_name" --kind symbol` to find symbols, then `python -m aura_agent_arena_cli read-slice --file <file> --symbol <symbol>` to read specific slices.

### gh CLI not available
The runbook prints the exact `gh pr create` command and the compare URL. You can open the PR manually via the compare URL in your browser.

## Safety Model

### Patch Authority

**Patch authority is exact source spans, hashes, CODEMAP facts, tests, and verifier gates.**

- `patch_authority: "exact_source_spans_and_hashes_only"`
- `vsa_patch_authority: false`
- VSA, JSpace, ST3GG, screenshots, summaries, and fuzzy similarity are **advisory only**.
- Every packet and contract includes these invariants.

### Git Safety

- No `git add .` — stage only specific scoped files.
- No commits to main.
- No untracked nested AuraOS folders or scratch directories.
- STOP if working tree is dirty before branch creation unless user explicitly approves.
- Use `git diff --stat` to verify exactly which files will be committed.

### Read Safety

- Broad hub-file reads are blocked unless a specific symbol or line range is requested.
- Forbidden directories: `.venv`, `node_modules`, `__pycache__`, build artifacts, generated files, caches.
- All paths must remain repo-relative.
- Absolute paths are rejected.

### No Provider Calls

- No hardcoded API keys.
- No provider API calls unless an explicit Fireworks worker command is requested.
- The token savings report uses `chars / 4` as a local estimate — it is NOT provider billing telemetry.

### Additive and Backward Compatible

- Does not replace the existing Coding Arena, Agent Arena Bridge, Human Agent Arena, or Fireworks worker.
- The CLI import of `aura_hermes_arena_mode` is wrapped in try/except — if it fails, all existing CLI commands still work.
- All new subcommands are additions to the existing `aura_agent_arena_cli` parser.

## Architecture

```
User objective
      │
      ▼
┌──────────────────────┐
│  hermes-contract     │  →  Ready-to-paste system prompt with workflow rules
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  preflight           │  →  JSON packet: digest, affordances, likely files/symbols, searches
│  (calls existing     │     suggested_read_slices, prepare command, safety rules, token baseline
│   Aura internals)    │
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  token-report        │  →  Raw vs Aura token comparison (local estimate)
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│  pr-runbook          │  →  Exact Git/Hermes workflow for the task
└──────────────────────┘
      │
      ▼
  Agent executes through:
    • Agent Arena Bridge (digest, search, read-slice, prepare, context, stage, verify, repair)
    • CODEMAP navigation
    • Affordance Directory
    • Concept Workspace
    • Node Inspector
    • Context Crusher / ST3GG / JSpace (advisory)
```

## Files

| File | Role |
|------|------|
| `aura_hermes_arena_mode.py` | Core module — contract generator, preflight, token report, PR runbook, guard file |
| `aura_agent_arena_cli.py` | Extended with `hermes-contract`, `preflight`, `token-report`, `pr-runbook`, `write-rules` subcommands |
| `.aura/HERMES_AURA_RULES.md` | Guard ruleset file |
| `tests/test_aura_hermes_arena_mode.py` | Deterministic tests (56 tests, no network/Fireworks/GitHub auth) |
| `docs/AURA_HERMES_ARENA_MODE.md` | This document |
