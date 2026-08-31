from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest

from scripts.aura_workcapsule_live_causal_corroboration import (
    PR572_VERSION,
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)


def _canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest_identity(value: str) -> dict:
    return {"kind": "DIGEST", "value": value}


def _authority568() -> dict:
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


def _authority572() -> dict:
    out = _authority568()
    out.pop("mutation_authorized")
    return out


def pr568_receipt(**overrides) -> dict:
    value = {
        "version": "AURA_WORKCAPSULE_LIVE_CAUSAL_RAW_SLICE_JOIN_V1",
        "live_recursive_target_raw_slice_reproved": True,
        "portable_raw_slice_transport_reproved": True,
        "causal_post_owner_reproved_from_raw_evidence": True,
        "live_recursive_raw_slice_bound_to_exact_causal_post": True,
        "same_exact_post_source_instance_proven": True,
        "same_exact_raw_target_slice_proven": True,
        "post_source_projection_receipt_identity": _digest_identity("11" * 32),
        "causal_post_closure_receipt_identity": _digest_identity("22" * 32),
        "dependency_key": {"file_id": 17, "relative_path": "src/a.py"},
        "source_generation": 43,
        "full_source_sha256_hex": "33" * 32,
        "full_source_byte_len": 32,
        "target_byte_start": 0,
        "target_byte_end": 6,
        "target_slice_byte_len": 6,
        "target_slice_sha256_hex": "44" * 32,
        "selected_target_semantic_handle_digest_hex": "ab" * 32,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "raw_slice_projection_producer_authenticated": False,
        "source_observation_producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "source_to_graph_dependency_map_proven": False,
        "node_level_invalidation_cone_proven": False,
        "runtime_name_resolution_proven": False,
        "call_graph_proven": False,
        "b_minus_approved": False,
        "authority": _authority568(),
    }
    value.update(overrides)
    return value


