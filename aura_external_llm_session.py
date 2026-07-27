"""Provider-neutral, slice-leased sessions for external LLMs using Aura's Agent Arena.

The protocol deliberately never gives a model the repository. Aura prepares the
arena, leases one bounded task, returns exact source/test slices, accepts a
candidate response, stages it through the existing boundary logic, verifies it,
and emits a repair turn when proof fails.

This module is an adapter. It does not grant patch authority, promote a patch,
commit, push, merge, or mutate production source.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable

SESSION_VERSION = "AURA_EXTERNAL_LLM_SESSION_V1"
TURN_VERSION = "AURA_EXTERNAL_LLM_TURN_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_ROLE_CONTRACTS: dict[str, dict[str, Any]] = {
    "worker": {
        "required_response": "unified_diff_only",
        "description": "Produce one bounded unified diff for the leased Act Capsule.",
    },
    "repair": {
        "required_response": "unified_diff_only",
        "description": "Repair the previously staged candidate using only the failure packet and leased slices.",
    },
}


def _digest(payload: Any, *, size: int = 12) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _token_estimate(text: Any) -> int:
    return max(0, (len(str(text or "")) + 3) // 4)


def _bounded_payload(value: Any, max_tokens: int) -> Any:
    """Return JSON-compatible evidence bounded by a deterministic token proxy."""
    text = json.dumps(value, sort_keys=True, default=str)
    if _token_estimate(text) <= max_tokens:
        return value
    char_limit = max(64, int(max_tokens) * 4)
    return {
        "truncated": True,
        "digest": _digest(value),
        "original_token_estimate": _token_estimate(text),
        "excerpt": text[:char_limit],
    }


def _bounded_text(value: Any, max_tokens: int) -> str:
    """Bound text under the same deterministic token proxy used by turns."""
    text = str(value or "")
    max_chars = max(0, int(max_tokens)) * 4
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""
    marker = f"[TRUNCATED digest={_digest(text)} tokens={_token_estimate(text)}]\n"
    if len(marker) >= max_chars:
        return marker[:max_chars]
    return marker + text[: max_chars - len(marker)]


def _diff_touched_files(diff: str) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        path = str(raw or "").strip().strip("'\"")
        if "\t" in path:
            path = path.split("\t", 1)[0]
        if path.startswith(("a/", "b/")):
            path = path[2:]
        path = path.replace("\\", "/").lstrip("./")
        if path and path != "/dev/null" and path not in seen:
            seen.add(path)
            files.append(path)

    for line in str(diff or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                add(parts[2])
                add(parts[3])
        elif line.startswith("--- "):
            add(line[4:])
        elif line.startswith("+++ "):
            add(line[4:])
        elif line.startswith("*** Update File: "):
            add(line[len("*** Update File: "):])
        elif line.startswith("*** Add File: "):
            add(line[len("*** Add File: "):])
    return files


@dataclass
class ExternalLLMTurn:
    turn_id: str
    session_id: str
    role: str
    task_id: str
    objective: str
    gate: str
    instruction: str
    output_contract: dict[str, Any]
    act_capsule: dict[str, Any]
    compressed_context: str
    source_slices: list[dict[str, Any]]
    test_slices: list[dict[str, Any]]
    failure_packet: dict[str, Any]
    allowed_files: list[str]
    do_not_touch: list[str]
    context_token_estimate: int
    max_output_tokens: int
    turn_index: int
    created_at: float
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    production_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"version": TURN_VERSION, **asdict(self)}


@dataclass
class ExternalLLMSession:
    session_id: str
    objective: str
    plan_phase_hash: str
    provider: str
    model: str
    act_capsules: list[dict[str, Any]]
    max_context_tokens: int
    max_output_tokens: int
    max_turns: int
    status: str = "OPEN"
    active_task_index: int = 0
    pending_turn: ExternalLLMTurn | None = None
    turns: list[dict[str, Any]] = field(default_factory=list)
    stage_results: list[dict[str, Any]] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def active_task(self) -> dict[str, Any] | None:
        if 0 <= self.active_task_index < len(self.act_capsules):
            return self.act_capsules[self.active_task_index]
        return None

    def public_state(self) -> dict[str, Any]:
        return {
            "version": SESSION_VERSION,
            "session_id": self.session_id,
            "objective": self.objective,
            "plan_phase_hash": self.plan_phase_hash,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "active_task_index": self.active_task_index,
            "task_count": len(self.act_capsules),
            "max_context_tokens": self.max_context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_turns": self.max_turns,
            "turn_count": len(self.turns),
            "stage_count": len(self.stage_results),
            "verification_count": len(self.verification_results),
            "pending_turn": self.pending_turn.to_dict() if self.pending_turn else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "production_mutation": False,
        }


class AuraExternalLLMSessionManager:
    """Stateful adapter over AuraAgentArenaBridge.

    An MCP/HTTP/client adapter can keep one manager alive and expose these four
    calls: open_session, next_turn, submit_response, and get_session.
    """

    def __init__(self, repo_root: str | Path = ".", bridge: Any | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        if bridge is None:
            from aura_agent_arena_bridge import AuraAgentArenaBridge

            bridge = AuraAgentArenaBridge(repo_root=self.repo_root)
        self.bridge = bridge
        self._sessions: dict[str, ExternalLLMSession] = {}

    def open_session(
        self,
        *,
        objective: str,
        target_file: str | None = None,
        target_symbol: str | None = None,
        acceptance_criteria: list[str] | None = None,
        risk_map: list[str] | None = None,
        constraints: list[str] | None = None,
        provider: str = "external",
        model: str = "",
        max_context_tokens: int = 2200,
        max_output_tokens: int = 2400,
        max_turns: int = 12,
    ) -> dict[str, Any]:
        objective = str(objective or "").strip()
        if not objective:
            return self._error("objective_required")
        if not 256 <= int(max_context_tokens) <= 16000:
            return self._error("max_context_tokens_out_of_range")
        if not 128 <= int(max_output_tokens) <= 16000:
            return self._error("max_output_tokens_out_of_range")
        if not 1 <= int(max_turns) <= 40:
            return self._error("max_turns_out_of_range")

        prepared = self.bridge.aura_prepare_arena(
            objective=objective,
            target_file=target_file,
            target_symbol=target_symbol,
            acceptance_criteria=list(acceptance_criteria or []),
            risk_map=list(risk_map or []),
            constraints=[
                "external_llm_receives_slices_only",
                "no_direct_production_mutation",
                "human_review_required",
                *list(constraints or []),
            ],
        )
        if not prepared.get("ok"):
            return {**prepared, "session_created": False}

        capsules = [dict(item) for item in prepared.get("act_capsules", []) if isinstance(item, dict)]
        if not capsules:
            return self._error("prepared_arena_has_no_act_capsules", details=prepared)

        seed = {
            "objective": objective,
            "plan_phase_hash": prepared.get("plan_phase_hash", ""),
            "provider": provider,
            "model": model,
            "created_at_ns": time.time_ns(),
        }
        session_id = f"ELLM-{_digest(seed, size=10)}"
        session = ExternalLLMSession(
            session_id=session_id,
            objective=objective,
            plan_phase_hash=str(prepared.get("plan_phase_hash", "")),
            provider=str(provider or "external"),
            model=str(model or ""),
            act_capsules=capsules,
            max_context_tokens=int(max_context_tokens),
            max_output_tokens=int(max_output_tokens),
            max_turns=int(max_turns),
        )
        self._sessions[session_id] = session
        turn = self._build_turn(session, role="worker", failure_packet={})
        if turn is None:
            session.status = "BLOCKED"
            session.updated_at = time.time()
            return {
                "ok": False,
                "error": "unable_to_build_leased_turn",
                "prepared": prepared,
                "session": session.public_state(),
            }
        session.pending_turn = turn
        session.status = "WAITING_FOR_MODEL"
        session.updated_at = time.time()
        return {
            "ok": True,
            "session_created": True,
            "prepared": prepared,
            "session": session.public_state(),
            "turn": turn.to_dict(),
        }

    def next_turn(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        if session is None:
            return self._error("session_not_found")
        return {
            "ok": session.pending_turn is not None,
            "session": session.public_state(),
            "turn": session.pending_turn.to_dict() if session.pending_turn else None,
        }

    def get_session(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        if session is None:
            return self._error("session_not_found")
        return {"ok": True, "session": session.public_state(), "turn_history": list(session.turns)}

    def submit_response(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        if session is None:
            return self._error("session_not_found")
        turn = session.pending_turn
        if turn is None:
            return self._error("no_pending_turn", session=session)
        if str(turn_id) != turn.turn_id:
            return self._error("turn_id_mismatch", session=session)
        if len(session.turns) >= session.max_turns:
            session.status = "BLOCKED_MAX_TURNS"
            session.pending_turn = None
            return self._error("max_turns_exceeded", session=session)

        text = str(response or "")
        usage = dict(provider_usage or {})
        record = {
            "turn": turn.to_dict(),
            "response_digest": _digest(text),
            "response_token_estimate": _token_estimate(text),
            "provider_usage": usage,
            "submitted_at": time.time(),
        }
        session.turns.append(record)
        session.pending_turn = None
        session.updated_at = time.time()

        if turn.role not in {"worker", "repair"}:
            session.status = "BLOCKED_UNKNOWN_ROLE"
            return self._error("unsupported_turn_role", session=session)

        touched_files = _diff_touched_files(text)
        if not touched_files:
            touched_files = list(turn.allowed_files)
        stage = self.bridge.aura_stage_patch(
            plan_phase_hash=session.plan_phase_hash,
            task_id=turn.task_id,
            owner=f"external_llm:{session.provider}:{session.model}".rstrip(":"),
            diff=text,
            affected_files=touched_files,
            affected_symbols=[
                str(turn.act_capsule.get("target_symbol"))
            ] if turn.act_capsule.get("target_symbol") else [],
            tests=[item.get("file", "") for item in turn.test_slices if item.get("file")],
        )
        session.stage_results.append(stage)
        if not stage.get("ok"):
            return self._queue_repair(
                session,
                failure_packet={
                    "source": "stage_gate",
                    "stage_result": stage,
                    "required_response": "unified_diff_only",
                },
            )

        verification = self.bridge.aura_verify_arena(
            plan_phase_hash=session.plan_phase_hash,
            test_scope="focused",
            runner="pytest",
            max_log_lines=80,
        )
        session.verification_results.append(verification)
        if verification.get("hotswap_ready"):
            session.active_task_index += 1
            if session.active_task is None:
                session.status = "READY_FOR_HUMAN_REVIEW"
                session.pending_turn = None
                session.updated_at = time.time()
                return {
                    "ok": True,
                    "status": session.status,
                    "session": session.public_state(),
                    "stage_result": stage,
                    "verification": verification,
                    "hotswap_status": self.bridge.aura_hotswap_status(
                        plan_phase_hash=session.plan_phase_hash
                    ),
                    "next_turn": None,
                }
            if len(session.turns) >= session.max_turns:
                session.pending_turn = None
                session.status = "BLOCKED_MAX_TURNS"
                session.updated_at = time.time()
                return {
                    "ok": False,
                    "status": session.status,
                    "session": session.public_state(),
                    "stage_result": stage,
                    "verification": verification,
                    "next_turn": None,
                    "error": "max_turns_exceeded",
                }
            next_turn = self._build_turn(session, role="worker", failure_packet={})
            if next_turn is None:
                session.pending_turn = None
                session.status = "BLOCKED_NEXT_TURN_UNAVAILABLE"
                session.updated_at = time.time()
                return {
                    "ok": False,
                    "status": session.status,
                    "session": session.public_state(),
                    "stage_result": stage,
                    "verification": verification,
                    "next_turn": None,
                    "error": "unable_to_build_leased_turn",
                }
            session.pending_turn = next_turn
            session.status = "WAITING_FOR_MODEL"
            session.updated_at = time.time()
            return {
                "ok": True,
                "status": session.status,
                "session": session.public_state(),
                "stage_result": stage,
                "verification": verification,
                "next_turn": next_turn.to_dict(),
            }

        repair = self.bridge.aura_repair_packet(
            plan_phase_hash=session.plan_phase_hash,
            task_id=turn.task_id,
            max_tokens_est=min(1500, session.max_context_tokens),
        )
        return self._queue_repair(
            session,
            failure_packet={
                "source": "verification_gate",
                "verification": verification,
                "repair": repair,
                "required_response": "unified_diff_only",
            },
            stage_result=stage,
            verification=verification,
        )

    def export_session(
        self,
        session_id: str,
        output_path: str | Path,
    ) -> dict[str, Any]:
        session = self._sessions.get(str(session_id))
        if session is None:
            return self._error("session_not_found")
        target = Path(output_path)
        if not target.is_absolute():
            target = self.repo_root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session": session.public_state(),
            "turn_history": session.turns,
            "stage_results": session.stage_results,
            "verification_results": session.verification_results,
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return {
            "ok": True,
            "path": str(target),
            "digest": _digest(payload),
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _queue_repair(
        self,
        session: ExternalLLMSession,
        *,
        failure_packet: dict[str, Any],
        stage_result: dict[str, Any] | None = None,
        verification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repair_turn = self._build_turn(session, role="repair", failure_packet=failure_packet)
        if repair_turn is None or len(session.turns) >= session.max_turns:
            session.status = "BLOCKED_REPAIR_UNAVAILABLE"
            session.pending_turn = None
        else:
            session.pending_turn = repair_turn
            session.status = "WAITING_FOR_REPAIR"
        session.updated_at = time.time()
        return {
            "ok": False,
            "status": session.status,
            "session": session.public_state(),
            "stage_result": stage_result or (session.stage_results[-1] if session.stage_results else {}),
            "verification": verification or {},
            "next_turn": repair_turn.to_dict() if repair_turn else None,
        }

    def _build_turn(
        self,
        session: ExternalLLMSession,
        *,
        role: str,
        failure_packet: dict[str, Any],
    ) -> ExternalLLMTurn | None:
        if len(session.turns) >= session.max_turns:
            return None
        task = session.active_task
        if task is None:
            return None
        task_id = str(task.get("task_id") or "")
        micro = self.bridge.aura_get_micro_context(
            plan_phase_hash=session.plan_phase_hash,
            task_id=task_id,
            depth=1,
            format="both",
            max_tokens_est=min(800, session.max_context_tokens),
        )
        if not micro.get("ok"):
            return None
        compressed_context = str(micro.get("compressed_context", ""))
        bilateral_micro_context = dict(
            micro.get("bilateral_micro_context") or {}
        )
        bounded_failure = _bounded_payload(
            failure_packet,
            max(96, session.max_context_tokens // 3),
        )
        fixed_without_compressed_context = _token_estimate(
            json.dumps(
                {
                    "failure_packet": bounded_failure,
                    "act_capsule": task,
                },
                default=str,
            )
        ) + 96
        compressed_context_budget = max(
            0,
            session.max_context_tokens - fixed_without_compressed_context,
        )
        if bilateral_micro_context:
            compressed_context += (
                "\n\n[BILATERAL_MICRO_CONTEXT]\n"
                + json.dumps(
                    bilateral_micro_context,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=str,
                )
            )
        compressed_context = _bounded_text(
            compressed_context,
            compressed_context_budget,
        )
        fixed_context_tokens = _token_estimate(
            json.dumps(
                {
                    "compressed_context": compressed_context,
                    "failure_packet": bounded_failure,
                    "act_capsule": task,
                },
                default=str,
            )
        ) + 96
        # Final serialized-payload fitting below is authoritative. If fixed
        # metadata consumes the budget, slices receive zero tokens.
        slice_token_budget = max(
            0,
            session.max_context_tokens - fixed_context_tokens,
        )
        source_slices, test_slices = self._lease_slices(
            micro,
            token_budget=slice_token_budget,
        )
        allowed_files = [
            str(path)
            for path in [
                task.get("target_file"),
                *list(task.get("related_files", []) or []),
            ]
            if path
        ]
        if failure_packet:
            repair = failure_packet.get("repair")
            if isinstance(repair, dict):
                for path in repair.get("allowed_files", []) or []:
                    if path and path not in allowed_files:
                        allowed_files.append(str(path))
        do_not_touch = []
        repair = failure_packet.get("repair")
        if isinstance(repair, dict):
            do_not_touch = [str(item) for item in repair.get("do_not_touch", []) or []]

        instruction = (
            "Return exactly one bounded unified diff. Use only the leased source and test slices. "
            "Do not invent files, symbols, APIs, dependencies, test results, or repository facts. "
            "Do not include prose. Do not touch files outside allowed_files."
        )
        if role == "repair":
            instruction = (
                "Repair the candidate using the exact failure packet and leased slices. "
                + instruction
            )
        context_payload = {
            "compressed_context": compressed_context,
            "source_slices": source_slices,
            "test_slices": test_slices,
            "failure_packet": bounded_failure,
            "act_capsule": task,
        }
        context_token_estimate = _token_estimate(
            json.dumps(context_payload, default=str)
        )
        while context_token_estimate > session.max_context_tokens and test_slices:
            test_slices.pop()
            context_payload["test_slices"] = test_slices
            context_token_estimate = _token_estimate(
                json.dumps(context_payload, default=str)
            )
        while context_token_estimate > session.max_context_tokens and source_slices:
            source_slices.pop()
            context_payload["source_slices"] = source_slices
            context_token_estimate = _token_estimate(
                json.dumps(context_payload, default=str)
            )
        if context_token_estimate > session.max_context_tokens:
            original_compressed_context = compressed_context
            low = 0
            high = _token_estimate(original_compressed_context)
            best_context: str | None = None
            best_estimate = 0
            while low <= high:
                midpoint = (low + high) // 2
                candidate = _bounded_text(original_compressed_context, midpoint)
                context_payload["compressed_context"] = candidate
                candidate_estimate = _token_estimate(
                    json.dumps(context_payload, default=str)
                )
                if candidate_estimate <= session.max_context_tokens:
                    best_context = candidate
                    best_estimate = candidate_estimate
                    low = midpoint + 1
                else:
                    high = midpoint - 1
            if best_context is None:
                return None
            compressed_context = best_context
            context_payload["compressed_context"] = compressed_context
            context_token_estimate = best_estimate
        turn_index = len(session.turns) + 1
        turn_id = f"TURN-{_digest({'session': session.session_id, 'task': task_id, 'role': role, 'index': turn_index}, size=8)}"
        return ExternalLLMTurn(
            turn_id=turn_id,
            session_id=session.session_id,
            role=role,
            task_id=task_id,
            objective=session.objective,
            gate="ACT" if role == "worker" else "REPAIR",
            instruction=instruction,
            output_contract=dict(_ROLE_CONTRACTS[role]),
            act_capsule=dict(task),
            compressed_context=compressed_context,
            source_slices=source_slices,
            test_slices=test_slices,
            failure_packet=dict(bounded_failure) if isinstance(bounded_failure, dict) else {"value": bounded_failure},
            allowed_files=allowed_files,
            do_not_touch=do_not_touch,
            context_token_estimate=context_token_estimate,
            max_output_tokens=session.max_output_tokens,
            turn_index=turn_index,
            created_at=time.time(),
        )

    def _lease_slices(
        self,
        micro: dict[str, Any],
        *,
        token_budget: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        remaining = max(0, int(token_budget))
        source_slices: list[dict[str, Any]] = []
        test_slices: list[dict[str, Any]] = []

        ranges = list(micro.get("line_ranges", []) or [])
        if ranges:
            for item in ranges[:3]:
                if remaining <= 64:
                    break
                file_path = str(item.get("file") or "")
                symbol = item.get("symbol")
                line_range = list(item.get("line_range", []) or [])
                max_lines = max(8, min(120, remaining // 4))
                result = self.bridge.aura_read_slice(
                    file=file_path,
                    symbol=str(symbol) if symbol else None,
                    line_start=line_range[0] if len(line_range) > 0 and not symbol else None,
                    line_end=line_range[1] if len(line_range) > 1 and not symbol else None,
                    max_lines=max_lines,
                )
                if result.get("ok"):
                    safe = self._compact_slice(result)
                    cost = _token_estimate(json.dumps(safe, sort_keys=True, default=str))
                    if cost <= remaining:
                        source_slices.append(safe)
                        remaining -= cost
        elif micro.get("target_file"):
            result = self.bridge.aura_read_slice(
                file=str(micro.get("target_file")),
                symbol=str(micro.get("target_symbol")) if micro.get("target_symbol") else None,
                max_lines=max(8, min(120, remaining // 4)),
            )
            if result.get("ok"):
                safe = self._compact_slice(result)
                cost = _token_estimate(json.dumps(safe, sort_keys=True, default=str))
                if cost <= remaining:
                    source_slices.append(safe)
                    remaining -= cost

        for test_file in list(micro.get("tests", []) or [])[:2]:
            if remaining <= 96:
                break
            result = self.bridge.aura_read_slice(
                file=str(test_file),
                max_lines=max(12, min(100, remaining // 4)),
            )
            if result.get("ok"):
                safe = self._compact_slice(result)
                cost = _token_estimate(json.dumps(safe, sort_keys=True, default=str))
                if cost <= remaining:
                    test_slices.append(safe)
                    remaining -= cost
        return source_slices, test_slices

    @staticmethod
    def _compact_slice(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "file": result.get("file", ""),
            "symbol": result.get("symbol", ""),
            "line_start": result.get("line_start"),
            "line_end": result.get("line_end"),
            "total_lines": result.get("total_lines"),
            "content": result.get("content", ""),
            "warnings": list(result.get("warnings", []) or []),
            "patch_authority": PATCH_AUTHORITY,
        }

    @staticmethod
    def _error(
        code: str,
        *,
        details: dict[str, Any] | None = None,
        session: ExternalLLMSession | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "error": str(code),
            "details": dict(details or {}),
            "session": session.public_state() if session else None,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "production_mutation": False,
        }


class InstrumentedExternalModelCaller:
    """Adapts any synchronous provider client to Live Architect's model_caller.

    The callback receives a provider-neutral request dict and may return either a
    string or {"text": ..., "usage": ..., "cost_usd": ...}. This lets OpenAI,
    Anthropic, Gemini, Fireworks, Hermes, local models, or a relay service use the
    same Aura architecture without Aura importing their SDKs.
    """

    def __init__(
        self,
        callback: Callable[[dict[str, Any]], Any],
        *,
        hard_prompt_token_limit: int = 16000,
    ) -> None:
        self.callback = callback
        self.hard_prompt_token_limit = int(hard_prompt_token_limit)
        self.records: list[dict[str, Any]] = []

    def __call__(self, provider: str, prompt: str, meta: dict[str, Any]) -> Any:
        prompt_tokens = _token_estimate(prompt)
        if prompt_tokens > self.hard_prompt_token_limit:
            raise ValueError(
                f"leased prompt exceeds hard limit: {prompt_tokens}>{self.hard_prompt_token_limit}"
            )
        request = {
            "version": TURN_VERSION,
            "provider": str(provider),
            "role": str(meta.get("role") or ""),
            "profile": dict(meta.get("profile") or {}),
            "meta": {
                key: value
                for key, value in meta.items()
                if key not in {"profile"}
            },
            "prompt": str(prompt),
            "input_token_estimate": prompt_tokens,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "production_mutation": False,
        }
        started = time.perf_counter()
        raw = self.callback(request)
        latency_ms = (time.perf_counter() - started) * 1000
        if isinstance(raw, dict):
            text = str(raw.get("text") or raw.get("output") or "")
            usage = dict(raw.get("usage") or {})
            cost_usd = raw.get("cost_usd")
        else:
            text = str(raw or "")
            usage = {}
            cost_usd = None
        record = {
            "provider": str(provider),
            "role": request["role"],
            "input_token_estimate": prompt_tokens,
            "output_token_estimate": _token_estimate(text),
            "provider_usage": usage,
            "cost_usd": cost_usd,
            "latency_ms": round(latency_ms, 3),
            "request_digest": _digest(request),
            "response_digest": _digest(text),
        }
        self.records.append(record)
        return text

    def summary(self) -> dict[str, Any]:
        return {
            "call_count": len(self.records),
            "input_token_estimate": sum(item["input_token_estimate"] for item in self.records),
            "output_token_estimate": sum(item["output_token_estimate"] for item in self.records),
            "reported_cost_usd": round(
                sum(float(item["cost_usd"]) for item in self.records if item["cost_usd"] is not None),
                8,
            ),
            "latency_ms": round(sum(float(item["latency_ms"]) for item in self.records), 3),
            "calls": list(self.records),
            "measurement_class": "PROVIDER_REPORTED_WHERE_AVAILABLE_WITH_CHAR4_TOKEN_PROXY",
        }


async def run_live_architect_with_external_callback(
    intent: str,
    *,
    callback: Callable[[dict[str, Any]], Any],
    repo_root: str | Path = ".",
    target_file: str | None = None,
    target_symbol: str | None = None,
    ledger_path: str | Path | None = None,
    staging_path: str | Path | None = None,
    test_commands: list[list[str]] | None = None,
    hard_prompt_token_limit: int = 16000,
) -> dict[str, Any]:
    """Run Aura's real multi-agent Live Architect with a provider-neutral callback.

    Aura still creates planner, critic, judge, worker, verification, rollback, and
    ledger stages. The callback merely supplies model completions for each leased
    role request. Returned usage separates model consumption from Aura's local
    deterministic work.
    """
    from aura_live_architect import run_live_architect_transaction

    caller = InstrumentedExternalModelCaller(
        callback,
        hard_prompt_token_limit=hard_prompt_token_limit,
    )
    transaction = await run_live_architect_transaction(
        intent,
        repo_root=repo_root,
        model_caller=caller,
        target_file=target_file,
        target_symbol=target_symbol,
        ledger_path=ledger_path,
        staging_path=staging_path,
        test_commands=test_commands,
    )
    return {
        "ok": True,
        "transaction": transaction.to_dict(),
        "model_usage": caller.summary(),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
    }
