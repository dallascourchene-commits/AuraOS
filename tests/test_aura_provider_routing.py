from __future__ import annotations

import asyncio
import json

from aura_api_rotator import ProviderKeyRotator, load_secrets, provider_key_pool
from aura_fusion import load_fusion_config
from aura_provider_registry import ProviderRegistry


def test_provider_key_pool_collects_primary_plural_numbered_and_aliases(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY_4", "env-four")
    secrets = {
        "DEEPSEEK_API_KEY": "primary",
        "DEEPSEEK_API_KEYS": ["backup-one", "backup-two", "backup-one"],
        "DEEPSEEK_API_KEY_2": "number-two",
        "DEEPSEEK_API_KEY_3": "paste_key_here",
    }
    assert provider_key_pool("deepseek", secrets) == [
        "primary", "backup-one", "backup-two", "number-two", "env-four",
    ]
    assert provider_key_pool("xai", {"GROK_API_KEY": "grok-alias"}) == ["grok-alias"]


def test_provider_rotator_round_robins_and_cools_failed_key(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("aura_api_rotator.time.time", lambda: now[0])
    rotator = ProviderKeyRotator("deepseek", keys=["one", "two"])
    assert rotator.iter_keys() == ["one", "two"]
    assert rotator.iter_keys() == ["two", "one"]
    rotator.record_failure("one", "429 quota")
    assert rotator.iter_keys() == ["two"]
    now[0] += 91
    assert set(rotator.iter_keys()) == {"one", "two"}


def test_registry_is_deepseek_first_and_role_aware():
    registry = ProviderRegistry()
    assert registry.provider_order("premium")[:3] == ["deepseek", "xai", "anthropic"]
    assert registry.provider_order("cheap_builder")[:2] == ["mistral", "groq"]
    assert registry.resolve_model("deepseek", "premium") == "deepseek-v4-pro"
    assert registry.resolve_model("deepseek", "cheap_builder") == "deepseek-v4-flash"
    assert registry.resolve_model("mistral", "premium") == "mistral-large-latest"
    assert registry.resolve_model("mistral", "cheap_builder") == "mistral-small-latest"
    assert registry.resolve_model("groq", "premium") == "llama-3.3-70b-versatile"
    assert registry.get_provider_config("xai")["api_key_aliases"] == ["GROK_API_KEY"]


def test_external_llm_rotates_keys_then_falls_back_provider(monkeypatch):
    import aura_llm_egress

    calls = []

    def fake_generate(url, api_key, payload, **_kwargs):
        calls.append((url, api_key, payload["model"]))
        if "deepseek" in url:
            return None, "429 quota exhausted"
        return "mistral-ok", None

    monkeypatch.setattr(aura_llm_egress, "openai_compatible_generate", fake_generate)
    egress = aura_llm_egress.ExternalLLM(
        secrets={
            "DEEPSEEK_API_KEYS": ["ds-one", "ds-two"],
            "MISTRAL_API_KEY": "mi-one",
        }
    )
    text, error, _latency = egress.generate(
        "route me",
        pre_egress=False,
        resonance_egress=False,
        context_crush=False,
    )
    assert error is None
    assert text == "mistral-ok"
    assert [call[1] for call in calls] == ["ds-one", "ds-two", "mi-one"]
    assert egress.provider == "mistral"
    assert egress.model == "mistral-large-latest"


def test_explicit_provider_rotates_keys_without_cross_provider_fallback(monkeypatch):
    import aura_llm_egress

    calls = []

    def fake_generate(url, api_key, payload, **_kwargs):
        calls.append((url, api_key))
        return None, "quota"

    monkeypatch.setattr(aura_llm_egress, "openai_compatible_generate", fake_generate)
    egress = aura_llm_egress.ExternalLLM(
        provider="deepseek",
        secrets={
            "DEEPSEEK_API_KEYS": ["strict-one", "strict-two"],
            "MISTRAL_API_KEY": "strict-mi-one",
        },
    )
    text, error, _latency = egress.generate(
        "strict route",
        pre_egress=False,
        resonance_egress=False,
        context_crush=False,
    )
    assert text is None
    assert "deepseek" in error
    assert [key for _url, key in calls] == ["strict-one", "strict-two"]


def test_loaded_secrets_synthesizes_fusion_roles(tmp_path):
    secrets_path = tmp_path / "aura_secrets.json"
    secrets_path.write_text(json.dumps({
        "DEEPSEEK_API_KEY": "ds-one",
        "MISTRAL_API_KEYS": ["mi-one", "mi-two"],
    }), encoding="utf-8")
    configured = load_secrets(secrets_path)
    panel, judge = load_fusion_config(configured)
    assert [(agent.role, agent.provider, agent.model) for agent in panel] == [
        ("THINKER", "deepseek", "deepseek-v4-pro"),
        ("WORKER", "mistral", "mistral-small-latest"),
        ("VERIFIER", "deepseek", "deepseek-v4-flash"),
    ]
    assert judge is not None
    assert (judge.provider, judge.model) == ("deepseek", "deepseek-v4-pro")


def test_direct_fusion_egress_rotates_loaded_keys_then_falls_back(monkeypatch):
    import aura_llm_egress

    calls = []
    secrets = {
        "DEEPSEEK_API_KEYS": ["ds-one", "ds-two"],
        "MISTRAL_API_KEY": "mi-one",
    }

    def fake_generate(url, api_key, payload, **_kwargs):
        calls.append((url, api_key, payload["model"]))
        if "deepseek" in url:
            return None, "429 quota"
        return "mistral-fallback", None

    monkeypatch.setattr(aura_llm_egress, "load_secrets", lambda: secrets)
    monkeypatch.setattr(aura_llm_egress, "openai_compatible_generate", fake_generate)
    text, error, _latency, _schema = aura_llm_egress.generate_openai_compatible_payload(
        provider="deepseek",
        base_url="https://api.deepseek.com/chat/completions",
        api_key="ds-one",
        model="deepseek-v4-pro",
        messages=[{"role": "user", "content": "analyze"}],
        context_crush=False,
    )
    assert error is None
    assert text == "mistral-fallback"
    assert [call[1] for call in calls] == ["ds-one", "ds-two", "mi-one"]


def test_architect_model_callback_maps_cost_tier_to_role(monkeypatch):
    import aura_llm_egress

    captured = []

    class FakeExternalLLM:
        def __init__(self, **kwargs):
            captured.append({"init": kwargs})

        def generate(self, prompt, **kwargs):
            captured[-1]["generate"] = {"prompt": prompt, **kwargs}
            return "ok", None, 0.01

    monkeypatch.setattr(aura_llm_egress, "ExternalLLM", FakeExternalLLM)
    assert aura_llm_egress.generate_architect_model(
        "MISTRAL",
        "critic",
        {"role": "shadow", "profile": {"cost_tier": "cheap"}},
    ) == "ok"
    assert captured[-1]["init"]["model"] == "cheap_builder"
    assert captured[-1]["init"]["provider"] == "mistral"
    assert captured[-1]["init"]["allow_provider_fallback"] is True

    assert aura_llm_egress.generate_architect_model(
        "DEEPSEEK",
        "judge",
        {"role": "judge", "profile": {"cost_tier": "premium"}},
    ) == "ok"
    assert captured[-1]["init"]["model"] == "premium"
    assert captured[-1]["init"]["provider"] == "deepseek"


def test_council_v3_router_defaults_follow_canonical_provider_policy():
    from aura_architect_council_v3 import SelectiveArchitectModelRouter

    profiles = SelectiveArchitectModelRouter().profiles
    assert profiles["planner"].provider == "DEEPSEEK"
    assert profiles["planner_alt"].provider == "MISTRAL"
    assert profiles["worker"].provider == "MISTRAL"
    assert profiles["shadow"].provider == "MISTRAL"
    assert profiles["judge"].provider == "DEEPSEEK"


def test_council_v3_intercepts_legacy_aura_node_callback(monkeypatch):
    import aura_llm_egress
    from aura_architect_council_v3 import SelectiveArchitectModelRouter

    calls = []

    async def legacy_callback(provider, prompt, payload):
        calls.append((provider, prompt, payload))
        return "legacy"

    legacy_callback.__module__ = "aura_node"
    legacy_callback.__name__ = "call_architect_model"
    monkeypatch.setattr(
        aura_llm_egress,
        "generate_architect_model",
        lambda provider, prompt, payload: f"canonical:{provider}:{payload['role']}",
    )

    router = SelectiveArchitectModelRouter(model_caller=legacy_callback)
    result = asyncio.run(router.call_model("judge", "review this", intensity=4))

    assert result == "canonical:DEEPSEEK:judge"
    assert calls == []


def test_legacy_fireworks_worker_name_routes_through_canonical_egress(monkeypatch):
    import aura_agent_arena_fireworks as bridge

    monkeypatch.setattr(bridge, "load_secrets", lambda: {"DEEPSEEK_API_KEY": "ds-worker"})
    monkeypatch.setattr(bridge, "_openai_worker_providers", lambda _secrets, _role: ["deepseek"])

    def fake_route(**kwargs):
        assert kwargs["model_role"] == "coding"
        assert kwargs["context_crush"] is False
        return (
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n",
            None,
            0.02,
            False,
            {"provider": "deepseek", "model": "deepseek-v4-pro", "fallback_index": 0, "key_count": 1},
        )

    monkeypatch.setattr(bridge, "generate_routed_openai_compatible_payload", fake_route)
    result = bridge.fireworks_patch_worker(
        task_id="A1",
        compressed_context="exact source slice",
        instruction="fix the local defect",
        model_tier="code",
    )
    assert result["ok"] is True
    assert result["provider"] == "deepseek"
    assert result["model"] == "deepseek-v4-pro"
    assert result["must_stage_before_apply"] is True
