import unittest
from research_factory import *
class T(unittest.TestCase):
 def test_1000(self): self.assertEqual(len(generate()),1000)
 def test_unique(self): self.assertEqual(len({x.id for x in generate()}),1000)
 def test_hot(self): self.assertEqual(len(hot_frontier(generate(),50)),50)
 def test_diverse_primitives(self): self.assertEqual(set(x.primitive for x in hot_frontier(generate(),50)),set(PRIMITIVES))
 def test_diverse_concerns(self): self.assertEqual(set(x.concern for x in hot_frontier(generate(),50)),set(CONCERNS))
 def test_diverse_ops(self): self.assertEqual(set(x.operator for x in hot_frontier(generate(),50)),set(OPERATORS))
 def test_nonpromotion(self): self.assertFalse(receipt(generate(),hot_frontier(generate()))['candidate_is_finding'])
 def test_k27_nonauthority(self): self.assertFalse(receipt(generate(),hot_frontier(generate()))['k27_is_authority'])
if __name__=='__main__':unittest.main()
