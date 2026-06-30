"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, travel_extractors, travel_source_registry, collections.abc, typing, pathlib, travel_price_sidecar, dataclasses
FUNCTIONS: to_dict, __init__, ingest_option_b_record, ingest_option_b_records, ingest_option_b_file
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from travel_extractors import NormalizedTravelRecord, extract_option_b_record
from travel_price_sidecar import TravelPriceSidecar
from travel_source_registry import TravelSourceRegistry

TRAVEL_SCRAPER_CORE_VERSION = "AURA_TRAVEL_SCRAPER_CORE_V1"


@dataclass(frozen=True)
class TravelIngestResult:
    resort_id: str
    source_id: str
    snapshot_id: str
    price_ids: tuple[str, ...] = ()
    room_type_ids: tuple[str, ...] = ()
    rate_plan_ids: tuple[str, ...] = ()
    media_asset_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    normalized: NormalizedTravelRecord | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TRAVEL_SCRAPER_CORE_VERSION,
            "resort_id": self.resort_id,
            "source_id": self.source_id,
            "snapshot_id": self.snapshot_id,
            "price_ids": list(self.price_ids),
            "room_type_ids": list(self.room_type_ids),
            "rate_plan_ids": list(self.rate_plan_ids),
            "media_asset_ids": list(self.media_asset_ids),
            "warnings": list(self.warnings),
        }


class TravelScraperCore:
    def __init__(self, sidecar: TravelPriceSidecar, registry: TravelSourceRegistry | None = None):
        self.sidecar = sidecar
        self.registry = registry or TravelSourceRegistry(sidecar)

    def ingest_option_b_record(
        self,
        record: dict[str, Any],
        *,
        scraper_kind: str,
        source_url: str | None = None,
        allow_unreviewed: bool = True,
    ) -> TravelIngestResult:
        profile = self.registry.profiles[scraper_kind]
        if profile.allow_state == "denied" and not allow_unreviewed:
            raise PermissionError(f"source profile is denied: {scraper_kind}")
        self.sidecar.conn.execute("SAVEPOINT ingest_record")
        savepoint_active = True
        try:
            effective_source_url = source_url or record.get("source_url") or record.get("url")
            source_id = self.registry.register_profile(
                scraper_kind,
                source_url=effective_source_url,
                overrides={
                    "allow_state": profile.allow_state,
                    "metadata": {"ingest_core": TRAVEL_SCRAPER_CORE_VERSION},
                },
            )
            raw_payload = json.dumps(record, sort_keys=True, ensure_ascii=True, indent=2)
            snapshot = self.sidecar.record_raw_snapshot(
                source_id=source_id,
                url=effective_source_url,
                content=raw_payload,
                parser_version=profile.parser_version,
                http_status=record.get("http_status"),
                metadata={"scraper_kind": scraper_kind, "ingest_core": TRAVEL_SCRAPER_CORE_VERSION},
            )
            normalized = extract_option_b_record(
                record,
                profile=profile,
                source_id=source_id,
                snapshot_id=snapshot["snapshot_id"],
            )
            resort_id = self.sidecar.upsert_resort(normalized.resort)
            existing_source = self.sidecar.conn.execute(
                "SELECT metadata_json FROM resort_sources WHERE source_id = ?", (source_id,)
            ).fetchone()
            existing_metadata = {}
            if existing_source and existing_source["metadata_json"]:
                existing_metadata = json.loads(existing_source["metadata_json"])
            merged_metadata = {**existing_metadata, **normalized.snapshot_metadata}
            source_dict = {
                **normalized.source,
                "resort_id": resort_id,
                "allow_state": profile.allow_state,
                "terms_status": profile.terms_status,
                "robots_allowed": profile.robots_allowed,
                "priority": profile.priority,
                "rate_limit_seconds": profile.rate_limit_seconds,
                "metadata": merged_metadata,
            }
            if effective_source_url and "url" not in normalized.source:
                source_dict["url"] = effective_source_url
            self.sidecar.upsert_source(source_dict)
            room_ids = [self.sidecar.upsert_room_type(dict(item, resort_id=resort_id)) for item in normalized.room_types]
            rate_ids = [self.sidecar.upsert_rate_plan(dict(item, resort_id=resort_id)) for item in normalized.rate_plans]
            price_ids = []
            for price in normalized.price_observations:
                enriched = dict(price, resort_id=resort_id)
                if not enriched.get("room_type_id") and len(room_ids) == 1:
                    enriched["room_type_id"] = room_ids[0]
                if not enriched.get("rate_plan_id") and len(rate_ids) == 1:
                    enriched["rate_plan_id"] = rate_ids[0]
                price_ids.append(self.sidecar.insert_price_observation(enriched))
            media_ids = [self.sidecar.upsert_media_asset(dict(item, resort_id=resort_id)) for item in normalized.media_assets]
            self.sidecar.write_resort_segments(
                resort_id=resort_id,
                semantic_metadata=normalized.semantic_metadata,
                deterministic_truth=normalized.deterministic_truth,
                source_id=source_id,
                snapshot_id=snapshot["snapshot_id"],
            )
            warnings: list[str] = []
            if not price_ids:
                warnings.append("no price observations extracted")
            if profile.allow_state == "operator_review_required":
                warnings.append("source compliance requires operator review")
            result = TravelIngestResult(
                resort_id=resort_id,
                source_id=source_id,
                snapshot_id=snapshot["snapshot_id"],
                price_ids=tuple(price_ids),
                room_type_ids=tuple(room_ids),
                rate_plan_ids=tuple(rate_ids),
                media_asset_ids=tuple(media_ids),
                warnings=tuple(warnings),
                normalized=normalized,
            )
            self.sidecar.conn.execute("RELEASE SAVEPOINT ingest_record")
            savepoint_active = False
            self.sidecar.commit()
            return result
        except Exception:
            if savepoint_active:
                self.sidecar.conn.execute("ROLLBACK TO SAVEPOINT ingest_record")
                self.sidecar.conn.execute("RELEASE SAVEPOINT ingest_record")
            raise

    def ingest_option_b_records(
        self,
        records: Iterable[dict[str, Any]],
        *,
        scraper_kind: str,
        source_url: str | None = None,
    ) -> list[TravelIngestResult]:
        return [self.ingest_option_b_record(record, scraper_kind=scraper_kind, source_url=source_url) for record in records]

    def ingest_option_b_file(self, path: str | Path, *, scraper_kind: str) -> list[TravelIngestResult]:
        source_path = Path(path)
        text = source_path.read_text(encoding="utf-8")
        if source_path.suffix.lower() == ".jsonl":
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            payload = json.loads(text)
            records = payload if isinstance(payload, list) else [payload]
        return self.ingest_option_b_records(records, scraper_kind=scraper_kind, source_url=str(source_path))
