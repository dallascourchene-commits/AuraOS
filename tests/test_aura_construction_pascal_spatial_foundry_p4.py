from __future__ import annotations

import hashlib
import json
import pytest
import shutil
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace


import aura_construction_pascal_spatial_foundry_p4_server as p4
from aura_construction_foundry_director import (
    ConstructionFoundryDirector,
    RequiredAsset,
    build_default_manifest,
)


def _run(root: Path, *args: str) -> str:
    return subprocess.run(
        [*args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout.strip()


def _git_repo(root: Path) -> None:
    _run(root, "git", "init")
    _run(root, "git", "config", "user.email", "tests@example.com")
    _run(root, "git", "config", "user.name", "AuraOS Tests")
    _run(root, "git", "add", ".")
    _run(root, "git", "commit", "-m", "fixture")


def _decoded(response):
    return response[0], json.loads(response[2].decode("utf-8"))


def _manifest():
    assets = (
        RequiredAsset("profile.json", hashlib.sha256(b"profile").hexdigest()),
        RequiredAsset("confirmation.json", hashlib.sha256(b"confirmation").hexdigest()),
    )
    return build_default_manifest(
        assets,
        runtime_profile_path=assets[0].path,
        confirmation_packet_path=assets[1].path,
    )


# Shared fixture for tests that need a P3 state with P4 members attached.
# This is NOT a real P4FoundryShowcaseState — it uses a P3FoundryShowcaseState
# with P4 attributes grafted on, mirroring the inheritance that P4 applies
# in production but without the full P4 lifecycle.
_P4_INITIAL_EVIDENCE = {
    "p3_available": True, "construction_identity_bound": True,
    "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
    "as_built_scene_bound": True, "compare_receipt_bound": True,
    "construction_candidates_bound": True, "domain_decision_bound": True,
    "identity_current": True, "operator_authorized": True,
    "fault_fixture_bound": True, "required_assets_bound": True,
    "rollback_adapter_ready": True, "u7_bridge_ready": True,
    "construction_state_unchanged": True, "capture_resources_dissolved": True,
}


@pytest.fixture
def p4_test_state(monkeypatch):
    """Return (state, director, ident_digest) for P3+P4 sync tests.

    Uses a P3FoundryShowcaseState with P4 members attached — NOT a real
    P4FoundryShowcaseState.  The _p4_runtime_lock is not created, so
    routes that acquire it are not reachable from this fixture.
    """
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = hashlib.sha256(b"fixture-identity").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        yield state, director, ident_digest
    finally:
        state.close()


def test_status_preserves_p3_fallback_when_p4_is_unavailable(monkeypatch):
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    state = SimpleNamespace(
        p4_available=False,
        p4_load_error="exact P4 identity unavailable",
        p3_available=True,
        p4_director=None,
    )
    status, payload = _decoded(
        p4.dispatch_p4_foundry_request(
            state,
            "GET",
            "/api/construction/director/status",
        )
    )
    assert status == 503
    assert payload["ok"] is False
    assert payload["p3_fallback_available"] is True
    assert payload["manifest_digest"] == ""
    assert payload["physical_work_authorized"] is False


def test_static_injection_is_retained_bounded_and_idempotent(monkeypatch):
    source = b"<html><head></head><body><section id=\"construction-decision-foundry\"></section></body></html>"
    monkeypatch.setattr(p4, "p3_static_response", lambda _route, _state: (200, "text/html; charset=utf-8", source))
    state = SimpleNamespace(p4_available=True, p4_static_assets={})
    first = p4._static_response("/", state)
    assert first[0] == 200
    assert first[2].count(b"construction-foundry-director.css") == 1
    assert first[2].count(b'id="construction-foundry-director"') == 1
    assert first[2].count(b"construction-foundry-director.js") == 1

    monkeypatch.setattr(p4, "p3_static_response", lambda _route, _state: first)
    second = p4._static_response("/", state)
    assert second[2] == first[2]


def test_confirmation_bundle_is_exact_head_bound_and_external(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".aura/runtime_profiles").mkdir(parents=True)
    (root / "tests/runtime").mkdir(parents=True)
    (root / ".aura/CODEMAP.md").write_text("# exact codemap\n", encoding="utf-8")
    verifier_body = b"console.log('verified');\n"
    (root / p4._VERIFIER_SOURCE).write_bytes(verifier_body)
    profile = {
        "profile_id": "p4-test-profile",
        "allowed_paths": [
            ".aura/runtime_profiles/construction_demo_bilateral.v2.json",
            ".aura/CODEMAP.md",
            p4._VERIFIER_SOURCE,
        ],
        "independent_verifier": {
            "source_path": p4._VERIFIER_SOURCE,
            "source_sha256": hashlib.sha256(verifier_body).hexdigest(),
            "verifier_id": "p4-test-verifier",
        },
    }
    (root / p4._RUNTIME_PROFILE).write_text(json.dumps(profile), encoding="utf-8")
    _git_repo(root)

    identity, confirmation_path, output_dir = p4._compile_confirmation_bundle(root)
    try:
        head = _run(root, "git", "rev-parse", "HEAD")
        tree = _run(root, "git", "rev-parse", "HEAD^{tree}")
        assert identity.repository_head == head
        assert identity.source_tree_digest == tree
        assert identity.verifier_source_digest == hashlib.sha256(verifier_body).hexdigest()
        assert confirmation_path.is_file()
        assert root not in confirmation_path.parents
        assert root not in output_dir.parents
        packet = json.loads(confirmation_path.read_text(encoding="utf-8"))
        assert identity.intent_digest == p4._bilateral_identity_digest(
            packet["intent_packet"]["intent_digest"], "intent digest"
        )
        assert identity.semantic_ledger_digest == p4._bilateral_identity_digest(
            packet["semantic_ledger"]["ledger_digest"], "Semantic Ledger digest"
        )
        assert identity.guardrail_set_digest == p4._bilateral_identity_digest(
            packet["confirmation_receipt"]["guardrail_set_digest"], "guardrail-set digest"
        )
        assert packet["confirmation_receipt"]["repository_head"] == head
        assert packet["u7_references"]["proposal_only"] is True
        assert packet["u7_references"]["current_reproof_required_before_learning"] is True
    finally:
        shutil.rmtree(confirmation_path.parent, ignore_errors=True)


def test_canonical_compiler_digest_projection_is_exact_and_namespaced():
    canonical = "a" * 32
    intent = p4._bilateral_identity_digest(canonical, "intent_digest")
    ledger = p4._bilateral_identity_digest(canonical, "semantic_ledger_digest")
    assert len(intent) == 64
    assert len(ledger) == 64
    assert intent != ledger
    assert p4._bilateral_identity_digest("b" * 40, "repository_head") == "b" * 40


def test_runtime_proof_adapter_retains_canonical_contract_and_required_assets(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    asset_path = root / "asset.js"
    asset_path.write_text("exact asset\n", encoding="utf-8")
    asset = RequiredAsset("asset.js", hashlib.sha256(asset_path.read_bytes()).hexdigest())
    canonical_contract = {
        "intent_digest": "1" * 32,
        "semantic_ledger_digest": "2" * 32,
        "guardrail_set_digest": "3" * 32,
        "confirmation_digest": "intent-confirmation_fixture",
        "intent_revision_status": "NOT_CREATED_NO_POST_CONFIRMATION_DRIFT",
        "expected_repository_head": "4" * 40,
        "expected_source_tree": "5" * 40,
    }
    confirmation = root.parent / "confirmation.json"
    confirmation.write_text(json.dumps({
        "intent_packet": {"intent_digest": canonical_contract["intent_digest"]},
        "semantic_ledger": {"ledger_digest": canonical_contract["semantic_ledger_digest"]},
        "confirmation_receipt": {
            "confirmation_id": canonical_contract["confirmation_digest"],
            "guardrail_set_digest": canonical_contract["guardrail_set_digest"],
            "repository_head": canonical_contract["expected_repository_head"],
            "source_tree_digest": canonical_contract["expected_source_tree"],
        },
        "u7_references": {
            "intent_revision_status": canonical_contract["intent_revision_status"],
        },
    }), encoding="utf-8")
    identity = p4.BilateralIdentity(
        intent_digest=p4._bilateral_identity_digest("1" * 32, "intent digest"),
        confirmation_digest=canonical_contract["confirmation_digest"],
        semantic_ledger_digest=p4._bilateral_identity_digest(
            "2" * 32, "Semantic Ledger digest"
        ),
        guardrail_set_digest=p4._bilateral_identity_digest(
            "3" * 32, "guardrail-set digest"
        ),
        intent_revision_id=canonical_contract["intent_revision_status"],
        repository_head=canonical_contract["expected_repository_head"],
        source_tree_digest=canonical_contract["expected_source_tree"],
        runtime_profile_digest="6" * 64,
        verifier_id="verifier",
        verifier_source_digest="7" * 64,
    )
    runtime_output = tmp_path / "runtime-output"
    runtime_output.mkdir()
    proof = {
        "ok": True,
        "intent_contract": canonical_contract,
        "required_trace_artifacts": [],
        "proof_digest": "8" * 64,
        "proof_path": str(runtime_output / "bilateral_runtime_proof.json"),
        "output_dir": str(runtime_output),
    }
    projected = p4._adapt_runtime_proof_identity(
        proof,
        identity=identity,
        confirmation_path=confirmation,
        repo_root=root,
        required_assets=(asset,),
    )
    assert projected["canonical_intent_contract"] == canonical_contract
    assert projected["intent_contract"]["intent_digest"] == identity.intent_digest
    assert projected["identity_adapter"]["verification_owner_changed"] is False
    assert any(row["path"] == "asset.js" for row in projected["required_trace_artifacts"])
    canonical = {
        key: value
        for key, value in projected.items()
        if key not in {"proof_digest", "proof_path", "output_dir"}
    }
    assert projected["proof_digest"] == p4.runtime_binding_digest(canonical)
    assert Path(projected["proof_path"]).is_file()
    stored = json.loads(Path(projected["proof_path"]).read_text(encoding="utf-8"))
    assert stored["proof_digest"] == projected["proof_digest"]


def test_canonical_u7_bridge_compiles_exact_execution_binding(tmp_path: Path):
    root = tmp_path / "repo"
    for relative in (
        ".aura/CODEMAP.json",
        "aura_construction_pascal_spatial_foundry_p4_server.py",
        "aura_construction_foundry_director.py",
        "aura_construction_pascal_spatial_foundry_p3_server.py",
        "aura_construction_spatial_foundry.py",
        "tests/test_aura_construction_foundry_director.py",
        "tests/test_aura_construction_pascal_spatial_foundry_p4.py",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "def _execute_chapter():\n    return None\n" if relative.endswith("p4_server.py") else "# exact fixture\n"
        target.write_text(body, encoding="utf-8")
    _git_repo(root)
    bridge = p4._P4U7Bridge(root)
    now = time.time()
    bridge.prepare(
        phase="phase-p4",
        task_id="construction-foundry-p4-current-reproof",
        packet_digest=hashlib.sha256(b"packet").hexdigest(),
        candidate_digest=hashlib.sha256(b"candidate").hexdigest(),
        observed_at=now,
    )
    session = bridge._require_session("phase-p4")
    binding = session["unified_execution_bindings"]["construction-foundry-p4-current-reproof"]
    assert binding.authority["automatic_promotion"] is False
    assert binding.authority["production_mutation"] is False
    assert binding.records["model_execution_packet"]["repository_head"] == _run(root, "git", "rev-parse", "HEAD")


def test_u7_contracts_remain_proposal_only_and_human_pending():
    now = time.time()
    packet = hashlib.sha256(b"packet").hexdigest()
    candidate = hashlib.sha256(b"candidate").hexdigest()
    prediction = p4._p4_prediction_contract(now, packet, candidate)
    observation = p4._p4_observation_contract(now, packet, candidate)
    finalization = p4._p4_finalization_contract(now, packet, candidate)
    proposal = prediction["crucible_proposal"]
    assert proposal["change_path"] == "soft_weight_profile.empirical_uncertainty"
    assert proposal["validation"]["passed"] is True
    assert observation["observer_id"] != prediction["producer_id"]
    assert finalization["human_disposition"] == "NOT_REVIEWED"
    assert finalization["arena_id"] == "construction"
    assert finalization["storage"]["attempt_archive_db_path"].startswith("Aura_Memory/")


def test_available_status_projects_exact_manifest_without_authority(monkeypatch):
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    director = ConstructionFoundryDirector(_manifest())
    state = SimpleNamespace(
        p4_available=True,
        p4_load_error="",
        p3_available=True,
        p4_director=director,
    )
    status, payload = _decoded(
        p4.dispatch_p4_foundry_request(
            state,
            "GET",
            "/api/construction/director/status",
        )
    )
    assert status == 200
    assert payload["manifest_digest"] == director.manifest.manifest_digest
    assert payload["automatic_execution"] is False


def test_p3_sync_protocol_end_to_end(monkeypatch):
    """End-to-end test: prepare→project→confirm→ack clears the gate.

    Uses one real P4FoundryShowcaseState with shared mutable state —
    no copies between separate P3 and P4 state objects.
    """
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    import hashlib as _hl
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = _hl.sha256(b"e2e-identity").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    # Use one real P3FoundryShowcaseState as the shared state.
    # P4FoundryShowcaseState inherits from P3, so this mirrors production.
    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    # Attach P4-specific attributes.
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        session = director.start_session(
            identity_digest=ident_digest,
            construction_state_digest=_hl.sha256(b"e2e-state").hexdigest(),
            initial_evidence={
                "p3_available": True, "construction_identity_bound": True,
                "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
                "as_built_scene_bound": True, "compare_receipt_bound": True,
                "construction_candidates_bound": True, "domain_decision_bound": True,
                "identity_current": True, "operator_authorized": True,
                "fault_fixture_bound": True, "required_assets_bound": True,
                "rollback_adapter_ready": True, "u7_bridge_ready": True,
                "construction_state_unchanged": True, "capture_resources_dissolved": True,
            },
        )
        session_id = session["session_id"]

        claimed = director.claim_next(session_id)
        assert claimed["admitted"] is True
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=claimed["claim_token"],
        )
        sess = director.require_session(session_id)
        assert sess.p3_sync_pending is True, "first chapter must create sync gate"

        last_receipt = sess.receipts[-1]
        chapter_id = last_receipt.get("chapter_id")
        manifest_chapter = director.manifest.chapter(chapter_id)
        active_view = dict(manifest_chapter.ui_directive or {}).get("active_view")

        # Step 1: prepare-p3-sync.
        prep_status, _, prep_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/prepare-p3-sync",
            {"identity_handle": "e2e-handle"},
        )
        assert prep_status == 200
        prep = json.loads(prep_resp.decode())
        assert prep["ok"] is True
        assert prep["sync_nonce"]

        # Capture sync map identity AFTER prepare creates it.
        sync_map = state._p3_sync_nonces

        sync_key = f"{session_id}:{prep['director_receipt_digest']}"
        assert sync_map[sync_key]["state"] == "PREPARED"

        # Step 2: P3 /project via real dispatch.
        projection = state.require_p3().compile(active_view=active_view, timeline_day=14.0)
        exact_identity = {
            "state_digest": projection["domain"]["state_digest"],
            "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
            "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
            "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
            "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
        }
        proj_status, _, proj_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST",
            "/api/construction/decision-lane/project",
            {
                **exact_identity,
                "active_view": active_view,
                "timeline_day": 14.0,
                "identity_handle": "e2e-handle",
                "identity_digest": prep["identity_digest"],
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"],
                "sync_nonce": prep["sync_nonce"],
            },
            request_origin="http://127.0.0.1:8765",
            request_host="127.0.0.1:8765",
        )
        assert proj_status == 200, f"P3 project failed: {proj_resp.decode()[:200]}"
        proj = json.loads(proj_resp.decode())
        assert proj["ok"] is True
        assert proj["projection_digest"], "P3 project must return projection_digest"
        assert proj["presentation_revision"], "P3 project must return presentation_revision"
        assert "presentation_receipt_digest" not in proj or not proj.get("presentation_receipt_digest"), \
            "P3 project must NOT return presentation_receipt_digest"

        # Verify state transitioned to PROJECTED.
        assert sync_map[sync_key]["state"] == "PROJECTED"

        # Step 3: confirm-presentation (render_capability is looked up
        # server-side, not supplied by the caller).
        confirm_status, _, confirm_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST",
            "/api/construction/decision-lane/confirm-presentation",
            {
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"],
                "active_view": active_view,
                "identity_digest": prep["identity_digest"],
                "projection_digest": proj["projection_digest"],
                "presentation_revision": proj["presentation_revision"],
            },
            request_origin="http://127.0.0.1:8765",
            request_host="127.0.0.1:8765",
        )
        assert confirm_status == 200, f"confirm failed: {confirm_resp.decode()[:200]}"
        confirm = json.loads(confirm_resp.decode())
        assert confirm["ok"] is True
        assert confirm["presentation_receipt_digest"], "confirm must return presentation_receipt_digest"

        # Verify state transitioned to RENDER_CONFIRMED.
        assert sync_map[sync_key]["state"] == "RENDER_CONFIRMED"

        # Verify the SAME sync map was mutated (no copies).
        assert state._p3_sync_nonces is sync_map
        assert sync_key in state._p3_retained_presentation

        # Step 4: ack-p3-sync.
        ack_status, _, ack_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/ack-p3-sync",
            {
                "identity_handle": "e2e-handle",
                "presentation_receipt": {
                    "chapter_id": chapter_id,
                    "active_view": active_view,
                    "receipt_digest": confirm["presentation_receipt_digest"],
                },
            },
        )
        assert ack_status == 200, f"ack failed: {ack_resp.decode()[:200]}"
        ack = json.loads(ack_resp.decode())
        assert ack["ok"] is True
        assert ack["session"]["p3_sync_pending"] is False

        # Verify state transitioned to ACKNOWLEDGED.
        assert sync_map[sync_key]["state"] == "ACKNOWLEDGED"

        # Step 5: Next transition is admitted.
        next_claim = director.claim_next(session_id)
        assert next_claim["admitted"] is True
    finally:
        state.close()


