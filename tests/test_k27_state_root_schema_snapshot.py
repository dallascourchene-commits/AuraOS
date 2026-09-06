import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / 'tools' / 'arena'
sys.path.insert(0, str(ARENA))

from k27_memory import FrameAddress, MemoryStore


def new_store(path: Path) -> MemoryStore:
    store = MemoryStore(path)
    store.register_frame('f', 'g', expected_generation=None)
    return store


class StateRootSchemaSnapshotTests(unittest.TestCase):
    def test_unexpected_trigger_is_rejected_before_working_rebind(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish(
                    'src', {'v': 1}, FrameAddress('f', 'g', (1,), 'src'),
                    source_url='u', source_version='1')
                store.publish(
                    'dep', {'v': 1}, FrameAddress('f', 'g', (2,), 'dep'),
                    source_url='u', source_version='1',
                    dependencies={'src': src['revision_id']},
                    dependency_epochs={'src': src['epoch']})
                committed_root = store.state_root()

            raw = sqlite3.connect(p)
            try:
                raw.execute('''
                    CREATE TRIGGER erase_dependency_edges
                    AFTER INSERT ON dependencies
                    BEGIN
                        DELETE FROM dependencies WHERE revision_id = NEW.revision_id;
                    END
                ''')
                raw.commit()
            finally:
                raw.close()

            with self.assertRaisesRegex(ValueError, 'schema objects'):
                MemoryStore(p)

            # The old authenticated root cannot silently authorize this schema.
            self.assertEqual(len(committed_root), 64)

    def test_state_root_uses_one_read_snapshot_under_concurrent_commit(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish(
                    'src', {'v': 1}, FrameAddress('f', 'g', (1,), 'src'),
                    source_url='u', source_version='1')
                before = store.state_root()
                store.db.execute('PRAGMA journal_mode=WAL')

                snapshot_open = threading.Event()
                writer_done = threading.Event()
                original_schema_snapshot = store._schema_snapshot

                def hooked_schema_snapshot():
                    rows = original_schema_snapshot()
                    snapshot_open.set()
                    if not writer_done.wait(5):
                        raise AssertionError('writer did not commit during read snapshot')
                    return rows

                store._schema_snapshot = hooked_schema_snapshot

                def writer():
                    if not snapshot_open.wait(5):
                        return
                    with MemoryStore(p) as other:
                        other.publish(
                            'src', {'v': 2}, FrameAddress('f', 'g', (1,), 'src'),
                            source_url='u', source_version='2',
                            expected_revision=src['revision_id'],
                            expected_epoch=src['epoch'],
                            expected_store_root=before)
                    writer_done.set()

                t = threading.Thread(target=writer)
                t.start()
                during = store.state_root()
                t.join(5)
                self.assertFalse(t.is_alive())
                self.assertEqual(during, before)

                store._schema_snapshot = original_schema_snapshot
                after = store.state_root()
                self.assertNotEqual(after, before)


if __name__ == '__main__':
    unittest.main()
