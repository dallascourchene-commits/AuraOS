"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa908-[Q-SYS:TRAVEL_OPTION_B_EXTRACTOR]
DIKWP_TIER: KNOWLEDGE
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Evidence-to-Sidecar Normalization)
DEPENDENCIES: dataclasses, datetime, hashlib, json, typing
FUNCTIONS: NormalizedTravelRecord, extract_option_b_record
SYNOPSIS: Normalizes local JSON output from Option B GitHub scrapers into exact deterministic sidecar fields and semantic VSA metadata fields without storing money in vectors.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from travel_price_sidecar import money_to_minor
from travel_source_registry import TravelSourceProfile

OPTION_B_EXTRACTOR_VERSION = "AURA_TRAVEL_OPTION_B_EXTRACTOR_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: Any, *, size: int = 8) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


def _first(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.replace("|", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = [value]
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _coordinates(record: dict[str, Any]) -> dict[str, float | None]:
    coords = _first(record, "coordinates", "geo", default={})
    if not isinstance(coords, dict):
        coords = {}
    lat = _first(record, "lat", "latitude", default=coords.get("lat") or coords.get("latitude"))
    lng = _first(record, "lng", "longitude", "lon", default=coords.get("lng") or coords.get("longitude") or coords.get("lon"))
    return {"lat": float(lat) if lat not in (None, "") else None, "lng": float(lng) if lng not in (None, "") else None}


def _slug(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    return "_".join(part for part in clean.split("_") if part) or "unknown"


def _price_items(record: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("calendar_prices", "prices", "offers", "price_observations", "rate_options"):
        value = record.get(key)
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, dict)]
    if any(key in record for key in ("checkin_date", "checkout_date", "total_price", "nightly_price", "baseline_seasonal_price")):
        return [record]
    return []


@dataclass(frozen=True)
class NormalizedTravelRecord:
    resort: dict[str, Any]
    source: dict[str, Any]
    snapshot_metadata: dict[str, Any]
    semantic_metadata: dict[str, Any]
    deterministic_truth: dict[str, Any]
    room_types: list[dict[str, Any]] = field(default_factory=list)
    rate_plans: list[dict[str, Any]] = field(default_factory=list)
    price_observations: list[dict[str, Any]] = field(default_factory=list)
    media_assets: list[dict[str, Any]] = field(default_factory=list)

    def semantic_tags(self) -> list[str]:
        tags: list[str] = []
        for key in ("climate_zone", "pacing_profile", "activities", "amenities", "seasonal", "locations"):
            tags.extend(_as_list(self.semantic_metadata.get(key)))
        return _as_list(tags)


def extract_option_b_record(
    record: dict[str, Any],
    *,
    profile: TravelSourceProfile,
    source_id: str,
    snapshot_id: str,
    observed_at: str | None = None,
) -> NormalizedTravelRecord:
    observed = observed_at or _first(record, "observed_at", "last_sync_timestamp", "scraped_at", default=_utc_now())
    name = str(_first(record, "name", "hotel_name", "resort_name", "title", default="Unknown Resort")).strip()
    coords = _coordinates(record)
    resort_id = str(_first(record, "resort_id", "hotel_id", "id", default=f"resort_{_slug(name)}_{_hash_payload([name, coords])}"))
    country = _first(record, "country", "country_name")
    region = _first(record, "region", "province", "state", "destination")
    city = _first(record, "city", "locality")
    amenities = _as_list(_first(record, "amenities", "amenity_list", "structural_amenities"))
    activities = _as_list(_first(record, "activities", "activity_descriptors", "guided_tours", "attractions", "things_to_do"))
    seasonal = _as_list(_first(record, "seasonal", "seasonal_offers", "best_seasons", "weather_tags"))
    locations = _as_list([item for item in (country, region, city, _first(record, "location_text", "address")) if item])
    semantic_metadata = {
        "climate_zone": _first(record, "climate_zone", "weather_zone", default="unknown"),
        "pacing_profile": _first(record, "pacing_profile", "vibe", "traveler_type", default="unknown"),
        "activities": activities,
        "amenities": amenities,
        "seasonal": seasonal,
        "locations": locations,
        "review_tags": _as_list(_first(record, "review_tags", "tags")),
        "source_profile": profile.scraper_kind,
    }
    deterministic_truth = {
        "base_currency": str(_first(record, "base_currency", "currency", default="USD")).upper(),
        "baseline_seasonal_price_minor": money_to_minor(_first(record, "baseline_seasonal_price", "base_price", "price", default=None)),
        "current_api_status": _first(record, "current_api_status", "freshness_status", default="OUTDATED_CACHE_REPLICA"),
        "last_sync_timestamp": observed,
        "source_id": source_id,
        "snapshot_id": snapshot_id,
    }
    room_types = [dict(item, resort_id=resort_id) for item in record.get("room_types", []) if isinstance(item, dict)]
    rate_plans = [dict(item, resort_id=resort_id) for item in record.get("rate_plans", []) if isinstance(item, dict)]
    if not room_types and _first(record, "room_type", "room_name"):
        room_types.append({"resort_id": resort_id, "name": _first(record, "room_type", "room_name")})
    if not rate_plans and _first(record, "rate_plan", "meal_plan", "cancellation_policy"):
        rate_plans.append(
            {
                "resort_id": resort_id,
                "name": _first(record, "rate_plan", default="Standard Rate"),
                "meal_plan": _first(record, "meal_plan"),
                "cancellation_policy": _first(record, "cancellation_policy"),
                "refundable": _first(record, "refundable"),
            }
        )
    price_observations: list[dict[str, Any]] = []
    for offer in _price_items(record):
        checkin = _first(offer, "checkin_date", "check_in", "start_date")
        checkout = _first(offer, "checkout_date", "check_out", "end_date")
        if not checkin or not checkout:
            continue
        price_observations.append(
            {
                "resort_id": resort_id,
                "room_type_id": offer.get("room_type_id"),
                "rate_plan_id": offer.get("rate_plan_id"),
                "checkin_date": str(checkin)[:10],
                "checkout_date": str(checkout)[:10],
                "occupancy_adults": offer.get("occupancy_adults", record.get("occupancy_adults")),
                "occupancy_children": offer.get("occupancy_children", record.get("occupancy_children")),
                "currency": str(_first(offer, "currency", default=deterministic_truth["base_currency"])).upper(),
                "nightly_price": _first(offer, "nightly_price", "nightly_rate"),
                "total_price": _first(offer, "total_price", "package_price", "price"),
                "taxes_fees": _first(offer, "taxes_fees", "taxes_and_fees"),
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "observed_at": observed,
                "parser_version": profile.parser_version,
                "freshness_status": _first(offer, "freshness_status", default="fresh"),
                "booking_url": _first(offer, "booking_url", "url", default=_first(record, "booking_url", "url")),
                "confidence": float(_first(offer, "confidence", default=0.9)),
                "provenance": {
                    "extractor_version": OPTION_B_EXTRACTOR_VERSION,
                    "parser_version": profile.parser_version,
                    "source_profile": profile.scraper_kind,
                    "source_url": _first(record, "source_url", "url"),
                    "snapshot_id": snapshot_id,
                },
            }
        )
    media_assets = []
    for item in record.get("media_assets", []) or record.get("media", []) or []:
        if isinstance(item, dict):
            media_assets.append(dict(item, resort_id=resort_id))
    if record.get("local_splat_path"):
        media_assets.append(
            {
                "resort_id": resort_id,
                "asset_type": "gaussian_splat",
                "title": f"{name} local splat",
                "local_path": record["local_splat_path"],
                "rights_status": record.get("media_rights_status", "unknown"),
            }
        )
    resort = {
        "resort_id": resort_id,
        "name": name,
        "brand": _first(record, "brand", "parent_chain", "chain"),
        "country": country,
        "region": region,
        "city": city,
        "address": _first(record, "address", "location_text"),
        "coordinates": coords,
        "star_rating": _first(record, "star_rating", "rating"),
        "official_url": _first(record, "official_url", "website"),
    }
    source = {
        "source_id": source_id,
        "source_type": profile.source_type,
        "scraper_kind": profile.scraper_kind,
        "source_url": _first(record, "source_url", "url"),
        "repo": profile.repo,
    }
    snapshot_metadata = {
        "extractor_version": OPTION_B_EXTRACTOR_VERSION,
        "parser_version": profile.parser_version,
        "expected_metadata": list(profile.expected_metadata),
    }
    return NormalizedTravelRecord(
        resort=resort,
        source=source,
        snapshot_metadata=snapshot_metadata,
        semantic_metadata=semantic_metadata,
        deterministic_truth=deterministic_truth,
        room_types=room_types,
        rate_plans=rate_plans,
        price_observations=price_observations,
        media_assets=media_assets,
    )
