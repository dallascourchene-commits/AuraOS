# Aura Runtime Refactor Harness

## Purpose

The Runtime Refactor Harness closes the gap between source-level verification and a real running application. It creates an isolated Python environment, starts one repository-declared local server, waits for an exact loopback readiness endpoint, executes a bounded runtime probe, runs retained verification commands, inventories and hashes the resulting evidence, terminates the server, and emits a deterministic receipt.

It is exposed through the existing Architecture Harness entrypoint:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  runtime \
  --profile .aura/runtime_profiles/construction_demo.v1.json \
  --output-dir ../AuraOS-runtime-evidence/construction \
  --install-requirements
```

The virtual environment and output directory must remain outside the repository checkout.

## Why it exists

Compilation, unit tests, fake renderers, schemas, and static review can all pass while a real application still fails during startup or interaction. The Construction Arena exposed this exact gap:

```text
source and mocked renderer tests passed
  → real Chromium initialized WebGL
  → first Gaussian frame included shader compilation and GPU warm-up
  → elapsed time exceeded the normal frame budget
  → performance evidence was misclassified as integrity failure
  → the renderer dissolved itself
  → every later control reported an uninitialized renderer
```

The browser evidence identified `Gaussian frame-time budget exceeded` as the first causal failure. The repair kept invalid timing fatal, but classified a valid slow frame as `DEGRADED_CONTINUE` with a measured receipt. It also replaced the no-op fallback mesh callback with a deterministic bounds-derived wireframe presentation, enabling Mesh, Splats, and Hybrid without claiming that browser GLB decoding exists.

This is the intended role of the harness: expose failures that only exist when real processes, browsers, graphics contexts, network boundaries, and UI sequences interact.

## Aura Axiom bindings

The Runtime Refactor Harness applies Aura's architectural principles as executable rules:

1. **Observe before mutation.** The first run captures a failure receipt and artifacts without editing the repository.
2. **Keep truths distinct.** Source truth, presentation truth, performance evidence, integrity evidence, and authority remain separate.
3. **Ground relationships.** The profile binds the server, readiness boundary, probe, retained tests, expected artifacts, and exact repository identity into one circuit.
4. **Fail closed at real hard boundaries.** Invalid paths, non-loopback servers, malformed profiles, missing artifacts, invalid timing, process timeouts, source mutation, and failed verification remain hard failures.
5. **Degrade honestly when safe.** A measured performance overrun may remain operational when integrity and authority are intact; the receipt preserves that distinction.
6. **Dissolve exactly.** The harness always terminates the local server and records whether forced cleanup was required.
7. **Verification proves; governance authorizes.** Runtime evidence may prove a behavior for one exact tree. It cannot patch, commit, push, open a pull request, or merge.

## Runtime profile contract

Profiles live under `.aura/runtime_profiles/` and use `AURA_RUNTIME_PROFILE_V1`.

```json
{
  "version": "AURA_RUNTIME_PROFILE_V1",
  "profile_id": "construction-demo-browser",
  "objective": "Prove the real Construction browser surface end to end.",
  "environment": {
    "create_venv": true,
    "requirements": ["requirements.txt"]
  },
  "server": {
    "command": ["{python}", "aura_spatial_cli.py", "--repo-root", "{repo}", "construction-video-demo", "--serve"],
    "readiness_url": "http://127.0.0.1:8767/api/construction-demo",
    "readiness_timeout_seconds": 60
  },
  "probe": {
    "command": ["node", "tests/runtime/construction_demo_browser_probe.cjs"],
    "timeout_seconds": 120,
    "env": {
      "AURA_RUNTIME_EVIDENCE_DIR": "{output}"
    },
    "required_artifacts": ["browser-evidence.json"],
    "success_json": "browser-evidence.json",
    "success_field": "ok"
  },
  "verification_commands": [
    ["node", "--check", "aura_spatial_web/construction_demo_app.js"]
  ]
}
```

Supported placeholders are:

- `{repo}` — exact repository root;
- `{output}` — external evidence directory;
- `{python}` — isolated virtual-environment Python.

Commands are argument arrays and never pass through a shell.

### Runtime Profile V2 confirmation recovery

An `AURA_RUNTIME_PROFILE_V2` run consumes its canonical confirmation before it
starts the V1 runtime path. This is intentionally fail closed: a crash,
readiness timeout, virtual-environment failure, or later verification failure
still consumes that confirmation even when no bilateral proof is emitted.

To recover, issue a new current confirmation packet and run again with a fresh,
empty output directory. Never delete or alter a record in the trusted
Git-common-directory `aura-confirmation-consumption-v1` ledger. Removing a
consumption record would defeat the replay boundary and is not an authorized
recovery action.

## Security and boundedness

The harness enforces:

- canonical UTF-8 JSON profiles no larger than 256 KiB;
- repository-relative, traversal-free profile and requirements paths;
- literal loopback HTTP readiness URLs with explicit ports, no credentials, and redirects disabled;
- bounded command counts, argument counts, argument sizes, timeouts, continuously drained 64 KiB stdout/stderr tails, and artifact counts/sizes;
- no shell command execution;
- an environment allowlist rather than blind inheritance;
- rejection of secret-bearing environment keys declared by a profile;
- evidence and virtual environments outside the repository checkout;
- exact Git head and working-tree comparison before and after execution;
- deterministic SHA-256 artifact inventory and a 64-character run digest;
- graceful process-group termination followed by bounded forced termination when necessary.

The profile may install tracked requirements only when `--install-requirements` is explicit.

## Evidence output

A run emits:

```text
runtime_harness_receipt.json
readiness.receipt.json
probe.receipt.json
probe.stdout.log
probe.stderr.log
server.stdout.log
server.stderr.log
server-termination.receipt.json
verify-*.receipt.json
profile-required artifacts
```

The final receipt includes:

- profile ID, path, SHA-256, objective, and Axiom bindings;
- repository head, branch, and working-tree status before and after;
- virtual-environment and interpreter identity;
- exact resolved commands;
- readiness attempts and response-prefix digest;
- probe return code, timeout state, and bounded output;
- verification receipts;
- required artifact presence, size, and SHA-256;
- cleanup result;
- cycle state and run digest;
- explicit no-mutation and human-review authority contract.

## Refactor cycle

### 1. Reproduce

Run the profile before changing source:

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  runtime \
  --profile .aura/runtime_profiles/construction_demo.v1.json \
  --output-dir ../AuraOS-runtime-evidence/before \
  --install-requirements
```

