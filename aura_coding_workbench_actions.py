"""Aura Coding Workbench actions with optional bounded route-capsule apertures."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
PATCH_AUTHORITY="exact_source_spans_and_hashes_only";VSA_PATCH_AUTHORITY=False;ACTIONS_VERSION="AURA_CODING_WORKBENCH_ACTIONS_V2"
def open_workspace(repo_root="."):
    from aura_topology_health import topology_health_packet
    h=topology_health_packet(repo_root=repo_root);return {"ok":True,"workspace":"opened","topology_health":h,"next_gate":h.get("next_gate","WORKSPACE_OPENED"),"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def scope_task(objective,repo_root="."):return {"ok":True,"objective":objective,"scope":{"type":"coding","objective":objective},"next_gate":"TASK_SCOPED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def filter_context(objective,repo_root=".",filters=None):return {"ok":True,"objective":objective,"filters":filters or {},"filtered_context":True,"next_gate":"CONTEXT_FILTERED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def localize_code(objective,repo_root=".",aperture=None):
    from aura_code_region_ranker import rank_code_regions
    active=dict(aperture or _default_localization_aperture(repo_root) or {});kwargs={}
    if active:
        kwargs["max_regions"]=max(1,int(active.get("maximum_symbols",12)));kwargs["max_lines"]=max(1,int(active.get("maximum_lines",600)))
    ranking=rank_code_regions(objective,repo_root=repo_root,**kwargs)
    max_files=max(1,int(active.get("maximum_files",len(ranking.get("files",[])) or 8))) if active else None;max_symbols=max(1,int(active.get("maximum_symbols",len(ranking.get("symbols",[])) or 12))) if active else None
    files=list(ranking.get("files",[]));symbols=list(ranking.get("symbols",[]));ranges=list(ranking.get("line_ranges",[]))
    if max_files is not None:files=files[:max_files]
    if max_symbols is not None:symbols=symbols[:max_symbols]
    result={"ok":True,"objective":objective,"localized_files":files,"localized_symbols":symbols,"line_ranges":ranges,"next_gate":"CODE_LOCALIZED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
    if active:result["route_capsule_usage"]={"actual_context_items":[*files,*symbols],"actual_tool_calls":["tool:topology_inspector"],"actual_model":"","budget_consumed":{"retrieved_files":len(files),"retrieved_symbols":len(symbols),"retrieved_line_ranges":len(ranges)},"data_aperture_enforced":True}
    return result
def rank_code_regions(objective,repo_root=".",max_regions=20,max_lines=400):
    from aura_code_region_ranker import rank_code_regions as _rank
    r=_rank(objective,repo_root=repo_root,max_regions=max_regions,max_lines=max_lines);r["next_gate"]="CODE_REGIONS_RANKED";return r
def slice_context(localization_packet,repo_root="."):
    f=localization_packet.get("localized_files",localization_packet.get("files",[]));s=localization_packet.get("localized_symbols",localization_packet.get("symbols",[]));l=localization_packet.get("line_ranges",[]);return {"ok":True,"sliced_files":f[:5],"sliced_symbols":s[:5],"exact_line_ranges":l[:5],"next_gate":"CONTEXT_SLICED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def build_change_graph(objective,localization_packet=None,repo_root="."):
    from aura_change_graph import build_change_graph as _build
    r=_build(objective,localization_packet,repo_root=repo_root)
    from aura_topology_health import topology_health_packet
    h=topology_health_packet(repo_root=repo_root)
    if h.get("topology_nodes",0)==0:return {"ok":False,"error":"Cannot build change graph with degraded topology.","next_gate":"NEED_TOPOLOGY_REPAIR","topology_health":h,"patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
    r["next_gate"]="CHANGE_GRAPH_BUILT";return r
def detect_refactor_candidates(change_graph,repo_root="."):
    from aura_refactor_candidate import detect_refactor_candidates as _detect
    r=_detect(change_graph,repo_root=repo_root);r["next_gate"]="REFACTOR_CANDIDATES_FOUND";return r
def split_work(candidate_or_objective,repo_root="."):
    from aura_work_splitter import split_large_objective
    obj=candidate_or_objective.get("objective",candidate_or_objective.get("title","")) if isinstance(candidate_or_objective,dict) else candidate_or_objective;r=split_large_objective(obj,repo_root=repo_root);r["next_gate"]="WORK_SPLIT";return r
def create_act_capsules(split_packet,repo_root="."):
    from aura_work_splitter import work_split_to_act_capsules
    r=work_split_to_act_capsules(split_packet,repo_root=repo_root);r["next_gate"]="ACT_CAPSULES_CREATED";return r
def prepare_agent_handoff(capsule_id,agent="hermes",repo_root="."):return {"ok":True,"capsule_id":capsule_id,"agent":agent,"handoff_packet":{"capsule_id":capsule_id,"agent":agent},"human_approval_required":True,"next_gate":"AGENT_HANDOFF_READY","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def stage_patch_plan(diff_or_patch_metadata,repo_root="."):return {"ok":True,"patch_metadata":diff_or_patch_metadata,"next_gate":"PATCH_STAGED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def run_targeted_tests(test_packet,repo_root="."):return {"ok":True,"test_packet":test_packet,"next_gate":"TESTS_RUNNING","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def verify_patch(verification_packet,repo_root="."):
    ok=verification_packet.get("ok",verification_packet.get("tests_pass",False));return {"ok":ok,"verification":verification_packet,"next_gate":"PATCH_VERIFIED" if ok else "REPAIR_REQUIRED","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def prepare_pr_packet(repo_root="."):return {"ok":True,"pr_ready":True,"next_gate":"PR_READY","patch_authority":PATCH_AUTHORITY,"vsa_patch_authority":False}
def _default_localization_aperture(repo_root):
    enabled=str(os.getenv("AURA_ROUTE_CAPSULES_ENABLED","0")).strip().casefold() in {"1","true","yes","on"}
    if not enabled:return None
    path=Path(repo_root).resolve()/".aura"/"data_apertures"/"coding_localize.v1.json"
    try:data=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError):return None
    return data if isinstance(data,dict) and data.get("allow_unbounded_repository_context") is not True else None
