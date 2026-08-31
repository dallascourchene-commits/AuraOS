from __future__ import annotations

import copy
import hashlib
import inspect
import json
from unittest.mock import patch

from scripts import aura_workcapsule_artifact_qualified_host_observation as artifact_host_owner
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    CAUSAL_HOST_VERSION,
    admit_causal_artifact_qualified_host_envelope,
    verify_causal_artifact_qualified_host_envelope,
    verify_causal_host_admission_envelope,
)
from tests.test_aura_workcapsule_artifact_qualified_host_observation import (
    WorkCapsuleArtifactQualifiedHostObservationTests,
)


def _sha(value) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _seal_causal(receipt: dict) -> dict:
    receipt.pop("receipt_identity", None)
    receipt["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": CAUSAL_HOST_VERSION,
        "value": _sha(receipt),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return receipt


class WorkCapsuleCausalArtifactQualifiedHostEnvelopeTests(
    WorkCapsuleArtifactQualifiedHostObservationTests
):
    def causal_host_receipt(self, *, states=None, target_ref=None, **overrides) -> dict:
        receipt = copy.deepcopy(
            self.host_receipt(states=states, target_ref=target_ref)
        )
        receipt.pop("receipt_identity", None)
        receipt["version"] = CAUSAL_HOST_VERSION
        receipt.update(
            {
                "causal_temporal_owner_reproved": True,
                "raw_owner_pre_lifecycle_derived": True,
                "raw_owner_post_candidate_derived": True,
                "post_o10_closure_derived": True,
                "pre_reentry_receipt_reused_for_post_o10": True,
                "fresh_post_reentry_receipt_substituted": False,
            }
        )
        receipt.update(overrides)
        return _seal_causal(receipt)

    def causal_kwargs(self, *, host=None, raw=None) -> dict:
        chosen_raw = raw if raw is not None else self.raw_receipt()
        parent = self.join_kwargs(raw=chosen_raw)
        return {
            **parent,
            "causal_host_admission_receipt": (
                host if host is not None else self.causal_host_receipt()
            ),
        }

    def test_exact_causal_host_envelope_binds_to_exact_artifact(self) -> None:
        self.assertEqual(
            [], verify_causal_artifact_qualified_host_envelope(**self.causal_kwargs())
        )
        out = admit_causal_artifact_qualified_host_envelope(**self.causal_kwargs())
        self.assertTrue(out["current_recursive_raw_target_reproved"])
        self.assertTrue(out["causal_host_admission_integrity_checked"])
        self.assertFalse(out["causal_host_admission_reproved_by_child"])
        self.assertFalse(out["causal_host_admission_producer_authenticated"])
        self.assertTrue(out["causal_temporal_owner_claim_carried"])
        self.assertTrue(out["pre_reentry_receipt_reused_for_post_o10"])
        self.assertFalse(out["fresh_post_reentry_receipt_substituted"])
        self.assertTrue(out["current_pr565_host_summary_owner_reused"])
        self.assertTrue(out["resolved_host_gates_bound_to_exact_artifact"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_foreign_artifact_target_ref_rejects_even_when_causal_envelope_resealed(self) -> None:
        host = self.causal_host_receipt(
            target_ref="aura-workcapsule-target-sha256:" + "cd" * 32
        )
        violations = verify_causal_artifact_qualified_host_envelope(
            **self.causal_kwargs(host=host)
        )
        self.assertTrue(
            any(
                "RESOLVED_HOST_GATE_TARGET_REF_MISMATCH:U_HEAD" in item
                for item in violations
            )
        )

    def test_causal_scar_cannot_be_resealed_away(self) -> None:
        for field, value in (
            ("pre_reentry_receipt_reused_for_post_o10", False),
            ("fresh_post_reentry_receipt_substituted", True),
            ("causal_temporal_owner_reproved", False),
        ):
            host = self.causal_host_receipt()
            host[field] = value
            _seal_causal(host)
            self.assertTrue(verify_causal_host_admission_envelope(host), field)

    def test_mask_and_disposition_are_derived_not_caller_truth(self) -> None:
        host = self.causal_host_receipt()
        host["unknown_mask"] = 0
        host["disposition"] = "HOST_OBSERVATIONS_COMPLETE_NONAUTHORIZING"
        _seal_causal(host)
        violations = verify_causal_host_admission_envelope(host)
        self.assertIn("UNKNOWN_MASK_MISMATCH", violations)
        self.assertIn("DISPOSITION_MISMATCH", violations)

    def test_bool_cannot_impersonate_fail_mask(self) -> None:
        host = self.causal_host_receipt()
        host["fail_mask"] = False
        _seal_causal(host)
        self.assertIn(
            "FAIL_MASK_MISMATCH", verify_causal_host_admission_envelope(host)
        )

    def test_current_pr565_candidate_probe_summary_is_not_caller_truth(self) -> None:
        host = self.causal_host_receipt()
        host["candidate_probes_by_unknown_gate"] = {}
        _seal_causal(host)
        self.assertIn(
            "HOST_CANDIDATE_PROBES_MISMATCH",
            verify_causal_host_admission_envelope(host),
        )

    def test_current_pr565_summary_owner_is_live_delegation(self) -> None:
        host = self.causal_host_receipt()
        with patch.object(
            artifact_host_owner,
            "_derived_host_state_violations",
            return_value=["CURRENT_PR565_OWNER_SENTINEL"],
        ):
            self.assertIn(
                "CURRENT_PR565_OWNER_SENTINEL",
                verify_causal_host_admission_envelope(host),
            )

    def test_nested_resolution_tamper_with_outer_reseal_still_rejects(self) -> None:
        host = self.causal_host_receipt()
        host["host_gate_resolutions"]["U_HEAD"]["target_ref"] = (
            "aura-workcapsule-target-sha256:" + "ef" * 32
        )
        _seal_causal(host)
        self.assertIn(
            "HOST_RESOLUTION_DIGEST_MISMATCH:U_HEAD",
            verify_causal_host_admission_envelope(host),
        )

    def test_all_pass_for_exact_artifact_stays_nonauthorizing(self) -> None:
        host = self.causal_host_receipt(
            states={gate: "PASS" for gate in self.host_receipt()["host_gate_states"]}
        )
        out = admit_causal_artifact_qualified_host_envelope(
            **self.causal_kwargs(host=host)
        )
        self.assertTrue(out["all_host_gates_pass_for_exact_artifact"])
        self.assertTrue(out["host_observation_set_complete"])
        self.assertFalse(out["host_resolver_trust_proven"])
        self.assertFalse(out["host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])

    def test_host_effect_authority_widening_rejects_after_reseal(self) -> None:
        host = self.causal_host_receipt()
        host["host_effect_ready"] = True
        _seal_causal(host)
        self.assertTrue(
            any(
                "host_effect_ready" in item
                for item in verify_causal_host_admission_envelope(host)
            )
        )

    def test_public_boundary_replaces_old_host_envelope_name_only(self) -> None:
        params = set(
            inspect.signature(verify_causal_artifact_qualified_host_envelope).parameters
        )
        self.assertEqual(
            {
                "scoped_target_inputs",
                "higher_owner_projection",
                "raw_slice_receipt",
                "causal_host_admission_receipt",
            },
            params,
        )
        self.assertNotIn("host_admission_receipt", params)
        self.assertNotIn("host_observation_resolver", params)
        self.assertNotIn("temporal_receipt", params)
        self.assertNotIn("effect_ready", params)


if __name__ == "__main__":
    import unittest

    unittest.main()
