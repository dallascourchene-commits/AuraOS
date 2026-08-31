from __future__ import annotations

import copy
import inspect
import unittest

from scripts import aura_workcapsule_live_artifact_raw_slice_noninterchangeability as target
from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    verify_host_admission_envelope,
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


def live_receipt(**overrides):
    states = {
        "U_HEAD": "PASS",
        "U_ROUTE": "UNKNOWN",
        "U_F2": "UNKNOWN",
        "U_CUSTODY": "UNKNOWN",
        "U_CANARY": "UNKNOWN",
    }
    value = {
        "version": target.PR575_VERSION,
        "live_causal_raw_slice_reproved": True,
        "live_causal_artifact_target_ref": "aura-workcapsule-target-sha256:" + "a" * 64,
        "host_admission_integrity_checked": True,
        "host_admission_reproved_by_child": False,
        "host_admission_producer_authenticated": False,
        "resolved_host_gates_bound_to_live_causal_artifact": True,
        "resolved_host_gate_count": 1,
        "resolved_host_gates": ["U_HEAD"],
        "unknown_host_gates": ["U_ROUTE", "U_F2", "U_CUSTODY", "U_CANARY"],
        "host_gate_states": states,
        "host_observation_set_complete": False,
        "all_host_gates_pass_for_live_causal_artifact": False,
        "causal_post_owner_reproved_from_raw_evidence": True,
        "same_exact_post_source_instance_proven": True,
        "same_exact_raw_target_slice_proven": True,
        "causal_post_closure_receipt_identity": {"kind": "DIGEST", "value": "b" * 64},
        "dependency_key": {"file_id": 17, "relative_path": "src/a.py"},
        "source_generation": 43,
        "full_source_sha256_hex": "c" * 64,
        "full_source_byte_len": 32,
        "target_byte_start": 0,
        "target_byte_end": 32,
        "target_slice_sha256_hex": "d" * 64,
        "selected_target_semantic_handle_digest_hex": "e" * 64,
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


def raw_receipt(**overrides):
    states = {gate: "UNKNOWN" for gate in target.GATES}
    payload = {
        "version": target.PR574_VERSION,
        "raw_slice_contract_owner": "PR566.verify_raw_slice_receipt",
        "causal_host_owner": "PR567.admit_causal_temporal_host_observation_admission",
        "raw_slice_receipt_digest": "f" * 64,
        "raw_slice_exact_current_local_evidence_validated": True,
        "causal_temporal_owner_reproved": True,
        "pre_reentry_receipt_reused_for_post_o10": True,
        "fresh_post_reentry_receipt_substituted": False,
        "host_gate_states": states,
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


class LiveArtifactRawSliceNoninterchangeabilityTests(unittest.TestCase):
    def test_exact_parent_receipts_prove_noninterchangeability(self):
        live = live_receipt()
        raw = raw_receipt()
        self.assertEqual(
            [],
            target.verify_live_artifact_raw_slice_noninterchangeability(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw,
            ),
        )
        out = target.admit_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
        )
        self.assertTrue(out["raw_slice_host_envelope_cross_cast_rejected"])
        self.assertFalse(out["raw_slice_used_as_host_resolution"])
        self.assertFalse(out["proof_artifacts_interchangeable"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_raw_slice_parent_receipt_is_not_a_host_admission_envelope(self):
        self.assertEqual(
            ["MALFORMED_HOST_ADMISSION_ENVELOPE"],
            verify_host_admission_envelope(raw_receipt()),
        )

    def test_resealed_raw_slice_rank_widening_rejects(self):
        raw = raw_receipt()
        raw["raw_slice_used_as_host_resolution"] = True
        raw.pop("receipt_identity")
        raw["receipt_identity"] = {
            "kind": "DIGEST",
            "algorithm_or_provider": "sha256",
            "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
            "scope_profile": target.PR574_VERSION,
            "value": target._sha(raw),
            "schema_version": "DigestOrImmutableIdentityV1-compatible",
        }
        violations = target.verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live_receipt(),
            causal_raw_slice_host_separation_receipt=raw,
        )
        self.assertIn(
            "PR574_CEILING_VIOLATED:raw_slice_used_as_host_resolution",
            violations,
        )

    def test_raw_slice_integrity_tamper_rejects(self):
        raw = raw_receipt()
        raw["raw_slice_receipt_digest"] = "0" * 64
        violations = target.verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live_receipt(),
            causal_raw_slice_host_separation_receipt=raw,
        )
        self.assertIn("PR574_RECEIPT_IDENTITY_MISMATCH", violations)

    def test_live_parent_target_binding_loss_rejects(self):
        live = live_receipt(resolved_host_gates_bound_to_live_causal_artifact=False)
        violations = target.verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw_receipt(),
        )
        self.assertIn(
            "PR575_REQUIRED_PROOF_MISSING:resolved_host_gates_bound_to_live_causal_artifact",
            violations,
        )

    def test_live_parent_authority_widening_rejects(self):
        live = live_receipt()
        live["authority"]["execution_authorized"] = True
        violations = target.verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw_receipt(),
        )
        self.assertIn("PR575_AUTHORITY_NOT_FALSE", violations)

    def test_unknown_fields_fail_closed(self):
        raw = raw_receipt()
        raw["semantic_truth"] = True
        violations = target.verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live_receipt(),
            causal_raw_slice_host_separation_receipt=raw,
        )
        self.assertEqual(["PR574_RAW_RECEIPT_SCHEMA_MISMATCH"], violations)

    def test_public_boundary_is_exactly_two_closed_parent_receipts(self):
        params = set(
            inspect.signature(
                target.verify_live_artifact_raw_slice_noninterchangeability
            ).parameters
        )
        self.assertEqual(
            {
                "live_artifact_host_receipt",
                "causal_raw_slice_host_separation_receipt",
            },
            params,
        )
        for forbidden in (
            "host_observation_resolver",
            "raw_slice_receipt",
            "artifact_target_ref",
            "target_ref",
            "execution_authorized",
            "host_effect_ready",
        ):
            self.assertNotIn(forbidden, params)

    def test_output_identity_is_deterministic(self):
        kwargs = {
            "live_artifact_host_receipt": live_receipt(),
            "causal_raw_slice_host_separation_receipt": raw_receipt(),
        }
        first = target.admit_live_artifact_raw_slice_noninterchangeability(**copy.deepcopy(kwargs))
        second = target.admit_live_artifact_raw_slice_noninterchangeability(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(len(first["receipt_identity"]["value"]), 64)


if __name__ == "__main__":
    unittest.main()
