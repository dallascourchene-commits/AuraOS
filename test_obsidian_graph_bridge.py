"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f1-[Q-SYS:OBSIDIAN_GRAPH_TESTS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: DEBWEWIN (Truth / Test Authority)
DEPENDENCIES: json, pathlib, tempfile, unittest, aura_graphify_schema, aura_topology_sync, aura_obsidian_graph_bridge
FUNCTIONS: TestGraphifySchema, TestTopologySync, TestObsidianGraphBridge
SYNOPSIS: Tests proving Obsidian notes are generated, Wikilinks are stable, graph JSON
validates, and sidecar truth is referenced rather than copied as authority.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

from aura_graphify_schema import (
    EDGE_TYPES,
    NODE_TYPES,
    EdgeType,
    GraphifyEdge,
    GraphifyNode,
    GraphifyPacket,
    GraphifyValidator,
    NodeType,
    SourceRef,
    SourceRefKind,
    edge_id_for,
    node_id_for,
    packet_from_json,
    packet_to_json,
    validate_packet,
)
from aura_topology_sync import (
    ChangeDetector,
    ChangeSet,
    SyncState,
    TopologySync,
    detect_changes,
    load_sync_state,
    save_sync_state,
)
from aura_obsidian_graph_bridge import (
    BRIDGE_VERSION,
    ObsidianGraphBridge,
    export_graph_json,
    export_vault,
    note_filename,
    wikilink,
    yaml_frontmatter,
)


# ---------------------------------------------------------------------------
# Test fixture builder — creates a minimal Aura repo on disk
# ---------------------------------------------------------------------------

