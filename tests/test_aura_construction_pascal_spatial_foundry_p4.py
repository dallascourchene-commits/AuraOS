from __future__ import annotations

import hashlib
import json
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
