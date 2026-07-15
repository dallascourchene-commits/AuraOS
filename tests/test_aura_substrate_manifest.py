from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aura_event_contracts import canonical_json
from aura_substrate_manifest import build_substrate_manifest
from aura_substrate_release import build_manifest_artifacts

ROOT = Path(__file__).resolve().parents[1]


def test_phase_ledger_order_and_dispositions() -> None:
    manifest = build_substrate_manifest()
    assert tuple(item.phase_id for item in manifest.phases) == (
        "P1", "P1.1", "P2.1", "P2.2", "P2.3", "P3.1", "P3.2",
        "P4.1", "P5.1", "P5.2", "P5.3", "P6.1", "P6.2", "P7", "P8",
    )
    dispositions = {item.phase_id: item.ownership_disposition for item in manifest.phases}
    assert dispositions["P5.3"] == "RETAIN_V1"
    assert dispositions["P6.2"] == "RETAIN_LEGACY_DUAL_READ"
    assert dispositions["P7"] == "RETAIN_CODING_ARENA_OWNER"
    assert dispositions["P8"] == "RETAIN_CIVIC_COMMONS_OWNER"
    assert all(not item.live_owner_changed for item in manifest.phases)
    assert all(not item.execution_authority_granted for item in manifest.phases)
    assert manifest.retained_external_surfaces == ("aura_substrate.py",)


def test_release_file_ledger_is_sorted_and_bounded() -> None:
    manifest = build_substrate_manifest()
    paths = tuple(item.path for item in manifest.files)
    assert paths == tuple(sorted(set(paths)))
    assert len(paths) == 38
    assert "aura_substrate.py" not in paths
    assert not any(path.startswith(("tests/", ".github/", ".aura/")) for path in paths)
    assert "topology_map.json" not in paths
    assert not any(path.endswith((".db", ".jsonl", ".sqlite")) for path in paths)


def test_committed_multipart_manifest_matches_builder() -> None:
    expected_receipt, expected_parts = build_manifest_artifacts(build_substrate_manifest())
    receipt_path = ROOT / "docs/aura_substrate_manifest.v1.json"
    receipt_text = receipt_path.read_text(encoding="utf-8")
    receipt = json.loads(receipt_text)
    assert receipt_text == canonical_json(receipt) + "\n"
    assert receipt == expected_receipt

    for relative, expected_payload in expected_parts:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
        assert text == canonical_json(payload) + "\n"
        assert payload == expected_payload
        expected_part = next(item for item in receipt["parts"] if item["path"] == relative)
        assert len(text.encode("utf-8")) == expected_part["byte_length"]
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == expected_part["sha256"]
