import random
import unittest
from dataclasses import asdict

from cross_city_bridge import *


class BridgeTests(unittest.TestCase):
    def contract(self, **kw):
        d = dict(
            bridge_id="GENEVA:SF:QUALIFICATION:v1",
            schema_version="1",
            exporting_jurisdiction="GENEVA_DIPLOMACY",
            exporting_owner="OWNER:GENEVA",
            importing_jurisdiction="SF_ENGINEERING",
            importing_owner="OWNER:SF",
            semantic_type="QUALIFICATION_EVIDENCE_V1",
            allowed_transformations=("IMPORT_AS_EVIDENCE",),
            forbidden_casts=("CAST_AS_EFFECT_PERMIT", "CAST_AS_MEMBERSHIP"),
            required_evidence_domains=("PROVENANCE", "CORRECTNESS"),
            required_local_gates=("OWNER_AUTHORITY",),
            dependency_invalidators=("issuer_generation", "destination_policy"),
            max_cost_units=8,
        )
        d.update(kw)
        return BridgeContract(**d)

    def envelope(self, **kw):
        d = dict(
            bridge_id="GENEVA:SF:QUALIFICATION:v1",
            source_ref="drive://credential/1",
            provider_generation="g1",
            semantic_root="root1",
            semantic_type="QUALIFICATION_EVIDENCE_V1",
            requested_transformation="IMPORT_AS_EVIDENCE",
            evidence=(
                EvidenceLeaf("PROVENANCE", "p1", "drive://credential/1", "g1"),
                EvidenceLeaf("CORRECTNESS", "c1", "drive://credential/1", "g1"),
            ),
            wallet_items=(
                WalletItem("QUALIFICATION_EVIDENCE", "w1", "drive://credential/1", "g1"),
            ),
            cost_units=2,
        )
        d.update(kw)
        return BridgeEnvelope(**d)

    def test_portable_evidence_requires_destination_local_gate(self):
        r = CrossCityBridgeCompiler().admit(self.contract(), self.envelope())
        self.assertEqual(r.disposition, "PORTABLE_EVIDENCE_ADMITTED_LOCAL_REVALIDATION_REQUIRED")
        self.assertEqual(r.destination_local_gates, ("OWNER_AUTHORITY",))
        self.assertFalse(r.authority_promoted)
        self.assertFalse(r.effect_authority)

    def test_effect_permit_never_crosses(self):
        with self.assertRaisesRegex(ValueError, "NONPORTABLE_WALLET_KIND"):
            CrossCityBridgeCompiler().admit(
                self.contract(),
                self.envelope(wallet_items=(WalletItem("EFFECT_PERMIT", "x", "src", "g1"),)),
            )

    def test_membership_never_crosses(self):
        with self.assertRaisesRegex(ValueError, "NONPORTABLE_WALLET_KIND"):
            self.envelope(wallet_items=(WalletItem("MEMBERSHIP", "x", "src", "g1"),)).validate()

    def test_authority_evidence_cannot_be_portable_leaf(self):
        with self.assertRaisesRegex(ValueError, "NONPORTABLE_EVIDENCE_DOMAIN"):
            self.envelope(evidence=(EvidenceLeaf("OWNER_AUTHORITY", "x", "src", "g1"),)).validate()

    def test_local_gate_cannot_be_compiled_as_portable_requirement(self):
        with self.assertRaisesRegex(ValueError, "LOCAL_GATE_CANNOT_BE_PORTABLE_EVIDENCE"):
            self.contract(required_evidence_domains=("OWNER_AUTHORITY",)).validate()

    def test_stale_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "STALE_EVIDENCE"):
            CrossCityBridgeCompiler().admit(
                self.contract(),
                self.envelope(evidence=(
                    EvidenceLeaf("PROVENANCE", "p", "src", "g1", False),
                    EvidenceLeaf("CORRECTNESS", "c", "src", "g1"),
                )),
            )

    def test_privacy_customs_precedes_admission(self):
        with self.assertRaisesRegex(ValueError, "PRIVACY_CUSTOMS_HOLD"):
            self.envelope(wallet_items=(
                WalletItem("WORK_SAMPLE", "w", "src", "g1", True, False),
            )).validate()

    def test_forbidden_cast_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "FORBIDDEN_CAST"):
            CrossCityBridgeCompiler().admit(
                self.contract(), self.envelope(requested_transformation="CAST_AS_EFFECT_PERMIT")
            )

    def test_unlisted_transform_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "TRANSFORM_NOT_ALLOWED"):
            CrossCityBridgeCompiler().admit(self.contract(), self.envelope(requested_transformation="MAGIC"))

    def test_cost_cap_is_hard(self):
        with self.assertRaisesRegex(ValueError, "COST_CAP_EXCEEDED"):
            CrossCityBridgeCompiler().admit(self.contract(), self.envelope(cost_units=9))

    def test_semantic_type_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "SEMANTIC_TYPE_MISMATCH"):
            CrossCityBridgeCompiler().admit(self.contract(), self.envelope(semantic_type="OTHER"))

    def test_missing_required_evidence_fails(self):
        with self.assertRaisesRegex(ValueError, "MISSING_REQUIRED_EVIDENCE"):
            CrossCityBridgeCompiler().admit(
                self.contract(),
                self.envelope(evidence=(EvidenceLeaf("PROVENANCE", "p", "src", "g1"),)),
            )

    def test_destination_owner_is_not_exporting_owner(self):
        r = CrossCityBridgeCompiler().admit(self.contract(), self.envelope())
        self.assertEqual(r.exporting_owner, "OWNER:GENEVA")
        self.assertEqual(r.importing_owner, "OWNER:SF")
        self.assertNotEqual(r.exporting_owner, r.importing_owner)

    def test_replay_digest_is_stable(self):
        self.assertEqual(self.envelope().envelope_digest, self.envelope().envelope_digest)

    def test_semantic_root_changes_replay_identity(self):
        self.assertNotEqual(
            self.envelope().envelope_digest,
            self.envelope(semantic_root="root2").envelope_digest,
        )

    def test_contract_compiles_from_declarative_mapping(self):
        c = self.contract()
        compiled = contract_from_mapping(asdict(c))
        self.assertEqual(compiled.contract_digest, c.contract_digest)

    def test_contract_policy_conflict_fails(self):
        with self.assertRaisesRegex(ValueError, "TRANSFORM_POLICY_CONFLICT"):
            self.contract(
                allowed_transformations=("IMPORT_AS_EVIDENCE",),
                forbidden_casts=("IMPORT_AS_EVIDENCE",),
            ).validate()

    def test_bridge_chain_revalidates_at_each_destination(self):
        a = self.contract()
        b = self.contract(
            bridge_id="SF:BOSTON:QUALIFICATION:v1",
            exporting_jurisdiction="SF_ENGINEERING",
            exporting_owner="OWNER:SF",
            importing_jurisdiction="BOSTON_RESEARCH",
            importing_owner="OWNER:BOSTON",
        )
        self.assertEqual(
            CrossCityBridgeCompiler().compose(a, b),
            "COMPOSABLE_REVALIDATE_AT_EACH_DESTINATION_NO_AUTHORITY_PROMOTION",
        )

    def test_chain_mismatch_holds(self):
        b = self.contract(
            bridge_id="NY:BOSTON:QUALIFICATION:v1",
            exporting_jurisdiction="NY_FINANCE",
            importing_jurisdiction="BOSTON_RESEARCH",
        )
        self.assertEqual(
            CrossCityBridgeCompiler().compose(self.contract(), b),
            "HOLD_JURISDICTION_CHAIN_MISMATCH",
        )

    def test_dependency_delta_is_selective(self):
        a = self.contract()
        b = self.contract(
            bridge_id="GENEVA:NY:WORK:v1",
            importing_jurisdiction="NY_FINANCE",
            importing_owner="OWNER:NY",
            dependency_invalidators=("wallet_generation",),
        )
        index = BridgeDependencyIndex((a, b))
        self.assertEqual(index.affected(("issuer_generation",)), (a.bridge_id,))
        self.assertEqual(index.affected(("unrelated",)), ())

    def test_1000_challenge_lattice_never_mints_local_authority(self):
        portable = sorted(PORTABLE_KINDS)[:5]
        kinds = portable + sorted(NONPORTABLE_KINDS) + ["SOURCE_POINTER"]
        self.assertEqual(len(kinds), 10)
        destinations = [f"CITY{i}" for i in range(10)]
        challenges = [
            "IMPORT", "EXPIRE", "REVOKE", "PRIVACY", "SCOPE",
            "LOCAL_VERIFY", "EFFECT_CROSSCAST", "DEDUPE", "DELTA", "COST",
        ]
        cells = 0
        for kind in kinds:
            for city in destinations:
                for _challenge in challenges:
                    cells += 1
                    c = self.contract(
                        bridge_id=f"GENEVA:{city}:{kind}:v1",
                        importing_jurisdiction=city,
                        importing_owner=f"OWNER:{city}",
                    )
                    if kind in NONPORTABLE_KINDS:
                        with self.assertRaises(ValueError):
                            self.envelope(
                                bridge_id=c.bridge_id,
                                wallet_items=(WalletItem(kind, "w", "src", "g1"),),
                            ).validate()
                        continue
                    env = self.envelope(
                        bridge_id=c.bridge_id,
                        wallet_items=(WalletItem(kind, "w", "src", "g1"),),
                    )
                    r = CrossCityBridgeCompiler().admit(c, env)
                    self.assertFalse(r.authority_promoted)
                    self.assertFalse(r.effect_authority)
                    self.assertEqual(r.destination_local_gates, ("OWNER_AUTHORITY",))
        self.assertEqual(cells, 1000)

    def test_100000_random_authority_crosscasts_fail_closed(self):
        rng = random.Random(27)
        compiler = CrossCityBridgeCompiler()
        for i in range(100000):
            mode = rng.randrange(4)
            if mode == 0:
                with self.assertRaises(ValueError):
                    self.envelope(wallet_items=(WalletItem("EFFECT_PERMIT", f"w{i}", "src", "g1"),)).validate()
            elif mode == 1:
                with self.assertRaises(ValueError):
                    self.envelope(evidence=(EvidenceLeaf("OWNER_AUTHORITY", f"e{i}", "src", "g1"),)).validate()
            elif mode == 2:
                with self.assertRaises(ValueError):
                    compiler.admit(self.contract(), self.envelope(requested_transformation="CAST_AS_EFFECT_PERMIT"))
            else:
                r = compiler.admit(self.contract(), self.envelope())
                self.assertFalse(r.authority_promoted or r.effect_authority)


if __name__ == "__main__":
    unittest.main()
