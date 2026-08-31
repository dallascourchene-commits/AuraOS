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
from scripts.aura_workcapsule_post_repair_source_projection_continuity import (
    POST_SOURCE_BODY_LENGTH_MISMATCH,
    POST_SOURCE_BODY_SHA_MISMATCH,
    POST_SOURCE_GENERATION_MISMATCH,
    POST_SOURCE_MISSING,
    PROJECTION_PREFIX,
    PROJECTION_SOURCE_NOT_REJECTED_PRE,
    TEMPORAL_PREFIX,
    admit_post_repair_source_projection_continuity,
    verify_portable_canonical_target_projection,
    verify_post_repair_source_projection_continuity,
)
from tests.test_aura_workcapsule_canonical_temporal_lifecycle_equivalence import (
    WorkCapsuleCanonicalTemporalLifecycleEquivalenceTests,
    identity,
)


class WorkCapsulePostRepairSourceProjectionContinuityTests(
    WorkCapsuleCanonicalTemporalLifecycleEquivalenceTests
):
    def projection(self, **overrides) -> dict:
        payload = {
            "schema": "AURA_ASTGE_POST_EDIT_CANONICAL_DEFINITION_TARGET_PROJECTION_V1",
            "version": 1,
            "canonicalization_profile": "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1",
            "source_generation_domain": "SOURCE",
            "source_generation_value": 43,
            "source_owner_ref": "source-owner://o28-fixture",
            "relative_path": "src/a.py",
            "file_id": 17,
            "source_sha256_hex": self.repaired_sha,
            "source_byte_len": len(self.repaired),
            "selected_target_scope_local_id": 9001,
            "selected_target_parent_scope_local_id": 8001,
            "selected_target_syntax_ordinal": 1,
            "selected_target_byte_start": 0,
            "selected_target_byte_end": len(self.repaired),
            "selected_target_semantic_handle_digest_hex": "ab" * 32,
            "definition_name": "target",
            "definition_owner_scope_local_id": 8001,
            "definition_target_scope_local_id": 9001,
            "selected_current_scope_is_binding_target": True,
            "binding_owner_is_selected_parent": True,
            "local_scope_id_is_semantic_identity": False,
            "post_edit_profiled_scope_current": True,
            "canonical_definition_target_current": True,
            "runtime_name_resolution_proven": False,
            "call_graph_proven": False,
            "semantic_patch_correctness_proven": False,
            "b_minus_approved": False,
            "producer_authenticated": False,
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

    def cross_kwargs(self, *, projection=None, post_outer=None, post_graph=None) -> dict:
        out = self.kwargs(post_outer=post_outer, post_graph=post_graph)
        out["astge_projection"] = projection if projection is not None else self.projection()
        return out

    def test_exact_portable_projection_binds_to_canonical_post_closed_source_instance(self) -> None:
        projection = self.projection()
        self.assertEqual([], verify_portable_canonical_target_projection(projection))
        self.assertEqual(
            [], verify_post_repair_source_projection_continuity(**self.cross_kwargs(projection=projection))
        )
        admitted = admit_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertTrue(admitted["source_instance_continuity_proven"])
        self.assertTrue(admitted["pre_rejected_dependency_matches_projection_source"])
        self.assertTrue(admitted["post_active_current_source_matches_projection"])
        self.assertEqual("CLOSED", admitted["post_closure_status"])
        self.assertEqual(43, admitted["post_source_generation"])
        self.assertEqual(self.repaired_sha, admitted["post_source_sha256"])
        self.assertFalse(admitted["projection_producer_authenticated"])
        self.assertFalse(admitted["semantic_repair_correctness_minted"])
        self.assertFalse(any(admitted["authority"].values()))

    def test_locally_valid_projection_with_wrong_post_generation_is_rejected_cross_runtime(self) -> None:
        projection = self.projection(source_generation_value=44)
        self.assertEqual([], verify_portable_canonical_target_projection(projection))
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertIn(POST_SOURCE_GENERATION_MISMATCH, violations)

    def test_locally_valid_projection_with_wrong_post_body_digest_is_rejected_cross_runtime(self) -> None:
        projection = self.projection(source_sha256_hex="11" * 32)
        self.assertEqual([], verify_portable_canonical_target_projection(projection))
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertIn(POST_SOURCE_BODY_SHA_MISMATCH, violations)

    def test_locally_valid_projection_with_wrong_post_body_length_is_rejected_cross_runtime(self) -> None:
        projection = self.projection(source_byte_len=len(self.repaired) + 1)
        self.assertEqual([], verify_portable_canonical_target_projection(projection))
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertIn(POST_SOURCE_BODY_LENGTH_MISMATCH, violations)

    def test_foreign_file_projection_cannot_attach_to_closed_lifecycle(self) -> None:
        projection = self.projection(file_id=99, relative_path="src/other.py")
        self.assertEqual([], verify_portable_canonical_target_projection(projection))
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertIn(PROJECTION_SOURCE_NOT_REJECTED_PRE, violations)
        self.assertIn(POST_SOURCE_MISSING, violations)

    def test_resealed_owner_target_relation_substitution_fails_projection_contract(self) -> None:
        projection = self.projection(definition_target_scope_local_id=9002)
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=projection)
        )
        self.assertIn(PROJECTION_PREFIX + "PROJECTION_TARGET_RELATION_MISMATCH", violations)

    def test_projection_cannot_launder_producer_or_semantic_authority(self) -> None:
        producer = self.projection(producer_authenticated=True)
        semantic = self.projection(semantic_patch_correctness_proven=True)
        producer_violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=producer)
        )
        semantic_violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(projection=semantic)
        )
        self.assertIn(
            PROJECTION_PREFIX + "PROJECTION_CEILING_VIOLATED:producer_authenticated",
            producer_violations,
        )
        self.assertIn(
            PROJECTION_PREFIX + "PROJECTION_CEILING_VIOLATED:semantic_patch_correctness_proven",
            semantic_violations,
        )

    def test_exact_post_hold_cannot_be_promoted_by_matching_projection(self) -> None:
        graph8 = copy.deepcopy(self.graph)
        graph8["graph_generation"] = 8
        graph8["graph_basis_identity"] = identity("graph-o28-8")
        graph8["witness_ref"] = "GRAPH:O28:8:CURRENT"
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
        violations = verify_post_repair_source_projection_continuity(
            **self.cross_kwargs(post_outer=outer, post_graph=graph8)
        )
        self.assertTrue(any(item.startswith(TEMPORAL_PREFIX) for item in violations))

    def test_public_boundary_has_no_lower_owner_or_caller_witness_escape_hatch(self) -> None:
        params = inspect.signature(verify_post_repair_source_projection_continuity).parameters
        for forbidden in (
            "candidate_binding",
            "observed_source_witnesses",
            "source_observation_receipt",
            "post_edit_witness",
            "projection_owner_receipt",
        ):
            self.assertNotIn(forbidden, params)
        self.assertIn("post_observation_bound_receipt", params)
        self.assertIn("astge_projection", params)

        source = Path(
            "scripts/aura_workcapsule_post_repair_source_projection_continuity.py"
        ).read_text()
        self.assertIn("verify_canonical_temporal_lifecycle_equivalence", source)
        self.assertNotIn("compile_source_reentry_observations", source)
        self.assertNotIn("compile_observation_bound_reentry_closure", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
