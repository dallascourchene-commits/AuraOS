from __future__ import annotations

from pathlib import Path

SELF = Path(__file__).resolve()
TARGET = SELF.with_name("sco_phase2_apply_review_fixes.py")


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
        '''            evaluated_at=data.get("evaluated_at"),
            expires_at=data.get("expires_at"),
''',
        '''            evaluated_at=_timestamp(data.get("evaluated_at"), "evaluated_at"),
            expires_at=_timestamp(data.get("expires_at"), "expires_at"),
''',
        "authority result timestamp validation block",
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
    text = replace_once(
        text,
        '''def patch_tests() -> None:
    append_once(
''',
        '''def patch_tests() -> None:
''' + test_repair + '''    append_once(
''',
        "authority result round-trip test repair insertion",
    )

    TARGET.write_text(text, encoding="utf-8")
    SELF.unlink()
    print("SCO_PHASE2_TRANSFORMER_POSTFLIGHT_PASS")


if __name__ == "__main__":
    main()