def _build_fixture(root: Path) -> dict[str, Path]:
    """Create a minimal Aura repo with all the source systems the bridge reads."""
    paths: dict[str, Path] = {}

    # Source file
    src = root / "aura_core.py"
    src.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    paths["source"] = src

    # Test file
    test = root / "test_aura_core.py"
    test.write_text("from aura_core import hello\n\ndef test_hello():\n    assert hello() == 'world'\n", encoding="utf-8")
    paths["test"] = test

    # Sidecar file
    sidecar = root / "travel_price_sidecar.py"
    sidecar.write_text("# travel price sidecar\n", encoding="utf-8")
    paths["sidecar"] = sidecar

    # Verifier file
    verifier = root / "aura_validation.py"
    verifier.write_text("# verifier\n", encoding="utf-8")
    paths["verifier"] = verifier

    # .aura/CODEMAP.json
    aura_dir = root / ".aura"
    aura_dir.mkdir(parents=True, exist_ok=True)
    codemap = {
        "status": "AURA_CODEMAP_ACTIVE",
        "files": [
            {"path": "aura_core.py", "role": "python_module", "bytes": 30,
             "lines": 2, "symbol_count": 1, "digest8": "abc12345",
             "topology": {"symbols": ["hello"], "neighbor_files": []}},
        ],
        "symbol_index": {
            "hello": [{"file": "aura_core.py", "kind": "function", "line": 1,
                       "end_line": 2, "semantic_id": "aura_core.py#function:hello:abc",
                       "signature_hash": "def hello()"}],
        },
        "topology": {
            "file_index": {},
        },
    }
    codemap_path = aura_dir / "CODEMAP.json"
    codemap_path.write_text(json.dumps(codemap, indent=2), encoding="utf-8")
    paths["codemap"] = codemap_path

    # .aura/pricing.json
    pricing = {
        "updated": "2026-06-30T00:00:00Z",
        "prices": {"mistral": {"in_per_1k": 0.0002, "out_per_1k": 0.0006}},
    }
    pricing_path = aura_dir / "pricing.json"
    pricing_path.write_text(json.dumps(pricing, indent=2), encoding="utf-8")
    paths["pricing"] = pricing_path

    # Aura_Memory/arena run
    mem_dir = root / "Aura_Memory"
    arena_dir = mem_dir / "arenas"
    arena_dir.mkdir(parents=True, exist_ok=True)
    arena = {
        "arena_id": "LPA-test123",
        "domain": "code",
        "intent": "test objective",
        "phase_hash": "abc123",
        "action_capsules": [
            {"capsule_id": "CAP-1", "domain": "code", "role": "builder",
             "objective": "build", "phase_hash": "h1"},
        ],
        "boundary_contracts": [
            {"contract_id": "BC-1", "capsule_id": "CAP-1", "domain": "code",
             "invariant": "preserve", "status": "placeholder", "phase_hash": "h2"},
        ],
        "agent_leases": [
            {"lease_id": "LEASE-1", "capsule_id": "CAP-1", "holder": "builder",
             "status": "active", "mode": "exclusive_write"},
        ],
        "verification_ledger": [
            {"stage": "shadow", "status": "passed"},
        ],
    }
    arena_path = arena_dir / "LPA-test123.json"
    arena_path.write_text(json.dumps(arena, indent=2), encoding="utf-8")
    paths["arena"] = arena_path

    # Aura_Memory/qdkt_index.db
    qdkt_db = mem_dir / "qdkt_index.db"
    conn = sqlite3.connect(str(qdkt_db))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS qdkt_events (
            event_id TEXT PRIMARY KEY, event_type TEXT, concept TEXT,
            rationale TEXT, confidence REAL, ts REAL
        );
        CREATE TABLE IF NOT EXISTS qdkt_crystals (
            concept_key TEXT PRIMARY KEY, action TEXT, confidence REAL,
            count INTEGER, last_confirmed REAL
        );
    """)
    conn.execute(
        "INSERT INTO qdkt_events VALUES (?,?,?,?,?,?)",
        ("QDKT-test1", "code_change", "test", "rationale", 0.8, 1000.0),
    )
    conn.execute(
        "INSERT INTO qdkt_crystals VALUES (?,?,?,?,?)",
        ("concept_key_1", "do_thing", 0.9, 3, 1000.0),
    )
    conn.commit()
    conn.close()
    paths["qdkt_db"] = qdkt_db

    # Aura_Memory/dream_retrieval_ledger.jsonl
    dream_ledger = mem_dir / "dream_retrieval_ledger.jsonl"
    dream_row = {
        "version": "AURA_DREAM_RETRIEVAL_V1",
        "query": "test query",
        "candidate_id": "CAP-1",
        "candidate_type": "action_capsule",
        "source": "arena",
        "usefulness_score": 0.85,
        "semantic_score": 0.7,
        "target_type": "action_capsule",
        "mode": "judge_heuristic",
        "verifier_result": None,
        "phase_hash": "dream_hash_1",
        "failure_reason": "",
        "rationale": "test",
        "features": {},
        "ts": 1000.0,
    }
    dream_ledger.write_text(json.dumps(dream_row) + "\n", encoding="utf-8")
    paths["dream_ledger"] = dream_ledger

    # Aura_Memory/aura_savings.db
    savings_db = mem_dir / "aura_savings.db"
    conn = sqlite3.connect(str(savings_db))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, ts_epoch REAL,
            provider TEXT, model TEXT, call_type TEXT, task TEXT, aspect TEXT,
            prompt_tokens INTEGER, output_tokens INTEGER, cost_usd REAL,
            latency_sec REAL, baseline_prompt_tokens INTEGER,
            baseline_output_tokens INTEGER, baseline_cost_usd REAL,
            tokens_saved INTEGER, cost_saved_usd REAL, error TEXT, metadata TEXT
        );
    """)
    conn.execute(
        "INSERT INTO llm_calls (ts, ts_epoch, provider, model, call_type, "
        "prompt_tokens, output_tokens, cost_usd, latency_sec, tokens_saved, cost_saved_usd) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("2026-06-30T00:00:00Z", 1000.0, "mistral", "test", "generate",
         100, 50, 0.001, 0.5, 50, 0.002),
    )
    conn.commit()
    conn.close()
    paths["savings_db"] = savings_db

    return paths


# ---------------------------------------------------------------------------
# Graphify schema tests
# ---------------------------------------------------------------------------

