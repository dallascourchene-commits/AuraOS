#!/usr/bin/env python3
"""Deterministic storey hierarchy/index compiler for the Construction demo IFC.

The dependency-free STEP scanner is preflight evidence only. Authoritative index
output requires IfcOpenShell and must agree with the preflight storey identities.
No output from this module is survey-authoritative or a Construction state owner.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_event_contracts import stable_digest

IFC_STOREY_INDEX_VERSION = "AURA_CONSTRUCTION_DEMO_IFC_STOREY_INDEX_V1"
IFC_PREFLIGHT_VERSION = "AURA_CONSTRUCTION_DEMO_IFC_PREFLIGHT_V1"
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_STOREYS = 64
MAX_SPACES = 100_000
MAX_ELEMENTS = 250_000
MAX_NAME_BYTES = 512
MAX_GLOBAL_ID_BYTES = 128
_IFC_STOREY_LINE = re.compile(r"^#(?P<entity_id>\d+)\s*=\s*IFCBUILDINGSTOREY\((?P<body>.*)\);\s*$", re.IGNORECASE)
_IFC_GLOBAL_ID = re.compile(r"^[A-Za-z0-9_$]{1,128}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class StoreyIdentity:
    storey_id: str
    ifc_global_id: str
    name: str
    elevation_m: float
    ordinal: int
    source_entity_id: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "storey_id": self.storey_id,
            "ifc_global_id": self.ifc_global_id,
            "name": self.name,
            "elevation_m": self.elevation_m,
            "ordinal": self.ordinal,
            "source_entity_id": self.source_entity_id,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, name: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _text(value: Any, name: str, *, fallback: str | None = None) -> str:
    if value is None or value == "$":
        if fallback is None:
            raise ValueError(f"{name} is required")
        value = fallback
    if type(value) is not str:
        value = str(value)
    normalized = " ".join(value.split())
    if not normalized or len(normalized.encode("utf-8")) > MAX_NAME_BYTES:
        raise ValueError(f"{name} must be a bounded non-empty string")
    return normalized


def _global_id(value: Any, name: str) -> str:
    if type(value) is not str or _IFC_GLOBAL_ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical IFC GlobalId")
    if len(value.encode("utf-8")) > MAX_GLOBAL_ID_BYTES:
        raise ValueError(f"{name} exceeds its byte limit")
    return value


def _finite(value: Any, name: str) -> float:
    if value in {None, "$", "*"}:
        value = 0.0
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _local_ref(value: str, name: str) -> str:
    if type(value) is not str or not value or "\\" in value or "://" in value:
        raise ValueError(f"{name} must be a local POSIX reference")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{name} must be repository-relative and normalized")
    return value


def _step_fields(body: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    quoted = False
    depth = 0
    index = 0
    while index < len(body):
        char = body[index]
        if char == "'":
            current.append(char)
            if quoted and index + 1 < len(body) and body[index + 1] == "'":
                current.append("'")
                index += 2
                continue
            quoted = not quoted
        elif not quoted and char == "(":
            depth += 1
            current.append(char)
        elif not quoted and char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("STEP field nesting is invalid")
            current.append(char)
        elif not quoted and depth == 0 and char == ",":
            fields.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    if quoted or depth != 0:
        raise ValueError("STEP field quoting or nesting is incomplete")
    fields.append("".join(current).strip())
    return fields


def _step_string(value: str, name: str) -> str:
    if len(value) < 2 or not value.startswith("'") or not value.endswith("'"):
        raise ValueError(f"{name} must be a STEP string")
    return value[1:-1].replace("''", "'")


def canonical_storey_id(
    *,
    source_sha256: str,
    ifc_global_id: str,
    name: str,
    elevation_m: float,
) -> str:
    payload = {
        "source_sha256": _require_sha256(source_sha256, "source_sha256"),
        "ifc_global_id": _global_id(ifc_global_id, "ifc_global_id"),
        "name": _text(name, "name"),
        "elevation_m": _finite(elevation_m, "elevation_m"),
    }
    return "storey-" + stable_digest(payload)[:20]


def _ordered_storeys(rows: Iterable[Mapping[str, Any]], source_sha256: str) -> tuple[StoreyIdentity, ...]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        global_id = _global_id(row.get("ifc_global_id"), "ifc_global_id")
        if global_id in seen:
            raise ValueError(f"duplicate IFC GlobalId: {global_id}")
        seen.add(global_id)
        normalized.append(
            {
                "ifc_global_id": global_id,
                "name": _text(row.get("name"), "storey name", fallback=f"Storey {global_id}"),
                "elevation_m": _finite(row.get("elevation_m"), "storey elevation"),
                "source_entity_id": row.get("source_entity_id"),
            }
        )
    if not normalized or len(normalized) > MAX_STOREYS:
        raise ValueError(f"IFC must contain between 1 and {MAX_STOREYS} usable storeys")
    normalized.sort(key=lambda item: (item["elevation_m"], item["ifc_global_id"]))
    return tuple(
        StoreyIdentity(
            storey_id=canonical_storey_id(
                source_sha256=source_sha256,
                ifc_global_id=item["ifc_global_id"],
                name=item["name"],
                elevation_m=item["elevation_m"],
            ),
            ifc_global_id=item["ifc_global_id"],
            name=item["name"],
            elevation_m=item["elevation_m"],
            ordinal=ordinal,
            source_entity_id=(
                int(item["source_entity_id"])
                if item["source_entity_id"] is not None
                else None
            ),
        )
        for ordinal, item in enumerate(normalized)
    )


def preflight_ifc_storeys(path: Path, *, expected_sha256: str | None = None) -> dict[str, Any]:
    source = path.expanduser().resolve(strict=True)
    if not source.is_file() or source.is_symlink():
        raise ValueError("IFC preflight source must be a regular non-symlink file")
    size = source.stat().st_size
    if size <= 0 or size > MAX_SOURCE_BYTES:
        raise ValueError("IFC preflight source violates its byte budget")
    observed_sha256 = _sha256_file(source)
    if expected_sha256 is not None and observed_sha256 != _require_sha256(expected_sha256, "expected_sha256"):
        raise ValueError("IFC source SHA-256 differs from the pinned source")
    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, start=1):
            match = _IFC_STOREY_LINE.match(line.strip())
            if match is None:
                continue
            fields = _step_fields(match.group("body"))
            if len(fields) < 10:
                raise ValueError(f"IfcBuildingStorey at line {line_number} has too few fields")
            rows.append(
                {
                    "ifc_global_id": _step_string(fields[0], "IfcBuildingStorey.GlobalId"),
                    "name": _step_string(fields[2], "IfcBuildingStorey.Name") if fields[2] != "$" else None,
                    "elevation_m": fields[-1],
                    "source_entity_id": int(match.group("entity_id")),
                }
            )
    storeys = _ordered_storeys(rows, observed_sha256)
    payload = {
        "version": IFC_PREFLIGHT_VERSION,
        "source_sha256": observed_sha256,
        "source_byte_length": size,
        "storeys": [item.to_dict() for item in storeys],
        "storey_count": len(storeys),
        "authority": "STEP_TEXT_PREFLIGHT_ONLY",
        "ifcopenshell_validation_required": True,
        "survey_authority": False,
        "construction_state_owner": False,
        "production_mutation": False,
    }
    return {**payload, "preflight_digest": stable_digest(payload)}


def _is_a(entity: Any, expected: str | None = None) -> str | bool:
    method = getattr(entity, "is_a", None)
    if not callable(method):
        raise ValueError("IFC entity does not provide is_a()")
    return method(expected) if expected is not None else method()


def _entity_row(entity: Any, *, storey_id: str, kind: str) -> dict[str, Any]:
    global_id = _global_id(getattr(entity, "GlobalId", None), f"{kind}.GlobalId")
    return {
        "global_id": global_id,
        "ifc_class": _text(_is_a(entity), f"{kind}.ifc_class"),
        "name": _text(getattr(entity, "Name", None), f"{kind}.Name", fallback=global_id),
        "storey_id": storey_id,
    }


def _related_entities(storey: Any) -> tuple[Any, ...]:
    values: list[Any] = []
    for relation in tuple(getattr(storey, "ContainsElements", ()) or ()):
        values.extend(tuple(getattr(relation, "RelatedElements", ()) or ()))
    for relation in tuple(getattr(storey, "IsDecomposedBy", ()) or ()):
        values.extend(tuple(getattr(relation, "RelatedObjects", ()) or ()))
    unique: dict[str, Any] = {}
    for entity in values:
        global_id = getattr(entity, "GlobalId", None)
        if global_id is not None:
            unique[str(global_id)] = entity
    return tuple(unique[key] for key in sorted(unique))


def compile_ifcopenshell_index(
    model: Any,
    *,
    source_sha256: str,
    source_ref: str,
    preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_digest = _require_sha256(source_sha256, "source_sha256")
    local_source_ref = _local_ref(source_ref, "source_ref")
    projects = tuple(model.by_type("IfcProject"))
    buildings = tuple(model.by_type("IfcBuilding"))
    if len(projects) != 1 or len(buildings) != 1:
        raise ValueError("Construction demo IFC must contain exactly one project and one building")
    project = projects[0]
    building = buildings[0]
    project_global_id = _global_id(getattr(project, "GlobalId", None), "project.GlobalId")
    building_global_id = _global_id(getattr(building, "GlobalId", None), "building.GlobalId")

    raw_storeys = []
    storey_entities: dict[str, Any] = {}
    for storey in tuple(model.by_type("IfcBuildingStorey")):
        global_id = _global_id(getattr(storey, "GlobalId", None), "storey.GlobalId")
        raw_storeys.append(
            {
                "ifc_global_id": global_id,
                "name": getattr(storey, "Name", None),
                "elevation_m": getattr(storey, "Elevation", 0.0),
                "source_entity_id": int(storey.id()) if callable(getattr(storey, "id", None)) else None,
            }
        )
        storey_entities[global_id] = storey
    storeys = _ordered_storeys(raw_storeys, source_digest)

    if preflight is not None:
        if preflight.get("source_sha256") != source_digest:
            raise ValueError("IfcOpenShell source differs from preflight source")
        expected = [
            (item["ifc_global_id"], item["name"], float(item["elevation_m"]))
            for item in preflight.get("storeys", ())
        ]
        observed = [(item.ifc_global_id, item.name, item.elevation_m) for item in storeys]
        if observed != expected:
            raise ValueError("IfcOpenShell storey hierarchy differs from STEP preflight")

    seen_global_ids = {project_global_id, building_global_id}
    spaces: list[dict[str, Any]] = []
    elements: list[dict[str, Any]] = []
    storey_rows: list[dict[str, Any]] = []
    for identity in storeys:
        if identity.ifc_global_id in seen_global_ids:
            raise ValueError(f"duplicate IFC GlobalId: {identity.ifc_global_id}")
        seen_global_ids.add(identity.ifc_global_id)
        storey = storey_entities[identity.ifc_global_id]
        storey_space_ids: list[str] = []
        storey_element_ids: list[str] = []
        for entity in _related_entities(storey):
            row_kind = "space" if _is_a(entity, "IfcSpace") else "element"
            row = _entity_row(entity, storey_id=identity.storey_id, kind=row_kind)
            if row["global_id"] in seen_global_ids:
                raise ValueError(f"duplicate IFC GlobalId: {row['global_id']}")
            seen_global_ids.add(row["global_id"])
            if row_kind == "space":
                spaces.append(row)
                storey_space_ids.append(row["global_id"])
            else:
                elements.append(row)
                storey_element_ids.append(row["global_id"])
        storey_rows.append(
            {
                **identity.to_dict(),
                "space_global_ids": sorted(storey_space_ids),
                "element_global_ids": sorted(storey_element_ids),
            }
        )
    if len(spaces) > MAX_SPACES or len(elements) > MAX_ELEMENTS:
        raise ValueError("IFC hierarchy exceeds bounded space or element counts")
    spaces.sort(key=lambda item: (item["storey_id"], item["global_id"]))
    elements.sort(key=lambda item: (item["storey_id"], item["global_id"]))
    payload = {
        "version": IFC_STOREY_INDEX_VERSION,
        "source_sha256": source_digest,
        "source_ref": local_source_ref,
        "project": {
            "ifc_global_id": project_global_id,
            "name": _text(getattr(project, "Name", None), "project.Name", fallback=project_global_id),
        },
        "building": {
            "ifc_global_id": building_global_id,
            "name": _text(getattr(building, "Name", None), "building.Name", fallback=building_global_id),
        },
        "storeys": storey_rows,
        "spaces": spaces,
        "elements": elements,
        "counts": {
            "storeys": len(storey_rows),
            "spaces": len(spaces),
            "elements": len(elements),
        },
        "deterministic_order": True,
        "ifcopenshell_validated": True,
        "survey_authority": False,
        "construction_state_owner": False,
        "production_mutation": False,
    }
    return {**payload, "hierarchy_digest": stable_digest(payload)}


def load_ifcopenshell_model(path: Path, *, module: Any | None = None) -> Any:
    if module is None:
        try:
            import ifcopenshell as module  # type: ignore[no-redef]
        except ImportError as exc:
            raise RuntimeError(
                "IfcOpenShell is required for authoritative IFC indexing; "
                "the STEP scanner is preflight evidence only"
            ) from exc
    return module.open(str(path))


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("preflight", "index"):
        child = subparsers.add_parser(command)
        child.add_argument("--source", type=Path, required=True)
        child.add_argument("--source-sha256", required=True)
        child.add_argument("--output", type=Path, required=True)
        child.add_argument(
            "--source-ref",
            default="demo_assets/construction_tuwien/source/CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc",
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preflight = preflight_ifc_storeys(args.source, expected_sha256=args.source_sha256)
    if args.command == "preflight":
        result = preflight
    else:
        model = load_ifcopenshell_model(args.source)
        result = compile_ifcopenshell_index(
            model,
            source_sha256=args.source_sha256,
            source_ref=args.source_ref,
            preflight=preflight,
        )
    _atomic_json(args.output, result)
    print(json.dumps({"output": str(args.output), "digest": result.get("hierarchy_digest") or result.get("preflight_digest")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
