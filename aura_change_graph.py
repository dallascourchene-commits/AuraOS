"""
Aura Change Graph — represent proposed coding changes as a graph.
Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import tokenize
from typing import Any, Mapping, Sequence

from aura_event_contracts import stable_digest

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
CHANGE_GRAPH_VERSION = "AURA_CHANGE_GRAPH_V1"

def _graph_id(objective: str) -> str:
    return hashlib.blake2b(objective.encode(), digest_size=8).hexdigest()

def build_change_graph(objective: str, localization_packet: dict | None = None, repo_root: str | Path = ".") -> dict[str, Any]:
    loc = localization_packet or {}
    files = loc.get("files", [])[:10]
    symbols = loc.get("symbols", [])[:10]
    tests = loc.get("tests", [])[:5]
    token_before = loc.get("raw_context_tokens_est", 0)
    token_after = loc.get("estimated_tokens", 0)
    comp_ratio = round(token_after / max(token_before, 1) * 100, 1) if token_before > 0 else 0.0
    jspace = {}
    try:
        from aura_jspace_codec import build_jspace_packet
        jp = build_jspace_packet({"intent": "code_refactor"}, {"route": "BUILDER_PATCH"})
        jspace = {"packet": jp.packet[:200]}
    except Exception: pass
    st3gg = {}
    try:
        from aura_arena_st3gg_codec import should_st3gg_encode_arena_capsule
        d = should_st3gg_encode_arena_capsule({"objective": objective})
        st3gg = {"enabled": d.enabled, "reason": d.reason}
    except Exception: pass
    return {
        "ok": True, "version": CHANGE_GRAPH_VERSION,
        "graph_id": _graph_id(objective), "objective": objective,
        "files": files, "symbols": symbols, "tests": tests,
        "dependencies": [], "risks": [], "command_risks": [], "agent_actions": [],
        "proposed_edges": [], "missing_edges": [],
        "required_evidence": ["grounding_ok", "tests_pass"],
        "token_cost_before": token_before, "token_cost_after": token_after,
        "compression_ratio": comp_ratio, "jspace_state": jspace, "st3gg_decision": st3gg,
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

def change_graph_from_regions(ranking_packet: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    return build_change_graph(ranking_packet.get("objective",""), ranking_packet, repo_root)

def add_test_nodes(graph: dict, tests: list[str]) -> dict:
    g = dict(graph); g["tests"] = list(set(g.get("tests",[]) + tests)); return g

def add_risk_nodes(graph: dict, risks: list[dict]) -> dict:
    g = dict(graph); g["risks"] = g.get("risks",[]) + risks; return g

def add_dependency_edges(graph: dict, deps: list[dict]) -> dict:
    g = dict(graph); g["dependencies"] = g.get("dependencies",[]) + deps; return g

def add_agent_action_nodes(graph: dict, actions: list[dict]) -> dict:
    g = dict(graph); g["agent_actions"] = g.get("agent_actions",[]) + actions; return g

def add_command_risk_nodes(graph: dict, risks: list[dict]) -> dict:
    g = dict(graph); g["command_risks"] = g.get("command_risks",[]) + risks; return g

def change_graph_to_act_capsules(graph: dict, repo_root: str | Path = ".") -> dict[str, Any]:
    if graph.get("graph_type") == "CODING_RELATIONSHIP_COMPASS":
        return compile_compass_act_capsules(graph)
    capsules = []
    for i, fp in enumerate(graph.get("files", [])[:5]):
        capsules.append({"task_id": f"A{i+1}", "target_file": fp, "objective": graph.get("objective",""),
                         "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY})
    return {"ok": True, "act_capsules": capsules, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def change_graph_to_token_report(graph: dict) -> dict[str, Any]:
    return {"ok": True, "token_cost_before": graph.get("token_cost_before",0),
            "token_cost_after": graph.get("token_cost_after",0),
            "compression_ratio": graph.get("compression_ratio",0),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def change_graph_to_review_packet(graph: dict) -> dict[str, Any]:
    return {"ok": True, "review_packet": {
        "files": graph.get("files",[]), "symbols": graph.get("symbols",[]),
        "tests": graph.get("tests",[]), "risks": graph.get("risks",[]),
        "command_risks": graph.get("command_risks",[])},
        "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


# ---------------------------------------------------------------------------
# C7 — typed Compass Change Graph, phase capsules, and Act Capsules
# ---------------------------------------------------------------------------

COMPASS_CHANGE_GRAPH_VERSION = "AURA_COMPASS_CHANGE_GRAPH_V1"
COMPASS_ACT_CAPSULE_VERSION = "AURA_COMPASS_ACT_CAPSULE_V1"
COMPASS_GROUNDING_RECEIPT_VERSION = "AURA_COMPASS_GROUNDING_RECEIPT_V1"


def _ordered_unique(values: Sequence[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def _node(node_type: str, payload: Mapping[str, Any], *, depends_on: Sequence[str] = ()) -> dict[str, Any]:
    body = {
        "node_type": str(node_type),
        "payload": dict(payload),
        "depends_on": _ordered_unique(depends_on),
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    return {"node_id": f"cgn_{stable_digest(body, digest_size=12)}", **body}


def _canonical_target_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "file_path": str(value.get("file_path") or ""),
        "symbol": str(value.get("symbol") or value.get("qualified_symbol") or ""),
        "line_start": int(value.get("line_start") or value.get("start_line") or 0),
        "line_end": int(value.get("line_end") or value.get("end_line") or 0),
        "source_hash": str(value.get("source_hash") or ""),
        "file_source_hash": str(value.get("file_source_hash") or ""),
    }


def _digest_matches(value: Any, supplied: str) -> bool:
    text = str(supplied or "")
    if not re.fullmatch(r"[0-9a-f]+", text) or len(text) % 2 or not 2 <= len(text) <= 128:
        return False
    return stable_digest(value, digest_size=len(text) // 2) == text


def _verify_target_source(repo_root: Path, binding: Mapping[str, Any]) -> None:
    file_path = str(binding.get("file_path") or "")
    relative = Path(file_path)
    if not file_path or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Compass grounding receipt contains a non-canonical target path")
    source_path = repo_root / relative
    if not source_path.is_file():
        raise ValueError(f"Compass grounding target is missing: {file_path}")
    try:
        with tokenize.open(source_path) as handle:
            source_text = handle.read()
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ValueError(f"Compass grounding target is unreadable: {file_path}") from exc
    actual_file_hash = hashlib.sha256(source_text.encode("utf-8", errors="replace")).hexdigest()
    if str(binding.get("file_source_hash") or "") != actual_file_hash:
        raise ValueError(f"Compass grounding file_source_hash mismatch: {file_path}")
    line_start = int(binding.get("line_start") or 0)
    line_end = int(binding.get("line_end") or 0)
    lines = source_text.splitlines()
    if line_start <= 0 or line_end < line_start or line_end > len(lines):
        raise ValueError(f"Compass grounding source span is invalid: {file_path}")
    actual_source_hash = hashlib.sha256(
        "\n".join(lines[line_start - 1 : line_end]).encode("utf-8", errors="replace")
    ).hexdigest()
    if str(binding.get("source_hash") or "") != actual_source_hash:
        raise ValueError(f"Compass grounding source_hash mismatch: {file_path}")


def _verify_grounding_receipt(
    compass_packet: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> tuple[list[dict[str, Any]], list[str], str]:
    receipt = compass_packet.get("grounding_receipt") or {}
    if not isinstance(receipt, Mapping):
        raise ValueError("Compass Change Graph requires a trusted grounding receipt")
    receipt_digest = str(compass_packet.get("grounding_receipt_digest") or "")
    if not receipt_digest or not _digest_matches(dict(receipt), receipt_digest):
        raise ValueError("Compass grounding receipt digest mismatch")
    grounding_digest = str(compass_packet.get("grounding_digest") or "")
    if (
        receipt.get("version") != COMPASS_GROUNDING_RECEIPT_VERSION
        or str(receipt.get("grounding_digest") or "") != grounding_digest
        or receipt.get("patch_authority") != PATCH_AUTHORITY
        or bool(receipt.get("vsa_patch_authority"))
        or not grounding_digest
    ):
        raise ValueError("Compass grounding receipt authority or identity mismatch")

    targets = [
        _canonical_target_binding(item)
        for item in compass_packet.get("recommended_targets", ()) or ()
        if isinstance(item, Mapping)
    ]
    bindings = [
        _canonical_target_binding(item)
        for item in receipt.get("target_bindings", ()) or ()
        if isinstance(item, Mapping)
    ]
    if len(targets) != len(list(compass_packet.get("recommended_targets", ()) or ())):
        raise ValueError("Compass recommended targets are not canonical mappings")
    if len(bindings) != len(list(receipt.get("target_bindings", ()) or ())):
        raise ValueError("Compass grounding target bindings are not canonical mappings")
    if targets != bindings:
        raise ValueError("Compass targets are not bound to the trusted grounding receipt")
    if not _digest_matches(bindings, str(receipt.get("source_evidence_digest") or "")):
        raise ValueError("Compass grounding source evidence digest mismatch")
    tests = _ordered_unique(compass_packet.get("required_tests", ()) or ())
    if tests != _ordered_unique(receipt.get("required_tests", ()) or ()):
        raise ValueError("Compass required tests are not bound to the grounding receipt")
    for binding in bindings:
        if not binding["file_path"]:
            raise ValueError("Compass grounding receipt target file_path is required")
        if binding["line_start"] <= 0 or binding["line_end"] < binding["line_start"]:
            raise ValueError("Compass grounding receipt exact source span is invalid")
        if not binding["source_hash"]:
            raise ValueError("Compass grounding receipt source_hash is required")
        if not binding["file_source_hash"]:
            raise ValueError("Compass grounding receipt file_source_hash is required")
        _verify_target_source(Path(repo_root).resolve(), binding)
    return bindings, tests, receipt_digest


def build_compass_change_graph(
    compass_packet: Mapping[str, Any],
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Compile exact grounded relationship intelligence into a proposal-only graph."""

    if not isinstance(compass_packet, Mapping) or not compass_packet.get("grounding_ok"):
        raise ValueError("Compass Change Graph requires grounded Compass evidence")
    objective = str(compass_packet.get("objective") or "").strip()
    compass_digest = str(compass_packet.get("grounding_digest") or "")
    if not objective or not compass_digest:
        raise ValueError("Compass Change Graph requires objective and grounding digest")
    targets, tests, grounding_receipt_digest = _verify_grounding_receipt(
        compass_packet,
        repo_root=repo_root,
    )
    adapters = _ordered_unique(compass_packet.get("required_adapters", ()) or ())
    prohibitions = [dict(item) for item in compass_packet.get("prohibitions", ()) or () if isinstance(item, Mapping)]
    risks = [dict(item) if isinstance(item, Mapping) else {"risk": str(item)} for item in (compass_packet.get("emergent_evidence") or {}).get("risk_map", ()) or ()]
    emergent = compass_packet.get("bounded_emergent_verification") or {}
    accepted_emergent = [dict(item) for item in emergent.get("accepted_candidates", ()) or () if isinstance(item, Mapping)]

    nodes: list[dict[str, Any]] = []
    action_ids: list[str] = []
    for index, target in enumerate(targets[:16], start=1):
        payload = {
            "task_id": f"CRC-A{index:02d}",
            "objective": objective,
            "target_file": str(target.get("file_path") or ""),
            "target_symbol": str(target.get("symbol") or ""),
            "line_start": int(target.get("line_start") or 0),
            "line_end": int(target.get("line_end") or 0),
            "source_hash": str(target.get("source_hash") or ""),
            "file_source_hash": str(target.get("file_source_hash") or ""),
            "tests": tests,
            "preconditions": ["exact source hash remains current", "C5 hard guards still pass"],
            "effects": ["proposal or exact-span Surgeon request only"],
            "rollback": ["discard proposal and restore the exact pre-change source hash"],
            "human_decision_required": True,
            "grounding_receipt_digest": grounding_receipt_digest,
        }
        item = _node("ACTION", payload)
        nodes.append(item)
        action_ids.append(item["node_id"])

    for test in tests:
        nodes.append(_node("TEST", {"test": test, "required": True}, depends_on=action_ids))
    for risk in risks:
        nodes.append(_node("RISK", risk, depends_on=action_ids))
    for adapter in adapters:
        nodes.append(_node("ADAPTER", {"adapter": adapter, "required": True}, depends_on=action_ids))
    for prohibition in prohibitions:
        nodes.append(_node("PROHIBITION", prohibition, depends_on=action_ids))
    for candidate in accepted_emergent:
        nodes.append(
            _node(
                "EXPERIMENT",
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "smallest_experiment": candidate.get("smallest_experiment"),
                    "failure_conditions": list(candidate.get("failure_conditions") or []),
                    "evidence_refs": list(candidate.get("evidence_refs") or []),
                },
                depends_on=action_ids,
            )
        )
    proof = _node(
        "PROOF",
        {
            "required_evidence": ["source_hash", "tests_pass", "verifier_receipt", "human_disposition"],
            "compass_digest": compass_digest,
        },
        depends_on=action_ids,
    )
    rollback = _node(
        "ROLLBACK",
        {"conditions": ["test failure", "source drift", "authority mismatch", "human denial"]},
        depends_on=[proof["node_id"]],
    )
    human = _node(
        "HUMAN_DECISION",
        {"allowed": ["APPROVE_FOR_SURGEON", "DENY", "DEFER", "REQUEST_EVIDENCE"]},
        depends_on=[proof["node_id"], rollback["node_id"]],
    )
    nodes.extend([proof, rollback, human])

    phase_capsules: list[dict[str, Any]] = []
    for phase_index in range(0, len(action_ids), 4):
        phase_actions = action_ids[phase_index : phase_index + 4]
        target_slice = targets[phase_index : phase_index + 4]
        invariant_payload = {
            "compass_digest": compass_digest,
            "grounding_receipt_digest": grounding_receipt_digest,
            "source_hashes": [str(item.get("source_hash") or "") for item in target_slice],
            "tests": tests,
            "patch_authority": PATCH_AUTHORITY,
        }
        phase = {
            "phase_id": f"CRC-P{phase_index // 4 + 1:02d}",
            "action_node_ids": phase_actions,
            "invariant_digest": stable_digest(invariant_payload),
            "continuity_checkpoint": {
                "compass_digest": compass_digest,
                "completed_action_node_ids": [],
                "next_action_node_id": phase_actions[0] if phase_actions else "",
                "human_review_required": True,
            },
            "proposal_only": True,
        }
        phase["phase_digest"] = stable_digest(phase)
        phase_capsules.append(phase)

    graph = {
        "ok": True,
        "version": COMPASS_CHANGE_GRAPH_VERSION,
        "graph_type": "CODING_RELATIONSHIP_COMPASS",
        "objective": objective,
        "compass_digest": compass_digest,
        "grounding_receipt_digest": grounding_receipt_digest,
        "nodes": nodes,
        "phase_capsules": phase_capsules,
        "required_tests": tests,
        "authority": {
            "execution_authority": False,
            "commit_authority": False,
            "pull_request_authority": False,
            "merge_authority": False,
            "human_review_required": True,
        },
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    graph["graph_digest"] = stable_digest(graph)
    return graph


def validate_compass_change_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(graph, Mapping):
        raise ValueError("Compass Change Graph must be a mapping")
    stored = str(graph.get("graph_digest") or "")
    body = dict(graph)
    body.pop("graph_digest", None)
    expected = stable_digest(body)
    if stored != expected:
        raise ValueError("Compass Change Graph digest mismatch")
    if graph.get("graph_type") != "CODING_RELATIONSHIP_COMPASS":
        raise ValueError("unsupported Compass Change Graph type")
    authority = graph.get("authority") or {}
    if not isinstance(authority, Mapping):
        raise ValueError("Compass Change Graph authority must be a mapping")
    forbidden = (
        authority.get("execution_authority")
        or authority.get("commit_authority")
        or authority.get("pull_request_authority")
        or authority.get("merge_authority")
        or not authority.get("human_review_required")
        or graph.get("patch_authority") != PATCH_AUTHORITY
        or bool(graph.get("vsa_patch_authority"))
    )
    if forbidden:
        raise ValueError("Compass Change Graph authority boundary changed")
    return {"ok": True, "graph_digest": stored, "node_count": len(graph.get("nodes", ()) or ())}


def compile_compass_act_capsules(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Compile actual proposal-only Act Capsules or fail closed on missing evidence."""

    validate_compass_change_graph(graph)
    tests = _ordered_unique(graph.get("required_tests", ()) or ())
    if not tests:
        return {
            "ok": False,
            "reason": "MISSING_DECLARED_TESTS",
            "fail_closed": True,
            "act_capsules": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    phases = {str(item.get("phase_id")): dict(item) for item in graph.get("phase_capsules", ()) or () if isinstance(item, Mapping)}
    action_to_phase = {
        node_id: phase_id
        for phase_id, phase in phases.items()
        for node_id in phase.get("action_node_ids", ()) or ()
    }
    capsules: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for node in graph.get("nodes", ()) or ():
        if not isinstance(node, Mapping) or node.get("node_type") != "ACTION":
            continue
        payload = dict(node.get("payload") or {})
        missing = [
            key
            for key in ("task_id", "target_file", "source_hash")
            if not str(payload.get(key) or "").strip()
        ]
        if int(payload.get("line_start") or 0) <= 0 or int(payload.get("line_end") or 0) < int(payload.get("line_start") or 0):
            missing.append("exact_source_span")
        if not payload.get("tests"):
            missing.append("tests")
        if not str(payload.get("grounding_receipt_digest") or ""):
            missing.append("grounding_receipt_digest")
        if missing:
            failures.append({"node_id": node.get("node_id"), "missing": sorted(set(missing))})
            continue
        phase_id = action_to_phase.get(str(node.get("node_id")), "")
        if not phase_id:
            failures.append({"node_id": node.get("node_id"), "missing": ["phase_id"]})
            continue
        capsule = {
            "version": COMPASS_ACT_CAPSULE_VERSION,
            "task_id": str(payload["task_id"]),
            "phase_id": phase_id,
            "objective": str(payload.get("objective") or ""),
            "target_file": str(payload.get("target_file") or ""),
            "target_symbol": str(payload.get("target_symbol") or ""),
            "source_span": {
                "line_start": payload.get("line_start"),
                "line_end": payload.get("line_end"),
                "source_hash": str(payload.get("source_hash") or ""),
                "file_source_hash": str(payload.get("file_source_hash") or ""),
            },
            "declared_tests": list(payload.get("tests") or []),
            "preconditions": list(payload.get("preconditions") or []),
            "effects": list(payload.get("effects") or []),
            "rollback": list(payload.get("rollback") or []),
            "surgeon_request": {
                "allowed_file": str(payload.get("target_file") or ""),
                "allowed_symbol": str(payload.get("target_symbol") or ""),
                "allowed_line_start": payload.get("line_start"),
                "allowed_line_end": payload.get("line_end"),
                "expected_source_hash": str(payload.get("source_hash") or ""),
                "required_tests": list(payload.get("tests") or []),
            },
            "proposal_only": True,
            "human_review_required": True,
            "automatic_commit": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
        capsule["capsule_digest"] = stable_digest(capsule, digest_size=16)
        capsules.append(capsule)
    if not capsules and not failures:
        return {
            "ok": False,
            "reason": "NO_ACTION_NODES",
            "fail_closed": True,
            "act_capsules": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    if failures:
        return {
            "ok": False,
            "reason": "CAPSULE_EVIDENCE_INCOMPLETE",
            "fail_closed": True,
            "failures": failures,
            "act_capsules": [],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    result = {
        "ok": True,
        "version": COMPASS_ACT_CAPSULE_VERSION,
        "graph_digest": graph.get("graph_digest"),
        "act_capsules": capsules,
        "phase_capsules": list(phases.values()),
        "proposal_only": True,
        "safe_to_patch": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    result["capsule_set_digest"] = stable_digest(result)
    return result
