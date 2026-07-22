from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from aura_construction_demo_contracts import ConstructionDemoSourceManifest
from aura_event_contracts import stable_digest
from scripts.aura_prepare_construction_demo_assets import (
    _validate_pinned_source_manifest,
    compile_gaussian_assets,
    convert_ifc_assets,
    split_storeys,
)

SOURCE_MANIFEST_DIGEST = "a" * 32
HIERARCHY_DIGEST = "b" * 32


class Storey:
    def __init__(self, global_id: str) -> None:
        self.GlobalId = global_id


class SplitModel:
    def __init__(self, global_id: str) -> None:
        self.global_id = global_id

    def by_type(self, name: str) -> tuple[Storey, ...]:
        return (Storey(self.global_id),) if name == "IfcBuildingStorey" else ()


class IfcModule:
    @staticmethod
    def open(path: str) -> object:
        value = Path(path)
        if value.name == "source.ifc":
            return object()
        return SplitModel(value.read_text(encoding="utf-8").strip())


class IfcPatch:
    @staticmethod
    def execute(request: dict[str, object]) -> None:
        output = Path(str(request["arguments"][0]))
        (output / "random-second.ifc").write_text("BBBBBBBBBBBBBBBBBBBBBB", encoding="utf-8")
        (output / "random-first.ifc").write_text("AAAAAAAAAAAAAAAAAAAAAA", encoding="utf-8")


def _hierarchy(source: Path, *, storeys: list[dict[str, str]] | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "version": "test-hierarchy-v1",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "ifcopenshell_validated": True,
        "storeys": storeys
        or [
            {"ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA", "storey_id": "storey-a"},
            {"ifc_global_id": "BBBBBBBBBBBBBBBBBBBBBB", "storey_id": "storey-b"},
        ],
    }
    body["hierarchy_digest"] = stable_digest(body)
    return body


def _split_receipt(tmp_path: Path, source: Path) -> dict[str, object]:
    generated = tmp_path / "generated"
    outputs = []
    for global_id, storey_id in (
        ("AAAAAAAAAAAAAAAAAAAAAA", "storey-a"),
        ("BBBBBBBBBBBBBBBBBBBBBB", "storey-b"),
    ):
        path = generated / "storeys" / storey_id / f"{storey_id}.ifc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(storey_id, encoding="utf-8")
        outputs.append(
            {
                "storey_id": storey_id,
                "ifc_global_id": global_id,
                "path": path.relative_to(tmp_path).as_posix(),
                "byte_length": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    body: dict[str, object] = {
        "version": "AURA_CONSTRUCTION_DEMO_ASSET_PREPARATION_V1",
        "phase": "SPLIT_STOREYS",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_manifest_digest": SOURCE_MANIFEST_DIGEST,
        "hierarchy_digest": HIERARCHY_DIGEST,
        "outputs": outputs,
        "output_count": len(outputs),
        "production_mutation": False,
        "construction_state_owner": False,
    }
    body["receipt_digest"] = stable_digest(body)
    return body


def _fake_ifcconvert(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
from pathlib import Path
import struct
import sys
if sys.argv[-1] == '--version':
    print('IfcConvert fake 1.0')
    raise SystemExit(0)
out = Path(sys.argv[-1])
out.parent.mkdir(parents=True, exist_ok=True)
if out.suffix == '.svg':
    out.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0" /></svg>', encoding='utf-8')
else:
    positions = struct.pack('<9f', 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    indices = struct.pack('<3H', 0, 1, 2)
    binary = positions + indices
    document = {
        'asset': {'version': '2.0'},
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(positions), 'target': 34962},
            {'buffer': 0, 'byteOffset': len(positions), 'byteLength': len(indices), 'target': 34963},
        ],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'},
            {'bufferView': 1, 'componentType': 5123, 'count': 3, 'type': 'SCALAR'},
        ],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1, 'mode': 4}]}],
        'nodes': [{'mesh': 0}],
        'scenes': [{'nodes': [0]}],
        'scene': 0,
    }
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * ((4 - len(encoded) % 4) % 4)
    binary += b'\\x00' * ((4 - len(binary) % 4) % 4)
    body = (
        struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
        + struct.pack('<II', len(binary), 0x004E4942) + binary
    )
    out.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def _conversion(tmp_path: Path, source: Path) -> tuple[dict[str, object], dict[str, object]]:
    split = _split_receipt(tmp_path, source)
    executable = tmp_path / "IfcConvert"
    _fake_ifcconvert(executable)
    conversion = convert_ifc_assets(
        source=source,
        split_receipt=split,
        output_dir=Path("generated"),
        repo_root=tmp_path,
        ifcconvert=executable,
        workers=2,
        source_manifest_digest=SOURCE_MANIFEST_DIGEST,
        hierarchy_digest=HIERARCHY_DIGEST,
        timeout_seconds=10,
    )
    return split, conversion


