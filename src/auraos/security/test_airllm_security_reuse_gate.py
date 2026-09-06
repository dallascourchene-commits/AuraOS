from __future__ import annotations

import copy
import itertools
import random
import unittest

import airllm_security_reuse_gate as gate


def generation():
    return {"semantic": "s", "source": "v4", "runtime": "p", "security": "w", "evidence": "e", "dependency": "d"}


def full_receipt():
    g = generation()
    leaves = []
    for index, (leaf_id, (axes, evidence_class)) in enumerate(gate._REQUIRED_LEAVES.items(), 1):
        leaves.append({
            "leaf_id": leaf_id,
            "axes": list(axes),
            "evidence_class": evidence_class,
            "status": "PASS",
            "proof": {
                "proof_id": f"proof-{leaf_id}",
                "proof_digest": f"{index:064x}",
                "status": "PASS",
                "bound_generation": {axis: g[axis] for axis in axes},
                "note": "",
            },
        })
    body = {
        "schema": gate.S,
        "subject": {
            "model_id": "zai-org/GLM-5.3",
            "model_sha256": "1" * 64,
            "loader_source_sha256": "2" * 64,
            "upstream_repository": "lyogavin/airllm",
            "upstream_release": "v4.0.0",
            "upstream_revision": "f" * 40,
        },
        "bound_generation": g,
        "current_generation": dict(g),
        "exact_foreign_parents": ["a", "b"],
        "leaves": leaves,
        "disposition": "LOCAL_VERIFIED_NONPROMOTING",
        "stale_or_missing": [],
        "effect_authority": False,
        "promotion_authorized": False,
        "owner_host_proven": False,
        "hosted_ci_proven": False,
        "gate10": False,
        "claim_ceiling": "D0",
        "laws": [],
    }
    return reseal(body)


def reseal(receipt):
    body = copy.deepcopy(receipt)
    body.pop("receipt_sha256", None)
    body.pop("k27", None)
    digest = gate.dig(body)
    body["receipt_sha256"] = digest
    raw = bytes.fromhex(digest)
    body["k27"] = [raw[0] % 27, raw[1] % 27, raw[2] % 27]
    return body


def request(receipt, authority=False):
    return gate.SecurityReuseRequest(
        scope="GENERAL_LOCAL_SECURITY",
        expected_receipt_sha256=receipt["receipt_sha256"],
        expected_subject_root=gate.subject_root(receipt),
        expected_current_generation_root=gate.generation_root(receipt),
        authority_requested=authority,
    )


class SecurityReuseLeafTests(unittest.TestCase):
    def test_complete_canonical_receipt_reuses_locally(self):
        receipt = full_receipt()
        self.assertTrue(gate.valid_receipt(receipt))
        decision = gate.admit(receipt, request(receipt))
        self.assertTrue(decision["reusable"])
        self.assertTrue(gate.verify(decision))
        self.assertFalse(decision["gate10"])

    def test_proofless_receipt_fails_even_when_self_consistent(self):
        receipt = full_receipt()
        receipt["leaves"] = []
        receipt = reseal(receipt)
        self.assertFalse(gate.valid_receipt(receipt))
        self.assertFalse(gate.admit(receipt, request(receipt))["reusable"])

    def test_missing_duplicate_or_wrong_leaf_shape_fails(self):
        mutations = []
        missing = full_receipt(); missing["leaves"] = missing["leaves"][:-1]; mutations.append(missing)
        duplicate = full_receipt(); duplicate["leaves"][-1] = copy.deepcopy(duplicate["leaves"][0]); mutations.append(duplicate)
        wrong_axes = full_receipt(); wrong_axes["leaves"][0]["axes"] = ["source"]; mutations.append(wrong_axes)
        for receipt in mutations:
            with self.subTest():
                self.assertFalse(gate.valid_receipt(reseal(receipt)))

    def test_failed_or_missing_proof_fails(self):
        failed = full_receipt(); failed["leaves"][0]["status"] = "FAIL"
        missing = full_receipt(); missing["leaves"][0]["proof"] = None
        for receipt in (failed, missing):
            self.assertFalse(gate.valid_receipt(reseal(receipt)))

    def test_proof_generation_mismatch_fails(self):
        receipt = full_receipt()
        receipt["leaves"][0]["proof"]["bound_generation"]["source"] = "stale"
        self.assertFalse(gate.valid_receipt(reseal(receipt)))

    def test_current_generation_drift_fails(self):
        receipt = full_receipt()
        receipt["current_generation"]["source"] = "stale"
        self.assertFalse(gate.valid_receipt(reseal(receipt)))

    def test_authority_request_never_reuses(self):
        receipt = full_receipt()
        self.assertFalse(gate.admit(receipt, request(receipt, authority=True))["reusable"])

    def test_hs1000_malformed_leaf_mutations_zero_false_reuse(self):
        rng = random.Random(20260905)
        false_reuses = 0
        for index in range(1000):
            receipt = full_receipt()
            kind = index % 8
            if kind == 0: receipt["leaves"] = []
            elif kind == 1: receipt["leaves"].pop()
            elif kind == 2: receipt["leaves"][0]["status"] = "FAIL"
            elif kind == 3: receipt["leaves"][0]["proof"] = None
            elif kind == 4: receipt["leaves"][0]["axes"] = ["source"]
            elif kind == 5: receipt["leaves"][0]["proof"]["bound_generation"]["source"] = "stale"
            elif kind == 6: receipt["current_generation"]["source"] = "stale"
            else: receipt["leaves"][0]["proof"]["proof_digest"] = ("a" if rng.random() < .5 else "b") * 63
            false_reuses += int(gate.valid_receipt(reseal(receipt)))
        self.assertEqual(false_reuses, 0)

    def test_omega8_has_one_all_hard_valid_keeper(self):
        self.assertEqual(sum(all(axis == 2 for axis in state) for state in itertools.product(range(3), repeat=8)), 1)

    def test_13d_trailing_context_never_repairs_proofless_core(self):
        receipt = full_receipt(); receipt["leaves"] = []; receipt = reseal(receipt)
        hard_valid = gate.valid_receipt(receipt)
        self.assertFalse(hard_valid)
        for trailing in itertools.product(range(3), repeat=5):
            self.assertFalse(hard_valid, trailing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
