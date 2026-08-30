"""Arena-facing governed adapter for Project006 Creator Studio media effects.

This is the missing seam between the already-proven AWJ-023 transactional
consumer and the NONO-brokered Creator Studio media child.  It deliberately
owns no Drive transport, durable cursor, lease/fence minting, SpendGrant
minting, or provider credentials.

The host consumer must call this adapter only after it has independently
resolved currentness, lease/fence and a live effect admission for the exact
handoff.  The adapter then launches the media child through NONO and returns a
redacted terminal record suitable for the existing bus writer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping, Sequence

from tools.project006.creator_media_handoff import HANDOFF_VERSION, validate_handoff

ADAPTER_VERSION = "AURA_CREATOR_MEDIA_ADAPTER_V1"
ADMISSION_VERSION = "LIVE_MEDIA_EFFECT_ADMISSION_V1"
CAPABILITY = "CREATOR_MEDIA_HIGGSFIELD_V1"
EFFECT_CLASS = "HIGGSFIELD_CREATOR_MEDIA_PROVIDER_EFFECT"
PROFILE_RELATIVE = Path("tools/project006/nono_profiles/creator-studio-higgsfield.json")
RUNNER_MODULE = "tools.project006.creator_media_nono_runner"

_REQUIRED = frozenset({"adapter_version", "command_id", "idempotency_key", "authority_ref", "arena_generation", "arena_head", "capability", "handoff", "effect_admission"})
_ADMISSION_REQUIRED = frozenset({"admission_version", "command_id", "idempotency_key", "authority_ref", "handoff_digest", "currentness_ref", "spend_grant_ref", "spend_ceiling_microusd", "spend_decision", "provider_effect_decision", "attempt_limit", "fallback_allowed", "media_route_ref", "media_kind", "admission_ref"})
_FORBIDDEN_KEYS = frozenset({"api_key", "api_keys", "credential", "credentials", "authorization", "password", "secret", "provider_url", "base_url", "endpoint", "status_url"})


class ArenaMediaAdapterError(ValueError):
    """Typed fail-closed Arena media adapter error."""


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _text(name: str, value: Any, maximum: int = 1024) -> str:
    if not isinstance(value, str):
        raise ArenaMediaAdapterError(f"INVALID_{name.upper()}")
    value = value.strip()
    if not value or len(value) > maximum or any(ord(ch) < 32 for ch in value):
        raise ArenaMediaAdapterError(f"INVALID_{name.upper()}")
    return value


def _reject_provider_control(value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if str(raw_key).strip().lower() in _FORBIDDEN_KEYS:
                raise ArenaMediaAdapterError("CALLER_PROVIDER_CONTROL_FORBIDDEN")
            _reject_provider_control(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_provider_control(child)


def validate_dispatch(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _REQUIRED:
        raise ArenaMediaAdapterError("INVALID_ADAPTER_SHAPE")
    _reject_provider_control(raw)
    if raw.get("adapter_version") != ADAPTER_VERSION:
        raise ArenaMediaAdapterError("UNSUPPORTED_ADAPTER_VERSION")
    if raw.get("capability") != CAPABILITY:
        raise ArenaMediaAdapterError("CAPABILITY_MISMATCH")

    command_id = _text("command_id", raw.get("command_id"), 256)
    idempotency_key = _text("idempotency_key", raw.get("idempotency_key"), 256)
    authority_ref = _text("authority_ref", raw.get("authority_ref"))
    arena_generation = raw.get("arena_generation")
    if not isinstance(arena_generation, int) or isinstance(arena_generation, bool) or arena_generation < 0:
        raise ArenaMediaAdapterError("INVALID_ARENA_GENERATION")
    arena_head = _text("arena_head", raw.get("arena_head"), 128)

    handoff = validate_handoff(raw.get("handoff"))
    if handoff["handoff_version"] != HANDOFF_VERSION:
        raise ArenaMediaAdapterError("HANDOFF_VERSION_MISMATCH")
    handoff_digest = _digest(handoff)

    admission = raw.get("effect_admission")
    if not isinstance(admission, Mapping) or set(admission) != _ADMISSION_REQUIRED:
        raise ArenaMediaAdapterError("INVALID_EFFECT_ADMISSION_SHAPE")
    if admission.get("admission_version") != ADMISSION_VERSION:
        raise ArenaMediaAdapterError("UNSUPPORTED_EFFECT_ADMISSION_VERSION")
    if _text("admission_command_id", admission.get("command_id"), 256) != command_id:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("admission_idempotency_key", admission.get("idempotency_key"), 256) != idempotency_key:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("admission_authority_ref", admission.get("authority_ref")) != authority_ref:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("handoff_digest", admission.get("handoff_digest"), 64) != handoff_digest:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("currentness_ref", admission.get("currentness_ref")) != handoff["currentness_ref"]:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("spend_grant_ref", admission.get("spend_grant_ref")) != handoff["spend_grant_ref"]:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("media_route_ref", admission.get("media_route_ref"), 128) != handoff["media_route_ref"]:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if _text("media_kind", admission.get("media_kind"), 32) != handoff["media_kind"]:
        raise ArenaMediaAdapterError("EFFECT_ADMISSION_BINDING_MISMATCH")
    if admission.get("spend_decision") != "ALLOW" or admission.get("provider_effect_decision") != "ALLOW":
        raise ArenaMediaAdapterError("LIVE_MEDIA_EFFECT_NOT_ALLOWED")
    ceiling = admission.get("spend_ceiling_microusd")
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling <= 0:
        raise ArenaMediaAdapterError("UNKNOWN_OR_INVALID_SPEND_CEILING")
    if admission.get("attempt_limit") != 1 or admission.get("fallback_allowed") is not False:
        raise ArenaMediaAdapterError("EFFECT_ATTEMPT_POLICY_WIDENED")
    admission_ref = _text("admission_ref", admission.get("admission_ref"))

    return {
        "adapter_version": ADAPTER_VERSION,
        "command_id": command_id,
        "idempotency_key": idempotency_key,
        "authority_ref": authority_ref,
        "arena_generation": arena_generation,
        "arena_head": arena_head,
        "capability": CAPABILITY,
        "effect_class": EFFECT_CLASS,
        "handoff": handoff,
        "handoff_digest": handoff_digest,
        "admission_ref": admission_ref,
        "spend_ceiling_microusd": ceiling,
    }


@dataclass(frozen=True)
class ChildResult:
    returncode: int
    stdout: str
    stderr: str = ""


Runner = Callable[[Sequence[str], str], ChildResult]


def _default_runner(argv: Sequence[str], stdin_text: str) -> ChildResult:
    proc = subprocess.run(
        list(argv),
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=930,
    )
    return ChildResult(returncode=int(proc.returncode), stdout=proc.stdout, stderr=proc.stderr)


def build_nono_argv(*, repo_root: Path) -> tuple[str, ...]:
    profile = (repo_root / PROFILE_RELATIVE).resolve()
    return (
        "nono",
        "run",
        "--profile",
        str(profile),
        "--",
        "python3",
        "-m",
        RUNNER_MODULE,
    )


def execute_live_media(raw: Mapping[str, Any], *, repo_root: Path, runner: Runner = _default_runner) -> dict[str, Any]:
    dispatch = validate_dispatch(raw)
    argv = build_nono_argv(repo_root=repo_root)
    child = runner(argv, json.dumps(dispatch["handoff"], sort_keys=True))

    base = {
        "adapter_version": ADAPTER_VERSION,
        "command_id": dispatch["command_id"],
        "idempotency_key": dispatch["idempotency_key"],
        "authority_ref": dispatch["authority_ref"],
        "arena_generation": dispatch["arena_generation"],
        "arena_head": dispatch["arena_head"],
        "capability": CAPABILITY,
        "effect_class": EFFECT_CLASS,
        "handoff_digest": dispatch["handoff_digest"],
        "effect_admission_ref": dispatch["admission_ref"],
        "spend_ceiling_microusd": dispatch["spend_ceiling_microusd"],
        "attempt_limit": 1,
        "fallback_allowed": False,
    }

    if child.returncode not in (0, 4):
        return {**base, "status": "MEDIA_CHILD_TYPED_ERROR", "provider_attempt_outcome": "UNKNOWN", "error": "CREATOR_MEDIA_NONO_CHILD_FAILURE"}
    try:
        payload = json.loads(child.stdout)
    except Exception:
        return {**base, "status": "MEDIA_CHILD_TYPED_ERROR", "provider_attempt_outcome": "UNKNOWN", "error": "CREATOR_MEDIA_NONO_CHILD_MALFORMED_OUTPUT"}
    if not isinstance(payload, Mapping) or not isinstance(payload.get("receipt"), Mapping):
        return {**base, "status": "MEDIA_CHILD_TYPED_ERROR", "provider_attempt_outcome": "UNKNOWN", "error": "CREATOR_MEDIA_NONO_CHILD_MALFORMED_OUTPUT"}

    receipt = dict(payload["receipt"])
    # Only fields already defined by the redacted provider-facing receipt cross
    # back into the Arena.  Never propagate stderr or environment values.
    return {
        **base,
        "status": "OK" if payload.get("ok") is True else "PROVIDER_TERMINAL_NON_OK",
        "provider_attempt_outcome": receipt.get("status", "UNKNOWN"),
        "media_receipt": receipt,
    }
