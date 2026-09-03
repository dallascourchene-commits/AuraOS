"""Bounded AirLLM tiny-fixture runtime proof for AWJ-032.

This probe is intentionally small and nonpromoting. It assumes AirLLM has already
been materialized from the pinned/remediated source into the current isolated
Python environment. It proves only the standard-architecture tiny fixture path:
HARD_FALSE runtime guard -> safetensors snapshot -> split -> load -> generate ->
reopen -> generate.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from huggingface_hub import snapshot_download

from airllm_runtime_hard_false import (
    AirLLMRemoteCodeWideningRejected,
    install_transformers_hard_false_guard,
)

MODEL_ID = "hf-internal-testing/tiny-random-LlamaForCausalLM"
MODEL_REVISION = "9fb191250dd56d0ba7ec9785a025ed29c03d5998"
SCHEMA = "AWJ032_AIRLLM_TINY_FIXTURE_RUNTIME_RECEIPT_V1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not root.exists():
        return out
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        out.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return out


def _versions() -> dict[str, str]:
    import accelerate
    import huggingface_hub
    import safetensors
    import torch
    import transformers

    try:
        import importlib.metadata as metadata
        airllm_version = metadata.version("airllm")
    except Exception:
        airllm_version = "UNKNOWN"

    return {
        "python": sys.version.split()[0],
        "airllm": airllm_version,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "accelerate": accelerate.__version__,
        "safetensors": safetensors.__version__,
        "huggingface_hub": huggingface_hub.__version__,
    }


def _one_generation(model: Any, text: str) -> dict[str, Any]:
    encoded = model.tokenizer(
        [text],
        return_tensors="pt",
        return_attention_mask=False,
        truncation=True,
        max_length=16,
        padding=False,
    )
    output = model.generate(
        encoded["input_ids"],
        max_new_tokens=1,
        use_cache=True,
        do_sample=False,
        return_dict_in_generate=True,
    )
    sequence = output.sequences[0]
    decoded = model.tokenizer.decode(sequence, skip_special_tokens=False)
    return {
        "input_shape": list(encoded["input_ids"].shape),
        "output_shape": list(output.sequences.shape),
        "decoded_nonempty": bool(decoded),
        "generated_token_count": int(output.sequences.shape[-1] - encoded["input_ids"].shape[-1]),
    }


def run(*, cache_dir: Path, shard_dir: Path, device: str) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    shard_dir.mkdir(parents=True, exist_ok=True)

    import transformers

    guard = install_transformers_hard_false_guard(transformers)
    try:
        negative_rejected = False
        try:
            transformers.AutoConfig.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                trust_remote_code=True,
                cache_dir=str(cache_dir),
            )
        except AirLLMRemoteCodeWideningRejected:
            negative_rejected = True
        if not negative_rejected:
            raise RuntimeError("RUNTIME_HARD_FALSE_NEGATIVE_PROBE_FAILED")

        # Positive loader probe: the guard must permit literal False.
        config = transformers.AutoConfig.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            trust_remote_code=False,
            cache_dir=str(cache_dir),
        )
        if getattr(config, "model_type", None) != "llama":
            raise RuntimeError("TINY_FIXTURE_CONFIG_NOT_LLAMA")

        snapshot = Path(
            snapshot_download(
                repo_id=MODEL_ID,
                revision=MODEL_REVISION,
                cache_dir=str(cache_dir),
                allow_patterns=[
                    "config.json",
                    "generation_config.json",
                    "model.safetensors",
                    "special_tokens_map.json",
                    "tokenizer.json",
                    "tokenizer.model",
                    "tokenizer_config.json",
                ],
            )
        ).resolve()

        snapshot_files = _manifest(snapshot)
        if not any(item["path"].endswith(".safetensors") for item in snapshot_files):
            raise RuntimeError("TINY_FIXTURE_SAFETENSORS_MISSING")
        if any(item["path"].endswith((".bin", ".pt", ".pth", ".pickle", ".pkl")) for item in snapshot_files):
            raise RuntimeError("TINY_FIXTURE_UNSAFE_WEIGHT_FORMAT_PRESENT")

        # Import AirLLM only after the runtime guard is active.
        from airllm import AutoModel

        model = AutoModel.from_pretrained(
            str(snapshot),
            device=device,
            layer_shards_saving_path=str(shard_dir),
            prefetching=False,
        )
        first = _one_generation(model, "Hello")
        first_manifest = _manifest(shard_dir)
        if not first_manifest:
            raise RuntimeError("AIRLLM_SPLIT_MANIFEST_EMPTY")

        del model
        gc.collect()

        # Reopen against the already-materialized split path and prove a second generation.
        model2 = AutoModel.from_pretrained(
            str(snapshot),
            device=device,
            layer_shards_saving_path=str(shard_dir),
            prefetching=False,
        )
        second = _one_generation(model2, "Hello")
        second_manifest = _manifest(shard_dir)
        del model2
        gc.collect()

        if first_manifest != second_manifest:
            raise RuntimeError("AIRLLM_REOPEN_SPLIT_MANIFEST_DRIFT")
        if first["generated_token_count"] < 1 or second["generated_token_count"] < 1:
            raise RuntimeError("AIRLLM_GENERATION_DID_NOT_ADVANCE")

        guard_receipt = guard.receipt()
        return {
            "schema": SCHEMA,
            "status": "PASS",
            "claim": "HARD_FALSE_FIXTURE_PATH_PROVEN",
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "device": device,
            "versions": _versions(),
            "runtime_guard": {
                "installed_boundaries": list(guard_receipt.installed_boundaries),
                "skipped_optional_boundaries": list(guard_receipt.skipped_optional_boundaries),
                "protected_call_count": guard_receipt.protected_call_count,
                "rejected_widening_count": guard_receipt.rejected_widening_count,
                "receipt_digest": guard_receipt.receipt_digest,
            },
            "fixture_manifest": snapshot_files,
            "split_manifest": first_manifest,
            "first_generation": first,
            "reopen_generation": second,
            "large_checkpoint_used": False,
            "remote_code_authorized": False,
            "provider_used": False,
            "claim_ceiling": "TINY_STANDARD_ARCHITECTURE_RUNTIME_PATH_ONLY_NOT_OWNER_HOST_PROOF",
        }
    finally:
        guard.restore()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=".awj032/hf-cache")
    parser.add_argument("--shard-dir", default=".awj032/tiny-llama-split")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--receipt", default=".awj032/AWJ032_TINY_RUNTIME_RECEIPT.json")
    args = parser.parse_args()

    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt = run(
            cache_dir=Path(args.cache_dir),
            shard_dir=Path(args.shard_dir),
            device=args.device,
        )
    except Exception as exc:  # noqa: BLE001 - materialize exact typed runtime blocker
        receipt = {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "device": args.device,
            "large_checkpoint_used": False,
            "remote_code_authorized": False,
            "provider_used": False,
            "claim_ceiling": "TINY_STANDARD_ARCHITECTURE_RUNTIME_PATH_ONLY_NOT_OWNER_HOST_PROOF",
        }
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
        return 2

    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
