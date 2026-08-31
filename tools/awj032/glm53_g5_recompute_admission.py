"""G5 v2: bounded G3 recompute admission after current G4-v2 invalidation.

D0 / HS1 / NONPROMOTING.

Current G4-v2 separates structural equality from owner-authenticated currentness:
matching caller labels yield STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED, never reuse.
G5-v2 therefore treats that state as a HOLD. Only an actual G4-v2
HOLD_RECOMPUTE_G3 may enter this recompute-admission membrane.

Exactly two foreign semantic parents are consumed as closed projections:
* PR #759: K27/scheme route aliases cannot reset retrieval no-progress debt.
* PR #755: explicit version transitions do not pay future read-currentness debt.

No retrieval, model/provider work, transfer, routing mutation, persistence or
physical I/O is executed here. Coordinate memory is not model-prefix KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AURA-GLM53-G5-RECOMPUTE-ADMISSION-v2"

G4_V2_HEAD = "025d619d24d95dd6acc29981b1bd61bce92e25a3"
G4_V2_SOURCE_BLOB = "3e5686c3fe635f59e85768e1270be98175983e03"
G4_V2_TEST_BLOB = "f0b0b6e0c62588e6325452b57bbd8bae246de6a0"
G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED = "STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED"
G4_HOLD_RECOMPUTE = "HOLD_RECOMPUTE_G3"
G4_AXES = (
    "prediction_generation", "calibration_generation", "policy_generation",
    "source_binding_generation", "runtime_generation", "cache_generation",
    "storage_geometry_generation", "host_profile_generation",
)

PR759_SEMANTIC_HEAD = "658b3bc651ee39454f6b94039d26ff76d48f73d8"
PR759_SOURCE_BLOB = "1abd821beb2a8a9a96b5ac2f0956195b20a321c7"
PR759_TEST_BLOB = "ddc88a73f49d6a09d67b388cf5c4958317e10ae2"
PR759_PROOF_HEAD = "cf6b07e5c498d7c429e6679a8ba5cec5e1e46ca6"
PR759_PROOF_RUN = 33436588718
PR759_PROOF_JOB = 99634405807

PR755_HEAD = "162fdb9c69f288090845453a67d1f41da28e8a53"
PR755_SOURCE_BLOB = "7ac33764ee238098a2887af96344ed642565ac48"
PR755_TEST_BLOB = "10c83c2432636908b237fe171eebd0714a10788f"
PR755_PROOF_RUN = 33435683382
PR755_PROOF_JOB = 99631408076

ALLOW_INITIAL = "ALLOW_INITIAL"
ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
COLLAPSE_CONE = "COLLAPSE_CONE"
HOLD_ALIAS_RESOLUTION_REQUIRED = "HOLD_ALIAS_RESOLUTION_REQUIRED"
BASE_PROGRESS_DISPOSITIONS = (
    ALLOW_INITIAL, ALLOW_CHANGED_AXIS, ALLOW_STATE_TRANSITION,
    CHANGE_AXIS_REQUIRED, COLLAPSE_CONE,
)
PROGRESS_DISPOSITIONS = BASE_PROGRESS_DISPOSITIONS + (HOLD_ALIAS_RESOLUTION_REQUIRED,)
PROGRESS_ADMISSIBLE = frozenset((ALLOW_INITIAL, ALLOW_CHANGED_AXIS, ALLOW_STATE_TRANSITION))

READ_RESOLVED_CURRENT = "RESOLVED_CURRENT"
READ_STALE = "STALE"
READ_UNKNOWN = "UNKNOWN"
READ_STATES = (READ_RESOLVED_CURRENT, READ_STALE, READ_UNKNOWN)

HOLD_G4_OWNER_CURRENTNESS_REQUIRED = "HOLD_G4_OWNER_CURRENTNESS_REQUIRED"
HOLD_ALIAS_RESOLUTION = "HOLD_ALIAS_RESOLUTION_REQUIRED"
HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED = "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
COLLAPSE_RECOMPUTE_CONE = "COLLAPSE_RECOMPUTE_CONE"
HOLD_VERSION_TRANSITION_REQUIRED = "HOLD_VERSION_TRANSITION_REQUIRED"
HOLD_SOURCE_READ_CURRENTNESS_REQUIRED = "HOLD_SOURCE_READ_CURRENTNESS_REQUIRED"
ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT = "ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


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
class G4V2RevalidationProjection:
    receipt_digest: str
    disposition: str
    changed_axes: tuple[str, ...]
    frozen_source_binding_generation: str
    current_source_binding_generation: str
    owner_currentness_authentication_required: bool = True
    owner_currentness_authenticated_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.receipt_digest, "G4_V2_RECEIPT_DIGEST")
        _required(self.frozen_source_binding_generation, "FROZEN_SOURCE_BINDING_GENERATION")
        _required(self.current_source_binding_generation, "CURRENT_SOURCE_BINDING_GENERATION")
        changed_set = set(self.changed_axes)
        canonical = tuple(axis for axis in G4_AXES if axis in changed_set)
        if canonical != self.changed_axes or len(changed_set) != len(self.changed_axes):
            raise ValueError("G4_V2_CHANGED_AXES_MUST_BE_CANONICAL_UNIQUE")
        source_drift = self.frozen_source_binding_generation != self.current_source_binding_generation
        if source_drift != ("source_binding_generation" in changed_set):
            raise ValueError("G4_V2_SOURCE_BINDING_DRIFT_DECLARATION_MISMATCH")
        if not self.owner_currentness_authentication_required:
            raise ValueError("G4_V2_OWNER_CURRENTNESS_AUTHENTICATION_MUST_REMAIN_REQUIRED")
        if self.owner_currentness_authenticated_by_this_contract:
            raise ValueError("G5_CANNOT_SELF_AUTHENTICATE_G4_OWNER_CURRENTNESS")
        if self.disposition == G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED:
            if self.changed_axes or source_drift:
                raise ValueError("G4_V2_STRUCTURAL_MATCH_CANNOT_HAVE_DRIFT")
        elif self.disposition == G4_HOLD_RECOMPUTE:
            if not self.changed_axes:
                raise ValueError("G4_V2_RECOMPUTE_HOLD_REQUIRES_DRIFT")
        else:
            raise ValueError("G4_V2_DISPOSITION_INVALID_OR_LEGACY")

    @property
    def source_binding_changed(self) -> bool:
        self.validate()
        return "source_binding_generation" in self.changed_axes


@dataclass(frozen=True)
class AliasStableProgressProjection:
    receipt_digest: str
    decision: str
    semantic_fingerprint_digest: str
    source_sid: str
    provider_state_generation: str
    evidence_digest: str
    route_projection_changed: bool
    source_sid_same: bool
    alias_projection_required: bool
    alias_projection_consumed: bool
    raw_decision: str | None = None
    semantic_decision: str | None = None
    source_currentness_proven: bool = False
    authority_granted: bool = False
    semantic_k27_authority_minted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        _sha256(self.receipt_digest, "ALIAS_PROGRESS_RECEIPT_DIGEST")
        _sha256(self.semantic_fingerprint_digest, "SEMANTIC_FINGERPRINT_DIGEST")
        _required(self.source_sid, "SOURCE_SID")
        _required(self.provider_state_generation, "PROVIDER_STATE_GENERATION")
        _sha256(self.evidence_digest, "EVIDENCE_DIGEST")
        if self.decision not in PROGRESS_DISPOSITIONS:
            raise ValueError("ALIAS_PROGRESS_DECISION_INVALID")
        if self.raw_decision is not None and self.raw_decision not in BASE_PROGRESS_DISPOSITIONS:
            raise ValueError("ALIAS_PROGRESS_RAW_DECISION_INVALID")
        if self.semantic_decision is not None and self.semantic_decision not in BASE_PROGRESS_DISPOSITIONS:
            raise ValueError("ALIAS_PROGRESS_SEMANTIC_DECISION_INVALID")

        # PR #759 computes this relation internally. Recompute the invariant here so a
        # caller cannot suppress alias debt and re-label route motion as semantic progress.
        expected_alias_required = self.route_projection_changed and self.source_sid_same
        if self.alias_projection_required != expected_alias_required:
            raise ValueError("ALIAS_REQUIREMENT_MUST_MATCH_SAME_SID_ROUTE_CHANGE")
        if self.alias_projection_consumed and not self.alias_projection_required:
            raise ValueError("ALIAS_PROJECTION_CONSUMED_WHEN_NOT_REQUIRED")

        if self.decision == HOLD_ALIAS_RESOLUTION_REQUIRED:
            if not self.alias_projection_required or self.alias_projection_consumed:
                raise ValueError("ALIAS_HOLD_STATE_INCONSISTENT")
            if self.semantic_decision is not None:
                raise ValueError("UNRESOLVED_ALIAS_CANNOT_HAVE_SEMANTIC_DECISION")
            if self.raw_decision is None:
                raise ValueError("UNRESOLVED_ALIAS_REQUIRES_RAW_DECISION")
        else:
            if self.alias_projection_required and not self.alias_projection_consumed:
                raise ValueError("UNRESOLVED_ALIAS_CANNOT_MINT_PROGRESS")
            if self.semantic_decision != self.decision:
                raise ValueError("ALIAS_PROGRESS_DECISION_MUST_BIND_SEMANTIC_DECISION")
            if self.raw_decision is None:
                raise ValueError("ALIAS_PROGRESS_RAW_DECISION_REQUIRED")

        # #759 initial retrieval has no previous view, therefore cannot claim same-SID
        # continuity or route movement. This blocks caller-forged initial resets.
        if self.decision == ALLOW_INITIAL:
            if self.source_sid_same or self.route_projection_changed or self.alias_projection_required or self.alias_projection_consumed:
                raise ValueError("INITIAL_PROGRESS_CANNOT_CLAIM_PRIOR_ROUTE_OR_SID")
            if self.raw_decision != ALLOW_INITIAL or self.semantic_decision != ALLOW_INITIAL:
                raise ValueError("INITIAL_PROGRESS_DECISION_SHAPE_INVALID")

        if any((self.source_currentness_proven, self.authority_granted,
                self.semantic_k27_authority_minted, self.native_private_transformer_kv_accessed)):
            raise ValueError("ALIAS_PROGRESS_PROJECTION_EXCEEDS_CLAIM_CEILING")


@dataclass(frozen=True)
class VersionTransitionProjection:
    receipt_digest: str
    predecessor_source_binding_generation: str
    successor_source_binding_generation: str
    explicit_successor_edge: bool
    future_read_currentness_required: bool
    source_currentness_proven_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.receipt_digest, "VERSION_TRANSITION_RECEIPT_DIGEST")
        _required(self.predecessor_source_binding_generation, "VERSION_PREDECESSOR")
        _required(self.successor_source_binding_generation, "VERSION_SUCCESSOR")
        if self.predecessor_source_binding_generation == self.successor_source_binding_generation:
            raise ValueError("VERSION_TRANSITION_REQUIRES_DISTINCT_GENERATIONS")
        if not self.explicit_successor_edge:
            raise ValueError("EXPLICIT_SUCCESSOR_EDGE_REQUIRED")
        if not self.future_read_currentness_required:
            raise ValueError("FUTURE_READ_CURRENTNESS_DEBT_MUST_BE_CARRIED")
        if self.source_currentness_proven_by_this_contract:
            raise ValueError("VERSION_TRANSITION_CANNOT_SELF_PROVE_CURRENTNESS")


@dataclass(frozen=True)
class SourceReadCurrentnessProjection:
    witness_digest: str
    source_binding_generation: str
    owner_generation: str
    state: str
    authenticated_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.witness_digest, "READ_CURRENTNESS_WITNESS_DIGEST")
        _required(self.source_binding_generation, "READ_SOURCE_BINDING_GENERATION")
        _required(self.owner_generation, "READ_CURRENTNESS_OWNER_GENERATION")
        if self.state not in READ_STATES:
            raise ValueError("READ_CURRENTNESS_STATE_INVALID")
        if self.authenticated_by_this_contract:
            raise ValueError("G5_CANNOT_SELF_AUTHENTICATE_READ_CURRENTNESS_OWNER")


@dataclass(frozen=True)
class G5V2Receipt:
    schema: str
    g4_v2_head: str
    pr759_semantic_head: str
    pr759_proof_head: str
    pr759_proof_run: int
    pr759_proof_job: int
    pr755_head: str
    pr755_proof_run: int
    pr755_proof_job: int
    g4_receipt_digest: str
    progress_receipt_digest: str
    version_transition_receipt_digest: str | None
    read_currentness_witness_digest: str | None
    disposition: str
    source_binding_changed: bool
    bounded_g3_recompute_attempt_admitted: bool
    g4_owner_currentness_resolved_by_this_contract: bool = False
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
            raise ValueError("G5_V2_SCHEMA_MISMATCH")
        if self.g4_v2_head != G4_V2_HEAD:
            raise ValueError("G5_V2_G4_HEAD_MISMATCH")
        if (self.pr759_semantic_head, self.pr759_proof_head, self.pr759_proof_run, self.pr759_proof_job) != (
            PR759_SEMANTIC_HEAD, PR759_PROOF_HEAD, PR759_PROOF_RUN, PR759_PROOF_JOB):
            raise ValueError("G5_V2_PR759_PROOF_COORDINATE_MISMATCH")
        if (self.pr755_head, self.pr755_proof_run, self.pr755_proof_job) != (
            PR755_HEAD, PR755_PROOF_RUN, PR755_PROOF_JOB):
            raise ValueError("G5_V2_PR755_PROOF_COORDINATE_MISMATCH")
        if self.bounded_g3_recompute_attempt_admitted != (self.disposition == ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT):
            raise ValueError("G5_V2_ADMISSION_BOOLEAN_MISMATCH")
        forbidden = (
            self.g4_owner_currentness_resolved_by_this_contract,
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
        if any(forbidden):
            raise ValueError("G5_V2_CANNOT_WIDEN_CURRENTNESS_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def _validate_join(g4: G4V2RevalidationProjection, progress: AliasStableProgressProjection,
                   version: VersionTransitionProjection | None,
                   currentness: SourceReadCurrentnessProjection | None) -> None:
    g4.validate(); progress.validate()
    if version is not None: version.validate()
    if currentness is not None: currentness.validate()
    if g4.source_binding_changed and version is not None:
        if version.predecessor_source_binding_generation != g4.frozen_source_binding_generation:
            raise ValueError("VERSION_PREDECESSOR_DOES_NOT_BIND_G4_FROZEN_SOURCE")
        if version.successor_source_binding_generation != g4.current_source_binding_generation:
            raise ValueError("VERSION_SUCCESSOR_DOES_NOT_BIND_G4_CURRENT_SOURCE")
    if currentness is not None and currentness.source_binding_generation != g4.current_source_binding_generation:
        raise ValueError("READ_CURRENTNESS_DOES_NOT_BIND_G4_CURRENT_SOURCE")


def disposition_tree(*, g4: G4V2RevalidationProjection, progress: AliasStableProgressProjection,
                     version: VersionTransitionProjection | None,
                     currentness: SourceReadCurrentnessProjection | None) -> str:
    _validate_join(g4, progress, version, currentness)
    if g4.disposition == G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED:
        return HOLD_G4_OWNER_CURRENTNESS_REQUIRED
    if progress.decision == HOLD_ALIAS_RESOLUTION_REQUIRED:
        return HOLD_ALIAS_RESOLUTION
    if progress.decision == COLLAPSE_CONE:
        return COLLAPSE_RECOMPUTE_CONE
    if progress.decision == CHANGE_AXIS_REQUIRED:
        return HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if progress.decision not in PROGRESS_ADMISSIBLE:
        raise AssertionError("UNHANDLED_PROGRESS_STATE")
    if g4.source_binding_changed:
        if version is None:
            return HOLD_VERSION_TRANSITION_REQUIRED
        if currentness is None or currentness.state != READ_RESOLVED_CURRENT:
            return HOLD_SOURCE_READ_CURRENTNESS_REQUIRED
    return ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT


def disposition_table(*, g4: G4V2RevalidationProjection, progress: AliasStableProgressProjection,
                      version: VersionTransitionProjection | None,
                      currentness: SourceReadCurrentnessProjection | None) -> str:
    _validate_join(g4, progress, version, currentness)
    rows = (
        (g4.disposition == G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED, HOLD_G4_OWNER_CURRENTNESS_REQUIRED),
        (progress.decision == HOLD_ALIAS_RESOLUTION_REQUIRED, HOLD_ALIAS_RESOLUTION),
        (progress.decision == COLLAPSE_CONE, COLLAPSE_RECOMPUTE_CONE),
        (progress.decision == CHANGE_AXIS_REQUIRED, HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED),
        (g4.source_binding_changed and version is None, HOLD_VERSION_TRANSITION_REQUIRED),
        (g4.source_binding_changed and version is not None and (currentness is None or currentness.state != READ_RESOLVED_CURRENT), HOLD_SOURCE_READ_CURRENTNESS_REQUIRED),
        (True, ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT),
    )
    return next(disposition for condition, disposition in rows if condition)


def assess_g3_recompute_admission(*, g4: G4V2RevalidationProjection,
                                  progress: AliasStableProgressProjection,
                                  version: VersionTransitionProjection | None = None,
                                  currentness: SourceReadCurrentnessProjection | None = None) -> G5V2Receipt:
    tree = disposition_tree(g4=g4, progress=progress, version=version, currentness=currentness)
    table = disposition_table(g4=g4, progress=progress, version=version, currentness=currentness)
    if tree != table:
        raise AssertionError("G5_V2_DIFFERENT_J_CLASSIFIERS_DISAGREE")
    receipt = G5V2Receipt(
        schema=SCHEMA,
        g4_v2_head=G4_V2_HEAD,
        pr759_semantic_head=PR759_SEMANTIC_HEAD,
        pr759_proof_head=PR759_PROOF_HEAD,
        pr759_proof_run=PR759_PROOF_RUN,
        pr759_proof_job=PR759_PROOF_JOB,
        pr755_head=PR755_HEAD,
        pr755_proof_run=PR755_PROOF_RUN,
        pr755_proof_job=PR755_PROOF_JOB,
        g4_receipt_digest=g4.receipt_digest,
        progress_receipt_digest=progress.receipt_digest,
        version_transition_receipt_digest=None if version is None else version.receipt_digest,
        read_currentness_witness_digest=None if currentness is None else currentness.witness_digest,
        disposition=tree,
        source_binding_changed=g4.source_binding_changed,
        bounded_g3_recompute_attempt_admitted=(tree == ADMIT_BOUNDED_G3_RECOMPUTE_ATTEMPT),
    )
    receipt.validate_claim_ceiling()
    return receipt


def _progress_case(decision: str) -> AliasStableProgressProjection:
    if decision == ALLOW_INITIAL:
        return AliasStableProgressProjection(
            receipt_digest="b" * 64,
            decision=decision,
            semantic_fingerprint_digest="c" * 64,
            source_sid="sid::glm53",
            provider_state_generation="provider::17",
            evidence_digest="d" * 64,
            route_projection_changed=False,
            source_sid_same=False,
            alias_projection_required=False,
            alias_projection_consumed=False,
            raw_decision=ALLOW_INITIAL,
            semantic_decision=ALLOW_INITIAL,
        )
    if decision == HOLD_ALIAS_RESOLUTION_REQUIRED:
        return AliasStableProgressProjection(
            receipt_digest="b" * 64,
            decision=decision,
            semantic_fingerprint_digest="c" * 64,
            source_sid="sid::glm53",
            provider_state_generation="provider::17",
            evidence_digest="d" * 64,
            route_projection_changed=True,
            source_sid_same=True,
            alias_projection_required=True,
            alias_projection_consumed=False,
            raw_decision=ALLOW_CHANGED_AXIS,
            semantic_decision=None,
        )
    return AliasStableProgressProjection(
        receipt_digest="b" * 64,
        decision=decision,
        semantic_fingerprint_digest="c" * 64,
        source_sid="sid::glm53",
        provider_state_generation="provider::17",
        evidence_digest="d" * 64,
        route_projection_changed=False,
        source_sid_same=True,
        alias_projection_required=False,
        alias_projection_consumed=False,
        raw_decision=decision,
        semantic_decision=decision,
    )


def prove_finite_recompute_lattice() -> dict[str, int]:
    """Exhaust the valid bounded control lattice through two independent classifiers."""
    counts: dict[str, int] = {"states": 0}
    for structural_match in (False, True):
        for source_changed in (False, True):
            if structural_match and source_changed:
                continue
            g4 = G4V2RevalidationProjection(
                receipt_digest="a" * 64,
                disposition=(G4_STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED if structural_match else G4_HOLD_RECOMPUTE),
                changed_axes=() if structural_match else (("source_binding_generation",) if source_changed else ("runtime_generation",)),
                frozen_source_binding_generation="source::17",
                current_source_binding_generation="source::18" if source_changed else "source::17",
            )
            for decision in PROGRESS_DISPOSITIONS:
                progress = _progress_case(decision)
                for version_present in (False, True):
                    version = VersionTransitionProjection(
                        receipt_digest="e" * 64,
                        predecessor_source_binding_generation="source::17",
                        successor_source_binding_generation="source::18",
                        explicit_successor_edge=True,
                        future_read_currentness_required=True,
                    ) if version_present and source_changed else None
                    for read_state in READ_STATES:
                        currentness = SourceReadCurrentnessProjection(
                            witness_digest="f" * 64,
                            source_binding_generation="source::18" if source_changed else "source::17",
                            owner_generation="read-owner::17",
                            state=read_state,
                        )
                        kwargs = dict(g4=g4, progress=progress, version=version, currentness=currentness)
                        a = disposition_tree(**kwargs); b = disposition_table(**kwargs)
                        if a != b:
                            raise AssertionError("G5_V2_FINITE_PROOF_DISAGREEMENT")
                        counts["states"] += 1
                        counts[a] = counts.get(a, 0) + 1
    return counts
