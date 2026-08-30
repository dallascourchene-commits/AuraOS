from dataclasses import replace
import pytest

from aura_materialization_admission_currentness import (
    AdmissionState,
    AdjudicationDisposition,
    ConsumerAdmissionObservationV1,
    ConsumerAdmissionResolverExpectationV1,
    ExecutionState,
    MaterializationReceiptV1,
    ResolvedConsumerAdmissionEvidenceV1,
    TransportClass,
    adjudicate,
    compile_consumer_observation,
    compile_materialization_receipt,
    logical_digest,
)


def mat(**overrides):
    base = dict(
        transport=TransportClass.GITHUB,
        producer_owner="codemap-owner",
        producer_generation="v2.1",
        policy_ref="policy://codemap/materialize",
        policy_generation="p7",
        parent_target_ref="H1",
        materialized_target_ref="H2",
        materialized_target_digest="sha256:h2",
        artifact_set_digest="sha256:artifacts",
        allowed_delta_digest="sha256:delta",
        currentness_ref="ref://heads/branch@H2",
        idempotency_key="idem-1",
        effect_receipt_ref="effect://push/1",
    )
    base.update(overrides)
    return MaterializationReceiptV1(**base)


def obs(**overrides):
    base = dict(
        consumer_owner="ci-owner",
        consumer_generation="ci-v3",
        observed_target_ref="H2",
        observed_target_digest="sha256:h2",
        idempotency_key="idem-1",
        consumer_currentness_ref="ci-current://H2",
        consumer_current=True,
        admission_state=AdmissionState.ADMITTED,
        admission_receipt_ref="admit://1",
    )
    base.update(overrides)
    return ConsumerAdmissionObservationV1(**base)


def expectation(**overrides):
    base = dict(
        resolver_ref="resolver://ci-currentness",
        resolver_generation="resolver-v4",
        consumer_owner="ci-owner",
        consumer_generation="ci-v3",
        consumer_currentness_ref="ci-current://H2",
        consumer_currentness_generation="currentness-v8",
    )
    base.update(overrides)
    return ConsumerAdmissionResolverExpectationV1(**base)


def evidence(**overrides):
    base = dict(
        resolver_ref="resolver://ci-currentness",
        resolver_generation="resolver-v4",
        consumer_owner="ci-owner",
        consumer_generation="ci-v3",
        consumer_currentness_ref="ci-current://H2",
        consumer_currentness_generation="currentness-v8",
        observed_target_ref="H2",
        observed_target_digest="sha256:h2",
        idempotency_key="idem-1",
        admission_receipt_ref="admit://1",
        admission_receipt_digest="sha256:admission",
        evidence_ref="evidence://ci/H2",
        resolved_current=True,
        resolved_admitted=True,
    )
    base.update(overrides)
    return ResolvedConsumerAdmissionEvidenceV1(**base)


def verified(m=None, o=None, e=None, x=None):
    return adjudicate(
        m or mat(),
        o or obs(),
        resolution_evidence=e or evidence(),
        resolver_expectation=x or expectation(),
    )


def test_materialized_without_observation():
    r = adjudicate(mat())
    assert r.disposition is AdjudicationDisposition.MATERIALIZED_NOT_ADMITTED
    assert not r.consumer_admitted_current
    assert not r.execution_observed


def test_raw_true_and_refs_do_not_mint_current_admission():
    r = adjudicate(mat(), obs())
    assert r.disposition is AdjudicationDisposition.EVIDENCE_REQUIRED
    assert not r.consumer_admitted_current


def test_exact_resolved_admission():
    r = verified()
    assert r.disposition is AdjudicationDisposition.CONSUMER_ADMITTED_CURRENT
    assert r.consumer_admitted_current
    assert not r.execution_observed


