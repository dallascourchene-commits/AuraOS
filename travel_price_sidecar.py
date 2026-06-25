"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa906-[Q-SYS:TRAVEL_SIDECAR]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Exact Travel Truth Sidecar)
DEPENDENCIES: dataclasses, datetime, decimal, hashlib, json, os, pathlib, sqlite3, typing
FUNCTIONS: TravelSidecarPaths, TravelPriceSidecar, money_to_minor, resolve_travel_data_root
SYNOPSIS: Local-disk travel sidecar for immutable raw scraper snapshots, exact price/date truth, JSONL semantic segments, and VSA pointer resolution. VSA retrieves meaning; sidecar retrieves truth.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any

TRAVEL_SIDECAR_VERSION = "AURA_TRAVEL_PRICE_SIDECAR_V1"
DEFAULT_TRAVEL_DATA_ROOT = "Aura_Memory/travel_sidecar"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_json_dumps(payload).encode("utf-8"), digest_size=size).hexdigest()


def _slug(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value or "").strip())
    return "_".join(part for part in clean.split("_") if part) or "unknown"


def resolve_travel_data_root(root: str | Path | None = None) -> Path:
    return Path(root or os.environ.get("AURA_TRAVEL_DATA_ROOT") or DEFAULT_TRAVEL_DATA_ROOT)


def money_to_minor(value: Any, *, already_minor: bool = False) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("money values cannot be booleans")
    if isinstance(value, int):
        if already_minor:
            return value
        return value * 100
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money value: {value!r}") from exc
    if already_minor:
        return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _date_nights(checkin: Any, checkout: Any) -> int | None:
    start = _parse_date(checkin)
    end = _parse_date(checkout)
    if not start or not end:
        return None
    nights = (end.date() - start.date()).days
    return nights if nights > 0 else None


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in ("metadata_json", "provenance_json", "semantic_tags_json"):
        if item.get(key):
            target_key = key[:-5] if key.endswith("_json") else key
            item[target_key] = json.loads(item[key])
    return item


@dataclass(frozen=True)
class TravelSidecarPaths:
    root: Path
    db_path: Path
    raw_snapshots_dir: Path
    segments_dir: Path
    deterministic_truth_jsonl: Path
    semantic_metadata_jsonl: Path
    vsa_pointer_jsonl: Path

    @classmethod
    def for_root(cls, root: str | Path | None = None) -> TravelSidecarPaths:
        base = resolve_travel_data_root(root)
        segments = base / "segments"
        return cls(
            root=base,
            db_path=base / "travel_sidecar.sqlite",
            raw_snapshots_dir=base / "raw_snapshots",
            segments_dir=segments,
            deterministic_truth_jsonl=segments / "deterministic_truth.jsonl",
            semantic_metadata_jsonl=segments / "semantic_metadata.jsonl",
            vsa_pointer_jsonl=segments / "vsa_pointers.jsonl",
        )


