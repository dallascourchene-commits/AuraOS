# AWJ032 O1 — AirLLM Streamed Training Admission

State: **D0 / nonpromoting / Gate10=false**.

This artifact records a current-source wake from AirLLM's September 2026 streamed-LoRA training support and converts it into an Aura fail-closed source/adapter admission boundary.

Material consequences:

1. Current streamed training is Qwen-specific in source (`AirLLMLoRA -> AirLLMQwen3_5`, `AirLLMLoRAQwen4Exp -> AirLLMQwen4Exp`).
2. GLM-5.3 is not admitted by that source generation and remains `HOLD_PORT_REQUIRED` for training; existing GLM inference/profile work is unaffected.
3. Adapter state must provide the exact expected LoRA key set; partial state is a HOLD.
4. Adapter identity binds base checkpoint, config, tokenizer, runtime, AirLLM commit, family/trainer, target topology, LoRA hyperparameters, packed-expert mode, keys and adapter value roots.
5. Search-scale proof is pressure only: the 1,000 frozen cells quotient to six consequence groups.

The proof receipt and exact-source hashes are in this directory.
