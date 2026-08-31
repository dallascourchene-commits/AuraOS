from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_scoped_canonical_higher_owner_target import (
    CANONICAL_PREFIX,
    SCOPED_PREFIX,
    WORKCAPSULE_FIELDS_MISMATCH,
    admit_scoped_canonical_higher_owner_target,
    verify_scoped_canonical_higher_owner_target,
)
from tests.test_aura_workcapsule_scoped_portable_target_identity import (
    WorkCapsuleScopedPortableTargetIdentityTests,
)


class WorkCapsuleScopedCanonicalHigherOwnerTargetTests(
    WorkCapsuleScopedPortableTargetIdentityTests
):
    def owner_chain_projection(self, *, nested=None, continuous_handle=None, **overrides) -> dict:
        nested_projection = nested if nested is not None else self.projection()
        handle = continuous_handle or nested_projection["payload"][
            "selected_target_semantic_handle_digest_hex"
        ]
        payload = {
            "schema": "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1",
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "canonical_target_projection": nested_projection,
            "continuous_semantic_handle_digest_hex": handle,
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
        return {
            "payload": payload,
            "payload_sha256": hashlib.sha256(
                json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
        }

    def workcapsule_inputs(self) -> dict:
        inputs = self.cross_kwargs()
        inputs.pop("astge_projection")
        return inputs

    def child_kwargs(self, *, scoped=None, owner=None, workcapsule=None) -> dict:
        return {
            "scoped_rebind_inputs": scoped if scoped is not None else self.scoped_inputs(),
            "workcapsule_inputs": workcapsule if workcapsule is not None else self.workcapsule_inputs(),
            "portable_higher_owner_projection": (
                owner if owner is not None else self.owner_chain_projection()
            ),
        }

    def test_exact_scoped_target_is_bound_through_one_canonical_higher_owner_envelope(self) -> None:
        self.assertEqual([], verify_scoped_canonical_higher_owner_target(**self.child_kwargs()))
        receipt = admit_scoped_canonical_higher_owner_target(**self.child_kwargs())
        self.assertTrue(receipt["canonical_higher_owner_owner_chain_verified"])
        self.assertTrue(receipt["same_scoped_post_edit_target_coordinate_proven"])
        self.assertFalse(receipt["caller_portable_target_projection_accepted"])
        self.assertTrue(receipt["caller_post_edit_witness_accepted_by_this_child"])
        self.assertFalse(receipt["post_edit_witness_derivation_claimed"])
        self.assertEqual("ab" * 32, receipt["continuous_semantic_handle_digest_hex"])
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(receipt["producer_authenticated"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_workcapsule_bundle_cannot_smuggle_a_second_target_projection(self) -> None:
        inputs = self.workcapsule_inputs()
        inputs["astge_projection"] = self.projection(source_generation_value=44)
        self.assertEqual(
            [WORKCAPSULE_FIELDS_MISMATCH],
            verify_scoped_canonical_higher_owner_target(
                **self.child_kwargs(workcapsule=inputs)
            ),
        )

    def test_owner_envelope_for_wrong_post_world_fails_before_scoped_join(self) -> None:
        nested = self.projection(source_generation_value=44)
        owner = self.owner_chain_projection(nested=nested)
        violations = verify_scoped_canonical_higher_owner_target(
            **self.child_kwargs(owner=owner)
        )
        self.assertTrue(any(item.startswith(CANONICAL_PREFIX) for item in violations), violations)

    def test_scoped_handle_drift_fails_against_canonical_nested_target(self) -> None:
        scoped = self.scoped_inputs(witness=self.scoped_witness(semantic_handle_digest="cd" * 32))
        violations = verify_scoped_canonical_higher_owner_target(
            **self.child_kwargs(scoped=scoped)
        )
        self.assertTrue(any(item.startswith(SCOPED_PREFIX) for item in violations), violations)

    def test_outer_authority_widening_fails_closed(self) -> None:
        owner = self.owner_chain_projection(commit_authorized=True)
        violations = verify_scoped_canonical_higher_owner_target(
            **self.child_kwargs(owner=owner)
        )
        self.assertTrue(any(item.startswith(CANONICAL_PREFIX) for item in violations), violations)

    def test_public_boundary_has_one_portable_envelope_and_no_target_projection_slot(self) -> None:
        params = set(inspect.signature(verify_scoped_canonical_higher_owner_target).parameters)
        self.assertEqual(
            {"scoped_rebind_inputs", "workcapsule_inputs", "portable_higher_owner_projection"},
            params,
        )
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)
        self.assertNotIn("post_edit_witness", params)


if __name__ == "__main__":
    import unittest

    unittest.main()
