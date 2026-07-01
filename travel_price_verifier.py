"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f1-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: typing, __future__, dataclasses, datetime
FUNCTIONS: _parse_time, _parse_date, to_dict, __init__, verify_price
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

TRAVEL_PRICE_VERIFIER_VERSION = "AURA_TRAVEL_PRICE_VERIFIER_V1"
BLOCKED_FRESHNESS = {"stale", "expired", "unverified", "denied", "outdated_cache_replica", "vector_only"}


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None


@dataclass(frozen=True)
class TravelPriceVerification:
    approved: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    price_id: str | None = None
    requires_live_recheck_before_booking: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TRAVEL_PRICE_VERIFIER_VERSION,
            "approved": self.approved,
            "price_id": self.price_id,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "requires_live_recheck_before_booking": self.requires_live_recheck_before_booking,
        }


class TravelPriceVerifier:
    def __init__(self, *, max_age_hours: int = 72, min_confidence: float = 0.75, require_taxes: bool = False):
        self.max_age_hours = max_age_hours
        self.min_confidence = min_confidence
        self.require_taxes = require_taxes

    def verify_price(self, price: dict[str, Any] | None) -> TravelPriceVerification:
        if not price:
            return TravelPriceVerification(False, ("missing_sidecar_price",), (), None)
        blockers: list[str] = []
        warnings: list[str] = []
        required = (
            "price_id",
            "resort_id",
            "checkin_date",
            "checkout_date",
            "nights",
            "currency",
            "source_id",
            "snapshot_id",
            "observed_at",
            "parser_version",
            "freshness_status",
        )
        for key in required:
            if price.get(key) in (None, ""):
                blockers.append(f"missing_{key}")
        if price.get("nightly_price_minor") is None and price.get("total_price_minor") is None:
            blockers.append("missing_exact_price_minor_units")
        if self.require_taxes and price.get("taxes_fees_minor") is None:
            blockers.append("missing_taxes_fees")
        status = str(price.get("freshness_status") or "").lower()
        if status in BLOCKED_FRESHNESS:
            blockers.append(f"blocked_freshness_{status}")
        observed = _parse_time(price.get("observed_at"))
        if observed is None:
            blockers.append("invalid_observed_at")
        else:
            age_hours = (datetime.now(timezone.utc) - observed).total_seconds() / 3600
            if age_hours > self.max_age_hours:
                blockers.append("price_observation_stale")
            elif age_hours > self.max_age_hours * 0.75:
                warnings.append("price_observation_near_stale")
        checkin = _parse_date(price.get("checkin_date"))
        checkout = _parse_date(price.get("checkout_date"))
        if not checkin or not checkout:
            blockers.append("invalid_date_range")
        elif checkout <= checkin:
            blockers.append("checkout_not_after_checkin")
        else:
            computed_nights = (checkout.date() - checkin.date()).days
            try:
                nights = int(price.get("nights", 0))
            except (TypeError, ValueError):
                blockers.append("invalid_nights_field")
            else:
                if nights <= 0:
                    blockers.append("nights_must_be_positive")
                elif nights != computed_nights:
                    blockers.append(f"nights_mismatch_expected_{computed_nights}_got_{nights}")
        try:
            confidence = float(price.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < self.min_confidence:
            blockers.append("source_confidence_below_threshold")
        if price.get("booking_url") in (None, ""):
            warnings.append("missing_booking_url")
        return TravelPriceVerification(
            approved=not blockers,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            price_id=price.get("price_id"),
        )

