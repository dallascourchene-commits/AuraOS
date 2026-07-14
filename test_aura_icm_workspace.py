"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9e1-[Q-SYS:ICM_TEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Test Integrity)
DEPENDENCIES: __future__, pytest, aura_icm_workspace, aura_liquid_planning_arena, aura_qdkt, aura_dream_retrieval
FUNCTIONS: test_export_creates_numbered_workspace, test_stage_context_declares_explicit_fields, test_human_edit_triggers_qdkt, test_dream_scores_written, test_import_roundtrip, test_boundary_contracts_jsonl
SYNOPSIS: Unit tests for the ICM workspace export/import layer. Validates filesystem tree, QDKT wiring, DREAM-lite rows, and round-trip integrity without touching live sidecars.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import aura_qdkt
from aura_dream_retrieval import DreamCandidate
from aura_icm_workspace import (
    ICMStageDescriptor,
    export_arena_transaction,
    import_workspace,
    record_human_edit,
    record_dream_scores,
    build_icm_aura_md,
    build_icm_context_md,
)
from aura_liquid_planning_arena import ActionCapsule, BoundaryContract
from aura_qdkt import UnifiedQDKT


def _sample_capsule() -> ActionCapsule:
    return ActionCapsule.create(
        capsule_id="CAP-1",
        domain="code",
        role="worker",
        objective="Patch demo.py",
        target={"file": "demo.py"},
        scope={"regions": [{"region_type": "file", "id": "demo.py"}]},
        allowed_actions=["edit file", "run tests"],
        forbidden_actions=["delete file", "add deps"],
        acceptance_checks=["tests pass"],
        expected_output="diff",
        escalation_triggers=["tests fail"],
    )


def _sample_contract() -> BoundaryContract:
    return BoundaryContract.placeholder(
        domain="code",
        capsule_id="CAP-1",
        boundary_type="file_scope",
        external_system="git",
        source_region={"file": "demo.py"},
        owned_scope=["demo.py"],
        assumptions=["demo.py exists"],
        required_inputs=["demo.py"],
        promised_outputs=["diff"],
        constraints=["no new deps"],
        escalation_triggers=["tests fail"],
        invariant="only demo.py may change",
    )


def test_export_creates_numbered_workspace(tmp_path):
    root = tmp_path / "icm"
    txn = {"objective": "test run", "domain": "code", "arena_id": "ARENA-1"}
    ref = export_arena_transaction(txn, root, domain="code", arena_id="ARENA-1")

    ws = Path(ref.workspace_path)
    assert ws.exists()
    assert (ws / "AURA.md").exists()
    assert (ws / "CONTEXT.md").exists()
    assert (ws / "boundary_contracts.jsonl").exists()
    assert (ws / "verifier_report.json").exists()
    assert (ws / "qdkt_events.jsonl").exists()
    assert (ws / "dream_scores.jsonl").exists()
    assert (ws / "metadata.json").exists()

    aura_md = (ws / "AURA.md").read_text(encoding="utf-8")
    assert "Layer 0" in aura_md
    assert "Layer 4" in aura_md
    assert "audit / edit / review layer" in aura_md

    ctx_md = (ws / "CONTEXT.md").read_text(encoding="utf-8")
    assert "Stage Routing" in ctx_md


