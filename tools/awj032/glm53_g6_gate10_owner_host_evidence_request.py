"""G6: compile a bounded owner-host evidence request toward GLM-5.3 Gate 10.

D0 / HS1 / NONPROMOTING.

Exactly two earned other-Agent semantic parents:
* Q18 / PR #761: the current representative E8 generation plus current source-header
  generation can make only a bounded C2 request proposal eligible. It does not bind
  tensor payloads, execute the model, prove physical I/O, or promote Gate 10.
* G5 / PR #766: a stale G3 plan may receive only one bounded recompute attempt after
  independent progress and source-version/read-currentness obligations clear. It does
  not execute recomputation or prove that the transfer plan is current afterward.

G6 does not execute GLM-5.3. It compiles an exact, deterministic request envelope for
an owner-host bounded C2 evidence trial and carries every still-unpaid Gate-10 debt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
from typing import Any

SCHEMA = "AURA-GLM53-G6-GATE10-OWNER-HOST-EVIDENCE-REQUEST-v1"

Q18_SEMANTIC_HEAD = "87fde6b21675c7876acc63f4ca30b2dda89970d0"
Q18_SOURCE_BLOB = "4cee26edaf0759fc80d31889ab9e4e268f9a4fbe"
Q18_TEST_BLOB = "95d590fe20604b1930279e68c58adb5b4345fd5c"
Q18_PROOF_ONLY_HEAD = "69b720efb3b6de704bab51f59179d1e258f33a06"
Q18_PROOF_RUN = 33436970079
Q18_PROOF_JOB = 99635635152
Q18_RECEIPT_DIGEST = "c53acb3ff471dbe3971ee4e7a75b28c4316b50fba88a414f406b93c271c90230"
Q18_ELIGIBLE = "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE"

G5_SEMANTIC_PROOF_HEAD = "8b1f38a6c917a9e7f1af941273164ca0db69821b"
G5_SOURCE_BLOB = "ae70cdfe60e20e544a9cbf0af3b4ac5bd365b205"
G5_TEST_BLOB = "e66980d879c1fe3d497c3a62a1fa75fb6ca83ccc"
G5_PROOF_RUN = 33437182779
G5_PROOF_JOB = 99636328991
G5_CONTRACT_SCHEMA = "AURA-GLM53-G5-RECOMPUTE-ADMISSION-v1"

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
Q18_PINNED_OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
Q18_SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"

REQUEST_SCOPE = "BOUNDED_C2_OWNER_HOST_EVIDENCE_TRIAL"
COMPILED = "OWNER_HOST_BOUNDED_C2_EVIDENCE_REQUEST_ENVELOPE_COMPILED"
HOLD_Q18 = "HOLD_Q18_CURRENT_GENERATION_PROPOSAL_REQUIRED"
HOLD_G5 = "HOLD_G5_TERMINAL_CONTRACT_REQUIRED"
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


def _sha256(value: str, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class Q18ProposalProjection:
    semantic_head: str
    proof_only_head: str
    proof_run: int
    proof_job: int
    receipt_digest: str
    disposition: str
    official_repository: str
    official_revision: str
    source_set_digest: str
    bounded_proposal_eligible: bool
    tensor_payload_bound: bool = False
    execution_authorized: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.semantic_head, self.proof_only_head, self.proof_run, self.proof_job) != (
            Q18_SEMANTIC_HEAD, Q18_PROOF_ONLY_HEAD, Q18_PROOF_RUN, Q18_PROOF_JOB
        ):
            raise ValueError("Q18_PROOF_COORDINATE_MISMATCH")
        if self.receipt_digest != Q18_RECEIPT_DIGEST:
            raise ValueError("Q18_RECEIPT_MISMATCH")
        if (self.official_repository, self.official_revision, self.source_set_digest) != (
            OFFICIAL_REPOSITORY, Q18_PINNED_OFFICIAL_REVISION, Q18_SOURCE_SET_DIGEST
        ):
            raise ValueError("Q18_OFFICIAL_SOURCE_IDENTITY_MISMATCH")
        if self.tensor_payload_bound or self.execution_authorized or self.gate10_promoted:
            raise ValueError("Q18_PROJECTION_EXCEEDS_PARENT_CLAIM_CEILING")


@dataclass(frozen=True)
class G5ContractProjection:
    semantic_proof_head: str
    proof_run: int
    proof_job: int
    source_blob: str
    test_blob: str
    schema: str
    terminal_green: bool
    require_current_transfer_plan_at_execution: bool
    require_independent_progress_on_recompute: bool
    require_future_read_currentness_on_source_change: bool
    execution_authorized: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        if (self.semantic_proof_head, self.proof_run, self.proof_job) != (
            G5_SEMANTIC_PROOF_HEAD, G5_PROOF_RUN, G5_PROOF_JOB
        ):
            raise ValueError("G5_PROOF_COORDINATE_MISMATCH")
        if (self.source_blob, self.test_blob, self.schema) != (
            G5_SOURCE_BLOB, G5_TEST_BLOB, G5_CONTRACT_SCHEMA
        ):
            raise ValueError("G5_SEMANTIC_BLOB_MISMATCH")
        if self.execution_authorized or self.gate10_promoted:
            raise ValueError("G5_PROJECTION_EXCEEDS_PARENT_CLAIM_CEILING")


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
            (self.owner_host_ref, "OWNER_HOST_REF_REQUIRED"),
            (self.principal_generation, "PRINCIPAL_GENERATION_REQUIRED"),
            (self.host_profile_generation, "HOST_PROFILE_GENERATION_REQUIRED"),
            (self.runtime_generation, "RUNTIME_GENERATION_REQUIRED"),
            (self.cache_generation, "CACHE_GENERATION_REQUIRED"),
            (self.storage_geometry_generation, "STORAGE_GEOMETRY_GENERATION_REQUIRED"),
            (self.evidence_sink_ref, "EVIDENCE_SINK_REF_REQUIRED"),
        ):
            _text(value, code)
        _sha256(self.resource_envelope_digest, "RESOURCE_ENVELOPE_DIGEST_INVALID")
        if self.owner_authenticated_by_this_contract or self.execution_authorized_by_this_contract:
            raise ValueError("OWNER_HOST_PROJECTION_EXCEEDS_NONPROMOTION_CEILING")


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
    full_flagship_execution_already_proven: bool = False
    auraos_resident_routing_already_proven: bool = False
    replay_recovery_already_proven: bool = False
    gate10_promoted: bool = False

    def validate(self) -> None:
        for value, code in (
            (self.request_manifest_digest, "REQUEST_MANIFEST_DIGEST_INVALID"),
            (self.benchmark_harness_digest, "BENCHMARK_HARNESS_DIGEST_INVALID"),
            (self.replay_contract_digest, "REPLAY_CONTRACT_DIGEST_INVALID"),
            (self.recovery_contract_digest, "RECOVERY_CONTRACT_DIGEST_INVALID"),
        ):
            _sha256(value, code)
        if self.required_evidence_axes != REQUIRED_EVIDENCE_AXES:
            raise ValueError("REQUIRED_EVIDENCE_AXES_MUST_MATCH_EXACTLY")
        if self.open_gate10_debt != OPEN_GATE10_DEBT:
            raise ValueError("OPEN_GATE10_DEBT_MUST_BE_CARRIED_EXACTLY")
        if not self.official_revision_revalidation_required:
            raise ValueError("OFFICIAL_REVISION_REVALIDATION_DEBT_MUST_BE_CARRIED")
        if any((
            self.actual_owner_host_evidence_already_observed,
            self.full_flagship_execution_already_proven,
            self.auraos_resident_routing_already_proven,
            self.replay_recovery_already_proven,
            self.gate10_promoted,
        )):
            raise ValueError("EVIDENCE_CONTRACT_CANNOT_SELF_PROMOTE_UNOBSERVED_GATE10_STATE")


@dataclass(frozen=True)
class G6RequestReceipt:
    disposition: str
    reason: str
    request_scope: str
    q18_receipt_digest: str
    g5_semantic_proof_head: str
    official_repository: str
    pinned_official_revision: str
    source_set_digest: str
    owner_host_ref: str
    principal_generation: str
    host_profile_generation: str
    runtime_generation: str
    cache_generation: str
    storage_geometry_generation: str
    resource_envelope_digest: str
    evidence_sink_ref: str
    request_manifest_digest: str
    benchmark_harness_digest: str
    replay_contract_digest: str
    recovery_contract_digest: str
    required_evidence_axes: tuple[str, ...]
    open_gate10_debt: tuple[str, ...]
    request_digest: str
    request_envelope_compiled: bool
    official_revision_revalidation_required: bool = True
    tensor_payload_bound: bool = False
    real_tensor_quantization_observed: bool = False
    owner_host_execution_observed: bool = False
    full_flagship_model_loaded: bool = False
    physical_io_proven: bool = False
    auraos_resident_routing_proven: bool = False
    replay_recovery_proven: bool = False
    execution_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.disposition == COMPILED and not self.request_envelope_compiled:
            raise ValueError("COMPILED_DISPOSITION_BOOLEAN_MISMATCH")
        if self.disposition != COMPILED and self.request_envelope_compiled:
            raise ValueError("HOLD_DISPOSITION_CANNOT_MARK_REQUEST_COMPILED")
        if any((
            self.tensor_payload_bound,
            self.real_tensor_quantization_observed,
            self.owner_host_execution_observed,
            self.full_flagship_model_loaded,
            self.physical_io_proven,
            self.auraos_resident_routing_proven,
            self.replay_recovery_proven,
            self.execution_authorized,
            self.semantic_k27_authority_minted,
            self.native_private_transformer_kv_accessed,
            self.gate10_promoted,
            self.merge_deploy_spend_public_financial_human_effect,
        )):
            raise ValueError("G6_CANNOT_WIDEN_EXECUTION_OR_GATE10_AUTHORITY")


@dataclass(frozen=True)
class _Flags:
    q18_current_generation_eligible: bool
    g5_terminal_contract_bound: bool
    exact_flagship_source_identity_bound: bool
    owner_host_target_bound: bool
    runtime_resource_generations_bound: bool
    evidence_sink_contract_bound: bool
    replay_recovery_contract_bound: bool
    gate10_debt_carried: bool
    claim_ceiling_preserved: bool


def _classify_tree(f: _Flags) -> str:
    if not f.q18_current_generation_eligible:
        return HOLD_Q18
    if not f.g5_terminal_contract_bound:
        return HOLD_G5
    if not f.exact_flagship_source_identity_bound:
        return HOLD_SOURCE
    if not f.owner_host_target_bound:
        return HOLD_OWNER
    if not f.runtime_resource_generations_bound:
        return HOLD_RESOURCE
    if not f.evidence_sink_contract_bound:
        return HOLD_EVIDENCE
    if not f.replay_recovery_contract_bound:
        return HOLD_REPLAY
    if not f.gate10_debt_carried:
        return HOLD_DEBT
    if not f.claim_ceiling_preserved:
        return HOLD_CEILING
    return COMPILED


def _classify_table(f: _Flags) -> str:
    rows = (
        (not f.q18_current_generation_eligible, HOLD_Q18),
        (not f.g5_terminal_contract_bound, HOLD_G5),
        (not f.exact_flagship_source_identity_bound, HOLD_SOURCE),
        (not f.owner_host_target_bound, HOLD_OWNER),
        (not f.runtime_resource_generations_bound, HOLD_RESOURCE),
        (not f.evidence_sink_contract_bound, HOLD_EVIDENCE),
        (not f.replay_recovery_contract_bound, HOLD_REPLAY),
        (not f.gate10_debt_carried, HOLD_DEBT),
        (not f.claim_ceiling_preserved, HOLD_CEILING),
        (True, COMPILED),
    )
    return next(disposition for condition, disposition in rows if condition)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=9):
        flags = _Flags(*bits)
        if _classify_tree(flags) != _classify_table(flags):
            raise AssertionError("G6_DIFFERENT_J_CLASSIFIERS_DISAGREE")
        checked += 1
    return checked


def compile_gate10_owner_host_evidence_request(
    *,
    q18: Q18ProposalProjection,
    g5: G5ContractProjection,
    owner: OwnerHostTargetProjection,
    evidence: EvidenceContractProjection,
) -> G6RequestReceipt:
    q18.validate()
    g5.validate()
    owner.validate()
    evidence.validate()

    flags = _Flags(
        q18_current_generation_eligible=(
            q18.disposition == Q18_ELIGIBLE and q18.bounded_proposal_eligible
        ),
        g5_terminal_contract_bound=(
            g5.terminal_green
            and g5.require_current_transfer_plan_at_execution
            and g5.require_independent_progress_on_recompute
            and g5.require_future_read_currentness_on_source_change
        ),
        exact_flagship_source_identity_bound=(
            q18.official_repository == OFFICIAL_REPOSITORY
            and q18.official_revision == Q18_PINNED_OFFICIAL_REVISION
            and q18.source_set_digest == Q18_SOURCE_SET_DIGEST
        ),
        owner_host_target_bound=bool(owner.owner_host_ref and owner.principal_generation),
        runtime_resource_generations_bound=bool(
            owner.host_profile_generation
            and owner.runtime_generation
            and owner.cache_generation
            and owner.storage_geometry_generation
            and owner.resource_envelope_digest
        ),
        evidence_sink_contract_bound=bool(
            owner.evidence_sink_ref
            and evidence.request_manifest_digest
            and evidence.benchmark_harness_digest
        ),
        replay_recovery_contract_bound=bool(
            evidence.replay_contract_digest and evidence.recovery_contract_digest
        ),
        gate10_debt_carried=(
            evidence.open_gate10_debt == OPEN_GATE10_DEBT
            and evidence.official_revision_revalidation_required
        ),
        claim_ceiling_preserved=True,
    )
    tree = _classify_tree(flags)
    table = _classify_table(flags)
    if tree != table:
        raise AssertionError("G6_DIFFERENT_J_CLASSIFIERS_DISAGREE")

    reason = {
        COMPILED: "exact bounded C2 proposal and loop-safe currentness contract are bound into a non-executing owner-host evidence request while all Gate-10 debt remains explicit",
        HOLD_Q18: "current-generation bounded C2 proposal eligibility missing",
        HOLD_G5: "terminal G5 progress/currentness contract not bound",
        HOLD_SOURCE: "exact flagship source identity not bound",
        HOLD_OWNER: "owner-host target or principal generation missing",
        HOLD_RESOURCE: "runtime/resource generations not bound",
        HOLD_EVIDENCE: "evidence sink contract not bound",
        HOLD_REPLAY: "replay/recovery contract not bound",
        HOLD_DEBT: "remaining Gate-10 debt not carried exactly",
        HOLD_CEILING: "claim ceiling widened",
    }[tree]

    body = {
        "schema": SCHEMA,
        "disposition": tree,
        "reason": reason,
        "request_scope": REQUEST_SCOPE,
        "q18_receipt_digest": q18.receipt_digest,
        "g5_semantic_proof_head": g5.semantic_proof_head,
        "official_repository": q18.official_repository,
        "pinned_official_revision": q18.official_revision,
        "source_set_digest": q18.source_set_digest,
        "owner_host_ref": owner.owner_host_ref,
        "principal_generation": owner.principal_generation,
        "host_profile_generation": owner.host_profile_generation,
        "runtime_generation": owner.runtime_generation,
        "cache_generation": owner.cache_generation,
        "storage_geometry_generation": owner.storage_geometry_generation,
        "resource_envelope_digest": owner.resource_envelope_digest,
        "evidence_sink_ref": owner.evidence_sink_ref,
        "request_manifest_digest": evidence.request_manifest_digest,
        "benchmark_harness_digest": evidence.benchmark_harness_digest,
        "replay_contract_digest": evidence.replay_contract_digest,
        "recovery_contract_digest": evidence.recovery_contract_digest,
        "required_evidence_axes": evidence.required_evidence_axes,
        "open_gate10_debt": evidence.open_gate10_debt,
        "official_revision_revalidation_required": evidence.official_revision_revalidation_required,
        "claim_ceiling": {
            "tensor_payload_bound": False,
            "real_tensor_quantization_observed": False,
            "owner_host_execution_observed": False,
            "full_flagship_model_loaded": False,
            "physical_io_proven": False,
            "auraos_resident_routing_proven": False,
            "replay_recovery_proven": False,
            "execution_authorized": False,
            "semantic_k27_authority_minted": False,
            "native_private_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    request_digest = _sha(body)
    receipt = G6RequestReceipt(
        disposition=tree,
        reason=reason,
        request_scope=REQUEST_SCOPE,
        q18_receipt_digest=q18.receipt_digest,
        g5_semantic_proof_head=g5.semantic_proof_head,
        official_repository=q18.official_repository,
        pinned_official_revision=q18.official_revision,
        source_set_digest=q18.source_set_digest,
        owner_host_ref=owner.owner_host_ref,
        principal_generation=owner.principal_generation,
        host_profile_generation=owner.host_profile_generation,
        runtime_generation=owner.runtime_generation,
        cache_generation=owner.cache_generation,
        storage_geometry_generation=owner.storage_geometry_generation,
        resource_envelope_digest=owner.resource_envelope_digest,
        evidence_sink_ref=owner.evidence_sink_ref,
        request_manifest_digest=evidence.request_manifest_digest,
        benchmark_harness_digest=evidence.benchmark_harness_digest,
        replay_contract_digest=evidence.replay_contract_digest,
        recovery_contract_digest=evidence.recovery_contract_digest,
        required_evidence_axes=evidence.required_evidence_axes,
        open_gate10_debt=evidence.open_gate10_debt,
        request_digest=request_digest,
        request_envelope_compiled=(tree == COMPILED),
        official_revision_revalidation_required=evidence.official_revision_revalidation_required,
    )
    receipt.validate_claim_ceiling()
    return receipt


LAWS = (
    "BoundedC2Proposal!=OwnerHostExecutionAuthority",
    "G5BoundedRecomputeAdmission!=CurrentTransferPlanProof",
    "RequestEnvelopeCompiled!=TensorPayloadBound!=ExecutionObserved",
    "PinnedOfficialRevision!=CurrentOfficialRevisionUntilRevalidated",
    "OwnerHostTarget!=OwnerAuthenticatedByThisContract",
    "ResourceEnvelope!=PhysicalIOProof",
    "ReplayContract!=ReplayRecoveryProof",
    "FullFlagshipIdentity!=FullFlagshipExecution",
    "Gate10DebtMustRemainExplicitUntilObserved",
    "K27Coordinate!=SemanticIdentity!=RuntimeTruth!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
