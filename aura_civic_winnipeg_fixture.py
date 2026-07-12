"""Deterministic synthetic fixture for the Winnipeg Community Pathways Lab."""
from __future__ import annotations

from typing import Any

TRUTH_SYNTHETIC = "SYNTHETIC_DEMO_DATA"


def _record(identifier: str, description: str, **extra: Any) -> dict[str, Any]:
    return {
        "truth_class": TRUTH_SYNTHETIC,
        "privacy_class": "PUBLIC_PSEUDONYMOUS",
        "consent_to_match": True,
        "description": description,
        **extra,
        **({"need_id": identifier} if identifier.startswith("WP-NEED") else {}),
        **({"offer_id": identifier} if identifier.startswith("WP-OFFER") else {}),
    }


def _feature(feature_id: str, name: str, kind: str, coordinates: Any, *, privacy: str = "PUBLIC_ATTRIBUTED") -> dict[str, Any]:
    geometry_type = "Polygon" if kind in {"boundary", "neighbourhood"} else "Point"
    return {
        "type": "Feature",
        "properties": {
            "feature_id": feature_id,
            "name": name,
            "type": kind,
            "jurisdiction_id": "winnipeg_mb_ca",
            "truth_class": TRUTH_SYNTHETIC,
            "privacy_class": privacy,
            "location_class": "NEIGHBOURHOOD_ONLY" if geometry_type == "Polygon" else "APPROXIMATE_LOCATION",
            "source_ref": TRUTH_SYNTHETIC,
        },
        "geometry": {"type": geometry_type, "coordinates": coordinates},
    }


