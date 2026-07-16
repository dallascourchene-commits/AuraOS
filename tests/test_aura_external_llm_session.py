from __future__ import annotations

import json
from pathlib import Path

from aura_external_llm_session import (
    AuraExternalLLMSessionManager as BaseAuraExternalLLMSessionManager,
    InstrumentedExternalModelCaller,
    _token_estimate,
)
from aura_external_llm_session_safe import AuraExternalLLMSessionManager


class FakeBridge:
    def __init__(self, *, verify_ready: bool = True) -> None:
        self.verify_ready = verify_ready
        self.calls: list[tuple[str, dict]] = []

    def aura_prepare_arena(self, **kwargs):
        self.calls.append(("prepare", kwargs))
        return {
            "ok": True,
            "plan_phase_hash": "PLAN-1",
            "act_capsules": [
                {
                    "task_id": "A1",
                    "target_file": "aura_memory.py",
                    "target_symbol": "consolidate_memory",
                    "related_files": [],
                    "objective": kwargs["objective"],
                    "size": "M",
                    "role": "cheap_builder",
                }
            ],
            "grounding_evidence": [],
            "shadow_findings": [],
            "routing_decisions": [{"task_id": "A1", "route": "BUILDER_PATCH"}],
            "ready_for_incubator": True,
        }

    def aura_get_micro_context(self, **kwargs):
        self.calls.append(("micro", kwargs))
        return {
            "ok": True,
            "task_id": "A1",
            "target_file": "aura_memory.py",
            "target_symbol": "consolidate_memory",
            "line_ranges": [
                {
                    "file": "aura_memory.py",
                    "symbol": "consolidate_memory",
                    "line_range": [20, 40],
                }
            ],
            "tests": ["tests/test_aura_memory.py"],
            "compressed_context": "Target file and exact symbol only.",
        }

    def aura_read_slice(self, **kwargs):
        self.calls.append(("read", kwargs))
        if str(kwargs["file"]).startswith("tests/"):
            content = "def test_consolidate_memory():\n    assert True"
        else:
            content = (
                "def consolidate_memory(items):\n"
                "    return list(dict.fromkeys(items))"
            )
        return {
            "ok": True,
            "file": kwargs["file"],
            "symbol": kwargs.get("symbol") or "",
            "line_start": 1,
            "line_end": len(content.splitlines()),
            "total_lines": 5000,
            "content": content,
            "warnings": [],
        }

    def aura_stage_patch(self, **kwargs):
        self.calls.append(("stage", kwargs))
        return {
            "ok": True,
            "patch": {
                "patch_id": "PATCH-1",
                "task_id": kwargs["task_id"],
                "affected_files": kwargs["affected_files"],
                "status": "staged",
            },
        }

    def aura_verify_arena(self, **kwargs):
        self.calls.append(("verify", kwargs))
        return {
            "ok": self.verify_ready,
            "stage": "ready" if self.verify_ready else "blocked",
            "failures": [] if self.verify_ready else [
                {"stage": "tests", "message": "one assertion failed"}
            ],
            "checks": [],
            "next_action": "promote_hotswap" if self.verify_ready else "repair_with_builder",
            "hotswap_ready": self.verify_ready,
        }

    def aura_repair_packet(self, **kwargs):
        self.calls.append(("repair", kwargs))
        return {
            "ok": True,
            "task_id": kwargs["task_id"],
            "failed_check": "tests",
            "compressed_error": "one assertion failed",
            "allowed_files": ["aura_memory.py"],
            "do_not_touch": ["aura_node.py"],
            "required_response": "unified diff only",
        }

    def aura_hotswap_status(self, **kwargs):
        self.calls.append(("hotswap", kwargs))
        return {
            "ok": True,
            "status": "ready",
            "hotswap_ready": True,
            "production_mutation": False,
        }


def test_open_session_returns_only_bounded_slices(tmp_path: Path) -> None:
    bridge = FakeBridge()
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    result = manager.open_session(
        objective="Consolidate memory, skills, and agent functions for the Human Agent Arena",
        max_context_tokens=700,
    )
    assert result["ok"] is True
    turn = result["turn"]
    assert turn["role"] == "worker"
    assert turn["source_slices"][0]["file"] == "aura_memory.py"
    assert turn["test_slices"][0]["file"] == "tests/test_aura_memory.py"
    assert turn["source_slices"][0]["total_lines"] == 5000
    assert "entire repository" not in json.dumps(turn).lower()
    assert turn["context_token_estimate"] <= 700
    assert turn["production_mutation"] is False
    assert all(name != "repo_download" for name, _ in bridge.calls)


