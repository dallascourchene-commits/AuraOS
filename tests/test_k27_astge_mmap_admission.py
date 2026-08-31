from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

import k27_astge_mmap_admission as admission
import k27_astge_mmap_lifecycle as life
import k27_astge_reference as ref


class ASTGEMmapAdmissionTests(unittest.TestCase):
    SNAPSHOT = "snapshot-generation-1"
    MANIFEST = hashlib.sha256(b"aura-k27-test-manifest").hexdigest()

    def fixture(self, td: str):
        graph = ref.build_balanced_tree(3, 2)
        nodes = os.path.join(td, "graph.nodes")
        edges = os.path.join(td, "graph.edges")
        ref.serialize_graph(nodes, edges, graph)
        return graph, nodes, edges

    def capability(self, nodes: str, edges: str, **changes):
        with life.LifecycleGuardedMmapGraphReader(nodes, edges) as guard:
            observed = guard.validate_generation()
            record = admission.BackingFileImmutabilityCapabilityV1(
                storage_root=str(Path(nodes).parent.resolve()),
                snapshot_generation=self.SNAPSHOT,
                manifest_digest=self.MANIFEST,
                nodes_generation_digest=guard._nodes_generation.generation_digest,
                edges_generation_digest=guard._edges_generation.generation_digest,
                combined_generation_digest=observed.combined_generation_digest,
                nodes_device=guard._nodes_generation.device,
                nodes_inode=guard._nodes_generation.inode,
                edges_device=guard._edges_generation.device,
                edges_inode=guard._edges_generation.inode,
                publisher_ref="publisher://snapshot-v1",
                verifier_ref="verifier://independent-v1",
                filesystem_semantics_ref="fs://posix-model-v1",
                external_mutation_disposition_ref="threat://external-mutation-excluded-v1",
                replacement_only_publication=True,
                published_generation_files_immutable=True,
                mapped_lifetime_within_capability=True,
                capability_current=True,
            )
        return replace(record, **changes)

    def private_open(self, nodes: str, edges: str, records):
        return admission._open_with_records(
            nodes_path=nodes,
            edges_path=edges,
            snapshot_generation=self.SNAPSHOT,
            manifest_digest=self.MANIFEST,
            records=tuple(records),
        )

    def test_production_registry_is_empty_and_public_path_holds(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            receipt = admission.backing_immutability_capability_registry_receipt()
            self.assertEqual(0, receipt.active_capability_count)
            self.assertEqual((), receipt.capability_digests)
            self.assertFalse(receipt.authority)
            self.assertFalse(receipt.external_effect)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REQUIRED"):
                admission.open_admitted_mmap_graph_reader(
                    nodes_path=nodes,
                    edges_path=edges,
                    snapshot_generation=self.SNAPSHOT,
                    manifest_digest=self.MANIFEST,
                )

    def test_public_signature_has_no_capability_or_registry_override(self):
        params = set(admission.mmap_admission_parameter_names())
        for forbidden in (
            "capability",
            "capabilities",
            "record",
            "records",
            "registry",
            "registry_lookup",
            "trusted",
            "immutable",
            "authority",
        ):
            self.assertNotIn(forbidden, params)

    def test_exact_private_capability_admits_only_eligibility(self):
        with tempfile.TemporaryDirectory() as td:
            graph, nodes, edges = self.fixture(td)
            capability = self.capability(nodes, edges)
            with self.private_open(nodes, edges, (capability,)) as reader:
                receipt = reader.admission_receipt
                self.assertTrue(receipt.mmap_eligible_under_registered_capability)
                self.assertFalse(receipt.concurrent_mutation_race_proven_safe)
                self.assertFalse(receipt.sigbus_impossible_proven)
                self.assertFalse(receipt.hostile_external_mutation_proven_safe)
                self.assertFalse(receipt.physical_crash_durability_proven)
                self.assertFalse(receipt.native_engine_safety_proven)
                self.assertFalse(receipt.performance_superiority_proven)
                self.assertFalse(receipt.authority)
                self.assertFalse(receipt.external_effect)
                self.assertEqual(
                    ref.query_heap(graph, 0, 2),
                    reader.query_affected_cone(0, 2).node_ids,
                )

    def test_same_publisher_and_verifier_is_not_independent(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            good = self.capability(nodes, edges)
            bad = replace(good, verifier_ref=good.publisher_ref)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_INDEPENDENT_VERIFIER_REQUIRED"):
                self.private_open(nodes, edges, (bad,))

    def test_truthy_non_boolean_capability_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            bad = replace(self.capability(nodes, edges), capability_current=1)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_CAPABILITY_CURRENT_BOOL_REQUIRED"):
                self.private_open(nodes, edges, (bad,))

    def test_effect_authority_widening_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            bad = replace(self.capability(nodes, edges), authority=True)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_EFFECT_AUTHORITY_FORBIDDEN"):
                self.private_open(nodes, edges, (bad,))

    def test_snapshot_or_manifest_substitution_cannot_match_capability(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            capability = self.capability(nodes, edges)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REQUIRED"):
                admission._open_with_records(
                    nodes_path=nodes,
                    edges_path=edges,
                    snapshot_generation="snapshot-other",
                    manifest_digest=self.MANIFEST,
                    records=(capability,),
                )
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REQUIRED"):
                admission._open_with_records(
                    nodes_path=nodes,
                    edges_path=edges,
                    snapshot_generation=self.SNAPSHOT,
                    manifest_digest=hashlib.sha256(b"other").hexdigest(),
                    records=(capability,),
                )

    def test_opened_file_identity_or_generation_substitution_cannot_match(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            good = self.capability(nodes, edges)
            for bad in (
                replace(good, nodes_inode=good.nodes_inode + 1),
                replace(good, combined_generation_digest="0" * 64),
            ):
                with self.subTest(bad=bad):
                    with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REQUIRED"):
                        self.private_open(nodes, edges, (bad,))

    def test_stale_or_revoked_exact_capability_fails_with_typed_state(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            good = self.capability(nodes, edges)
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_STALE"):
                self.private_open(nodes, edges, (replace(good, capability_current=False),))
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REVOKED"):
                self.private_open(nodes, edges, (replace(good, revoked=True),))

    def test_multiple_exact_capabilities_fail_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            a = self.capability(nodes, edges)
            b = replace(a, verifier_ref="verifier://independent-v2")
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_AMBIGUOUS"):
                self.private_open(nodes, edges, (a, b))

    def test_malformed_unrelated_registry_neighbor_poisoning_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            good = self.capability(nodes, edges)
            malformed = replace(
                good,
                snapshot_generation="unrelated-generation",
                schema="WrongSchema",
            )
            with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_SCHEMA_MISMATCH"):
                self.private_open(nodes, edges, (good, malformed))

    def test_capability_does_not_replace_runtime_generation_guard(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            capability = self.capability(nodes, edges)
            with self.private_open(nodes, edges, (capability,)) as reader:
                with open(nodes, "r+b") as handle:
                    first = handle.read(1)
                    handle.seek(0)
                    handle.write(bytes([first[0] ^ 1]))
                    handle.flush()
                    os.fsync(handle.fileno())
                with self.assertRaisesRegex(life.MmapLifecycleError, "NODES_FILE_CONTENT_DRIFT"):
                    reader.get_node(0)

    def test_reopen_requires_fresh_admission(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            capability = self.capability(nodes, edges)
            with self.private_open(nodes, edges, (capability,)) as reader:
                with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_EXPLICIT_READMISSION_REQUIRED"):
                    reader.reopen()

    def test_read_only_permissions_alone_do_not_admit_mmap(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            os.chmod(nodes, 0o444)
            os.chmod(edges, 0o444)
            try:
                with self.assertRaisesRegex(life.MmapLifecycleError, "MMAP_IMMUTABILITY_CAPABILITY_REQUIRED"):
                    admission.open_admitted_mmap_graph_reader(
                        nodes_path=nodes,
                        edges_path=edges,
                        snapshot_generation=self.SNAPSHOT,
                        manifest_digest=self.MANIFEST,
                    )
            finally:
                os.chmod(nodes, 0o644)
                os.chmod(edges, 0o644)

    def test_capability_policy_flags_must_be_exact_true(self):
        with tempfile.TemporaryDirectory() as td:
            _, nodes, edges = self.fixture(td)
            good = self.capability(nodes, edges)
            cases = (
                ("replacement_only_publication", "MMAP_REPLACEMENT_ONLY_PUBLICATION_REQUIRED"),
                ("published_generation_files_immutable", "MMAP_PUBLISHED_GENERATION_IMMUTABILITY_REQUIRED"),
                ("mapped_lifetime_within_capability", "MMAP_CAPABILITY_LIFETIME_BOUND_REQUIRED"),
            )
            for field, code in cases:
                with self.subTest(field=field):
                    with self.assertRaisesRegex(life.MmapLifecycleError, code):
                        self.private_open(nodes, edges, (replace(good, **{field: False}),))


if __name__ == "__main__":
    unittest.main()
