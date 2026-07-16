"""Content-addressed evidence extension for the refactor chronicle.

The compact JSONL chronicle keeps digests and references. Redacted prompt/response
content is stored separately for human recall and replay without injecting full
historical conversations into each future model turn.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aura_arena_experience import sanitize_experience_payload
from aura_refactor_chronicle import RefactorChronicle

EVIDENCE_STORE_VERSION = "AURA_REFACTOR_EVIDENCE_STORE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


class RecordedRefactorChronicle(RefactorChronicle):
    """Refactor chronicle with redacted content-addressed evidence bundles."""

    def __init__(self, *args: Any, evidence_dir: str | Path | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.evidence_dir = (
            Path(evidence_dir).resolve()
            if evidence_dir is not None
            else self.path.parent / "refactor_evidence"
        )
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_type: str,
        *,
        prompt: str = "",
        response: str = "",
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        enriched = dict(payload or {})
        evidence_refs: list[str] = []
        evidence_redactions: list[str] = []
        if prompt or response:
            safe, redactions = sanitize_experience_payload(
                {
                    "version": EVIDENCE_STORE_VERSION,
                    "event_type": str(event_type or ""),
                    "prompt": str(prompt or ""),
                    "response": str(response or ""),
                    "patch_authority": PATCH_AUTHORITY,
                    "vsa_patch_authority": False,
                    "production_mutation": False,
                }
            )
            digest = _digest(safe)
            target = self.evidence_dir / f"{digest}.json"
            if not target.exists():
                temp = target.with_suffix(".tmp")
                temp.write_text(_canonical(safe) + "\n", encoding="utf-8")
                os.replace(temp, target)
            evidence_refs.append(str(target))
            evidence_redactions.extend(str(item) for item in redactions)
            enriched["prompt_evidence_digest"] = _digest(str(prompt or "")) if prompt else ""
            enriched["response_evidence_digest"] = _digest(str(response or "")) if response else ""
        if evidence_refs:
            enriched["content_evidence_refs"] = evidence_refs
            enriched["content_evidence_redactions"] = sorted(set(evidence_redactions))
        result = super().record(
            event_type,
            prompt=prompt,
            response=response,
            payload=enriched,
            **kwargs,
        )
        if result.get("ok"):
            result["content_evidence_refs"] = evidence_refs
            result["content_evidence_redactions"] = sorted(set(evidence_redactions))
        return result


__all__ = ["RecordedRefactorChronicle"]
