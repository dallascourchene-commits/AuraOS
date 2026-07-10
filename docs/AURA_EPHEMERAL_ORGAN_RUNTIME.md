# Aura Ephemeral Organ Runtime

## What This Is

The Ephemeral Organ Runtime allows Aura to grow a temporary organ from intent — a read-only repository investigation workspace that discovers existing capabilities, generates a declarative UI schema, records evidence and cost telemetry, and dissolves automatically.

## Architecture

```
human objective
→ IntentPacket
→ Capability Resolution Packet
→ six-slot LEXC route
→ machine effect route
→ product automaton
→ Ephemeral Organ Manifest
→ capability lease
→ sandbox preparation
→ read-only execution
→ declarative UI schema
→ verifier
→ cost/resource record
→ dissolution
→ capability revocation
→ dissolution receipt
```

## Modules

| Module | Purpose |
|--------|---------|
| `.aura/ephemeral_app.lexc` | Six-slot ephemeral grammar (256 routes) |
| `aura_ephemeral_manifest.py` | Manifest dataclasses with deterministic digest |
| `aura_ephemeral_fst.py` | Product automaton: LEXC + AuraCodingArenaRouter + lifecycle + lease + policy |
| `aura_ephemeral_lifecycle.py` | 16-state lifecycle machine with explicit transitions |
| `aura_ephemeral_sandbox.py` | Built-in adapter allowlist + Wasmtime detection, fail-closed |
| `aura_ephemeral_registry.py` | Track active/dissolved organs, manifest digests, leases |
| `aura_ephemeral_arena.py` | Arena integration: ActionCapsule, BoundaryContract, ArenaLease |
| `aura_ephemeral_runtime.py` | Orchestrator: plan → validate → run → verify → dissolve |

## CLI Commands

```
python -m aura_agent_arena_cli ephemeral-plan --objective "..."
python -m aura_agent_arena_cli ephemeral-validate --organ-id <id> --human-approval
python -m aura_agent_arena_cli ephemeral-run --organ-id <id>
python -m aura_agent_arena_cli ephemeral-status --organ-id <id>
python -m aura_agent_arena_cli ephemeral-dissolve --organ-id <id>
python -m aura_agent_arena_cli ephemeral-receipt --organ-id <id>
```

## Three FST Routing Layers Integrated

1. **LEXC route** (semantic six-slot morphotactic validation via `AuraLexc`)
2. **Machine route** (deterministic hard gates via `AuraCodingArenaRouter` in `aura_fst_routing.py`)
3. **Pre-egress interceptor** (`aura_pre_egress_interceptor.py` — numpy-based slot matrix)

The product automaton combines LEXC + machine route + lifecycle + lease + policy + sandbox + human approval.

## FST is an Admission Grammar, Not a Sandbox

The FST determines whether an action is structurally expressible and policy-valid. It is **not** a security sandbox. A route may deny authority. A route may never create authority that was not explicitly granted.

## MVP: Read-Only Repository Investigation Organ

The only required MVP application. It may:
- Read CODEMAP, Module Manifest, source slices, topology, affordances, capability lanes, plugin manifests
- Compute in memory
- Write JSON/audit artifacts to its own temporary directory
- Generate a declarative UI schema
- Dissolve

It may NOT:
- Access the network
- Install packages
- Read secrets
- Execute arbitrary native code
- Mutate production
- Commit, push, open a PR
- Become permanent automatically

## Invariants

```yaml
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
unknown_route_policy: deny
ambient_authority: forbidden
arbitrary_native_execution: forbidden
human_approval_for_consequential_effects: required
ephemeral_capabilities: explicit_and_expiring
dissolution: mandatory
```
