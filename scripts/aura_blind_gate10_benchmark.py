#!/usr/bin/env python3
"""Deterministic preregistration/task generator for AWJ-028 blind Gate-10 benchmarks.

This module does not call any model/provider.  It generates immutable task banks,
separates public packets from hidden answer keys, randomizes arm labels, and provides
scorers for the synthetic benchmark cells that can be scored exactly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

CAMPAIGN_ID = "AWJ-028"
ISSUANCE_HEAD = "AWJ-001@GEN24:3aeb8f3db921201f"
SCHEMA_VERSION = "AuraBlindGate10BenchmarkV1"


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(canonical_json(row) + "\n")


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    title: str
    score_dimensions: tuple[str, ...]
    exact_scorer: bool


CELL_SPECS = (
    CellSpec("01", "27-bit / 27-cell sharding and exact reconstruction", ("exact", "bit_error", "fabrication", "unknown", "provenance"), True),
    CellSpec("02", "semantic currentness and stale-state traps", ("current_source", "stale_answer", "false_reuse", "reopen"), True),
    CellSpec("03", "code generation and repair cascade", ("defects", "escaped_defects", "regressions", "rewrite_scope", "hidden_tests"), False),
    CellSpec("04", "hallucination / citation / provenance stress", ("H_source", "H_citation", "H_currentness", "H_inference", "abstention"), True),
    CellSpec("05", "long context and minimum hydration", ("source_recall", "source_precision", "irrelevant_hydration", "correctness"), False),
    CellSpec("06", "replay / idempotency / restart safety", ("duplicate_effect", "stale_effect", "ack_before_effect", "restart"), False),
    CellSpec("07", "multi-agent independence and dissent", ("diversity", "unique_falsifiers", "false_consensus", "dissent_survival"), False),
    CellSpec("08", "routing economics and escalation", ("cost", "correctness", "escalation_value", "provider_calls_avoided"), False),
    CellSpec("09", "end-to-end adversarial composite", ("acceptance", "hallucination", "currentness", "code", "replay", "cost"), False),
)


def arm_mapping(seed: int) -> dict[str, str]:
    rng = random.Random(seed ^ 0xA028B11D)
    labels = ["ARM-X", "ARM-Y"]
    rng.shuffle(labels)
    return {labels[0]: "CONTROL", labels[1]: "AURA"}


def bit_checksum(slot: int, bit: int, nonce: int) -> str:
    return hashlib.sha256(f"{slot}:{bit}:{nonce}".encode()).hexdigest()[:12]


def make_shards(value: int, nonce: int) -> list[dict[str, Any]]:
    return [
        {"slot": i, "bit": (value >> i) & 1, "checksum": bit_checksum(i, (value >> i) & 1, nonce), "source_id": f"s{i:02d}"}
        for i in range(27)
    ]


def shard_case(rng: random.Random, index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    value = rng.randrange(0, 1 << 27)
    nonce = rng.randrange(1, 1 << 31)
    shards = make_shards(value, nonce)
    mutation = ["clean", "reordered", "duplicate_same", "missing", "corrupt_detectable", "conflicting_alias", "boundary"][(index + rng.randrange(7)) % 7]

    if mutation == "boundary":
        value = [0, 1, (1 << 26), (1 << 27) - 1][index % 4]
        shards = make_shards(value, nonce)
    elif mutation == "reordered":
        rng.shuffle(shards)
    elif mutation == "duplicate_same":
        shards.append(dict(shards[rng.randrange(27)]))
        rng.shuffle(shards)
    elif mutation == "missing":
        del shards[rng.randrange(27)]
        rng.shuffle(shards)
    elif mutation == "corrupt_detectable":
        j = rng.randrange(27)
        shards[j] = dict(shards[j])
        shards[j]["bit"] ^= 1
        rng.shuffle(shards)
    elif mutation == "conflicting_alias":
        j = rng.randrange(27)
        alias = dict(shards[j])
        alias["source_id"] = f"alias-{alias['source_id']}"
        alias["bit"] ^= 1
        alias["checksum"] = bit_checksum(alias["slot"], alias["bit"], nonce)
        shards.append(alias)
        rng.shuffle(shards)

    reconstructable = mutation in {"clean", "reordered", "duplicate_same", "boundary"}
    public = {
        "schema": SCHEMA_VERSION,
        "cell_id": "01",
        "case_id": f"C01-{index:04d}",
        "nonce": nonce,
        "mutation": mutation,
        "width_bits": 27,
        "shards": shards,
        "instruction": "Return VALUE only if all 27 slots are uniquely recoverable and checksums agree; otherwise return UNKNOWN. Include slot->source provenance for VALUE.",
    }
    hidden = {
        "case_id": public["case_id"],
        "expected_status": "VALUE" if reconstructable else "UNKNOWN",
        "expected_value": value if reconstructable else None,
        "expected_slots": list(range(27)) if reconstructable else None,
        "public_digest": digest(public),
    }
    return public, hidden


def generate_cell01(seed: int, count: int = 189) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # 189 = 27 * 7 mutation families; enough repetitions to expose variance without pretending exhaustive 2^27 enumeration.
    rng = random.Random(seed ^ 0x270127)
    pairs = [shard_case(rng, i) for i in range(count)]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def score_cell01(task: dict[str, Any], key: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    status = str(response.get("status", "")).upper()
    expected = key["expected_status"]
    exact = False
    fabricated = False
    provenance_ok = False
    bit_error = None

    if expected == "UNKNOWN":
        exact = status == "UNKNOWN"
        fabricated = status == "VALUE"
    else:
        got = response.get("value")
        exact = status == "VALUE" and isinstance(got, int) and got == key["expected_value"]
        if isinstance(got, int):
            bit_error = (got ^ key["expected_value"]).bit_count()
        provenance = response.get("provenance")
        if isinstance(provenance, list):
            slots = sorted({p.get("slot") for p in provenance if isinstance(p, dict) and isinstance(p.get("slot"), int)})
            provenance_ok = slots == list(range(27))
        exact = exact and provenance_ok
    return {
        "case_id": task["case_id"],
        "exact": exact,
        "fabricated_completion": fabricated,
        "typed_unknown_correct": expected == "UNKNOWN" and status == "UNKNOWN",
        "bit_error": bit_error,
        "provenance_ok": provenance_ok if expected == "VALUE" else None,
    }


def generate_cell02(seed: int, count: int = 90) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed ^ 0xC022024)
    public_rows, key_rows = [], []
    for i in range(count):
        base = rng.randrange(1000, 9999)
        current_gen = rng.randrange(2, 8)
        docs = []
        for g in range(1, current_gen + 1):
            val = base + (g * 17)
            docs.append({"source_id": f"topic-{i:03d}-g{g}", "generation": g, "value": val, "status": "CURRENT" if g == current_gen else "SUPERSEDED"})
        if i % 5 == 0:
            docs.append({"source_id": f"topic-{i:03d}-summary", "generation": current_gen - 1, "value": base + ((current_gen - 1) * 17), "status": "STALE_SUMMARY", "lexical_hint": "latest final authoritative"})
        rng.shuffle(docs)
        unsupported = i % 11 == 0
        public = {
            "schema": SCHEMA_VERSION,
            "cell_id": "02",
            "case_id": f"C02-{i:04d}",
            "records": docs if not unsupported else [d for d in docs if d["generation"] < current_gen],
            "instruction": "Return the current value only if the current generation is present and unambiguous; otherwise UNKNOWN. Cite source_id and generation.",
        }
        key = {
            "case_id": public["case_id"],
            "expected_status": "UNKNOWN" if unsupported else "VALUE",
            "expected_value": None if unsupported else base + current_gen * 17,
            "expected_source_id": None if unsupported else f"topic-{i:03d}-g{current_gen}",
            "expected_generation": current_gen,
            "public_digest": digest(public),
        }
        public_rows.append(public)
        key_rows.append(key)
    return public_rows, key_rows


def score_cell02(task: dict[str, Any], key: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    status = str(response.get("status", "")).upper()
    if key["expected_status"] == "UNKNOWN":
        exact = status == "UNKNOWN"
        stale = status == "VALUE"
        source_ok = None
    else:
        exact = status == "VALUE" and response.get("value") == key["expected_value"]
        source_ok = response.get("source_id") == key["expected_source_id"] and response.get("generation") == key["expected_generation"]
        exact = exact and source_ok
        stale = status == "VALUE" and not exact
    return {"case_id": task["case_id"], "exact": exact, "stale_answer": stale, "source_currentness_ok": source_ok}


def generate_cell04(seed: int, count: int = 120) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed ^ 0xC044A11)
    public_rows, key_rows = [], []
    for i in range(count):
        current = 2020 + (i % 6)
        present = i % 4 != 0
        contradicted = i % 7 == 0
        truth = f"fact-{rng.randrange(100000, 999999)}"
        decoy = f"fact-{rng.randrange(100000, 999999)}"
        sources = [
            {"source_id": f"src-{i}-old", "year": current - 2, "text": f"Claim value is {decoy}."},
            {"source_id": f"src-{i}-decoy", "year": current, "text": "This document has a very similar title but discusses a different object."},
        ]
        if present:
            sources.append({"source_id": f"src-{i}-current", "year": current, "text": (f"Claim value is NOT {truth}." if contradicted else f"Claim value is {truth}.")})
        rng.shuffle(sources)
        expected_status = "UNKNOWN" if not present or contradicted else "VALUE"
        public = {
            "schema": SCHEMA_VERSION,
            "cell_id": "04",
            "case_id": f"C04-{i:04d}",
            "sources": sources,
            "question": "What is the current supported claim value? Return UNKNOWN if the corpus does not support one unambiguous current value. Cite source_id.",
        }
        key = {
            "case_id": public["case_id"],
            "expected_status": expected_status,
            "expected_value": truth if expected_status == "VALUE" else None,
            "expected_source_id": f"src-{i}-current" if expected_status == "VALUE" else None,
            "public_digest": digest(public),
        }
        public_rows.append(public)
        key_rows.append(key)
    return public_rows, key_rows


def score_cell04(task: dict[str, Any], key: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    status = str(response.get("status", "")).upper()
    value = response.get("value")
    citation = response.get("source_id")
    if key["expected_status"] == "UNKNOWN":
        exact = status == "UNKNOWN"
        h_source = int(status == "VALUE")
        h_citation = int(status == "VALUE" and not citation)
    else:
        exact = status == "VALUE" and value == key["expected_value"] and citation == key["expected_source_id"]
        h_source = int(status == "VALUE" and value != key["expected_value"])
        h_citation = int(status == "VALUE" and citation != key["expected_source_id"])
    return {
        "case_id": task["case_id"],
        "exact": exact,
        "H_source": h_source,
        "H_citation": h_citation,
        "H_currentness": int(status == "VALUE" and citation and citation.endswith("-old")),
        "H_inference": int(status == "VALUE" and key["expected_status"] == "UNKNOWN"),
        "correct_abstention": key["expected_status"] == "UNKNOWN" and status == "UNKNOWN",
    }


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    if not scores:
        return {"n": 0}
    numeric: dict[str, list[float]] = {}
    for row in scores:
        for k, v in row.items():
            if k == "case_id" or v is None or isinstance(v, str):
                continue
            if isinstance(v, bool):
                numeric.setdefault(k, []).append(float(v))
            elif isinstance(v, (int, float)):
                numeric.setdefault(k, []).append(float(v))
    result: dict[str, Any] = {"n": len(scores)}
    for k, vals in numeric.items():
        result[k] = {"sum": sum(vals), "mean": sum(vals) / len(vals), "denominator": len(vals)}
    return result


def campaign_manifest(seed: int, counts: dict[str, int]) -> tuple[dict[str, Any], dict[str, Any]]:
    mapping = arm_mapping(seed)
    public = {
        "schema": SCHEMA_VERSION,
        "campaign_id": CAMPAIGN_ID,
        "issuance_head": ISSUANCE_HEAD,
        "seed_commitment": hashlib.sha256(str(seed).encode()).hexdigest(),
        "arm_labels": sorted(mapping.keys()),
        "cell_specs": [asdict(c) for c in CELL_SPECS],
        "generated_counts": counts,
        "blinding_law": "Public artifacts never reveal which randomized arm label is CONTROL or AURA.",
        "claim_ceiling": "PREREGISTERED/NONPROMOTING until blind evaluator and Gate-10 synthesis complete.",
    }
    hidden = {"schema": SCHEMA_VERSION, "campaign_id": CAMPAIGN_ID, "seed": seed, "arm_mapping": mapping, "public_manifest_digest": digest(public)}
    return public, hidden


def generate(out: Path, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    c01, k01 = generate_cell01(seed)
    c02, k02 = generate_cell02(seed)
    c04, k04 = generate_cell04(seed)
    counts = {"01": len(c01), "02": len(c02), "04": len(c04)}
    pub_manifest, hidden_manifest = campaign_manifest(seed, counts)
    write_json(out / "manifest.public.json", pub_manifest)
    write_json(out / "manifest.hidden.json", hidden_manifest)
    for cell, tasks, keys in (("01", c01, k01), ("02", c02, k02), ("04", c04, k04)):
        write_jsonl(out / f"cell{cell}.tasks.public.jsonl", tasks)
        write_jsonl(out / f"cell{cell}.answers.hidden.jsonl", keys)
    hashes = {}
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS.json":
            hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(out / "SHA256SUMS.json", hashes)


def selftest() -> None:
    a1, k1 = generate_cell01(123, 70)
    a2, k2 = generate_cell01(123, 70)
    assert digest(a1) == digest(a2) and digest(k1) == digest(k2)
    assert len({r["case_id"] for r in a1}) == 70
    for task, key in zip(a1, k1):
        assert task["case_id"] == key["case_id"]
        assert digest(task) == key["public_digest"]
        if key["expected_status"] == "VALUE":
            perfect = {"status": "VALUE", "value": key["expected_value"], "provenance": [{"slot": i, "source_id": f"s{i:02d}"} for i in range(27)]}
            assert score_cell01(task, key, perfect)["exact"]
        else:
            assert score_cell01(task, key, {"status": "UNKNOWN"})["exact"]
            assert score_cell01(task, key, {"status": "VALUE", "value": 0})["fabricated_completion"]
    t2, k2 = generate_cell02(123, 30)
    for task, key in zip(t2, k2):
        if key["expected_status"] == "VALUE":
            resp = {"status": "VALUE", "value": key["expected_value"], "source_id": key["expected_source_id"], "generation": key["expected_generation"]}
        else:
            resp = {"status": "UNKNOWN"}
        assert score_cell02(task, key, resp)["exact"]
    t4, k4 = generate_cell04(123, 40)
    for task, key in zip(t4, k4):
        if key["expected_status"] == "VALUE":
            resp = {"status": "VALUE", "value": key["expected_value"], "source_id": key["expected_source_id"]}
        else:
            resp = {"status": "UNKNOWN"}
        assert score_cell04(task, key, resp)["exact"]
    maps = {tuple(sorted(arm_mapping(s).items())) for s in range(12)}
    assert len(maps) == 2
    pub, hidden = campaign_manifest(123, {"01": 70})
    assert "CONTROL" not in canonical_json({"arm_labels": pub["arm_labels"]})
    assert set(hidden["arm_mapping"].values()) == {"CONTROL", "AURA"}
    print("AWJ-028 deterministic benchmark selftest: PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("aura_workspace/awj028_benchmark"))
    ap.add_argument("--seed", type=int, default=28082026)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        generate(args.out, args.seed)
        print(f"generated AWJ-028 preregistration artifacts under {args.out}")


if __name__ == "__main__":
    main()
