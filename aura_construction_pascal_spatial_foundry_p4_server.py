"""P4 deterministic Foundry Director over the merged P3 Construction experience.

P3 remains the fallback presentation owner.  This additive server compiles one
exact, offline Director manifest; derives current demo identity on the server;
binds every stateful request to the P3 Construction/Pascal identities; delegates
capture/replay/repair/preview/U7 work to the existing Construction-bound B11-B15
service; and exposes only presentation directives plus exact receipts.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import asdict
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

from aura_bilateral_intent_compiler import (
    analyze_bilateral_request,
    compile_confirmed_bilateral_intent,
    create_refinement_session,
)
from aura_bilateral_live_repair_foundry import BilateralIdentity, BilateralLiveRepairError
from aura_construction_foundry_director import (
    ConstructionFoundryDirector,
    DirectorControl,
    RequiredAsset,
    build_default_manifest,
    canonical_bytes,
    digest,
    runtime_binding_digest,
)
from aura_construction_pascal_spatial_foundry_p3_server import (
    IPv6HTTPServer,
    P3FoundryShowcaseState,
    _IDENTITY_KEYS,
    _assert_exact_identities_from_projection,
    _content_security_policy as p3_content_security_policy,
    _error,
    _json,
    _loopback_origin,
    _validate_request_context,
    _static_response as p3_static_response,
    _query_projection_body,
    dispatch_p3_foundry_request,
)
from aura_event_contracts import stable_digest
from aura_architect_loop import ACT_CAPSULE_VERSION, ActCapsule
from aura_model_cognome import ModelEndpointIdentity
from aura_unified_memory_continuity_toolchain import compile_bridge_execution_binding
from aura_showcase_live_repair_server import DEFAULT_HOST, DEFAULT_PORT, MAX_BODY_BYTES
from aura_pascal_spatial_presentation import PascalPresentationError

P4_FOUNDRY_SERVER_VERSION = "AURA_CONSTRUCTION_PASCAL_SPATIAL_FOUNDRY_P4_SERVER_V1"
STATIC_DIR = Path(__file__).resolve().parent / "aura_showcase"
_RUNTIME_PROFILE = ".aura/runtime_profiles/construction_demo_bilateral.v2.json"
_CONFIRMATION_TEMPLATE = ".aura/runtime_profiles/construction_foundry_p4.confirmation.template.json"
_VERIFIER_SOURCE = "tests/runtime/construction_demo_browser_probe.cjs"
_P4_STATIC_PATHS = {
    "construction-foundry-director.css": STATIC_DIR / "construction-foundry-director.css",
    "construction-foundry-director.js": STATIC_DIR / "construction-foundry-director.js",
}
_P4_SOURCE_ASSETS = (
    "aura_construction_foundry_director.py",
    "aura_construction_pascal_spatial_foundry_p4_server.py",
    "aura_construction_pascal_spatial_foundry_p3_server.py",
    "aura_construction_foundry_decision.py",
    "aura_showcase/construction-foundry-director.css",
    "aura_showcase/construction-foundry-director.js",
    "aura_showcase/construction-decision-foundry.js",
    "aura_showcase/construction-decision-as-built-sync.js",
    "aura_showcase/pascal-workbench/pascal-workbench.js",
    "aura_showcase/pascal-workbench/fixture.json",
    "aura_showcase/pascal-workbench/artifact-manifest.json",
    "aura_showcase/pascal-workbench/coordinate-receipt.json",
    _RUNTIME_PROFILE,
    _CONFIRMATION_TEMPLATE,
    "scripts/aura_runtime_profile_v2_adapter.py",
    _VERIFIER_SOURCE,
)
_P4_MARKUP = b"""
<section id="construction-foundry-director" class="foundry-card construction-director" aria-label="P4 Construction Foundry Director">
  <div class="construction-director-heading">
    <div><p class="eyebrow">P4 - deterministic guided Director</p><h2>Construction decision and bounded self-repair tour</h2></div>
    <p id="construction-director-status">Director not started.</p>
  </div>
  <div class="construction-director-controls" role="group" aria-label="Director controls">
    <button type="button" data-director-control="PLAY">Play</button>
    <button type="button" data-director-control="PAUSE">Pause</button>
    <button type="button" data-director-control="PREVIOUS">Previous</button>
    <button type="button" data-director-control="NEXT">Next</button>
    <button type="button" data-director-control="RESYNC">Re-sync P3</button>
    <button type="button" data-director-control="RESTART">Restart</button>
  </div>
  <label>Chapter <select id="construction-director-chapters"></select></label>
  <div id="construction-director-current"></div>
  <div id="construction-director-notes"></div>
  <details><summary>Exact route receipt</summary><pre id="construction-director-receipt"></pre></details>
