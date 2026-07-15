from __future__ import annotations

import hashlib
from pathlib import Path

import aura_substrate_verifier as verifier
from aura_event_contracts import canonical_json
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


def _manifest(data: bytes, *, symbols=("PublicThing",), versions=(("VERSION", "V1"),)) -> SubstrateManifest:
    record = SubstrateFileRecord(
        "contract.py",
        FileRole.CANONICAL_CONTRACT,
        ("P1",),
        public_symbols=symbols,
        version_bindings=versions,
        expected_git_blob_sha1=_blob(data),
    )
    phase = PhaseDisposition(
        phase_id="P1",
        title="test phase",
        source_pr=1,
        merge_commit="0" * 40,
        component_paths=("contract.py",),
        dependencies=(),
        evidence_paths=("evidence.md",),
        retained_dependency_paths=(),
        contract_status=ContractStatus.CANONICAL,
        compatibility_mode=CompatibilityMode.ADDITIVE,
        migration_status=MigrationStatus.CANONICAL_CONTRACT_ADOPTED,
        live_owner="test owner",
        ownership_disposition="RETAIN_TEST_OWNER",
    )
    return SubstrateManifest(files=(record,), phases=(phase,))


def _prepare(tmp_path: Path, monkeypatch, source: bytes, manifest: SubstrateManifest) -> None:
    (tmp_path / "contract.py").write_bytes(source)
    (tmp_path / "evidence.md").write_text("evidence\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(canonical_json(manifest.to_dict()) + "\n", encoding="utf-8")
    index = build_release_index(tmp_path, manifest)
    (tmp_path / "index.json").write_text(canonical_json(index) + "\n", encoding="utf-8")
    monkeypatch.setattr(verifier, "build_substrate_manifest", lambda: manifest)
    monkeypatch.setattr(verifier, "_verify_git_history", lambda *_args: None)


def test_verifier_accepts_exact_manifest_symbols_versions_and_index(tmp_path: Path, monkeypatch) -> None:
    source = b'VERSION = "V1"\nclass PublicThing:\n    pass\n'
    manifest = _manifest(source)
    _prepare(tmp_path, monkeypatch, source, manifest)
    report = verifier.verify_substrate_release(tmp_path, "manifest.json", "index.json")
    assert report.passed is True
    assert report.checked_symbols == 1
    assert report.checked_versions == 1


def test_verifier_detects_digest_symbol_version_dependency_and_index_drift(tmp_path: Path, monkeypatch) -> None:
    original = b'VERSION = "V1"\nclass PublicThing:\n    pass\n'
    manifest = _manifest(original)
    changed = b'import aura_untracked\nVERSION = "V2"\nclass Replacement:\n    pass\n'
    _prepare(tmp_path, monkeypatch, changed, manifest)
    (tmp_path / "index.json").write_text("{}\n", encoding="utf-8")
    report = verifier.verify_substrate_release(tmp_path, "manifest.json", "index.json")
    codes = {item.code for item in report.findings}
    assert {
        "PINNED_FILE_DIGEST_MISMATCH",
        "PUBLIC_SYMBOL_MISSING",
        "VERSION_BINDING_MISMATCH",
        "UNDECLARED_AURA_DEPENDENCY",
        "RELEASE_INDEX_CONTENT_MISMATCH",
    } <= codes
    assert report.passed is False
