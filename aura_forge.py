"""Aura Forge — verified engineering product facade over Aura's Coding Arena.

Aura Forge does not introduce a second planner, staging store, verifier, or
learning path. It freezes the existing Architect/Coding Arena preparation,
compiles an evidence contract from exact Arena outputs, and opens the existing
controlled slice-leased Surgeon session. External models remain replaceable
workers and every completed run stops at human review.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import uuid
from typing import Any, Callable, Mapping, Sequence

FORGE_VERSION = "AURA_FORGE_V1"
FORGE_CONTRACT_VERSION = "AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
REVIEW_READY_STATUS = "READY_FOR_HUMAN_REVIEW"

DEFAULT_REQUIRED_GATES = (
    "canonical_arena_verifier",
    "hotswap_readiness",
)
SUPPORTED_REQUIRED_GATES = frozenset(DEFAULT_REQUIRED_GATES)

_CANONICAL_CONSTRAINTS = (
    "codemap_and_exact_source_grounding_required",
    "reuse_existing_capabilities_before_invention",
    "external_workers_receive_slices_only",
    "staging_and_verification_use_canonical_arena_owners",
    "no_direct_production_mutation",
    "no_automatic_commit_push_pr_or_merge",
    "human_review_required",
)

_SECRET_KEYS = frozenset({
    "api_key",
    "password",
    "private_key",
    "secret",
    "credential",
    "credentials",
    "access_token",
    "auth_token",
    "bearer_token",
    "refresh_token",
    "authorization",
    "client_secret",
    "passphrase",
    "signing_key",
})
_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
_TOKEN_USAGE_KEYS = frozenset({
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
})


def _digest(value: Any, *, size: int = 16) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _clean_strings(values: Sequence[Any] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("expected an array of strings")
    cleaned: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return tuple(cleaned)


def _safe_repo_path(value: Any, *, field_name: str) -> str | None:
    text = str(value or "").replace("\\", "/").strip()
    if not text:
        return None
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field_name} must be a repository-relative path")
    normalized = path.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized == ".":
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _sanitize(value: Any) -> Any:
    """Remove secret-like mapping fields from product-visible evidence."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            is_secret_token = (
                (lowered == "token" or lowered.endswith("_token"))
                and lowered not in _TOKEN_USAGE_KEYS
            )
            if (
                lowered in _SECRET_KEYS
                or lowered.endswith(_SECRET_SUFFIXES)
                or is_secret_token
            ):
                continue
            result[key_text] = _sanitize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def _git_head(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else "UNAVAILABLE"


@dataclass(frozen=True)
class ForgeRunRequest:
    """Human-selected bounds for one verified engineering run."""

    objective: str
    target_file: str | None = None
    target_symbol: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    risk_map: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    provider: str = "external"
    model: str = ""
    council_mode: str = "SELECTIVE_V3"
    council_call_budget: int = 12
    max_context_tokens: int = 2200
    max_output_tokens: int = 2400
    max_turns: int = 12
    max_local_repairs: int = 2
    required_gates: tuple[str, ...] = DEFAULT_REQUIRED_GATES
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: "ForgeRunRequest | Mapping[str, Any]") -> "ForgeRunRequest":
        if isinstance(value, cls):
            raw: Mapping[str, Any] = asdict(value)
        elif isinstance(value, Mapping):
            raw = value
        else:
            raise ValueError("forge request must be an object")

        objective = str(raw.get("objective") or "").strip()
        if not objective:
            raise ValueError("objective is required")

        target_symbol = str(raw.get("target_symbol") or "").strip() or None
        provider = str(raw.get("provider") or "external").strip() or "external"
        model = str(raw.get("model") or "").strip()
        council_mode = str(raw.get("council_mode") or "SELECTIVE_V3").strip().upper()
        if council_mode not in {"AUTO", "SELECTIVE_V3", "FULL_V2"}:
            raise ValueError("Forge council_mode must be AUTO, SELECTIVE_V3, or FULL_V2")

        def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
            value_ = raw.get(name, default)
            if isinstance(value_, bool):
                raise ValueError(f"{name} must be an integer")
            try:
                parsed = int(value_)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError(f"{name} must be an integer") from exc
            if parsed < minimum or parsed > maximum:
                raise ValueError(f"{name} must be between {minimum} and {maximum}")
            return parsed

        if "required_gates" in raw:
            gates = _clean_strings(raw.get("required_gates"))
        else:
            gates = DEFAULT_REQUIRED_GATES
        if not gates:
            raise ValueError("required_gates must not be empty")
        unsupported = sorted(set(gates) - SUPPORTED_REQUIRED_GATES)
        if unsupported:
            raise ValueError(f"unsupported required_gates: {unsupported}")

        metadata_value = raw.get("metadata")
        if metadata_value is None:
            metadata: dict[str, Any] = {}
        elif isinstance(metadata_value, Mapping):
            metadata = _sanitize(dict(metadata_value))
        else:
            raise ValueError("metadata must be an object")

        return cls(
            objective=objective,
            target_file=_safe_repo_path(raw.get("target_file"), field_name="target_file"),
            target_symbol=target_symbol,
            acceptance_criteria=_clean_strings(raw.get("acceptance_criteria")),
            risk_map=_clean_strings(raw.get("risk_map")),
            constraints=_clean_strings(raw.get("constraints")),
            provider=provider,
            model=model,
            council_mode=council_mode,
            council_call_budget=bounded("council_call_budget", 12, 1, 32),
            max_context_tokens=bounded("max_context_tokens", 2200, 256, 16000),
            max_output_tokens=bounded("max_output_tokens", 2400, 128, 16000),
            max_turns=bounded("max_turns", 12, 1, 40),
            max_local_repairs=bounded("max_local_repairs", 2, 0, 8),
            required_gates=gates,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "acceptance_criteria",
            "risk_map",
            "constraints",
            "required_gates",
        ):
            payload[key] = list(payload[key])
        payload["metadata"] = _sanitize(payload["metadata"])
        return payload