def test_split_storeys_maps_random_outputs_to_canonical_ids(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    receipt = split_storeys(
        source=source,
        hierarchy=_hierarchy(source),
        output_dir=Path("generated"),
        repo_root=tmp_path,
        source_manifest_digest=SOURCE_MANIFEST_DIGEST,
        ifcopenshell_module=IfcModule,
        ifcpatch_module=IfcPatch,
    )

    assert receipt["phase"] == "SPLIT_STOREYS"
    assert receipt["source_manifest_digest"] == SOURCE_MANIFEST_DIGEST
    assert [item["storey_id"] for item in receipt["outputs"]] == ["storey-a", "storey-b"]
    for item in receipt["outputs"]:
        path = tmp_path / item["path"]
        assert path.name == f"{item['storey_id']}.ifc"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert (tmp_path / "generated/receipts/split-storeys.json").is_file()


def test_split_storeys_rejects_non_authoritative_or_tampered_hierarchy(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    hierarchy = _hierarchy(source)
    hierarchy["ifcopenshell_validated"] = False
    with pytest.raises(ValueError, match="hierarchy_digest"):
        split_storeys(
            source=source,
            hierarchy=hierarchy,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            ifcopenshell_module=IfcModule,
            ifcpatch_module=IfcPatch,
        )


def test_split_storeys_rejects_traversal_absolute_and_duplicate_ids_before_writes(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    bad_rows = [
        [
            {"ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA", "storey_id": "../escape"},
            {"ifc_global_id": "BBBBBBBBBBBBBBBBBBBBBB", "storey_id": "storey-b"},
        ],
        [
            {"ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA", "storey_id": "/tmp/escape"},
            {"ifc_global_id": "BBBBBBBBBBBBBBBBBBBBBB", "storey_id": "storey-b"},
        ],
        [
            {"ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA", "storey_id": "same"},
            {"ifc_global_id": "BBBBBBBBBBBBBBBBBBBBBB", "storey_id": "same"},
        ],
    ]
    for rows in bad_rows:
        with pytest.raises(ValueError, match="storey_id|duplicate storey ids"):
            split_storeys(
                source=source,
                hierarchy=_hierarchy(source, storeys=rows),
                output_dir=Path("generated"),
                repo_root=tmp_path,
                source_manifest_digest=SOURCE_MANIFEST_DIGEST,
                ifcopenshell_module=IfcModule,
                ifcpatch_module=IfcPatch,
            )
    assert not (tmp_path.parent / "escape").exists()


def test_convert_ifc_assets_writes_verified_outputs_and_authenticated_receipts(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split, receipt = _conversion(tmp_path, source)

    assert receipt["phase"] == "CONVERT_GLB_SVG"
    assert receipt["split_receipt_digest"] == split["receipt_digest"]
    assert receipt["output_count"] == 5
    assert receipt["external_resource_fetch"] is False
    identity = receipt["ifcconvert_identity"]
    assert identity["version_text"] == "IfcConvert fake 1.0"
    assert identity["sha256"] == hashlib.sha256((tmp_path / "IfcConvert").read_bytes()).hexdigest()
    assert {item["representation"] for item in receipt["outputs"]} == {"MESH_GLB", "FLOOR_PLAN_SVG"}
    assert all(item["split_receipt_digest"] == split["receipt_digest"] for item in receipt["outputs"])
    assert all(item["ifcconvert_identity_digest"] == identity["identity_digest"] for item in receipt["outputs"])
    assert all("duration_seconds" not in item["command_receipt"] for item in receipt["outputs"])
    glb_rows = [item for item in receipt["outputs"] if item["representation"] == "MESH_GLB"]
    assert all(item["canonicalization"]["runtime_admitted"] is True for item in glb_rows)
    assert all(len(item["runtime_import_receipt_digest"]) == 64 for item in glb_rows)
    assert all(item["canonicalization"]["output"] == item["output"] for item in glb_rows)
    assert all(
        item["canonicalization"]["source"].endswith(".glb") for item in glb_rows
    )
    assert (tmp_path / "generated/building-full.glb").is_file()
    assert (tmp_path / "generated/storeys/storey-a/storey-a.svg").read_bytes().startswith(b"<?xml")
    assert (tmp_path / "generated/receipts/convert-glb-svg.json").is_file()


def test_convert_ifc_assets_rejects_tampered_split_receipt_even_when_file_hash_matches(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split = _split_receipt(tmp_path, source)
    split["source_manifest_digest"] = "c" * 32
    split["receipt_digest"] = stable_digest({k: v for k, v in split.items() if k != "receipt_digest"})
    executable = tmp_path / "IfcConvert"
    _fake_ifcconvert(executable)

    with pytest.raises(ValueError, match="source-manifest lineage"):
        convert_ifc_assets(
            source=source,
            split_receipt=split,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            ifcconvert=executable,
            workers=1,
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            hierarchy_digest=HIERARCHY_DIGEST,
        )


def _fake_gaussian_compiler(tmp_path: Path, calls: list[dict[str, object]]):
    def fake_compiler(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        ply = Path(kwargs["output_ply"])
        spz = Path(kwargs["output_spz"])
        ply.write_bytes(b"ply")
        spz.write_bytes(b"spz")
        source_digest = str(kwargs["source_digest"])
        scope = str(kwargs["scope"])

        def representation(kind: str, path: Path) -> dict[str, object]:
            body: dict[str, object] = {
                "representation": kind,
                "path": path.relative_to(tmp_path).as_posix(),
                "byte_length": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            body["receipt_digest"] = stable_digest(body)
            return body

        body: dict[str, object] = {
            "source_digest": source_digest,
            "scope": scope,
            "splat_count": kwargs["target_count"],
            "ply": representation("GAUSSIAN_PLY", ply),
            "spz": representation("GAUSSIAN_SPZ", spz),
        }
        body["receipt_digest"] = stable_digest(body)
        return body

    return fake_compiler


def test_compile_gaussian_assets_authenticates_resume_chain_and_profiles(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split, conversion = _conversion(tmp_path, source)
    calls: list[dict[str, object]] = []

    receipt = compile_gaussian_assets(
        conversion_receipt=conversion,
        split_receipt=split,
        output_dir=Path("generated"),
        repo_root=tmp_path,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_manifest_digest=SOURCE_MANIFEST_DIGEST,
        hierarchy_digest=HIERARCHY_DIGEST,
        profile="STANDARD",
        storey_target_count=20,
        building_target_count=40,
        mesh_compiler=_fake_gaussian_compiler(tmp_path, calls),
    )

    assert receipt["phase"] == "SAMPLE_GAUSSIANS_WRITE_SPZ"
    assert receipt["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["output_count"] == 3
    assert receipt["profile_limits"] == {"STOREY": 75_000, "BUILDING": 100_000}
    assert [(call["scope"], call["target_count"]) for call in calls] == [
        ("BUILDING", 40),
        ("STOREY", 20),
        ("STOREY", 20),
    ]
    assert (tmp_path / "generated/building-full.gaussian.ply").read_bytes() == b"ply"
    assert (tmp_path / "generated/building-full.spz").read_bytes() == b"spz"
    assert (tmp_path / "generated/receipts/compile-gaussians.json").is_file()


def test_compile_gaussian_assets_rejects_tampered_conversion_job_and_lineage(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split, conversion = _conversion(tmp_path, source)

    nested_tamper = copy.deepcopy(conversion)
    nested_tamper["outputs"][0]["representation"] = "FLOOR_PLAN_SVG"
    nested_tamper["receipt_digest"] = stable_digest(
        {k: v for k, v in nested_tamper.items() if k != "receipt_digest"}
    )
    with pytest.raises(ValueError, match="receipt_digest"):
        compile_gaussian_assets(
            conversion_receipt=nested_tamper,
            split_receipt=split,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            hierarchy_digest=HIERARCHY_DIGEST,
            profile="LOW",
            mesh_compiler=lambda **_kwargs: {},
        )

    lineage_tamper = copy.deepcopy(conversion)
    lineage_tamper["source_manifest_digest"] = "d" * 32
    lineage_tamper["receipt_digest"] = stable_digest(
        {k: v for k, v in lineage_tamper.items() if k != "receipt_digest"}
    )
    with pytest.raises(ValueError, match="lineage"):
        compile_gaussian_assets(
            conversion_receipt=lineage_tamper,
            split_receipt=split,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            hierarchy_digest=HIERARCHY_DIGEST,
            profile="LOW",
            mesh_compiler=lambda **_kwargs: {},
        )


def test_pinned_source_manifest_rejects_self_consistent_substitution() -> None:
    value = {
        "version": "AURA_CONSTRUCTION_DEMO_SOURCE_MANIFEST_V1",
        "source_id": "tuwien-custom-escape-route-ifc-v2",
        "title": "Custom Test Model for Escape Route Analysis in IFC format",
        "creators": [
            "Christian Schranz",
            "Daniel Pfeiffer",
            "Harald Urban",
            "Sebastian Zdanowicz",
            "Simon Fischer",
        ],
        "publisher": "TU Wien",
        "doi": "10.48436/a185k-86v39",
        "source_filename": "CustomTestModel-EscapeRouteAnalysis-ZDB-v2.ifc",
        "source_byte_length": 7_404_420,
        "published_md5": "58a6e009b16bd3808cacd72b11fcf216",
        "observed_sha256": "29945f654c636d758a95b66eb0e107ec35afc7e1c7857a7ff652586e7728ba29",
        "license_id": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "downloaded_at": "2026-07-22T10:14:02Z",
        "fictional_source": True,
        "survey_authority": False,
        "person_level_data_included": False,
        "external_fetch_required_at_runtime": False,
        "source_manifest_digest": "22bd970d5babc6ad2d6a22ca2c278738",
    }
    canonical = ConstructionDemoSourceManifest.from_dict(value)
    _validate_pinned_source_manifest(canonical)

    substituted = dict(value)
    substituted["source_id"] = "replacement-source"
    substituted.pop("source_manifest_digest")
    with pytest.raises(ValueError, match="canonical TU Wien"):
        _validate_pinned_source_manifest(
            ConstructionDemoSourceManifest.from_dict(substituted)
        )


def test_compile_gaussian_assets_requires_every_storey_glb_job(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split, conversion = _conversion(tmp_path, source)
    incomplete = copy.deepcopy(conversion)
    incomplete["outputs"] = [
        item for item in incomplete["outputs"] if item["job_id"] != "storey-b-glb"
    ]
    incomplete["output_count"] = len(incomplete["outputs"])
    incomplete["receipt_digest"] = stable_digest(
        {key: value for key, value in incomplete.items() if key != "receipt_digest"}
    )

    with pytest.raises(ValueError, match="exact full-building and storey GLB jobs"):
        compile_gaussian_assets(
            conversion_receipt=incomplete,
            split_receipt=split,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            hierarchy_digest=HIERARCHY_DIGEST,
            profile="LOW",
            mesh_compiler=lambda **_kwargs: {},
        )


def test_compile_gaussian_assets_rejects_tampered_canonical_glb_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split, conversion = _conversion(tmp_path, source)
    tampered = copy.deepcopy(conversion)
    glb = next(item for item in tampered["outputs"] if item["representation"] == "MESH_GLB")
    glb["canonicalization"]["runtime_admitted"] = False
    glb["canonicalization"]["receipt_digest"] = stable_digest(
        {key: value for key, value in glb["canonicalization"].items() if key != "receipt_digest"}
    )
    glb["receipt_digest"] = stable_digest(
        {key: value for key, value in glb.items() if key != "receipt_digest"}
    )
    tampered["receipt_digest"] = stable_digest(
        {key: value for key, value in tampered.items() if key != "receipt_digest"}
    )

    with pytest.raises(ValueError, match="canonical GLB evidence"):
        compile_gaussian_assets(
            conversion_receipt=tampered,
            split_receipt=split,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_manifest_digest=SOURCE_MANIFEST_DIGEST,
            hierarchy_digest=HIERARCHY_DIGEST,
            profile="LOW",
            mesh_compiler=lambda **_kwargs: {},
        )
