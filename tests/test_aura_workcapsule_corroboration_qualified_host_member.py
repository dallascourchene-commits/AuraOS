from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest

from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
)
from scripts.aura_workcapsule_corroboration_qualified_host_member import (
    HOST_TARGET_PREFIX,
    PROOF_ARTIFACT_PREFIX,
    admit_corroboration_qualified_host_member,
    verify_corroboration_qualified_host_member,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _authority() -> dict:
    return {
        "review_authorized": False,
        "mutation_authorized": False,
        "execution_authorized": False,
        "commit_authorized": False,
        "merge_authorized": False,
        "promotion_authorized": False,
        "provider_effect_authorized": False,
        "public_effect_authorized": False,
        "human_authority": False,
    }


def live_host_receipt(*, pr568=None, target_ref=None, all_pass=False, **overrides) -> dict:
    pr568 = copy.deepcopy(pr568 if pr568 is not None else pr568_receipt())
    states = {
        "U_HEAD": "PASS" if all_pass else "UNKNOWN",
        "U_ROUTE": "PASS" if all_pass else "UNKNOWN",
        "U_F2": "PASS" if all_pass else "UNKNOWN",
        "U_CUSTODY": "PASS" if all_pass else "UNKNOWN",
        "U_CANARY": "PASS" if all_pass else "UNKNOWN",
    }
    resolved = [gate for gate, state in states.items() if state in {"PASS", "FAIL"}]
    unknown = [gate for gate, state in states.items() if state == "UNKNOWN"]
    value = {
        "version": "AURA_WORKCAPSULE_LIVE_CAUSAL_ARTIFACT_HOST_OBSERVATION_V1",
        "live_causal_raw_slice_reproved": True,
        "live_causal_artifact_target_ref": target_ref or HOST_TARGET_PREFIX + _sha(pr568),
        "host_admission_integrity_checked": True,
        "host_admission_reproved_by_child": False,
        "host_admission_producer_authenticated": False,
        "resolved_host_gates_bound_to_live_causal_artifact": True,
        "resolved_host_gate_count": len(resolved),
        "resolved_host_gates": resolved,
        "unknown_host_gates": unknown,
        "host_gate_states": states,
        "host_observation_set_complete": not unknown,
        "all_host_gates_pass_for_live_causal_artifact": all_pass,
        "causal_post_owner_reproved_from_raw_evidence": True,
        "same_exact_post_source_instance_proven": True,
        "same_exact_raw_target_slice_proven": True,
        "causal_post_closure_receipt_identity": copy.deepcopy(
            pr568["causal_post_closure_receipt_identity"]
        ),
        "dependency_key": copy.deepcopy(pr568["dependency_key"]),
        "source_generation": pr568["source_generation"],
        "full_source_sha256_hex": pr568["full_source_sha256_hex"],
        "full_source_byte_len": pr568["full_source_byte_len"],
        "target_byte_start": pr568["target_byte_start"],
        "target_byte_end": pr568["target_byte_end"],
        "target_slice_sha256_hex": pr568["target_slice_sha256_hex"],
        "selected_target_semantic_handle_digest_hex": pr568[
            "selected_target_semantic_handle_digest_hex"
        ],
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_proven": False,
        "producer_authenticated": False,
        "authority": _authority(),
    }
    value.update(overrides)
    return value


class CorroborationQualifiedHostMemberTests(unittest.TestCase):
    def test_host_target_is_exact_pr568_member_without_reference_identity_collapse(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a)
        self.assertEqual(
            [],
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )
        out = admit_corroboration_qualified_host_member(
            live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
        )
        self.assertTrue(out["host_target_is_exact_pr568_corroboration_member"])
        self.assertTrue(out["same_underlying_pr568_digest_across_reference_schemes"])
        self.assertTrue(out["reference_scheme_identity_preserved"])
        self.assertNotEqual(out["host_target_ref"], out["pr568_proof_artifact_ref"])
        self.assertTrue(out["host_target_ref"].startswith(HOST_TARGET_PREFIX))
        self.assertTrue(out["pr568_proof_artifact_ref"].startswith(PROOF_ARTIFACT_PREFIX))
        self.assertEqual(out["host_target_digest"], out["pr568_member_digest"])
        self.assertFalse(out["host_target_is_pr572_sibling"])
        self.assertFalse(out["host_target_is_corroboration_edge"])
        self.assertFalse(out["semantic_equivalence_proven"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_pr572_sibling_digest_cannot_impersonate_host_target_member(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        corroboration = admit_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b)
        sibling_digest = corroboration["pr572_artifact_ref"].split(":", 1)[1]
        host = live_host_receipt(pr568=a, target_ref=HOST_TARGET_PREFIX + sibling_digest)
        violations = verify_corroboration_qualified_host_member(
            live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
        )
        self.assertIn("HOST_TARGET_NOT_PR568_CORROBORATION_MEMBER", violations)
        self.assertIn("HOST_TARGET_ALIASES_PR572_SIBLING", violations)

    def test_corroboration_edge_digest_cannot_impersonate_member_target(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        corroboration = admit_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b)
        host = live_host_receipt(pr568=a, target_ref=HOST_TARGET_PREFIX + _sha(corroboration))
        violations = verify_corroboration_qualified_host_member(
            live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
        )
        self.assertIn("HOST_TARGET_ALIASES_CORROBORATION_EDGE", violations)
        self.assertIn("HOST_TARGET_NOT_PR568_CORROBORATION_MEMBER", violations)

    def test_proof_reference_scheme_cannot_be_cross_cast_as_host_target_string(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        corroboration = admit_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b)
        host = live_host_receipt(pr568=a, target_ref=corroboration["pr568_artifact_ref"])
        self.assertIn(
            "LIVE_HOST_TARGET_REF_INVALID",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_live_host_source_drift_rejects_even_with_correct_target_digest(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a, source_generation=44)
        self.assertIn(
            "LIVE_HOST_PR568_SOURCE_INSTANCE_MISMATCH",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_live_host_target_coordinate_drift_rejects_even_with_correct_target_digest(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a, target_slice_sha256_hex="66" * 32)
        self.assertIn(
            "LIVE_HOST_PR568_TARGET_SLICE_MISMATCH",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_live_host_o10_drift_rejects(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(
            pr568=a,
            causal_post_closure_receipt_identity={"kind": "DIGEST", "value": "99" * 32},
        )
        self.assertIn(
            "LIVE_HOST_PR568_CAUSAL_O10_MISMATCH",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_host_state_derived_fields_cannot_drift(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a, resolved_host_gate_count=1)
        self.assertIn(
            "LIVE_HOST_RESOLVED_GATE_COUNT_MISMATCH",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_host_authority_widening_fails_closed(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a)
        host["authority"]["execution_authorized"] = True
        self.assertIn(
            "LIVE_HOST_AUTHORITY_WIDENED",
            verify_corroboration_qualified_host_member(
                live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
            ),
        )

    def test_corroboration_owner_still_rejects_parent_world_drift(self) -> None:
        a, b = pr568_receipt(), pr572_receipt(source_generation=44)
        host = live_host_receipt(pr568=a)
        violations = verify_corroboration_qualified_host_member(
            live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
        )
        self.assertIn("CORROBORATION_LIVE_SOURCE_INSTANCE_MISMATCH", violations)

    def test_all_pass_host_state_remains_nonauthorizing(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        out = admit_corroboration_qualified_host_member(
            live_host_receipt=live_host_receipt(pr568=a, all_pass=True),
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertTrue(out["host_observation_set_complete"])
        self.assertEqual(set(out["host_gate_states"].values()), {"PASS"})
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["resolver_trust_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["effect_authority_proven"])

    def test_public_boundary_is_three_closed_parent_receipts_only(self) -> None:
        params = set(inspect.signature(verify_corroboration_qualified_host_member).parameters)
        self.assertEqual({"live_host_receipt", "pr568_receipt", "pr572_receipt"}, params)

    def test_admission_is_deterministic(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        host = live_host_receipt(pr568=a)
        first = admit_corroboration_qualified_host_member(
            live_host_receipt=host, pr568_receipt=a, pr572_receipt=b
        )
        second = admit_corroboration_qualified_host_member(
            live_host_receipt=copy.deepcopy(host),
            pr568_receipt=copy.deepcopy(a),
            pr572_receipt=copy.deepcopy(b),
        )
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
