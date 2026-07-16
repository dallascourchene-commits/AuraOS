"""Safe filesystem and execution boundary for persistent external-LLM sessions.

The canonical MCP-facing manager confines exports to
``Aura_Staging/external_llm_sessions`` and additionally enforces postconditions
that the legacy base session did not guarantee: complete slice payloads must fit
the leased budget, and no session may advertise a model turn after its turn
budget is exhausted or when the next micro-context cannot be built.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aura_external_llm_session import _token_estimate
from aura_external_llm_session_persistent import (
    PersistentAuraExternalLLMSessionManager as _BaseSessionManager,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)

EXPORT_ROOT = Path("Aura_Staging") / "external_llm_sessions"


class AuraExternalLLMSessionManager(_BaseSessionManager):
    """Persistent recorded session manager confined to Aura's review workspace."""

    def _lease_slices(
        self,
        micro: dict[str, Any],
        *,
        token_budget: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Lease slices while charging the complete serialized payload cost."""
        remaining = max(0, int(token_budget))
        source_slices: list[dict[str, Any]] = []
        test_slices: list[dict[str, Any]] = []

        def admit(result: dict[str, Any], target: list[dict[str, Any]]) -> None:
            nonlocal remaining
            if not result.get("ok"):
                return
            safe = self._compact_slice(result)
            cost = _token_estimate(json.dumps(safe, sort_keys=True, default=str))
            if cost <= remaining:
                target.append(safe)
                remaining -= cost

        ranges = list(micro.get("line_ranges", []) or [])
        if ranges:
            for item in ranges[:3]:
                if remaining <= 64:
                    break
                file_path = str(item.get("file") or "")
                symbol = item.get("symbol")
                line_range = list(item.get("line_range", []) or [])
                admit(
                    self.bridge.aura_read_slice(
                        file=file_path,
                        symbol=str(symbol) if symbol else None,
                        line_start=line_range[0] if len(line_range) > 0 and not symbol else None,
                        line_end=line_range[1] if len(line_range) > 1 and not symbol else None,
                        max_lines=max(8, min(120, remaining // 4)),
                    ),
                    source_slices,
                )
        elif micro.get("target_file") and remaining > 64:
            admit(
                self.bridge.aura_read_slice(
                    file=str(micro.get("target_file")),
                    symbol=str(micro.get("target_symbol")) if micro.get("target_symbol") else None,
                    max_lines=max(8, min(120, remaining // 4)),
                ),
                source_slices,
            )

        for test_file in list(micro.get("tests", []) or [])[:2]:
            if remaining <= 96:
                break
            admit(
                self.bridge.aura_read_slice(
                    file=str(test_file),
                    max_lines=max(12, min(100, remaining // 4)),
                ),
                test_slices,
            )
        return source_slices, test_slices

    def submit_response(
        self,
        *,
        session_id: str,
        turn_id: str,
        response: str,
        provider_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = super().submit_response(
            session_id=session_id,
            turn_id=turn_id,
            response=response,
            provider_usage=provider_usage,
        )
        session = self._sessions.get(str(session_id))
        if session is None:
            return result

        blocked_status = ""
        if len(session.turns) >= session.max_turns and session.pending_turn is not None:
            blocked_status = "BLOCKED_MAX_TURNS"
        elif session.status == "WAITING_FOR_MODEL" and session.pending_turn is None:
            blocked_status = "BLOCKED_NEXT_TURN_UNAVAILABLE"

        if blocked_status:
            session.pending_turn = None
            session.status = blocked_status
            result.update(
                {
                    "ok": False,
                    "status": blocked_status,
                    "session": session.public_state(),
                    "next_turn": None,
                    "error": (
                        "max_turns_exceeded"
                        if blocked_status == "BLOCKED_MAX_TURNS"
                        else "unable_to_build_leased_turn"
                    ),
                }
            )
            if hasattr(self, "_finalize"):
                result["experience"] = self._finalize(session)
        return result

    def export_session(self, session_id: str, output_path: str | Path) -> dict[str, Any]:
        raw = Path(str(output_path or "").strip())
        if not str(raw):
            return self._safe_export_error("output_path_required")
        if raw.is_absolute():
            return self._safe_export_error("absolute_export_path_forbidden")
        if any(part == ".." for part in raw.parts):
            return self._safe_export_error("export_path_traversal_forbidden")

        relative = raw
        export_prefix = EXPORT_ROOT.parts
        if relative.parts[: len(export_prefix)] == export_prefix:
            relative = Path(*relative.parts[len(export_prefix) :])
        if not relative.parts:
            return self._safe_export_error("export_filename_required")

        root = (self.repo_root / EXPORT_ROOT).resolve()
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return self._safe_export_error("export_path_outside_review_workspace")

        root.mkdir(parents=True, exist_ok=True)
        try:
            resolved_root = root.resolve(strict=True)
            resolved_parent = target.parent
            resolved_parent.mkdir(parents=True, exist_ok=True)
            resolved_target = target.resolve()
            resolved_target.relative_to(resolved_root)
        except (OSError, ValueError):
            return self._safe_export_error("export_symlink_or_boundary_violation")

        result = super().export_session(session_id, resolved_target)
        if result.get("ok"):
            result["review_workspace"] = EXPORT_ROOT.as_posix()
            result["relative_path"] = resolved_target.relative_to(self.repo_root).as_posix()
            session = self._sessions.get(str(session_id))
            if session is not None:
                result["chronicle"] = self.chronicle.summary(
                    correlation_id=f"REF-{session.session_id}",
                    session_id=session.session_id,
                )
                result["content_evidence_dir"] = str(self.chronicle.evidence_dir)
        return result

    @staticmethod
    def _safe_export_error(code: str) -> dict[str, Any]:
        return {
            "ok": False,
            "error": code,
            "review_workspace": EXPORT_ROOT.as_posix(),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "production_mutation": False,
        }
