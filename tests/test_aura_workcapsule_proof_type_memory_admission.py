from __future__ import annotations

import copy
import inspect
import unittest

from scripts import aura_workcapsule_proof_type_memory_admission as target
from tests.test_aura_workcapsule_live_artifact_raw_slice_noninterchangeability import (
    live_receipt,
    raw_receipt,
)


class WorkCapsuleProofTypeMemoryAdmissionTests(unittest.TestCase):
    def kwargs(self):
        return {
            "live_artifact_host_receipt": live_receipt(),
            "causal_raw_slice_host_separation_receipt": raw_receipt(),
        }

    def test_projection_derives_two_distinct_typed_nodes_from_pr580(self):
        out = target.project_pr580_proof_types_to_memory(**self.kwargs())
        host = out["live_host_memory_node"]
        raw = out["raw_slice_memory_node"]
        self.assertTrue(out["proof_types_derived_from_pr580_relation"])
        self.assertTrue(out["live_host_and_raw_slice_artifacts_distinct"])
        self.assertNotEqual(host["artifact_ref"], raw["artifact_ref"])
        self.assertEqual(target.HOST_EVIDENCE_TYPE, host["evidence_type"])
        self.assertEqual(target.RAW_EVIDENCE_TYPE, raw["evidence_type"])
        self.assertEqual(["retrieval", "host-currentness"], host["allowed_use_classes"])
        self.assertEqual(["retrieval"], raw["allowed_use_classes"])
        self.assertFalse(out["proof_artifacts_interchangeable"])
        self.assertFalse(out["raw_slice_used_as_host_resolution"])

    def test_retrieval_admits_both_but_host_currentness_admits_host_only(self):
        out = target.admit_pr580_proof_type_memory_views(**self.kwargs())
        retrieval = out["retrieval_admission"]
        currentness = out["host_currentness_admission"]
        self.assertEqual(2, len(retrieval["eligible_artifact_refs"]))
        self.assertEqual(1, len(currentness["eligible_artifact_refs"]))
        self.assertTrue(out["retrieval_admits_live_host_evidence"])
        self.assertTrue(out["retrieval_admits_raw_slice_evidence"])
        self.assertTrue(out["host_currentness_admits_live_host_evidence"])
        self.assertFalse(out["host_currentness_admits_raw_slice_evidence"])
        self.assertEqual(
            ["USE_CLASS_NOT_ALLOWED", "EVIDENCE_TYPE_NOT_ACCEPTED"],
            out["raw_slice_host_currentness_rejection_reasons"],
        )

    def test_generation_is_pinned_and_currentness_claim_is_bounded(self):
        out = target.project_pr580_proof_types_to_memory(**self.kwargs())
        for key in ("live_host_memory_node", "raw_slice_memory_node"):
            node = out[key]
            self.assertTrue(node["current"])
            self.assertTrue(node["generation_ref"].startswith(
                "github:commit:" + target.PR580_GENERATION + ":"
            ))
        self.assertEqual(target.PR580_GENERATION, out["pr580_generation"])
        self.assertEqual(target.PR581_GENERATION, out["pr581_generation"])
        self.assertTrue(out["generation_bound_currentness_only"])
        self.assertFalse(out["ambient_repository_currentness_reproved"])

    def test_raw_slice_rank_widening_rejects_before_memory_projection(self):
        raw = raw_receipt()
        raw["raw_slice_used_as_host_resolution"] = True
        raw.pop("receipt_identity")
        from scripts import aura_workcapsule_live_artifact_raw_slice_noninterchangeability as pr580
        raw["receipt_identity"] = {
            "kind": "DIGEST",
            "algorithm_or_provider": "sha256",
            "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
            "scope_profile": pr580.PR574_VERSION,
            "value": pr580._sha(raw),
            "schema_version": "DigestOrImmutableIdentityV1-compatible",
        }
        with self.assertRaisesRegex(ValueError, "raw_slice_used_as_host_resolution"):
            target.project_pr580_proof_types_to_memory(
                live_artifact_host_receipt=live_receipt(),
                causal_raw_slice_host_separation_receipt=raw,
            )

    def test_live_host_authority_widening_rejects_before_memory_projection(self):
        live = live_receipt()
        live["authority"]["execution_authorized"] = True
        with self.assertRaisesRegex(ValueError, "PR575_AUTHORITY_NOT_FALSE"):
            target.project_pr580_proof_types_to_memory(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw_receipt(),
            )

    def test_pr581_outputs_remain_rank_neutral_and_nonauthorizing(self):
        out = target.admit_pr580_proof_type_memory_views(**self.kwargs())
        for admission_key in ("retrieval_admission", "host_currentness_admission"):
            admission = out[admission_key]
            self.assertFalse(admission["corroboration_rank_transition_performed"])
            self.assertFalse(admission["semantic_truth_proven"])
            self.assertFalse(admission["producer_authentication_proven"])
            self.assertFalse(admission["effect_authority_proven"])
            self.assertFalse(admission["native_private_transformer_kv_accessed"])
        self.assertFalse(out["corroboration_or_memory_count_grants_host_rank"])
        self.assertFalse(out["producer_authenticated"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])

    def test_public_boundary_has_no_type_context_currentness_or_rank_override(self):
        for function in (
            target.project_pr580_proof_types_to_memory,
            target.admit_pr580_proof_type_memory_views,
        ):
            params = set(inspect.signature(function).parameters)
            self.assertEqual(
                {
                    "live_artifact_host_receipt",
                    "causal_raw_slice_host_separation_receipt",
                },
                params,
            )
            for forbidden in (
                "evidence_type",
                "use_class",
                "context",
                "current",
                "generation_ref",
                "host_rank",
                "host_resolver",
                "authority",
            ):
                self.assertNotIn(forbidden, params)

    def test_projection_and_views_are_deterministic(self):
        kwargs = self.kwargs()
        first = target.admit_pr580_proof_type_memory_views(**copy.deepcopy(kwargs))
        second = target.admit_pr580_proof_type_memory_views(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
