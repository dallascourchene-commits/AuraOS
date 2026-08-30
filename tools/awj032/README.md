# AWJ-032 AirLLM G1 source admission

Status: **STAGED / NONPROMOTING / HOST REPRODUCTION REQUIRED**.

This directory provides a deterministic pre-import source gate for the AWJ-032 AirLLM campaign. It exists to enforce the current Aura rule that remote model code may not be silently enabled.

## Current source finding

The source review on 2026-08-30 pins upstream AirLLM v3.3.0 to tag commit `c92cea691412715a218306acb01fc9c2c681a8f2` (Apache-2.0). Stock v3.3.0 still passes `trust_remote_code=True` unconditionally in `AutoModel.get_module_class()`, so it is not admitted under Aura's default hard-false policy.

Upstream AirLLM PR #306 is useful design evidence but remains open and deliberately retains automatic fallback to remote code; it therefore does not by itself satisfy a hard opt-out.

## Gate behavior

`airllm_source_admission.py` runs before importing AirLLM/model code and emits a deterministic receipt. It blocks:

- literal `trust_remote_code=True`;
- dynamic/non-literal `trust_remote_code` values;
- nested `pip install` mutation in the inspected package/setup source;
- package version drift from the expected pin;
- missing/unparseable package source.

It also hashes the inspected source set so the host receipt can bind the exact admitted tree.

A separately authorized exact-hash remote-code allowlist is intentionally *not* hidden in this module; that would require its own authority/currentness contract.

Constructor-side focused suite: 8/8 unittest methods PASS. Host exact-head reproduction and audit of the actual materialized AirLLM tree are still required.

Run:

```bash
cd tools/awj032
python -m unittest -v test_airllm_source_admission.py
python airllm_source_admission.py <materialized-airllm-source-root> --expected-version 3.3.0
```

A blocked result is a valid G1 outcome and must prevent G2/G3 from laundering the dependency/security gate. No model download, import, generation, or Gate-4 canary is authorized by this directory.
