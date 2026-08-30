from __future__ import annotations

from scripts.bughound_bugbot_lab import CASES, CASE_BY_ID, SCHEMA, run_case, verify_ground_truth


def test_suite_contains_required_foundry_families():
    families = {case.family for case in CASES}
    assert {
        "STALE_GENERATION",
        "REPLAY_IDEMPOTENCY",
        "IDENTITY_ALIAS_COLLAPSE",
        "AUTHORITY_SUBSTITUTION",
        "NONCOMMUTATION_ORDER",
        "PRODUCER_RESIDUE_CONSUMER",
        "CACHE_INVALIDATION",
        "REOPEN_PROPAGATION",
        "PARSER_BOUNDARY",
        "MERGE_DEFAULT_FALLBACK",
    } <= families


def test_cross_boundary_review_lineage_adds_two_distinct_cases():
    endpoint = CASE_BY_ID["BB-011"]
    identity = CASE_BY_ID["BB-012"]
    assert endpoint.lineage_refs == ("AuraOS#291",)
    assert identity.lineage_refs == ("AuraOS#295",)
    assert endpoint.family != identity.family


def test_every_buggy_and_fixed_variant_matches_registered_oracle():
    for case in CASES:
        assert run_case(case.case_id, "buggy") == case.expected_buggy
        assert run_case(case.case_id, "fixed") == case.expected_fixed
        assert case.expected_buggy != case.expected_fixed


def test_suite_receipt_is_deterministic_and_complete():
    first = verify_ground_truth()
    second = verify_ground_truth()
    assert first == second
    assert first["schema"] == SCHEMA
    assert first["case_count"] == 12
    assert first["passed"] is True
    assert len(first["suite_digest"]) == 64
    assert all(row["passed"] for row in first["results"])
    assert first["claim_ceiling"] == "SYNTHETIC_D0_GROUND_TRUTH_ONLY"


def test_case_receipts_have_exact_reproducer_contract_fields():
    for case in CASES:
        receipt = case.receipt()
        assert receipt["case_id"] == case.case_id
        assert receipt["buggy_source_ref"].startswith("bugbot://")
        assert receipt["fixed_source_ref"].startswith("bugbot://")
        assert receipt["trigger"]
        assert receipt["invariant"]
        assert receipt["causal_cone"]
        assert len(receipt["case_digest"]) == 64


def test_endpoint_boundary_escape_is_blocked_by_fixed_variant():
    assert run_case("BB-011", "buggy") == "other.example"
    assert run_case("BB-011", "fixed") == "REDIRECT_BLOCKED"


def test_identity_transplant_is_rejected_by_fixed_variant():
    assert run_case("BB-012", "buggy") is True
    assert run_case("BB-012", "fixed") is False


def test_replay_effect_executes_once_in_fixed_variant():
    assert run_case("BB-002", "buggy") == 14
    assert run_case("BB-002", "fixed") == 7


def test_reopen_propagation_reaches_transitive_hard_dependent():
    assert run_case("BB-008", "buggy") == ("parser", "source")
    assert run_case("BB-008", "fixed") == ("parser", "report", "source")