</section>
"""
_P4_STYLE = b'  <link rel="stylesheet" href="construction-foundry-director.css">\n'
_P4_SCRIPT = b'  <script src="construction-foundry-director.js"></script>\n'
_EXACT_DIGEST = re.compile(r"^[0-9a-f]{40,64}$")

_POSITIVE = (
    "The canonical Runtime Profile V1 path completes successfully before bilateral assertions are evaluated.",
    "The selected Construction storey, issue, blueprint, annotations, and inspector identity remain stable across Mesh, Splats, Hybrid, isolate, show-all, and relaunch transitions.",
)
_AUTHORITY_NEGATIVE = "Do not grant production mutation, automatic merge, physical-work, or professional authority."
_PRESERVATION = "Do not mutate canonical Construction source geometry or lose the selected inspector state."
_FAULT_NEGATIVES = (
    "Do not make hidden storeys pickable or focusable.",
    "Do not silently substitute a missing or ambiguous blueprint.",
    "Do not suppress stale asset digests, initialization races, cancellation, device loss, cleanup, or dissolution failures.",
)
_NEGATIVE = (_AUTHORITY_NEGATIVE, _PRESERVATION, *_FAULT_NEGATIVES)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _bilateral_identity_digest(value: Any, name: str) -> str:
    """Project canonical compiler identities into B11's older hex envelope.

    The canonical bilateral compiler uses 32-character BLAKE2 identities while
    B11 admits Git/SHA-style 40-64 character fields.  Shorter canonical values
    are retained in the external packet and projected through a deterministic,
    namespaced SHA-256 handle for the B11 packet/proof boundary.
    """
    text = str(value or "").strip().lower()
    if not text or not re.fullmatch(r"[0-9a-f]{32,64}", text):
        raise PascalPresentationError(f"canonical {name} is not a 32-64 character exact digest")
    if _EXACT_DIGEST.fullmatch(text):
        return text
    return hashlib.sha256(
        canonical_bytes(
            {
                "version": "AURA_B11_CANONICAL_DIGEST_PROJECTION_V1",
                "field": name,
                "canonical_digest": text,
            }
        )
    ).hexdigest()


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _safe_repo_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PascalPresentationError(f"P4 required asset escaped repository root: {relative}") from exc
    if not path.is_file() or path.is_symlink():
        raise PascalPresentationError(f"P4 required asset is unavailable: {relative}")
    return path


def _compile_confirmation_bundle(root: Path) -> tuple[BilateralIdentity, Path, Path]:
    head = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    if _git(root, "status", "--porcelain"):
        raise PascalPresentationError("P4 deterministic demo requires a clean exact-head checkout")
    profile_path = _safe_repo_file(root, _RUNTIME_PROFILE)
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    if not isinstance(profile, Mapping):
        raise PascalPresentationError("P4 runtime profile must be a JSON object")
    verifier = profile.get("independent_verifier")
    if not isinstance(verifier, Mapping):
        raise PascalPresentationError("P4 runtime profile omitted the independent verifier")
    verifier_path = _safe_repo_file(root, str(verifier.get("source_path") or ""))
    verifier_digest = _sha256_bytes(verifier_path.read_bytes())
    if verifier_digest != verifier.get("source_sha256"):
        raise PascalPresentationError("P4 runtime verifier source differs from the exact profile identity")
    source_request = " ".join((*_POSITIVE, *_NEGATIVE))
    analysis = analyze_bilateral_request(
        source_request,
        arena="CONSTRUCTION",
        affected_files=tuple(str(item) for item in profile.get("allowed_paths") or ()),
        supplied_positive_requirements=_POSITIVE,
        supplied_negative_requirements=_NEGATIVE,
    )
    if analysis.questions or analysis.teach_back is None:
        raise PascalPresentationError("P4 deterministic confirmation unexpectedly requires clarification")
    now = time.time()
    session = create_refinement_session(
        analysis,
        repository_head=head,
        working_tree_digest=tree,
        arena="CONSTRUCTION",
        created_at=now,
        expires_at=now + 86_400,
    )
    codemap_path = _safe_repo_file(root, ".aura/CODEMAP.md")
    packet = compile_confirmed_bilateral_intent(
        session=session,
        analysis=analysis,
        repository_head=head,
        source_tree_digest=tree,
        working_tree_clean_receipt=stable_digest({"head": head, "tree": tree, "clean": True}),
        allowed_paths=tuple(str(item) for item in profile.get("allowed_paths") or ()),
        runtime_profile_digest=_sha256_bytes(profile_bytes),
        workflow_phase_hash=stable_digest({"director": P4_FOUNDRY_SERVER_VERSION, "state": "CAPTURE_AUTHORIZED"}),
        topology_evidence_digest=stable_digest({"manifest": "P4", "profile": profile.get("profile_id")}),
        topology_selected=True,
        codemap_digest=_sha256_bytes(codemap_path.read_bytes()),
        human_reviewer="Dallas Courchene - deterministic P4 recording fixture",
        confirmed_at=now,
        expires_at=now + 86_400,
        arena="Construction",
    )
    intent = dict(packet["intent_packet"])
    receipt = dict(packet["confirmation_receipt"])
    ledger = dict(packet["semantic_ledger"])
    u7 = dict(packet["u7_references"])
    identity = BilateralIdentity(
        intent_digest=_bilateral_identity_digest(intent["intent_digest"], "intent digest"),
        confirmation_digest=str(receipt["confirmation_id"]),
        semantic_ledger_digest=_bilateral_identity_digest(ledger["ledger_digest"], "Semantic Ledger digest"),
        guardrail_set_digest=_bilateral_identity_digest(receipt["guardrail_set_digest"], "guardrail-set digest"),
        intent_revision_id=str(u7["intent_revision_status"]),
        repository_head=head,
        source_tree_digest=tree,
        runtime_profile_digest=_sha256_bytes(profile_bytes),
        verifier_id=str(verifier["verifier_id"]),
        verifier_source_digest=verifier_digest,
    )
    external_root = Path(tempfile.mkdtemp(prefix="auraos-p4-runtime-"))
    external_root.chmod(0o700)
    confirmation_path = external_root / "confirmation.json"
    confirmation_path.write_bytes(canonical_bytes(packet))
    confirmation_path.chmod(0o600)
    output_dir = external_root / "runtime-output"
    return identity, confirmation_path, output_dir


def _confirmation_intent_contract(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise PascalPresentationError("P4 canonical confirmation packet is unavailable")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
        intent = dict(packet["intent_packet"])
        ledger = dict(packet["semantic_ledger"])
        receipt = dict(packet["confirmation_receipt"])
        u7 = dict(packet["u7_references"])
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PascalPresentationError("P4 canonical confirmation packet is invalid") from exc
    return {
        "intent_digest": str(intent["intent_digest"]),
        "semantic_ledger_digest": str(ledger["ledger_digest"]),
        "confirmation_digest": str(receipt["confirmation_id"]),
        "guardrail_set_digest": str(receipt["guardrail_set_digest"]),
        "intent_revision_status": str(u7["intent_revision_status"]),
        "expected_repository_head": str(receipt["repository_head"]),
        "expected_source_tree": str(receipt["source_tree_digest"]),
    }


def _adapt_runtime_proof_identity(
    proof: Mapping[str, Any],
    *,
    identity: BilateralIdentity,
    confirmation_path: Path,
    repo_root: Path,
    required_assets: tuple[RequiredAsset, ...],
) -> dict[str, Any]:
    """Project canonical compiler IDs into B11's hex-only identity envelope.

    Runtime Profile V2 remains the verifier.  This adapter verifies and retains
    its exact canonical contract, then adds a deterministic SHA-256 binding only
    for the three canonical owner IDs whose native stable IDs are 32 hex chars.
    """

    if not isinstance(proof, Mapping):
        raise PascalPresentationError("Runtime Profile V2 returned a non-object proof")
    canonical_contract = proof.get("intent_contract")
    if not isinstance(canonical_contract, Mapping):
        raise PascalPresentationError("Runtime Profile V2 omitted its canonical intent contract")
    expected_canonical = _confirmation_intent_contract(confirmation_path)
    for name, expected in expected_canonical.items():
        if canonical_contract.get(name) != expected:
            raise PascalPresentationError(
                f"Runtime Profile V2 canonical {name} differs from the confirmation packet"
            )
    adapted_contract = {
        **dict(canonical_contract),
        "intent_digest": _bilateral_identity_digest(
            canonical_contract["intent_digest"], "intent digest"
        ),
        "semantic_ledger_digest": _bilateral_identity_digest(
            canonical_contract["semantic_ledger_digest"], "Semantic Ledger digest"
        ),
        "guardrail_set_digest": _bilateral_identity_digest(
            canonical_contract["guardrail_set_digest"], "guardrail-set digest"
        ),
    }
    expected_adapted = {
        "intent_digest": identity.intent_digest,
        "semantic_ledger_digest": identity.semantic_ledger_digest,
        "confirmation_digest": identity.confirmation_digest,
        "guardrail_set_digest": identity.guardrail_set_digest,
        "intent_revision_status": identity.intent_revision_id,
        "expected_repository_head": identity.repository_head,
        "expected_source_tree": identity.source_tree_digest,
    }
    for name, expected in expected_adapted.items():
        if adapted_contract.get(name) != expected:
            raise PascalPresentationError(
                f"P4 B11 identity adapter produced a mismatched {name}"
            )
    canonical_traces = proof.get("required_trace_artifacts")
    if not isinstance(canonical_traces, list):
        raise PascalPresentationError("Runtime Profile V2 omitted its canonical trace inventory")
    source_asset_traces: list[dict[str, Any]] = []
    for asset in required_assets:
        source = _safe_repo_file(repo_root, asset.path)
        body = source.read_bytes()
        if _sha256_bytes(body) != asset.sha256:
            raise PascalPresentationError(
                f"P4 required asset changed after Director manifest compilation: {asset.path}"
            )
        source_asset_traces.append({
            "path": asset.path,
            "present": True,
            "size_bytes": len(body),
            "within_size_limit": True,
            "sha256": asset.sha256,
            "evidence_class": "EXACT_REPOSITORY_ASSET",
        })
    canonical_proof_digest = str(proof.get("proof_digest") or "")
    adapted = {
        **dict(proof),
        "canonical_intent_contract": dict(canonical_contract),
        "intent_contract": adapted_contract,
        "canonical_required_trace_artifacts": list(canonical_traces),
        "required_trace_artifacts": [*canonical_traces, *source_asset_traces],
        "canonical_runtime_proof_digest": canonical_proof_digest,
        "identity_adapter": {
            "version": "AURA_P4_RUNTIME_PROOF_IDENTITY_ADAPTER_V1",
            "canonical_contract_digest": digest(dict(canonical_contract)),
            "adapted_contract_digest": digest(adapted_contract),
            "required_asset_set_digest": digest([item.to_dict() for item in required_assets]),
            "required_asset_count": len(source_asset_traces),
            "canonical_runtime_owner": (
                "scripts.aura_runtime_profile_v2_adapter.run_runtime_profile_v2"
            ),
            "verification_owner_changed": False,
            "production_mutation": False,
            "automatic_promotion": False,
            "human_review_required": True,
        },
    }
    canonical = {
        key: value
        for key, value in adapted.items()
        if key not in {"proof_digest", "proof_path", "output_dir"}
    }
    adapted["proof_digest"] = runtime_binding_digest(canonical)
    output_dir = Path(str(adapted.get("output_dir") or "")).expanduser()
    if output_dir.is_dir():
        projected_path = output_dir / "bilateral_runtime_proof_b11_projection.json"
        projected_payload = {
            key: value
            for key, value in adapted.items()
            if key not in {"proof_path", "output_dir"}
        }
        projected_path.write_text(
            json.dumps(projected_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        adapted["proof_path"] = str(projected_path)
    return adapted


class _P4U7Bridge:
    """Prepare one exact canonical execution binding for the P4 U7 delegate."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self._sessions: dict[str, dict[str, Any]] = {}

    def prepare(
        self,
        *,
        phase: str,
        task_id: str,
        packet_digest: str,
        candidate_digest: str,
        observed_at: float,
    ) -> None:
        capsule = ActCapsule(
            capsule_version=ACT_CAPSULE_VERSION,
            task_id=task_id,
            role="bounded_verifier",
            objective="Retain exact P4 selection-repair evidence through canonical current reproof",
            target_file="aura_construction_pascal_spatial_foundry_p4_server.py",
            target_symbol="_execute_chapter",
            related_files=[
                "aura_construction_foundry_director.py",
                "aura_construction_pascal_spatial_foundry_p3_server.py",
                "aura_construction_spatial_foundry.py",
            ],
            acceptance="P0, independent P1, current reproof, and human disposition remain exact and proposal-only.",
            escalate_if=["Construction truth changes", "authority expands", "source identity moves"],
            constraints=[
                "preserve canonical U7 owners",
                "do not authorize physical work",
                "do not promote learning automatically",
            ],
        )
        session: dict[str, Any] = {
            "prepared": SimpleNamespace(plan=SimpleNamespace(act_capsules=[capsule])),
            "unified_execution_bindings": {},
            "unified_crucible_proposals": {},
            "unified_crucible_bindings": {},
            "unified_crucible_proposal_storage": {},
            "unified_prediction_packets": {},
            "unified_p1_observations": {},
            "unified_continuity_receipts": {},
            "unified_current_reproofs": {},
            "unified_human_dispositions": {},
            "unified_learning_decisions": {},
            "unified_relationship_experiences": {},
            "unified_qdkt_admissions": {},
            "unified_learning_results": {},
        }
        self._sessions[phase] = session
        head = _git(self.repo_root, "rev-parse", "HEAD")
        endpoint = ModelEndpointIdentity.create(
            provider="aura-deterministic-fixture",
            requested_model="none",
            returned_model="none",
            base_url_digest=stable_digest({"base_url": "offline"}),
            access_class="OPEN_WEIGHT",
            endpoint_fingerprint=stable_digest({"fixture": P4_FOUNDRY_SERVER_VERSION}),
            fingerprint_version="identity-v1",
            provider_revision="p4",
            tokenizer_family="none",
            price_snapshot_digest=stable_digest({"price": 0}),
            first_seen_at=observed_at - 120,
            last_seen_at=observed_at - 60,
            status="ACTIVE",
        )
        binding = compile_bridge_execution_binding(
            self,
            plan_phase_hash=phase,
            task_id=task_id,
            contract={
                "expected_repository_head": head,
                "purpose": "Bind P4 current reproof to exact retained runtime and preview evidence",
                "user_meaning": "Demonstrate bounded self-repair without changing Construction truth or granting authority",
                "authority": {"inspect": True, "edit": False, "test": True},
                "semantic_definitions": [
                    {
                        "term": term,
                        "means": [f"P4 governed {term}"],
                        "does_not_mean": [f"automatic {term} authority"],
                        "source_refs": [f"p4:{term}"],
                    }
                    for term in ("repair", "current reproof", "human disposition", "Construction truth")
                ],
                "model_profile": {
                    "endpoint_identity": endpoint.to_dict(),
                    "calibrated_at": observed_at - 60,
                    "expires_at": observed_at + 300,
                    "evidence_refs": [packet_digest, candidate_digest],
                    "uncertainty": 0.0,
                },
                "provider_config_digest": stable_digest({"provider": "offline-deterministic"}),
                "observed_at": observed_at,
            },
        )
        session["unified_execution_bindings"][task_id] = binding

    def _require_session(self, phase: str) -> dict[str, Any]:
        retained = self._sessions.get(phase)
        if retained is None:
            raise ValueError("P4 canonical U7 bridge was not prepared for this phase")
        return retained

    def aura_get_micro_context(self, **_kwargs: Any) -> dict[str, Any]:
        target_file = "aura_construction_pascal_spatial_foundry_p4_server.py"
        source = (self.repo_root / target_file).read_text(encoding="utf-8").splitlines()
        start = next(
            (index for index, line in enumerate(source, 1) if line.startswith("def _execute_chapter(")),
            None,
        )
        if start is None:
            raise ValueError("P4 _execute_chapter source symbol is unavailable")
        end = len(source)
        for index in range(start + 1, len(source) + 1):
            line = source[index - 1]
            if line and not line.startswith((" ", "\t")) and line.startswith(("def ", "class ")):
                end = index - 1
                break
        return {
            "ok": True,
            "target_file": target_file,
            "target_symbol": "_execute_chapter",
            "line_ranges": [
                {
                    "file": target_file,
                    "symbol": "_execute_chapter",
                    "line_range": [start, end],
                }
            ],
            "tests": [
                "tests/test_aura_construction_foundry_director.py",
                "tests/test_aura_construction_pascal_spatial_foundry_p4.py",
            ],
            "route_decision": {"route": "VERIFIER_ONLY"},
        }


