# AuraOS Verified Ephemeral Workspace V2

**Master implementation unit:** PR2
**Exact base:** `9c04a1efa57461a6078acb9f3b569766cbd2ab24` (merged PR #255)
**Terminal state:** `READY_FOR_HUMAN_REVIEW`

## Objective

PR2 preserves the public one-shot Ephemeral Organ V1 flow and adds a separate,
interactive V2 workspace lifecycle. V2 compiles the immutable PR1
`EphemeralWorkspaceRecipe` into an exact `WorkspaceExecutionGraph`, binds that
complete graph to independently supplied recipe and adapter expectations,
admits it under a unique nonce and expiring lease, executes only dependency-ready
nodes, prepares proposal-only action certificates, and dissolves all temporary
state on completion, cancellation, failure, invalidation, expiry, or process
interruption.

```text
V1 organ (unchanged)
plan -> run fixed steps -> verify -> dissolve

V2 workspace
recipe -> compile -> parse -> bind -> admit -> activate
       -> execute exact graph nodes / interact
       -> prepare proof-carrying domain handoff
       -> complete | cancel | fail | expire | invalidate
       -> revoke lease -> remove sandbox -> verify cleanup -> dissolve
```

No renderer, WebXR, multimodal, collaboration, package, marketplace, payment,
source-mutation, deployment, publication, professional, physical-work, or merge
authority is introduced.

## Exact-head Harness grounding

The repository-owned read-only Harness export ran against the exact merged PR1
head. The resulting architecture digest was
`bf397cce5a66c4c121965dcfd8df81bb`. The bounded Coding Relationship Compass
packet completed with digest
`2568b3320969ede51387b76da2df64d86d59a45244befa29`; its evidence grounding
digest was `5c9b9d7469bc5b18ef525612c8ee1705cad9d83c8aeb22d7`.

The final nine-file allowed set is recorded in the objective and Waboose request.
Its architecture scope digest is
`d0f74015d3f1b616aa10b631a0632dcc77936bb010101712b4b8216fc33a25c3`.
Generated CODEMAP/topology files are deliberately excluded until source and tests
are stable.

## Canonical owner matrix

| Concern | Existing owner retained | PR2 disposition |
|---|---|---|
| PR1 recipe/canonicalization/authority | `aura_ephemeral_workspace_contracts.py` | Read and bind; never replaced |
| V1 one-shot orchestration | `aura_ephemeral_runtime.py` | Unchanged |
| V1 lifecycle DFA | `aura_ephemeral_lifecycle.py` | Unchanged |
| Adapter implementation | `aura_ephemeral_sandbox.py` | Existing allowlisted implementations retained |
| Adapter operational identity | `aura_ephemeral_adapter_registry.py` | Add exact behavioral digests, host/rollback evidence, revocation |
| Persistent lifecycle state | `aura_ephemeral_registry_store.py` | Add a separate schema-v2 table and CAS methods |
| Path policy/sandbox cleanup | existing path-policy and sandbox owners | Reused; no second sandbox owner |
| V2 orchestration | `aura_ephemeral_workspace_runtime_v2.py` | New additive companion only |
| Domain action | Forge/domain owner | Certificate preparation only; no execution authority |
| Verification/human disposition | Runtime Harness/Waboose/Council/human | Preserved |

## Trust states

### Parse

`parse_workspace_execution_graph_v2()` accepts only exact bounded JSON structure,
canonical IDs and SHA-256 digests, the closed PR1 authority envelope, matching
node/graph self-integrity, and explicit denial of arbitrary native execution.

### Bind

`bind_workspace_execution_graph_v2()` recompiles the complete expected graph from
an independently supplied current PR1 recipe, complete capability-to-adapter map,
and current operational registry. A self-consistent but stale graph fails.

### Admit

`admit_workspace_v2()` admits only a bound, unexpired graph under a unique
activation nonce. Duplicate workspace identity or nonce fails in SQLite. Admission
does not execute a callback or grant domain authority.

## WorkspaceExecutionGraph invariants

Every graph binds exact capability, adapter, implementation, input schema, output
schema, assumption, source, recipe, and graph identities. Semantic validation
requires:

- a non-empty acyclic graph;
- exact entry and terminal sets;
- every node reachable from an entry and able to reach a terminal;
- no duplicate/self/dangling edge;
- no unknown or revoked adapter;
- no denied or undeclared effect;
- a human gate on every consequential `domain_handoff` node;
- zero model and network calls in PR2;
- bounded retry, timeout, tool-call, output, memory, and wall-time declarations;
- graph lifetime bounded by the recipe;
- exact closed authority and `arbitrary_native_execution: false`.

Nodes are executed in sorted topological waves. PR2 records how many nodes are
proven independent but intentionally uses deterministic serial execution
(`parallelism_used: 1`) until a later bounded implementation proves safe
concurrency behavior.

## Receipts and failure attribution

A verified node receipt binds:

- workspace and graph identity;
- node, adapter, and implementation identity;
- exact input and output digests;
- ordered upstream receipt digests;
- assumptions and source identity;
- start/end timestamps;
- the complete receipt digest.

Failures are classified as `local`, `upstream`, `structural`, `stale`, `policy`,
`budget`, `cancellation`, or `environment`. Ordinary adapter exceptions are
normalized into a failed result. `KeyboardInterrupt`, `SystemExit`, and other
process-level exceptions are never swallowed: cleanup runs and the original
exception is re-raised, with a cleanup exception explicitly chained if cleanup
itself fails.

Partial re-execution reuses a receipt only when the exact node binding,
implementation, assumptions, source, and all upstream receipt digests remain
unchanged. Changed nodes and their complete downstream closure are re-executed.

## Hostile-output boundary

Adapter results are copied through a bounded JSON detacher before inspection or
persistence. It rejects recursive containers, hostile mapping/sequence protocol
failures, duplicate/non-string keys, non-finite numbers, oversized nesting,
item-count or string ceilings, and non-JSON values. Declared output paths must
resolve inside the unique workspace sandbox and cannot be symlink escapes.

The registry binds portable callable source identity (module, qualified name, and
SHA-256 of source text) rather than process- or checkout-specific bytecode/`repr()`
values. Revocation changes the adapter identity and blocks later calls.

## Lifecycle and cleanup

V2 uses its own states:

```text
ADMITTED -> ACTIVATING -> ACTIVE
ACTIVE -> COMPLETING | CANCELLING | INVALIDATING | FAILING | EXPIRING
terminal-preparation -> DISSOLVING -> DISSOLVED
```

State changes are compare-and-set. Activation can occur only once. A dissolved
workspace cannot activate or resume. Every terminal path revokes the workspace
lease, removes the sandbox directory, verifies both facts, and records a cleanup
receipt. Cleanup failure remains visible in `DISSOLVING`; it is never mislabeled
as dissolved.

## SpatialActionCertificate V2

A certificate binds the principal, requested operation, exact subjects/targets,
workspace graph, policy, approval class, runtime environment, effect boundary,
assumptions, cost, reversibility, proof obligations, nonce, and expiry.

Its receipt sequence is closed and monotonic:

```text
PREPARED -> OPEN -> APPROVED -> EXECUTED -> CLOSED
              human        canonical owner   runtime/outcome owner
```

The Spatial/runtime layer may prepare and open the record. It cannot provide the
canonical execution or outcome proof required to progress through the final
states. Even an `EXECUTED` or `CLOSED` certificate is evidence projected from the
canonical owner; it is not a grant of authority from the spatial layer.

## Verification

Run from an external environment:

```bash
python -m py_compile \
  aura_ephemeral_adapter_registry.py \
  aura_ephemeral_registry_store.py \
  aura_ephemeral_workspace_runtime_v2.py \
  tests/test_aura_ephemeral_workspace_runtime_v2.py

pytest -q tests/test_aura_ephemeral_workspace_runtime_v2.py

pytest -q \
  tests/test_aura_ephemeral_runtime.py \
  tests/test_aura_ephemeral_phase0_hardening.py \
  tests/test_aura_ephemeral_workspace_contracts.py

python - <<'PY'
import json
from jsonschema import Draft202012Validator
for path in (
    "schemas/aura_workspace_execution_graph_v2.schema.json",
    "schemas/aura_spatial_action_certificate_v2.schema.json",
):
    Draft202012Validator.check_schema(json.load(open(path, encoding="utf-8")))
PY

git diff --check
```

Hosted checks must additionally run fatal Ruff classes and confirm that the diff
contains only the exact allowed files. External reviewers are not automatically
requested. Human review and merge remain separate decisions.

## Explicit exclusions

PR2 does not begin PR3, implement project reconstruction, render a spatial scene,
consume sensor streams, add collaboration, package Aura capabilities, publish a
marketplace, move money, enable Wasmtime/WASI arbitrary components, mutate source,
or regenerate generated navigation while source is unstable.
