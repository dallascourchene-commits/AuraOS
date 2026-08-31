from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

from scripts.aura_workcapsule_post_source_portable_higher_owner_continuity import (
    OWNER_CHAIN_HANDLE_MISMATCH,
    OWNER_CHAIN_PREFIX,
    SOURCE_CONTINUITY_PREFIX,
    admit_post_source_portable_higher_owner_continuity,
    verify_portable_higher_owner_owner_chain_projection,
    verify_post_source_portable_higher_owner_continuity,
)
from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    POST_SOURCE_BODY_SHA_MISMATCH,
    POST_SOURCE_GENERATION_MISMATCH,
)
from tests.test_aura_workcapsule_post_repair_source_projection_continuity import (
    WorkCapsulePostRepairSourceProjectionContinuityTests,
)


class WorkCapsulePostSourcePortableHigherOwnerContinuityTests(
    WorkCapsulePostRepairSourceProjectionContinuityTests
):
    def owner_chain_projection(
        self,
        *,
        nested_projection=None,
        continuous_handle: str | None = None,
        **overrides,
    ) -> dict:
        nested = nested_projection if nested_projection is not None else self.projection()
        handle = (
            continuous_handle
            if continuous_handle is not None
            else nested["payload"]["selected_target_semantic_handle_digest_hex"]
        )
        payload = {
            "schema": "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1",
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "canonical_target_projection": nested,
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
        digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return {"payload": payload, "payload_sha256": digest}

    def child_kwargs(self, *, owner_projection=None, post_outer=None, post_graph=None) -> dict:
        out = self.kwargs(post_outer=post_outer, post_graph=post_graph)
        out["portable_higher_owner_projection"] = (
            owner_projection if owner_projection is not None else self.owner_chain_projection()
        )
        return out

    def test_exact_portable_higher_owner_target_binds_to_exact_post_source(self) -> None:
        owner = self.owner_chain_projection()
        self.assertEqual([], verify_portable_higher_owner_owner_chain_projection(owner))
        self.assertEqual([], verify_post_source_portable_higher_owner_continuity(**self.child_kwargs(owner_projection=owner)))
        admitted = admit_post_source_portable_higher_owner_continuity(
            **self.child_kwargs(owner_projection=owner)
        )
        self.assertTrue(admitted["source_instance_continuity_proven"])
        self.assertTrue(admitted["portable_higher_owner_owner_chain_verified"])
        self.assertTrue(admitted["higher_owner_semantic_handle_continuity_proven"])
        self.assertEqual("CLOSED", admitted["post_closure_status"])
        self.assertEqual("ab" * 32, admitted["continuous_semantic_handle_digest_hex"])
        self.assertFalse(admitted["projection_producer_authenticated"])
        self.assertFalse(admitted["source_currentness_minted_by_child"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_locally_valid_outer_handle_divergence_is_rejected(self) -> None:
        owner = self.owner_chain_projection(continuous_handle="cd" * 32)
        violations = verify_portable_higher_owner_owner_chain_projection(owner)
        self.assertIn(OWNER_CHAIN_HANDLE_MISMATCH, violations)
        child = verify_post_source_portable_higher_owner_continuity(
            **self.child_kwargs(owner_projection=owner)
        )
        self.assertIn(OWNER_CHAIN_PREFIX + OWNER_CHAIN_HANDLE_MISMATCH, child)

    def test_nested_projection_can_be_owner_chain_valid_but_wrong_post_world(self) -> None:
        nested = self.projection(source_generation_value=44)
        owner = self.owner_chain_projection(nested_projection=nested)
        self.assertEqual([], verify_portable_higher_owner_owner_chain_projection(owner))
        violations = verify_post_source_portable_higher_owner_continuity(
            **self.child_kwargs(owner_projection=owner)
        )
        self.assertIn(
            SOURCE_CONTINUITY_PREFIX + POST_SOURCE_GENERATION_MISMATCH,
            violations,
        )

    def test_locally_valid_owner_chain_for_wrong_post_body_is_rejected(self) -> None:
        nested = self.projection(source_sha256_hex="11" * 32)
        owner = self.owner_chain_projection(nested_projection=nested)
        self.assertEqual([], verify_portable_higher_owner_owner_chain_projection(owner))
        violations = verify_post_source_portable_higher_owner_continuity(
            **self.child_kwargs(owner_projection=owner)
        )
        self.assertIn(
            SOURCE_CONTINUITY_PREFIX + POST_SOURCE_BODY_SHA_MISMATCH,
            violations,
        )

    def test_nested_projection_tamper_is_not_hidden_by_outer_reseal(self) -> None:
        owner = self.owner_chain_projection()
        owner["payload"]["canonical_target_projection"]["payload"]["definition_name"] = "tampered"
        owner["payload_sha256"] = hashlib.sha256(
            json.dumps(owner["payload"], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        violations = verify_portable_higher_owner_owner_chain_projection(owner)
        self.assertIn("NESTED_PROJECTION_PAYLOAD_DIGEST_MISMATCH", violations)

    def test_outer_authority_widening_is_rejected_even_when_resealed(self) -> None:
        owner = self.owner_chain_projection(commit_authorized=True)
        violations = verify_portable_higher_owner_owner_chain_projection(owner)
        self.assertIn("OWNER_CHAIN_CEILING_VIOLATED:commit_authorized", violations)

    def test_outer_payload_digest_tamper_is_rejected(self) -> None:
        owner = self.owner_chain_projection()
        owner["payload_sha256"] = "00" * 32
        violations = verify_portable_higher_owner_owner_chain_projection(owner)
        self.assertIn("OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH", violations)

    def test_unknown_outer_field_is_rejected(self) -> None:
        owner = self.owner_chain_projection()
        owner["payload"]["semantic_truth_proven"] = True
        owner["payload_sha256"] = hashlib.sha256(
            json.dumps(owner["payload"], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(
            ["OWNER_CHAIN_SCHEMA_FIELDS_MISMATCH"],
            verify_portable_higher_owner_owner_chain_projection(owner),
        )

    def test_false_owner_chain_proof_flag_is_rejected(self) -> None:
        owner = self.owner_chain_projection(one_canonical_post_edit_consequence=False)
        violations = verify_portable_higher_owner_owner_chain_projection(owner)
        self.assertIn(
            "OWNER_CHAIN_PROOF_FLAG_MISSING:one_canonical_post_edit_consequence",
            violations,
        )

    def test_public_boundary_accepts_no_raw_astge_or_lower_replay_escape_hatch(self) -> None:
        params = inspect.signature(verify_post_source_portable_higher_owner_continuity).parameters
        self.assertIn("portable_higher_owner_projection", params)
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)
        for forbidden in (
            "candidate_binding",
            "observed_source_witnesses",
            "source_observation_receipt",
            "post_edit_witness",
            "reduced_owner_chain",
        ):
            self.assertNotIn(forbidden, params)

        source = Path(
            "scripts/aura_workcapsule_post_source_portable_higher_owner_continuity.py"
        ).read_text()
        self.assertIn("verify_post_repair_source_projection_continuity", source)
        self.assertIn("verify_portable_canonical_target_projection", source)
        self.assertNotIn("compile_source_reentry_observations", source)
        self.assertNotIn("derive_post_reentry_candidate", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
