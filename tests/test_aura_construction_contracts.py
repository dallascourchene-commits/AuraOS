from dataclasses import replace
import pytest
from aura_event_contracts import ActorType, MeasurementClass
from aura_construction_contracts import *

D='a'*32
D2='b'*32

def scope(): return ConstructionScope('P1','Z1','WP1')
def evidence(**kw):
    data=dict(scope=scope(),subject_id='wall-1',evidence_class=ConstructionEvidenceClass.DOCUMENT,source_ref='doc-1',payload_digest=D,measurement_class=MeasurementClass.EMPIRICAL,confidence=.9,authority_class=ConstructionAuthorityClass.INFORMATIVE,privacy_class=ConstructionPrivacyClass.PROJECT,observed_at=1.0,expires_at=20.0)
    data.update(kw); return ConstructionEvidence.create(**data)
def claim(ev=None, **kw):
    ev=ev or evidence()
    data=dict(scope=scope(),subject_id='wall-1',predicate='installed',value_digest=D2,claimant_id='contractor-1',evidence_refs=(ev.evidence_id,),measurement_class=MeasurementClass.EMPIRICAL,confidence=.8,authority_class=ConstructionAuthorityClass.CONTRACTOR,privacy_class=ConstructionPrivacyClass.PROJECT,created_at=2.0,expires_at=20.0)
    data.update(kw); return ConstructionClaim.create(**data)

def test_scope_key_is_deterministic(): assert scope().scope_key=='P1/Z1/WP1'
def test_scope_rejects_non_normalized_text():
    with pytest.raises(ValueError): ConstructionScope(' P1')
def test_evidence_identity_is_stable(): assert evidence()==evidence()
def test_evidence_tampering_is_rejected():
    with pytest.raises(ValueError): replace(evidence(),confidence=.1)
def test_sensor_cannot_carry_professional_authority():
    with pytest.raises(ValueError): evidence(evidence_class=ConstructionEvidenceClass.SENSOR,authority_class=ConstructionAuthorityClass.PROFESSIONAL)
def test_sensitive_evidence_requires_consent():
    with pytest.raises(ValueError): evidence(privacy_class=ConstructionPrivacyClass.SENSITIVE)
def test_sensitive_evidence_accepts_consent(): assert evidence(privacy_class=ConstructionPrivacyClass.SENSITIVE,consent_refs=('consent-1',)).consent_refs
def test_claim_identity_is_stable():
    ev=evidence(); assert claim(ev)==claim(ev)
def test_claim_tampering_is_rejected():
    with pytest.raises(ValueError): replace(claim(),value_digest='c'*32)
def test_professional_claim_requires_evidence():
    with pytest.raises(ValueError): claim(evidence_refs=(),authority_class=ConstructionAuthorityClass.PROFESSIONAL)
def test_event_genesis_and_envelope():
    ev=evidence(); e=ConstructionEvent.create(ledger_id='construction/P1',sequence_number=1,previous_chain_digest=GENESIS_CHAIN_DIGEST,trace_id='trace-1',record=ev,actor_id='human-1',actor_type=ActorType.HUMAN,created_at=3.0)
    env=e.to_aura_event_envelope(); assert env.proposal_only is True and env.payload_ref==ev.evidence_id and e.project_id=='P1'
def test_first_event_requires_genesis():
    with pytest.raises(ValueError): ConstructionEvent.create(ledger_id='construction/P1',sequence_number=1,previous_chain_digest='bad',trace_id='t',record=evidence(),actor_id='h',actor_type=ActorType.HUMAN,created_at=3)
def test_parent_and_supersession_refs_must_be_disjoint():
    with pytest.raises(ValueError): ConstructionEvent.create(ledger_id='construction/P1',sequence_number=2,previous_chain_digest=D,trace_id='t',record=evidence(),actor_id='h',actor_type=ActorType.HUMAN,parent_event_ids=('e1',),supersedes_event_ids=('e1',),created_at=3)
def test_invalid_payload_digest_fails():
    with pytest.raises(ValueError): evidence(payload_digest='not-a-digest')
