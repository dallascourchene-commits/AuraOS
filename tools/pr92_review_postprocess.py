from pathlib import Path

path = Path("tests/test_aura_ai_router_dynamic.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '''(tmp_path / "alpha.py").write_text("def target():
    return 'alpha'
", encoding="utf-8")''',
    '''(tmp_path / "alpha.py").write_text("def target():\\n    return 'alpha'\\n", encoding="utf-8")''',
)
text = text.replace(
    '''(tmp_path / "beta.py").write_text("def target():
    return 'beta'
", encoding="utf-8")''',
    '''(tmp_path / "beta.py").write_text("def target():\\n    return 'beta'\\n", encoding="utf-8")''',
)
path.write_text(text, encoding="utf-8")

# The generic Cognome store supports approved PAIRED_LIVE comparison records
# without router-specific authorization metadata. Router replay protection is
# supplied by its authorization-bound comparison ID, so preserve this API.
path = Path("aura_model_cognome_store_io.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '        if mode == "PAIRED_LIVE" and not str(clean.get("authorization_id") or "").strip(): raise ValueError("PAIRED_LIVE requires authorization_id")\n',
    "",
)
path.write_text(text, encoding="utf-8")

# Equal-degree hubs originate from a set, so degree-only sorting is unstable.
path = Path("aura_topology_manager.py")
text = path.read_text(encoding="utf-8")
text = text.replace(
    '''        hubs = sorted(
            [(nid, in_degree[nid] + out_degree[nid]) for nid in connected],
            key=lambda x: x[1],
            reverse=True,
        )[:15]
''',
    '''        hubs = sorted(
            [(nid, in_degree[nid] + out_degree[nid]) for nid in connected],
            key=lambda item: (-item[1], item[0]),
        )[:15]
''',
)
path.write_text(text, encoding="utf-8")

path = Path("tests/test_aura_adaptive_security.py")
text = path.read_text(encoding="utf-8")
marker = "test_topology_hub_ties_are_sorted_by_node_id"
if marker not in text:
    text = text.rstrip() + '''


def test_topology_hub_ties_are_sorted_by_node_id(tmp_path) -> None:
    from aura_topology_manager import TopologyBuilder

    builder = TopologyBuilder(tmp_path)
    builder.nodes = [{"id": node_id} for node_id in ("c", "a", "b")]
    builder._node_ids = {"a", "b", "c"}
    builder.edges = [
        {"source": "a", "target": "b", "kind": "call"},
        {"source": "b", "target": "c", "kind": "call"},
        {"source": "c", "target": "a", "kind": "call"},
    ]

    hubs = builder._compute_diagnostics()["top_hubs"]
    assert [item["id"] for item in hubs] == ["a", "b", "c"]
''' + "\n"
path.write_text(text, encoding="utf-8")
