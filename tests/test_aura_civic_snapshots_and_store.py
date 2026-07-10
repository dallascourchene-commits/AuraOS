"""Tests for official snapshots and session store."""
from __future__ import annotations
from pathlib import Path
import sys, json, subprocess, tempfile, os
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestSnapshots:
    def test_list_snapshots(self):
        from aura_civic_snapshots import list_snapshots
        r = list_snapshots()
        assert r["ok"] is True
        assert len(r["snapshots"]) >= 7

    def test_load_snapshot(self):
        from aura_civic_snapshots import load_snapshot
        r = load_snapshot("winnipeg_bylaw_zoning")
        assert r["ok"] is True
        m = r["manifest"]
        assert m["evidence_class"] == "OFFICIAL_SNAPSHOT"
        assert m["publisher"] == "City of Winnipeg"
        assert m["licence"] != ""
        assert m["as_of"] != ""

    def test_digest_verification(self):
        from aura_civic_snapshots import verify_snapshot_digest
        r = verify_snapshot_digest("winnipeg_council_record")
        assert r["ok"] is True

    def test_synthetic_false(self):
        from aura_civic_snapshots import load_snapshot
        for sid in ["winnipeg_neighbourhood_boundaries", "manitoba_acts", "federal_acts", "stats_can_demographics"]:
            r = load_snapshot(sid)
            assert r["ok"] is True
            assert r["manifest"]["synthetic"] is False

    def test_known_limitations_present(self):
        from aura_civic_snapshots import load_snapshot
        r = load_snapshot("ourwinnipeg_plan")
        assert r["ok"] is True
        assert "known_limitations" in r["manifest"]
        assert r["manifest"]["known_limitations"] != ""

    def test_unknown_snapshot_fails(self):
        from aura_civic_snapshots import load_snapshot
        r = load_snapshot("nonexistent_snapshot")
        assert r["ok"] is False

    def test_all_snapshots_have_required_fields(self):
        from aura_civic_snapshots import list_snapshots, load_snapshot
        required = ["source_id", "publisher", "jurisdiction", "source_uri",
                    "as_of", "licence", "content_digest", "evidence_class",
                    "schema_version", "record_count", "geographic_scope"]
        r = list_snapshots()
        for snap in r["snapshots"]:
            sr = load_snapshot(snap["snapshot_id"])
            assert sr["ok"] is True
            for field in required:
                assert field in sr["manifest"], f"Missing {field} in {snap['snapshot_id']}"


class TestSessionStore:
    def test_create_and_retrieve(self, tmp_path):
        from aura_civic_session_store import CivicSessionStore
        store = CivicSessionStore.for_tests(str(tmp_path))
        session = {
            "session_id": "TEST-001", "objective": "test objective",
            "objective_hash": "abc123", "state": "CREATED",
            "profile_set": {"jurisdiction_profile_refs": ["winnipeg"]},
            "created_at": 1234.0, "fixture_mode": True,
            "contributions": [], "organ_receipts": [],
        }
        store.create_session(session)
        r = store.get_session("TEST-001")
        assert r["ok"] is True
        assert r["session"]["objective"] == "test objective"
        store.close()

    def test_update_session(self, tmp_path):
        from aura_civic_session_store import CivicSessionStore
        store = CivicSessionStore.for_tests(str(tmp_path))
        store.create_session({"session_id": "TEST-002", "objective": "test",
                              "objective_hash": "h", "state": "CREATED",
                              "profile_set": {}, "created_at": 1.0})
        store.update_session("TEST-002", {"state": "ANALYZING", "workstreams": [{"id": "w1"}]})
        r = store.get_session("TEST-002")
        assert r["session"]["state"] == "ANALYZING"
        assert len(r["session"]["workstreams"]) == 1
        store.close()

    def test_cross_process_persistence(self, tmp_path):
        """Create in one process, retrieve in another."""
        db_path = tmp_path / "cross.sqlite3"
        repo_str = str(REPO_ROOT).replace("\\", "/")
        db_str = str(db_path).replace("\\", "/")
        script1 = tmp_path / "create.py"
        script1.write_text(f'''
import sys; sys.path.insert(0, r"{repo_str}")
from aura_civic_session_store import CivicSessionStore
s = CivicSessionStore(r"{db_str}")
s.create_session({{"session_id": "XPROC-001", "objective": "cross process", "objective_hash": "x", "state": "CREATED", "profile_set": {{}}, "created_at": 1.0}})
s.close()
print("created")
''')
        r1 = subprocess.run([sys.executable, str(script1)], capture_output=True, text=True, timeout=30)
        assert r1.returncode == 0, r1.stderr[:200]

        script2 = tmp_path / "retrieve.py"
        script2.write_text(f'''
import sys; sys.path.insert(0, r"{repo_str}")
from aura_civic_session_store import CivicSessionStore
s = CivicSessionStore(r"{db_str}")
r = s.get_session("XPROC-001")
print(r["ok"])
s.close()
''')
        r2 = subprocess.run([sys.executable, str(script2)], capture_output=True, text=True, timeout=30)
        assert "True" in r2.stdout, f"Cross-process failed: {r2.stderr[:200]}"

    def test_restart_retrieves_history(self, tmp_path):
        from aura_civic_session_store import CivicSessionStore
        db_path = str(tmp_path / "restart.sqlite3")
        store1 = CivicSessionStore(db_path)
        store1.create_session({"session_id": "RESTART-001", "objective": "restart test",
                               "objective_hash": "r", "state": "CREATED",
                               "profile_set": {}, "created_at": 1.0})
        store1.close()
        # Reopen
        store2 = CivicSessionStore(db_path)
        r = store2.get_session("RESTART-001")
        assert r["ok"] is True
        assert r["session"]["objective"] == "restart test"
        store2.close()


class TestCivicAPI:
    """Test the Civic API dispatcher without sockets."""

    def test_status_endpoint(self):
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        parsed = urlparse("/api/civic/status")
        code, data = _handle_civic_api("GET", "/api/civic/status", parsed, {})
        assert code == 200
        assert data["ok"] is True
        assert data["civic_available"] is True

    def test_create_session_endpoint(self):
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        parsed = urlparse("/api/civic/sessions")
        code, data = _handle_civic_api("POST", "/api/civic/sessions", parsed, {"objective": "test API"})
        assert code == 200
        assert data["ok"] is True
        assert data["session"]["session_id"].startswith("CIVIC-")

    def test_get_session_endpoint(self):
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        # First create
        parsed_create = urlparse("/api/civic/sessions")
        _, data = _handle_civic_api("POST", "/api/civic/sessions", parsed_create, {"objective": "test get"})
        sid = data["session"]["session_id"]
        # Then get
        parsed_get = urlparse(f"/api/civic/sessions/{sid}")
        code, result = _handle_civic_api("GET", f"/api/civic/sessions/{sid}", parsed_get, {})
        assert code == 200
        assert result["ok"] is True

    def test_unknown_route_404(self):
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        parsed = urlparse("/api/civic/unknown")
        code, _ = _handle_civic_api("GET", "/api/civic/unknown", parsed, {})
        assert code == 404

    def test_no_prohibited_actions_in_api(self):
        """Verify the API has no endpoints for prohibited actions."""
        from aura_human_agent_arena_server import _handle_civic_api
        from urllib.parse import urlparse
        # Try to submit to government — should not be a route
        parsed = urlparse("/api/civic/sessions/TEST/submit-government")
        code, _ = _handle_civic_api("POST", "/api/civic/sessions/TEST/submit-government", parsed, {})
        assert code == 404
