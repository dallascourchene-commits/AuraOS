"""Declarative Civic project registry for Aura's guided showcase."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from aura_civic_winnipeg_fixture import TRUTH_SYNTHETIC, winnipeg_pathways_fixtures

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class CivicProjectDefinition:
    project_id: str
    title: str
    objective: str
    jurisdiction_id: str
    jurisdiction_label: str
    context_profiles: tuple[str, ...]
    mandatory_constraints: tuple[str, ...]
    guided_steps: tuple[str, ...]
    organ_sequence: tuple[str, ...]
    fixtures_factory: Callable[[], dict[str, Any]]
    demo_issue: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        packet = asdict(self)
        packet.pop("fixtures_factory", None)
        packet.update({"patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False, "non_binding": True})
        return packet


def _existing_project(project_id: str) -> CivicProjectDefinition:
    from aura_civic_demo_fixtures import council_issue_fixtures, hairstylist_fixtures, youth_centre_fixtures
    table = {
        "hairstylist": ("Community-Owned Hairstyling Service", hairstylist_fixtures, ("CivicProfileOrgan", "CivicMapOrgan", "CommunityContributionOrgan", "CommunityResourceMatcherOrgan", "CivicMITOSISOrgan", "CivicMUSICOrgan", "CivicEvidenceOrgan", "ConsentArcOrgan", "WhatIfOrgan", "PilotTunnelOrgan", "DecisionPacketOrgan")),
        "youth_centre": ("Youth Healing, Training, and Employment Centre", youth_centre_fixtures, ("CivicProfileOrgan", "CivicMapOrgan", "CommunityContributionOrgan", "CommunityResourceMatcherOrgan", "CivicMITOSISOrgan", "CivicMUSICOrgan", "CivicEvidenceOrgan", "ConsentArcOrgan", "WhatIfOrgan", "PilotTunnelOrgan", "DecisionPacketOrgan")),
        "council_pulse": ("Civic Issue Pulse", council_issue_fixtures, ("CivicProfileOrgan", "CouncilIssuePulseOrgan", "DecisionPacketOrgan")),
    }
    title, factory, organs = table[project_id]
    fixture = factory()
    return CivicProjectDefinition(
        project_id, title, str(fixture.get("objective") or title), "winnipeg_mb_ca", "Winnipeg, Manitoba", (),
        ("human_authority", "privacy", "non_binding"),
        ("WELCOME", "FRAME_OBJECTIVE", "EXPLORE", "REVIEW_PACKET", "COMPLETE"), organs, factory,
    )


WINNIPEG_PATHWAYS = CivicProjectDefinition(
    project_id="winnipeg_pathways",
    title="Winnipeg Community Pathways Lab",
    objective=winnipeg_pathways_fixtures()["objective"],
    jurisdiction_id="winnipeg_mb_ca",
    jurisdiction_label="Winnipeg, Manitoba",
    context_profiles=(),
    mandatory_constraints=(
        "human_authority", "community_authority", "privacy_by_default",
        "no_person_level_vulnerability_mapping", "explicit_context_selection_only",
        "non_binding_outputs", "reversible_pilot",
    ),
    guided_steps=(
        "WELCOME", "FRAME_OBJECTIVE", "SELECT_CONTEXT", "EXPLORE_MAP",
        "ADD_COMMUNITY_INPUT", "DECOMPOSE_WORK", "COMPARE_SCENARIOS",
        "REVIEW_CONSENT", "RUN_WHAT_IF", "DESIGN_PILOT", "REVIEW_PACKET", "COMPLETE",
    ),
    organ_sequence=(
        "CivicProfileOrgan", "CivicMapOrgan", "CommunityContributionOrgan",
        "CommunityResourceMatcherOrgan", "CivicMITOSISOrgan", "CivicMUSICOrgan",
        "CivicEvidenceOrgan", "ConsentArcOrgan", "SystemicContextOrgan",
        "WhatIfOrgan", "PilotTunnelOrgan", "DecisionPacketOrgan",
    ),
    fixtures_factory=winnipeg_pathways_fixtures,
    demo_issue={
        "issue_id": "WINNIPEG-MAP-CANDIDATE-VISIBILITY",
        "title": "Candidate pilot location is hidden at the initial map zoom",
        "observed": "The showcase opens at zoom 11 while candidate features require zoom 12.",
        "question": "Is this intended policy, fixture data, or a presentation default mismatch?",
        "recommended_option": "Preserve map policy and focus the guided candidate step at zoom 12.",
        "files": ["aura_showcase/app.js", "aura_civic_map.py", "aura_civic_projects.py", "tests/test_aura_showcase_guided_project.py"],
        "tests": ["tests/test_aura_showcase_guided_project.py"],
        "candidate_options": [
            "Open every Civic project at zoom 12.",
            "Lower candidate visibility to zoom 11.",
            "Keep policy unchanged and focus only the candidate step at zoom 12.",
        ],
        "production_mutation": False,
        "human_review_required": True,
    },
)


def list_projects() -> dict[str, Any]:
    projects = [_existing_project(name) for name in ("hairstylist", "youth_centre", "council_pulse")]
    projects.append(WINNIPEG_PATHWAYS)
    return {"ok": True, "projects": [item.to_dict() for item in projects], "default_project_id": "winnipeg_pathways", "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False}


def get_project(project_id: str) -> CivicProjectDefinition:
    key = str(project_id or "").strip()
    if key == "winnipeg_pathways":
        return WINNIPEG_PATHWAYS
    if key in {"hairstylist", "youth_centre", "council_pulse"}:
        return _existing_project(key)
    raise KeyError(f"unknown civic project: {key}")


__all__ = ["CivicProjectDefinition", "TRUTH_SYNTHETIC", "WINNIPEG_PATHWAYS", "get_project", "list_projects", "winnipeg_pathways_fixtures"]
