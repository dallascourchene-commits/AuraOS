#!/usr/bin/env python3
"""Fail-closed AWJ-001 GEN25 descendant rebase barrier.

Derived from exactly two hosted-green foreign owners:
- PR559 host-observation admission: temporal closure != host/effect readiness.
- PR556 causal POST owner: lifecycle state must derive across distinct evidence phases.

The root promotion is an invalidator, not inherited descendant authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Any

SCHEMA = "AURA-AWJ001-GEN25-DESCENDANT-REBASE-BARRIER-v1"
CURRENT_ROOT_GENERATION = 25
CURRENT_ROOT_HEAD = "d91e0a39358901c5"
CURRENT_ROOT_RECEIPT_DRIVE_ID = "1yIwhSYDQbYLQRVSLIgGerARriDOyYof4uiXh2---chY"
PARENT_HOST_HEAD = "26201c63c3531bbf631ef34803c6f01ccd7499d3"
PARENT_HOST_RUN = 33355149887
PARENT_CAUSAL_HEAD = "5fae4070f82a9b5882ae0f63877359bf6e5a9a2b"
PARENT_CAUSAL_RUN = 33354561517
CONVERGENCE_COMMIT = "cf9f66a7854b34111566c6f532ebf45af9a82343"

CURRENT_CANDIDATE = "CURRENT_CANDIDATE_NONAUTHORIZING"
HOLD_ROOT_RECEIPT = "HOLD_ROOT_RECEIPT_NOT_EXACT"
REBASE_ROOT_GENERATION = "REBASE_REQUIRED_ROOT_GENERATION"
REBASE_ROOT_HEAD = "REBASE_REQUIRED_ROOT_HEAD"
REBASE_TEMPORAL_OWNER = "REBASE_REQUIRED_TEMPORAL_OWNER"
REBASE_HOST_OBSERVATION = "REBASE_REQUIRED_HOST_OBSERVATION_OWNER"
REBASE_COMMAND = "REBASE_REQUIRED_COMMAND_CURRENTNESS"
REBASE_LEASE = "REBASE_REQUIRED_LEASE_FENCE"
HOLD_CEILING = "HOLD_CLAIM_CEILING"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False, default=str).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DescendantContext:
    descendant_id: str
    descendant_kind: str
    compiled_root_generation: int
    compiled_root_head: str
    temporal_owner_generation: int
    host_observation_owner_generation: int
    command_bound_root_generation: int
    command_bound_root_head: str
    lease_fence_root_generation: int
    lease_fence_root_head: str
    root_receipt_drive_id: str = CURRENT_ROOT_RECEIPT_DRIVE_ID
    effect_authority_requested: bool = False


@dataclass(frozen=True)
class _Flags:
    root_receipt_exact: bool
    root_generation_exact: bool
    root_head_exact: bool
    temporal_owner_current: bool
    host_observation_owner_current: bool
    command_currentness_bound: bool
    lease_fence_current: bool
    claim_ceiling: bool


def _tree(f: _Flags) -> str:
    if not f.root_receipt_exact: return HOLD_ROOT_RECEIPT
    if not f.root_generation_exact: return REBASE_ROOT_GENERATION
    if not f.root_head_exact: return REBASE_ROOT_HEAD
    if not f.temporal_owner_current: return REBASE_TEMPORAL_OWNER
    if not f.host_observation_owner_current: return REBASE_HOST_OBSERVATION
    if not f.command_currentness_bound: return REBASE_COMMAND
    if not f.lease_fence_current: return REBASE_LEASE
    if not f.claim_ceiling: return HOLD_CEILING
    return CURRENT_CANDIDATE


def _table(f: _Flags) -> str:
    rows = (
        (not f.root_receipt_exact, HOLD_ROOT_RECEIPT),
        (not f.root_generation_exact, REBASE_ROOT_GENERATION),
        (not f.root_head_exact, REBASE_ROOT_HEAD),
        (not f.temporal_owner_current, REBASE_TEMPORAL_OWNER),
        (not f.host_observation_owner_current, REBASE_HOST_OBSERVATION),
        (not f.command_currentness_bound, REBASE_COMMAND),
        (not f.lease_fence_current, REBASE_LEASE),
        (not f.claim_ceiling, HOLD_CEILING),
        (True, CURRENT_CANDIDATE),
    )
    return next(disposition for predicate, disposition in rows if predicate)


def prove_different_j() -> int:
    checked = 0
    for bits in itertools.product((False, True), repeat=8):
        flags = _Flags(*bits)
        if _tree(flags) != _table(flags):
            raise AssertionError("AWJ001_GEN25_REBASE_DIFFERENT_J_DIVERGED")
        checked += 1
    return checked


@dataclass(frozen=True)
class DescendantRebaseReceipt:
    schema: str
    descendant_id: str
    descendant_kind: str
    disposition: str
    current_root_generation: int
    current_root_head: str
    compiled_root_generation: int
    compiled_root_head: str
    temporal_owner_generation: int
    host_observation_owner_generation: int
    command_bound_root_generation: int
    command_bound_root_head: str
    lease_fence_root_generation: int
    lease_fence_root_head: str
    rebase_required: bool
    current_candidate: bool
    effect_authorized: bool
    host_effect_ready: bool
    inherited_root_authority: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    receipt_digest: str

    def validate(self) -> None:
        if self.effect_authorized or self.host_effect_ready or self.inherited_root_authority:
            raise ValueError("AWJ001_DESCENDANT_EFFECT_AUTHORITY_WIDENED")
        if self.semantic_k27_authority_minted or self.native_private_transformer_kv_accessed:
            raise ValueError("AWJ001_DESCENDANT_CLAIM_CEILING_WIDENED")
        if self.current_candidate != (self.disposition == CURRENT_CANDIDATE):
            raise ValueError("AWJ001_DESCENDANT_CURRENT_CANDIDATE_INCONSISTENT")
        if self.rebase_required != self.disposition.startswith("REBASE_REQUIRED_"):
            raise ValueError("AWJ001_DESCENDANT_REBASE_FLAG_INCONSISTENT")
        body = _receipt_body(self, include_digest=False)
        if self.receipt_digest != _sha(body):
            raise ValueError("AWJ001_DESCENDANT_RECEIPT_DIGEST_MISMATCH")


def _receipt_body(receipt: DescendantRebaseReceipt, *, include_digest: bool) -> dict[str, Any]:
    body = {
        "schema": receipt.schema,
        "descendant_id": receipt.descendant_id,
        "descendant_kind": receipt.descendant_kind,
        "disposition": receipt.disposition,
        "current_root_generation": receipt.current_root_generation,
        "current_root_head": receipt.current_root_head,
        "compiled_root_generation": receipt.compiled_root_generation,
        "compiled_root_head": receipt.compiled_root_head,
        "temporal_owner_generation": receipt.temporal_owner_generation,
        "host_observation_owner_generation": receipt.host_observation_owner_generation,
        "command_bound_root_generation": receipt.command_bound_root_generation,
        "command_bound_root_head": receipt.command_bound_root_head,
        "lease_fence_root_generation": receipt.lease_fence_root_generation,
        "lease_fence_root_head": receipt.lease_fence_root_head,
        "rebase_required": receipt.rebase_required,
        "current_candidate": receipt.current_candidate,
        "effect_authorized": receipt.effect_authorized,
        "host_effect_ready": receipt.host_effect_ready,
        "inherited_root_authority": receipt.inherited_root_authority,
        "semantic_k27_authority_minted": receipt.semantic_k27_authority_minted,
        "native_private_transformer_kv_accessed": receipt.native_private_transformer_kv_accessed,
    }
    if include_digest:
        body["receipt_digest"] = receipt.receipt_digest
    return body


def assess_descendant(ctx: DescendantContext) -> DescendantRebaseReceipt:
    flags = _Flags(
        root_receipt_exact=ctx.root_receipt_drive_id == CURRENT_ROOT_RECEIPT_DRIVE_ID,
        root_generation_exact=ctx.compiled_root_generation == CURRENT_ROOT_GENERATION,
        root_head_exact=ctx.compiled_root_head == CURRENT_ROOT_HEAD,
        temporal_owner_current=ctx.temporal_owner_generation == CURRENT_ROOT_GENERATION,
        host_observation_owner_current=ctx.host_observation_owner_generation == CURRENT_ROOT_GENERATION,
        command_currentness_bound=(ctx.command_bound_root_generation == CURRENT_ROOT_GENERATION and ctx.command_bound_root_head == CURRENT_ROOT_HEAD),
        lease_fence_current=(ctx.lease_fence_root_generation == CURRENT_ROOT_GENERATION and ctx.lease_fence_root_head == CURRENT_ROOT_HEAD),
        claim_ceiling=not ctx.effect_authority_requested,
    )
    disposition = _tree(flags)
    if disposition != _table(flags):
        raise RuntimeError("AWJ001_GEN25_REBASE_RUNTIME_DIFFERENT_J_DIVERGED")
    partial = DescendantRebaseReceipt(
        schema=SCHEMA,
        descendant_id=ctx.descendant_id,
        descendant_kind=ctx.descendant_kind,
        disposition=disposition,
        current_root_generation=CURRENT_ROOT_GENERATION,
        current_root_head=CURRENT_ROOT_HEAD,
        compiled_root_generation=ctx.compiled_root_generation,
        compiled_root_head=ctx.compiled_root_head,
        temporal_owner_generation=ctx.temporal_owner_generation,
        host_observation_owner_generation=ctx.host_observation_owner_generation,
        command_bound_root_generation=ctx.command_bound_root_generation,
        command_bound_root_head=ctx.command_bound_root_head,
        lease_fence_root_generation=ctx.lease_fence_root_generation,
        lease_fence_root_head=ctx.lease_fence_root_head,
        rebase_required=disposition.startswith("REBASE_REQUIRED_"),
        current_candidate=disposition == CURRENT_CANDIDATE,
        effect_authorized=False,
        host_effect_ready=False,
        inherited_root_authority=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        receipt_digest="",
    )
    receipt = DescendantRebaseReceipt(**{**partial.__dict__, "receipt_digest": _sha(_receipt_body(partial, include_digest=False))})
    receipt.validate()
    return receipt


def gen24_fixture(kind: str = "WORKCAPSULE") -> DescendantContext:
    return DescendantContext(
        descendant_id="fixture:gen24-bound",
        descendant_kind=kind,
        compiled_root_generation=24,
        compiled_root_head="3aeb8f3db921201f",
        temporal_owner_generation=24,
        host_observation_owner_generation=24,
        command_bound_root_generation=24,
        command_bound_root_head="3aeb8f3db921201f",
        lease_fence_root_generation=24,
        lease_fence_root_head="3aeb8f3db921201f",
    )


def gen25_fixture(kind: str = "WORKCAPSULE") -> DescendantContext:
    return DescendantContext(
        descendant_id="fixture:gen25-bound",
        descendant_kind=kind,
        compiled_root_generation=25,
        compiled_root_head=CURRENT_ROOT_HEAD,
        temporal_owner_generation=25,
        host_observation_owner_generation=25,
        command_bound_root_generation=25,
        command_bound_root_head=CURRENT_ROOT_HEAD,
        lease_fence_root_generation=25,
        lease_fence_root_head=CURRENT_ROOT_HEAD,
    )


LAWS = (
    "RootPromotionInvalidatesStaleDescendantCurrentness",
    "GEN24BoundDescendantUnderGEN25=>RebaseRequiredBeforeEffect",
    "HostObservationCurrentnessDependsOnTemporalOwnerGeneration",
    "POST_CLOSED!=HOST_OBSERVATION_COMPLETE!=HOST_EFFECT_READY",
    "DistinctEvidencePhasesMustNotCollapse",
    "MatchingGEN25Descendant=>CurrentCandidateOnly",
    "RootAuthority!=InheritedDescendantAuthority",
    "K27Placement!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
