"""Feature-flagged Coding Workbench integration for C2 route capsules.

The legacy ``CodingWorkbenchWFSTSession`` remains unchanged. This opt-in subclass
replaces only the runtime and localization action, preserving every existing gate,
state transition, review requirement, and no-commit/no-merge boundary.
"""
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any, Iterable

from aura_arena_experience import build_arena_experience
from aura_arena_wfst_compiler import ARENA_WFST_COMPILER_VERSION
from aura_coding_workbench_wfst_adapter import (
    CodingWorkbenchWFSTSession,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    _action_packet,
    _git_value,
    _source_hashes_from_evidence,
    _working_tree_digest,
)
from aura_route_capsule_live_runtime import (
    ROUTE_CAPSULE_LIVE_RUNTIME_VERSION,
    CapsuleAwareArenaWFSTRuntime,
)

CODING_WORKBENCH_CAPSULE_ADAPTER_VERSION = "AURA_CODING_WORKBENCH_CAPSULE_ADAPTER_V1"


class CapsuleCodingWorkbenchWFSTSession(CodingWorkbenchWFSTSession):
    """Opt-in session that executes one bounded localization capsule path."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        session_path: str | Path | None = None,
        restore: bool = True,
        route_capsules_enabled: bool = False,
        capsule_lease_capabilities: Iterable[str] = (),
        requested_model: str = "",
    ) -> None:
        self.route_capsules_enabled = bool(route_capsules_enabled)
        self.capsule_lease_capabilities = tuple(
            dict.fromkeys(str(item).strip() for item in capsule_lease_capabilities if str(item).strip())
        )
        self.requested_model = str(requested_model or "").strip()
        self._capsule_context_items: list[dict[str, Any]] = []
        self._capsule_memory_refs: list[str] = []
        self._capsule_budget_consumed: dict[str, float] = {}
        super().__init__(repo_root=repo_root, session_path=session_path, restore=restore)

        runtime = CapsuleAwareArenaWFSTRuntime(
            repo_root=self.repo_root,
            route_capsules_enabled=self.route_capsules_enabled,
        )
        route_root = self.repo_root / ".aura" / "arena_routes"
        coding = runtime.register_manifest(route_root / "coding.v1.json")
        meta = runtime.register_manifest(route_root / "meta.v1.json")
        capsule_localize = runtime.attach_capsule(
            arena_id="coding_workbench",
            transition_id="CODING.TASK_SCOPED.LOCALIZE_CODE",
            route_capsule_ref=".aura/route_capsules/coding_localize.v1.json",
            morphology_profile_ref=".aura/morphology_profiles/six_slot.v1.json",
            feature_flag="c2_coding_localization_enabled",
        )
        self.runtime = runtime
        self.initialization = {
            "coding": coding,
            "meta": meta,
            "capsule_localize": capsule_localize,
        }
        self._event(
            "c2_runtime",
            f"enabled={self.route_capsules_enabled};leases={len(self.capsule_lease_capabilities)}",
        )
        self._persist()

    def _ready(self) -> bool:
        base_ready = bool(
            self.initialization.get("coding", {}).get("ok")
            and self.initialization.get("meta", {}).get("ok")
        )
        if not self.route_capsules_enabled:
            return base_ready
        return bool(base_ready and self.initialization.get("capsule_localize", {}).get("ok"))

    def get_state(self) -> dict[str, Any]:
        state = super().get_state()
        state.update({
            "version": CODING_WORKBENCH_CAPSULE_ADAPTER_VERSION,
            "route_capsules_enabled": self.route_capsules_enabled,
            "capsule_lease_capabilities": list(self.capsule_lease_capabilities),
            "requested_model": self.requested_model,
            "automatic_capsule_activation": False,
        })
        return state

    def _policy(self) -> dict[str, Any]:
        policy = super()._policy()
        policy.update({
            "route_capsules_enabled": self.route_capsules_enabled,
            "c2_coding_localization_enabled": self.route_capsules_enabled,
            "grounding_class": "exact_source_hashes",
            "context_class": "bounded_route_capsule",
            "model_class": self.requested_model or "no_model",
            "resource_budget": "coding_localize.v1",
        })
        return policy

    def _context(self, payload: dict[str, Any]) -> dict[str, Any]:
        context = super()._context(payload)
        leases = payload.get("lease_capabilities")
        if leases is None:
            leases = self.capsule_lease_capabilities
        context.update({
            "lease_capabilities": tuple(str(item) for item in leases or ()),
            "requested_model": str(payload.get("requested_model") or self.requested_model),
            "capsule_context_items": list(payload.get("capsule_context_items") or self._capsule_context_items),
            "capsule_memory_refs": list(payload.get("capsule_memory_refs") or self._capsule_memory_refs),
            "capsule_budget_consumed": dict(
                payload.get("capsule_budget_consumed") or self._capsule_budget_consumed
            ),
            "exact_target": str(payload.get("exact_target") or ""),
            "target_file": str(payload.get("target_file") or ""),
            "target_symbol": str(payload.get("target_symbol") or ""),
            "request_voice": "HUMAN_AGENT",
        })
        return context

    def _record_experience(
        self, *, started_at: float, state_before: str, state_after: str,
        selected_transition: str, final_outcome: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        ledger = self._ledger_instance()
        if ledger is None:
            return {
                "ok": False,
                "reason": self._ledger_error or "experience_ledger_unavailable",
                "persistent": False,
            }
        try:
            experience = build_arena_experience(
                arena_id="coding_workbench",
                arena_version="AURA_CODING_WORKBENCH_SEQUENCE_V1",
                grammar_version="coding-workbench-wfst-v1",
                runtime_version=ROUTE_CAPSULE_LIVE_RUNTIME_VERSION,
                compiler_version=ARENA_WFST_COMPILER_VERSION,
                state_before=state_before,
                state_after=state_after,
                selected_transition=selected_transition,
                final_outcome=final_outcome,
                payload={
                    "evidence_keys": sorted(self.evidence),
                    "capsule_usage": dict(self.evidence.get("route_capsule_usage") or {}),
                    **payload,
                },
                task_id=self.session_id,
                workflow_id=self.session_id,
                started_at=started_at,
                completed_at=time.time(),
                repository_commit_sha=_git_value(self.repo_root, ["rev-parse", "HEAD"]),
                working_tree_digest=_working_tree_digest(self.repo_root),
                objective=self.objective,
                source_hashes=_source_hashes_from_evidence(self.evidence),
            )
            result = ledger.record(experience)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "reason": f"experience_record_failed:{type(exc).__name__}",
                "persistent": False,
            }
        return {**result, "persistent": bool(result.get("ok"))}

    def _do_localize_code(self, payload: dict[str, Any]) -> dict[str, Any]:
        from aura_coding_workbench_actions import localize_code

        started = time.perf_counter()
        output = dict(localize_code(self.objective, repo_root=self.repo_root) or {})
        selected = dict((getattr(self.runtime, "last_route", {}) or {}).get("selected") or {})
        aperture = dict(selected.get("materialized_aperture") or {})
        if self.route_capsules_enabled and not aperture:
            return self._denial(
                "enabled_route_capsule_was_not_materialized",
                action_id="localize_code",
            )

        data_aperture = dict(aperture.get("data_aperture") or {})
        maximum_files = _positive_int(data_aperture.get("maximum_files"), 0)
        maximum_symbols = _positive_int(data_aperture.get("maximum_symbols"), 0)
        maximum_lines = _positive_int(data_aperture.get("maximum_lines"), 0)

        files = list(output.get("localized_files") or [])
        symbols = list(output.get("localized_symbols") or [])
        line_ranges = list(output.get("line_ranges") or [])
        if maximum_files:
            files = files[:maximum_files]
        if maximum_symbols:
            symbols = symbols[:maximum_symbols]
        line_ranges = _bounded_line_ranges(line_ranges, maximum_lines)

        output["localized_files"] = files
        output["localized_symbols"] = symbols
        output["line_ranges"] = line_ranges
        elapsed = max(0.0, time.perf_counter() - started)
        context_items = _localization_context_items(files, symbols, line_ranges)
        capability_bindings = [
            str(item.get("capability_id") or "")
            for item in (aperture.get("tool_bundle") or {}).get("capability_bindings", [])
            if str(item.get("capability_id") or "")
        ]
        tool_calls = ["aura_code_region_ranker.rank_code_regions"]
        selected_model = str(aperture.get("selected_model") or "")
        consumed = {
            "input_tokens": max(1.0, len(self.objective) / 4.0) if self.objective else 0.0,
            "output_tokens": max(
                1.0,
                len(json.dumps({"files": files, "symbols": symbols, "ranges": line_ranges}, default=str)) / 4.0,
            ),
            "tool_calls": float(len(tool_calls)),
            "model_calls": 0.0 if selected_model in {"", "no_model"} else 1.0,
            "wall_seconds": elapsed,
        }
        capsule_usage = {
            "capsule_id": (selected.get("route_capsule") or {}).get("capsule_id"),
            "capsule_digest": (selected.get("route_capsule") or {}).get("capsule_digest"),
            "aperture_digest": aperture.get("aperture_digest"),
            "context_items": context_items,
            "tool_calls": tool_calls,
            "bound_capabilities": capability_bindings,
            "model": selected_model,
            "budget_consumed": consumed,
            "runtime_execution_performed": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        output["capsule_usage"] = capsule_usage
        output["route_capsule_enforced"] = bool(aperture)
        exceeded = _exceeded_budget(aperture.get("execution_budget") or {}, consumed)
        if exceeded:
            output.update({
                "ok": False,
                "status": "DENIED",
                "reason": "capsule_budget_exceeded_after_execution",
                "message": "Measured localization usage exceeded the pinned capsule budget.",
                "missing_evidence": [f"budget_within:{name}" for name in exceeded],
                "budget_exceeded": exceeded,
            })

        if output.get("ok"):
            self.evidence.update({
                "localized_files": files,
                "localized_symbols": symbols,
                "line_ranges": line_ranges,
                "route_capsule_usage": capsule_usage,
            })
            self._capsule_context_items = context_items
            self._capsule_budget_consumed = consumed

        packet = _action_packet(output, "localize_code", produced={
            "localized_files": files,
            "localized_symbols": symbols,
            "line_ranges": line_ranges,
            "route_capsule_usage": capsule_usage,
        })
        packet["capsule_usage"] = capsule_usage
        return packet


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _bounded_line_ranges(ranges: list[Any], maximum_lines: int) -> list[Any]:
    if not maximum_lines:
        return ranges
    output: list[Any] = []
    consumed = 0
    for item in ranges:
        if isinstance(item, dict):
            start = _positive_int(item.get("start") or item.get("line_start"), 0)
            end = _positive_int(item.get("end") or item.get("line_end"), start)
            count = max(0, end - start + 1) if start else _positive_int(item.get("line_count"), 0)
        else:
            count = 0
        if consumed + count > maximum_lines:
            continue
        output.append(item)
        consumed += count
    return output


def _localization_context_items(
    files: list[Any], symbols: list[Any], ranges: list[Any]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, raw_file in enumerate(files):
        if isinstance(raw_file, dict):
            path = str(raw_file.get("path") or raw_file.get("file") or "")
            source_hash = str(raw_file.get("source_hash") or raw_file.get("hash") or "")
        else:
            path = str(raw_file or "")
            source_hash = ""
        line_range = ranges[index] if index < len(ranges) and isinstance(ranges[index], dict) else {}
        symbol = symbols[index] if index < len(symbols) else ""
        output.append({
            "path": path,
            "symbol": str(symbol or ""),
            "line_start": _positive_int(line_range.get("start") or line_range.get("line_start"), 0),
            "line_end": _positive_int(line_range.get("end") or line_range.get("line_end"), 0),
            "line_count": _positive_int(line_range.get("line_count"), 0),
            "source_hash": source_hash,
        })
    return output


def _exceeded_budget(budget: dict[str, Any], consumed: dict[str, float]) -> list[str]:
    exceeded: list[str] = []
    for name, used in consumed.items():
        try:
            limit = max(0.0, float(budget.get(name, 0.0)))
        except (TypeError, ValueError):
            limit = 0.0
        if limit and used > limit:
            exceeded.append(name)
    return exceeded
