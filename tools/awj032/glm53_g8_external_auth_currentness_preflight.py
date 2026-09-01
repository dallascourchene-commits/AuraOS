#!/usr/bin/env python3
"""G8: compile an external-auth/currentness preflight from exact-green G7 x Q20.

D0 / HS1 / NONPROMOTING.

Exactly two terminal-green other-Agent semantic parents:
- G7 / PR #781: structural progress/admission match; parent producer authentication,
  presented currentness, and future read-currentness remain external debts.
- Q20 / PR #784: exact official GLM-5.3 revision revalidation candidate; the observed
  repository diff is metadata-only, while future effect-time source currentness remains
  explicitly unproven and must be re-read at the effect boundary.

This module does not authenticate either parent, re-read Hugging Face, bind tensor bytes,
execute a model, authorize a provider effect, or promote Gate 10. It compiles only the
bounded request that a later external authenticator/currentness reader must satisfy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import itertools
import json
from typing import Any

import tools.awj032.glm53_g7_progress_current_admission_handoff as g7
import tools.quantization.aura_glm53_q20_official_source_revision_revalidation as q20

SCHEMA = "AURA-GLM53-G8-EXTERNAL-AUTH-CURRENTNESS-PREFLIGHT-v1"
CONVERGENCE_COMMIT = "32492eea84f7fedbbd9c4af31ac4a5bb1ba14620"

G7_PROOF_HEAD = "8a065ad2f017d1c44b0d0da98f59fe5ba5a00af3"
G7_SOURCE_BLOB = "ca364b1dbb2b86b708ce554b21e0e00c13da9f5b"
G7_PROOF_RUN = 33441379499
G7_PROOF_JOB = 99650162512
G7_POSITIVE = "STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED"

Q20_PROOF_HEAD = "2c7f42adf18a7421d7d4d21fb78a37a88445f82f"
Q20_SOURCE_BLOB = "27f8572edad81d3bdb680c116270a9abcfbce9cf"
Q20_PROOF_RUN = 33481589083
Q20_PROOF_JOB = 99772192034
Q20_POSITIVE = q20.CANDIDATE

OFFICIAL_SOURCE_URI = "https://huggingface.co/zai-org/GLM-5.3"

COMPILED = "GATE10_EXTERNAL_AUTH_CURRENTNESS_PREFLIGHT_REQUEST_COMPILED"
HOLD_G7 = "HOLD_G7_STRUCTURAL_CANDIDATE_REQUIRED"
HOLD_Q20 = "HOLD_Q20_SOURCE_REVALIDATION_CANDIDATE_REQUIRED"
HOLD_SOURCE_VIEW = "HOLD_G7_Q20_SOURCE_VIEW_RELATION_REQUIRED"
HOLD_DEBT = "HOLD_EXTERNAL_AUTH_CURRENTNESS_DEBT_PRESERVATION_REQUIRED"
HOLD_TARGET = "HOLD_EXTERNAL_AUTH_CURRENTNESS_TARGET_REQUIRED"
HOLD_EVIDENCE = "HOLD_REQUIRED_AUTH_CURRENTNESS_EVIDENCE_SET_REQUIRED"
HOLD_CEILING = "HOLD_G8_CLAIM_CEILING"

REQUIRED_EVIDENCE = (
    "G7_PARENT_PRODUCER_AUTHENTICATION",
    "G7_PRESENTED_CURRENTNESS_AUTHENTICATION",
    "FUTURE_READ_CURRENTNESS_AUTHENTICATION",
    "EFFECT_TIME_OFFICIAL_SOURCE_HEAD_REREAD",
    "EFFECT_TIME_Q20_OBSERVATION_SUPERSESSION_CHECK",
    "OWNER_PRINCIPAL_GENERATION_AUTHENTICATION",
    "AUTHENTICATOR_AND_CURRENTNESS_READER_PROVENANCE",
    "AUTH_CURRENTNESS_RESULT_RECEIPT_DIGEST",
)

OPEN_DOWNSTREAM_DEBT = (
    "TENSOR_PAYLOAD_BINDING",
    "REAL_QUANTIZATION_OR_MODEL_EXECUTION",
    "OWNER_HOST_PHYSICAL_OBSERVATION",
    "AURAOS_RESIDENT_ROUTING",
    "REPLAY_RECOVERY_PROOF",
    "GATE10_SYNTHESIS_AND_PROMOTION",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _valid_digest(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _nonempty(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class ExternalAuthCurrentnessTarget:
    principal_ref: str
    principal_generation: str
    authenticator_ref: str
    currentness_reader_ref: str
    evidence_sink_ref: str
    replay_contract_digest: str
    required_evidence: tuple[str, ...] = REQUIRED_EVIDENCE
    producer_authenticated_by_request: bool = False
    presented_currentness_proven_by_request: bool = False
    future_read_currentness_proven_by_request: bool = False
    effect_time_source_currentness_proven_by_request: bool = False
    execution_authorized_by_request: bool = False
    effect_authorized_by_request: bool = False
    gate10_promoted_by_request: bool = False

    def validate(self) -> None:
        if self.replay_contract_digest and not _valid_digest(self.replay_contract_digest):
            raise ValueError("REPLAY_CONTRACT_DIGEST_INVALID")
        if any(
            (
                self.producer_authenticated_by_request,
                self.presented_currentness_proven_by_request,
                self.future_read_currentness_proven_by_request,
                self.effect_time_source_currentness_proven_by_request,
                self.execution_authorized_by_request,
                self.effect_authorized_by_request,
                self.gate10_promoted_by_request,
            )
        ):
            raise ValueError("G8_TARGET_CANNOT_SELF_SATISFY_AUTH_CURRENTNESS_OR_AUTHORITY")

    @property
    def complete(self) -> bool:
        return all(
            _nonempty(value)
            for value in (
                self.principal_ref,
                self.principal_generation,
                self.authenticator_ref,
                self.currentness_reader_ref,
                self.evidence_sink_ref,
            )
        ) and _valid_digest(self.replay_contract_digest)


@dataclass(frozen=True)
class G8PreflightReceipt:
    disposition: str
    reason: str
    request_digest: str
    preflight_request_compiled: bool
    g7_handoff_receipt_digest: str
    q20_source_revalidation_receipt_digest: str
    structural_subject_identity: str
    structural_evidence_generation_key: str
    structural_material_digest: str
    structural_source_generation_key: str
    source_view_uri: str
    q20_observed_revision: str
    q20_retrieval_epoch: str
    required_evidence: tuple[str, ...]
    open_downstream_debt: tuple[str, ...]
    principal_ref: str
    principal_generation: str
    authenticator_ref: str
    currentness_reader_ref: str
    evidence_sink_ref: str
    replay_contract_digest: str
    exact_g7_parent_bound: bool
    exact_q20_parent_bound: bool
    source_view_relation_bound: bool
    parent_debts_preserved: bool
    parent_producer_authenticated: bool = False
    presented_currentness_authenticated: bool = False
    future_read_currentness_proven: bool = False
    effect_time_source_head_observed: bool = False
    effect_time_source_currentness_proven: bool = False
    q20_observation_still_current_at_effect: bool = False
    tensor_payload_bound: bool = False
    source_truth_proven: bool = False
    evidence_admitted: bool = False
    owner_host_execution_observed: bool = False
    physical_io_proven: bool = False
    auraos_resident_routing_proven: bool = False
    replay_recovery_proven: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if (self.disposition == COMPILED) != self.preflight_request_compiled:
            raise ValueError("G8_DISPOSITION_BOOLEAN_MISMATCH")
        if self.preflight_request_compiled and not (
            self.exact_g7_parent_bound
            and self.exact_q20_parent_bound
            and self.source_view_relation_bound
            and self.parent_debts_preserved
            and self.required_evidence == REQUIRED_EVIDENCE
            and self.open_downstream_debt == OPEN_DOWNSTREAM_DEBT
        ):
            raise ValueError("G8_COMPILED_REQUEST_MISSING_REQUIRED_BINDING")
        if any(
            (
                self.parent_producer_authenticated,
                self.presented_currentness_authenticated,
                self.future_read_currentness_proven,
                self.effect_time_source_head_observed,
                self.effect_time_source_currentness_proven,
                self.q20_observation_still_current_at_effect,
                self.tensor_payload_bound,
                self.source_truth_proven,
                self.evidence_admitted,
                self.owner_host_execution_observed,
                self.physical_io_proven,
                self.auraos_resident_routing_proven,
                self.replay_recovery_proven,
                self.execution_authorized,
                self.effect_authorized,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
                self.merge_deploy_spend_public_financial_human_effect,
            )
        ):
            raise ValueError("G8_EXCEEDED_NONPROMOTION_CEILING")


@dataclass(frozen=True)
class _Flags:
    g7_structural: bool
    q20_candidate: bool
    source_view_relation: bool
    debts_preserved: bool
    target_complete: bool
    evidence_exact: bool
    ceiling: bool


def _tree(flags: _Flags) -> str:
    if not flags.g7_structural:
        return HOLD_G7
    if not flags.q20_candidate:
        return HOLD_Q20
    if not flags.source_view_relation:
        return HOLD_SOURCE_VIEW
    if not flags.debts_preserved:
        return HOLD_DEBT
    if not flags.target_complete:
        return HOLD_TARGET
    if not flags.evidence_exact:
        return HOLD_EVIDENCE
    if not flags.ceiling:
        return HOLD_CEILING
    return COMPILED


def _table(flags: _Flags) -> str:
    rows = (
        (not flags.g7_structural, HOLD_G7),
        (not flags.q20_candidate, HOLD_Q20),
        (not flags.source_view_relation, HOLD_SOURCE_VIEW),
        (not flags.debts_preserved, HOLD_DEBT),
        (not flags.target_complete, HOLD_TARGET),
        (not flags.evidence_exact, HOLD_EVIDENCE),
        (not flags.ceiling, HOLD_CEILING),
        (True, COMPILED),
    )
    return next(disposition for predicate, disposition in rows if predicate)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=7):
        flags = _Flags(*bits)
        if _tree(flags) != _table(flags):
            raise AssertionError("G8_DIFFERENT_J_CLASSIFIERS_DIVERGED")
        checked += 1
    return checked


def _validate_parent_semantic_constants() -> None:
    if g7.SCHEMA != "AURA-GLM53-G7-PROGRESS-ADMISSION-STRUCTURAL-HANDOFF-v2":
        raise RuntimeError("G7_SCHEMA_DRIFT")
    if q20.SCHEMA != "AURA_GLM53_Q20_OFFICIAL_SOURCE_REVISION_REVALIDATION_V1":
        raise RuntimeError("Q20_SCHEMA_DRIFT")
    if q20.OFFICIAL_REPOSITORY != "zai-org/GLM-5.3":
        raise RuntimeError("Q20_OFFICIAL_REPOSITORY_DRIFT")


def compile_external_auth_currentness_preflight(
    *,
    progress: g7.ProgressBoundHandoffProjectionV2,
    reuse: g7.AdmissionReuseProjectionV2,
    presented: g7.PresentedHandoffUseContextV2,
    q20_q18: q20.Q18Projection,
    q20_observation: q20.OfficialSourceRevisionObservation,
    target: ExternalAuthCurrentnessTarget,
) -> G8PreflightReceipt:
    """Compile a request for external auth/currentness evidence; never satisfy it here."""
    _validate_parent_semantic_constants()
    target.validate()

    g7_receipt = g7.bind_progress_admission_structural_handoff(
        progress=progress,
        reuse=reuse,
        presented=presented,
    )
    q20_receipt = q20.assess_official_source_revision(
        q18=q20_q18,
        observation=q20_observation,
    )

    g7_ok = (
        g7_receipt.structural_candidate
        and g7_receipt.disposition.value == G7_POSITIVE
    )
    q20_ok = q20_receipt.get("disposition") == Q20_POSITIVE
    source_view_ok = (
        g7_receipt.exact_source_uri == OFFICIAL_SOURCE_URI
        and q20_receipt.get("official_repository") == q20.OFFICIAL_REPOSITORY
    )
    debts_ok = (
        g7_receipt.parent_projection_authentication_required
        and not g7_receipt.parent_projection_authenticated_by_this_contract
        and g7_receipt.presented_currentness_authentication_required
        and not g7_receipt.presented_currentness_authenticated_by_this_contract
        and g7_receipt.future_read_currentness_required
        and not g7_receipt.future_read_currentness_proven
        and q20_receipt.get("future_effect_source_revalidation_required") is True
        and q20_receipt.get("source_currentness_at_future_effect_proven") is False
        and q20_receipt.get("tensor_payload_bound") is False
        and q20_receipt.get("model_execution_observed") is False
        and q20_receipt.get("gate10_promoted") is False
    )
    flags = _Flags(
        g7_structural=g7_ok,
        q20_candidate=q20_ok,
        source_view_relation=source_view_ok,
        debts_preserved=debts_ok,
        target_complete=target.complete,
        evidence_exact=target.required_evidence == REQUIRED_EVIDENCE,
        ceiling=True,
    )
    disposition = _tree(flags)
    if disposition != _table(flags):
        raise RuntimeError("G8_RUNTIME_DIFFERENT_J_DIVERGED")

    reason = {
        COMPILED: "exact-green G7 structural match and Q20 source-revalidation candidate are bound into a nonexecuting request for external producer/currentness evidence",
        HOLD_G7: "exact G7 structural progress/admission candidate required",
        HOLD_Q20: "exact Q20 official-source revalidation candidate required",
        HOLD_SOURCE_VIEW: "G7 source view and Q20 official repository namespace are not the same bounded source view",
        HOLD_DEBT: "one or more G7/Q20 external-auth or future-currentness debts were collapsed",
        HOLD_TARGET: "external authenticator/currentness-reader target is incomplete",
        HOLD_EVIDENCE: "required external auth/currentness evidence vocabulary changed",
        HOLD_CEILING: "G8 nonpromotion ceiling widened",
    }[disposition]

    body = {
        "schema": SCHEMA,
        "disposition": disposition,
        "parents": {
            "g7_proof_head": G7_PROOF_HEAD,
            "g7_source_blob": G7_SOURCE_BLOB,
            "g7_proof_run": G7_PROOF_RUN,
            "g7_proof_job": G7_PROOF_JOB,
            "q20_proof_head": Q20_PROOF_HEAD,
            "q20_source_blob": Q20_SOURCE_BLOB,
            "q20_proof_run": Q20_PROOF_RUN,
            "q20_proof_job": Q20_PROOF_JOB,
            "true_convergence_commit": CONVERGENCE_COMMIT,
        },
        "g7_handoff_receipt_digest": g7_receipt.handoff_receipt_digest,
        "q20_source_revalidation_receipt_digest": q20_receipt["receipt_digest"],
        "g7_structural_identity": {
            "subject_identity": g7_receipt.subject_identity,
            "evidence_generation_key": g7_receipt.evidence_generation_key,
            "material_digest": g7_receipt.material_digest,
            "source_generation_key": g7_receipt.source_generation_key,
            "exact_source_uri": g7_receipt.exact_source_uri,
        },
        "q20_observation_identity": {
            "observed_revision": q20_receipt["provider_observed_head_revision"],
            "retrieval_epoch": q20_receipt["retrieval_epoch"],
            "future_effect_source_revalidation_required": True,
        },
        "target": asdict(target),
        "open_downstream_debt": OPEN_DOWNSTREAM_DEBT,
    }

    ready = disposition == COMPILED
    receipt = G8PreflightReceipt(
        disposition=disposition,
        reason=reason,
        request_digest=_sha(body),
        preflight_request_compiled=ready,
        g7_handoff_receipt_digest=g7_receipt.handoff_receipt_digest,
        q20_source_revalidation_receipt_digest=str(q20_receipt["receipt_digest"]),
        structural_subject_identity=g7_receipt.subject_identity or "",
        structural_evidence_generation_key=g7_receipt.evidence_generation_key or "",
        structural_material_digest=g7_receipt.material_digest or "",
        structural_source_generation_key=g7_receipt.source_generation_key or "",
        source_view_uri=g7_receipt.exact_source_uri or "",
        q20_observed_revision=str(q20_receipt["provider_observed_head_revision"]),
        q20_retrieval_epoch=str(q20_receipt["retrieval_epoch"]),
        required_evidence=target.required_evidence,
        open_downstream_debt=OPEN_DOWNSTREAM_DEBT,
        principal_ref=target.principal_ref,
        principal_generation=target.principal_generation,
        authenticator_ref=target.authenticator_ref,
        currentness_reader_ref=target.currentness_reader_ref,
        evidence_sink_ref=target.evidence_sink_ref,
        replay_contract_digest=target.replay_contract_digest,
        exact_g7_parent_bound=g7_ok,
        exact_q20_parent_bound=q20_ok,
        source_view_relation_bound=source_view_ok,
        parent_debts_preserved=debts_ok,
    )
    receipt.validate_claim_ceiling()
    return receipt


def fixture_target() -> ExternalAuthCurrentnessTarget:
    return ExternalAuthCurrentnessTarget(
        principal_ref="owner-principal:glm53:gate10",
        principal_generation="principal-generation:1",
        authenticator_ref="authenticator:external:glm53",
        currentness_reader_ref="currentness-reader:huggingface:glm53",
        evidence_sink_ref="artifact:awj032:g8:auth-currentness-result",
        replay_contract_digest="8" * 64,
    )


def fixture_inputs() -> tuple[
    g7.ProgressBoundHandoffProjectionV2,
    g7.AdmissionReuseProjectionV2,
    g7.PresentedHandoffUseContextV2,
    q20.Q18Projection,
    q20.OfficialSourceRevisionObservation,
    ExternalAuthCurrentnessTarget,
]:
    progress, reuse, presented = g7.fixture()
    return (
        progress,
        reuse,
        presented,
        q20.current_q18_projection(),
        q20.observed_current_source_fixture(),
        fixture_target(),
    )


LAWS = (
    "StructuralMatch!=ParentProducerAuthentication",
    "PresentedUseContextMatch!=AuthenticatedCurrentness",
    "Q20SourceRevisionRevalidationCandidate!=EffectTimeSourceCurrentness",
    "ObservedHeadAtT0!=ObservedHeadAtEffectTime",
    "MetadataOnlyObservedDiff!=TensorPayloadBinding",
    "SameRepositoryView!=SameSourceGeneration!=TensorPayloadBinding",
    "PreflightRequestCompiled!=AuthCurrentnessEvidenceSatisfied",
    "AuthCurrentnessEvidenceSatisfied!=OwnerHostExecutionAuthority",
    "FutureReadCurrentnessMustBeObservedAtUseTime",
    "K27Coordinate!=SourceIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
