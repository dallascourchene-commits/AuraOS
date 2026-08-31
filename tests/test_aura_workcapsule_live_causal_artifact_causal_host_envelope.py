from __future__ import annotations

import copy
import hashlib
import inspect
import json

from scripts.aura_workcapsule_artifact_qualified_host_observation import (
    GATES,
    TARGET_REF_MISMATCH,
    artifact_target_ref,
)
from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    CAUSAL_HOST_VERSION,
    verify_causal_host_admission_envelope,
)
from scripts.aura_workcapsule_current_recursive_target_raw_slice_binding import (
    admit_current_recursive_target_raw_slice_binding,
)
from scripts.aura_workcapsule_live_causal_artifact_causal_host_envelope import (
    CAUSAL_CLOSURE_IDENTITY_MISMATCH,
    admit_live_causal_artifact_causal_host_envelope,
    verify_live_causal_artifact_causal_host_envelope,
)
from scripts.aura_workcapsule_live_causal_artifact_host_observation import (
    live_causal_artifact_target_ref,
)
from tests.test_aura_workcapsule_live_causal_artifact_host_observation import (
    WorkCapsuleLiveCausalArtifactHostObservationTests,
)


def _sha(value) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
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


class WorkCapsuleLiveCausalArtifactCausalHostEnvelopeTests(
    WorkCapsuleLiveCausalArtifactHostObservationTests
):
    def causal_host_receipt(self, *, target_ref=None, all_pass=False) -> dict:
        live = self.live_receipt()
        exact_ref = target_ref or live_causal_artifact_target_ref(live)
        receipt = copy.deepcopy(
            self.host_receipt(target_ref=exact_ref, all_pass=all_pass)
        )
        receipt.pop("receipt_identity", None)
        receipt["version"] = CAUSAL_HOST_VERSION
        receipt["post_closure_receipt_identity"] = copy.deepcopy(
            live["causal_post_closure_receipt_identity"]
        )
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
        return _seal_causal(receipt)

    def child_kwargs(self, *, host=None) -> dict:
        kwargs = self.o38_kwargs()
        kwargs["causal_host_admission_receipt"] = (
            host if host is not None else self.causal_host_receipt()
        )
        return kwargs

    def test_exact_causal_envelope_binds_to_exact_live_artifact_and_world(self) -> None:
        kwargs = self.child_kwargs()
        self.assertEqual([], verify_live_causal_artifact_causal_host_envelope(**kwargs))
        out = admit_live_causal_artifact_causal_host_envelope(**kwargs)
        self.assertTrue(out["live_causal_artifact_reproved"])
        self.assertTrue(out["causal_host_envelope_integrity_checked"])
        self.assertTrue(out["same_causal_post_closure_identity_proven"])
        self.assertTrue(out["resolved_causal_host_gates_bound_to_live_artifact"])
        self.assertTrue(out["artifact_target_ref_excludes_host_observation_state"])
        self.assertFalse(out["causal_host_envelope_reproved_by_child"])
        self.assertFalse(out["causal_host_envelope_producer_authenticated"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_valid_resealed_foreign_causal_world_fails_relation_not_envelope(self) -> None:
        host = self.causal_host_receipt()
        foreign = copy.deepcopy(host["post_closure_receipt_identity"])
        foreign["value"] = "cd" * 32
        host["post_closure_receipt_identity"] = foreign
        _seal_causal(host)
        self.assertEqual([], verify_causal_host_admission_envelope(host))
        violations = verify_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=host)
        )
        self.assertIn(CAUSAL_CLOSURE_IDENTITY_MISMATCH, violations)

    def test_old_pr562_target_ref_is_stale_for_causal_current_envelope(self) -> None:
        old_local = admit_current_recursive_target_raw_slice_binding(
            **self.join_kwargs(raw=self.raw_receipt())
        )
        old_ref = artifact_target_ref(old_local)
        live_ref = live_causal_artifact_target_ref(self.live_receipt())
        self.assertNotEqual(old_ref, live_ref)
        host = self.causal_host_receipt(target_ref=old_ref)
        violations = verify_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=host)
        )
        self.assertIn(f"{TARGET_REF_MISMATCH}:U_HEAD", violations)

    def test_artifact_ref_is_invariant_to_host_observation_state(self) -> None:
        partial = admit_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=self.causal_host_receipt())
        )
        complete = admit_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=self.causal_host_receipt(all_pass=True))
        )
        self.assertNotEqual(
            partial["host_observation_set_complete"],
            complete["host_observation_set_complete"],
        )
        self.assertNotEqual(partial["host_gate_states"], complete["host_gate_states"])
        self.assertEqual(
            partial["live_causal_artifact_target_ref"],
            complete["live_causal_artifact_target_ref"],
        )

    def test_causal_envelope_tamper_fails_before_target_binding(self) -> None:
        host = self.causal_host_receipt()
        host["unknown_mask"] = 0
        _seal_causal(host)
        violations = verify_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=host)
        )
        self.assertTrue(
            any(item.startswith("CAUSAL_HOST_ENVELOPE_") for item in violations)
        )

    def test_all_pass_for_live_artifact_remains_nonauthorizing(self) -> None:
        out = admit_live_causal_artifact_causal_host_envelope(
            **self.child_kwargs(host=self.causal_host_receipt(all_pass=True))
        )
        self.assertTrue(out["all_host_gates_pass_for_live_artifact"])
        self.assertTrue(out["host_observation_set_complete"])
        self.assertFalse(out["causal_host_resolver_trust_proven"])
        self.assertFalse(out["causal_host_observation_authority_proven"])
        self.assertFalse(out["trusted_continuation_ready"])
        self.assertFalse(out["host_effect_ready"])
        self.assertFalse(any(out["authority"].values()))

    def test_public_boundary_has_no_old_envelope_or_identity_override(self) -> None:
        params = set(
            inspect.signature(
                verify_live_causal_artifact_causal_host_envelope
            ).parameters
        )
        self.assertIn("causal_host_admission_receipt", params)
        for forbidden in (
            "host_admission_receipt",
            "artifact_target_ref",
            "host_target_ref",
            "post_source_witness",
            "post_closure_receipt",
            "host_observation_resolver",
            "host_effect_ready",
            "execution_authorized",
            "provider_effect_authorized",
        ):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    import unittest

    unittest.main()
