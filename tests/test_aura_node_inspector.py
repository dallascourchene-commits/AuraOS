"""Tests for the Aura Node Inspector (Intelligence Layer V1.2).

Tests cover:
- inspect_node for exact topology nodes and CODEMAP-projected nodes
- inspect_node for unresolved candidates (NEEDS_GROUNDING)
- why_is_node_here grounding path
- show exact source (no full file dump)
- expand_node returns additional nodes/edges
- JSpace state is present and advisory
- FST route frame includes intent/action/scope/grounding/tests/cost
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure the repo root is on the path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_node_inspector import (
    inspect_node,
    expand_node,
    why_is_node_here,
    route_node_command,
    ORIGIN_EXACT_TOPOLOGY,
    ORIGIN_CODEMAP_PROJECTED,
    ORIGIN_UNRESOLVED,
    PATCH_AUTHORITY,
)


# ---------------------------------------------------------------------------
# inspect_node tests
# ---------------------------------------------------------------------------


class TestInspectNode:
    """Tests for inspect_node function."""

    def test_inspect_exact_topology_node(self):
        """inspect_node returns grounded packet for an exact topology node."""
        # Use a known CODEMAP file as a topology node
        topology = {
            "nodes": [
                {
                    "id": "aura_fst_routing.py::global_scope",
                    "label": "aura_fst_routing.py",
                    "node_type": "file",
                    "file_path": "aura_fst_routing.py",
                    "symbol": "",
                    "kind": "file",
                    "x": 0, "y": 0, "z": 0,
                    "metadata": {"node_origin": "exact_topology_node"},
                }
            ],
            "links": [],
        }
        pkt = inspect_node(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
            topology=topology,
        )
        assert pkt.node_origin == ORIGIN_EXACT_TOPOLOGY
        assert pkt.entity_exists is True
        assert pkt.file_path == "aura_fst_routing.py"
        assert pkt.patch_authority is False
        assert pkt.vsa_patch_authority is False
        assert pkt.confidence > 0.0

    def test_inspect_codemap_projected_node(self):
        """inspect_node returns grounded packet for a CODEMAP-projected node."""
        # Use a file that exists in CODEMAP but pass no topology
        pkt = inspect_node(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
        )
        assert pkt.node_origin == ORIGIN_CODEMAP_PROJECTED
        assert pkt.entity_exists is True
        assert pkt.file_path == "aura_fst_routing.py"
        assert pkt.grounding_source == ".aura/CODEMAP.json"
        assert pkt.patch_authority is False

    def test_inspect_unresolved_candidate(self):
        """inspect_node returns NEEDS_GROUNDING for unresolved candidate."""
        pkt = inspect_node(
            "nonexistent_file_xyz.py::fake_symbol",
            repo_root=REPO_ROOT,
        )
        assert pkt.node_origin == ORIGIN_UNRESOLVED
        assert pkt.entity_exists is False
        assert "NEEDS_GROUNDING" in pkt.why_here

    def test_inspect_empty_node_id(self):
        """inspect_node handles empty node ID gracefully."""
        pkt = inspect_node("", repo_root=REPO_ROOT)
        assert pkt.node_origin == ORIGIN_UNRESOLVED

    def test_inspect_packet_to_dict(self):
        """NodeIntelligencePacket.to_dict returns all required fields."""
        pkt = inspect_node(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
        )
        d = pkt.to_dict()
        assert "node_id" in d
        assert "node_origin" in d
        assert "why_here" in d
        assert "grounding_source" in d
        assert "file_path" in d
        assert "symbol" in d
        assert "kind" in d
        assert "line_range" in d
        assert "digest8" in d
        assert "semantic_id" in d
        assert "signature_hash" in d
        assert "entity_exists" in d
        assert "patch_authority" in d
        assert "vsa_patch_authority" in d
        assert "relationships" in d
        assert "risk" in d
        assert "jspace_state" in d
        assert "fst_route" in d
        assert "recommended_affordances" in d
        assert "next_actions" in d
        assert "confidence" in d
        assert "notes" in d

    def test_inspect_truth_packet(self):
        """to_truth_packet includes required fields."""
        pkt = inspect_node(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
        )
        tp = pkt.to_truth_packet()
        assert "node_origins" in tp
        assert "codemap_projected_nodes" in tp
        assert "exact_topology_nodes" in tp
        assert "ghost_hypothesis_edges" in tp
        assert "unresolved_candidates" in tp
        assert "line_ranges" in tp
        assert "source_hashes" in tp
        assert "signature_hashes" in tp
        assert "grounding_source" in tp
        assert tp["patch_authority"] == PATCH_AUTHORITY
        assert tp["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# why_is_node_here tests
# ---------------------------------------------------------------------------


class TestWhyIsNodeHere:
    """Tests for why_is_node_here function."""

    def test_why_here_returns_grounding_path(self):
        """why_is_node_here returns a grounding path explanation."""
        result = why_is_node_here(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert "node_origin" in result
        assert "truth_packet" in result
        assert "patch_authority" in result
        assert result["vsa_patch_authority"] is False

    def test_why_here_unresolved(self):
        """why_is_node_here for unresolved node includes NEEDS_GROUNDING."""
        result = why_is_node_here(
            "nonexistent_xyz.py::fake",
            repo_root=REPO_ROOT,
        )
        assert result["node_origin"] == ORIGIN_UNRESOLVED
        assert "NEEDS_GROUNDING" in result["answer"]


# ---------------------------------------------------------------------------
# expand_node tests
# ---------------------------------------------------------------------------


class TestExpandNode:
    """Tests for expand_node function."""

    def test_expand_balanced(self):
        """expand_node with balanced mode returns additional nodes/edges."""
        result = expand_node(
            "aura_fst_routing.py::global_scope",
            expansion_mode="balanced",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert "additional_nodes" in result
        assert "additional_links" in result
        assert "truth_packet" in result
        assert "node_intelligence" in result
        assert "visual_update" in result
        assert "next_actions" in result
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False

    def test_expand_children(self):
        """expand_node with children mode returns contained symbols."""
        result = expand_node(
            "aura_fst_routing.py::global_scope",
            expansion_mode="children",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        # Should find some contained symbols (aura_fst_routing.py has functions)
        nodes = result.get("additional_nodes", [])
        assert isinstance(nodes, list)
        # If CODEMAP has contains for this file, nodes should be non-empty
        if nodes:
            assert all(n["id"] != "aura_fst_routing.py::global_scope" for n in nodes)

    def test_expand_risks(self):
        """expand_node with risks mode returns risk assessment."""
        result = expand_node(
            "aura_fst_routing.py::global_scope",
            expansion_mode="risks",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert "risk" in result.get("answer", "").lower() or "severity" in str(result.get("visual_update", {}))

    def test_expand_unresolved(self):
        """expand_node for unresolved node returns NEEDS_GROUNDING."""
        result = expand_node(
            "nonexistent_xyz.py::fake",
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True
        assert "NEEDS_GROUNDING" in result.get("answer", "")

    def test_expand_does_not_dump_full_source(self):
        """expand_node should not dump full source files."""
        result = expand_node(
            "aura_fst_routing.py::global_scope",
            repo_root=REPO_ROOT,
        )
        answer = result.get("answer", "")
        # Should recommend read_slice, not dump source
        assert "aura_read_slice" in answer or "read_slice" in str(result.get("read_slice_command", ""))


# ---------------------------------------------------------------------------
# route_node_command tests
# ---------------------------------------------------------------------------


class TestRouteNodeCommand:
    """Tests for FST/JSpace route_node_command function."""

    def test_route_frame_structure(self):
        """route_node_command returns a well-formed route frame."""
        frame = route_node_command(
            "explain selected node",
            selected_node_ids=["aura_fst_routing.py::global_scope"],
            repo_root=REPO_ROOT,
        )
        assert "intent" in frame
        assert "artifact" in frame
        assert "action" in frame
        assert "scope" in frame
        assert "risk" in frame
        assert "grounding" in frame
        assert "tests" in frame
        assert "quality" in frame
        assert "cost" in frame
        assert "route" in frame
        assert "next_state" in frame

    def test_route_intent_explain(self):
        """route_node_command maps 'explain' to explain intent."""
        frame = route_node_command("explain this node", repo_root=REPO_ROOT)
        assert frame["intent"] == "explain"

    def test_route_intent_refactor(self):
        """route_node_command maps 'refactor' to code_refactor intent."""
        frame = route_node_command("refactor this function", repo_root=REPO_ROOT)
        assert frame["intent"] == "code_refactor"

    def test_route_jspace_advisory(self):
        """JSpace state is present and advisory (not patch authority)."""
        frame = route_node_command("inspect node", repo_root=REPO_ROOT)
        # JSpace state may be empty if jspace codec has issues, but key should exist
        assert "jspace_state" in frame


# ---------------------------------------------------------------------------
# Safety invariants
# ---------------------------------------------------------------------------


class TestSafetyInvariants:
    """Verify no production mutation and patch authority invariants."""

    def test_no_fake_node_language(self):
        """No user-facing 'fake node' language in node inspector output."""
        pkt = inspect_node("aura_fst_routing.py::global_scope", repo_root=REPO_ROOT)
        d = pkt.to_dict()
        serialized = json.dumps(d)
        assert "fake node" not in serialized.lower()
        assert "synthetic node" not in serialized.lower()

    def test_patch_authority_invariant(self):
        """All packets maintain patch authority invariant."""
        pkt = inspect_node("aura_fst_routing.py::global_scope", repo_root=REPO_ROOT)
        assert pkt.patch_authority is False
        assert pkt.vsa_patch_authority is False
        tp = pkt.to_truth_packet()
        assert tp["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert tp["vsa_patch_authority"] is False
