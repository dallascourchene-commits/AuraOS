"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa90c-[Q-SYS:TRAVEL_PACKAGE_ARENA]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Planner-Verifier Travel Arena)
DEPENDENCIES: dataclasses, hashlib, json, typing, aura_liquid_planning_arena, travel_price_sidecar, travel_price_verifier, travel_vsa_pointer_index
FUNCTIONS: TravelPackageArena, TravelPackageCandidate
SYNOPSIS: Sidecar-aware Travel Arena that resolves VSA semantic pointers into exact price records, verifies freshness/provenance, attaches BoundaryContracts, and rejects stale or vector-only prices.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from aura_liquid_planning_arena import BoundaryContract, TravelArenaAdapter
from travel_price_sidecar import TravelPriceSidecar
from travel_price_verifier import TravelPriceVerifier
from travel_vsa_pointer_index import TravelVSAPointerIndex

TRAVEL_PACKAGE_ARENA_VERSION = "AURA_TRAVEL_PACKAGE_ARENA_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: Any, *, size: int = 8) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


@dataclass(frozen=True)
class TravelPackageCandidate:
    package_id: str
    traveler_intent: dict[str, Any]
    vsa_id: str
    resort: dict[str, Any] | None
    exact_price: dict[str, Any]
    semantic_match: dict[str, Any]
    verification: dict[str, Any]
    boundary_contracts: tuple[dict[str, Any], ...]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TRAVEL_PACKAGE_ARENA_VERSION,
            "package_id": self.package_id,
            "traveler_intent": dict(self.traveler_intent),
            "vsa_id": self.vsa_id,
            "resort": self.resort,
            "exact_price": dict(self.exact_price),
            "semantic_match": dict(self.semantic_match),
            "verification": dict(self.verification),
            "boundary_contracts": list(self.boundary_contracts),
            "status": self.status,
        }


class TravelPackageArena:
    def __init__(
        self,
        sidecar: TravelPriceSidecar,
        *,
        pointer_index: TravelVSAPointerIndex | None = None,
        verifier: TravelPriceVerifier | None = None,
        adapter: TravelArenaAdapter | None = None,
    ):
        self.sidecar = sidecar
        self.pointer_index = pointer_index or TravelVSAPointerIndex(sidecar)
        self.verifier = verifier or TravelPriceVerifier()
        self.adapter = adapter or TravelArenaAdapter()

    def _boundary_contracts(self, *, package_id: str, price: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        common = {
            "domain": "travel",
            "capsule_id": package_id,
            "source_region": {"resort_id": price.get("resort_id"), "price_id": price.get("price_id")},
            "owned_scope": [str(price.get("resort_id")), str(price.get("price_id"))],
            "assumptions": ["sidecar record is exact source of price truth"],
            "required_inputs": ["source_id", "snapshot_id", "observed_at", "parser_version", "freshness_status"],
            "promised_outputs": ["verified package candidate or refusal"],
            "constraints": ["human approval required before booking or payment"],
            "escalation_triggers": ["stale price", "missing tax data", "payment/legal boundary", "booking action requested"],
            "invariant": "VSA retrieves meaning; sidecar retrieves truth; Arena composes packages; verifier blocks stale or invented prices",
        }
        contracts = [
            BoundaryContract.placeholder(
                **common,
                boundary_type="price_freshness",
                external_system="travel_price_sidecar.price_observations",
                metadata={"price_id": price.get("price_id"), "observed_at": price.get("observed_at")},
            ),
            BoundaryContract.placeholder(
                **common,
                boundary_type="booking_payment",
                external_system="human-approved booking/payment system",
                metadata={"requires_human_approval": True},
            ),
            BoundaryContract.placeholder(
                **common,
                boundary_type="legal_travel",
                external_system="visa/terms/cancellation policy review",
                metadata={"requires_policy_review": True},
            ),
        ]
        return tuple(item.to_dict() for item in contracts)

    def build_candidate_from_vsa_price(
        self,
        vsa_id: str,
        *,
        traveler_intent: dict[str, Any],
        match_reason: list[str] | None = None,
    ) -> TravelPackageCandidate:
        pointer = self.sidecar.resolve_pointer(vsa_id)
        if not pointer:
            raise ValueError("vector_only_price_pointer")
        if pointer.get("sidecar_table") != "price_observations":
            raise ValueError("vsa_pointer_does_not_resolve_to_price")
        price = self.pointer_index.resolve_exact_price(vsa_id)
        verification = self.verifier.verify_price(price)
        if not verification.approved:
            raise ValueError(f"price_verification_failed:{','.join(verification.blockers)}")
        assert price is not None
        resort = self.sidecar.get_resort(str(price["resort_id"]))
        package_id = f"pkg_{_hash_payload([vsa_id, traveler_intent, price.get('price_id')])}"
        exact_price = {
            "price_id": price["price_id"],
            "checkin_date": price["checkin_date"],
            "checkout_date": price["checkout_date"],
            "nights": price["nights"],
            "currency": price["currency"],
            "nightly_price_minor": price.get("nightly_price_minor"),
            "total_price_minor": price.get("total_price_minor"),
            "taxes_fees_minor": price.get("taxes_fees_minor"),
            "observed_at": price["observed_at"],
            "freshness_status": price["freshness_status"],
            "source_id": price["source_id"],
            "snapshot_id": price["snapshot_id"],
            "source_confidence": price.get("confidence"),
            "requires_live_recheck_before_booking": True,
        }
        semantic_match = {
            "vsa_id": vsa_id,
            "entity_type": pointer.get("entity_type"),
            "semantic_tags": pointer.get("semantic_tags", []),
            "match_reason": list(match_reason or pointer.get("semantic_tags", []) or []),
        }
        return TravelPackageCandidate(
            package_id=package_id,
            traveler_intent=traveler_intent,
            vsa_id=vsa_id,
            resort=resort,
            exact_price=exact_price,
            semantic_match=semantic_match,
            verification=verification.to_dict(),
            boundary_contracts=self._boundary_contracts(package_id=package_id, price=price),
            status="verified_pending_human_approval",
        )

    def arena_action_for_intent(self, traveler_intent: dict[str, Any]) -> dict[str, Any]:
        action = self.adapter.action_capsule_from_intent(
            objective=str(traveler_intent.get("objective") or "Build verified travel package options."),
            capsule_id=str(traveler_intent.get("capsule_id") or f"TRAVEL-{_hash_payload(traveler_intent)}"),
            target=traveler_intent,
            constraints=["exact sidecar price required", "human approval before booking/payment"],
        )
        return action.to_dict()

