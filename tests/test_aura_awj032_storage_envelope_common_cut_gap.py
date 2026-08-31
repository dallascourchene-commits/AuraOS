from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from scripts.aura_awj032_storage_envelope_common_cut_gap import (
    MISSING_COMMON_CUT_KEYS,
    StorageEnvelopeCommonCutGapError,
    assess_storage_envelope_common_cut_gap,
)
from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import run_bounded_storage_probe
from tools.thinkpad_sustained_operating_envelope import observe_sustained_operating_envelope


class StorageEnvelopeCommonCutGapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "weights.bin").write_bytes(b"aura-o52" * 4096)
        self.proc = root / "proc"
        self.sys = root / "sys"
        self.proc.mkdir()
        self.sys.mkdir()

        self.request = OwnerHostC2CanaryRequest(
            w3_proof_logical_id="ab" * 32,
            preflight_receipt_digest="cd" * 32,
            airllm_source_revision="airllm-reviewed-source@deadbeef",
            airllm_security_evidence_digest="12" * 32,
            host_snapshot_digest="34" * 32,
            storage_plan_digest="56" * 32,
            workspace_root=str(self.workspace),
            max_payload_bytes=1024 * 1024,
            max_wall_seconds=10,
            effect_admission_ref="owner-effect:awj032:o52-fixture",
        )
        self.probe = run_bounded_storage_probe(
            request=self.request,
            relative_path="weights.bin",
            byte_offset=0,
            probe_bytes=8192,
            chunk_bytes=4096,
            max_wall_seconds=2.0,
        )
        self.envelope = observe_sustained_operating_envelope(
            proc_root=str(self.proc),
            sys_root=str(self.sys),
            observed_at_utc="2026-08-31T06:50:00+00:00",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def assess(self, *, request=None, probe=None, envelope=None):
        return assess_storage_envelope_common_cut_gap(
            request=request or self.request,
            probe_receipt=probe or self.probe,
            envelope=envelope or self.envelope,
        )

    def assert_code(self, code, fn):
        with self.assertRaises(StorageEnvelopeCommonCutGapError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def test_two_valid_current_artifacts_still_do_not_make_common_cut(self):
        receipt = self.assess()
        self.assertTrue(receipt.storage_current_in_owned_generation)
        self.assertTrue(receipt.envelope_current_at_observation_time_only)
        self.assertFalse(receipt.authenticated_host_session_or_generation_bound)
        self.assertFalse(receipt.storage_absolute_observation_time_available)
        self.assertFalse(receipt.same_host_identity_proven)
        self.assertFalse(receipt.temporal_overlap_proven)
        self.assertFalse(receipt.same_host_common_cut_proven)
        self.assertFalse(receipt.performance_join_admissible)
        self.assertEqual(receipt.missing_common_cut_keys, MISSING_COMMON_CUT_KEYS)

    def test_request_host_snapshot_digest_is_not_authenticated_host_identity(self):
        receipt = self.assess()
        self.assertEqual(receipt.request_host_snapshot_digest, self.request.host_snapshot_digest)
        self.assertFalse(receipt.host_snapshot_digest_is_authenticated_host_identity)
        self.assertFalse(receipt.producer_authenticated)

    def test_moving_envelope_time_changes_relation_identity_without_minting_overlap(self):
        later = replace(self.envelope, observed_at_utc="2026-08-31T07:10:00+00:00")
        a = self.assess()
        b = self.assess(envelope=later)
        self.assertNotEqual(a.envelope_observation_digest, b.envelope_observation_digest)
        self.assertNotEqual(a.receipt_digest, b.receipt_digest)
        self.assertFalse(b.temporal_overlap_proven)
        self.assertFalse(b.same_host_common_cut_proven)

    def test_naive_envelope_time_fails_closed(self):
        naive = replace(self.envelope, observed_at_utc="2026-08-31T06:50:00")
        self.assert_code(
            "ENVELOPE_OBSERVATION_TIME_MUST_BE_OFFSET_AWARE",
            lambda: self.assess(envelope=naive),
        )

    def test_envelope_identity_or_authentication_widening_fails_closed(self):
        widened_identity = replace(self.envelope, thinkpad_identity_proven=True)
        self.assert_code(
            "OPERATING_ENVELOPE_CEILING_WIDENED",
            lambda: self.assess(envelope=widened_identity),
        )
        widened_auth = replace(self.envelope, producer_authenticated=True)
        self.assert_code(
            "OPERATING_ENVELOPE_CEILING_WIDENED",
            lambda: self.assess(envelope=widened_auth),
        )

    def test_storage_physical_nvme_widening_is_rejected_by_parent_owner(self):
        widened = replace(self.probe, physical_nvme_io_attested=True)
        with self.assertRaisesRegex(ValueError, "STORAGE_PROBE_CEILING_WIDENED"):
            self.assess(probe=widened)

    def test_currentness_domains_remain_distinct(self):
        receipt = self.assess()
        self.assertEqual(receipt.storage_currentness_domain, "awj032-storage-probe-generation")
        self.assertEqual(
            receipt.envelope_currentness_domain,
            "owner-host-operating-envelope-observation-generation",
        )
        self.assertFalse(receipt.physical_nvme_currentness_proven)
        self.assertFalse(receipt.causal_attribution_proven)

    def test_public_boundary_has_no_join_or_authority_override(self):
        import inspect
        params = tuple(inspect.signature(assess_storage_envelope_common_cut_gap).parameters)
        self.assertEqual(params, ("request", "probe_receipt", "envelope"))
        forbidden = {
            "host_session_ref",
            "storage_observed_at_utc",
            "same_host",
            "temporal_overlap",
            "causal_attribution",
            "performance_join_admissible",
            "physical_nvme_currentness",
            "producer_authenticated",
            "w4_admitted",
            "g2_admitted",
            "effect_authority",
        }
        self.assertTrue(forbidden.isdisjoint(params))

    def test_frozen_inputs_produce_deterministic_gap_identity(self):
        a = self.assess()
        b = self.assess()
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertEqual(a.missing_common_cut_keys, b.missing_common_cut_keys)
        self.assertFalse(a.w4_admitted)
        self.assertFalse(a.g2_admitted)
        self.assertFalse(a.effect_authority_proven)
        self.assertFalse(a.semantic_k27_authority_minted)
        self.assertFalse(a.native_private_transformer_kv_accessed)


if __name__ == "__main__":
    unittest.main()
