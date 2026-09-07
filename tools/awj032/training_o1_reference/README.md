# AWJ032 AirLLM Training O1 — D0 Reference

This cone binds the 2026-09 AirLLM streamed-LoRA training generation to exact source and adapter identity without authorizing model execution.

## Current-source discriminator

Pinned upstream: `lyogavin/airllm@55e435087d951da8c25ab3672e969025241a398e`.

The pinned `airllm_lora.py` implements streamed trainers for Qwen-specific families:

- `AirLLMLoRA(AirLLMQwen3_5)` for Qwen3.5/Qwen3.8 dense text training;
- `AirLLMLoRAQwen4Exp(AirLLMQwen4Exp)` for Qwen3.8 Flash-Next / Qwen4Exp.

No GLM-specific streamed trainer exists in that source generation. Therefore:

`AIRLLM_TRAINING_ADVERTISED != GLM_TRAINING_SUPPORTED`

GLM-5.3 is `HOLD_PORT_REQUIRED` until a separately proven GLM training port exists. This does not block the existing GLM inference/profile lane.

## Adapter identity law

The pinned raw adapter loader iterates provided state keys and reports keys not found in the model, but does not prove that every expected LoRA parameter is present in the supplied state. The raw saved state also does not carry the Aura base-checkpoint/runtime/tokenizer provenance envelope required by this reference.

This cone therefore requires:

- exact adapter key-set equality, not subset loading;
- exact base checkpoint root;
- exact base config root;
- exact tokenizer root;
- exact runtime root;
- exact AirLLM commit;
- exact model-family trainer identity;
- exact target-module topology;
- LoRA rank/alpha/packed-expert identity;
- exact adapter value roots.

A mismatch is a HOLD/rebind condition, never authority to guess a compatible base.

## Reproduction

Clone the pinned AirLLM commit into repository root as `.awj032_airllm_upstream_fixture`, then run from this directory:

```bash
python -m unittest -q test_training_admission
```

The committed proof receipt records three clean-environment local reference runs and a second three-environment reproof of the published source bytes.

## Authority ceiling

D0/nonpromoting only. No training, generation, tensor-payload read, checkpoint split/delete/copy/move, provider spend, main merge, deploy, or Gate-10 promotion is authorized by this reference.