def test_p3_sync_protocol_rejects_ack_without_render_confirmation(monkeypatch):
    """Critical negative: prepare→project→ack (skip confirm) must fail."""
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    import hashlib as _hl
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = _hl.sha256(b"e2e-skip").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        session = director.start_session(
            identity_digest=ident_digest,
            construction_state_digest=_hl.sha256(b"e2e-skip-state").hexdigest(),
            initial_evidence={
                "p3_available": True, "construction_identity_bound": True,
                "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
                "as_built_scene_bound": True, "compare_receipt_bound": True,
                "construction_candidates_bound": True, "domain_decision_bound": True,
                "identity_current": True, "operator_authorized": True,
                "fault_fixture_bound": True, "required_assets_bound": True,
                "rollback_adapter_ready": True, "u7_bridge_ready": True,
                "construction_state_unchanged": True, "capture_resources_dissolved": True,
            },
        )
        session_id = session["session_id"]
        claimed = director.claim_next(session_id)
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=claimed["claim_token"],
        )
        assert director.require_session(session_id).p3_sync_pending is True

        # prepare
        prep_status, _, prep_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/prepare-p3-sync",
            {"identity_handle": "e2e-skip"},
        )
        assert prep_status == 200
        prep = json.loads(prep_resp.decode())

        # project
        sess = director.require_session(session_id)
        chapter_id = sess.receipts[-1].get("chapter_id")
        active_view = dict(director.manifest.chapter(chapter_id).ui_directive or {}).get("active_view")
        projection = state.require_p3().compile(active_view=active_view, timeline_day=14.0)
        exact_identity = {
            "state_digest": projection["domain"]["state_digest"],
            "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
            "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
            "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
            "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
        }
        proj_status, _, proj_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/project",
            {
                **exact_identity, "active_view": active_view, "timeline_day": 14.0,
                "identity_handle": "e2e-skip", "identity_digest": prep["identity_digest"],
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"], "sync_nonce": prep["sync_nonce"],
            },
            request_origin="http://127.0.0.1:8765", request_host="127.0.0.1:8765",
        )
        assert proj_status == 200
        proj = json.loads(proj_resp.decode())
        assert proj["projection_digest"]

        sync_key = f"{session_id}:{prep['director_receipt_digest']}"
        assert state._p3_sync_nonces[sync_key]["state"] == "PROJECTED"

        # Try ack WITHOUT confirm-presentation — must fail.
        ack_status, _, ack_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/ack-p3-sync",
            {
                "identity_handle": "e2e-skip",
                "presentation_receipt": {
                    "chapter_id": chapter_id, "active_view": active_view,
                    "receipt_digest": "forged-attempt",
                },
            },
        )
        assert ack_status == 409, f"ack must fail with 409 when state is PROJECTED, not RENDER_CONFIRMED: {ack_resp.decode()[:200]}"
        assert director.require_session(session_id).p3_sync_pending is True
        assert state._p3_sync_nonces[sync_key]["state"] == "PROJECTED"
    finally:
        state.close()


