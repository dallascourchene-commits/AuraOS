import inspect
from contextlib import contextmanager
from dataclasses import replace

import pytest

from tools.awj032 import glm53_official_mtp_role_source_appraiser as appraiser
from tools.awj032 import glm53_registered_mtp_role_appraiser as r
from tools.awj032 import glm53_pr340_producer_snapshot as snapshot
from tools.awj032 import test_glm53_official_mtp_role_source_appraiser as legacy_tests


def pin_for(report):
    return r.PR340ProducerRegistryPin(
        final_report_digest=snapshot.final_source_bound_report_digest(report),
        snapshot_digest="e" * 64,
        classification_stage_logical_id=report["logical_id"],
        producer_base_head=appraiser.PR340_PRODUCER_SEMANTIC_GENERATION,
        producer_execution_head="d" * 40,
        run_id=101,
        job_id=202,
        model_revision=report["model_revision"],
        index_sha256=report["index_sha256"],
        source_bundle_id=report["source_bundle_id"],
        config_parsed_sha256=report["config_parsed_sha256"],
        index_parsed_sha256=report["index_parsed_sha256"],
        weight_map_digest=report["weight_map_digest"],
        blocker_set=tuple(report["blockers"]),
        registry_receipt_ref="drive:test-independent-registry",
    )


@contextmanager
def synthetic_control():
    evidence = legacy_tests.observe_synthetic()
    report = legacy_tests.producer_report_for(evidence)
    pin = pin_for(report)
    old_pin = r.CANONICAL_PR340_PRODUCER_PIN
    old_index = appraiser.OFFICIAL_INDEX_SHA256
    r.CANONICAL_PR340_PRODUCER_PIN = pin
    appraiser.OFFICIAL_INDEX_SHA256 = evidence.index_sha256
    try:
        yield report, evidence, pin
    finally:
        r.CANONICAL_PR340_PRODUCER_PIN = old_pin
        appraiser.OFFICIAL_INDEX_SHA256 = old_index


def test_canonical_public_api_has_no_caller_expected_producer_parameters():
    names = set(inspect.signature(r.verify_and_admit_registered_official_mtp_role).parameters)
    assert names == {"report", "read_full"}
    with pytest.raises(TypeError):
        r.verify_and_admit_registered_official_mtp_role(
            {}, expected_pr340_logical_id="f" * 64
        )


def test_exact_registered_report_admits_only_mtp_provenance():
    with synthetic_control() as (report, evidence, pin):
        out = r._apply_registered_official_mtp_role(report, evidence)
    assert out["status"] == "READY_FOR_HEADER_AND_TINY_FIXTURE"
    assert out["blockers"] == []
    assert out["extra_layer_resolver_provenance_proven"] is True
    assert out["pr340_final_report_registry_proven"] is True
    assert out["pr340_final_report_digest"] == pin.final_report_digest
    assert out["pr340_registry_receipt_ref"] == pin.registry_receipt_ref
    assert out["pr340_registry_producer_execution_head"] == pin.producer_execution_head
    assert out["g2_admitted"] is False
    assert out["large_checkpoint_admitted"] is False
    assert out["runtime_execution_proven"] is False


def test_public_wrapper_observes_source_then_consumes_registry_without_expected_args():
    config_raw, index_raw = legacy_tests.sources()
    evidence = legacy_tests.observe_synthetic()
    report = legacy_tests.producer_report_for(evidence)
    pin = pin_for(report)
    old_pin = r.CANONICAL_PR340_PRODUCER_PIN
    old_index = appraiser.OFFICIAL_INDEX_SHA256
    r.CANONICAL_PR340_PRODUCER_PIN = pin
    appraiser.OFFICIAL_INDEX_SHA256 = evidence.index_sha256
    try:
        out = r.verify_and_admit_registered_official_mtp_role(
            report,
            read_full=legacy_tests.reader_for(config_raw, index_raw),
        )
    finally:
        r.CANONICAL_PR340_PRODUCER_PIN = old_pin
        appraiser.OFFICIAL_INDEX_SHA256 = old_index
    assert out["pr340_final_report_registry_proven"] is True
    assert out["blockers"] == []