def _p4_prediction_contract(now: float, packet_digest: str, candidate_digest: str) -> dict[str, Any]:
    return {
        "current_state_digest": stable_digest({"state": "previewed", "packet": packet_digest}),
        "prompt_runtime_digest": stable_digest({"runtime": "P4", "candidate": candidate_digest}),
        "proposed_transition": "retain exact verified P4 selection-repair evidence",
        "expected_state_delta": ["presentation selection synchronization restored"],
        "expected_evidence": [packet_digest, candidate_digest, "p4:isolated-preview"],
        "expected_cost": {"tokens": 0, "seconds": 0.0},
        "expected_risk": ["stale source", "self verification", "Construction authority confusion"],
        "producer_id": "p4-bounded-repair-producer",
        "crucible_bound_at": now,
        "committed_at": now + 0.5,
        "crucible_proposal": {
            "proposal_id": f"CPROP-p4-{candidate_digest[:16]}",
            "run_id": f"CRUN-p4-{packet_digest[:16]}",
            "candidate_id": f"candidate-p4-{candidate_digest[:16]}",
            "arena_id": "construction",
            "grammar_version": "AURA_CONSTRUCTION_SPATIAL_FOUNDRY_GUARDED_WFST_V1",
            "manifest_path": _CONFIRMATION_TEMPLATE,
            "manifest_digest": stable_digest({"manifest": "P4", "candidate": candidate_digest}),
            "state_before": "PREVIEWED",
            "transition_id": "current-reproof-after-isolated-preview",
            "change_path": "soft_weight_profile.empirical_uncertainty",
            "current_value": 0.5,
            "proposed_value": 0.4,
            "validation": {
                "passed": True,
                "proposal_recommendation": "PROPOSE",
                "all_proposal_thresholds_met": True,
            },
            "proposal_thresholds": {"minimum_verified_previews": 1},
            "threshold_assessment": {"all_proposal_thresholds_met": True},
            "train_experience_ids": [f"p4-train-{packet_digest[:16]}"],
            "validation_experience_ids": [f"p4-validation-{candidate_digest[:16]}"],
            "shadow_experience_ids": ["p4-shadow-offline"],
            "source_experience_digest": stable_digest({"packet": packet_digest, "candidate": candidate_digest}),
            "created_at": now - 1,
        },
        "storage": {"crucible_db_path": "Aura_Memory/p4_foundry_runtime/crucible.db"},
    }


