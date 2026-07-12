# Aura Sovereign Learning Arena — AMD Hackathon Act II Track 3

## One-command inspection demo

```bash
docker compose -f docker-compose.track3.yml up --build
```

Open `http://127.0.0.1:8080`.

The default container uses a deterministic fixture worker, so judges need no model download, API key, or AMD notebook access. It executes two related coding tasks, verifies both in detached copies, creates two crystals, and shows the second task reusing the first verified procedure.

## What the demo proves

```text
human objective
  -> DIR -> ASP -> CLASS -> SUBJ -> VOICE -> STEM
  -> guarded WFST admission
  -> bounded Coding Arena
  -> replaceable worker
  -> detached verifier
  -> verified crystal
  -> reusable procedure
```

The browser dashboard shows:

- polysynthetic intent compilation;
- hard-guarded WFST admission and blocked actions;
- exact Arena file and verifier boundaries;
- fixture, local Ollama, or AMD/Gemma worker identity;
- passing verification and sandbox dissolution;
- verified crystal creation and reuse;
- the Anishinaabemowin tutor's sovereign-knowledge response contract;
- the preserved AMD ROCm and Gemma/LoRA path.

## Live local Ollama mode

Dallas's Windows laptop already has the 3B coding model installed. Ollama runs natively on Windows and serves its API at `http://localhost:11434`.

### Native PowerShell run

```powershell
ollama list

python aura_amd_track3_cli.py `
  --crystals .aura/runtime/amd_track3/verified_crystals.jsonl `
  demo-sequence `
  --provider ollama `
  --endpoint http://127.0.0.1:11434 `
  --model qwen2.5-coder:3b `
  --reset-demo

python aura_amd_track3_cli.py serve --host 127.0.0.1 --port 8080
```

### Container connected to Windows Ollama

```powershell
$env:AURA_PROVIDER="ollama"
$env:AURA_ENDPOINT="http://host.docker.internal:11434"
$env:AURA_MODEL="qwen2.5-coder:3b"
docker compose -f docker-compose.track3.yml up --build
```

If Ollama is unavailable, return to guaranteed inspection mode:

```powershell
$env:AURA_PROVIDER="fixture"
docker compose -f docker-compose.track3.yml up --build
```

## Optional DeepSeek fallback

The existing OpenAI-compatible provider can call DeepSeek without adding another authority path:

```powershell
$env:DEEPSEEK_API_KEY="<local secret>"
python aura_amd_track3_cli.py demo-sequence `
  --provider openai-compatible `
  --endpoint https://api.deepseek.com/v1 `
  --model deepseek-chat `
  --reset-demo
```

Secrets are read from environment variables only and are never written to crystals or dashboard output.

## AMD judge path

The AMD implementation remains intact even when the inspection machine is not attached to the hackathon notebook:

```text
AMD ROCm notebook
  -> Gemma inference through a local OpenAI-compatible endpoint
  -> bounded Aura task worker
  -> detached verification
  -> verified crystals
  -> optional PEFT/LoRA Gemma adapter training
```

Notebook launch:

```bash
python -m pip install -r requirements-amd-track3.txt
export AURA_AMD_BACKEND="AMD ROCm notebook"
export AURA_TRACK3_ENDPOINT="http://127.0.0.1:8000/v1"
export AURA_TRACK3_MODEL="google/gemma-3-4b-it"
python aura_amd_track3_cli.py run-loop \
  --provider openai-compatible \
  --endpoint "$AURA_TRACK3_ENDPOINT" \
  --model "$AURA_TRACK3_MODEL" \
  --cycles 1
```

After verified crystals exist:

```bash
python aura_amd_track3_train.py \
  --model "$AURA_TRACK3_MODEL" \
  --crystals .aura/runtime/amd_track3/verified_crystals.jsonl
```

## Three-minute judge script

1. Open the dashboard and state: **Aura is not an LLM wrapper; models are replaceable workers inside governed Arenas.**
2. Show the six-slot packet: `DIR -> ASP -> CLASS -> SUBJ -> VOICE -> STEM`.
3. Show guarded actions: inspect, bounded proposal, declared verifier.
4. Show blocked actions: secrets, unrelated files, commit, push, merge.
5. Show task one creating the `guard-clause-validation` crystal.
6. Show task two reusing that crystal and passing its independent verifier.
7. Show `source_checkout_mutated=false` and `dissolution_verified=true`.
8. Show the sovereign-knowledge card: confidence, sources, dialect, governance, and review are mandatory for Anishinaabemowin outputs.
9. Show the AMD path: ROCm Gemma inference and optional LoRA training from verified crystals.

## Authority boundaries

- Work occurs only in detached temporary repository copies.
- Tasks declare exact `allowed_files`.
- Verifiers are argv arrays, not shell strings.
- Only passing results become training-eligible crystals.
- Prior crystals are advice, never authority.
- The source checkout remains unchanged.
- No automatic commit, push, pull request, review request, or merge occurs.
- Phase C3 remains proposal-only and human-review governed.
