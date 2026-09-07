import unittest
from tools.arena.triadic_confluence_runtime import *


def art(i, clauses, ceiling=5, verified=True):
    return Artifact(i, tuple(clauses), authority_ceiling=ceiling, terminal_verified=verified)

def c(key, value, consequence, scope="GLOBAL", authority=1):
    return Clause(key, value, consequence, scope=scope, authority=authority)

class TestTriadicConfluence(unittest.TestCase):
    def test_foreign_parents_required(self):
        a=art("A",[c("x","1","x")])
        with self.assertRaises(ValueError): confluence_rebase(a,a)

    def test_verified_parents_required(self):
        with self.assertRaises(ValueError): confluence_rebase(art("A",[],verified=False),art("B",[]))

    def test_complementary_preserves_both(self):
        r=confluence_rebase(art("A",[c("orientation","walk","learn relations")]), art("B",[c("orientation","compile","current situatedness")]))
        self.assertEqual(r.action, RebaseAction.COMPOSE)
        self.assertEqual(len(r.clauses),2)
        self.assertTrue(r.durable_generation)

    def test_equivalent_dedupes_provenance(self):
        a=art("A",[c("rule","stop","fixed point")])
        b=art("B",[c("rule","stop","fixed point")])
        base=semantic_normal_form_hash(a.clauses)
        r=confluence_rebase(a,b,prior_normal_form_hash=base)
        self.assertEqual(r.action,RebaseAction.COLLAPSE_SAME)
        self.assertFalse(r.durable_generation)
        self.assertEqual(set(r.clauses[0].provenance),{"A","B"})

    def test_conflict_holds(self):
        r=confluence_rebase(art("A",[c("gate","allow","promotion",authority=1)]),art("B",[c("gate","deny","promotion",authority=1)]))
        self.assertEqual(r.action,RebaseAction.HOLD)
        self.assertFalse(r.durable_generation)
        self.assertTrue(r.unresolved_conflicts)

    def test_dominance_is_scoped(self):
        r=confluence_rebase(art("A",[c("gate","allow","promotion",authority=1)]),art("B",[c("gate","deny","promotion",authority=3)]))
        self.assertEqual(r.action,RebaseAction.SUPERSEDE_SCOPED)
        self.assertEqual(r.clauses[0].value,"deny")

    def test_specialization_preserves_both(self):
        r=confluence_rebase(art("A",[c("runtime","arena","identity","GLOBAL")]),art("B",[c("runtime","owner-host","identity","LAPTOP")]))
        self.assertEqual(len(r.clauses),2)
        self.assertIn(Relation.SPECIALIZES,{d.relation for d in r.decisions})

    def test_authority_ceiling_is_meet(self):
        r=confluence_rebase(art("A",[],ceiling=8),art("B",[],ceiling=3))
        self.assertEqual(r.authority_ceiling,3)

    def test_verified_compression_can_earn_amendment_without_semantic_change(self):
        a=art("A",[c("rule","stop","fixed point")])
        b=art("B",[c("rule","stop","fixed point")])
        base=semantic_normal_form_hash(a.clauses)
        d=MaterialDelta("COMPRESSION","fewer hydrated bytes",True,1000,400)
        r=confluence_rebase(a,b,material_deltas=[d],prior_normal_form_hash=base)
        self.assertEqual(r.action,RebaseAction.AMEND)
        self.assertTrue(r.durable_generation)

    def test_unverified_compression_gets_zero_credit(self):
        a=art("A",[c("rule","stop","fixed point")]); b=art("B",[c("rule","stop","fixed point")])
        base=semantic_normal_form_hash(a.clauses)
        r=confluence_rebase(a,b,material_deltas=[MaterialDelta("COMPRESSION","claimed",False,100,10)],prior_normal_form_hash=base)
        self.assertEqual(r.action,RebaseAction.COLLAPSE_SAME)

    def test_regressive_compression_gets_zero_credit(self):
        a=art("A",[c("rule","stop","fixed point")]); b=art("B",[c("rule","stop","fixed point")])
        base=semantic_normal_form_hash(a.clauses)
        r=confluence_rebase(a,b,material_deltas=[MaterialDelta("COMPRESSION","worse",True,100,101)],prior_normal_form_hash=base)
        self.assertEqual(r.action,RebaseAction.COLLAPSE_SAME)

    def test_refinement_debt_increments_on_noop(self):
        a=art("A",[c("r","x","c")]); b=art("B",[c("r","x","c")]); base=semantic_normal_form_hash(a.clauses)
        r=confluence_rebase(a,b,prior_normal_form_hash=base,refinement_debt=1)
        self.assertEqual(r.refinement_debt,2)

    def test_material_semantic_delta_resets_debt(self):
        r=confluence_rebase(art("A",[c("a","1","a")]),art("B",[c("b","1","b")]),material_deltas=[MaterialDelta("SEMANTIC","new invariant",True)],refinement_debt=4)
        self.assertEqual(r.refinement_debt,0)

    def test_idempotence_semantic_normal_form(self):
        a=art("A",[c("r","x","c")]); b=art("B",[c("r","x","c")])
        r1=confluence_rebase(a,b)
        child=art("C",r1.clauses)
        r2=confluence_rebase(child,art("D",r1.clauses))
        self.assertEqual(r1.normal_form_hash,r2.normal_form_hash)

    def test_commutative_for_compatible_parents(self):
        a=art("A",[c("walk","yes","learn")]); b=art("B",[c("compile","yes","situate")])
        r1=confluence_rebase(a,b); r2=confluence_rebase(b,a)
        self.assertEqual(r1.normal_form_hash,r2.normal_form_hash)
        self.assertEqual(r1.authority_ceiling,r2.authority_ceiling)

    def test_deterministic_digest(self):
        a=art("A",[c("walk","yes","learn")]); b=art("B",[c("compile","yes","situate")])
        self.assertEqual(result_digest(confluence_rebase(a,b)),result_digest(confluence_rebase(a,b)))

    def test_provenance_retains_both_parents(self):
        r=confluence_rebase(art("A",[c("r","x","c")]),art("B",[c("r","x","c")]))
        self.assertEqual(set(r.clauses[0].provenance),{"A","B"})

    def test_unknown_delta_cannot_earn_generation_on_same_state(self):
        a=art("A",[c("r","x","c")]); b=art("B",[c("r","x","c")]); base=semantic_normal_form_hash(a.clauses)
        r=confluence_rebase(a,b,material_deltas=[MaterialDelta("WORDING","nicer prose",True)],prior_normal_form_hash=base)
        self.assertEqual(r.action,RebaseAction.COLLAPSE_SAME)

    def test_multi_clause_same_topic_does_not_drop_unpaired(self):
        a=art("A",[c("orientation","walk","learn"),c("orientation","triad","challenge")])
        b=art("B",[c("orientation","compile","situate")])
        r=confluence_rebase(a,b)
        self.assertEqual(len(r.clauses),3)
        self.assertFalse(r.unresolved_conflicts)

    def test_multiclause_commutative(self):
        a=art("A",[c("orientation","walk","learn"),c("orientation","triad","challenge")])
        b=art("B",[c("orientation","compile","situate"),c("orientation","stop","fixed-point")])
        self.assertEqual(confluence_rebase(a,b).normal_form_hash,confluence_rebase(b,a).normal_form_hash)

if __name__ == "__main__": unittest.main(verbosity=2)
