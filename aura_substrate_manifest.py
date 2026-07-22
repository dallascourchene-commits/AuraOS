"""Deterministic P1-P8 cognitive-substrate manifest for P9."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from aura_event_contracts import canonical_json
from aura_substrate_contracts import (
    CompatibilityMode,
    ContractStatus,
    FileRole,
    MigrationStatus,
    PhaseDisposition,
    SubstrateFileRecord,
    SubstrateManifest,
)

MANIFEST_PATH = Path("docs/aura_substrate_manifest.v1.json")
RELEASE_INDEX_PATH = Path("docs/aura_substrate_release_index.v1.json")


def _file(
    path: str,
    role: FileRole,
    phase_ids: tuple[str, ...],
    sha1: str | None = None,
    symbols: tuple[str, ...] = (),
    versions: tuple[tuple[str, str], ...] = (),
) -> SubstrateFileRecord:
    return SubstrateFileRecord(
        path=path,
        role=role,
        phase_ids=phase_ids,
        public_symbols=symbols,
        version_bindings=versions,
        expected_git_blob_sha1=sha1,
        release_included=True,
    )


_FILE_ROWS = (
    ("aura_arena_st3gg_shadow.py", FileRole.DOMAIN_SHADOW, ("P5.2",), "76762e5699aa321815ba9a925346f8ea5cb0414c", ("ArenaST3GGV2ShadowComparison", "ArenaST3GGShadowResult", "encode_arena_capsule_with_v2_shadow"), (("ARENA_ST3GG_SHADOW_VERSION", "AURA_ARENA_ST3GG_V2_SHADOW_P5_2"),)),
    ("aura_civic_planning.py", FileRole.DOMAIN_SHADOW, ("P8",), "9c1c0342d182d56fdfd9563ceb4455617935d95a", ("CivicProjectionError", "inspect_civic_commons_planning_compatibility"), ()),
    ("aura_civic_planning_inventory.py", FileRole.INTEGRITY_HELPER, ("P8",), "4ab77a7d829234b8b96a23219f91da542f34b99d", ("build_civic_surface_inventory",), ()),
    ("aura_civic_planning_types.py", FileRole.DOMAIN_SHADOW, ("P8",), "fee2a4f1a9142b7e7dfb525db7926fc458434830", ("CivicCompatibilityReport", "CivicPlanningInspection", "CivicSurfaceInventory"), (("CIVIC_P8_VERSION", "AURA_CIVIC_PLANNING_P8"), ("CIVIC_INVENTORY_VERSION", "AURA_CIVIC_SURFACE_INVENTORY_P8"))),
    ("aura_coding_arena_planning.py", FileRole.DOMAIN_SHADOW, ("P7",), "2372f81bd21fef2af808b2dede9397bb901216d0", ("CodingArenaProjectionError", "inspect_coding_arena_planning_compatibility"), ()),
    ("aura_coding_arena_planning_integrity.py", FileRole.INTEGRITY_HELPER, ("P7",), "a207df7956922ae3528364e09c7df883468abd54", ("validate_legacy_coding_arena_integrity",), ()),
    ("aura_coding_arena_planning_types.py", FileRole.DOMAIN_SHADOW, ("P7",), "fd674a28d99fe5364daad38d4d36451c5d84d7af", ("CodingArenaCompatibilityReport", "CodingArenaPlanningInspection"), (("CODING_ARENA_PLANNING_VERSION", "AURA_CODING_ARENA_PLANNING_P7"), ("CODING_ARENA_COMPATIBILITY_VERSION", "AURA_CODING_ARENA_COMPATIBILITY_P7"))),
    ("aura_continuity_packet.py", FileRole.CANONICAL_CONTRACT, ("P4.1",), "1a18610802138ca9d634a20608a627077a811841", ("J2RouteView", "J2ArenaView", "J2ContinuityPacket"), (("J2_CONTINUITY_VERSION", "AURA_CONTINUITY_PACKET_J2"),)),
    ("aura_event_contracts.py", FileRole.CANONICAL_CONTRACT, ("P1", "P1.1", "P3.1", "P6.1"), "c47913af0adcb35edaadc5a4c17b0613e4f3df73", ("AuraEventEnvelope", "ToolDecisionRecord", "ToolResultRecord", "AppendOnlyEventStore"), (("EVENT_CONTRACTS_VERSION", "AURA_EVENT_CONTRACTS_V1"),)),
    ("aura_exact_record_identity.py", FileRole.INTEGRITY_HELPER, ("P8",), "eee65c7abe5e807ed3e35a10093159ac31952792", ("ExactRecordIdentityError", "require_exact_copied_fields"), ()),
    ("aura_planning_board.py", FileRole.CANONICAL_CONTRACT, ("P2.1", "P7", "P8"), "a248b7e875760b46f5707dc5c517935ff9996128", ("GoalSpec", "ActionSpec", "PlanningBoard", "verify_board_continuity"), (("PLANNING_BOARD_VERSION", "AURA_PLANNING_BOARD_V1"),)),
    ("aura_planning_events.py", FileRole.READ_ONLY_PROJECTOR, ("P3.1",), "a591088f8f524e40bfcffdb427c4028d916536ad", ("PlanningEventKind", "PlanningEventReceipt"), (("PLANNING_EVENT_PROJECTION_VERSION", "AURA_PLANNING_EVENT_PROJECTION_V1"),)),
    ("aura_planning_frontier.py", FileRole.READ_ONLY_PROJECTOR, ("P2.3",), "52e50fbd00abaa4d883060c0e085594e13d1ad94", ("CandidateConvergence", "FrontierConvergenceReport"), (("FRONTIER_VERSION", "AURA_PLANNING_FRONTIER_V1"),)),
    ("aura_planning_projector.py", FileRole.READ_ONLY_PROJECTOR, ("P3.2",), "5c83d21c226105ad11fa86b59cf6c005a07f18c6", ("ProjectionFinding", "PlanningHistoryChain"), (("PLANNING_PROJECTOR_VERSION", "AURA_PLANNING_PROJECTOR_V1"),)),
    ("aura_planning_regression.py", FileRole.READ_ONLY_PROJECTOR, ("P2.2",), "401b69f94b0dd3c86076eaa01f45de2927a45175", ("RegressionCandidate", "RegressionReport"), (("REGRESSION_VERSION", "AURA_PLANNING_REGRESSION_V1"),)),
    ("aura_qdkt_compatibility.py", FileRole.COMPATIBILITY_FACADE, ("P6.2",), "7461a24db74577308e6e668f9bdd1d0ce18e21fe", ("qdkt_ownership_recommendation",), ()),
    ("aura_qdkt_compatibility_types.py", FileRole.COMPATIBILITY_FACADE, ("P6.2",), "cebaf0ffb70e9e9c8a5a08b6a839ba75d0ad8742", ("QDKTInventoryEntry", "QDKTDualReadStatus"), (("QDKT_COMPATIBILITY_VERSION", "AURA_QDKT_COMPATIBILITY_P6_2"), ("QDKT_RECOMMENDATION", "RETAIN_LEGACY_DUAL_READ"))),
    ("aura_qdkt_inventory.py", FileRole.INTEGRITY_HELPER, ("P6.2",), "016b859e132ee42b9aca22e28bf00a25ed2f84a7", (), ()),
    ("aura_qdkt_observations.py", FileRole.CANONICAL_CONTRACT, ("P6.1",), "237e7d2c98e41990b6cd45845c8a2b0050b5b54f", ("QDKTObservation", "QDKTTruthClass"), (("QDKT_EVENT_VERSION", "AURA_QDKT_EVENTS_P6_1"), ("QDKT_GENERATOR_VERSION", "QUANTUM_MERKLE_DAG_V1"))),
    ("aura_qdkt_projection.py", FileRole.READ_ONLY_PROJECTOR, ("P6.1", "P6.2"), "9541a130838829c374154612ccf05d3e1de41576", ("project_qdkt_events",), ()),
    ("aura_qdkt_projection_io.py", FileRole.INTEGRITY_HELPER, ("P6.1", "P6.2"), "61097dd5a14f7f045653986f53216d7e9af5b25b", ("FindingCollector",), ()),
    ("aura_qdkt_projection_types.py", FileRole.READ_ONLY_PROJECTOR, ("P6.1",), "5e38627788ded8d6c905cf6e2fcd636994bee328", ("ProjectedQDKTEvent", "QDKTProjectionReport"), (("QDKT_PROJECTOR_VERSION", "AURA_QDKT_PROJECTOR_P6_1"),)),
    ("aura_relational_authority.py", FileRole.CANONICAL_CONTRACT, ("P1.1",), "bb7ad9ac2aeb4310050fbec394645aad2d1f0f32", ("AuthorityGrant", "ApprovalAttestation", "QuorumPolicy", "GovernanceDecision"), (("AUTHORITY_CONTRACTS_VERSION", "AURA_RELATIONAL_AUTHORITY_V1"),)),
    ("aura_shadow_tool_observability.py", FileRole.COMPATIBILITY_FACADE, ("P1",), "8a0dcbd57835283568a3a0275c4245485c4529b8", ("ObservedToolCall", "invoke_tool_shadow"), (("SHADOW_OBSERVABILITY_VERSION", "AURA_SHADOW_TOOL_OBSERVABILITY_V1"),)),
    ("aura_st3gg_compatibility.py", FileRole.COMPATIBILITY_FACADE, ("P5.3",), "4ccad6845fe95a991a3997f5bf605e31a899e044", ("encode_source_with_v2_facade", "compress_report_with_v2_facade", "p5_3_legacy_disposition"), ()),
    ("aura_st3gg_compatibility_recall.py", FileRole.INTEGRITY_HELPER, ("P5.3",), "f342e8632e5380aec222245b1e54ca44ea335071", ("dual_read_st3gg_recall",), ()),
    ("aura_st3gg_compatibility_types.py", FileRole.COMPATIBILITY_FACADE, ("P5.3",), "219d0df3caf76344bc1bccea93cec016bc9f14bc", ("ST3GGLegacyDisposition", "ST3GGCanonicalBinding", "ST3GGRecallDualReadEvidence"), (("ST3GG_COMPATIBILITY_VERSION", "AURA_ST3GG_COMPATIBILITY_P5_3"), ("EXECUTION_MODE", "OPT_IN_COMPATIBILITY"))),
    ("aura_st3gg_contracts.py", FileRole.CANONICAL_CONTRACT, ("P5.1", "P5.2", "P5.3"), "2f3cfde20fe6b171a9dc4326075bc607331d7c6b", ("ST3GGDecision", "ST3GGExactRecallRecord", "ST3GGSavingsPolicy", "prepare_st3gg_artifact"), (("ST3GG_CONTRACT_VERSION", "AURA_ST3GG_CONTRACT_V2"),)),
    ("aura_substrate_contracts.py", FileRole.RELEASE_TOOLING, (), None, ("SubstrateManifest", "VerificationReport"), (("SUBSTRATE_MANIFEST_VERSION", "AURA_SUBSTRATE_MANIFEST_P9_V1"), ("SUBSTRATE_RELEASE_INDEX_VERSION", "AURA_SUBSTRATE_RELEASE_INDEX_P9_V1"), ("SUBSTRATE_VERIFIER_VERSION", "AURA_SUBSTRATE_VERIFIER_P9_V1"))),
    ("aura_substrate_manifest.py", FileRole.RELEASE_TOOLING, (), None, ("build_substrate_manifest", "write_manifest"), ()),
    ("aura_substrate_release.py", FileRole.RELEASE_TOOLING, (), None, ("build_release_index", "write_release_index"), ()),
    ("aura_substrate_verifier.py", FileRole.RELEASE_TOOLING, (), None, ("verify_substrate_release",), ()),
    ("aura_workflow_gates.py", FileRole.COMPATIBILITY_FACADE, ("P1.1",), "0e138b814a5e21f8345cbcde73859e220240203f", ("evaluate_gate", "workflow_state_machine"), ()),
    ("docs/AURA_COGNITIVE_SUBSTRATE_P9.md", FileRole.PUBLIC_DOCUMENTATION, (), None, (), ()),
    ("docs/AURA_SUBSTRATE_INTEGRATION_P9.md", FileRole.PUBLIC_DOCUMENTATION, (), None, (), ()),
    ("docs/AURA_SUBSTRATE_PHASE_DISPOSITIONS_P9.md", FileRole.PUBLIC_DOCUMENTATION, (), None, (), ()),
    ("docs/AURA_SUBSTRATE_RELEASE_CHECKLIST_P9.md", FileRole.PUBLIC_DOCUMENTATION, (), None, (), ()),
    ("docs/AURA_SUBSTRATE_SECURITY_PRIVACY_P9.md", FileRole.PUBLIC_DOCUMENTATION, (), None, (), ()),
)

_FILES = tuple(sorted((_file(*row) for row in _FILE_ROWS), key=lambda item: item.path))


def _phase(
    phase_id: str,
    title: str,
    source_pr: int,
    merge_commit: str,
    components: tuple[str, ...],
    dependencies: tuple[str, ...],
    evidence: tuple[str, ...],
    contract_status: ContractStatus,
    compatibility_mode: CompatibilityMode,
    migration_status: MigrationStatus,
    live_owner: str,
    disposition: str,
    retained: tuple[str, ...] = (),
) -> PhaseDisposition:
    return PhaseDisposition(
        phase_id=phase_id,
        title=title,
        source_pr=source_pr,
        merge_commit=merge_commit,
        component_paths=components,
        dependencies=dependencies,
        evidence_paths=evidence,
        retained_dependency_paths=retained,
        contract_status=contract_status,
        compatibility_mode=compatibility_mode,
        migration_status=migration_status,
        live_owner=live_owner,
        ownership_disposition=disposition,
    )


_PHASE_ROWS = (
    ("P1", "Canonical event and tool-decision contracts", 94, "4673842f8813db0f8e5c42e836c41f8c19f6f9fa", ("aura_event_contracts.py", "aura_shadow_tool_observability.py"), (), ("tests/test_aura_event_contracts.py", "tests/test_aura_shadow_tool_observability.py", ".github/workflows/ci.yml"), ContractStatus.CANONICAL, CompatibilityMode.ADDITIVE, MigrationStatus.CANONICAL_CONTRACT_ADOPTED, "aura_event_contracts.AppendOnlyEventStore", "CANONICAL_EVENT_CONTRACT_OWNER", ()),
    ("P1.1", "Privacy and relational authority hardening", 96, "efa2a8e6699d3cda99642fb4f1581d7598e3117d", ("aura_event_contracts.py", "aura_relational_authority.py", "aura_workflow_gates.py"), ("P1",), (".github/workflows/p1-1-authority-contracts.yml", "tests/test_aura_relational_authority.py", "tests/test_p1_1_adversarial_review.py"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.ADDITIVE, MigrationStatus.CANONICAL_CONTRACT_ADOPTED, "aura_relational_authority", "CANONICAL_AUTHORITY_CONTRACT", ()),
    ("P2.1", "Proposal-only Planning Board IR", 98, "8775edfec85ee8ab76253744da08d653692d5178", ("aura_planning_board.py",), ("P1", "P1.1"), (".github/workflows/p2-1-planning-board-contracts.yml", "tests/test_aura_planning_board.py"), ContractStatus.CANONICAL, CompatibilityMode.ADDITIVE, MigrationStatus.CANONICAL_CONTRACT_ADOPTED, "existing planners and domain owners", "RETAIN_EXISTING_PLANNERS", ("aura_relationship_contracts.py",)),
    ("P2.2", "Bounded backward regression", 101, "110c8b46230863bf4d6a3239e15caf0977e3516d", ("aura_planning_regression.py",), ("P2.1",), (".github/workflows/p2-2-planning-regression.yml", "tests/test_aura_planning_regression.py", "tests/test_aura_planning_regression_adversarial.py"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.READ_ONLY, MigrationStatus.CANONICAL_PROJECTION_ADOPTED, "existing planners and domain owners", "RETAIN_EXISTING_PLANNERS", ()),
    ("P2.3", "Forward symbolic replay and convergence", 103, "516f40da76e55bdfc9bb49e9b17f345af9e0d5bf", ("aura_planning_frontier.py",), ("P2.1", "P2.2"), (".github/workflows/p2-3-planning-frontier.yml", "tests/test_aura_planning_frontier.py"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.READ_ONLY, MigrationStatus.CANONICAL_PROJECTION_ADOPTED, "existing planners and domain owners", "RETAIN_EXISTING_PLANNERS", ()),
    ("P3.1", "Append-only planning event projection", 105, "307d27e49e428b3b0fe88271d612f8523d117171", ("aura_planning_events.py",), ("P1", "P2.1", "P2.2", "P2.3"), (".github/workflows/p3-1-planning-events.yml", "tests/test_aura_planning_events.py"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.ADDITIVE, MigrationStatus.CANONICAL_PROJECTION_ADOPTED, "aura_event_contracts.AppendOnlyEventStore", "APPEND_ONLY_EVENT_STORE_RETAINED", ()),
    ("P3.2", "Read-only planning history projector", 107, "cff6defa3166972bff472e1a28ce9d48ad28dda6", ("aura_planning_projector.py",), ("P3.1",), (".github/workflows/p3-2-planning-projector.yml", "tests/test_aura_planning_projector.py", "tests/test_aura_planning_projector_hardening.py"), ContractStatus.READ_ONLY_PROJECTION, CompatibilityMode.READ_ONLY, MigrationStatus.CANONICAL_PROJECTION_ADOPTED, "aura_event_contracts.AppendOnlyEventStore", "READ_ONLY_NO_REPAIR", ()),
    ("P4.1", "Canonical J2 continuity packet", 109, "c6acb538127b8e64982ce98164d4742f2eba9c7b", ("aura_continuity_packet.py",), ("P2.1", "P3.2"), (".github/workflows/p4-1-j2-continuity.yml", "tests/test_aura_continuity_packet.py", "tests/test_aura_continuity_packet_digest_hardening.py"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.ADDITIVE, MigrationStatus.LIVE_OWNER_RETAINED, "J0 and J1 writers and parsers", "RETAIN_J0_J1_COMPATIBILITY", ("aura_arena_state_packet.py", "aura_jspace_codec.py")),
    ("P5.1", "Canonical ST3GG V2 contracts", 111, "5868cf9b1a04f7a075b2b51115e69f8824710586", ("aura_st3gg_contracts.py",), ("P1",), (".github/workflows/p5-1-st3gg-contracts.yml", "tests/test_aura_st3gg_contracts.py", "docs/AURA_ST3GG_CANONICAL_CONTRACTS.md"), ContractStatus.CANONICAL, CompatibilityMode.ADDITIVE, MigrationStatus.LEGACY_OWNER_RETAINED, "legacy ST3GG writers and recall stores", "RETAIN_LEGACY_ST3GG_OWNERS", ("aura_tokenizer_guard.py",)),
    ("P5.2", "Arena ST3GG V2 verified shadow", 113, "52a60c3af71a4026fcb31c23407647b71783a055", ("aura_arena_st3gg_shadow.py", "aura_st3gg_contracts.py"), ("P5.1",), (".github/workflows/p5-2-st3gg-arena-shadow.yml", "tests/test_aura_arena_st3gg_shadow.py", "docs/AURA_ST3GG_ARENA_SHADOW_P5_2.md"), ContractStatus.VERIFIED_SHADOW, CompatibilityMode.SHADOW_ONLY, MigrationStatus.LEGACY_OWNER_RETAINED, "aura_arena_st3gg_codec and aura_st3gg_recall", "RETAIN_V1_SHADOW_V2", ("aura_arena_st3gg_codec.py", "aura_st3gg_recall.py")),
    ("P5.3", "Cross-surface ST3GG compatibility", 115, "64d55bede16abb6bd627d200b598f4274b7e778c", ("aura_st3gg_compatibility.py", "aura_st3gg_compatibility_recall.py", "aura_st3gg_compatibility_types.py", "aura_st3gg_contracts.py"), ("P5.1", "P5.2"), (".github/workflows/p5-3-st3gg-compatibility.yml", "tests/test_aura_st3gg_compatibility.py", "docs/AURA_ST3GG_COMPATIBILITY_P5_3.md"), ContractStatus.VERIFIED_COMPATIBILITY, CompatibilityMode.OPT_IN_COMPATIBILITY, MigrationStatus.LEGACY_OWNER_RETAINED, "aura_st3gg_recall", "RETAIN_V1", ("aura_arena_st3gg_egress.py", "aura_st3gg_codec.py", "aura_st3gg_recall.py")),
    ("P6.1", "Canonical QDKT observations and events", 117, "92369bdccfbb59dc97ce0f28050aed1b93841420", ("aura_qdkt_observations.py", "aura_qdkt_projection.py", "aura_qdkt_projection_io.py", "aura_qdkt_projection_types.py"), ("P1",), (".github/workflows/p6-1-qdkt-events.yml", "tests/test_aura_qdkt_observations.py", "tests/test_aura_qdkt_projection_core.py", "docs/AURA_QDKT_EVENTS_P6_1.md"), ContractStatus.CANONICAL_EXTENSION, CompatibilityMode.ADDITIVE, MigrationStatus.LEGACY_OWNER_RETAINED, "quantum_dag.QuantumMerkleDAG", "RETAIN_LEGACY_RESULT_OWNER", ("aura_relationship_experience.py", "quantum_dag.py")),
    ("P6.2", "QDKT inventory and dual-read compatibility", 119, "4d4b4d0a4799f18c7798794a70b5e808f3f00bf2", ("aura_qdkt_compatibility.py", "aura_qdkt_compatibility_types.py", "aura_qdkt_inventory.py", "aura_qdkt_projection.py", "aura_qdkt_projection_io.py"), ("P6.1",), (".github/workflows/p6-2-qdkt-compatibility.yml", "tests/test_aura_qdkt_compatibility.py", "tests/test_aura_qdkt_inventory.py", "docs/AURA_QDKT_COMPATIBILITY_P6_2.md"), ContractStatus.VERIFIED_COMPATIBILITY, CompatibilityMode.RETAINED_LEGACY_DUAL_READ, MigrationStatus.LEGACY_OWNER_RETAINED, "quantum_dag.QuantumMerkleDAG", "RETAIN_LEGACY_DUAL_READ", ("quantum_dag.py",)),
    ("P7", "Coding Arena Planning Board shadow", 121, "a2a880246e73563c7c55c4b0d99e59b17f514b26", ("aura_coding_arena_planning.py", "aura_coding_arena_planning_integrity.py", "aura_coding_arena_planning_types.py", "aura_planning_board.py"), ("P1.1", "P2.1"), (".github/workflows/p7-coding-arena-planning-board.yml", "tests/test_aura_coding_arena_planning.py", "tests/test_aura_coding_arena_planning_integrity.py", "docs/AURA_CODING_ARENA_PLANNING_BOARD_P7.md"), ContractStatus.VERIFIED_SHADOW, CompatibilityMode.SHADOW_ONLY, MigrationStatus.LIVE_OWNER_RETAINED, "aura_architect_loop and aura_liquid_planning_arena", "RETAIN_CODING_ARENA_OWNER", ("aura_architect_loop.py", "aura_liquid_planning_arena.py")),
    ("P8", "Civic Commons Planning Board shadow", 122, "ab91d1b019b3df902f86793e59c9695750f2b784", ("aura_civic_planning.py", "aura_civic_planning_inventory.py", "aura_civic_planning_types.py", "aura_exact_record_identity.py", "aura_planning_board.py"), ("P1.1", "P2.1"), (".github/workflows/p8-civic-commons-planning.yml", "tests/test_aura_civic_planning_packet_identity.py", "tests/test_aura_civic_planning_integration.py", "tests/test_aura_civic_planning_stress.py"), ContractStatus.VERIFIED_SHADOW, CompatibilityMode.READ_ONLY, MigrationStatus.LIVE_OWNER_RETAINED, "aura_civic_runtime", "RETAIN_CIVIC_COMMONS_OWNER", ("aura_civic_organs.py", "aura_civic_projects.py", "aura_civic_runtime.py", "aura_civic_session_store.py")),
)

_PHASES = tuple(_phase(*row) for row in _PHASE_ROWS)


def build_substrate_manifest() -> SubstrateManifest:
    return SubstrateManifest(
        files=_FILES,
        phases=_PHASES,
        retained_external_surfaces=("aura_substrate.py",),
    )


def write_manifest(path: str | Path = MANIFEST_PATH) -> dict[str, Any]:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_substrate_manifest().to_dict()
    output.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(MANIFEST_PATH))
    args = parser.parse_args()
    write_manifest(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MANIFEST_PATH", "RELEASE_INDEX_PATH", "build_substrate_manifest", "write_manifest"]
