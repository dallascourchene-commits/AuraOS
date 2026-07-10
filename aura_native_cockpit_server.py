"""
Aura Native Cockpit Server — CLI entry point for the native cockpit.

Usage:
    python -m aura_native_cockpit --repo-root .
    python -m aura_native_cockpit ingest-intent --file .aura/intents/example.aura.md
    python -m aura_native_cockpit contract --objective "Refactor Fireworks egress"
    python -m aura_native_cockpit connectome
    python -m aura_native_cockpit token-economy --objective "..." --files f1.py,f2.py
    python -m aura_native_cockpit gates
    python -m aura_native_cockpit handoff --intent-file .aura/intents/example.aura.md --agent hermes

The cockpit is read-only — it never mutates production code.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from aura_native_cockpit import AuraNativeCockpit, COCKPIT_VERSION


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aura-native-cockpit",
        description="Aura Native Cockpit — primary human coding interface.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    subparsers = parser.add_subparsers(dest="command", help="Cockpit commands")

    # ingest-intent
    p_ingest = subparsers.add_parser("ingest-intent", help="Ingest an intent document")
    p_ingest.add_argument("--file", required=True, help="Path to .aura.md intent document")
    p_ingest.add_argument("--json", action="store_true", help="Output full JSON")

    # contract
    p_contract = subparsers.add_parser("contract", help="Generate a native cockpit contract")
    p_contract.add_argument("--objective", required=True, help="Coding objective")
    p_contract.add_argument("--json", action="store_true", help="Output full JSON")

    # validate-lexc
    p_lexc = subparsers.add_parser("validate-lexc", help="Validate LEXC route from intent document")
    p_lexc.add_argument("--file", required=True, help="Path to .aura.md intent document")

    # connectome
    p_connectome = subparsers.add_parser("connectome", help="Build capability connectome")

    # capability-path
    p_cap_path = subparsers.add_parser("capability-path", help="Find capability path for an objective")
    p_cap_path.add_argument("--objective", required=True, help="Coding objective")

    # explain-capability
    p_explain = subparsers.add_parser("explain-capability", help="Explain a capability")
    p_explain.add_argument("--id", required=True, help="Capability ID")

    # token-economy
    p_economy = subparsers.add_parser("token-economy", help="Compute token economy report")
    p_economy.add_argument("--objective", required=True, help="Coding objective")
    p_economy.add_argument("--files", required=True, help="Comma-separated file paths")

    # gates
    p_gates = subparsers.add_parser("gates", help="Show workflow state machine")

    # evaluate-gate
    p_eval = subparsers.add_parser("evaluate-gate", help="Evaluate a workflow gate")
    p_eval.add_argument("--state", required=True, help="Workflow state name")
    p_eval.add_argument("--evidence", default="{}", help="JSON evidence dict")

    # ground
    p_ground = subparsers.add_parser("ground", help="Ground an intent")
    p_ground.add_argument("--objective", required=True, help="Coding objective")
    p_ground.add_argument("--target-symbol", default=None, help="Target symbol")

    # handoff
    p_handoff = subparsers.add_parser("handoff", help="Prepare agent handoff from intent document")
    p_handoff.add_argument("--intent-file", required=True, help="Path to .aura.md intent document")
    p_handoff.add_argument("--agent", default="hermes", help="Agent name (hermes, codex)")

    # diagnose
    p_diag = subparsers.add_parser("diagnose", help="Diagnose a topology node")
    p_diag.add_argument("--node-id", required=True, help="Node ID")

    # emergent-audit
    p_emergent = subparsers.add_parser("emergent-audit", help="Run emergent capability audit")
    p_emergent.add_argument("--objective", required=True, help="Coding objective")

    args = parser.parse_args(argv)

    if not args.command:
        # No subcommand — print info
        print(f"Aura Native Cockpit v{COCKPIT_VERSION}")
        print("Use --help for available commands.")
        return 0

    cockpit = AuraNativeCockpit(repo_root=args.repo_root)

    if args.command == "ingest-intent":
        result = cockpit.ingest_intent(args.file)
        if args.json or not result.get("ok"):
            _print_json(result)
        else:
            # Print a summary
            print(f"Objective: {result.get('objective', '')}")
            print(f"Polysynthetic: {result.get('polysynthetic_packet', '')}")
            print(f"LEXC valid: {result.get('lexc_valid', False)}")
            print(f"Route: {result.get('route_decision', {}).get('route', '')}")
            print(f"Likely files: {', '.join(result.get('likely_files', [])[:5])}")
            print(f"Likely symbols: {', '.join(result.get('likely_symbols', [])[:5])}")
        return 0 if result.get("ok") else 1

    elif args.command == "contract":
        result = cockpit.cockpit_contract(args.objective)
        if args.json:
            _print_json(result)
        else:
            print(result.get("contract", ""))
        return 0 if result.get("ok") else 1

    elif args.command == "validate-lexc":
        result = cockpit.validate_lexc_route(args.file)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "connectome":
        result = cockpit.capability_connectome()
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "capability-path":
        result = cockpit.capability_path(args.objective)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "explain-capability":
        result = cockpit.explain_capability(args.id)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "token-economy":
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        result = cockpit.token_economy(args.objective, files)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "gates":
        result = cockpit.workflow_gates()
        _print_json(result)
        return 0 if result.get("ok", True) else 1

    elif args.command == "evaluate-gate":
        try:
            evidence = json.loads(args.evidence)
        except json.JSONDecodeError:
            evidence = {}
        result = cockpit.evaluate_gate(args.state, evidence)
        _print_json(result)
        return 0 if result.get("ok", False) else 1

    elif args.command == "ground":
        result = cockpit.ground_intent(args.objective, args.target_symbol)
        _print_json(result)
        return 0 if result.get("ok", result.get("grounding_ok", False)) else 1

    elif args.command == "handoff":
        # First ingest the intent
        packet = cockpit.ingest_intent(args.intent_file)
        if not packet.get("ok"):
            _print_json(packet)
            return 1
        # Then prepare handoff
        result = cockpit.prepare_handoff(packet, agent=args.agent)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "diagnose":
        result = cockpit.diagnose_selection(args.node_id)
        _print_json(result)
        return 0 if result.get("ok") else 1

    elif args.command == "emergent-audit":
        result = cockpit.emergent_audit(args.objective)
        _print_json(result)
        return 0 if result.get("ok") else 1

    # Unsupported command
    print(f"Unsupported command: {args.command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