def _p4_observation_contract(now: float, packet_digest: str, candidate_digest: str) -> dict[str, Any]:
    return {
        "observed_state_delta": ["presentation selection synchronization restored"],
        "observed_evidence_refs": [packet_digest, candidate_digest, "p4:isolated-preview:verified"],
        "observed_cost": {"tokens": 0, "seconds": 0.0},
        "missing_measurements": [],
        "observer_id": "p4-independent-runtime-verifier",
        "observed_at": now + 1,
    }


def _p4_finalization_contract(now: float, packet_digest: str, candidate_digest: str) -> dict[str, Any]:
    return {
        "human_disposition_requirement_ref": "p4:human-review:required",
        "error_class": "INTERFACE",
        "prediction_error": [],
        "consequence_dimensions": ["correctness", "continuity", "authority separation"],
        "protected_pathways": ["Construction truth", "exact runtime proof", "human authority"],
        "mutation_budget": ["no automatic mutation", "presentation-only candidate"],
        "replay_burden": ["re-run exact Runtime Profile V2 and isolated preview"],
        "raw_evidence_refs": [packet_digest, candidate_digest, "p4:runtime-v2", "p4:preview"],
        "replacement_candidate_refs": [candidate_digest],
        "uncertainty": 0.0,
        "receipt_producer_id": "p4-continuity-receipt-producer",
        "verifier_evidence_refs": ["p4:runtime-v2", "p4:preview"],
        "reproof_verifier_id": "p4-independent-current-reproof-verifier",
        "reproof_evidence_refs": [packet_digest, candidate_digest, "p4:current-source"],
        "reproof_verified_at": now + 3,
        "disposition_actor_id": "p4-recording-operator",
        "disposition_actor_type": "HUMAN",
        "human_disposition": "NOT_REVIEWED",
        "disposition_reason_ref": "p4:human-review:pending",
        "disposition_created_at": now + 4,
        "relationship_recorded_at": now + 4.5,
        "relationship_id": "relationship:p4-selection-sync-repair",
        "relationship_digest": stable_digest({"relationship": "p4-selection-sync-repair"}),
        "outcome": "FAILURE",
        "source_refs": [
            "aura_construction_foundry_director.py",
            "aura_construction_pascal_spatial_foundry_p4_server.py",
        ],
        "privacy_class": "PROJECT",
        "reason": "The exact repair remains proposal-only pending separate human review.",
        "purpose_compatible": True,
        "privacy_compatible": True,
        "consent_compatible": True,
        "sovereignty_compatible": True,
        "trace_id": f"trace-p4-{packet_digest[:16]}",
        "qdkt_actor_id": "aura-governed-qdkt-adapter",
        "arena_id": "construction",
        "qdkt_created_at": now + 5,
        "storage": {
            "crucible_db_path": "Aura_Memory/p4_foundry_runtime/crucible.db",
            "experience_db_path": "Aura_Memory/p4_foundry_runtime/experience.db",
            "qdkt_event_root": "Aura_Memory/p4_foundry_runtime/qdkt-events",
            "attempt_archive_db_path": "Aura_Memory/p4_foundry_runtime/u7-attempts.db",
        },
    }


class P4FoundryShowcaseState(P3FoundryShowcaseState):
    """P3 plus one exact Director, server-derived identity, and external runtime evidence."""

    def __init__(self, repo_root: str | Path, **kwargs: Any) -> None:
        root = Path(repo_root).resolve()
        self.p4_load_error = ""
        self.p4_static_assets: dict[str, bytes] = {}
        self.p4_required_assets: tuple[RequiredAsset, ...] = ()
        self.p4_identity: BilateralIdentity | None = None
        self.p4_confirmation_path: Path | None = None
        self.p4_runtime_output_dir: Path | None = None
        self.p4_director: ConstructionFoundryDirector | None = None
        self.p4_confirmation_consumed = False
        self._p4_external_roots: set[Path] = set()
        self._p4_runtime_lock = threading.RLock()
        self.p4_u7_bridge = _P4U7Bridge(root)
        try:
            identity, confirmation_path, output_dir = _compile_confirmation_bundle(root)
            self.p4_identity = identity
            self.p4_confirmation_path = confirmation_path
            self.p4_runtime_output_dir = output_dir
            self._p4_external_roots.add(confirmation_path.parent)
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, PascalPresentationError) as exc:
            self.p4_load_error = str(exc)
        provider: Callable[[], BilateralIdentity] | None = None
        resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None
        if self.p4_identity is not None:
            provider = lambda: self._current_demo_identity()
            resolver = lambda expected: self._resolve_demo_identity(expected)
        super().__init__(
            root,
            trusted_identity_provider=provider,
            current_identity_resolver=resolver,
            **kwargs,
        )
        if self.p4_load_error or not self.p3_available:
            if not self.p4_load_error:
                self.p4_load_error = self.p3_load_error or "P3 Foundry is unavailable"
            return
        try:
            retained = {}
            for route, path in _P4_STATIC_PATHS.items():
                if not path.is_file() or path.is_symlink():
                    raise PascalPresentationError(f"P4 static asset is unavailable: {route}")
                retained[route] = path.read_bytes()
            required_assets = tuple(
                RequiredAsset(relative, _sha256_bytes(_safe_repo_file(root, relative).read_bytes()))
                for relative in _P4_SOURCE_ASSETS
            )
            manifest = build_default_manifest(
                required_assets,
                runtime_profile_path=_RUNTIME_PROFILE,
                confirmation_packet_path=_CONFIRMATION_TEMPLATE,
            )
            self.p4_static_assets = retained
            self.p4_required_assets = required_assets
            self.p4_director = ConstructionFoundryDirector(manifest)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, PascalPresentationError) as exc:
            self.p4_load_error = str(exc)
            self.p4_static_assets = {}
            self.p4_required_assets = ()
            self.p4_director = None

    def _current_demo_identity(self) -> BilateralIdentity:
        if self.p4_identity is None:
            raise BilateralLiveRepairError("P4 server-derived identity is unavailable")
        return self._resolve_demo_identity(self.p4_identity)

    def _resolve_demo_identity(self, expected: BilateralIdentity) -> BilateralIdentity:
        root = self.repo_root
        current = BilateralIdentity(
            **{
                **asdict(expected),
                "repository_head": _git(root, "rev-parse", "HEAD"),
                "source_tree_digest": _git(root, "rev-parse", "HEAD^{tree}"),
                "runtime_profile_digest": _sha256_bytes(_safe_repo_file(root, _RUNTIME_PROFILE).read_bytes()),
                "verifier_source_digest": _sha256_bytes(_safe_repo_file(root, _VERIFIER_SOURCE).read_bytes()),
            }
        )
        expected.assert_current(current)
        if _git(root, "status", "--porcelain"):
            raise BilateralLiveRepairError("P4 exact identity became dirty after startup")
        return current

    def _cleanup_external_roots(self, *, retain: set[Path] | None = None) -> int:
        retained = {item.resolve() for item in (retain or set())}
        removed = 0
        for root in tuple(self._p4_external_roots):
            resolved = root.resolve()
            if resolved in retained:
                continue
            if root.is_symlink():
                raise PascalPresentationError("P4 external runtime root became a symlink")
            if root.exists():
                shutil.rmtree(root)
            self._p4_external_roots.discard(root)
            removed += 1
        return removed

    def refresh_demo_identity(self) -> BilateralIdentity:
        with self._p4_runtime_lock:
            identity, confirmation_path, output_dir = _compile_confirmation_bundle(self.repo_root)
            new_root = confirmation_path.parent
            self._p4_external_roots.add(new_root)
            self._cleanup_external_roots(retain={new_root})
            self.p4_identity = identity
            self.p4_confirmation_path = confirmation_path
            self.p4_runtime_output_dir = output_dir
            self.p4_confirmation_consumed = False
            self.p4_u7_bridge._sessions.clear()
        return identity

    def execute_exact_runtime_replay(self, *, packet_id: str, identity: BilateralIdentity) -> dict[str, Any]:
        # Acquire the lock at the very beginning so lifecycle mutations
        # (refresh, dissolve, close) cannot interleave with state reads.
        with self._p4_runtime_lock:
            if self.p4_confirmation_path is None or self.p4_runtime_output_dir is None:
                raise PascalPresentationError("P4 external runtime paths are unavailable")
            if self.p4_confirmation_consumed:
                raise PascalPresentationError(
                    "P4 confirmation was already consumed; dissolve and Restart for a fresh exact confirmation"
                )
            # Capture immutable local references inside the lock.
            confirmation_path = self.p4_confirmation_path
            runtime_output_dir = self.p4_runtime_output_dir
            service = self.live_repair
            canonical_runner = service.runtime_runner

            def adapted_runner(root: Path, **kwargs: Any) -> Mapping[str, Any]:
                canonical_proof = canonical_runner(root, **kwargs)
                return _adapt_runtime_proof_identity(
                    canonical_proof,
                    identity=identity,
                    confirmation_path=confirmation_path,
                    repo_root=self.repo_root,
                    required_assets=self.p4_required_assets,
                )

            service.runtime_runner = adapted_runner
            try:
                result = service.execute_replay(
                    packet_id=packet_id,
                    profile_path=_RUNTIME_PROFILE,
                    confirmation_packet=confirmation_path,
                    output_dir=runtime_output_dir,
                )
            finally:
                service.runtime_runner = canonical_runner
            if result.get("ok") is not True:
                raise PascalPresentationError("P4 Runtime Profile V2 proof did not satisfy every obligation")
            self.p4_confirmation_consumed = True
        return result

    def dissolve_p4_runtime(self) -> dict[str, Any]:
        with self._p4_runtime_lock:
            service = self._live_repair
            before = service.status() if service is not None else {
                "active_capture_count": 0,
                "pending_packet_archive_count": 0,
            }
            if before.get("active_capture_count") != 0:
                raise PascalPresentationError("P4 cannot dissolve while a bounded capture remains active")
            if before.get("pending_packet_archive_count") != 0:
                raise PascalPresentationError("P4 cannot dissolve while incident archival remains pending")
            if service is not None:
                service.close()
                self._live_repair = None
            self.p4_u7_bridge._sessions.clear()
            removed_roots = self._cleanup_external_roots()
        return {
            "ok": True,
            "status": "DISSOLVED",
            "live_repair_service_released": service is not None,
            "active_captures_before_release": int(before.get("active_capture_count") or 0),
            "pending_archives_before_release": int(before.get("pending_packet_archive_count") or 0),
            "external_runtime_roots_removed": removed_roots,
            "u7_sessions_cleared": True,
            "listeners_released": True,
            "timers_released": True,
            "buffers_cleared": True,
            "construction_state_unchanged": True,
            "production_mutation": False,
            "automatic_promotion": False,
        }

    @property
    def p4_available(self) -> bool:
        return (
            self.p3_available
            and self.p4_identity is not None
            and self.p4_confirmation_path is not None
            and self.p4_runtime_output_dir is not None
            and self.p4_director is not None
            and set(self.p4_static_assets) == set(_P4_STATIC_PATHS)
            and len(self.p4_required_assets) == len(_P4_SOURCE_ASSETS)
        )

    def require_p4(self) -> ConstructionFoundryDirector:
        if not self.p4_available or self.p4_director is None:
            raise PascalPresentationError("P4 Director is unavailable; the P3 Foundry remains active")
        return self.p4_director

    def close(self) -> None:
        with self._p4_runtime_lock:
            if self.p4_director is not None:
                self.p4_director.close()
            self.p4_director = None
            self.p4_static_assets.clear()
            self.p4_required_assets = ()
            self.p4_u7_bridge._sessions.clear()
            self._cleanup_external_roots()
        super().close()


