from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

from scripts.aura_workcapsule_observation_bound_closure import (
    HOLD,
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_post_repair_portable_higher_owner_continuity import (
    OWNER_CHAIN_HANDLE_MISMATCH,
    OWNER_CHAIN_PREFIX,
    OWNER_CHAIN_SCHEMA,
    POST_SOURCE_PREFIX,
    admit_post_repair_portable_higher_owner_continuity,
    verify_portable_higher_owner_chain,
    verify_post_repair_portable_higher_owner_continuity,
)
from tests.test_aura_workcapsule_post_repair_source_projection_continuity import (
    WorkCapsulePostRepairSourceProjectionContinuityTests,
    identity,
)


class WorkCapsulePostRepairPortableHigherOwnerContinuityTests(
    WorkCapsulePostRepairSourceProjectionContinuityTests
):
    def higher_owner_projection(self, *, nested=None, **overrides) -> dict:
        nested_projection = copy.deepcopy(nested if nested is not None else self.projection())
        payload = {
            "schema": OWNER_CHAIN_SCHEMA,
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "canonical_target_projection": nested_projection,
            "continuous_semantic_handle_digest_hex": nested_projection["payload"][
                "selected_target_semantic_handle_digest_hex"
            ],
            "outer_constructor_reproved_by_inner_owner": True,
            "one_canonical_post_edit_consequence": True,
            "higher_owner_semantic_handle_continuity_proven": True,
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
        payload.update(overrides)
        digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return {"payload": payload, "payload_sha256": digest}

    @staticmethod
    def reseal_nested(projection: dict) -> dict:
        projection = copy.deepcopy(projection)
        projection["payload_sha256"] = hashlib.sha256(
            json.dumps(
                projection["payload"], separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        return projection

    def child_kwargs(self, *, outer=None, post_outer=None, post_graph=None) -> dict:
        kwargs = self.kwargs(post_outer=post_outer, post_graph=post_graph)
        kwargs["higher_owner_projection"] = (
            outer if outer is not None else self.higher_owner_projection()
        )
        return kwargs

    def test_exact_outer_chain_closes_on_same_nested_post_source_projection(self) -> None:
        outer = self.higher_owner_projection()
        self.assertEqual([], verify_portable_higher_owner_chain(outer))
        self.assertEqual(
            [], verify_post_repair_portable_higher_owner_continuity(**self.child_kwargs(outer=outer))
        )
        admitted = admit_post_repair_portable_higher_owner_continuity(
            **self.child_kwargs(outer=outer)
        )
        self.assertTrue(admitted["post_repair_source_instance_continuity_proven"])
        self.assertTrue(admitted["portable_higher_owner_chain_verified"])
        self.assertTrue(admitted["same_nested_canonical_target_projection_proven"])
        self.assertTrue(admitted["higher_owner_semantic_handle_continuity_proven"])
        self.assertEqual(
            outer["payload"]["canonical_target_projection"]["payload_sha256"],
            admitted["nested_canonical_target_projection_payload_sha256"],
        )
        self.assertFalse(admitted["projection_producer_authenticated"])
        self.assertFalse(admitted["higher_owner_producer_authenticated"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_resealed_outer_handle_substitution_fails_closed(self) -> None:
        outer = self.higher_owner_projection(continuous_semantic_handle_digest_hex="cd" * 32)
        violations = verify_portable_higher_owner_chain(outer)
        self.assertIn(OWNER_CHAIN_HANDLE_MISMATCH, violations)

    def test_outer_authority_elevation_fails_even_when_digest_is_resealed(self) -> None:
        outer = self.higher_owner_projection(commit_authorized=True)
        violations = verify_post_repair_portable_higher_owner_continuity(
            **self.child_kwargs(outer=outer)
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX + "OWNER_CHAIN_CEILING_VIOLATED:commit_authorized",
            violations,
        )

    def test_locally_valid_outer_with_wrong_nested_source_generation_fails_cross_runtime(self) -> None:
        nested = self.projection(source_generation_value=44)
        outer = self.higher_owner_projection(nested=nested)
        self.assertEqual([], verify_portable_higher_owner_chain(outer))
        violations = verify_post_repair_portable_higher_owner_continuity(
            **self.child_kwargs(outer=outer)
        )
        self.assertIn(
            POST_SOURCE_PREFIX + "POST_SOURCE_GENERATION_MISMATCH",
            violations,
        )

    def test_nested_tamper_without_nested_reseal_is_not_saved_by_valid_outer_digest(self) -> None:
        nested = self.projection()
        nested["payload"]["definition_name"] = "tampered"
        outer = self.higher_owner_projection(nested=nested)
        violations = verify_portable_higher_owner_chain(outer)
        self.assertTrue(any(item.startswith("NESTED_") for item in violations))

    def test_unknown_outer_field_is_rejected_even_with_recomputed_digest(self) -> None:
        outer = self.higher_owner_projection()
        outer["payload"]["parallel_truth_plane"] = True
        outer["payload_sha256"] = hashlib.sha256(
            json.dumps(
                outer["payload"], separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            ["OWNER_CHAIN_FIELDS_MISMATCH"], verify_portable_higher_owner_chain(outer)
        )

    def test_post_hold_cannot_be_promoted_by_matching_higher_owner_projection(self) -> None:
        graph8 = copy.deepcopy(self.graph)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-o29-8")
        graph8["witness_ref"] = "GRAPH:O29:8:CURRENT"
        outer_receipt = compile_observation_bound_reentry_closure(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph8,
        )
        self.assertEqual(HOLD, outer_receipt["closure_status"])
        violations = verify_post_repair_portable_higher_owner_continuity(
            **self.child_kwargs(post_outer=outer_receipt, post_graph=graph8)
        )
        self.assertTrue(any(item.startswith(POST_SOURCE_PREFIX) for item in violations))

    def test_public_boundary_has_one_outer_projection_and_no_second_nested_escape_hatch(self) -> None:
        params = inspect.signature(
            verify_post_repair_portable_higher_owner_continuity
        ).parameters
        self.assertIn("higher_owner_projection", params)
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)
        self.assertNotIn("projection_owner_receipt", params)

        source = Path(
            "scripts/aura_workcapsule_post_repair_portable_higher_owner_continuity.py"
        ).read_text()
        self.assertIn("aura_workcapsule_post_source_portable_higher_owner_continuity", source)
        self.assertNotIn("verify_post_repair_source_projection_continuity", source)
        self.assertNotIn("compile_source_reentry_observations", source)
        self.assertNotIn("compile_observation_bound_reentry_closure", source)
        self.assertNotIn("derive_post_reentry_candidate", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
