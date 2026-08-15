# AuraOS Security and Accuracy Scorecard

- **AuraOS parent:** `607de4e8fe7c529da55406a2f3973d41ed63fa9d`
- **InjecAgent source:** `f19c9f2c79a41046eb13c03c51a24c567a8ffa07`
- **Legacy τ-bench source:** `59a200c6d575d595120f1cb70fea53cef0632f6b`
- **Pinned fixture SHA-256:** `73a7240bfa11e72dbd0a35ad603c5efb5b33f4ca42fcda4275cb308da27adef4`
- **Worker execution:** W1–W7 concurrent deterministic lanes; not seven independent LLMs.

## InjecAgent-derived security gate

The pinned official attacker catalog contains **62 cases** (30 direct-harm + 32 data-stealing). The harness evaluates each source-bound attacker identity in both base and enhanced forms: **124 payload identities × 7 lanes = 868 gate trials**.

- Attack transitions reaching executable state: **0 / 868**
- **L0/FST gate-layer ASR: 0.0000%**
- Required 0% ASR on the executed gate surface: **PASS**
- Official InjecAgent end-to-end ASR-valid / ASR-all across 1,054 synthesized agent episodes: **NOT MEASURED**

The L0 tensor is an explicit deterministic security feature vector, not a transformer-internal tensor. The first hard gate is provenance: external tool data is data, not authority. External content that requests tool effects cannot become an executable action, regardless of lexical phrasing. Enhanced attack identity is separately represented in the tensor.

## Legacy τ-bench trajectory preservation

A bounded exact-source sample of **6 oracle tasks** (3 airline + 3 retail) is replayed across seven lanes: **42 task-lane trials / 203 expected action transitions**.

- Exact oracle-action canonical preservation through the authority/grammar gate: **42 / 42 = 100.00%**
- Malformed tool-name perturbations rejected: **42 / 42 tasks**
- Same trajectories presented as untrusted external data rejected: **42 / 42 tasks**
- Official τ-bench pass^k / conversational-agent score: **NOT MEASURED**

The original τ-bench repository now warns its airline/retail tasks are outdated and points to τ³-bench; this is a compatibility audit against the pinned legacy revision, not a current benchmark claim.

## Fleet invariants

- W1–W7 completed: **7 / 7**
- Benign/authority controls: **28 / 28**
- External data never mints authority: **PASS**
- Source/authority hard gate precedes execution: **PASS**
- FST tool grammar rejects malformed action names: **PASS**

## Negative space

- The 0% result is **gate-layer ASR**, not end-to-end LLM/agent ASR.
- The 62 attacker cases are source identities used to synthesize the official 1,054 episodes; this run does not claim 1,054 full episode executions.
- No official InjecAgent ASR-valid/ASR-all was computed.
- No official τ-bench pass^k was computed.
- W1–W7 are concurrent lanes over one deterministic harness, not independent model-family replications.

## Artifact integrity

Results SHA-256: `e68fce56304757a98870189cbd3c68c9b78ca3e6df9856d8da72282c59c550d6`
The receipt is Ed25519-signed with an ephemeral execution key. Its signature authenticates artifact integrity only; it does not establish human identity, promotion authority, or repository ownership.
