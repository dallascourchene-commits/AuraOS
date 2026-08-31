#!/usr/bin/env python3
"""Q15 verification-generation currentness adapter.

The Q15 semantic membrane remains owned by
``aura_execution_qualified_portable_materialization_evidence``. This adapter
binds the exact provider identifiers observed for the terminal Q14 producer
run without changing any source/page/semantic/freshness/claim law.

Why this exists: the first Q15 hosted generations exposed two proof-transport
scars in sequence: timezone rendering was compared instead of the exact
instant, then Q14 provider evidence was addressed with a stale job id and a
noncanonical workflow label. Provider identity is currentness evidence, not a
reason to fork the semantic owner.
"""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

# Support both `python -m tools.quantization...` and direct file execution from
# repository-root workflows. This modifies import transport only.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.quantization import aura_execution_qualified_portable_materialization_evidence as q15

Q14_RUN = 33399560819
Q14_JOB = 99512247000
Q14_WORKFLOW = "GLM53 Official Source E8 Materialization Canary"
Q14_JOB_NAME = "q14-official-source-e8-canary"


def bind_current_provider_descriptor() -> None:
    """Rebind only Q14's exact hosted execution descriptor."""
    if q15.Q14_RUN != Q14_RUN:
        raise RuntimeError("Q14_RUN_OWNER_DRIFT")
    if q15.Q14_HEAD != "ee70934e0c45572588829e742e512a897b23863f":
        raise RuntimeError("Q14_HEAD_OWNER_DRIFT")
    if q15.Q14_ARTIFACT_ID != 9760937399:
        raise RuntimeError("Q14_ARTIFACT_OWNER_DRIFT")

    q15.Q14_JOB = Q14_JOB
    q15.Q14_WORKFLOW = Q14_WORKFLOW


def descriptor() -> dict[str, Any]:
    bind_current_provider_descriptor()
    return {
        "q14_run": q15.Q14_RUN,
        "q14_job": q15.Q14_JOB,
        "q14_job_name": Q14_JOB_NAME,
        "q14_workflow": q15.Q14_WORKFLOW,
        "q14_head": q15.Q14_HEAD,
        "q14_artifact_id": q15.Q14_ARTIFACT_ID,
        "semantic_owner_unchanged": True,
        "provider_descriptor_is_semantic_authority": False,
        "provider_descriptor_is_effect_authority": False,
    }


def admit(*args: Any, **kwargs: Any):
    bind_current_provider_descriptor()
    return q15.admit(*args, **kwargs)


def main() -> None:
    bind_current_provider_descriptor()
    q15.main()


if __name__ == "__main__":
    main()
