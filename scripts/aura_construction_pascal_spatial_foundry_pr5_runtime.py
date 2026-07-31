#!/usr/bin/env python3
"""Run the exact PR5 Construction + Pascal Spatial Foundry bilateral proof.

This is a bounded operator adapter. It compiles one external canonical bilateral
confirmation against the exact clean PR5 V2 profile, delegates execution to the
existing Runtime Profile V2 adapter, removes the temporary confirmation root,
and grants no patch, publication, merge, Construction, deployment, or learning
authority.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aura_construction_pascal_spatial_foundry_p4_server import _compile_confirmation_bundle
from scripts.aura_runtime_profile_v2_adapter import run_runtime_profile_v2

PROFILE = ".aura/runtime_profiles/construction_pascal_spatial_foundry_bilateral.v2.json"
POSITIVE_REQUIREMENTS = (
    "The complete fifteen-chapter Construction and Pascal Spatial Foundry tour produces every required current-run screenshot and exact evidence artifact in real Chromium.",
    "The verified tour preserves the exact source tree, proves terminal cleanup of every leased process and presentation resource, proves a fresh relaunch, and records identical canonical Construction state digests before and after.",
)
NEGATIVE_REQUIREMENTS = (
    "Do not grant production mutation, automatic merge, physical-work, professional, payment, access, deployment, or learning-promotion authority.",
    "Do not contact any origin outside the declared loopback server, execute from a dirty checkout, or reuse a prior output directory.",
    "Do not create a second Construction truth, runtime, archive, verifier, rollback, policy, routing, persistence, authority, or learning owner.",
)


def run(
    repo_root: str | Path,
    *,
    output_dir: str | Path,
    venv: str | Path | None = None,
    install_requirements: bool = False,
    baseline_receipt: str | Path | None = None,
) -> dict[str, object]:
    root = Path(repo_root).expanduser().resolve()
    _identity, confirmation_path, _unused_output = _compile_confirmation_bundle(
        root,
        runtime_profile_path=PROFILE,
        positive_requirements=POSITIVE_REQUIREMENTS,
        negative_requirements=NEGATIVE_REQUIREMENTS,
        human_reviewer="Dallas Courchene - PR5 Construction + Pascal full-MVP runtime fixture",
    )
    temporary_root = confirmation_path.parent
    try:
        return run_runtime_profile_v2(
            root,
            profile_path=PROFILE,
            confirmation_packet=confirmation_path,
            output_dir=output_dir,
            venv_path=venv,
            install_requirements=install_requirements,
            allow_dirty=False,
            baseline_receipt=baseline_receipt,
        )
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--venv")
    parser.add_argument("--install-requirements", action="store_true")
    parser.add_argument("--baseline-receipt")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = run(
            args.repo_root,
            output_dir=args.output_dir,
            venv=args.venv,
            install_requirements=args.install_requirements,
            baseline_receipt=args.baseline_receipt,
        )
    except Exception as exc:  # CLI boundary: retain a structured fail-closed receipt.
        result = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "human_review_required": True,
            "production_mutation": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
