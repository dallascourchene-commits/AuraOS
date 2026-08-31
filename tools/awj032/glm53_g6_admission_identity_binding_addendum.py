"""G6 W3 addendum: preserve PR #769 admission-reuse identity into Gate-10 request.

D0 / HS1 / NONPROMOTING / STACKED ADDENDUM.

Exactly two foreign semantic parents remain those of canonical G6-v2 / PR #782:
- PR #769 generation-bound admission reuse.
- PR #727 operation/observer/backend provenance contract.

PR #782 correctly requires a current bounded-C2 reuse candidate plus operation
provenance before compiling an owner-host evidence request. Its base projection,
however, reduces PR #769 to a generic family/disposition/current-context summary.
PR #769's consequence-bearing receipt contains a stronger identity vector:
admission receipt digest, subject identity, source generation, evidence generation,
owner context, decision context, and reuse digest.

This addendum binds that exact vector to the already-compiled G6 request. It does
not authenticate a caller-supplied receipt; exact parent proof authentication stays
in hosted CI and future owner/runtime receipt authentication remains unpaid.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
from typing import Any

from tools.awj032.glm53_g6_gate10_owner_host_evidence_request import (
    COMPILED,
    G6RequestReceipt,
    OFFICIAL_REPOSITORY,
    PINNED_OFFICIAL_REVISION,
    SOURCE_SET_DIGEST,
)

SCHEMA = "AURA-GLM53-G6-ADMISSION-IDENTITY-BINDING-W3-v1"

REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
REUSE_SOURCE_BLOB = "d171d0938e469a4383490d1a691750c2068f21e7"
REUSE_TEST_BLOB = "58fad37a0f89853098fa3dbbe2f2a1771574e449"
REUSE_RUN = 33437612722
REUSE_JOB = 99637780915
REUSE_FAMILY = "GLM53_BOUNDED_C2_PROPOSAL"
REUSE_DISPOSITION = "REUSE_CANDIDATE"

PROV_HEAD = "293c59d7260372ccd3b9e8130b12979b052c3ed9"
PROV_SOURCE_BLOB = "98db548b6e8f7443b79d979eb0e177ac6aa68534"
PROV_RUN = 33416248604
PROV_JOB = 99567478616

IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED = "IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED"
HOLD_BASE_G6_REQUEST_REQUIRED = "HOLD_BASE_G6_REQUEST_REQUIRED"
HOLD_EXACT_REUSE_FAMILY_REQUIRED = "HOLD_EXACT_REUSE_FAMILY_REQUIRED"
HOLD_REUSE_CANDIDATE_REQUIRED = "HOLD_REUSE_CANDIDATE_REQUIRED"
HOLD_REUSE_IDENTITY_REQUIRED = "HOLD_REUSE_IDENTITY_REQUIRED"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class AdmissionReuseIdentityProjection:
    """Lossless consequence-bearing projection of a PR #769 reuse candidate."""

    proof_head: str
    proof_run: int
    proof_job: int
    source_blob: str
    test_blob: str
    admission_family: str
    disposition: str
    admission_receipt_digest: str
    reuse_digest: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    candidate_only: bool = True
    admission_reused_as_authority: bool = False
    source_currentness_proven: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        if (
            self.proof_head,
            self.proof_run,
            self.proof_job,
            self.source_blob,
            self.test_blob,
        ) != (
            REUSE_HEAD,
            REUSE_RUN,
            REUSE_JOB,
            REUSE_SOURCE_BLOB,
            REUSE_TEST_BLOB,
        ):
            raise ValueError("REUSE_PARENT_PROOF_COORDINATE_MISMATCH")
        _digest(self.admission_receipt_digest, "ADMISSION_RECEIPT_DIGEST_INVALID")
        _digest(self.reuse_digest, "REUSE_DIGEST_INVALID")
        for value, code in (
            (self.admission_family, "ADMISSION_FAMILY_REQUIRED"),
            (self.disposition, "REUSE_DISPOSITION_REQUIRED"),
            (self.subject_identity, "SUBJECT_IDENTITY_REQUIRED"),
            (self.source_generation_key, "SOURCE_GENERATION_KEY_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED"),
            (self.owner_context_key, "OWNER_CONTEXT_KEY_REQUIRED"),
            (self.decision_context_key, "DECISION_CONTEXT_KEY_REQUIRED"),
        ):
            _text(value, code)
        if self.candidate_only is not True:
            raise ValueError("REUSE_MUST_REMAIN_CANDIDATE_ONLY")
        if any(
            (
                self.admission_reused_as_authority,
                self.source_currentness_proven,
                self.execution_authorized,
                self.effect_authorized,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
            )
        ):
            raise ValueError("REUSE_IDENTITY_PROJECTION_EXCEEDS_PARENT_CEILING")

    @property
    def identity_digest(self) -> str:
        self.validate_shape()
        return _sha(
            {
                "domain": SCHEMA,
                "family": self.admission_family,
                "admission_receipt_digest": self.admission_receipt_digest,
                "reuse_digest": self.reuse_digest,
                "subject_identity": self.subject_identity,
                "source_generation_key": self.source_generation_key,
                "evidence_generation_key": self.evidence_generation_key,
                "owner_context_key": self.owner_context_key,
                "decision_context_key": self.decision_context_key,
            }
        )