def test_direct_event_record_kind_mismatch_fails():
    e=ConstructionEvent.create(ledger_id='construction/P1',sequence_number=1,previous_chain_digest=GENESIS_CHAIN_DIGEST,trace_id='t',record=evidence(),actor_id='h',actor_type=ActorType.HUMAN,created_at=3)
    with pytest.raises(ValueError): replace(e,record_kind=ConstructionRecordKind.CLAIM.value)

def test_normalization_colliding_evidence_refs_fail_closed():
    ev=evidence()
    with pytest.raises(ValueError):
        ConstructionClaim.create(scope=scope(),subject_id='wall-1',predicate='installed',value_digest=D2,claimant_id='contractor-1',evidence_refs=(ev.evidence_id, f' {ev.evidence_id} '),measurement_class=MeasurementClass.EMPIRICAL,confidence=.8,authority_class=ConstructionAuthorityClass.CONTRACTOR,privacy_class=ConstructionPrivacyClass.PROJECT,created_at=2.0,expires_at=20.0)

def test_direct_unsorted_reference_tuple_is_rejected():
    ev=evidence(); c=claim(ev)
    with pytest.raises(ValueError): replace(c,evidence_refs=('z','a'),claim_id=c.claim_id,claim_digest=c.claim_digest)

def test_event_ledger_is_bound_to_project():
    with pytest.raises(ValueError): ConstructionEvent.create(ledger_id='construction/P2',sequence_number=1,previous_chain_digest=GENESIS_CHAIN_DIGEST,trace_id='t',record=evidence(),actor_id='h',actor_type=ActorType.HUMAN,created_at=3)

def test_event_duplicate_normalized_parent_refs_fail_closed():
    with pytest.raises(ValueError): ConstructionEvent.create(ledger_id='construction/P1',sequence_number=2,previous_chain_digest=D,trace_id='t',record=evidence(),actor_id='h',actor_type=ActorType.HUMAN,parent_event_ids=('event-1',' event-1 '),created_at=3)

def test_scope_rejects_reserved_delimiters():
    for value in ('P/1', 'P*1', 'P|1', 'P\\1'):
        with pytest.raises(ValueError):
            ConstructionScope(value)


def test_structured_state_keys_do_not_alias_delimiter_like_text():
    first = ConstructionEvidence.create(
        scope=scope(), subject_id='a|b', evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref='c', payload_digest=D, measurement_class=MeasurementClass.EMPIRICAL,
        confidence=.9, authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT, observed_at=1,
    )
    second = ConstructionEvidence.create(
        scope=scope(), subject_id='a', evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref='b|c', payload_digest=D, measurement_class=MeasurementClass.EMPIRICAL,
        confidence=.9, authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT, observed_at=1,
    )
    assert first.state_key != second.state_key


def test_event_cannot_predate_its_record():
    ev = evidence(observed_at=5, expires_at=20)
    with pytest.raises(ValueError):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number=1,
            previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='t', record=ev,
            actor_id='h', actor_type=ActorType.HUMAN, created_at=4,
        )


def test_non_genesis_event_requires_hex_chain_reference():
    with pytest.raises(ValueError):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number=2,
            previous_chain_digest='not-a-digest', trace_id='t', record=evidence(),
            actor_id='h', actor_type=ActorType.HUMAN, created_at=3,
        )


def test_normalized_reference_helpers_reject_non_strings():
    with pytest.raises(ValueError):
        claim(evidence_refs=(123,))

def test_work_package_scope_requires_zone():
    with pytest.raises(ValueError):
        ConstructionScope('P1', work_package_id='WP1')


def test_create_rejects_non_string_text_fields_instead_of_stringifying():
    with pytest.raises(ValueError):
        evidence(subject_id=123)
    with pytest.raises(ValueError):
        evidence(source_ref=123)
    ev = evidence()
    with pytest.raises(ValueError):
        ConstructionClaim.create(
            scope=scope(), subject_id='wall-1', predicate='installed',
            value_digest=D2, claimant_id=123, evidence_refs=(ev.evidence_id,),
            measurement_class=MeasurementClass.EMPIRICAL, confidence=.8,
            authority_class=ConstructionAuthorityClass.CONTRACTOR,
            privacy_class=ConstructionPrivacyClass.PROJECT, created_at=2.0,
        )


