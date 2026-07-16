"""Persistent recorded-session adapter with redacted prompt/response evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from aura_external_llm_session_recorded import (
    RecordedAuraExternalLLMSessionManager as _RecordedManager,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)
from aura_refactor_chronicle_recorded import RecordedRefactorChronicle


class PersistentAuraExternalLLMSessionManager(_RecordedManager):
    """Record compact events plus content-addressed, redacted turn evidence."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        bridge: Any | None = None,
        *,
        chronicle_path: str | Path | None = None,
        experience_db_path: str | Path | None = None,
        evidence_dir: str | Path | None = None,
        max_local_repairs: int = 2,
    ) -> None:
        super().__init__(
            repo_root=repo_root,
            bridge=bridge,
            chronicle_path=chronicle_path,
            experience_db_path=experience_db_path,
            max_local_repairs=max_local_repairs,
        )
        self.chronicle = RecordedRefactorChronicle(
            self.repo_root,
            path=chronicle_path,
            experience_db_path=experience_db_path,
            evidence_dir=evidence_dir,
        )


__all__ = [
    "PersistentAuraExternalLLMSessionManager",
    "PATCH_AUTHORITY",
    "VSA_PATCH_AUTHORITY",
]
