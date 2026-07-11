# Aura Human–Agent Arena Workflow V2

## Purpose

The Arena is no longer organized around a graph. It is a universal human intent surface that can answer questions, inspect Aura, prepare coding work, launch bounded temporary tools, collect evidence, explain denials, and present work for human review.

The topology graph remains available as an optional spatial lens. Exact source files, symbols, hashes, tests, verifier gates, leases, and boundary contracts remain authoritative.

## Workflow spine

```text
FRAME → GROUND → PLAN → ACT → PROVE → DECIDE
```

The ordered actions are:

1. Frame objective
2. Ground in Aura
3. Prepare Arena capsule
4. Stage candidate patch
5. Run ephemeral test lab
6. Verify evidence
7. Check hotswap gate
8. Human review
9. Export review packet

Every action declares required and produced evidence. A blocked action must return:

- the missing evidence;
- the reason for denial;
- the smallest safe remediation;
- the bounded tool or prior gate that can produce the evidence.

## Ephemeral tool contract

Trusted built-in tools can be summoned from the Arena and dissolve after execution. The initial catalog includes:

- Ephemeral Test Lab
- Capability Resolver
- Topology Inspector
- Exact Source Lens
- Rust / WebAssembly Lab

Built-in tools receive explicit inputs, a capability lease, a temporary workspace, resource limits, and a dissolution receipt.

Generated or external Rust/WebAssembly components never fall back to native execution. They require an actually configured Wasmtime/WASI host contract. When that runtime is absent or incomplete, the Arena fails closed and shows the missing runtime evidence.

## Patch and review authority

The Arena does not directly merge or promote production changes.

```text
models propose
Arena stages
Shadow critiques
Judge decides
verifier proves
human reviews
```

A human-review record explicitly reports:

```json
{
  "merge_performed": false,
  "production_mutation": false
}
```

A separate explicit operator action outside this workflow is still required to merge.

## Civic map contract

The Civic Arena is map-first. The browser does not receive all civic data and decide what to hide. The server projects the current map view using:

- active jurisdiction;
- viewport bounding box;
- zoom band;
- privacy class;
- location-precision class;
- truth and source metadata.

Zoom behavior:

```text
3–6   jurisdiction boundaries and aggregate context
7–9   planning areas and neighbourhood summaries
10–12 public facilities, transit, services, and civic issues
13–18 public or community-authorized local records and scenarios
```

Protected or unauthorized records are suppressed before projection. The response includes suppression counts and an accessible table equivalent for every visible feature.

## API additions

```text
GET  /api/human-agent/workflow
POST /api/human-agent/workflow/action
POST /api/human-agent/workflow/command
GET  /api/human-agent/tools
POST /api/human-agent/tools/run
GET  /api/human-agent/tool-runs/{run_id}
GET  /api/civic/sessions/{session_id}/map-projection
```

All additions preserve:

```text
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
```
