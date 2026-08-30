"""Provider-neutral Arena Triadic orchestration for AuraOS.

This module does not own provider selection, credentials, Drive transport, effect
admission, or authority. It compiles consequence-ordered leaf calls and persists
every leaf before dependent synthesis. A host-owned adapter must execute each
LeafCall through the already-admitted provider/effect membrane (for DeepSeek,
that is the Project-006 / PR306 canonical egress seam).

Two modes are explicit:

INDEPENDENT_RECIPROCAL
    A+, B-, and C0 receive the same common WorkCapsule independently (3 calls),
    each then performs a reciprocal BASE_TRIAD synthesis over all three leaves
    from its own role/view (3 calls), followed by one FINAL_DIMENSIONAL_REBASE
    (1 call). Total: 7 calls per independent cell. This preserves first-pass
    independence and matches the existing C81 execution pattern.

STAGGERED_EFFICIENT
    A+ Construct -> B- Challenge(A) -> C0 Verify(A,B) -> A+ Rebase(B,C).
    Total: 4 calls per cell. This is cheaper but does not preserve independent
    first-pass perspectives, so it must not be substituted when independent
    verification is a requirement.

HyperScale expands across independent cells only. Worker count never creates
evidence independence by itself.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Literal, Protocol

Mode = Literal["INDEPENDENT_RECIPROCAL", "STAGGERED_EFFICIENT"]


class ArenaTriadError(RuntimeError):
    """Base typed orchestration failure."""


class ArenaTriadStale(ArenaTriadError):
    """Command is bound to a stale Arena head."""


class ArenaTriadBudgetExceeded(ArenaTriadError):
    """Planned calls exceed the explicit command budget."""


@dataclass(frozen=True)
class WorkCell:
    cell_id: str
    objective: str
    source_refs: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    reopen_handles: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArenaTriadCommand:
    command_id: str
    idempotency_key: str
    arena_head: str
    objective: str
    cells: tuple[WorkCell, ...]
    mode: Mode = "INDEPENDENT_RECIPROCAL"
    effect: str = "D0"
    gate_target: int = 10
    max_concurrency: int = 9
    max_leaf_calls: int = 256
    mission: str = "Streamline Aura architecture to minimal friction."
    purpose: str = (
        "Move human intent through the smallest lawful consequence-complete path."
    )


@dataclass(frozen=True)
class LeafCall:
    """One model/provider effect request, prior to host-owned effect admission."""

    parent_command_id: str
    parent_idempotency_key: str
    arena_head: str
    cell_id: str
    phase: str
    role: str
    sequence: int
    child_idempotency_key: str
    common_capsule: dict[str, Any]
    role_instruction: str
    prior_artifact_refs: tuple[str, ...]
    prior_artifacts: dict[str, Any]


@dataclass(frozen=True)
class LeafResult:
    """Structured provider result returned by a host-owned admitted executor."""

    status: str
    payload: dict[str, Any]
    provider: str | None = None
    model: str | None = None
    provider_attempt_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    cost_state: str = "UNKNOWN"
    cost_observation: dict[str, Any] = field(default_factory=dict)


class LeafExecutor(Protocol):
    def __call__(self, call: LeafCall) -> LeafResult: ...


@dataclass(frozen=True)
class LeafReceipt:
    command_id: str
    child_idempotency_key: str
    arena_head: str
    cell_id: str
    phase: str
    role: str
    sequence: int
    artifact_path: str
    artifact_sha256: str
    provider: str | None
    model: str | None
    provider_attempt_id: str | None
    usage: dict[str, Any]
    cost_state: str


_REQUIRED_RESULT_KEYS = {
    "claims",
    "evidence",
    "dissent",
    "residuals",
    "reopen",
    "next_action",
    "claim_ceiling",
}


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_component(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)


def _validate_payload(payload: dict[str, Any]) -> None:
    missing = sorted(_REQUIRED_RESULT_KEYS - set(payload))
    if missing:
        raise ArenaTriadError("leaf_result_missing:" + ",".join(missing))
    for name in ("claims", "evidence", "dissent", "residuals", "reopen"):
        if not isinstance(payload.get(name), list):
            raise ArenaTriadError(f"leaf_result_not_list:{name}")


def _common_capsule(command: ArenaTriadCommand, cell: WorkCell) -> dict[str, Any]:
    # Keep this structure identical across the role leaves of a cell. A provider
    # adapter should serialize it before the role-specific suffix, allowing
    # provider-side prefix caching where available.
    return {
        "schema": "AuraArenaCommonCapsuleV1",
        "parent_command_id": command.command_id,
        "arena_head": command.arena_head,
        "effect": command.effect,
        "gate_target": command.gate_target,
        "mission": command.mission,
        "purpose": command.purpose,
        "root_objective": command.objective,
        "cell": asdict(cell),
        "laws": [
            "ARENA_FIRST",
            "CURRENTNESS_BEFORE_REASONING",
            "SOURCE_OWNER_NOT_MIRROR",
            "ADDRESS_NOT_AUTHORITY",
            "QUEUE_NOT_EXECUTION",
            "REUSE_BEFORE_RECOMPUTE",
            "PRESERVE_DISSENT",
            "NO_SELF_PROMOTION",
            "STOP_AT_GATE10",
        ],
        "output_contract": {
            "claims": ["string"],
            "evidence": ["string"],
            "dissent": ["string"],
            "residuals": ["string"],
            "reopen": ["string"],
            "next_action": "string",
            "claim_ceiling": "string",
        },
    }


_ROLE_INSTRUCTIONS = {
    "A_CONSTRUCT": (
        "Construct the smallest lawful implementation/procedure. Reuse existing "
        "AuraOS/Arena primitives and exact receipts. Name concrete modules, tests, "
        "commands, and acceptance evidence. Do not widen architecture unnecessarily."
    ),
    "B_CHALLENGE": (
        "Attack the construct or bounded objective. Search for stale currentness, "
        "source/mirror confusion, duplicate effects, replay/fence failure, authority "
        "collapse, hidden spend widening, truncation/data loss, and simpler baselines."
    ),
    "C_VERIFY": (
        "Verify exact claims against sources/currentness/effect ceilings. Classify "
        "what is proven, partial, unobserved, or blocked. Preserve negative evidence."
    ),
    "BASE_TRIAD_A": (
        "From A+ perspective, synthesize the three independent leaves. Preserve B- "
        "dissent and C0 evidence ceilings; do not average disagreements away."
    ),
    "BASE_TRIAD_B": (
        "From B- perspective, synthesize the three independent leaves. Retain every "
        "live falsifier and identify where A+/C0 overclaim or under-specify."
    ),
    "BASE_TRIAD_C": (
        "From C0 perspective, synthesize the three independent leaves into an "
        "evidence-status matrix and exact reopen conditions."
    ),
    "FINAL_DIMENSIONAL_REBASE": (
        "Perform the final dimensional rebase over all reciprocal syntheses. Return "
        "the smallest successor state, preserved dissent, what must not be re-derived, "
        "and the next consequence-complete work packet. Stop at Gate 10."
    ),
    "A_REBASE": (
        "Rebase A+ using B- and C0. Preserve unresolved dissent. Return the smallest "
        "successor state and exact reopen handles rather than a narrative expansion."
    ),
}


def _leaf_call(
    command: ArenaTriadCommand,
    cell: WorkCell,
    *,
    phase: str,
    role: str,
    sequence: int,
    prior: dict[str, Any],
    prior_refs: tuple[str, ...],
) -> LeafCall:
    child = (
        f"{command.idempotency_key}/{_safe_component(cell.cell_id)}/"
        f"{sequence:02d}-{role}"
    )
    return LeafCall(
        parent_command_id=command.command_id,
        parent_idempotency_key=command.idempotency_key,
        arena_head=command.arena_head,
        cell_id=cell.cell_id,
        phase=phase,
        role=role,
        sequence=sequence,
        child_idempotency_key=child,
        common_capsule=_common_capsule(command, cell),
        role_instruction=_ROLE_INSTRUCTIONS[role],
        prior_artifact_refs=prior_refs,
        prior_artifacts=prior,
    )


def _leaf_file(run_root: Path, cell_id: str, sequence: int, role: str) -> Path:
    folder = run_root / "leaves" / _safe_component(cell_id)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{sequence:02d}_{role}.json"


def _persist(
    path: Path,
    command: ArenaTriadCommand,
    call: LeafCall,
    result: LeafResult,
) -> LeafReceipt:
    if result.status != "OK":
        raise ArenaTriadError(
            f"leaf_failed:{call.cell_id}:{call.role}:{result.status}"
        )
    _validate_payload(result.payload)
    envelope = {
        "schema": "AuraArenaLeafReceiptV1",
        "parent_command_id": command.command_id,
        "parent_idempotency_key": command.idempotency_key,
        "child_idempotency_key": call.child_idempotency_key,
        "arena_head": command.arena_head,
        "cell_id": call.cell_id,
        "phase": call.phase,
        "role": call.role,
        "sequence": call.sequence,
        "provider": result.provider,
        "model": result.model,
        "provider_attempt_id": result.provider_attempt_id,
        "usage": result.usage,
        "cost_state": result.cost_state,
        "cost_observation": result.cost_observation,
        "payload": result.payload,
        "recorded_at_unix": time.time(),
    }
    raw = (_canonical(envelope) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return LeafReceipt(
        command_id=command.command_id,
        child_idempotency_key=call.child_idempotency_key,
        arena_head=command.arena_head,
        cell_id=call.cell_id,
        phase=call.phase,
        role=call.role,
        sequence=call.sequence,
        artifact_path=str(path),
        artifact_sha256=_sha(raw),
        provider=result.provider,
        model=result.model,
        provider_attempt_id=result.provider_attempt_id,
        usage=result.usage,
        cost_state=result.cost_state,
    )


def _run_leaf(
    command: ArenaTriadCommand,
    cell: WorkCell,
    run_root: Path,
    executor: LeafExecutor,
    *,
    phase: str,
    role: str,
    sequence: int,
    prior: dict[str, Any] | None = None,
    prior_refs: tuple[str, ...] = (),
) -> tuple[LeafReceipt, dict[str, Any]]:
    call = _leaf_call(
        command,
        cell,
        phase=phase,
        role=role,
        sequence=sequence,
        prior=prior or {},
        prior_refs=prior_refs,
    )
    result = executor(call)
    path = _leaf_file(run_root, cell.cell_id, sequence, role)
    receipt = _persist(path, command, call, result)
    return receipt, result.payload


def _independent_reciprocal(
    command: ArenaTriadCommand,
    cell: WorkCell,
    run_root: Path,
    executor: LeafExecutor,
) -> dict[str, Any]:
    receipts: list[LeafReceipt] = []
    leafs: dict[str, dict[str, Any]] = {}
    refs: dict[str, str] = {}

    # Independent first pass: none receives another worker's output.
    for seq, role in enumerate(("A_CONSTRUCT", "B_CHALLENGE", "C_VERIFY"), start=1):
        receipt, payload = _run_leaf(
            command, cell, run_root, executor,
            phase="LEAF", role=role, sequence=seq
        )
        receipts.append(receipt)
        leafs[role] = payload
        refs[role] = receipt.artifact_path

    peer_bundle = {
        "A_CONSTRUCT": leafs["A_CONSTRUCT"],
        "B_CHALLENGE": leafs["B_CHALLENGE"],
        "C_VERIFY": leafs["C_VERIFY"],
    }
    peer_refs = tuple(refs[k] for k in ("A_CONSTRUCT", "B_CHALLENGE", "C_VERIFY"))

    bases: dict[str, dict[str, Any]] = {}
    base_refs: list[str] = []
    for seq, role in enumerate(
        ("BASE_TRIAD_A", "BASE_TRIAD_B", "BASE_TRIAD_C"), start=4
    ):
        receipt, payload = _run_leaf(
            command, cell, run_root, executor,
            phase="BASE_TRIAD",
            role=role,
            sequence=seq,
            prior=peer_bundle,
            prior_refs=peer_refs,
        )
        receipts.append(receipt)
        bases[role] = payload
        base_refs.append(receipt.artifact_path)

    receipt, final_payload = _run_leaf(
        command, cell, run_root, executor,
        phase="FINAL",
        role="FINAL_DIMENSIONAL_REBASE",
        sequence=7,
        prior=bases,
        prior_refs=tuple(base_refs),
    )
    receipts.append(receipt)

    return {
        "cell_id": cell.cell_id,
        "mode": "INDEPENDENT_RECIPROCAL",
        "leaf_receipts": [asdict(item) for item in receipts],
        "final_payload": final_payload,
    }


def _staggered_efficient(
    command: ArenaTriadCommand,
    cell: WorkCell,
    run_root: Path,
    executor: LeafExecutor,
) -> dict[str, Any]:
    receipts: list[LeafReceipt] = []

    a_receipt, a = _run_leaf(
        command, cell, run_root, executor,
        phase="LEAF", role="A_CONSTRUCT", sequence=1
    )
    receipts.append(a_receipt)

    b_receipt, b = _run_leaf(
        command, cell, run_root, executor,
        phase="CHALLENGE", role="B_CHALLENGE", sequence=2,
        prior={"A_CONSTRUCT": a}, prior_refs=(a_receipt.artifact_path,)
    )
    receipts.append(b_receipt)

    c_receipt, c = _run_leaf(
        command, cell, run_root, executor,
        phase="VERIFY", role="C_VERIFY", sequence=3,
        prior={"A_CONSTRUCT": a, "B_CHALLENGE": b},
        prior_refs=(a_receipt.artifact_path, b_receipt.artifact_path)
    )
    receipts.append(c_receipt)

    r_receipt, rebased = _run_leaf(
        command, cell, run_root, executor,
        phase="REBASE", role="A_REBASE", sequence=4,
        prior={"B_CHALLENGE": b, "C_VERIFY": c},
        prior_refs=(b_receipt.artifact_path, c_receipt.artifact_path)
    )
    receipts.append(r_receipt)

    return {
        "cell_id": cell.cell_id,
        "mode": "STAGGERED_EFFICIENT",
        "leaf_receipts": [asdict(item) for item in receipts],
        "final_payload": rebased,
    }


def _calls_per_cell(mode: Mode) -> int:
    return 7 if mode == "INDEPENDENT_RECIPROCAL" else 4


def parse_command(raw: dict[str, Any]) -> ArenaTriadCommand:
    cells = tuple(
        WorkCell(
            cell_id=str(item["cell_id"]),
            objective=str(item["objective"]),
            source_refs=tuple(str(x) for x in item.get("source_refs", [])),
            constraints=tuple(str(x) for x in item.get("constraints", [])),
            reopen_handles=tuple(str(x) for x in item.get("reopen_handles", [])),
        )
        for item in raw.get("cells", [])
    )
    mode = str(raw.get("mode", "INDEPENDENT_RECIPROCAL"))
    if mode not in ("INDEPENDENT_RECIPROCAL", "STAGGERED_EFFICIENT"):
        raise ArenaTriadError(f"unsupported_mode:{mode}")
    return ArenaTriadCommand(
        command_id=str(raw["command_id"]),
        idempotency_key=str(raw["idempotency_key"]),
        arena_head=str(raw["arena_head"]),
        objective=str(raw["objective"]),
        cells=cells,
        mode=mode,  # type: ignore[arg-type]
        effect=str(raw.get("effect", "D0")),
        gate_target=int(raw.get("gate_target", 10)),
        max_concurrency=int(raw.get("max_concurrency", 9)),
        max_leaf_calls=int(raw.get("max_leaf_calls", 256)),
        mission=str(raw.get("mission", ArenaTriadCommand.mission)),
        purpose=str(raw.get("purpose", ArenaTriadCommand.purpose)),
    )


def _usage_totals(cells: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for cell in cells:
        for receipt in cell["leaf_receipts"]:
            usage = receipt.get("usage") or {}
            for key, value in usage.items():
                if isinstance(value, int):
                    totals[key] = totals.get(key, 0) + value
    return totals


def execute_arena_triads(
    raw_command: dict[str, Any],
    *,
    current_arena_head: str,
    leaf_executor: LeafExecutor,
    output_root: str | Path = "aura_workspace/arena_triads",
) -> dict[str, Any]:
    command = parse_command(raw_command)
    if command.effect != "D0":
        raise ArenaTriadError("D1_PLUS_requires_separate_authority")
    if command.gate_target > 10:
        raise ArenaTriadError("autonomy_stops_at_Gate10")
    if command.arena_head != current_arena_head:
        raise ArenaTriadStale(
            f"stale_arena_head:{command.arena_head}!={current_arena_head}"
        )
    if not command.cells:
        raise ArenaTriadError("no_independent_cells")

    planned = len(command.cells) * _calls_per_cell(command.mode)
    if planned > command.max_leaf_calls:
        raise ArenaTriadBudgetExceeded(
            f"planned_leaf_calls={planned}>max_leaf_calls={command.max_leaf_calls}"
        )

    run_root = Path(output_root) / _safe_component(command.idempotency_key)
    result_path = run_root / "RESULT.json"
    if result_path.exists():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        existing["idempotent_replay"] = True
        return existing

    run_root.mkdir(parents=True, exist_ok=True)
    ack = {
        "schema": "AuraArenaTriadAckV1",
        "command_id": command.command_id,
        "idempotency_key": command.idempotency_key,
        "arena_head": command.arena_head,
        "mode": command.mode,
        "status": "ACK_ORCHESTRATION_ACCEPTED_BEFORE_LEAF_EFFECT",
        "independent_cells": len(command.cells),
        "planned_leaf_calls": planned,
        "recorded_at_unix": time.time(),
    }
    (run_root / "ACK.json").write_text(_canonical(ack) + "\n", encoding="utf-8")

    runner = (
        _independent_reciprocal
        if command.mode == "INDEPENDENT_RECIPROCAL"
        else _staggered_efficient
    )
    workers = max(1, min(command.max_concurrency, len(command.cells)))
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="aura-cell") as pool:
        futures = {
            pool.submit(runner, command, cell, run_root, leaf_executor): cell.cell_id
            for cell in command.cells
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["cell_id"])

    # Important: final top-level result contains refs/digests, not full leaf bodies.
    # Full leaf payloads remain in per-leaf artifacts and are reopened only as needed.
    result = {
        "schema": "AuraArenaTriadResultV1",
        "command_id": command.command_id,
        "idempotency_key": command.idempotency_key,
        "arena_head": command.arena_head,
        "mode": command.mode,
        "status": "TERMINAL_SUCCESS",
        "planned_leaf_calls": planned,
        "usage_totals": _usage_totals(results),
        "cells": [
            {
                "cell_id": cell["cell_id"],
                "mode": cell["mode"],
                "leaf_receipts": cell["leaf_receipts"],
                "final_payload": cell["final_payload"],
            }
            for cell in results
        ],
        "claim_ceiling": "MODEL_OUTPUT_ONLY_NONPROMOTING_GATE10",
        "hyperdrive": {
            "collapse": "leaf-receipts + final-cell-rebases",
            "reopen_on": ["newer_arena_head", "source_invalidator", "failed_acceptance_axis"],
        },
        "recorded_at_unix": time.time(),
    }
    provisional = (_canonical(result) + "\n").encode("utf-8")
    result["result_digest"] = _sha(provisional)
    result_path.write_text(_canonical(result) + "\n", encoding="utf-8")
    return result
