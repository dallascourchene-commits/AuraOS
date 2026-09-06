from pathlib import Path
import tempfile

from tools.arena.k27_memory.persistent_memory import MemoryStore
from tools.arena.k27_memory.world_atlas import FrameAddress


def test_identical_source_republish_invalidates_dependents_on_epoch_advance():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "memory.sqlite"
        with MemoryStore(db) as store:
            store.register_frame("frame", "g1", expected_generation=None)

            source_address = FrameAddress("frame", "g1", (1,), "source")
            dependent_address = FrameAddress("frame", "g1", (2,), "dependent")

            first = store.publish(
                "source",
                {"value": 1},
                source_address,
                source_url="fixture://source",
                source_version="v1",
                expected_revision=None,
                expected_epoch=None,
            )
            dependent = store.publish(
                "dependent",
                {"derived": True},
                dependent_address,
                source_url="fixture://dependent",
                source_version="v1",
                expected_revision=None,
                expected_epoch=None,
                dependencies={"source": first["revision_id"]},
                dependency_epochs={"source": first["epoch"]},
            )
            assert store.get("dependent")["state"] == "fresh"

            second = store.publish(
                "source",
                {"value": 1},
                source_address,
                source_url="fixture://source",
                source_version="v1",
                expected_revision=first["revision_id"],
                expected_epoch=first["epoch"],
            )

            assert second["revision_id"] == first["revision_id"]
            assert second["epoch"] == first["epoch"] + 1
            assert "dependent" in second["invalidated"]

            stale = store.get("dependent", allow_stale=True)
            assert stale["revision_id"] == dependent["revision_id"]
            assert stale["state"] == "stale"
            assert stale["epoch"] == dependent["epoch"] + 1
