"""
Aura Refactor Candidate — detect practical coding candidates from change graphs.
Advisory only — cannot authorize patching.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
CANDIDATE_VERSION = "AURA_REFACTOR_CANDIDATE_V1"

def detect_refactor_candidates(change_graph: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    candidates = []
    obj = change_graph.get("objective", "")
    files = change_graph.get("files", [])
    symbols = change_graph.get("symbols", [])
    tests = change_graph.get("tests", [])
    risks = change_graph.get("risks", [])
    if files and symbols:
        candidates.append({
            "candidate_id": "C1", "title": f"Refactor {symbols[0] if symbols else files[0]}",
            "objective": obj, "candidate_type": "refactor",
            "target_files": files[:3], "target_symbols": symbols[:3],
            "required_tests": tests, "current_evidence": ["change_graph"],
            "missing_evidence": ["grounding_ok", "exact_source_spans"],
            "risk_level": "medium", "estimated_tokens_to_patch": 2000,
            "suggested_work_split": "single_pr", "suggested_agent": "hermes",
            "command_risk": "unchecked", "approval_required": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    if files and not tests:
        candidates.append({
            "candidate_id": "C2", "title": "Add tests for changed regions",
            "objective": obj, "candidate_type": "test_gap",
            "target_files": files[:2], "target_symbols": [],
            "required_tests": [], "current_evidence": ["change_graph"],
            "missing_evidence": ["test_coverage"],
            "risk_level": "low", "estimated_tokens_to_patch": 1000,
            "suggested_work_split": "single_pr", "suggested_agent": "hermes",
            "command_risk": "unchecked", "approval_required": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    if risks:
        candidates.append({
            "candidate_id": "C3", "title": "Address security risks",
            "objective": obj, "candidate_type": "security_hardening",
            "target_files": files[:2], "target_symbols": [],
            "required_tests": tests, "current_evidence": ["risk_nodes"],
            "missing_evidence": ["security_review"],
            "risk_level": "high", "estimated_tokens_to_patch": 1500,
            "suggested_work_split": "single_pr", "suggested_agent": "hermes",
            "command_risk": "needs_review", "approval_required": True,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    return {"ok": True, "version": CANDIDATE_VERSION, "objective": obj,
            "candidates": candidates, "candidate_count": len(candidates),
            "advisory_only": True,
            "note": "RefactorCandidate is advisory only. Must pass Coding Arena Grounding before Agent Arena handoff.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def candidate_to_grounding_requirement(candidate: dict) -> dict[str, Any]:
    return {"ok": True, "candidate_id": candidate.get("candidate_id",""),
            "required": ["exact_source_spans", "source_hashes", "tests", "verifier_gates"],
            "current": candidate.get("current_evidence", []),
            "missing": candidate.get("missing_evidence", []),
            "can_patch": False,
            "note": "Cannot patch without Coding Arena Grounding.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
