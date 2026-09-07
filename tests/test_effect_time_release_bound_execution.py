import unittest
from dataclasses import replace

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext
from tools.arena.installed_runtime_bound_delegation import RuntimeTarget
from tools.project006.installed_runtime_attestation import RuntimeReleaseManifest, HostMeasurement, MeasurementEvidence
from tools.arena.effect_time_loaded_process_currentness import (
    InstalledRuntimeAttestation, LoadedProcessWitness, AtUseObservation, MutationModel,
    Disposition as ProcessDisposition, decide as decide_process,
)
from tools.arena.effect_time_release_bound_execution import *

H = lambda c: c * 64

def fixture():
    operation = StableOperation("arena", H("1"), "effect", H("2"), H("3"))
    op = operation.root()
    hops = (
        DelegationHop("root", frozenset({"run"}), 1, 1, True),
        DelegationHop("worker", frozenset({"run"}), 1, 2, True),
    )
    admission = DomainAdmission("arena", op, H("4"), frozenset({"run"}), 1, 7, True, True)
    ctx = AttemptContext("worker", H("5"), 3, True, H("6"), True, H("2"), frozenset({"run"}), 1)
    manifest = RuntimeReleaseManifest("release-1", "repo", "head-1", 7, op, {"core": H("a"), "plugin": H("b")})
    measurement = HostMeasurement("host", "head-1", dict(manifest.components), "inc-1", H("2"), 100, (1, 2, 3))
    evidence = MeasurementEvidence(measurement.technical_root, manifest.release_root, "verifier", "observer", True, True, True, True, 90, 200)
    target = RuntimeTarget("host", "inc-1", manifest.release_root)
    process = LoadedProcessWitness(
        "host", manifest.release_root, "pid", "start", 4, 9,
        (("core", H("a")), ("plugin", H("b"))), "dispatch",
        MutationModel.MUTATION_OBSERVED_AND_VERSIONED, 2, (), "population", "worker-1",
        True, 110, 180, True,
    )
    at_use = AtUseObservation(120, "host", manifest.release_root, "pid", "start", 4, 9,
                              process.loaded_units_root(), "dispatch", 2, "population", "worker-1", None, True)
    scope = ExecutableScope(("core", "plugin"))
    return operation, hops, admission, ctx, manifest, target, measurement, evidence, process, at_use, scope

def run(f=None, **kw):
    vals = list(f or fixture())
    names = ["operation","hops","admission","ctx","manifest","target","measurement","evidence","process","at_use","executable_scope"]
    data = dict(zip(names, vals)); data.update(kw)
    return bind_effect_time(**data, owner_reported_updated=True, now_ms=120)

class O7Tests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(run().disposition, ExecutionDisposition.ADMIT_D0)

    def test_direct_parent_dual_pass_wrong_bytes_is_closed(self):
        f = list(fixture()); manifest, measurement, evidence = f[4], f[6], f[7]
        wrong = replace(f[8], loaded_units=(("core", H("c")), ("plugin", H("d"))))
        obs = replace(f[9], loaded_units_root=wrong.loaded_units_root())
        derived = InstalledRuntimeAttestation("host", manifest.release_root, manifest.owner_generation,
                                              measurement.observed_at_ms, evidence.expires_at_ms, True, True)
        self.assertEqual(decide_process(derived, wrong, obs).disposition, ProcessDisposition.ADMIT_D0)
        f[8], f[9] = wrong, obs
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_LOADED_UNIT_HASH_MISMATCH)

    def test_missing_loaded_unit_holds(self):
        f = list(fixture()); p = replace(f[8], loaded_units=(("core", H("a")),)); f[8]=p; f[9]=replace(f[9], loaded_units_root=p.loaded_units_root())
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_LOADED_UNIT_SET_MISMATCH)

    def test_extra_loaded_unit_holds(self):
        f=list(fixture()); p=replace(f[8],loaded_units=f[8].loaded_units+(("rogue",H("c")),)); f[8]=p; f[9]=replace(f[9],loaded_units_root=p.loaded_units_root())
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_LOADED_UNIT_SET_MISMATCH)

    def test_duplicate_loaded_unit_holds(self):
        f=list(fixture()); p=replace(f[8],loaded_units=(("core",H("a")),("core",H("a")),("plugin",H("b")))); f[8]=p; f[9]=replace(f[9],loaded_units_root=p.loaded_units_root())
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_LOADED_UNIT_SET_MISMATCH)

    def test_scope_missing_from_manifest_holds(self):
        self.assertEqual(run(executable_scope=ExecutableScope(("core","missing"))).disposition, ExecutionDisposition.HOLD_EXECUTABLE_SCOPE_INVALID)

    def test_duplicate_scope_holds(self):
        self.assertEqual(run(executable_scope=ExecutableScope(("core","core"))).disposition, ExecutionDisposition.HOLD_EXECUTABLE_SCOPE_INVALID)

    def test_same_cut_required(self):
        f=list(fixture()); f[9]=replace(f[9],now=121)
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_TIME_CUT_MISMATCH)

    def test_future_process_witness_holds(self):
        f=list(fixture()); f[8]=replace(f[8],observed_at=121)
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_PROCESS_FUTURE_OBSERVATION)

    def test_process_restart_holds(self):
        f=list(fixture()); f[9]=replace(f[9],process_start_nonce="restart")
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_EFFECT_TIME_PROCESS)

    def test_dispatch_move_holds(self):
        f=list(fixture()); f[9]=replace(f[9],dispatch_root="moved")
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_EFFECT_TIME_PROCESS)

    def test_parent_runtime_bound_hold_propagates(self):
        f=list(fixture()); f[3]=replace(f[3],source_incarnation_root=H("9"))
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_RUNTIME_BOUND)

    def test_stale_measurement_holds(self):
        f=list(fixture()); f[7]=replace(f[7],expires_at_ms=119)
        self.assertEqual(run(f).disposition, ExecutionDisposition.HOLD_RUNTIME_BOUND)

    def test_k27_navigation_does_not_rotate_permit(self):
        f1=fixture(); d1=run(f1)
        f2=list(f1); f2[6]=replace(f2[6],k27_coordinate=(26,25,24)); d2=run(f2)
        self.assertEqual(d1.execution_permit_root,d2.execution_permit_root)

    def test_authority_ceiling(self):
        d=run(); self.assertFalse(d.effect_authority or d.training_authority or d.checkpoint_authority or d.project_write_authority or d.gate10)

if __name__ == "__main__": unittest.main()
