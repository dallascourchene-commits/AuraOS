from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.aura_ifc_storey_index import (
    canonical_storey_id,
    compile_ifcopenshell_index,
    load_ifcopenshell_model,
    preflight_ifc_storeys,
)


class Entity:
    def __init__(self, ifc_class: str, global_id: str, name: str, *, elevation: float = 0.0, entity_id: int = 1) -> None:
        self._ifc_class = ifc_class
        self.GlobalId = global_id
        self.Name = name
        self.Elevation = elevation
        self._entity_id = entity_id
        self.ContainsElements: tuple[Relation, ...] = ()
        self.IsDecomposedBy: tuple[Relation, ...] = ()

    def is_a(self, expected: str | None = None) -> str | bool:
        return self._ifc_class == expected if expected is not None else self._ifc_class

    def id(self) -> int:
        return self._entity_id


class Relation:
    def __init__(self, *, elements: tuple[Entity, ...] = (), objects: tuple[Entity, ...] = ()) -> None:
        self.RelatedElements = elements
        self.RelatedObjects = objects


class Model:
    def __init__(self, entities: dict[str, tuple[Entity, ...]]) -> None:
        self.entities = entities

    def by_type(self, name: str) -> tuple[Entity, ...]:
        return self.entities.get(name, ())


def _ifc_text() -> bytes:
    return b"""ISO-10303-21;\nDATA;\n#5= IFCBUILDINGSTOREY('BBBBBBBBBBBBBBBBBBBBBB',#1,'Floor 1',$,$,#2,$,$,.ELEMENT.,3.4);\n#4= IFCBUILDINGSTOREY('AAAAAAAAAAAAAAAAAAAAAA',#1,'Floor 0',$,$,#3,$,$,.ELEMENT.,0.);\nENDSEC;\nEND-ISO-10303-21;\n"""


def test_preflight_orders_storeys_and_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "model.ifc"
    source.write_bytes(_ifc_text())
    digest = hashlib.sha256(_ifc_text()).hexdigest()

    first = preflight_ifc_storeys(source, expected_sha256=digest)
    second = preflight_ifc_storeys(source, expected_sha256=digest)

    assert first == second
    assert [item["name"] for item in first["storeys"]] == ["Floor 0", "Floor 1"]
    assert [item["ordinal"] for item in first["storeys"]] == [0, 1]
    assert first["authority"] == "STEP_TEXT_PREFLIGHT_ONLY"
    assert first["ifcopenshell_validation_required"] is True
    assert first["survey_authority"] is False


def test_preflight_rejects_hash_drift_and_duplicate_global_ids(tmp_path: Path) -> None:
    source = tmp_path / "model.ifc"
    source.write_bytes(_ifc_text())
    with pytest.raises(ValueError, match="SHA-256"):
        preflight_ifc_storeys(source, expected_sha256="0" * 64)

    duplicate = _ifc_text().replace(b"BBBBBBBBBBBBBBBBBBBBBB", b"AAAAAAAAAAAAAAAAAAAAAA")
    source.write_bytes(duplicate)
    with pytest.raises(ValueError, match="duplicate IFC GlobalId"):
        preflight_ifc_storeys(source)


def test_canonical_storey_id_binds_source_identity() -> None:
    common = {
        "ifc_global_id": "AAAAAAAAAAAAAAAAAAAAAA",
        "name": "Floor 0",
        "elevation_m": 0.0,
    }
    first = canonical_storey_id(source_sha256="1" * 64, **common)
    assert first == canonical_storey_id(source_sha256="1" * 64, **common)
    assert first != canonical_storey_id(source_sha256="2" * 64, **common)


def test_compile_ifcopenshell_index_matches_preflight_and_bounds_entities(tmp_path: Path) -> None:
    source = tmp_path / "model.ifc"
    source.write_bytes(_ifc_text())
    source_sha = hashlib.sha256(_ifc_text()).hexdigest()
    preflight = preflight_ifc_storeys(source, expected_sha256=source_sha)

    floor0 = Entity("IfcBuildingStorey", "AAAAAAAAAAAAAAAAAAAAAA", "Floor 0", entity_id=4)
    floor1 = Entity("IfcBuildingStorey", "BBBBBBBBBBBBBBBBBBBBBB", "Floor 1", elevation=3.4, entity_id=5)
    wall = Entity("IfcWall", "CCCCCCCCCCCCCCCCCCCCCC", "Wall")
    space = Entity("IfcSpace", "DDDDDDDDDDDDDDDDDDDDDD", "Room")
    floor0.ContainsElements = (Relation(elements=(wall,)),)
    floor0.IsDecomposedBy = (Relation(objects=(space,)),)
    model = Model(
        {
            "IfcProject": (Entity("IfcProject", "PPPPPPPPPPPPPPPPPPPPPP", "Project"),),
            "IfcBuilding": (Entity("IfcBuilding", "GGGGGGGGGGGGGGGGGGGGGG", "Building"),),
            "IfcBuildingStorey": (floor1, floor0),
        }
    )

    result = compile_ifcopenshell_index(
        model,
        source_sha256=source_sha,
        source_ref="demo_assets/construction_tuwien/source/model.ifc",
        preflight=preflight,
    )

    assert result["counts"] == {"storeys": 2, "spaces": 1, "elements": 1}
    assert [item["name"] for item in result["storeys"]] == ["Floor 0", "Floor 1"]
    assert result["spaces"][0]["global_id"] == "DDDDDDDDDDDDDDDDDDDDDD"
    assert result["elements"][0]["global_id"] == "CCCCCCCCCCCCCCCCCCCCCC"
    assert result["ifcopenshell_validated"] is True
    assert result["construction_state_owner"] is False


def test_compile_ifcopenshell_index_rejects_preflight_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "model.ifc"
    source.write_bytes(_ifc_text())
    source_sha = hashlib.sha256(_ifc_text()).hexdigest()
    preflight = preflight_ifc_storeys(source)
    floor = Entity("IfcBuildingStorey", "AAAAAAAAAAAAAAAAAAAAAA", "Renamed", entity_id=4)
    model = Model(
        {
            "IfcProject": (Entity("IfcProject", "PPPPPPPPPPPPPPPPPPPPPP", "Project"),),
            "IfcBuilding": (Entity("IfcBuilding", "GGGGGGGGGGGGGGGGGGGGGG", "Building"),),
            "IfcBuildingStorey": (floor,),
        }
    )
    with pytest.raises(ValueError, match="differs from STEP preflight"):
        compile_ifcopenshell_index(
            model,
            source_sha256=source_sha,
            source_ref="demo_assets/construction_tuwien/source/model.ifc",
            preflight=preflight,
        )


def test_load_ifcopenshell_model_uses_explicit_module(tmp_path: Path) -> None:
    source = tmp_path / "model.ifc"
    source.write_text("ISO-10303-21;", encoding="utf-8")

    class Module:
        @staticmethod
        def open(path: str) -> str:
            return path

    assert load_ifcopenshell_model(source, module=Module) == str(source)
