import json
from pathlib import Path
import shutil
import tempfile
import unittest

from aura_k27_memory_city import FrameAddress, K27Path, MemoryConflict, MemoryStore
from aura_k27_memory_city_runtime import (
    AUTHORITY, EXPECTED_SOURCE_DATABASE_SHA256, EXPECTED_COLD_SOURCE_MANIFEST_SHA256, EXPECTED_RECIPE_VERSION, EXPECTED_SEMANTIC_ROOT,
    FRAME, GENERATION, K27MemoryCityRuntime, default_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DB = default_registry(ROOT)


class K27RuntimeBindingTests(unittest.TestCase):
    def test_root_import_contract(self):
        self.assertEqual(K27Path((2, 0, 0)).digits, (2, 0, 0))
        self.assertEqual(FrameAddress(FRAME, GENERATION, (2,), "x").frame_id, FRAME)

    def test_canonical_registry_exact_identity_and_live_routes(self):
        with K27MemoryCityRuntime(ROOT) as runtime:
            status = runtime.status()
            self.assertEqual(status["source_database_sha256"], EXPECTED_SOURCE_DATABASE_SHA256)
            self.assertEqual(status["cold_source_manifest_sha256"], EXPECTED_COLD_SOURCE_MANIFEST_SHA256)
            self.assertEqual(status["registry_recipe_version"], EXPECTED_RECIPE_VERSION)
            self.assertEqual(len(status["runtime_database_sha256"]), 64)
            self.assertEqual(status["semantic_registry_root"], EXPECTED_SEMANTIC_ROOT)
            self.assertEqual(status["record_count"], 1115)
            self.assertEqual(status["route_count"], 1000)
            self.assertEqual(len(runtime.under((2,))), 1000)
            self.assertTrue(all(row["state"] == "fresh" for row in runtime.under((0,))))

    def test_recipe_rebuild_does_not_require_raw_sqlite_bytes(self):
        self.assertFalse((ROOT / ".aura/k27_memory_city/research_registry.sqlite").exists())
        with tempfile.TemporaryDirectory(prefix="k27-logical-rebuild-") as tmp:
            import os
            old = os.environ.get("AURA_K27_RUNTIME_CACHE")
            os.environ["AURA_K27_RUNTIME_CACHE"] = tmp
            try:
                rebuilt = default_registry(ROOT)
                with MemoryStore(rebuilt, read_only=True) as store:
                    self.assertEqual(len(store.under(FRAME, GENERATION)), 1115)
            finally:
                if old is None:
                    os.environ.pop("AURA_K27_RUNTIME_CACHE", None)
                else:
                    os.environ["AURA_K27_RUNTIME_CACHE"] = old

    def test_canonical_registry_is_read_only(self):
        with K27MemoryCityRuntime(ROOT) as runtime:
            with MemoryStore(runtime.registry_path, read_only=True) as store:
                with self.assertRaises(MemoryConflict):
                    store.register_frame("forbidden", "g1")
                with self.assertRaises(MemoryConflict):
                    store.publish(
                        "forbidden", {"x": 1}, FrameAddress(FRAME, GENERATION, (2,), "forbidden"),
                        source_url="fixture:none", source_version="1"
                    )

    def test_authority_is_nonpromoting(self):
        self.assertTrue(AUTHORITY)
        self.assertFalse(any(AUTHORITY.values()))

    def test_ephemeral_copy_preserves_revision_plus_epoch_cas(self):
        with tempfile.TemporaryDirectory(prefix="k27-runtime-test-") as tmp:
            copied = Path(tmp) / "registry.sqlite"
            shutil.copyfile(DB, copied)
            with MemoryStore(copied) as store:
                base = store.get("K27-EXT-001")
                address = base["address"]
                fa = FrameAddress(address["frame_id"], address["frame_generation"], tuple(address["path"]), "K27-EXT-001")
                store.retract("K27-EXT-001", expected_revision=base["revision_id"], expected_epoch=base["epoch"])
                retired = store.get("K27-EXT-001", allow_stale=True)
                restored = store.publish(
                    "K27-EXT-001", base["payload"], fa,
                    source_url=base["source_url"], source_version=base["source_version"],
                    expected_revision=base["revision_id"], expected_epoch=retired["epoch"],
                    dependencies=base["dependencies"],
                )
                self.assertEqual(restored["revision_id"], base["revision_id"])
                self.assertGreater(restored["epoch"], base["epoch"])
                with self.assertRaises(MemoryConflict):
                    store.publish(
                        "K27-EXT-001", {"wrong": True}, fa,
                        source_url=base["source_url"], source_version="bad",
                        expected_revision=base["revision_id"], expected_epoch=base["epoch"]
                    )


if __name__ == "__main__":
    unittest.main()
