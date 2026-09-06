from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Sequence

from successor_admission_gate import (
    ARENA_TERMINAL,
    D0,
    AdmissionContext,
    Disposition,
    GateResult,
    ParentArtifact,
    consequence_root,
    evaluate_successor_pair,
    normalized_parent,
    sha256_obj,
)


class SuccessionDisposition(str, Enum):
    FOREIGN_PARENT_PAIR_ACCEPTED = "FOREIGN_PARENT_PAIR_ACCEPTED"
    EXACTLY_TWO_PARENTS_HOLD = "EXACTLY_TWO_PARENTS_HOLD"
    SAME_LINEAGE_PAIR_HOLD = "SAME_LINEAGE_PAIR_HOLD"
    FOREIGN_ANCESTRY_ONLY_HOLD = "FOREIGN_ANCESTRY_ONLY_HOLD"
    CONSEQUENCE_DUPLICATE_HOLD = "CONSEQUENCE_DUPLICATE_HOLD"
    PARENT_IDENTITY_UNRESOLVED_HOLD = "PARENT_IDENTITY_UNRESOLVED_HOLD"
    TERMINAL_RECEIPT_INTEGRITY_HOLD = "TERMINAL_RECEIPT_INTEGRITY_HOLD"
    TEMPORAL_CURRENTNESS_HOLD = "TEMPORAL_CURRENTNESS_HOLD"
    TERMINAL_CLASS_HOLD = "TERMINAL_CLASS_HOLD"
    PROJECTION_HOLD = "PROJECTION_HOLD"
    AUTHORITY_HOLD = "AUTHORITY_HOLD"
    OTHER_ANCESTRY_HOLD = "OTHER_ANCESTRY_HOLD"


@dataclass(frozen=True)
class ImmediateTerminalReceipt:
    """Source-bound identity of the *immediate* semantic terminal.

    ancestry_actor_ids are provenance only. They can never substitute for actor_id.
    The receipt root binds all fields so a caller cannot swap immediate identity while
    reusing the same terminal receipt root.
    """

    receipt_id: str
    artifact_id: str
    actor_id: str
    lineage_root: str
    created_at: str
    artifact_class: str
    semantic_terminal: bool
    projection_of: Optional[str]
    consequence_root: str
    derivation_root: str
    source_owner_ref: str
    source_revision_root: str
    ancestry_actor_ids: tuple[str, ...] = ()
    authority_ceiling: str = D0

    @property
    def receipt_root(self) -> str:
        return sha256_obj({"schema": "AURA-IMMEDIATE-TERMINAL-RECEIPT-v1", **asdict(self)})


@dataclass(frozen=True)
class ParentEvidence:
    parent: ParentArtifact
    immediate_receipt: Optional[ImmediateTerminalReceipt]


@dataclass(frozen=True)
class ParentAdmissionResult:
    disposition: SuccessionDisposition
    reasons: tuple[str, ...]
    pair_root: str
    k27_coordinate: tuple[int, int, int]
    legacy_gate_disposition: str
    authority_ceiling: str = D0


