"""Content-addressed temporal persistence for Aura arenas.

This module persists compact, verifier-bound arena state. It does not resume
work automatically, grant patch authority, promote grammar, authorize physical
work, release funds, or certify evidence. Restore operations return reviewable
assessment packets only.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Iterator, Mapping

from aura_refactor_state_identity import digest, normalize
from aura_refactor_state_ledger_core import RefactorStateLedger, reconstruct_state_from_ledger

TEMPORAL_PERSISTENCE_VERSION = "AURA_TEMPORAL_PERSISTENCE_V1"
TEMPORAL_CHECKPOINT_VERSION = "AURA_TEMPORAL_CHECKPOINT_V1"
TEMPORAL_REGISTRY_VERSION = "AURA_TEMPORAL_REGISTRY_V1"
RESTORATION_ASSESSMENT_VERSION = "AURA_RESTORATION_ASSESSMENT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
HUMAN_REVIEW_REQUIRED = True

_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HEX_HEAD = re.compile(r"^[0-9a-f]{7,64}$")


def _component(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if not text and allow_empty:
        return ""
    if not _COMPONENT.fullmatch(text):
        raise ValueError(f"{name} must be a canonical identifier")
    return text


def _repo_head(value: Any) -> str:
    if type(value) is not str:
        raise ValueError("repo_head must be a string")
    text = value.strip()
    if not _HEX_HEAD.fullmatch(text):
        raise ValueError("repo_head must be 7-64 lowercase hexadecimal characters")
    return text


def _sequence(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("sequence_number must be a non-negative integer")
    return value


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    normalized = normalize(dict(value))
    if not isinstance(normalized, dict):
        raise ValueError(f"{name} did not normalize to an object")
    return normalized


def _invariant_digests(values: Mapping[str, Any] | None) -> dict[str, str]:
    raw = dict(values or {})
    result: dict[str, str] = {}
    for key in sorted(raw):
        name = _component(str(key), "invariant name")
        result[name] = digest(raw[key], size=16)
    return result


def _checkpoint_identity(
    *,
    arena_id: str,
    session_id: str,
    parent_checkpoint_id: str,
    branch_name: str,
    sequence_number: int,
    repo_head: str,
    payload_digest: str,
    invariant_digests: Mapping[str, str],
    source_kind: str,
) -> dict[str, Any]:
    return {
        "version": TEMPORAL_CHECKPOINT_VERSION,
        "arena_id": arena_id,
        "session_id": session_id,
        "parent_checkpoint_id": parent_checkpoint_id,
        "branch_name": branch_name,
        "sequence_number": sequence_number,
        "repo_head": repo_head,
        "payload_digest": payload_digest,
        "invariant_digests": dict(invariant_digests),
        "source_kind": source_kind,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "human_review_required": HUMAN_REVIEW_REQUIRED,
        "automatic_resume": False,
    }


@dataclass(frozen=True)
class TemporalCheckpoint:
    checkpoint_id: str
    arena_id: str
    session_id: str
    parent_checkpoint_id: str
    branch_name: str
    sequence_number: int
    repo_head: str
    payload: dict[str, Any]
    payload_digest: str
    invariant_digests: dict[str, str]
    source_kind: str
    created_at: float
    record_digest: str
    version: str = TEMPORAL_CHECKPOINT_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    human_review_required: bool = HUMAN_REVIEW_REQUIRED
    automatic_resume: bool = False

    def __post_init__(self) -> None:
        _component(self.arena_id, "arena_id")
        _component(self.session_id, "session_id")
        _component(self.parent_checkpoint_id, "parent_checkpoint_id", allow_empty=True)
        _component(self.branch_name, "branch_name", allow_empty=True)
        _sequence(self.sequence_number)
        _repo_head(self.repo_head)
        _component(self.source_kind, "source_kind")
        if (
            type(self.created_at) not in {int, float}
            or not math.isfinite(float(self.created_at))
            or float(self.created_at) < 0
        ):
            raise ValueError("created_at must be finite and non-negative")
        if self.version != TEMPORAL_CHECKPOINT_VERSION:
            raise ValueError("unsupported temporal checkpoint version")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("temporal checkpoint authority boundary changed")
        if self.human_review_required is not True or self.automatic_resume is not False:
            raise ValueError("temporal checkpoint crossed the review boundary")
        payload = _mapping(self.payload, "payload")
        if payload != self.payload:
            raise ValueError("payload must already be canonical normalized data")
        expected_payload = digest(payload, size=20)
        if self.payload_digest != expected_payload:
            raise ValueError("payload digest mismatch")
        expected_identity = _checkpoint_identity(
            arena_id=self.arena_id,
            session_id=self.session_id,
            parent_checkpoint_id=self.parent_checkpoint_id,
            branch_name=self.branch_name,
            sequence_number=self.sequence_number,
            repo_head=self.repo_head,
            payload_digest=self.payload_digest,
            invariant_digests=self.invariant_digests,
            source_kind=self.source_kind,
        )
        expected_id = f"CHK-{digest(expected_identity, size=20)}"
        if self.checkpoint_id != expected_id:
            raise ValueError("checkpoint identity mismatch")
        expected_record = digest(
            {
                "identity": expected_identity,
                "payload": payload,
                "created_at": float(self.created_at),
            },
            size=20,
        )
        if self.record_digest != expected_record:
            raise ValueError("checkpoint record digest mismatch")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TemporalCheckpoint":
        data = dict(value)
        allowed = {
            "checkpoint_id",
            "arena_id",
            "session_id",
            "parent_checkpoint_id",
            "branch_name",
            "sequence_number",
            "repo_head",
            "payload",
            "payload_digest",
            "invariant_digests",
            "source_kind",
            "created_at",
            "record_digest",
            "version",
            "patch_authority",
            "vsa_patch_authority",
       "human_review_required",
            "automatic_resume",
        }
        unknown = sorted(set(data).difference(allowed))
        if unknown:
            raise ValueError(f"unknown temporal checkpoint fields: {unknown}")
        return cls(
            checkpoint_id=data.get("checkpoint_id"),
            arena_id=data.get("arena_id"),
            session_id=data.get("session_id"),
            parent_checkpoint_id=data.get("parent_checkpoint_id", ""),
            branch_name=data.get("branch_name", ""),
            sequence_number=data.get("sequence_number"),
            repo_head=data.get("repo_head"),
            payload=_mapping(data.get("payload"), "payload"),
            payload_digest=data.get("payload_digest"),
            invariant_digests={
                str(key): str(item)
                for key, item in _mapping(data.get("invariant_digests", {}), "invariant_digests").items()
            },
            source_kind=data.get("source_kind"),
            created_at=data.get("created_at"),
            record_digest=data.get("record_digest"),
            version=data.get("version"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
            human_review_required=data.get("human_review_required"),
            automatic_resume=data.get("automatic_resume"),
        )


@dataclass(frozen=True)
class RestorationAssessment:
    checkpoint_id: str
    status: str
    can_direct_resume: bool
    mismatches: tuple[str, ...]
    repo_head_matches: bool
    invariant_matches: bool
    mitosis_required: bool
    remaining_context_tokens: int
    surgeon_context_limit: int
    next_gate: str
    human_review_required: bool = True
    automatic_resume: bool = False
    version: str = RESTORATION_ASSESSMENT_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["mismatches"] = list(self.mismatches)
        return value


class TemporalCheckpointRegistry:
    """Append-only checkpoint registry with content-addressed checkpoint files."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        memory_root: str | Path = "Aura_Memory/checkpoints",
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        raw_root = Path(memory_root)
        if raw_root.is_absolute():
            raise ValueError("memory_root must be repository-relative")
        self.root = (self.repo_root / raw_root).resolve()
        try:
            self.root.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("memory_root escaped repo_root") from exc
        self.registry_path = self.root / "registry.jsonl"
        self.lock_path = self.root / ".registry.lock"

    @contextmanager
    def _lock(self, *, create: bool = True) -> Iterator[None]:
        if not self.root.exists() and not create:
            yield
            return
        self.root.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        backend = ""
        lock_module: Any = None
        try:
            try:
                import fcntl  # type: ignore
            except ImportError:
                fcntl = None  # type: ignore[assignment]
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                backend = "fcntl"
                lock_module = fcntl
            else:
                try:
                    import msvcrt  # type: ignore
                except ImportError as exc:
                    raise RuntimeError("platform does not provide a supported file lock") from exc
                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                    os.fsync(handle.fileno())
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                backend = "msvcrt"
                lock_module = msvcrt
        except OSError as exc:
            handle.close()
            raise RuntimeError("failed to acquire temporal registry lock") from exc
        try:
            yield
        finally:
            try:
                if backend == "fcntl":
                    lock_module.flock(handle.fileno(), lock_module.LOCK_UN)
                elif backend == "msvcrt":
                    handle.seek(0)
                    lock_module.locking(handle.fileno(), lock_module.LK_UNLCK, 1)
            finally:
                handle.close()

    def _checkpoint_path(self, checkpoint: TemporalCheckpoint) -> Path:
        path = (
            self.root
            / checkpoint.arena_id
            / checkpoint.session_id
            / f"{checkpoint.checkpoint_id}.json"
        ).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("checkpoint path escaped persistence root") from exc
        return path

    def _atomic_json(self, path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _registry_entries_unlocked(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        previous = ""
        with self.registry_path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if not raw.strip():
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"registry line {line_number} is not valid JSON") from exc
                if not isinstance(entry, dict):
                    raise ValueError(f"registry line {line_number} is not an object")
                body = {key: item for key, item in entry.items() if key != "entry_digest"}
                if body.get("registry_version") != TEMPORAL_REGISTRY_VERSION:
                    raise ValueError(f"registry line {line_number} has unsupported version")
                if body.get("previous_entry_digest", "") != previous:
                    raise ValueError(f"registry chain mismatch at line {line_number}")
                expected = digest(body, size=20)
                if entry.get("entry_digest") != expected:
                    raise ValueError(f"registry digest mismatch at line {line_number}")
                previous = expected
                entries.append(entry)
        return entries

    def verify_registry(self) -> dict[str, Any]:
        with self._lock(create=False):
            entries = self._registry_entries_unlocked()
            for entry in entries:
                self._load_from_entry_unlocked(entry)
        return {
            "ok": True,
            "version": TEMPORAL_REGISTRY_VERSION,
            "entry_count": len(entries),
            "verified_checkpoint_count": len(entries),
            "last_entry_digest": entries[-1]["entry_digest"] if entries else "",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def _entry_index_unlocked(self) -> dict[str, dict[str, Any]]:
        return {
            str(entry["checkpoint_id"]): entry
            for entry in self._registry_entries_unlocked()
        }

    def write_checkpoint(
        self,
        *,
        arena_id: str,
        session_id: str,
        repo_head: str,
        payload: Mapping[str, Any],
        invariant_values: Mapping[str, Any] | None = None,
        prehashed_invariant_digests: Mapping[str, str] | None = None,
        parent_checkpoint_id: str = "",
        branch_name: str = "",
        sequence_number: int | None = None,
        source_kind: str = "ARENA_STATE",
        created_at: float | None = None,
    ) -> dict[str, Any]:
        arena = _component(arena_id, "arena_id")
        session = _component(session_id, "session_id")
        parent = _component(parent_checkpoint_id, "parent_checkpoint_id", allow_empty=True)
        branch = _component(branch_name, "branch_name", allow_empty=True)
        source = _component(source_kind, "source_kind")
        head = _repo_head(repo_head)
        normalized_payload = _mapping(payload, "payload")
        payload_digest = digest(normalized_payload, size=20)
        if invariant_values is not None and prehashed_invariant_digests is not None:
            raise ValueError("provide invariant values or prehashed digests, not both")
        if prehashed_invariant_digests is None:
            invariants = _invariant_digests(invariant_values)
        else:
            invariants = {}
            for key, item in sorted(dict(prehashed_invariant_digests).items()):
                name = _component(str(key), "invariant name")
                if type(item) is not str or len(item) != 32 or any(
                    ch not in "0123456789abcdef" for ch in item
                ):
                    raise ValueError("prehashed invariant digests must be 32 lowercase hex characters")
                invariants[name] = item
        generated_at = float(time.time() if created_at is None else created_at)
        if not math.isfinite(generated_at) or generated_at < 0:
            raise ValueError("created_at must be finite and non-negative")

        with self._lock():
            index = self._entry_index_unlocked()
            parent_record: TemporalCheckpoint | None = None
            if parent:
                parent_entry = index.get(parent)
                if parent_entry is None:
                    raise ValueError("parent checkpoint does not exist")
                parent_record = self._load_from_entry_unlocked(parent_entry)
                if parent_record.arena_id != arena or parent_record.session_id != session:
                    raise ValueError("parent checkpoint belongs to another arena session")
            expected_sequence = parent_record.sequence_number + 1 if parent_record else 0
            seq = expected_sequence if sequence_number is None else _sequence(sequence_number)
            if seq != expected_sequence:
                raise ValueError("sequence_number must continue the parent chain")

            identity = _checkpoint_identity(
                arena_id=arena,
                session_id=session,
                parent_checkpoint_id=parent,
                branch_name=branch,
                sequence_number=seq,
                repo_head=head,
                payload_digest=payload_digest,
                invariant_digests=invariants,
                source_kind=source,
            )
            checkpoint_id = f"CHK-{digest(identity, size=20)}"
            record_digest = digest(
                {
                    "identity": identity,
                    "payload": normalized_payload,
                    "created_at": generated_at,
                },
                size=20,
            )
            checkpoint = TemporalCheckpoint(
                checkpoint_id=checkpoint_id,
                arena_id=arena,
                session_id=session,
                parent_checkpoint_id=parent,
                branch_name=branch,
                sequence_number=seq,
                repo_head=head,
                payload=normalized_payload,
                payload_digest=payload_digest,
                invariant_digests=invariants,
                source_kind=source,
                created_at=generated_at,
                record_digest=record_digest,
            )
            existing = index.get(checkpoint_id)
            if existing is not None:
                loaded = self._load_from_entry_unlocked(existing)
                return {
                    "ok": True,
                    "created": False,
                    "checkpoint": loaded.to_dict(),
                    "registry_entry": existing,
                }

            path = self._checkpoint_path(checkpoint)
            self._atomic_json(path, checkpoint.to_dict())
            entries = self._registry_entries_unlocked()
            previous = entries[-1]["entry_digest"] if entries else ""
            relative_path = path.relative_to(self.repo_root).as_posix()
            body = {
                "registry_version": TEMPORAL_REGISTRY_VERSION,
                "checkpoint_id": checkpoint_id,
                "arena_id": arena,
                "session_id": session,
                "parent_checkpoint_id": parent,
                "branch_name": branch,
                "sequence_number": seq,
                "repo_head": head,
                "created_at": generated_at,
                "checkpoint_path": relative_path,
                "record_digest": record_digest,
                "previous_entry_digest": previous,
            }
            entry = {**body, "entry_digest": digest(body, size=20)}
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            encoded = json.dumps(
                entry,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ) + "\n"
            with self.registry_path.open("a", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            return {
                "ok": True,
                "created": True,
                "checkpoint": checkpoint.to_dict(),
                "registry_entry": entry,
            }

    def _load_from_entry_unlocked(self, entry: Mapping[str, Any]) -> TemporalCheckpoint:
        raw_path = str(entry.get("checkpoint_path") or "")
        path = (self.repo_root / raw_path).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("registry checkpoint path escaped persistence root") from exc
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"checkpoint file is missing or invalid: {raw_path}") from exc
        checkpoint = TemporalCheckpoint.from_dict(value)
        expected_path = self._checkpoint_path(checkpoint).relative_to(self.repo_root).as_posix()
        expected_entry = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "arena_id": checkpoint.arena_id,
            "session_id": checkpoint.session_id,
            "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
            "branch_name": checkpoint.branch_name,
            "sequence_number": checkpoint.sequence_number,
            "repo_head": checkpoint.repo_head,
            "created_at": checkpoint.created_at,
            "checkpoint_path": expected_path,
            "record_digest": checkpoint.record_digest,
        }
        for key, expected in expected_entry.items():
            if entry.get(key) != expected:
                raise ValueError(f"registry {key} does not match checkpoint file")
        return checkpoint

    def load_checkpoint(self, checkpoint_id: str) -> TemporalCheckpoint:
        identifier = _component(checkpoint_id, "checkpoint_id")
        with self._lock(create=False):
            entry = self._entry_index_unlocked().get(identifier)
            if entry is None:
                raise KeyError(f"checkpoint not found: {identifier}")
            return self._load_from_entry_unlocked(entry)

    def list_checkpoints(
        self,
        *,
        arena_id: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        if type(limit) is not int or limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        arena = _component(arena_id, "arena_id") if arena_id is not None else ""
        session = _component(session_id, "session_id") if session_id is not None else ""
        with self._lock(create=False):
            entries = self._registry_entries_unlocked()
        filtered = [
            entry
            for entry in entries
            if (not arena or entry.get("arena_id") == arena)
            and (not session or entry.get("session_id") == session)
        ]
        return {
            "ok": True,
            "count": len(filtered[-limit:]),
            "checkpoints": filtered[-limit:],
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def fork_checkpoint(
        self,
        checkpoint_id: str,
        *,
        branch_name: str,
        repo_head: str | None = None,
        payload: Mapping[str, Any] | None = None,
        invariant_values: Mapping[str, Any] | None = None,
        created_at: float | None = None,
    ) -> dict[str, Any]:
        parent = self.load_checkpoint(checkpoint_id)
        return self.write_checkpoint(
            arena_id=parent.arena_id,
            session_id=parent.session_id,
            repo_head=repo_head or parent.repo_head,
            payload=parent.payload if payload is None else payload,
            invariant_values=invariant_values,
            prehashed_invariant_digests=(
                None if invariant_values is not None else parent.invariant_digests
            ),
            parent_checkpoint_id=parent.checkpoint_id,
            branch_name=branch_name,
            source_kind="FORK",
            created_at=created_at,
        )

    def assess_restore(
        self,
        checkpoint_id: str,
        *,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> RestorationAssessment:
        checkpoint = self.load_checkpoint(checkpoint_id)
        head = _repo_head(current_repo_head)
        current = _invariant_digests(current_invariant_values)
        mismatches: list[str] = []
        repo_match = head == checkpoint.repo_head
        if not repo_match:
            mismatches.append("repo_head_changed")
        for key, expected in checkpoint.invariant_digests.items():
            actual = current.get(key)
            if actual is None:
                mismatches.append(f"invariant_missing:{key}")
            elif actual != expected:
                mismatches.append(f"invariant_changed:{key}")
        invariant_match = not any(item.startswith("invariant_") for item in mismatches)

        if type(remaining_context_tokens) is not int or remaining_context_tokens < 0:
            raise ValueError("remaining_context_tokens must be a non-negative integer")
        if type(surgeon_context_limit) is not int or surgeon_context_limit < 0:
            raise ValueError("surgeon_context_limit must be a non-negative integer")
        mitosis = bool(
            surgeon_context_limit
            and remaining_context_tokens > int(surgeon_context_limit * 0.75)
        )
        if mismatches:
            status = "RESTORATION_COUNCIL_REQUIRED"
            next_gate = "VERIFY_AND_REBASE"
            direct = False
        elif mitosis:
            status = "MITOSIS_REQUIRED"
            next_gate = "SLICE_REMAINING_WORK"
            direct = False
        else:
            status = "DIRECT_RESUME_REVIEW_REQUIRED"
            next_gate = "HUMAN_REVIEW_THEN_SURGEON"
            direct = True
        return RestorationAssessment(
            checkpoint_id=checkpoint.checkpoint_id,
            status=status,
            can_direct_resume=direct,
            mismatches=tuple(mismatches),
            repo_head_matches=repo_match,
            invariant_matches=invariant_match,
            mitosis_required=mitosis,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
            next_gate=next_gate,
        )

    def restoration_packet(
        self,
        checkpoint_id: str,
        *,
        current_repo_head: str,
        current_invariant_values: Mapping[str, Any] | None = None,
        remaining_context_tokens: int = 0,
        surgeon_context_limit: int = 0,
    ) -> dict[str, Any]:
        checkpoint = self.load_checkpoint(checkpoint_id)
        assessment = self.assess_restore(
            checkpoint_id,
            current_repo_head=current_repo_head,
            current_invariant_values=current_invariant_values,
            remaining_context_tokens=remaining_context_tokens,
            surgeon_context_limit=surgeon_context_limit,
        )
        return {
            "ok": True,
            "checkpoint": checkpoint.to_dict(),
            "assessment": assessment.to_dict(),
            "resume_applied": False,
            "human_review_required": True,
            "automatic_resume": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def observatory_projection(self, checkpoint_id: str) -> dict[str, Any]:
        checkpoint = self.load_checkpoint(checkpoint_id)
        return {
            "ok": True,
            "checkpoint_id": checkpoint.checkpoint_id,
            "arena_id": checkpoint.arena_id,
            "session_id": checkpoint.session_id,
            "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
            "branch_name": checkpoint.branch_name,
            "sequence_number": checkpoint.sequence_number,
            "repo_head": checkpoint.repo_head,
            "payload_digest": checkpoint.payload_digest,
            "invariant_names": sorted(checkpoint.invariant_digests),
            "source_kind": checkpoint.source_kind,
            "created_at": checkpoint.created_at,
            "read_only": True,
            "payload_included": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def _ledger_from_dict(value: Mapping[str, Any]) -> RefactorStateLedger:
    data = dict(value)
    data["completed_task_ids"] = tuple(data.get("completed_task_ids", ()))
    data["invariants"] = tuple(data.get("invariants", ()))
    return RefactorStateLedger(**data)


def checkpoint_refactor_state(
    registry: TemporalCheckpointRegistry,
    *,
    ledger: RefactorStateLedger,
    sidecar: Mapping[str, Any],
    repo_head: str,
    arena_id: str = "coding_arena",
    parent_checkpoint_id: str = "",
    branch_name: str = "",
    created_at: float | None = None,
) -> dict[str, Any]:
    if type(ledger) is not RefactorStateLedger:
        raise ValueError("ledger must be an exact RefactorStateLedger")
    projection = reconstruct_state_from_ledger(ledger, sidecar)
    payload = {
        "ledger": ledger.to_dict(),
        "sidecar": _mapping(sidecar, "sidecar"),
        "projection": _mapping(projection, "projection"),
    }
    invariants = {
        "history_root_digest": ledger.history_root_digest,
        "execution_state_digest": ledger.execution_state_digest,
        "reconstruction_sidecar_digest": ledger.reconstruction_sidecar_digest,
        "patch_authority": ledger.patch_authority,
        "vsa_patch_authority": ledger.vsa_patch_authority,
    }
    return registry.write_checkpoint(
        arena_id=arena_id,
        session_id=ledger.session_id,
        repo_head=repo_head,
        payload=payload,
        invariant_values=invariants,
        parent_checkpoint_id=parent_checkpoint_id,
        branch_name=branch_name,
        source_kind="REFACTOR_STATE_LEDGER_V3",
        created_at=created_at,
    )


def verify_refactor_checkpoint(checkpoint: TemporalCheckpoint) -> dict[str, Any]:
    payload = checkpoint.payload
    ledger_raw = payload.get("ledger")
    sidecar = payload.get("sidecar")
    if not isinstance(ledger_raw, Mapping) or not isinstance(sidecar, Mapping):
        raise ValueError("checkpoint is not a refactor-state checkpoint")
    ledger = _ledger_from_dict(ledger_raw)
    projection = reconstruct_state_from_ledger(ledger, sidecar)
    if normalize(projection) != payload.get("projection"):
        raise ValueError("checkpoint projection does not match ledger reconstruction")
    return {
        "ok": True,
        "checkpoint_id": checkpoint.checkpoint_id,
        "session_id": ledger.session_id,
        "projection": projection,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = [
    "HUMAN_REVIEW_REQUIRED",
    "PATCH_AUTHORITY",
    "RESTORATION_ASSESSMENT_VERSION",
    "TEMPORAL_CHECKPOINT_VERSION",
    "TEMPORAL_PERSISTENCE_VERSION",
    "TEMPORAL_REGISTRY_VERSION",
    "TemporalCheckpoint",
    "TemporalCheckpointRegistry",
    "RestorationAssessment",
    "checkpoint_refactor_state",
    "verify_refactor_checkpoint",
]
