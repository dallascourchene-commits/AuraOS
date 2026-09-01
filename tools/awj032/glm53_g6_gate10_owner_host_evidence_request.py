"""G6: compile one current, identity-preserving owner-host Gate-10 evidence request.

D0 / HS1 / NONPROMOTING.

Exactly two terminal foreign semantic parents:
- PR #769 generation-bound admission reuse.
- PR #727 operation/observer/backend provenance contract.

Q18 / PR #761 is transitive lineage inherited through PR #769, not a third
Objective parent. PR #582 and PR #586 remain canonical downstream transport/return
owners and are compatibility constraints, not additional derivation parents.

This module is the single semantic owner for G6 request construction. It binds the
exact Q18 historical admission receipt, the full PR #769 current-use identity vector,
and the exact PR #769 reuse-digest relation directly into the request. There is no
post-hoc join between a caller-supplied precompiled request and a separate identity.

The module does not authenticate the projected PR #769 receipt producer, prove source
currentness, execute GLM-5.3, observe physical I/O, authorize effects, or promote Gate 10.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import itertools
import json
from typing import Any

SCHEMA = "AURA-GLM53-G6-GATE10-OWNER-HOST-EVIDENCE-REQUEST-v4"

REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
REUSE_SOURCE_BLOB = "d171d0938e469a4383490d1a691750c2068f21e7"
REUSE_TEST_BLOB = "58fad37a0f89853098fa3dbbe2f2a1771574e449"
REUSE_RUN = 33437612722
REUSE_JOB = 99637780915
REUSE_FAMILY = "GLM53_BOUNDED_C2_PROPOSAL"
REUSE_DISPOSITION = "REUSE_CANDIDATE"

PR769_SCHEMA = "AURA-GENERATION-BOUND-ADMISSION-REUSE-v1"
PR769_REUSE_REASON = "all identity-bearing producer/source/evidence/owner/decision axes remain exact"

# Q18 is transitive lineage carried through PR #769. Zero extra Objective-parent credit.
Q18_HEAD = "aed81432db8b84d2f43b8a85d06d4b72e16f6a50"
Q18_SOURCE_BLOB = "4cee26edaf0759fc80d31889ab9e4e268f9a4fbe"
Q18_RUN = 33436580962
Q18_JOB = 99634379758
Q18_RECEIPT_DIGEST = "c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230"

PROV_HEAD = "293c59d7260372ccd3b9e8130b12979b052c3ed9"
PROV_SOURCE_BLOB = "98db548b6e8f7443b79d979eb0e177ac6aa68534"
PROV_RUN = 33416248604
PROV_JOB = 99567478616

# Canonical downstream transport owners; zero derivation-parent credit here.
C2_HANDOFF_HEAD = "24a5404ee3b987dee12192917e40b35d3a43e81c"
C2_HANDOFF_RUN = 33360061584
LIFECYCLE_RETURN_HEAD = "aa3fcd9a4cefd18dbc991c3e8a450fcfbbb6726b"
LIFECYCLE_RETURN_RUN = 33360529366

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
PINNED_OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"

COMPILED = "OWNER_HOST_BOUNDED_C2_EVIDENCE_REQUEST_ENVELOPE_COMPILED"
HOLD_REUSE = "HOLD_EXACT_CURRENT_GLM53_REUSE_IDENTITY_REQUIRED"
HOLD_PROVENANCE = "HOLD_OPERATION_PROVENANCE_CONTRACT_REQUIRED"
HOLD_SOURCE = "HOLD_EXACT_FLAGSHIP_SOURCE_IDENTITY_REQUIRED"
HOLD_OWNER = "HOLD_OWNER_HOST_TARGET_REQUIRED"
HOLD_RESOURCE = "HOLD_RUNTIME_RESOURCE_GENERATIONS_REQUIRED"
HOLD_EVIDENCE = "HOLD_EVIDENCE_SINK_CONTRACT_REQUIRED"
HOLD_REPLAY = "HOLD_REPLAY_RECOVERY_CONTRACT_REQUIRED"
HOLD_DEBT = "HOLD_GATE10_DEBT_CARRY_REQUIRED"
HOLD_CEILING = "HOLD_CLAIM_CEILING"

REUSE_IDENTITY_OK = "EXACT_Q18_PR769_REUSE_IDENTITY_BOUND"
REUSE_HOLD_FAMILY = "REUSE_HOLD_EXACT_GLM53_FAMILY_REQUIRED"
REUSE_HOLD_DISPOSITION = "REUSE_HOLD_CANDIDATE_DISPOSITION_REQUIRED"
REUSE_HOLD_CURRENT = "REUSE_HOLD_CURRENT_CONTEXT_REQUIRED"
REUSE_HOLD_Q18_RECEIPT = "REUSE_HOLD_EXACT_Q18_ADMISSION_RECEIPT_REQUIRED"
REUSE_HOLD_DIGEST_RELATION = "REUSE_HOLD_PR769_REUSE_DIGEST_RELATION_REQUIRED"

REQUIRED_EVIDENCE_AXES = (
    "OFFICIAL_SOURCE_REVISION_REVALIDATION",
    "TENSOR_PAYLOAD_BINDING",
    "REAL_TENSOR_QUANTIZATION",
    "EXACT_OPERATION_IDENTITY",
    "OBSERVER_BACKEND_PROVENANCE",
    "OWNER_HOST_RUNTIME_GENERATIONS",
    "PHYSICAL_IO_METRICS",
    "OUTPUT_AND_RECEIPT_HASHES",
    "REPLAY_RECEIPT",
    "RECOVERY_RECEIPT",
)
OPEN_GATE10_DEBT = (
    "FULL_FLAGSHIP_MODEL_LOAD",
    "AURAOS_RESIDENT_ROUTING",
    "OWNER_HOST_END_TO_END_EXECUTION",
    "AUTHENTICATED_PHYSICAL_OBSERVATION",
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
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code).lower()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class AdmissionReuseProjection:
    """Lossless consequence-bearing projection of one PR #769 reuse receipt."""

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
    current_context_exact: bool
    candidate_only: bool = True
    reuse_receipt_authenticated_by_this_projection: bool = False
    source_currentness_proven: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False

    def validate_shape(self) -> None:
        if (
            self.proof_head,
            self.proof_run,
            self.proof_job,
            self.source_blob,
            self.test_blob,
        ) != (REUSE_HEAD, REUSE_RUN, REUSE_JOB, REUSE_SOURCE_BLOB, REUSE_TEST_BLOB):
            raise ValueError("REUSE_PARENT_PROOF_MISMATCH")
        _text(self.admission_family, "REUSE_FAMILY_REQUIRED")
        _text(self.disposition, "REUSE_DISPOSITION_REQUIRED")
        _digest(self.admission_receipt_digest, "ADMISSION_RECEIPT_DIGEST_INVALID")
        _digest(self.reuse_digest, "REUSE_DIGEST_INVALID")
        for value, code in (
            (self.subject_identity, "SUBJECT_IDENTITY_REQUIRED"),
            (self.source_generation_key, "SOURCE_GENERATION_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_REQUIRED"),
            (self.owner_context_key, "OWNER_CONTEXT_REQUIRED"),
            (self.decision_context_key, "DECISION_CONTEXT_REQUIRED"),
        ):
            _text(value, code)
        if not isinstance(self.current_context_exact, bool):
            raise ValueError("CURRENT_CONTEXT_EXACT_MUST_BE_BOOL")
        if self.candidate_only is not True:
            raise ValueError("REUSE_MUST_REMAIN_CANDIDATE_ONLY")
        if any(
            (
                self.reuse_receipt_authenticated_by_this_projection,
                self.source_currentness_proven,
                self.execution_authorized,
                self.effect_authorized,
                self.semantic_k27_authority,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
            )
        ):
            raise ValueError("REUSE_PROJECTION_EXCEEDS_PARENT_CEILING")

    @property
    def identity_digest(self) -> str:
        self.validate_shape()
        return _sha(
            {
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


def expected_pr769_reuse_digest(reuse: AdmissionReuseProjection) -> str:
    """Reproduce the exact PR #769 REUSE_CANDIDATE commitment.

    This proves structural consistency of the projected receipt. It does not
    authenticate the receipt producer or prove currentness by itself.
    """
    reuse.validate_shape()
    return _sha(
        {
            "schema": PR769_SCHEMA,
            "disposition": REUSE_DISPOSITION,
            "reason": PR769_REUSE_REASON,
            "family": reuse.admission_family,
            "admission_receipt_digest": reuse.admission_receipt_digest,
            "subject_identity": reuse.subject_identity,
            "source_generation_key": reuse.source_generation_key,
            "evidence_generation_key": reuse.evidence_generation_key,
            "owner_context_key": reuse.owner_context_key,
            "decision_context_key": reuse.decision_context_key,
            "claim_ceiling": {
                "candidate_only": True,
                "admission_reused_as_authority": False,
                "execution_authorized": False,
                "effect_authorized": False,
                "source_currentness_proven": False,
                "semantic_truth_proven": False,
                "semantic_k27_authority": False,
                "native_private_transformer_kv_accessed": False,
            },
        }
    )


def classify_reuse_identity(reuse: AdmissionReuseProjection) -> str:
    """Ordered current-use classification for the composite G6 reuse axis."""
    reuse.validate_shape()
    if reuse.admission_family != REUSE_FAMILY:
        return REUSE_HOLD_FAMILY
    if reuse.disposition != REUSE_DISPOSITION:
        return REUSE_HOLD_DISPOSITION
    if not reuse.current_context_exact:
        return REUSE_HOLD_CURRENT
    if reuse.admission_receipt_digest != Q18_RECEIPT_DIGEST:
        return REUSE_HOLD_Q18_RECEIPT
    if reuse.reuse_digest != expected_pr769_reuse_digest(reuse):
        return REUSE_HOLD_DIGEST_RELATION
    return REUSE_IDENTITY_OK


@dataclass(frozen=True)
class ObservationProvenanceContractProjection:
    proof_head: str
    proof_run: int
    proof_job: int
    source_blob: str
    exact_operation_binding_required: bool
    observer_backend_provenance_required: bool
    producer_authentication_required: bool
    tiny_fixture_is_glm53_evidence: bool = False
    physical_observation_proven: bool = False
    execution_authorized: bool = False

    def validate(self) -> None:
        if (self.proof_head, self.proof_run, self.proof_job, self.source_blob) != (
            PROV_HEAD,
            PROV_RUN,
            PROV_JOB,
            PROV_SOURCE_BLOB,
        ):
            raise ValueError("PROVENANCE_PROOF_MISMATCH")
        if self.tiny_fixture_is_glm53_evidence or self.physical_observation_proven or self.execution_authorized:
            raise ValueError("PROVENANCE_PROJECTION_EXCEEDS_CEILING")


@dataclass(frozen=True)
class SourceIdentityProjection:
    repository: str
    pinned_revision: str
    source_set_digest: str
    official_revision_revalidation_required: bool
    source_currentness_proven: bool = False
    tensor_payload_bound: bool = False

    def validate(self) -> None:
        _text(self.repository, "SOURCE_REPOSITORY")
        _text(self.pinned_revision, "SOURCE_REVISION")
        _digest(self.source_set_digest, "SOURCE_SET_DIGEST")
        if self.source_currentness_proven or self.tensor_payload_bound:
            raise ValueError("SOURCE_PROJECTION_EXCEEDS_CEILING")

    @property
    def exact_request_identity(self) -> bool:
        self.validate()
        return (
            self.repository == OFFICIAL_REPOSITORY
            and self.pinned_revision == PINNED_OFFICIAL_REVISION
            and self.source_set_digest == SOURCE_SET_DIGEST
            and self.official_revision_revalidation_required
        )


@dataclass(frozen=True)
class OwnerHostTargetProjection:
    owner_host_ref: str
    principal_generation: str
    host_profile_generation: str
    runtime_generation: str
    cache_generation: str
    storage_geometry_generation: str
    resource_envelope_digest: str
    evidence_sink_ref: str
    owner_authenticated_by_this_contract: bool = False
    execution_authorized_by_this_contract: bool = False

    def validate(self) -> None:
        for value, code in (
            (self.owner_host_ref, "OWNER"),
            (self.principal_generation, "PRINCIPAL"),
            (self.host_profile_generation, "HOST"),
            (self.runtime_generation, "RUNTIME"),
            (self.cache_generation, "CACHE"),
            (self.storage_geometry_generation, "STORAGE"),
            (self.evidence_sink_ref, "SINK"),
        ):
            _text(value, code)
        _digest(self.resource_envelope_digest, "RESOURCE_DIGEST")
        if self.owner_authenticated_by_this_contract or self.execution_authorized_by_this_contract:
            raise ValueError("OWNER_PROJECTION_EXCEEDS_CEILING")


@dataclass(frozen=True)
class EvidenceContractProjection:
    request_manifest_digest: str
    benchmark_harness_digest: str
    replay_contract_digest: str
    recovery_contract_digest: str
    required_evidence_axes: tuple[str, ...]
    open_gate10_debt: tuple[str, ...]
    official_revision_revalidation_required: bool
    actual_owner_host_evidence_already_observed: bool = False
    authenticated_physical_observation_already_proven: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        for value, code in (
            (self.request_manifest_digest, "MANIFEST"),
            (self.benchmark_harness_digest, "HARNESS"),
            (self.replay_contract_digest, "REPLAY"),
            (self.recovery_contract_digest, "RECOVERY"),
        ):
            _digest(value, code)
        if self.required_evidence_axes != REQUIRED_EVIDENCE_AXES:
            raise ValueError("EVIDENCE_AXES_MISMATCH")
        if self.open_gate10_debt != OPEN_GATE10_DEBT:
            raise ValueError("GATE10_DEBT_MISMATCH")
        if not self.official_revision_revalidation_required:
            raise ValueError("REVISION_REVALIDATION_REQUIRED")
        if (
            self.actual_owner_host_evidence_already_observed
            or self.authenticated_physical_observation_already_proven
            or self.gate10_promoted
        ):
            raise ValueError("EVIDENCE_CONTRACT_SELF_PROMOTION")


@dataclass(frozen=True)
class G6RequestReceipt:
    disposition: str
    reason: str
    reuse_identity_reason_code: str
    request_digest: str
    request_envelope_compiled: bool
    official_repository: str
    pinned_official_revision: str
    source_set_digest: str
    owner_host_ref: str
    required_evidence_axes: tuple[str, ...]
    open_gate10_debt: tuple[str, ...]
    current_reuse_candidate_bound: bool
    exact_glm53_reuse_identity_bound: bool
    exact_q18_admission_receipt_bound: bool
    pr769_reuse_digest_structurally_verified: bool
    admission_reuse_identity_digest: str
    admission_receipt_digest: str
    reuse_digest: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    operation_provenance_contract_bound: bool
    exact_source_request_identity_bound: bool
    single_owner_request_constructed_by_this_contract: bool = True
    caller_supplied_precompiled_request_accepted: bool = False
    official_revision_revalidation_required: bool = True
    canonical_c2_handoff_head: str = C2_HANDOFF_HEAD
    canonical_c2_handoff_run: int = C2_HANDOFF_RUN
    canonical_lifecycle_return_head: str = LIFECYCLE_RETURN_HEAD
    canonical_lifecycle_return_run: int = LIFECYCLE_RETURN_RUN
    reuse_receipt_authenticated_by_this_contract: bool = False
    source_currentness_proven_by_this_contract: bool = False
    tensor_payload_bound: bool = False
    real_tensor_quantization_observed: bool = False
    owner_host_execution_observed: bool = False
    full_flagship_model_loaded: bool = False
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
        if (self.disposition == COMPILED) != self.request_envelope_compiled:
            raise ValueError("DISPOSITION_BOOLEAN_MISMATCH")
        if self.caller_supplied_precompiled_request_accepted:
            raise ValueError("CALLER_SUPPLIED_PRECOMPILED_REQUEST_FORBIDDEN")
        if self.request_envelope_compiled and not (
            self.single_owner_request_constructed_by_this_contract
            and self.current_reuse_candidate_bound
            and self.exact_glm53_reuse_identity_bound
            and self.exact_q18_admission_receipt_bound
            and self.pr769_reuse_digest_structurally_verified
            and self.operation_provenance_contract_bound
            and self.exact_source_request_identity_bound
            and self.reuse_identity_reason_code == REUSE_IDENTITY_OK
            and self.admission_receipt_digest == Q18_RECEIPT_DIGEST
        ):
            raise ValueError("COMPILED_REQUEST_MISSING_REQUIRED_BINDING")
        if any(
            (
                self.reuse_receipt_authenticated_by_this_contract,
                self.source_currentness_proven_by_this_contract,
                self.tensor_payload_bound,
                self.real_tensor_quantization_observed,
                self.owner_host_execution_observed,
                self.full_flagship_model_loaded,
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
        ):
            raise ValueError("G6_EXCEEDED_CEILING")


@dataclass(frozen=True)
class _Flags:
    reuse: bool
    provenance: bool
    source: bool
    owner: bool
    resource: bool
    evidence: bool
    replay: bool
    debt: bool
    ceiling: bool


def _tree(flags: _Flags) -> str:
    if not flags.reuse:
        return HOLD_REUSE
    if not flags.provenance:
        return HOLD_PROVENANCE
    if not flags.source:
        return HOLD_SOURCE
    if not flags.owner:
        return HOLD_OWNER
    if not flags.resource:
        return HOLD_RESOURCE
    if not flags.evidence:
        return HOLD_EVIDENCE
    if not flags.replay:
        return HOLD_REPLAY
    if not flags.debt:
        return HOLD_DEBT
    if not flags.ceiling:
        return HOLD_CEILING
    return COMPILED


def _table(flags: _Flags) -> str:
    ordered = (
        (not flags.reuse, HOLD_REUSE),
        (not flags.provenance, HOLD_PROVENANCE),
        (not flags.source, HOLD_SOURCE),
        (not flags.owner, HOLD_OWNER),
        (not flags.resource, HOLD_RESOURCE),
        (not flags.evidence, HOLD_EVIDENCE),
        (not flags.replay, HOLD_REPLAY),
        (not flags.debt, HOLD_DEBT),
        (not flags.ceiling, HOLD_CEILING),
        (True, COMPILED),
    )
    return next(disposition for predicate, disposition in ordered if predicate)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=9):
        flags = _Flags(*bits)
        if _tree(flags) != _table(flags):
            raise AssertionError("G6_DIFFERENT_J_DIVERGED")
        checked += 1
    return checked


def _reuse_tree(
    family_ok: bool,
    disposition_ok: bool,
    current_ok: bool,
    q18_ok: bool,
    digest_ok: bool,
) -> str:
    if not family_ok:
        return REUSE_HOLD_FAMILY
    if not disposition_ok:
        return REUSE_HOLD_DISPOSITION
    if not current_ok:
        return REUSE_HOLD_CURRENT
    if not q18_ok:
        return REUSE_HOLD_Q18_RECEIPT
    if not digest_ok:
        return REUSE_HOLD_DIGEST_RELATION
    return REUSE_IDENTITY_OK


def _reuse_table(
    family_ok: bool,
    disposition_ok: bool,
    current_ok: bool,
    q18_ok: bool,
    digest_ok: bool,
) -> str:
    rows = (
        (not family_ok, REUSE_HOLD_FAMILY),
        (not disposition_ok, REUSE_HOLD_DISPOSITION),
        (not current_ok, REUSE_HOLD_CURRENT),
        (not q18_ok, REUSE_HOLD_Q18_RECEIPT),
        (not digest_ok, REUSE_HOLD_DIGEST_RELATION),
        (True, REUSE_IDENTITY_OK),
    )
    return next(code for predicate, code in rows if predicate)


def prove_reuse_identity_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=5):
        if _reuse_tree(*bits) != _reuse_table(*bits):
            raise AssertionError("G6_REUSE_IDENTITY_DIFFERENT_J_DIVERGED")
        checked += 1
    return checked


def public_api_parameters() -> tuple[str, ...]:
    """Guard against reintroducing a caller-supplied precompiled request join."""
    return tuple(inspect.signature(compile_gate10_owner_host_evidence_request).parameters)


def compile_gate10_owner_host_evidence_request(
    *,
    reuse: AdmissionReuseProjection,
    provenance: ObservationProvenanceContractProjection,
    source: SourceIdentityProjection,
    owner: OwnerHostTargetProjection,
    evidence: EvidenceContractProjection,
) -> G6RequestReceipt:
    reuse.validate_shape()
    provenance.validate()
    source.validate()
    owner.validate()
    evidence.validate()

    reuse_reason = classify_reuse_identity(reuse)
    reuse_ok = reuse_reason == REUSE_IDENTITY_OK
    provenance_ok = (
        provenance.exact_operation_binding_required
        and provenance.observer_backend_provenance_required
        and provenance.producer_authentication_required
    )
    source_ok = source.exact_request_identity
    flags = _Flags(
        reuse_ok,
        provenance_ok,
        source_ok,
        bool(owner.owner_host_ref and owner.principal_generation),
        bool(
            owner.host_profile_generation
            and owner.runtime_generation
            and owner.cache_generation
            and owner.storage_geometry_generation
            and owner.resource_envelope_digest
        ),
        bool(owner.evidence_sink_ref and evidence.request_manifest_digest and evidence.benchmark_harness_digest),
        bool(evidence.replay_contract_digest and evidence.recovery_contract_digest),
        evidence.open_gate10_debt == OPEN_GATE10_DEBT
        and evidence.official_revision_revalidation_required
        and source.official_revision_revalidation_required,
        True,
    )
    disposition = _tree(flags)
    if disposition != _table(flags):
        raise RuntimeError("G6_DIFFERENT_J_RUNTIME_DIVERGED")

    reason = {
        COMPILED: "exact Q18/PR769 reuse identity, source request identity, operation provenance and owner-host evidence contracts commute into one nonexecuting request",
        HOLD_REUSE: f"exact current Q18/PR769 GLM-5.3 reuse identity required: {reuse_reason}",
        HOLD_PROVENANCE: "operation/observer/backend provenance contract missing",
        HOLD_SOURCE: "exact flagship source request identity missing",
        HOLD_OWNER: "owner-host target missing",
        HOLD_RESOURCE: "runtime/resource generations missing",
        HOLD_EVIDENCE: "evidence sink contract missing",
        HOLD_REPLAY: "replay/recovery contract missing",
        HOLD_DEBT: "Gate-10 debt not carried",
        HOLD_CEILING: "claim ceiling widened",
    }[disposition]

    body = {
        "schema": SCHEMA,
        "disposition": disposition,
        "reuse": asdict(reuse),
        "reuse_identity_reason_code": reuse_reason,
        "reuse_identity_digest": reuse.identity_digest,
        "q18_transitive_lineage": {
            "head": Q18_HEAD,
            "source_blob": Q18_SOURCE_BLOB,
            "run": Q18_RUN,
            "job": Q18_JOB,
            "receipt_digest": Q18_RECEIPT_DIGEST,
        },
        "provenance": asdict(provenance),
        "source": asdict(source),
        "owner": asdict(owner),
        "evidence": asdict(evidence),
        "canonical_return_path": {
            "c2_handoff_head": C2_HANDOFF_HEAD,
            "c2_handoff_run": C2_HANDOFF_RUN,
            "lifecycle_return_head": LIFECYCLE_RETURN_HEAD,
            "lifecycle_return_run": LIFECYCLE_RETURN_RUN,
        },
    }

    accepted_reuse = reuse if reuse_ok else None
    accepted_source = source if source_ok else None
    receipt = G6RequestReceipt(
        disposition=disposition,
        reason=reason,
        reuse_identity_reason_code=reuse_reason,
        request_digest=_sha(body),
        request_envelope_compiled=disposition == COMPILED,
        official_repository=accepted_source.repository if accepted_source else "",
        pinned_official_revision=accepted_source.pinned_revision if accepted_source else "",
        source_set_digest=accepted_source.source_set_digest if accepted_source else "",
        owner_host_ref=owner.owner_host_ref,
        required_evidence_axes=evidence.required_evidence_axes,
        open_gate10_debt=evidence.open_gate10_debt,
        current_reuse_candidate_bound=reuse_ok,
        exact_glm53_reuse_identity_bound=reuse_ok,
        exact_q18_admission_receipt_bound=bool(
            reuse_ok and accepted_reuse and accepted_reuse.admission_receipt_digest == Q18_RECEIPT_DIGEST
        ),
        pr769_reuse_digest_structurally_verified=bool(
            reuse_ok and accepted_reuse and accepted_reuse.reuse_digest == expected_pr769_reuse_digest(accepted_reuse)
        ),
        admission_reuse_identity_digest=accepted_reuse.identity_digest if accepted_reuse else "",
        admission_receipt_digest=accepted_reuse.admission_receipt_digest if accepted_reuse else "",
        reuse_digest=accepted_reuse.reuse_digest if accepted_reuse else "",
        subject_identity=accepted_reuse.subject_identity if accepted_reuse else "",
        source_generation_key=accepted_reuse.source_generation_key if accepted_reuse else "",
        evidence_generation_key=accepted_reuse.evidence_generation_key if accepted_reuse else "",
        owner_context_key=accepted_reuse.owner_context_key if accepted_reuse else "",
        decision_context_key=accepted_reuse.decision_context_key if accepted_reuse else "",
        operation_provenance_contract_bound=provenance_ok,
        exact_source_request_identity_bound=source_ok,
        official_revision_revalidation_required=evidence.official_revision_revalidation_required,
    )
    receipt.validate_claim_ceiling()
    return receipt


LAWS = (
    "AdmissionValidAtProduce!=AdmissionReusableAtUse",
    "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
    "GLM53AdmissionFamilyMustRemainExact",
    "ExactQ18AdmissionReceiptMustRemainBound",
    "Q18ReceiptIdentityInheritedThroughPR769Lineage",
    "PR769ReuseDigestMustCommitExactIdentityVector",
    "DigestShape!=DigestRelationProof",
    "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+Decision+ReuseDigestMustSurviveProjection",
    "SingleOwnerCompilerEliminatesPostHocIdentityJoin",
    "CallerSuppliedPrecompiledRequest!=IdentityBoundRequest",
    "IdentityBinding!=ReceiptProducerAuthentication",
    "IdentityBinding!=SourceCurrentnessTruth",
    "CallerWitness!=BackendObservationProvenance",
    "PhysicalAttestationBoolean!=PhysicalObservationProvenance",
    "RequestEnvelopeCompiled!=TensorPayloadBound!=ExecutionObserved",
    "PinnedOfficialRevision!=CurrentOfficialRevisionUntilRevalidated",
    "SourceRequestIdentity!=SourceCurrentnessTruth",
    "FullFlagshipIdentity!=FullFlagshipExecution",
    "CanonicalC2ReturnPath!=ProducerAuthentication",
    "Gate10DebtMustRemainExplicitUntilObserved",
    "K27Coordinate!=SemanticIdentity!=RuntimeTruth!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
