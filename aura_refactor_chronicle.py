"""Append-only refactor history for replay, human recall, and governed learning.

Every refactor session can emit small immutable events while it moves through plan,
leased model turns, staging, verification, repair, and human review.  The chronicle
is descriptive evidence only: it grants no patch or promotion authority.

Terminal sessions are also projected into Aura's existing ArenaExperience V3
ledger so refactor outcomes participate in the same governed learning substrate as
other Arenas instead of creating a disconnected memory silo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable

from aura_arena_experience import build_arena_experience, sanitize_experience_payload
from aura_arena_experience_ledger import ArenaExperienceLedger

REFACTOR_CHRONICLE_VERSION = "AURA_REFACTOR_CHRONICLE_V1"
REFACTOR_EXPERIENCE_ARENA_ID = "AURA_REFACTOR_ARENA"
REFACTOR_EXPERIENCE_ARENA_VERSION = "AURA_REFACTOR_ARENA_V1"
REFACTOR_GRAMMAR_VERSION = "AURA_REFACTOR_EVENT_GRAMMAR_V1"
REFACTOR_RUNTIME_VERSION = "AURA_EXTERNAL_LLM_SESSION_V1"
REFACTOR_COMPILER_VERSION = "AURA_ARCHITECT_LOOP_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_EVENT_FIELDS = (
    "event_type",
    "correlation_id",
    "session_id",
    "objective_hash",
    "plan_phase_hash",
    "task_id",
    "gate",
    "status",
    "provider",
    "model",
    "input_tokens_estimated",
    "output_tokens_estimated",
    "input_tokens_reported",
    "output_tokens_reported",
    "cost_usd_reported",
    "prompt_digest",
    "response_digest",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_canonical(value).encode("utf-8"), digest_size=size).hexdigest()


def _objective_hash(objective: str) -> str:
    return _digest(str(objective or ""), size=16) if str(objective or "").strip() else ""


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _git_sha(root: Path) -> str:
    head = root / ".git" / "HEAD"
    try:
        value = head.read_text(encoding="utf-8").strip()
        if value.startswith("ref:"):
            ref = root / ".git" / value.split(":", 1)[1].strip()
            return ref.read_text(encoding="utf-8").strip()[:128]
        return value[:128]
    except OSError:
        return ""


def _grammar_manifest_digest() -> str:
    return _digest(
        {
            "version": REFACTOR_CHRONICLE_VERSION,
            "fields": _EVENT_FIELDS,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        }
    )


@dataclass(frozen=True)
class RefactorChronicleEvent:
    event_id: str
    sequence: int
    timestamp: float
    event_type: str
    correlation_id: str
    session_id: str = ""
    objective_hash: str = ""
    plan_phase_hash: str = ""
    task_id: str = ""
    gate: str = ""
    status: str = ""
    provider: str = ""
    model: str = ""
    input_tokens_estimated: int = 0
    output_tokens_estimated: int = 0
    input_tokens_reported: int | None = None
    output_tokens_reported: int | None = None
    cost_usd_reported: float | None = None
    prompt_digest: str = ""
    response_digest: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    redactions: tuple[str, ...] = ()
    measurement_classes: dict[str, str] = field(default_factory=dict)
    version: str = REFACTOR_CHRONICLE_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False
    production_mutation: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["redactions"] = list(self.redactions)
        return data


class RefactorChronicle:
    """Append-only refactor event stream with ArenaExperience projection."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        path: str | Path | None = None,
        experience_db_path: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.path = (
            Path(path).resolve()
            if path is not None
            else self.repo_root / "Aura_Memory" / "refactor_chronicle.jsonl"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.experience_db_path = Path(experience_db_path).resolve() if experience_db_path else None

    def record(
        self,
        event_type: str,
        *,
        correlation_id: str,
        session_id: str = "",
        objective: str = "",
        plan_phase_hash: str = "",
        task_id: str = "",
        gate: str = "",
        status: str = "",
        provider: str = "",
        model: str = "",
        input_tokens_estimated: int = 0,
        output_tokens_estimated: int = 0,
        input_tokens_reported: int | None = None,
        output_tokens_reported: int | None = None,
        cost_usd_reported: float | None = None,
        prompt: str = "",
        response: str = "",
        payload: dict[str, Any] | None = None,
        measurement_classes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        event_name = str(event_type or "").strip()
        correlation = str(correlation_id or "").strip()
        if not event_name:
            return self._deny("event_type_required")
        if not correlation:
            return self._deny("correlation_id_required")

        safe_payload, redactions = sanitize_experience_payload(dict(payload or {}))
        sequence = self._next_sequence(correlation)
        timestamp = time.time()
        identity = {
            "correlation_id": correlation,
            "sequence": sequence,
            "event_type": event_name,
            "timestamp_ns": time.time_ns(),
            "session_id": session_id,
            "task_id": task_id,
        }
        event = RefactorChronicleEvent(
            event_id=f"RFE-{_digest(identity, size=12)}",
            sequence=sequence,
            timestamp=timestamp,
            event_type=event_name,
            correlation_id=correlation,
            session_id=str(session_id or ""),
            objective_hash=_objective_hash(objective),
            plan_phase_hash=str(plan_phase_hash or ""),
            task_id=str(task_id or ""),
            gate=str(gate or ""),
            status=str(status or ""),
            provider=str(provider or "")[:120],
            model=str(model or "")[:160],
            input_tokens_estimated=max(0, _integer(input_tokens_estimated)),
            output_tokens_estimated=max(0, _integer(output_tokens_estimated)),
            input_tokens_reported=(
                max(0, _integer(input_tokens_reported))
                if input_tokens_reported is not None
                else None
            ),
            output_tokens_reported=(
                max(0, _integer(output_tokens_reported))
                if output_tokens_reported is not None
                else None
            ),
            cost_usd_reported=(
                max(0.0, _number(cost_usd_reported))
                if cost_usd_reported is not None
                else None
            ),
            prompt_digest=_digest(prompt, size=12) if prompt else "",
            response_digest=_digest(response, size=12) if response else "",
            payload=safe_payload,
            redactions=tuple(sorted(set(str(item) for item in redactions))),
            measurement_classes=dict(
                measurement_classes
                or {
                    "input_tokens_estimated": "ESTIMATED_CHAR4_PROXY",
                    "output_tokens_estimated": "ESTIMATED_CHAR4_PROXY",
                    "input_tokens_reported": "PROVIDER_REPORTED_OR_UNAVAILABLE",
                    "output_tokens_reported": "PROVIDER_REPORTED_OR_UNAVAILABLE",
                    "cost_usd_reported": "PROVIDER_REPORTED_OR_UNAVAILABLE",
                }
            ),
        )
        line = _canonical(event.to_dict()) + "\n"
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            return self._deny(f"chronicle_write_failed:{type(exc).__name__}")
        return {
            "ok": True,
            "event_id": event.event_id,
            "sequence": event.sequence,
            "chronicle_path": str(self.path),
            "event_digest": _digest(event.to_dict()),
            "redactions": list(event.redactions),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }

    def history(
        self,
        *,
        correlation_id: str = "",
        session_id: str = "",
        event_type: str = "",
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self.path.exists():
            return rows
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        row = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if correlation_id and row.get("correlation_id") != correlation_id:
                        continue
                    if session_id and row.get("session_id") != session_id:
                        continue
                    if event_type and row.get("event_type") != event_type:
                        continue
                    rows.append(row)
        except OSError:
            return []
        return rows[-max(1, min(int(limit), 10000)) :]

    def summary(self, *, correlation_id: str = "", session_id: str = "") -> dict[str, Any]:
        rows = self.history(correlation_id=correlation_id, session_id=session_id, limit=10000)
        totals = {
            "input_tokens_estimated": 0,
            "output_tokens_estimated": 0,
            "input_tokens_reported": 0,
            "output_tokens_reported": 0,
            "cost_usd_reported": 0.0,
        }
        reported_input_available = False
        reported_output_available = False
        reported_cost_available = False
        event_counts: dict[str, int] = {}
        repair_count = 0
        task_ids: list[str] = []
        for row in rows:
            event_name = str(row.get("event_type") or "")
            event_counts[event_name] = event_counts.get(event_name, 0) + 1
            if "repair" in event_name.lower() or str(row.get("gate") or "").upper() == "REPAIR":
                repair_count += 1
            task_id = str(row.get("task_id") or "")
            if task_id and task_id not in task_ids:
                task_ids.append(task_id)
            totals["input_tokens_estimated"] += _integer(row.get("input_tokens_estimated"))
            totals["output_tokens_estimated"] += _integer(row.get("output_tokens_estimated"))
            if row.get("input_tokens_reported") is not None:
                reported_input_available = True
                totals["input_tokens_reported"] += _integer(row.get("input_tokens_reported"))
            if row.get("output_tokens_reported") is not None:
                reported_output_available = True
                totals["output_tokens_reported"] += _integer(row.get("output_tokens_reported"))
            if row.get("cost_usd_reported") is not None:
                reported_cost_available = True
                totals["cost_usd_reported"] += _number(row.get("cost_usd_reported"))
        if not reported_input_available:
            totals["input_tokens_reported"] = None
        if not reported_output_available:
            totals["output_tokens_reported"] = None
        if not reported_cost_available:
            totals["cost_usd_reported"] = None
        elif totals["cost_usd_reported"] is not None:
            totals["cost_usd_reported"] = round(float(totals["cost_usd_reported"]), 8)
        return {
            "ok": True,
            "version": REFACTOR_CHRONICLE_VERSION,
            "correlation_id": correlation_id,
            "session_id": session_id,
            "event_count": len(rows),
            "event_counts": event_counts,
            "task_ids": task_ids,
            "task_count": len(task_ids),
            "repair_event_count": repair_count,
            "token_totals": totals,
            "first_timestamp": rows[0].get("timestamp") if rows else None,
            "last_timestamp": rows[-1].get("timestamp") if rows else None,
            "last_status": rows[-1].get("status") if rows else "",
            "chronicle_path": str(self.path),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }

    def finalize_experience(
        self,
        *,
        correlation_id: str,
        session_id: str,
        objective: str,
        plan_phase_hash: str,
        final_outcome: str,
        state_before: str,
        state_after: str,
        selected_transition: str,
        provider: str = "",
        model: str = "",
        raw_evidence_refs: Iterable[str] = (),
        learning_notes: Iterable[str] = (),
        working_tree_digest: str = "",
    ) -> dict[str, Any]:
        rows = self.history(correlation_id=correlation_id, session_id=session_id, limit=10000)
        summary = self.summary(correlation_id=correlation_id, session_id=session_id)
        timestamps = [float(row.get("timestamp") or 0.0) for row in rows if row.get("timestamp")]
        started_at = min(timestamps) if timestamps else time.time()
        completed_at = max(timestamps) if timestamps else started_at
        source_hashes = sorted(
            {
                str(value)
                for row in rows
                for value in (
                    row.get("prompt_digest"),
                    row.get("response_digest"),
                    row.get("payload", {}).get("stage_digest") if isinstance(row.get("payload"), dict) else "",
                    row.get("payload", {}).get("verification_digest") if isinstance(row.get("payload"), dict) else "",
                )
                if value
            }
        )
        task_ids = list(summary.get("task_ids") or [])
        payload = {
            "refactor_chronicle": {
                "version": REFACTOR_CHRONICLE_VERSION,
                "correlation_id": correlation_id,
                "session_id": session_id,
                "plan_phase_hash": plan_phase_hash,
                "event_count": len(rows),
                "event_digests": [_digest(row, size=12) for row in rows],
                "summary": summary,
                "learning_notes": [str(item) for item in learning_notes if str(item)],
            },
            "route": {
                "selected_transition": selected_transition,
                "alternatives": [],
                "predictions": [],
            },
            "verification": {
                "passed": str(final_outcome).upper() in {"READY_FOR_HUMAN_REVIEW", "VERIFIED", "COMPLETED"},
                "failure_count": sum(
                    1
                    for row in rows
                    if str(row.get("status") or "").upper().startswith("BLOCKED")
                    or str(row.get("event_type") or "").endswith("failed")
                ),
            },
            "safety": {
                "production_mutation": False,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": False,
            },
            "human_alignment": {
                "human_review_required": True,
                "terminal_state": state_after,
            },
            "budget_consumed": summary.get("token_totals", {}),
        }
        try:
            experience = build_arena_experience(
                arena_id=REFACTOR_EXPERIENCE_ARENA_ID,
                arena_version=REFACTOR_EXPERIENCE_ARENA_VERSION,
                grammar_version=REFACTOR_GRAMMAR_VERSION,
                grammar_manifest_digest=_grammar_manifest_digest(),
                runtime_version=REFACTOR_RUNTIME_VERSION,
                compiler_version=REFACTOR_COMPILER_VERSION,
                state_before=state_before,
                state_after=state_after,
                selected_transition=selected_transition,
                final_outcome=final_outcome,
                payload=payload,
                correlation_id=correlation_id,
                task_id=task_ids[-1] if task_ids else "",
                workflow_id=session_id,
                started_at=started_at,
                completed_at=completed_at,
                repository_commit_sha=_git_sha(self.repo_root),
                working_tree_digest=working_tree_digest,
                objective=objective,
                source_hashes=source_hashes,
                provider=provider,
                model=model,
                measurement_class="MIXED_MEASURED_ESTIMATED_PROVIDER_REPORTED",
                raw_evidence_refs=[str(item) for item in raw_evidence_refs if str(item)],
                actual_tool_calls=sorted(
                    {
                        str(row.get("event_type") or "")
                        for row in rows
                        if str(row.get("event_type") or "")
                    }
                ),
                actual_model=model,
                budget_requested={},
                budget_consumed=dict(summary.get("token_totals") or {}),
                route_capsule_digest=str(plan_phase_hash or ""),
                actual_context_digest=_digest(
                    [
                        {
                            "task_id": row.get("task_id"),
                            "prompt_digest": row.get("prompt_digest"),
                            "input_tokens_estimated": row.get("input_tokens_estimated"),
                        }
                        for row in rows
                    ]
                ),
            )
            with ArenaExperienceLedger(
                self.repo_root,
                db_path=self.experience_db_path,
            ) as ledger:
                result = ledger.record(experience)
        except Exception as exc:
            return self._deny(f"experience_projection_failed:{type(exc).__name__}")
        return {
            **result,
            "chronicle_summary": summary,
            "experience_projection": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }

    def _next_sequence(self, correlation_id: str) -> int:
        rows = self.history(correlation_id=correlation_id, limit=10000)
        return 1 + max((_integer(row.get("sequence")) for row in rows), default=0)

    @staticmethod
    def _deny(error: str, **extra: Any) -> dict[str, Any]:
        return {
            "ok": False,
            "error": error,
            **extra,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "production_mutation": False,
        }
