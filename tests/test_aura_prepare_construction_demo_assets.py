from __future__ import annotations

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


def _hierarchy(source: Path) -> dict[str, object]:
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    body: dict[str, object] = {
        "source_sha256": source_sha,
        "ifcopenshell_validated": True,
        "storeys": [
            {"ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA", "storey_id": "storey-a"},
            {"ifc_global_id": "BBBBBBBBBBBBBBBBBBBBBB", "storey_id": "storey-b"},
        ],
    }
    body["hierarchy_digest"] = stable_digest(body)
    return body


def test_split_storeys_maps_random_outputs_to_canonical_ids(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    receipt = split_storeys(
        source=source,
        hierarchy=_hierarchy(source),
        output_dir=Path("generated"),
        repo_root=tmp_path,
        ifcopenshell_module=IfcModule,
        ifcpatch_module=IfcPatch,
    )

    assert receipt["phase"] == "SPLIT_STOREYS"
    assert [item["storey_id"] for item in receipt["outputs"]] == ["storey-a", "storey-b"]
    for item in receipt["outputs"]:
        path = tmp_path / item["path"]
        assert path.name == f"{item['storey_id']}.ifc"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert (tmp_path / "generated/receipts/split-storeys.json").is_file()


def test_split_storeys_rejects_non_authoritative_hierarchy(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    hierarchy = _hierarchy(source)
    hierarchy["ifcopenshell_validated"] = False
    with pytest.raises(ValueError, match="authoritative"):
        split_storeys(
            source=source,
            hierarchy=hierarchy,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            ifcopenshell_module=IfcModule,
            ifcpatch_module=IfcPatch,
        )


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
    out.write_text('<svg xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M0 0\" /></svg>', encoding='utf-8')
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


def test_convert_ifc_assets_writes_verified_outputs_and_receipts(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    generated = tmp_path / "generated"
    split_outputs = []
    for storey_id in ("storey-a", "storey-b"):
        path = generated / "storeys" / storey_id / f"{storey_id}.ifc"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(storey_id, encoding="utf-8")
        split_outputs.append(
            {
                "storey_id": storey_id,
                "path": path.relative_to(tmp_path).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    split_body = {
        "phase": "SPLIT_STOREYS",
        "outputs": split_outputs,
        "production_mutation": False,
    }
    split_body["receipt_digest"] = stable_digest(split_body)
    executable = tmp_path / "IfcConvert"
    _fake_ifcconvert(executable)

    receipt = convert_ifc_assets(
        source=source,
        split_receipt=split_body,
        output_dir=Path("generated"),
        repo_root=tmp_path,
        ifcconvert=executable,
        workers=2,
        timeout_seconds=10,
    )

    assert receipt["phase"] == "CONVERT_GLB_SVG"
    assert receipt["output_count"] == 5
    assert receipt["external_resource_fetch"] is False
    assert {item["representation"] for item in receipt["outputs"]} == {"MESH_GLB", "FLOOR_PLAN_SVG"}
    assert (generated / "building-full.glb").is_file()
    assert (generated / "storeys/storey-a/storey-a.svg").read_bytes().startswith(b"<?xml")
    assert (generated / "receipts/convert-glb-svg.json").is_file()


def test_convert_ifc_assets_rejects_split_digest_drift(tmp_path: Path) -> None:
    source = tmp_path / "source.ifc"
    source.write_text("source", encoding="utf-8")
    split = tmp_path / "split.ifc"
    split.write_text("actual", encoding="utf-8")
    executable = tmp_path / "IfcConvert"
    _fake_ifcconvert(executable)
    receipt = {
        "phase": "SPLIT_STOREYS",
        "outputs": [{"storey_id": "storey-a", "path": "split.ifc", "sha256": "0" * 64}],
        "production_mutation": False,
        "receipt_digest": "f" * 32,
    }
    with pytest.raises(ValueError, match="digest drifted"):
        convert_ifc_assets(
            source=source,
            split_receipt=receipt,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            ifcconvert=executable,
            workers=1,
        )


def test_compile_gaussian_assets_distinguishes_building_and_storey_profiles(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    building = generated / "building-full.glb"
    storey = generated / "storeys/storey-a/storey-a.glb"
    svg = generated / "storeys/storey-a/storey-a.svg"
    for path, body in ((building, b"building"), (storey, b"storey"), (svg, b"svg")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    outputs = []
    for job_id, path, representation in (
        ("building-full-glb", building, "MESH_GLB"),
        ("storey-a-glb", storey, "MESH_GLB"),
        ("storey-a-svg", svg, "FLOOR_PLAN_SVG"),
    ):
        row = {
            "job_id": job_id,
            "output": path.relative_to(tmp_path).as_posix(),
            "output_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "representation": representation,
        }
        row["receipt_digest"] = stable_digest(row)
        outputs.append(row)
    conversion = {
        "phase": "CONVERT_GLB_SVG",
        "outputs": outputs,
        "production_mutation": False,
    }
    conversion["receipt_digest"] = stable_digest(conversion)
    calls = []

    def fake_compiler(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        ply = Path(kwargs["output_ply"])
        spz = Path(kwargs["output_spz"])
        ply.write_bytes(b"ply")
        spz.write_bytes(b"spz")
        source_digest = str(kwargs["source_digest"])
        scope = str(kwargs["scope"])
        return {
            "source_digest": source_digest,
            "scope": scope,
            "splat_count": kwargs["target_count"],
            "ply": {"path": ply.relative_to(tmp_path).as_posix()},
            "spz": {"path": spz.relative_to(tmp_path).as_posix()},
            "receipt_digest": stable_digest({"source": source_digest, "scope": scope}),
        }

    receipt = compile_gaussian_assets(
        conversion_receipt=conversion,
        output_dir=Path("generated"),
        repo_root=tmp_path,
        profile="STANDARD",
        storey_target_count=20,
        building_target_count=40,
        mesh_compiler=fake_compiler,
    )

    assert receipt["phase"] == "SAMPLE_GAUSSIANS_WRITE_SPZ"
    assert receipt["output_count"] == 2
    assert receipt["profile_limits"] == {"STOREY": 150_000, "BUILDING": 500_000}
    assert [(call["scope"], call["target_count"]) for call in calls] == [
        ("BUILDING", 40),
        ("STOREY", 20),
    ]
    assert (generated / "building-full.gaussian.ply").read_bytes() == b"ply"
    assert (generated / "building-full.spz").read_bytes() == b"spz"
    assert (generated / "receipts/compile-gaussians.json").is_file()


def test_compile_gaussian_assets_rejects_glb_digest_drift(tmp_path: Path) -> None:
    glb = tmp_path / "building.glb"
    glb.write_bytes(b"actual")
    row = {
        "job_id": "building-full-glb",
        "output": "building.glb",
        "output_sha256": "0" * 64,
        "representation": "MESH_GLB",
        "receipt_digest": "f" * 32,
    }
    conversion = {
        "phase": "CONVERT_GLB_SVG",
        "outputs": [row],
        "production_mutation": False,
        "receipt_digest": "e" * 32,
    }
    with pytest.raises(ValueError, match="digest drifted"):
        compile_gaussian_assets(
            conversion_receipt=conversion,
            output_dir=Path("generated"),
            repo_root=tmp_path,
            profile="LOW",
            mesh_compiler=lambda **_kwargs: {},
        )
