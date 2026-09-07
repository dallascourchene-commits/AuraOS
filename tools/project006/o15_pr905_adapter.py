from __future__ import annotations

from typing import Any

from tools.project006.o15_reference.o15_workcell_stable_operation import (
    Action,
    ProofBoundAttempt,
    SemanticOperation,
)


def _action_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    if not isinstance(raw, str):
        raise ValueError("PR905_PARENT_ACTION_INVALID")
    return raw


def from_pr905_proof_bound_permit(
    operation: SemanticOperation,
    proof_permit: Any,
) -> ProofBoundAttempt:
    """Translate PR905's non-owning proof-bound permit into O15's attempt witness.

    This adapter does not authorize or execute anything. PR905 remains the admission
    membrane and its parent journal remains the durable effect-attempt owner. O15
    only consumes the already-produced proof-bound candidate and cross-binds it to
    stable semantic operation identity plus current host workcell evidence.
    """

    parent = getattr(proof_permit, "parent_permit", None)
    if parent is None:
        raise ValueError("PR905_PARENT_PERMIT_REQUIRED")
    action_raw = _action_value(getattr(parent, "action", None))
    try:
        action = Action(action_raw)
    except ValueError as exc:
        raise ValueError("PR905_PARENT_ACTION_NOT_PROVIDER_CANDIDATE") from exc
    if action not in (Action.CALL, Action.RETRY):
        raise ValueError("PR905_PARENT_ACTION_NOT_PROVIDER_CANDIDATE")
    if getattr(parent, "command_id", None) != operation.command_id:
        raise ValueError("PR905_PARENT_COMMAND_MOVED")
    attempt_root = getattr(parent, "effect_attempt_root", None)
    if attempt_root is None:
        raise ValueError("PR905_DURABLE_ATTEMPT_ROOT_REQUIRED")
    count = getattr(parent, "provider_request_count", None)
    admission_root = getattr(proof_permit, "proof_bound_admission_root", None)
    return ProofBoundAttempt(
        action=action,
        command_id=operation.command_id,
        stable_operation_root=operation.root,
        proof_bound_admission_root=admission_root,
        parent_attempt_root=attempt_root,
        provider_request_count=count,
    )