def test_execution_observed_requires_resolved_admission_and_stays_zero_quality():
    o = obs(execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec://1")
    assert adjudicate(mat(), o).disposition is AdjudicationDisposition.EVIDENCE_REQUIRED
    r = verified(o=o)
    assert r.disposition is AdjudicationDisposition.EXECUTION_OBSERVED
    assert r.execution_observed
    assert not r.quality_satisfied and not r.authority


@pytest.mark.parametrize(
    "state,expected",
    [
        (ExecutionState.FAILED, AdjudicationDisposition.EXECUTION_FAILED),
        (ExecutionState.RECONCILE_REQUIRED, AdjudicationDisposition.RECONCILE_REQUIRED),
    ],
)
def test_non_success_execution_states_are_separate(state, expected):
    r = verified(o=obs(execution_state=state, execution_receipt_ref="exec://x"))
    assert r.disposition is expected
    assert r.consumer_admitted_current
    assert not r.execution_observed


def test_refusal_needs_no_positive_evidence_credit():
    r = adjudicate(mat(), obs(admission_state=AdmissionState.REFUSED, admission_receipt_ref="refuse://1"))
    assert r.disposition is AdjudicationDisposition.CONSUMER_REFUSED
    assert not r.consumer_admitted_current


def test_duplicate_is_noop_not_credit():
    r = adjudicate(mat(), obs(admission_state=AdmissionState.DUPLICATE_NOOP, admission_receipt_ref="dup://1"))
    assert r.disposition is AdjudicationDisposition.DUPLICATE_NOOP_OBSERVED
    assert not r.consumer_admitted_current


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("idempotency_key", "wrong", AdjudicationDisposition.IDEMPOTENCY_MISMATCH),
        ("observed_target_ref", "H3", AdjudicationDisposition.ADMISSION_TARGET_MISMATCH),
        ("observed_target_digest", "sha256:wrong", AdjudicationDisposition.ADMISSION_TARGET_DIGEST_MISMATCH),
        ("consumer_current", False, AdjudicationDisposition.CURRENTNESS_REOPEN),
    ],
)
def test_observation_mismatch_classes_precede_resolution(field, value, expected):
    r = adjudicate(mat(), obs(**{field: value}))
    assert r.disposition is expected
    assert not r.consumer_admitted_current


def test_explicit_stale_reopen():
    r = adjudicate(mat(), obs(admission_state=AdmissionState.STALE_REOPEN, admission_receipt_ref=""))
    assert r.disposition is AdjudicationDisposition.CURRENTNESS_REOPEN


@pytest.mark.parametrize("transport", list(TransportClass))
def test_transport_neutral_verified_semantics(transport):
    r = verified(m=mat(transport=transport))
    assert r.disposition is AdjudicationDisposition.CONSUMER_ADMITTED_CURRENT
    assert not r.authority


