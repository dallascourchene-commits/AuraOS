import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "arena"))

from memory_city_handoff_current_read_seal import *
from memory_city_horizon_fenced_handoff import digest

R = lambda x: digest({"x": x})


@dataclass(frozen=True)
class ReadCert:
    status: str = "READY_D0"
    coverage_receipt_root: str = R("coverage")
    program_root: str = R("program")
    sealed_domain_root: str = R("domain")
    coverage_generation: int = 4
    binding_roots: tuple = (R("b1"), R("b2"))
    member_support_roots: tuple = (R("s1"), R("s2"))
    transition_model_root: str = R("transition")
    horizon: int = 2
    future_congruence_root: str | None = R("future")
    consequence_root: str = R("consequence")
    receipt_root: str = R("certificate")


@dataclass(frozen=True)
class ReadUse:
    status: str = "READY_D0"
    reason: str = "current"
    certificate_root: str = R("certificate")


def bundle(cert=None, use=None):
    cert = cert or ReadCert()
    use = use or ReadUse()
    semantic = semantic_handoff_root(cert)
    use_root = read_use_root(cert, use)
    current = CurrentReadUseBinding(use_root, R("read-owner"))
    evidence = SemanticHandoffEvidence(use_root, semantic, R("owner"), R("verifier"))
    mutation = MutationBoundaryProjection(
        "cell", 7, R("cfg"), 11, 19, 19, "agent", 100,
        semantic, R("transition-authority"), R("resource")
    )
    verification = HandoffVerificationContext(
        "cell", 7, R("cfg"), 11, 19, 19,
        R("owner"), R("verifier"), R("transition-authority"), R("resource"), 10
    )
    return cert, use, current, evidence, mutation, verification


class CurrentReadUseSealTests(unittest.TestCase):
    def test_exact_current_read_use_preserves_d0_ready(self):
        self.assertEqual(
            compile_current_horizon_fenced_handoff(*bundle()).disposition,
            HandoffDisposition.READY_D0,
        )

    def test_read_owner_move_rebinds_before_mutation_checks(self):
        cert, use, current, evidence, mutation, verification = bundle()
        moved = CurrentReadUseBinding(R("new-current-read-use"), current.read_owner_receipt_root)
        out = compile_current_horizon_fenced_handoff(
            cert, use, moved, evidence, mutation, verification
        )
        self.assertEqual(out.disposition, HandoffDisposition.REBIND_REQUIRED)
        self.assertEqual(out.reason, "CURRENT_READ_USE_MOVED")

    def test_stale_ready_cannot_survive_current_hold_root(self):
        cert, old_ready, current, evidence, mutation, verification = bundle()
        current_hold = ReadUse(status="HOLD_D0", reason="semantic_moved")
        moved = CurrentReadUseBinding(
            read_use_root(cert, current_hold), current.read_owner_receipt_root
        )
        out = compile_current_horizon_fenced_handoff(
            cert, old_ready, moved, evidence, mutation, verification
        )
        self.assertEqual(out.disposition, HandoffDisposition.REBIND_REQUIRED)

    def test_same_certificate_but_new_current_use_root_rebinds(self):
        cert, use, current, evidence, mutation, verification = bundle()
        # Same certificate identity; the owner has a new at-use decision root.
        moved = CurrentReadUseBinding(R("same-cert-new-use"), current.read_owner_receipt_root)
        self.assertEqual(
            compile_current_horizon_fenced_handoff(
                cert, use, moved, evidence, mutation, verification
            ).disposition,
            HandoffDisposition.REBIND_REQUIRED,
        )

    def test_bad_read_binding_cannot_mint_authority(self):
        with self.assertRaises(ValueError):
            CurrentReadUseBinding(R("r"), R("o"), effect_authority=True)

    def test_existing_mutation_fence_checks_still_apply_after_seal(self):
        cert, use, current, evidence, mutation, verification = bundle()
        stale = MutationBoundaryProjection(
            mutation.cell_id, mutation.revision, mutation.configuration_root,
            mutation.support_epoch, 19, 18, mutation.holder,
            mutation.expires_at, mutation.semantic_handoff_root,
            mutation.transition_authority_receipt_root,
            mutation.resource_fence_receipt_root,
        )
        out = compile_current_horizon_fenced_handoff(
            cert, use, current, evidence, stale, verification
        )
        self.assertEqual(out.disposition, HandoffDisposition.HOLD)


if __name__ == "__main__":
    unittest.main()
