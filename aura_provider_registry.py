"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:PROVIDER_REGISTRY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Secrets Isolation)
DEPENDENCIES: __future__, os, typing
FUNCTIONS: ProviderRegistry, get_provider_config, get_redacted_health_report
SYNOPSIS: Configuration-driven registry managing external LLM endpoints and roles.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

AURA_PROVIDER_REGISTRY_V1 = "AURA_PROVIDER_REGISTRY_V1"
FIREWORKS_GLM_5P2 = "accounts/fireworks/models/glm-5p2"
FIREWORKS_DEEPSEEK_V4_FLASH = "accounts/fireworks/models/deepseek-v4-flash"
DEEPSEEK_V4_FLASH = "deepseek-v4-flash"
DEEPSEEK_V4_PRO = "deepseek-v4-pro"


def _config(
    provider: str,
    key: str,
    url: str,
    model: str,
    *,
    capabilities: list[str],
    default_roles: dict[str, str],
    api: str = "openai",
    model_priority: list[str] | None = None,
) -> Dict[str, Any]:
    packet: Dict[str, Any] = {
        "provider": provider,
        "api_key_env": key,
        "key": key,
        "base_url": url,
        "url": url,
        "capabilities": list(capabilities),
        "default_roles": dict(default_roles),
        "model": model,
        "model_priority": list(model_priority or [model]),
        "zero_local_ram": True,
        "version": AURA_PROVIDER_REGISTRY_V1,
    }
    if api != "openai":
        packet["api"] = api
    return packet


class ProviderRegistry:
    """External provider and model-role registry with no plaintext secrets."""

    def __init__(self) -> None:
        self.provider_priority = [
            "fireworks",
            "deepseek",
            "anthropic",
            "mistral",
            "sambanova",
            "groq",
            "cerebras",
            "openrouter",
            "github",
            "openai",
            "gemini",
        ]
        self.providers: Dict[str, Dict[str, Any]] = {
            "fireworks": _config(
                "fireworks",
                "FIREWORKS_API_KEY",
                "https://api.fireworks.ai/inference/v1/chat/completions",
                FIREWORKS_GLM_5P2,
                capabilities=["chat", "structured_outputs", "tool_calling", "vision", "batch", "embeddings"],
                default_roles={
                    "primary": FIREWORKS_GLM_5P2,
                    "premium": FIREWORKS_GLM_5P2,
                    "reasoner": FIREWORKS_GLM_5P2,
                    "coding": FIREWORKS_GLM_5P2,
                    "cheap_builder": FIREWORKS_DEEPSEEK_V4_FLASH,
                    "shadow": FIREWORKS_DEEPSEEK_V4_FLASH,
                    "summarizer": FIREWORKS_DEEPSEEK_V4_FLASH,
                },
                model_priority=[FIREWORKS_GLM_5P2, FIREWORKS_DEEPSEEK_V4_FLASH],
            ),
            "deepseek": _config(
                "deepseek",
                "DEEPSEEK_API_KEY",
                "https://api.deepseek.com/chat/completions",
                DEEPSEEK_V4_FLASH,
                capabilities=["chat", "structured_outputs", "tool_calling", "reasoning", "long_context"],
                default_roles={
                    "primary": DEEPSEEK_V4_PRO,
                    "premium": DEEPSEEK_V4_PRO,
                    "reasoner": DEEPSEEK_V4_PRO,
                    "coding": DEEPSEEK_V4_PRO,
                    "cheap_builder": DEEPSEEK_V4_FLASH,
                    "shadow": DEEPSEEK_V4_FLASH,
                    "summarizer": DEEPSEEK_V4_FLASH,
                },
                model_priority=[DEEPSEEK_V4_FLASH, DEEPSEEK_V4_PRO],
            ),
            "mistral": _config(
                "mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1/chat/completions", "mistral-small-latest",
                capabilities=["chat", "structured_outputs"],
                default_roles={"cheap_builder": "mistral-small-latest", "shadow": "mistral-small-latest", "summarizer": "mistral-small-latest"},
            ),
            "sambanova": _config(
                "sambanova", "SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1/chat/completions", "Meta-Llama-3.3-70B-Instruct",
                capabilities=["chat"],
                default_roles={"cheap_builder": "Meta-Llama-3.3-70B-Instruct", "shadow": "Meta-Llama-3.3-70B-Instruct"},
            ),
            "groq": _config(
                "groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile",
                capabilities=["chat", "tool_calling"],
                default_roles={"cheap_builder": "llama-3.3-70b-versatile", "shadow": "llama-3.3-70b-versatile", "summarizer": "llama-3.3-70b-versatile"},
            ),
            "cerebras": _config(
                "cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions", "llama-3.3-70b",
                capabilities=["chat"],
                default_roles={"cheap_builder": "llama-3.3-70b", "shadow": "llama-3.3-70b"},
            ),
            "openrouter": _config(
                "openrouter", "OPEN_ROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.3-70b-instruct",
                capabilities=["chat"],
                default_roles={"cheap_builder": "meta-llama/llama-3.3-70b-instruct", "shadow": "meta-llama/llama-3.3-70b-instruct"},
            ),
            "github": _config(
                "github", "GITHUB_TOKEN", "https://models.inference.ai.azure.com/chat/completions", "gpt-4o-mini",
                capabilities=["chat"],
                default_roles={"cheap_builder": "gpt-4o-mini", "shadow": "gpt-4o-mini"},
            ),
            "openai": _config(
                "openai", "OPENAI_API_KEY", "https://api.openai.com/v1/chat/completions", "gpt-4o-mini",
                capabilities=["chat"],
                default_roles={"cheap_builder": "gpt-4o-mini", "shadow": "gpt-4o-mini"},
            ),
            "anthropic": _config(
                "anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/messages", "claude-sonnet-4-6",
                capabilities=["chat"],
                default_roles={"cheap_builder": "claude-sonnet-4-6", "shadow": "claude-sonnet-4-6"},
                api="anthropic",
            ),
            "gemini": _config(
                "gemini", "GEMINI_API_KEY", "(gemini-rest)", "gemini-1.5-flash",
                capabilities=["chat", "vision", "structured_outputs"],
                default_roles={"cheap_builder": "gemini-1.5-flash", "shadow": "gemini-1.5-flash", "summarizer": "gemini-1.5-flash"},
                api="gemini",
            ),
        }

    def get_provider_config(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return self.providers.get(provider_id)

    def get_api_key(self, provider_id: str) -> Optional[str]:
        config = self.get_provider_config(provider_id)
        return os.environ.get(config["api_key_env"]) if config else None

    def get_redacted_health_report(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        for pid, cfg in self.providers.items():
            key = self.get_api_key(pid)
            configured = bool(key and key.strip())
            redacted = "NOT_SET"
            if configured:
                redacted = key[:4] + "..." + key[-4:] if len(key) > 8 else "REDACTED"
            report[pid] = {
                "configured": configured,
                "api_key": redacted,
                "base_url": cfg["base_url"],
                "model": cfg["model"],
                "model_priority": list(cfg.get("model_priority") or []),
                "capabilities": cfg["capabilities"],
                "zero_local_ram": cfg["zero_local_ram"],
            }
        return report

    def __repr__(self) -> str:
        return f"ProviderRegistry(providers={list(self.providers.keys())})"
