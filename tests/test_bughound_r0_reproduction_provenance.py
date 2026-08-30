from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import os
import unittest

from tools.bughound.arena_runtime import (
    BugHoundArenaRuntimeR0,
    BugHoundArenaRuntimeR0SpecV1,
    source_tree_digest,
)
from tools.bughound.bounty_candidate_admission import IndependentBountyReproductionReceiptV1
from tools.bughound.r0_reproduction_provenance import (
    WITNESS_EVENT_TYPE,
    bind_r0_offline_reproduction_provenance,
    reproduction_witness_ref,
    r0_reproduction_environment_digest,
)
from tools.bughound.target_profile import (
    AURAOS_HARDENING_PROFILE_ID,
    CASH_BOUNTY_PROFILE_ID,
    BugHoundTargetProfileV1,
)


class BugHoundR0ReproductionProvenanceTests(unittest.TestCase):
    def source(self):
        return {
            "src/app.py": "VALUE = 1\n",
            "tests/test_app.py": "def test_value():\n    assert 1 == 1\n",
        }

    def profile(self, *, auraos: bool = False):
        if auraos:
            return BugHoundTargetProfileV1(
                profile_id=AURAOS_HARDENING_PROFILE_ID,
                profile_kind="INTERNAL_AURAOS_HARDENING",
                target_ref="repo://AuraOS",
                target_generation="auraos-r0",
            )
        return BugHoundTargetProfileV1(
            profile_id=CASH_BOUNTY_PROFILE_ID,
            profile_kind="EXTERNAL_CASH_BOUNTY",
            target_ref="program://authorized/local-snapshot",
            target_generation="target-r0",
        )

    def runtime(self, *, auraos: bool = False):
        source = self.source()
        spec = BugHoundArenaRuntimeR0SpecV1(
            profile=self.profile(auraos=auraos),
            source_digest=source_tree_digest(source),
        )
        return BugHoundArenaRuntimeR0(spec, source)

    @staticmethod
    def witness_digest():
        return hashlib.sha256(b"bounded-offline-witness-v1").hexdigest()

    def build_bound_inputs(self, *, auraos: bool = False, extra_event: bool = False):
        runtime = self.runtime(auraos=auraos)
        materialization = runtime.materialize()
        reproduction = IndependentBountyReproductionReceiptV1(
            candidate_id="candidate-r0-001",
            target_ref=materialization.target_ref,
            target_generation=materialization.target_generation,
            reproducer_ref="arena://independent-reproducer/r0-fixture",
            reproducer_generation="fixture-generation-1",
            result="REPRODUCED_OFFLINE_FIXTURE",
            witness_digest=self.witness_digest(),
            environment_digest=r0_reproduction_environment_digest(materialization),
            scope_rules_digest="scope-rules-digest-1",
            source_currentness_ref="source-currentness:fixture-1",
            external_effect=False,
        )
        event = runtime.append_evidence(
            event_type=WITNESS_EVENT_TYPE,
            artifact_ref=reproduction_witness_ref(reproduction.candidate_id),
            artifact_digest=reproduction.witness_digest,
        )
        if extra_event:
            runtime.append_evidence(
                event_type="DIAGNOSTIC",
                artifact_ref="artifact://diagnostic/1",
                artifact_digest=hashlib.sha256(b"diagnostic").hexdigest(),
            )
        teardown = runtime.teardown()
        return materialization, reproduction, event, teardown

    def test_exact_r0_witness_lineage_binds_without_promoting_trust(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        out = bind_r0_offline_reproduction_provenance(
            materialization=materialization,
            reproduction=reproduction,
            witness_event=event,
            teardown=teardown,
        )
        self.assertTrue(out.witness_artifact_bound)
        self.assertTrue(out.runtime_lineage_bound)
        self.assertTrue(out.source_lineage_bound)
        self.assertTrue(out.teardown_bound)
        self.assertFalse(out.command_execution_proven)
        self.assertFalse(out.reproducer_identity_proven)
        self.assertFalse(out.independent_reproduction_registry_proven)
        self.assertFalse(out.vulnerability_specific_reproduction_proven)
        self.assertFalse(out.os_network_isolation_proven)
        self.assertFalse(out.external_effect)
        self.assertEqual(out.environment_digest, r0_reproduction_environment_digest(materialization))
        self.assertEqual(out.registry_binding_coordinates["witness_digest"], reproduction.witness_digest)

    def test_environment_must_bind_exact_materialization(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        reproduction = replace(reproduction, environment_digest="different-environment")
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_ENVIRONMENT_DIGEST_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_target_generation_substitution_fails(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        reproduction = replace(reproduction, target_generation="different-generation")
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_TARGET_GENERATION_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_witness_digest_substitution_fails(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        bad_event = replace(event, artifact_digest=hashlib.sha256(b"other").hexdigest())
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_WITNESS_DIGEST_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=bad_event,
                teardown=teardown,
            )

    def test_witness_event_role_substitution_fails(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        bad_event = replace(event, event_type="STATIC_CANDIDATE")
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_WITNESS_EVENT_TYPE_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=bad_event,
                teardown=teardown,
            )

    def test_unbound_extra_evidence_event_fails_closed(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs(extra_event=True)
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_SINGLE_BOUND_WITNESS_REQUIRED"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_source_mutation_before_teardown_fails(self):
        runtime = self.runtime()
        materialization = runtime.materialize()
        reproduction = IndependentBountyReproductionReceiptV1(
            candidate_id="candidate-r0-001",
            target_ref=materialization.target_ref,
            target_generation=materialization.target_generation,
            reproducer_ref="arena://independent-reproducer/r0-fixture",
            reproducer_generation="fixture-generation-1",
            result="REPRODUCED_OFFLINE_FIXTURE",
            witness_digest=self.witness_digest(),
            environment_digest=r0_reproduction_environment_digest(materialization),
            scope_rules_digest="scope-rules-digest-1",
            source_currentness_ref="source-currentness:fixture-1",
        )
        event = runtime.append_evidence(
            event_type=WITNESS_EVENT_TYPE,
            artifact_ref=reproduction_witness_ref(reproduction.candidate_id),
            artifact_digest=reproduction.witness_digest,
        )
        target = runtime.source_path / "src" / "app.py"
        os.chmod(runtime.source_path / "src", 0o755)
        os.chmod(target, 0o644)
        target.write_text("VALUE = 999\n", encoding="utf-8")
        teardown = runtime.teardown()
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_TEARDOWN_SOURCE_OBSERVED_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_materialization_network_or_os_sandbox_claim_cannot_widen(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_NETWORK_OFF_REQUIRED"):
            bind_r0_offline_reproduction_provenance(
                materialization=replace(materialization, network_policy="HOST_NETWORK"),
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )
        with self.assertRaisesRegex(ValueError, "R0_OS_NETWORK_ISOLATION_CANNOT_BE_CLAIMED"):
            bind_r0_offline_reproduction_provenance(
                materialization=replace(materialization, os_network_isolation_proven=True),
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_reproduction_external_effect_is_forbidden(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=replace(reproduction, external_effect=True),
                witness_event=event,
                teardown=teardown,
            )

    def test_teardown_capsule_substitution_fails(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_TEARDOWN_CAPSULE_MISMATCH"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=replace(teardown, capsule_id="different-capsule"),
            )

    def test_auraos_runtime_cannot_cross_cast_into_cash_reproduction_adapter(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs(auraos=True)
        with self.assertRaisesRegex(ValueError, "R0_REPRODUCTION_CASH_PROFILE_REQUIRED"):
            bind_r0_offline_reproduction_provenance(
                materialization=materialization,
                reproduction=reproduction,
                witness_event=event,
                teardown=teardown,
            )

    def test_public_surface_has_no_registry_or_authority_override(self):
        params = tuple(inspect.signature(bind_r0_offline_reproduction_provenance).parameters)
        self.assertEqual(params, ("materialization", "reproduction", "witness_event", "teardown"))
        for forbidden in (
            "registry",
            "registry_lookup",
            "trusted",
            "authority",
            "network_policy",
            "credential",
            "submission_authorized",
            "vulnerability_specific_reproduction_proven",
        ):
            self.assertNotIn(forbidden, params)

    def test_provenance_receipt_is_deterministic(self):
        materialization, reproduction, event, teardown = self.build_bound_inputs()
        one = bind_r0_offline_reproduction_provenance(
            materialization=materialization,
            reproduction=reproduction,
            witness_event=event,
            teardown=teardown,
        )
        two = bind_r0_offline_reproduction_provenance(
            materialization=materialization,
            reproduction=reproduction,
            witness_event=event,
            teardown=teardown,
        )
        self.assertEqual(one.receipt_digest, two.receipt_digest)


if __name__ == "__main__":
    unittest.main()
