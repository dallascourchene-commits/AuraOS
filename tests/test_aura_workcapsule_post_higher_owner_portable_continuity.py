from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_post_higher_owner_portable_continuity import (
    OWNER_PREFIX,
    SOURCE_PREFIX,
    admit_post_higher_owner_portable_continuity,
    verify_portable_higher_owner_projection,
    verify_post_higher_owner_portable_continuity,
)
from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    POST_SOURCE_BODY_SHA_MISMATCH,
)
from tests.test_aura_workcapsule_post_repair_source_projection_continuity import (
    WorkCapsulePostRepairSourceProjectionContinuityTests,
)


OUTER_FIELDS = (
    "schema",
    "version",
    "canonicalization_profile",
    "canonical_target_projection",
    "continuous_semantic_handle_digest_hex",
    "outer_constructor_reproved_by_inner_owner",
    "one_canonical_post_edit_consequence",
    "higher_owner_semantic_handle_continuity_proven",
    "producer_authenticated",
    "runtime_name_resolution_proven",
    "call_graph_proven",
    "semantic_patch_correctness_proven",
    "b_minus_approved",
    "review_authorized",
    "mutation_authorized",
    "execution_authorized",
    "commit_authorized",
    "merge_authorized",
    "promotion_authorized",
    "provider_effect_authorized",
    "public_effect_authorized",
    "human_authority",
)


class WorkCapsulePostHigherOwnerPortableContinuityTests(
    WorkCapsulePostRepairSourceProjectionContinuityTests
):
    def higher_owner(self, *, nested=None, **overrides) -> dict:
        nested = copy.deepcopy(nested if nested is not None else self.projection())
        payload = {
            "schema": "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1",
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "canonical_target_projection": nested,
            "continuous_semantic_handle_digest_hex": nested["payload"][
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
        ordered = {field: payload[field] for field in OUTER_FIELDS}
        digest = hashlib.sha256(
            json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return {"payload": payload, "payload_sha256": digest}

    def owner_kwargs(self, *, owner=None) -> dict:
        out = self.kwargs()
        out["higher_owner_projection"] = owner if owner is not None else self.higher_owner()
        return out

    def test_exact_shared_nested_projection_binds_closed_post_source_and_higher_owner(self) -> None:
        owner = self.higher_owner()
        self.assertEqual([], verify_portable_higher_owner_projection(owner))
        self.assertEqual([], verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner)))
        admitted = admit_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertTrue(admitted["post_source_instance_continuity_proven"])
        self.assertTrue(admitted["portable_higher_owner_owner_chain_verified"])
        self.assertTrue(admitted["same_nested_canonical_target_projection_bound"])
        self.assertTrue(admitted["higher_owner_semantic_handle_continuity_proven"])
        self.assertEqual("CLOSED", admitted["post_closure_status"])
        self.assertFalse(admitted["projection_producer_authenticated"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_locally_valid_higher_owner_envelope_for_wrong_post_body_fails_source_instance(self) -> None:
        nested = self.projection(source_sha256_hex="11" * 32)
        owner = self.higher_owner(nested=nested)
        self.assertEqual([], verify_portable_higher_owner_projection(owner))
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(SOURCE_PREFIX + POST_SOURCE_BODY_SHA_MISMATCH, violations)

    def test_continuous_handle_divergence_is_rejected_even_when_outer_digest_is_resealed(self) -> None:
        owner = self.higher_owner(continuous_semantic_handle_digest_hex="cd" * 32)
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(OWNER_PREFIX + "HIGHER_OWNER_CONTINUOUS_HANDLE_MISMATCH", violations)

    def test_outer_authority_widening_is_rejected(self) -> None:
        owner = self.higher_owner(commit_authorized=True)
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(OWNER_PREFIX + "HIGHER_OWNER_CEILING_VIOLATED:commit_authorized", violations)

    def test_outer_payload_digest_tamper_is_rejected(self) -> None:
        owner = self.higher_owner()
        owner["payload_sha256"] = "00" * 32
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(OWNER_PREFIX + "HIGHER_OWNER_PAYLOAD_DIGEST_MISMATCH", violations)

    def test_unknown_outer_field_is_rejected(self) -> None:
        owner = self.higher_owner()
        owner["payload"]["new_authority_plane"] = False
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(OWNER_PREFIX + "HIGHER_OWNER_SCHEMA_FIELDS_MISMATCH", violations)

    def test_missing_owner_reproof_is_rejected(self) -> None:
        owner = self.higher_owner(outer_constructor_reproved_by_inner_owner=False)
        violations = verify_post_higher_owner_portable_continuity(**self.owner_kwargs(owner=owner))
        self.assertIn(
            OWNER_PREFIX
            + "HIGHER_OWNER_REQUIRED_CLAIM_FALSE:outer_constructor_reproved_by_inner_owner",
            violations,
        )

    def test_public_boundary_has_no_second_projection_or_lower_owner_escape_hatch(self) -> None:
        params = inspect.signature(verify_post_higher_owner_portable_continuity).parameters
        self.assertIn("higher_owner_projection", params)
        for forbidden in (
            "astge_projection",
            "canonical_target_projection",
            "projection_owner_receipt",
            "post_edit_witness",
            "candidate_binding",
            "observed_source_witnesses",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