@dataclass(frozen=True)
class ForgeEvidenceContract:
    """Exact, reviewable authority and proof contract for one Forge run."""

    contract_id: str
    request_digest: str
    objective: str
    objective_digest: str
    repository: Mapping[str, Any]
    plan_phase_hash: str
    act_capsules: tuple[Mapping[str, Any], ...]
    task_evidence: tuple[Mapping[str, Any], ...]
    acceptance_criteria: tuple[str, ...]
    risk_map: tuple[str, ...]
    constraints: tuple[str, ...]
    required_gates: tuple[str, ...]
    allowed_files: tuple[str, ...]
    worker_contract: Mapping[str, Any]
    authority: Mapping[str, Any]
    lifecycle: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    version: str = FORGE_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "act_capsules",
            "task_evidence",
            "acceptance_criteria",
            "risk_map",
            "constraints",
            "required_gates",
            "allowed_files",
            "lifecycle",
        ):
            payload[key] = list(payload[key])
        return _sanitize(payload)


SessionManagerFactory = Callable[[ForgeRunRequest, Any, Path], Any]


class AuraForgeRuntime:
    """Product facade over canonical Coding Arena and controlled Surgeon owners."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        bridge: Any | None = None,
        session_manager_factory: SessionManagerFactory | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        if bridge is None:
            from aura_agent_arena_bridge import AuraAgentArenaBridge

            bridge = AuraAgentArenaBridge(repo_root=self.repo_root)
        self.bridge = bridge
        self._session_manager_factory = session_manager_factory or self._default_session_manager
        self._runs: dict[str, dict[str, Any]] = {}
        self._run_counter = 0

    @staticmethod
    def _default_session_manager(request: ForgeRunRequest, bridge: Any, repo_root: Path) -> Any:
        from aura_controlled_refactor_session import ControlledRefactorSessionManager

        return ControlledRefactorSessionManager(
            repo_root=repo_root,
            bridge=bridge,
            surface="coding_arena",
            control={
                "council_mode": request.council_mode,
                "council_call_budget": request.council_call_budget,
                "surgeon_mode": "STAGE_AND_VERIFY",
                "surgeon_max_turns": request.max_turns,
                "surgeon_max_local_repairs": request.max_local_repairs,
                "surgeon_context_tokens": request.max_context_tokens,
                "surgeon_output_tokens": request.max_output_tokens,
                "record_outputs": True,
                "human_review_required": True,
                "production_mutation": False,
                "vsa_patch_authority": False,
                "output_root": "Aura_Staging/aura_forge",
            },
        )

    @staticmethod
    def _error(code: str, *, stage: str, details: Any = None) -> dict[str, Any]:
        result = {
            "ok": False,
            "version": FORGE_VERSION,
            "error": code,
            "stage": stage,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        if details is not None:
            result["details"] = _sanitize(details)
        return result

    def prepare(self, value: ForgeRunRequest | Mapping[str, Any]) -> dict[str, Any]:
        """Compile a frozen Coding Arena plan and evidence contract; execute nothing."""
        try:
            request = ForgeRunRequest.from_value(value)
        except ValueError as exc:
            return self._error(str(exc), stage="REQUEST")

        try:
            repo_digest = self.bridge.aura_repo_digest(include_hubs=False, max_lines=80)
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "repository_digest_error",
                stage="GROUND",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(repo_digest, Mapping):
            return self._error("repository_digest_invalid", stage="GROUND")
        if not repo_digest.get("ok"):
            return self._error("repository_digest_unavailable", stage="GROUND", details=repo_digest)

        all_constraints = [*_CANONICAL_CONSTRAINTS, *request.constraints]
        try:
            prepared = self.bridge.aura_prepare_arena(
                objective=request.objective,
                target_file=request.target_file,
                target_symbol=request.target_symbol,
                acceptance_criteria=list(request.acceptance_criteria),
                risk_map=list(request.risk_map),
                constraints=list(dict.fromkeys(all_constraints)),
            )
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "arena_prepare_error",
                stage="PLAN",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(prepared, Mapping):
            return self._error("arena_prepare_invalid", stage="PLAN")
        if not prepared.get("ok"):
            return self._error("arena_prepare_failed", stage="PLAN", details=prepared)
        if list(prepared.get("blockers") or []):
            return self._error("arena_prepare_blocked", stage="PLAN", details=prepared)
        if prepared.get("builder_patch_authorized") is not True:
            return self._error("builder_patch_not_authorized", stage="PLAN", details=prepared)

        act_capsules = [dict(item) for item in prepared.get("act_capsules", []) if isinstance(item, Mapping)]
        if not act_capsules:
            return self._error("prepared_arena_has_no_act_capsules", stage="PLAN")

        task_evidence: list[dict[str, Any]] = []
        for capsule in act_capsules:
            task_id = str(capsule.get("task_id") or "")
            try:
                micro = self.bridge.aura_get_micro_context(
                    plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
                    task_id=task_id,
                    depth=1,
                    format="both",
                    max_tokens_est=min(800, request.max_context_tokens),
                )
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "task_micro_context_error",
                    stage="GROUND",
                    details={"task_id": task_id, "exception_type": type(exc).__name__},
                )
            if not isinstance(micro, Mapping):
                return self._error(
                    "task_micro_context_invalid",
                    stage="GROUND",
                    details={"task_id": task_id},
                )
            if not micro.get("ok"):
                return self._error(
                    "task_micro_context_unavailable",
                    stage="GROUND",
                    details={"task_id": task_id, "micro_context": micro},
                )
            task_evidence.append(
                _sanitize(
                    {
                        "task_id": task_id,
                        "target_file": micro.get("target_file"),
                        "target_symbol": micro.get("target_symbol"),
                        "line_ranges": micro.get("line_ranges", []),
                        "dependencies": micro.get("dependencies", []),
                        "tests": micro.get("tests", []),
                        "route_decision": micro.get("route_decision", {}),
                        "compressed_context_digest": _digest(micro.get("compressed_context", "")),
                        "jspace_present": bool(micro.get("jspace_packet")),
                        "st3gg_present": bool(micro.get("st3gg_egress")),
                    }
                )
            )

        contract = self._compile_contract(request, repo_digest, prepared, act_capsules, task_evidence)
        run_id = f"FORGE-{contract.contract_id[:16]}-{uuid.uuid4().hex[:12]}"
        self._runs[run_id] = {
            "request": request,
            "contract": contract,
            "prepared": dict(prepared),
            "manager": None,
            "session_id": "",
            "last_result": {},
            "status": "PREPARED",
        }
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": "PREPARED",
            "contract": contract.to_dict(),
            "prepared": _sanitize(prepared),
            "production_mutation": False,
            "human_review_required": True,
        }

    def start(self, value: ForgeRunRequest | Mapping[str, Any]) -> dict[str, Any]:
        """Prepare the contract and open the existing frozen-plan Surgeon session."""
        prepared_result = self.prepare(value)
        if not prepared_result.get("ok"):
            return prepared_result

        run_id = str(prepared_result["run_id"])
        state = self._runs[run_id]
        request: ForgeRunRequest = state["request"]
        try:
            manager = self._session_manager_factory(request, self.bridge, self.repo_root)
            opened = manager.open_prepared_session(
                prepared_arena=state["prepared"],
                objective=request.objective,
                provider=request.provider,
                model=request.model,
                run_id=run_id,
                metadata={
                    **dict(request.metadata),
                    "forge_version": FORGE_VERSION,
                    "forge_contract_id": state["contract"].contract_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            state["status"] = "BLOCKED_SESSION_EXCEPTION"
            return self._error(
                "controlled_session_open_error",
                stage="ACT",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(opened, Mapping):
            state["status"] = "BLOCKED_SESSION_INVALID"
            return self._error("controlled_session_open_invalid", stage="ACT")
        if not opened.get("session_created"):
            state["last_result"] = dict(opened)
            state["status"] = "BLOCKED_SESSION_OPEN"
            return self._error("controlled_session_open_failed", stage="ACT", details=opened)

        session = dict(opened.get("session") or {})
        session_id = str(session.get("session_id") or "")
        if not session_id:
            state["status"] = "BLOCKED_SESSION_ID"
            return self._error("controlled_session_missing_id", stage="ACT", details=opened)

        state.update(
            {
                "manager": manager,
                "session_id": session_id,
                "last_result": dict(opened),
                "status": str(session.get("status") or "WAITING_FOR_MODEL"),
            }
        )
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": state["status"],
            "contract": state["contract"].to_dict(),
            "session": _sanitize(session),
            "turn": _sanitize(opened.get("turn") or session.get("pending_turn")),
            "control_profile": _sanitize(opened.get("control_profile", {})),
            "production_mutation": False,
            "human_review_required": True,
        }

    def submit(
        self,
        *,
        run_id: str,
        turn_id: str,
        response: str,
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = self._runs.get(str(run_id))
        if state is None:
            return self._error("forge_run_not_found", stage="ACT")
        manager = state.get("manager")
        if manager is None:
            return self._error("forge_run_not_started", stage="ACT")

        try:
            result = manager.submit_response(
                session_id=state["session_id"],
                turn_id=str(turn_id),
                response=str(response or ""),
                provider_usage=_sanitize(dict(provider_usage or {})),
            )
        except Exception as exc:  # noqa: BLE001
            state["status"] = "BLOCKED_SUBMIT_EXCEPTION"
            return self._error(
                "controlled_session_submit_error",
                stage="ACT",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(result, Mapping):
            state["status"] = "BLOCKED_SUBMIT_INVALID"
            return self._error("controlled_session_submit_invalid", stage="ACT")
        state["last_result"] = dict(result)
        session = dict(result.get("session") or {})
        state["status"] = str(result.get("status") or session.get("status") or state["status"])
        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
            "human_review_packet": self.human_review_packet(run_id)
            if state["status"] == REVIEW_READY_STATUS
            else None,
            "production_mutation": False,
            "human_review_required": True,
        }

    def status(self, run_id: str) -> dict[str, Any]:
        state = self._runs.get(str(run_id))
        if state is None:
            return self._error("forge_run_not_found", stage="STATUS")
        manager = state.get("manager")
        session: dict[str, Any] = {}
        if manager is not None:
            try:
                current = manager.get_session(state["session_id"])
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "controlled_session_status_error",
                    stage="STATUS",
                    details={"exception_type": type(exc).__name__},
                )
            if not isinstance(current, Mapping):
                return self._error("controlled_session_status_invalid", stage="STATUS")
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])
        review_packet = (
            self.human_review_packet(run_id)
            if state["status"] == REVIEW_READY_STATUS
            else None
        )
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": state["status"],
            "contract": state["contract"].to_dict(),
            "session": _sanitize(session),
            "decision_eligible": bool(
                review_packet and review_packet.get("decision_eligible") is True
            ),
            "human_review_packet": review_packet,
            "production_mutation": False,
            "human_review_required": True,
        }

    def human_review_packet(self, run_id: str) -> dict[str, Any]:
        state = self._runs.get(str(run_id))
        if state is None:
            return self._error("forge_run_not_found", stage="DECIDE")

        manager = state.get("manager")
        session: dict[str, Any] = {}
        if manager is not None:
            try:
                current = manager.get_session(state["session_id"])
            except Exception as exc:  # noqa: BLE001
                return self._error(
                    "controlled_session_review_error",
                    stage="DECIDE",
                    details={"exception_type": type(exc).__name__},
                )
            if not isinstance(current, Mapping):
                return self._error("controlled_session_review_invalid", stage="DECIDE")
            if current.get("ok"):
                session = dict(current.get("session") or {})
                state["status"] = str(session.get("status") or state["status"])

        last_result = dict(state.get("last_result") or {})
        verification = dict(last_result.get("verification") or {})
        hotswap_status = dict(last_result.get("hotswap_status") or {})
        if state.get("session_id") and not hotswap_status:
            try:
                hotswap_status = dict(
                    self.bridge.aura_hotswap_status(
                        plan_phase_hash=state["contract"].plan_phase_hash
                    )
                    or {}
                )
            except Exception:  # noqa: BLE001
                hotswap_status = {}

        ready = state["status"] == REVIEW_READY_STATUS
        gate_results = {
            "canonical_arena_verifier": bool(
                verification.get("ok") is True and not list(verification.get("failures") or [])
            ),
            "hotswap_readiness": bool(
                verification.get("hotswap_ready") is True
                or hotswap_status.get("hotswap_ready") is True
            ),
        }
        required = state["contract"].required_gates
        decision_eligible = bool(ready and all(gate_results.get(name) is True for name in required))
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "packet_type": "AURA_FORGE_HUMAN_REVIEW_PACKET_V1",
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
            "status": state["status"],
            "session": _sanitize(session),
            "verification": _sanitize(verification),
            "hotswap_status": _sanitize(hotswap_status),
            "required_gate_results": gate_results,
            "decision_eligible": decision_eligible,
            "decision_options": [
                "ACCEPT_FOR_SEPARATE_PROMOTION_REVIEW",
                "REQUEST_REPAIR_OR_REPLAN",
                "REJECT",
            ],
            "promotion_performed": False,
            "production_mutation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def export(self, run_id: str, output_path: str | Path) -> dict[str, Any]:
        state = self._runs.get(str(run_id))
        if state is None:
            return self._error("forge_run_not_found", stage="EXPORT")
        manager = state.get("manager")
        if manager is None:
            return self._error("forge_run_not_started", stage="EXPORT")
        try:
            result = manager.export_session(state["session_id"], output_path)
        except Exception as exc:  # noqa: BLE001
            return self._error(
                "controlled_session_export_error",
                stage="EXPORT",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(result, Mapping):
            return self._error("controlled_session_export_invalid", stage="EXPORT")
        return {
            **_sanitize(result),
            "version": FORGE_VERSION,
            "run_id": run_id,
            "contract_id": state["contract"].contract_id,
            "production_mutation": False,
            "human_review_required": True,
        }

    def _compile_contract(
        self,
        request: ForgeRunRequest,
        repo_digest: Mapping[str, Any],
        prepared: Mapping[str, Any],
        act_capsules: Sequence[Mapping[str, Any]],
        task_evidence: Sequence[Mapping[str, Any]],
    ) -> ForgeEvidenceContract:
        allowed_files: list[str] = []
        for capsule in act_capsules:
            for candidate in [capsule.get("target_file"), *list(capsule.get("related_files") or [])]:
                path = _safe_repo_path(candidate, field_name="allowed_file") if candidate else None
                if path and path not in allowed_files:
                    allowed_files.append(path)

        constraints = tuple(dict.fromkeys([*_CANONICAL_CONSTRAINTS, *request.constraints]))
        repository = _sanitize(
            {
                "head_sha": _git_head(self.repo_root),
                "codemap_status": repo_digest.get("codemap_status"),
                "file_count": repo_digest.get("file_count"),
                "symbol_count": repo_digest.get("symbol_count"),
                "topology_nodes": repo_digest.get("topology_nodes"),
                "topology_edges": repo_digest.get("topology_edges"),
                "source_of_truth": repo_digest.get("source_of_truth", []),
            }
        )
        request_payload = request.to_dict()
        request_digest = _digest(request_payload)
        identity_payload = {
            "request_digest": request_digest,
            "repository": repository,
            "plan_phase_hash": str(prepared.get("plan_phase_hash") or ""),
            "act_capsules": list(act_capsules),
            "task_evidence": list(task_evidence),
            "required_gates": list(request.required_gates),
        }
        contract_id = _digest(identity_payload)
        return ForgeEvidenceContract(
            contract_id=contract_id,
            request_digest=request_digest,
            objective=request.objective,
            objective_digest=_digest(request.objective),
            repository=repository,
            plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
            act_capsules=tuple(_sanitize(dict(item)) for item in act_capsules),
            task_evidence=tuple(_sanitize(dict(item)) for item in task_evidence),
            acceptance_criteria=request.acceptance_criteria,
            risk_map=request.risk_map,
            constraints=constraints,
            required_gates=request.required_gates,
            allowed_files=tuple(allowed_files),
            worker_contract={
                "provider": request.provider,
                "model": request.model,
                "input": "bounded_exact_source_and_test_slices",
                "required_response": "unified_diff_only",
                "max_context_tokens": request.max_context_tokens,
                "max_output_tokens": request.max_output_tokens,
                "max_turns": request.max_turns,
                "max_local_repairs": request.max_local_repairs,
                "council_mode": request.council_mode,
                "council_call_budget": request.council_call_budget,
            },
            authority={
                "planning_proposes": True,
                "verification_proves": True,
                "human_authorizes": True,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "production_mutation": False,
                "automatic_commit": False,
                "automatic_push": False,
                "automatic_pull_request": False,
                "automatic_merge": False,
            },
            lifecycle=(
                "FRAME",
                "GROUND",
                "PLAN",
                "ACT",
                "PROVE",
                "DECIDE",
                "DISSOLVE",
            ),
            metadata=request.metadata,
        )


def validate_forge_contract(value: Mapping[str, Any]) -> list[str]:
    """Return structural contract errors without granting execution authority."""
    if not isinstance(value, Mapping):
        return ["contract_must_be_object"]
    required = {
        "version", "contract_id", "request_digest", "objective", "objective_digest",
        "repository", "plan_phase_hash", "act_capsules", "task_evidence",
        "required_gates", "allowed_files", "worker_contract", "authority", "lifecycle",
    }
    errors = [f"missing:{name}" for name in sorted(required - set(value))]
    if value.get("version") != FORGE_CONTRACT_VERSION:
        errors.append("unsupported_version")
    for name in ("contract_id", "request_digest", "objective", "objective_digest", "plan_phase_hash"):
        if not str(value.get(name) or "").strip():
            errors.append(f"{name}_must_not_be_empty")
    if not isinstance(value.get("repository"), Mapping):
        errors.append("repository_must_be_object")
    if not isinstance(value.get("worker_contract"), Mapping):
        errors.append("worker_contract_must_be_object")

    authority = value.get("authority")
    expected_authority = {
        "planning_proposes": True,
        "verification_proves": True,
        "human_authorizes": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
    }
    if isinstance(authority, Mapping):
        for name, expected in expected_authority.items():
            if authority.get(name) != expected:
                errors.append(f"invalid_authority:{name}")
    else:
        errors.append("authority_must_be_object")

    gates_value = value.get("required_gates")
    if not isinstance(gates_value, (list, tuple)):
        errors.append("required_gates_must_be_array")
    elif not gates_value:
        errors.append("required_gates_must_not_be_empty")
    else:
        unsupported = sorted(set(gates_value) - SUPPORTED_REQUIRED_GATES)
        if unsupported:
            errors.append(f"unsupported_required_gates:{','.join(unsupported)}")

    capsules_value = value.get("act_capsules")
    if not isinstance(capsules_value, (list, tuple)):
        errors.append("act_capsules_must_be_array")
    elif not capsules_value:
        errors.append("act_capsules_must_not_be_empty")

    evidence_value = value.get("task_evidence")
    if not isinstance(evidence_value, (list, tuple)):
        errors.append("task_evidence_must_be_array")
    elif not evidence_value:
        errors.append("task_evidence_must_not_be_empty")

    expected_lifecycle = ["FRAME", "GROUND", "PLAN", "ACT", "PROVE", "DECIDE", "DISSOLVE"]
    lifecycle_value = value.get("lifecycle")
    if not isinstance(lifecycle_value, (list, tuple)) or list(lifecycle_value) != expected_lifecycle:
        errors.append("invalid_lifecycle")

    allowed_files = value.get("allowed_files")
    if not isinstance(allowed_files, list):
        errors.append("allowed_files_must_be_array")
    else:
        for item in allowed_files:
            try:
                _safe_repo_path(item, field_name="allowed_file")
            except ValueError:
                errors.append(f"invalid_allowed_file:{item}")
    return errors


__all__ = [
    "AuraForgeRuntime",
    "DEFAULT_REQUIRED_GATES",
    "FORGE_CONTRACT_VERSION",
    "FORGE_VERSION",
    "ForgeEvidenceContract",
    "ForgeRunRequest",
    "PATCH_AUTHORITY",
    "REVIEW_READY_STATUS",
    "SUPPORTED_REQUIRED_GATES",
    "VSA_PATCH_AUTHORITY",
    "validate_forge_contract",
]
