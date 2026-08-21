from dataclasses import FrozenInstanceError

import pytest

from aura_triadic_helix import (
    ContractViolation,
    Epoch,
    ObjectiveBinding,
    OutputRef,
    PositionExecutionIdentity,
    RoundCommitStatus,
    TriadPosition,
    TriadRoundCommitReceipt,
)

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64
D7 = "7" * 64
D8 = "8" * 64
D9 = "9" * 64


def objective() -> ObjectiveBinding:
    return ObjectiveBinding("O-C1", D1, "AURA_V9", 7, D2, D3)


def output(position: TriadPosition, epoch: int, digest: str) -> OutputRef:
    return OutputRef(
        position,
        Epoch(epoch),
        digest,
        objective().identity(),
        7,
        D2,
        D3,
        D4,
        True,
    )


def execution(position: TriadPosition, suffix: str) -> PositionExecutionIdentity:
    return PositionExecutionIdentity(
        position,
        f"worker-{suffix}",
        f"model-{suffix}",
        f"provider-{suffix}",
        f"group-{suffix}",
        f"assignment-{suffix}",
        D3,
    )


def receipt(*, x_peers=None, evidence=None, x_output=None) -> TriadRoundCommitReceipt:
    return TriadRoundCommitReceipt(
        workflow_id="wf-1",
        objective=objective(),
        epoch=Epoch(1),
        bootstrap_flag=False,
        x_peer_inputs=x_peers
        if x_peers is not None
        else [output(TriadPosition.Y, 0, D5), output(TriadPosition.Z, 0, D6)],
        y_peer_inputs=[
            output(TriadPosition.X, 0, D7),
            output(TriadPosition.Z, 0, D6),
        ],
        z_peer_inputs=[
            output(TriadPosition.X, 0, D7),
            output(TriadPosition.Y, 0, D5),
        ],
        external_evidence_refs=evidence if evidence is not None else ["source-b", "source-a"],
        x_output=x_output or output(TriadPosition.X, 1, D7),
        y_output=output(TriadPosition.Y, 1, D8),
        z_output=output(TriadPosition.Z, 1, D9),
        x_execution=execution(TriadPosition.X, "x"),
        y_execution=execution(TriadPosition.Y, "y"),
        z_execution=execution(TriadPosition.Z, "z"),
        handoff_plan_ref="handoff-1",
        committed_at="2026-08-21T18:40:00-07:00",
        commit_status=RoundCommitStatus.COMMITTED,
    )


def test_objective_identity_binds_source_currentness_and_authority():
    base = objective()
    assert base.identity() != ObjectiveBinding("O-C1", D1, "AURA_V9", 8, D2, D3).identity()
    assert base.identity() != ObjectiveBinding("O-C1", D1, "AURA_V9", 7, D4, D3).identity()
    assert base.identity() != ObjectiveBinding("O-C1", D1, "AURA_V9", 7, D2, D4).identity()


def test_round_digest_is_permutation_invariant_for_set_like_inputs():
    first = receipt()
    second = receipt(
        x_peers=list(reversed(first.x_peer_inputs)),
        evidence=list(reversed(first.external_evidence_refs)),
    )
    assert first.receipt_digest() == second.receipt_digest()


def test_round_record_computes_receipt_digest_instead_of_accepting_one():
    item = receipt()
    record = item.to_record()
    assert record["receipt_digest"] == item.receipt_digest()
    assert len(record["receipt_digest"]) == 64


def test_duplicate_peer_ref_is_rejected_structurally():
    peer = output(TriadPosition.Y, 0, D5)
    with pytest.raises(ContractViolation, match="duplicate canonical"):
        receipt(x_peers=[peer, peer]).protected_body()


def test_wrong_output_slot_is_rejected():
    wrong = output(TriadPosition.Y, 1, D7)
    with pytest.raises(ContractViolation, match="x_output must carry position X"):
        receipt(x_output=wrong).protected_body()


def test_output_epoch_must_match_round_epoch():
    wrong = output(TriadPosition.X, 2, D7)
    with pytest.raises(ContractViolation, match="x_output epoch must equal receipt epoch"):
        receipt(x_output=wrong).protected_body()


def test_invalid_digest_and_generation_fail_closed():
    with pytest.raises(ContractViolation, match="objective_digest"):
        ObjectiveBinding("O-C1", "not-a-digest", "AURA_V9", 7, D2, D3).protected_body()
    with pytest.raises(ContractViolation, match="source_generation"):
        ObjectiveBinding("O-C1", D1, "AURA_V9", -1, D2, D3).protected_body()


def test_contract_objects_are_frozen():
    item = objective()
    with pytest.raises(FrozenInstanceError):
        item.objective_id = "changed"
