"""G5-v2 W3: owner-resolved G4 drift premise gate.

D0 / HS1 / NONPROMOTING / STACKED ADDENDUM TO PR #774.

PR #774 correctly makes structural equality a HOLD, but its drift projection is
still caller-constructible. This module does not reimplement G5-v2. It wraps the
canonical G5-v2 classifier and prevents a raw structural G4 drift projection from
becoming the strongest downstream recompute consequence by itself.

A drift may become only an OWNER_RESOLVED_RECOMPUTE_CANDIDATE after one injected
owner resolver returns an exact observation while a stable owner-state epoch
brackets the consequence-changing read. The resolver itself is an external trust
boundary: this pure contract does not authenticate its producer or prove that an
epoch token is globally change-complete/non-reused.

Exactly two terminal-green foreign laws motivate the membrane:
* O65 / PR #704: separately current reads do not establish one serializable owner
  state; one owner epoch must bracket the read set.
* PR #769: AdmissionValidAtProduce != AdmissionReusableAtUse; current-use
  generation drift requires revalidation from the appropriate owner.

No G3 recompute, retrieval, model/provider work, transfer, routing, persistence,
physical I/O, Gate-10 promotion or effect authority is executed or granted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

from tools.awj032.glm53_g5_recompute_admission import (
    ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT,
    G4_AXES,
    G4_HOLD_RECOMPUTE,
    G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED,
    G4V2RevalidationProjection,
    AliasStableProgressProjection,
    SourceReadCurrentnessProjection,
    VersionTransitionProjection,
    assess_g3_recompute_admission,
)

SCHEMA = "AURA-GLM53-G5-OWNER-RESOLVED-RECOMPUTE-PREMISE-v1"
G5_V2_OWNER_HEAD_AT_CUT = "5c18883358d041846d7451bdcfa3a5739af675b1"

O65_SEMANTIC_PROOF_HEAD = "7efca33d95f6dc39c4e159250d45373b260060ed"
O65_PROOF_RUN = 33410032496
O65_PROOF_JOB = 99546999922

PR769_PROOF_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
PR769_PROOF_RUN = 33437612722
PR769_PROOF_JOB = 99637780915

OWNER_RESOLVED_G4_HOLD = "HOLD_RECOMPUTE_G3_OWNER_RESOLVED"

HOLD_G4_OWNER_RESOLVED_DRIFT_REQUIRED = "HOLD_G4_OWNER_RESOLVED_DRIFT_REQUIRED"
HOLD_G4_OWNER_RESOLUTION_FAILED = "HOLD_G4_OWNER_RESOLUTION_FAILED"
HOLD_G4_OWNER_EPOCH_CHANGED = "HOLD_G4_OWNER_EPOCH_CHANGED"
HOLD_G4_OWNER_OBSERVATION_MISMATCH = "HOLD_G4_OWNER_OBSERVATION_MISMATCH"
BASE_G5_HOLD = "BASE_G5_HOLD"
OWNER_RESOLVED_RECOMPUTE_CANDIDATE = "OWNER_RESOLVED_RECOMPUTE_CANDIDATE"


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


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: str, name: str) -> str:
    value = _required(value, name)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{name}_MUST_BE_LOWER_HEX_SHA256")
    return value


@dataclass(frozen=True)
class OwnerResolvedG4DriftObservation:
    observation_digest: str
    g4_receipt_digest: str
    disposition: str
    changed_axes: tuple[str, ...]
    frozen_source_binding_generation: str
    current_source_binding_generation: str
    owner_state_epoch: str
    owner_resolver_generation: str
    resolver_authenticated_by_this_contract: bool = False
    owner_currentness_truth_proven_by_this_contract: bool = False
    epoch_change_complete_proven_by_this_contract: bool = False
    reuse_authorized_by_this_contract: bool = False
    recompute_executed_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.observation_digest, "OWNER_G4_OBSERVATION_DIGEST")
        _sha256(self.g4_receipt_digest, "OWNER_G4_RECEIPT_DIGEST")
        if self.disposition != OWNER_RESOLVED_G4_HOLD:
            raise ValueError("OWNER_G4_DRIFT_DISPOSITION_REQUIRED")
        changed_set = set(self.changed_axes)
        if not changed_set:
            raise ValueError("OWNER_G4_DRIFT_REQUIRES_CHANGED_AXIS")
        if len(changed_set) != len(self.changed_axes):
            raise ValueError("OWNER_G4_CHANGED_AXES_MUST_BE_UNIQUE")
        if tuple(axis for axis in G4_AXES if axis in changed_set) != self.changed_axes:
            raise ValueError("OWNER_G4_CHANGED_AXES_MUST_BE_CANONICAL")
        _required(self.frozen_source_binding_generation, "OWNER_G4_FROZEN_SOURCE_GENERATION")
        _required(self.current_source_binding_generation, "OWNER_G4_CURRENT_SOURCE_GENERATION")
        _required(self.owner_state_epoch, "OWNER_G4_STATE_EPOCH")
        _required(self.owner_resolver_generation, "OWNER_G4_RESOLVER_GENERATION")
        if any(
            (
                self.resolver_authenticated_by_this_contract,
                self.owner_currentness_truth_proven_by_this_contract,
                self.epoch_change_complete_proven_by_this_contract,
                self.reuse_authorized_by_this_contract,
                self.recompute_executed_by_this_contract,
            )
        ):
            raise ValueError("OWNER_G4_OBSERVATION_CANNOT_SELF_MINT_TRUST_OR_EFFECT")


class G4DriftOwnerResolver(Protocol):
    """Injected owner/runtime boundary; producer trust is external to this contract."""

    def resolve_state_epoch(self, *, g4_receipt_digest: str) -> str: ...

    def resolve_g4_drift(
        self, *, g4_receipt_digest: str
    ) -> OwnerResolvedG4DriftObservation: ...


@dataclass(frozen=True)
class G5OwnerResolvedPremiseReceipt:
    schema: str
    g5_v2_owner_head_at_cut: str
    o65_semantic_proof_head: str
    o65_proof_run: int
    o65_proof_job: int
    pr769_proof_head: str
    pr769_proof_run: int
    pr769_proof_job: int
    g4_receipt_digest: str
    base_g5_receipt_digest: str
    base_g5_disposition: str
    owner_observation_digest: str | None
    owner_state_epoch: str | None
    owner_resolver_generation: str | None
    disposition: str
    owner_resolved_recompute_candidate: bool
    raw_structural_projection_sufficient: bool = False
    resolver_authenticated_by_this_contract: bool = False
    owner_currentness_truth_proven_by_this_contract: bool = False
    epoch_change_complete_proven_by_this_contract: bool = False
    bounded_g3_recompute_attempt_admitted_by_this_contract: bool = False
    recompute_executed_by_this_contract: bool = False
    retrieval_or_provider_effect_authorized: bool = False
    transfer_effect_authorized: bool = False
    native_route_mutated: bool = False
    physical_io_proven: bool = False
    source_currentness_minted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_financial_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("G5_OWNER_PREMISE_SCHEMA_MISMATCH")
        if self.g5_v2_owner_head_at_cut != G5_V2_OWNER_HEAD_AT_CUT:
            raise ValueError("G5_OWNER_PREMISE_G5_HEAD_MISMATCH")
        if (self.o65_semantic_proof_head, self.o65_proof_run, self.o65_proof_job) != (
            O65_SEMANTIC_PROOF_HEAD, O65_PROOF_RUN, O65_PROOF_JOB
        ):
            raise ValueError("G5_OWNER_PREMISE_O65_PROOF_MISMATCH")
        if (self.pr769_proof_head, self.pr769_proof_run, self.pr769_proof_job) != (
            PR769_PROOF_HEAD, PR769_PROOF_RUN, PR769_PROOF_JOB
        ):
            raise ValueError("G5_OWNER_PREMISE_PR769_PROOF_MISMATCH")
        _sha256(self.g4_receipt_digest, "G5_OWNER_PREMISE_G4_RECEIPT_DIGEST")
        _sha256(self.base_g5_receipt_digest, "G5_OWNER_PREMISE_BASE_G5_RECEIPT_DIGEST")
        expected_candidate = self.disposition == OWNER_RESOLVED_RECOMPUTE_CANDIDATE
        if self.owner_resolved_recompute_candidate != expected_candidate:
            raise ValueError("G5_OWNER_PREMISE_CANDIDATE_BOOLEAN_MISMATCH")
        if expected_candidate:
            if not (self.owner_observation_digest and self.owner_state_epoch and self.owner_resolver_generation):
                raise ValueError("G5_OWNER_PREMISE_CANDIDATE_REQUIRES_OWNER_OBSERVATION")
            _sha256(self.owner_observation_digest, "G5_OWNER_PREMISE_OWNER_OBSERVATION_DIGEST")
        if self.raw_structural_projection_sufficient:
            raise ValueError("RAW_G4_STRUCTURAL_PROJECTION_CANNOT_BE_SUFFICIENT")
        if any(
            (
                self.resolver_authenticated_by_this_contract,
                self.owner_currentness_truth_proven_by_this_contract,
                self.epoch_change_complete_proven_by_this_contract,
                self.bounded_g3_recompute_attempt_admitted_by_this_contract,
                self.recompute_executed_by_this_contract,
                self.retrieval_or_provider_effect_authorized,
                self.transfer_effect_authorized,
                self.native_route_mutated,
                self.physical_io_proven,
                self.source_currentness_minted,
                self.semantic_k27_authority_minted,
                self.native_private_transformer_kv_accessed,
                self.gate10_promoted,
                self.merge_deploy_spend_public_financial_human_effect,
            )
        ):
            raise ValueError("G5_OWNER_PREMISE_CANNOT_WIDEN_TRUST_EXECUTION_OR_EFFECT")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def _receipt(
    *,
    g4: G4V2RevalidationProjection,
    base_receipt: Any,
    disposition: str,
    observation: OwnerResolvedG4DriftObservation | None = None,
) -> G5OwnerResolvedPremiseReceipt:
    result = G5OwnerResolvedPremiseReceipt(
        schema=SCHEMA,
        g5_v2_owner_head_at_cut=G5_V2_OWNER_HEAD_AT_CUT,
        o65_semantic_proof_head=O65_SEMANTIC_PROOF_HEAD,
        o65_proof_run=O65_PROOF_RUN,
        o65_proof_job=O65_PROOF_JOB,
        pr769_proof_head=PR769_PROOF_HEAD,
        pr769_proof_run=PR769_PROOF_RUN,
        pr769_proof_job=PR769_PROOF_JOB,
        g4_receipt_digest=g4.receipt_digest,
        base_g5_receipt_digest=base_receipt.receipt_digest,
        base_g5_disposition=base_receipt.disposition,
        owner_observation_digest=None if observation is None else observation.observation_digest,
        owner_state_epoch=None if observation is None else observation.owner_state_epoch,
        owner_resolver_generation=None if observation is None else observation.owner_resolver_generation,
        disposition=disposition,
        owner_resolved_recompute_candidate=(disposition == OWNER_RESOLVED_RECOMPUTE_CANDIDATE),
    )
    result.validate_claim_ceiling()
    return result


def _observation_matches(
    *, g4: G4V2RevalidationProjection, observation: OwnerResolvedG4DriftObservation
) -> bool:
    observation.validate()
    return (
        observation.g4_receipt_digest == g4.receipt_digest
        and observation.changed_axes == g4.changed_axes
        and observation.frozen_source_binding_generation == g4.frozen_source_binding_generation
        and observation.current_source_binding_generation == g4.current_source_binding_generation
    )


def assess_owner_resolved_recompute_premise(
    *,
    g4: G4V2RevalidationProjection,
    progress: AliasStableProgressProjection,
    version: VersionTransitionProjection | None = None,
    currentness: SourceReadCurrentnessProjection | None = None,
    resolver: G4DriftOwnerResolver | None = None,
) -> G5OwnerResolvedPremiseReceipt:
    """Wrap canonical G5-v2 and prevent raw drift projection -> recompute admission.

    Structural-match and all ordinary G5 HOLD states retain their base disposition.
    If canonical G5-v2 would emit ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT, this wrapper
    requires an exact owner-resolved drift observation inside one stable epoch.
    Even then, the strongest output is only OWNER_RESOLVED_RECOMPUTE_CANDIDATE.
    """
    g4.validate()
    base_receipt = assess_g3_recompute_admission(
        g4=g4,
        progress=progress,
        version=version,
        currentness=currentness,
    )

    if base_receipt.disposition != ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT:
        return _receipt(g4=g4, base_receipt=base_receipt, disposition=BASE_G5_HOLD)

    if g4.disposition != G4_HOLD_RECOMPUTE or not g4.changed_axes:
        raise AssertionError("G5_OWNER_PREMISE_BASE_ADMISSION_WITHOUT_G4_DRIFT")
    if resolver is None:
        return _receipt(
            g4=g4,
            base_receipt=base_receipt,
            disposition=HOLD_G4_OWNER_RESOLVED_DRIFT_REQUIRED,
        )

    try:
        epoch_before = _required(
            resolver.resolve_state_epoch(g4_receipt_digest=g4.receipt_digest),
            "OWNER_EPOCH_BEFORE",
        )
        observation = resolver.resolve_g4_drift(g4_receipt_digest=g4.receipt_digest)
        if not isinstance(observation, OwnerResolvedG4DriftObservation):
            return _receipt(
                g4=g4,
                base_receipt=base_receipt,
                disposition=HOLD_G4_OWNER_RESOLUTION_FAILED,
            )
        observation.validate()
        epoch_after = _required(
            resolver.resolve_state_epoch(g4_receipt_digest=g4.receipt_digest),
            "OWNER_EPOCH_AFTER",
        )
    except Exception:
        return _receipt(
            g4=g4,
            base_receipt=base_receipt,
            disposition=HOLD_G4_OWNER_RESOLUTION_FAILED,
        )

    if epoch_before != epoch_after or observation.owner_state_epoch != epoch_before:
        return _receipt(
            g4=g4,
            base_receipt=base_receipt,
            disposition=HOLD_G4_OWNER_EPOCH_CHANGED,
        )
    if not _observation_matches(g4=g4, observation=observation):
        return _receipt(
            g4=g4,
            base_receipt=base_receipt,
            disposition=HOLD_G4_OWNER_OBSERVATION_MISMATCH,
        )

    return _receipt(
        g4=g4,
        base_receipt=base_receipt,
        disposition=OWNER_RESOLVED_RECOMPUTE_CANDIDATE,
        observation=observation,
    )
