from __future__ import annotations

from dataclasses import replace
import itertools
import random
import unittest

from selective_revalidation import (
    CurrentnessState,
    Decision,
    EvidenceLeaf,
    TransferEstimate,
    changed_dimensions,
    revalidate,
)


def state(**changes):
    base = CurrentnessState(
        model_source_rev="model:g1",
        airllm_source_rev="airllm:g1",
        topology_rev="topology:g1",
        tokenizer_rev="tokenizer:g1",
        runtime_rev="runtime:g1",
        adapter_rev="adapter:g1",
        router_rev="router:g1",
        pager_rev="pager:g1",
        calibration_rev="cal:g1",
        cost_model_rev="cost:g1",
        authority_epoch="D0_NONPROMOTING",
        gate_state="NO_GATE10",
    )
    return replace(base, **changes)


def estimate(s=None, **changes):
    s = s or state()
    base = TransferEstimate(
        model_source_rev=s.model_source_rev,
        topology_rev=s.topology_rev,
        calibration_rev=s.calibration_rev,
        cost_model_rev=s.cost_model_rev,
        p_hit=0.80,
        miss_stall_seconds=0.050,
        logical_bytes=1_000_000,
        effective_storage_bytes_per_second=100_000_000,
        eviction_penalty_seconds=0.001,
        rework_penalty_seconds=0.001,
        energy_joules=0.5,
    )
    return replace(base, **changes)


LEAVES = (
    EvidenceLeaf("source_admission", frozenset({"model_source_rev", "airllm_source_rev", "topology_rev", "tokenizer_rev"})),
    EvidenceLeaf("runtime_workcell", frozenset({"runtime_rev", "adapter_rev"})),
    EvidenceLeaf("router_pager_contract", frozenset({"router_rev", "pager_rev", "topology_rev"})),
    EvidenceLeaf("transfer_calibration", frozenset({"calibration_rev", "model_source_rev", "topology_rev"})),
    EvidenceLeaf("transfer_cost_model", frozenset({"cost_model_rev", "pager_rev"})),
    EvidenceLeaf("authority_gate", frozenset({"authority_epoch", "gate_state"})),
)


class SelectiveRevalidationTests(unittest.TestCase):
    def test_no_delta_positive_margin_is_plan_eligible(self):
        s = state()
        r = revalidate(s, s, estimate(s), LEAVES)
        self.assertEqual(r.decision, Decision.PLAN_ELIGIBLE_D0)
        self.assertEqual(r.changed_dimensions, ())
        self.assertEqual(r.reproof_leaves, ())

    def test_model_delta_reopens_only_declared_dependents(self):
        p = state()
        c = state(model_source_rev="model:g2")
        e = estimate(c)
        r = revalidate(p, c, e, LEAVES)
        self.assertEqual(r.decision, Decision.REPROOF_REQUIRED)
        self.assertEqual(set(r.reproof_leaves), {"source_admission", "transfer_calibration"})
        self.assertNotIn("runtime_workcell", r.reproof_leaves)
        self.assertNotIn("transfer_cost_model", r.reproof_leaves)

    def test_cost_model_delta_reopens_only_cost_leaf(self):
        p = state()
        c = state(cost_model_rev="cost:g2")
        r = revalidate(p, c, estimate(c), LEAVES)
        self.assertEqual(r.reproof_leaves, ("transfer_cost_model",))

    def test_stale_estimate_abstains_before_reuse(self):
        p = state()
        c = state(topology_rev="topology:g2")
        r = revalidate(p, c, estimate(p), LEAVES)
        self.assertEqual(r.decision, Decision.ABSTAIN_STALE_ESTIMATE)

    def test_low_confidence_abstains(self):
        s = state()
        r = revalidate(s, s, estimate(s, p_hit=0.20), LEAVES, min_hit_probability=0.50)
        self.assertEqual(r.decision, Decision.ABSTAIN_LOW_CONFIDENCE)

    def test_nonpositive_margin_abstains(self):
        s = state()
        r = revalidate(s, s, estimate(s, p_hit=0.9, miss_stall_seconds=0.001, logical_bytes=100_000_000), LEAVES)
        self.assertEqual(r.decision, Decision.ABSTAIN_NONPOSITIVE_MARGIN)

    def test_latency_value_cannot_pay_energy_debt(self):
        s = state()
        r = revalidate(s, s, estimate(s, p_hit=1.0, miss_stall_seconds=5.0, energy_joules=10.0), LEAVES, energy_budget_joules=1.0)
        self.assertEqual(r.decision, Decision.ABSTAIN_ENERGY_DEBT)

    def test_authority_change_holds_even_if_economics_are_good(self):
        p = state()
        c = state(authority_epoch="PROMOTED")
        r = revalidate(p, c, estimate(c), LEAVES)
        self.assertEqual(r.decision, Decision.HOLD_AUTHORITY)

    def test_eight_corner_crystalline_lattice(self):
        # estimate-current × positive-margin × energy-pass; only the keeper corner may plan.
        admitted = 0
        for estimate_current, positive_margin, energy_pass in itertools.product([False, True], repeat=3):
            p = state()
            c = state()
            e = estimate(c)
            if not estimate_current:
                e = replace(e, model_source_rev="model:stale")
            if not positive_margin:
                e = replace(e, miss_stall_seconds=0.001, logical_bytes=100_000_000)
            if not energy_pass:
                e = replace(e, energy_joules=10.0)
            r = revalidate(p, c, e, LEAVES, energy_budget_joules=1.0)
            admitted += r.decision is Decision.PLAN_ELIGIBLE_D0
        self.assertEqual(admitted, 1)

    def test_hyperscale_1000_selective_reproof_and_no_stale_admission(self):
        rng = random.Random(722803)
        fields = [
            "model_source_rev", "airllm_source_rev", "topology_rev", "tokenizer_rev",
            "runtime_rev", "adapter_rev", "router_rev", "pager_rev",
            "calibration_rev", "cost_model_rev",
        ]
        stale_admissions = 0
        overbroad_reproofs = 0
        seen_decisions = set()
        for i in range(1000):
            p = state()
            changed = rng.sample(fields, rng.randint(0, 3))
            kwargs = {name: getattr(p, name) + ":next" for name in changed}
            c = state(**kwargs)
            e = estimate(c)
            if rng.random() < 0.20:
                e = replace(e, calibration_rev="cal:stale")
            if rng.random() < 0.20:
                e = replace(e, p_hit=0.2)
            r = revalidate(p, c, e, LEAVES)
            seen_decisions.add(r.decision)
            expected = {
                leaf.name for leaf in LEAVES if leaf.dependencies & set(changed_dimensions(p, c))
            }
            overbroad_reproofs += set(r.reproof_leaves) != expected
            if r.decision is Decision.PLAN_ELIGIBLE_D0:
                stale_admissions += any(
                    getattr(e, f) != getattr(c, f)
                    for f in ("model_source_rev", "topology_rev", "calibration_rev", "cost_model_rev")
                )
            self.assertEqual(len(r.y13), 13)
        self.assertEqual(stale_admissions, 0)
        self.assertEqual(overbroad_reproofs, 0)
        self.assertGreaterEqual(len(seen_decisions), 4)


if __name__ == "__main__":
    unittest.main()
