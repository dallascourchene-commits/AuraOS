"""Deterministic P3 Construction decision lane for the composed Spatial Foundry.

This module composes existing canonical Construction, Spatial, demo-fixture, and
Pascal presentation owners. It creates no Construction truth, approval,
persistence, renderer, routing, verification, or learning authority.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

from aura_construction_demo_director import load_construction_demo_asset_pack
from aura_construction_demo_fixture import ConstructionDemoProjectFixture
from aura_construction_demo_fixture_builder import (
    build_construction_demo_project_fixture,
    build_construction_demo_runtime_packet,
)
from aura_construction_demo_projection import project_construction_demo_to_scene
from aura_construction_spatial_foundry import (
    ConstructionCoordinationCandidateArtifact,
    DomainDecisionEnvelope,
)
from aura_event_contracts import canonical_json, stable_digest
from aura_pascal_spatial_presentation import (
    AuraPascalCoordinateReceipt,
    PascalNodeBinding,
    PascalPresentationError,
    PascalSceneArtifactManifest,
    sha256_digest,
)
from aura_spatial_contracts import SpatialInteractionAction, SpatialRenderBudget, SpatialSceneSnapshot
from aura_spatial_interaction import compile_spatial_interaction
from aura_spatial_render_plan import (
    compile_spatial_device_profile,
    negotiate_spatial_render_plan,
)

CONSTRUCTION_FOUNDRY_DECISION_VERSION = "AURA_CONSTRUCTION_FOUNDRY_DECISION_LANE_V1"
CONSTRUCTION_DECISION_EXPORT_VERSION = "AURA_CONSTRUCTION_DECISION_SUPPORT_EXPORT_V1"
CONSTRUCTION_COMPARE_RECEIPT_VERSION = "AURA_CONSTRUCTION_COMPARE_PRESENTATION_RECEIPT_V1"
CONSTRUCTION_AS_BUILT_PACKET_VERSION = "AURA_CONSTRUCTION_FOUNDRY_AS_BUILT_PACKET_V1"

_ALLOWED_VIEWS = frozenset({"DESIGN", "FLOOR_PLAN", "AS_BUILT", "COMPARE"})
_ROLE_TITLES = {
    "HARD_BLOCKED": "Continue upper-floor drilling",
    "NEEDS_EVIDENCE": "Advance electrical isolation package",
    "READY_FOR_HUMAN_REVIEW": "Shift crew to released preparation work",
}


def _finite(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _view(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("active_view must be a string")
    normalized = value.strip().upper()
    if normalized not in _ALLOWED_VIEWS:
        raise ValueError(f"unsupported Construction Foundry view: {normalized}")
    return normalized


def _pdf_text(value: Any) -> str:
    text = " ".join(str(value).split())
    return (
        text.encode("ascii", "replace")
        .decode("ascii")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _minimal_pdf(lines: list[str]) -> bytes:
    """Build a deterministic single-page PDF without adding a PDF dependency."""
    rows = ["BT", "/F1 9 Tf", "45 760 Td", "12 TL"]
    for index, line in enumerate(lines[:52]):
        if index:
            rows.append("T*")
        rows.append(f"({_pdf_text(line)[:118]}) Tj")
    rows.append("ET")
    stream = "\n".join(rows).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n%AuraOS-P3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def _assessment_by_id(runtime_packet: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    evaluation = runtime_packet.get("evaluation")
    if not isinstance(evaluation, Mapping):
        raise ValueError("Construction runtime packet lacks an exact evaluation")
    rows = evaluation.get("assessments")
    if not isinstance(rows, list) or any(not isinstance(item, Mapping) for item in rows):
        raise ValueError("Construction runtime evaluation assessments are invalid")
    return {str(item.get("candidate_id")): item for item in rows}


def _candidate_by_title(fixture: ConstructionDemoProjectFixture, title: str):
    rows = [item for item in fixture.candidates if item.title == title]
    if len(rows) != 1:
        raise ValueError(f"fixture does not contain one exact candidate titled {title!r}")
    return rows[0]


def _domain_to_pascal_storeys(
    fixture: ConstructionDemoProjectFixture,
    manifest: PascalSceneArtifactManifest,
) -> dict[str, str]:
    domain_storeys = tuple(
        item.storey_id
        for item in sorted(
            fixture.asset_pack.storeys,
            key=lambda item: (item.ordinal, item.storey_id),
        )
    )
    if not domain_storeys or not manifest.storey_ids:
        raise ValueError("Construction and Pascal storey sets must be non-empty")
    return {
        storey_id: manifest.storey_ids[index % len(manifest.storey_ids)]
        for index, storey_id in enumerate(domain_storeys)
    }


def _binding_for_package(
    manifest: PascalSceneArtifactManifest,
    presentation_storey_id: str,
    package_id: str,
) -> PascalNodeBinding:
    selectable = tuple(
        sorted(
            (
                item
                for item in manifest.node_bindings
                if item.storey_id == presentation_storey_id and item.selectable
            ),
            key=lambda item: item.node_id,
        )
    )
    if not selectable:
        raise PascalPresentationError("presentation storey has no selectable Pascal binding")
    digest = stable_digest({"package_id": package_id, "storey_id": presentation_storey_id})
    return selectable[int(digest[:8], 16) % len(selectable)]


def _work_package_rows(
    fixture: ConstructionDemoProjectFixture,
    manifest: PascalSceneArtifactManifest,
    scene: SpatialSceneSnapshot,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    storey_map = _domain_to_pascal_storeys(fixture, manifest)
    storey_frames = {item.storey_id: item.frame_id for item in fixture.asset_pack.storeys}
    budgets = {item.work_package_id: item for item in fixture.budget_lines}
    inspections = {item.inspection_id: item for item in fixture.inspections}
    hazards = {item.hazard_id: item for item in fixture.hazards}
    spatial_package_entities = {
        str(dict(item.metadata).get("work_package_ref")): item.entity_id
        for item in scene.entities
        if dict(item.metadata).get("work_package_ref")
    }
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for package in fixture.work_packages:
        presentation_storey_id = storey_map[package.storey_id]
        binding = _binding_for_package(
            manifest,
            presentation_storey_id,
            package.work_package_id,
        )
        budget = budgets[package.work_package_id]
        spatial_entity_id = spatial_package_entities.get(package.work_package_id)
        if not spatial_entity_id:
            raise ValueError("Construction work package lacks an exact Spatial entity")
        row = {
            "work_package_id": package.work_package_id,
            "title": package.title,
            "status": package.status,
            "construction_scope_ref": f"construction-scope:{package.scope.scope_key}",
            "spatial_entity_id": spatial_entity_id,
            "domain_storey_id": package.storey_id,
            "as_built_frame_id": storey_frames[package.storey_id],
            "presentation_storey_id": presentation_storey_id,
            "presentation_mapping_class": "PRESENTATION_ONLY_NON_CANONICAL_ASSOCIATION",
            "zone_id": package.zone_id,
            "trade_id": package.trade_id,
            "planned_start_day": package.planned_start_day,
            "planned_finish_day": package.planned_finish_day,
            "dependency_ids": list(package.dependency_ids),
            "evidence_refs": list(package.evidence_refs),
            "inspections": [inspections[item].to_dict() for item in package.inspection_ids],
            "hazards": [hazards[item].to_dict() for item in package.hazard_ids],
            "rule_ids": list(package.rule_ids),
            "crane_window_id": package.crane_window_id,
            "professional_release_required": package.professional_release_required,
            "budget": budget.to_dict(),
            "pascal_node_id": binding.node_id,
            "pascal_aura_entity_id": binding.aura_entity_id,
            "pascal_aura_target_ref": binding.aura_target_ref,
            "pascal_mapping_mutated": False,
            "survey_authority": False,
            "physical_work_authorized": False,
            "payment_released": False,
            "automatic_execution": False,
        }
        rows.append(row)
        by_id[package.work_package_id] = row
    return rows, by_id


def _needs_evidence_package(
    candidate: ConstructionCoordinationCandidate,
    fixture: ConstructionDemoProjectFixture,
    work_packages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Derive the work package whose inspections gate this candidate.

    Each required claim's scope carries a work_package_id.  Find the claim
    in the fixture state's active claim events, read its scope, and look up
    the projected work package row.  Fall back to the candidate's own scope
    if no claim-scope package is found.
    """
    claim_events = getattr(fixture.state, "active_claim_events", ())
    if isinstance(claim_events, (tuple, list)):
        for event in claim_events:
            claim = getattr(event, "record", None)
            if claim is None:
                continue
            claim_id = getattr(claim, "claim_id", "")
            if claim_id in candidate.required_claim_ids:
                wp_id = getattr(claim.scope, "work_package_id", "")
                pkg = work_packages.get(wp_id)
                if pkg is not None:
                    return pkg
    # Fallback: use the candidate's own scope work package
    own_wp = work_packages.get(candidate.scope.work_package_id, {})
    if own_wp:
        return own_wp
    raise ValueError(
        "NEEDS_EVIDENCE candidate cannot derive its gating work package "
        "from required claims or candidate scope"
    )