def test_confirm_presentation_rejects_without_project(monkeypatch):
    """Negative: confirm-presentation without prior P3 /project must fail."""
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    import hashlib as _hl
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = _hl.sha256(b"e2e-no-project").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        session = director.start_session(
            identity_digest=ident_digest,
            construction_state_digest=_hl.sha256(b"e2e-no-project-state").hexdigest(),
            initial_evidence={
                "p3_available": True, "construction_identity_bound": True,
                "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
                "as_built_scene_bound": True, "compare_receipt_bound": True,
                "construction_candidates_bound": True, "domain_decision_bound": True,
                "identity_current": True, "operator_authorized": True,
                "fault_fixture_bound": True, "required_assets_bound": True,
                "rollback_adapter_ready": True, "u7_bridge_ready": True,
                "construction_state_unchanged": True, "capture_resources_dissolved": True,
            },
        )
        session_id = session["session_id"]
        claimed = director.claim_next(session_id)
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=claimed["claim_token"],
        )
        assert director.require_session(session_id).p3_sync_pending is True

        # prepare only — no project.
        prep_status, _, prep_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/prepare-p3-sync",
            {"identity_handle": "e2e-no-project"},
        )
        assert prep_status == 200
        prep = json.loads(prep_resp.decode())

        # Try confirm-presentation without project — sync record is PREPARED.
        confirm_status, _, confirm_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST",
            "/api/construction/decision-lane/confirm-presentation",
            {
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"],
                "active_view": prep["active_view"],
                "identity_digest": prep["identity_digest"],
                "projection_digest": "forged",
                "presentation_revision": "forged",
            },
            request_origin="http://127.0.0.1:8765",
            request_host="127.0.0.1:8765",
        )
        assert confirm_status == 409, f"confirm must fail with 409 when state is PREPARED, not PROJECTED: {confirm_resp.decode()[:200]}"
        assert director.require_session(session_id).p3_sync_pending is True
        sync_key = f"{session_id}:{prep['director_receipt_digest']}"
        assert state._p3_sync_nonces[sync_key]["state"] == "PREPARED"
    finally:
        state.close()


