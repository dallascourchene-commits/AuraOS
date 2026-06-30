"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:PROVIDER_REGISTRY]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Secrets Isolation)
DEPENDENCIES: __future__, os, json, typing
FUNCTIONS: ProviderRegistry, get_provider_config, get_redacted_health_report
SYNOPSIS: Configuration-driven registry managing key details and capabilities of external LLM endpoints.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import os
from typing import Dict, Any, List, Optional

AURA_PROVIDER_REGISTRY_V1 = "AURA_PROVIDER_REGISTRY_V1"


class ProviderRegistry:
    """
    Stores external LLM provider configurations, model names, role suitability,
    and structured-output support. Ensures keys are never hardcoded or logged in plaintext.
    """

    def __init__(self):
        self.providers: Dict[str, Dict[str, Any]] = {
            "fireworks": {
                "provider": "fireworks",
                "api_key_env": "FIREWORKS_API_KEY",
                "key": "FIREWORKS_API_KEY",  # legacy key compat
                "base_url": "https://api.fireworks.ai/inference/v1/chat/completions",
                "url": "https://api.fireworks.ai/inference/v1/chat/completions",  # legacy url compat
                "capabilities": [
                    "chat",
                    "structured_outputs",
                    "tool_calling",
                    "vision",
                    "batch",
                    "embeddings"
                ],
                "default_roles": {
                    "cheap_builder": "accounts/fireworks/models/llama-v3p1-70b-instruct",
                    "shadow": "accounts/fireworks/models/llama-v3p1-70b-instruct",
                    "summarizer": "accounts/fireworks/models/llama-v3p1-8b-instruct"
                },
                "model": "accounts/fireworks/models/llama-v3p1-70b-instruct",  # default model
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "mistral": {
                "provider": "mistral",
                "api_key_env": "MISTRAL_API_KEY",
                "key": "MISTRAL_API_KEY",
                "base_url": "https://api.mistral.ai/v1/chat/completions",
                "url": "https://api.mistral.ai/v1/chat/completions",
                "capabilities": ["chat", "structured_outputs"],
                "default_roles": {
                    "cheap_builder": "mistral-small-latest",
                    "shadow": "mistral-small-latest",
                    "summarizer": "mistral-small-latest"
                },
                "model": "mistral-small-latest",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "sambanova": {
                "provider": "sambanova",
                "api_key_env": "SAMBANOVA_API_KEY",
                "key": "SAMBANOVA_API_KEY",
                "base_url": "https://api.sambanova.ai/v1/chat/completions",
                "url": "https://api.sambanova.ai/v1/chat/completions",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "Meta-Llama-3.3-70B-Instruct",
                    "shadow": "Meta-Llama-3.3-70B-Instruct"
                },
                "model": "Meta-Llama-3.3-70B-Instruct",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "groq": {
                "provider": "groq",
                "api_key_env": "GROQ_API_KEY",
                "key": "GROQ_API_KEY",
                "base_url": "https://api.groq.com/openai/v1/chat/completions",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "capabilities": ["chat", "tool_calling"],
                "default_roles": {
                    "cheap_builder": "llama-3.3-70b-versatile",
                    "shadow": "llama-3.3-70b-versatile",
                    "summarizer": "llama-3.3-70b-versatile"
                },
                "model": "llama-3.3-70b-versatile",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "cerebras": {
                "provider": "cerebras",
                "api_key_env": "CEREBRAS_API_KEY",
                "key": "CEREBRAS_API_KEY",
                "base_url": "https://api.cerebras.ai/v1/chat/completions",
                "url": "https://api.cerebras.ai/v1/chat/completions",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "llama-3.3-70b",
                    "shadow": "llama-3.3-70b"
                },
                "model": "llama-3.3-70b",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "openrouter": {
                "provider": "openrouter",
                "api_key_env": "OPEN_ROUTER_API_KEY",
                "key": "OPEN_ROUTER_API_KEY",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "meta-llama/llama-3.3-70b-instruct",
                    "shadow": "meta-llama/llama-3.3-70b-instruct"
                },
                "model": "meta-llama/llama-3.3-70b-instruct",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "github": {
                "provider": "github",
                "api_key_env": "GITHUB_TOKEN",
                "key": "GITHUB_TOKEN",
                "base_url": "https://models.inference.ai.azure.com/chat/completions",
                "url": "https://models.inference.ai.azure.com/chat/completions",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "gpt-4o-mini",
                    "shadow": "gpt-4o-mini"
                },
                "model": "gpt-4o-mini",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "openai": {
                "provider": "openai",
                "api_key_env": "OPENAI_API_KEY",
                "key": "OPENAI_API_KEY",
                "base_url": "https://api.openai.com/v1/chat/completions",
                "url": "https://api.openai.com/v1/chat/completions",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "gpt-4o-mini",
                    "shadow": "gpt-4o-mini"
                },
                "model": "gpt-4o-mini",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "anthropic": {
                "provider": "anthropic",
                "api_key_env": "ANTHROPIC_API_KEY",
                "key": "ANTHROPIC_API_KEY",
                "api": "anthropic",
                "base_url": "https://api.anthropic.com/v1/messages",
                "url": "https://api.anthropic.com/v1/messages",
                "capabilities": ["chat"],
                "default_roles": {
                    "cheap_builder": "claude-sonnet-4-6",
                    "shadow": "claude-sonnet-4-6"
                },
                "model": "claude-sonnet-4-6",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            },
            "gemini": {
                "provider": "gemini",
                "api_key_env": "GEMINI_API_KEY",
                "key": "GEMINI_API_KEY",
                "api": "gemini",
                "base_url": "(gemini-rest)",
                "url": "(gemini-rest)",
                "capabilities": ["chat", "vision", "structured_outputs"],
                "default_roles": {
                    "cheap_builder": "gemini-1.5-flash",
                    "shadow": "gemini-1.5-flash",
                    "summarizer": "gemini-1.5-flash"
                },
                "model": "gemini-1.5-flash",
                "zero_local_ram": True,
                "version": AURA_PROVIDER_REGISTRY_V1
            }
        }

    def get_provider_config(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Returns the configuration for a given provider, if registered."""
        return self.providers.get(provider_id)

    def get_api_key(self, provider_id: str) -> Optional[str]:
        """Resolves the API key strictly from the environment variable, not a literal storage."""
        config = self.get_provider_config(provider_id)
        if not config:
            return None
        env_var = config["api_key_env"]
        return os.environ.get(env_var)

    def get_redacted_health_report(self) -> Dict[str, Any]:
        """Generates a health report of registered providers, ensuring keys are redacted."""
        report = {}
        for pid, cfg in self.providers.items():
            key = self.get_api_key(pid)
            configured = False
            redacted_val = "NOT_SET"
            if key and key.strip():
                configured = True
                redacted_val = key[:4] + "..." + key[-4:] if len(key) > 8 else "REDACTED"
            
            report[pid] = {
                "configured": configured,
                "api_key": redacted_val,
                "base_url": cfg["base_url"],
                "capabilities": cfg["capabilities"],
                "zero_local_ram": cfg["zero_local_ram"]
            }
        return report

    def __repr__(self) -> str:
        # Override repr to ensure secrets are never logged or exposed accidentally
        return f"ProviderRegistry(providers={list(self.providers.keys())})"