def _candidate_projection(
    *,
    role: str,
    fixture: ConstructionDemoProjectFixture,
    runtime_packet: Mapping[str, Any],
    work_packages: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate = _candidate_by_title(fixture, _ROLE_TITLES[role])
    artifact = ConstructionCoordinationCandidateArtifact(
        candidate=candidate,
        base_state_digest=fixture.state.state_digest,
    )
    assessment = _assessment_by_id(runtime_packet).get(candidate.candidate_id)
    if assessment is None:
        raise ValueError("Construction candidate lacks its exact evaluation assessment")
    blockers = tuple(str(item) for item in assessment.get("blockers", []))
    readiness_reports = assessment.get("readiness_reports")
    if not isinstance(readiness_reports, list):
        raise ValueError("candidate readiness reports must be an array")
    claim_total = len(candidate.required_claim_ids)
    claim_ready = sum(
        1
        for item in readiness_reports
        if isinstance(item, Mapping) and item.get("ready") is True
    )
    open_obligations: list[str] = []
    if role == "HARD_BLOCKED":
        open_obligations.extend(blockers or ("hard blocker remains open",))
    elif role == "NEEDS_EVIDENCE":
        # Derive the work package from the candidate's required claims rather
        # than hardcoding a package ID.  Each required claim's scope carries
        # the work_package_id whose inspections gate this candidate.
        package = _needs_evidence_package(
            candidate, fixture, work_packages
        )
        for inspection in package.get("inspections", []):
            if inspection.get("status") != "PASSED":
                open_obligations.append(
                    f"inspection:{inspection.get('inspection_id')}:{inspection.get('status')}"
                )
        open_obligations.append("professional review remains external")
    else:
        open_obligations.append("authorized owner review remains external")

    evidence_open = [
        item for item in open_obligations if "review remains external" not in item
    ]
    closure_total = claim_total + len(evidence_open)
    closure_satisfied = claim_ready
    if closure_total == 0:
        closure_total = 1
        closure_satisfied = 1
    expected_status = (
        "HARD_BLOCKED"
        if assessment.get("admissible") is not True
        else "NEEDS_EVIDENCE"
        if evidence_open
        else "READY_FOR_HUMAN_REVIEW"
    )
    if expected_status != role:
        raise ValueError(f"candidate role changed from {role} to {expected_status}")
    return {
        "role": role,
        "artifact": artifact.to_dict(),
        "assessment": dict(assessment),
        "assessment_render_policy": "EXACT_EVIDENCE_AND_STATUS_ONLY_NO_PERCENTAGE",
        "closure_count": closure_satisfied,
        "closure_total": closure_total,
        "open_obligations": sorted(set(open_obligations)),
        "schedule_delta_hours": candidate.projected_time_delta_hours,
        "budget_delta_cad": candidate.projected_cost_delta_cad,
        "idle_time_delta_hours": candidate.projected_idle_delta_hours,
        "measurement_class": candidate.measurement_class,
        "recommended_for_human_review": role == "READY_FOR_HUMAN_REVIEW",
        "physical_work_authorized": False,
        "professional_approval": False,
        "payment_released": False,
        "access_granted": False,
        "automatic_execution": False,
    }


def _scene_entity_id(scene: SpatialSceneSnapshot, metadata_key: str, expected: str) -> str:
    matches = [
        item.entity_id
        for item in scene.entities
        if str(dict(item.metadata).get(metadata_key) or "") == expected
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Spatial scene does not contain one exact {metadata_key}={expected!r} entity"
        )
    return matches[0]


def _as_built_packet(
    fixture: ConstructionDemoProjectFixture,
    scene: SpatialSceneSnapshot,
) -> dict[str, Any]:
    device = compile_spatial_device_profile(
        profile_id="device:construction-foundry-p3-as-built",
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
        source_refs=("source:construction-foundry-p3-as-built",),
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
        "version": CONSTRUCTION_AS_BUILT_PACKET_VERSION,
        "tour": "p3-decision-lane",
        "tour_steps": [],
        "scene": scene.to_dict(),
        "render_plan": plan.to_dict(),
        "state_digest": fixture.state.state_digest,
        "runtime_bound": True,
        "fixture_digest": fixture.fixture_digest,
        "asset_pack_digest": fixture.asset_pack.asset_pack_digest,
        "fallback_asset_pack": True,
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


@dataclass(frozen=True)
class ConstructionFoundryDecisionCompiler:
    """Compile exact, disposable P3 decision-lane projections."""

    manifest: PascalSceneArtifactManifest
    coordinate_receipt: AuraPascalCoordinateReceipt
    asset_pack_path: Path | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, PascalSceneArtifactManifest):
            raise ValueError("manifest must be an exact PascalSceneArtifactManifest")
        if not isinstance(self.coordinate_receipt, AuraPascalCoordinateReceipt):
            raise ValueError(
                "coordinate_receipt must be an exact AuraPascalCoordinateReceipt"
            )
        self.manifest.__post_init__()
        self.coordinate_receipt.__post_init__()
        if self.coordinate_receipt.pascal_artifact_digest != self.manifest.artifact_digest:
            raise ValueError("coordinate receipt belongs to another Pascal artifact")

    def _fixture(self) -> tuple[ConstructionDemoProjectFixture, bool]:
        asset_pack, fallback = load_construction_demo_asset_pack(self.asset_pack_path)
        return build_construction_demo_project_fixture(asset_pack), fallback

    def exact_identities(self) -> dict[str, str]:
        fixture, _fallback = self._fixture()
        runtime_packet = build_construction_demo_runtime_packet(fixture)
        purpose_digest = stable_digest(
            {
                "objective": "present the P3 Construction decision lane for authorized human review",
                "state_digest": fixture.state.state_digest,
                "runtime_packet_digest": stable_digest(runtime_packet, digest_size=32),
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            },
            digest_size=32,
        )
        scene = project_construction_demo_to_scene(
            fixture,
            runtime_packet,
            purpose_digest=purpose_digest,
            scene_id="construction-foundry-p3-as-built",
        )
        return {
            "state_digest": fixture.state.state_digest,
            "runtime_packet_digest": stable_digest(runtime_packet, digest_size=32),
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "as_built_scene_digest": scene.scene_digest,
        }

    def compile(
        self,
        *,
        active_view: str = "DESIGN",
        selected_storey: str | None = None,
        selected_node: str | None = None,
        selected_issue_id: str | None = None,
        selected_candidate_id: str | None = None,
        selected_candidate_digest: str | None = None,
        timeline_day: float = 12.0,
    ) -> dict[str, Any]:
        view = _view(active_view)
        day = _finite(timeline_day, "timeline_day")
        if not 0.0 <= day <= 30.0:
            raise ValueError("timeline_day must be between 0 and 30")
        storey_id = selected_storey or self.manifest.storey_ids[0]
        if storey_id not in self.manifest.storey_ids:
            raise PascalPresentationError(
                "selected storey is not admitted by the Pascal artifact"
            )
        binding = (
            self.manifest.binding_for_node(selected_node)
            if selected_node is not None
            else self.manifest.first_selectable_on_storey(storey_id)
        )
        if binding.storey_id != storey_id:
            raise PascalPresentationError(
                "hidden-storey Pascal target selection is forbidden"
            )
        if not binding.selectable:
            raise PascalPresentationError("selected Pascal node is not selectable")

        fixture, fallback = self._fixture()
        if fallback is not True:
            raise ValueError(
                "generated asset-pack browser decoding is not implemented for the offline P3 lane"
            )
        runtime_packet = build_construction_demo_runtime_packet(fixture)
        runtime_packet_digest = stable_digest(runtime_packet, digest_size=32)
        purpose_digest = stable_digest(
            {
                "objective": "present the P3 Construction decision lane for authorized human review",
                "state_digest": fixture.state.state_digest,
                "runtime_packet_digest": runtime_packet_digest,
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            },
            digest_size=32,
        )
        as_built_scene = project_construction_demo_to_scene(
            fixture,
            runtime_packet,
            purpose_digest=purpose_digest,
            scene_id="construction-foundry-p3-as-built",
        )
        work_packages, work_package_by_id = _work_package_rows(
            fixture,
            self.manifest,
            as_built_scene,
        )
        issue_id = selected_issue_id or fixture.focus_scope.work_package_id
        selected_issue = work_package_by_id.get(issue_id)
        if selected_issue is None:
            raise ValueError("selected issue is not admitted by the P3 decision lane")
        # Bind the selected issue to the selected Pascal storey/node.  The
        # issue's presentation_storey_id and pascal_node_id must match the
        # independently selected Pascal binding, otherwise the compare receipt
        # would claim unrelated targets are synchronized.  When the caller
        # explicitly selects an issue, its Pascal binding must match.  When
        # no issue is specified, derive the Pascal binding from the issue's
        # work package instead of accepting an unrelated default.
        if selected_issue_id is not None:
            if (
                selected_issue["presentation_storey_id"] != storey_id
                or selected_issue["pascal_node_id"] != binding.node_id
            ):
                raise PascalPresentationError(
                    "selected issue does not bind to the selected Pascal storey/node"
                )
        else:
            # No explicit issue selection — override the default Pascal
            # binding with the issue's canonical presentation targets.
            storey_id = selected_issue["presentation_storey_id"]
            binding = self.manifest.binding_for_node(
                selected_issue["pascal_node_id"]
            )

        candidates = [
            _candidate_projection(
                role=role,
                fixture=fixture,
                runtime_packet=runtime_packet,
                work_packages=work_package_by_id,
            )
            for role in (
                "HARD_BLOCKED",
                "NEEDS_EVIDENCE",
                "READY_FOR_HUMAN_REVIEW",
            )
        ]
        recommended = next(
            item for item in candidates if item["recommended_for_human_review"]
        )
        if selected_candidate_id is not None:
            selected_rows = [
                item
                for item in candidates
                if item["artifact"]["candidate_id"] == selected_candidate_id
            ]
            if len(selected_rows) != 1:
                raise ValueError(
                    "selected candidate is not admitted by the P3 decision lane"
                )
            selected_candidate = selected_rows[0]
        else:
            selected_candidate = recommended
        if (
            selected_candidate_digest is not None
            and selected_candidate_digest
            != selected_candidate["artifact"]["candidate_digest"]
        ):
            raise ValueError("selected candidate digest is stale or belongs to another candidate")

        decision = DomainDecisionEnvelope(
            status="READY_FOR_HUMAN_REVIEW",
            candidate_id=recommended["artifact"]["candidate_id"],
            candidate_digest=recommended["artifact"]["candidate_digest"],
            recommended_for_human_review=True,
            reasons=(
                "hard guards were applied before ranking",
                "the drilling hold is preserved",
                "dispositive evidence and domain authority remain external",
            ),
            open_obligations=("authorized owner review remains external",),
        )
        compare_receipt_body = {
            "version": CONSTRUCTION_COMPARE_RECEIPT_VERSION,
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "pascal_coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "pascal_spatial_scene_digest": self.coordinate_receipt.spatial_scene_digest,
            "as_built_scene_digest": as_built_scene.scene_digest,
            "synchronization": {
                "presentation_storey": storey_id,
                "selected_pascal_node": binding.node_id,
                "pascal_aura_target_ref": binding.aura_target_ref,
                "selected_issue_id": issue_id,
                "as_built_frame_id": selected_issue["as_built_frame_id"],
                "timeline_day": day,
            },
            "split_screen_only": True,
            "same_canvas_depth_composition": False,
            "visual_alignment_only": True,
            "survey_authority": False,
            "construction_truth": False,
        }
        compare_receipt = {
            **compare_receipt_body,
            "receipt_digest": stable_digest(compare_receipt_body, digest_size=32),
        }

        issue_interaction = compile_spatial_interaction(
            as_built_scene,
            action=SpatialInteractionAction.FOCUS,
            target_entity_ids=(selected_issue["spatial_entity_id"],),
            metadata={
                "active_view": view,
                "timeline_day": day,
                "selected_issue_id": issue_id,
                "presentation_storey_id": storey_id,
                "pascal_node_id": binding.node_id,
            },
        )
        candidate_title = selected_candidate["artifact"]["title"]
        matching_alternatives = [
            item for item in fixture.alternatives if item.title == candidate_title
        ]
        if len(matching_alternatives) != 1:
            raise ValueError(
                "selected Construction candidate lacks one exact presentation alternative"
            )
        candidate_entity_id = _scene_entity_id(
            as_built_scene,
            "alternative_ref",
            matching_alternatives[0].alternative_id,
        )
        candidate_interaction = compile_spatial_interaction(
            as_built_scene,
            action=SpatialInteractionAction.SELECT,
            target_entity_ids=(candidate_entity_id,),
            metadata={
                "selected_candidate_digest": selected_candidate["artifact"][
                    "candidate_digest"
                ],
                "review_only": True,
            },
        )
        as_built_packet = _as_built_packet(fixture, as_built_scene)

        body = {
            "version": CONSTRUCTION_FOUNDRY_DECISION_VERSION,
            "domain": {
                "arena_id": "construction",
                "domain_type": "CONSTRUCTION_DECISION",
                "state_digest": fixture.state.state_digest,
                "runtime_packet_digest": runtime_packet_digest,
                "fixture_digest": fixture.fixture_digest,
                "asset_pack_digest": fixture.asset_pack.asset_pack_digest,
                "fallback_asset_pack": fallback,
                "privacy_class": "PROJECT",
            },
            "artifacts": {
                "pascal_artifact_digest": self.manifest.artifact_digest,
                "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
                "pascal_spatial_scene_digest": self.coordinate_receipt.spatial_scene_digest,
                "as_built_scene_digest": as_built_scene.scene_digest,
                "compare_receipt": compare_receipt,
            },
            "presentation": {
                "available_views": sorted(_ALLOWED_VIEWS),
                "active_view": view,
                "selected_storey": storey_id,
                "selected_node": binding.node_id,
                "selected_entity": binding.aura_entity_id,
                "selected_target_ref": binding.aura_target_ref,
                "selected_issue_id": issue_id,
                "selected_issue_spatial_entity_id": selected_issue["spatial_entity_id"],
                "selected_domain_storey_id": selected_issue["domain_storey_id"],
                "as_built_frame_id": selected_issue["as_built_frame_id"],
                "selected_candidate_id": selected_candidate["artifact"]["candidate_id"],
                "selected_candidate_digest": selected_candidate["artifact"][
                    "candidate_digest"
                ],
                "timeline_day": day,
                "camera_target": {
                    "pascal_entity_id": binding.aura_entity_id,
                    "as_built_entity_id": selected_issue["spatial_entity_id"],
                    "as_built_frame_id": selected_issue["as_built_frame_id"],
                },
                "selection_survives_view_switch": True,
                "design_truth_class": "PROPOSAL",
                "as_built_truth_class": "DERIVED_PRESENTATION",
            },
            "domain_targets": [
                {
                    "target_id": item.node_id,
                    "target_type": item.node_kind,
                    "canonical_ref": item.aura_target_ref,
                    "aura_entity_id": item.aura_entity_id,
                    "storey_id": item.storey_id,
                    "selectable": item.selectable,
                    "truth_class": "PRESENTATION",
                }
                for item in self.manifest.node_bindings
            ],
            "construction": {
                "work_packages": work_packages,
                "geofences": [
                    {
                        "geofence_id": f"presentation-zone:{item.zone_id}",
                        "zone_id": item.zone_id,
                        "storey_id": item.storey_id,
                        "truth_class": "SYNTHETIC_DEMO_PRESENTATION",
                        "survey_authority": False,
                        "access_authority": False,
                    }
                    for item in fixture.work_packages
                ],
                "crew_projection": [
                    {
                        "trade_id": item.trade_id,
                        "trade_name": item.name,
                        "subcontractor_id": item.subcontractor_id,
                        "person_level_data_included": False,
                        "crew_count_claimed": False,
                        "projection_only": True,
                    }
                    for item in fixture.trades
                ],
                "schedule_projection": [
                    {
                        "work_package_id": item["work_package_id"],
                        "planned_start_day": item["planned_start_day"],
                        "planned_finish_day": item["planned_finish_day"],
                        "dependency_ids": item["dependency_ids"],
                        "projection_only": True,
                    }
                    for item in work_packages
                ],
                "material_staging": [
                    {
                        "staging_id": f"staging:{item['work_package_id']}",
                        "work_package_id": item["work_package_id"],
                        "storey_id": item["domain_storey_id"],
                        "zone_id": item["zone_id"],
                        "truth_class": "SYNTHETIC_DEMO_PRESENTATION",
                        "physical_work_authorized": False,
                    }
                    for item in work_packages
                    if item["status"] in {"READY_FOR_REVIEW", "ACTIVE"}
                ],
                "waste_and_bin_zones": [
                    {
                        "zone_id": f"waste-bin:{storey_id}",
                        "storey_id": storey_id,
                        "truth_class": "SYNTHETIC_DEMO_PRESENTATION",
                        "access_authority": False,
                    }
                    for storey_id in sorted(
                        {item["domain_storey_id"] for item in work_packages}
                    )
                ],
                "trades": [item.to_dict() for item in fixture.trades],
                "inspections": [item.to_dict() for item in fixture.inspections],
                "hazards": [item.to_dict() for item in fixture.hazards],
                "rules": [item.to_dict() for item in fixture.rules],
                "work_history": [item.to_dict() for item in fixture.work_history],
                "evidence_pins": [
                    {
                        "work_package_id": item["work_package_id"],
                        "construction_scope_ref": item["construction_scope_ref"],
                        "spatial_entity_id": item["spatial_entity_id"],
                        "domain_storey_id": item["domain_storey_id"],
                        "as_built_frame_id": item["as_built_frame_id"],
                        "presentation_storey_id": item["presentation_storey_id"],
                        "pascal_node_id": item["pascal_node_id"],
                        "pascal_aura_target_ref": item["pascal_aura_target_ref"],
                        "evidence_refs": item["evidence_refs"],
                        "inspection_ids": [
                            row["inspection_id"] for row in item["inspections"]
                        ],
                        "hazard_ids": [row["hazard_id"] for row in item["hazards"]],
                        "authority_owner": "AUTHORIZED_DOMAIN_REVIEW",
                        "visual_truth": False,
                    }
                    for item in work_packages
                    if item["evidence_refs"] or item["inspections"] or item["hazards"]
                ],
                "overlays": {
                    "work_packages": True,
                    "hazards": True,
                    "geofences": True,
                    "inspections": True,
                    "dependencies": True,
                    "crews": True,
                    "budget": True,
                    "schedule": True,
                    "material_staging": True,
                    "waste_and_bin_zones": True,
                },
            },
            "spatial_interactions": {
                "selected_issue_focus": issue_interaction.to_dict(),
                "selected_candidate_review": candidate_interaction.to_dict(),
            },
            "coordination_candidates": candidates,
            "domain_decision": decision.to_dict(),
            "authority": {
                "visual_truth": False,
                "construction_truth_owner": "ConstructionProjectState",
                "survey_authority": False,
                "professional_approval": False,
                "physical_work_authorized": False,
                "payment_released": False,
                "access_granted": False,
                "automatic_execution": False,
                "source_records_mutated": False,
                "construction_event_appended": False,
                "human_review_required": True,
            },
            "dikwp_provenance": {
                "enabled": False,
                "reason": (
                    "optional DIKWP projection remains deferred because no current canonical "
                    "DIKWPEnvelope owner was resolved in the exact P3 source neighborhood"
                ),
                "truth_owner_changed": False,
            },
        }
        projection_digest = stable_digest(body, digest_size=32)
        export_body = {
            "version": CONSTRUCTION_DECISION_EXPORT_VERSION,
            "projection_digest": projection_digest,
            "state_digest": fixture.state.state_digest,
            "runtime_packet_digest": runtime_packet_digest,
            "pascal_artifact_digest": self.manifest.artifact_digest,
            "coordinate_receipt_digest": self.coordinate_receipt.receipt_digest,
            "as_built_scene_digest": as_built_scene.scene_digest,
            "decision": decision.to_dict(),
            "candidate_digests": [
                item["artifact"]["candidate_digest"] for item in candidates
            ],
            "selected_candidate": {
                "candidate_id": selected_candidate["artifact"]["candidate_id"],
                "candidate_digest": selected_candidate["artifact"]["candidate_digest"],
                "role": selected_candidate["role"],
                "title": selected_candidate["artifact"]["title"],
            },
            "presentation_state": {
                "active_view": view,
                "selected_storey": storey_id,
                "selected_node": binding.node_id,
                "selected_issue_id": issue_id,
                "timeline_day": day,
            },
            "source_records_mutated": False,
            "construction_event_appended": False,
            "physical_work_authorized": False,
            "professional_approval": False,
            "payment_released": False,
            "access_granted": False,
            "automatic_execution": False,
            "human_review_required": True,
            "canonical_project_record": False,
            "approved_change_order": False,
        }
        export_json = (canonical_json(export_body) + "\n").encode("utf-8")
        export_pdf = _minimal_pdf(
            [
                "AuraOS P3 Construction Decision Support",
                f"Projection: {projection_digest}",
                f"Construction state: {fixture.state.state_digest}",
                f"Pascal artifact: {self.manifest.artifact_digest}",
                f"Coordinate receipt: {self.coordinate_receipt.receipt_digest}",
                f"As-built scene: {as_built_scene.scene_digest}",
                f"Recommended candidate: {decision.candidate_id}",
                f"Selected candidate: {selected_candidate['artifact']['candidate_id']}",
                f"Selected candidate role: {selected_candidate['role']}",
                f"Active view: {view}",
                f"Selected storey: {storey_id}",
                f"Selected node: {binding.node_id}",
                f"Selected issue: {issue_id}",
                f"Timeline day: {day}",
                "Status: READY_FOR_HUMAN_REVIEW (not approval)",
                "Physical work authorized: false",
                "Professional approval: false",
                "Payment released: false",
                "Access granted: false",
                "Automatic execution: false",
            ]
        )
        as_built_json = (canonical_json(as_built_packet) + "\n").encode("utf-8")
        return {
            **body,
            "projection_digest": projection_digest,
            "exports": {
                "json_sha256": sha256_digest(export_json),
                "pdf_sha256": sha256_digest(export_pdf),
                "ifc_export_sha256": None,
                "pascal_export_sha256": self.manifest.scene_json_sha256,
                "canonical_project_record": False,
                "approved_change_order": False,
            },
            "_export_json": export_json,
            "_export_pdf": export_pdf,
            "_as_built_packet_json": as_built_json,
        }


def public_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    """Remove server-local byte payloads from a compiled projection."""
    return {key: item for key, item in value.items() if not key.startswith("_")}


__all__ = [
    "CONSTRUCTION_AS_BUILT_PACKET_VERSION",
    "CONSTRUCTION_COMPARE_RECEIPT_VERSION",
    "CONSTRUCTION_DECISION_EXPORT_VERSION",
    "CONSTRUCTION_FOUNDRY_DECISION_VERSION",
    "ConstructionFoundryDecisionCompiler",
    "public_projection",
]
