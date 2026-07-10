"""
Aura Pricing Registry — versioned price records with snapshot preservation.

Replaces uncontrolled fallback pricing with versioned price records.
Supports local configuration overrides. Preserves the price snapshot used
for each historical run. Never silently substitutes pricing for unknown models.

Dependencies: stdlib only.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
REGISTRY_VERSION = "AURA_PRICING_REGISTRY_V2"

# Cost status values
COST_MEASURED = "COST_MEASURED"  # Provider-billed
COST_CALCULATED = "COST_CALCULATED"  # Registry price * tokens
COST_UNKNOWN = "COST_UNKNOWN"  # No pricing available
COST_LOCAL_ZERO = "COST_LOCAL_ZERO"  # Local model, zero API cost


@dataclass(frozen=True)
class PriceRecord:
    provider: str
    model: str
    input_per_million_usd: float
    output_per_million_usd: float
    cached_input_per_million_usd: float | None = None
    cache_write_per_million_usd: float | None = None
    effective_at: str = "2026-07-01"
    source: str = "aura_pricing_registry_v2"
    currency: str = "USD"
    registry_version: str = REGISTRY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "input_per_million_usd": self.input_per_million_usd,
            "output_per_million_usd": self.output_per_million_usd,
            "cached_input_per_million_usd": self.cached_input_per_million_usd,
            "cache_write_per_million_usd": self.cache_write_per_million_usd,
            "effective_at": self.effective_at,
            "source": self.source,
            "currency": self.currency,
            "registry_version": self.registry_version,
        }


# Seed pricing table (migrated from aura_token_economics.PRICING_PER_M with versioning)
_SEED_PRICES: list[PriceRecord] = [
    PriceRecord("anthropic", "claude-sonnet-4-6", 3.00, 15.00, cached_input_per_million_usd=0.30),
    PriceRecord("anthropic", "claude-opus-4-8", 5.00, 25.00, cached_input_per_million_usd=0.50),
    PriceRecord("anthropic", "claude-3-5-haiku-latest", 0.80, 4.00),
    PriceRecord("mistral", "mistral-small-latest", 0.20, 0.60),
    PriceRecord("mistral", "codestral-latest", 0.30, 0.90),
    PriceRecord("sambanova", "Meta-Llama-3.3-70B-Instruct", 0.60, 1.20),
    PriceRecord("groq", "llama-3.3-70b-versatile", 0.59, 0.79),
    PriceRecord("groq", "llama-3.3-70b-specdec", 0.59, 0.99),
    PriceRecord("gemini", "gemini-1.5-flash", 0.07, 0.30),
    PriceRecord("gemini", "gemini-1.5-pro", 3.50, 10.50),
    PriceRecord("openai", "gpt-4o-mini", 0.15, 0.60),
    PriceRecord("fireworks", "accounts/fireworks/models/glm-5p2", 0.90, 0.90),
]


class PricingRegistry:
    """Versioned pricing registry with snapshot preservation."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.root = Path(repo_root).resolve()
        self._prices: dict[str, PriceRecord] = {}
        self._load_seed()
        self._load_overrides()

    def _load_seed(self) -> None:
        for record in _SEED_PRICES:
            self._prices[record.model] = record

    def _load_overrides(self) -> None:
        """Load local pricing overrides from .aura/pricing_overrides.json."""
        path = self.root / ".aura" / "pricing_overrides.json"
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                for entry in data.get("prices", []):
                    record = PriceRecord(
                        provider=entry.get("provider", "unknown"),
                        model=entry["model"],
                        input_per_million_usd=float(entry["input_per_million_usd"]),
                        output_per_million_usd=float(entry["output_per_million_usd"]),
                        cached_input_per_million_usd=entry.get("cached_input_per_million_usd"),
                        cache_write_per_million_usd=entry.get("cache_write_per_million_usd"),
                        source="local_override",
                    )
                    self._prices[record.model] = record
        except Exception:
            pass

    def get_price(self, model: str) -> PriceRecord | None:
        """Get price record for a model. Returns None if unknown."""
        return self._prices.get(model)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
        cached_input_tokens: int | None = None,
        cache_creation_tokens: int | None = None,
        provider_billed_cost: float | None = None,
    ) -> dict[str, Any]:
        """Calculate cost with measurement precedence.

        Precedence:
        1. Provider-billed cost (COST_MEASURED)
        2. Registry price calculation (COST_CALCULATED)
        3. Unknown (COST_UNKNOWN)
        """
        # Provider-billed cost takes precedence
        if provider_billed_cost is not None:
            return {
                "cost_usd": provider_billed_cost,
                "cost_status": COST_MEASURED,
                "price_snapshot": None,
                "calculation_detail": "provider_billed",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        price = self.get_price(model)
        if price is None:
            return {
                "cost_usd": None,
                "cost_status": COST_UNKNOWN,
                "price_snapshot": None,
                "calculation_detail": "no_pricing_for_model",
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        # Calculate from registry prices
        in_cost = (input_tokens or 0) / 1_000_000 * price.input_per_million_usd
        out_cost = (output_tokens or 0) / 1_000_000 * price.output_per_million_usd

        cached_cost = 0.0
        if cached_input_tokens and price.cached_input_per_million_usd is not None:
            cached_cost = cached_input_tokens / 1_000_000 * price.cached_input_per_million_usd
            # Cached tokens are typically charged at the cached rate instead of full input rate
            in_cost = (max(0, (input_tokens or 0) - cached_input_tokens)) / 1_000_000 * price.input_per_million_usd

        cache_write_cost = 0.0
        if cache_creation_tokens and price.cache_write_per_million_usd is not None:
            cache_write_cost = cache_creation_tokens / 1_000_000 * price.cache_write_per_million_usd

        total_cost = round(in_cost + out_cost + cached_cost + cache_write_cost, 6)

        return {
            "cost_usd": total_cost,
            "cost_status": COST_CALCULATED,
            "price_snapshot": price.to_dict(),
            "calculation_detail": {
                "input_cost": round(in_cost, 6),
                "output_cost": round(out_cost, 6),
                "cached_cost": round(cached_cost, 6),
                "cache_write_cost": round(cache_write_cost, 6),
            },
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of all current prices for persistence."""
        return {
            "registry_version": REGISTRY_VERSION,
            "prices": [r.to_dict() for r in self._prices.values()],
        }

    def list_models(self) -> list[str]:
        return list(self._prices.keys())