@pytest.mark.parametrize(
    "field",
    ["consumer_admitted", "execution_observed", "quality_satisfied", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"],
)
def test_materialization_cannot_self_mint_authority(field):
    with pytest.raises(ValueError):
        mat(**{field: True})


@pytest.mark.parametrize("field", ["quality_claim", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"])
def test_consumer_cannot_self_mint_authority(field):
    with pytest.raises(ValueError):
        obs(**{field: True})


@pytest.mark.parametrize("field", ["quality_claim", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"])
def test_resolution_evidence_cannot_self_mint_authority(field):
    with pytest.raises(ValueError):
        evidence(**{field: True})


def test_resolver_expectation_cannot_mint_authority():
    with pytest.raises(ValueError):
        expectation(authority=True)


@pytest.mark.parametrize("value", ["true", 1, None])
def test_consumer_current_must_be_real_bool(value):
    with pytest.raises(ValueError):
        obs(consumer_current=value)


@pytest.mark.parametrize("field", ["resolved_current", "resolved_admitted"])
@pytest.mark.parametrize("value", ["true", 1, None])
def test_resolution_booleans_must_be_real_bool(field, value):
    with pytest.raises(ValueError):
        evidence(**{field: value})


def test_execution_requires_admission():
    with pytest.raises(ValueError):
        obs(admission_state=AdmissionState.NOT_OBSERVED, admission_receipt_ref="", execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec://1")


@pytest.mark.parametrize("state", [ExecutionState.EXECUTED, ExecutionState.FAILED, ExecutionState.RECONCILE_REQUIRED])
def test_nonempty_execution_receipt_required(state):
    with pytest.raises(ValueError):
        obs(execution_state=state, execution_receipt_ref="")


@pytest.mark.parametrize("state", [AdmissionState.ADMITTED, AdmissionState.REFUSED, AdmissionState.DUPLICATE_NOOP])
def test_nonempty_admission_receipt_required(state):
    with pytest.raises(ValueError):
        obs(admission_state=state, admission_receipt_ref="")


def test_unknown_transport_rejected():
    payload = mat().__dict__.copy()
    payload["transport"] = "TELEPATHY"
    with pytest.raises(ValueError):
        compile_materialization_receipt(payload)


def test_unknown_admission_rejected():
    payload = obs().__dict__.copy()
    payload["admission_state"] = "MAYBE"
    with pytest.raises(ValueError):
        compile_consumer_observation(payload)


def test_unknown_execution_rejected():
    payload = obs().__dict__.copy()
    payload["execution_state"] = "MAYBE"
    with pytest.raises(ValueError):
        compile_consumer_observation(payload)


@pytest.mark.parametrize(
    "field",
    ["producer_owner", "producer_generation", "policy_ref", "policy_generation", "parent_target_ref", "materialized_target_ref", "materialized_target_digest", "artifact_set_digest", "allowed_delta_digest", "currentness_ref", "idempotency_key", "effect_receipt_ref"],
)
def test_materialization_required_text(field):
    with pytest.raises(ValueError):
        mat(**{field: ""})


@pytest.mark.parametrize(
    "field",
    ["consumer_owner", "consumer_generation", "observed_target_ref", "observed_target_digest", "idempotency_key", "consumer_currentness_ref"],
)
def test_consumer_required_text(field):
    with pytest.raises(ValueError):
        obs(**{field: ""})


@pytest.mark.parametrize(
    "field",
    ["resolver_ref", "resolver_generation", "consumer_owner", "consumer_generation", "consumer_currentness_ref", "consumer_currentness_generation"],
)
def test_resolver_expectation_required_text(field):
    with pytest.raises(ValueError):
        expectation(**{field: ""})


@pytest.mark.parametrize(
    "field",
    ["resolver_ref", "resolver_generation", "consumer_owner", "consumer_generation", "consumer_currentness_ref", "consumer_currentness_generation", "observed_target_ref", "observed_target_digest", "idempotency_key", "admission_receipt_ref", "admission_receipt_digest", "evidence_ref"],
)
def test_resolution_evidence_required_text(field):
    with pytest.raises(ValueError):
        evidence(**{field: ""})


def test_schema_mismatch_materialization():
    with pytest.raises(ValueError):
        mat(schema="OLD")


def test_schema_mismatch_consumer():
    with pytest.raises(ValueError):
        obs(schema="OLD")


def test_schema_mismatch_expectation():
    with pytest.raises(ValueError):
        expectation(schema="OLD")


def test_schema_mismatch_evidence():
    with pytest.raises(ValueError):
        evidence(schema="OLD")


def test_digest_is_deterministic():
    a = mat()
    b = mat()
    assert a.receipt_digest == b.receipt_digest == logical_digest(a)


@pytest.mark.parametrize(
    "field,value",
    [("materialized_target_ref", "H9"), ("materialized_target_digest", "sha256:h9"), ("idempotency_key", "idem-9"), ("producer_generation", "v9"), ("policy_generation", "p9")],
)
def test_materialization_identity_changes_digest(field, value):
    a = mat()
    b = replace(a, **{field: value})
    assert a.receipt_digest != b.receipt_digest


@pytest.mark.parametrize(
    "field,value",
    [("consumer_generation", "ci-v4"), ("observed_target_ref", "H9"), ("observed_target_digest", "sha256:h9"), ("idempotency_key", "idem-9"), ("consumer_currentness_ref", "ci-current://H9")],
)
def test_observation_identity_changes_digest(field, value):
    a = obs()
    b = replace(a, **{field: value})
    assert a.receipt_digest != b.receipt_digest


@pytest.mark.parametrize(
    "e_over,x_over",
    [
        ({"resolver_ref": "resolver://other"}, {}),
        ({"resolver_generation": "resolver-v5"}, {}),
        ({"consumer_owner": "other-owner"}, {}),
        ({"consumer_generation": "ci-v4"}, {}),
        ({"consumer_currentness_ref": "ci-current://H9"}, {}),
        ({"consumer_currentness_generation": "currentness-v9"}, {}),
        ({"observed_target_ref": "H9"}, {}),
        ({"observed_target_digest": "sha256:h9"}, {}),
        ({"idempotency_key": "idem-9"}, {}),
        ({"admission_receipt_ref": "admit://2"}, {}),
        ({}, {"resolver_generation": "resolver-v5"}),
        ({}, {"consumer_generation": "ci-v4"}),
        ({}, {"consumer_currentness_generation": "currentness-v9"}),
    ],
)
def test_any_resolution_or_expectation_generation_mismatch_fails_closed(e_over, x_over):
    r = verified(e=evidence(**e_over), x=expectation(**x_over))
    assert r.disposition is AdjudicationDisposition.EVIDENCE_MISMATCH
    assert not r.consumer_admitted_current


def test_resolver_says_not_current_reopens():
    r = verified(e=evidence(resolved_current=False))
    assert r.disposition is AdjudicationDisposition.CURRENTNESS_REOPEN
    assert not r.consumer_admitted_current


def test_resolver_says_not_admitted_stays_evidence_required():
    r = verified(e=evidence(resolved_admitted=False))
    assert r.disposition is AdjudicationDisposition.EVIDENCE_REQUIRED
    assert not r.consumer_admitted_current


def test_mapping_compile_accepts_string_enums_but_does_not_create_resolved_evidence():
    m = mat().__dict__.copy()
    m["transport"] = "GITHUB"
    assert compile_materialization_receipt(m).transport is TransportClass.GITHUB
    o = obs().__dict__.copy()
    o["admission_state"] = "ADMITTED"
    o["execution_state"] = "NOT_OBSERVED"
    claim = compile_consumer_observation(o)
    assert claim.admission_state is AdmissionState.ADMITTED
    assert adjudicate(mat(), claim).disposition is AdjudicationDisposition.EVIDENCE_REQUIRED


def test_github_h1_h2_fixture_requires_exact_h2_resolver_evidence():
    m = mat(transport=TransportClass.GITHUB, parent_target_ref="8f8792e", materialized_target_ref="542a60b", materialized_target_digest="git-tree:dc60b44", idempotency_key="codemap:8f8792e->542a60b")
    o = obs(observed_target_ref="542a60b", observed_target_digest="git-tree:dc60b44", idempotency_key="codemap:8f8792e->542a60b", consumer_currentness_ref="ci-current://542a60b")
    assert adjudicate(m, o).disposition is AdjudicationDisposition.EVIDENCE_REQUIRED
    x = expectation(consumer_currentness_ref="ci-current://542a60b")
    e = evidence(observed_target_ref="542a60b", observed_target_digest="git-tree:dc60b44", idempotency_key="codemap:8f8792e->542a60b", consumer_currentness_ref="ci-current://542a60b")
    assert adjudicate(m, o, resolution_evidence=e, resolver_expectation=x).disposition is AdjudicationDisposition.CONSUMER_ADMITTED_CURRENT


def test_drive_bus_r2_fixture_requires_local_consumer_resolver_evidence():
    key = "AWJ032-GLM53-06-STRICT-D0-PAGER-CACHE-TRACE-BENCHMARK-20260830-R2"
    m = mat(transport=TransportClass.DRIVE_BUS, parent_target_ref="R1", materialized_target_ref="drive:R2", materialized_target_digest="sha256:r2-envelope", idempotency_key=key)
    o = obs(consumer_owner="aura-local-consumer", observed_target_ref="drive:R2", observed_target_digest="sha256:r2-envelope", idempotency_key=key, consumer_currentness_ref="local-current://R2")
    assert adjudicate(m, o).disposition is AdjudicationDisposition.EVIDENCE_REQUIRED
    x = expectation(consumer_owner="aura-local-consumer", consumer_currentness_ref="local-current://R2")
    e = evidence(consumer_owner="aura-local-consumer", observed_target_ref="drive:R2", observed_target_digest="sha256:r2-envelope", idempotency_key=key, consumer_currentness_ref="local-current://R2")
    assert adjudicate(m, o, resolution_evidence=e, resolver_expectation=x).disposition is AdjudicationDisposition.CONSUMER_ADMITTED_CURRENT


def test_policy_compatibility_fields_do_not_admit():
    assert adjudicate(mat(policy_ref="owner-policy://valid", policy_generation="current")).disposition is AdjudicationDisposition.MATERIALIZED_NOT_ADMITTED


def test_result_flags_always_nonpromoting():
    cases = [
        adjudicate(mat()),
        adjudicate(mat(), obs()),
        verified(),
        verified(o=obs(execution_state=ExecutionState.EXECUTED, execution_receipt_ref="exec://1")),
        adjudicate(mat(), obs(admission_state=AdmissionState.REFUSED, admission_receipt_ref="refuse://1")),
    ]
    for r in cases:
        assert not r.quality_satisfied
        assert not r.effect_authorized
        assert not r.promotion_authorized
        assert not r.merge_authorized
        assert not r.authority