def _projection_and_identity(state: P4FoundryShowcaseState, body: Mapping[str, Any], *, require_all: bool) -> tuple[dict[str, Any], BilateralIdentity]:
    projection = state.require_p3().compile()
    _assert_exact_identities_from_projection(projection, body, require_all=require_all)
    identity = state.resolve_request_identity(body, expected=state.p4_identity)
    return projection, identity


def _initial_evidence(
    state: P4FoundryShowcaseState,
    projection: Mapping[str, Any],
) -> dict[str, bool]:
    domain = projection.get("domain")
    artifacts = projection.get("artifacts")
    candidates = projection.get("coordination_candidates")
    decision = projection.get("domain_decision")
    authority = projection.get("authority")
    if not all(isinstance(item, Mapping) for item in (domain, artifacts, decision, authority)):
        raise PascalPresentationError("P4 requires the exact complete P3 projection contract")
    compare = artifacts.get("compare_receipt")
    if not isinstance(compare, Mapping):
        raise PascalPresentationError("P4 requires the exact P3 compare receipt")
    forbidden_authority = (
        "survey_authority",
        "professional_approval",
        "physical_work_authorized",
        "payment_released",
        "access_granted",
        "automatic_execution",
        "source_records_mutated",
        "construction_event_appended",
    )
    return {
        "p3_available": state.p3_available,
        "construction_identity_bound": bool(domain.get("state_digest") and domain.get("runtime_packet_digest")),
        "pascal_artifact_bound": bool(artifacts.get("pascal_artifact_digest")),
        "coordinate_receipt_bound": bool(artifacts.get("coordinate_receipt_digest")),
        "as_built_scene_bound": bool(artifacts.get("as_built_scene_digest")),
        "compare_receipt_bound": (
            compare.get("visual_alignment_only") is True
            and compare.get("survey_authority") is False
            and compare.get("construction_truth") is False
            and compare.get("receipt_digest")
            == stable_digest(
                {key: value for key, value in compare.items() if key != "receipt_digest"},
                digest_size=32,
            )
        ),
        "construction_candidates_bound": (
            isinstance(candidates, list)
            and len(candidates) == 3
            and all(
                isinstance(item, Mapping)
                and isinstance(item.get("artifact"), Mapping)
                and bool(item["artifact"].get("candidate_id"))
                and bool(item["artifact"].get("candidate_digest"))
                for item in candidates
            )
        ),
        "domain_decision_bound": (
            decision.get("human_review_required") is True
            and all(decision.get(name) is False for name in (
                "physical_work_authorized",
                "professional_approval",
                "payment_released",
                "access_granted",
                "automatic_execution",
                "survey_authority",
                "construction_truth",
            ))
            and all(authority.get(name) is False for name in forbidden_authority)
        ),
        "identity_current": True,
        "operator_authorized": True,
        "fault_fixture_bound": True,
        "required_assets_bound": bool(state.p4_required_assets),
        "rollback_adapter_ready": True,
        "u7_bridge_ready": True,
        "construction_state_unchanged": True,
        "capture_resources_dissolved": False,
    }


def _start_exact_session(
    state: P4FoundryShowcaseState,
    projection: Mapping[str, Any],
    identity: BilateralIdentity,
) -> dict[str, Any]:
    director = state.require_p4()
    session = director.start_session(
        identity_digest=identity.identity_digest,
        construction_state_digest=str(projection["domain"]["state_digest"]),
        initial_evidence=_initial_evidence(state, projection),
    )
    return {"ok": True, "session": session, "manifest": director.manifest.to_dict()}


def _session_start(state: P4FoundryShowcaseState, body: Mapping[str, Any]) -> dict[str, Any]:
    with state._p4_runtime_lock:
        if state.p4_confirmation_consumed:
            raise PascalPresentationError(
                "P4 confirmation was already consumed; use Restart after dissolution"
            )
        allowed = frozenset({"identity_handle", *_IDENTITY_KEYS})
        unknown = sorted(set(body) - allowed)
        if unknown:
            raise PascalPresentationError(f"P4 session start contains unknown fields: {unknown}")
        projection, identity = _projection_and_identity(state, body, require_all=True)
        return _start_exact_session(state, projection, identity)


