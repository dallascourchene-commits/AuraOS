from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from memory_city_handoff_current_read_seal import *
from memory_city_horizon_fenced_handoff import digest

SEED = 88317
R = lambda x: digest({"x": x})


@dataclass(frozen=True)
class ReadCert:
    status: str
    coverage_receipt_root: str
    program_root: str
    sealed_domain_root: str
    coverage_generation: int
    binding_roots: tuple[str, ...]
    member_support_roots: tuple[str, ...]
    transition_model_root: str
    horizon: int
    future_congruence_root: str | None
    consequence_root: str
    receipt_root: str


@dataclass(frozen=True)
class ReadUse:
    status: str
    reason: str
    certificate_root: str


def run(cases: int = 20000) -> dict:
    rng = random.Random(SEED)
    stats = {
        "cases": cases,
        "semantic_moves": 0,
        "legacy_prior_ready_false_ready": 0,
        "sealed_false_ready": 0,
        "sealed_false_hold": 0,
        "sealed_rebind": 0,
        "authority_minted": 0,
    }
    for i in range(cases):
        cert = ReadCert(
            "READY_D0", R(f"coverage-{i}"), R(f"program-{i}"), R(f"domain-{i}"), i % 7,
            (R(f"b1-{i}"), R(f"b2-{i}")), (R(f"s1-{i}"), R(f"s2-{i}")),
            R(f"transition-{i}"), 2, R(f"future-{i}"), R(f"consequence-{i}"), R(f"cert-{i}"),
        )
        prior = ReadUse("READY_D0", "current_at_t0", cert.receipt_root)
        prior_root = read_use_root(cert, prior)
        moved = rng.random() < 0.61
        if moved:
            stats["semantic_moves"] += 1
            current_use = ReadUse(
                "READY_D0" if rng.random() < 0.5 else "HOLD_D0",
                "semantic_moved",
                cert.receipt_root,
            )
            # Current owner identity moves even when the certificate root is unchanged.
            current_root = digest({
                "schema": "AURA-CURRENT-READ-OWNER-ROOT-v1",
                "base_read_use_root": read_use_root(cert, current_use),
                "current_semantic_nonce": i,
            })
        else:
            current_root = prior_root

        semantic = semantic_handoff_root(cert)
        evidence = SemanticHandoffEvidence(prior_root, semantic, R(f"owner-{i}"), R(f"verifier-{i}"))
        mutation = MutationBoundaryProjection(
            f"cell-{i}", 7, R(f"cfg-{i}"), 11, 19, 19, "agent", 100,
            semantic, R(f"ta-{i}"), R(f"resource-{i}"),
        )
        verification = HandoffVerificationContext(
            f"cell-{i}", 7, R(f"cfg-{i}"), 11, 19, 19,
            R(f"owner-{i}"), R(f"verifier-{i}"), R(f"ta-{i}"), R(f"resource-{i}"), 10,
        )
        current = CurrentReadUseBinding(current_root, R(f"read-owner-{i}"))

        legacy = compile_horizon_fenced_handoff(cert, prior, evidence, mutation, verification)
        sealed = compile_current_horizon_fenced_handoff(
            cert, prior, current, evidence, mutation, verification
        )
        oracle_ready = not moved
        stats["legacy_prior_ready_false_ready"] += int(
            legacy.disposition is HandoffDisposition.READY_D0 and not oracle_ready
        )
        stats["sealed_false_ready"] += int(
            sealed.disposition is HandoffDisposition.READY_D0 and not oracle_ready
        )
        stats["sealed_false_hold"] += int(
            sealed.disposition is not HandoffDisposition.READY_D0 and oracle_ready
        )
        stats["sealed_rebind"] += int(
            sealed.disposition is HandoffDisposition.REBIND_REQUIRED
        )
        stats["authority_minted"] += int(
            sealed.authority_minted or sealed.effect_authority or sealed.gate10
        )

    payload = {
        "schema": "AURA-MEMORY-CITY-HANDOFF-CURRENT-READ-SEAL-CAMPAIGN-v1",
        "seed": SEED,
        "stats": stats,
    }
    payload["campaign_root"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
