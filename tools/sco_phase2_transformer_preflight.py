from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().with_name("sco_phase2_apply_review_fixes.py")


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"preflight expected one match, found {count}: {old[:100]!r}")
    return text.replace(old, new)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''    for old, new in (
        ('consent_refs=tuple(data.get("consent_refs", ())),',
         'consent_refs=_sequence_input(data.get("consent_refs", ()), "evidence.consent_refs"),'),
        ('evidence_refs=tuple(data.get("evidence_refs", ())),',
         'evidence_refs=_sequence_input(data.get("evidence_refs", ()), "claim.evidence_refs"),'),
        ('consent_refs=tuple(data.get("consent_refs", ())),',
         'consent_refs=_sequence_input(data.get("consent_refs", ()), "claim.consent_refs"),'),
        ('parent_event_ids=tuple(data.get("parent_event_ids", ())),',
         'parent_event_ids=_sequence_input(data.get("parent_event_ids", ()), "event.parent_event_ids"),'),
        ('supersedes_event_ids=tuple(data.get("supersedes_event_ids", ())),',
         'supersedes_event_ids=_sequence_input(data.get("supersedes_event_ids", ()), "event.supersedes_event_ids"),'),
    ):
        replace_exact(path, old, new)
''',
        '''    replace_exact(
        path,
        ''' + "'''" + '''            privacy_class=data.get("privacy_class"),
            consent_refs=tuple(data.get("consent_refs", ())),
            observed_at=data.get("observed_at"),
''' + "'''" + ''',
        ''' + "'''" + '''            privacy_class=data.get("privacy_class"),
            consent_refs=_sequence_input(
                data.get("consent_refs", ()), "evidence.consent_refs"
            ),
            observed_at=data.get("observed_at"),
''' + "'''" + ''',
    )
    replace_exact(
        path,
        ''' + "'''" + '''            claimant_id=data.get("claimant_id"),
            evidence_refs=tuple(data.get("evidence_refs", ())),
            measurement_class=data.get("measurement_class"),
''' + "'''" + ''',
        ''' + "'''" + '''            claimant_id=data.get("claimant_id"),
            evidence_refs=_sequence_input(
                data.get("evidence_refs", ()), "claim.evidence_refs"
            ),
            measurement_class=data.get("measurement_class"),
''' + "'''" + ''',
    )
    replace_exact(
        path,
        ''' + "'''" + '''            privacy_class=data.get("privacy_class"),
            consent_refs=tuple(data.get("consent_refs", ())),
            created_at=data.get("created_at"),
''' + "'''" + ''',
        ''' + "'''" + '''            privacy_class=data.get("privacy_class"),
            consent_refs=_sequence_input(
                data.get("consent_refs", ()), "claim.consent_refs"
            ),
            created_at=data.get("created_at"),
''' + "'''" + ''',
    )
    for old, new in (
        ('parent_event_ids=tuple(data.get("parent_event_ids", ())),',
         'parent_event_ids=_sequence_input(data.get("parent_event_ids", ()), "event.parent_event_ids"),'),
        ('supersedes_event_ids=tuple(data.get("supersedes_event_ids", ())),',
         'supersedes_event_ids=_sequence_input(data.get("supersedes_event_ids", ()), "event.supersedes_event_ids"),'),
    ):
        replace_exact(path, old, new)
''',
    )

    text = replace_once(
        text,
        '''    for old, new in (
        ('active_event_ids=tuple(data.get("active_event_ids", ())),',
         'active_event_ids=_sequence_input(data.get("active_event_ids", ()), "state.active_event_ids"),'),
        ('superseded_event_ids=tuple(data.get("superseded_event_ids", ())),',
         'superseded_event_ids=_sequence_input(data.get("superseded_event_ids", ()), "state.superseded_event_ids"),'),
''',
        '''    replace_exact(
        path,
        ''' + "'''" + '''            active_event_ids=tuple(data.get("active_event_ids", ())),
            superseded_event_ids=tuple(data.get("superseded_event_ids", ())),
''' + "'''" + ''',
        ''' + "'''" + '''            active_event_ids=_sequence_input(
                data.get("active_event_ids", ()), "state.active_event_ids"
            ),
            superseded_event_ids=_sequence_input(
                data.get("superseded_event_ids", ()), "state.superseded_event_ids"
            ),
''' + "'''" + ''',
    )
    for old, new in (
''',
    )

    text = replace_once(
        text,
        '''def patch_authority() -> None:
    path = "aura_construction_authority.py"
    replace_exact(
''',
        '''def patch_authority() -> None:
    path = "aura_construction_authority.py"
    replace_exact(
        path,
        ''' + "'''" + '''from aura_construction_contracts import (
    ConstructionScope,
''' + "'''" + ''',
        ''' + "'''" + '''from aura_construction_contracts import (
    ConstructionClaim,
    ConstructionEvidence,
    ConstructionScope,
''' + "'''" + ''',
    )
    replace_exact(
''',
    )

    text = replace_once(
        text,
        '''    append_once(
        "tests/test_aura_construction_authority.py",
        "test_review_hardening_result_expiry_is_capped_by_evidence_freshness",
''',
        '''    replace_exact(
        "tests/test_aura_construction_authority.py",
        ''' + "'''" + '''    AuthorityGrant,
    QuorumPolicy,
''' + "'''" + ''',
        ''' + "'''" + '''    AuthorityGrant,
    ChainedAuthorityReceipt,
    QuorumPolicy,
''' + "'''" + ''',
    )
    append_once(
        "tests/test_aura_construction_authority.py",
        "test_review_hardening_result_expiry_is_capped_by_evidence_freshness",
''',
    )

    text = replace_once(
        text,
        '__import__("aura_relational_authority").ChainedAuthorityReceipt.create(',
        'ChainedAuthorityReceipt.create(',
    )

    text = replace_once(
        text,
        '''    replace_exact(
        "tests/test_aura_construction_authority.py",
        ''' + "'''" + '''    assert not decision.authorized
    assert not result.digitally_ready
''' + "'''" + ''',
        ''' + "'''" + '''    assert not decision.authorized
    assert not result.digitally_ready
    assert any("invalid_attestation" in reason for reason in result.missing_reasons)
''' + "'''" + ''',
        count=1,
    )
''',
        '',
    )

    TARGET.write_text(text, encoding="utf-8")
    print("SCO_PHASE2_TRANSFORMER_PREFLIGHT_PASS")


if __name__ == "__main__":
    main()
