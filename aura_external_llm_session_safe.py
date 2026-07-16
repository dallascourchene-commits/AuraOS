"""Safe filesystem boundary for persistent external-LLM session exports.

The persistent manager records compact events, token usage, state ledgers, and
redacted content-addressed prompt/response evidence. This adapter confines the
MCP-visible export effect to ``Aura_Staging/external_llm_sessions``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_external_llm_session_persistent import (
    PersistentAuraExternalLLMSessionManager as _BaseSessionManager,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)

EXPORT_ROOT = Path("Aura_Staging") / "external_llm_sessions"


class AuraExternalLLMSessionManager(_BaseSessionManager):
    """Persistent recorded session manager confined to Aura's review workspace."""

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
