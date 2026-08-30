from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.project006.creator_media_arena_adapter import (
    ADAPTER_VERSION,
    ADMISSION_VERSION,
    CAPABILITY,
    ArenaMediaAdapterError,
    ChildResult,
    execute_live_media,
    validate_dispatch,
)
from tools.project006.creator_media_handoff import HANDOFF_VERSION


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def handoff(route="higgsfield.qwen-image-3"):
    return {
        "handoff_version": HANDOFF_VERSION,
        "root_dispatch_id": "root-1",
        "dispatch_generation": 24,
        "intent_digest": "a" * 64,
        "validation_receipt_ref": "validation-1",
        "media_route_ref": route,
        "capsule_id": "capsule-1",
        "lease_generation": 7,
        "fencing_token": "fence-private",
        "currentness_ref": "current-1",
        "spend_grant_ref": "spend-1",
        "prompt": "A red apple on a white table",
    }


def dispatch(route="higgsfield.qwen-image-3"):
    h = handoff(route)
    normalized = {
        **h,
        "media_kind": "image" if "image" in route else "video",
        "create_path": "/alibaba/qwen-image-3/text-to-image" if route == "higgsfield.qwen-image-3" else "/kling-video/v3.0/std/text-to-video",
        "deadline_ms": 180000,
        "poll_initial_ms": 2000,
        "poll_max_ms": 10000,
    }
    # validate_handoff adds derived fields before adapter digesting.
    from tools.project006.creator_media_handoff import validate_handoff
    normalized = validate_handoff(h)
    return {
        "adapter_version": ADAPTER_VERSION,
        "command_id": "cmd-1",
        "idempotency_key": "key-1",
        "authority_ref": "owner-1",
        "arena_generation": 24,
        "arena_head": "3aeb8f3db921201f",
        "capability": CAPABILITY,
        "handoff": h,
        "effect_admission": {
            "admission_version": ADMISSION_VERSION,
            "command_id": "cmd-1",
            "idempotency_key": "key-1",
            "authority_ref": "owner-1",
            "handoff_digest": _digest(normalized),
            "currentness_ref": "current-1",
            "spend_grant_ref": "spend-1",
            "spend_ceiling_microusd": 1000000,
            "spend_decision": "ALLOW",
            "provider_effect_decision": "ALLOW",
            "attempt_limit": 1,
            "fallback_allowed": False,
            "media_route_ref": route,
            "media_kind": normalized["media_kind"],
            "admission_ref": "live-admission-1",
        },
    }


def test_valid_dispatch_binds_exact_admission():
    out = validate_dispatch(dispatch())
    assert out["capability"] == CAPABILITY
    assert out["spend_ceiling_microusd"] == 1000000


def test_rejects_forged_spend_reference():
    raw = dispatch()
    raw["effect_admission"]["spend_grant_ref"] = "other"
    with pytest.raises(ArenaMediaAdapterError, match="EFFECT_ADMISSION_BINDING_MISMATCH"):
        validate_dispatch(raw)


def test_rejects_unknown_cost():
    raw = dispatch()
    raw["effect_admission"]["spend_ceiling_microusd"] = 0
    with pytest.raises(ArenaMediaAdapterError, match="UNKNOWN_OR_INVALID_SPEND_CEILING"):
        validate_dispatch(raw)


def test_rejects_retry_or_fallback_widening():
    raw = dispatch()
    raw["effect_admission"]["attempt_limit"] = 2
    with pytest.raises(ArenaMediaAdapterError, match="EFFECT_ATTEMPT_POLICY_WIDENED"):
        validate_dispatch(raw)


def test_rejects_caller_provider_endpoint_control():
    raw = dispatch()
    raw["handoff"]["endpoint"] = "https://evil.example"
    with pytest.raises(ArenaMediaAdapterError, match="CALLER_PROVIDER_CONTROL_FORBIDDEN"):
        validate_dispatch(raw)


def test_executes_only_through_nono_profile_and_returns_receipt():
    seen = {}
    def runner(argv, stdin_text):
        seen["argv"] = tuple(argv)
        seen["stdin"] = json.loads(stdin_text)
        return ChildResult(0, json.dumps({
            "ok": True,
            "receipt": {
                "status": "OK",
                "provider": "higgsfield",
                "media_kind": "image",
                "asset_url": "https://assets.example/image.png",
                "attempts": 1,
            },
        }))

    out = execute_live_media(dispatch(), repo_root=Path("/repo"), runner=runner)
    assert seen["argv"][0:3] == ("nono", "run", "--profile")
    assert seen["argv"][-3:] == ("python3", "-m", "tools.project006.creator_media_nono_runner")
    assert seen["stdin"]["fencing_token"] == "fence-private"
    assert out["status"] == "OK"
    assert out["media_receipt"]["asset_url"].endswith("image.png")
    assert "fencing_token" not in json.dumps(out)


def test_child_failure_is_redacted():
    def runner(argv, stdin_text):
        return ChildResult(3, "", "SECRET SHOULD NEVER RETURN")
    out = execute_live_media(dispatch(), repo_root=Path("/repo"), runner=runner)
    assert out["status"] == "MEDIA_CHILD_TYPED_ERROR"
    assert "SECRET" not in json.dumps(out)
