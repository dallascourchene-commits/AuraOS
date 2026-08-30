from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from scripts.bughound_foundry_intake import (
    Authorization,
    BugCaseV1,
    DuplicateClass,
    IntakeError,
    ProgramCurrentnessReceiptV1,
    Visibility,
    classify_duplicate,
    compile_case_index,
    currentness_binding_digest,
    k27_hint,
    lattice_registry_state,
    sha256_hex,
)

NOW = datetime(2026, 8, 30, 21, 30, tzinfo=timezone.utc)


def receipt(**overrides):
    base = dict(
        program_id="example-program",
        program_source="https://example.invalid/program",
        program_generation="2026-08-30",
        checked_at="2026-08-30T21:00:00+00:00",
        scope_source="https://example.invalid/program/scope",
        rules_source="https://example.invalid/program/rules",
        scope_digest=sha256_hex("scope-v1"),
        rules_digest=sha256_hex("rules-v1"),
        authorization=Authorization.LOCAL_SANDBOX_ONLY.value,
        testing_mode="LOCAL_REPOSITORY_ONLY",
        submission_gate="HUMAN_GATE10",
        safe_harbor_source=None,
        exact_scope_bound=False,
        rules_current=True,
    )
    base.update(overrides)
    return ProgramCurrentnessReceiptV1(**base)


def case(case_id="C1", **overrides):
    base = dict(
        case_id=case_id,
        source_ref=f"repo://example@abc/{case_id}",
        source_generation="abc",
        language="python",
        component="dispatcher",
        defect_operator="AUTHORITY_SUBSTITUTION",
        invariant="credential-bearing request remains on admitted endpoint",
        consequence_class="CROSS_BOUNDARY_REQUEST",
        trigger="redirect to unadmitted host",
        oracle="request is rejected before credential forwarding",
        causal_cone=("resolve_route", "transport", "redirect"),
        fix_ref="commit://fix",
        visibility=Visibility.TRAIN_REFERENCE.value,
        patch_digest=sha256_hex("fix-a"),
    )
    base.update(overrides)
    return BugCaseV1(**base)


def test_local_receipt_admits_local_not_live():
    result = receipt().validate(now=NOW)
    assert result["local_testing_admitted"] is True
    assert result["live_testing_admitted"] is False
    assert result["safe_harbor_is_scope"] is False


def test_safe_harbor_alone_never_creates_live_scope():
    result = receipt(
        authorization=Authorization.PUBLIC_PROGRAM.value,
        safe_harbor_source="https://example.invalid/safe-harbor",
        exact_scope_bound=False,
        testing_mode="EXACT_CURRENT_SCOPE",
    ).validate(now=NOW)
    assert result["live_testing_admitted"] is False


def test_exact_current_public_scope_can_admit_live_testing_input():
    result = receipt(
        authorization=Authorization.PUBLIC_PROGRAM.value,
        exact_scope_bound=True,
        testing_mode="EXACT_CURRENT_SCOPE",
    ).validate(now=NOW)
    assert result["live_testing_admitted"] is True
    assert result["claim_ceiling"] == "CURRENTNESS_AND_ADMISSION_INPUT_ONLY"


def test_stale_program_receipt_fails_closed():
    stale = receipt(checked_at=(NOW - timedelta(days=2)).isoformat())
    with pytest.raises(IntakeError, match="PROGRAM_CURRENTNESS_STALE"):
        stale.validate(now=NOW)


def test_submission_gate_cannot_be_silently_widened():
    with pytest.raises(IntakeError, match="SUBMISSION_GATE_MUST_REMAIN_HUMAN_GATE10"):
        receipt(submission_gate="AUTO_SUBMIT").validate(now=NOW)


def test_root_cause_duplicate_beats_wording_or_source_difference():
    left = case("C1")
    right = case(
        "C2",
        source_ref="repo://other@def/C2",
        source_generation="def",
        trigger="different wording for redirect escape",
        oracle="same invariant checked by another harness",
        patch_digest=sha256_hex("different-patch"),
    )
    assert classify_duplicate(left, right) is DuplicateClass.ROOT_CAUSE_DUPLICATE


def test_same_patch_is_not_enough_to_call_same_vulnerability():
    digest = sha256_hex("shared-fix")
    left = case("C1", patch_digest=digest)
    right = case(
        "C2",
        patch_digest=digest,
        defect_operator="IDENTITY_ALIAS_COLLAPSE",
        invariant="accepted identity derives from protected facts",
        consequence_class="IDENTITY_TRANSPLANT",
        causal_cone=("facts", "identity", "binding"),
    )
    assert classify_duplicate(left, right) is DuplicateClass.PATCH_COLLISION_ONLY


def test_holdout_packet_hides_fix_and_patch_digest():
    hidden = case("H1", visibility=Visibility.HOLDOUT_TEST.value)
    packet = hidden.public_packet()
    assert "fix_ref" not in packet
    assert "patch_digest" not in packet
    assert packet["visibility"] == Visibility.HOLDOUT_TEST.value


def test_source_generation_is_part_of_case_identity():
    original = case("C1")
    moved = replace(original, source_generation="next")
    assert original.case_identity() != moved.case_identity()


def test_scope_or_rules_change_invalidates_currentness_binding():
    original = receipt()
    scope_changed = replace(original, scope_digest=sha256_hex("scope-v2"))
    rules_changed = replace(original, rules_digest=sha256_hex("rules-v2"))
    assert currentness_binding_digest(original) != currentness_binding_digest(scope_changed)
    assert currentness_binding_digest(original) != currentness_binding_digest(rules_changed)


def test_k27_is_deterministic_advisory_range():
    locator = "https://arxiv.org/abs/2608.14065"
    assert k27_hint(locator) == k27_hint(locator)
    assert 0 <= k27_hint(locator) <= 26


def test_case_index_rejects_duplicate_identity_even_with_new_case_id():
    left = case("C1")
    right = replace(left, case_id="C2")
    with pytest.raises(IntakeError, match="DUPLICATE_CASE_IDENTITY"):
        compile_case_index([left, right])


def test_case_index_preserves_k27_as_hint_only():
    rows = compile_case_index([case("C1")])
    assert rows[0]["case_id"] == "C1"
    assert 0 <= rows[0]["k27_hint"] <= 26
    assert "authority" not in rows[0]


def test_unresolved_lattice_registry_fails_closed_without_invention():
    state = lattice_registry_state(None)
    assert state == {
        "status": "LATTICE_REGISTRY_GAP",
        "semantic_lattice_use": False,
        "claim_ceiling": "CONTROL_TOPOLOGIES_ONLY",
    }
    assert lattice_registry_state({"structures": [{"name": "x", "source_ref": "s"}]})["status"] == "LATTICE_REGISTRY_GAP"


def test_exact_eight_source_bound_lattice_entries_resolve_only_as_experiment_input():
    registry = {
        "structures": [
            {"name": f"registered-{i}", "source_ref": f"drive://registry/{i}"}
            for i in range(8)
        ]
    }
    state = lattice_registry_state(registry)
    assert state["status"] == "LATTICE_REGISTRY_RESOLVED"
    assert state["semantic_lattice_use"] is True
    assert state["count"] == 8
    assert state["claim_ceiling"] == "TOPOLOGY_EXPERIMENT_INPUT_ONLY"
