from __future__ import annotations

import copy
import hashlib
import inspect

from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    DEPENDENCY_MISMATCH,
    PROJECTION_DIGEST_MISMATCH,
    RAW_PREFIX,
    SOURCE_GENERATION_MISMATCH,
    TARGET_HANDLE_MISMATCH,
    TARGET_SPAN_MISMATCH,
    admit_current_recursive_target_raw_slice_binding,
    verify_current_recursive_target_raw_slice_binding,
)
from tests.test_aura_workcapsule_scoped_higher_owner_portable_continuity import (
    WorkCapsuleScopedHigherOwnerPortableContinuityTests,
)


class WorkCapsuleCurrentRecursiveTargetRawSliceBindingTests(
    WorkCapsuleScopedHigherOwnerPortableContinuityTests
):
    def raw_receipt(self, **overrides) -> dict:
        owner = self.owner_projection()
        nested = owner["payload"]["canonical_target_projection"]
        payload = nested["payload"]
        receipt = {
            "version": "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1",
            "projection_payload_sha256": nested["payload_sha256"],
            "file_id": payload["file_id"],
            "relative_path": payload["relative_path"],
            "source_generation": payload["source_generation_value"],
            "full_source_sha256_hex": payload["source_sha256_hex"],
            "full_source_byte_len": payload["source_byte_len"],
            "target_byte_start": payload["selected_target_byte_start"],
            "target_byte_end": payload["selected_target_byte_end"],
            "target_slice_byte_len": payload["selected_target_byte_end"]
            - payload["selected_target_byte_start"],
            "target_slice_sha256_hex": hashlib.sha256(
                self.repaired[
                    payload["selected_target_byte_start"] : payload["selected_target_byte_end"]
                ]
            ).hexdigest(),
            "selected_target_semantic_handle_digest_hex": payload[
                "selected_target_semantic_handle_digest_hex"
            ],
            "portable_target_bound_to_exact_current_raw_slice": True,
            "source_currentness_revalidated_at_materialization": True,
            "synthetic_record_is_materialization_coordinate_only": True,
            "storage_node_identity_minted": False,
            "semantic_handle_carried_from_portable_owner": True,
            "semantic_handle_derived_from_raw_slice": False,
            "semantic_identity_proven_by_raw_slice": False,
            "producer_authenticated": False,
            "runtime_name_resolution_proven": False,
            "call_graph_proven": False,
            "semantic_patch_correctness_proven": False,
            "b_minus_approved": False,
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
        receipt.update(overrides)
        return receipt

    def join_kwargs(self, *, owner=None, raw=None) -> dict:
        return {
            "scoped_target_inputs": self.joined_kwargs(),
            "higher_owner_projection": owner if owner is not None else self.owner_projection(),
            "raw_slice_receipt": raw if raw is not None else self.raw_receipt(),
        }

    def test_current_recursive_target_binds_to_exact_current_raw_slice(self) -> None:
        self.assertEqual([], verify_current_recursive_target_raw_slice_binding(**self.join_kwargs()))
        receipt = admit_current_recursive_target_raw_slice_binding(**self.join_kwargs())
        self.assertTrue(receipt["current_recursive_target_reproved"])
        self.assertTrue(receipt["exact_current_raw_slice_evidence_consumed"])
        self.assertTrue(receipt["same_portable_projection_payload_proven"])
        self.assertTrue(receipt["same_source_instance_proven"])
        self.assertTrue(receipt["same_exact_target_span_proven"])
        self.assertTrue(receipt["opaque_semantic_handle_continuity_proven"])
        self.assertEqual(hashlib.sha256(self.repaired).hexdigest(), receipt["target_slice_sha256_hex"])
        self.assertFalse(receipt["raw_slice_receipt_producer_authenticated"])
        self.assertFalse(receipt["semantic_handle_derived_from_raw_slice"])
        self.assertFalse(receipt["semantic_identity_proven_by_raw_slice"])
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_independently_valid_raw_receipt_wrong_projection_digest_rejects(self) -> None:
        raw = self.raw_receipt(projection_payload_sha256="cd" * 32)
        self.assertIn(PROJECTION_DIGEST_MISMATCH, verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)))

    def test_raw_source_generation_drift_rejects(self) -> None:
        raw = self.raw_receipt(source_generation=44)
        self.assertIn(SOURCE_GENERATION_MISMATCH, verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)))

    def test_raw_dependency_drift_rejects(self) -> None:
        raw = self.raw_receipt(relative_path="src/other.py")
        self.assertIn(DEPENDENCY_MISMATCH, verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)))

    def test_raw_span_drift_rejects(self) -> None:
        raw = self.raw_receipt(target_byte_start=1, target_slice_byte_len=len(self.repaired) - 1)
        self.assertIn(TARGET_SPAN_MISMATCH, verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)))

    def test_raw_handle_drift_rejects(self) -> None:
        raw = self.raw_receipt(selected_target_semantic_handle_digest_hex="cd" * 32)
        self.assertIn(TARGET_HANDLE_MISMATCH, verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)))

    def test_raw_receipt_cannot_claim_handle_derivation_or_producer_trust(self) -> None:
        handle = self.raw_receipt(semantic_handle_derived_from_raw_slice=True)
        producer = self.raw_receipt(producer_authenticated=True)
        self.assertIn(
            RAW_PREFIX + "CEILING_VIOLATED:semantic_handle_derived_from_raw_slice",
            verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=handle)),
        )
        self.assertIn(
            RAW_PREFIX + "CEILING_VIOLATED:producer_authenticated",
            verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=producer)),
        )

    def test_unknown_raw_receipt_field_fails_closed(self) -> None:
        raw = self.raw_receipt()
        raw["semantic_identity"] = "invented"
        self.assertEqual(
            [RAW_PREFIX + "MALFORMED_RECEIPT"],
            verify_current_recursive_target_raw_slice_binding(**self.join_kwargs(raw=raw)),
        )

    def test_public_boundary_has_no_raw_bytes_or_source_catalog_escape_hatch(self) -> None:
        params = inspect.signature(verify_current_recursive_target_raw_slice_binding).parameters
        self.assertEqual(
            {"scoped_target_inputs", "higher_owner_projection", "raw_slice_receipt"},
            set(params),
        )
        for forbidden in (
            "raw_bytes",
            "source_catalog",
            "post_edit_witness",
            "astge_projection",
            "semantic_handle",
            "producer_trusted",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
