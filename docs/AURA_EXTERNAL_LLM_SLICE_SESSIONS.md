# Aura External-LLM Slice Sessions

## Purpose

This adapter lets an external LLM work **through Aura** without receiving or
downloading the repository.

The model receives one leased turn packet at a time:

```text
objective
+ current role and gate
+ one Act Capsule
+ exact authorized source slices
+ bounded nearby test slices
+ output contract
+ prior failure evidence, when repairing
```

Aura retains:

- CODEMAP and topology search;
- plan phase identity;
- Refactor Arena boundaries and leases;
- patch staging;
- test and verifier execution;
- repair-packet generation;
- hot-swap readiness;
- human review authority;
- session evidence and usage records.

The adapter never commits, pushes, merges, promotes, or directly mutates
production source.

## Two integration modes

### 1. MCP slice-session loop

Run the additive Agent Arena MCP entrypoint:

```bash
python aura_agent_arena_mcp_external_llm.py
```

It exposes every existing Agent Arena MCP tool plus:

| Tool | Purpose |
|---|---|
| `aura_llm_session_open` | Prepare the Arena and return the first bounded turn |
| `aura_llm_session_next` | Fetch the current pending turn |
| `aura_llm_session_submit` | Submit a diff; Aura stages, verifies, and returns completion or repair |
| `aura_llm_session_status` | Inspect safe session state and measured turn history |
| `aura_llm_session_export` | Export review evidence as JSON |

An MCP-capable agent can autonomously repeat:

```text
open
→ inspect leased turn
→ produce required response
→ submit
→ receive repair turn if blocked
→ submit repair
→ stop at READY_FOR_HUMAN_REVIEW
```

The same `AuraAgentArenaBridge` object is retained for every turn, preserving
the plan phase hash, staged state, verification evidence, and Arena boundaries.

### 2. Direct provider callback

`run_live_architect_with_external_callback()` runs Aura's real Live Architect
Council using any provider-neutral callback.

```python
import asyncio

from aura_external_llm_session import (
    run_live_architect_with_external_callback,
)


def my_model_client(request: dict) -> dict:
    # Route by request["role"], request["provider"], or request["profile"].
    # Call OpenAI, Anthropic, Gemini, Fireworks, Hermes, a local model, etc.
    return {
        "text": call_my_provider(request["prompt"]),
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
        },
        "cost_usd": 0.0,
    }


result = asyncio.run(
    run_live_architect_with_external_callback(
        "Consolidate Aura's memory, skill, and agentic functions for the Human Agent Arena",
        callback=my_model_client,
        repo_root=".",
    )
)
```

Aura still determines the planner, alternate planner, Shadow critics, Judge,
Builder tasks, temporary-workspace verification, rollback capsule, ledger
record, and hot-swap readiness. The callback only supplies model completions.

## Leased turn packet

A turn includes:

```json
{
  "role": "worker",
  "gate": "ACT",
  "task_id": "A1",
  "objective": "...",
  "act_capsule": {},
  "compressed_context": "...",
  "source_slices": [
    {
      "file": "aura_example.py",
      "symbol": "target_symbol",
      "line_start": 30,
      "line_end": 76,
      "content": "..."
    }
  ],
  "test_slices": [],
  "failure_packet": {},
  "allowed_files": ["aura_example.py"],
  "do_not_touch": [],
  "context_token_estimate": 1174,
  "max_output_tokens": 2400,
  "output_contract": {
    "required_response": "unified_diff_only"
  },
  "production_mutation": false
}
```

No full-repository archive or broad file dump is present.

## Automatic repair

When staging or verification fails:

```text
failure
→ Aura repair packet
→ exact allowed files
→ do-not-touch files
→ bounded source/test slices
→ repair turn
→ model returns revised unified diff
→ Aura stages and verifies again
```

The failed response and provider usage are retained in the session history.

## Measurement

`InstrumentedExternalModelCaller` records, per model call:

- role;
- provider;
- estimated input and output tokens;
- provider-reported usage when supplied;
- provider-reported cost when supplied;
- latency;
- request and response digests.

This is the instrumentation required for the Architect benchmark:

```text
same objective
same repository commit
same quality gates
different orchestration arms
→ compare total model tokens, cost, latency, grounding, verifier result,
  repair count, blast radius, and human-review readiness
```

## Authority invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
production_mutation: false
automatic_commit: false
automatic_push: false
automatic_merge: false
human_review_required: true
```