def test_final_source_bound_mutation_fails_even_when_legacy_logical_id_is_unchanged():
    with synthetic_control() as (report, _evidence, _pin):
        forged = dict(report)
        forged["source_binding_proven"] = False
        assert forged["logical_id"] == report["logical_id"]
        with pytest.raises(r.RegistryBoundMTPRoleError, match="PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH"):
            r.verify_registered_pr340_report(forged)


def test_caller_cannot_self_consistently_forge_blocker_set_against_registry():
    with synthetic_control() as (report, _evidence, _pin):
        forged = legacy_tests._with_producer_blockers(report, [])
        assert forged["logical_id"] != report["logical_id"]
        with pytest.raises(r.RegistryBoundMTPRoleError, match="PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH"):
            r.verify_registered_pr340_report(forged)


def test_legacy_logical_id_substitution_is_rejected_separately():
    with synthetic_control() as (report, _evidence, _pin):
        forged = dict(report)
        forged["logical_id"] = "f" * 64
        assert snapshot.final_source_bound_report_digest(forged) == snapshot.final_source_bound_report_digest(report)
        with pytest.raises(r.RegistryBoundMTPRoleError, match="PR340_REGISTRY_REPORT_FIELD_MISMATCH"):
            r.verify_registered_pr340_report(forged)


def test_stale_or_authority_widened_registry_pin_fails_closed():
    with synthetic_control() as (report, _evidence, pin):
        for changed, code in (
            (replace(pin, registry_current=False), "PR340_REGISTRY_PIN_STALE"),
            (replace(pin, authority=True), "PR340_REGISTRY_AUTHORITY_WIDENING_FORBIDDEN"),
            (replace(pin, g2_admitted=True), "PR340_REGISTRY_AUTHORITY_WIDENING_FORBIDDEN"),
        ):
            r.CANONICAL_PR340_PRODUCER_PIN = changed
            with pytest.raises(r.RegistryBoundMTPRoleError, match=code):
                r.verify_registered_pr340_report(report)
            r.CANONICAL_PR340_PRODUCER_PIN = pin


def test_wrong_registry_semantic_generation_fails_before_candidate_comparison():
    with synthetic_control() as (report, _evidence, pin):
        r.CANONICAL_PR340_PRODUCER_PIN = replace(pin, producer_base_head="f" * 40)
        with pytest.raises(r.RegistryBoundMTPRoleError, match="PR340_REGISTRY_SEMANTIC_GENERATION_MISMATCH"):
            r.verify_registered_pr340_report(report)


def test_effect_widening_cannot_borrow_registry_provenance():
    with synthetic_control() as (report, _evidence, _pin):
        forged = dict(report)
        forged["g2_admitted"] = True
        with pytest.raises(r.RegistryBoundMTPRoleError, match="PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH"):
            r.verify_registered_pr340_report(forged)


def test_production_registry_constants_match_independent_arena_pin():
    pin = r.PR340ProducerRegistryPin()
    assert pin.registry_receipt_ref == "drive:1Tb7F-vu_Rb8bImIQXscword8tRRpt_DawtJV9dMnKEw"
    assert pin.final_report_digest == "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9"
    assert pin.snapshot_digest == "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851"
    assert pin.classification_stage_logical_id == "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa"
    assert pin.producer_base_head == "6c1d65fceb084ea3cbe8a59b7e28818155788504"
    assert pin.producer_execution_head == "a120b0be445990a95476f2286bb75036039da7bb"
    assert pin.run_id == 33339511610
    assert pin.job_id == 99332466601
    assert pin.blocker_set == (appraiser.PROVENANCE_BLOCKER,)
    assert pin.authority is False and pin.g2_admitted is False and pin.runtime_execution_proven is False
