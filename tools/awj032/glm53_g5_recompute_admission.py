"""G5 v2: trust-quarantined recompute candidate after G4 structural invalidation.

D0 / HS1 / NONPROMOTING.

G4 v2 proves only a structural eight-axis comparison. A structural match does not
authenticate owner currentness, and a structural drift does not by itself grant
recompute execution authority. The historical hosted SUCCESS at 68d76cb7... is
a proof-plumbing descendant of the superseded pre-W3 G4 source and is retained
only as a scar; it is not terminal proof for repaired G4 v2.

G5 joins the two independent downstream laws from PR #754 (activity is not
progress without independent delta) and PR #755 (version transition is not
future read currentness), but keeps every positive outcome as a candidate until
an external owner/currentness trust boundary and repaired-G4 terminal proof are
available.

Laws:
    SupersededProofSuccess != RepairedSemanticProof
    StructuralG4Match != AuthenticatedNoRecomputeDecision
    CallerResolvedCurrent != AuthenticatedOwnerCurrentness
    CandidateRecompute != RecomputeAdmission != RecomputeExecution
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA = "AURA-GLM53-G5-RECOMPUTE-ADMISSION-v2"

G4_REPAIRED_SEMANTIC_HEAD = "025d619d24d95dd6acc29981b1bd61bce92e25a3"
G4_SUPERSEDED_PROOF_HEAD = "68d76cb7d08366d085be13ad68871ab3c9cf00e1"
G4_SUPERSEDED_PROOF_RUN = 33436142388
G4_SUPERSEDED_PROOF_JOB = 99632931053

PR754_OWNER_HEAD = "412e683b8a3d28bd57e4dc39059283cc823e2fb3"
PR754_SOURCE_BLOB = "5e20a51af1bbafa17c56b3a80125bcf003cc6b62"
PR754_TEST_BLOB = "fd70a6a2ba38220f633c7becf421fbe472bd6b6b"
PR754_PROOF_MIRROR_HEAD = "f85135562a5975cd7ea1892ab1c221d9004d3e0d"
PR754_PROOF_RUN = 33435590114
PR754_PROOF_JOB = 99631099474

PR755_HEAD = "162fdb9c69f288090845453a67d1f41da28e8a53"
PR755_SOURCE_BLOB = "7ac33764ee238098a2887af96344ed642565ac48"
PR755_TEST_BLOB = "10c83c2432636908b237fe171eebd0714a10788f"
PR755_PROOF_RUN = 33435683382
PR755_PROOF_JOB = 99631408076

G4_STRUCTURAL_MATCH = "STRUCTURAL_MATCH_OWNER_AUTH_REQUIRED"
G4_HOLD_RECOMPUTE = "HOLD_RECOMPUTE_G3"
G4_AXES = (
    "prediction_generation",
    "calibration_generation",
    "policy_generation",
    "source_binding_generation",
    "runtime_generation",
    "cache_generation",
    "storage_geometry_generation",
    "host_profile_generation",
)

PROGRESS_ALLOW_INITIAL = "ALLOW_INITIAL"
PROGRESS_ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
PROGRESS_ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
PROGRESS_CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
PROGRESS_COLLAPSE_CONE = "COLLAPSE_CONE"
PROGRESS_DISPOSITIONS = (
    PROGRESS_ALLOW_INITIAL,
    PROGRESS_ALLOW_CHANGED_AXIS,
    PROGRESS_ALLOW_STATE_TRANSITION,
    PROGRESS_CHANGE_AXIS_REQUIRED,
    PROGRESS_COLLAPSE_CONE,
)

READ_RESOLVED_CURRENT = "RESOLVED_CURRENT"
READ_STALE = "STALE"
READ_UNKNOWN = "UNKNOWN"
READ_STATES = (READ_RESOLVED_CURRENT, READ_STALE, READ_UNKNOWN)

HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED = "HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED"
HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED = "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
COLLAPSE_RECOMPUTE_CONE = "COLLAPSE_RECOMPUTE_CONE"
HOLD_VERSION_TRANSITION_REQUIRED = "HOLD_VERSION_TRANSITION_REQUIRED"
HOLD_SOURCE_READ_CURRENTNESS_REQUIRED = "HOLD_SOURCE_READ_CURRENTNESS_REQUIRED"
CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED = (
    "CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED"
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
class G4RevalidationProjection:
    receipt_digest: str
    disposition: str
    changed_axes: tuple[str, ...]
    frozen_source_binding_generation: str
    current_source_binding_generation: str
    owner_currentness_authenticated: bool = False
    reuse_authorized: bool = False

    def validate(self) -> None:
        _sha256(self.receipt_digest, "G4_RECEIPT_DIGEST")
        _required(self.frozen_source_binding_generation, "FROZEN_SOURCE_BINDING_GENERATION")
        _required(self.current_source_binding_generation, "CURRENT_SOURCE_BINDING_GENERATION")
        canonical = tuple(axis for axis in G4_AXES if axis in set(self.changed_axes))
        if canonical != self.changed_axes or len(set(self.changed_axes)) != len(self.changed_axes):
            raise ValueError("G4_CHANGED_AXES_MUST_BE_CANONICAL_UNIQUE")
        source_drift = (
            self.frozen_source_binding_generation != self.current_source_binding_generation
        )
        declares_source_drift = "source_binding_generation" in self.changed_axes
        if source_drift != declares_source_drift:
            raise ValueError("G4_SOURCE_BINDING_DRIFT_DECLARATION_MISMATCH")
        if self.disposition == G4_STRUCTURAL_MATCH:
            if self.changed_axes:
                raise ValueError("G4_STRUCTURAL_MATCH_CANNOT_HAVE_CHANGED_AXES")
        elif self.disposition == G4_HOLD_RECOMPUTE:
            if not self.changed_axes:
                raise ValueError("G4_HOLD_REQUIRES_CHANGED_AXIS")
        else:
            raise ValueError("G4_DISPOSITION_INVALID")
        if self.owner_currentness_authenticated or self.reuse_authorized:
            raise ValueError("G4_PROJECTION_CANNOT_SELF_MINT_CURRENTNESS_OR_REUSE_AUTHORITY")

    @property
    def source_binding_changed(self) -> bool:
        self.validate()
        return "source_binding_generation" in self.changed_axes


@dataclass(frozen=True)
class RetrievalProgressProjection:
    receipt_digest: str
    disposition: str
    retrieval_fingerprint_digest: str
    provider_state_generation: str
    evidence_digest: str

    def validate(self) -> None:
        _sha256(self.receipt_digest, "PROGRESS_RECEIPT_DIGEST")
        _sha256(self.retrieval_fingerprint_digest, "RETRIEVAL_FINGERPRINT_DIGEST")
        _required(self.provider_state_generation, "PROVIDER_STATE_GENERATION")
        _sha256(self.evidence_digest, "EVIDENCE_DIGEST")
        if self.disposition not in PROGRESS_DISPOSITIONS:
            raise ValueError("PROGRESS_DISPOSITION_INVALID")


@dataclass(frozen=True)
class VersionTransitionProjection:
    receipt_digest: str
    predecessor_source_binding_generation: str
    successor_source_binding_generation: str
    explicit_successor_edge: bool
    future_read_currentness_required: bool
    source_owner_authenticated_by_this_contract: bool = False
    source_currentness_proven_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.receipt_digest, "VERSION_TRANSITION_RECEIPT_DIGEST")
        _required(
            self.predecessor_source_binding_generation,
            "PREDECESSOR_SOURCE_BINDING_GENERATION",
        )
        _required(
            self.successor_source_binding_generation,
            "SUCCESSOR_SOURCE_BINDING_GENERATION",
        )
        if self.predecessor_source_binding_generation == self.successor_source_binding_generation:
            raise ValueError("VERSION_TRANSITION_REQUIRES_DISTINCT_GENERATIONS")
        if not self.explicit_successor_edge:
            raise ValueError("EXPLICIT_SUCCESSOR_EDGE_REQUIRED")
        if not self.future_read_currentness_required:
            raise ValueError("FUTURE_READ_CURRENTNESS_DEBT_MUST_BE_CARRIED")
        if self.source_owner_authenticated_by_this_contract or self.source_currentness_proven_by_this_contract:
            raise ValueError("VERSION_PROJECTION_CANNOT_WIDEN_SOURCE_AUTHORITY")


@dataclass(frozen=True)
class SourceReadCurrentnessProjection:
    witness_digest: str
    source_binding_generation: str
    owner_generation: str
    state: str
    external_owner_authentication_required: bool = True
    authenticated_by_this_contract: bool = False

    def validate(self) -> None:
        _sha256(self.witness_digest, "READ_CURRENTNESS_WITNESS_DIGEST")
        _required(self.source_binding_generation, "READ_SOURCE_BINDING_GENERATION")
        _required(self.owner_generation, "READ_CURRENTNESS_OWNER_GENERATION")
        if self.state not in READ_STATES:
            raise ValueError("READ_CURRENTNESS_STATE_INVALID")
        if self.external_owner_authentication_required is not True:
            raise ValueError("EXTERNAL_OWNER_AUTHENTICATION_MUST_REMAIN_REQUIRED")
        if self.authenticated_by_this_contract:
            raise ValueError("G5_CANNOT_SELF_AUTHENTICATE_CURRENTNESS_OWNER")


@dataclass(frozen=True)
class G5RecomputeAdmissionReceipt:
    schema: str
    g4_repaired_semantic_head: str
    g4_superseded_proof_head: str
    g4_superseded_proof_run: int
    g4_superseded_proof_job: int
    pr754_owner_head: str
    pr754_proof_mirror_head: str
    pr754_proof_run: int
    pr754_proof_job: int
    pr755_head: str
    pr755_proof_run: int
    pr755_proof_job: int
    g4_receipt_digest: str
    progress_receipt_digest: str
    version_transition_receipt_digest: str | None
    read_currentness_witness_digest: str | None
    disposition: str
    source_binding_changed: bool
    bounded_g3_recompute_attempt_admitted: bool = False
    g4_repaired_terminal_proof_required: bool = True
    g4_repaired_terminal_proof_available: bool = False
    external_owner_currentness_auth_required: bool = True
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
            raise ValueError("G5_SCHEMA_MISMATCH")
        if self.g4_repaired_semantic_head != G4_REPAIRED_SEMANTIC_HEAD:
            raise ValueError("G5_G4_REPAIRED_SEMANTIC_HEAD_MISMATCH")
        if (
            self.g4_superseded_proof_head,
            self.g4_superseded_proof_run,
            self.g4_superseded_proof_job,
        ) != (
            G4_SUPERSEDED_PROOF_HEAD,
            G4_SUPERSEDED_PROOF_RUN,
            G4_SUPERSEDED_PROOF_JOB,
        ):
            raise ValueError("G5_G4_SUPERSEDED_PROOF_SCAR_MISMATCH")
        if (
            self.pr754_owner_head,
            self.pr754_proof_mirror_head,
            self.pr754_proof_run,
            self.pr754_proof_job,
        ) != (
            PR754_OWNER_HEAD,
            PR754_PROOF_MIRROR_HEAD,
            PR754_PROOF_RUN,
            PR754_PROOF_JOB,
        ):
            raise ValueError("G5_PR754_PROOF_COORDINATE_MISMATCH")
        if (self.pr755_head, self.pr755_proof_run, self.pr755_proof_job) != (
            PR755_HEAD,
            PR755_PROOF_RUN,
            PR755_PROOF_JOB,
        ):
            raise ValueError("G5_PR755_PROOF_COORDINATE_MISMATCH")
        if self.bounded_g3_recompute_attempt_admitted is not False:
            raise ValueError("G5_V2_CANNOT_ADMIT_RECOMPUTE_WITHOUT_EXTERNAL_TRUST")
        if self.g4_repaired_terminal_proof_required is not True:
            raise ValueError("G4_REPAIRED_TERMINAL_PROOF_MUST_REMAIN_REQUIRED")
        if self.g4_repaired_terminal_proof_available is not False:
            raise ValueError("G5_CANNOT_SELF_MINT_REPAIRED_G4_TERMINAL_PROOF")
        if self.external_owner_currentness_auth_required is not True:
            raise ValueError("EXTERNAL_OWNER_CURRENTNESS_AUTH_MUST_REMAIN_REQUIRED")
        if any(
            (
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
            raise ValueError("G5_CANNOT_WIDEN_EXECUTION_OR_EFFECT_AUTHORITY")

    @property
    def receipt_digest(self) -> str:
        self.validate_claim_ceiling()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def _validate_join(
    g4: G4RevalidationProjection,
    progress: RetrievalProgressProjection,
    version: VersionTransitionProjection | None,
    currentness: SourceReadCurrentnessProjection | None,
) -> None:
    g4.validate()
    progress.validate()
    if version is not None:
        version.validate()
    if currentness is not None:
        currentness.validate()
    if g4.source_binding_changed and version is not None:
        if version.predecessor_source_binding_generation != g4.frozen_source_binding_generation:
            raise ValueError("VERSION_PREDECESSOR_DOES_NOT_BIND_G4_FROZEN_SOURCE")
        if version.successor_source_binding_generation != g4.current_source_binding_generation:
            raise ValueError("VERSION_SUCCESSOR_DOES_NOT_BIND_G4_CURRENT_SOURCE")
    if (
        currentness is not None
        and currentness.source_binding_generation != g4.current_source_binding_generation
    ):
        raise ValueError("READ_CURRENTNESS_DOES_NOT_BIND_G4_CURRENT_SOURCE")


def disposition_tree(
    *,
    g4: G4RevalidationProjection,
    progress: RetrievalProgressProjection,
    version: VersionTransitionProjection | None,
    currentness: SourceReadCurrentnessProjection | None,
) -> str:
    _validate_join(g4, progress, version, currentness)
    if g4.disposition == G4_STRUCTURAL_MATCH:
        return HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED
    if progress.disposition == PROGRESS_COLLAPSE_CONE:
        return COLLAPSE_RECOMPUTE_CONE
    if progress.disposition == PROGRESS_CHANGE_AXIS_REQUIRED:
        return HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if g4.source_binding_changed:
        if version is None:
            return HOLD_VERSION_TRANSITION_REQUIRED
        if currentness is None or currentness.state != READ_RESOLVED_CURRENT:
            return HOLD_SOURCE_READ_CURRENTNESS_REQUIRED
    return CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED


def disposition_table(
    *,
    g4: G4RevalidationProjection,
    progress: RetrievalProgressProjection,
    version: VersionTransitionProjection | None,
    currentness: SourceReadCurrentnessProjection | None,
) -> str:
    _validate_join(g4, progress, version, currentness)
    rows = (
        (g4.disposition == G4_STRUCTURAL_MATCH, HOLD_G4_OWNER_CURRENTNESS_AUTH_REQUIRED),
        (progress.disposition == PROGRESS_COLLAPSE_CONE, COLLAPSE_RECOMPUTE_CONE),
        (progress.disposition == PROGRESS_CHANGE_AXIS_REQUIRED, HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED),
        (g4.source_binding_changed and version is None, HOLD_VERSION_TRANSITION_REQUIRED),
        (
            g4.source_binding_changed
            and version is not None
            and (currentness is None or currentness.state != READ_RESOLVED_CURRENT),
            HOLD_SOURCE_READ_CURRENTNESS_REQUIRED,
        ),
        (True, CANDIDATE_G3_RECOMPUTE_EXTERNAL_TRUST_REQUIRED),
    )
    return next(disposition for condition, disposition in rows if condition)


def assess_g3_recompute_admission(
    *,
    g4: G4RevalidationProjection,
    progress: RetrievalProgressProjection,
    version: VersionTransitionProjection | None = None,
    currentness: SourceReadCurrentnessProjection | None = None,
) -> G5RecomputeAdmissionReceipt:
    tree = disposition_tree(
        g4=g4,
        progress=progress,
        version=version,
        currentness=currentness,
    )
    table = disposition_table(
        g4=g4,
        progress=progress,
        version=version,
        currentness=currentness,
    )
    if tree != table:
        raise AssertionError("G5_DIFFERENT_J_CLASSIFIERS_DISAGREE")
    receipt = G5RecomputeAdmissionReceipt(
        schema=SCHEMA,
        g4_repaired_semantic_head=G4_REPAIRED_SEMANTIC_HEAD,
        g4_superseded_proof_head=G4_SUPERSEDED_PROOF_HEAD,
        g4_superseded_proof_run=G4_SUPERSEDED_PROOF_RUN,
        g4_superseded_proof_job=G4_SUPERSEDED_PROOF_JOB,
        pr754_owner_head=PR754_OWNER_HEAD,
        pr754_proof_mirror_head=PR754_PROOF_MIRROR_HEAD,
        pr754_proof_run=PR754_PROOF_RUN,
        pr754_proof_job=PR754_PROOF_JOB,
        pr755_head=PR755_HEAD,
        pr755_proof_run=PR755_PROOF_RUN,
        pr755_proof_job=PR755_PROOF_JOB,
        g4_receipt_digest=g4.receipt_digest,
        progress_receipt_digest=progress.receipt_digest,
        version_transition_receipt_digest=(
            None if version is None else version.receipt_digest
        ),
        read_currentness_witness_digest=(
            None if currentness is None else currentness.witness_digest
        ),
        disposition=tree,
        source_binding_changed=g4.source_binding_changed,
        bounded_g3_recompute_attempt_admitted=False,
    )
    receipt.validate_claim_ceiling()
    return receipt


def prove_finite_recompute_lattice() -> Mapping[str, int]:
    """Exhaust the 90 valid structural control combinations."""
    counts: dict[str, int] = {}
    states = 0
    for requires_recompute in (False, True):
        source_modes = (False,) if not requires_recompute else (False, True)
        for source_changed in source_modes:
            for progress_disposition in PROGRESS_DISPOSITIONS:
                for version_present in (False, True):
                    for read_state in READ_STATES:
                        frozen = "source::17"
                        current = "source::18" if source_changed else frozen
                        changed_axes: tuple[str, ...] = ()
                        g4_disposition = G4_STRUCTURAL_MATCH
                        if requires_recompute:
                            g4_disposition = G4_HOLD_RECOMPUTE
                            changed_axes = (
                                ("source_binding_generation",)
                                if source_changed
                                else ("runtime_generation",)
                            )
                        g4 = G4RevalidationProjection(
                            receipt_digest="a" * 64,
                            disposition=g4_disposition,
                            changed_axes=changed_axes,
                            frozen_source_binding_generation=frozen,
                            current_source_binding_generation=current,
                        )
                        progress = RetrievalProgressProjection(
                            receipt_digest="b" * 64,
                            disposition=progress_disposition,
                            retrieval_fingerprint_digest="c" * 64,
                            provider_state_generation="provider::17",
                            evidence_digest="d" * 64,
                        )
                        version = None
                        if version_present:
                            version = VersionTransitionProjection(
                                receipt_digest="e" * 64,
                                predecessor_source_binding_generation=(
                                    frozen if source_changed else "surplus::old"
                                ),
                                successor_source_binding_generation=(
                                    current if source_changed else "surplus::new"
                                ),
                                explicit_successor_edge=True,
                                future_read_currentness_required=True,
                            )
                        currentness = SourceReadCurrentnessProjection(
                            witness_digest="f" * 64,
                            source_binding_generation=current,
                            owner_generation="reader::17",
                            state=read_state,
                        )
                        tree = disposition_tree(
                            g4=g4,
                            progress=progress,
                            version=version,
                            currentness=currentness,
                        )
                        table = disposition_table(
                            g4=g4,
                            progress=progress,
                            version=version,
                            currentness=currentness,
                        )
                        if tree != table:
                            raise AssertionError("G5_FINITE_LATTICE_CLASSIFIER_MISMATCH")
                        receipt = assess_g3_recompute_admission(
                            g4=g4,
                            progress=progress,
                            version=version,
                            currentness=currentness,
                        )
                        if receipt.disposition != tree:
                            raise AssertionError("G5_FINITE_LATTICE_RECEIPT_MISMATCH")
                        if receipt.bounded_g3_recompute_attempt_admitted:
                            raise AssertionError("G5_V2_FINITE_LATTICE_CANNOT_ADMIT_RECOMPUTE")
                        counts[tree] = counts.get(tree, 0) + 1
                        states += 1
    return {"states": states, **dict(sorted(counts.items()))}
