from datetime import datetime, timedelta, timezone
import json

import pytest

from travel_media_assets import TravelMediaAssetRegistry
from travel_package_arena import TravelPackageArena
from travel_price_sidecar import TravelPriceSidecar
from travel_price_verifier import TravelPriceVerifier
from travel_scraper_core import TravelScraperCore
from travel_vsa_pointer_index import TravelVSAPointerIndex, reject_exact_price_payload


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sample_option_b_record() -> dict:
    return {
        "hotel_id": "expedia_cancun_001",
        "hotel_name": "Example Reef Resort",
        "parent_chain": "Example Collection",
        "country": "Mexico",
        "region": "Quintana Roo",
        "city": "Cancun",
        "coordinates": {"lat": 21.0963, "lng": -86.7754},
        "climate_zone": "Equatorial Marine",
        "pacing_profile": "Family beach with moderate adventure",
        "activities": ["Reef Diving", "Kids Club", "Snorkeling"],
        "amenities": ["All-Inclusive Dining", "Private Beach Front", "Pool"],
        "seasonal": ["February sun", "winter escape"],
        "source_url": "https://example.test/hotel/example-reef",
        "observed_at": _now(),
        "room_types": [{"name": "Ocean View Double", "capacity_adults": 2, "capacity_children": 2}],
        "rate_plans": [{"name": "Refundable All Inclusive", "meal_plan": "all_inclusive", "refundable": True}],
        "calendar_prices": [
            {
                "checkin_date": "2027-02-12",
                "checkout_date": "2027-02-19",
                "occupancy_adults": 2,
                "occupancy_children": 2,
                "currency": "CAD",
                "nightly_price": "467.78",
                "total_price": "3274.44",
                "taxes_fees": "274.44",
                "booking_url": "https://example.test/book/example-reef",
                "confidence": 0.94,
            }
        ],
        "local_splat_path": "assets/splats/cancun_001.spz",
    }


def test_option_b_ingestion_preserves_raw_snapshot_and_sidecar_segments(tmp_path):
    sidecar = TravelPriceSidecar(tmp_path / "travel")
    core = TravelScraperCore(sidecar)

    result = core.ingest_option_b_record(_sample_option_b_record(), scraper_kind="expedia_hotels")
    price = sidecar.get_price(result.price_ids[0])

    assert result.resort_id == "expedia_cancun_001"
    assert price["total_price_minor"] == 327444
    assert price["nightly_price_minor"] == 46778
    assert price["taxes_fees_minor"] == 27444
    assert price["parser_version"] == "option_b_expedia_hotels_parser_v1"
    snapshot_rows = list((tmp_path / "travel" / "raw_snapshots").glob("**/*.json"))
    assert len(snapshot_rows) == 1
    assert "Example Reef Resort" in snapshot_rows[0].read_text(encoding="utf-8")
    semantic_lines = (tmp_path / "travel" / "segments" / "semantic_metadata.jsonl").read_text(encoding="utf-8")
    truth_lines = (tmp_path / "travel" / "segments" / "deterministic_truth.jsonl").read_text(encoding="utf-8")
    assert "Reef Diving" in semantic_lines
    assert "baseline_seasonal_price_minor" in truth_lines
    sidecar.close()


def test_vsa_pointer_resolves_exact_price_without_storing_money_in_vector_payload(tmp_path):
    sidecar = TravelPriceSidecar(tmp_path / "travel")
    result = TravelScraperCore(sidecar).ingest_option_b_record(_sample_option_b_record(), scraper_kind="expedia_hotels")
    price = sidecar.get_price(result.price_ids[0])
    pointer_index = TravelVSAPointerIndex(sidecar)
    vsa_id = pointer_index.index_price_offer(
        price_id=price["price_id"],
        resort_id=result.resort_id,
        semantic_tags=["family", "beach", "kids club", "february"],
        checkin_date=price["checkin_date"],
        checkout_date=price["checkout_date"],
    )
    pointer = sidecar.resolve_pointer(vsa_id)
    pointer_blob = json.dumps(pointer, sort_keys=True)

    assert pointer["sidecar_table"] == "price_observations"
    assert pointer["sidecar_key"] == price["price_id"]
    assert "327444" not in pointer_blob
    assert "total_price_minor" not in pointer_blob
    candidate = TravelPackageArena(sidecar).build_candidate_from_vsa_price(
        vsa_id,
        traveler_intent={"party": "family of 4", "budget_minor": 600000, "month": "February"},
    )
    assert candidate.exact_price["total_price_minor"] == 327444
    assert candidate.status == "verified_pending_human_approval"
    assert {item["boundary_type"] for item in candidate.boundary_contracts} == {
        "price_freshness",
        "booking_payment",
        "legal_travel",
    }
    sidecar.close()


def test_stale_price_is_blocked_before_package_display(tmp_path):
    record = _sample_option_b_record()
    record["observed_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    sidecar = TravelPriceSidecar(tmp_path / "travel")
    result = TravelScraperCore(sidecar).ingest_option_b_record(record, scraper_kind="expedia_hotels")
    price = sidecar.get_price(result.price_ids[0])
    verifier = TravelPriceVerifier(max_age_hours=24)

    verdict = verifier.verify_price(price)

    assert verdict.approved is False
    assert "price_observation_stale" in verdict.blockers
    sidecar.close()


def test_vsa_rejects_exact_price_payloads():
    with pytest.raises(ValueError, match="exact price field"):
        reject_exact_price_payload({"semantic_tags": ["beach"], "total_price_minor": 327444})


def test_media_registry_accepts_gaussian_splat_references(tmp_path):
    sidecar = TravelPriceSidecar(tmp_path / "travel")
    sidecar.upsert_resort({"resort_id": "resort_media_001", "name": "Media Resort"})
    registry = TravelMediaAssetRegistry(sidecar)

    asset_id = registry.register_gaussian_splat(
        resort_id="resort_media_001",
        local_path="assets/splats/media_001.spz",
        title="Media Resort walkthrough",
    )
    contract = registry.premium_media_contract(resort_id="resort_media_001", asset_id=asset_id)

    assert contract["requires_rights_review"] is True
    assert contract["premium_listing_surface"] == "360/video/gaussian_splat"
    sidecar.close()

