"""
Aura Agent Arena Bridge — CLI wrapper.

Exposes all bridge tools as shell commands so any CLI-based agent can use
Aura's Coding Arena without MCP support.

Usage:
    python -m aura_agent_arena_cli digest
    python -m aura_agent_arena_cli prepare --objective "..." --target-file ... --target-symbol ...
    python -m aura_agent_arena_cli search --query "..." --kind symbol
    python -m aura_agent_arena_cli context --task-id A1 --format both
    python -m aura_agent_arena_cli read-slice --file aura_fst_routing.py --symbol AuraCodingArenaRouter
    python -m aura_agent_arena_cli fireworks-patch --task-id A1 --instruction "..."
    python -m aura_agent_arena_cli stage-patch --task-id A1 --diff-file patch.diff
    python -m aura_agent_arena_cli verify --scope declared
    python -m aura_agent_arena_cli repair-packet --task-id A1
    python -m aura_agent_arena_cli status
    python -m aura_agent_arena_cli export-icm
    python -m aura_agent_arena_cli find-affordances --objective "refactor coding arena"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_fireworks import fireworks_patch_worker

# Hermes Arena Mode — optional import (additive, does not break existing CLI)
try:
    from aura_hermes_arena_mode import (
        generate_hermes_contract,
        generate_pr_runbook,
        generate_token_savings_report,
        run_preflight,
        write_hermes_aura_rules,
    )
    _HERMES_MODE_AVAILABLE = True
except Exception:  # noqa: BLE001
    _HERMES_MODE_AVAILABLE = False

# Module-level bridge instance — persists across CLI calls within one process.
_bridge: AuraAgentArenaBridge | None = None
# Module-level plan_phase_hash — set by prepare, used by subsequent commands.
_plan_phase_hash: str | None = None


def _get_bridge() -> AuraAgentArenaBridge:
    global _bridge
    if _bridge is None:
        _bridge = AuraAgentArenaBridge()
    return _bridge


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def _load_plan_phase_hash() -> str | None:
    """Load plan_phase_hash from env or a temp file."""
    global _plan_phase_hash
    if _plan_phase_hash:
        return _plan_phase_hash
    env_hash = os.environ.get("AURA_ARENA_PLAN_PHASE_HASH", "")
    if env_hash:
        return env_hash
    # Try loading from temp file.
    try:
        from pathlib import Path

        p = Path("/tmp/aura_arena_plan_phase_hash")
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _save_plan_phase_hash(phase_hash: str) -> None:
    global _plan_phase_hash
    _plan_phase_hash = phase_hash
    try:
        from pathlib import Path

        Path("/tmp/aura_arena_plan_phase_hash").write_text(phase_hash, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _require_plan_phase_hash() -> str:
    phase_hash = _load_plan_phase_hash()
    if not phase_hash:
        print(json.dumps({
            "ok": False,
            "error": "No plan_phase_hash found. Run 'prepare' first or set AURA_ARENA_PLAN_PHASE_HASH env.",
        }, indent=2))
        raise SystemExit(1)
    return phase_hash


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_digest(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_repo_digest(
        include_hubs=not args.no_hubs,
        max_lines=args.max_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_prepare(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_prepare_arena(
        objective=args.objective,
        target_file=args.target_file,
        target_symbol=args.target_symbol,
        acceptance_criteria=args.acceptance_criteria.split(",") if args.acceptance_criteria else None,
        risk_map=args.risk_map.split(",") if args.risk_map else None,
        constraints=args.constraints.split(",") if args.constraints else None,
    )
    if result.get("ok") and result.get("plan_phase_hash"):
        _save_plan_phase_hash(result["plan_phase_hash"])
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_search(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_search_code(
        query=args.query,
        search_kind=args.kind,
        max_results=args.max_results,
        include_neighbors=not args.no_neighbors,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_context(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        depth=args.depth,
        format=args.format,
        max_tokens_est=args.max_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_read_slice(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_read_slice(
        file=args.file,
        symbol=args.symbol,
        line_start=args.line_start,
        line_end=args.line_end,
        max_lines=args.max_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_fireworks_patch(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()

    # Get compressed context for the task.
    context_result = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
    )
    compressed_context = context_result.get("compressed_context", "")

    result = fireworks_patch_worker(
        task_id=args.task_id,
        compressed_context=compressed_context,
        instruction=args.instruction,
        model_tier=args.model_tier,
        max_output_tokens=args.max_output_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_stage_patch(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()

    # Read diff from file or stdin.
    diff_content = ""
    if args.diff_file:
        try:
            with open(args.diff_file, "r", encoding="utf-8") as f:
                diff_content = f.read()
        except OSError as exc:
            print(json.dumps({"ok": False, "error": f"Cannot read diff file: {exc}"}, indent=2))
            return 1
    elif args.diff:
        diff_content = args.diff
    else:
        # Read from stdin.
        diff_content = sys.stdin.read()

    result = bridge.aura_stage_patch(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        owner=args.owner,
        diff=diff_content,
        affected_files=args.affected_files.split(",") if args.affected_files else [],
        affected_symbols=args.affected_symbols.split(",") if args.affected_symbols else None,
        tests=args.tests.split(",") if args.tests else None,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_verify(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_verify_arena(
        plan_phase_hash=phase_hash,
        test_scope=args.scope,
        runner=args.runner,
        max_log_lines=args.max_log_lines,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_repair_packet(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_repair_packet(
        plan_phase_hash=phase_hash,
        task_id=args.task_id,
        failure_id=args.failure_id,
        max_tokens_est=args.max_tokens,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_status(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_hotswap_status(
        plan_phase_hash=phase_hash,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_export_icm(args: argparse.Namespace) -> int:
    phase_hash = _require_plan_phase_hash()
    bridge = _get_bridge()
    result = bridge.aura_export_icm(
        plan_phase_hash=phase_hash,
        workspace_root=args.workspace_root,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_find_affordances(args: argparse.Namespace) -> int:
    bridge = _get_bridge()
    result = bridge.aura_find_affordances(
        objective=args.objective,
        target_files=[item.strip() for item in args.target_files.split(",") if item.strip()] if args.target_files else None,
        target_symbols=[item.strip() for item in args.target_symbols.split(",") if item.strip()] if args.target_symbols else None,
        include_affordances=not args.no_affordances,
        top_k=args.top_k,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Hermes Arena Mode command handlers
# ---------------------------------------------------------------------------


def _require_hermes_mode() -> None:
    """Raise SystemExit if Hermes Arena Mode is not available."""
    if not _HERMES_MODE_AVAILABLE:
        print(json.dumps({
            "ok": False,
            "error": "Hermes Arena Mode is not available. Ensure aura_hermes_arena_mode.py is importable.",
        }, indent=2))
        raise SystemExit(1)


def cmd_hermes_contract(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    result = generate_hermes_contract(
        objective=args.objective,
        mode=args.mode,
        repo_root=".",
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(result.get("contract", ""))
        else:
            _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_preflight(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    target_files = None
    if args.target_files:
        target_files = [f.strip() for f in args.target_files.split(",") if f.strip()]
    target_symbols = None
    if args.target_symbols:
        target_symbols = [s.strip() for s in args.target_symbols.split(",") if s.strip()]
    result = run_preflight(
        objective=args.objective,
        repo_root=".",
        target_files=target_files,
        target_symbols=target_symbols,
    )
    _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_token_report(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = generate_token_savings_report(
        objective=args.objective,
        files=files,
        repo_root=".",
        include_preflight=args.include_preflight,
        output_format=args.format,
    )
    if args.format == "markdown" and result.get("ok"):
        print(result.get("markdown", ""))
    else:
        _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_pr_runbook(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    files = None
    if args.files:
        files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = generate_pr_runbook(
        objective=args.objective,
        branch=args.branch,
        repo_root=".",
        files=files,
    )
    if args.json:
        _print_json(result)
    else:
        if result.get("ok"):
            print(result.get("runbook", ""))
        else:
            _print_json(result)
    return 0 if result.get("ok") else 1


def cmd_write_rules(args: argparse.Namespace) -> int:
    _require_hermes_mode()
    result = write_hermes_aura_rules(repo_root=".")
    _print_json(result)
    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aura-agent-arena",
        description="Aura Agent Arena Bridge — CLI for external coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # digest
    p_digest = subparsers.add_parser("digest", help="Return repo orientation packet")
    p_digest.add_argument("--no-hubs", action="store_true", help="Exclude hub list")
    p_digest.add_argument("--max-lines", type=int, default=120, help="Max lines in output")
    p_digest.set_defaults(func=cmd_digest)

    # prepare
    p_prepare = subparsers.add_parser("prepare", help="Run Aura's prepare pipeline")
    p_prepare.add_argument("--objective", required=True, help="Task objective")
    p_prepare.add_argument("--target-file", default=None, help="Target file path")
    p_prepare.add_argument("--target-symbol", default=None, help="Target symbol name")
    p_prepare.add_argument("--acceptance-criteria", default=None, help="Comma-separated criteria")
    p_prepare.add_argument("--risk-map", default=None, help="Comma-separated risks")
    p_prepare.add_argument("--constraints", default=None, help="Comma-separated constraints")
    p_prepare.set_defaults(func=cmd_prepare)

    # search
    p_search = subparsers.add_parser("search", help="Search CODEMAP")
    p_search.add_argument("--query", required=True, help="Search query")
    p_search.add_argument("--kind", default="symbol", choices=["symbol", "file", "text", "command"])
    p_search.add_argument("--max-results", type=int, default=10)
    p_search.add_argument("--no-neighbors", action="store_true")
    p_search.set_defaults(func=cmd_search)

    # context
    p_context = subparsers.add_parser("context", help="Get micro-context for a task")
    p_context.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_context.add_argument("--format", default="both", choices=["capsule", "st3gg", "both"])
    p_context.add_argument("--depth", type=int, default=1)
    p_context.add_argument("--max-tokens", type=int, default=2000)
    p_context.set_defaults(func=cmd_context)

    # read-slice
    p_read = subparsers.add_parser("read-slice", help="Read a bounded file slice")
    p_read.add_argument("--file", required=True, help="File path (repo-relative)")
    p_read.add_argument("--symbol", default=None, help="Symbol to read")
    p_read.add_argument("--line-start", type=int, default=None)
    p_read.add_argument("--line-end", type=int, default=None)
    p_read.add_argument("--max-lines", type=int, default=120)
    p_read.set_defaults(func=cmd_read_slice)

    # fireworks-patch
    p_fw = subparsers.add_parser("fireworks-patch", help="Call Fireworks for a candidate diff")
    p_fw.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_fw.add_argument("--instruction", required=True, help="Instruction for the model")
    p_fw.add_argument("--model-tier", default="fast", choices=["fast", "code", "judge"])
    p_fw.add_argument("--max-output-tokens", type=int, default=2048)
    p_fw.set_defaults(func=cmd_fireworks_patch)

    # stage-patch
    p_stage = subparsers.add_parser("stage-patch", help="Stage a patch through the arena")
    p_stage.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_stage.add_argument("--diff-file", default=None, help="File containing the unified diff")
    p_stage.add_argument("--diff", default=None, help="Inline diff content")
    p_stage.add_argument("--affected-files", default=None, help="Comma-separated affected files")
    p_stage.add_argument("--affected-symbols", default=None, help="Comma-separated affected symbols")
    p_stage.add_argument("--tests", default=None, help="Comma-separated test files")
    p_stage.add_argument("--owner", default="external_agent")
    p_stage.set_defaults(func=cmd_stage_patch)

    # verify
    p_verify = subparsers.add_parser("verify", help="Run verifier/tests")
    p_verify.add_argument("--scope", default="focused", choices=["focused", "all", "declared"])
    p_verify.add_argument("--runner", default="pytest")
    p_verify.add_argument("--max-log-lines", type=int, default=80)
    p_verify.set_defaults(func=cmd_verify)

    # repair-packet
    p_repair = subparsers.add_parser("repair-packet", help="Get repair context for a failed patch")
    p_repair.add_argument("--task-id", required=True, help="Act capsule task ID")
    p_repair.add_argument("--failure-id", default=None, help="Specific failure stage ID")
    p_repair.add_argument("--max-tokens", type=int, default=1500)
    p_repair.set_defaults(func=cmd_repair_packet)

    # status
    p_status = subparsers.add_parser("status", help="Check hotswap/promotion status")
    p_status.set_defaults(func=cmd_status)

    # export-icm
    p_export = subparsers.add_parser("export-icm", help="Export arena to ICM workspace")
    p_export.add_argument("--workspace-root", default=None)
    p_export.set_defaults(func=cmd_export_icm)

    # find-affordances
    p_aff = subparsers.add_parser("find-affordances", help="Find internal Aura tools for an objective")
    p_aff.add_argument("--objective", required=True, help="Task objective or question")
    p_aff.add_argument("--target-files", default=None, help="Comma-separated target file paths")
    p_aff.add_argument("--target-symbols", default=None, help="Comma-separated target symbol names")
    p_aff.add_argument("--no-affordances", action="store_true", help="Skip affordance cards")
    p_aff.add_argument("--top-k", type=int, default=7, help="Max affordances to return (3-7)")
    p_aff.set_defaults(func=cmd_find_affordances)

    # ---- Hermes Arena Mode subcommands (additive) ----

    # hermes-contract
    p_contract = subparsers.add_parser(
        "hermes-contract",
        help="Generate a ready-to-paste Hermes operating contract / system prompt",
    )
    p_contract.add_argument("--objective", required=True, help="Coding objective")
    p_contract.add_argument("--mode", default="pr", choices=["pr", "direct"], help="Operating mode (default: pr)")
    p_contract.add_argument("--json", action="store_true", help="Output full JSON instead of markdown contract text")
    p_contract.set_defaults(func=cmd_hermes_contract)

    # preflight
    p_preflight = subparsers.add_parser(
        "preflight",
        help="Generate a compact JSON preflight packet for a coding objective",
    )
    p_preflight.add_argument("--objective", required=True, help="Coding objective")
    p_preflight.add_argument("--target-files", default=None, help="Comma-separated target file paths")
    p_preflight.add_argument("--target-symbols", default=None, help="Comma-separated target symbol names")
    p_preflight.set_defaults(func=cmd_preflight)

    # token-report
    p_token = subparsers.add_parser(
        "token-report",
        help="Generate a token savings report comparing raw vs Aura context usage",
    )
    p_token.add_argument("--objective", required=True, help="Coding objective")
    p_token.add_argument("--files", required=True, help="Comma-separated repo-relative file paths")
    p_token.add_argument("--include-preflight", action="store_true", help="Include full preflight packet in report")
    p_token.add_argument("--format", default="json", choices=["json", "markdown"], help="Output format (default: json)")
    p_token.set_defaults(func=cmd_token_report)

    # pr-runbook
    p_runbook = subparsers.add_parser(
        "pr-runbook",
        help="Generate a PR-safe Git/Hermes workflow runbook for a task",
    )
    p_runbook.add_argument("--objective", required=True, help="Coding objective")
    p_runbook.add_argument("--branch", required=True, help="Feature branch name (e.g. feature/my-task)")
    p_runbook.add_argument("--files", default=None, help="Comma-separated files that will be modified")
    p_runbook.add_argument("--json", action="store_true", help="Output full JSON instead of markdown runbook text")
    p_runbook.set_defaults(func=cmd_pr_runbook)

    # write-rules
    p_rules = subparsers.add_parser(
        "write-rules",
        help="Write .aura/HERMES_AURA_RULES.md guard file",
    )
    p_rules.set_defaults(func=cmd_write_rules)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())