def test_confirm_presentation_rejects_duplicate(monkeypatch):
    """Negative: double confirm-presentation must fail on second call."""
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    import hashlib as _hl
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = _hl.sha256(b"e2e-double-confirm").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        session = director.start_session(
            identity_digest=ident_digest,
            construction_state_digest=_hl.sha256(b"e2e-double-confirm-state").hexdigest(),
            initial_evidence={
                "p3_available": True, "construction_identity_bound": True,
                "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
                "as_built_scene_bound": True, "compare_receipt_bound": True,
                "construction_candidates_bound": True, "domain_decision_bound": True,
                "identity_current": True, "operator_authorized": True,
                "fault_fixture_bound": True, "required_assets_bound": True,
                "rollback_adapter_ready": True, "u7_bridge_ready": True,
                "construction_state_unchanged": True, "capture_resources_dissolved": True,
            },
        )
        session_id = session["session_id"]
        claimed = director.claim_next(session_id)
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=claimed["claim_token"],
        )
        assert director.require_session(session_id).p3_sync_pending is True

        # prepare + project
        prep_status, _, prep_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/prepare-p3-sync",
            {"identity_handle": "e2e-double-confirm"},
        )
        assert prep_status == 200
        prep = json.loads(prep_resp.decode())

        sess = director.require_session(session_id)
        chapter_id = sess.receipts[-1].get("chapter_id")
        active_view = dict(director.manifest.chapter(chapter_id).ui_directive or {}).get("active_view")
        projection = state.require_p3().compile(active_view=active_view, timeline_day=14.0)
        exact_identity = {
            "state_digest": projection["domain"]["state_digest"],
            "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
            "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
            "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
            "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
        }
        proj_status, _, proj_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/project",
            {
                **exact_identity, "active_view": active_view, "timeline_day": 14.0,
                "identity_handle": "e2e-double-confirm", "identity_digest": prep["identity_digest"],
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"], "sync_nonce": prep["sync_nonce"],
            },
            request_origin="http://127.0.0.1:8765", request_host="127.0.0.1:8765",
        )
        assert proj_status == 200
        proj = json.loads(proj_resp.decode())

        # First confirm — should succeed (render_capability looked up server-side).
        confirm_body = {
            "director_session_id": prep["director_session_id"],
            "director_receipt_digest": prep["director_receipt_digest"],
            "chapter_id": prep["chapter_id"],
            "active_view": active_view,
            "identity_digest": prep["identity_digest"],
            "projection_digest": proj["projection_digest"],
            "presentation_revision": proj["presentation_revision"],
        }
        c1_status, _, _ = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/confirm-presentation",
            confirm_body, request_origin="http://127.0.0.1:8765", request_host="127.0.0.1:8765",
        )
        assert c1_status == 200

        # Second confirm — must fail (state is RENDER_CONFIRMED, not PROJECTED).
        c2_status, _, c2_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/confirm-presentation",
            confirm_body, request_origin="http://127.0.0.1:8765", request_host="127.0.0.1:8765",
        )
        assert c2_status == 409, f"duplicate confirm must return 409: {c2_resp.decode()[:200]}"
        assert "RENDER_CONFIRMED" in c2_resp.decode()
        assert director.require_session(session_id).p3_sync_pending is True
    finally:
        state.close()


