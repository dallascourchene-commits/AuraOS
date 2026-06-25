"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa907-[Q-SYS:TRAVEL_SOURCE_REGISTRY]
DIKWP_TIER: KNOWLEDGE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Compliant Source Registry)
DEPENDENCIES: dataclasses, datetime, typing, travel_price_sidecar
FUNCTIONS: TravelSourceProfile, option_b_source_profiles, TravelSourceRegistry
SYNOPSIS: Registry for Option B open-source travel scrapers with compliance, rate-limit, source-priority, and metadata expectations before raw records enter Aura Travel.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from travel_price_sidecar import TravelPriceSidecar


OPTION_B_REGISTRY_VERSION = "AURA_TRAVEL_OPTION_B_SOURCE_REGISTRY_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class TravelSourceProfile:
    scraper_kind: str
    repo: str
    source_type: str
    target: str
    expected_metadata: tuple[str, ...]
    parser_version: str
    priority: int
    rate_limit_seconds: float
    allow_state: str = "operator_review_required"
    robots_allowed: bool | None = None
    terms_status: str = "operator_review_required"
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_source_record(self, *, source_url: str | None = None, resort_id: str | None = None) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "scraper_kind": self.scraper_kind,
            "source_url": source_url,
            "repo": self.repo,
            "resort_id": resort_id,
            "robots_allowed": self.robots_allowed,
            "terms_status": self.terms_status,
            "allow_state": self.allow_state,
            "priority": self.priority,
            "rate_limit_seconds": self.rate_limit_seconds,
            "last_checked_at": _utc_now(),
            "metadata": {
                "registry_version": OPTION_B_REGISTRY_VERSION,
                "target": self.target,
                "expected_metadata": list(self.expected_metadata),
                "parser_version": self.parser_version,
                "notes": list(self.notes),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def option_b_source_profiles() -> dict[str, TravelSourceProfile]:
    return {
        "tripadvisor": TravelSourceProfile(
            scraper_kind="tripadvisor",
            repo="omkarcloud/tripadvisor-scraper",
            source_type="option_b_github_scraper",
            target="TripAdvisor",
            expected_metadata=(
                "activity_descriptors",
                "restaurant_attachments",
                "guided_tours",
                "attraction_descriptors",
                "location_text",
                "review_tags",
            ),
            parser_version="option_b_tripadvisor_parser_v1",
            priority=20,
            rate_limit_seconds=5.0,
            notes=("Use for climate-specific activities, local attractions, and high-resonance intent text.",),
        ),
        "tripadvisor_apify": TravelSourceProfile(
            scraper_kind="tripadvisor_apify",
            repo="apify/tripadvisor-scraper",
            source_type="option_b_github_scraper",
            target="TripAdvisor",
            expected_metadata=("activity_descriptors", "attraction_descriptors", "location_text", "review_tags"),
            parser_version="option_b_tripadvisor_parser_v1",
            priority=15,
            rate_limit_seconds=5.0,
            notes=("Alternate TripAdvisor scraper profile; requires operator review of target terms.",),
        ),
        "expedia_hotels": TravelSourceProfile(
            scraper_kind="expedia_hotels",
            repo="Ramun-123/expedia-hotels-4-0",
            source_type="option_b_github_scraper",
            target="Expedia/Hotels.com/Orbitz",
            expected_metadata=(
                "hotel_name",
                "coordinates",
                "amenities",
                "cancellation_policy",
                "calendar_prices",
                "booking_url",
            ),
            parser_version="option_b_expedia_hotels_parser_v1",
            priority=30,
            rate_limit_seconds=6.0,
            notes=("Use for exact hotel metadata, amenities, cancellation policies, and historical calendar prices.",),
        ),
    }


class TravelSourceRegistry:
    def __init__(self, sidecar: TravelPriceSidecar):
        self.sidecar = sidecar
        self.profiles = option_b_source_profiles()

    def register_profile(
        self,
        scraper_kind: str,
        *,
        source_url: str | None = None,
        resort_id: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> str:
        if scraper_kind not in self.profiles:
            raise KeyError(f"unknown travel source profile: {scraper_kind}")
        record = self.profiles[scraper_kind].to_source_record(source_url=source_url, resort_id=resort_id)
        if overrides:
            metadata = dict(record.get("metadata", {}))
            metadata.update(overrides.pop("metadata", {}) if "metadata" in overrides else {})
            record.update(overrides)
            record["metadata"] = metadata
        return self.sidecar.upsert_source(record)

    def register_option_b_defaults(self) -> dict[str, str]:
        return {key: self.register_profile(key) for key in self.profiles}

    def source_manifest(self) -> dict[str, Any]:
        return {
            "version": OPTION_B_REGISTRY_VERSION,
            "profiles": {key: profile.to_dict() for key, profile in self.profiles.items()},
            "invariant": "scrapers collect raw evidence; sidecar stores exact truth; VSA stores semantic pointers",
        }