def test_export_with_stages_creates_stage_folders(tmp_path):
    root = tmp_path / "icm"
    capsule = _sample_capsule()
    contract = _sample_contract()
    stage = ICMStageDescriptor(
        stage_number=1,
        stage_name="build",
        capsule=capsule,
        contracts=[contract],
        inputs=["demo.py"],
        process="apply diff",
        outputs=["diff", "test_result"],
        allowed_actions=["edit file", "run tests"],
        forbidden_actions=["delete file"],
        verifier_gates=["tests pass"],
        human_review_status="pending",
        references={"codemap": {"files": ["demo.py"]}},
        artifacts={"diff": {"lines_added": 3}},
    )

    ref = export_arena_transaction(
        {"objective": "patch demo"},
        root,
        domain="code",
        arena_id="ARENA-2",
        stages=[stage],
    )
    ws = Path(ref.workspace_path)
    stage_dir = ws / "stages" / "01_build"
    assert stage_dir.exists()
    assert (stage_dir / "CONTEXT.md").exists()
    assert (stage_dir / "references").exists()
    assert (stage_dir / "output").exists()

    assert (stage_dir / "references" / "codemap.json").exists()
    assert (stage_dir / "output" / "diff.json").exists()

    ctx = (stage_dir / "CONTEXT.md").read_text(encoding="utf-8")
    assert "## Inputs" in ctx
    assert "- demo.py" in ctx
    assert "## Process" in ctx
    assert "apply diff" in ctx
    assert "## Outputs" in ctx
    assert "diff" in ctx
    assert "## Allowed Actions" in ctx
    assert "edit file" in ctx
    assert "## Forbidden Actions" in ctx
    assert "delete file" in ctx
    assert "## Verifier Gates" in ctx
    assert "tests pass" in ctx
    assert "## Human Review Status: `pending`" in ctx
    assert "ActionCapsule" in ctx
    assert "BoundaryContracts" in ctx

    lines = (ws / "boundary_contracts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["boundary_type"] == "file_scope"



def test_export_with_dream_candidates_writes_scores(tmp_path):
    root = tmp_path / "icm"
    candidates = [
        DreamCandidate(
            candidate_id="c1",
            candidate_type="code_context",
            source="CODEMAP",
            content="demo.py",
            semantic_score=0.9,
        ),
        DreamCandidate(
            candidate_id="c2",
            candidate_type="code_context",
            source="CODEMAP",
            content="other.py",
            semantic_score=0.5,
        ),
    ]
    ref = export_arena_transaction(
        {"objective": "patch demo"},
        root,
        domain="code",
        arena_id="ARENA-3",
        dream_candidates=candidates,
        dream_query="patch demo",
        dream_target_type="code_context",
    )
    ws = Path(ref.workspace_path)
    dream_lines = (ws / "dream_scores.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(dream_lines) == 2
    scores = [json.loads(line) for line in dream_lines]
    assert scores[0]["candidate_id"] == "c1"
    assert scores[0]["usefulness_score"] >= scores[1]["usefulness_score"]


def test_export_qdkt_event_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(aura_qdkt, "_MEMPALACE_DB", tmp_path / "mempalace.db")
    monkeypatch.setattr(aura_qdkt, "_WORKSPACE_DB", tmp_path / "workspace.db")
    monkeypatch.setattr(aura_qdkt, "_CRYSTAL_JSON", tmp_path / "crystals.json")
    qdkt = UnifiedQDKT()

    root = tmp_path / "icm"
    ref = export_arena_transaction(
        {"objective": "patch demo"},
        root,
        domain="code",
        arena_id="ARENA-4",
        qdkt=qdkt,
    )
    ws = Path(ref.workspace_path)
    qdkt_lines = (ws / "qdkt_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(qdkt_lines) >= 1
    event = json.loads(qdkt_lines[0])
    assert event["event_type"] == "icm_workspace_export"
    assert event["confidence"] == 0.95

    with sqlite3.connect(tmp_path / "workspace.db") as conn:
        rows = conn.execute(
            "SELECT event_type, concept FROM qdkt_events WHERE event_type = 'icm_workspace_export'"
        ).fetchall()
    assert len(rows) >= 1


def test_human_edit_triggers_qdkt_and_creates_diff(tmp_path, monkeypatch):
    monkeypatch.setattr(aura_qdkt, "_MEMPALACE_DB", tmp_path / "mempalace.db")
    monkeypatch.setattr(aura_qdkt, "_WORKSPACE_DB", tmp_path / "workspace.db")
    monkeypatch.setattr(aura_qdkt, "_CRYSTAL_JSON", tmp_path / "crystals.json")
    qdkt = UnifiedQDKT()

    root = tmp_path / "icm"
    capsule = _sample_capsule()
    stage = ICMStageDescriptor(
        stage_number=1,
        stage_name="edit",
        capsule=capsule,
        contracts=[],
        inputs=["a.py"],
        process="edit",
        outputs=["a.py"],
        allowed_actions=["edit"],
        forbidden_actions=["delete"],
        verifier_gates=["lint pass"],
        human_review_status="pending",
    )
    ref = export_arena_transaction(
        {"objective": "edit a.py"},
        root,
        stages=[stage],
    )
    ws = Path(ref.workspace_path)

    event = record_human_edit(
        ws,
        "edit",
        old_text="old content",
        new_text="new content",
        editor_id="tester",
        rationale="fix typo",
        qdkt=qdkt,
    )
    assert event["event_type"] == "human_edit"
    assert event["concept"] == f"icm:{ws.name}:edit"

    edit_files = list((ws / "stages" / "01_edit" / "output").glob("human_edit_*.md"))
    assert len(edit_files) == 1
    edit_md = edit_files[0].read_text(encoding="utf-8")
    assert "old content" in edit_md
    assert "new content" in edit_md
    assert "fix typo" in edit_md

    qdkt_lines = (ws / "qdkt_events.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(qdkt_lines) >= 2
    last_event = json.loads(qdkt_lines[-1])
    assert last_event["event_type"] == "human_edit"

    with sqlite3.connect(tmp_path / "workspace.db") as conn:
        rows = conn.execute(
            "SELECT event_type, concept FROM qdkt_events WHERE event_type = 'human_edit'"
        ).fetchall()
    assert len(rows) >= 1




def test_record_dream_scores_appends(tmp_path):
    root = tmp_path / "icm"
    ref = export_arena_transaction(
        {"objective": "demo"},
        root,
        domain="code",
    )
    ws = Path(ref.workspace_path)
    record_dream_scores(ws, [{"candidate_id": "x", "usefulness_score": 0.8}])
    lines = (ws / "dream_scores.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    assert json.loads(lines[-1])["candidate_id"] == "x"


def test_import_roundtrip(tmp_path):
    root = tmp_path / "icm"
    capsule = _sample_capsule()
    contract = _sample_contract()
    stage = ICMStageDescriptor(
        stage_number=1,
        stage_name="lint",
        capsule=capsule,
        contracts=[contract],
        inputs=["src.py"],
        process="lint src.py",
        outputs=["lint_report"],
        allowed_actions=["run linter"],
        forbidden_actions=["auto-fix without review"],
        verifier_gates=["zero errors"],
        human_review_status="approved",
        references={"schema": {"type": "json"}},
        artifacts={"report": {"errors": 0}},
    )
    ref = export_arena_transaction(
        {"objective": "lint"},
        root,
        domain="code",
        arena_id="ARENA-5",
        stages=[stage],
        verifier_report={"overall": "passed"},
    )
    ws = Path(ref.workspace_path)

    imported = import_workspace(ws)
    assert imported.domain == "code"
    assert imported.arena_id == "ARENA-5"
    assert len(imported.stages) == 1
    s = imported.stages[0]
    assert s.stage_name == "lint"
    assert s.inputs == ["src.py"]
    assert s.process == "lint src.py"
    assert s.outputs == ["lint_report"]
    assert s.allowed_actions == ["run linter"]
    assert s.forbidden_actions == ["auto-fix without review"]
    assert s.verifier_gates == ["zero errors"]
    assert s.human_review_status == "approved"
    assert s.references == {"schema": {"type": "json"}}
    assert s.artifacts == {"report": {"errors": 0}}
    assert len(imported.boundary_contracts) == 1
    assert imported.verifier_report == {"overall": "passed"}
    assert len(imported.qdkt_events) >= 1
    assert imported.metadata["stage_count"] == 1


def test_export_numbering_increments(tmp_path):
    root = tmp_path / "icm"
    export_arena_transaction({"objective": "first"}, root)
    export_arena_transaction({"objective": "second"}, root)
    ref3 = export_arena_transaction({"objective": "third"}, root)

    ws = Path(ref3.workspace_path)
    assert ws.name.startswith("003_")


def test_build_icm_aura_md_contains_all_layers():
    md = build_icm_aura_md(
        domain="travel",
        arena_id="A-1",
        arena_version="V1",
        workspace_id="W-1",
    )
    assert "Layer 0" in md
    assert "Layer 1" in md
    assert "Layer 4" in md
    assert "travel" in md


def test_build_icm_context_md_contains_stage_table():
    stage = ICMStageDescriptor(
        stage_number=1,
        stage_name="plan",
        capsule={},
        contracts=[],
        inputs=["budget"],
        outputs=["options"],
        verifier_gates=["price check"],
        human_review_status="pending",
    )
    md = build_icm_context_md(arena_id="A-1", domain="travel", stages=[stage])
    assert "plan" in md
    assert "budget" in md
    assert "price check" in md
    assert "pending" in md



def test_arena_export_to_icm_creates_workspace(tmp_path):
    from aura_liquid_planning_arena import (
        LIQUID_ARENA_VERSION,
        LiquidPlanningArena,
        export_arena_to_icm,
    )

    arena = LiquidPlanningArena(
        arena_version=LIQUID_ARENA_VERSION,
        arena_id="ARENA-ICM-1",
        domain="code",
        intent="patch demo.py",
        plan_ref="plan-1",
        domain_objects=["files", "diffs", "tests"],
        adapter={"domain": "code"},
        action_capsules=[
            {
                "capsule_id": "CAP-1",
                "role": "worker",
                "required_inputs": ["demo.py"],
                "promised_outputs": ["diff"],
                "allowed_actions": ["edit"],
                "forbidden_actions": ["delete"],
            }
        ],
        boundary_contracts=[
            {
                "capsule_id": "CAP-1",
                "boundary_type": "file_scope",
                "contract_id": "BC-1",
            }
        ],
        verification_ledger=[
            {"capsule_id": "CAP-1", "verifier_id": "lint_pass"}
        ],
        agent_leases=[{"lease_id": "L-1"}],
        shared_action_queue=[],
        phase_hash="ph1",
    )

    root = tmp_path / "icm"
    ref = export_arena_to_icm(arena, root)
    ws = Path(ref.workspace_path)
    assert ws.exists()
    assert (ws / "AURA.md").exists()
    assert (ws / "CONTEXT.md").exists()
    assert (ws / "stages" / "01_cap-1" / "CONTEXT.md").exists()
    ctx = (ws / "stages" / "01_cap-1" / "CONTEXT.md").read_text(encoding="utf-8")
    assert "worker" in ctx
    assert "lint_pass" in ctx


def test_travel_package_export_to_icm_creates_workspace(tmp_path):
    from travel_package_arena import TravelPackageArena, TravelPackageCandidate

    root = tmp_path / "icm"
    arena = TravelPackageArena(
        sidecar=None,  # type: ignore[arg-type]
        pointer_index=None,
        verifier=None,
        adapter=None,
    )
    candidate = TravelPackageCandidate(
        package_id="PKG-1",
        traveler_intent={"objective": "beach vacation"},
        vsa_id="VSA-1",
        resort={"name": "Test Resort"},
        exact_price={"price_id": "P-1", "nightly_price_minor": 10000},
        semantic_match={"semantic_tags": ["beach", "family"], "dream_usefulness": {"semantic_score": 0.8}},
        verification={"approved": True, "blockers": [], "warnings": []},
        boundary_contracts=(),
        status="verified_pending_human_approval",
    )

    ref = arena.export_candidate_to_icm(candidate, root)
    ws = Path(ref.workspace_path)
    assert ws.exists()
    assert (ws / "AURA.md").exists()
    assert (ws / "stages" / "01_travel_package" / "CONTEXT.md").exists()
    ctx = (ws / "stages" / "01_travel_package" / "CONTEXT.md").read_text(encoding="utf-8")
    assert "travel_package" in ctx
    assert "price_freshness" in ctx
    assert "booking_payment" in ctx


def test_cli_module_imports():
    import aura_icm_cli

    assert callable(aura_icm_cli.main)

