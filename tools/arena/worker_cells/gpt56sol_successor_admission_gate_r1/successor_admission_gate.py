from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Optional, Sequence

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ARENA_TERMINAL = "ARENA_TERMINAL"
D0 = "D0"


class Disposition(str, Enum):
    QUARANTINE = "QUARANTINE"
    HOLD = "HOLD"
    ELIGIBLE_TO_MINT_SUCCESSOR = "ELIGIBLE_TO_MINT_SUCCESSOR"


@dataclass(frozen=True)
class ParentArtifact:
    artifact_id: str
    actor_id: str
    lineage_root: str
    created_at: str
    artifact_class: str
    semantic_terminal: bool
    projection_of: Optional[str]
    consequence_axes: tuple[str, ...]
    consequence_action: str
    invariant_delta: str
    receipt_root: str
    derivation_root: str
    model_id: str = ""


@dataclass(frozen=True)
class AdmissionContext:
    current_actor_id: str
    predecessor_artifact_id: str
    predecessor_cut: str
    evaluated_at: str
    authority_ceiling: str = D0


@dataclass(frozen=True)
class GateResult:
    disposition: Disposition
    reasons: tuple[str, ...]
    pair_root: str
    k27_coordinate: tuple[int, int, int]
    authority_ceiling: str = D0


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be an ISO-8601 UTC string ending in Z")
    dt = datetime.fromisoformat(value[:-1] + "+00:00")
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _root(value: str, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValueError(f"{name} must be lowercase 64-hex")
    return value


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def consequence_root(parent: ParentArtifact) -> str:
    axes = tuple(sorted({_text(axis, "consequence_axis") for axis in parent.consequence_axes}))
    if not axes:
        raise ValueError("consequence_axes must be non-empty")
    return sha256_obj({
        "axes": axes,
        "action": _text(parent.consequence_action, "consequence_action"),
        "invariant_delta": _text(parent.invariant_delta, "invariant_delta"),
    })


def normalized_parent(parent: ParentArtifact) -> dict:
    return {
        "artifact_id": _text(parent.artifact_id, "artifact_id"),
        "actor_id": _text(parent.actor_id, "actor_id"),
        "lineage_root": _root(parent.lineage_root, "lineage_root"),
        "created_at": _parse_utc(parent.created_at).isoformat(),
        "artifact_class": _text(parent.artifact_class, "artifact_class"),
        "semantic_terminal": bool(parent.semantic_terminal),
        "projection_of": parent.projection_of,
        "consequence_root": consequence_root(parent),
        "receipt_root": _root(parent.receipt_root, "receipt_root"),
        "derivation_root": _root(parent.derivation_root, "derivation_root"),
        "model_id": parent.model_id,
    }


def _k27_from_digest(digest: str) -> tuple[int, int, int]:
    slot = int(digest[:8], 16) % 27
    return (slot % 3, (slot // 3) % 3, (slot // 9) % 3)


def evaluate_successor_pair(parents: Sequence[ParentArtifact], ctx: AdmissionContext) -> GateResult:
    """Fail closed on ancestry. K27 is locality only; it never repairs a failed gate."""
    reasons: list[str] = []
    if len(parents) != 2:
        material = {"ctx": ctx.__dict__, "parent_count": len(parents)}
        digest = sha256_obj(material)
        return GateResult(Disposition.HOLD, ("EXACTLY_TWO_PARENTS_REQUIRED",), digest, _k27_from_digest(digest))

    cut = _parse_utc(ctx.predecessor_cut)
    evaluated = _parse_utc(ctx.evaluated_at)
    if evaluated <= cut:
        raise ValueError("evaluated_at must be strictly after predecessor_cut")
    current_actor = _text(ctx.current_actor_id, "current_actor_id")
    _text(ctx.predecessor_artifact_id, "predecessor_artifact_id")

    norm = [normalized_parent(p) for p in parents]

    for idx, (raw, n) in enumerate(zip(parents, norm), start=1):
        created = _parse_utc(raw.created_at)
        if n["actor_id"] == current_actor:
            reasons.append(f"P{idx}_NOT_FOREIGN_ACTOR")
        if created <= cut:
            reasons.append(f"P{idx}_NOT_POST_CUT")
        if created > evaluated:
            reasons.append(f"P{idx}_FUTURE_DATED")
        if n["artifact_class"] != ARENA_TERMINAL or not n["semantic_terminal"]:
            reasons.append(f"P{idx}_NOT_SEMANTIC_TERMINAL")
        if n["projection_of"] is not None:
            reasons.append(f"P{idx}_PROJECTION_ONLY")

    if norm[0]["actor_id"] == norm[1]["actor_id"]:
        reasons.append("PARENT_ACTORS_NOT_DISTINCT")
    if norm[0]["lineage_root"] == norm[1]["lineage_root"]:
        reasons.append("PARENT_LINEAGES_NOT_DISTINCT")
    if norm[0]["consequence_root"] == norm[1]["consequence_root"]:
        reasons.append("PARENT_CONSEQUENCES_NOT_DISTINCT")
    if norm[0]["receipt_root"] == norm[1]["receipt_root"]:
        reasons.append("PARENT_RECEIPTS_NOT_DISTINCT")
    if norm[0]["derivation_root"] == norm[1]["derivation_root"]:
        reasons.append("PARENT_DERIVATIONS_NOT_DISTINCT")

    material = {
        "predecessor_artifact_id": ctx.predecessor_artifact_id,
        "predecessor_cut": cut.isoformat(),
        "evaluated_at": evaluated.isoformat(),
        "current_actor_id": current_actor,
        "authority_ceiling": D0,
        "parents": sorted(norm, key=lambda x: x["artifact_id"]),
        "reasons": sorted(set(reasons)),
    }
    digest = sha256_obj(material)
    disposition = Disposition.QUARANTINE if reasons else Disposition.ELIGIBLE_TO_MINT_SUCCESSOR
    return GateResult(disposition, tuple(sorted(set(reasons))), digest, _k27_from_digest(digest))


def independent_oracle(parents: Sequence[ParentArtifact], ctx: AdmissionContext) -> Disposition:
    """Independent restatement used by the campaign; intentionally does not call evaluate_successor_pair."""
    if len(parents) != 2:
        return Disposition.HOLD
    cut = _parse_utc(ctx.predecessor_cut)
    now = _parse_utc(ctx.evaluated_at)
    p0, p1 = parents
    try:
        normalized_parent(p0)
        normalized_parent(p1)
    except (ValueError, TypeError):
        return Disposition.QUARANTINE
    if any(_parse_utc(p.created_at) <= cut or _parse_utc(p.created_at) > now for p in parents):
        return Disposition.QUARANTINE
    if any(p.actor_id == ctx.current_actor_id for p in parents):
        return Disposition.QUARANTINE
    if p0.actor_id == p1.actor_id:
        return Disposition.QUARANTINE
    if p0.lineage_root == p1.lineage_root:
        return Disposition.QUARANTINE
    if any(p.artifact_class != ARENA_TERMINAL or not p.semantic_terminal or p.projection_of is not None for p in parents):
        return Disposition.QUARANTINE
    if consequence_root(p0) == consequence_root(p1):
        return Disposition.QUARANTINE
    if p0.receipt_root == p1.receipt_root or p0.derivation_root == p1.derivation_root:
        return Disposition.QUARANTINE
    return Disposition.ELIGIBLE_TO_MINT_SUCCESSOR


def omega8_classify(axes: Sequence[int]) -> Disposition:
    """Each axis: 0 invalid, 1 unresolved, 2 valid. Only the all-2 state is a keeper."""
    if len(axes) != 8 or any(v not in (0, 1, 2) for v in axes):
        raise ValueError("Omega8 requires eight ternary axes")
    if 0 in axes:
        return Disposition.QUARANTINE
    if 1 in axes:
        return Disposition.HOLD
    return Disposition.ELIGIBLE_TO_MINT_SUCCESSOR


def thirteen_d_collapse(hard8: Sequence[int], context5: Sequence[int]) -> Disposition:
    """Context cannot repair failed ancestry. The five context axes are non-authoritative."""
    if len(context5) != 5 or any(v not in (0, 1, 2) for v in context5):
        raise ValueError("13D tail requires five ternary context axes")
    return omega8_classify(hard8)
