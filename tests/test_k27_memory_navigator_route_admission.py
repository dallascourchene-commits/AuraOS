import random
import unittest

from tools.arena.k27_memory_navigator.route_card_admission import (
    CapacityEnvelope, Disposition, Polarity, ProofReceipt, RouteIdentity,
    TemporalRequirement, TimingMode, UseContext, admit, canonical_receipt_root,
)

H = "0" * 64
A = "1" * 64
B = "2" * 64


def identity(**kw):
    base = dict(objective_root=H, target_id="MCGPS:TARGET", source_root=A,
                dependency_root=B, map_generation="g1", lifecycle_epoch=7,
                owner_incarnation="boot-a", currentness_generation=11, k27=(1, 0, 2))
    base.update(kw)
    return RouteIdentity(**base)


def envelope(**kw):
    base = dict(hydration=9, route_cost=12, lawfield_crossings=1, disclosure=3)
    base.update(kw)
    return CapacityEnvelope(**base)


def temporal(**kw):
    base = dict(event_time=100, deadline=130, worst_case_finish=120,
                phase_tolerance=4, lawfield_transition=True, irreversible_or_external=False)
    base.update(kw)
    return TemporalRequirement(**base)


def receipt(polarity=Polarity.POSITIVE, **kw):
    t = kw.pop("temporal", temporal())
    return ProofReceipt(polarity=polarity,
                        route_identity=kw.pop("route_identity", identity()),
                        certified_envelope=kw.pop("certified_envelope", envelope()),
                        temporal_mode=t.mode, event_time=t.event_time, **kw)


def use(**kw):
    return UseContext(identity=kw.pop("identity", identity()),
                      envelope=kw.pop("envelope", envelope()),
                      temporal=kw.pop("temporal", temporal()), **kw)


def reference(r, u):
    mode = u.temporal.mode
    if (u.irreversible_effect_already_committed or not u.current_source
            or not u.local_knowledge_sufficient or not u.capability_current
            or not u.disclosure_budget_ok or not u.temporal.deadline_safe):
        return Disposition.HOLD
    hard = r.route_identity.hard_roots() != u.identity.hard_roots()
    if r.polarity is Polarity.NEGATIVE:
        if hard or not u.envelope.no_wider_than(r.certified_envelope) or mode is not r.temporal_mode:
            return Disposition.REPROVE
        moved = (u.identity.currentness_generation != r.route_identity.currentness_generation
                 or u.temporal.event_time != r.event_time)
        if moved:
            return (Disposition.REBIND_NEGATIVE_CURRENTNESS_D0
                    if r.state_independent_negative else Disposition.REPROVE)
        return Disposition.REUSE_NEGATIVE_D0
    if (hard or u.identity.currentness_generation != r.route_identity.currentness_generation
            or u.temporal.event_time != r.event_time or u.envelope != r.certified_envelope
            or mode is not r.temporal_mode):
        return Disposition.REPROVE
    return Disposition.READY_D0


