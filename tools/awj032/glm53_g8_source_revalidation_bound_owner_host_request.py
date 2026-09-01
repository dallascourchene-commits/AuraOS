"""G8: bind canonical G6 owner-host request compilation to exact Q20 source revalidation.

D0 / HS1 / NONPROMOTING.

Exactly two fresh terminal other-Agent parents:
- G6 / PR #782: canonical single-owner Gate-10 evidence request compiler.
- Q20 / PR #784: live official-source revision revalidation candidate.

G8 owns only their relation. It calls both parent owners unchanged. It does not accept a
caller-supplied G6 request receipt or a caller-supplied Q20 source receipt.

Compile-time source-revalidation evidence remains distinct from future effect-time
currentness. No tensor binding, execution, physical observation, authority, Gate-10
promotion, semantic K27 authority, or native/private transformer KV access is granted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import itertools
import json
from typing import Any

import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as g6
import tools.quantization.aura_glm53_q20_official_source_revision_revalidation as q20

SCHEMA = "AURA-GLM53-G8-SOURCE-REVALIDATION-BOUND-OWNER-HOST-REQUEST-v1"

G6_HEAD = "28b5cca9d4b3eed93af21b631fb38fe9e19609e3"
G6_SOURCE_BLOB = "e7203d06048ba3fdc02b19afc064cf99b4a0c091"
G6_TEST_BLOB = "56d4711ff8337014f7cfede369cb355d65f05c3a"
G6_WORKFLOW_BLOB = "20e6671b2e6decc3d646463e1183bb66ba191864"
G6_RUN = 33480840778
G6_JOB = 99769880019

Q20_HEAD = "2c7f42adf18a7421d7d4d21fb78a37a88445f82f"
Q20_SOURCE_BLOB = "27f8572edad81d3bdb680c116270a9abcfbce9cf"
Q20_TEST_BLOB = "9294c67ec2819168fe81a2376fdab76844473ea3"
Q20_WORKFLOW_BLOB = "adaee944c4e42f3e30ce433a8f7d5e22ad8dfe40"
Q20_RUN = 33481589083
Q20_JOB = 99772192034
Q20_RECEIPT_DIGEST = "d68aeb063d516ec310cc60c1be5823f11b002e17298b6e17e6b612660c785a82"

CONVERGENCE_COMMIT = "19eae95910e2a309d4e0edf00e7cdfee40bb5e69"

CANDIDATE = "SOURCE_REVALIDATION_BOUND_OWNER_HOST_REQUEST_CANDIDATE"
HOLD_G6 = "HOLD_CANONICAL_G6_REQUEST_NOT_COMPILED"
HOLD_Q20 = "HOLD_Q20_SOURCE_REVALIDATION_NOT_CANDIDATE"
HOLD_REPOSITORY = "HOLD_G6_Q20_REPOSITORY_RELATION"
HOLD_PINNED_REVISION = "HOLD_G6_Q20_PINNED_REVISION_RELATION"
HOLD_OBSERVATION_GENERATION = "HOLD_Q20_OBSERVATION_GENERATION"
HOLD_EFFECT_DEBT = "HOLD_FUTURE_EFFECT_CURRENTNESS_DEBT"
HOLD_CEILING = "HOLD_G8_CLAIM_CEILING"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class _Flags:
    g6_compiled: bool
    q20_candidate: bool
    repository_relation: bool
    pinned_revision_relation: bool
    observation_generation: bool
    effect_debt_retained: bool
    ceiling: bool


def _tree(flags: _Flags) -> str:
    if not flags.g6_compiled:
        return HOLD_G6
    if not flags.q20_candidate:
        return HOLD_Q20
    if not flags.repository_relation:
        return HOLD_REPOSITORY
    if not flags.pinned_revision_relation:
        return HOLD_PINNED_REVISION
    if not flags.observation_generation:
        return HOLD_OBSERVATION_GENERATION
    if not flags.effect_debt_retained:
        return HOLD_EFFECT_DEBT
    if not flags.ceiling:
        return HOLD_CEILING
    return CANDIDATE


def _table(flags: _Flags) -> str:
    rows = (
        (not flags.g6_compiled, HOLD_G6),
        (not flags.q20_candidate, HOLD_Q20),
        (not flags.repository_relation, HOLD_REPOSITORY),
        (not flags.pinned_revision_relation, HOLD_PINNED_REVISION),
        (not flags.observation_generation, HOLD_OBSERVATION_GENERATION),
        (not flags.effect_debt_retained, HOLD_EFFECT_DEBT),
        (not flags.ceiling, HOLD_CEILING),
        (True, CANDIDATE),
    )
    return next(disposition for predicate, disposition in rows if predicate)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=7):
        flags = _Flags(*bits)
        if _tree(flags) != _table(flags):
            raise AssertionError("G8_DIFFERENT_J_DIVERGED")
        checked += 1
    return checked


@dataclass(frozen=True)
class G8Receipt:
    disposition: str
    reason: str
    receipt_digest: str
    g6_request_digest: str
    q20_receipt_digest: str
    official_repository: str
    pinned_official_revision: str
    q20_observed_head_revision: str
    q20_live_proof_head: str
    q20_live_proof_run: int
    q20_live_proof_job: int
    g6_request_compiled: bool
    q20_source_revalidation_candidate_bound: bool
    request_source_relation_bound: bool
    q20_exact_observation_generation_bound: bool
    request_compile_source_revalidation_evidence_bound: bool
    official_revision_revalidation_axis_retained: bool
    future_effect_source_revalidation_required: bool
    source_currentness_proven_by_this_contract: bool = False
    source_currentness_at_future_effect_proven: bool = False
    tensor_payload_bytes_observed_by_this_contract: bool = False
    tensor_payload_bound: bool = False
    real_tensor_quantization_observed: bool = False
    model_execution_observed: bool = False
    owner_host_execution_observed: bool = False
    physical_io_observed: bool = False
    observer_backend_authenticated: bool = False
    auraos_resident_routing_observed: bool = False
    replay_recovery_proven: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if (self.disposition == CANDIDATE) != self.request_compile_source_revalidation_evidence_bound:
            raise ValueError("G8_DISPOSITION_BOOLEAN_MISMATCH")
        if self.request_compile_source_revalidation_evidence_bound and not (
            self.g6_request_compiled
            and self.q20_source_revalidation_candidate_bound
            and self.request_source_relation_bound
            and self.q20_exact_observation_generation_bound
            and self.official_revision_revalidation_axis_retained
            and self.future_effect_source_revalidation_required
        ):
            raise ValueError("G8_CANDIDATE_MISSING_REQUIRED_BINDING")
        if any(
            (
                self.source_currentness_proven_by_this_contract,
                self.source_currentness_at_future_effect_proven,
                self.tensor_payload_bytes_observed_by_this_contract,
                self.tensor_payload_bound,
                self.real_tensor_quantization_observed,
                self.model_execution_observed,
                self.owner_host_execution_observed,
                self.physical_io_observed,
                self.observer_backend_authenticated,
                self.auraos_resident_routing_observed,
                self.replay_recovery_proven,
                self.execution_authorized,
                self.effect_authorized,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
                self.merge_deploy_spend_public_financial_human_effect,
            )
        ):
            raise ValueError("G8_EXCEEDED_CLAIM_CEILING")


def _q20_receipt() -> dict[str, object]:
    receipt = q20.assess_official_source_revision(
        q18=q20.current_q18_projection(),
        observation=q20.observed_current_source_fixture(),
    )
    if receipt.get("receipt_digest") != Q20_RECEIPT_DIGEST:
        raise ValueError("Q20_EXACT_RECEIPT_DIGEST_MISMATCH")
    return receipt


def bind_source_revalidation_to_owner_host_request(
    *,
    reuse: g6.AdmissionReuseProjection,
    provenance: g6.ObservationProvenanceContractProjection,
    source: g6.SourceIdentityProjection,
    owner: g6.OwnerHostTargetProjection,
    evidence: g6.EvidenceContractProjection,
) -> G8Receipt:
    """Bind canonical parent-owner outputs without accepting either parent receipt from callers."""

    request = g6.compile_gate10_owner_host_evidence_request(
        reuse=reuse, provenance=provenance, source=source, owner=owner, evidence=evidence
    )
    request.validate_claim_ceiling()

    source_receipt = _q20_receipt()

    g6_compiled = request.disposition == g6.COMPILED and request.request_envelope_compiled
    q20_candidate = (
        source_receipt["disposition"] == q20.CANDIDATE
        and source_receipt["gate10_source_binding_candidate"] is True
        and source_receipt["tracked_model_payload_generation_unchanged_across_observed_diff"] is True
    )
    repository_relation = (
        request.official_repository
        == source_receipt["official_repository"]
        == g6.OFFICIAL_REPOSITORY
        == q20.OFFICIAL_REPOSITORY
    )
    pinned_revision_relation = (
        request.pinned_official_revision
        == source_receipt["q18_pinned_revision"]
        == g6.PINNED_OFFICIAL_REVISION
        == q20.PINNED_REVISION
    )
    observation_generation = (
        Q20_HEAD == "2c7f42adf18a7421d7d4d21fb78a37a88445f82f"
        and Q20_RUN == 33481589083
        and Q20_JOB == 99772192034
        and source_receipt["provider_observed_head_revision"] == q20.CURRENT_OBSERVED_REVISION
        and source_receipt["receipt_digest"] == Q20_RECEIPT_DIGEST
    )
    effect_debt_retained = (
        request.official_revision_revalidation_required
        and "OFFICIAL_SOURCE_REVISION_REVALIDATION" in request.required_evidence_axes
        and source_receipt["future_effect_source_revalidation_required"] is True
        and source_receipt["source_currentness_at_future_effect_proven"] is False
    )
    ceiling = not any(
        (
            request.source_currentness_proven_by_this_contract,
            request.tensor_payload_bound,
            request.real_tensor_quantization_observed,
            request.owner_host_execution_observed,
            request.execution_authorized,
            request.gate10_promoted,
            source_receipt["tensor_payload_bound"],
            source_receipt["model_execution_observed"],
            source_receipt["owner_host_execution_observed"],
            source_receipt["gate10_promoted"],
            source_receipt["semantic_k27_authority_minted"],
            source_receipt["native_private_transformer_kv_accessed"],
        )
    )

    flags = _Flags(
        g6_compiled,
        q20_candidate,
        repository_relation,
        pinned_revision_relation,
        observation_generation,
        effect_debt_retained,
        ceiling,
    )
    disposition = _tree(flags)
    if disposition != _table(flags):
        raise RuntimeError("G8_DIFFERENT_J_RUNTIME_DIVERGED")

    reason = {
        CANDIDATE: (
            "canonical G6 request identity and exact Q20 live source-revalidation generation "
            "commute while future effect-time currentness debt remains explicit"
        ),
        HOLD_G6: "canonical G6 request did not compile",
        HOLD_Q20: "Q20 source-revalidation result is not the exact bounded candidate",
        HOLD_REPOSITORY: "G6 request and Q20 observation do not bind the same official repository",
        HOLD_PINNED_REVISION: "G6 request and Q20 observation do not bind the same pinned revision",
        HOLD_OBSERVATION_GENERATION: "exact Q20 hosted observation generation is not bound",
        HOLD_EFFECT_DEBT: "future effect-time source revalidation debt was dropped",
        HOLD_CEILING: "parent or child claim ceiling widened",
    }[disposition]

    body = {
        "schema": SCHEMA,
        "exact_two_parent_convergence": CONVERGENCE_COMMIT,
        "g6_parent": {
            "head": G6_HEAD,
            "source_blob": G6_SOURCE_BLOB,
            "test_blob": G6_TEST_BLOB,
            "workflow_blob": G6_WORKFLOW_BLOB,
            "run": G6_RUN,
            "job": G6_JOB,
            "request_digest": request.request_digest,
        },
        "q20_parent": {
            "head": Q20_HEAD,
            "source_blob": Q20_SOURCE_BLOB,
            "test_blob": Q20_TEST_BLOB,
            "workflow_blob": Q20_WORKFLOW_BLOB,
            "run": Q20_RUN,
            "job": Q20_JOB,
            "receipt_digest": source_receipt["receipt_digest"],
            "observed_head_revision": source_receipt["provider_observed_head_revision"],
        },
        "official_repository": request.official_repository,
        "pinned_official_revision": request.pinned_official_revision,
        "disposition": disposition,
        "future_effect_source_revalidation_required": True,
        "source_currentness_at_future_effect_proven": False,
        "claim_ceiling": {
            "tensor_payload_bound": False,
            "model_execution_observed": False,
            "owner_host_execution_observed": False,
            "physical_io_observed": False,
            "execution_authorized": False,
            "effect_authorized": False,
            "semantic_k27_authority_minted": False,
            "native_private_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    receipt = G8Receipt(
        disposition=disposition,
        reason=reason,
        receipt_digest=_sha(body),
        g6_request_digest=request.request_digest,
        q20_receipt_digest=str(source_receipt["receipt_digest"]),
        official_repository=request.official_repository if repository_relation else "",
        pinned_official_revision=request.pinned_official_revision if pinned_revision_relation else "",
        q20_observed_head_revision=(
            str(source_receipt["provider_observed_head_revision"]) if observation_generation else ""
        ),
        q20_live_proof_head=Q20_HEAD,
        q20_live_proof_run=Q20_RUN,
        q20_live_proof_job=Q20_JOB,
        g6_request_compiled=g6_compiled,
        q20_source_revalidation_candidate_bound=q20_candidate,
        request_source_relation_bound=repository_relation and pinned_revision_relation,
        q20_exact_observation_generation_bound=observation_generation,
        request_compile_source_revalidation_evidence_bound=disposition == CANDIDATE,
        official_revision_revalidation_axis_retained=(
            "OFFICIAL_SOURCE_REVISION_REVALIDATION" in request.required_evidence_axes
        ),
        future_effect_source_revalidation_required=True,
    )
    receipt.validate_claim_ceiling()
    return receipt


def public_api_parameters() -> tuple[str, ...]:
    return tuple(inspect.signature(bind_source_revalidation_to_owner_host_request).parameters)


LAWS = (
    "CallerSuppliedPrecompiledRequest!=IdentityBoundRequest",
    "CallerSuppliedQ20Receipt!=LiveSourceObservationGeneration",
    "RepositoryRevisionChanged!=ModelPayloadGenerationChanged",
    "CompileTimeSourceRevalidation!=EffectTimeSourceCurrentness",
    "SourceRevalidationEvidenceBoundAtRequestCompile!=SourceCurrentAtFutureEffect",
    "MatchingSourceLabels!=RevalidationGenerationBound",
    "RequestSourceIdentity!=SourceCurrentnessTruth",
    "TrackedPayloadPathUnchanged!=FutureSourceCurrentness",
    "Q20SourceRevalidationCandidate!=OwnerHostExecutionAuthority",
    "G6RequestCompiled!=OwnerHostExecutionObserved",
    "K27Coordinate!=SourceIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
