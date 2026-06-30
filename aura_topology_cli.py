"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9b5-[Q-SYS:TOPOLOGY_CLI]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / CLI Interface)
DEPENDENCIES: __future__, argparse, json, pathlib, sys, typing, aura_topology_snapshot_builder, aura_scene_graph_exporter, aura_amd_demo_scenario
FUNCTIONS: main, run_cmd
SYNOPSIS: Exposes command-line interface utilities for snapshotting, exporting, and running demo scenarios.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from aura_topology_snapshot_builder import AuraTopologySnapshotBuilder
from aura_scene_graph_exporter import AuraSceneGraphExporter
from aura_amd_demo_scenario import run_demo_scenario
from aura_topology_state_machine import TopologyStateMachine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AuraOS Topology-Native Substrate CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Command: snapshot
    subparsers.add_parser("snapshot", help="Build and print summary of current topology snapshot")

    # Command: demo-amd
    subparsers.add_parser("demo-amd", help="Run the 10-step AMD Hackathon Demo Scenario")

    # Command: export
    export_parser = subparsers.add_parser("export", help="Export the active topology graph")
    export_parser.add_argument("--format", choices=["cytoscape", "threejs", "all"], default="all",
                               help="Format to export (default: all)")
    export_parser.add_argument("--outdir", default="Aura_Sandbox", help="Output directory (default: Aura_Sandbox)")

    # Command: explain-node
    explain_parser = subparsers.add_parser("explain-node", help="Inspect properties of a specific node")
    explain_parser.add_argument("node_id", help="Node ID (e.g. aura_node.py::TokenEncoder)")

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        builder = AuraTopologySnapshotBuilder()
        snapshot = builder.build_snapshot("cli_snap")
        print("=== AURAOS SCENE GRAPH SNAPSHOT ===")
        print(f"  Snapshot ID    : {snapshot.snapshot_id}")
        print(f"  Timestamp      : {snapshot.timestamp}")
        print(f"  Version        : {snapshot.version}")
        print(f"  Total Nodes    : {len(snapshot.nodes)}")
        print(f"  Total Edges    : {len(snapshot.edges)}")
        print(f"  Density Score  : {snapshot.topology_density_score}")
        return 0

    elif args.command == "demo-amd":
        success = run_demo_scenario(verbose=True)
        return 0 if success else 1

    elif args.command == "export":
        builder = AuraTopologySnapshotBuilder()
        snapshot = builder.build_snapshot("cli_export_snap")
        exporter = AuraSceneGraphExporter(args.outdir)
        
        if args.format == "all":
            res = exporter.export_all(snapshot)
            print(f"Successfully exported all formats to: {args.outdir}")
            for fmt, path in res.items():
                print(f"  • {fmt}: {path}")
        elif args.format == "cytoscape":
            cy = exporter.to_cytoscape(snapshot)
            out_file = Path(args.outdir) / "cytoscape_graph.json"
            out_file.write_text(json.dumps(cy, indent=2), encoding="utf-8")
            print(f"Exported Cytoscape JSON to: {out_file}")
        elif args.format == "threejs":
            tj = exporter.to_threejs(snapshot)
            out_file = Path(args.outdir) / "threejs_graph.json"
            out_file.write_text(json.dumps(tj, indent=2), encoding="utf-8")
            print(f"Exported Three.js JSON to: {out_file}")
        return 0

    elif args.command == "explain-node":
        builder = AuraTopologySnapshotBuilder()
        snapshot = builder.build_snapshot("cli_explain_snap")
        node_id = args.node_id
        
        if node_id not in snapshot.nodes:
            # Try to match by contains
            matches = [nid for nid in snapshot.nodes if node_id.lower() in nid.lower()]
            if not matches:
                print(f"[-] Node '{node_id}' not found in snapshot.")
                return 1
            node_id = matches[0]
            print(f"[*] Partial match found, explaining: {node_id}")

        node = snapshot.nodes[node_id]
        allowed, forbidden = TopologyStateMachine.derive_gates(node)
        print(f"=== NODE EXPLANATION: {node.node_id} ===")
        print(f"  Type           : {node.node_type}")
        print(f"  Shape / Color  : {node.shape} / {node.color}")
        print(f"  Status         : {node.status}")
        print(f"  Luminance      : {node.luminance}")
        print(f"  Source Ref     : {node.source_ref.kind} at {node.source_ref.path}")
        print(f"  Hardware Target: {node.hardware_profile.preferred_device} ({node.hardware_profile.execution_status})")
        print(f"  Allowed Actions: {allowed}")
        print(f"  Forbidden      : {forbidden}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
