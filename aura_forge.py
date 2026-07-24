"""Aura Forge — verified engineering product facade over Aura's Coding Arena.

Aura Forge does not introduce a second planner, staging store, verifier, or
learning path. It freezes the existing Architect/Coding Arena preparation,
compiles an evidence contract from exact Arena outputs, and opens the existing
controlled slice-leased Surgeon session. External models remain replaceable
workers and every completed run stops at human review.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import ast
import copy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import threading
from typing import Any
import uuid

FORGE_VERSION = "AURA_FORGE_V1"
FORGE_CONTRACT_VERSION = "AURA_FORGE_ARENA_EVIDENCE_CONTRACT_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
REVIEW_READY_STATUS = "READY_FOR_HUMAN_REVIEW"
CODEMAP_PATH = ".aura/CODEMAP.json"
_FULL_DIGEST_PREFIX = "blake2b-256:"
_GIT_OID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_GIT_REF_RE = re.compile(r"^refs/[A-Za-z0-9._/-]{1,512}$")

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

_SECRET_KEYS = frozenset(
    {
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
    }
)
_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
_TOKEN_USAGE_KEYS = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "cached_tokens",
        "reasoning_tokens",
    }
)


def _digest(value: Any, *, size: int = 16) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _full_digest(value: Any) -> str:
    """Return an algorithm-labelled digest of the complete canonical value."""
    return f"{_FULL_DIGEST_PREFIX}{_digest(value, size=32)}"


def _repo_file_digest(repo_root: Path, relative_path: str) -> str:
    """Hash one repository-relative file without following it outside the repository."""
    root = repo_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return "OUTSIDE_REPOSITORY"
    if not candidate.exists():
        return "MISSING"
    if not candidate.is_file():
        return "NOT_A_REGULAR_FILE"
    hasher = hashlib.blake2b(digest_size=32)
    try:
        with candidate.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError:
        return "UNAVAILABLE"
    return f"{_FULL_DIGEST_PREFIX}{hasher.hexdigest()}"


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
            is_secret_token = (lowered == "token" or lowered.endswith("_token")) and lowered not in _TOKEN_USAGE_KEYS
            if lowered in _SECRET_KEYS or lowered.endswith(_SECRET_SUFFIXES) or is_secret_token:
                continue
            result[key_text] = _sanitize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return value


def _git_head(repo_root: Path) -> str:
    """Resolve a Git HEAD without depending on a mutable external executable."""

    try:
        marker = repo_root / ".git"
        if marker.is_dir():
            git_dir = marker.resolve()
        elif marker.is_file():
            pointer = marker.read_text(encoding="utf-8")[:4096].strip()
            if not pointer.startswith("gitdir: "):
                return "UNAVAILABLE"
            raw_git_dir = Path(pointer[8:].strip())
            git_dir = (raw_git_dir if raw_git_dir.is_absolute() else repo_root / raw_git_dir).resolve()
        else:
            return "UNAVAILABLE"

        common_dir = git_dir
        common_marker = git_dir / "commondir"
        if common_marker.is_file():
            raw_common = Path(common_marker.read_text(encoding="utf-8")[:4096].strip())
            common_dir = (raw_common if raw_common.is_absolute() else git_dir / raw_common).resolve()

        head = (git_dir / "HEAD").read_text(encoding="ascii")[:1024].strip()
        direct = head.lower()
        if _GIT_OID_RE.fullmatch(direct) is not None:
            return direct
        if not head.startswith("ref: "):
            return "UNAVAILABLE"
        ref = head[5:].strip().replace("\\", "/")
        ref_path = PurePosixPath(ref)
        if _GIT_REF_RE.fullmatch(ref) is None or ref_path.is_absolute() or ".." in ref_path.parts or "//" in ref:
            return "UNAVAILABLE"
        for base in (git_dir, common_dir):
            candidate = base.joinpath(*ref_path.parts)
            if candidate.is_file():
                value = candidate.read_text(encoding="ascii")[:1024].strip().lower()
                return value if _GIT_OID_RE.fullmatch(value) is not None else "UNAVAILABLE"
        packed = common_dir / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="ascii")[:8_000_000].splitlines():
                if not line or line.startswith(("#", "^")):
                    continue
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[1] == ref:
                    value = parts[0].lower()
                    return value if _GIT_OID_RE.fullmatch(value) is not None else "UNAVAILABLE"
    except (OSError, UnicodeError, ValueError):
        return "UNAVAILABLE"
    return "UNAVAILABLE"


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
    def from_value(cls, value: ForgeRunRequest | Mapping[str, Any]) -> ForgeRunRequest:
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


def forge_contract_digest(value: ForgeEvidenceContract | Mapping[str, Any]) -> str:
    """Digest every canonical contract field for an external authority binding."""
    if isinstance(value, ForgeEvidenceContract):
        payload = value.to_dict()
    elif isinstance(value, Mapping):
        payload = dict(value)
    else:
        raise ValueError("forge contract must be an object")
    return _full_digest(payload)


SessionManagerFactory = Callable[[ForgeRunRequest, Any, Path], Any]


class _FrozenEvidenceBridge:
    """Expose only retained Arena evidence to the execution session."""

    def __init__(
        self,
        bridge: Any,
        prepared: Mapping[str, Any],
        micro_contexts: Mapping[str, Mapping[str, Any]],
        *,
        repo_root: Path,
        expected_source_hashes: Mapping[str, Any],
    ) -> None:
        self._bridge = bridge
        self._prepared = copy.deepcopy(dict(prepared))
        self._micro_contexts = {str(task_id): copy.deepcopy(dict(packet)) for task_id, packet in micro_contexts.items()}
        self._slice_grants = self._compile_slice_grants(self._micro_contexts)
        self._source_snapshots = self._freeze_sources(repo_root, expected_source_hashes)

    @staticmethod
    def _compile_slice_grants(
        micro_contexts: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        grants: dict[str, list[dict[str, Any]]] = {}

        def grant(file: Any, *, symbol: Any = None, line_range: Any = None) -> None:
            path = _safe_repo_path(file, field_name="source_slice")
            if not path:
                return
            bounds = list(line_range or [])
            descriptor = {
                "symbol": str(symbol) if symbol else "",
                "line_start": int(bounds[0]) if len(bounds) > 0 else None,
                "line_end": int(bounds[1]) if len(bounds) > 1 else None,
            }
            if descriptor not in grants.setdefault(path, []):
                grants[path].append(descriptor)

        for micro in micro_contexts.values():
            ranges = [item for item in list(micro.get("line_ranges") or []) if isinstance(item, Mapping)]
            if ranges:
                for item in ranges[:3]:
                    grant(item.get("file"), symbol=item.get("symbol"), line_range=item.get("line_range"))
            else:
                grant(micro.get("target_file"), symbol=micro.get("target_symbol"))
            for test_file in list(micro.get("tests") or [])[:2]:
                grant(test_file)
        return grants

    @staticmethod
    def _freeze_sources(
        repo_root: Path,
        expected_source_hashes: Mapping[str, Any],
    ) -> dict[str, tuple[str, ...]]:
        snapshots: dict[str, tuple[str, ...]] = {}
        root = repo_root.resolve()
        for raw_path, raw_digest in expected_source_hashes.items():
            path = _safe_repo_path(raw_path, field_name="source_snapshot")
            if not path:
                continue
            expected_digest = str(raw_digest or "")
            candidate = (root / path).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError("source_snapshot_outside_repository") from exc
            if expected_digest == "MISSING":
                if candidate.exists():
                    raise ValueError("source_snapshot_digest_mismatch")
                continue
            try:
                payload = candidate.read_bytes()
            except OSError as exc:
                raise ValueError("source_snapshot_unavailable") from exc
            actual_digest = f"{_FULL_DIGEST_PREFIX}{hashlib.blake2b(payload, digest_size=32).hexdigest()}"
            if actual_digest != expected_digest:
                raise ValueError("source_snapshot_digest_mismatch")
            snapshots[path] = tuple(payload.decode("utf-8", errors="replace").splitlines())
        return snapshots

    def aura_prepare_arena(self, **_kwargs: Any) -> dict[str, Any]:
        return copy.deepcopy(self._prepared)

    def aura_get_micro_context(self, **kwargs: Any) -> dict[str, Any]:
        task_id = str(kwargs.get("task_id") or "")
        if task_id not in self._micro_contexts:
            raise ValueError("unretained_forge_task_evidence")
        return copy.deepcopy(self._micro_contexts[task_id])

    def aura_read_slice(self, **kwargs: Any) -> dict[str, Any]:
        """Serve only retained slice grants from immutable, contract-hashed bytes."""
        try:
            path = _safe_repo_path(kwargs.get("file"), field_name="source_slice")
        except ValueError:
            path = None
        if not path or path not in self._slice_grants:
            return {"ok": False, "error": "unretained_forge_source_slice"}
        lines = self._source_snapshots.get(path)
        if lines is None:
            return {"ok": False, "error": "missing_grounding"}

        symbol = str(kwargs.get("symbol") or "")
        requested_start = kwargs.get("line_start")
        requested_end = kwargs.get("line_end")
        matching_grant = next(
            (
                grant
                for grant in self._slice_grants[path]
                if (symbol and grant["symbol"] == symbol)
                or (
                    not symbol
                    and not grant["symbol"]
                    and (
                        grant["line_start"] is None
                        or (
                            requested_start == grant["line_start"]
                            and requested_end == grant["line_end"]
                        )
                    )
                )
            ),
            None,
        )
        if matching_grant is None:
            return {"ok": False, "error": "unretained_forge_source_slice"}

        max_lines = max(1, min(120, int(kwargs.get("max_lines") or 1)))
        line_start = matching_grant["line_start"]
        line_end = matching_grant["line_end"]
        if symbol:
            try:
                tree = ast.parse("\n".join(lines))
            except SyntaxError:
                return {"ok": False, "error": "target_symbol_unresolved"}
            node = next(
                (
                    item
                    for item in ast.walk(tree)
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    and item.name == symbol
                ),
                None,
            )
            if node is None:
                return {"ok": False, "error": "target_symbol_unresolved"}
            line_start = node.lineno
            line_end = getattr(node, "end_lineno", node.lineno) or node.lineno
        if line_start is None:
            line_start = 1
        if line_end is None or line_end - line_start + 1 > max_lines:
            line_end = line_start + max_lines - 1
        end_index = min(len(lines), line_end)
        raw_content = "\n".join(lines[max(0, line_start - 1) : end_index])
        try:
            from aura_tokenizer_guard import sanitize_tokenizer_channels

            guard = sanitize_tokenizer_channels(raw_content)
            safe_content = guard.sanitized_text
            warnings = guard.warnings()
        except Exception:  # noqa: BLE001
            safe_content = raw_content
            warnings = []
        try:
            from aura_agent_arena_bridge import _compress_text

            safe_content = _compress_text(safe_content, max_tokens=max_lines * 4)
        except Exception:  # noqa: BLE001
            safe_content = safe_content[: max_lines * 16]
        return {
            "ok": True,
            "file": path,
            "symbol": symbol,
            "line_start": line_start,
            "line_end": end_index,
            "total_lines": len(lines),
            "content": safe_content,
            "warnings": list(warnings or []),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def aura_stage_patch(self, **kwargs: Any) -> dict[str, Any]:
        return self._bridge.aura_stage_patch(**kwargs)

    def aura_verify_arena(self, **kwargs: Any) -> dict[str, Any]:
        return self._bridge.aura_verify_arena(**kwargs)

    def aura_hotswap_status(self, **kwargs: Any) -> dict[str, Any]:
        return self._bridge.aura_hotswap_status(**kwargs)

    def aura_repair_packet(self, **kwargs: Any) -> dict[str, Any]:
        return self._bridge.aura_repair_packet(**kwargs)


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
        self._run_lock = threading.RLock()

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
        except Exception as exc:
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
        except Exception as exc:
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
        frozen_micro_contexts: dict[str, dict[str, Any]] = {}
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
            except Exception as exc:
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
            frozen_micro = _sanitize(dict(micro))
            frozen_micro_contexts[task_id] = copy.deepcopy(frozen_micro)
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
                        "micro_context_digest": _full_digest(frozen_micro),
                        "jspace_present": bool(micro.get("jspace_packet")),
                        "st3gg_present": bool(micro.get("st3gg_egress")),
                    }
                )
            )

        unified_config = request.metadata.get("unified_memory_continuity")
        if unified_config is not None:
            if not isinstance(unified_config, Mapping):
                return self._error("unified_memory_continuity_metadata_invalid", stage="GROUND")
            compile_binding = getattr(self.bridge, "aura_compile_unified_execution", None)
            if not callable(compile_binding):
                return self._error("unified_memory_continuity_bridge_unavailable", stage="GROUND")
            for capsule in act_capsules:
                task_id = str(capsule.get("task_id") or "")
                result = compile_binding(
                    plan_phase_hash=str(prepared.get("plan_phase_hash") or ""),
                    task_id=task_id,
                    contract=dict(unified_config),
                )
                if not isinstance(result, Mapping) or result.get("ok") is not True:
                    return self._error(
                        "unified_memory_continuity_compile_failed",
                        stage="GROUND",
                        details={"task_id": task_id, "result": result},
                    )
                records = dict(result.get("records") or {})
                summary = {
                    "binding_id": result.get("binding_id"),
                    "binding_digest": result.get("binding_digest"),
                    "intent_digest": dict(records.get("intent_packet") or {}).get("intent_digest"),
                    "model_execution_packet_digest": dict(
                        records.get("model_execution_packet") or {}
                    ).get("packet_digest"),
                    "required_verification_depth": dict(records.get("council") or {}).get(
                        "required_verification_depth"
                    ),
                    "p0_required": True,
                    "human_review_required": True,
                }
                matching = next(
                    (item for item in task_evidence if str(item.get("task_id") or "") == task_id),
                    None,
                )
                if matching is not None:
                    matching["unified_memory_continuity"] = _sanitize(summary)

        contract = self._compile_contract(request, repo_digest, prepared, act_capsules, task_evidence)
        contract_errors = validate_forge_contract(contract.to_dict())
        if contract_errors:
            return self._error(
                "compiled_forge_contract_invalid",
                stage="GROUND",
                details={"errors": contract_errors},
            )
        contract_digest = forge_contract_digest(contract)
        run_id = f"FORGE-{contract.contract_id[:16]}-{uuid.uuid4().hex[:12]}"
        try:
            execution_bridge = _FrozenEvidenceBridge(
                self.bridge,
                prepared,
                frozen_micro_contexts,
                repo_root=self.repo_root,
                expected_source_hashes=contract.repository["allowed_file_source_hashes"],
            )
        except (OSError, ValueError) as exc:
            return self._error(
                "source_evidence_freeze_error",
                stage="GROUND",
                details={"reason": str(exc)},
            )
        with self._run_lock:
            self._runs[run_id] = {
                "request": request,
                "contract": contract,
                "contract_digest": contract_digest,
                "prepared": dict(prepared),
                "execution_bridge": execution_bridge,
                "manager": None,
                "session_id": "",
                "last_result": {},
                "status": "PREPARED",
                "lock": threading.RLock(),
            }
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": "PREPARED",
            "contract": contract.to_dict(),
            "contract_digest": contract_digest,
            "prepared": _sanitize(prepared),
            "production_mutation": False,
            "human_review_required": True,
        }

    def start(self, value: ForgeRunRequest | Mapping[str, Any]) -> dict[str, Any]:
        """Prepare exactly once, then start that retained frozen-plan session."""
        prepared_result = self.prepare(value)
        if not prepared_result.get("ok"):
            return prepared_result
        return self.start_prepared(
            str(prepared_result["run_id"]),
            expected_contract_id=str(prepared_result["contract"]["contract_id"]),
            expected_contract_digest=str(prepared_result["contract_digest"]),
        )

    def start_prepared(
        self,
        run_id: str,
        *,
        expected_contract_id: str | None = None,
        expected_contract_digest: str | None = None,
    ) -> dict[str, Any]:
        """Start one exact retained PREPARED run, once, after revalidating its evidence."""
        run_key = str(run_id or "")
        with self._run_lock:
            state = self._runs.get(run_key)
            if state is None:
                return self._error("forge_run_not_found", stage="ACT")
            if state.get("status") != "PREPARED":
                return self._error(
                    "forge_run_not_prepared",
                    stage="ACT",
                    details={"run_id": run_key, "status": state.get("status")},
                )

            contract = state.get("contract")
            if not isinstance(contract, ForgeEvidenceContract):
                state["status"] = "BLOCKED_CONTRACT_INVALID"
                return self._error("retained_forge_contract_invalid", stage="GROUND")
            contract_payload = contract.to_dict()
            actual_contract_digest = forge_contract_digest(contract_payload)
            if actual_contract_digest != state.get("contract_digest"):
                state["status"] = "BLOCKED_CONTRACT_DIGEST"
                return self._error("retained_forge_contract_digest_mismatch", stage="GROUND")
            if expected_contract_id is not None and str(expected_contract_id) != contract.contract_id:
                state["status"] = "BLOCKED_EXPECTED_CONTRACT_ID"
                return self._error("expected_forge_contract_id_mismatch", stage="GROUND")
            if expected_contract_digest is not None and str(expected_contract_digest) != actual_contract_digest:
                state["status"] = "BLOCKED_EXPECTED_CONTRACT_DIGEST"
                return self._error("expected_forge_contract_digest_mismatch", stage="GROUND")

            contract_errors = validate_forge_contract(contract_payload)
            if contract_errors:
                state["status"] = "BLOCKED_CONTRACT_INVALID"
                return self._error(
                    "retained_forge_contract_invalid",
                    stage="GROUND",
                    details={"errors": contract_errors},
                )
            repository_drift = self._repository_drift(contract)
            if repository_drift:
                state["status"] = "BLOCKED_REPOSITORY_DRIFT"
                return self._error(
                    "forge_repository_evidence_drift",
                    stage="GROUND",
                    details={"drift": repository_drift},
                )

            # This transition is made while holding the run lock. A concurrent or
            # repeated caller can no longer create a second controlled session.
            state["status"] = "STARTING"
            request: ForgeRunRequest = state["request"]

        try:
            manager = self._session_manager_factory(
                request,
                state["execution_bridge"],
                self.repo_root,
            )
            opened = manager.open_prepared_session(
                prepared_arena=state["prepared"],
                objective=request.objective,
                provider=request.provider,
                model=request.model,
                run_id=run_key,
                metadata={
                    **dict(request.metadata),
                    "forge_version": FORGE_VERSION,
                    "forge_contract_id": contract.contract_id,
                    "forge_contract_digest": actual_contract_digest,
                },
            )
        except Exception as exc:
            with self._run_lock:
                state["status"] = "BLOCKED_SESSION_EXCEPTION"
            return self._error(
                "controlled_session_open_error",
                stage="ACT",
                details={"exception_type": type(exc).__name__},
            )
        if not isinstance(opened, Mapping):
            with self._run_lock:
                state["status"] = "BLOCKED_SESSION_INVALID"
            return self._error("controlled_session_open_invalid", stage="ACT")
        if not opened.get("session_created"):
            with self._run_lock:
                state["last_result"] = dict(opened)
                state["status"] = "BLOCKED_SESSION_OPEN"
            return self._error("controlled_session_open_failed", stage="ACT", details=opened)

        session = dict(opened.get("session") or {})
        session_id = str(session.get("session_id") or "")
        if not session_id:
            with self._run_lock:
                state["status"] = "BLOCKED_SESSION_ID"
            return self._error("controlled_session_missing_id", stage="ACT", details=opened)

        with self._run_lock:
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
            "run_id": run_key,
            "status": state["status"],
            "contract": contract_payload,
            "contract_digest": actual_contract_digest,
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
        with state["lock"]:
            manager = state.get("manager")
            if manager is None:
                return self._error("forge_run_not_started", stage="ACT")
            if state.get("status") not in {"WAITING_FOR_MODEL", "WAITING_FOR_REPAIR"}:
                return self._error("forge_run_not_waiting_for_response", stage="ACT")
            answer = str(response or "")
            if (len(answer.encode("utf-8")) + 3) // 4 > state["request"].max_output_tokens:
                return self._error("forge_output_budget_exceeded", stage="ACT")

            try:
                result = manager.submit_response(
                    session_id=state["session_id"],
                    turn_id=str(turn_id),
                    response=answer,
                    provider_usage=_sanitize(dict(provider_usage or {})),
                )
            except Exception as exc:
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
            except Exception as exc:
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
        review_packet = self.human_review_packet(run_id) if state["status"] == REVIEW_READY_STATUS else None
        return {
            "ok": True,
            "version": FORGE_VERSION,
            "run_id": run_id,
            "status": state["status"],
            "contract": state["contract"].to_dict(),
            "contract_digest": state["contract_digest"],
            "session": _sanitize(session),
            "decision_eligible": bool(review_packet and review_packet.get("decision_eligible") is True),
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
            except Exception as exc:
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
                    self.bridge.aura_hotswap_status(plan_phase_hash=state["contract"].plan_phase_hash) or {}
                )
            except Exception:
                hotswap_status = {}

        ready = state["status"] == REVIEW_READY_STATUS
        gate_results = {
            "canonical_arena_verifier": bool(
                verification.get("ok") is True and not list(verification.get("failures") or [])
            ),
            "hotswap_readiness": bool(
                verification.get("hotswap_ready") is True or hotswap_status.get("hotswap_ready") is True
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
            "contract_digest": state["contract_digest"],
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
        except Exception as exc:
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
            "contract_digest": state["contract_digest"],
            "production_mutation": False,
            "human_review_required": True,
        }

    def _repository_drift(self, contract: ForgeEvidenceContract) -> dict[str, Any]:
        """Compare retained authority evidence with the repository at start time."""
        repository = contract.repository
        drift: dict[str, Any] = {}

        expected_head = str(repository.get("head_sha") or "")
        current_head = _git_head(self.repo_root)
        if current_head != expected_head:
            drift["head_sha"] = {"expected": expected_head, "actual": current_head}

        codemap_path = str(repository.get("codemap_path") or CODEMAP_PATH)
        expected_codemap = str(repository.get("codemap_digest") or "")
        current_codemap = _repo_file_digest(self.repo_root, codemap_path)
        if current_codemap != expected_codemap:
            drift["codemap_digest"] = {
                "path": codemap_path,
                "expected": expected_codemap,
                "actual": current_codemap,
            }

        expected_sources = repository.get("allowed_file_source_hashes")
        if not isinstance(expected_sources, Mapping):
            drift["allowed_file_source_hashes"] = {"error": "missing_or_invalid"}
            return drift
        source_drift: dict[str, Any] = {}
        for path in contract.allowed_files:
            expected = str(expected_sources.get(path) or "")
            actual = _repo_file_digest(self.repo_root, path)
            if actual != expected:
                source_drift[path] = {"expected": expected, "actual": actual}
        if source_drift:
            drift["allowed_file_source_hashes"] = source_drift
        return drift

    def _compile_contract(
        self,
        request: ForgeRunRequest,
        repo_digest: Mapping[str, Any],
        prepared: Mapping[str, Any],
        act_capsules: Sequence[Mapping[str, Any]],
        task_evidence: Sequence[Mapping[str, Any]],
    ) -> ForgeEvidenceContract:
        allowed_files: list[str] = []

        def add_allowed(candidate: Any) -> None:
            if not candidate:
                return
            path = _safe_repo_path(candidate, field_name="allowed_file")
            if path not in allowed_files:
                allowed_files.append(path)

        for capsule in act_capsules:
            for candidate in [capsule.get("target_file"), *list(capsule.get("related_files") or [])]:
                add_allowed(candidate)
        for evidence in task_evidence:
            add_allowed(evidence.get("target_file"))
            for field_name in ("dependencies", "tests", "related_files"):
                for candidate in list(evidence.get(field_name) or []):
                    add_allowed(candidate)
            for line_range in list(evidence.get("line_ranges") or []):
                if isinstance(line_range, Mapping):
                    add_allowed(line_range.get("file"))

        constraints = tuple(dict.fromkeys([*_CANONICAL_CONSTRAINTS, *request.constraints]))
        allowed_file_source_hashes = {path: _repo_file_digest(self.repo_root, path) for path in allowed_files}
        repository = _sanitize(
            {
                "head_sha": _git_head(self.repo_root),
                "codemap_path": CODEMAP_PATH,
                "codemap_digest": _repo_file_digest(self.repo_root, CODEMAP_PATH),
                "allowed_file_source_hashes": allowed_file_source_hashes,
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
        canonical_capsules = [_sanitize(dict(item)) for item in act_capsules]
        canonical_evidence = [_sanitize(dict(item)) for item in task_evidence]
        identity_payload = {
            "request_digest": request_digest,
            "repository": repository,
            "plan_phase_hash": str(prepared.get("plan_phase_hash") or ""),
            "act_capsules": canonical_capsules,
            "task_evidence": canonical_evidence,
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
            act_capsules=tuple(canonical_capsules),
            task_evidence=tuple(canonical_evidence),
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
        "version",
        "contract_id",
        "request_digest",
        "objective",
        "objective_digest",
        "repository",
        "plan_phase_hash",
        "act_capsules",
        "task_evidence",
        "required_gates",
        "allowed_files",
        "worker_contract",
        "authority",
        "lifecycle",
    }
    errors = [f"missing:{name}" for name in sorted(required - set(value))]
    if value.get("version") != FORGE_CONTRACT_VERSION:
        errors.append("unsupported_version")
    for name in ("contract_id", "request_digest", "objective", "objective_digest", "plan_phase_hash"):
        if not str(value.get(name) or "").strip():
            errors.append(f"{name}_must_not_be_empty")
    repository = value.get("repository")
    if not isinstance(repository, Mapping):
        errors.append("repository_must_be_object")
    else:
        head_sha = str(repository.get("head_sha") or "")
        if _GIT_OID_RE.fullmatch(head_sha) is None:
            errors.append("repository_head_sha_invalid")
        if repository.get("codemap_path") != CODEMAP_PATH:
            errors.append("invalid_repository_codemap_path")
        if not str(repository.get("codemap_digest") or "").startswith(_FULL_DIGEST_PREFIX):
            errors.append("repository_codemap_digest_invalid")
        if not isinstance(repository.get("allowed_file_source_hashes"), Mapping):
            errors.append("repository_source_hashes_must_be_object")
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
        if isinstance(repository, Mapping):
            source_hashes = repository.get("allowed_file_source_hashes")
            if isinstance(source_hashes, Mapping):
                allowed_keys = {str(item) for item in allowed_files}
                source_keys = {str(item) for item in source_hashes}
                if source_keys != allowed_keys:
                    errors.append("repository_source_hashes_scope_mismatch")
                for path, digest in source_hashes.items():
                    digest_text = str(digest or "")
                    if digest_text != "MISSING" and not digest_text.startswith(_FULL_DIGEST_PREFIX):
                        errors.append(f"repository_source_hash_invalid:{path}")
    return errors


__all__ = [
    "CODEMAP_PATH",
    "DEFAULT_REQUIRED_GATES",
    "FORGE_CONTRACT_VERSION",
    "FORGE_VERSION",
    "PATCH_AUTHORITY",
    "REVIEW_READY_STATUS",
    "SUPPORTED_REQUIRED_GATES",
    "VSA_PATCH_AUTHORITY",
    "AuraForgeRuntime",
    "ForgeEvidenceContract",
    "ForgeRunRequest",
    "forge_contract_digest",
    "validate_forge_contract",
]
