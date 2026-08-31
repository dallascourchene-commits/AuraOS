from __future__ import annotations

import copy
import hashlib
import json
import unittest

from scripts.aura_workcapsule_context_binding import ACTIVE, COLD, CURRENT, STALE, compile_workcapsule_context_binding
from scripts.aura_workcapsule_reentry_closure import CLOSED, HOLD, compile_reentry_closure, verify_reentry_closure
from scripts.aura_workcapsule_reentry_closure_exact_verifier import (
    CANDIDATE_BINDING_IDENTITY_MISMATCH,
    EXACT_CLOSURE_INPUT_MISMATCH,
    PREVIOUS_BINDING_IDENTITY_MISMATCH,
    REENTRY_RECEIPT_IDENTITY_MISMATCH,
    admit_exact_reentry_closure,
    verify_exact_reentry_closure,
)
from scripts.aura_workcapsule_reentry_invalidation import compile_reentry_invalidation


def identity(value: str) -> dict[str, str]:
    return {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "TEST_V1",
        "scope_profile": "TEST_SCOPE",
        "value": value,
        "schema_version": "1",
    }


def reseal_o10_self_digest(receipt: dict) -> None:
    without_identity = copy.deepcopy(receipt)
    prior_identity = without_identity.pop("receipt_identity")
    canonical = json.dumps(without_identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    new_identity = copy.deepcopy(prior_identity)
    new_identity["value"] = hashlib.sha256(canonical).hexdigest()
    receipt["receipt_identity"] = new_identity


class WorkCapsuleReentryClosureExactVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capsule = {
            "capsule_id": "CAP-O11-1",
            "capsule_generation": 11,
            "parent_work_order_interface_binding_generation": 7,
            "execution_basis_identity": identity("basis-o11"),
        }
        self.graph = {
            "graph_id": "ASTGE-GRAPH-O11",
            "graph_generation": 11,
            "graph_basis_identity": identity("graph-o11"),
            "currentness": CURRENT,
            "witness_ref": "GRAPH:O11:CURRENT",
        }
        self.sources = [
            {
                "role": ACTIVE,
                "file_id": 3,
                "relative_path": "src/a.py",
                "source_generation": 1,
                "source_sha256": "a" * 64,
                "source_byte_len": 100,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:3:1",
            },
            {
                "role": ACTIVE,
                "file_id": 4,
                "relative_path": "src/b.py",
                "source_generation": 1,
                "source_sha256": "b" * 64,
                "source_byte_len": 200,
                "currentness": CURRENT,
                "witness_ref": "SOURCE:4:1",
            },
            {
                "role": COLD,
                "file_id": 9,
                "relative_path": "docs/frontier.md",
                "source_generation": 1,
                "source_sha256": "c" * 64,
                "source_byte_len": 50,
                "currentness": "UNKNOWN",
                "witness_ref": "SOURCE:9:UNKNOWN",
            },
        ]
        self.previous = self.binding(self.graph, self.sources)
        observed = copy.deepcopy(self.sources)
        observed[0]["currentness"] = STALE
        observed[0]["witness_ref"] = "SOURCE:3:STALE"
        self.plan = compile_reentry_invalidation(
            previous_binding=self.previous,
            observed_graph_witness=self.graph,
            observed_source_witnesses=observed,
        )
        rebound = copy.deepcopy(self.sources)
        rebound[0]["source_generation"] = 2
        rebound[0]["source_sha256"] = "d" * 64
        rebound[0]["source_byte_len"] = 101
        rebound[0]["witness_ref"] = "SOURCE:3:2:CURRENT"
        self.candidate = self.binding(self.graph, rebound)
        self.closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.plan,
            candidate_binding=self.candidate,
        )
        self.assertEqual(CLOSED, self.closure["closure_status"])

    def binding(self, graph, sources):
        return compile_workcapsule_context_binding(
            capsule=self.capsule,
            graph_witness=copy.deepcopy(graph),
            source_witnesses=copy.deepcopy(sources),
        )

    def verify(self, closure, *, previous=None, plan=None, candidate=None):
        return verify_exact_reentry_closure(
            previous_binding=previous or self.previous,
            reentry_receipt=plan or self.plan,
            candidate_binding=candidate or self.candidate,
            closure_receipt=closure,
        )

    def test_exact_canonical_closure_is_admitted(self):
        self.assertEqual([], self.verify(self.closure))
        admitted = admit_exact_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.plan,
            candidate_binding=self.candidate,
            closure_receipt=self.closure,
        )
        self.assertTrue(admitted["exact_closure_input_reproduction"])
        self.assertEqual(CLOSED, admitted["closure_status"])
        self.assertFalse(admitted["producer_identity_authenticated"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_resealed_previous_binding_identity_substitution_is_rejected(self):
        tampered = copy.deepcopy(self.closure)
        tampered["previous_binding_identity"]["value"] = "f" * 64
        reseal_o10_self_digest(tampered)
        self.assertEqual([], verify_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(PREVIOUS_BINDING_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_CLOSURE_INPUT_MISMATCH, violations)

    def test_resealed_reentry_receipt_identity_substitution_is_rejected(self):
        tampered = copy.deepcopy(self.closure)
        tampered["reentry_receipt_identity"]["value"] = "e" * 64
        reseal_o10_self_digest(tampered)
        self.assertEqual([], verify_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(REENTRY_RECEIPT_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_CLOSURE_INPUT_MISMATCH, violations)

    def test_resealed_candidate_binding_identity_substitution_is_rejected(self):
        tampered = copy.deepcopy(self.closure)
        tampered["candidate_binding_identity"]["value"] = "d" * 64
        reseal_o10_self_digest(tampered)
        self.assertEqual([], verify_reentry_closure(tampered))
        violations = self.verify(tampered)
        self.assertIn(CANDIDATE_BINDING_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_CLOSURE_INPUT_MISMATCH, violations)

    def test_old_closed_receipt_rejected_against_changed_candidate(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["source_generation"] = 3
        changed[0]["source_sha256"] = "9" * 64
        changed[0]["source_byte_len"] = 102
        changed[0]["witness_ref"] = "SOURCE:3:3:CURRENT"
        changed_candidate = self.binding(self.graph, changed)
        violations = self.verify(self.closure, candidate=changed_candidate)
        self.assertIn(CANDIDATE_BINDING_IDENTITY_MISMATCH, violations)
        self.assertIn(EXACT_CLOSURE_INPUT_MISMATCH, violations)

    def test_exact_hold_receipt_is_still_exactly_reproducible_without_promotion(self):
        collateral = copy.deepcopy(self.sources)
        collateral[0]["source_generation"] = 2
        collateral[0]["source_sha256"] = "d" * 64
        collateral[1]["source_generation"] = 2
        collateral[1]["source_sha256"] = "e" * 64
        candidate = self.binding(self.graph, collateral)
        closure = compile_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.plan,
            candidate_binding=candidate,
        )
        self.assertEqual(HOLD, closure["closure_status"])
        self.assertEqual([], self.verify(closure, candidate=candidate))
        admitted = admit_exact_reentry_closure(
            previous_binding=self.previous,
            reentry_receipt=self.plan,
            candidate_binding=candidate,
            closure_receipt=closure,
        )
        self.assertEqual(HOLD, admitted["closure_status"])
        self.assertFalse(any(admitted["authority"].values()))


if __name__ == "__main__":
    unittest.main()
