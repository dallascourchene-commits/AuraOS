"""G6 W3: compile a current, provenance-bound owner-host evidence request toward Gate 10.

D0 / HS1 / NONPROMOTING.

Exactly two terminal foreign parents:
- PR #769: generation-bound admission reuse. A historical bounded C2 proposal is not
  reusable at owner-host use time until producer/subject/source/evidence/owner/decision
  generations commute. Positive state is REUSE_CANDIDATE only.
- PR #727: secure operation-bound observation envelope. Physical observation requires
  exact operation/workload/source plus observer/backend provenance; a caller boolean or
  structurally matching witness cannot manufacture physical truth.

Existing transport owners remain canonical downstream constraints rather than new
objective parents: PR #582 owns OwnerHostC2CanaryRequest/Receipt/join and PR #586 owns
its nonmetric lifecycle-return packet. This module compiles a request into that future
owner-host world. It never executes GLM-5.3, authenticates the future owner-host
producer, observes physical I/O, or promotes Gate 10.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib, itertools, json
from typing import Any

SCHEMA = "AURA-GLM53-G6-GATE10-OWNER-HOST-EVIDENCE-REQUEST-v2"

REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
REUSE_SOURCE_BLOB = "d171d0938e469a4383490d1a691750c2068f21e7"
REUSE_TEST_BLOB = "58fad37a0f89853098fa3dbbe2f2a1771574e449"
REUSE_RUN = 33437612722
REUSE_JOB = 99637780915
REUSE_FAMILY = "BOUNDED_C2_PROPOSAL"
REUSE_DISPOSITION = "REUSE_CANDIDATE"

PROV_HEAD = "293c59d7260372ccd3b9e8130b12979b052c3ed9"
PROV_SOURCE_BLOB = "98db548b6e8f7443b79d979eb0e177ac6aa68534"
PROV_RUN = 33416248604
PROV_JOB = 99567478616

# Canonical downstream transport owners. These are collision/compatibility constraints,
# not derivation parents for this objective.
C2_HANDOFF_HEAD = "24a5404ee3b987dee12192917e40b35d3a43e81c"
C2_HANDOFF_RUN = 33360061584
LIFECYCLE_RETURN_HEAD = "aa3fcd9a4cefd18dbc991c3e8a450fcfbbb6726b"
LIFECYCLE_RETURN_RUN = 33360529366

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
PINNED_OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"

REQUEST_SCOPE = "BOUNDED_C2_OWNER_HOST_EVIDENCE_TRIAL"
COMPILED = "OWNER_HOST_BOUNDED_C2_EVIDENCE_REQUEST_ENVELOPE_COMPILED"
HOLD_REUSE = "HOLD_CURRENT_REUSE_CANDIDATE_REQUIRED"
HOLD_PROVENANCE = "HOLD_OPERATION_PROVENANCE_CONTRACT_REQUIRED"
HOLD_SOURCE = "HOLD_EXACT_FLAGSHIP_SOURCE_IDENTITY_REQUIRED"
HOLD_OWNER = "HOLD_OWNER_HOST_TARGET_REQUIRED"
HOLD_RESOURCE = "HOLD_RUNTIME_RESOURCE_GENERATIONS_REQUIRED"
HOLD_EVIDENCE = "HOLD_EVIDENCE_SINK_CONTRACT_REQUIRED"
HOLD_REPLAY = "HOLD_REPLAY_RECOVERY_CONTRACT_REQUIRED"
HOLD_DEBT = "HOLD_GATE10_DEBT_CARRY_REQUIRED"
HOLD_CEILING = "HOLD_CLAIM_CEILING"

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


def _canonical(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(v: Any) -> str:
    return hashlib.sha256(_canonical(v)).hexdigest()


def _text(v: str, code: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(code)
    return v.strip()


def _digest(v: str, code: str) -> str:
    v = _text(v, code)
    if len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
        raise ValueError(code)
    return v


@dataclass(frozen=True)
class AdmissionReuseProjection:
    proof_head: str
    proof_run: int
    proof_job: int
    source_blob: str
    test_blob: str
    admission_family: str
    disposition: str
    current_context_exact: bool
    source_currentness_proven: bool = False
    execution_authorized: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (
            self.proof_head,
            self.proof_run,
            self.proof_job,
            self.source_blob,
            self.test_blob,
        ) != (REUSE_HEAD, REUSE_RUN, REUSE_JOB, REUSE_SOURCE_BLOB, REUSE_TEST_BLOB):
            raise ValueError("REUSE_PROOF_MISMATCH")
        if self.admission_family != REUSE_FAMILY:
            raise ValueError("REUSE_FAMILY_MISMATCH")
        if self.source_currentness_proven or self.execution_authorized or self.gate10_promoted:
            raise ValueError("REUSE_PROJECTION_EXCEEDS_CEILING")


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

    def exact_request_identity(self) -> bool:
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
        for v, c in (
            (self.owner_host_ref, "OWNER"),
            (self.principal_generation, "PRINCIPAL"),
            (self.host_profile_generation, "HOST"),
            (self.runtime_generation, "RUNTIME"),
            (self.cache_generation, "CACHE"),
            (self.storage_geometry_generation, "STORAGE"),
            (self.evidence_sink_ref, "SINK"),
        ):
            _text(v, c)
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
        for v, c in (
            (self.request_manifest_digest, "MANIFEST"),
            (self.benchmark_harness_digest, "HARNESS"),
            (self.replay_contract_digest, "REPLAY"),
            (self.recovery_contract_digest, "RECOVERY"),
        ):
            _digest(v, c)
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
    request_digest: str
    request_envelope_compiled: bool
    official_repository: str
    pinned_official_revision: str
    source_set_digest: str
    owner_host_ref: str
    required_evidence_axes: tuple[str, ...]
    open_gate10_debt: tuple[str, ...]
    current_reuse_candidate_bound: bool
    operation_provenance_contract_bound: bool
    exact_source_request_identity_bound: bool
    official_revision_revalidation_required: bool = True
    canonical_c2_handoff_head: str = C2_HANDOFF_HEAD
    canonical_c2_handoff_run: int = C2_HANDOFF_RUN
    canonical_lifecycle_return_head: str = LIFECYCLE_RETURN_HEAD
    canonical_lifecycle_return_run: int = LIFECYCLE_RETURN_RUN
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
        if any(
            (
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


def _tree(f: _Flags) -> str:
    if not f.reuse:
        return HOLD_REUSE
    if not f.provenance:
        return HOLD_PROVENANCE
    if not f.source:
        return HOLD_SOURCE
    if not f.owner:
        return HOLD_OWNER
    if not f.resource:
        return HOLD_RESOURCE
    if not f.evidence:
        return HOLD_EVIDENCE
    if not f.replay:
        return HOLD_REPLAY
    if not f.debt:
        return HOLD_DEBT
    if not f.ceiling:
        return HOLD_CEILING
    return COMPILED


def _table(f: _Flags) -> str:
    rows = (
        (not f.reuse, HOLD_REUSE),
        (not f.provenance, HOLD_PROVENANCE),
        (not f.source, HOLD_SOURCE),
        (not f.owner, HOLD_OWNER),
        (not f.resource, HOLD_RESOURCE),
        (not f.evidence, HOLD_EVIDENCE),
        (not f.replay, HOLD_REPLAY),
        (not f.debt, HOLD_DEBT),
        (not f.ceiling, HOLD_CEILING),
        (True, COMPILED),
    )
    return next(d for p, d in rows if p)


def prove_different_j() -> int:
    n = 0
    for bits in itertools.product((False, True), repeat=9):
        f = _Flags(*bits)
        assert _tree(f) == _table(f)
        n += 1
    return n


def compile_gate10_owner_host_evidence_request(
    *,
    reuse: AdmissionReuseProjection,
    provenance: ObservationProvenanceContractProjection,
    source: SourceIdentityProjection,
    owner: OwnerHostTargetProjection,
    evidence: EvidenceContractProjection,
) -> G6RequestReceipt:
    reuse.validate()
    provenance.validate()
    source.validate()
    owner.validate()
    evidence.validate()

    flags = _Flags(
        reuse.disposition == REUSE_DISPOSITION and reuse.current_context_exact,
        provenance.exact_operation_binding_required
        and provenance.observer_backend_provenance_required
        and provenance.producer_authentication_required,
        source.exact_request_identity(),
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
    assert disposition == _table(flags)
    reason = {
        COMPILED: "current bounded C2 reuse candidate, exact source request identity, and operation-provenance requirements commute into a nonexecuting owner-host evidence request",
        HOLD_REUSE: "current bounded C2 reuse candidate missing",
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
        "reuse_head": reuse.proof_head,
        "provenance_head": provenance.proof_head,
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
    # Held receipts suppress the caller-supplied source identity rather than echoing an
    # unaccepted value as though it were the canonical current request source.
    accepted_repo = source.repository if flags.source else ""
    accepted_revision = source.pinned_revision if flags.source else ""
    accepted_source_set = source.source_set_digest if flags.source else ""
    r = G6RequestReceipt(
        disposition,
        reason,
        _sha(body),
        disposition == COMPILED,
        accepted_repo,
        accepted_revision,
        accepted_source_set,
        owner.owner_host_ref,
        evidence.required_evidence_axes,
        evidence.open_gate10_debt,
        flags.reuse,
        flags.provenance,
        flags.source,
        evidence.official_revision_revalidation_required,
    )
    r.validate_claim_ceiling()
    return r


LAWS = (
    "AdmissionValidAtProduce!=AdmissionReusableAtUse",
    "ReuseCandidate!=ExecutionAuthority",
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
