#!/usr/bin/env python3
"""Reproducible Aura architecture and runtime-refactor harness.

The original PR #182 implementation is preserved byte-for-byte in
``scripts.aura_architecture_harness_core``. This stable entrypoint keeps every
existing command and private compatibility surface while adding proposal-only
GitHub workflow discovery, atomic Git-tree publication guidance, and the
runtime profile command. Runtime profiles reproduce and verify a local
application in an isolated environment, but never patch, commit, push, open a
pull request, or merge.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts import aura_architecture_harness_core as _core
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    import aura_architecture_harness_core as _core  # type: ignore[no-redef]

from aura_architecture_harness_git_tree_routing import (
    AUTHORITY_CONTRACT as GITHUB_ROUTING_AUTHORITY_CONTRACT,
    VERSION as GITHUB_ROUTING_VERSION,
    WORKFLOW_DISCOVERY as GITHUB_WORKFLOW_DISCOVERY,
    pr184_atomic_publication_case_study,
)

# Preserve every existing public and private symbol used by PR #182 callers/tests.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_ORIGINAL_DOCTOR = _core.doctor
_ORIGINAL_CREATE_AI_HANDOFF = _core.create_ai_handoff
_ORIGINAL_RUN_ARCHITECTURE = _core.run_architecture

GITHUB_PUBLICATION_ROUTE_VERSION = GITHUB_ROUTING_VERSION


def _github_publication_route_policy() -> dict[str, Any]:
    """Return untrusted routing guidance plus a non-replayable historical case study."""

    case = pr184_atomic_publication_case_study()
    return {
        "version": GITHUB_ROUTING_VERSION,
        "status": "PROPOSAL_ONLY_EXTERNAL_CONNECTOR_REQUIRED",
        "trust_model": "UNTRUSTED_PROPOSAL_EXECUTOR_MUST_REFETCH",
        "workflow_discovery": copy.deepcopy(GITHUB_WORKFLOW_DISCOVERY),
        "preferred_fallback": "atomic_git_object_route",
        "connector_sequence": copy.deepcopy(case["connector_sequence"]),
        "preconditions": copy.deepcopy(case["preconditions"]),
        "rollback": copy.deepcopy(case["rollback"]),
        "case_study": copy.deepcopy(case["case_study"]),
        "authority": copy.deepcopy(GITHUB_ROUTING_AUTHORITY_CONTRACT),
    }


def doctor(root: Path, python: Path | None) -> dict[str, Any]:
    """Run the original doctor and expose GitHub publication routing guidance."""

    output = _ORIGINAL_DOCTOR(root, python)
    output["github_publication_route"] = _github_publication_route_policy()
    return output


def create_ai_handoff(
    root: Path,
    *,
    output_dir: str | Path | None,
    inline_max_bytes: int = DEFAULT_INLINE_MAX_BYTES,
    allow_dirty: bool = False,
    create_archive: bool = True,
) -> dict[str, Any]:
    """Create the original handoff plus deterministic GitHub routing metadata."""

    # Preserve the PR #182 compatibility seam: callers and tests may
    # monkeypatch the wrapper helper while the original function resolves it
    # from the core module's globals.
    _core._read_git_blob = _read_git_blob
    result = _ORIGINAL_CREATE_AI_HANDOFF(
        root,
        output_dir=output_dir,
        inline_max_bytes=inline_max_bytes,
        allow_dirty=allow_dirty,
        create_archive=create_archive,
    )
    route = _github_publication_route_policy()
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["github_publication_route"] = route
    _core._write(manifest_path, manifest)
    result["github_publication_route"] = route
    return result


def run_architecture(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Run the original architecture analysis and bind routing into its summary."""

    output = _ORIGINAL_RUN_ARCHITECTURE(root, **kwargs)
    output.pop("run_digest", None)
    output["github_publication_route"] = _github_publication_route_policy()
    output["run_digest"] = _core._digest(output)
    output_dir = Path(kwargs["output_dir"]).expanduser().resolve()
    _core._write(output_dir / "harness_summary.json", output)
    return output


# The original main() resolves these functions from its own module globals.
_core.doctor = doctor
_core.create_ai_handoff = create_ai_handoff
_core.run_architecture = run_architecture


def main(argv: Iterable[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else list(sys.argv[1:])
    if "runtime" in arguments:
        runtime_index = arguments.index("runtime")
        runtime_arguments = [
            *arguments[:runtime_index],
            *arguments[runtime_index + 1 :],
        ]
        try:
            from scripts.aura_runtime_refactor_harness import (
                main as runtime_main,
            )
        except ModuleNotFoundError:  # Direct execution from scripts directory.
            from aura_runtime_refactor_harness import (  # type: ignore[no-redef]
                main as runtime_main,
            )
        return runtime_main(runtime_arguments)
    return _core.main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