def winnipeg_pathways_fixtures() -> dict[str, Any]:
    objective = (
        "Design a Winnipeg community network connecting low-barrier housing, mobile outreach, "
        "Indigenous-led healing, transportation, training, employment, and neighbourhood support "
        "while preserving privacy and community authority."
    )
    needs = [
        _record("WP-NEED-HOUSING", "Low-barrier temporary housing and stable-housing navigation"),
        _record("WP-NEED-OUTREACH", "Mobile outreach capacity during evenings and weekends"),
        _record("WP-NEED-HEALING", "Indigenous-led cultural and healing programming with explicit community governance"),
        _record("WP-NEED-TRANSIT", "Transportation between neighbourhood services and training programs"),
        _record("WP-NEED-EMPLOYMENT", "Training connected to real employment pathways"),
    ]
    offers = [
        _record("WP-OFFER-SPACE", "Public community room near transit", offer_type="space"),
        _record("WP-OFFER-VAN", "One outreach van for a bounded pilot", offer_type="transport"),
        _record("WP-OFFER-WORKERS", "Community health and housing-navigation workers", offer_type="skill"),
        _record("WP-OFFER-CULTURE", "Consenting cultural facilitators", offer_type="mentor"),
        _record("WP-OFFER-TRAINING", "Accessible employment and skills provider", offer_type="training"),
        _record("WP-OFFER-EMPLOYER", "Employer partner for a supervised cohort", offer_type="employment"),
    ]
    scenarios = [
        {
            "scenario_id": "WP-SCEN-HUBS",
            "title": "Distributed Neighbourhood Hubs",
            "description": "Small community-led access points coordinated through shared navigation.",
            "metrics": {"local_ownership": .9, "accessibility": .82, "funding_feasibility": .45, "time_to_implementation": .55, "reversibility": .8},
            "truth_class": TRUTH_SYNTHETIC,
        },
        {
            "scenario_id": "WP-SCEN-MOBILE",
            "title": "Mobile Outreach and Housing Navigation",
            "description": "A mobile team connects people with housing, healing, and employment supports.",
            "metrics": {"local_ownership": .72, "accessibility": .9, "funding_feasibility": .7, "time_to_implementation": .88, "reversibility": .92},
            "truth_class": TRUTH_SYNTHETIC,
        },
        {
            "scenario_id": "WP-SCEN-CENTRAL",
            "title": "Central Healing, Training, and Employment Centre",
            "description": "One integrated site combines multiple programs.",
            "metrics": {"local_ownership": .68, "accessibility": .5, "funding_feasibility": .25, "time_to_implementation": .3, "reversibility": .35},
            "truth_class": TRUTH_SYNTHETIC,
        },
        {
            "scenario_id": "WP-SCEN-NETWORK",
            "title": "Coordinated Existing-Service Network",
            "description": "Organizations retain autonomy while sharing referral infrastructure.",
            "metrics": {"local_ownership": .78, "accessibility": .76, "funding_feasibility": .78, "time_to_implementation": .72, "reversibility": .84},
            "truth_class": TRUTH_SYNTHETIC,
        },
    ]
    return {
        "objective": objective,
        "needs": needs,
        "offers": offers,
        "concerns": [
            {"concern_id": "WP-CONCERN-PRIVACY", "description": "Do not map vulnerable individuals or person-level risk", "truth_class": TRUTH_SYNTHETIC},
            {"concern_id": "WP-CONCERN-DATA", "description": "Cultural knowledge requires explicit governance", "truth_class": TRUTH_SYNTHETIC},
            {"concern_id": "WP-CONCERN-TRANSIT", "description": "Evening transportation remains uncertain", "truth_class": TRUTH_SYNTHETIC},
            {"concern_id": "WP-CONCERN-AUTHORITY", "description": "No automatic spending, binding vote, or government submission", "truth_class": TRUTH_SYNTHETIC},
        ],
        "objections": [{
            "objection_id": "WP-OBJ-CENTRAL",
            "proposal_ref": "WP-SCEN-CENTRAL",
            "reason": "A single central site may increase transportation burden.",
            "severity": "CRITICAL_OBJECTION",
            "truth_class": TRUTH_SYNTHETIC,
        }],
        "representation_gaps": [
            "People with lived experience have not yet reviewed the pilot",
            "Youth participation is underrepresented",
            "Elder and cultural-governance participation requires invitation and consent",
        ],
        "scenarios": scenarios,
        "legal_instruments": [
            {"instrument_id": "WP-LI-ZONING", "name": "Zoning and occupancy questions", "level": "bylaw", "applicability": "REQUIRES_HUMAN_REVIEW", "source_ref": "SYNTHETIC_DEMO_REFERENCE", "as_of_date": "2026-07-12", "truth_class": TRUTH_SYNTHETIC},
            {"instrument_id": "WP-LI-PRIVACY", "name": "Privacy and community data-governance questions", "level": "policy", "applicability": "REQUIRES_HUMAN_REVIEW", "source_ref": "SYNTHETIC_DEMO_REFERENCE", "as_of_date": "2026-07-12", "truth_class": TRUTH_SYNTHETIC},
        ],
        "council_items": [],
        "basemap": {
            "provider": "OpenStreetMap",
            "tile_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "© OpenStreetMap contributors",
            "network_optional": True,
            "offline_fallback": "Aura synthetic governed grid",
            "test_community_label": "West Broadway synthetic test community",
            "default_center": [-97.152, 49.895],
            "test_community_center": [-97.165, 49.8865],
        },
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                _feature("WP-BOUNDARY", "Central Winnipeg Demonstration Area", "boundary", [[[-97.19, 49.87], [-97.08, 49.87], [-97.08, 49.94], [-97.19, 49.94], [-97.19, 49.87]]]),
                _feature("WP-TEST-COMMUNITY", "West Broadway Synthetic Test Community", "neighbourhood", [[[-97.181, 49.878], [-97.146, 49.878], [-97.146, 49.895], [-97.181, 49.895], [-97.181, 49.878]]]),
                _feature("WP-FACILITY-1", "Community Partner Site", "facility", [-97.162, 49.884]),
                _feature("WP-TRANSIT-1", "Transit Connection", "transit", [-97.167, 49.886]),
                _feature("WP-SERVICE-1", "Housing Navigation Access Point", "service", [-97.153, 49.89]),
                _feature("WP-CANDIDATE-1", "Proposed Mobile Pilot Staging Site", "candidate", [-97.176, 49.889], privacy="COMMUNITY_ONLY"),
            ],
        },
        "heatmap": {
            "metric": "service_access_distance",
            "source": TRUTH_SYNTHETIC,
            "time_range": "synthetic demonstration period",
            "geographic_unit": "aggregate demonstration zone",
            "aggregation": "average",
            "denominator": "synthetic resident index",
            "missing_data_rate": 0.0,
            "freshness": "2026-07-12",
            "uncertainty": "high_synthetic_demo",
            "truth_class": TRUTH_SYNTHETIC,
            "values": [{"label": "Zone A", "value": 1.4}, {"label": "Zone B", "value": 2.6}],
        },
        "what_if_defaults": {"funding_feasibility": .68, "accessibility": .9, "time_to_implementation": .86},
        "pilot_template": {
            "duration_days": 90,
            "components": ["mobile outreach", "partner site", "weekly healing program", "housing navigator", "training cohort"],
            "review_days": [30, 60, 90],
            "funding_allocated": False,
            "binding_authority": False,
        },
    }
