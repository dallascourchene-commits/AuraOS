from __future__ import annotations

"""Non-minting Gate-10 reviewer admission kernel for K27 Memory City.

This module verifies mechanical admission evidence only. It does not
authenticate a reviewer identity, mint Gate 10, merge, deploy, or confer
truth/currentness/effect authority.

Keeper:
    ReviewerGreen != Gate10Authority
    SameLineageReview != IndependentReview
    Gate10Admission => all 13 hard axes pass
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping, Sequence
import json
import re

SCHEMA = "AURA-K27-GATE10-REVIEWER-ADMISSION-v1"
TERMINAL_CLASS = "ARENA_TERMINAL"
EXPECTED_ROUNDS = 750
CONCURRENT_ATTEMPTS_PER_ROUND = 5
EXPECTED_RECORDS = 1115
EXPECTED_PAYLOADS = 69

REGISTRY_SHA256 = "246dbded0a33eaede035b829bfcae9f8ee50d769f5c28f1a955a16073131d86f"
SEMANTIC_REGISTRY_ROOT = "7e0095415ffb6450aeb39f1faba782f27a1fb628e481fe7d1975aa5a649cf1c1"
PROVENANCE_ARCHIVE_SHA256 = "042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319"
PROVENANCE_MANIFEST_SHA256 = "1c8c69ab9d3c8ed9a7badff9fb22da187cbc22c73019210b4dc2194690e1588b"
SCENE_SOURCE_SHA256 = "b2cb2a2c1ebe65848d61da4db6225dbce2c686357bb427e1584468c44787a5a7"

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("ascii")).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and _GIT_SHA.fullmatch(value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


class Decision(str, Enum):
    READY_FOR_GATE10_DIFFERENT_J_DISPOSITION = "READY_FOR_GATE10_DIFFERENT_J_DISPOSITION"
    HOLD = "HOLD"


@dataclass(frozen=True)
class AdmissionReceipt:
    schema: str
    decision: Decision
    reasons: tuple[str, ...]
    axes: Mapping[str, bool]
    reviewed_head_sha: str | None
    reviewer_lineage_root: str | None
    evidence_root: str | None
    receipt_root: str
    authority_minted: bool = False
    gate10: bool = False
    canonical_promotion: bool = False
    merge_authority: bool = False
    effect_authority: bool = False


def replay_trace_root(trace: Sequence[Mapping[str, Any]]) -> str:
    return digest(list(trace))


def evidence_root(evidence: Mapping[str, Any]) -> str:
    return digest(evidence)


def terminal_receipt_root(terminal: Mapping[str, Any]) -> str:
    payload = {k: terminal[k] for k in terminal if k != "receipt_root"}
    return digest(payload)


def _trace_exact(trace: Any, replay: Mapping[str, Any]) -> bool:
    if not isinstance(trace, list) or len(trace) != EXPECTED_ROUNDS:
        return False
    if replay.get("campaign_root") != replay_trace_root(trace):
        return False
    for index, row in enumerate(trace):
        if not isinstance(row, Mapping):
            return False
        if row.get("round") != index:
            return False
        if row.get("concurrent_attempts") != CONCURRENT_ATTEMPTS_PER_ROUND:
            return False
        if row.get("winner_count") != 1:
            return False
        if row.get("store_root_conflict_holds") != CONCURRENT_ATTEMPTS_PER_ROUND - 1:
            return False
        if row.get("stale_dependency_probe") != "HOLD_STALE_DEPENDENCY":
            return False
        if row.get("aba_violations") != 0:
            return False
        if row.get("false_accepts") != 0 or row.get("false_holds") != 0:
            return False
        if not _is_sha256(row.get("post_repair_state_root")):
            return False
    return True


def evaluate_gate10_reviewer_admission(*, owner_lineage_root: str, current_head_sha: str,
                                       terminal: Mapping[str, Any], evidence: Mapping[str, Any]) -> AdmissionReceipt:
    """Fail-closed, noncompensatory Gate-10 reviewer admission.

    Passing means only that the supplied evidence is structurally ready for a
    genuinely independent authority process to evaluate. It is not Gate 10.
    """
    reasons: list[str] = []
    replay = evidence.get("replay") if isinstance(evidence, Mapping) else None
    registry = evidence.get("registry") if isinstance(evidence, Mapping) else None
    provenance = evidence.get("provenance") if isinstance(evidence, Mapping) else None
    invalidation = evidence.get("invalidation") if isinstance(evidence, Mapping) else None
    authority = evidence.get("authority") if isinstance(evidence, Mapping) else None
    reviewer_identity = evidence.get("reviewer_identity") if isinstance(evidence, Mapping) else None

    terminal_head = terminal.get("reviewed_head_sha") if isinstance(terminal, Mapping) else None
    terminal_evidence_root = terminal.get("evidence_root") if isinstance(terminal, Mapping) else None
    terminal_lineage = terminal.get("lineage_root") if isinstance(terminal, Mapping) else None

    axes: dict[str, bool] = {}

    axes["01_exact_current_head"] = _is_git_sha(current_head_sha) and terminal_head == current_head_sha
    if not axes["01_exact_current_head"]:
        reasons.append("HOLD_REVIEW_HEAD_NOT_EXACT_CURRENT_HEAD")

    axes["02_terminal_class"] = terminal.get("terminal_class") == TERMINAL_CLASS
    if not axes["02_terminal_class"]:
        reasons.append("HOLD_NOT_ARENA_TERMINAL")

    # This kernel does not authenticate reviewer identity. It only consumes an
    # exact upstream projection whose authority status says that authentication
    # occurred elsewhere. Different strings are never accepted as Different-J.
    axes["03_reviewer_identity_authenticated_projection"] = (
        all(_nonempty(terminal.get(key)) for key in ("terminal_id", "actor_id", "lineage_root", "derivation_root"))
        and isinstance(reviewer_identity, Mapping)
        and reviewer_identity.get("authority_status") == "EXTERNALLY_AUTHENTICATED"
        and _nonempty(reviewer_identity.get("generation"))
        and _is_sha256(reviewer_identity.get("attestation_root"))
        and reviewer_identity.get("actor_id") == terminal.get("actor_id")
        and reviewer_identity.get("lineage_root") == terminal_lineage
    )
    if not axes["03_reviewer_identity_authenticated_projection"]:
        reasons.append("HOLD_REVIEWER_IDENTITY_NOT_EXTERNALLY_AUTHENTICATED_AND_BOUND")

    axes["04_different_j"] = (
        axes["03_reviewer_identity_authenticated_projection"]
        and _nonempty(owner_lineage_root)
        and _nonempty(terminal_lineage)
        and owner_lineage_root != terminal_lineage
    )
    if not axes["04_different_j"]:
        reasons.append("HOLD_SAME_OR_UNAUTHENTICATED_LINEAGE_REVIEW")

    axes["05_terminal_receipt_root"] = _is_sha256(terminal.get("receipt_root")) and terminal.get("receipt_root") == terminal_receipt_root(terminal)
    if not axes["05_terminal_receipt_root"]:
        reasons.append("HOLD_TERMINAL_RECEIPT_ROOT_MISMATCH")

    axes["06_complete_evidence_root"] = _is_sha256(terminal_evidence_root) and terminal_evidence_root == evidence_root(evidence)
    if not axes["06_complete_evidence_root"]:
        reasons.append("HOLD_EVIDENCE_ROOT_MISMATCH")

    axes["07_replay_complete"] = (
        isinstance(replay, Mapping)
        and replay.get("campaign_complete") is True
        and replay.get("completed_rounds") == EXPECTED_ROUNDS
        and replay.get("round_failures") == 0
        and replay.get("concurrent_attempts") == EXPECTED_ROUNDS * CONCURRENT_ATTEMPTS_PER_ROUND
        and replay.get("stale_dependency_probes") == EXPECTED_ROUNDS
        and replay.get("aba_violations") == 0
        and replay.get("false_accepts") == 0
        and replay.get("false_holds") == 0
    )
    if not axes["07_replay_complete"]:
        reasons.append("HOLD_REPLAY_INCOMPLETE_OR_COUNTER_MISMATCH")

    axes["08_full_trace_recomputable"] = isinstance(replay, Mapping) and _trace_exact(replay.get("trace"), replay)
    if not axes["08_full_trace_recomputable"]:
        reasons.append("HOLD_REPLAY_TRACE_NOT_COMPLETE_RECOMPUTABLE")

    axes["09_registry_shape"] = (
        isinstance(registry, Mapping)
        and registry.get("dataSound") is True
        and registry.get("uniqueKeys") == EXPECTED_RECORDS
        and registry.get("ambiguousDigests") == 0
        and registry.get("registry_sha256") == REGISTRY_SHA256
        and registry.get("semantic_registry_root") == SEMANTIC_REGISTRY_ROOT
    )
    if not axes["09_registry_shape"]:
        reasons.append("HOLD_REGISTRY_SHAPE_OR_IDENTITY_MISMATCH")

    axes["10_provider_bytes"] = (
        isinstance(provenance, Mapping)
        and provenance.get("archive_sha256") == PROVENANCE_ARCHIVE_SHA256
        and provenance.get("manifest_sha256") == PROVENANCE_MANIFEST_SHA256
        and provenance.get("scene_source_sha256") == SCENE_SOURCE_SHA256
        and provenance.get("manifest_payloads_verified") == EXPECTED_PAYLOADS
        and provenance.get("provider_bytes_bound") is True
    )
    if not axes["10_provider_bytes"]:
        reasons.append("HOLD_PROVIDER_BYTES_NOT_EXACTLY_BOUND")

    axes["11_invalidation_bounded_deterministic"] = (
        isinstance(invalidation, Mapping)
        and invalidation.get("bounded") is True
        and invalidation.get("deterministic") is True
        and invalidation.get("ambiguous_edges") == 0
    )
    if not axes["11_invalidation_bounded_deterministic"]:
        reasons.append("HOLD_INVALIDATION_CONE_NOT_BOUNDED_DETERMINISTIC")

    axes["12_authority_decoupled_from_coordinate"] = (
        isinstance(authority, Mapping)
        and authority.get("k27_coordinate_authority") is False
        and authority.get("truth_authority") is False
        and authority.get("currentness_authority") is False
    )
    if not axes["12_authority_decoupled_from_coordinate"]:
        reasons.append("HOLD_COORDINATE_AUTHORITY_NOT_DECOUPLED")

    axes["13_nonpromoting_reviewer_claim"] = (
        isinstance(authority, Mapping)
        and authority.get("authority_minted") is False
        and authority.get("gate10") is False
        and authority.get("canonical_promotion") is False
        and authority.get("merge_authority") is False
        and authority.get("effect_authority") is False
    )
    if not axes["13_nonpromoting_reviewer_claim"]:
        reasons.append("HOLD_REVIEWER_PREMATURE_AUTHORITY_CLAIM")

    decision = Decision.READY_FOR_GATE10_DIFFERENT_J_DISPOSITION if all(axes.values()) else Decision.HOLD
    unsigned = {
        "schema": SCHEMA,
        "decision": decision.value,
        "reasons": sorted(set(reasons)),
        "axes": axes,
        "reviewed_head_sha": terminal_head,
        "reviewer_lineage_root": terminal_lineage,
        "evidence_root": terminal_evidence_root,
        "authority_minted": False,
        "gate10": False,
        "canonical_promotion": False,
        "merge_authority": False,
        "effect_authority": False,
    }
    return AdmissionReceipt(
        schema=SCHEMA,
        decision=decision,
        reasons=tuple(sorted(set(reasons))),
        axes=axes,
        reviewed_head_sha=terminal_head,
        reviewer_lineage_root=terminal_lineage,
        evidence_root=terminal_evidence_root,
        receipt_root=digest(unsigned),
    )


def build_terminal(*, terminal_id: str, actor_id: str, lineage_root: str, derivation_root: str,
                   reviewed_head_sha: str, evidence: Mapping[str, Any]) -> dict[str, Any]:
    terminal = {
        "terminal_class": TERMINAL_CLASS,
        "terminal_id": terminal_id,
        "actor_id": actor_id,
        "lineage_root": lineage_root,
        "derivation_root": derivation_root,
        "reviewed_head_sha": reviewed_head_sha,
        "evidence_root": evidence_root(evidence),
    }
    terminal["receipt_root"] = terminal_receipt_root(terminal)
    return terminal
