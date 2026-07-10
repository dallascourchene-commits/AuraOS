# Aura Ephemeral Organ Security Model

## Core Principle

**FST is an admission grammar, not the entire sandbox.**

The FST may determine whether an action is structurally expressible and policy-valid. It must not be treated as sufficient isolation for malicious or compromised code.

## Security Composition

```
ALLOW(action) =
    intent_route.complete
    ∧ machine_route.accepted
    ∧ lifecycle.transition_allowed
    ∧ requested_capabilities ⊆ granted_lease
    ∧ component_digests_verified
    ∧ policy_checks_pass
    ∧ sandbox_available
    ∧ verifier_gate_passes
    ∧ required_human_approval_present
```

## Fail-Closed Rules

```
NO ROUTE       → DENY
UNKNOWN EFFECT → DENY
NO LEASE       → DENY
HASH MISMATCH  → DENY
TTL EXPIRED    → DENY
NO SANDBOX FOR ARBITRARY CODE → DENY
```

## Sandbox Boundaries

### Built-in Adapters (MVP)
- Explicit Python allowlist: `resolve_capabilities`, `search_code`, `read_slice`, `render_ui_schema`, `emit_telemetry`, `write_temp_audit`
- These are read-only or write-to-temp-only
- They call existing Aura modules, not arbitrary code

### Arbitrary Components
- Require Wasmtime/WASI runtime with:
  - No network
  - No inherited environment
  - No secrets
  - No host filesystem preopens except organ-specific temp directory
  - Bounded wall clock, memory, output, tool calls
- If Wasmtime is unavailable: **fail closed**, never fall back to native execution
- Python AST checks are NOT a complete security sandbox

### What is NOT Accepted in MVP
- Arbitrary Python execution
- JavaScript/HTML execution
- Package installation
- Shell execution
- Path traversal
- Symlink escapes
- Network access
- Secret access
- Production mutation

## Boundary Contracts

Eight boundary contracts are created for each organ:
1. **Capability** — requested ⊆ granted
2. **Filesystem** — writes confined to temp dir
3. **Network** — network_calls = 0
4. **Data/privacy** — no secrets in outputs
5. **Resource** — budget enforced
6. **Lifecycle/TTL** — dissolution mandatory
7. **UI** — declarative JSON only
8. **Crystallization** — proposal only, no automatic promotion

## Dissolution Proof

Every completed or failed organ dissolves:
- All capabilities revoked
- Temporary directory removed
- Dissolution receipt recorded
- `verify_dissolution()` confirms cleanup

## Advisory vs Authoritative

| Layer | Role |
|-------|------|
| VSA, DREAM, JSpace, ST3GG, semantic similarity | Discovery and ranking only — may NOT grant authority |
| Exact files, symbols, hashes, tests, verifier results | Authoritative |
| FST route | Admission gate — necessary but not sufficient |
| Human approval | Required for consequential effects |

## Truth Requirements

- Do not claim AST checking is a complete sandbox
- Do not claim FST validation alone is secure isolation
- Do not claim an isolated subprocess is secure arbitrary-code isolation
- Arbitrary components require a properly restricted Wasmtime/WASI runtime
- Without that runtime, fail closed
