"""AWJ-032 selective evidence reproof after a semantic-source delta.

This module does not execute AirLLM, a model, or a workflow. It computes the
smallest evidence cone that must be re-proved when one dependency generation
moves. Stable historical evidence stays historical support; it never becomes a
current owner-host observation merely because its code blob is unchanged.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Iterable

SOURCE_SECURITY = "SOURCE_SECURITY"
RUNTIME_CAPABILITY = "RUNTIME_CAPABILITY"
TINY_FIXTURE_RUNTIME = "TINY_FIXTURE_RUNTIME"
OWNER_HOST_CURRENTNESS = "OWNER_HOST_CURRENTNESS"


@dataclass(frozen=True)
class EvidenceLeaf:
    leaf_id: str
    domain: str
    dependencies: tuple[str, ...]
    historical_proof_root: str


@dataclass(frozen=True)
class GenerationDelta:
    dependency: str
    old_generation: str
    new_generation: str


@dataclass(frozen=True)
class ReproofDecision:
    leaf_id: str
    disposition: str
    invalidators: tuple[str, ...]


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode("ascii")).hexdigest()


def compile_reproof(
    leaves: Iterable[EvidenceLeaf],
    deltas: Iterable[GenerationDelta],
    *,
    claiming_owner_host_current: bool = False,
) -> dict:
    """Return a deterministic minimum reproof plan.

    A changed dependency reopens only leaves that explicitly depend on it.
    Untouched hosted/runtime evidence is historical compatible support. When a
    caller asks for current owner-host truth, runtime/fixture/host leaves require
    owner-host reproduction even if their code generations are unchanged.
    """
    changed = {d.dependency for d in deltas if d.old_generation != d.new_generation}
    decisions: list[ReproofDecision] = []
    for leaf in leaves:
        touched = tuple(sorted(changed.intersection(leaf.dependencies)))
        if touched:
            disposition = "REPROOF_REQUIRED"
        elif claiming_owner_host_current and leaf.domain in {
            RUNTIME_CAPABILITY,
            TINY_FIXTURE_RUNTIME,
            OWNER_HOST_CURRENTNESS,
        }:
            disposition = "OWNER_HOST_REPROOF_REQUIRED"
        else:
            disposition = "HISTORICAL_COMPATIBLE_SUPPORT"
        decisions.append(ReproofDecision(leaf.leaf_id, disposition, touched))

    out = {
        "changed_dependencies": sorted(changed),
        "claiming_owner_host_current": claiming_owner_host_current,
        "decisions": [asdict(item) for item in decisions],
        "authority_ceiling": "D0_NONPROMOTING_NO_EXECUTION_AUTHORITY",
    }
    out["plan_root"] = _digest(out)
    return out


def pr311_current_fixture() -> tuple[list[EvidenceLeaf], list[GenerationDelta]]:
    """Current bounded fixture: hosted Tiny proof generation -> PR311 d422ca47.

    The current source-admission blob changed. Remediation, runtime guard, and
    tiny-fixture probe blobs are unchanged across the compared generations.
    """
    leaves = [
        EvidenceLeaf(
            "G1_SOURCE_ADMISSION",
            SOURCE_SECURITY,
            ("airllm_source_admission.py",),
            "PR311_HOSTED_TINY_SEMANTIC_HEAD_6da6ee77",
        ),
        EvidenceLeaf(
            "HARD_FALSE_REMEDIATION",
            SOURCE_SECURITY,
            ("airllm_hard_false_remediation.py",),
            "HOSTED_REMEDIATION_SUPPORT",
        ),
        EvidenceLeaf(
            "RUNTIME_HARD_FALSE_GUARD",
            RUNTIME_CAPABILITY,
            ("airllm_runtime_hard_false.py",),
            "HOSTED_RUNTIME_GUARD_SUPPORT",
        ),
        EvidenceLeaf(
            "TINY_SPLIT_GENERATE_REOPEN",
            TINY_FIXTURE_RUNTIME,
            (
                "airllm_tiny_fixture_probe.py",
                "tiny_fixture_revision",
                "runtime_dependency_tuple",
            ),
            "HOSTED_TINY_RUNTIME_SUPPORT",
        ),
        EvidenceLeaf(
            "OWNER_HOST_G3",
            OWNER_HOST_CURRENTNESS,
            ("host_profile_generation", "owner_host_resource_generation"),
            "OWNER_HOST_EFFECT_UNOBSERVED",
        ),
    ]
    deltas = [
        GenerationDelta(
            "airllm_source_admission.py",
            "396e03924b71d5ae728b49a22239af9f19138d09",
            "225bbef955e62dbfc6c81711371bc95f7a8d9941",
        ),
        GenerationDelta(
            "airllm_hard_false_remediation.py",
            "8b2c83307c83d9fac1ac2121bebc3bc45d480ef4",
            "8b2c83307c83d9fac1ac2121bebc3bc45d480ef4",
        ),
        GenerationDelta(
            "airllm_runtime_hard_false.py",
            "4e55c6443fcac4185fcb56a0f6a4b579bb21366a",
            "4e55c6443fcac4185fcb56a0f6a4b579bb21366a",
        ),
        GenerationDelta(
            "airllm_tiny_fixture_probe.py",
            "57643f19ddbf8c35e838c2c9b21b520b052dcade",
            "57643f19ddbf8c35e838c2c9b21b520b052dcade",
        ),
    ]
    return leaves, deltas


if __name__ == "__main__":
    fixture_leaves, fixture_deltas = pr311_current_fixture()
    print(json.dumps(compile_reproof(fixture_leaves, fixture_deltas), indent=2, sort_keys=True))
