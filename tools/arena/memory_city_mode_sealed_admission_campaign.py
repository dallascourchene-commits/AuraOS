from __future__ import annotations
import hashlib, json, random
from memory_city_coverage_membrane import (
    AdmissionMode, PositiveTrace, compile_coverage_certificate,
    compile_proof_carrying_typed_admission,
)

SEED = 880021

def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def run(cases: int = 10000) -> dict:
    rng = random.Random(SEED)
    stats = {
        "cases": cases,
        "read_ready": 0,
        "read_hold": 0,
        "effect_requests": 0,
        "effect_ready": 0,
        "effect_tecc_hold": 0,
        "legacy_generic_false_effect_ready": 0,
        "authority_minted": 0,
        "mode_receipt_collision": 0,
    }
    for i in range(cases):
        program, domain, generation = h(f"p{i}"), h(f"d{i}"), rng.randrange(8)
        obligations = tuple(f"b{j}" for j in range(rng.randint(1, 5)))
        complete = rng.random() < 0.62
        if complete:
            positive = tuple(PositiveTrace(b, program, domain, generation, h("t" + b + str(i))) for b in obligations)
        else:
            cutoff = rng.randrange(len(obligations))
            positive = tuple(PositiveTrace(b, program, domain, generation, h("t" + b + str(i))) for b in obligations[:cutoff])
        coverage = compile_coverage_certificate(
            program_root=program, sealed_domain_root=domain, generation=generation,
            obligations=obligations, positive=positive,
        )
        common = dict(
            typed_closure_receipt_root=h("tc" + str(i)), coverage=coverage,
            support_root=h("s" + str(i)), influence_root=h("i" + str(i)),
            transition_model_root=h("m" + str(i)),
            future_congruence_root=(h("f" + str(i)) if rng.random() < 0.5 else None),
            horizon=rng.choice((0, 0, 1, 2)),
        )
        read = compile_proof_carrying_typed_admission(**common, mode=AdmissionMode.READ_ONLY)
        effect = compile_proof_carrying_typed_admission(**common, mode=AdmissionMode.EFFECT_BOUND)
        stats["read_ready"] += int(read["disposition"] == "READY_D0")
        stats["read_hold"] += int(read["disposition"] != "READY_D0")
        stats["effect_requests"] += 1
        stats["effect_ready"] += int(effect["disposition"] == "READY_D0")
        stats["effect_tecc_hold"] += int(effect["disposition"] == "HOLD_TECC_REQUIRED_D0")
        # Deliberately unsafe predecessor interpretation: generic read READY is reused as effect READY.
        stats["legacy_generic_false_effect_ready"] += int(read["disposition"] == "READY_D0")
        stats["authority_minted"] += int(any((effect["authority_minted"], effect["mutation_authority"], effect["effect_authority"], effect["gate10"])))
        stats["mode_receipt_collision"] += int(read["receipt_root"] == effect["receipt_root"])
    payload = {
        "schema": "AURA-MEMORY-CITY-MODE-SEALED-ADMISSION-CAMPAIGN-v1",
        "seed": SEED,
        "stats": stats,
    }
    payload["campaign_root"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload

if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
