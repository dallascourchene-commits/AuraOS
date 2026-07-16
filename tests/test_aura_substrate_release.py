from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aura_substrate_contracts import (
    CompatibilityMode,
    ContractStatus,
    FileRole,
    MigrationStatus,
    PhaseDisposition,
    SubstrateFileRecord,
    SubstrateManifest,
)
from aura_substrate_release import build_release_index


def _blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _manifest(path: str) -> SubstrateManifest:
    record = SubstrateFileRecord(path, FileRole.CANONICAL_CONTRACT, ("P1",))
    phase = PhaseDisposition(
        phase_id="P1",
        title="test phase",
        source_pr=1,
        merge_commit="0" * 40,
        component_paths=(path,),
        dependencies=(),
        evidence_paths=(path,),
        retained_dependency_paths=(),
        contract_status=ContractStatus.CANONICAL,
        compatibility_mode=CompatibilityMode.ADDITIVE,
        migration_status=MigrationStatus.CANONICAL_CONTRACT_ADOPTED,
        live_owner="test owner",
        ownership_disposition="RETAIN_TEST_OWNER",
    )
    return SubstrateManifest(files=(record,), phases=(phase,))


def test_release_index_is_deterministic_and_binds_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "contract.py"
    first_bytes = b"value = 1\n"
    path.write_bytes(first_bytes)
    manifest = _manifest("contract.py")

    first = build_release_index(tmp_path, manifest)
    repeated = build_release_index(tmp_path, manifest)
    assert first == repeated
    assert first["files"] == [
        {
            "path": "contract.py",
            "role": "CANONICAL_CONTRACT",
            "git_blob_sha1": _blob(first_bytes),
        }
    ]
    assert first["package_format"] == "INDEX_ONLY"
    assert first["publication_performed"] is False
    assert first["index_digest"]

    second_bytes = b"value = 2\n"
    path.write_bytes(second_bytes)
    changed = build_release_index(tmp_path, manifest)
    assert changed != first
    assert changed["files"][0]["git_blob_sha1"] == _blob(second_bytes)
    assert changed["index_digest"] != first["index_digest"]


def test_release_index_rejects_symlinks_forbidden_paths_and_non_utf8(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "linked.py").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes repository|non-symlink"):
        build_release_index(tmp_path, _manifest("linked.py"))

    (tmp_path / "bad.py").write_bytes(b"\xff")
    with pytest.raises(ValueError, match="not UTF-8"):
        build_release_index(tmp_path, _manifest("bad.py"))

    (tmp_path / "topology_map.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden"):
        build_release_index(tmp_path, _manifest("topology_map.json"))
