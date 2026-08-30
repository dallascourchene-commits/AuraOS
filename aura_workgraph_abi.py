"""Clock-stable compatibility and fencing helpers for staged Aura WorkGraph candidates.

This module is intentionally authority-neutral. It does not select, claim, wake,
execute, or persist work. It only derives stable compatibility identities and
monotonic fencing tokens that host adapters can bind to an atomic state write.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
from typing import Any, Mapping

ABI_SCHEMA = "AuraWorkGraphABIV1"
FENCE_SCHEMA = "AuraWorkGraphClaimFenceV1"
SUPPORTED_PROJECTION_SCHEMAS = frozenset(
    {"WorkGraphProjectionV1", "AuraArenaWorkGraphProjectionV1"}
)
_VOLATILE_KEYS = frozenset(
    {
        "generated_at_ms",
        "now_ms",
        "observed_at_ms",
        "generated_at",
    }
)


class WorkGraphABIError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_plain(v) for v in value), key=_canonical_text)
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int)):
        return value.value
    if isinstance(value, float) and not math.isfinite(value):
        raise WorkGraphABIError("NONFINITE_NUMBER")
    return value


def _canonical_text(value: Any) -> str:
    return json.dumps(
        _plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(domain: str, value: Any) -> str:
    payload = domain.encode("utf-8") + b"\0" + _canonical_text(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _projection_dict(projection: Any) -> dict[str, Any]:
    if isinstance(projection, Mapping):
        out = _plain(projection)
    elif hasattr(projection, "to_dict") and callable(projection.to_dict):
        out = _plain(projection.to_dict())
    else:
        raise WorkGraphABIError("PROJECTION_NOT_MAPPABLE")
    if not isinstance(out, dict):
        raise WorkGraphABIError("PROJECTION_NOT_OBJECT")
    schema = str(out.get("schema") or "")
    if schema not in SUPPORTED_PROJECTION_SCHEMAS:
        raise WorkGraphABIError("PROJECTION_SCHEMA_UNSUPPORTED")
    return out


def _strip_volatile(value: Any) -> Any:
    value = _plain(value)
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in sorted(value.items())
            if key not in _VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def stable_projection_revision(projection: Any) -> str:
    """Return a logical revision that ignores observation-clock-only fields.

    Lease timestamps remain included because changing a lease is a state mutation;
    only observation/generation clocks are removed.
    """
    value = _strip_volatile(_projection_dict(projection))
    value.pop("graph_digest", None)
    return _digest("AURA_WORKGRAPH_LOGICAL_REVISION_V1", value)


def _first(mapping: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return default


def _normalize_cell_from_315(row: Mapping[str, Any]) -> dict[str, Any]:
    work = row.get("work") if isinstance(row.get("work"), Mapping) else row
    lease = _first(row, "active_lease", default=None)
    if lease is None and isinstance(work, Mapping):
        lease = work.get("claim_lease")
    return {
        "work_id": str(_first(work, "work_id", "cell_id", default="")),
        "effective_state": str(
            _first(row, "effective_state", default=_first(work, "state", default=""))
        ),
        "dependencies": sorted(
            str(v) for v in (_first(work, "dependencies", default=[]) or [])
        ),
        "required_capabilities": sorted(
            str(v) for v in (_first(work, "required_capabilities", default=[]) or [])
        ),
        "effect_class": str(
            _first(work, "required_effect_ceiling", "effect_class", default="D0")
        ),
        "execution_state": str(_first(work, "execution_state", default="UNKNOWN")),
        "lease": _strip_volatile(lease) if lease else None,
    }


def _normalize_cell_from_313(row: Mapping[str, Any]) -> dict[str, Any]:
    claims = row.get("active_claims") or []
    lease = None
    if claims:
        claim = sorted(
            (_plain(v) for v in claims), key=lambda v: str(v.get("claim_id", ""))
        )[0]
        lease = {
            "lease_id": claim.get("claim_id"),
            "worker_id": claim.get("worker_id"),
            "basis_revision": claim.get("basis_graph_digest"),
            "currentness_basis": claim.get("currentness_ref"),
            "fence_epoch": claim.get("generation"),
        }
    return {
        "work_id": str(_first(row, "cell_id", "work_id", default="")),
        "effective_state": str(_first(row, "effective_state", "state", default="")),
        "dependencies": sorted(str(v) for v in (row.get("dependencies") or [])),
        "required_capabilities": sorted(
            str(v) for v in (row.get("required_capabilities") or [])
        ),
        "effect_class": str(
            _first(row, "effect_class", "required_effect_ceiling", default="D0")
        ),
        "execution_state": str(row.get("execution_state") or "UNKNOWN"),
        "lease": lease,
    }


def common_abi_view(projection: Any) -> dict[str, Any]:
    """Project either staged WorkGraph schema into a minimal comparison ABI.

    This is a compatibility view, not an ownership/supersession decision.
    """
    value = _projection_dict(projection)
    schema = value["schema"]
    if schema == "WorkGraphProjectionV1":
        rows = value.get("work_items") or value.get("work") or []
        cells = [_normalize_cell_from_315(row) for row in rows]
        currentness = _first(
            value, "canonical_orientation_revision", "currentness_ref", default=""
        )
        board_revision = value.get("board_revision") or ""
    else:
        rows = value.get("cells") or []
        cells = [_normalize_cell_from_313(row) for row in rows]
        currentness = value.get("currentness_ref") or ""
        board_revision = value.get("board_revision") or ""
    cells = sorted(cells, key=lambda row: row["work_id"])
    return {
        "schema": ABI_SCHEMA,
        "source_projection_schema": schema,
        "project_id": str(value.get("project_id") or ""),
        "currentness_ref": str(currentness),
        "board_ref": str(value.get("board_ref") or ""),
        "board_revision": str(board_revision),
        "cells": cells,
        "coordination_only": True,
        "execution_proven": False,
    }


def common_abi_revision(projection: Any) -> str:
    view = common_abi_view(projection)
    view = dict(view)
    view.pop("source_projection_schema", None)
    return _digest("AURA_WORKGRAPH_COMMON_ABI_V1", view)


@dataclass(frozen=True)
class ClaimFence:
    project_id: str
    work_id: str
    worker_id: str
    basis_revision: str
    fence_epoch: int
    schema: str = FENCE_SCHEMA

    def __post_init__(self) -> None:
        for field in ("project_id", "work_id", "worker_id", "basis_revision"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise WorkGraphABIError(f"{field.upper()}_REQUIRED")
        if (
            not isinstance(self.fence_epoch, int)
            or isinstance(self.fence_epoch, bool)
            or self.fence_epoch < 1
        ):
            raise WorkGraphABIError("FENCE_EPOCH_INVALID")
        if self.schema != FENCE_SCHEMA:
            raise WorkGraphABIError("FENCE_SCHEMA_INVALID")

    @property
    def token(self) -> str:
        return _digest("AURA_WORKGRAPH_CLAIM_FENCE_V1", asdict(self))


def next_claim_fence(
    *,
    project_id: str,
    work_id: str,
    worker_id: str,
    basis_revision: str,
    previous: ClaimFence | None = None,
) -> ClaimFence:
    if previous is not None:
        if previous.project_id != project_id or previous.work_id != work_id:
            raise WorkGraphABIError("FENCE_LINEAGE_MISMATCH")
        epoch = previous.fence_epoch + 1
    else:
        epoch = 1
    return ClaimFence(project_id, work_id, worker_id, basis_revision, epoch)


def validate_claim_fence(
    candidate: ClaimFence, *, minimum_epoch: int, basis_revision: str
) -> None:
    if (
        not isinstance(minimum_epoch, int)
        or isinstance(minimum_epoch, bool)
        or minimum_epoch < 0
    ):
        raise WorkGraphABIError("MINIMUM_FENCE_INVALID")
    if candidate.basis_revision != basis_revision:
        raise WorkGraphABIError("FENCE_STALE_BASIS")
    if candidate.fence_epoch <= minimum_epoch:
        raise WorkGraphABIError("FENCE_STALE_OWNER")


def compatibility_report(left: Any, right: Any) -> dict[str, Any]:
    lview = common_abi_view(left)
    rview = common_abi_view(right)
    l_ids = {row["work_id"] for row in lview["cells"]}
    r_ids = {row["work_id"] for row in rview["cells"]}
    return {
        "schema": "AuraWorkGraphCompatibilityReportV1",
        "left_schema": lview["source_projection_schema"],
        "right_schema": rview["source_projection_schema"],
        "same_project": lview["project_id"] == rview["project_id"],
        "same_currentness": lview["currentness_ref"] == rview["currentness_ref"],
        "shared_work_ids": sorted(l_ids & r_ids),
        "left_only_work_ids": sorted(l_ids - r_ids),
        "right_only_work_ids": sorted(r_ids - l_ids),
        "semantic_revision_equal": common_abi_revision(left)
        == common_abi_revision(right),
        "ownership_decision": "UNRESOLVED",
        "promotion_allowed": False,
    }
