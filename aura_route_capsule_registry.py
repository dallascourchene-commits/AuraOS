"""Fail-closed repository-relative registries for Aura route-capsule components."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

ROUTE_CAPSULE_REGISTRY_VERSION = "AURA_ROUTE_CAPSULE_REGISTRY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

REFERENCE_ROOTS = {
    "morphology_profile_ref": PurePosixPath(".aura/morphology_profiles"),
    "vsa_profile_ref": PurePosixPath(".aura/vsa_profiles"),
    "data_aperture_ref": PurePosixPath(".aura/data_apertures"),
    "memory_aperture_ref": PurePosixPath(".aura/memory_apertures"),
    "tool_bundle_ref": PurePosixPath(".aura/tool_bundles"),
    "model_policy_ref": PurePosixPath(".aura/model_policies"),
    "execution_budget_ref": PurePosixPath(".aura/execution_budgets"),
    "verifier_contract_ref": PurePosixPath(".aura/verifier_contracts"),
    "output_schema_ref": PurePosixPath(".aura/output_schemas"),
    "route_capsule": PurePosixPath(".aura/route_capsules"),
}


@dataclass(frozen=True)
class LoadedRegistryComponent:
    field_name: str
    relative_path: str
    absolute_path: Path
    component_id: str
    kind: str
    schema_version: str
    digest: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "relative_path": self.relative_path,
            "component_id": self.component_id,
            "kind": self.kind,
            "schema_version": self.schema_version,
            "digest": self.digest,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def canonical_json_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def resolve_repository_reference(repo_root: str | Path, reference: str, *, field_name: str) -> tuple[Path, str]:
    root = Path(repo_root).resolve()
    raw = str(reference or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError(f"{field_name} is required")
    pure = PurePosixPath(raw)
    if not pure.parts:
        raise ValueError(f"{field_name} contains unsafe path traversal")
    if pure.is_absolute() or ":" in pure.parts[0]:
        raise ValueError(f"{field_name} must be repository-relative")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"{field_name} contains unsafe path traversal")
    expected_root = REFERENCE_ROOTS.get(field_name)
    if expected_root is None:
        raise ValueError(f"unsupported route-capsule reference field: {field_name}")
    try:
        pure.relative_to(expected_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must remain under {expected_root.as_posix()}") from exc
    if pure.suffix.casefold() != ".json":
        raise ValueError(f"{field_name} must reference a JSON component")

    candidate = root.joinpath(*pure.parts)
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"{field_name} may not traverse symlinks")
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"component not found: {pure.as_posix()}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field_name} escapes the repository root") from exc
    return resolved, pure.as_posix()


def load_registry_component(repo_root: str | Path, reference: str, *, field_name: str) -> LoadedRegistryComponent:
    path, relative = resolve_repository_reference(repo_root, reference, field_name=field_name)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON component {relative}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TypeError(f"component {relative} must contain an object")
    schema_version = str(payload.get("schema_version") or "").strip()
    component_id = str(payload.get("component_id") or "").strip()
    kind = str(payload.get("kind") or "").strip()
    if not schema_version or not component_id or not kind:
        raise ValueError(f"component {relative} requires schema_version, component_id, and kind")
    return LoadedRegistryComponent(
        field_name=field_name,
        relative_path=relative,
        absolute_path=path,
        component_id=component_id,
        kind=kind,
        schema_version=schema_version,
        digest=canonical_json_digest(payload),
        payload=payload,
    )
