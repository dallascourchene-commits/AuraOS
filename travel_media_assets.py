"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f4-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: pathlib, travel_price_sidecar, typing, __future__
FUNCTIONS: __init__, register_asset, register_gaussian_splat, premium_media_contract
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from travel_price_sidecar import TravelPriceSidecar

TRAVEL_MEDIA_ASSET_VERSION = "AURA_TRAVEL_MEDIA_ASSET_V1"


class TravelMediaAssetRegistry:
    def __init__(self, sidecar: TravelPriceSidecar):
        self.sidecar = sidecar

    def register_asset(
        self,
        *,
        resort_id: str,
        asset_type: str,
        title: str | None = None,
        storage_url: str | None = None,
        local_path: str | Path | None = None,
        rights_status: str = "unknown",
    ) -> str:
        if not storage_url and not local_path:
            raise ValueError("media asset requires storage_url or local_path")
        if asset_type == "gaussian_splat" and local_path:
            suffix = Path(local_path).suffix.lower()
            if suffix not in {".spz", ".ply", ".ksplat", ".splat"}:
                raise ValueError("gaussian_splat asset should reference .spz, .ply, .ksplat, or .splat")
        return self.sidecar.upsert_media_asset(
            {
                "version": TRAVEL_MEDIA_ASSET_VERSION,
                "resort_id": resort_id,
                "asset_type": asset_type,
                "title": title,
                "storage_url": storage_url,
                "local_path": str(local_path) if local_path is not None else None,
                "rights_status": rights_status,
            }
        )

    def register_gaussian_splat(
        self,
        *,
        resort_id: str,
        local_path: str | Path,
        title: str | None = None,
        rights_status: str = "operator_review_required",
    ) -> str:
        return self.register_asset(
            resort_id=resort_id,
            asset_type="gaussian_splat",
            title=title,
            local_path=local_path,
            rights_status=rights_status,
        )

    def premium_media_contract(self, *, resort_id: str, asset_id: str) -> dict[str, Any]:
        return {
            "version": TRAVEL_MEDIA_ASSET_VERSION,
            "resort_id": resort_id,
            "asset_id": asset_id,
            "requires_rights_review": True,
            "premium_listing_surface": "360/video/gaussian_splat",
            "invariant": "VSA may point to media assets, but sidecar keeps rights and storage truth",
        }

