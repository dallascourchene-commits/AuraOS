from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import FrozenSet, Tuple


def canonical(v):
    if isinstance(v, Enum):
        return v.value
    if hasattr(v, "__dataclass_fields__"):
        return canonical(asdict(v))
    if isinstance(v, dict):
        return {str(k): canonical(v[k]) for k in sorted(v)}
    if isinstance(v, (list, tuple)):
        return [canonical(x) for x in v]
    if isinstance(v, (set, frozenset)):
        return sorted(canonical(x) for x in v)
    if v is None or isinstance(v, (bool, int, str)):
        return v
    raise TypeError(type(v).__name__)


def digest(v) -> str:
    return sha256(json.dumps(canonical(v), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("TIMESTAMP_REQUIRED")
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError("TIMESTAMP_INVALID") from e
    if dt.tzinfo is None:
        raise ValueError("TIMESTAMP_MUST_BE_OFFSET_AWARE")
    return dt.astimezone(timezone.utc)


class SuccessionDisposition(str, Enum):
    FOREIGN_PARENT_PAIR_ACCEPTED = "FOREIGN_PARENT_PAIR_ACCEPTED"
    SAME_LINEAGE_PAIR_HOLD = "SAME_LINEAGE_PAIR_HOLD"
    FOREIGN_ANCESTRY_ONLY_HOLD = "FOREIGN_ANCESTRY_ONLY_HOLD"
    CONSEQUENCE_DUPLICATE_HOLD = "CONSEQUENCE_DUPLICATE_HOLD"
    PARENT_IDENTITY_UNRESOLVED_HOLD = "PARENT_IDENTITY_UNRESOLVED_HOLD"
    PRE_CUT_PARENT_HOLD = "PRE_CUT_PARENT_HOLD"
    NOT_FOREIGN_TO_CURRENT_HOLD = "NOT_FOREIGN_TO_CURRENT_HOLD"
    TERMINAL_RECEIPT_MISMATCH_HOLD = "TERMINAL_RECEIPT_MISMATCH_HOLD"
    NONSEMANTIC_TERMINAL_HOLD = "NONSEMANTIC_TERMINAL_HOLD"
    AUTHORITY_WIDENING_HOLD = "AUTHORITY_WIDENING_HOLD"
    PARENT_COUNT_HOLD = "PARENT_COUNT_HOLD"


@dataclass(frozen=True)
class TerminalParentReceipt:
    terminal_id: str
    actor_id: str
    actor_lineage_id: str
    consequence_root: str
    terminal_created_at: str
    semantic_terminal: bool
    actor_identity_admitted: bool
    ancestry_roots: FrozenSet[str] = frozenset()
    effect_authority: bool = False
    gate10: bool = False
    receipt_root: str = ""

    def payload(self) -> dict:
        return {
            "terminal_id": self.terminal_id,
            "actor_id": self.actor_id,
            "actor_lineage_id": self.actor_lineage_id,
            "consequence_root": self.consequence_root,
            "terminal_created_at": self.terminal_created_at,
            "semantic_terminal": self.semantic_terminal,
            "actor_identity_admitted": self.actor_identity_admitted,
            "ancestry_roots": sorted(self.ancestry_roots),
            "effect_authority": self.effect_authority,
            "gate10": self.gate10,
        }

    def computed_root(self) -> str:
        return digest(self.payload())

    def validate_shape(self) -> None:
        if not all((self.terminal_id, self.actor_id, self.actor_lineage_id, self.consequence_root, self.terminal_created_at)):
            raise ValueError("TERMINAL_IDENTITY_REQUIRED")
        if type(self.semantic_terminal) is not bool or type(self.actor_identity_admitted) is not bool:
            raise ValueError("TERMINAL_ADMISSION_BOOL_REQUIRED")
        if type(self.effect_authority) is not bool or type(self.gate10) is not bool:
            raise ValueError("AUTHORITY_BOOL_REQUIRED")
        parse_time(self.terminal_created_at)
        if not self.receipt_root or len(self.receipt_root) != 64 or any(c not in "0123456789abcdef" for c in self.receipt_root):
            raise ValueError("TERMINAL_RECEIPT_ROOT_INVALID")

    @classmethod
    def seal(cls, **kwargs) -> "TerminalParentReceipt":
        temp = cls(receipt_root="", **kwargs)
        return cls(**kwargs, receipt_root=temp.computed_root())


@dataclass(frozen=True)
class SuccessionAdmissionRequest:
    current_actor_lineage_id: str
    cut_time: str
    parents: Tuple[TerminalParentReceipt, ...]
    require_foreign: bool = True
    effect_authority_requested: bool = False

    def validate(self) -> None:
        if not self.current_actor_lineage_id:
            raise ValueError("CURRENT_ACTOR_LINEAGE_REQUIRED")
        if type(self.require_foreign) is not bool or type(self.effect_authority_requested) is not bool:
            raise ValueError("REQUEST_BOOL_REQUIRED")
        parse_time(self.cut_time)


@dataclass(frozen=True)
class SuccessionAdmissionReceipt:
    disposition: SuccessionDisposition
    reasons: Tuple[str, ...]
    parent_terminal_ids: Tuple[str, ...]
    parent_lineages: Tuple[str, ...]
    parent_consequences: Tuple[str, ...]
    cut_time: str
    current_actor_lineage_id: str
    objective_seed: str | None
    effect_authority: bool = False
    gate10: bool = False

    @property
    def receipt_digest(self) -> str:
        return digest(asdict(self))


class SuccessionParentAdmissionKernel:
    """D0 gate for immediate post-cut parent credit. Never grants effects or truth authority."""

    def assess(self, req: SuccessionAdmissionRequest) -> SuccessionAdmissionReceipt:
        req.validate()
        parents = tuple(req.parents)
        reasons: list[str] = []

        if req.effect_authority_requested:
            return self._receipt(req, SuccessionDisposition.AUTHORITY_WIDENING_HOLD,
                                 ("D0 succession admission cannot request effect authority",), None)
        if len(parents) != 2:
            return self._receipt(req, SuccessionDisposition.PARENT_COUNT_HOLD,
                                 (f"exactly_two_parents_required:{len(parents)}",), None)

        cut = parse_time(req.cut_time)
        for p in parents:
            try:
                p.validate_shape()
            except ValueError as e:
                reasons.append(f"{p.terminal_id or '<unbound>'}:{e}")
                continue
            if p.effect_authority or p.gate10:
                reasons.append(f"{p.terminal_id}:authority_widening")
            if p.receipt_root != p.computed_root():
                reasons.append(f"{p.terminal_id}:receipt_root_mismatch")
            if not p.semantic_terminal:
                reasons.append(f"{p.terminal_id}:not_semantic_terminal")
            if not p.actor_identity_admitted:
                # Foreign ancestry cannot compensate for unresolved immediate actor identity.
                reasons.append(f"{p.terminal_id}:immediate_actor_identity_unadmitted")
            if parse_time(p.terminal_created_at) <= cut:
                reasons.append(f"{p.terminal_id}:not_post_cut")

        if reasons:
            if any("authority_widening" in r for r in reasons):
                disp = SuccessionDisposition.AUTHORITY_WIDENING_HOLD
            elif any("receipt_root_mismatch" in r for r in reasons):
                disp = SuccessionDisposition.TERMINAL_RECEIPT_MISMATCH_HOLD
            elif any("not_semantic_terminal" in r for r in reasons):
                disp = SuccessionDisposition.NONSEMANTIC_TERMINAL_HOLD
            elif any("not_post_cut" in r for r in reasons):
                disp = SuccessionDisposition.PRE_CUT_PARENT_HOLD
            elif any("immediate_actor_identity_unadmitted" in r for r in reasons):
                if any(p.ancestry_roots for p in parents):
                    disp = SuccessionDisposition.FOREIGN_ANCESTRY_ONLY_HOLD
                else:
                    disp = SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
            else:
                disp = SuccessionDisposition.PARENT_IDENTITY_UNRESOLVED_HOLD
            return self._receipt(req, disp, tuple(sorted(reasons)), None)

        a, b = parents
        if a.actor_lineage_id == b.actor_lineage_id:
            return self._receipt(req, SuccessionDisposition.SAME_LINEAGE_PAIR_HOLD,
                                 ("immediate_parent_lineages_must_be_distinct",), None)
        if req.require_foreign and (a.actor_lineage_id == req.current_actor_lineage_id or b.actor_lineage_id == req.current_actor_lineage_id):
            return self._receipt(req, SuccessionDisposition.NOT_FOREIGN_TO_CURRENT_HOLD,
                                 ("each_immediate_parent_must_be_foreign_to_current_actor_lineage",), None)
        if a.consequence_root == b.consequence_root:
            return self._receipt(req, SuccessionDisposition.CONSEQUENCE_DUPLICATE_HOLD,
                                 ("parent_consequence_roots_must_be_distinct",), None)

        seed = digest((a.receipt_root, b.receipt_root, req.cut_time, req.current_actor_lineage_id,
                       "NEXT_MINIMUM_CONSEQUENCE_CONE"))
        return self._receipt(req, SuccessionDisposition.FOREIGN_PARENT_PAIR_ACCEPTED, (), seed)

    @staticmethod
    def _receipt(req, disposition, reasons, seed):
        ps = tuple(req.parents)
        return SuccessionAdmissionReceipt(
            disposition=disposition,
            reasons=tuple(reasons),
            parent_terminal_ids=tuple(p.terminal_id for p in ps),
            parent_lineages=tuple(p.actor_lineage_id for p in ps),
            parent_consequences=tuple(p.consequence_root for p in ps),
            cut_time=req.cut_time,
            current_actor_lineage_id=req.current_actor_lineage_id,
            objective_seed=seed,
        )
