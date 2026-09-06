# AirLLM process-isolation worker cell

Objective: remove the concurrency hazard created when a hard-false Transformers membrane temporarily monkey-patches process-global loader classes.

Keeper: `GuardedRuntimeMutation -> DedicatedSpawnedInterpreter -> CanonicalJSONRPC -> HostGlobalStateUnaffected`.

This cell deliberately does **not** return a loaded model object to the host interpreter. Long-lived mutable model/runtime state stays in the spawned worker. The parent sees only explicitly allowlisted JSON-safe method results. That prevents monkey-patched Transformers classes, module globals, arbitrary pickles, and loaded model objects from crossing the boundary.

The cell is an integration primitive, not a claim that PR #835 is automatically merge-safe. A production AirLLM adapter still needs to construct the manifest-pinned native wrapper inside the child and define the exact JSON-safe inference surface. The existing in-process wrapper must not be treated as thread-isolated merely because it uses an Aura lock.

Security/currentness context: the cell is designed to compose with the existing PR #835 hard-false remote-code membrane, exact source/model manifests, proof-leaf reuse gate, and the new persistent `load_custom_generate` denial. Process isolation solves the unrelated-caller visibility problem; it does not replace those admission checks.

Authority ceiling: D0 software/control-plane proof only. No model/provider execution, physical throughput/latency/memory/energy result, deployment, merge authority, truth/effect authority, or Gate10.
