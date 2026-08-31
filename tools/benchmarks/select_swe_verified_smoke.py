from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

DEFAULT_SEED = "AURA-VERIFIED-50-SMOKE-v1"


def select_instance_ids(instance_ids: Iterable[str], *, count: int = 50, seed: str = DEFAULT_SEED) -> list[str]:
    ids = list(instance_ids)
    if not ids or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("INVALID_INSTANCE_IDS")
    if len(set(ids)) != len(ids):
        raise ValueError("DUPLICATE_INSTANCE_ID")
    if count <= 0 or count > len(ids):
        raise ValueError("INVALID_SELECTION_COUNT")

    def rank(instance_id: str) -> tuple[str, str]:
        digest = hashlib.sha256(f"{seed}\0{instance_id}".encode("utf-8")).hexdigest()
        return digest, instance_id

    return sorted(ids, key=rank)[:count]


def read_jsonl_ids(path: Path) -> list[str]:
    result: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            instance_id = record.get("instance_id")
            if not isinstance(instance_id, str) or not instance_id:
                raise ValueError(f"MISSING_INSTANCE_ID_LINE_{line_number}")
            result.append(instance_id)
    return result


def build_manifest(ids: list[str], *, source_generation: str, count: int, seed: str) -> dict:
    selected = select_instance_ids(ids, count=count, seed=seed)
    source_digest = hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
    selection_digest = hashlib.sha256("\n".join(selected).encode("utf-8")).hexdigest()
    return {
        "schema_id": "AURA_SWE_VERIFIED_SMOKE_MANIFEST_V1",
        "name": f"Aura Verified-{count} Smoke",
        "official": False,
        "leaderboard_score": False,
        "source_dataset": "princeton-nlp/SWE-bench_Verified",
        "source_generation": source_generation,
        "source_instance_count": len(ids),
        "source_instance_set_digest": source_digest,
        "selection_seed": seed,
        "selection_count": count,
        "selected_instance_ids": selected,
        "selection_digest": selection_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic non-official SWE-bench Verified smoke manifest.")
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--source-generation", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--require-source-count", type=int, default=500)
    args = parser.parse_args()

    ids = read_jsonl_ids(args.input_jsonl)
    if args.require_source_count and len(ids) != args.require_source_count:
        raise SystemExit(f"SOURCE_COUNT_MISMATCH expected={args.require_source_count} actual={len(ids)}")
    manifest = build_manifest(ids, source_generation=args.source_generation, count=args.count, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