def _execute_chapter(state: P4FoundryShowcaseState, session_id: str, transition: Mapping[str, Any]) -> dict[str, Any]:
    director = state.require_p4()
    session = director.require_session(session_id)
    chapter = director.manifest.chapter(str(dict(transition["chapter"])["chapter_id"]))
    fixture = director.manifest.fault_fixture
    identity = state._current_demo_identity()
    context = session.context
    evidence: dict[str, bool] = {}
    updates: dict[str, Any] = {}
    effect = chapter.effect
    _pending_capture_id: str | None = None
    if effect in {"FRAME_CONSTRUCTION", "SET_VIEW", "FOCUS_CANDIDATES", "RETURN_CONSTRUCTION"}:
        result = {"ok": True, "effect": effect, "ui_directive": dict(chapter.ui_directive), "projection_only": True}
    elif effect == "START_CAPTURE":
        result = state.live_repair.start_capture({
            "identity": asdict(identity),
            "release_id": P4_FOUNDRY_SERVER_VERSION,
            "environment_id": "loopback-p4-director",
            "capture_authorized": True,
            "max_events": 32,
            "retention_seconds": 300,
            "arena_id": "construction",
        })
        updates["capture_id"] = result["capture_id"]
        evidence.update({"capture_active": True, "capture_resources_dissolved": False})
        # If commit_next fails after start_capture has mutated service state,
        # clean up the orphaned capture before re-raising.
        _pending_capture_id = result["capture_id"]
    elif effect == "MARK_INCIDENT":
        capture_id = str(context.get("capture_id") or "")
        state.live_repair.observe(capture_id, fixture.event_type, {"fixture_id": fixture.fixture_id, "selection_sync": "STALE_ACKNOWLEDGEMENT"})
        result = state.live_repair.mark(capture_id, fixture.marker, {"fixture_id": fixture.fixture_id})
        evidence["incident_marker_present"] = True
    elif effect == "FINALIZE_CAPTURE":
        capture_id = str(context.get("capture_id") or "")
        result = state.live_repair.finalize_capture(capture_id, {
            "expected_positive": _POSITIVE,
            "expected_negative": (_AUTHORITY_NEGATIVE, *_FAULT_NEGATIVES),
            "preservation_claims": (_PRESERVATION,),
            "required_assets": [item.to_dict() for item in state.p4_required_assets],
            "arena_id": "construction",
            "objective": "Retain one exact P4 presentation fault without changing Construction truth",
        })
        packet = dict(result["packet"])
        updates["packet_id"] = packet["packet_id"]
        updates["packet_digest"] = packet["packet_digest"]
        evidence.update({"capture_dissolved": True, "replay_packet_retained": True, "capture_resources_dissolved": True})
    elif effect == "RUN_RUNTIME_REPLAY":
        packet_id = str(context.get("packet_id") or "")
        result = state.execute_exact_runtime_replay(
            packet_id=packet_id,
            identity=identity,
        )
        updates["runtime_proof_ref"] = result["runtime_proof_ref"]
        evidence["runtime_proof_retained"] = True
    elif effect == "RECORD_REPAIR_ATTEMPT":
        packet_id = str(context.get("packet_id") or "")
        result_obj = state.live_repair.record_repair_attempt(
            packet_id=packet_id,
            hypothesis=fixture.hypothesis,
            candidate_digest=fixture.runtime_candidate_digest,
            runtime_proof_ref=str(context.get("runtime_proof_ref") or ""),
            minimized_counterexample={"fixture_id": fixture.fixture_id, "selection_synchronized": False},
            current_identity=identity,
            arena_id="construction",
        )
        result = {"ok": True, "attempt": result_obj.to_dict(), "route_class": result_obj.route_class}
        updates["candidate_digest"] = result_obj.candidate_digest
        evidence["repair_attempt_retained"] = True
    elif effect == "PREVIEW_DEGRADED":
        packet_id = str(context.get("packet_id") or "")
        receipt = state.live_repair.preview_candidate(
            packet_id=packet_id,
            current_identity=identity,
            candidate_digest=str(context.get("candidate_digest") or fixture.runtime_candidate_digest),
            last_verified_digest=fixture.last_verified_digest,
            health_before=fixture.degraded_health_before,
            health_after=fixture.degraded_health_after,
            environment_class="LOCAL_EPHEMERAL",
            rollback_preauthorized=True,
            rollback_reason=fixture.rollback_reason,
            restore_local=lambda expected: expected,
        )
        result = {"ok": True, "preview": receipt.to_dict()}
        updates["rollback_preview_id"] = receipt.preview_id
        evidence["rollback_receipt_retained"] = True
    elif effect == "PREVIEW_SUCCESS":
        packet_id = str(context.get("packet_id") or "")
        receipt = state.live_repair.preview_candidate(
            packet_id=packet_id,
            current_identity=identity,
            candidate_digest=str(context.get("candidate_digest") or fixture.runtime_candidate_digest),
            last_verified_digest=fixture.last_verified_digest,
            health_before=fixture.successful_health_before,
            health_after=fixture.successful_health_after,
            environment_class="LOCAL_EPHEMERAL",
            rollback_preauthorized=False,
        )
        result = {"ok": True, "preview": receipt.to_dict()}
        updates["successful_preview_id"] = receipt.preview_id
        evidence["successful_preview_retained"] = True
    elif effect == "RUN_GOVERNED_U7":
        packet_id = str(context.get("packet_id") or "")
        packet = state.live_repair.packet(packet_id)
        candidate = str(context.get("candidate_digest") or fixture.runtime_candidate_digest)
        phase = stable_digest({"packet_id": packet_id, "candidate_digest": candidate, "phase": "P4_CURRENT_REPROOF"})
        task_id = "construction-foundry-p4-current-reproof"
        observed_at = time.time()
        state.p4_u7_bridge.prepare(
            phase=phase,
            task_id=task_id,
            packet_digest=packet.packet_digest,
            candidate_digest=candidate,
            observed_at=observed_at,
        )
        result = state.live_repair.run_governed_u7(
            packet_id=packet_id,
            candidate_digest=candidate,
            current_identity=identity,
            bridge=state.p4_u7_bridge,
            plan_phase_hash=phase,
            task_id=task_id,
            prediction_contract=_p4_prediction_contract(observed_at, packet.packet_digest, candidate),
            observation_contract=_p4_observation_contract(observed_at, packet.packet_digest, candidate),
            finalization_contract=_p4_finalization_contract(observed_at, packet.packet_digest, candidate),
        )
        updates["u7_result"] = result
        evidence["human_disposition_retained"] = True
    elif effect == "DISSOLVE":
        packet_id = str(context.get("packet_id") or "")
        if packet_id:
            state.live_repair.assert_current_identity(packet_id)
        result = state.dissolve_p4_runtime()
        evidence["runtime_resources_dissolved"] = True
    else:
        raise PascalPresentationError(f"unsupported P4 chapter effect: {effect}")
    _claim_token = str(transition.get("claim_token") or "")
    try:
        return director.commit_next(
            session_id,
            transition_digest=str(transition["transition_digest"]),
            effect_receipt=result,
            claim_token=_claim_token,
            evidence_updates=evidence,
            context_updates=updates,
        )
    except Exception as exc:
        # Release the transition claim so the session is not permanently stuck.
        # Pass the claim_token so a stale error path cannot release a newer
        # claim that belongs to a different request.
        director.release_claim(session_id, claim_token=_claim_token)
        if _pending_capture_id is not None:
            try:
                cleanup_result = state.live_repair.finalize_capture(_pending_capture_id, {
                    "expected_positive": (),
                    "expected_negative": (),
                    "preservation_claims": (),
                    "required_assets": [],
                    "arena_id": "construction",
                    "objective": "Orphaned-capture cleanup after failed Director commit (uncommitted transition)",
                })
                # Persist the orphan-cleanup receipt in the Director failure
                # ledger via a lock-protected API so the archive artifact is
                # traceable to the failed transition even if context mutation
                # would race with session close.
                orphan_receipt = {
                    "orphaned_capture_id": _pending_capture_id,
                    "orphan_cleanup_result": cleanup_result,
                    "orphan_status": "UNCOMMITTED_TRANSITION_CLEANUP",
                    "director_commit_failed": True,
                    "original_error": str(exc),
                }
                director.record_failure_ledger(session_id, orphan_receipt)
            except Exception as cleanup_exc:
                # Cleanup evidence must not be hidden.  Attach the cleanup
                # failure to the re-raised error so it remains observable.
                # Chain from the original commit failure so the full
                # exception context is preserved.
                raise RuntimeError(
                    f"P4 Director commit failed ({exc}) and orphaned capture "
                    f"{_pending_capture_id} could not be released: {cleanup_exc}"
                ) from exc
        raise