@dataclass(frozen=True)
class G6AdmissionIdentityBindingReceipt:
    schema: str
    disposition: str
    reason_code: str
    base_g6_request_digest: str
    admission_reuse_identity_digest: str
    admission_receipt_digest: str
    reuse_digest: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    binding_digest: str
    exact_glm53_reuse_family_bound: bool
    exact_reuse_candidate_identity_bound: bool
    base_g6_request_compiled: bool
    reuse_receipt_authenticated_by_this_contract: bool = False
    source_currentness_proven_by_this_contract: bool = False
    owner_authenticated_by_this_contract: bool = False
    tensor_payload_bound: bool = False
    model_or_provider_execution_observed: bool = False
    physical_io_proven: bool = False
    observer_backend_authenticated: bool = False
    auraos_resident_routing_proven: bool = False
    replay_recovery_proven: bool = False
    execution_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G6_IDENTITY_BINDING_SCHEMA_MISMATCH")
        _digest(self.base_g6_request_digest, "BASE_G6_REQUEST_DIGEST_INVALID")
        _digest(self.admission_reuse_identity_digest, "ADMISSION_REUSE_IDENTITY_DIGEST_INVALID")
        _digest(self.admission_receipt_digest, "BOUND_ADMISSION_RECEIPT_DIGEST_INVALID")
        _digest(self.reuse_digest, "BOUND_REUSE_DIGEST_INVALID")
        _digest(self.binding_digest, "G6_IDENTITY_BINDING_DIGEST_INVALID")
        for value, code in (
            (self.subject_identity, "BOUND_SUBJECT_IDENTITY_REQUIRED"),
            (self.source_generation_key, "BOUND_SOURCE_GENERATION_REQUIRED"),
            (self.evidence_generation_key, "BOUND_EVIDENCE_GENERATION_REQUIRED"),
            (self.owner_context_key, "BOUND_OWNER_CONTEXT_REQUIRED"),
            (self.decision_context_key, "BOUND_DECISION_CONTEXT_REQUIRED"),
        ):
            _text(value, code)

        if self.disposition == IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED:
            if not (
                self.base_g6_request_compiled
                and self.exact_glm53_reuse_family_bound
                and self.exact_reuse_candidate_identity_bound
            ):
                raise ValueError("IDENTITY_BOUND_POSITIVE_STATE_INVALID")
        else:
            raise ValueError("G6_IDENTITY_BINDING_DISPOSITION_INVALID")

        forbidden = (
            self.reuse_receipt_authenticated_by_this_contract,
            self.source_currentness_proven_by_this_contract,
            self.owner_authenticated_by_this_contract,
            self.tensor_payload_bound,
            self.model_or_provider_execution_observed,
            self.physical_io_proven,
            self.observer_backend_authenticated,
            self.auraos_resident_routing_proven,
            self.replay_recovery_proven,
            self.execution_authorized,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("G6_IDENTITY_BINDING_CANNOT_WIDEN_AUTHORITY_OR_TRUTH")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def bind_g6_request_to_admission_identity(
    *,
    base_request: G6RequestReceipt,
    reuse_identity: AdmissionReuseIdentityProjection,
) -> G6AdmissionIdentityBindingReceipt:
    """Bind the complete PR #769 identity vector to one compiled G6 request.

    A successful return proves deterministic identity preservation only. It does
    not authenticate who produced the reuse receipt or establish source/currentness,
    execution, observation, or Gate-10 truth.
    """

    base_request.validate_claim_ceiling()
    reuse_identity.validate_shape()

    if not (
        base_request.disposition == COMPILED
        and base_request.request_envelope_compiled
        and base_request.current_reuse_candidate_bound
        and base_request.operation_provenance_contract_bound
    ):
        raise ValueError(HOLD_BASE_G6_REQUEST_REQUIRED)
    if reuse_identity.admission_family != REUSE_FAMILY:
        raise ValueError(HOLD_EXACT_REUSE_FAMILY_REQUIRED)
    if reuse_identity.disposition != REUSE_DISPOSITION:
        raise ValueError(HOLD_REUSE_CANDIDATE_REQUIRED)

    if (
        base_request.official_repository,
        base_request.pinned_official_revision,
        base_request.source_set_digest,
    ) != (OFFICIAL_REPOSITORY, PINNED_OFFICIAL_REVISION, SOURCE_SET_DIGEST):
        raise ValueError("BASE_G6_FLAGSHIP_SOURCE_IDENTITY_MISMATCH")

    identity_digest = reuse_identity.identity_digest
    binding_digest = _sha(
        {
            "domain": SCHEMA,
            "base_g6_request_digest": base_request.request_digest,
            "admission_reuse_identity_digest": identity_digest,
            "admission_receipt_digest": reuse_identity.admission_receipt_digest,
            "reuse_digest": reuse_identity.reuse_digest,
            "subject_identity": reuse_identity.subject_identity,
            "source_generation_key": reuse_identity.source_generation_key,
            "evidence_generation_key": reuse_identity.evidence_generation_key,
            "owner_context_key": reuse_identity.owner_context_key,
            "decision_context_key": reuse_identity.decision_context_key,
        }
    )

    receipt = G6AdmissionIdentityBindingReceipt(
        schema=SCHEMA,
        disposition=IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED,
        reason_code="EXACT_PR769_REUSE_IDENTITY_VECTOR_BOUND_TO_G6_REQUEST_EXTERNAL_RECEIPT_AUTH_REQUIRED",
        base_g6_request_digest=base_request.request_digest,
        admission_reuse_identity_digest=identity_digest,
        admission_receipt_digest=reuse_identity.admission_receipt_digest,
        reuse_digest=reuse_identity.reuse_digest,
        subject_identity=reuse_identity.subject_identity,
        source_generation_key=reuse_identity.source_generation_key,
        evidence_generation_key=reuse_identity.evidence_generation_key,
        owner_context_key=reuse_identity.owner_context_key,
        decision_context_key=reuse_identity.decision_context_key,
        binding_digest=binding_digest,
        exact_glm53_reuse_family_bound=True,
        exact_reuse_candidate_identity_bound=True,
        base_g6_request_compiled=True,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_identity_binding_lattice() -> int:
    """Exhaust summary conditions; only all-true can reach the binding operation."""
    checked = 0
    for base_ok, family_ok, disposition_ok, identity_complete in itertools.product(
        (False, True), repeat=4
    ):
        if not base_ok:
            expected = HOLD_BASE_G6_REQUEST_REQUIRED
        elif not family_ok:
            expected = HOLD_EXACT_REUSE_FAMILY_REQUIRED
        elif not disposition_ok:
            expected = HOLD_REUSE_CANDIDATE_REQUIRED
        elif not identity_complete:
            expected = HOLD_REUSE_IDENTITY_REQUIRED
        else:
            expected = IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED
        if expected not in (
            HOLD_BASE_G6_REQUEST_REQUIRED,
            HOLD_EXACT_REUSE_FAMILY_REQUIRED,
            HOLD_REUSE_CANDIDATE_REQUIRED,
            HOLD_REUSE_IDENTITY_REQUIRED,
            IDENTITY_BOUND_EXTERNAL_AUTH_REQUIRED,
        ):
            raise AssertionError("G6_IDENTITY_BINDING_LATTICE_INVALID")
        checked += 1
    return checked


LAWS = (
    "AdmissionValidAtProduce!=AdmissionReusableAtUse",
    "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
    "GLM53AdmissionFamilyMustRemainExact",
    "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+Decision+ReuseDigestMustSurviveProjection",
    "IdentityBinding!=ReceiptProducerAuthentication",
    "IdentityBinding!=SourceCurrentnessTruth",
    "CallerWitness!=BackendObservationProvenance",
    "RequestEnvelopeCompiled!=TensorPayloadBound!=ExecutionObserved",
    "RepoHeadChanged!=TensorSourceGenerationChanged",
    "Gate10DebtMustRemainExplicitUntilObserved",
    "K27Coordinate!=SemanticIdentity!=RuntimeTruth!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