def test_anti_replay_ordering_allows_direct_sequence_without_renderer_proof(monkeypatch):
    """Trust Model A: prepare→project→confirm→ack succeeds via direct API.

    See docs/AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_P4.md § "Trust model"
    for the canonical statement of this trust boundary.

    The synchronization protocol proves ordered, non-replayable completion
    by Aura's trusted same-origin presentation agent.  It does NOT
    independently attest against a malicious client controlling that agent.

    The protocol provides:
    - Ordering (PREPARED → PROJECTED → RENDER_CONFIRMED → ACKNOWLEDGED)
    - Anti-replay (one-time nonce, one-time state transitions)
    - Receipt unpredictability (render_capability is server-owned and
      never returned to any caller, making receipt_digest non-deterministic
      from the caller's perspective — this is anti-forgery, NOT renderer
      attestation)

    It does NOT provide cryptographic proof that a human observed pixels.
    The render_capability prevents offline receipt forgery but cannot
    prevent the same trusted browser from asking the signing endpoint
    to sign the claim — because under Trust Model A that browser IS
    the trusted agent.

    This test documents the achievable guarantee: a caller who is the
    browser's agent CAN transition the state machine.  The receipt is
    bound to server-owned values the caller cannot predict or forge
    offline.  This is the correct and final trust model for this
    offline local demo.
    """
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    director = ConstructionFoundryDirector(_manifest())
    import hashlib as _hl
    from collections import namedtuple
    FakeIdentity = namedtuple("FakeIdentity", ["identity_digest"])
    ident_digest = _hl.sha256(b"e2e-direct-confirm").hexdigest()
    fake_identity = FakeIdentity(identity_digest=ident_digest)

    def fake_proj_identity(_state, _body, require_all=True):
        return ({}, fake_identity)
    monkeypatch.setattr(p4, "_projection_and_identity", fake_proj_identity)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    state.p4_available = True
    state.p4_load_error = ""
    state.p4_director = director
    state.presentation_origin = "http://127.0.0.1:8765"
    state.presentation_netloc = "127.0.0.1:8765"
    state.require_p4 = lambda: director

    try:
        session = director.start_session(
            identity_digest=ident_digest,
            construction_state_digest=_hl.sha256(b"e2e-direct-confirm-state").hexdigest(),
            initial_evidence={
                "p3_available": True, "construction_identity_bound": True,
                "pascal_artifact_bound": True, "coordinate_receipt_bound": True,
                "as_built_scene_bound": True, "compare_receipt_bound": True,
                "construction_candidates_bound": True, "domain_decision_bound": True,
                "identity_current": True, "operator_authorized": True,
                "fault_fixture_bound": True, "required_assets_bound": True,
                "rollback_adapter_ready": True, "u7_bridge_ready": True,
                "construction_state_unchanged": True, "capture_resources_dissolved": True,
            },
        )
        session_id = session["session_id"]
        claimed = director.claim_next(session_id)
        director.commit_next(
            session_id,
            transition_digest=claimed["transition_digest"],
            effect_receipt={"ok": True},
            claim_token=claimed["claim_token"],
        )
        assert director.require_session(session_id).p3_sync_pending is True

        prep_status, _, prep_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/prepare-p3-sync",
            {"identity_handle": "e2e-direct-confirm"},
        )
        assert prep_status == 200
        prep = json.loads(prep_resp.decode())

        sess = director.require_session(session_id)
        chapter_id = sess.receipts[-1].get("chapter_id")
        active_view = dict(director.manifest.chapter(chapter_id).ui_directive or {}).get("active_view")
        projection = state.require_p3().compile(active_view=active_view, timeline_day=14.0)
        exact_identity = {
            "state_digest": projection["domain"]["state_digest"],
            "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
            "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
            "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
            "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
        }
        proj_status, _, proj_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/project",
            {
                **exact_identity, "active_view": active_view, "timeline_day": 14.0,
                "identity_handle": "e2e-direct-confirm", "identity_digest": prep["identity_digest"],
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"], "sync_nonce": prep["sync_nonce"],
            },
            request_origin="http://127.0.0.1:8765", request_host="127.0.0.1:8765",
        )
        assert proj_status == 200
        proj = json.loads(proj_resp.decode())
        assert proj["projection_digest"]

        # Confirm directly with project response values — no render step.
        confirm_status, _, confirm_resp = p3mod.dispatch_p3_foundry_request(
            state, "POST",
            "/api/construction/decision-lane/confirm-presentation",
            {
                "director_session_id": prep["director_session_id"],
                "director_receipt_digest": prep["director_receipt_digest"],
                "chapter_id": prep["chapter_id"],
                "active_view": active_view,
                "identity_digest": prep["identity_digest"],
                "projection_digest": proj["projection_digest"],
                "presentation_revision": proj["presentation_revision"],
            },
            request_origin="http://127.0.0.1:8765",
            request_host="127.0.0.1:8765",
        )
        assert confirm_status == 200
        confirm = json.loads(confirm_resp.decode())
        assert confirm["presentation_receipt_digest"]

        # The receipt_digest is non-deterministic from the caller's view
        # because it includes the server-owned render_capability.
        _sync_key = f"{session_id}:{prep['director_receipt_digest']}"
        _sync_record = state._p3_sync_nonces[_sync_key]
        _expected_receipt = _hl.sha256("|".join([
            "v1", prep["director_session_id"], prep["director_receipt_digest"],
            prep["chapter_id"], active_view, prep["identity_digest"],
            proj["projection_digest"], proj["presentation_revision"],
            _sync_record["render_capability"],
        ]).encode()).hexdigest()
        assert confirm["presentation_receipt_digest"] == _expected_receipt
        assert _sync_record["state"] == "RENDER_CONFIRMED"

        # ack-p3-sync
        ack_status, _, ack_resp = p4.dispatch_p4_foundry_request(
            state, "POST",
            f"/api/construction/director/session/{session_id}/ack-p3-sync",
            {
                "identity_handle": "e2e-direct-confirm",
                "presentation_receipt": {
                    "chapter_id": chapter_id, "active_view": active_view,
                    "receipt_digest": confirm["presentation_receipt_digest"],
                },
            },
        )
        assert ack_status == 200
        assert director.require_session(session_id).p3_sync_pending is False
    finally:
        state.close()


