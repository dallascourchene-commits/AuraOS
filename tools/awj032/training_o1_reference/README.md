# AWJ032 AirLLM Training O1 — D0 Reference

This cone binds the 2026-09 AirLLM streamed-LoRA training generation to exact source and adapter identity without authorizing model execution.

## Current-source discriminator

Pinned upstream: `lyogavin/airllm@55e435087d951da8c25ab3672e969025241a398e`.

The exact family identifiers admitted by this reference are:

- `qwen3_5` → `AirLLMLoRA(AirLLMQwen3_5)`;
- `qwen3_8_dense` → the same `AirLLMLoRA(AirLLMQwen3_5)` source route;
- `qwen4_exp` → `AirLLMLoRAQwen4Exp(AirLLMQwen4Exp)`.

Upstream descriptions may use names such as Flash-Next around the Qwen4Exp route, but this reference does **not** treat those descriptions as additional accepted family identifiers. A new alias requires an explicit source-bound mapping and reproof.

No GLM-specific streamed trainer exists in the pinned source generation. Therefore `AIRLLM_TRAINING_ADVERTISED != GLM_TRAINING_SUPPORTED`; GLM-5.3 remains `HOLD_PORT_REQUIRED` until a separately proven GLM training port exists. This does not block the existing GLM inference/profile lane.

## Adapter identity law

The pinned raw adapter loader iterates provided state keys and reports keys not found in the model, but does not prove that every expected LoRA parameter is present in the supplied state. The raw saved state also does not carry the Aura base-checkpoint/runtime/tokenizer provenance envelope required by this reference.

This cone therefore requires exact adapter key-set equality plus exact base checkpoint, base config, tokenizer, runtime, AirLLM commit, model-family/trainer, target topology, LoRA rank/alpha/packed-expert identity, and adapter value roots. O4 additionally carries the signed manifest preimage through R1 and O2 so downstream family/base/config/tokenizer/value identity cannot be laundered behind an opaque adapter root.

A mismatch is a HOLD/rebind condition, never authority to guess a compatible base.

## Reproduction

From the **repository root** run:

```bash
python -m unittest -q tools.awj032.training_o1_reference.test_training_admission
```

The pinned upstream-fixture audit is one fixture-dependent test. When `.awj032_airllm_upstream_fixture` is not provisioned, only that test is skipped; the remaining O1 tests still execute. O4's published-head receipt records the current cross-cone clean-environment proof.

## Authority ceiling

D0/nonpromoting only. The validator may read/hash the **provided adapter byte values** supplied as evidence in order to compare them with manifest roots. That bounded evidence read is not model execution and is not checkpoint/model tensor materialization. No model training or generation, model/checkpoint tensor-payload read, checkpoint split/delete/copy/move, provider spend, main merge, deploy, or Gate-10 promotion is authorized by this reference.

Current post-review proof: `artifacts/arena/awj032_airllm_training_o4/PROOF_RECEIPT_O4_PUBLISHED.json`.