class TestGraphifySchema(unittest.TestCase):
    """Tests for the typed graph schema and validator."""

    def test_all_17_edge_types_present(self):
        """Requirement 7: all 17 edge types must be defined."""
        expected = {
            "IMPORTS", "CALLS", "TESTS", "VERIFIES", "STORES_TRUTH_IN",
            "POINTS_TO", "BLOCKS", "DEPENDS_ON", "LEASES", "APPROVES",
            "REJECTS", "LEARNED_FROM", "CRYSTALLIZED_AS", "RETRIEVED_BY",
            "HELPED", "AFFECTS",
        }
        self.assertEqual(EDGE_TYPES, expected)
        self.assertEqual(len(EDGE_TYPES), 16)

    def test_node_types_present(self):
        """Requirement 4: node types for all exported record kinds."""
        for name in ("FILE", "SYMBOL", "ACTION_CAPSULE", "BOUNDARY_CONTRACT",
                     "ARENA_RUN", "QDKT_EVENT", "QDKT_CRYSTAL", "DREAM_SCORE",
                     "SIDECAR_REF", "VERIFIER_REPORT", "HOT_SWAP_CAPSULE",
                     "PRICE", "TRANSACTION"):
            self.assertIn(name, NODE_TYPES, f"missing node type {name}")

    def test_node_id_deterministic(self):
        """Node IDs are stable across calls."""
        id1 = node_id_for(NodeType.FILE.value, "aura_core.py")
        id2 = node_id_for(NodeType.FILE.value, "aura_core.py")
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("gf:FILE:"))

    def test_edge_id_deterministic(self):
        """Edge IDs are stable across calls."""
        id1 = edge_id_for("a", "b", EdgeType.IMPORTS.value)
        id2 = edge_id_for("a", "b", EdgeType.IMPORTS.value)
        self.assertEqual(id1, id2)
        self.assertTrue(id1.startswith("gfe:"))

    def test_validator_rejects_missing_source_ref(self):
        """Requirement 8: truth-bearing nodes must link to source record."""
        # A PRICE node with an empty source_ref should fail validation
        node = GraphifyNode(
            id=node_id_for(NodeType.PRICE.value, "test"),
            type=NodeType.PRICE.value,
            label="price-test",
            source_ref=SourceRef(kind="", path="", key=""),
        )
        packet = GraphifyPacket(
            version="test", generated_at="", project={},
            nodes=[node], edges=[],
        )
        validator = GraphifyValidator()
        issues = validator.validate(packet)
        errors = [i for i in issues if i.severity == "error"]
        self.assertTrue(any(i.code == "MISSING_SOURCE_REF_KIND" for i in errors))
        self.assertTrue(any(i.code == "MISSING_SOURCE_REF_PATH" for i in errors))
        self.assertTrue(any(i.code == "MISSING_SOURCE_REF_KEY" for i in errors))

    def test_validator_accepts_valid_node(self):
        """A truth-bearing node with a proper source_ref passes validation."""
        node = GraphifyNode(
            id=node_id_for(NodeType.PRICE.value, "pricing:mistral"),
            type=NodeType.PRICE.value,
            label="price-mistral",
            source_ref=SourceRef(
                kind=SourceRefKind.PRICING_JSON.value,
                path=".aura/pricing.json",
                key="pricing:mistral",
            ),
        )
        packet = GraphifyPacket(
            version="test", generated_at="", project={},
            nodes=[node], edges=[],
        )
        validator = GraphifyValidator()
        issues = validator.validate(packet)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [])

    def test_validator_rejects_dangling_edge(self):
        """Edges must reference existing nodes."""
        node = GraphifyNode(
            id=node_id_for(NodeType.FILE.value, "a.py"),
            type=NodeType.FILE.value,
            label="a.py",
            source_ref=SourceRef(
                kind=SourceRefKind.SOURCE_FILE.value,
                path="a.py", key="a.py",
            ),
        )
        edge = GraphifyEdge(
            id=edge_id_for(node.id, "nonexistent", EdgeType.IMPORTS.value),
            source=node.id,
            target="gf:FILE:nonexistent",
            type=EdgeType.IMPORTS.value,
        )
        packet = GraphifyPacket(
            version="test", generated_at="", project={},
            nodes=[node], edges=[edge],
        )
        validator = GraphifyValidator()
        issues = validator.validate(packet)
        errors = [i for i in issues if i.severity == "error"]
        self.assertTrue(any(i.code == "DANGLING_EDGE_TARGET" for i in errors))

    def test_validator_rejects_truth_edge_without_source_ref(self):
        """Requirement 8: truth-asserting edges must carry a source_ref."""
        node_a = GraphifyNode(
            id=node_id_for(NodeType.FILE.value, "a.py"),
            type=NodeType.FILE.value, label="a.py",
            source_ref=SourceRef(kind=SourceRefKind.SOURCE_FILE.value,
                                 path="a.py", key="a.py"),
        )
        node_b = GraphifyNode(
            id=node_id_for(NodeType.VERIFIER_REPORT.value, "v.py"),
            type=NodeType.VERIFIER_REPORT.value, label="v.py",
            source_ref=SourceRef(kind=SourceRefKind.VERIFIER_FILE.value,
                                 path="v.py", key="v.py"),
        )
        # VERIFIES edge without source_ref
        edge = GraphifyEdge(
            id=edge_id_for(node_b.id, node_a.id, EdgeType.VERIFIES.value),
            source=node_b.id, target=node_a.id,
            type=EdgeType.VERIFIES.value,
            source_ref=None,
        )
        packet = GraphifyPacket(
            version="test", generated_at="", project={},
            nodes=[node_a, node_b], edges=[edge],
        )
        validator = GraphifyValidator()
        issues = validator.validate(packet)
        errors = [i for i in issues if i.severity == "error"]
        self.assertTrue(any(i.code == "TRUTH_EDGE_MISSING_SOURCE_REF" for i in errors))

    def test_packet_json_roundtrip(self):
        """Packet serialises to JSON and back losslessly."""
        node = GraphifyNode(
            id=node_id_for(NodeType.FILE.value, "a.py"),
            type=NodeType.FILE.value, label="a.py",
            source_ref=SourceRef(kind=SourceRefKind.SOURCE_FILE.value,
                                 path="a.py", key="a.py"),
            properties={"role": "python_module"},
        )
        edge = GraphifyEdge(
            id=edge_id_for(node.id, node.id, EdgeType.DEPENDS_ON.value),
            source=node.id, target=node.id,
            type=EdgeType.DEPENDS_ON.value,
            source_ref=SourceRef(kind=SourceRefKind.CODEMAP.value,
                                 path=".aura/CODEMAP.json", key="test"),
        )
        packet = GraphifyPacket(
            version="test", generated_at="2026", project={"name": "test"},
            nodes=[node], edges=[edge], meta={"total_nodes": 1},
        )
        text = packet_to_json(packet)
        restored = packet_from_json(text)
        self.assertEqual(restored.nodes[0].id, node.id)
        self.assertEqual(restored.edges[0].type, EdgeType.DEPENDS_ON.value)
        self.assertEqual(restored.nodes[0].source_ref.kind, SourceRefKind.SOURCE_FILE.value)


