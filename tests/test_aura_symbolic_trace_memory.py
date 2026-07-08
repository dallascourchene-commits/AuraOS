import json
from pathlib import Path

from aura_emergent_capability_auditor import record_capability_audit_trace_nodes
from aura_symbolic_trace_memory import (
    AuraTraceMemoryConfig,
    build_trace_canvas,
    lookup_trace_node,
    offload_raw_evidence,
    record_trace_event,
    render_trace_canvas_for_prompt,
    score_replaceability,
    should_inject_canvas,
    summarize_trace_memory,
)
from aura_topological_context_anchor import CodeTopoAnchor, render_builder_context


def test_raw_evidence_offloads_with_stable_node_id_and_source_hash(tmp_path: Path):
    ref = offload_raw_evidence("builder:N1", "raw builder evidence", tmp_path, kind="builder")
    again = offload_raw_evidence("builder:N1", "raw builder evidence", tmp_path, kind="builder")

    assert ref.node_id == "builder:N1"
    assert ref.source_hash == again.source_hash
    assert (tmp_path / ref.path).exists()
    assert "Aura_Memory/trace_refs" in ref.path


def test_trace_atoms_append_to_jsonl_and_survive_reload(tmp_path: Path):
    atom = record_trace_event(
        {
            "event_type": "builder_response",
            "task_id": "A1",
            "node_id": "N1",
            "summary": "response captured",
            "raw_text": "full response",
        },
        tmp_path,
    )

    report = summarize_trace_memory(tmp_path)
    lookup = lookup_trace_node("N1", tmp_path)

    assert report.atom_count == 1
    assert lookup["atoms"][0]["atom_id"] == atom.atom_id
    assert lookup["node"]["summary"] == "response captured"


def test_corrupt_jsonl_line_is_tolerated_and_reported(tmp_path: Path):
    record_trace_event({"event_type": "ok", "task_id": "A1", "node_id": "N1", "raw_text": "ok"}, tmp_path)
    atoms_path = tmp_path / "Aura_Memory" / "trace_atoms.jsonl"
    with atoms_path.open("a", encoding="utf-8") as handle:
        handle.write("{not json}\n")

    report = summarize_trace_memory(tmp_path)
    canvas = build_trace_canvas("A1", tmp_path)

    assert report.atom_count == 1
    assert any("corrupt_jsonl_line" in warning for warning in report.warnings)
    assert any("corrupt_jsonl_line" in warning for warning in canvas.warnings)


def test_canvas_renders_mermaid_with_node_id_references(tmp_path: Path):
    record_trace_event(
        {
            "event_type": "builder_prompt",
            "task_id": "A1",
            "node_id": "NODE-123",
            "summary": "prompt captured",
            "raw_text": "prompt body",
        },
        tmp_path,
    )

    canvas = build_trace_canvas("A1", tmp_path)
    rendered = render_trace_canvas_for_prompt(canvas)

    assert "graph TD" in canvas.mermaid
    assert "NODE-123" in canvas.mermaid
    assert "node_id=NODE-123" in rendered
    assert "raw_ref=" in rendered


def test_lookup_by_node_id_recovers_raw_ref_and_summary(tmp_path: Path):
    record_trace_event(
        {
            "event_type": "preflight_result",
            "task_id": "A1",
            "node_id": "PRE-N1",
            "summary": "preflight failed on hunk header",
            "raw_text": "git apply failed with hunk header issue",
        },
        tmp_path,
    )

    lookup = lookup_trace_node("PRE-N1", tmp_path)

    assert lookup["raw_refs"]
    assert "preflight failed" in lookup["node"]["summary"]
    assert "hunk header issue" in next(iter(lookup["raw_evidence"].values()))


def test_replaceability_scoring_marks_exact_patch_context_low():
    score = score_replaceability(
        {
            "event_type": "builder_prompt",
            "source_excerpt": "def answer():\n    return 1",
            "source_hash": "abc123",
            "raw_text": "diff --git a/demo.py b/demo.py\n@@ -1 +1 @@",
        }
    )

    assert score <= 0.1


def test_token_pressure_helper_returns_mild_aggressive_emergency():
    config = AuraTraceMemoryConfig()

    assert should_inject_canvas(50, 100, config) == "mild"
    assert should_inject_canvas(85, 100, config) == "aggressive"
    assert should_inject_canvas(95, 100, config) == "emergency"


def test_builder_failure_event_can_be_recorded_and_rendered_compactly(tmp_path: Path):
    failure = {
        "status": "missing_patch_diff",
        "reason_codes": ["missing_patch_diff", "builder_refusal"],
        "raw_model_response": "I cannot provide a diff.",
    }
    record_trace_event(
        {
            "event_type": "builder_failure_report",
            "task_id": "A-BUILD",
            "node_id": "A-BUILD:failure",
            "status": "blocked",
            "summary": "Builder failed to produce a diff",
            "raw_text": json.dumps(failure),
        },
        tmp_path,
    )

    rendered = render_trace_canvas_for_prompt(build_trace_canvas("A-BUILD", tmp_path))

    assert "builder failure report" in rendered
    assert "A-BUILD:failure" in rendered
    assert "Builder failed to produce a diff" in rendered


def test_emergent_capability_finding_can_be_recorded_as_trace_node(tmp_path: Path):
    report = {
        "route": "EMERGENT_CAPABILITY_AUDIT",
        "subsystem": "coding_arena",
        "findings": [
            {
                "finding_id": "finding-1",
                "title": "Unwired builder and verifier bridge",
                "subsystem": "coding_arena",
                "safe_to_patch": False,
                "symbols": [
                    {"symbol": "Builder", "file_path": "aura_builder_context.py"},
                    {"symbol": "Verifier", "file_path": "aura_live_architect.py"},
                ],
            }
        ],
        "future_potentials": [],
    }

    atom_ids = record_capability_audit_trace_nodes(report, tmp_path, task_id="audit-task")
    lookup = lookup_trace_node("finding-1", tmp_path)

    assert atom_ids
    assert lookup["node"]["status"] == "proposed"
    assert "Unwired builder and verifier bridge" in lookup["node"]["summary"]
    assert "aura_live_architect.py" in lookup["node"]["related_files"]


def test_trace_canvas_injection_never_replaces_exact_topological_source_spans(tmp_path: Path):
    anchor = CodeTopoAnchor.build_from_files({"demo.py": "def target():\n    return 1\n"})
    packet = anchor.nearest_context("target")
    exact_context = render_builder_context(packet)
    record_trace_event(
        {
            "event_type": "trace_summary",
            "task_id": "A1",
            "node_id": "summary-node",
            "summary": "advisory memory only",
            "raw_text": "summary raw evidence",
        },
        tmp_path,
    )

    trace_prompt = render_trace_canvas_for_prompt(build_trace_canvas("A1", tmp_path))
    combined_prompt = exact_context + "\n" + trace_prompt

    assert "exact_span: demo.py:1-2 symbol=target" in combined_prompt
    assert "patch_authority: exact source spans with source_hash only" in combined_prompt
    assert "AURA SYMBOLIC TRACE CANVAS (ADVISORY)" in trace_prompt
    assert "Topological Context Anchor" in trace_prompt
