"""CLI for Phase C3 isolated capsule trials and proposal-only Agent IR induction."""
from __future__ import annotations

import argparse
import json

from aura_capsule_trial_runner import TRIAL_EXECUTION_LEASE
from aura_phase_c3_trial_crucible import CapsuleTrialCrucibleService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aura Phase C3 — isolated capsule trials and review-only procedure induction"
    )
    parser.add_argument("--repo-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show C3 trial-ledger and authority status")

    run_once = sub.add_parser("run-once", help="Run one explicitly enabled isolated C3 trial cycle")
    run_once.add_argument(
        "--policy-ref",
        default=".aura/capsule_trial_policies/coding_localize.v1.json",
    )
    run_once.add_argument(
        "--cases-ref",
        default=".aura/capsule_trial_cases/coding_localize.v1.json",
    )
    run_once.add_argument("--enable-trials", action="store_true")
    run_once.add_argument(
        "--lease-capability",
        action="append",
        default=[],
        help=f"Repeatable explicit lease capability; requires {TRIAL_EXECUTION_LEASE}",
    )

    procedures = sub.add_parser("procedures", help="List stored PROCEDURE_INDUCTION_PROPOSED packets")
    procedures.add_argument("--limit", type=int, default=50)
    procedure = sub.add_parser("procedure", help="Read one stored procedure proposal")
    procedure.add_argument("procedure_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = CapsuleTrialCrucibleService(args.repo_root)
    try:
        if args.command == "status":
            result = service.status()
        elif args.command == "run-once":
            result = service.run_once(
                policy_ref=args.policy_ref,
                cases_ref=args.cases_ref,
                trials_enabled=bool(args.enable_trials),
                lease_capabilities=args.lease_capability,
            )
        elif args.command == "procedures":
            rows = service.store.list_procedures(limit=args.limit)
            result = {
                "ok": True,
                "procedures": rows,
                "count": len(rows),
                "automatic_code_installation": False,
            }
        else:
            row = service.store.get_procedure(args.procedure_id)
            result = {
                "ok": bool(row),
                "procedure": row,
                "reason": "" if row else "procedure_not_found",
                "automatic_code_installation": False,
            }
    finally:
        service.close()
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