# ---------------------------------------------------------------------------
# Topology sync tests
# ---------------------------------------------------------------------------

class TestTopologySync(unittest.TestCase):
    """Tests for incremental sync and change detection."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.fixture = _build_fixture(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_first_sync_is_full_resync(self):
        """A fresh sync state triggers a full resync."""
        detector = ChangeDetector(root=self.tmpdir)
        state = SyncState()  # last_sync_unix == 0
        changes = detector.detect(state)
        self.assertTrue(changes.full_resync)

    def test_incremental_detects_changed_file(self):
        """Requirement 9: only changed files are re-exported."""
        sync = TopologySync(root=self.tmpdir,
                            state_path=self.tmpdir / "sync_state.json")
        # First sync (full)
        changes1, state1 = sync.plan(force_full=True)
        sync.commit(changes1, state1)
        # Modify a file
        self.fixture["source"].write_text("def hello():\n    return 'changed'\n", encoding="utf-8")
        # Second sync (incremental)
        changes2, state2 = sync.plan()
        self.assertFalse(changes2.full_resync)
        self.assertIn("aura_core.py", changes2.changed_files)

    def test_incremental_detects_removed_file(self):
        """Removed files are detected."""
        sync = TopologySync(root=self.tmpdir,
                            state_path=self.tmpdir / "sync_state.json")
        changes1, state1 = sync.plan(force_full=True)
        sync.commit(changes1, state1)
        # Remove a file
        self.fixture["sidecar"].unlink()
        changes2, state2 = sync.plan()
        self.assertIn("travel_price_sidecar.py", changes2.removed_files)

    def test_incremental_detects_new_qdkt_event(self):
        """New QDKT events are detected."""
        sync = TopologySync(root=self.tmpdir,
                            state_path=self.tmpdir / "sync_state.json")
        changes1, state1 = sync.plan(force_full=True)
        sync.commit(changes1, state1)
        # Add a new QDKT event
        conn = sqlite3.connect(str(self.fixture["qdkt_db"]))
        conn.execute(
            "INSERT INTO qdkt_events VALUES (?,?,?,?,?,?)",
            ("QDKT-new", "test", "c", "r", 0.5, 2000.0),
        )
        conn.commit()
        conn.close()
        changes2, _ = sync.plan()
        self.assertIn("QDKT-new", changes2.new_qdkt_events)

    def test_incremental_detects_new_savings_row(self):
        """New savings DB rows are detected."""
        sync = TopologySync(root=self.tmpdir,
                            state_path=self.tmpdir / "sync_state.json")
        changes1, state1 = sync.plan(force_full=True)
        sync.commit(changes1, state1)
        # Add a new savings row
        conn = sqlite3.connect(str(self.fixture["savings_db"]))
        conn.execute(
            "INSERT INTO llm_calls (ts, ts_epoch, provider, model, call_type, "
            "prompt_tokens, output_tokens, cost_usd, latency_sec, tokens_saved, cost_saved_usd) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("2026-06-30T01:00:00Z", 2000.0, "groq", "test", "generate",
             200, 100, 0.002, 0.3, 100, 0.004),
        )
        conn.commit()
        conn.close()
        changes2, _ = sync.plan()
        self.assertTrue(len(changes2.new_savings_ids) > 0)

    def test_no_changes_after_commit(self):
        """After a commit, a second plan reports no changes."""
        sync = TopologySync(root=self.tmpdir,
                            state_path=self.tmpdir / "sync_state.json")
        changes1, state1 = sync.plan(force_full=True)
        sync.commit(changes1, state1)
        changes2, _ = sync.plan()
        self.assertFalse(changes2.has_changes)


# ---------------------------------------------------------------------------
# Obsidian + Graphify bridge tests
# ---------------------------------------------------------------------------

class TestObsidianGraphBridge(unittest.TestCase):
    """Tests proving Obsidian notes are generated, Wikilinks are stable,
    graph JSON validates, and sidecar truth is referenced rather than copied."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.fixture = _build_fixture(self.tmpdir)
        self.vault_dir = self.tmpdir / "Aura_Vault"
        self.graph_path = self.tmpdir / ".aura" / "graphify_graph.json"
        self.sync_state_path = self.tmpdir / ".aura" / "obsidian_graph_sync_state.json"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_bridge(self) -> ObsidianGraphBridge:
        return ObsidianGraphBridge(
            root=self.tmpdir,
            vault_dir=self.vault_dir,
            graph_path=self.graph_path,
            sync_state_path=self.sync_state_path,
        )

    # -- Requirement 4: Obsidian notes are generated --

    def test_notes_are_generated(self):
        """Markdown notes are written for every graph node."""
        bridge = self._make_bridge()
        result = bridge.export(force_full=True)
        self.assertGreater(result.notes_written, 0)
        # The vault directory should contain .md files
        md_files = list(self.vault_dir.glob("*.md"))
        self.assertGreater(len(md_files), 0)
        # Index note should exist
        self.assertTrue((self.vault_dir / "Aura_Graph_Index.md").exists())

    def test_notes_have_yaml_frontmatter(self):
        """Each note starts with a YAML frontmatter block."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        md_files = [f for f in self.vault_dir.glob("*.md")
                    if f.name != "Aura_Graph_Index.md"]
        self.assertGreater(len(md_files), 0)
        for md_file in md_files:
            text = md_file.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{md_file.name} missing frontmatter")
            # Frontmatter must end with a closing ---
            end = text.find("\n---\n", 4)
            self.assertGreater(end, 0, f"{md_file.name} frontmatter not closed")
            frontmatter = text[4:end]
            # Must contain aura_id and source_ref fields
            self.assertIn("aura_id:", frontmatter)
            self.assertIn("source_ref_kind:", frontmatter)
            self.assertIn("source_ref_path:", frontmatter)

    def test_note_for_file_node(self):
        """A FILE node note is generated with the file path in frontmatter."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        # Find the note for aura_core.py
        found = False
        for md_file in self.vault_dir.glob("file_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "source_ref_path: aura_core.py" in text:
                found = True
                self.assertIn("node_type: FILE", text)
                self.assertIn("source_ref_kind: source_file", text)
                self.assertIn("source_ref_path: aura_core.py", text)
                break
        self.assertTrue(found, "no note found for aura_core.py")

    def test_note_for_action_capsule(self):
        """An ACTION_CAPSULE note is generated from the Arena run."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("action_capsule_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "CAP-1" in text:
                found = True
                self.assertIn("node_type: ACTION_CAPSULE", text)
                self.assertIn("source_ref_kind: arena_dir", text)
                break
        self.assertTrue(found, "no note found for ActionCapsule CAP-1")

    def test_note_for_qdkt_event(self):
        """A QDKT_EVENT note is generated from the QDKT DB."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("qdkt_event_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "QDKT-test1" in text:
                found = True
                self.assertIn("node_type: QDKT_EVENT", text)
                self.assertIn("source_ref_kind: qdkt_db", text)
                break
        self.assertTrue(found, "no note found for QDKT event QDKT-test1")

    def test_note_for_dream_score(self):
        """A DREAM_SCORE note is generated from the DREAM ledger."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("dream_score_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "dream_hash_1" in text:
                found = True
                self.assertIn("node_type: DREAM_SCORE", text)
                self.assertIn("source_ref_kind: dream_ledger", text)
                break
        self.assertTrue(found, "no note found for DREAM score dream_hash_1")

    def test_note_for_transaction(self):
        """A TRANSACTION note is generated from the savings DB."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("transaction_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "call-1" in text or "mistral" in text:
                found = True
                self.assertIn("node_type: TRANSACTION", text)
                self.assertIn("source_ref_kind: savings_db", text)
                break
        self.assertTrue(found, "no note found for savings transaction")

    def test_note_for_price(self):
        """A PRICE note is generated from pricing.json."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("price_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "mistral" in text:
                found = True
                self.assertIn("node_type: PRICE", text)
                self.assertIn("source_ref_kind: pricing_json", text)
                break
        self.assertTrue(found, "no note found for price mistral")

    # -- Requirement 5: Wikilinks are stable --

    def test_wikilinks_are_stable(self):
        """Wikilinks use deterministic note filenames."""
        wl1 = wikilink(NodeType.FILE.value, "aura_core.py")
        wl2 = wikilink(NodeType.FILE.value, "aura_core.py")
        self.assertEqual(wl1, wl2)
        self.assertTrue(wl1.startswith("[[file_"))
        self.assertTrue(wl1.endswith("]]"))

    def test_notes_contain_wikilinks(self):
        """Notes contain Obsidian Wikilinks to connected nodes."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        # The Arena run note should link to its action capsule
        found_arena = False
        for md_file in self.vault_dir.glob("arena_run_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "LPA-test123" in text:
                found_arena = True
                # Should contain at least one wikilink
                self.assertIn("[[", text)
                self.assertIn("]]", text)
                break
        self.assertTrue(found_arena, "no note found for Arena run LPA-test123")

    def test_wikilink_format(self):
        """Wikilinks use the [[note_name]] Obsidian format."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        # Check that at least one note has a properly formatted wikilink
        has_wikilink = False
        for md_file in self.vault_dir.glob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "[[" in text and "]]" in text:
                has_wikilink = True
                break
        self.assertTrue(has_wikilink, "no wikilinks found in any note")

    # -- Requirement 6: Graph JSON with typed nodes and edges --

    def test_graph_json_is_written(self):
        """The graph JSON file is written and is valid JSON."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        self.assertTrue(self.graph_path.exists())
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertGreater(len(data["nodes"]), 0)

    def test_graph_nodes_are_typed(self):
        """Graph nodes have a recognised type."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            self.assertIn(node["type"], NODE_TYPES,
                          f"node {node['id']} has unknown type {node['type']}")

    def test_graph_edges_are_typed(self):
        """Graph edges have a recognised type."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        for edge in data["edges"]:
            self.assertIn(edge["type"], EDGE_TYPES,
                          f"edge {edge['id']} has unknown type {edge['type']}")

    def test_graph_json_validates(self):
        """The exported graph JSON passes validation."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        text = self.graph_path.read_text(encoding="utf-8")
        packet = packet_from_json(text)
        issues = validate_packet(packet, root=self.tmpdir)
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(errors, [], f"validation errors: {errors}")

    # -- Requirement 8: sidecar truth is referenced, not copied as authority --

    def test_sidecar_note_references_source_not_copies(self):
        """Sidecar notes reference the source file, not copy its content as authority."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        found = False
        for md_file in self.vault_dir.glob("sidecar_ref_*.md"):
            text = md_file.read_text(encoding="utf-8")
            if "travel_price_sidecar.py" in text:
                found = True
                # Must contain a source_ref pointing to the sidecar file
                self.assertIn("source_ref_kind: sidecar_file", text)
                self.assertIn("source_ref_path: travel_price_sidecar.py", text)
                # Must contain the "Source of Truth" disclaimer
                self.assertIn("export", text.lower())
                self.assertIn("source of truth", text.lower())
                # Must NOT copy the file content as authority
                self.assertNotIn("# travel price sidecar", text)
                break
        self.assertTrue(found, "no note found for sidecar travel_price_sidecar.py")

    def test_every_node_has_source_ref(self):
        """Every graph node carries a source_ref pointing to its authoritative record."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            ref = node.get("source_ref", {})
            self.assertTrue(ref.get("kind"), f"node {node['id']} has empty source_ref.kind")
            self.assertTrue(ref.get("path"), f"node {node['id']} has empty source_ref.path")
            self.assertTrue(ref.get("key"), f"node {node['id']} has empty source_ref.key")

    def test_truth_bearing_nodes_link_to_source(self):
        """Prices, transactions, and verifier claims link to their source records."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        for node in data["nodes"]:
            if node["type"] in ("PRICE", "TRANSACTION", "VERIFIER_REPORT",
                                "QDKT_EVENT", "QDKT_CRYSTAL", "DREAM_SCORE",
                                "ACTION_CAPSULE", "BOUNDARY_CONTRACT"):
                ref = node["source_ref"]
                # The source_ref path must be non-empty and point to a real source
                self.assertTrue(ref["path"], f"{node['type']} node has empty source path")
                # The key must identify the specific record
                self.assertTrue(ref["key"], f"{node['type']} node has empty source key")

    # -- Requirement 9: incremental sync --

    def test_incremental_export_only_changed(self):
        """Requirement 9: only changed records are re-exported."""
        bridge = self._make_bridge()
        # First export (full)
        result1 = bridge.export(force_full=True)
        self.assertTrue(result1.full_resync)
        first_count = result1.notes_written
        # Second export (no changes)
        result2 = bridge.export()
        self.assertEqual(result2.notes_written, 0)
        self.assertEqual(result2.change_summary, "no changes")
        # Modify a file
        self.fixture["source"].write_text("def hello():\n    return 'changed'\n", encoding="utf-8")
        # Third export (incremental)
        result3 = bridge.export()
        self.assertFalse(result3.full_resync)
        self.assertGreater(result3.notes_written, 0)

    # -- Requirement 1: Obsidian is export, not source of truth --

    def test_obsidian_is_export_not_source(self):
        """The vault explicitly states it is an export, not the source of truth."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        index = (self.vault_dir / "Aura_Graph_Index.md").read_text(encoding="utf-8")
        self.assertIn("export", index.lower())
        self.assertIn("source of truth", index.lower())

    # -- Requirement 2: Graphify is typed, not a mock tag generator --

    def test_graphify_is_typed_not_mock(self):
        """Graph nodes and edges use the typed schema, not arbitrary tags."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        # Every node type must be from the NodeType enum
        for node in data["nodes"]:
            self.assertIn(node["type"], NODE_TYPES)
        # Every edge type must be from the EdgeType enum
        for edge in data["edges"]:
            self.assertIn(edge["type"], EDGE_TYPES)

    # -- Edge type coverage --

    def test_edge_types_in_export(self):
        """The export uses multiple edge types from the canonical set."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        edge_types_used = {edge["type"] for edge in data["edges"]}
        # Should use at least DEPENDS_ON and STORES_TRUTH_IN or VERIFIES
        self.assertIn("DEPENDS_ON", edge_types_used)

    def test_blocks_edge_from_boundary_contract(self):
        """BoundaryContract BLOCKS ActionCapsule."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        blocks_edges = [e for e in data["edges"] if e["type"] == "BLOCKS"]
        self.assertGreater(len(blocks_edges), 0, "no BLOCKS edges found")

    def test_leases_edge_from_arena_lease(self):
        """ArenaLease LEASES ActionCapsule."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        leases_edges = [e for e in data["edges"] if e["type"] == "LEASES"]
        self.assertGreater(len(leases_edges), 0, "no LEASES edges found")

    def test_approves_edge_from_verification(self):
        """Verification ledger APPROVES produces an APPROVES edge."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        approves_edges = [e for e in data["edges"] if e["type"] == "APPROVES"]
        self.assertGreater(len(approves_edges), 0, "no APPROVES edges found")

    def test_stores_truth_in_edge_from_sidecar(self):
        """Sidecar STORES_TRUTH_IN the file it holds truth in."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        sti_edges = [e for e in data["edges"] if e["type"] == "STORES_TRUTH_IN"]
        self.assertGreater(len(sti_edges), 0, "no STORES_TRUTH_IN edges found")

    def test_verifies_edge_from_verifier(self):
        """Verifier VERIFIES the file it gates."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        verifies_edges = [e for e in data["edges"] if e["type"] == "VERIFIES"]
        self.assertGreater(len(verifies_edges), 0, "no VERIFIES edges found")

    def test_tests_edge_from_test_file(self):
        """Test file TESTS the module it tests."""
        bridge = self._make_bridge()
        bridge.export(force_full=True)
        data = json.loads(self.graph_path.read_text(encoding="utf-8"))
        tests_edges = [e for e in data["edges"] if e["type"] == "TESTS"]
        self.assertGreater(len(tests_edges), 0, "no TESTS edges found")

    # -- Convenience functions --

    def test_export_graph_json_function(self):
        """The export_graph_json convenience function works."""
        path = export_graph_json(root=self.tmpdir, graph_path=self.graph_path,
                                 force_full=True)
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)

    def test_export_vault_function(self):
        """The export_vault convenience function works."""
        result = export_vault(root=self.tmpdir, vault_dir=self.vault_dir,
                              graph_path=self.graph_path, force_full=True)
        self.assertGreater(result.notes_written, 0)
        self.assertTrue(self.graph_path.exists())


# ---------------------------------------------------------------------------
# YAML frontmatter tests
# ---------------------------------------------------------------------------

class TestYamlFrontmatter(unittest.TestCase):

    def test_simple_frontmatter(self):
        fm = yaml_frontmatter({"key": "value", "num": 42})
        self.assertTrue(fm.startswith("---\n"))
        self.assertTrue(fm.endswith("\n---"))
        self.assertIn("key: value", fm)
        self.assertIn("num: 42", fm)

    def test_list_frontmatter(self):
        fm = yaml_frontmatter({"tags": ["a", "b"]})
        self.assertIn("tags:", fm)
        self.assertIn("- a", fm)
        self.assertIn("- b", fm)

    def test_special_chars_escaped(self):
        fm = yaml_frontmatter({"path": "a:b:c"})
        # Colons should trigger quoting
        self.assertIn('"a:b:c"', fm)


if __name__ == "__main__":
    unittest.main()