A failing run returns `RUNTIME_FAILURE_REPRODUCED` and preserves the exact evidence.

### 2. Localize and review

Use the failure message, console/page errors, screenshots, server logs, CODEMAP, Coding Relationship Compass, and Waboose to identify the smallest causal path. Runtime evidence is a localization input, not patch authority.

### 3. Repair

A human-authorized coding agent may apply a bounded patch through the existing Coding Arena, Forge, Agent Bridge, or explicit repository tooling. Preserve the baseline receipt and do not rewrite it.

### 4. Verify against the baseline

```bash
python scripts/aura_architecture_harness.py \
  --repo-root . \
  runtime \
  --profile .aura/runtime_profiles/construction_demo.v1.json \
  --output-dir ../AuraOS-runtime-evidence/after \
  --baseline-receipt ../AuraOS-runtime-evidence/before/runtime_harness_receipt.json \
  --install-requirements
```

A failed baseline followed by a successful exact-profile run returns `REPAIRED_AND_VERIFIED`. The new receipt binds the prior receipt's path, SHA-256, run digest, profile ID, and outcome.

### 5. Run Waboose and retained gates

Runtime success is necessary but not sufficient. Run the exact focused test suite, Waboose, security checks, and generated-navigation verification required by the changed subsystem.

### 6. Human decision

A maintainer reviews the source diff, before/after runtime receipts, Waboose findings, tests, screenshots, and authority boundary before authorizing publication or merge.

## Construction profile

The retained Construction profile:

```text
.aura/runtime_profiles/construction_demo.v1.json
```

It boots the real deterministic server and runs:

```text
tests/runtime/construction_demo_browser_probe.cjs
```

The probe verifies:

- server/API/page loading;
- WebGL2 availability and context state;
- non-empty canvas dimensions;
- storey controls;
- orbit, zoom, explode, collapse, and show-all controls;
- Mesh, Splats, and Hybrid mode changes;
- the complete director tour;
- absence of console errors, page errors, and request failures;
- final renderer dissolution and zero-resource status;
- screenshots before and after the tour.

## Relationship to other Aura organs

- **Architecture Harness:** owns the stable entrypoint, virtual-environment discipline, AI-safe handoffs, architecture analysis, and runtime-profile delegation.
- **CODEMAP / topology:** localizes likely owners and relationships before a repair.
- **Coding Relationship Compass:** compiles the objective-scoped change and proof neighborhood.
- **Waboose:** searches deterministic and semantic defect classes around the observed failure.
- **Council V3 / Surgeon:** prepares bounded repair strategy when multiple interfaces or invariants interact.
- **Forge / Coding Arena:** stages and verifies an authorized patch.
- **Crucible:** can retain the before/after scenario as a non-authoritative regression lesson.
- **Observatory:** presents receipts, claims, failure classes, and proof boundaries.
- **Agent Bridge:** may publish a separately authorized, exact-head change; the Runtime Refactor Harness cannot.

## Authority contract

```yaml
runtime_evidence_authority: false
production_mutation: false
automatic_fix: false
automatic_commit: false
automatic_push: false
automatic_pull_request: false
automatic_merge: false
patch_authority: exact_source_spans_and_hashes_only
human_review_required: true
```
