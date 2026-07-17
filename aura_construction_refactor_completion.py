"""Machine-enforced completion audit for the SCO Construction E0-E14 refactor.

The audit checks canonical owners, Human Agent/Observatory wiring, documentation,
and authority boundaries. It distinguishes unfinished implementation from explicit
policy deferrals such as real connectors and physical-control authority.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from aura_construction_contracts import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY
from aura_event_contracts import stable_digest

CONSTRUCTION_REFACTOR_COMPLETION_VERSION = "AURA_SCO_CONSTRUCTION_REFACTOR_COMPLETION_V1"

_REQUIRED_SYMBOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "E0": {"aura_refactor_skeleton.py": ("RefactorSkeleton",)},
    "E1": {
        "aura_construction_refactor_plan.py": (
            "build_construction_capability_reuse_matrix",
        )
    },
    "E2": {"aura_refactor_skeleton.py": ("RefactorSkeletonStore",)},
    "E3": {
        "aura_construction_refactor_plan.py": (
            "compile_ready_nodes_to_action_capsules",
        )
    },
    "E4": {
        "aura_construction_contracts.py": (
            "ConstructionScope",
            "ConstructionClaim",
            "ConstructionEvidence",
            "ConstructionEvent",
        )
    },
    "E5": {
        "aura_construction_state.py": (
            "ConstructionProjectState",
            "replay_construction_events",
            "query_claim_readiness",
        )
    },
    "E6": {
        "aura_construction_authority.py": (
            "ConstructionReceiptBinding",
            "verify_construction_receipts",
        )
    },
    "E7": {
        "aura_construction_adapter.py": (
            "ConstructionAdvisoryLane",
            "evaluate_construction_candidates",
        )
    },
    "E8": {"aura_construction_adapter.py": ("ConstructionArenaAdapter",)},
    "E9": {
        "aura_construction_human_agent.py": (
            "ConstructionHumanAgentProfile",
            "ConstructionHumanAgentProfileService",
            "build_construction_human_agent_profile",
        )
    },
    "E10": {
        "aura_construction_learning.py": ("run_construction_phase3_learning",)
    },
    "E11": {
        "aura_construction_benchmark.py": ("run_construction_phase3_benchmark",)
    },
    "E12": {
        "aura_temporal_persistence.py": ("TemporalCheckpointRegistry",),
        "aura_arena_persistence_adapters.py": (
            "ArenaPersistenceCoordinator",
        ),
    },
    "E13": {
        "aura_construction_refactor_completion.py": (
            "validate_construction_refactor_completion",
        )
    },
}

_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "aura_human_agent_arena_server.py": (
        "/api/human-agent/construction/status",
        "/api/human-agent/construction/profile",
        "/api/human-agent/construction/observatory",
        "/api/human-agent/construction/handoff",
        "/api/human-agent/construction/checkpoint",
    ),
    "aura_human_agent_arena/index.html": (
        'data-surface="construction-workspace"',
        'id="construction-workspace"',
        'src="construction.js"',
    ),
    "aura_human_agent_arena/construction.js": (
        "/api/human-agent/construction/profile",
        "/api/human-agent/construction/observatory",
    ),
    "docs/AURA_CROSS_ARENA_CHANGE_HANDOFF_LOG.md": (
        "WIRE-SCO-001",
        "WIRE-SCO-012",
        "READY_FOR_PINNED_MERGE",
    ),
    "README.md": ("Construction Human Agent profile",),
    ".aura/ARCHITECTURE.md": ("Construction Human Agent and Observatory",),
    "USER_GUIDE.md": ("Construction review surface",),
}

_POLICY_DEFERRALS = (
    "real owner contractor payment access sensor and safety connectors",
    "physical construction control",
    "professional safety engineering legal or regulatory certification",
    "automatic payment release or fund transfer",
    "automatic state restoration hotswap commit push pull request or merge",
    "commercial field-performance claims",
)


@dataclass(frozen=True)
class ConstructionRefactorNodeAudit:
    node_id: str
    status: str
    owners: tuple[str, ...]
    missing: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["owners"] = list(self.owners)
        value["missing"] = list(self.missing)
        return value


def _canonical_root(repo_root: str | Path) -> Path:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise ValueError("repo_root must be an existing directory")
    return root


def _symbols(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"cannot parse required owner {path.name}: {exc}") from exc
    return {
        item.name
        for item in tree.body
        if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _audit_node(root: Path, node_id: str, owners: Mapping[str, tuple[str, ...]]) -> ConstructionRefactorNodeAudit:
    missing: list[str] = []
    owner_names: list[str] = []
    for relative_path, expected_symbols in owners.items():
        path = root / relative_path
        owner_names.append(relative_path)
        if not path.is_file():
            missing.append(f"missing_file:{relative_path}")
            continue
        present = _symbols(path)
        for symbol in expected_symbols:
            if symbol not in present:
                missing.append(f"missing_symbol:{relative_path}:{symbol}")
    return ConstructionRefactorNodeAudit(
        node_id=node_id,
        status="INTEGRATED" if not missing else "INCOMPLETE",
        owners=tuple(sorted(owner_names)),
        missing=tuple(sorted(missing)),
    )


def _marker_failures(root: Path) -> list[str]:
    failures: list[str] = []
    for relative_path, markers in _REQUIRED_MARKERS.items():
        path = root / relative_path
        if not path.is_file():
            failures.append(f"missing_file:{relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                failures.append(f"missing_marker:{relative_path}:{marker}")
    return sorted(failures)


def validate_construction_refactor_completion(
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Return the exact remaining implementation and release status."""
    root = _canonical_root(repo_root)
    nodes = tuple(
        _audit_node(root, node_id, owners)
        for node_id, owners in sorted(
            _REQUIRED_SYMBOLS.items(), key=lambda item: int(item[0][1:])
        )
    )
    marker_failures = _marker_failures(root)
    node_failures = [
        failure
        for node in nodes
        for failure in node.missing
    ]
    unresolved = sorted({*marker_failures, *node_failures})
    runtime_complete = not unresolved
    release_status = (
        "READY_FOR_PINNED_MERGE" if runtime_complete else "IMPLEMENTATION_INCOMPLETE"
    )
    node_status = {node.node_id: node.status for node in nodes}
    human_surface_failures = [
        item
        for item in marker_failures
        if any(
            owner in item
            for owner in (
                "aura_human_agent_arena_server.py",
                "aura_human_agent_arena/index.html",
                "aura_human_agent_arena/construction.js",
            )
        )
    ]
    observatory_failures = [
        item for item in human_surface_failures if "observatory" in item
    ]
    construction_human_agent_integrated = (
        node_status.get("E9") == "INTEGRATED" and not human_surface_failures
    )
    payload = {
        "version": CONSTRUCTION_REFACTOR_COMPLETION_VERSION,
        "runtime_nodes": [node.to_dict() for node in nodes],
        "runtime_complete": runtime_complete,
        "e14_release_status": release_status,
        "unresolved": unresolved,
        "policy_deferrals": list(_POLICY_DEFERRALS),
        "policy_deferrals_are_incomplete_work": False,
        "construction_human_agent_integrated": construction_human_agent_integrated,
        "observatory_read_only": (
            construction_human_agent_integrated and not observatory_failures
        ),
        "handoff_validation_enforced": any(
            node.node_id == "E13" and node.status == "INTEGRATED" for node in nodes
        ),
        "human_review_required": True,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "professional_certification_authorized": False,
        "automatic_merge": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    payload["audit_digest"] = stable_digest(payload)
    return {"ok": runtime_complete, **payload}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate SCO Construction E0-E14 refactor completion."
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    try:
        result = validate_construction_refactor_completion(args.repo_root)
    except ValueError as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONSTRUCTION_REFACTOR_COMPLETION_VERSION",
    "ConstructionRefactorNodeAudit",
    "validate_construction_refactor_completion",
]