def pr572_receipt(**overrides) -> dict:
    value = {
        "version": PR572_VERSION,
        "live_pr560_to_pr556_causal_slice_join_proven": True,
        "portable_raw_slice_projection_verified": True,
        "live_post_source_coordinate_match_proven": True,
        "causal_post_owner_reproved_by_child": True,
        "post_source_projection_receipt_identity": _digest_identity("11" * 32),
        "matched_live_post_source_witness_ref": "source-witness:post:17",
        "raw_slice_projection_payload_sha256": "55" * 32,
        "file_id": 17,
        "relative_path": "src/a.py",
        "source_generation": 43,
        "full_source_sha256_hex": "33" * 32,
        "full_source_byte_len": 32,
        "target_byte_start": 0,
        "target_byte_end": 6,
        "target_slice_sha256_hex": "44" * 32,
        "selected_target_semantic_handle_digest_hex": "ab" * 32,
        "causal_pre_closure_status": "HOLD",
        "causal_post_closure_status": "CLOSED",
        "causal_post_o10_receipt_identity": _digest_identity("22" * 32),
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "host_disposition": "HOST_OBSERVATION_REQUIRED",
        "host_gate_states": {
            "U_HEAD": "UNKNOWN",
            "U_ROUTE": "UNKNOWN",
            "U_F2": "UNKNOWN",
            "U_CUSTODY": "UNKNOWN",
            "U_CANARY": "UNKNOWN",
        },
        "host_observation_set_complete": False,
        "host_observation_authority_proven": False,
        "resolver_trust_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "raw_slice_promoted_to_host_rank": False,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "producer_authenticated": False,
        "semantic_repair_correctness_proven": False,
        "source_currentness_minted": False,
        "authority": _authority572(),
    }
    value.update(overrides)
    value.pop("receipt_identity", None)
    value["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": PR572_VERSION,
        "value": hashlib.sha256(_canonical_bytes(value)).hexdigest(),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return value


class LiveCausalCorroborationTests(unittest.TestCase):
    def test_independent_proofs_corroborate_same_live_source_without_artifact_collapse(self) -> None:
        a = pr568_receipt()
        b = pr572_receipt()
        self.assertEqual([], verify_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b))
        out = admit_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b)
        self.assertTrue(out["same_live_source_instance_proven"])
        self.assertTrue(out["same_live_target_slice_proven"])
        self.assertTrue(out["same_post_source_projection_identity_proven"])
        self.assertTrue(out["same_causal_o10_identity_proven"])
        self.assertTrue(out["independent_proof_artifacts_preserved"])
        self.assertTrue(out["proof_artifact_refs_distinct"])
        self.assertNotEqual(out["pr568_artifact_ref"], out["pr572_artifact_ref"])
        self.assertFalse(out["semantic_equivalence_proven"])
        self.assertFalse(out["producer_authentication_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(out["semantic_k27_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_source_generation_drift_breaks_corroboration(self) -> None:
        b = pr572_receipt(source_generation=44)
        self.assertIn(
            "LIVE_SOURCE_INSTANCE_MISMATCH",
            verify_live_causal_corroboration(pr568_receipt=pr568_receipt(), pr572_receipt=b),
        )

    def test_target_slice_drift_breaks_corroboration(self) -> None:
        b = pr572_receipt(target_slice_sha256_hex="66" * 32)
        self.assertIn(
            "LIVE_TARGET_SLICE_MISMATCH",
            verify_live_causal_corroboration(pr568_receipt=pr568_receipt(), pr572_receipt=b),
        )

    def test_post_projection_identity_drift_breaks_corroboration(self) -> None:
        b = pr572_receipt(post_source_projection_receipt_identity=_digest_identity("77" * 32))
        self.assertIn(
            "POST_SOURCE_PROJECTION_IDENTITY_MISMATCH",
            verify_live_causal_corroboration(pr568_receipt=pr568_receipt(), pr572_receipt=b),
        )

    def test_causal_o10_identity_drift_breaks_corroboration(self) -> None:
        b = pr572_receipt(causal_post_o10_receipt_identity=_digest_identity("88" * 32))
        self.assertIn(
            "CAUSAL_O10_IDENTITY_MISMATCH",
            verify_live_causal_corroboration(pr568_receipt=pr568_receipt(), pr572_receipt=b),
        )

    def test_parent_schema_widening_fails_closed(self) -> None:
        a = pr568_receipt()
        a["semantic_truth"] = True
        self.assertEqual(
            ["PR568_RECEIPT_SCHEMA_MISMATCH"],
            verify_live_causal_corroboration(pr568_receipt=a, pr572_receipt=pr572_receipt()),
        )

    def test_parent_authority_widening_fails_closed(self) -> None:
        a = pr568_receipt()
        a["authority"]["execution_authorized"] = True
        self.assertIn(
            "PR568_AUTHORITY_WIDENED",
            verify_live_causal_corroboration(pr568_receipt=a, pr572_receipt=pr572_receipt()),
        )

    def test_pr572_self_integrity_is_verified(self) -> None:
        b = pr572_receipt()
        b["full_source_byte_len"] = 33
        violations = verify_live_causal_corroboration(pr568_receipt=pr568_receipt(), pr572_receipt=b)
        self.assertIn("PR572_RECEIPT_IDENTITY_MISMATCH", violations)

    def test_public_boundary_is_two_receipts_only(self) -> None:
        params = set(inspect.signature(verify_live_causal_corroboration).parameters)
        self.assertEqual({"pr568_receipt", "pr572_receipt"}, params)

    def test_admission_identity_is_deterministic(self) -> None:
        a, b = pr568_receipt(), pr572_receipt()
        first = admit_live_causal_corroboration(pr568_receipt=a, pr572_receipt=b)
        second = admit_live_causal_corroboration(pr568_receipt=copy.deepcopy(a), pr572_receipt=copy.deepcopy(b))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