class NavigatorRouteAdmissionTests(unittest.TestCase):
    def test_positive_exact_ready(self):
        self.assertEqual(admit(receipt(), use()).disposition, Disposition.READY_D0)

    def test_positive_currentness_reprove(self):
        self.assertEqual(admit(receipt(), use(identity=identity(currentness_generation=12))).disposition, Disposition.REPROVE)

    def test_positive_event_time_reprove(self):
        self.assertEqual(admit(receipt(), use(temporal=temporal(event_time=101))).disposition, Disposition.REPROVE)

    def test_positive_envelope_must_be_exact(self):
        self.assertEqual(admit(receipt(), use(envelope=envelope(hydration=8))).disposition, Disposition.REPROVE)

    def test_negative_shrink_reuse(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(envelope=envelope(hydration=8, route_cost=10))).disposition, Disposition.REUSE_NEGATIVE_D0)

    def test_negative_widen_reprove(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(envelope=envelope(hydration=10))).disposition, Disposition.REPROVE)

    def test_negative_currentness_rebind(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(identity=identity(currentness_generation=12))).disposition, Disposition.REBIND_NEGATIVE_CURRENTNESS_D0)

    def test_negative_event_time_rebind(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(temporal=temporal(event_time=101))).disposition, Disposition.REBIND_NEGATIVE_CURRENTNESS_D0)

    def test_state_dependent_negative_reprove(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=False)
        self.assertEqual(admit(r, use(identity=identity(currentness_generation=12))).disposition, Disposition.REPROVE)

    def test_lifecycle_is_hard(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(identity=identity(lifecycle_epoch=8))).disposition, Disposition.REPROVE)

    def test_incarnation_is_hard(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(identity=identity(owner_incarnation="boot-b"))).disposition, Disposition.REPROVE)

    def test_dependency_is_hard(self):
        r = receipt(Polarity.NEGATIVE, state_independent_negative=True)
        self.assertEqual(admit(r, use(identity=identity(dependency_root="3" * 64))).disposition, Disposition.REPROVE)

    def test_k27_move_does_not_mint_or_block(self):
        result = admit(receipt(), use(identity=identity(k27=(2, 2, 2))))
        self.assertEqual(result.disposition, Disposition.READY_D0)
        self.assertFalse(result.effect_authority)
        self.assertFalse(result.gate10)

    def test_deadline_miss_holds(self):
        self.assertEqual(admit(receipt(), use(temporal=temporal(worst_case_finish=131))).disposition, Disposition.HOLD)

    def test_unknown_deadline_finish_holds(self):
        self.assertEqual(admit(receipt(), use(temporal=temporal(worst_case_finish=None))).disposition, Disposition.HOLD)

    def test_causal_mode(self):
        self.assertEqual(temporal(deadline=None, worst_case_finish=None,
                                  phase_tolerance=None, lawfield_transition=False).mode,
                         TimingMode.CAUSAL)

    def test_exact_window(self):
        self.assertEqual(temporal(irreversible_or_external=True).mode, TimingMode.EXACT_WINDOW)

    def test_capability_at_use_holds(self):
        self.assertEqual(admit(receipt(), use(capability_current=False)).disposition, Disposition.HOLD)

    def test_knowledge_holds(self):
        self.assertEqual(admit(receipt(), use(local_knowledge_sufficient=False)).disposition, Disposition.HOLD)

    def test_disclosure_holds(self):
        self.assertEqual(admit(receipt(), use(disclosure_budget_ok=False)).disposition, Disposition.HOLD)

    def test_irreversible_already_committed_holds(self):
        self.assertEqual(admit(receipt(), use(irreversible_effect_already_committed=True)).disposition, Disposition.HOLD)

    def test_bool_k27_rejected(self):
        with self.assertRaises(ValueError):
            identity(k27=(True, 0, 1))

    def test_receipt_cannot_mint_authority(self):
        with self.assertRaises(ValueError):
            receipt(authority_minted=True)

    def test_receipt_root_stable(self):
        self.assertEqual(canonical_receipt_root(receipt()), canonical_receipt_root(receipt()))

    def test_randomized_reference_oracle(self):
        rng = random.Random(7107)
        for _ in range(30000):
            neg = rng.random() < 0.55
            r = receipt(Polarity.NEGATIVE if neg else Polarity.POSITIVE,
                        state_independent_negative=(neg and rng.random() < 0.7))
            ident = identity(
                currentness_generation=11 + int(rng.random() < 0.18),
                lifecycle_epoch=7 + int(rng.random() < 0.05),
                owner_incarnation="boot-b" if rng.random() < 0.04 else "boot-a",
                dependency_root="3" * 64 if rng.random() < 0.04 else B,
                k27=(rng.randrange(3), rng.randrange(3), rng.randrange(3)),
            )
            cap = CapacityEnvelope(
                9 + rng.choice([-2, -1, 0, 0, 0, 1]),
                12 + rng.choice([-2, 0, 0, 1]),
                1 + rng.choice([-1, 0, 0, 1]),
                3 + rng.choice([-1, 0, 0, 1]),
            )
            tt = temporal(event_time=100 + int(rng.random() < 0.12),
                          worst_case_finish=131 if rng.random() < 0.025 else 120,
                          irreversible_or_external=(rng.random() < 0.06))
            u = UseContext(identity=ident, envelope=cap, temporal=tt,
                           current_source=rng.random() > .02,
                           capability_current=rng.random() > .02,
                           local_knowledge_sufficient=rng.random() > .02,
                           disclosure_budget_ok=rng.random() > .02,
                           irreversible_effect_already_committed=rng.random() < .005)
            self.assertIs(admit(r, u).disposition, reference(r, u))


if __name__ == "__main__":
    unittest.main()
