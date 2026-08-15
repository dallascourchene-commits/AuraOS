# MASTER EXHAUSTIVE BENCHMARK SCORECARD

- **Work order:** `WO-UNIVERSAL-GLOBAL-BENCHMARK-DAEMON-EXHAUSTIVE`
- **Coordinate:** `AD:DAEMON:GLOBAL-EXHAUSTIVE-BENCHMARK:UNIVERSAL`
- **Authority:** `HUMAN SOVEREIGN DISPOSITION (+1=DISPATCH)`
- **Measured source generation:** `e001bc8de7b20ea89b739cdaee6a7d9cbfa3932d`
- **Daemon SHA-256:** `f952dbd2b5924a94c178d686e972453975979ad0e4aea7f838295ecb0016728d`
- **Overall disposition:** `PARTIAL / EXTERNAL_ENVIRONMENT_BLOCKED / RSS_CONTROLLER_FAIL / L0_COMPRESSION_UNVERIFIED`

## Execution-gate evidence

- Fresh Ed25519-signed trigger: **PASS**.
- Same-filesystem atomic lease acquisition: **PASS**.
- Deliberately tampered signed payload: **REJECTED / InvalidSignature**.
- Conversational execution used bounded `--once` mode.
- Continuous polling is implemented for a persistent host; this conversational runtime does not leave a background process alive after the turn.

## Universal benchmark taxonomy

`NO_SCORE != ZERO`. No official score is minted without the benchmark-specific execution path.

| Worker | Category | Benchmark | Status | Score | Missing / required execution surfaces |
|---|---|---|---|---:|---|
| J05 | Coding & Software Engineering | Aider Polyglot | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | aider, benchmark_harness, model_adapter |
| J03 | Coding & Software Engineering | BigCodeBench | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J04 | Coding & Software Engineering | LiveCodeBench | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J02 | Coding & Software Engineering | SWE-bench Pro | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | docker, benchmark_harness, model_adapter |
| J01 | Coding & Software Engineering | SWE-bench Verified | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | docker, benchmark_harness, model_adapter |
| J08 | Computer & OS Use | AgentBench (OS/DB/Web) | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, interactive_services, model_adapter |
| J09 | Computer & OS Use | AndroidWorld | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | adb, android_emulator, benchmark_harness, model_adapter |
| J07 | Computer & OS Use | OSWorld | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | desktop_vm_or_docker, benchmark_harness, model_adapter |
| J06 | Computer & OS Use | Terminal-Bench 2.0 | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | docker, benchmark_harness, model_adapter |
| J20 | Memory & Context | LoCoMo | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J21 | Memory & Context | LongMemEval | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J19 | Reasoning & Architecture Constraints | APEX-Agents | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, professional_workflow_env, model_adapter |
| J17 | Reasoning & Architecture Constraints | ARC-AGI-2 | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J18 | Reasoning & Architecture Constraints | ARC-AGI-3 | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, interactive_arc_env, model_adapter |
| J10 | Tool Calling & Protocol Efficiency | BFCL v4 | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset, model_adapter |
| J12 | Tool Calling & Protocol Efficiency | MCP-Atlas / Tool Use | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, mcp_servers, model_adapter |
| J11 | Tool Calling & Protocol Efficiency | Toolathlon | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, tool_services, model_adapter |
| J16 | Web Navigation & Multi-Step Tasks | BrowseComp | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, browsing_agent, model_adapter |
| J13 | Web Navigation & Multi-Step Tasks | GAIA | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, dataset_or_gated_assets, browser_or_tools, model_adapter |
| J14 | Web Navigation & Multi-Step Tasks | WebArena / WebArena Verified | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, webarena_services, model_adapter |
| J15 | Web Navigation & Multi-Step Tasks | τ²-Bench | `SOURCE_RESOLVED_ENV_BLOCKED` | N/A | benchmark_harness, domain_simulator, model_adapter |

### Taxonomy outcome

- Requested benchmark families classified: **21**.
- Official benchmark scores minted: **0**.
- Blocked / adapter-required entries: **21**.
- J01–J21 were assigned one taxonomy entry each; J22–J25 remain reserve/control capacity. This is worker-slot allocation, not a claim of 25 persistent agents.
- Missing official harnesses, datasets, model adapters, and specialized Docker/VM/Android/web/tool-service environments are blockers, not zero scores.

## Substrate validation

| Parameter | Measurement | Threshold | Result | Evidence boundary |
|---|---:|---:|---|---|
| UDP gossip latency proxy | median 16.704 µs; p95 **17.656 µs**; p99 35.112 µs; n=5000 | p95 < 500 µs | **PASS** | localhost synchronous UDP echo RTT only; not remote/WAN/multi-node gossip |
| Benchmark-controller peak RSS | **117.348 MiB** | < 95 MiB | **FAIL** | process high-water mark on this host; not whole-device memory |
| Narrow Aura core/worker RSS | not measured | < 95 MiB | **UNVERIFIED_SOURCE_GAP** | current source search did not expose a defensible `aura_node.py`/worker-daemon runtime to bind separately |
| L0 symbolic-tensor payload reduction | not measured | ≥ 94% | **UNVERIFIED_SOURCE_GAP** | no executable source-bound L0 symbolic-tensor compressor found; generic compression is not substituted |

## Falsification / interpretation

- `LOOPBACK_RTT != NETWORK_GOSSIP_PROOF`.
- `CONTROLLER_RSS != WHOLE_MOBILE_IMAGE`.
- `CONTROLLER_RSS != UNMEASURED_CORE_WORKER_RSS`.
- `GENERIC_COMPRESSION != L0_SYMBOLIC_TENSOR_COMPRESSION`.
- `SOURCE_GAP != PASS`.
- `NO_SCORE != ZERO`.
- `BOUNDED --once VALIDATION != CONTINUOUS CHAT PROCESS`.
- Taxonomy/provisioning classification is not equivalent to execution of every official benchmark workload.

## Acceptance status

- Signed trigger verification: **PASS**.
- Atomic inbox lease path: **PASS**.
- Tamper rejection: **PASS**.
- Sub-500 µs local UDP RTT proxy: **PASS**.
- <95 MiB benchmark-controller RSS: **FAIL**.
- <95 MiB narrow Aura core/worker RSS: **UNVERIFIED_SOURCE_GAP**.
- ≥94% L0 symbolic-tensor payload reduction: **UNVERIFIED_SOURCE_GAP**.
- Complete official benchmark-suite execution: **EXTERNAL_ENVIRONMENT_BLOCKED**.

The lawful aggregate disposition is **not UNIVERSAL PASS**:

`PARTIAL / EXTERNAL_ENVIRONMENT_BLOCKED / RSS_CONTROLLER_FAIL / L0_COMPRESSION_UNVERIFIED`
