from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tools.project006.o15_pr905_adapter import from_pr905_proof_bound_permit
from tools.project006.o15_reference.o15_workcell_stable_operation import (
    Action,
    Gate,
    HostCurrent,
    SemanticOperation,
    issue_lease,
)
from tools.project006.tecc_effect_admission_bridge import ProofBoundProviderActionPermit

KEY = b"o15-hosted-interop-key-32-bytes!!"

def r(x: str) -> str:
    from tools.project006.o15_reference.o15_workcell_stable_operation import H
    return H(["interop", x])


def operation() -> SemanticOperation:
    return SemanticOperation(
        "cmd-o15", "idem-o15", "drive-file-o15", "revision-o15", r("source"),
        r("intent"), r("contract"), r("payload"),
    )


def current() -> HostCurrent:
    return HostCurrent("session-o15", r("objective"), "K27", r("card"), r("progress"), 9, 50)


def lease(c: HostCurrent, handle: str = "host-workcell-o15-abcdefgh"):
    return issue_lease(
        key=KEY, handle=handle, session_id=c.session_id, objective_root=c.objective_root,
        project=c.project, card_root=c.card_root, progress_root=c.progress_root,
        host_generation=c.host_generation, issued_at=40, expires_at=100,
    )


def pr905_permit(op: SemanticOperation, *, action="CALL_PROVIDER_FIRST_TIME", count=1, attempt=None, admission=None):
    parent = SimpleNamespace(
        action=action,
        command_id=op.command_id,
        effect_attempt_root=attempt or r(f"attempt-{count}"),
        provider_request_count=count,
    )
    return ProofBoundProviderActionPermit(
        parent,
        admission or r(f"admission-{count}"),
        r("tecc-input"),
        r("consumer-admission"),
        r("authorization"),
    )


class O15Pr905InteropTest(unittest.TestCase):
    def gate(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        return Gate(Path(tmp.name) / "o15.sqlite", lease_key=KEY)

    def test_first_pr905_candidate_binds_current_workcell_and_stable_operation(self):
        op = operation(); c = current(); l = lease(c); g = self.gate()
        attempt = from_pr905_proof_bound_permit(op, pr905_permit(op))
        permit = g.expose_first(op, l, c, attempt)
        self.assertEqual(permit.action, Action.CALL)
        self.assertEqual(permit.stable_operation_root, op.root)
        self.assertEqual(permit.proof_bound_admission_root, attempt.proof_bound_admission_root)
        self.assertFalse(permit.effect_authority)

    def test_pr905_missing_durable_attempt_root_fails_closed(self):
        op = operation(); p = pr905_permit(op)
        p = ProofBoundProviderActionPermit(
            SimpleNamespace(action="CALL_PROVIDER_FIRST_TIME", command_id=op.command_id,
                            effect_attempt_root=None, provider_request_count=1),
            p.proof_bound_admission_root, p.tecc_input_root,
            p.consumer_admission_root, p.authorization_receipt_root,
        )
        with self.assertRaisesRegex(ValueError, "DURABLE_ATTEMPT"):
            from_pr905_proof_bound_permit(op, p)

    def test_pr905_rebind_and_workcell_reissue_preserve_operation_change_execution_witness(self):
        op = operation(); c = current(); g = self.gate(); l1 = lease(c)
        a1 = from_pr905_proof_bound_permit(op, pr905_permit(op))
        p1 = g.expose_first(op, l1, c, a1)
        g.ambiguous(op.command_id, op.root)
        l2 = lease(c, "host-workcell-o15-reissue-abcd")
        a2 = from_pr905_proof_bound_permit(
            op, pr905_permit(op, action="RETRY_EXACT_SAME_EFFECT", count=2,
                             admission=r("fresh-admission")),
        )
        p2 = g.retry(op, l2, c, a2, r("authenticated-recovery-verdict"))
        self.assertEqual(p1.stable_operation_root, p2.stable_operation_root)
        self.assertNotEqual(p1.execution_witness_root, p2.execution_witness_root)

    def test_result_closure_does_not_revalidate_expired_workcell(self):
        op = operation(); c = current(); g = self.gate()
        a = from_pr905_proof_bound_permit(op, pr905_permit(op))
        g.expose_first(op, lease(c), c, a)
        g.record_result(op.command_id, r("result"))
        self.assertEqual(g.return_writer_only(op.command_id), Action.RETURN)


if __name__ == "__main__":
    unittest.main()
