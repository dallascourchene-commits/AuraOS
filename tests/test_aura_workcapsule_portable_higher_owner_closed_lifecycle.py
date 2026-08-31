from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_observation_bound_closure import (
    HOLD,
    compile_observation_bound_reentry_closure,
)
from scripts.aura_workcapsule_portable_higher_owner_closed_lifecycle import (
    OWNER_CHAIN_PREFIX,
    SOURCE_CONTINUITY_PREFIX,
    admit_portable_higher_owner_chain_inside_closed_lifecycle,
    verify_portable_higher_owner_chain_inside_closed_lifecycle,
    verify_portable_higher_owner_chain_projection,
)
from tests.test_aura_workcapsule_post_repair_source_projection_continuity import (
    WorkCapsulePostRepairSourceProjectionContinuityTests,
    identity,
)


class WorkCapsulePortableHigherOwnerClosedLifecycleTests(
    WorkCapsulePostRepairSourceProjectionContinuityTests
):
    def owner_chain(self, *, projection=None, **overrides) -> dict:
        nested = projection if projection is not None else self.projection()
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
        digest = hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return {"payload": payload, "payload_sha256": digest}

    def lifecycle_kwargs(self, *, post_outer=None, post_graph=None) -> dict:
        return self.kwargs(post_outer=post_outer, post_graph=post_graph)

    def test_exact_outer_chain_is_the_only_astge_transport_used_by_closed_lifecycle(self) -> None:
        chain = self.owner_chain()
        self.assertEqual([], verify_portable_higher_owner_chain_projection(chain))
        self.assertEqual(
            [],
            verify_portable_higher_owner_chain_inside_closed_lifecycle(
                portable_owner_chain_projection=chain,
                **self.lifecycle_kwargs(),
            ),
        )
        admitted = admit_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertEqual("CLOSED", admitted["post_closure_status"])
        self.assertTrue(admitted["source_instance_continuity_proven"])
        self.assertTrue(admitted["portable_higher_owner_chain_verified"])
        self.assertTrue(admitted["same_nested_projection_used_by_lifecycle"])
        self.assertTrue(
            admitted["canonical_target_handle_continuity_inside_closed_lifecycle_proven"]
        )
        self.assertFalse(admitted["caller_lower_astge_projection_accepted"])
        self.assertFalse(admitted["projection_producer_authenticated"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_resealed_outer_handle_divergence_fails_before_lifecycle_credit(self) -> None:
        chain = self.owner_chain(continuous_semantic_handle_digest_hex="cd" * 32)
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX + "OWNER_CHAIN_CONTINUOUS_HANDLE_MISMATCH",
            violations,
        )

    def test_valid_nested_projection_for_wrong_post_source_cannot_hide_inside_valid_outer_chain(self) -> None:
        foreign_nested = self.projection(source_generation_value=44)
        chain = self.owner_chain(projection=foreign_nested)
        self.assertEqual([], verify_portable_higher_owner_chain_projection(chain))
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            SOURCE_CONTINUITY_PREFIX + "POST_SOURCE_GENERATION_MISMATCH",
            violations,
        )

    def test_outer_authority_widening_is_rejected_even_when_resealed(self) -> None:
        chain = self.owner_chain(commit_authorized=True)
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX + "OWNER_CHAIN_CEILING_VIOLATED:commit_authorized",
            violations,
        )

    def test_nested_authority_widening_is_rejected_even_when_both_layers_are_resealed(self) -> None:
        nested = self.projection(producer_authenticated=True)
        chain = self.owner_chain(projection=nested)
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX
            + "NESTED_PROJECTION_CEILING_VIOLATED:producer_authenticated",
            violations,
        )

    def test_outer_schema_widening_fails_closed(self) -> None:
        chain = self.owner_chain()
        widened = copy.deepcopy(chain)
        widened["payload"]["future_authority"] = False
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=widened,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX + "OWNER_CHAIN_SCHEMA_FIELDS_MISMATCH",
            violations,
        )

    def test_outer_payload_tamper_without_reseal_fails_digest(self) -> None:
        chain = self.owner_chain()
        chain["payload"]["one_canonical_post_edit_consequence"] = False
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=chain,
            **self.lifecycle_kwargs(),
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX
            + "OWNER_CHAIN_POSITIVE_PROOF_MISSING:one_canonical_post_edit_consequence",
            violations,
        )
        self.assertIn(
            OWNER_CHAIN_PREFIX + "OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH",
            violations,
        )

    def test_exact_post_hold_cannot_be_promoted_by_portable_owner_chain(self) -> None:
        graph8 = copy.deepcopy(self.graph)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-o22-8")
        graph8["witness_ref"] = "GRAPH:O22:8:CURRENT"
        outer = compile_observation_bound_reentry_closure(
            root=self.post_root,
            codemap=self.codemap,
            anchor_manifest=self.anchors,
            witness_manifest=self.post_witness,
            previous_binding=self.previous,
            reentry_receipt=self.reentry,
            candidate_graph_witness=graph8,
        )
        self.assertEqual(HOLD, outer["closure_status"])
        violations = verify_portable_higher_owner_chain_inside_closed_lifecycle(
            portable_owner_chain_projection=self.owner_chain(),
            **self.lifecycle_kwargs(post_outer=outer, post_graph=graph8),
        )
        self.assertTrue(any(item.startswith(SOURCE_CONTINUITY_PREFIX) for item in violations))

    def test_public_boundary_has_no_second_lower_projection_escape_hatch(self) -> None:
        params = inspect.signature(
            verify_portable_higher_owner_chain_inside_closed_lifecycle
        ).parameters
        self.assertIn("portable_owner_chain_projection", params)
        self.assertNotIn("astge_projection", params)
        self.assertNotIn("canonical_target_projection", params)
        self.assertNotIn("candidate_binding", params)
        self.assertNotIn("source_observation_receipt", params)


if __name__ == "__main__":
    import unittest

    unittest.main()
