from __future__ import annotations

import copy
import inspect
import unittest

from scripts import aura_workcapsule_causal_envelope_raw_slice_noninterchangeability as target
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)


def authority() -> dict[str, bool]:
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


def pr573_receipt(**overrides):
    states = {
        "U_HEAD": "PASS",
        "U_ROUTE": "UNKNOWN",
        "U_F2": "UNKNOWN",
        "U_CUSTODY": "UNKNOWN",
        "U_CANARY": "UNKNOWN",
    }
    value = {
        "version": target.PR573_VERSION,
        "current_recursive_raw_target_reproved": True,
        "artifact_target_ref": "aura-workcapsule-target-sha256:" + "a" * 64,
        "causal_host_admission_integrity_checked": True,
        "causal_host_admission_reproved_by_child": False,
        "causal_host_admission_producer_authenticated": False,
        "causal_temporal_owner_claim_carried": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "current_pr565_host_summary_owner_reused": True,
        "resolved_host_gates_bound_to_exact_artifact": True,
        "resolved_host_gate_count": 1,
        "resolved_host_gates": ["U_HEAD"],
        "unknown_host_gates": ["U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY"],
        "host_gate_states": states,
        "host_observation_set_complete": False,
        "all_host_gates_pass_for_exact_artifact": False,
        "target_slice_sha256_hex": "b" * 64,
        "target_slice_byte_len": 32,
        "dependency_key": {"file_id": 17, "relative_path": "src/a.py"},
        "source_generation": 43,
        "full_source_sha256_hex": "c" * 64,
        "selected_target_semantic_handle_digest_hex": "d" * 64,
        "semantic_handle_derived_from_raw_slice": False,
        "semantic_identity_proven_by_raw_slice": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_proven": False,
        "producer_authenticated": False,
        "authority": authority(),
    }
    value.update(overrides)
    return value


def pr574_receipt(**overrides):
    payload = {
        "version": target.PR574_VERSION,
        "raw_slice_contract_owner": "PR566.verify_raw_slice_receipt",
        "causal_host_owner": "PR567.admit_causal_temporal_host_observation_admission",
        "raw_slice_receipt_digest": "e" * 64,
        "raw_slice_exact_current_local_evidence_validated": True,
        "causal_temporal_owner_reproved": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "host_gate_states": {gate: "UNKNOWN" for gate in target.GATES},
        "host_disposition": "HOST_OBSERVATION_REQUIRED",
        "host_observation_set_complete": False,
        "raw_slice_promoted_to_host_rank": False,
        "raw_slice_used_as_host_resolution": False,
        "raw_slice_semantic_identity_proven": False,
        "raw_slice_producer_authenticated": False,
        "host_observation_authority_proven": False,
        "host_resolver_trust_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "semantic_repair_correctness_minted": False,
        "authority": authority(),
    }
    payload.update(overrides)
    out = dict(payload)
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": target.PR574_VERSION,
        "value": target._sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out


class CausalEnvelopeRawSliceNoninterchangeabilityTests(unittest.TestCase):
    def test_exact_parent_consequences_prove_negative_relation(self):
        kwargs = {
            "causal_artifact_host_receipt": pr573_receipt(),
            "causal_raw_slice_host_separation_receipt": pr574_receipt(),
        }
        self.assertEqual([], target.verify_causal_envelope_raw_slice_noninterchangeability(**kwargs))
        out = target.admit_causal_envelope_raw_slice_noninterchangeability(**kwargs)
        self.assertTrue(out["raw_slice_causal_host_envelope_cross_cast_rejected"])
        self.assertFalse(out["proof_artifacts_interchangeable"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_pr574_receipt_is_not_pr573_causal_host_envelope(self):
        self.assertEqual(
            ["MALFORMED_CAUSAL_HOST_ADMISSION_ENVELOPE"],
            verify_causal_host_admission_envelope(pr574_receipt()),
        )

    def test_raw_rank_widening_rejects_even_when_resealed(self):
        raw = pr574_receipt(raw_slice_used_as_host_resolution=True)
        violations = target.verify_causal_envelope_raw_slice_noninterchangeability(
            causal_artifact_host_receipt=pr573_receipt(),
            causal_raw_slice_host_separation_receipt=raw,
        )
        self.assertIn("PR574_CEILING_VIOLATED:raw_slice_used_as_host_resolution", violations)

    def test_pr573_producer_auth_widening_rejects(self):
        host = pr573_receipt(causal_host_admission_producer_authenticated=True)
        violations = target.verify_causal_envelope_raw_slice_noninterchangeability(
            causal_artifact_host_receipt=host,
            causal_raw_slice_host_separation_receipt=pr574_receipt(),
        )
        self.assertIn("PR573_CEILING_VIOLATED:causal_host_admission_producer_authenticated", violations)

    def test_schema_widening_fails_closed(self):
        raw = pr574_receipt()
        raw["host_truth"] = True
        self.assertEqual(
            ["PR574_CONSEQUENCE_SCHEMA_MISMATCH"],
            target.verify_causal_envelope_raw_slice_noninterchangeability(
                causal_artifact_host_receipt=pr573_receipt(),
                causal_raw_slice_host_separation_receipt=raw,
            ),
        )

    def test_public_boundary_has_only_two_closed_parent_receipts(self):
        self.assertEqual(
            {"causal_artifact_host_receipt", "causal_raw_slice_host_separation_receipt"},
            set(inspect.signature(target.verify_causal_envelope_raw_slice_noninterchangeability).parameters),
        )

    def test_output_is_deterministic(self):
        kwargs = {
            "causal_artifact_host_receipt": pr573_receipt(),
            "causal_raw_slice_host_separation_receipt": pr574_receipt(),
        }
        first = target.admit_causal_envelope_raw_slice_noninterchangeability(**copy.deepcopy(kwargs))
        second = target.admit_causal_envelope_raw_slice_noninterchangeability(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
