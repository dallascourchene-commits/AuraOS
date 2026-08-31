from __future__ import annotations

import copy
import hashlib
import inspect
import json
import unittest

from scripts.aura_workcapsule_corroboration_preserves_evidence_classes import (
    HOST_TARGET_PREFIX,
    PROOF_ARTIFACT_PREFIX,
    admit_corroboration_preserves_evidence_classes,
    verify_corroboration_preserves_evidence_classes,
)
from tests.test_aura_workcapsule_live_artifact_raw_slice_noninterchangeability import (
    live_receipt,
    raw_receipt,
)
from tests.test_aura_workcapsule_live_causal_corroboration import (
    pr568_receipt,
    pr572_receipt,
)


def _sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def exact_inputs():
    a = pr568_receipt()
    b = pr572_receipt()
    live = live_receipt(
        live_causal_artifact_target_ref=HOST_TARGET_PREFIX + _sha(a),
        dependency_key=copy.deepcopy(a["dependency_key"]),
        source_generation=a["source_generation"],
        full_source_sha256_hex=a["full_source_sha256_hex"],
        full_source_byte_len=a["full_source_byte_len"],
        target_byte_start=a["target_byte_start"],
        target_byte_end=a["target_byte_end"],
        target_slice_sha256_hex=a["target_slice_sha256_hex"],
        selected_target_semantic_handle_digest_hex=a[
            "selected_target_semantic_handle_digest_hex"
        ],
        causal_post_closure_receipt_identity=copy.deepcopy(
            a["causal_post_closure_receipt_identity"]
        ),
    )
    return live, raw_receipt(), a, b


class CorroborationPreservesEvidenceClassesTests(unittest.TestCase):
    def test_exact_relations_preserve_classes_and_distinct_lineage(self) -> None:
        live, raw, a, b = exact_inputs()
        self.assertEqual(
            [],
            verify_corroboration_preserves_evidence_classes(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )
        out = admit_corroboration_preserves_evidence_classes(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertTrue(out["noninterchangeability_owner_reproved"])
        self.assertTrue(out["corroboration_owner_reproved"])
        self.assertTrue(out["live_artifact_target_is_pr568_corroboration_member"])
        self.assertTrue(out["corroboration_preserves_evidence_class_boundary"])
        self.assertFalse(out["pr572_sibling_substitutable_for_live_artifact_host_evidence"])
        self.assertFalse(out["pr572_sibling_substitutable_for_causal_raw_slice_evidence"])
        self.assertFalse(out["raw_slice_and_live_artifact_host_evidence_interchangeable_after_corroboration"])
        self.assertTrue(out["proof_artifact_refs_distinct"])
        self.assertTrue(out["live_artifact_target_ref"].startswith(HOST_TARGET_PREFIX))
        self.assertTrue(out["pr568_proof_artifact_ref"].startswith(PROOF_ARTIFACT_PREFIX))
        self.assertNotEqual(out["live_artifact_target_ref"], out["pr568_proof_artifact_ref"])
        self.assertFalse(out["semantic_equivalence_proven"])
        self.assertFalse(out["semantic_truth_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["effect_authority_proven"])
        self.assertFalse(any(out["authority"].values()))

    def test_live_target_must_be_pr568_member_not_arbitrary_digest(self) -> None:
        live, raw, a, b = exact_inputs()
        live["live_causal_artifact_target_ref"] = HOST_TARGET_PREFIX + "0" * 64
        self.assertIn(
            "LIVE_ARTIFACT_TARGET_NOT_PR568_CORROBORATION_MEMBER",
            verify_corroboration_preserves_evidence_classes(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_pr572_sibling_is_rejected_in_live_host_evidence_slot_by_parent_owner(self) -> None:
        live, raw, a, b = exact_inputs()
        # Positive verification proves the production membrane observed the exact expected
        # PR580 schema rejection for the sibling in the live-host slot.
        self.assertEqual(
            [],
            verify_corroboration_preserves_evidence_classes(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )
        out = admit_corroboration_preserves_evidence_classes(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertFalse(out["pr572_sibling_substitutable_for_live_artifact_host_evidence"])

    def test_pr572_sibling_is_rejected_in_raw_slice_evidence_slot_by_parent_owner(self) -> None:
        live, raw, a, b = exact_inputs()
        out = admit_corroboration_preserves_evidence_classes(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertFalse(out["pr572_sibling_substitutable_for_causal_raw_slice_evidence"])

    def test_pr580_noninterchangeability_failure_stops_before_corroboration_claim(self) -> None:
        live, raw, a, b = exact_inputs()
        raw["raw_slice_used_as_host_resolution"] = True
        raw.pop("receipt_identity")
        from scripts import aura_workcapsule_live_artifact_raw_slice_noninterchangeability as pr580
        payload = copy.deepcopy(raw)
        raw["receipt_identity"] = {
            "kind": "DIGEST",
            "algorithm_or_provider": "sha256",
            "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
            "scope_profile": pr580.PR574_VERSION,
            "value": pr580._sha(payload),
            "schema_version": "DigestOrImmutableIdentityV1-compatible",
        }
        violations = verify_corroboration_preserves_evidence_classes(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertIn(
            "NONINTERCHANGEABILITY_PR574_CEILING_VIOLATED:raw_slice_used_as_host_resolution",
            violations,
        )

    def test_pr577_world_drift_stops_before_class_preservation_claim(self) -> None:
        live, raw, a, b = exact_inputs()
        b["source_generation"] = 44
        self.assertIn(
            "CORROBORATION_LIVE_SOURCE_INSTANCE_MISMATCH",
            verify_corroboration_preserves_evidence_classes(
                live_artifact_host_receipt=live,
                causal_raw_slice_host_separation_receipt=raw,
                pr568_receipt=a,
                pr572_receipt=b,
            ),
        )

    def test_reference_schemes_do_not_collapse_even_for_same_underlying_digest(self) -> None:
        live, raw, a, b = exact_inputs()
        out = admit_corroboration_preserves_evidence_classes(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
            pr568_receipt=a,
            pr572_receipt=b,
        )
        self.assertTrue(out["same_underlying_pr568_digest_across_reference_schemes"])
        self.assertTrue(out["reference_scheme_identity_preserved"])
        self.assertNotEqual(out["live_artifact_target_ref"], out["pr568_proof_artifact_ref"])

    def test_public_boundary_is_four_closed_parent_receipts_only(self) -> None:
        params = set(inspect.signature(verify_corroboration_preserves_evidence_classes).parameters)
        self.assertEqual(
            {
                "live_artifact_host_receipt",
                "causal_raw_slice_host_separation_receipt",
                "pr568_receipt",
                "pr572_receipt",
            },
            params,
        )
        for forbidden in (
            "host_observation_resolver",
            "corroboration_override",
            "evidence_class_override",
            "artifact_target_ref",
            "execution_authorized",
            "host_effect_ready",
        ):
            self.assertNotIn(forbidden, params)

    def test_admission_is_deterministic(self) -> None:
        live, raw, a, b = exact_inputs()
        kwargs = {
            "live_artifact_host_receipt": live,
            "causal_raw_slice_host_separation_receipt": raw,
            "pr568_receipt": a,
            "pr572_receipt": b,
        }
        first = admit_corroboration_preserves_evidence_classes(**copy.deepcopy(kwargs))
        second = admit_corroboration_preserves_evidence_classes(**copy.deepcopy(kwargs))
        self.assertEqual(first, second)
        self.assertEqual(64, len(first["receipt_identity"]["value"]))


if __name__ == "__main__":
    unittest.main()
