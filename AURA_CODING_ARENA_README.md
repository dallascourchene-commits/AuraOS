# Aura Human-First 3D Coding Arena MVP

This MVP is a local, browser-based control deck for selecting a small code
micro-arena before any worker model acts.

The source of truth is local Aura topology: `.aura/CODEMAP.json`,
`.aura/understand_graph.json`, AST-derived paths, and exact line/symbol facts.
The 3D view is only a human interface. Screenshots or VLM summaries are optional
orientation aids and are never patch authority.

## Run Locally

```bash
python aura_coding_arena_server.py --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

Offline demo mode:

```bash
python aura_coding_arena_server.py --host 127.0.0.1 --port 8080 --demo
```

Print topology JSON without serving:

```bash
python aura_coding_arena_server.py --demo --print-topology
```

## Docker

```bash
docker build -t aura-coding-arena .
docker run --rm -p 8080:8080 aura-coding-arena
```

The container starts in demo mode by default and does not require secrets.

## Phone on Same LAN

For a local demo on a trusted LAN:

```bash
python aura_coding_arena_server.py --host 0.0.0.0 --port 8080 --demo
```

Open `http://<your-computer-lan-ip>:8080` from the phone. Do this only on a
trusted network; the MVP has no authentication.

## Voice / Text Commands

The UI uses the browser Web Speech API when available and falls back to typed
commands.

Supported deterministic commands:

- `isolate this class`
- `show dependencies`
- `compile capsule`
- `mark missing route`
- `send to worker`
- `simulate route`

These commands only call local API routes. They do not call provider APIs.

## What the Capsule Does

The capsule compiler converts the selected graph node into compact JSON:

- selected node IDs
- exact target files and symbols where available
- line ranges
- callers, callees, dependencies, and tests
- candidate wiring faults
- token-cost comparison
- deterministic route scorecard

The capsule is intentionally smaller than raw CODEMAP/topology JSON. Worker
models should receive the capsule, not the full repository graph.

## ST3GG Coding Arena Egress

Coding Arena capsules can expose an optional ST3GG egress view when the local
char/4 token estimate shows a useful savings. The egress payload is a visible
ASCII machine capsule plus a local recall pointer; it does not use hidden
Unicode, zero-width characters, private-use characters, bidi controls, or other
steganographic carriers.

The full original capsule is stored in Aura-local ST3GG recall sidecars, so a
diagnostic can recover the exact JSON by pointer or hash. Worker models may use
the compact ST3GG view as advisory context, but they cannot patch from ST3GG
alone. Exact source spans, source hashes, tests, and verifier gates remain the
only patch authority. Tokenizer guard sanitization strips forbidden carriers
before egress, and compression is disabled when it does not clear the benchmark
savings threshold.

## Simulated vs Real

Real in this MVP:

- CODEMAP/demo topology loading
- click selection and depth-1/depth-2 expansion
- deterministic capsule JSON
- candidate wiring fault detection
- token savings estimate
- local route scorecard

Simulated in this MVP:

- `LOCAL_GEMMA_VISUAL_SUMMARY`
- `CODEGEMMA_MICRO_PATCH`
- `FIREWORKS_TEXT_REASONER`
- `OPENHANDS_SANDBOX`

The scorecard records whether a route would require vision, network, or
secrets, but it never performs external calls.

## Metrics and Benchmarks

Measured during the MVP verification run from this checkout:

| Check | Result |
|-------|--------|
| Real CODEMAP topology load | `600` nodes and `1,225` links loaded from `.aura/CODEMAP.json` in `334.382 ms`. |
| Offline demo topology | `5` nodes and `4` links loaded in `2.563 ms`, including one intentional missing-route edge. |
| Capsule compiler | Demo router selection compiled to a complete `1,163` token emitted capsule in `2.529 ms`. |
| Compact context nucleus | Embedded selected-node context estimated at `358` tokens from a `50,000` token raw demo baseline, a `99.3%` reduction. |
| Complete worker capsule savings | Full capsule including constraints, faults, token costs, and route scorecard saves `97.6%` against the raw demo baseline. |
| Route scorecard | Simulated route selection completed in `0.039 ms`, selected `LOCAL_DETERMINISTIC`, and recorded `network_calls_made=false`. |
| Browser render smoke | Desktop screenshot rendered a nonblank Canvas/side-panel UI with `1,278` sampled colors. |
| Mobile layout smoke | `390x844` viewport stacked canvas and panel, kept selected node JSON visible, and had no horizontal overflow. |
| Tests | `python -m pytest tests -q` passed `61` tests in `1.98 s`; focused arena and related topology subset passed `38` tests in `2.04 s`. |

The full repository-level `python -m pytest -q` command is currently blocked
before collection by the pre-existing root `test_syntax_fixes.py` import-time
`sys.exit(0)`. The maintained `tests/` package and focused arena/topology tests
pass.

## Research Notes

- `3d-force-graph` and `react-force-graph` are strong WebGL choices, but this
  repo's `.aura/SECURITY.md` forbids new dependencies in this packet. The MVP
  therefore uses a dependency-free Canvas 3D projection, while keeping the API
  compatible with future Three.js/force-graph rendering.
- RepoGraph and AutoCodeRover reinforce that graph structure should guide
  localization, not replace exact text. The capsule keeps file/symbol/line facts
  explicit.
- RepoRepair shows that hierarchical function/file context helps repository
  repair, so the micro-arena defaults to depth 1 and optionally expands to depth
  2 instead of dumping full graph JSON.
- SWE-Doctor motivates candidate fault records before patching, so the MVP flags
  missing tests, missing callers, high fan-in/fan-out, stale files, and token
  budget pressure.
- SWE-Skills-Bench warns that blindly injecting skills can waste tokens, so the
  scorecard exposes route fit and blockers instead of auto-sending to a worker.
- Recent visual-repository-agent work reports that vision-only repository
  understanding degrades accuracy and cost; this MVP treats visualization as a
  supplement to exact topology text.
- Gemma 3n, SmolVLM2, and Qwen2.5-VL are plausible future local/low-cost visual
  summary routes. They remain deferred because exact local topology is enough
  for the MVP and no model should infer identifiers from pixels.

## Next Upgrade

Replace the Canvas renderer with a `3d-force-graph`/Three.js frontend only if a
future packet explicitly allows the dependency or vendored asset. Keep the
capsule API unchanged so the renderer remains replaceable.
