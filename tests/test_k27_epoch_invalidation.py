import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / 'tools' / 'arena'
sys.path.insert(0, str(ARENA))

from k27_memory import FrameAddress, MemoryConflict, MemoryStore, StaleMemory


def new_store(path: Path) -> MemoryStore:
    store = MemoryStore(path)
    store.register_frame('f', 'g', expected_generation=None)
    return store


class EpochInvalidationTests(unittest.TestCase):
    def test_schema_probe_uses_parameterized_table_valued_pragma(self):
        with tempfile.TemporaryDirectory() as td:
            with new_store(Path(td) / 'm.sqlite') as store:
                cols = tuple(r['name'] for r in store.db.execute(
                    'SELECT name FROM pragma_table_info(?) ORDER BY cid', ('objects',)))
                self.assertEqual(cols, ('object_id','current_rev','state','frame_id','frame_generation','path','epoch'))

    def test_identical_republish_advances_epoch_and_invalidates_dependent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                dep = store.publish('dep', {'v': 1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                                    dependencies={'src': src['revision_id']}, dependency_epochs={'src': src['epoch']})
                again = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                      expected_revision=src['revision_id'], expected_epoch=src['epoch'])
                self.assertEqual(again['revision_id'], src['revision_id'])
                self.assertEqual(again['epoch'], src['epoch'] + 1)
                self.assertEqual(again['invalidated'], ['dep'])
                with self.assertRaises(StaleMemory):
                    store.get('dep')
                self.assertEqual(store.get('dep', allow_stale=True)['epoch'], dep['epoch'] + 1)

    def test_changed_revision_still_invalidates_dependent(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                store.publish('dep', {'v': 1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                              dependencies={'src': src['revision_id']}, dependency_epochs={'src': src['epoch']})
                out = store.publish('src', {'v': 2}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='2',
                                    expected_revision=src['revision_id'], expected_epoch=src['epoch'])
                self.assertNotEqual(out['revision_id'], src['revision_id'])
                self.assertEqual(out['invalidated'], ['dep'])

    def test_stale_dependency_epoch_holds_even_when_revision_repeats(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                again = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                      expected_revision=src['revision_id'], expected_epoch=src['epoch'])
                self.assertEqual(again['revision_id'], src['revision_id'])
                with self.assertRaises(StaleMemory):
                    store.publish('late', {'v': 1}, FrameAddress('f','g',(3,),'late'), source_url='u', source_version='1',
                                  dependencies={'src': src['revision_id']}, dependency_epochs={'src': src['epoch']})

    def test_state_root_changes_on_epoch_only_transition(self):
        with tempfile.TemporaryDirectory() as td:
            with new_store(Path(td) / 'm.sqlite') as store:
                src = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                before = store.state_root()
                again = store.publish('src', {'v': 1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                      expected_revision=src['revision_id'], expected_epoch=src['epoch'])
                self.assertEqual(again['revision_id'], src['revision_id'])
                self.assertNotEqual(before, store.state_root())

    def test_store_root_cas_rejects_unrelated_movement(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                root = store.state_root()
                store.publish('a', {'v':1}, FrameAddress('f','g',(1,),'a'), source_url='u', source_version='1', expected_store_root=root)
                with self.assertRaises(MemoryConflict):
                    store.publish('b', {'v':1}, FrameAddress('f','g',(2,),'b'), source_url='u', source_version='1', expected_store_root=root)

    def test_five_way_identical_republish_has_one_winner(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                root = store.state_root()
            def attempt(_):
                try:
                    with MemoryStore(p) as store:
                        store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                      expected_revision=src['revision_id'], expected_epoch=src['epoch'], expected_store_root=root)
                    return 'WIN'
                except (MemoryConflict, StaleMemory):
                    return 'HOLD'
            with ThreadPoolExecutor(max_workers=5) as pool:
                results = list(pool.map(attempt, range(5)))
            self.assertEqual(results.count('WIN'), 1)
            self.assertEqual(results.count('HOLD'), 4)

    def test_invalidation_receipt_order_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                for name, digit in [('z',3),('a',4),('m',5)]:
                    store.publish(name, {'v':1}, FrameAddress('f','g',(digit,),name), source_url='u', source_version='1',
                                  dependencies={'src':src['revision_id']}, dependency_epochs={'src':src['epoch']})
                out = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1',
                                    expected_revision=src['revision_id'], expected_epoch=src['epoch'])
                self.assertEqual(out['invalidated'], ['a','m','z'])

    def test_state_root_rejects_ambient_payload_envelope_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                env = json.loads(store.db.execute(
                    'SELECT envelope FROM revisions WHERE revision_id=?', (src['revision_id'],)).fetchone()[0])
                env['payload']['v'] = 999
                store.db.execute('UPDATE revisions SET envelope=? WHERE revision_id=?',
                                 (json.dumps(env, sort_keys=True, separators=(',',':')), src['revision_id']))
                with self.assertRaisesRegex(MemoryConflict, 'revision envelope digest mismatch'):
                    store.state_root()
                with self.assertRaisesRegex(MemoryConflict, 'revision envelope digest mismatch'):
                    store.get('src')

    def test_state_root_rejects_ambient_source_metadata_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                env = json.loads(store.db.execute(
                    'SELECT envelope FROM revisions WHERE revision_id=?', (src['revision_id'],)).fetchone()[0])
                env['source_version'] = 'forged'
                store.db.execute('UPDATE revisions SET envelope=? WHERE revision_id=?',
                                 (json.dumps(env, sort_keys=True, separators=(',',':')), src['revision_id']))
                with self.assertRaises(MemoryConflict):
                    store.history('src', src['revision_id'])

    def test_dependency_edge_mutation_changes_whole_store_root(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                src = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                dep = store.publish('dep', {'v':1}, FrameAddress('f','g',(2,),'dep'), source_url='u', source_version='1',
                                    dependencies={'src':src['revision_id']}, dependency_epochs={'src':src['epoch']})
                before = store.state_root()
                store.db.execute('DELETE FROM dependencies WHERE revision_id=?', (dep['revision_id'],))
                self.assertNotEqual(before, store.state_root())

    def test_historical_revision_mutation_is_not_hidden_by_current_object(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'm.sqlite'
            with new_store(p) as store:
                first = store.publish('src', {'v':1}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='1')
                second = store.publish('src', {'v':2}, FrameAddress('f','g',(1,),'src'), source_url='u', source_version='2',
                                       expected_revision=first['revision_id'], expected_epoch=first['epoch'])
                env = json.loads(store.db.execute(
                    'SELECT envelope FROM revisions WHERE revision_id=?', (first['revision_id'],)).fetchone()[0])
                env['source_url'] = 'forged'
                store.db.execute('UPDATE revisions SET envelope=? WHERE revision_id=?',
                                 (json.dumps(env, sort_keys=True, separators=(',',':')), first['revision_id']))
                with self.assertRaises(MemoryConflict):
                    store.state_root()
                self.assertEqual(store.get('src')['revision_id'], second['revision_id'])


if __name__ == '__main__':
    unittest.main()