def test_p3_project_rejects_partial_director_bindings(monkeypatch):
    """P3 /project must reject partial Director binding groups with 400.

    If any Director binding field is present (e.g. director_session_id
    alone), the route must require the complete binding group and reject
    with 400 — not fall through to a plain projection response.
    """
    monkeypatch.setattr(p4, "_validate_request_context", lambda *_args, **_kwargs: None)
    import aura_construction_pascal_spatial_foundry_p3_server as p3mod
    monkeypatch.setattr(p3mod, "_validate_request_context", lambda *_args, **_kwargs: None)

    state = p3mod.P3FoundryShowcaseState(
        Path(__file__).resolve().parents[1],
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin="http://127.0.0.1:8765",
    )
    try:
        # Compile a real projection to get valid identity fields.
        projection = state.require_p3().compile(active_view="DESIGN", timeline_day=14.0)
        # Only director_session_id present — no other Director bindings.
        status, _, resp = p3mod.dispatch_p3_foundry_request(
            state, "POST", "/api/construction/decision-lane/project",
            {
                "active_view": "DESIGN", "timeline_day": 14.0,
                "state_digest": projection["domain"]["state_digest"],
                "runtime_packet_digest": projection["domain"]["runtime_packet_digest"],
                "pascal_artifact_digest": projection["artifacts"]["pascal_artifact_digest"],
                "coordinate_receipt_digest": projection["artifacts"]["coordinate_receipt_digest"],
                "as_built_scene_digest": projection["artifacts"]["as_built_scene_digest"],
                "director_session_id": "partial-session-id",
                # Missing: director_receipt_digest, identity_digest,
                # chapter_id, sync_nonce
            },
            request_origin="http://127.0.0.1:8765",
            request_host="127.0.0.1:8765",
        )
        assert status == 400, f"partial bindings should be rejected, got {status}: {resp.decode()[:200]}"
        body = json.loads(resp.decode())
        assert "missing required fields" in body.get("error", "")
        # Verify no sync state was created.
        assert not hasattr(state, "_p3_sync_nonces") or not state._p3_sync_nonces
    finally:
        state.close()
