"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:SCENE_GRAPH_EXPORTER]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Visual Export)
DEPENDENCIES: __future__, json, pathlib, typing, aura_scene_graph_schema
FUNCTIONS: AuraSceneGraphExporter, export_all, to_cytoscape, to_threejs, to_obsidian
SYNOPSIS: Serializes and exports SceneGraphSnapshot views into standard Cytoscape, Three.js, and Obsidian formats.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List
from aura_scene_graph_schema import SceneGraphSnapshot


class AuraSceneGraphExporter:
    """
    Serializes and exports immutable SceneGraphSnapshot views to multiple targets
    for consumption by humans, LLMs, and front-end visualization engines.
    """

    def __init__(self, output_dir: str | Path = "."):
        self.output_dir = Path(output_dir).resolve()

    def to_dict(self, snapshot: SceneGraphSnapshot) -> Dict[str, Any]:
        """Serializes the snapshot to a plain python dict."""
        nodes_dict = {}
        for nid, node in snapshot.nodes.items():
            nodes_dict[nid] = {
                "id": node.node_id,
                "type": node.node_type,
                "shape": node.shape,
                "color": node.color,
                "status": node.status,
                "luminance": node.luminance,
                "source_ref": {
                    "kind": node.source_ref.kind,
                    "path": node.source_ref.path,
                    "symbol": node.source_ref.symbol,
                },
                "hardware_profile": {
                    "preferred_device": node.hardware_profile.preferred_device,
                    "execution_status": node.hardware_profile.execution_status,
                }
            }
        
        edges_list = []
        for edge in snapshot.edges:
            edges_list.append({
                "source": edge.source,
                "target": edge.target,
                "edge_type": edge.edge_type,
                "verified": edge.verified,
                "luminance": edge.luminance,
            })

        return {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp,
            "nodes": nodes_dict,
            "edges": edges_list,
            "topology_density_score": snapshot.topology_density_score,
            "active_prior_id": snapshot.active_prior_id,
            "version": snapshot.version
        }

    def to_cytoscape(self, snapshot: SceneGraphSnapshot) -> Dict[str, Any]:
        """Exports snapshot to Cytoscape.js elements JSON format."""
        elements = []
        for nid, node in snapshot.nodes.items():
            elements.append({
                "data": {
                    "id": node.node_id,
                    "label": node.node_id,
                    "shape": node.shape,
                    "color": node.color,
                    "luminance": node.luminance,
                    "status": node.status,
                }
            })
        for edge in snapshot.edges:
            elements.append({
                "data": {
                    "id": f"{edge.source}->{edge.target}",
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.edge_type,
                }
            })
        return {"elements": elements}

    def to_threejs(self, snapshot: SceneGraphSnapshot) -> Dict[str, Any]:
        """Exports snapshot to Three.js-compatible coordinates format."""
        nodes_list = []
        import random
        # Seed randomly to get stable coordinates for demo
        rng = random.Random(hash(snapshot.snapshot_id))
        
        for nid, node in snapshot.nodes.items():
            nodes_list.append({
                "id": node.node_id,
                "x": round(rng.uniform(-10.0, 10.0), 3),
                "y": round(rng.uniform(-10.0, 10.0), 3),
                "z": round(rng.uniform(-10.0, 10.0), 3),
                "shape": node.shape,
                "color": node.color,
                "luminance": node.luminance,
            })
        
        links_list = []
        for edge in snapshot.edges:
            links_list.append({
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
            })
        return {"nodes": nodes_list, "links": links_list}

    def to_obsidian(self, snapshot: SceneGraphSnapshot, vault_dir_name: str = "Aura_Vault") -> Path:
        """Exports nodes to Obsidian-compatible markdown notes."""
        vault_path = self.output_dir / vault_dir_name
        vault_path.mkdir(parents=True, exist_ok=True)
        
        for nid, node in snapshot.nodes.items():
            # Sanitize filename
            filename = nid.replace("::", "__").replace("/", "_").replace("\\", "_")
            if not filename.endswith(".md"):
                filename = f"{filename}.md"
            
            note_path = vault_path / filename
            
            # Find neighbors for wiki-links
            in_links = [e.source for e in snapshot.edges if e.target == nid]
            out_links = [e.target for e in snapshot.edges if e.source == nid]
            
            wiki_links = []
            for link in in_links:
                lnk_file = link.replace("::", "__").replace("/", "_").replace("\\", "_")
                wiki_links.append(f"- [[{lnk_file}]] (incoming)")
            for link in out_links:
                lnk_file = link.replace("::", "__").replace("/", "_").replace("\\", "_")
                wiki_links.append(f"- [[{lnk_file}]] (outgoing)")

            content = [
                "---",
                f"id: \"{node.node_id}\"",
                f"type: {node.node_type}",
                f"status: {node.status}",
                f"luminance: {node.luminance}",
                f"preferred_device: {node.hardware_profile.preferred_device}",
                "---",
                "",
                f"# Node: {node.node_id}",
                "",
                f"**Type**: {node.node_type}  ",
                f"**Status**: {node.status}  ",
                f"**Luminance**: {node.luminance}  ",
                f"**Preferred Hardware Device**: {node.hardware_profile.preferred_device}  ",
                "",
                "## Relationships",
                "\n".join(wiki_links) if wiki_links else "No active topology links.",
                "",
                "## Metadata",
                f"Grounding score: {node.source_grounding_score}",
                f"Verifier score: {node.verifier_pass_score}",
                f"Missing symbol penalty: {node.missing_symbol_penalty}",
            ]
            note_path.write_text("\n".join(content), encoding="utf-8")
        
        return vault_path

    def export_all(self, snapshot: SceneGraphSnapshot) -> Dict[str, Any]:
        """Saves all format variants to the output directory."""
        # Generic graph.json
        graph_dict = self.to_dict(snapshot)
        (self.output_dir / "graph.json").write_text(json.dumps(graph_dict, indent=2), encoding="utf-8")
        
        # Graphify JSON
        (self.output_dir / "graphify_graph.json").write_text(json.dumps(graph_dict, indent=2), encoding="utf-8")

        # Cytoscape JSON
        cy_dict = self.to_cytoscape(snapshot)
        (self.output_dir / "cytoscape_graph.json").write_text(json.dumps(cy_dict, indent=2), encoding="utf-8")

        # Threejs JSON
        three_dict = self.to_threejs(snapshot)
        (self.output_dir / "threejs_graph.json").write_text(json.dumps(three_dict, indent=2), encoding="utf-8")

        # Obsidian vault
        vault_path = self.to_obsidian(snapshot)

        return {
            "graph_json": str(self.output_dir / "graph.json"),
            "graphify_json": str(self.output_dir / "graphify_graph.json"),
            "cytoscape_json": str(self.output_dir / "cytoscape_graph.json"),
            "threejs_json": str(self.output_dir / "threejs_graph.json"),
            "obsidian_vault": str(vault_path),
        }
