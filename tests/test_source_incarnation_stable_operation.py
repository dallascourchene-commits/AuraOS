import unittest
from dataclasses import replace

from tools.arena.source_incarnation_stable_operation import (
    AdmissionClaim, Disposition, StableOperationIntent, VerifiedAdmission,
    compile_attempt, compile_stable_operation, digest, make_test_verified_admission,
    project_source_incarnation,
)
from tools.project006.transport_source_identity_bridge import DriveSourceIncarnation

R = lambda s: digest({"r": s})


def source(file_id="f1", revision="r1", data=b"alpha", mime="text/plain"):
    return DriveSourceIncarnation(file_id, revision, mime, data)


def intent(payload="p1", occurrence="occ-1"):
    return StableOperationIntent("creative", "edit", occurrence, R(payload), R("policy"))


def claim(op, actor="agent-a", k27=(1,2,3), host=1, admgen=1, admission="a1", current="c1"):
    return AdmissionClaim(op.operation_root, R(admission), R(current), actor, R("card"), R("lease"), R("progress"), host, admgen, k27)


def resolver_ok(c): return make_test_verified_admission(c)


class TestSourceIncarnationStableOperation(unittest.TestCase):
    def test_projection_recomputes_o17_root(self):
        s = source()
        p = project_source_incarnation(s)
        self.assertEqual(p.incarnation_root, s.incarnation_root)

    def test_same_semantics_same_source_same_operation(self):
        self.assertEqual(compile_stable_operation(source(), intent()).operation_root,
                         compile_stable_operation(source(), intent()).operation_root)

    def test_same_bytes_different_file_rotates_operation(self):
        self.assertNotEqual(compile_stable_operation(source("f1"), intent()).operation_root,
                            compile_stable_operation(source("f2"), intent()).operation_root)

    def test_same_bytes_different_revision_rotates_operation(self):
        self.assertNotEqual(compile_stable_operation(source(revision="r1"), intent()).operation_root,
                            compile_stable_operation(source(revision="r2"), intent()).operation_root)

    def test_mime_rotates_operation(self):
        self.assertNotEqual(compile_stable_operation(source(mime="text/plain"), intent()).operation_root,
                            compile_stable_operation(source(mime="text/markdown"), intent()).operation_root)

    def test_content_rotates_operation(self):
        self.assertNotEqual(compile_stable_operation(source(data=b"alpha"), intent()).operation_root,
                            compile_stable_operation(source(data=b"beta"), intent()).operation_root)

    def test_semantic_payload_rotates_operation(self):
        self.assertNotEqual(compile_stable_operation(source(), intent("p1")).operation_root,
                            compile_stable_operation(source(), intent("p2")).operation_root)

    def test_occurrence_scope_rotates_repeatable_operation(self):
        self.assertNotEqual(compile_stable_operation(source(), intent(occurrence="day1")).operation_root,
                            compile_stable_operation(source(), intent(occurrence="day2")).operation_root)

    def test_navigation_actor_rebind_preserves_operation_rotates_attempt(self):
        op = compile_stable_operation(source(), intent())
        a = compile_attempt(op, claim(op, actor="agent-a", k27=(1,2,3)), resolver_ok)
        b = compile_attempt(op, claim(op, actor="agent-b", k27=(13,5,1), host=2, admgen=2), resolver_ok)
        self.assertEqual(a.operation_root, b.operation_root)
        self.assertNotEqual(a.attempt_root, b.attempt_root)
        self.assertEqual(a.disposition, Disposition.ATTEMPT_D0)
        self.assertEqual(b.disposition, Disposition.ATTEMPT_D0)

    def test_current_admission_move_rotates_attempt(self):
        op = compile_stable_operation(source(), intent())
        a = compile_attempt(op, claim(op, admission="a1", current="c1"), resolver_ok)
        b = compile_attempt(op, claim(op, admission="a2", current="c2", admgen=2), resolver_ok)
        self.assertEqual(a.operation_root, b.operation_root)
        self.assertNotEqual(a.attempt_root, b.attempt_root)

    def test_unverified_admission_holds(self):
        op = compile_stable_operation(source(), intent())
        d = compile_attempt(op, claim(op), lambda c: None)
        self.assertEqual(d.disposition, Disposition.HOLD)

    def test_operation_mismatch_rebinds(self):
        op = compile_stable_operation(source(), intent())
        c = replace(claim(op), operation_root=R("other-op"))
        d = compile_attempt(op, c, resolver_ok)
        self.assertEqual(d.disposition, Disposition.REBIND)

    def test_forged_verifier_claim_root_reproves(self):
        op = compile_stable_operation(source(), intent())
        c = claim(op)
        good = make_test_verified_admission(c)
        bad = replace(good, claim_root=R("forged"))
        d = compile_attempt(op, c, lambda _: bad)
        self.assertEqual(d.disposition, Disposition.REPROVE)

    def test_transport_required_without_observation_holds(self):
        op = compile_stable_operation(source(), intent())
        d = compile_attempt(op, claim(op), resolver_ok, transport_required=True)
        self.assertEqual(d.disposition, Disposition.HOLD)

    def test_transport_observation_is_attempt_not_operation_identity(self):
        op = compile_stable_operation(source(), intent())
        c = claim(op)
        a = compile_attempt(op, c, resolver_ok, transport_observation_root=R("transport-a"), transport_required=True)
        b = compile_attempt(op, c, resolver_ok, transport_observation_root=R("transport-b"), transport_required=True)
        self.assertEqual(a.operation_root, b.operation_root)
        self.assertNotEqual(a.attempt_root, b.attempt_root)

    def test_verified_admission_cannot_mint_effect_authority(self):
        op = compile_stable_operation(source(), intent())
        c = claim(op)
        good = make_test_verified_admission(c)
        with self.assertRaises(ValueError):
            VerifiedAdmission(**{**good.__dict__, "effect_authority": True})


if __name__ == "__main__":
    unittest.main()