def dispatch_p4_foundry_request(
    state: P4FoundryShowcaseState,
    method: str,
    raw_path: str,
    payload: Mapping[str, Any] | None = None,
    *,
    request_origin: str | None = None,
    request_host: str | None = None,
) -> tuple[int, str, bytes]:
    route = urlparse(raw_path).path.rstrip("/") or "/"
    if not route.startswith("/api/construction/director"):
        return dispatch_p3_foundry_request(
            state,
            method,
            raw_path,
            payload,
            request_origin=request_origin,
            request_host=request_host,
        )
    body = dict(payload or {})
    try:
        _validate_request_context(
            state,
            method,
            request_origin=request_origin,
            request_host=request_host,
        )
        if method == "GET" and route == "/api/construction/director/status":
            director = state.p4_director if state.p4_available else None
            return _json(200 if state.p4_available else 503, {
                "ok": state.p4_available,
                "available": state.p4_available,
                "reason": state.p4_load_error,
                "p4_server_version": P4_FOUNDRY_SERVER_VERSION,
                "p3_fallback_available": state.p3_available,
                "manifest_digest": director.manifest.manifest_digest if director is not None else "",
                "offline_deterministic": True,
                "human_review_required": True,
                "automatic_execution": False,
                "physical_work_authorized": False,
            })
        director = state.require_p4()
        if method == "GET" and route == "/api/construction/director/manifest":
            return _json(200, {"ok": True, "manifest": director.manifest.to_dict()})
        if method == "POST" and route == "/api/construction/director/session/start":
            return _json(200, _session_start(state, body))
        if route.startswith("/api/construction/director/session/"):
            suffix = route.removeprefix("/api/construction/director/session/")
            parts = suffix.split("/")
            session_id = parts[0]
            if method == "GET" and len(parts) == 1:
                _resolved_projection, resolved_identity = _projection_and_identity(
                    state, _query_projection_body(raw_path), require_all=True,
                )
                target_session = director.require_session(session_id)
                if resolved_identity.identity_digest != target_session.identity_digest:
                    raise PascalPresentationError(
                        "resolved identity does not match the session's bound identity"
                    )
                return _json(200, {"ok": True, "session": target_session.snapshot(director.manifest), "receipts": director.receipts(session_id)})
            if method == "POST" and len(parts) == 2 and parts[1] == "prepare-p3-sync":
                # Resolve the bilateral identity and return the binding
                # values the browser needs to call P3 project for presentation
                # retention.  This separates evidence creation (browser-driven
                # P3 project after waitForP3View) from evidence validation
                # (ack-p3-sync which only looks up the retained record).
                _resolved, resolved_identity = _projection_and_identity(state, body, require_all=True)
                _target = director.require_session(session_id)
                if resolved_identity.identity_digest != _target.identity_digest:
                    raise PascalPresentationError(
                        "resolved identity does not match the session's bound identity"
                    )
                _last_receipt = _target.receipts[-1] if _target.receipts else {}
                _last_chapter_id = _last_receipt.get("chapter_id", "")
                _required_chapter = director.manifest.chapter(_last_chapter_id)
                _required_view = dict(_required_chapter.ui_directive or {}).get("active_view")
                _director_receipt_digest = str(_last_receipt.get("receipt_digest") or _last_receipt.get("transition_digest") or "")
                # Write a one-time nonce to P3 state that the project route
                # must consume.  This ties retention to a prepare-p3-sync call
                # and makes the project route's retention a consumed, one-time
                # server event rather than a replayable caller assertion.
                _sync_nonce = secrets.token_hex(16)
                if not hasattr(state, "_p3_sync_nonces"):
                    state._p3_sync_nonces = {}
                _sync_key = f"{session_id}:{_director_receipt_digest}"
                # Store a complete server-owned synchronization record.
                # The nonce is consumed during P3 /project (PREPARED→PROJECTED).
                # A separate confirm-presentation step (PROJECTED→RENDER_CONFIRMED)
                # is required before ack-p3-sync can clear the gate.
                state._p3_sync_nonces[_sync_key] = {
                    "state": "PREPARED",
                    "sync_nonce": _sync_nonce,
                    "director_session_id": session_id,
                    "director_receipt_digest": _director_receipt_digest,
                    "chapter_id": _last_chapter_id,
                    "required_view": _required_view,
                    "identity_digest": resolved_identity.identity_digest,
                    "projection_digest": "",
                    "presentation_revision": "",
                    "presentation_receipt_digest": "",
                }
                return _json(200, {
                    "ok": True,
                    "identity_digest": resolved_identity.identity_digest,
                    "director_session_id": session_id,
                    "director_receipt_digest": _director_receipt_digest,
                    "chapter_id": _last_chapter_id,
                    "active_view": _required_view,
                    "sync_nonce": _sync_nonce,
                })
            if method == "POST" and len(parts) == 2 and parts[1] == "ack-p3-sync":
                _resolved, resolved_identity = _projection_and_identity(state, body, require_all=True)
                _target = director.require_session(session_id)
                if resolved_identity.identity_digest != _target.identity_digest:
                    raise PascalPresentationError(
                        "resolved identity does not match the session's bound identity"
                    )
                _presentation_receipt = body.get("presentation_receipt")
                if not isinstance(_presentation_receipt, Mapping):
                    raise PascalPresentationError("P3 presentation receipt is required and must be an object")
                # ack-p3-sync performs LOOKUP/VALIDATION ONLY.  It does NOT
                # call P3 project or P3 issue — those would create the evidence
                # being validated.  The browser must have already called P3
                # project (after waitForP3View) to create the retained record.
                _target_session = director.require_session(session_id)
                _last_receipt = _target_session.receipts[-1] if _target_session.receipts else {}
                _last_chapter_id = _last_receipt.get("chapter_id", "")
                _required_chapter = director.manifest.chapter(_last_chapter_id)
                _required_view = dict(_required_chapter.ui_directive or {}).get("active_view")
                _director_receipt_digest = str(_last_receipt.get("receipt_digest") or _last_receipt.get("transition_digest") or "")
                # Call P3 validate ONLY — lookup of an already-retained record.
                _p3_validate_body = {
                    "chapter_id": _presentation_receipt.get("chapter_id", _last_chapter_id),
                    "receipt_digest": _presentation_receipt.get("receipt_digest", ""),
                    "director_session_id": session_id,
                    "director_receipt_digest": _director_receipt_digest,
                }
                _p3_status, _, _p3_resp = dispatch_p3_foundry_request(
                    state, "POST",
                    "/api/construction/decision-lane/validate-presentation-receipt",
                    _p3_validate_body,
                    request_origin=state.presentation_origin,
                    request_host=state.presentation_netloc,
                )
                if _p3_status != 200:
                    raise PascalPresentationError("P3 presentation receipt validation failed — no retained record matches")
                _p3_retained = json.loads(_p3_resp).get("presentation_receipt", {})
                # Validate ALL retained receipt binding fields.
                if _p3_retained.get("director_session_id") != session_id:
                    raise PascalPresentationError("P3 receipt director_session_id does not match target session")
                if _p3_retained.get("chapter_id") != _last_chapter_id:
                    raise PascalPresentationError("P3 receipt chapter_id does not match last committed chapter")
                if _required_view and _p3_retained.get("active_view") != _required_view:
                    raise PascalPresentationError("P3 receipt active_view does not match required presentation view")
                if _p3_retained.get("identity_digest") != resolved_identity.identity_digest:
                    raise PascalPresentationError("P3 receipt identity does not match resolved identity")
                if _p3_retained.get("director_receipt_digest") != _director_receipt_digest:
                    raise PascalPresentationError("P3 receipt director_receipt_digest does not match last committed receipt digest")
                # Use the P3-retained receipt as authoritative.
                _presentation_receipt = dict(_p3_retained)
                # Perform the Director acknowledgement FIRST — it can raise
                # if the receipt is invalid, the session identity doesn't
                # match, or the manifest-required view is wrong.  Only
                # after it succeeds do we transition the sync record.
                _ack_result = director.acknowledge_p3_sync(
                    session_id,
                    presentation_receipt=_presentation_receipt,
                )
                # Transition: RENDER_CONFIRMED → ACKNOWLEDGED.
                _sync_map = getattr(state, "_p3_sync_nonces", None)
                _sync_key = f"{session_id}:{_director_receipt_digest}"
                if _sync_map and _sync_key in _sync_map:
                    _sync_map[_sync_key]["state"] = "ACKNOWLEDGED"
                return _json(200, _ack_result)
            if method == "POST" and len(parts) == 2 and parts[1] == "control":
                allowed = {"control", "chapter_id", "identity_handle", *_IDENTITY_KEYS}
                unknown = sorted(set(body) - allowed)
                if unknown:
                    raise PascalPresentationError(f"P4 control request contains unknown fields: {unknown}")
                _resolved, resolved_identity = _projection_and_identity(state, body, require_all=True)
                _target = director.require_session(session_id)
                if resolved_identity.identity_digest != _target.identity_digest:
                    raise PascalPresentationError(
                        "resolved identity does not match the session's bound identity"
                    )
                control = DirectorControl(str(body.get("control") or "").upper())
                if control is DirectorControl.RESTART:
                    prior = director.require_session(session_id)
                    if not prior.dissolved:
                        raise PascalPresentationError("Restart requires the prior presentation session to be dissolved")
                    identity = state.refresh_demo_identity()
                    projection = state.require_p3().compile()
                    restarted = _start_exact_session(state, projection, identity)
                    restarted["restarted_from_session_id"] = session_id
                    restarted["identity_summary"] = state.issue_current_identity_summary()
                    return _json(200, restarted)
                if control in {DirectorControl.PLAY, DirectorControl.PAUSE, DirectorControl.PREVIOUS, DirectorControl.JUMP}:
                    return _json(200, director.control(session_id, control=control, chapter_id=str(body.get("chapter_id") or "")))
                prior = director.require_session(session_id)
                browsing_retained_chapter = prior.selected_index < prior.executed_index
                navigation = director.control(session_id, control=DirectorControl.NEXT)
                if browsing_retained_chapter:
                    return _json(200, navigation)
                transition = director.claim_next(session_id)
                if transition.get("admitted") is not True:
                    return _json(409, {"ok": False, "error": "P4 transition is blocked", "transition": transition})
                try:
                    return _json(200, _execute_chapter(state, session_id, transition))
                except Exception:
                    # Release the claim if the effect itself threw before
                    # commit_next could run, so the session is not stuck.
                    # Pass the claim_token so we only release OUR claim, not
                    # a newer one from a different request.
                    director.release_claim(session_id, claim_token=str(transition.get("claim_token") or ""))
                    raise
        return _error("unknown P4 Construction Director route", 404)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError, json.JSONDecodeError, BilateralLiveRepairError, PascalPresentationError, TypeError, ValueError, KeyError, OverflowError) as exc:
        return _error(str(exc), 409)


