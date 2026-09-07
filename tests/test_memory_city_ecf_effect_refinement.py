from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import sys
import unittest

ARENA = Path(__file__).resolve().parents[1] / "tools" / "arena"
sys.path.insert(0, str(ARENA))

from memory_city_consequence_refinement import (  # noqa: E402
    EffectIntent,
    EffectObligationProjection,
    compile_effect_refinement,
)
from memory_city_ecf_adapter import (  # noqa: E402
    ECFAdmissionIndex,
    ECFCurrentCut,
    ECFLeafAdmissionWitness,
)
from memory_city_ecf_effect_refinement import (  # noqa: E402
    EffectObligationObservation,
    OWNER_TRUST_BOUNDARY,
    compile_ecf_effect_refinement,
)


def hx(value: str) -> str:
    return sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Cert:
    status: str
    receipt_root: str
    coverage_receipt_root: str
    program_root: str
    sealed_domain_root: str
    consequence_root: str
    transition_model_root: str
    coverage_generation: int
    horizon: int
    future_congruence_root: str
    binding_roots: tuple[str, ...]


def fixture(
    tag: str = "x",
    *,
    admit: bool = True,
    cut_mut: dict | None = None,
    witness_mut: dict | None = None,
    intent: EffectIntent | None = None,
    obs: EffectObligationObservation | None = None,
):
    binding = hx(f"binding:{tag}")
    cert = Cert(
        "READY_D0",
        hx(f"rr:{tag}"),
        hx(f"cov:{tag}"),
        hx(f"prog:{tag}"),
        hx(f"dom:{tag}"),
        hx(f"cons:{tag}"),
        hx(f"trans:{tag}"),
        7,
        2,
        hx(f"future:{tag}"),
        (binding,),
    )
    intent = intent or EffectIntent(hx(f"intent:{tag}"), hx(f"ed:{tag}"), hx(f"ep:{tag}"))
    obs = obs or EffectObligationObservation(
        binding,
        hx(f"obl:{tag}"),
        hx(f"source:{tag}"),
        hx(f"nuis:{tag}"),
    )
    cut = ECFCurrentCut(
        "J",
        4,
        hx("registry"),
        "producer",
        "inc-7",
        "memory_city.effect_obligation",
        hx("cut"),
    )
    if cut_mut:
        cut = replace(cut, **cut_mut)
    witness = ECFLeafAdmissionWitness(
        "w1",
        obs.evidence_digest(intent),
        "J",
        4,
        hx("registry"),
        "producer",
        "inc-7",
        "memory_city.effect_obligation",
        hx("cut"),
        hx("auth"),
        hx("grant"),
    )
    if witness_mut:
        witness = replace(witness, **witness_mut)
    roots = (witness.witness_root,) if admit else ()
    index = ECFAdmissionIndex(cut, (witness,), admitted_witness_roots=roots)
    return cert, intent, obs, index, witness


def multi_fixture(tag: str = "multi"):
    bindings = (hx(f"binding:{tag}:a"), hx(f"binding:{tag}:b"))
    cert = Cert(
        "READY_D0",
        hx(f"rr:{tag}"),
        hx(f"cov:{tag}"),
        hx(f"prog:{tag}"),
        hx(f"dom:{tag}"),
        hx(f"cons:{tag}"),
        hx(f"trans:{tag}"),
        7,
        2,
        hx(f"future:{tag}"),
        tuple(sorted(bindings)),
    )
    intent = EffectIntent(hx(f"intent:{tag}"), hx(f"ed:{tag}"), hx(f"ep:{tag}"))
    observations = tuple(
        EffectObligationObservation(
            binding,
            hx(f"obl:{tag}:{i}"),
            hx(f"source:{tag}:{i}"),
            hx(f"nuis:{tag}:{i}"),
        )
        for i, binding in enumerate(bindings)
    )
    cut = ECFCurrentCut(
        "J",
        4,
        hx("registry"),
        "producer",
        "inc-7",
        "memory_city.effect_obligation",
        hx("cut"),
    )
    witnesses = tuple(
        ECFLeafAdmissionWitness(
            f"w{i}",
            obs.evidence_digest(intent),
            "J",
            4,
            hx("registry"),
            "producer",
            "inc-7",
            "memory_city.effect_obligation",
            hx("cut"),
            hx(f"auth:{i}"),
            hx(f"grant:{i}"),
        )
        for i, obs in enumerate(observations)
    )
    index = ECFAdmissionIndex(
        cut,
        witnesses,
        admitted_witness_roots=tuple(w.witness_root for w in witnesses),
    )
    return cert, intent, observations, index


