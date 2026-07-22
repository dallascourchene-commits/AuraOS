from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from aura_event_contracts import stable_digest
from scripts.aura_prepare_construction_demo_assets import (
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
out = Path(sys.argv[-1])
out.parent.mkdir(parents=True, exist_ok=True)
if '.svg.' in out.name:
    out.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0" /></svg>', encoding='utf-8')
else:
    doc = json.dumps(
        {'asset': {'version': '2.0'}, 'scenes': [{}], 'nodes': [], 'meshes': []},
        separators=(',', ':'),
    ).encode()
    doc += b' ' * ((4 - len(doc) % 4) % 4)
    total = 20 + len(doc)
    out.write_bytes(struct.pack('<4sII', b'glTF', 2, total) + struct.pack('<II', len(doc), 0x4E4F534A) + doc)
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
    assert {item["representation"] for item in receipt["outputs"]} == {"MESH_GLB", "FLOOR_PLAN_SVG"}
    assert all(item["split_receipt_digest"] == split["receipt_digest"] for item in receipt["outputs"])
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
