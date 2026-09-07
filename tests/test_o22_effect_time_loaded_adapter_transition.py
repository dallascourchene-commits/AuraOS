import unittest
from dataclasses import replace
from hashlib import sha256

from tools.awj032.training_o2_transition_reference.test_transition_envelope import TransitionTest
from tools.awj032.training_o22_effect_time_activation.effect_time_activation import (
    Disposition,
    activation_dispatch_root,
    bind_effect_time_activation,
    required_loaded_units,
)
from tools.arena.effect_time_loaded_process_currentness import (
    AtUseObservation,
    InstalledRuntimeAttestation,
    LoadedProcessWitness,
    MutationModel,
)


def R(s):
    return sha256(s.encode()).hexdigest()


class O22EffectTimeLoadedAdapterTransitionTest(unittest.TestCase):
    def setUp(self):
        parent = TransitionTest(methodName="test_valid")
        parent.setUp()
        self.parent = parent
        self.ack, self.result = parent.pair()
        runtime_root = parent.env.intent.inference_runtime_root
        dispatch_root = activation_dispatch_root(parent.core, parent.env)
        self.installed = InstalledRuntimeAttestation(
            host_id="host-1",
            installed_runtime_root=runtime_root,
            generation=7,
            observed_at=10,
            valid_until=100,
            authenticated=True,
            current=True,
        )
        self.process = LoadedProcessWitness(
            host_id="host-1",
            installed_runtime_root=runtime_root,
            process_id="pid-1",
            process_start_nonce="nonce-1",
            process_generation=3,
            load_generation=4,
            loaded_units=required_loaded_units(parent.core, parent.env),
            dispatch_root=dispatch_root,
            mutation_model=MutationModel.MUTATION_OBSERVED_AND_VERSIONED,
            mutation_generation=5,
            unresolved_answer_bearing_units=(),
            serving_population_root=R("population-1"),
            worker_id="worker-1",
            population_complete=True,
            observed_at=10,
            valid_until=100,
            authenticated=True,
        )
        self.at_use = AtUseObservation(
            now=13,
            host_id="host-1",
            installed_runtime_root=runtime_root,
            process_id="pid-1",
            process_start_nonce="nonce-1",
            process_generation=3,
            load_generation=4,
            loaded_units_root=self.process.loaded_units_root(),
            dispatch_root=dispatch_root,
            mutation_generation=5,
            serving_population_root=R("population-1"),
            selected_worker_id="worker-1",
            immutable_cut_root=None,
            immutable_cut_current=False,
        )

    def decide(self, **kw):
        args = dict(
            core=self.parent.core,
            env=self.parent.env,
            permit=self.parent.permit,
            admission_resolver=self.parent.resolver,
            trace_authority=self.parent.trace,
            ack=self.ack,
            result=self.result,
            independently_recomputed_source_digest=self.parent.env.source_envelope_digest,
            now=13,
            observed_source_root=self.parent.semantic.source_root,
            observed_target_topology_root=self.parent.semantic.target_topology_root,
            installed=self.installed,
            process=self.process,
            at_use=self.at_use,
        )
        args.update(kw)
        return bind_effect_time_activation(**args)

    def process_with_units(self, replacements=None, omit=()):
        values = dict(self.process.loaded_units)
        values.update(replacements or {})
        for key in omit:
            values.pop(key, None)
        p = replace(self.process, loaded_units=tuple(sorted(values.items())))
        a = replace(self.at_use, loaded_units_root=p.loaded_units_root())
        return p, a

    def test_valid(self):
        d = self.decide()
        self.assertEqual(d.disposition, Disposition.ADMIT_D0)
        self.assertIsNotNone(d.activation_witness_root)

    def test_wrong_loaded_adapter_core_holds_even_when_process_is_current(self):
        p, a = self.process_with_units({"awj032.adapter_core_root": R("wrong-core")})
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_LOADED_ADAPTER_CORE_MISMATCH")

    def test_wrong_loaded_source_holds(self):
        p, a = self.process_with_units({"awj032.adapter_source_root": R("wrong-source")})
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_LOADED_SOURCE_MISMATCH")

    def test_wrong_loaded_topology_holds(self):
        p, a = self.process_with_units({"awj032.adapter_target_topology_root": R("wrong-topology")})
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_LOADED_TOPOLOGY_MISMATCH")

    def test_wrong_loaded_runtime_holds(self):
        p, a = self.process_with_units({"awj032.inference_runtime_root": R("wrong-runtime")})
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_LOADED_RUNTIME_MISMATCH")

    def test_missing_required_loaded_unit_holds(self):
        p, a = self.process_with_units(omit=("awj032.adapter_source_root",))
        self.assertTrue(self.decide(process=p, at_use=a).reason.startswith("HOLD_REQUIRED_LOADED_UNIT_MISSING:"))

    def test_duplicate_loaded_unit_name_holds(self):
        dup = self.process.loaded_units + (("awj032.adapter_core_root", self.parent.core.identity_root),)
        p = replace(self.process, loaded_units=dup)
        a = replace(self.at_use, loaded_units_root=p.loaded_units_root())
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_DUPLICATE_LOADED_UNIT_NAME")

    def test_wrong_dispatch_holds_even_when_process_parent_passes(self):
        p = replace(self.process, dispatch_root=R("wrong-dispatch"))
        a = replace(self.at_use, dispatch_root=p.dispatch_root)
        self.assertEqual(self.decide(process=p, at_use=a).reason, "HOLD_ACTIVATION_DISPATCH_MISMATCH")

    def test_different_installed_runtime_holds_even_if_process_parent_matches_it(self):
        other = R("other-runtime")
        i = replace(self.installed, installed_runtime_root=other)
        p = replace(self.process, installed_runtime_root=other)
        a = replace(self.at_use, installed_runtime_root=other)
        self.assertEqual(self.decide(installed=i, process=p, at_use=a).reason, "HOLD_INFERENCE_RUNTIME_NOT_INSTALLED_RUNTIME")

    def test_stale_installed_process_parent_holds(self):
        i = replace(self.installed, current=False)
        self.assertTrue(self.decide(installed=i).reason.startswith("HOLD_PROCESS:"))

    def test_expired_process_holds(self):
        p = replace(self.process, valid_until=12)
        self.assertTrue(self.decide(process=p).reason.startswith("HOLD_PROCESS:"))

    def test_process_reissue_rotates_activation_witness(self):
        first = self.decide()
        p = replace(self.process, process_id="pid-2", process_start_nonce="nonce-2", process_generation=4)
        a = replace(self.at_use, process_id="pid-2", process_start_nonce="nonce-2", process_generation=4)
        second = self.decide(process=p, at_use=a)
        self.assertEqual(second.disposition, Disposition.ADMIT_D0)
        self.assertNotEqual(first.activation_witness_root, second.activation_witness_root)
        self.assertEqual(first.transition_root, second.transition_root)

    def test_load_reissue_rotates_activation_witness(self):
        first = self.decide()
        p = replace(self.process, load_generation=5)
        a = replace(self.at_use, load_generation=5)
        second = self.decide(process=p, at_use=a)
        self.assertEqual(second.disposition, Disposition.ADMIT_D0)
        self.assertNotEqual(first.activation_witness_root, second.activation_witness_root)

    def test_worker_reissue_rotates_activation_witness(self):
        first = self.decide()
        p = replace(self.process, worker_id="worker-2", serving_population_root=R("population-2"))
        a = replace(self.at_use, selected_worker_id="worker-2", serving_population_root=R("population-2"))
        second = self.decide(process=p, at_use=a)
        self.assertEqual(second.disposition, Disposition.ADMIT_D0)
        self.assertNotEqual(first.activation_witness_root, second.activation_witness_root)

    def test_unobservable_mutation_holds(self):
        p = replace(self.process, mutation_model=MutationModel.MUTATION_UNOBSERVABLE)
        self.assertTrue(self.decide(process=p).reason.startswith("HOLD_PROCESS:"))

    def test_mutation_generation_move_holds(self):
        a = replace(self.at_use, mutation_generation=6)
        self.assertTrue(self.decide(at_use=a).reason.startswith("HOLD_PROCESS:"))

    def test_unresolved_lazy_unit_holds(self):
        p = replace(self.process, unresolved_answer_bearing_units=("lazy.adapter",))
        self.assertTrue(self.decide(process=p).reason.startswith("HOLD_PROCESS:"))

    def test_incomplete_population_holds(self):
        p = replace(self.process, population_complete=False)
        self.assertTrue(self.decide(process=p).reason.startswith("HOLD_PROCESS:"))

    def test_transition_bad_result_signature_holds(self):
        bad = replace(self.result, mac=R("bad"))
        self.assertTrue(self.decide(result=bad).reason.startswith("HOLD_TRANSITION:"))

    def test_transition_source_recompute_holds(self):
        self.assertTrue(self.decide(independently_recomputed_source_digest=R("bad")).reason.startswith("HOLD_TRANSITION:"))

    def test_transition_observed_source_move_holds(self):
        self.assertTrue(self.decide(observed_source_root=R("moved")).reason.startswith("HOLD_TRANSITION:"))

    def test_transition_observed_topology_move_holds(self):
        self.assertTrue(self.decide(observed_target_topology_root=R("moved")).reason.startswith("HOLD_TRANSITION:"))

    def test_extra_nonrequired_loaded_unit_is_identity_bearing_but_not_rejected(self):
        p, a = self.process_with_units({"auxiliary.current.unit": R("aux")})
        first = self.decide()
        second = self.decide(process=p, at_use=a)
        self.assertEqual(second.disposition, Disposition.ADMIT_D0)
        self.assertNotEqual(first.activation_witness_root, second.activation_witness_root)

    def test_authority_ceiling(self):
        d = self.decide()
        self.assertFalse(d.effect_authority)
        self.assertFalse(d.training_authority)
        self.assertFalse(d.checkpoint_authority)
        self.assertFalse(d.project_write_authority)
        self.assertFalse(d.gate10)


if __name__ == "__main__":
    unittest.main()
