from __future__ import annotations

import unittest

import tools.awj032.glm53_g6_admission_identity_binding_addendum as a
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as g6


class AbsorbedG6IdentityAddendumTests(unittest.TestCase):
    def test_addendum_is_not_an_independent_semantic_owner(self):
        status = a.canonical_owner_status()
        self.assertTrue(status["absorbed"])
        self.assertFalse(status["independent_semantic_owner"])
        self.assertEqual(status["closure_credit"], 0)
        self.assertEqual(status["canonical_schema"], g6.SCHEMA)

    def test_all_w3_findings_live_in_canonical_owner(self):
        for law in a.ABSORBED_LAWS:
            self.assertIn(law, g6.LAWS)


if __name__ == "__main__":
    unittest.main()
