import json
from pathlib import Path

from aura_fusion import (
    AuraFusionAgent,
    AuraFusionCoordinator,
    JUDGE_SCHEMA,
    PANEL_SCHEMA,
    build_task_capsule,
    load_fusion_config,
    parse_json_object,
)


def _fusion_config():
    return {
        "OPEN_ROUTER_API_KEY": "sk-test-openrouter",
        "GROQ_API_KEY": "sk-test-groq",
        "AURA_FUSION_PANEL": [
            {
                "name": "thinker",
                "role": "THINKER",
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "api_key_name": "OPEN_ROUTER_API_KEY",
                "model": "model-a",
            },
            {
                "name": "worker",
                "role": "WORKER",
                "provider": "groq",
                "base_url": "https://api.groq.com/openai/v1/chat/completions",
                "api_key_name": "GROQ_API_KEY",
                "model": "model-b",
            },
        ],
        "AURA_FUSION_JUDGE": {
            "name": "judge",
            "role": "JUDGE",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key_name": "OPEN_ROUTER_API_KEY",
            "model": "judge-model",
        },
    }


def test_fusion_config_loads_from_aura_secrets_style_dict():
    panel, judge = load_fusion_config(_fusion_config())

    assert [agent.role for agent in panel] == ["THINKER", "WORKER"]
    assert judge is not None
    assert judge.role == "JUDGE"
    assert panel[0].api_key_name == "OPEN_ROUTER_API_KEY"


def test_capsule_has_stable_phase_hash_and_required_fields():
    capsule = build_task_capsule(
        "Compare router strategies",
        target_file="aura_router.py",
        target_symbol="AutoRouter",
        output_mode="JSON_EDIT_PLAN",
        codemap_epoch="epoch-test",
    )

    assert capsule["capsule_version"] == "AURA_FUSION_CAPSULE_V1"
    assert capsule["target_file"] == "aura_router.py"
    assert len(capsule["phase_hash"]) == 32


def test_parse_json_object_handles_fenced_json():
    data = parse_json_object('```json\n{"role":"THINKER","answer":"ok"}\n```')
    assert data == {"role": "THINKER", "answer": "ok"}


def test_panel_and_judge_schema_required_fields_are_explicit():
    assert "confidence" in PANEL_SCHEMA["required"]
    assert "final_answer" in JUDGE_SCHEMA["required"]
    assert "contradictions" in JUDGE_SCHEMA["required"]


def test_mock_fusion_run_logs_structured_result(tmp_path: Path):
    log_path = tmp_path / "fusion_runs.jsonl"
    coordinator = AuraFusionCoordinator(secrets={}, mock=True, log_path=str(log_path))
    result = coordinator.run("Compare router and Fusion orchestration")

    assert result.ok is True
    assert result.metrics["panel_count"] == 3
    assert result.judge_output["ok"] is True
    assert "mock synthesis complete" in result.final_answer

    logged = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert logged["phase_hash"] == result.phase_hash


def test_fusion_gate_blocks_ungrounded_mutation_before_panel_dispatch(tmp_path: Path):
    log_path = tmp_path / "fusion_runs.jsonl"
    coordinator = AuraFusionCoordinator(secrets={}, mock=True, log_path=str(log_path))
    result = coordinator.run("fix the router", output_mode="JSON_EDIT_PLAN")

    assert result.ok is False
    assert result.metrics["panel_count"] == 0
    assert "target_file" in result.final_answer


def test_missing_api_key_rejects_cleanly_without_secret_leak(tmp_path: Path):
    agent = AuraFusionAgent(
        name="thinker",
        role="THINKER",
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key_name="OPEN_ROUTER_API_KEY",
        model="model-a",
    )
    judge = AuraFusionAgent(
        name="judge",
        role="JUDGE",
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        api_key_name="OPEN_ROUTER_API_KEY",
        model="judge-model",
    )
    coordinator = AuraFusionCoordinator(
        secrets={"OPEN_ROUTER_API_KEY": "paste_key_here"},
        panel=[agent],
        judge=judge,
        mock=False,
        log_path=str(tmp_path / "fusion_runs.jsonl"),
    )
    result = coordinator.run("Compare router strategies")

    assert result.ok is False
    assert "missing usable API key named OPEN_ROUTER_API_KEY" in result.final_answer
    assert "paste_key_here" not in result.final_answer
