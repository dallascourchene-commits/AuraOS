from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    verify_portable_canonical_target_projection,
)
from scripts.aura_workcapsule_scoped_higher_owner_portable_continuity import (
    NESTED_PAYLOAD_FIELDS,
    OUTER_DIGEST_MISMATCH,
    OUTER_PAYLOAD_FIELDS,
    OWNER_PREFIX,
    PROJECTION_DIGEST_MISMATCH,
    admit_scoped_higher_owner_portable_continuity,
    canonical_portable_higher_owner_payload_bytes,
    verify_portable_higher_owner_projection,
    verify_scoped_higher_owner_portable_continuity,
)
from tests.test_aura_workcapsule_scoped_portable_target_identity import (
    WorkCapsuleScopedPortableTargetIdentityTests,
)


class WorkCapsuleScopedHigherOwnerPortableContinuityTests(
    WorkCapsuleScopedPortableTargetIdentityTests
):
    def owner_projection(self, *, nested=None, payload_overrides=None) -> dict:
        payload = {
            "schema": "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1",
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "canonical_target_projection": copy.deepcopy(nested if nested is not None else self.projection()),
            "continuous_semantic_handle_digest_hex": "ab" * 32,
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
        if payload_overrides:
            payload.update(payload_overrides)
        out = {"payload": payload, "payload_sha256": "0" * 64}
        out["payload_sha256"] = hashlib.sha256(
            canonical_portable_higher_owner_payload_bytes(payload)
        ).hexdigest()
        return out

    def o29_kwargs(self, *, owner=None) -> dict:
        """Build only the O29 public arguments without shadowing inherited fixture helpers."""
        return {
            "scoped_target_inputs": self.joined_kwargs(),
            "higher_owner_projection": owner if owner is not None else self.owner_projection(),
        }

    @staticmethod
    def reseal_nested(projection: dict) -> None:
        payload = projection["payload"]
        ordered = {field: payload[field] for field in NESTED_PAYLOAD_FIELDS}
        projection["payload_sha256"] = hashlib.sha256(
            json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()

    def test_exact_scoped_target_is_same_pr541_higher_owner_target(self) -> None:
        self.assertEqual([], verify_scoped_higher_owner_portable_continuity(**self.o29_kwargs()))
        receipt = admit_scoped_higher_owner_portable_continuity(**self.o29_kwargs())
        self.assertTrue(receipt["same_scoped_target_as_higher_owner_projection_proven"])
        self.assertTrue(receipt["recursive_cross_runtime_canonicalization_proven"])
        self.assertTrue(receipt["same_nested_portable_projection_digest_proven"])
        self.assertTrue(receipt["higher_owner_handle_equals_scoped_target_handle_proven"])
        self.assertFalse(receipt["producer_authenticated"])
        self.assertFalse(receipt["semantic_repair_correctness_proven"])
        self.assertFalse(receipt["reentry_closed"])
        self.assertFalse(any(receipt["authority"].values()))

    def test_nested_member_reorder_with_original_canonical_digest_is_order_insensitive(self) -> None:
        owner = self.owner_projection()
        canonical_outer_digest = owner["payload_sha256"]
        nested = owner["payload"]["canonical_target_projection"]
        nested["payload"] = dict(reversed(list(nested["payload"].items())))
        self.assertEqual([], verify_portable_canonical_target_projection(nested))
        self.assertEqual(canonical_outer_digest, owner["payload_sha256"])
        self.assertEqual([], verify_portable_higher_owner_projection(owner))

    def test_nested_member_reorder_cannot_mint_python_order_dependent_outer_digest(self) -> None:
        owner = self.owner_projection()
        nested = owner["payload"]["canonical_target_projection"]
        nested["payload"] = dict(reversed(list(nested["payload"].items())))
        self.assertEqual([], verify_portable_canonical_target_projection(nested))
        caller_order_outer = {field: owner["payload"][field] for field in OUTER_PAYLOAD_FIELDS}
        buggy_digest = hashlib.sha256(
            json.dumps(caller_order_outer, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(owner["payload_sha256"], buggy_digest)
        owner["payload_sha256"] = buggy_digest
        self.assertIn(OUTER_DIGEST_MISMATCH, verify_portable_higher_owner_projection(owner))
        self.assertIn(
            OWNER_PREFIX + OUTER_DIGEST_MISMATCH,
            verify_scoped_higher_owner_portable_continuity(**self.o29_kwargs(owner=owner)),
        )

    def test_independently_valid_nested_projection_from_different_source_generation_rejects(self) -> None:
        nested = copy.deepcopy(self.projection())
        nested["payload"]["source_generation_value"] = 44
        self.reseal_nested(nested)
        self.assertEqual([], verify_portable_canonical_target_projection(nested))
        owner = self.owner_projection(nested=nested)
        violations = verify_scoped_higher_owner_portable_continuity(**self.o29_kwargs(owner=owner))
        self.assertIn(PROJECTION_DIGEST_MISMATCH, violations)

    def test_outer_continuous_handle_drift_rejects_even_after_reseal(self) -> None:
        owner = self.owner_projection(payload_overrides={"continuous_semantic_handle_digest_hex": "cd" * 32})
        self.assertIn("OUTER_HIGHER_OWNER_HANDLE_MISMATCH", verify_portable_higher_owner_projection(owner))

    def test_outer_authority_widening_rejects_even_after_reseal(self) -> None:
        owner = self.owner_projection(payload_overrides={"commit_authorized": True})
        self.assertIn("OUTER_CEILING_VIOLATED:commit_authorized", verify_portable_higher_owner_projection(owner))

    def test_unknown_outer_field_fails_closed(self) -> None:
        owner = self.owner_projection()
        owner["payload"]["future_authority"] = False
        self.assertEqual(["MALFORMED_OUTER_PAYLOAD"], verify_portable_higher_owner_projection(owner))

    def test_integer_truthiness_cannot_impersonate_outer_version(self) -> None:
        owner = self.owner_projection()
        owner["payload"]["version"] = True
        # Recompute directly would otherwise exploit Python True == 1; exact type must reject first.
        self.assertIn("OUTER_SCHEMA_VERSION_MISMATCH", verify_portable_higher_owner_projection(owner))

    def test_public_boundary_has_no_second_target_or_raw_owner_escape_hatch(self) -> None:
        params = inspect.signature(verify_scoped_higher_owner_portable_continuity).parameters
        self.assertEqual({"scoped_target_inputs", "higher_owner_projection"}, set(params))
        for forbidden in ("post_edit_witness", "astge_projection", "reduced_owner_receipt", "candidate_binding"):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
