from __future__ import annotations

import copy

import pytest

from tools.benchmarks.long_horizon_preregistration import build_preregistration


D_A = "a" * 64
D_B = "b" * 64
D_C = "c" * 64
D_D = "d" * 64


def arms():
    return [
        {
            "blinded_label": "arm-02",
            "adapter_generation": "adapter-gen-b",
            "adapter_command_digest": D_B,
            "condition_commitment": D_D,
        },
        {
            "blinded_label": "arm-01",
            "adapter_generation": "adapter-gen-a",
            "adapter_command_digest": D_A,
            "condition_commitment": D_C,
        },
    ]


def test_preregistration_is_order_independent_and_frozen():
    first = build_preregistration(
        campaign_id="arena-long-horizon-001",
        rounds=25,
        seed=17,
        timeout_seconds=120,
        arms=arms(),
    )
    second = build_preregistration(
        campaign_id="arena-long-horizon-001",
        rounds=25,
        seed=17,
        timeout_seconds=120,
        arms=list(reversed(arms())),
    )
    assert first == second
    assert first["claim_ceiling"] == "PREREGISTRATION_ONLY_NO_COMPARATIVE_RESULT"
    assert first["cache_or_index_hit_is_evidence"] is False
    assert first["semantic_k27_coordinate"] == "UNRESOLVED_CANONICAL_RESOLVER_REQUIRED"
    assert [arm["blinded_label"] for arm in first["arms"]] == ["arm-01", "arm-02"]
    assert len(first["workload_digest"]) == 64
    assert len(first["preregistration_digest"]) == 64


def test_condition_mapping_cannot_be_embedded_in_blinded_manifest():
    bad = arms()
    bad[0]["condition_name"] = "AURA"
    with pytest.raises(ValueError, match="UNBLINDED_CONDITION_FIELD_FORBIDDEN"):
        build_preregistration(
            campaign_id="arena-long-horizon-001",
            rounds=25,
            seed=17,
            timeout_seconds=120,
            arms=bad,
        )


def test_duplicate_blinded_label_fails_closed():
    bad = arms()
    bad[1]["blinded_label"] = bad[0]["blinded_label"]
    with pytest.raises(ValueError, match="DUPLICATE_BLINDED_LABEL"):
        build_preregistration(
            campaign_id="arena-long-horizon-001",
            rounds=25,
            seed=17,
            timeout_seconds=120,
            arms=bad,
        )


def test_adapter_generation_and_command_digest_are_identity_bearing():
    base = build_preregistration(
        campaign_id="arena-long-horizon-001",
        rounds=25,
        seed=17,
        timeout_seconds=120,
        arms=arms(),
    )
    changed_generation = arms()
    changed_generation[0]["adapter_generation"] = "adapter-gen-b2"
    changed = build_preregistration(
        campaign_id="arena-long-horizon-001",
        rounds=25,
        seed=17,
        timeout_seconds=120,
        arms=changed_generation,
    )
    assert changed["preregistration_digest"] != base["preregistration_digest"]

    changed_command = copy.deepcopy(arms())
    changed_command[0]["adapter_command_digest"] = "e" * 64
    changed = build_preregistration(
        campaign_id="arena-long-horizon-001",
        rounds=25,
        seed=17,
        timeout_seconds=120,
        arms=changed_command,
    )
    assert changed["preregistration_digest"] != base["preregistration_digest"]


def test_invalid_identity_or_timeout_fails_closed():
    bad_generation = arms()
    bad_generation[0]["adapter_generation"] = ""
    with pytest.raises(ValueError, match="ADAPTER_GENERATION_REQUIRED"):
        build_preregistration(
            campaign_id="arena-long-horizon-001",
            rounds=25,
            seed=17,
            timeout_seconds=120,
            arms=bad_generation,
        )

    bad_digest = arms()
    bad_digest[0]["adapter_command_digest"] = "not-a-digest"
    with pytest.raises(ValueError, match="ADAPTER_COMMAND_DIGEST_MUST_BE_SHA256"):
        build_preregistration(
            campaign_id="arena-long-horizon-001",
            rounds=25,
            seed=17,
            timeout_seconds=120,
            arms=bad_digest,
        )

    with pytest.raises(ValueError, match="TIMEOUT_SECONDS_MUST_BE_POSITIVE"):
        build_preregistration(
            campaign_id="arena-long-horizon-001",
            rounds=25,
            seed=17,
            timeout_seconds=0,
            arms=arms(),
        )