def _static_response(route: str, state: P4FoundryShowcaseState | None = None) -> tuple[int, str, bytes]:
    normalized = route.lstrip("/")
    if normalized in _P4_STATIC_PATHS:
        if state is None or not state.p4_available:
            return _error("P4 static asset is unavailable", 404)
        body = state.p4_static_assets.get(normalized)
        if body is None:
            return _error("P4 static asset is unavailable", 404)
        return (200, "application/javascript; charset=utf-8", body) if normalized.endswith(".js") else (200, "text/css; charset=utf-8", body)
    status, content_type, body = p3_static_response(route, state)
    if status == 200 and route in {"/", "/index.html"} and state is not None and state.p4_available:
        lower = body.lower()
        if b"construction-foundry-director.css" not in lower:
            anchor = lower.find(b"</head>")
            if anchor < 0:
                return _error("P3 markup lacks a </head> anchor for P4 injection", 500)
            body = body[:anchor] + _P4_STYLE + body[anchor:]
            lower = body.lower()
        if b'id="construction-foundry-director"' not in lower:
            anchor = lower.find(b'id="construction-decision-foundry"')
            if anchor < 0:
                return _error("P3 markup lacks a Construction decision anchor for P4 injection", 500)
            section = lower.rfind(b"<section", 0, anchor)
            if section < 0:
                return _error("P3 markup lacks a section boundary for P4 injection", 500)
            body = body[:section] + _P4_MARKUP + b"\n  " + body[section:]
            lower = body.lower()
        if b"construction-foundry-director.js" not in lower:
            anchor = lower.find(b"</body>")
            if anchor < 0:
                return _error("P3 markup lacks a </body> anchor for P4 injection", 500)
            body = body[:anchor] + _P4_SCRIPT + body[anchor:]
    return status, content_type, body


def _content_security_policy(route: str) -> str | None:
    retained = p3_content_security_policy(route)
    if retained is not None:
        return retained
    if route in {"/construction-foundry-director.js", "/construction-foundry-director.css"}:
        return "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    return None


def make_handler(state: P4FoundryShowcaseState):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, body: bytes, *, route: str) -> None:
            self.send_response(status)
            for name, value in (
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
            ):
                self.send_header(name, value)
            policy = _content_security_policy(route)
            if policy is not None:
                self.send_header("Content-Security-Policy", policy)
            self.end_headers()
            self.wfile.write(body)

        def _payload(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
            except (TypeError, ValueError) as exc:
                raise PascalPresentationError("Content-Length must be a valid integer") from exc
            if length < 0 or length > MAX_BODY_BYTES:
                raise PascalPresentationError(f"request body must be between 0 and {MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise PascalPresentationError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            route = urlparse(self.path).path
            response = dispatch_p4_foundry_request(
                state,
                "GET",
                self.path,
                request_origin=self.headers.get("Origin"),
                request_host=self.headers.get("Host"),
            ) if route.startswith("/api/") else _static_response(route, state)
            self._send(*response, route=route)

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            try:
                payload = self._payload()
            except (UnicodeDecodeError, json.JSONDecodeError, PascalPresentationError) as exc:
                self._send(*_error(str(exc), 400), route=route)
                return
            response = dispatch_p4_foundry_request(
                state,
                "POST",
                self.path,
                payload,
                request_origin=self.headers.get("Origin"),
                request_host=self.headers.get("Host"),
            )
            self._send(*response, route=route)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    return Handler


def serve(*, host: str, port: int, repo_root: str | Path, demo_project: str, auto_start: bool, asset_pack_path: str | Path | None = None) -> None:
    origin_host = "[::1]" if host == "::1" else host
    origin = _loopback_origin(f"http://{origin_host}:{port}")
    state = P4FoundryShowcaseState(
        repo_root,
        demo_project=demo_project,
        auto_start=auto_start,
        presentation_origin=origin,
        asset_pack_path=asset_pack_path,
    )
    server_type = IPv6HTTPServer if host == "::1" else HTTPServer
    server = server_type((host, port), make_handler(state))
    try:
        print(f"Aura Construction Pascal Spatial Foundry P4: {origin}")
        server.serve_forever()
    finally:
        server.server_close()
        state.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--demo-project", default="winnipeg_pathways")
    parser.add_argument("--asset-pack")
    parser.add_argument("--no-auto-start", action="store_true")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, repo_root=args.repo_root, demo_project=args.demo_project, auto_start=not args.no_auto_start, asset_pack_path=args.asset_pack)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "P4_FOUNDRY_SERVER_VERSION",
    "P4FoundryShowcaseState",
    "dispatch_p4_foundry_request",
    "make_handler",
    "serve",
]
