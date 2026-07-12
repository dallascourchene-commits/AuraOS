"""Phase C1 tests for deterministic polysynthetic intent and route capsules."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from aura_polysynthetic_intent import PolysyntheticIntentPacket, bind_intent_packet
from aura_route_capsule_binding import rank_admissible_capsules
from aura_route_capsule_compiler import compile_route_capsule
from aura_route_capsule_registry import load_registry_component, resolve_repository_reference
from aura_vsa_encoding_profile import (
    DEFAULT_COMPLEX_PHASOR_V1,
    bind,
    cosine,
    seeded_hv,
    unbind,
    vector_digest,
)


def _write(repo: Path, rel: str, payload: dict) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def _fixture_repo(repo: Path, *, capability: str = "tool:topology_inspector") -> None:
    components = {
        ".aura/morphology_profiles/six_slot.v1.json": {
            "schema_version": "AURA_MORPHOLOGY_PROFILE_V1", "component_id": "six_slot.v1", "kind": "morphology_profile",
            "slot_order": ["DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"],
        },
        ".aura/vsa_profiles/complex_phasor.v1.json": {
            "schema_version": "AURA_VSA_ENCODING_PROFILE_V1", "component_id": "complex_phasor.v1", "kind": "vsa_profile",
            "profile_id": "AURA_COMPLEX_PHASOR_V1", "dimensions": 10000, "dtype": "complex64",
            "binding": "elementwise_multiply", "unbinding": "conjugate_multiply", "bundling": "normalized_sum",
            "permutation": "cyclic_shift", "permutation_shift": 4097, "normalization": "l2", "seed_scheme": "blake2b-64",
        },
        ".aura/data_apertures/localize.v1.json": {
            "schema_version": "AURA_DATA_APERTURE_V1", "component_id": "localize.v1", "kind": "data_aperture",
            "maximum_files": 8, "maximum_lines": 600,
        },
        ".aura/memory_apertures/localize.v1.json": {
            "schema_version": "AURA_MEMORY_APERTURE_V1", "component_id": "localize.v1", "kind": "memory_aperture",
            "maximum_experiences": 20,
        },
        ".aura/tool_bundles/localize.v1.json": {
            "schema_version": "AURA_TOOL_BUNDLE_V1", "component_id": "localize.v1", "kind": "tool_bundle",
            "requested_capabilities": [capability],
        },
        ".aura/model_policies/local_first.v1.json": {
            "schema_version": "AURA_MODEL_POLICY_V1", "component_id": "local_first.v1", "kind": "model_policy",
            "default": "no_model", "fallback": "local_model",
        },
        ".aura/execution_budgets/localize.v1.json": {
            "schema_version": "AURA_EXECUTION_BUDGET_V1", "component_id": "localize.v1", "kind": "execution_budget",
            "input_tokens": 6000, "output_tokens": 1500, "tool_calls": 8,
        },
        ".aura/verifier_contracts/localize.v1.json": {
            "schema_version": "AURA_VERIFIER_CONTRACT_V1", "component_id": "localize.v1", "kind": "verifier_contract",
            "required": ["exact_source_hashes", "focused_tests"],
        },
        ".aura/output_schemas/localization.v1.json": {
            "schema_version": "AURA_OUTPUT_SCHEMA_V1", "component_id": "localization.v1", "kind": "output_schema",
            "type": "LocalizationPacket",
        },
    }
    for rel, payload in components.items():
        _write(repo, rel, payload)
    _write(repo, ".aura/route_capsules/localize.v1.json", {
        "schema_version": "AURA_EXECUTABLE_ROUTE_CAPSULE_V1",
        "capsule_id": "CODING.LOCALIZE.V1", "capsule_version": "v1", "transition_id": "CODING.TASK_SCOPED.LOCALIZE_CODE",
        "morphology_profile_ref": ".aura/morphology_profiles/six_slot.v1.json",
        "vsa_profile_ref": ".aura/vsa_profiles/complex_phasor.v1.json",
        "data_aperture_ref": ".aura/data_apertures/localize.v1.json",
        "memory_aperture_ref": ".aura/memory_apertures/localize.v1.json",
        "tool_bundle_ref": ".aura/tool_bundles/localize.v1.json",
        "model_policy_ref": ".aura/model_policies/local_first.v1.json",
        "execution_budget_ref": ".aura/execution_budgets/localize.v1.json",
        "verifier_contract_ref": ".aura/verifier_contracts/localize.v1.json",
        "output_schema_ref": ".aura/output_schemas/localization.v1.json",
        "morphology_signature": {
            "DIR": "OUT", "ASP": "GROUND", "CLASS": "LOCALIZE",
            "SUBJ": "REPO", "VOICE": "HUMAN", "STEM": "INSPECT"
        },
        "routing_adjuncts": {},
        "requested_capabilities": [capability],
        "metadata": {"phase": "C1", "live_routing": False},
    })


def _resolver(ok: bool = True):
    def resolve(capabilities):
        if not ok:
            return {"ok": False, "bindings": [], "denials": [{"reason": "unbound"}]}
        return {"ok": True, "bindings": [{"capability_id": item, "grounded": True} for item in capabilities], "denials": []}
    return resolve


def test_seeded_hypervectors_are_cross_process_deterministic():
    expected = vector_digest(seeded_hv("same-label"))
    code = "from aura_vsa_encoding_profile import seeded_hv,vector_digest; print(vector_digest(seeded_hv('same-label')))"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONHASHSEED": "random"}
    actual = subprocess.check_output([sys.executable, "-c", code], text=True, env=env).strip()
    assert actual == expected


def test_bind_unbind_recovers_filler():
    role = seeded_hv("ROLE")
    filler = seeded_hv("FILLER")
    recovered = unbind(bind(role, filler), role)
    assert cosine(recovered, filler) > 0.999999


def test_profile_digest_is_stable():
    assert DEFAULT_COMPLEX_PHASOR_V1.digest() == DEFAULT_COMPLEX_PHASOR_V1.digest()
    assert len(DEFAULT_COMPLEX_PHASOR_V1.digest()) == 40


def test_intent_aliases_canonicalize_and_order_slots():
    packet = PolysyntheticIntentPacket.from_slots({
        "direction": "ROUTE", "aspect": "GROUND", "classifier": "LOCALIZE",
        "subject": "AuraOS", "voice": "HUMAN_AGENT", "stem": "INSPECT",
    }, adjuncts={"risk": "low", "cost": "bounded"}, objective="Find code")
    assert [name for name, _ in packet.slot_items()] == ["DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"]
    assert packet.canonical_dict()["slots"]["CLASS"] == "LOCALIZE"


def test_intent_rejects_missing_unknown_and_duplicate_aliases():
    with pytest.raises(ValueError, match="missing core slots"):
        PolysyntheticIntentPacket.from_slots({"DIR": "x"})
    with pytest.raises(ValueError, match="unknown core slot"):
        PolysyntheticIntentPacket.from_slots({**dict.fromkeys(["DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"], "x"), "RISK": "high"})
    with pytest.raises(ValueError, match="duplicate core slot"):
        PolysyntheticIntentPacket.from_slots({"DIR": "x", "DIRECTION": "y", "ASP": "x", "CLASS": "x", "SUBJ": "x", "VOICE": "x", "STEM": "x"})


def test_bound_intent_is_stable_and_does_not_claim_authority():
    packet = PolysyntheticIntentPacket.from_symbol_sequence(["OUT", "GROUND", "LOCALIZE", "REPO", "HUMAN", "INSPECT"])
    first = bind_intent_packet(packet)
    second = bind_intent_packet(packet)
    assert first.vector_digest == second.vector_digest
    assert first.to_dict()["routing_authority"] == "advisory_after_hard_guards"
    assert first.to_dict()["vsa_patch_authority"] is False


def test_registry_rejects_absolute_traversal_and_wrong_directory(tmp_path):
    _fixture_repo(tmp_path)
    with pytest.raises(ValueError, match="repository-relative"):
        resolve_repository_reference(tmp_path, "/tmp/x.json", field_name="data_aperture_ref")
    with pytest.raises(ValueError, match="traversal"):
        resolve_repository_reference(tmp_path, ".aura/data_apertures/../x.json", field_name="data_aperture_ref")
    with pytest.raises(ValueError, match="must remain under"):
        resolve_repository_reference(tmp_path, ".aura/tool_bundles/localize.v1.json", field_name="data_aperture_ref")


def test_registry_rejects_symlink_segments(tmp_path):
    _fixture_repo(tmp_path)
    target = tmp_path / "outside"
    target.mkdir()
    (target / "x.json").write_text("{}", encoding="utf-8")
    link = tmp_path / ".aura" / "data_apertures" / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symlinks"):
        resolve_repository_reference(tmp_path, ".aura/data_apertures/linked/x.json", field_name="data_aperture_ref")


def test_component_requires_identity_fields(tmp_path):
    path = tmp_path / ".aura/data_apertures/bad.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="requires schema_version"):
        load_registry_component(tmp_path, ".aura/data_apertures/bad.json", field_name="data_aperture_ref")


def test_capsule_compiles_with_grounded_capabilities(tmp_path):
    _fixture_repo(tmp_path)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    assert result.ok is True
    packet = result.compiled.to_dict()
    assert packet["automatic_activation"] is False
    assert packet["vsa_patch_authority"] is False
    assert len(packet["component_digests"]) == 9


def test_repository_example_capsule_compiles_with_real_binding():
    repo_root = Path(__file__).resolve().parents[1]
    result = compile_route_capsule(
        ".aura/route_capsules/coding_localize.v1.json",
        repo_root=repo_root,
    )
    assert result.ok, [item.to_dict() for item in result.diagnostics]
    assert result.compiled.capability_bindings


def test_capsule_digest_and_compilation_are_stable(tmp_path):
    _fixture_repo(tmp_path)
    first = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    second = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    assert first.compiled.capsule_manifest_digest == second.compiled.capsule_manifest_digest
    assert first.compiled.route_signature_digest == second.compiled.route_signature_digest


def test_capsule_fails_closed_on_unbound_capability(tmp_path):
    _fixture_repo(tmp_path)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver(False))
    assert result.ok is False
    assert result.diagnostics[0].code == "unbound_capability_bundle"


def test_capsule_rejects_tool_bundle_mismatch(tmp_path):
    _fixture_repo(tmp_path)
    payload = json.loads((tmp_path / ".aura/route_capsules/localize.v1.json").read_text())
    payload["requested_capabilities"] = []
    _write(tmp_path, ".aura/route_capsules/localize.v1.json", payload)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    assert result.ok is False
    assert result.diagnostics[0].code == "capability_bundle_mismatch"


def test_capsule_rejects_executable_fields(tmp_path):
    _fixture_repo(tmp_path)
    payload = json.loads((tmp_path / ".aura/route_capsules/localize.v1.json").read_text())
    payload["metadata"]["shell"] = "rm -rf /"
    _write(tmp_path, ".aura/route_capsules/localize.v1.json", payload)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    assert result.ok is False
    assert "forbidden" in result.diagnostics[0].message


def test_resonance_scores_only_pre_admitted_capsules(tmp_path):
    _fixture_repo(tmp_path)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    packet = PolysyntheticIntentPacket.from_symbol_sequence(["OUT", "GROUND", "LOCALIZE", "REPO", "HUMAN", "INSPECT"])
    intent = bind_intent_packet(packet)
    assert rank_admissible_capsules(intent, [result.compiled], admissible_capsule_ids=set(), repo_root=tmp_path) == []
    scored = rank_admissible_capsules(intent, [result.compiled], admissible_capsule_ids={"CODING.LOCALIZE.V1"}, repo_root=tmp_path)
    assert len(scored) == 1
    assert scored[0].routing_authority == "advisory_after_hard_guards"
    assert scored[0].resonance > 0.999


def test_compiled_capsule_detects_stale_profile_digest(tmp_path):
    _fixture_repo(tmp_path)
    result = compile_route_capsule(".aura/route_capsules/localize.v1.json", repo_root=tmp_path, capability_resolver=_resolver())
    profile_path = tmp_path / ".aura/vsa_profiles/complex_phasor.v1.json"
    payload = json.loads(profile_path.read_text())
    payload["permutation_shift"] = 7
    profile_path.write_text(json.dumps(payload), encoding="utf-8")
    packet = PolysyntheticIntentPacket.from_symbol_sequence(["OUT", "GROUND", "LOCALIZE", "REPO", "HUMAN", "INSPECT"])
    intent = bind_intent_packet(packet)
    with pytest.raises(ValueError, match="stale compiled capsule"):
        rank_admissible_capsules(intent, [result.compiled], admissible_capsule_ids={"CODING.LOCALIZE.V1"}, repo_root=tmp_path)
