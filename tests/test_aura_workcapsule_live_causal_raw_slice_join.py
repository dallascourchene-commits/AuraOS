from __future__ import annotations

import copy
import hashlib
import inspect

from scripts.aura_k27_astge_portable_raw_slice_causal_handoff import (
    CANONICALIZATION,
    RAW_SLICE_VERSION,
    SCHEMA,
    canonical_raw_slice_payload_bytes,
)
from scripts.aura_workcapsule_live_causal_raw_slice_join import (
    RAW_PROJECTION_MISMATCH,
    admit_live_causal_raw_slice_join,
    verify_live_causal_raw_slice_join,
)
from tests.test_aura_workcapsule_current_recursive_target_raw_slice_binding import (
    WorkCapsuleCurrentRecursiveTargetRawSliceBindingTests,
)
from tests.test_aura_workcapsule_two_phase_source_bound_closure import (
    WorkCapsuleTwoPhaseSourceBoundClosureTests,
)


class WorkCapsuleLiveCausalRawSliceJoinTests(
    WorkCapsuleCurrentRecursiveTargetRawSliceBindingTests
):
    def setUp(self) -> None:
        super().setUp()
        self.causal = WorkCapsuleTwoPhaseSourceBoundClosureTests(
            "test_two_phase_raw_owner_bound_exact_closed_lifecycle"
        )
        self.causal.setUp()
        self.assertEqual(self.repaired, self.causal.repaired)
        self.assertEqual(
            hashlib.sha256(self.repaired).hexdigest(), self.causal.repaired_sha
        )

    def tearDown(self) -> None:
        self.causal.tearDown()
        super().tearDown()

    def portable_projection(self, raw: dict | None = None) -> dict:
        raw = copy.deepcopy(raw if raw is not None else self.raw_receipt())
        payload = {
            "schema": SCHEMA,
            "version": 1,
            "canonicalization_profile": CANONICALIZATION,
            "raw_slice_version": RAW_SLICE_VERSION,
            "projection_payload_sha256": raw["projection_payload_sha256"],
            "file_id": raw["file_id"],
            "relative_path": raw["relative_path"],
            "source_generation": raw["source_generation"],
            "full_source_sha256_hex": raw["full_source_sha256_hex"],
            "full_source_byte_len": raw["full_source_byte_len"],
            "target_byte_start": raw["target_byte_start"],
            "target_byte_end": raw["target_byte_end"],
            "target_slice_byte_len": raw["target_slice_byte_len"],
            "target_slice_sha256_hex": raw["target_slice_sha256_hex"],
            "selected_target_semantic_handle_digest_hex": raw[
                "selected_target_semantic_handle_digest_hex"
            ],
            "portable_target_bound_to_exact_current_raw_slice": raw[
                "portable_target_bound_to_exact_current_raw_slice"
            ],
            "source_currentness_revalidated_at_materialization": raw[
                "source_currentness_revalidated_at_materialization"
            ],
            "synthetic_record_is_materialization_coordinate_only": raw[
                "synthetic_record_is_materialization_coordinate_only"
            ],
            "storage_node_identity_minted": raw["storage_node_identity_minted"],
            "semantic_handle_carried_from_portable_owner": raw[
                "semantic_handle_carried_from_portable_owner"
            ],
            "semantic_handle_derived_from_raw_slice": raw[
                "semantic_handle_derived_from_raw_slice"
            ],
            "semantic_identity_proven_by_raw_slice": raw[
                "semantic_identity_proven_by_raw_slice"
            ],
            "producer_authenticated": raw["producer_authenticated"],
            "runtime_name_resolution_proven": raw[
                "runtime_name_resolution_proven"
            ],
            "call_graph_proven": raw["call_graph_proven"],
            "semantic_patch_correctness_proven": raw[
                "semantic_patch_correctness_proven"
            ],
            "b_minus_approved": raw["b_minus_approved"],
            "review_authorized": raw["review_authorized"],
            "mutation_authorized": raw["mutation_authorized"],
            "execution_authorized": raw["execution_authorized"],
            "commit_authorized": raw["commit_authorized"],
            "merge_authorized": raw["merge_authorized"],
            "promotion_authorized": raw["promotion_authorized"],
            "provider_effect_authorized": raw["provider_effect_authorized"],
            "public_effect_authorized": raw["public_effect_authorized"],
            "human_authority": raw["human_authority"],
        }
        return {
            "payload": payload,
            "payload_sha256": hashlib.sha256(
                canonical_raw_slice_payload_bytes(payload)
            ).hexdigest(),
        }

    def causal_kwargs(self, *, post_witness=None) -> dict:
        c = self.causal
        return {
            "pre_root": c.pre_root,
            "pre_codemap": c.codemap,
            "pre_anchor_manifest": c.anchors,
            "pre_witness_manifest": c.pre_witness,
            "previous_binding": c.previous,
            "pre_graph_witness": c.graph,
            "post_root": c.post_root,
            "post_codemap": c.codemap,
            "post_anchor_manifest": c.anchors,
            "post_witness_manifest": (
                post_witness if post_witness is not None else c.post_witness
            ),
            "post_graph_witness": c.graph,
        }

    def o38_kwargs(self, *, raw=None, projection=None, post_witness=None) -> dict:
        raw = raw if raw is not None else self.raw_receipt()
        result = self.join_kwargs(raw=raw)
        result["raw_slice_projection"] = (
            projection if projection is not None else self.portable_projection(raw)
        )
        result.update(self.causal_kwargs(post_witness=post_witness))
        return result

    def test_live_recursive_raw_slice_binds_to_exact_causal_post(self) -> None:
        self.assertEqual([], verify_live_causal_raw_slice_join(**self.o38_kwargs()))
        receipt = admit_live_causal_raw_slice_join(**self.o38_kwargs())
        self.assertTrue(receipt["live_recursive_target_raw_slice_reproved"])
        self.assertTrue(receipt["portable_raw_slice_transport_reproved"])
        self.assertTrue(receipt["causal_post_owner_reproved_from_raw_evidence"])
        self.assertTrue(receipt["live_recursive_raw_slice_bound_to_exact_causal_post"])
        self.assertTrue(receipt["same_exact_post_source_instance_proven"])
        self.assertTrue(receipt["same_exact_raw_target_slice_proven"])
        self.assertEqual(43, receipt["source_generation"])
        self.assertEqual(self.causal.repaired_sha, receipt["full_source_sha256_hex"])
        self.assertEqual(
            hashlib.sha256(self.repaired).hexdigest(),
            receipt["target_slice_sha256_hex"],
        )
        self.assertFalse(receipt["semantic_handle_derived_from_raw_slice"])
        self.assertFalse(receipt["semantic_identity_proven_by_raw_slice"])
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_valid_foreign_portable_projection_cannot_replace_live_raw_receipt(self) -> None:
        foreign_raw = self.raw_receipt(target_slice_sha256_hex="cd" * 32)
        foreign_projection = self.portable_projection(foreign_raw)
        violations = verify_live_causal_raw_slice_join(
            **self.o38_kwargs(projection=foreign_projection)
        )
        self.assertIn(RAW_PROJECTION_MISMATCH, violations)

    def test_post_source_drift_breaks_causal_owner_before_live_join(self) -> None:
        (self.causal.post_root / "src/a.py").write_bytes(
            b"def target(x):\n    return x + 4\n"
        )
        violations = verify_live_causal_raw_slice_join(**self.o38_kwargs())
        self.assertTrue(any(item.startswith("CAUSAL_POST_") for item in violations))

    def test_foreign_post_generation_is_not_cross_cast_to_live_raw_slice(self) -> None:
        witness = copy.deepcopy(self.causal.post_witness)
        witness["witnesses"][0]["source_generation"] = 44
        violations = verify_live_causal_raw_slice_join(
            **self.o38_kwargs(post_witness=witness)
        )
        self.assertTrue(any(item.startswith("CAUSAL_POST_") for item in violations))

    def test_public_boundary_has_no_causal_or_source_intermediate_escape_hatch(self) -> None:
        params = set(inspect.signature(verify_live_causal_raw_slice_join).parameters)
        self.assertIn("raw_slice_receipt", params)
        self.assertIn("raw_slice_projection", params)
        self.assertIn("pre_root", params)
        self.assertIn("post_root", params)
        for forbidden in (
            "post_source_witness",
            "closure_receipt",
            "post_closure_receipt",
            "candidate_binding",
            "reentry_receipt",
            "source_observation_receipt",
            "raw_bytes",
            "source_catalog",
            "second_raw_slice_receipt",
            "authority_override",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