def test_submit_response_stages_verifies_and_stops_for_human_review(tmp_path: Path) -> None:
    bridge = FakeBridge(verify_ready=True)
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    opened = manager.open_session(objective="Consolidate Aura capabilities")
    turn = opened["turn"]
    diff = (
        "diff --git a/aura_memory.py b/aura_memory.py\n"
        "--- a/aura_memory.py\n"
        "+++ b/aura_memory.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def consolidate_memory(items):\n"
        "+def consolidate_memory(items):\n"
        "     return list(dict.fromkeys(items))\n"
    )
    result = manager.submit_response(
        session_id=opened["session"]["session_id"],
        turn_id=turn["turn_id"],
        response=diff,
        provider_usage={"input_tokens": 300, "output_tokens": 80},
    )
    assert result["ok"] is True
    assert result["status"] == "READY_FOR_HUMAN_REVIEW"
    assert result["next_turn"] is None
    stage_call = next(payload for name, payload in bridge.calls if name == "stage")
    assert stage_call["affected_files"] == ["aura_memory.py"]
    assert result["hotswap_status"]["production_mutation"] is False


def test_failed_verification_returns_bounded_repair_turn(tmp_path: Path) -> None:
    bridge = FakeBridge(verify_ready=False)
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    opened = manager.open_session(objective="Consolidate Aura capabilities")
    turn = opened["turn"]
    diff = (
        "diff --git a/aura_memory.py b/aura_memory.py\n"
        "--- a/aura_memory.py\n"
        "+++ b/aura_memory.py\n"
        "@@ -1 +1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
    )
    result = manager.submit_response(
        session_id=opened["session"]["session_id"],
        turn_id=turn["turn_id"],
        response=diff,
    )
    assert result["ok"] is False
    assert result["status"] == "WAITING_FOR_REPAIR"
    repair = result["next_turn"]
    assert repair["role"] == "repair"
    assert repair["failure_packet"]["source"] == "verification_gate"
    assert repair["allowed_files"] == ["aura_memory.py"]
    assert repair["do_not_touch"] == ["aura_node.py"]
    assert repair["context_token_estimate"] <= 2200


def test_session_export_is_confined_to_review_workspace(tmp_path: Path) -> None:
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=FakeBridge())
    opened = manager.open_session(objective="Consolidate Aura capabilities")
    result = manager.export_session(opened["session"]["session_id"], "review/session.json")
    assert result["ok"] is True
    assert result["relative_path"] == "Aura_Staging/external_llm_sessions/review/session.json"
    target = tmp_path / result["relative_path"]
    assert target.is_file()
    assert json.loads(target.read_text(encoding="utf-8"))["session"]["production_mutation"] is False


def test_session_export_rejects_absolute_and_parent_paths(tmp_path: Path) -> None:
    manager = AuraExternalLLMSessionManager(tmp_path, bridge=FakeBridge())
    opened = manager.open_session(objective="Consolidate Aura capabilities")
    session_id = opened["session"]["session_id"]
    absolute = manager.export_session(session_id, tmp_path.parent / "escape.json")
    traversal = manager.export_session(session_id, "../escape.json")
    assert absolute["ok"] is False
    assert absolute["error"] == "absolute_export_path_forbidden"
    assert traversal["ok"] is False
    assert traversal["error"] == "export_path_traversal_forbidden"
    assert not (tmp_path.parent / "escape.json").exists()


def test_instrumented_caller_records_role_tokens_cost_and_digests() -> None:
    def callback(request):
        assert request["production_mutation"] is False
        return {
            "text": '{"approved": true}',
            "usage": {"input_tokens": 44, "output_tokens": 5},
            "cost_usd": 0.0004,
        }

    caller = InstrumentedExternalModelCaller(callback, hard_prompt_token_limit=1000)
    text = caller(
        "OPENAI",
        "Return JSON only.",
        {"role": "judge", "profile": {"model_class": "premium_judge"}},
    )
    assert text == '{"approved": true}'
    summary = caller.summary()
    assert summary["call_count"] == 1
    assert summary["reported_cost_usd"] == 0.0004
    assert summary["calls"][0]["role"] == "judge"
    assert summary["calls"][0]["request_digest"]
    assert summary["calls"][0]["response_digest"]