class TravelPriceSidecar:
    def __init__(self, root: str | Path | None = None):
        self.paths = TravelSidecarPaths.for_root(root)
        self._ensure_layout()
        self.conn = sqlite3.connect(self.paths.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def _ensure_layout(self) -> None:
        self.paths.raw_snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.paths.segments_dir.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS resorts (
                resort_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT,
                country TEXT,
                region TEXT,
                city TEXT,
                address TEXT,
                latitude REAL,
                longitude REAL,
                star_rating REAL,
                official_url TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS resort_sources (
                source_id TEXT PRIMARY KEY,
                resort_id TEXT,
                source_type TEXT NOT NULL,
                scraper_kind TEXT,
                source_url TEXT,
                repo TEXT,
                robots_allowed INTEGER,
                terms_status TEXT,
                allow_state TEXT DEFAULT 'unknown',
                priority INTEGER DEFAULT 0,
                rate_limit_seconds REAL,
                last_checked_at TEXT,
                metadata_json TEXT
            );
            CREATE TABLE IF NOT EXISTS raw_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                url TEXT,
                content_hash TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                http_status INTEGER,
                parser_version TEXT,
                metadata_json TEXT
            );
            CREATE TABLE IF NOT EXISTS room_types (
                room_type_id TEXT PRIMARY KEY,
                resort_id TEXT NOT NULL,
                name TEXT NOT NULL,
                capacity_adults INTEGER,
                capacity_children INTEGER,
                bed_config TEXT,
                view_type TEXT,
                amenities_json TEXT
            );
            CREATE TABLE IF NOT EXISTS rate_plans (
                rate_plan_id TEXT PRIMARY KEY,
                resort_id TEXT NOT NULL,
                name TEXT,
                meal_plan TEXT,
                refundable INTEGER,
                cancellation_policy TEXT,
                inclusions_json TEXT
            );
            CREATE TABLE IF NOT EXISTS price_observations (
                price_id TEXT PRIMARY KEY,
                resort_id TEXT NOT NULL,
                room_type_id TEXT,
                rate_plan_id TEXT,
                checkin_date TEXT NOT NULL,
                checkout_date TEXT NOT NULL,
                nights INTEGER NOT NULL,
                occupancy_adults INTEGER,
                occupancy_children INTEGER,
                currency TEXT NOT NULL,
                nightly_price_minor INTEGER,
                total_price_minor INTEGER,
                taxes_fees_minor INTEGER,
                source_id TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                parser_version TEXT,
                freshness_status TEXT DEFAULT 'fresh',
                booking_url TEXT,
                confidence REAL DEFAULT 1.0,
                provenance_json TEXT
            );
            CREATE TABLE IF NOT EXISTS vsa_entity_pointers (
                vsa_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                sidecar_table TEXT NOT NULL,
                sidecar_key TEXT NOT NULL,
                semantic_tags_json TEXT,
                vector_hash TEXT,
                exact_lookup_required INTEGER DEFAULT 1,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS media_assets (
                asset_id TEXT PRIMARY KEY,
                resort_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                title TEXT,
                storage_url TEXT,
                local_path TEXT,
                rights_status TEXT,
                created_at TEXT
            );
            """
        )
        columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(price_observations)").fetchall()
        }
        if "parser_version" not in columns:
            self.conn.execute("ALTER TABLE price_observations ADD COLUMN parser_version TEXT")
        self.conn.commit()

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_json_dumps(record) + "\n")

    def append_deterministic_truth(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.paths.deterministic_truth_jsonl, record)

    def append_semantic_metadata(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.paths.semantic_metadata_jsonl, record)

    def append_vsa_pointer(self, record: dict[str, Any]) -> None:
        self.append_jsonl(self.paths.vsa_pointer_jsonl, record)

    def upsert_resort(self, resort: dict[str, Any]) -> str:
        now = _utc_now()
        name = str(resort.get("name") or "Unknown Resort").strip()
        resort_id = str(resort.get("resort_id") or f"resort_{_slug(name)}_{_hash_payload(resort)[:8]}")
        coordinates = resort.get("coordinates") or {}
        latitude = resort.get("latitude", coordinates.get("lat") if isinstance(coordinates, dict) else None)
        longitude = resort.get("longitude", coordinates.get("lng") if isinstance(coordinates, dict) else None)
        self.conn.execute(
            """
            INSERT INTO resorts (
                resort_id, name, brand, country, region, city, address,
                latitude, longitude, star_rating, official_url, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resort_id) DO UPDATE SET
                name=excluded.name,
                brand=excluded.brand,
                country=excluded.country,
                region=excluded.region,
                city=excluded.city,
                address=excluded.address,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                star_rating=excluded.star_rating,
                official_url=excluded.official_url,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                resort_id,
                name,
                resort.get("brand") or resort.get("parent_chain"),
                resort.get("country"),
                resort.get("region"),
                resort.get("city"),
                resort.get("address"),
                latitude,
                longitude,
                resort.get("star_rating"),
                resort.get("official_url"),
                resort.get("status", "active"),
                resort.get("created_at", now),
                now,
            ),
        )
        return resort_id

    def upsert_room_type(self, room: dict[str, Any]) -> str:
        resort_id = str(room["resort_id"])
        name = str(room.get("name") or "Standard Room").strip()
        room_type_id = str(room.get("room_type_id") or f"room_{_slug(resort_id)}_{_hash_payload([resort_id, name])[:10]}")
        self.conn.execute(
            """
            INSERT INTO room_types (
                room_type_id, resort_id, name, capacity_adults, capacity_children,
                bed_config, view_type, amenities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(room_type_id) DO UPDATE SET
                resort_id=excluded.resort_id,
                name=excluded.name,
                capacity_adults=excluded.capacity_adults,
                capacity_children=excluded.capacity_children,
                bed_config=excluded.bed_config,
                view_type=excluded.view_type,
                amenities_json=excluded.amenities_json
            """,
            (
                room_type_id,
                resort_id,
                name,
                room.get("capacity_adults"),
                room.get("capacity_children"),
                room.get("bed_config"),
                room.get("view_type"),
                _json_dumps(room.get("amenities", [])),
            ),
        )
        return room_type_id

    def upsert_rate_plan(self, rate_plan: dict[str, Any]) -> str:
        resort_id = str(rate_plan["resort_id"])
        name = str(rate_plan.get("name") or "Standard Rate").strip()
        rate_plan_id = str(rate_plan.get("rate_plan_id") or f"rate_{_slug(resort_id)}_{_hash_payload([resort_id, name])[:10]}")
        refundable = rate_plan.get("refundable")
        self.conn.execute(
            """
            INSERT INTO rate_plans (
                rate_plan_id, resort_id, name, meal_plan, refundable,
                cancellation_policy, inclusions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rate_plan_id) DO UPDATE SET
                resort_id=excluded.resort_id,
                name=excluded.name,
                meal_plan=excluded.meal_plan,
                refundable=excluded.refundable,
                cancellation_policy=excluded.cancellation_policy,
                inclusions_json=excluded.inclusions_json
            """,
            (
                rate_plan_id,
                resort_id,
                name,
                rate_plan.get("meal_plan"),
                int(bool(refundable)) if refundable is not None else None,
                rate_plan.get("cancellation_policy"),
                _json_dumps(rate_plan.get("inclusions", [])),
            ),
        )
        return rate_plan_id

    def upsert_source(self, source: dict[str, Any]) -> str:
        if source.get("source_id"):
            source_id = str(source["source_id"])
        else:
            identity_keys = {
                "source_type": source.get("source_type"),
                "scraper_kind": source.get("scraper_kind"),
                "source_url": source.get("source_url"),
                "repo": source.get("repo"),
                "resort_id": source.get("resort_id"),
            }
            source_id = f"source_{_hash_payload(identity_keys)[:12]}"
        self.conn.execute(
            """
            INSERT INTO resort_sources (
                source_id, resort_id, source_type, scraper_kind, source_url, repo,
                robots_allowed, terms_status, allow_state, priority,
                rate_limit_seconds, last_checked_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                resort_id=excluded.resort_id,
                source_type=excluded.source_type,
                scraper_kind=excluded.scraper_kind,
                source_url=excluded.source_url,
                repo=excluded.repo,
                robots_allowed=excluded.robots_allowed,
                terms_status=excluded.terms_status,
                allow_state=excluded.allow_state,
                priority=excluded.priority,
                rate_limit_seconds=excluded.rate_limit_seconds,
                last_checked_at=excluded.last_checked_at,
                metadata_json=excluded.metadata_json
            """,
            (
                source_id,
                source.get("resort_id"),
                source.get("source_type", "option_b_scraper_output"),
                source.get("scraper_kind"),
                source.get("source_url"),
                source.get("repo"),
                int(bool(source.get("robots_allowed"))) if source.get("robots_allowed") is not None else None,
                source.get("terms_status"),
                source.get("allow_state", "unknown"),
                int(source.get("priority", 0)),
                source.get("rate_limit_seconds"),
                source.get("last_checked_at") or _utc_now(),
                _json_dumps(source.get("metadata", {})),
            ),
        )
        return source_id

    def record_raw_snapshot(
        self,
        *,
        source_id: str,
        url: str | None,
        content: str | bytes,
        parser_version: str,
        http_status: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fetched_at = _utc_now()
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
        content_hash = hashlib.sha256(raw).hexdigest()
        snapshot_id = f"snap_{_hash_payload([source_id, url, content_hash, fetched_at])[:16]}"
        day_dir = self.paths.raw_snapshots_dir / fetched_at[:10]
        day_dir.mkdir(parents=True, exist_ok=True)
        storage_path = day_dir / f"{snapshot_id}.json"
        storage_path.write_bytes(raw)
        row = {
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "fetched_at": fetched_at,
            "url": url,
            "content_hash": content_hash,
            "storage_path": str(storage_path),
            "http_status": http_status,
            "parser_version": parser_version,
            "metadata": dict(metadata or {}),
        }
        self.conn.execute(
            """
            INSERT INTO raw_snapshots (
                snapshot_id, source_id, fetched_at, url, content_hash,
                storage_path, http_status, parser_version, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                source_id,
                fetched_at,
                url,
                content_hash,
                str(storage_path),
                http_status,
                parser_version,
                _json_dumps(row["metadata"]),
            ),
        )
        return row

    def insert_price_observation(self, observation: dict[str, Any]) -> str:
        required = ("resort_id", "checkin_date", "checkout_date", "currency", "source_id", "snapshot_id", "observed_at")
        missing = [key for key in required if not observation.get(key)]
        if missing:
            raise ValueError(f"missing price observation fields: {', '.join(missing)}")
        nightly = (
            money_to_minor(observation.get("nightly_price_minor"), already_minor=True)
            if "nightly_price_minor" in observation
            else money_to_minor(observation.get("nightly_price"))
        )
        total = (
            money_to_minor(observation.get("total_price_minor"), already_minor=True)
            if "total_price_minor" in observation
            else money_to_minor(observation.get("total_price"))
        )
        taxes = (
            money_to_minor(observation.get("taxes_fees_minor"), already_minor=True)
            if "taxes_fees_minor" in observation
            else money_to_minor(observation.get("taxes_fees"))
        )
        if nightly is None and total is None:
            raise ValueError("price observation requires nightly_price or total_price")
        derived_nights = _date_nights(observation["checkin_date"], observation["checkout_date"])
        explicit_nights = observation.get("nights")
        if derived_nights is None:
            raise ValueError(f"cannot compute stay duration from checkin_date={observation.get('checkin_date')} and checkout_date={observation.get('checkout_date')}")
        if explicit_nights is not None:
            explicit_nights = int(explicit_nights)
            if explicit_nights != derived_nights:
                raise ValueError(f"nights field ({explicit_nights}) does not match computed duration ({derived_nights} nights)")
        nights = derived_nights
        price_id = str(
            observation.get("price_id")
            or f"price_{_hash_payload([observation.get('resort_id'), observation.get('checkin_date'), observation.get('checkout_date'), total, nightly, observation.get('source_id')])[:16]}"
        )
        self.conn.execute(
            """
            INSERT INTO price_observations (
                price_id, resort_id, room_type_id, rate_plan_id, checkin_date, checkout_date,
                nights, occupancy_adults, occupancy_children, currency, nightly_price_minor,
                total_price_minor, taxes_fees_minor, source_id, snapshot_id, observed_at,
                parser_version, freshness_status, booking_url, confidence, provenance_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(price_id) DO UPDATE SET
                resort_id=excluded.resort_id,
                room_type_id=excluded.room_type_id,
                rate_plan_id=excluded.rate_plan_id,
                checkin_date=excluded.checkin_date,
                checkout_date=excluded.checkout_date,
                nights=excluded.nights,
                occupancy_adults=excluded.occupancy_adults,
                occupancy_children=excluded.occupancy_children,
                currency=excluded.currency,
                nightly_price_minor=excluded.nightly_price_minor,
                total_price_minor=excluded.total_price_minor,
                taxes_fees_minor=excluded.taxes_fees_minor,
                source_id=excluded.source_id,
                snapshot_id=excluded.snapshot_id,
                observed_at=excluded.observed_at,
                parser_version=excluded.parser_version,
                freshness_status=excluded.freshness_status,
                booking_url=excluded.booking_url,
                confidence=excluded.confidence,
                provenance_json=excluded.provenance_json
            """,
            (
                price_id,
                observation["resort_id"],
                observation.get("room_type_id"),
                observation.get("rate_plan_id"),
                str(observation["checkin_date"])[:10],
                str(observation["checkout_date"])[:10],
                nights,
                observation.get("occupancy_adults"),
                observation.get("occupancy_children"),
                str(observation["currency"]).upper(),
                nightly,
                total,
                taxes,
                observation["source_id"],
                observation["snapshot_id"],
                observation["observed_at"],
                observation.get("parser_version") or observation.get("provenance", {}).get("parser_version"),
                observation.get("freshness_status", "fresh"),
                observation.get("booking_url"),
                float(observation.get("confidence", 1.0)),
                _json_dumps(observation.get("provenance", {})),
            ),
        )
        return price_id

    def upsert_vsa_pointer(self, pointer: dict[str, Any]) -> str:
        vsa_id = str(pointer["vsa_id"])
        semantic_tags = pointer.get("semantic_tags", [])
        self.conn.execute(
            """
            INSERT INTO vsa_entity_pointers (
                vsa_id, entity_type, entity_id, sidecar_table, sidecar_key,
                semantic_tags_json, vector_hash, exact_lookup_required, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vsa_id) DO UPDATE SET
                entity_type=excluded.entity_type,
                entity_id=excluded.entity_id,
                sidecar_table=excluded.sidecar_table,
                sidecar_key=excluded.sidecar_key,
                semantic_tags_json=excluded.semantic_tags_json,
                vector_hash=excluded.vector_hash,
                exact_lookup_required=excluded.exact_lookup_required,
                updated_at=excluded.updated_at
            """,
            (
                vsa_id,
                pointer["entity_type"],
                pointer["entity_id"],
                pointer["sidecar_table"],
                pointer["sidecar_key"],
                _json_dumps(semantic_tags),
                pointer.get("vector_hash"),
                int(bool(pointer.get("exact_lookup_required", True))),
                pointer.get("updated_at") or _utc_now(),
            ),
        )
        self.append_vsa_pointer(dict(pointer, semantic_tags=semantic_tags))
        return vsa_id

    def upsert_media_asset(self, asset: dict[str, Any]) -> str:
        asset_id = str(asset.get("asset_id") or f"asset_{_hash_payload(asset)[:14]}")
        self.conn.execute(
            """
            INSERT INTO media_assets (
                asset_id, resort_id, asset_type, title, storage_url,
                local_path, rights_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                resort_id=excluded.resort_id,
                asset_type=excluded.asset_type,
                title=excluded.title,
                storage_url=excluded.storage_url,
                local_path=excluded.local_path,
                rights_status=excluded.rights_status
            """,
            (
                asset_id,
                asset["resort_id"],
                asset.get("asset_type", "image"),
                asset.get("title"),
                asset.get("storage_url"),
                asset.get("local_path"),
                asset.get("rights_status", "unknown"),
                asset.get("created_at") or _utc_now(),
            ),
        )
        return asset_id

    def write_resort_segments(
        self,
        *,
        resort_id: str,
        semantic_metadata: dict[str, Any],
        deterministic_truth: dict[str, Any],
        source_id: str,
        snapshot_id: str,
    ) -> None:
        semantic_record = {
            "version": TRAVEL_SIDECAR_VERSION,
            "segment": "semantic_metadata",
            "resort_id": resort_id,
            "source_id": source_id,
            "snapshot_id": snapshot_id,
            "metadata": dict(semantic_metadata),
            "written_at": _utc_now(),
        }
        truth_record = {
            "version": TRAVEL_SIDECAR_VERSION,
            "segment": "deterministic_truth",
            "resort_id": resort_id,
            "source_id": source_id,
            "snapshot_id": snapshot_id,
            "truth": dict(deterministic_truth),
            "written_at": _utc_now(),
        }
        self.append_semantic_metadata(semantic_record)
        self.append_deterministic_truth(truth_record)

    def get_resort(self, resort_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM resorts WHERE resort_id = ?", (resort_id,)).fetchone()
        return _row_to_dict(row)

    def get_price(self, price_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM price_observations WHERE price_id = ?", (price_id,)).fetchone()
        return _row_to_dict(row)

    def resolve_pointer(self, vsa_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM vsa_entity_pointers WHERE vsa_id = ?", (vsa_id,)).fetchone()
        return _row_to_dict(row)

    def resolve_vsa_price(self, vsa_id: str) -> dict[str, Any] | None:
        pointer = self.resolve_pointer(vsa_id)
        if not pointer or pointer.get("sidecar_table") != "price_observations":
            return None
        return self.get_price(str(pointer["sidecar_key"]))

    def query_prices(
        self,
        *,
        resort_id: str,
        checkin_date: str | None = None,
        checkout_date: str | None = None,
        occupancy_adults: int | None = None,
        occupancy_children: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["resort_id = ?"]
        args: list[Any] = [resort_id]
        for key, value in (
            ("checkin_date", checkin_date),
            ("checkout_date", checkout_date),
            ("occupancy_adults", occupancy_adults),
            ("occupancy_children", occupancy_children),
        ):
            if value is not None:
                clauses.append(f"{key} = ?")
                args.append(value)
        rows = self.conn.execute(
            f"SELECT * FROM price_observations WHERE {' AND '.join(clauses)} ORDER BY observed_at DESC",
            args,
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
