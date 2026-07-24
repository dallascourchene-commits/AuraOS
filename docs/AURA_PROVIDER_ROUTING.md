# Aura Provider Routing and API-Key Rotation

Aura's external-model policy is owned by:

- `aura_provider_registry.py` — provider endpoints, model roles, and deterministic provider order;
- `aura_api_rotator.py` — secret loading, provider key pools, round-robin selection, and cooldowns;
- `aura_llm_egress.py` — guarded calls, role-aware provider fallback, logging, and Council callbacks.

Council, Council V3, AuraFusion, and the legacy-named Agent Arena Fireworks worker must use these owners rather than hard-coding provider calls.

## Default policy

Premium, reasoner, coding, and default work starts with direct DeepSeek. The direct DeepSeek premium role uses `deepseek-v4-pro`; its cheap/Shadow role uses `deepseek-v4-flash`.

Cheap, Shadow, and summarization work starts with lower-cost providers such as Mistral before consuming premium lanes. Mistral uses `mistral-large-latest` for premium work and `mistral-small-latest` for cheap work.

xAI/Grok is registered through `XAI_API_KEY` or the `GROK_API_KEY` alias and participates when a usable key exists. Fireworks remains a compatibility fallback; it is no longer the primary route.

An explicitly pinned `ExternalLLM(provider=...)` call rotates that provider's keys but does not cross providers. Unpinned calls and governed Council/Fusion/Agent Bridge calls fall through to the next configured provider after key exhaustion, quota errors, timeouts, or provider failures.

## Secrets-file shapes

For any registered provider, Aura accepts all of these forms:

```json
{
  "DEEPSEEK_API_KEY": "primary",
  "DEEPSEEK_API_KEYS": ["backup-1", "backup-2"],
  "DEEPSEEK_API_KEY_2": "numbered-backup"
}
```

Plural values may be JSON lists or comma/semicolon-separated strings. Numbered keys are discovered deterministically. Environment values supplement `aura_secrets.json`. Placeholder-looking values are rejected.

Equivalent forms work for `MISTRAL`, `XAI`, `GROQ`, `SAMBANOVA`, `CEREBRAS`, `OPENAI`, `FIREWORKS`, and other registered providers. Registered aliases include:

- `GROK_API_KEY` for xAI;
- `OPENROUTER_API_KEY` for `OPEN_ROUTER_API_KEY`;
- `GEMINI_KEY` and `GOOGLE_API_KEY` for Gemini;
- `GITHUB_MODELS_API_KEY` for GitHub Models.

Never commit `aura_secrets.json` or real keys.

## Role routing

```text
premium/default/reasoner/coding
  → DeepSeek first
  → rotate every DeepSeek key
  → next configured premium provider

cheap/shadow/summarizer
  → lower-cost provider order
  → rotate every key for that provider
  → next configured cheap provider
```

AuraFusion automatically synthesizes a role-aware panel when `AURA_FUSION_PANEL` and `AURA_FUSION_JUDGE` are absent or empty. Explicit legacy panel configuration remains supported and is treated as the preferred route, not a single point of failure.

## Authority boundaries

Provider routing changes transport and model selection only. They grant no patch, commit, push, pull-request, merge, grammar-promotion, or policy authority. Exact source spans, hashes, tests, verifier gates, and human authorization remain controlling.
