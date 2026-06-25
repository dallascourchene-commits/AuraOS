"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa90a-[Q-SYS:TRAVEL_VSA_POINTERS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Meaning Pointers, Exact Truth Elsewhere)
DEPENDENCIES: dataclasses, hashlib, json, typing, travel_price_sidecar
FUNCTIONS: TravelVSAPointerIndex, make_travel_vsa_id, reject_exact_price_payload
SYNOPSIS: Deterministic VSA-style semantic address registry for Aura Travel. VSA rows store semantic tags and sidecar keys only; exact prices stay in the sidecar.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from travel_price_sidecar import TravelPriceSidecar


TRAVEL_VSA_POINTER_VERSION = "AURA_TRAVEL_VSA_POINTER_V1"
PRICE_FORBIDDEN_KEYS = {
    "price",
    "base_price",
    "baseline_seasonal_price",
    "baseline_seasonal_price_minor",
    "nightly_price",
    "nightly_price_minor",
    "total_price",
    "total_price_minor",
    "taxes_fees",
    "taxes_fees_minor",
    "currency_amount",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    return hashlib.blake2b(_json_dumps(payload).encode("utf-8"), digest_size=size).hexdigest()


def _stable_tags(tags: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags or []:
        text = str(tag).strip().lower()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def reject_exact_price_payload(payload: Any, *, path: str = "payload") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in PRICE_FORBIDDEN_KEYS:
                raise ValueError(f"exact price field cannot be stored in VSA payload: {path}.{key}")
            reject_exact_price_payload(value, path=f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            reject_exact_price_payload(item, path=f"{path}[{index}]")


def make_travel_vsa_id(*, entity_type: str, entity_id: str, semantic_tags: list[str], scope: str = "") -> str:
    tags = _stable_tags(semantic_tags)
    digest = _hash_payload({"entity_type": entity_type, "entity_id": entity_id, "semantic_tags": tags, "scope": scope})
    return f"VSA:travel:{entity_type}:{digest}"


@dataclass(frozen=True)
class TravelVSAPointer:
    vsa_id: str
    entity_type: str
    entity_id: str
    sidecar_table: str
    sidecar_key: str
    semantic_tags: tuple[str, ...]
    vector_hash: str
    exact_lookup_required: bool = True
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TRAVEL_VSA_POINTER_VERSION,
            "vsa_id": self.vsa_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "sidecar_table": self.sidecar_table,
            "sidecar_key": self.sidecar_key,
            "semantic_tags": list(self.semantic_tags),
            "vector_hash": self.vector_hash,
            "exact_lookup_required": self.exact_lookup_required,
            "updated_at": self.updated_at,
        }


class TravelVSAPointerIndex:
    def __init__(self, sidecar: TravelPriceSidecar):
        self.sidecar = sidecar

    def build_pointer(
        self,
        *,
        entity_type: str,
        entity_id: str,
        sidecar_table: str,
        sidecar_key: str,
        semantic_tags: list[str],
        scope: str = "",
        semantic_payload: dict[str, Any] | None = None,
    ) -> TravelVSAPointer:
        payload = dict(semantic_payload or {}, semantic_tags=_stable_tags(semantic_tags))
        reject_exact_price_payload(payload)
        tags = _stable_tags(semantic_tags)
        vsa_id = make_travel_vsa_id(entity_type=entity_type, entity_id=entity_id, semantic_tags=tags, scope=scope)
        vector_hash = _hash_payload({"vsa_id": vsa_id, "semantic_payload": payload})
        return TravelVSAPointer(
            vsa_id=vsa_id,
            entity_type=entity_type,
            entity_id=entity_id,
            sidecar_table=sidecar_table,
            sidecar_key=sidecar_key,
            semantic_tags=tuple(tags),
            vector_hash=vector_hash,
            updated_at=_utc_now(),
        )

    def upsert_pointer(self, pointer: TravelVSAPointer) -> str:
        return self.sidecar.upsert_vsa_pointer(pointer.to_dict())

    def index_resort(self, *, resort_id: str, semantic_metadata: dict[str, Any]) -> str:
        tags: list[str] = []
        for key in ("climate_zone", "pacing_profile", "activities", "amenities", "seasonal", "locations", "review_tags"):
            value = semantic_metadata.get(key)
            if isinstance(value, list):
                tags.extend(str(item) for item in value)
            elif value:
                tags.append(str(value))
        pointer = self.build_pointer(
            entity_type="resort",
            entity_id=resort_id,
            sidecar_table="resorts",
            sidecar_key=resort_id,
            semantic_tags=tags,
            semantic_payload=semantic_metadata,
        )
        return self.upsert_pointer(pointer)

    def index_price_offer(
        self,
        *,
        price_id: str,
        resort_id: str,
        semantic_tags: list[str],
        checkin_date: str | None = None,
        checkout_date: str | None = None,
    ) -> str:
        pointer = self.build_pointer(
            entity_type="price_offer",
            entity_id=price_id,
            sidecar_table="price_observations",
            sidecar_key=price_id,
            semantic_tags=semantic_tags,
            scope=f"{resort_id}:{checkin_date or ''}:{checkout_date or ''}",
            semantic_payload={
                "resort_id": resort_id,
                "checkin_date": checkin_date,
                "checkout_date": checkout_date,
                "tags": semantic_tags,
            },
        )
        return self.upsert_pointer(pointer)

    def resolve_exact_price(self, vsa_id: str) -> dict[str, Any] | None:
        return self.sidecar.resolve_vsa_price(vsa_id)

