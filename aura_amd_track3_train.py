"""Optional LoRA trainer for verified Aura crystals on AMD-hosted Gemma notebooks."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any


def load_crystals(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if row.get("training_eligible") is not True:
                continue
            returncode_value = row.get("test_returncode")
            if returncode_value is None:
                continue
            try:
                returncode = int(returncode_value)
            except (ValueError, TypeError):
                continue
            if returncode == 0:
                rows.append(row)
    return rows


def format_example(row: dict[str, Any]) -> str:
    proposal = row.get("proposal") or {}
    return json.dumps(
        {
            "task_id": row.get("task_id"),
            "instruction": "Produce a minimal bounded repository patch that passes the declared verifier.",
            "solution_summary": proposal.get("summary"),
            "files": proposal.get("files"),
            "verification": {
                "command": row.get("test_command"),
                "returncode": row.get("test_returncode"),
            },
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def train_once(args: argparse.Namespace) -> dict[str, Any]:
    crystals = load_crystals(args.crystals)
    if len(crystals) < args.minimum_examples:
        return {"ok": False, "status": "WAITING_FOR_CRYSTALS", "count": len(crystals), "minimum": args.minimum_examples}

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        return {"ok": False, "status": "TRAINING_DEPENDENCIES_MISSING", "reason": type(exc).__name__}

    if not torch.cuda.is_available():
        return {"ok": False, "status": "AMD_GPU_UNAVAILABLE", "torch_version": torch.__version__}

    texts = [format_example(row) for row in crystals]
    dataset = Dataset.from_dict({"text": texts})
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=False,
    )
    config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )
    output = Path(args.output_dir) / time.strftime("adapter-%Y%m%d-%H%M%S")
    training_args = SFTConfig(
        output_dir=str(output),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=max(1, args.gradient_accumulation_steps),
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        logging_steps=1,
        save_strategy="epoch",
        bf16=True,
        report_to=[],
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        packing=True,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
        peft_config=config,
        args=training_args,
    )
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint or None)
    trainer.save_model(str(output))
    tokenizer.save_pretrained(str(output))
    manifest = {
        "ok": True,
        "status": "ADAPTER_TRAINED",
        "model": args.model,
        "adapter_path": str(output),
        "crystal_count": len(crystals),
        "amd_backend": os.environ.get("AURA_AMD_BACKEND", "ROCm"),
        "torch_version": torch.__version__,
        "device_name": torch.cuda.get_device_name(0),
    }
    (output / "aura_training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a resumable Gemma LoRA from verified Aura crystals")
    parser.add_argument("--crystals", default=".aura/runtime/amd_track3/verified_crystals.jsonl")
    parser.add_argument("--model", default=os.environ.get("AURA_TRACK3_MODEL", "google/gemma-3-4b-it"))
    parser.add_argument("--output-dir", default=".aura/runtime/amd_track3/adapters")
    parser.add_argument("--minimum-examples", type=int, default=3)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--resume-from-checkpoint", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    result = train_once(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
