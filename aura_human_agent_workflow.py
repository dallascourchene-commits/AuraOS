"""Grounded workflow spine for Aura's Human Agent Arena.

The surface may be conversational, but every consequential step is governed by
explicit evidence. Phase A2 makes the guarded-WFST controller the default command
and server-action path while preserving the existing action implementations.
Nothing here merges or mutates production directly.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import time
from typing import Any

from aura_arena_tool_runtime import ArenaToolRuntime, list_tools

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
WORKFLOW_VERSION = "AURA_HUMAN_AGENT_WORKFLOW_V2"

ACTIONS = (
    {"action_id":"set_objective","title":"Frame objective","phase":"FRAME","purpose":"Turn any request into the active bounded objective.","requires":(),"produces":("objective",)},
    {"action_id":"ground_context","title":"Ground in Aura","phase":"GROUND","purpose":"Locate exact files, symbols, tests, risks, and existing capabilities.","requires":("objective",),"produces":("grounding",),"tool_id":"topology_inspector"},
    {"action_id":"prepare_capsule","title":"Prepare Arena capsule","phase":"PLAN","purpose":"Compile Action Capsules, leases, boundaries, and a handoff.","requires":("objective","grounding"),"produces":("plan_phase_hash","act_capsules")},
    {"action_id":"stage_patch","title":"Stage candidate patch","phase":"ACT","purpose":"Stage a candidate diff without writing production directly.","requires":("plan_phase_hash","candidate_diff","affected_files"),"produces":("staged_patch",)},
    {"action_id":"run_tests","title":"Run ephemeral test lab","phase":"PROVE","purpose":"Run focused pytest targets and preserve measured evidence.","requires":("test_targets",),"produces":("test_evidence",),"tool_id":"test_lab"},
    {"action_id":"verify_patch","title":"Verify evidence","phase":"PROVE","purpose":"Evaluate staged work and test evidence against verifier gates.","requires":("staged_patch","test_evidence"),"produces":("verification_packet",)},
    {"action_id":"check_hotswap","title":"Check hotswap gate","phase":"DECIDE","purpose":"Explain whether the transaction is ready for human review.","requires":("staged_patch","test_evidence","verification_packet"),"produces":("hotswap_status",)},
    {"action_id":"human_review","title":"Human review","phase":"DECIDE","purpose":"Record review only; do not merge or promote production.","requires":("hotswap_status",),"produces":("human_review",)},
    {"action_id":"export_handoff","title":"Export review packet","phase":"DECIDE","purpose":"Export grounded evidence for review or agent continuation.","requires":("plan_phase_hash",),"produces":("review_packet",)},
)
ACTION_BY_ID = {item["action_id"]: item for item in ACTIONS}
PHASES = ("FRAME","GROUND","PLAN","ACT","PROVE","DECIDE")


class ToolRuntimeFacade:
    """Preserve the Arena-facing packet shape over ArenaToolRuntime."""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._runtime = ArenaToolRuntime(self.repo_root)
        self.runs: dict[str, dict[str, Any]] = {}

    def get_tools(self) -> dict[str, Any]:
        return self._runtime.get_tools()

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self.runs.get(str(run_id))
        return {"ok": bool(run), "run": run} if run else {"ok":False,"error":"tool_run_not_found","run_id":run_id}

    def execute(self, tool_id: str, *, objective: str = "", inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        raw = self._runtime.execute(
            tool_id,
            objective=str(objective),
            inputs=dict(inputs or {}),
        )
        result = dict(raw.get("outputs") or {})
        run_id = str(raw.get("run_id") or f"TOOL-{int(time.time()*1000)}")
        outputs = self._normalize_outputs(tool_id, raw, result)
        denial = dict(raw.get("denial") or {})
        if raw.get("status") == "DENIED" and not denial:
            denial = {
                "reason": result.get("reason") or raw.get("error") or "tool_denied",
                "missing": result.get("missing_evidence", []),
                "remediation": result.get("remediation", []),
                "fail_closed": True,
            }
        packet = {
            "run_id":run_id,
            "tool_id":str(raw.get("tool_id") or tool_id),
            "status":str(raw.get("status") or "FAILED"),
            "outputs":outputs,
            "denial":denial,
            "sandbox_receipt":dict(raw.get("sandbox_receipt") or {}),
            "dissolution_receipt":dict(raw.get("dissolution_receipt") or {}),
            "raw":raw,
            "patch_authority":PATCH_AUTHORITY,
            "vsa_patch_authority":VSA_PATCH_AUTHORITY,
        }
        self.runs[run_id] = packet
        return packet

    @staticmethod
    def _normalize_outputs(tool_id: str, raw: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        if tool_id == "topology_inspector":
            direct_files = list(result.get("localized_files") or [])
            direct_symbols = list(result.get("localized_symbols") or [])
            direct_ranges = list(result.get("line_ranges") or [])
            ranking = dict(result.get("ranking") or {})
            if direct_files or direct_symbols or direct_ranges or ranking:
                tests = list(result.get("tests") or ranking.get("tests") or [])
                return {
                    "ok": bool(result.get("ok")),
                    "localized_files": direct_files,
                    "localized_symbols": direct_symbols,
                    "line_ranges": direct_ranges,
                    "ranking": ranking,
                    "tests": tests,
                    "truth_class": result.get("truth_class", "EXACT_REPOSITORY_FACTS"),
                }

            hits = list((result.get("grounding_packet") or {}).get("results") or [])
            files: list[str] = []
            symbols: list[str] = []
            ranges: list[dict[str, Any]] = []
            tests: list[str] = []
            for hit in hits:
                if not isinstance(hit, dict):
                    continue
                file_path = str(hit.get("file") or "")
                symbol = str(hit.get("symbol") or "")
                if file_path and file_path not in files:
                    files.append(file_path)
                if symbol and symbol not in symbols:
                    symbols.append(symbol)
                if file_path:
                    ranges.append({"file":file_path,"symbol":symbol,"line_range":hit.get("line_range",[])})
                for candidate in [file_path, *list(hit.get("neighbors") or [])]:
                    if isinstance(candidate,str) and Path(candidate).name.startswith("test_") and candidate not in tests:
                        tests.append(candidate)
            return {
                "ok": bool(result.get("ok", raw.get("status") == "COMPLETED")),
                "localized_files": files,
                "localized_symbols": symbols,
                "line_ranges": ranges,
                "ranking": {"results": hits, "tests": tests},
                "tests": tests,
            }

        if tool_id == "test_lab":
            evidence = dict(result.get("test_evidence") or result)
            evidence["ok"] = bool(evidence.get("ok"))
            evidence["status"] = str(raw.get("status") or evidence.get("status") or "")
            if not evidence["ok"]:
                evidence["missing_evidence"] = evidence.get("missing_evidence", ["passing_test_evidence"])
            return evidence

        return {**result,"ok":bool(result.get("ok",raw.get("status") == "COMPLETED"))}


class HumanAgentWorkflow:
    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.workflow_id = "HWF-" + hashlib.blake2b(f"{self.repo_root}:{time.time()}".encode(),digest_size=8).hexdigest()
        self.objective = ""
        self.evidence: dict[str, Any] = {}
        self.gate_dialogue_audit: list[dict[str, Any]] = []
        self.last_result: dict[str, Any] = {}
        self.event_log: list[dict[str, Any]] = []
        self.tools = ToolRuntimeFacade(self.repo_root)
        self.state = self
        self._bridge: Any = None
        self._wfst_controller: Any = None
        self._wfst_error = ""
        self._event("init","Grounded Human-Agent workflow opened")

    def _bridge_instance(self) -> Any:
        if self._bridge is None:
            from aura_agent_arena_bridge import AuraAgentArenaBridge
            self._bridge = AuraAgentArenaBridge(repo_root=self.repo_root)
        return self._bridge

    def _wfst_instance(self) -> Any:
        if self._wfst_controller is not None:
            return self._wfst_controller
        if self._wfst_error:
            return None
        try:
            from aura_human_agent_wfst_adapter import HumanAgentWFSTController
            self._wfst_controller = HumanAgentWFSTController(self, repo_root=self.repo_root)
        except Exception as exc:  # noqa: BLE001
            self._wfst_error = f"human_agent_wfst_unavailable:{type(exc).__name__}"
            return None
        return self._wfst_controller

    def close(self) -> None:
        if self._wfst_controller is not None:
            self._wfst_controller.close()

    def _event(self, kind: str, detail: str) -> None:
        self.event_log.append({"ts":time.time(),"kind":kind,"detail":detail})
        self.event_log = self.event_log[-120:]

    def _has(self, key: str) -> bool:
        value = self.evidence.get(key)
        return value is not None and (not isinstance(value,(str,list,dict,tuple,set)) or len(value)>0)

    @staticmethod
    def _remediation(missing: list[str]) -> list[dict[str,str]]:
        mapping = {
            "objective":("Frame the objective","set_objective"),"grounding":("Ground the objective in CODEMAP","ground_context"),
            "test_targets":("Find focused tests","ground_context"),"plan_phase_hash":("Prepare the Arena capsule","prepare_capsule"),
            "candidate_diff":("Provide or generate a candidate diff","prepare_agent_task"),"affected_files":("Select exact affected files","ground_context"),
            "staged_patch":("Stage a candidate patch","stage_patch"),"test_evidence":("Run the ephemeral test lab","run_tests"),
            "verification_packet":("Run the verifier","verify_patch"),"hotswap_status":("Check the hotswap gate","check_hotswap"),
        }
        return [{"label":mapping.get(item,(f"Provide {item}",""))[0],"action":mapping.get(item,("", ""))[1],"evidence":item} for item in missing]

    def _action_states(self) -> list[dict[str, Any]]:
        actions = []
        for action in ACTIONS:
            missing = [key for key in action.get("requires",()) if not self._has(key)]
            complete = bool(action.get("produces")) and all(self._has(key) for key in action.get("produces",()))
            actions.append({
                **action,
                "requires":list(action.get("requires",())),
                "produces":list(action.get("produces",())),
                "status":"COMPLETE" if complete else ("BLOCKED" if missing else "READY"),
                "missing_evidence":missing,
                "enabled":not missing,
                "remediation":self._remediation(missing),
            })
        return actions

    def current_phase(self) -> str:
        actions = self._action_states()
        return next((phase for phase in PHASES if any(a["phase"]==phase and a["status"] in {"READY","BLOCKED"} for a in actions)),"DECIDE")

    def get_state_without_routing(self) -> dict[str, Any]:
        actions = self._action_states()
        return {
            "ok":True,
            "version":WORKFLOW_VERSION,
            "workflow_id":self.workflow_id,
            "objective":self.objective,
            "current_phase":self.current_phase(),
            "evidence_keys":sorted(self.evidence),
            "evidence":self.evidence,
            "actions":actions,
            "last_result":self.last_result,
            "event_log":self.event_log[-40:],
            "gate_dialogue_audit":self.gate_dialogue_audit[-40:],
            "patch_authority":PATCH_AUTHORITY,
            "vsa_patch_authority":VSA_PATCH_AUTHORITY,
        }

    def get_state(self) -> dict[str, Any]:
        packet = self.get_state_without_routing()
        controller = self._wfst_instance()
        if controller is None:
            routing = {
                "ok":False,
                "reason":self._wfst_error or "human_agent_wfst_unavailable",
                "fail_closed":True,
                "recommended":[],"available":[],"blocked":[],"meta":[],
            }
        else:
            routing = controller.project_state()
        packet.update({
            "routing":routing,
            "recommended":routing.get("recommended",[]),
            "available":routing.get("available",[]),
            "blocked":routing.get("blocked",[]),
            "meta":routing.get("meta",[]),
            "grammar_version":routing.get("grammar_version",""),
            "state_packet":routing.get("state_packet",{}),
        })
        return packet

    def execute(self, action_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a previously admitted action implementation.

        Direct callers retain this compatibility API. User/server surfaces should use
        ``execute_guarded`` or ``ingest_command`` so the WFST admits the action first.
        """
        payload = dict(payload or {})
        action = ACTION_BY_ID.get(str(action_id))
        if not action:
            return self._result(False,str(action_id),"Unknown workflow action.",[str(action_id)])
        missing = [key for key in action.get("requires",()) if not self._has(key)]
        for key in list(missing):
            if payload.get(key):
                self.evidence[key] = payload[key]
                missing = [item for item in missing if item != key]
        if missing:
            return self._result(False,action_id,f"{action['title']} denied because required evidence is missing.",missing)
        try:
            result = getattr(self,f"_do_{action_id}")(payload)
        except Exception as exc:  # noqa: BLE001
            result = self._result(False,action_id,f"Action failed: {exc}")
        self.last_result = result
        self._event("action",f"{action_id}:{result.get('status')}")
        return result

    def execute_guarded(self, action_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        controller = self._wfst_instance()
        if controller is None:
            return self._result(False, str(action_id), "Guarded WFST routing is unavailable; action failed closed.", ["guarded_wfst"])
        return controller.route_action(str(action_id), payload=dict(payload or {}))

    def preview_guarded_command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        controller = self._wfst_instance()
        if controller is None:
            return self._result(False, "command", "Guarded WFST routing is unavailable; command failed closed.", ["guarded_wfst"])
        return controller.preview_command(str(command or ""), payload=dict(payload or {}))

    def ingest_command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        controller = self._wfst_instance()
        if controller is None:
            return self._result(False,"command","Guarded WFST routing is unavailable; command failed closed.",["guarded_wfst"])
        return controller.route_command(str(command or ""), payload=dict(payload or {}))

    def _do_set_objective(self, payload: dict[str, Any]) -> dict[str, Any]:
        objective = str(payload.get("objective") or "").strip()
        if not objective:
            return self._result(False,"set_objective","Objective is required.",["objective"])
        if objective != self.objective:
            self.evidence.clear()
        self.objective, self.evidence["objective"] = objective, objective
        return self._result(True,"set_objective",f"Objective framed: {objective}",produced={"objective":objective})

    def _do_ground_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        run = self.tools.execute("topology_inspector",objective=self.objective)
        output = dict(run.get("outputs") or {})
        if not output.get("ok"):
            return self._result(False,"ground_context","Grounding tool failed.",["grounding"],details=run)
        grounding = {
            "localized_files":output.get("localized_files",[]),
            "localized_symbols":output.get("localized_symbols",[]),
            "line_ranges":output.get("line_ranges",[]),
            "ranking":output.get("ranking",{}),
            "tool_run_id":run.get("run_id",""),
            "dissolution_receipt":run.get("dissolution_receipt",{}),
        }
        tests = list(output.get("tests") or (output.get("ranking") or {}).get("tests") or [])
        self.evidence.update({"grounding":grounding,"affected_files":grounding["localized_files"][:8]})
        if tests:
            self.evidence["test_targets"] = tests[:8]
        return self._result(True,"ground_context","Objective grounded in exact repository evidence.",produced={"grounding":grounding,"test_targets":tests},details=run)

    def _do_prepare_capsule(self, payload: dict[str, Any]) -> dict[str, Any]:
        grounding = self.evidence.get("grounding",{})
        files, symbols = grounding.get("localized_files",[]), grounding.get("localized_symbols",[])
        prepared = self._bridge_instance().aura_prepare_arena(
            objective=self.objective,
            target_file=files[0] if files else None,
            target_symbol=symbols[0] if symbols else None,
            acceptance_criteria=list(payload.get("acceptance_criteria",[]) or []),
            constraints=["stage_before_mutation","human_review_required"],
        )
        if not prepared.get("ok"):
            return self._result(False,"prepare_capsule","Arena preparation was denied.",["grounded_preparation"],details=prepared)
        self.evidence.update({"plan_phase_hash":prepared.get("plan_phase_hash",""),"act_capsules":prepared.get("act_capsules",[])})
        tests = [test for item in prepared.get("grounding_evidence",[]) if isinstance(item,dict) for test in item.get("test_files",[]) if test]
        if tests:
            self.evidence["test_targets"] = list(dict.fromkeys(tests))
        if prepared.get("act_capsules") and prepared["act_capsules"][0].get("target_file"):
            self.evidence["affected_files"] = [prepared["act_capsules"][0]["target_file"]]
        return self._result(True,"prepare_capsule","Arena capsule, lease, boundaries, and handoff prepared.",produced={"plan_phase_hash":self.evidence["plan_phase_hash"],"act_capsules":self.evidence["act_capsules"]},details=prepared)

    def _do_stage_patch(self, payload: dict[str, Any]) -> dict[str, Any]:
        diff = str(payload.get("candidate_diff") or self.evidence.get("candidate_diff") or "")
        capsules = self.evidence.get("act_capsules",[])
        files = list(payload.get("affected_files") or self.evidence.get("affected_files") or [])
        task_id = str(payload.get("task_id") or (capsules[0].get("task_id") if capsules else ""))
        if not diff.strip():
            return self._result(False,"stage_patch","Patch staging denied: no candidate diff exists.",["candidate_diff"])
        staged = self._bridge_instance().aura_stage_patch(
            plan_phase_hash=str(self.evidence.get("plan_phase_hash","")),
            task_id=task_id,
            owner="human_agent_arena",
            diff=diff,
            affected_files=files,
            affected_symbols=list(payload.get("affected_symbols",[]) or []),
            tests=list(self.evidence.get("test_targets",[]) or []),
        )
        if not staged.get("ok"):
            return self._result(False,"stage_patch","Candidate patch was rejected by the staging gate.",["acceptable_staged_patch"],details=staged)
        self.evidence.update({"candidate_diff":diff,"staged_patch":staged.get("patch",staged)})
        return self._result(True,"stage_patch","Candidate patch staged. Production remains unchanged.",produced={"staged_patch":self.evidence["staged_patch"]},details=staged)

    def _do_run_tests(self, payload: dict[str, Any]) -> dict[str, Any]:
        run = self.tools.execute("test_lab",objective=self.objective,inputs={"test_targets":payload.get("test_targets") or self.evidence.get("test_targets",[])})
        output = dict(run.get("outputs") or {})
        if not output.get("ok"):
            return self._result(False,"run_tests","The test lab did not produce passing evidence.",output.get("missing_evidence",["passing_test_evidence"]),details=run)
        evidence = {**output,"tool_run_id":run.get("run_id",""),"dissolution_receipt":run.get("dissolution_receipt",{})}
        self.evidence["test_evidence"] = evidence
        return self._result(True,"run_tests","Focused tests completed and measured evidence was preserved.",produced={"test_evidence":evidence},details=run)

    def _do_verify_patch(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan_hash = str(self.evidence.get("plan_phase_hash",""))
        verification = self._bridge_instance().aura_verify_arena(plan_phase_hash=plan_hash,test_scope="focused") if plan_hash and self.evidence.get("staged_patch") else {
            "ok":bool((self.evidence.get("test_evidence") or {}).get("passed",(self.evidence.get("test_evidence") or {}).get("ok"))),
            "stage":"evidence_only_verifier",
        }
        if not verification.get("ok"):
            return self._result(False,"verify_patch","Verification failed; repair evidence is required.",["passing_verification"],details=verification)
        self.evidence["verification_packet"] = verification
        return self._result(True,"verify_patch","Verifier gates passed for the available evidence.",produced={"verification_packet":verification},details=verification)

    def _do_check_hotswap(self, payload: dict[str, Any]) -> dict[str, Any]:
        status = self._bridge_instance().aura_hotswap_status(plan_phase_hash=str(self.evidence.get("plan_phase_hash","")))
        ready = status.get("status") in {"ready","READY","approved"} or status.get("hotswap_ready") is True
        self.evidence["hotswap_status"] = status
        return self._result(
            ready,
            "check_hotswap",
            "Hotswap gate is ready for human review." if ready else "Hotswap remains blocked; missing proof is shown below.",
            [] if ready else status.get("missing_evidence",["hotswap_ready_evidence"]),
            produced={"hotswap_status":status},
            details=status,
        )

    def _do_human_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        review = {
            "reviewed":True,
            "approved_for_next_gate":bool(payload.get("approved",False)),
            "reviewer":str(payload.get("reviewer") or "human_operator"),
            "note":str(payload.get("note") or ""),
            "merge_performed":False,
            "production_mutation":False,
            "reviewed_at":time.time(),
        }
        self.evidence["human_review"] = review
        return self._result(True,"human_review","Human review recorded. No merge or production promotion was performed.",produced={"human_review":review})

    def _do_export_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        exported = self._bridge_instance().aura_export_icm(plan_phase_hash=str(self.evidence.get("plan_phase_hash","")),workspace_root="Aura_Memory/icm_workspaces")
        if not exported.get("ok"):
            return self._result(False,"export_handoff","Review packet export failed.",details=exported)
        self.evidence["review_packet"] = exported
        return self._result(True,"export_handoff","Grounded review packet exported for review.",produced={"review_packet":exported},details=exported)

    def _result(self, ok: bool, action_id: str, message: str, missing: list[str] | None = None, *, produced: dict[str, Any] | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
        missing = list(missing or [])
        return {
            "ok":bool(ok),
            "status":"ALLOWED" if ok else "DENIED",
            "action_id":action_id,
            "message":message,
            "produced_evidence":dict(produced or {}),
            "missing_evidence":missing,
            "remediation":self._remediation(missing),
            "details":dict(details or {}),
            "workflow":self.get_state(),
            "patch_authority":PATCH_AUTHORITY,
            "vsa_patch_authority":VSA_PATCH_AUTHORITY,
        }
