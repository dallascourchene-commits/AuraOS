# AuraOS Master Exhaustive Benchmark Scorecard

**Work order:** `WO-UNIVERSAL-GLOBAL-BENCHMARK-DAEMON-EXHAUSTIVE`  
**Coordinate:** `AD:DAEMON:GLOBAL-EXHAUSTIVE-BENCHMARK:UNIVERSAL`  
**Signed-trigger source commit:** `fa8fed2a2c1644911125d473f93dc2390a062722`  
**Generated UTC:** `2026-08-15T04:14:46.618495Z`  
**Overall disposition:** `PARTIAL / EXTERNAL_ENVIRONMENT_BLOCKED / L0_COMPRESSION_UNVERIFIED`

> This scorecard does not turn environment preflight into benchmark scores. Official benchmark results are recorded only when their benchmark-specific datasets, runtimes, services, model adapters, and graders actually execute. `SOURCE_RESOLVED_ENV_BLOCKED` is not a benchmark failure and is not a zero score; it means no valid score can be minted on this host.

## Executive result

- Signed filesystem trigger: **PASS** — Ed25519 signature verified against a preconfigured trusted public key; trigger was atomically leased and processed.
- Tamper test: **PASS** — modified payload with the original signature was rejected with `InvalidSignature`.
- Worker pool: **21 taxonomy entries dispatched across J01–J21 of the J01–J25 pool**; four slots remained available.
- Official external benchmark scores minted: **0**. All 21 requested benchmark families require environment/assets/model adapters not provisioned on this execution host.
- UDP gossip proxy: **PASS** for localhost loopback RTT — median **27.641 µs**, p95 **29.484 µs**, p99 **59.248 µs** over 5,000 round trips. This is not a remote-mesh latency claim.
- Core Aura worker RSS: **PASS** — **14.828 MiB** peak RSS under system Python, versus the `<95 MiB` gate. System-Python baseline was **8.195 MiB**.
- Benchmark-controller RSS: **FAIL as a controller profile** — **116.934 MiB** in the heavier pyvenv runtime. It is reported separately and not substituted for the core substrate measurement.
- L0 symbolic-tensor compression ≥94%: **UNVERIFIED / SOURCE GAP** — no source-bound executable L0 tensor compressor was found in the bound/current searchable repository surfaces; generic JSON/zlib compression was deliberately not substituted.

## External benchmark taxonomy

| Category | Benchmark | Worker | Disposition | Local blocker |
| :--- | :--- | :---: | :--- | :--- |
| Coding & Software Engineering | Aider Polyglot | J05 | **SOURCE_RESOLVED_ENV_BLOCKED** | aider, benchmark_harness, model_adapter |
| Coding & Software Engineering | BigCodeBench | J03 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Coding & Software Engineering | LiveCodeBench | J04 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Coding & Software Engineering | SWE-bench Pro | J02 | **SOURCE_RESOLVED_ACCESS_PARTIAL_ENV_BLOCKED** | docker, benchmark_harness, model_adapter; Public portion exists; held-out/commercial portions are not fully public; Docker/harness/model adapter absent. |
| Coding & Software Engineering | SWE-bench Verified | J01 | **SOURCE_RESOLVED_ENV_BLOCKED** | docker, benchmark_harness, model_adapter |
| Computer & OS Use | AgentBench (OS/DB/Web) | J08 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, interactive_services, model_adapter |
| Computer & OS Use | AndroidWorld | J09 | **SOURCE_RESOLVED_ENV_BLOCKED** | adb, android_emulator, benchmark_harness, model_adapter |
| Computer & OS Use | OSWorld | J07 | **SOURCE_RESOLVED_ENV_BLOCKED** | desktop_vm_or_docker, benchmark_harness, model_adapter |
| Computer & OS Use | Terminal-Bench 2.0 | J06 | **SOURCE_RESOLVED_ENV_BLOCKED** | docker, benchmark_harness, model_adapter |
| Memory & Context | LoCoMo | J20 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Memory & Context | LongMemEval | J21 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Reasoning & Architecture Constraints | APEX-Agents | J19 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, professional_workflow_env, model_adapter |
| Reasoning & Architecture Constraints | ARC-AGI-2 | J17 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Reasoning & Architecture Constraints | ARC-AGI-3 | J18 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, interactive_arc_env, model_adapter |
| Tool Calling & Protocol Efficiency | BFCL v4 | J10 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, dataset, model_adapter |
| Tool Calling & Protocol Efficiency | MCP-Atlas / Tool Use | J12 | **SOURCE_RESOLVED_ACCESS_PARTIAL_ENV_BLOCKED** | benchmark_harness, mcp_servers, model_adapter; Published benchmark describes a containerized harness and public subset; full local MCP server harness is absent. |
| Tool Calling & Protocol Efficiency | Toolathlon | J11 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, tool_services, model_adapter |
| Web Navigation & Multi-Step Tasks | BrowseComp | J16 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, browsing_agent, model_adapter |
| Web Navigation & Multi-Step Tasks | GAIA | J13 | **SOURCE_RESOLVED_ACCESS_GATED_ENV_BLOCKED** | benchmark_harness, dataset_or_gated_assets, browser_or_tools, model_adapter; Official dataset requires accepting access conditions; local dataset/model/tool stack absent. |
| Web Navigation & Multi-Step Tasks | WebArena / WebArena Verified | J14 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, webarena_services, model_adapter |
| Web Navigation & Multi-Step Tasks | τ²-Bench | J15 | **SOURCE_RESOLVED_ENV_BLOCKED** | benchmark_harness, domain_simulator, model_adapter |