def test_create_rejects_noncanonical_uppercase_hex_digest():
    with pytest.raises(ValueError, match='lowercase'):
        evidence(payload_digest=D.upper())


def test_direct_enum_storage_alias_is_rejected_even_when_identity_would_match():
    item = evidence()
    with pytest.raises(ValueError, match='canonical string'):
        replace(item, evidence_class=ConstructionEvidenceClass.DOCUMENT)


def test_event_create_rejects_non_string_actor_and_trace_fields():
    item = evidence()
    with pytest.raises(ValueError):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number=1,
            previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id=123,
            record=item, actor_id='human', actor_type=ActorType.HUMAN,
            created_at=3.0,
        )
    with pytest.raises(ValueError):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number=1,
            previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='trace',
            record=item, actor_id=123, actor_type=ActorType.HUMAN,
            created_at=3.0,
        )


def test_persisted_contracts_reject_numeric_string_coercion():
    item = evidence()
    payload = item.to_dict()
    payload['confidence'] = '0.9'
    with pytest.raises(ValueError, match='canonical finite float'):
        ConstructionEvidence.from_dict(payload)

    payload = item.to_dict()
    payload['observed_at'] = '1.0'
    with pytest.raises(ValueError, match='canonical finite float'):
        ConstructionEvidence.from_dict(payload)


def test_persisted_event_rejects_string_sequence_number():
    item = ConstructionEvent.create(
        ledger_id='construction/P1', sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='trace',
        record=evidence(), actor_id='human', actor_type=ActorType.HUMAN,
        created_at=3.0,
    )
    payload = item.to_dict()
    payload['sequence_number'] = '1'
    with pytest.raises(ValueError, match='positive integer'):
        ConstructionEvent.from_dict(payload)


def test_create_rejects_boolean_or_string_numeric_aliases():
    with pytest.raises(ValueError, match='must be numeric'):
        evidence(confidence=True)
    with pytest.raises(ValueError, match='must be numeric'):
        evidence(observed_at='1.0')
    with pytest.raises(ValueError, match='sequence_number must be an integer'):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number='1',
            previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='trace',
            record=evidence(), actor_id='human', actor_type=ActorType.HUMAN,
            created_at=3.0,
        )


def test_create_rejects_non_enum_stringifiable_actor_type():
    class PretendsToBeHuman:
        def __str__(self):
            return 'HUMAN'

    with pytest.raises(ValueError, match='must be a string or ActorType'):
        ConstructionEvent.create(
            ledger_id='construction/P1', sequence_number=1,
            previous_chain_digest=GENESIS_CHAIN_DIGEST, trace_id='trace',
            record=evidence(), actor_id='human', actor_type=PretendsToBeHuman(),
            created_at=3.0,
        )

def test_review_hardening_scalar_reference_collections_fail_closed():
    item = evidence()
    payload = item.to_dict()
    payload["consent_refs"] = "consent-ref"
    with pytest.raises(ValueError, match="list or tuple"):
        ConstructionEvidence.from_dict(payload)

    claimed = claim(item)
    payload = claimed.to_dict()
    payload["evidence_refs"] = item.evidence_id
    with pytest.raises(ValueError, match="list or tuple"):
        ConstructionClaim.from_dict(payload)


def test_review_hardening_scope_rejects_falsy_non_string_components():
    for value in (None, False, 0):
        with pytest.raises(ValueError, match="must be a string"):
            ConstructionScope("P1", value)
        with pytest.raises(ValueError, match="must be a string"):
            ConstructionScope("P1", "Z1", value)


def test_review_hardening_event_rejects_invalid_record_before_dereference():
    item = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace",
        record=evidence(),
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=3.0,
    )
    with pytest.raises(ValueError, match="exact ConstructionClaim or ConstructionEvidence"):
        replace(item, record=object())


def test_review_hardening_policy_scope_omits_state_wildcards():
    item = evidence(scope=ConstructionScope("P1"))
    event = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace",
        record=item,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=3.0,
    )
    assert event.to_aura_event_envelope().policy_scope == "construction/P1"
