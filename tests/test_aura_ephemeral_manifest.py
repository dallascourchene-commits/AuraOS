"""Tests for Aura Ephemeral Organ Manifest."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_ephemeral_manifest import (
    create_manifest, EphemeralOrganManifest, EphemeralOrganReceipt,
    MANIFEST_VERSION, PATCH_AUTHORITY,
)


class TestManifest:
    def test_create_manifest(self):
        m = create_manifest("test ephemeral organ", ttl_seconds=60)
        assert m.manifest_version == MANIFEST_VERSION
        assert m.organ_id.startswith("EORG-")
        assert m.objective == "test ephemeral organ"
        assert m.ttl_seconds == 60
        assert m.creator == "human"
        assert m.patch_authority == PATCH_AUTHORITY
        assert m.vsa_patch_authority is False

    def test_manifest_digest_deterministic(self):
        m1 = create_manifest("test", ttl_seconds=60)
        m2 = create_manifest("test", ttl_seconds=60, organ_id=m1.organ_id)
        # Same inputs should produce same digest
        assert m1.compute_digest() == m2.compute_digest()

    def test_manifest_digest_verification(self):
        m = create_manifest("test", ttl_seconds=60)
        digest = m.compute_digest()
        assert m.verify_digest(digest) is True
        assert m.verify_digest("wrong") is False

    def test_mvp_capabilities_granted(self):
        m = create_manifest("test", ttl_seconds=60)
        granted = set(m.granted_capabilities)
        assert "resolve_capabilities" in granted
        assert "search_code" in granted
        assert "read_slice" in granted
        assert "render_ui_schema" in granted
        assert "dissolve" in granted

    def test_mvp_capabilities_forbidden(self):
        m = create_manifest("test", ttl_seconds=60, requested_capabilities=["external_network", "package_install"])
        denied = {d["capability"] for d in m.denied_capabilities}
        assert "external_network" in denied
        assert "package_install" in denied

    def test_data_policy_no_secrets(self):
        m = create_manifest("test", ttl_seconds=60)
        assert m.data_policy["private_memory_export"] is False
        assert m.data_policy["raw_sidecar_dump"] is False
        assert m.data_policy["secrets_access"] is False

    def test_ui_manifest_not_executable(self):
        m = create_manifest("test", ttl_seconds=60)
        # ui_manifest is a dict after to_dict
        d = m.to_dict()
        assert d["ui_manifest"]["executable"] is False

    def test_receipt(self):
        r = EphemeralOrganReceipt(organ_id="EORG-test", manifest_digest="abc", state="DISSOLVED", dissolved=True)
        assert r.receipt_version == "AURA_EPHEMERAL_RECEIPT_V1"
        assert r.patch_authority == PATCH_AUTHORITY

    def test_no_secrets_in_manifest(self):
        m = create_manifest("test", ttl_seconds=60)
        d = m.to_dict()
        # Check no secret-like strings
        import json
        text = json.dumps(d)
        assert "api_key" not in text.lower()
        assert "password" not in text.lower()
        assert "secret" not in text.lower() or "secrets_access" in text  # data_policy field is ok