### Interpretation

The requested taxonomy is fully enumerated and source-reviewed, but this runtime lacks Docker/Podman, Android emulator/ADB, VM tooling, benchmark datasets, benchmark-specific harness installations, and model-provider credentials. Playwright and `uv` are present, but those alone are insufficient to run WebArena/τ²-Bench or the other official suites. Therefore no pass rate, accuracy, resolve rate, or leaderboard percentile is asserted for those suites.

## Substrate validation

| Gate | Fresh measurement | Result | Boundary |
| :--- | :--- | :---: | :--- |
| UDP gossip latency `<500 µs` | localhost RTT p95 `29.484 µs` | **PASS (loopback only)** | Not WAN/remote P2P |
| Core worker peak RSS `<95 MiB` | `14.828 MiB` (`/usr/bin/python3`) | **PASS** | Exact current stdlib worker daemon; host measurement |
| Benchmark controller peak RSS `<95 MiB` | `116.934 MiB` (pyvenv) | **FAIL** | Orchestration/control process, not core substrate |
| L0 symbolic tensor payload reduction `>=94%` | no executable compressor found | **UNVERIFIED** | Source gap; no synthetic substitute |

## Existing repository-defined validation evidence

The current repository generation also contains `aura_workspace/outbox/WO-FLEET-AUTONOMOUS-EXECUTE.industry-validation.json`, reporting **15/15 repository-defined gates PASS** from an earlier source-bound run. That evidence covers internal FST/Merkle/SQLite/UDP/fleet/lease behavior; it is retained as inherited evidence and is **not** presented as execution of SWE-bench, OSWorld, BFCL, WebArena, ARC, or the other external benchmarks.

## Signed-trigger daemon behavior

The added `scripts/aura_global_benchmark_daemon.py` supports continuous host polling or bounded `--once` execution. It verifies Ed25519 signatures using a separately configured trusted public key, atomically moves a trigger into a lease filename before execution, dispatches the taxonomy across a 25-worker pool, writes canonical telemetry, and rejects altered signatures. The private signing key used for this validation is ephemeral and is not committed.

**Important runtime boundary:** this ChatGPT execution cannot remain alive as a persistent background process after the response. The daemon implementation is suitable for a persistent external host, but this validation exercised it in bounded `--once` mode and terminated it cleanly.

## Primary-source review anchors

- SWE-bench evaluation requires its benchmark harness and containerized execution; SWE-bench Verified is an official dataset variant.
- OSWorld requires a provisioned desktop/VM or supported sandbox provider; AndroidWorld requires an Android emulator.
- BFCL v4 includes agentic categories and uses its own generation/evaluation harness.
- WebArena/WebArena Verified require a browser benchmark environment; τ²-Bench uses its domain simulator and model/provider configuration.
- GAIA validation/test access is gated; ARC-AGI-2 publishes public task data; APEX-Agents uses realistic cross-application worlds; MCP-Atlas publishes an MCP-server/tool benchmark with a public subset.
- BigCodeBench, LiveCodeBench, Aider Polyglot, Terminal-Bench, AgentBench, Toolathlon, BrowseComp, LoCoMo, and LongMemEval remain benchmark-specific evaluation surfaces and are not approximated by Aura internal microbenchmarks.

## Artifact integrity

- Telemetry SHA-256: `54a33de49810962bea7eb75450bd06b7a247144653c6180599e4be6e8964c3ae`
- Daemon SHA-256: `f952dbd2b5924a94c178d686e972453975979ad0e4aea7f838295ecb0016728d`
- Final execution receipt is Ed25519-signed; its embedded public key proves integrity under that ephemeral execution key, not human/organization identity.
