# ARCHITECTURE (context anchor)

Minimal map so the model does not need the whole repo. This is the *only*
architectural context an Aura packet should need for a surgical edit.

- **`aura_substrate.py`** — Aura's LLM-free core: intent compression, surgical
  context selection, guardrail loading. Runs with zero model calls.
- **`aura_llm_egress.py`** — the single external egress; the only place a model
  is called (external providers only; internal/local engine and Gemini disabled).
- **`aura_node.py`** — legacy async REPL / orchestrator. Very large; never load
  it whole.
- **`aura_mesh.py`** — `AuraMeshSwarm` swarm engine. UDP beacons + a fixed
  16-byte binary frame protocol (`pack_secure_polysynthetic_packet` /
  `unpack_secure_polysynthetic_packet`). `offload_compute` ships a job to a peer.
- **`aura_topological_scanner.py`** — AST + regex scanner. `compile_unified_graph()`
  writes `Aura_Memory/live_topology_ast.json` (`nodes`, `edges`).
- **`gateway.py`** — VSA routing + `compile_thought_package` context compressor.

### Protocol invariants (do not break)

- The mesh binary frame is `struct.pack("<HHHHHHf", *six_uint16, float)` =
  16 bytes. `pack_secure_polysynthetic_packet(slot_indices: list, compliance_score: float)`.
- Topology JSON node id format is `"<file>::<symbol>"`.
- `[AURA_MASTER_KEY]` header docstrings carry `DEPENDENCIES` and `FUNCTIONS`
  lists used as a cheap symbol index.
