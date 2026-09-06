# Generation-bound canonical-JSON AirLLM isolation

Rebase parents:
- AGENT_01 O19: `HistoricalAdmission AND ValidReceiptSyntax != CurrentAdmission`.
- AGENT_14 O5: local semantic proof and external authentication are distinct, noncompensatory evidence planes.

Keeper:
`CurrentGenerationBinding + DifferentProcessOwnership + ExactCapabilitySet + CanonicalJSONRuntimeIPC + FailurePoisoning -> D0 IsolationEligibility`.

This is a stricter optional layer over the process-isolation direction in PR #844. It keeps the wrapper/model lifetime in a spawned child, binds currentness to the exact security subject generation, semantic-admission surface, model identity, wrapper identity, transport schema, and capability set, and permits only `status` plus `generate_json` across the runtime message plane.

Runtime messages use canonical JSON over `Connection.send_bytes/recv_bytes`; arbitrary Python result objects are not deserialized in the parent. Tensor-like child results may cross only after `.tolist()` normalization to JSON. Non-JSON results, worker exceptions, timeouts, or malformed receipts poison the proxy and require a new object.

The default real wrapper symbol is package-stable: `auraos.security.airllm_native_compat_wrapper.ManifestPinnedNativeAirLLMWrapper`.

Limit: Python `multiprocessing` still bootstraps the trusted child process from parent-controlled arguments. This is not an OS privilege sandbox. Real AirLLM/Transformers execution and model-specific JSON input adaptation remain a separate evidence plane.

Authority ceiling: D0 only; no provider truth, model performance, deployment, merge authority, effect authority, native/private KV access, or Gate10.
