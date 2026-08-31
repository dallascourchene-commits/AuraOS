from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest import mock

from scripts import aura_workcapsule_post_repair_portable_higher_owner_continuity as legacy
from scripts import aura_workcapsule_post_source_portable_higher_owner_continuity as canonical
from tests.test_aura_workcapsule_post_repair_portable_higher_owner_continuity import (
    WorkCapsulePostRepairPortableHigherOwnerContinuityTests,
)


class WorkCapsulePortableHigherOwnerOwnerReductionTests(
    WorkCapsulePostRepairPortableHigherOwnerContinuityTests
):
    def test_real_fixture_has_one_canonical_consequence_across_both_public_vocabularies(self) -> None:
        outer = self.higher_owner_projection()
        legacy_kwargs = self.child_kwargs(outer=outer)
        canonical_kwargs = dict(legacy_kwargs)
        canonical_kwargs["portable_higher_owner_projection"] = canonical_kwargs.pop(
            "higher_owner_projection"
        )

        self.assertEqual([], canonical.verify_post_source_portable_higher_owner_continuity(**canonical_kwargs))
        self.assertEqual([], legacy.verify_post_repair_portable_higher_owner_continuity(**legacy_kwargs))

        canonical_receipt = canonical.admit_post_source_portable_higher_owner_continuity(
            **canonical_kwargs
        )
        legacy_receipt = legacy.admit_post_repair_portable_higher_owner_continuity(**legacy_kwargs)

        self.assertEqual(
            canonical_receipt["source_instance_continuity_proven"],
            legacy_receipt["post_repair_source_instance_continuity_proven"],
        )
        self.assertEqual(
            canonical_receipt["portable_higher_owner_owner_chain_verified"],
            legacy_receipt["portable_higher_owner_chain_verified"],
        )
        self.assertEqual(
            canonical_receipt["nested_canonical_target_projection_payload_sha256"],
            legacy_receipt["nested_canonical_target_projection_payload_sha256"],
        )
        self.assertEqual(
            canonical_receipt["portable_owner_chain_payload_sha256"],
            legacy_receipt["portable_higher_owner_payload_sha256"],
        )
        self.assertEqual(
            canonical_receipt["continuous_semantic_handle_digest_hex"],
            legacy_receipt["continuous_semantic_handle_digest_hex"],
        )
        self.assertEqual(
            canonical_receipt["post_closure_status"], legacy_receipt["post_closure_status"]
        )
        self.assertEqual(
            canonical_receipt["post_source_generation"], legacy_receipt["post_source_generation"]
        )
        self.assertEqual(canonical_receipt["post_source_sha256"], legacy_receipt["post_source_sha256"])
        self.assertEqual(
            canonical_receipt["post_source_byte_len"], legacy_receipt["post_source_byte_len"]
        )
        self.assertFalse(any(canonical_receipt["authority"].values()))
        self.assertFalse(any(legacy_receipt["authority"].values()))

    def test_legacy_outer_validator_delegates_to_canonical_and_translates_vocabulary(self) -> None:
        outer = self.higher_owner_projection()
        with mock.patch.object(
            legacy._canonical,
            "verify_portable_higher_owner_owner_chain_projection",
            return_value=[
                "OWNER_CHAIN_SCHEMA_FIELDS_MISMATCH",
                "OWNER_CHAIN_PROOF_FLAG_MISSING:one_canonical_post_edit_consequence",
                "OWNER_CHAIN_CONTINUOUS_HANDLE_INVALID",
            ],
        ) as delegated:
            self.assertEqual(
                [
                    legacy.OWNER_CHAIN_FIELDS_MISMATCH,
                    legacy.OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN
                    + ":one_canonical_post_edit_consequence",
                    legacy.OWNER_CHAIN_HANDLE_INVALID,
                ],
                legacy.verify_portable_higher_owner_chain(outer),
            )
            delegated.assert_called_once_with(outer)

    def test_legacy_consequence_verifier_delegates_to_canonical_and_translates_prefixes(self) -> None:
        outer = self.higher_owner_projection()
        kwargs = self.child_kwargs(outer=outer)
        with mock.patch.object(
            legacy._canonical,
            "verify_post_source_portable_higher_owner_continuity",
            return_value=[
                "OWNER_CHAIN_OWNER_CHAIN_CEILING_VIOLATED:commit_authorized",
                "SOURCE_CONTINUITY_POST_SOURCE_GENERATION_MISMATCH",
                canonical.SOURCE_RECEIPT_HANDLE_MISMATCH,
            ],
        ) as delegated:
            self.assertEqual(
                [
                    "OWNER_CHAIN_OWNER_CHAIN_CEILING_VIOLATED:commit_authorized",
                    "POST_SOURCE_POST_SOURCE_GENERATION_MISMATCH",
                    "POST_SOURCE_SOURCE_RECEIPT_HANDLE_MISMATCH",
                ],
                legacy.verify_post_repair_portable_higher_owner_continuity(**kwargs),
            )
            expected = dict(kwargs)
            expected["portable_higher_owner_projection"] = expected.pop("higher_owner_projection")
            delegated.assert_called_once_with(**expected)

    def test_canonical_stronger_source_receipt_checks_are_not_dropped_by_facade(self) -> None:
        outer = self.higher_owner_projection()
        kwargs = self.child_kwargs(outer=outer)
        with mock.patch.object(
            legacy._canonical,
            "verify_post_source_portable_higher_owner_continuity",
            return_value=[canonical.SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH],
        ):
            self.assertEqual(
                ["POST_SOURCE_SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH"],
                legacy.verify_post_repair_portable_higher_owner_continuity(**kwargs),
            )

    def test_legacy_admission_is_vocabulary_adapter_over_canonical_receipt(self) -> None:
        outer = self.higher_owner_projection()
        kwargs = self.child_kwargs(outer=outer)
        canonical_receipt = {
            "source_instance_continuity_proven": True,
            "portable_higher_owner_owner_chain_verified": True,
            "higher_owner_semantic_handle_continuity_proven": True,
            "post_closure_status": "CLOSED",
            "post_source_generation": 43,
            "post_source_sha256": "ab" * 32,
            "post_source_byte_len": 123,
            "continuous_semantic_handle_digest_hex": "cd" * 32,
            "portable_owner_chain_payload_sha256": "ef" * 32,
            "nested_canonical_target_projection_payload_sha256": "12" * 32,
            "projection_producer_authenticated": False,
            "semantic_repair_correctness_minted": False,
            "runtime_name_resolution_proven": False,
            "call_graph_proven": False,
            "b_minus_approved": False,
            "authority": {
                "review_authorized": False,
                "mutation_authorized": False,
                "execution_authorized": False,
                "commit_authorized": False,
                "merge_authorized": False,
                "promotion_authorized": False,
                "provider_effect_authorized": False,
                "public_effect_authorized": False,
                "human_authority": False,
            },
        }
        with mock.patch.object(
            legacy,
            "verify_post_repair_portable_higher_owner_continuity",
            return_value=[],
        ), mock.patch.object(
            legacy._canonical,
            "admit_post_source_portable_higher_owner_continuity",
            return_value=canonical_receipt,
        ) as delegated:
            receipt = legacy.admit_post_repair_portable_higher_owner_continuity(**kwargs)
            self.assertTrue(receipt["post_repair_source_instance_continuity_proven"])
            self.assertTrue(receipt["portable_higher_owner_chain_verified"])
            self.assertEqual("12" * 32, receipt["nested_canonical_target_projection_payload_sha256"])
            self.assertEqual("ef" * 32, receipt["portable_higher_owner_payload_sha256"])
            self.assertFalse(receipt["projection_producer_authenticated"])
            self.assertFalse(receipt["higher_owner_producer_authenticated"])
            self.assertFalse(any(receipt["authority"].values()))
            expected = dict(kwargs)
            expected["portable_higher_owner_projection"] = expected.pop("higher_owner_projection")
            delegated.assert_called_once_with(**expected)

    def test_legacy_source_contains_no_second_semantic_owner(self) -> None:
        source = Path(
            "scripts/aura_workcapsule_post_repair_portable_higher_owner_continuity.py"
        ).read_text()
        self.assertIn("aura_workcapsule_post_source_portable_higher_owner_continuity", source)
        tree = ast.parse(source)

        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        self.assertNotIn(
            "scripts.aura_workcapsule_post_repair_source_projection_continuity",
            imported_modules,
        )

        called_names: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
        for forbidden_call in (
            "verify_portable_canonical_target_projection",
            "verify_post_repair_source_projection_continuity",
            "admit_post_repair_source_projection_continuity",
        ):
            self.assertNotIn(forbidden_call, called_names)

        assigned_names = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Name)
        }
        for forbidden_owner_state in (
            "_OWNER_CHAIN_FIELDS",
            "_TARGET_PAYLOAD_FIELDS",
            "_OWNER_CHAIN_POSITIVE_FIELDS",
            "_OWNER_CHAIN_NEGATIVE_FIELDS",
        ):
            self.assertNotIn(forbidden_owner_state, assigned_names)
        self.assertNotIn("_owner_chain_payload_bytes", called_names)

    def test_legacy_public_boundary_is_preserved_without_second_projection_slot(self) -> None:
        params = inspect.signature(
            legacy.verify_post_repair_portable_higher_owner_continuity
        ).parameters
        self.assertIn("higher_owner_projection", params)
        self.assertIn("workcapsule_kwargs", params)
        for forbidden in (
            "astge_projection",
            "canonical_target_projection",
            "portable_higher_owner_projection",
            "post_edit_witness",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
