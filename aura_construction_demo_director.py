"""Deterministic local director for the Construction Arena G7 video surface.

The director composes the existing G4 fixture, G5 projection, and G6 renderer
packet. It owns presentation sequencing only and grants no domain authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

from aura_construction_demo_contracts import (
    CC_BY_4_0,
    CC_BY_4_0_URL,
    TU_WIEN_DOI,
    TU_WIEN_PUBLISHED_MD5,
    TU_WIEN_SOURCE_FILENAME,
    TU_WIEN_SOURCE_ID,
    ConstructionDemoAssetBinding,
    ConstructionDemoAssetPack,
    ConstructionDemoRepresentation,
    ConstructionDemoSourceManifest,
    ConstructionDemoStorey,
    ConstructionDemoTruthClass,
)
from aura_construction_demo_fixture_builder import (
    build_construction_demo_project_fixture,
    build_construction_demo_runtime_packet,
)
from aura_construction_demo_projection import project_construction_demo_to_scene
from aura_event_contracts import canonical_json, stable_digest
from aura_spatial_contracts import SpatialRenderBudget
from aura_spatial_render_plan import compile_spatial_device_profile, negotiate_spatial_render_plan

CONSTRUCTION_DEMO_DIRECTOR_VERSION = "AURA_CONSTRUCTION_DEMO_DIRECTOR_V1"
CONSTRUCTION_DEMO_TOURS = ("full", "blocked-work", "alternatives", "timeline")
FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST = (
    "5e4620fc5ea92315714eaf3bfe0247f4a18f6ed51997efb9c5c389d20536d7b7"
)


@dataclass(frozen=True)
class ConstructionDemoTourStep:
    """One bounded, presentation-only director action."""

    step_id: str
    title: str
    action: str
    duration_ms: int
    target: str | None = None
    value: float | str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "action": self.action,
            "duration_ms": self.duration_ms,
            "target": self.target,
            "value": self.value,
            "execution_authority": False,
            "presentation_only": True,
        }


def _fallback_manifest() -> ConstructionDemoSourceManifest:
    return ConstructionDemoSourceManifest(
        source_id=TU_WIEN_SOURCE_ID,
        title="Custom Test Model for Escape Route Analysis in IFC format",
        creators=("Fischer", "Pfeiffer", "Schranz", "Urban", "Zdanowicz"),
        publisher="TU Wien Research Data",
        doi=TU_WIEN_DOI,
        source_filename=TU_WIEN_SOURCE_FILENAME,
        source_byte_length=7_100_000,
        published_md5=TU_WIEN_PUBLISHED_MD5,
        observed_sha256="a" * 64,
        license_id=CC_BY_4_0,
        license_url=CC_BY_4_0_URL,
        downloaded_at="2026-07-22T10:00:00Z",
    )


def _fallback_asset(
    storey_id: str,
    representation: ConstructionDemoRepresentation,
    suffix: str,
) -> ConstructionDemoAssetBinding:
    media_types = {
        ConstructionDemoRepresentation.MESH_GLB: "model/gltf-binary",
        ConstructionDemoRepresentation.FLOOR_PLAN_SVG: "image/svg+xml",
        ConstructionDemoRepresentation.GAUSSIAN_SPZ: "application/vnd.aura.spz",
    }
    digest_character = suffix[0] if suffix[0] in "abcdef" else "b"
    representation_digest = (
        FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST
        if representation is ConstructionDemoRepresentation.GAUSSIAN_SPZ
        else "d" * 64
    )
    return ConstructionDemoAssetBinding(
        asset_id=f"asset-{storey_id}-{suffix}",
        storey_id=storey_id,
        representation=representation,
        uri=f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.{suffix}",
        media_type=media_types[representation],
        content_digest=digest_character * 64,
        byte_length=4096,
        coordinate_system="RIGHT_HANDED_Y_UP_METERS",
        unit_scale_meters=1.0,
        bounds_min=(-10.0, 0.0, -10.0),
        bounds_max=(10.0, 4.0, 10.0),
        source_refs=(f"ifc:storey:{storey_id}",),
        import_receipt_digest="c" * 64,
        representation_digest=representation_digest,
        truth_class=ConstructionDemoTruthClass.DERIVED_PRESENTATION,
    )


def build_fallback_construction_demo_asset_pack() -> ConstructionDemoAssetPack:
    """Build the deterministic local fallback pack used without generated assets."""

    storeys: list[ConstructionDemoStorey] = []
    assets: list[ConstructionDemoAssetBinding] = []
    for ordinal in range(5):
        storey_id = f"storey-{ordinal:02d}"
        storeys.append(
            ConstructionDemoStorey(
                storey_id=storey_id,
                ifc_global_id=f"ifc-global-id-{ordinal:02d}",
                name=f"Storey {ordinal:02d}",
                elevation_m=float(ordinal * 4),
                ordinal=ordinal,
                source_ifc_ref=(
                    f"demo_assets/construction_tuwien/generated/storeys/{storey_id}/{storey_id}.ifc"
                ),
                mesh_asset_id=f"asset-{storey_id}-glb",
                floor_plan_asset_id=f"asset-{storey_id}-svg",
                gaussian_asset_id=f"asset-{storey_id}-spz",
                bounds_min=(-10.0, 0.0, -10.0),
                bounds_max=(10.0, 4.0, 10.0),
                frame_id=f"{storey_id}-frame",
                source_refs=(f"ifc:storey:{storey_id}",),
            )
        )
        assets.extend(
            (
                _fallback_asset(storey_id, ConstructionDemoRepresentation.MESH_GLB, "glb"),
                _fallback_asset(
                    storey_id,
                    ConstructionDemoRepresentation.FLOOR_PLAN_SVG,
                    "svg",
                ),
                _fallback_asset(
                    storey_id,
                    ConstructionDemoRepresentation.GAUSSIAN_SPZ,
                    "spz",
                ),
            )
        )
    return ConstructionDemoAssetPack(
        source_manifest=_fallback_manifest(),
        building_id="construction-demo-building",
        building_frame_id="construction-demo-building-frame",
        storeys=tuple(storeys),
        assets=tuple(sorted(assets, key=lambda item: item.asset_id)),
        element_index_digest="e" * 32,
        hierarchy_digest="f" * 32,
        generator_version="construction-demo-generator-v1",
        generator_request_digest="1" * 32,
    )


def load_construction_demo_asset_pack(
    path: Path | None,
) -> tuple[ConstructionDemoAssetPack, bool]:
    """Load an admitted pack or return the deterministic local fallback."""

    if path is None:
        return build_fallback_construction_demo_asset_pack(), True
    payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Construction demo asset pack must be a JSON object")
    return ConstructionDemoAssetPack.from_dict(payload), False


def _full_tour() -> tuple[ConstructionDemoTourStep, ...]:
    return (
        ConstructionDemoTourStep(
            "01-attribution", "Open source attribution", "SHOW_ATTRIBUTION", 1800
        ),
        ConstructionDemoTourStep(
            "02-building", "Complete hybrid building", "SHOW_ALL", 2200
        ),
        ConstructionDemoTourStep(
            "03-orbit", "Orbit the building", "ORBIT", 2600, value=0.55
        ),
        ConstructionDemoTourStep(
            "04-explode", "Explode storeys", "EXPLODE", 2200, value=4.0
        ),
        ConstructionDemoTourStep(
            "05-plans", "Reveal floor plans", "TOGGLE_LAYER", 1600, "floorPlans", "on"
        ),
        ConstructionDemoTourStep(
            "06-timeline", "Replay project progress", "TIMELINE", 3200, value=12.0
        ),
        ConstructionDemoTourStep(
            "07-blocked", "Find blocked drilling", "FOCUS_STATUS", 2400, "BLOCKED"
        ),
        ConstructionDemoTourStep(
            "08-evidence", "Show blocking evidence", "TOGGLE_LAYER", 1800, "blockers", "on"
        ),
        ConstructionDemoTourStep(
            "09-unsafe", "Keep unsafe option blocked", "FOCUS_BLOCKED_ALTERNATIVE", 2200
        ),
        ConstructionDemoTourStep(
            "10-alternate", "Show safe alternate work", "FOCUS_RECOMMENDED_ALTERNATIVE", 2400
        ),
        ConstructionDemoTourStep(
            "11-trades", "Show subcontractor history", "TOGGLE_LAYER", 1800, "trades", "on"
        ),
        ConstructionDemoTourStep(
            "12-dependencies", "Show dependencies", "TOGGLE_LAYER", 1800, "dependencies", "on"
        ),
        ConstructionDemoTourStep(
            "13-rules", "Show synthetic rule gates", "TOGGLE_LAYER", 1800, "syntheticRules", "on"
        ),
        ConstructionDemoTourStep(
            "14-budget", "Compare schedule and budget", "TOGGLE_LAYER", 2200, "budgets", "on"
        ),
        ConstructionDemoTourStep(
            "15-review",
            "Select recommendation for human review",
            "FOCUS_RECOMMENDED_ALTERNATIVE",
            2200,
        ),
        ConstructionDemoTourStep(
            "16-observatory", "Open evidence summary", "SHOW_OBSERVATORY", 2200
        ),
        ConstructionDemoTourStep(
            "17-decision", "Produce human decision packet", "SHOW_DECISION_PACKET", 2200
        ),
        ConstructionDemoTourStep(
            "18-dissolve", "Dissolve Arena and release renderer", "DISSOLVE", 1800
        ),
    )


def _tour_steps(name: str) -> tuple[ConstructionDemoTourStep, ...]:
    if name not in CONSTRUCTION_DEMO_TOURS:
        raise ValueError(f"unsupported Construction demo tour: {name}")
    full = _full_tour()
    if name == "full":
        return full
    selected = {
        "blocked-work": {
            "02-building",
            "04-explode",
            "07-blocked",
            "08-evidence",
            "09-unsafe",
            "18-dissolve",
        },
        "alternatives": {
            "02-building",
            "07-blocked",
            "09-unsafe",
            "10-alternate",
            "14-budget",
            "15-review",
            "18-dissolve",
        },
        "timeline": {
            "02-building",
            "04-explode",
            "05-plans",
            "06-timeline",
            "11-trades",
            "18-dissolve",
        },
    }[name]
    return tuple(step for step in full if step.step_id in selected)


def compile_construction_demo_packet(
    *,
    asset_pack_path: Path | None = None,
    tour: str = "full",
) -> dict[str, Any]:
    """Compile the deterministic browser packet for the local Construction demo."""

    asset_pack, fallback = load_construction_demo_asset_pack(asset_pack_path)
    fixture = build_construction_demo_project_fixture(asset_pack)
    runtime_packet = build_construction_demo_runtime_packet(fixture)
    purpose_digest = stable_digest(
        {
            "objective": "record the governed synthetic Construction Arena demonstration",
            "tour": tour,
            "asset_pack_digest": asset_pack.asset_pack_digest,
        },
        digest_size=32,
    )
    scene = project_construction_demo_to_scene(
        fixture,
        runtime_packet,
        purpose_digest=purpose_digest,
        scene_id=f"construction-video-demo-{tour}",
    )
    device = compile_spatial_device_profile(
        profile_id="device:construction-video-demo",
        supported_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        budget=SpatialRenderBudget(
            max_entities=1024,
            max_links=4096,
            max_assets=512,
            max_asset_bytes=268_435_456,
            max_cpu_ms_per_frame=33.0,
            max_gpu_bytes=536_870_912,
            max_network_bytes=0,
        ),
        xr_user_activation=False,
        source_refs=("source:local-construction-video-demo",),
    )
    plan = negotiate_spatial_render_plan(
        scene,
        device,
        preferred_renderers=("WEBGL2", "ACCESSIBLE_2D", "HEADLESS"),
        allow_xr=False,
    )
    recommended = next(
        (item for item in fixture.alternatives if item.recommended_for_human_review),
        None,
    )
    return {
        "ok": True,
        "version": CONSTRUCTION_DEMO_DIRECTOR_VERSION,
        "tour": tour,
        "tour_steps": [step.to_dict() for step in _tour_steps(tour)],
        "scene": scene.to_dict(),
        "render_plan": plan.to_dict(),
        "fixture_digest": fixture.fixture_digest,
        "asset_pack_digest": asset_pack.asset_pack_digest,
        "fallback_asset_pack": fallback,
        "attribution": (
            "Building geometry adapted from the TU Wien Custom Test Model for Escape Route "
            "Analysis in IFC format, DOI 10.48436/a185k-86v39, CC BY 4.0. All project, "
            "schedule, budget, organization, hazard, rule, and status data are fictional."
        ),
        "recommended_alternative_id": (
            recommended.alternative_id if recommended is not None else None
        ),
        "blocked_work_package_id": fixture.focus_scope.work_package_id,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_controlled": False,
        "professional_certification_claimed": False,
        "legal_or_regulatory_authority_claimed": False,
        "survey_authority_claimed": False,
        "renderer_authority": False,
        "automatic_execution": False,
        "automatic_merge": False,
        "human_review_required": True,
    }


def write_construction_demo_packet(packet: Mapping[str, Any], path: Path) -> Path:
    """Write one canonical, deterministic browser packet."""

    destination = path.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(canonical_json(dict(packet)) + "\n", encoding="utf-8")
    return destination


_ALLOWED_STATIC_PREFIXES = (
    "/aura_spatial_web/",
    "/demo_assets/construction_tuwien/generated/",
)


def _safe_construction_demo_static_path(raw_path: str) -> str | None:
    decoded = unquote(urlparse(raw_path).path)
    if "\\" in decoded or "\x00" in decoded:
        return None
    candidate = PurePosixPath(decoded)
    if ".." in candidate.parts:
        return None
    normalized = "/" + str(candidate).lstrip("/")
    if not any(normalized.startswith(prefix) for prefix in _ALLOWED_STATIC_PREFIXES):
        return None
    return normalized


class _ConstructionDemoHandler(SimpleHTTPRequestHandler):
    packet: bytes = b"{}"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/demo/construction", "/demo/construction/"}:
            self.path = "/aura_spatial_web/construction_demo.html"
        elif parsed.path == "/api/construction-demo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(self.packet)))
            self.end_headers()
            self.wfile.write(self.packet)
            return
        else:
            safe_path = _safe_construction_demo_static_path(self.path)
            if safe_path is None:
                self.send_error(404)
                return
            self.path = safe_path
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve_construction_demo(
    repo_root: Path,
    packet: Mapping[str, Any],
    *,
    host: str = "127.0.0.1",
    port: int = 8767,
) -> None:
    """Serve the local video surface and packet until interrupted."""

    root = repo_root.expanduser().resolve()
    handler_type = type(
        "ConstructionDemoHandler",
        (_ConstructionDemoHandler,),
        {"packet": (canonical_json(dict(packet)) + "\n").encode("utf-8")},
    )
    server = ThreadingHTTPServer(
        (host, port),
        partial(handler_type, directory=str(root)),
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


__all__ = [
    "CONSTRUCTION_DEMO_DIRECTOR_VERSION",
    "CONSTRUCTION_DEMO_TOURS",
    "FALLBACK_GAUSSIAN_REPRESENTATION_DIGEST",
    "ConstructionDemoTourStep",
    "build_fallback_construction_demo_asset_pack",
    "compile_construction_demo_packet",
    "load_construction_demo_asset_pack",
    "serve_construction_demo",
    "write_construction_demo_packet",
]
