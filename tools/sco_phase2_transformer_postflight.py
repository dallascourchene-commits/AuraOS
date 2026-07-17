from __future__ import annotations

from pathlib import Path

SELF = Path(__file__).resolve()
TARGET = SELF.with_name("sco_phase2_apply_review_fixes.py")

# Persisted authority timestamps must fail canonical-float validation before
# nested readiness-report equality checks can mask the malformed field.


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"postflight expected one {label}, found {count}")
    return text.replace(old, new)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''    replace_exact(path, "        grants=tuple(grants),", "        grants=grant_items,", count=1)
    replace_exact(path, "        attestations=tuple(attestations),", "        attestations=attestation_items,", count=1)
''',
        '''    replace_exact(
        path,
        ''' + "'''" + '''    decision = evaluate_governance(
        action_id=request.action_id,
        action_payload_digest=request.action_digest,
        policy_scope=request.policy_scope,
        capability_scope=request.capability_scope,
        grants=tuple(grants),
        attestations=tuple(attestations),
        quorum_policy=quorum_policy,
''' + "'''" + ''',
        ''' + "'''" + '''    decision = evaluate_governance(
        action_id=request.action_id,
        action_payload_digest=request.action_digest,
        policy_scope=request.policy_scope,
        capability_scope=request.capability_scope,
        grants=grant_items,
        attestations=attestation_items,
        quorum_policy=quorum_policy,
''' + "'''" + ''',
    )
''',
        "governance repair block",
    )

    text = replace_once(
        text,
        '''        if any(item.state_digest != self.state_digest for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another state")
        if any(item.evaluated_at != self.evaluated_at for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another evaluation")
''',
        '''        if any(item.state_digest != self.state_digest for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another state")
        _require_canonical_float(self.evaluated_at, "result.evaluated_at")
        if any(item.evaluated_at != self.evaluated_at for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another evaluation")
''',
        "canonical authority timestamp validation order",
    )

    test_repair = '''    replace_exact(
        "tests/test_aura_construction_authority.py",
        ''' + "'''" + '''def test_authority_result_round_trip_revalidates_nested_reports():
    state, request, _ = fixtures()
    result, _ = evaluate_ready(state, request)
    assert ConstructionAuthorityResult.from_dict(result.to_dict()) == result
    payload = result.to_dict()
    payload["readiness_reports"][0]["state_digest"] = "f" * 32
    with pytest.raises(ValueError):
        ConstructionAuthorityResult.from_dict(payload)
''' + "'''" + ''',
        ''' + "'''" + '''def test_authority_result_round_trip_revalidates_nested_reports():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    assert ConstructionAuthorityResult.from_dict(
        result.to_dict(),
        request=request,
        state=state,
        governance_decision=decision,
    ) == result
    payload = result.to_dict()
    payload["readiness_reports"][0]["state_digest"] = "f" * 32
    with pytest.raises(ValueError):
        ConstructionAuthorityResult.from_dict(
            payload,
            request=request,
            state=state,
            governance_decision=decision,
        )
''' + "'''" + ''',
        count=1,
    )
'''

    coverage_repair = '''    append_once(
        "tests/test_aura_construction_authority.py",
        "test_review_hardening_validation_helpers_fail_closed",
        r''' + "'''" + '''
def test_review_hardening_validation_helpers_fail_closed():
    import aura_construction_authority as authority

    scope = ConstructionScope("P1", "Z1", "WP1")
    project_scope = ConstructionScope("P1")
    policy = QuorumPolicy.create(
        risk_class=RiskClass.LOW,
        minimum_approval_count=1,
        required_functional_roles=("OWNER",),
        minimum_distinct_principals=1,
    )
    replay_base = {
        "grants": (),
        "attestations": (),
        "quorum_policy": policy,
        "verified_authority_refs": ("authority-ref",),
        "verified_attestation_refs": ("attestation-ref",),
    }
    invalid_calls = (
        lambda: authority._text(None, "value"),
        lambda: authority._normalized_text_input("", "value"),
        lambda: authority._digest(None, "digest"),
        lambda: authority._digest("A" * 32, "digest"),
        lambda: authority._tuple_strings([], "items"),
        lambda: authority._tuple_strings(("a", "a"), "items"),
        lambda: authority._tuple_strings(("b", "a"), "items"),
        lambda: authority._tuple_strings((), "items", allow_empty=False),
        lambda: authority._normalized_unique("scalar", "items"),
        lambda: authority._normalized_unique((None,), "items"),
        lambda: authority._normalized_unique(("",), "items"),
        lambda: authority._normalized_unique((" a ", "a"), "items"),
        lambda: authority._normalized_unique((), "items", allow_empty=False),
        lambda: authority._verified_digest_bindings({}, "bindings"),
        lambda: authority._timestamp("1", "time"),
        lambda: authority._timestamp(float("inf"), "time"),
        lambda: authority._require_canonical_float(1, "time"),
        lambda: authority._validate_policy_scope(scope, "bad/P1"),
        lambda: authority._validate_policy_scope(scope, "construction/P2"),
        lambda: authority._validate_policy_scope(project_scope, "construction/P1/"),
        lambda: authority._validate_authority_boundary(
            proposal_only=False,
            human_release_required=True,
            physical_work_authorized=False,
            patch_authority=authority.PATCH_AUTHORITY,
            vsa_patch_authority=False,
        ),
        lambda: authority._validate_authority_boundary(
            proposal_only=True,
            human_release_required=True,
            physical_work_authorized=False,
            patch_authority="wrong",
            vsa_patch_authority=False,
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "grants": []}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "attestations": []}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "quorum_policy": object()}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "proposer_principal_id": None}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "normal_policy": object()}
        ),
        lambda: authority.ConstructionGovernanceReplay(
            **{**replay_base, "emergency_reason": None}
        ),
    )
    for call in invalid_calls:
        with pytest.raises(ValueError):
            call()
''' + "'''" + ''',
    )
'''

    text = replace_once(
        text,
        '''def patch_tests() -> None:
    append_once(
''',
        '''def patch_tests() -> None:
''' + test_repair + coverage_repair + '''    append_once(
''',
        "authority test repair insertion",
    )

    TARGET.write_text(text, encoding="utf-8")
    SELF.unlink()
    print("SCO_PHASE2_TRANSFORMER_POSTFLIGHT_PASS")


if __name__ == "__main__":
    main()