def _nonempty(value: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _hex64(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _receipt_reasons(evidence: ParentEvidence, idx: int, ctx: AdmissionContext) -> list[str]:
    p = evidence.parent
    r = evidence.immediate_receipt
    pre = f"P{idx}_"
    if r is None:
        return [pre + "IMMEDIATE_TERMINAL_RECEIPT_REQUIRED"]

    reasons: list[str] = []
    if r.authority_ceiling != D0:
        reasons.append(pre + "RECEIPT_AUTHORITY_WIDENING")
    if not _nonempty(r.receipt_id) or not _nonempty(r.source_owner_ref) or not _hex64(r.source_revision_root):
        reasons.append(pre + "SOURCE_BOUND_IDENTITY_UNRESOLVED")
    if not _hex64(r.lineage_root) or not _hex64(r.consequence_root) or not _hex64(r.derivation_root):
        reasons.append(pre + "RECEIPT_ROOT_FIELD_INVALID")

    try:
        n = normalized_parent(p)
        expected_consequence = consequence_root(p)
    except (ValueError, TypeError):
        return reasons + [pre + "PARENT_NORMALIZATION_FAILED"]

    identity_pairs = (
        (n["artifact_id"], r.artifact_id, "ARTIFACT_ID"),
        (n["actor_id"], r.actor_id, "ACTOR_ID"),
        (n["lineage_root"], r.lineage_root, "LINEAGE_ROOT"),
        (p.created_at, r.created_at, "CREATED_AT"),
        (n["artifact_class"], r.artifact_class, "ARTIFACT_CLASS"),
        (bool(n["semantic_terminal"]), bool(r.semantic_terminal), "SEMANTIC_TERMINAL"),
        (n["projection_of"], r.projection_of, "PROJECTION_OF"),
        (expected_consequence, r.consequence_root, "CONSEQUENCE_ROOT"),
        (n["derivation_root"], r.derivation_root, "DERIVATION_ROOT"),
    )
    for left, right, label in identity_pairs:
        if left != right:
            reasons.append(pre + "IMMEDIATE_IDENTITY_MISMATCH_" + label)

    if n["receipt_root"] != r.receipt_root:
        reasons.append(pre + "TERMINAL_RECEIPT_ROOT_MISMATCH")

    # This is the core laundering detector: foreign ancestry is provenance only.
    ancestry = {a for a in r.ancestry_actor_ids if _nonempty(a)}
    if r.actor_id == ctx.current_actor_id and any(a != ctx.current_actor_id for a in ancestry):
        reasons.append(pre + "FOREIGN_ANCESTRY_ONLY")
    return reasons


def _select_disposition(reasons: Sequence[str], legacy: GateResult) -> SuccessionDisposition:
    rs = tuple(reasons)
    if not rs and legacy.disposition is Disposition.ELIGIBLE_TO_MINT_SUCCESSOR:
        return SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED
    if any("EXACTLY_TWO" in x for x in rs):
        return SuccessionDisposition.EXACTLY_TWO_PARENTS_HOLD
    if any("AUTHORITY_WIDENING" in x for x in rs):
        return SuccessionDisposition.AUTHORITY_HOLD
    if any("IMMEDIATE_TERMINAL_RECEIPT_REQUIRED" in x or "SOURCE_BOUND_IDENTITY_UNRESOLVED" in x or "PARENT_NORMALIZATION_FAILED" in x for x in rs):
        return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    if any("IMMEDIATE_IDENTITY_MISMATCH" in x for x in rs):
        return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    if any("TERMINAL_RECEIPT_ROOT_MISMATCH" in x or "RECEIPT_ROOT_FIELD_INVALID" in x for x in rs):
        return SuccessionDisposition.TERMINAL_RECEIPT_INTEGRITY_HOLD
    if any("FOREIGN_ANCESTRY_ONLY" in x for x in rs):
        return SuccessionDisposition.FOREIGN_ANCESTRY_ONLY_HOLD
    all_reasons = set(rs) | set(legacy.reasons)
    if "PARENT_CONSEQUENCES_NOT_DISTINCT" in all_reasons:
        return SuccessionDisposition.CONSEQUENCE_DUPLICATE_HOLD
    if any(x in all_reasons for x in ("PARENT_ACTORS_NOT_DISTINCT", "PARENT_LINEAGES_NOT_DISTINCT")) or any("NOT_FOREIGN_ACTOR" in x for x in all_reasons):
        return SuccessionDisposition.SAME_LINEAGE_PAIR_HOLD
    if any("NOT_POST_CUT" in x or "FUTURE_DATED" in x for x in all_reasons):
        return SuccessionDisposition.TEMPORAL_CURRENTNESS_HOLD
    if any("NOT_SEMANTIC_TERMINAL" in x for x in all_reasons):
        return SuccessionDisposition.TERMINAL_CLASS_HOLD
    if any("PROJECTION_ONLY" in x for x in all_reasons):
        return SuccessionDisposition.PROJECTION_HOLD
    return SuccessionDisposition.OTHER_ANCESTRY_HOLD


def admit_successor_pair(evidence: Sequence[ParentEvidence], ctx: AdmissionContext) -> ParentAdmissionResult:
    """R2: immediate-terminal receipt admission before legacy successor gating."""
    if len(evidence) != 2:
        material = {"schema": "AURA-SUCCESSOR-PARENT-ADMISSION-R2", "ctx": asdict(ctx), "parent_count": len(evidence)}
        root = sha256_obj(material)
        slot = int(root[:8], 16) % 27
        return ParentAdmissionResult(
            SuccessionDisposition.EXACTLY_TWO_PARENTS_HOLD,
            ("EXACTLY_TWO_IMMEDIATE_TERMINALS_REQUIRED",),
            root,
            (slot % 3, (slot // 3) % 3, (slot // 9) % 3),
            Disposition.HOLD.value,
        )

    parents = [e.parent for e in evidence]
    receipt_reasons: list[str] = []
    for idx, ev in enumerate(evidence, start=1):
        receipt_reasons.extend(_receipt_reasons(ev, idx, ctx))

    legacy = evaluate_successor_pair(parents, ctx)
    reasons = tuple(sorted(set(receipt_reasons) | set(legacy.reasons)))
    disposition = _select_disposition(reasons, legacy)
    material = {
        "schema": "AURA-SUCCESSOR-PARENT-ADMISSION-R2",
        "ctx": asdict(ctx),
        "parents": [normalized_parent(p) for p in parents],
        "terminal_receipts": [None if e.immediate_receipt is None else asdict(e.immediate_receipt) | {"receipt_root": e.immediate_receipt.receipt_root} for e in evidence],
        "legacy_gate_root": legacy.pair_root,
        "reasons": reasons,
        "disposition": disposition.value,
        "authority_ceiling": D0,
    }
    root = sha256_obj(material)
    slot = int(root[:8], 16) % 27
    return ParentAdmissionResult(disposition, reasons, root, (slot % 3, (slot // 3) % 3, (slot // 9) % 3), legacy.disposition.value)


def independent_r2_oracle(evidence: Sequence[ParentEvidence], ctx: AdmissionContext) -> SuccessionDisposition:
    """Independent restatement; does not call admit_successor_pair."""
    if len(evidence) != 2:
        return SuccessionDisposition.EXACTLY_TWO_PARENTS_HOLD
    parents = [e.parent for e in evidence]
    receipts = [e.immediate_receipt for e in evidence]
    if any(r is None for r in receipts):
        return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
    assert receipts[0] is not None and receipts[1] is not None
    for p, r in zip(parents, receipts):
        if r.authority_ceiling != D0:
            return SuccessionDisposition.AUTHORITY_HOLD
        if not _nonempty(r.source_owner_ref) or not _hex64(r.source_revision_root):
            return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
        try:
            n = normalized_parent(p)
            c = consequence_root(p)
        except (ValueError, TypeError):
            return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
        if (n["artifact_id"], n["actor_id"], n["lineage_root"], p.created_at, n["artifact_class"], bool(n["semantic_terminal"]), n["projection_of"], c, n["derivation_root"]) != (
            r.artifact_id, r.actor_id, r.lineage_root, r.created_at, r.artifact_class, bool(r.semantic_terminal), r.projection_of, r.consequence_root, r.derivation_root
        ):
            return SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
        if n["receipt_root"] != r.receipt_root:
            return SuccessionDisposition.TERMINAL_RECEIPT_INTEGRITY_HOLD
        if r.actor_id == ctx.current_actor_id and any(a != ctx.current_actor_id for a in r.ancestry_actor_ids):
            return SuccessionDisposition.FOREIGN_ANCESTRY_ONLY_HOLD

    legacy = evaluate_successor_pair(parents, ctx)
    if legacy.disposition is Disposition.ELIGIBLE_TO_MINT_SUCCESSOR:
        return SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED
    rs = set(legacy.reasons)
    if "PARENT_CONSEQUENCES_NOT_DISTINCT" in rs:
        return SuccessionDisposition.CONSEQUENCE_DUPLICATE_HOLD
    if "PARENT_ACTORS_NOT_DISTINCT" in rs or "PARENT_LINEAGES_NOT_DISTINCT" in rs or any("NOT_FOREIGN_ACTOR" in x for x in rs):
        return SuccessionDisposition.SAME_LINEAGE_PAIR_HOLD
    if any("NOT_POST_CUT" in x or "FUTURE_DATED" in x for x in rs):
        return SuccessionDisposition.TEMPORAL_CURRENTNESS_HOLD
    if any("NOT_SEMANTIC_TERMINAL" in x for x in rs):
        return SuccessionDisposition.TERMINAL_CLASS_HOLD
    if any("PROJECTION_ONLY" in x for x in rs):
        return SuccessionDisposition.PROJECTION_HOLD
    return SuccessionDisposition.OTHER_ANCESTRY_HOLD
