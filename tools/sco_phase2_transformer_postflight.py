from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().with_name("sco_phase2_apply_review_fixes.py")


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    old = '''    replace_exact(path, "        grants=tuple(grants),", "        grants=grant_items,", count=1)
    replace_exact(path, "        attestations=tuple(attestations),", "        attestations=attestation_items,", count=1)
'''
    new = '''    replace_exact(
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
'''
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"postflight expected one governance repair block, found {count}")
    TARGET.write_text(text.replace(old, new), encoding="utf-8")
    print("SCO_PHASE2_TRANSFORMER_POSTFLIGHT_PASS")


if __name__ == "__main__":
    main()