class ECFEffectRefinementTests(unittest.TestCase):
    def test_valid_ecf_admission_is_only_ready_path(self):
        cert, intent, obs, index, witness = fixture()
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.plan.status, "READY_REFINED_D0")
        self.assertEqual(result.plan.subclasses[0].evidence_roots, (witness.witness_root,))
        self.assertFalse(result.effect_authority)
        self.assertFalse(result.upstream_owner_authentication_claimed)
        self.assertEqual(result.owner_trust_boundary, OWNER_TRUST_BOUNDARY)

    def test_self_attested_old_o8_baseline_would_ready_but_seal_holds(self):
        cert, intent, obs, index, _ = fixture(admit=False)
        baseline = compile_effect_refinement(
            (
                EffectObligationProjection(
                    obs.read_binding_root,
                    obs.effect_obligation_root,
                    hx("fake"),
                    True,
                    True,
                    obs.nuisance_configuration_root,
                ),
            ),
            cert,
            intent,
        )
        sealed = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(baseline.status, "READY_REFINED_D0")
        self.assertEqual(sealed.plan.status, "PARTIAL_HOLD_D0")
        self.assertEqual(sealed.per_binding_status[0][1], "HOLD_ECF_WITNESS_NOT_ADMITTED")

    def test_obligation_substitution_invalidates_admitted_witness(self):
        cert, intent, obs, index, _ = fixture()
        moved = replace(obs, effect_obligation_root=hx("moved"))
        result = compile_ecf_effect_refinement((moved,), cert, intent, index)
        self.assertEqual(result.plan.status, "PARTIAL_HOLD_D0")
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_WITNESS_NOT_FOUND")

    def test_intent_substitution_invalidates_admitted_witness(self):
        cert, intent, obs, index, _ = fixture()
        moved = EffectIntent(hx("new-intent"), intent.effect_domain_root, intent.program_root)
        result = compile_ecf_effect_refinement((obs,), cert, moved, index)
        self.assertEqual(result.plan.status, "PARTIAL_HOLD_D0")

    def test_source_observation_substitution_invalidates_witness(self):
        cert, intent, obs, index, _ = fixture()
        moved = replace(obs, source_observation_root=hx("new-source"))
        result = compile_ecf_effect_refinement((moved,), cert, intent, index)
        self.assertEqual(result.plan.status, "PARTIAL_HOLD_D0")

    def test_jurisdiction_generation_move_holds(self):
        cert, intent, obs, index, _ = fixture(cut_mut={"jurisdiction_generation": 5})
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_JURISDICTION_CURRENTNESS")

    def test_registry_move_holds(self):
        cert, intent, obs, index, _ = fixture(cut_mut={"producer_registry_root": hx("registry2")})
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_PRODUCER_REGISTRY_CURRENTNESS")

    def test_producer_incarnation_move_holds(self):
        cert, intent, obs, index, _ = fixture(cut_mut={"producer_incarnation": "inc-8"})
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_PRODUCER_CURRENTNESS")

    def test_scope_move_holds(self):
        cert, intent, obs, index, _ = fixture(cut_mut={"evidence_scope": "memory_city.other_scope"})
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_WITNESS_NOT_FOUND")

    def test_coherent_cut_move_holds(self):
        cert, intent, obs, index, _ = fixture(cut_mut={"coherent_cut_root": hx("cut2")})
        result = compile_ecf_effect_refinement((obs,), cert, intent, index)
        self.assertEqual(result.per_binding_status[0][1], "HOLD_ECF_COHERENT_CUT_MISMATCH")

    def test_nuisance_change_does_not_split_plan(self):
        cert, intent, obs, index, _ = fixture()
        first = compile_ecf_effect_refinement((obs,), cert, intent, index)
        second = compile_ecf_effect_refinement(
            (replace(obs, nuisance_configuration_root=hx("n2")),), cert, intent, index
        )
        self.assertEqual(first.plan.plan_root, second.plan.plan_root)
        self.assertEqual(first.plan.subclasses[0].subclass_root, second.plan.subclasses[0].subclass_root)

    def test_binding_envelope_mismatch_holds(self):
        cert, intent, obs, index, _ = fixture()
        detached = replace(obs, read_binding_root=hx("detached"))
        result = compile_ecf_effect_refinement((detached,), cert, intent, index)
        self.assertEqual(result.plan.status, "HOLD_BINDING_ENVELOPE_D0")

    def test_ecf_cut_is_bound_into_refinement_receipt(self):
        cert, intent, obs, index, _ = fixture()
        first = compile_ecf_effect_refinement((obs,), cert, intent, index)
        cert2, intent2, obs2, index2, _ = fixture("x", cut_mut={"coherent_cut_root": hx("cut2")})
        second = compile_ecf_effect_refinement((obs2,), cert2, intent2, index2)
        self.assertNotEqual(first.evidence_set_root, second.evidence_set_root)

    def test_multibinding_observation_order_is_not_identity(self):
        cert, intent, observations, index = multi_fixture()
        first = compile_ecf_effect_refinement(observations, cert, intent, index)
        second = compile_ecf_effect_refinement(tuple(reversed(observations)), cert, intent, index)
        self.assertEqual(first.plan.plan_root, second.plan.plan_root)
        self.assertEqual(first.evidence_set_root, second.evidence_set_root)

    def test_fabricated_upstream_admission_set_is_explicit_out_of_scope_canary(self):
        # This intentionally demonstrates the trust boundary: if an attacker is
        # allowed to impersonate the upstream ECF owner and fabricate the
        # admitted-witness set itself, this D0 adapter cannot authenticate that
        # owner. The result MUST stay visible in proof receipts as zero claim of
        # upstream-owner authentication.
        cert, intent, obs, _, witness = fixture(admit=False)
        cut = ECFCurrentCut(
            "J", 4, hx("registry"), "producer", "inc-7",
            "memory_city.effect_obligation", hx("cut")
        )
        fabricated = ECFAdmissionIndex(cut, (witness,), admitted_witness_roots=(witness.witness_root,))
        result = compile_ecf_effect_refinement((obs,), cert, intent, fabricated)
        self.assertEqual(result.plan.status, "READY_REFINED_D0")
        self.assertFalse(result.upstream_owner_authentication_claimed)


if __name__ == "__main__":
    unittest.main()
