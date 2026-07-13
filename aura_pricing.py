"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:2A86BBF77059E372]
DIKWP_TIER: KNOWLEDGE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Honest Accounting)
DEPENDENCIES: json, os, time
FUNCTIONS: PriceBook, get_pricebook
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]

Aura PriceBook — per-provider token pricing with weekly auto-refresh.
====================================================================

Single source of truth for $/1k token prices, persisted at .aura/pricing.json
with a last-updated timestamp. Prices go stale after 7 days; `maybe_refresh()`
re-fetches if a fetcher is registered. Without a fetcher Aura never fabricates
live prices.
"""
from __future__ import annotations

import json
import os
import time

_DIR = os.path.dirname(os.path.abspath(__file__))
PRICING_PATH = os.path.join(_DIR, ".aura", "pricing.json")
STALE_AFTER_DAYS = 7

# Seed prices in USD per 1,000 tokens. Fireworks reflects its primary GLM 5.2
# route; the budget DeepSeek-V4-Flash role has a lower model-specific price and
# should be refreshed by a future model-aware pricing fetcher when selected.
DEFAULT_PRICES: dict[str, dict] = {
    "fireworks":  {"in_per_1k": 0.0014,  "out_per_1k": 0.0044},
    "deepseek":   {"in_per_1k": 0.00014, "out_per_1k": 0.00028},
    "mistral":    {"in_per_1k": 0.0002,  "out_per_1k": 0.0006},
    "sambanova":  {"in_per_1k": 0.0006,  "out_per_1k": 0.0012},
    "groq":       {"in_per_1k": 0.00059, "out_per_1k": 0.00079},
    "cerebras":   {"in_per_1k": 0.00085, "out_per_1k": 0.0012},
    "openrouter": {"in_per_1k": 0.0006,  "out_per_1k": 0.0006},
    "github":     {"in_per_1k": 0.00015, "out_per_1k": 0.0006},
    "openai":     {"in_per_1k": 0.00015, "out_per_1k": 0.0006},
    "anthropic":  {"in_per_1k": 0.0008,  "out_per_1k": 0.004},
    "gemini":     {"in_per_1k": 0.00007, "out_per_1k": 0.0003},
    "mock":       {"in_per_1k": 0.0,     "out_per_1k": 0.0},
}


class PriceBook:
    def __init__(self, path: str = PRICING_PATH):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception:
                pass
        data = {
            "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prices": dict(DEFAULT_PRICES),
        }
        self._save(data)
        return data

    def _save(self, data: dict | None = None) -> None:
        data = data if data is not None else self.data
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def price(self, provider: str) -> tuple[float, float]:
        packet = (
            self.data.get("prices", {}).get(provider)
            or DEFAULT_PRICES.get(provider)
            or {"in_per_1k": 0.0, "out_per_1k": 0.0}
        )
        return float(packet["in_per_1k"]), float(packet["out_per_1k"])

    def cost(self, provider: str, in_tokens: int, out_tokens: int) -> float:
        price_in, price_out = self.price(provider)
        return round(in_tokens / 1000 * price_in + out_tokens / 1000 * price_out, 6)

    def updated_at(self) -> str:
        return self.data.get("updated", "")

    def is_stale(self, days: int = STALE_AFTER_DAYS) -> bool:
        timestamp = self.data.get("updated")
        if not timestamp:
            return True
        try:
            parsed = time.mktime(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ"))
        except ValueError:
            return True
        return (time.time() - parsed) > days * 86400

    def update(self, provider: str, in_per_1k: float, out_per_1k: float) -> None:
        self.data.setdefault("prices", {})[provider] = {
            "in_per_1k": float(in_per_1k),
            "out_per_1k": float(out_per_1k),
        }
        self.data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save()

    def maybe_refresh(self, fetcher=None, days: int = STALE_AFTER_DAYS) -> bool:
        if not self.is_stale(days) or fetcher is None:
            return False
        try:
            fresh = fetcher() or {}
        except Exception:
            return False
        if not isinstance(fresh, dict) or not fresh:
            return False
        changed = self.data.get("prices", {}) != fresh
        self.data["prices"] = {**self.data.get("prices", {}), **fresh}
        self.data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save()
        return changed


_BOOK: PriceBook | None = None


def get_pricebook() -> PriceBook:
    global _BOOK
    if _BOOK is None:
        _BOOK = PriceBook()
    return _BOOK
