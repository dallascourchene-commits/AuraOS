# Process-Global Patch Isolation Membrane — blocker prototype

## Objective

Close the unresolved AirLLM/Transformers P2 at the architectural boundary: a lock can serialize Aura callers but cannot stop unrelated threads from observing process-global monkey patches.

Keeper law:

`RegisteredModulePatch -> DedicatedProcess OR HOLD`.

`PrivateUnregisteredModule -> LocalSyntheticTestingOnly`.

`DedicatedProcessState != ProviderTruth != ModelExecutionProof != EffectAuthority`.

## Design

`require_patch_isolation(module)` classifies a module object by actual process registration. An unregistered synthetic module is a private object graph and may be patched for unit tests. A module present in `sys.modules` is process-global and fails closed unless execution is inside the private worker context created by `DedicatedProcessService`.

`DedicatedProcessService` uses the multiprocessing `spawn` context. It keeps resident state in the child process and exposes bounded method-name RPC over a private Pipe. This matters for AirLLM because a loaded model may not be serializable; the correct boundary is to keep the model resident in the worker and send operations/results, not to load under a global patch and return the live model to the parent.

The service rejects private method names, unserializable requests, dead workers, malformed start receipts, and same-PID receipts.

## Integration consequence

PR #835 can adopt this primitive by refusing the current process-global membrane when the real imported Transformers module is registered in the main process, and by moving native-compat load plus model operations into a dedicated service process. This prototype does not mutate AGENT_01 owner files and does not claim the upstream P2 is closed until that integration occurs.

## Authority ceiling

D0 process-isolation/control-plane proof only. No OS sandbox, provider truth, actual AirLLM/model execution, performance, deployment, merge authority, truth/effect authority, or Gate10.
