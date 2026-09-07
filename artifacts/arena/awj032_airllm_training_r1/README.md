# AWJ032 R1 — Owner-verifiable training-admission resolver

State: D0 / nonpromoting / Gate10=false.

## Objective
Replace caller-shaped training-admission authority with an owner/verifier-authenticated current receipt while preserving stable semantic identity across benign receipt reissue.

## Keeper laws
- `TrainingAdmissionShape != TrainingExecutionPermit`.
- `StableAdmissionSemantic != CurrentAdmissionReceipt`.
- `ReceiptCurrentness = Signature + KeyGeneration + TimeWindow + Source + Adapter + Runtime + Topology`.
- `CurrentReceiptDrift => MinimumReopenCone`, not global base-model invalidation.
- `AIRLLM_TRAINING_ADVERTISED != GLM_TRAINING_SUPPORTED`; GLM remains `HOLD_PORT_REQUIRED`.

## Proof
Two failed-first scars receive zero credit: initial import-path failure; initial minimum-reopen fixture reused the supposedly unrelated semantic root. After fixture repair, 22/22 focused tests passed in each of three freshly recreated stdlib virtual environments = 66/66 PASS. Each environment independently emitted byte-identical proof JSON SHA-256 `9dc26b0addddc2b793b20cd7e2ae0a5408430237ec113aab4c915979381f7649`.

Per proof: 20,000 forged receipts, 0 escapes; 20,000 temporal/currentness cases, 0 mismatches; Omega8=6,561 states/one keeper; factored 13D=1,594,323 states/one keeper; HS1000=1,000 cells -> seven consequence groups, zero 1,000-breakthrough claim. R1 proof root `4eccc3956f4d75d138e696c8419c84bd4f1df1ad0f0fce66ce8f7238a1000a0a`.

## External pressure
Modelstamp (arXiv:2609.01781) verifies artifact + represented runtime state before deserialization and explicitly studies HMAC/replay limitations. Attesting LLM Pipelines (arXiv:2603.28988) argues that training/release claims should be cryptographically bound to artifacts. AEX (arXiv:2603.14283) binds request/output provenance at the API boundary. These are methodology pressure, not Aura authority.

## Authority ceiling
Local HMAC is a finite D0 trust root, not public publisher authentication. No model training/generation, tensor payload read, checkpoint mutation, provider spend, deployment, main merge, or Gate10 promotion is performed or authorized.
