# Aura Crucible — AMD Hackathon Act II Track 3 Demo

## What this adds

Aura now has a runnable Track 3 demo layer that turns small, bounded coding tasks into verified reusable training records called **crystals**.

The main path is intentionally easy to find:

```text
aura_amd_track3_cli.py
  -> aura_amd_track3_worker.py
  -> detached repository copy
  -> argv-only verifier command
  -> .aura/runtime/amd_track3/verified_crystals.jsonl
  -> aura_amd_track3_train.py
  -> Gemma LoRA adapter checkpoint
```

This layer surrounds Phase C3. It does not weaken C3's proposal-only authority and never commits, pushes, or merges generated code.

## Why AMD is meaningful

On the hackathon notebook, the AMD GPU is used for two bounded workloads:

1. **Gemma coding inference** through a local OpenAI-compatible endpoint such as vLLM/ROCm, or through an approved Fireworks endpoint.
2. **Background LoRA crystallization** with the ROCm-compatible PyTorch build already provided by the AMD notebook image.

The worker and trainer are separated so inference and adapter training can be scheduled independently without changing the verified crystal format.

## Fast public demo

The public container uses a deterministic fixture provider. It downloads no model, requires no secret, creates three verified crystals, and exposes status on port 8080.

```bash
docker build -f Dockerfile.amd-track3 -t aura-track3:demo .
docker run --rm -p 8080:8080 aura-track3:demo
curl http://127.0.0.1:8080/
```

The returned JSON identifies the Track 3 path, AMD backend label, crystal count, latest crystal, and preserved C3 authority.

## AMD notebook launch

```bash
git clone https://github.com/dallascourchene-commits/AuraOS.git
cd AuraOS
python -m pip install -r requirements-amd-track3.txt
```

Use the ROCm-compatible `torch` package already installed in the notebook. Do not replace it with a CUDA wheel.

### Option A — local Gemma endpoint

Start the notebook's existing Gemma server, then run:

```bash
export AURA_AMD_BACKEND="AMD ROCm notebook"
export AURA_TRACK3_ENDPOINT="http://127.0.0.1:8000/v1"
export AURA_TRACK3_MODEL="google/gemma-3-4b-it"
python aura_amd_track3_cli.py run-loop \
  --provider openai-compatible \
  --interval-seconds 60
```

For a stable demo, use the Gemma checkpoint already downloaded on the notebook. Gemma 3 4B is the conservative fallback; Gemma 3 12B is appropriate when it is already present and confirmed to fit.

### Option B — approved Fireworks endpoint

```bash
export AURA_TRACK3_ENDPOINT="https://api.fireworks.ai/inference/v1"
export AURA_TRACK3_MODEL="<approved-model-id>"
export AURA_TRACK3_API_KEY="<secret>"
python aura_amd_track3_cli.py run-loop --provider openai-compatible
```

No API key is required by the public container. External services are optional and explicitly configured through environment variables.

## Background adapter training

After at least three verified crystals exist:

```bash
python aura_amd_track3_train.py \
  --model "$AURA_TRACK3_MODEL" \
  --crystals .aura/runtime/amd_track3/verified_crystals.jsonl \
  --output-dir .aura/runtime/amd_track3/adapters
```

The trainer:

- accepts only `training_eligible=true` records with return code zero;
- trains a PEFT LoRA adapter rather than rewriting the base model;
- uses BF16 on the visible AMD GPU;
- supports checkpoint continuation;
- saves an `aura_training_manifest.json` beside each adapter.

## Safety and reliability boundaries

- Tasks declare exact `allowed_files`.
- Proposals containing any other path fail closed.
- Work occurs in a detached temporary repository copy.
- Verifiers are argv arrays, not shell command strings.
- Only passing attempts become crystals.
- The source checkout remains unchanged.
- No generated commit, push, pull request, review request, or merge occurs.
- Phase C3 remains the proposal and human-review authority boundary.

## Track 3 self-check

- **Clear AMD usage:** documented ROCm inference and BF16 LoRA training.
- **Clear README:** this file gives architecture, setup, run commands, and external-service variables.
- **Runnable project:** deterministic container mode requires no model or secret.
- **Original work:** verified experiences are transformed into Aura Agent-IR-compatible reusable crystals.
- **Easy implementation path:** four root modules, one task manifest, one JSONL ledger.
- **Complete outputs:** every declared task returns a success or failure record; no silent skipping.
- **Runtime discipline:** public container performs no runtime model download.

## Demo narrative

1. Show `status` with zero or existing crystals.
2. Start `run-loop` against Gemma on the AMD notebook.
3. Show a small task, the bounded file allowlist, and the verifier command.
4. Show the detached attempt and passing test evidence.
5. Show the new JSONL crystal and unchanged source checkout.
6. Start or show the LoRA trainer reading only verified crystals.
7. Show the adapter manifest and explain that future Aura coding tasks can load the latest accepted adapter.