class TwoTaskBridge(FakeBridge):
    def __init__(self, *, fail_second_micro: bool = False) -> None:
        super().__init__(verify_ready=True)
        self.fail_second_micro = fail_second_micro

    def aura_prepare_arena(self, **kwargs):
        result = super().aura_prepare_arena(**kwargs)
        result["act_capsules"] = [
            dict(result["act_capsules"][0]),
            {
                "task_id": "A2",
                "target_file": "aura_skills.py",
                "target_symbol": "consolidate_skills",
                "related_files": [],
                "objective": kwargs["objective"],
                "size": "M",
                "role": "cheap_builder",
            },
        ]
        result["routing_decisions"].append({"task_id": "A2", "route": "BUILDER_PATCH"})
        return result

    def aura_get_micro_context(self, **kwargs):
        if kwargs.get("task_id") == "A2" and self.fail_second_micro:
            self.calls.append(("micro", kwargs))
            return {"ok": False, "error": "micro_context_unavailable"}
        result = super().aura_get_micro_context(**kwargs)
        if kwargs.get("task_id") == "A2":
            result.update(
                {
                    "task_id": "A2",
                    "target_file": "aura_skills.py",
                    "target_symbol": "consolidate_skills",
                    "line_ranges": [
                        {
                            "file": "aura_skills.py",
                            "symbol": "consolidate_skills",
                            "line_range": [10, 30],
                        }
                    ],
                    "tests": [],
                }
            )
        return result


class OversizedFallbackBridge(FakeBridge):
    def aura_read_slice(self, **kwargs):
        self.calls.append(("read", kwargs))
        return {
            "ok": True,
            "file": "nested/" + "x" * 160 + ".py",
            "symbol": "oversized_symbol",
            "line_start": 1,
            "line_end": 1,
            "total_lines": 1,
            "content": "x = 1",
            "warnings": ["w" * 160],
        }


def _review_diff(path: str = "aura_memory.py") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
    )


def test_base_manager_blocks_successive_turn_at_max_turns(tmp_path: Path) -> None:
    bridge = TwoTaskBridge()
    manager = BaseAuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    opened = manager.open_session(objective="Complete two capsules", max_turns=1)
    before = len([1 for name, _ in bridge.calls if name == "micro"])
    result = manager.submit_response(
        session_id=opened["session"]["session_id"],
        turn_id=opened["turn"]["turn_id"],
        response=_review_diff(),
    )
    after = len([1 for name, _ in bridge.calls if name == "micro"])
    assert result["ok"] is False
    assert result["status"] == "BLOCKED_MAX_TURNS"
    assert result["next_turn"] is None
    assert result["session"]["pending_turn"] is None
    assert after == before


def test_base_manager_never_waits_without_pending_turn(tmp_path: Path) -> None:
    bridge = TwoTaskBridge(fail_second_micro=True)
    manager = BaseAuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    opened = manager.open_session(objective="Complete two capsules", max_turns=4)
    result = manager.submit_response(
        session_id=opened["session"]["session_id"],
        turn_id=opened["turn"]["turn_id"],
        response=_review_diff(),
    )
    assert result["ok"] is False
    assert result["status"] == "BLOCKED_NEXT_TURN_UNAVAILABLE"
    assert result["next_turn"] is None
    assert result["session"]["pending_turn"] is None


def test_base_manager_fallback_charges_full_serialized_slice(tmp_path: Path) -> None:
    bridge = OversizedFallbackBridge()
    manager = BaseAuraExternalLLMSessionManager(tmp_path, bridge=bridge)
    micro = {
        "ok": True,
        "target_file": "aura_memory.py",
        "target_symbol": "consolidate_memory",
        "line_ranges": [],
        "tests": [],
    }
    source, test_slices = manager._lease_slices(micro, token_budget=70)
    assert source == []
    assert test_slices == []
    compact = manager._compact_slice(bridge.aura_read_slice(file="aura_memory.py"))
    assert _token_estimate(json.dumps(compact, sort_keys=True, default=str)) > 70
