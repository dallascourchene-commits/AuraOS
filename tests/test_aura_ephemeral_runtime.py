"""Tests for Aura Ephemeral Runtime — end-to-end."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_ephemeral_runtime import (
    plan_ephemeral_organ, validate_ephemeral_organ, run_ephemeral_organ,
    ephemeral_status, dissolve_ephemeral_organ, ephemeral_receipt,
)
from aura_ephemeral_registry import get_registry
from aura_ephemeral_lifecycle import EphemeralState


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before each test."""
    reg = get_registry()
    reg._organs.clear()
    yield
    reg._organs.clear()


class TestPlanAndValidate:
    def test_plan_ephemeral_organ(self):
        result = plan_ephemeral_organ("test ephemeral investigation", ttl_seconds=60, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["organ_id"].startswith("EORG-")
        assert result["manifest_digest"] != ""
        assert result["state"] == "DRAFTED"
        assert "capability_resolution" in result
        assert "lexc_route" in result

    def test_validate_ephemeral_organ(self):
        plan = plan_ephemeral_organ("test", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        result = validate_ephemeral_organ(organ_id, repo_root=REPO_ROOT, human_approval=True)
        assert "product_automaton" in result

    def test_validate_nonexistent_organ(self):
        result = validate_ephemeral_organ("nonexistent", repo_root=REPO_ROOT)
        assert result["ok"] is False


class TestRunAndDissolve:
    def test_full_e2e_run(self):
        """End-to-end: plan → run → dissolve → receipt."""
        # Plan
        plan = plan_ephemeral_organ("show every existing Aura function relevant to ephemeral apps", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        assert plan["ok"] is True

        # Run (includes sandbox, execution, verification, dissolution)
        result = run_ephemeral_organ(organ_id, repo_root=REPO_ROOT, human_approval=True)
        assert result["ok"] is True
        assert result["verifier_passed"] is True
        assert result["dissolution"]["capabilities_revoked"] is True
        assert result["dissolution"]["temp_dir_removed"] is True
        assert result["dissolution"]["dissolution_verified"] is True
        assert result["state"] == "DISSOLVED"

    def test_dissolution_receipt(self):
        plan = plan_ephemeral_organ("test", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        run_ephemeral_organ(organ_id, repo_root=REPO_ROOT, human_approval=True)
        receipt = ephemeral_receipt(organ_id)
        assert receipt["ok"] is True
        assert receipt["receipt"]["dissolved"] is True
        assert receipt["receipt"]["temp_dir_removed"] is True

    def test_capabilities_revoked_after_dissolution(self):
        plan = plan_ephemeral_organ("test", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        run_ephemeral_organ(organ_id, repo_root=REPO_ROOT, human_approval=True)
        status = ephemeral_status(organ_id)
        assert status["organ"]["state"] == "DISSOLVED"
        assert bool(status["organ"]["dissolution_receipt"]) is True

    def test_no_production_file_mutation(self):
        """E2E must not mutate production files."""
        import hashlib
        # Hash a production file before
        prod_file = REPO_ROOT / "aura_lexc.py"
        before = hashlib.blake2b(prod_file.read_bytes(), digest_size=8).hexdigest()
        # Run ephemeral organ
        plan = plan_ephemeral_organ("test no mutation", ttl_seconds=60, repo_root=REPO_ROOT)
        run_ephemeral_organ(plan["organ_id"], repo_root=REPO_ROOT, human_approval=True)
        # Hash after
        after = hashlib.blake2b(prod_file.read_bytes(), digest_size=8).hexdigest()
        assert before == after

    def test_manual_dissolve(self):
        plan = plan_ephemeral_organ("test manual dissolve", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        result = dissolve_ephemeral_organ(organ_id)
        assert result["ok"] is True
        assert result["receipt"]["dissolved"] is True

    def test_invariants_preserved(self):
        plan = plan_ephemeral_organ("test invariants", ttl_seconds=60, repo_root=REPO_ROOT)
        organ_id = plan["organ_id"]
        result = run_ephemeral_organ(organ_id, repo_root=REPO_ROOT, human_approval=True)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_registry_audit_export(self):
        from aura_ephemeral_registry import get_registry
        plan = plan_ephemeral_organ("test audit", ttl_seconds=60, repo_root=REPO_ROOT)
        run_ephemeral_organ(plan["organ_id"], repo_root=REPO_ROOT, human_approval=True)
        reg = get_registry()
        audit = reg.export_audit()
        assert audit["ok"] is True
        assert audit["count"] > 0
        # No secrets in audit
        import json
        text = json.dumps(audit)
        assert "api_key" not in text.lower()
        assert "password" not in text.lower()

    def test_expired_organ_detection(self):
        from aura_ephemeral_registry import get_registry, EphemeralOrganRecord
        import time
        reg = get_registry()
        reg.register(EphemeralOrganRecord(
            organ_id="EORG-expired", manifest_digest="x", state="RUNNING",
            created_at=time.time() - 1000, expires_at=time.time() - 1,
        ))
        expired = reg.check_expired()
        assert "EORG-expired" in expired["expired_organ_ids"]
