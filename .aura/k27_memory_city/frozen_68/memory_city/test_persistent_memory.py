import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from coordinate_bridge import *
from persistent_memory import MemoryStore, MemoryConflict, StaleMemory
from world_atlas import FrameAddress, FrameAtlas, FrameTransform, WorldFrame

class PersistentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='aura-memory-')
        self.file=Path(self.tmp.name)/'city.sqlite'
        self.s=MemoryStore(self.file);self.s.register_frame('city','g1')
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def put(self,key,payload=None,path=(0,),**kwargs):
        if kwargs.get('expected_revision') is not None and 'expected_epoch' not in kwargs:
            kwargs['expected_epoch']=self.s.get(key,allow_stale=True)['epoch']
        return self.s.publish(key,payload or {'name':key},FrameAddress('city','g1',path,key),
            source_url='https://example.org/source/'+key,source_version='v1',**kwargs)['revision_id']
    def chain(self):
        a=self.put('A'); b=self.put('B',dependencies={'A':a}); c=self.put('C',dependencies={'B':b}); d=self.put('D')
        return a,b,c,d
    def test_durable_restart_and_history(self):
        a=self.put('A'); self.s.close();self.s=MemoryStore(self.file)
        self.assertEqual(self.s.get('A')['revision_id'],a)
        a2=self.put('A',{'name':'renamed'},expected_revision=a)
        self.assertNotEqual(a,a2);self.assertEqual(self.s.history('A',a)['payload']['name'],'A')
        self.assertIsNone(self.s.history('other',a))
    def test_selective_transitive_invalidation(self):
        a,b,c,d=self.chain()
        result=self.s.publish('A',{'v':2},FrameAddress('city','g1',(0,),'A'),source_url='https://example.org/A',source_version='v2',expected_revision=a,expected_epoch=1)
        self.assertEqual(result['invalidated'],['B','C'])
        for key in ('B','C'):
            with self.assertRaises(StaleMemory):self.s.get(key)
        self.assertEqual(self.s.get('D')['revision_id'],d)
    def test_stale_dependency_blocks_publish(self):
        a,b,c,d=self.chain();self.put('A',{'v':2},expected_revision=a)
        with self.assertRaises(StaleMemory):self.put('E',dependencies={'B':b})
        self.assertIsNone(self.s.get('E'))
    def test_missing_dependency_rolls_back_all_rows(self):
        with self.assertRaises(StaleMemory):self.put('E',dependencies={'missing':'missing-rev'})
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM revisions').fetchone()[0],0)
    def test_interrupted_publication_is_atomic(self):
        a,b,c,d=self.chain()
        with patch.object(self.s,'_invalidate',side_effect=RuntimeError('injected interruption')):
            with self.assertRaises(RuntimeError):self.put('A',{'v':2},expected_revision=a)
        self.assertEqual(self.s.get('A')['revision_id'],a)
        self.assertEqual(self.s.get('B')['revision_id'],b)
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM revisions').fetchone()[0],4)
    def test_readers_see_old_snapshot_until_commit(self):
        a=self.put('A')
        with MemoryStore(self.file) as other:
            invalidate=self.s._invalidate
            def observe(roots):
                self.assertEqual(other.get('A')['revision_id'],a)
                return invalidate(roots)
            with patch.object(self.s,'_invalidate',side_effect=observe):
                new=self.put('A',{'v':2},expected_revision=a)
            self.assertEqual(other.get('A')['revision_id'],new)
    def test_concurrent_writer_compare_and_swap(self):
        a=self.put('A')
        with MemoryStore(self.file) as other:
            new=self.put('A',{'v':2},expected_revision=a)
            with self.assertRaises(MemoryConflict):
                other.publish('A',{'v':3},FrameAddress('city','g1',(0,),'A'),source_url='x',source_version='3',expected_revision=a,expected_epoch=1)
            self.assertEqual(other.get('A')['revision_id'],new)
    def test_move_preserves_object_identity_and_payload_digest(self):
        a=self.put('A');old=self.s.get('A');new=self.put('A',path=(2,3),expected_revision=a)
        self.assertNotEqual(a,new);self.assertEqual(old['payload_sha256'],self.s.get('A')['payload_sha256'])
        self.assertEqual(self.s.under('city','g1',(0,)),[])
        self.assertEqual(self.s.under('city','g1',(2,))[0]['object_id'],'A')
    def test_prefix_query_matches_exhaustive_reference(self):
        paths=[(),(0,),(0,0),(0,1),(1,),(10,),(26,26)]
        for i,p in enumerate(paths):self.put(str(i),path=p)
        for prefix in paths:
            expected={str(i) for i,p in enumerate(paths) if p[:len(prefix)]==prefix}
            self.assertEqual({r['object_id'] for r in self.s.under('city','g1',prefix)},expected)
    def test_colocated_records_are_all_returned(self):
        self.put('A');self.put('B')
        self.assertEqual([r['object_id'] for r in self.s.under('city','g1',(0,))],['A','B'])
    def test_frame_change_invalidates_and_requires_new_generation(self):
        a=self.put('A')
        self.assertEqual(self.s.register_frame('city','g2',expected_generation='g1'),['A'])
        with self.assertRaises(StaleMemory):self.put('B')
        with self.assertRaises(StaleMemory):self.s.get('A')
        self.assertEqual(self.s.under('city','g1'),[])
        self.assertIsNotNone(self.s.history('A',a))
        with self.assertRaises(MemoryConflict):self.s.register_frame('city','g3',expected_generation='g1')
    def test_cross_frame_dependency_is_invalidated(self):
        a=self.put('A');self.s.register_frame('other','g1')
        self.s.publish('B',{},FrameAddress('other','g1',(),'B'),source_url='b',source_version='1',dependencies={'A':a})
        self.assertEqual(self.s.register_frame('city','g2',expected_generation='g1'),['A','B'])
    def test_retraction_preserves_history_and_propagates(self):
        a,b,c,d=self.chain();self.assertEqual(self.s.retract('A',expected_revision=a,expected_epoch=1),['B','C'])
        self.assertEqual(self.s.get('A',allow_stale=True)['state'],'retracted')
        self.assertIsNotNone(self.s.history('A',a))
        self.assertEqual(self.s.get('D')['revision_id'],d)
    def test_current_object_cycles_are_rejected(self):
        a=self.put('A');b=self.put('B',dependencies={'A':a})
        with self.assertRaises(MemoryConflict):self.put('A',{'v':2},expected_revision=a,dependencies={'B':b})
        self.assertEqual(self.s.get('A')['revision_id'],a)
    def test_invalid_scalar_paths_and_payloads_rejected(self):
        for digits in ((True,),(1.0,),(-1,),(27,),tuple([0]*129)):
            with self.assertRaises(ValueError):checked_path(digits)
        for payload in ({'x':float('nan')},{'x':float('inf')}):
            with self.assertRaises(ValueError):self.put('A',payload)
        with self.assertRaises(ValueError):self.s.publish('A',{},FrameAddress('city','g1',(),'B'),source_url='x',source_version='1')
    def test_explicit_transform_roundtrip(self):
        self.put('A',path=(0,5,26));self.s.register_frame('view','v1')
        atlas=FrameAtlas();atlas.add_frame(WorldFrame('city','g1','e','CANONICAL'));atlas.add_frame(WorldFrame('view','v1','e','GENERATED'))
        atlas.add_transform(FrameTransform('city','g1','view','v1',(2,1,0),(True,False,True)))
        out=self.s.project('A',atlas,'view');self.assertEqual(out.canonical_ref,'A')
        self.assertEqual(out.path,(20,5,6))
        atlas.add_transform(FrameTransform('view','v1','city','g1',(2,1,0),(True,False,True)))
        self.assertEqual(atlas.project(out,'city').path,(0,5,26))
        self.assertEqual(self.s.get('A')['address']['frame_id'],'city')
    def test_bad_transform_cannot_silently_collapse_axes(self):
        self.put('A');self.s.register_frame('view','v1');atlas=FrameAtlas()
        atlas.add_frame(WorldFrame('city','g1','e','CANONICAL'));atlas.add_frame(WorldFrame('view','v1','e','GENERATED'))
        atlas.add_transform(FrameTransform('city','g1','view','v1',(0,0,0)))
        with self.assertRaises(ValueError):self.s.project('A',atlas,'view')
    def test_distinct_coordinate_schemes_and_eight_corners(self):
        self.assertEqual(digest_bucket('ff'*32).xyz,(12,12,12))
        self.assertEqual(set(local_octants()),{0,2,6,8,18,20,24,26})
        with self.assertRaises(ValueError):checked_address(digest_bucket('ff'*32))

if __name__=='__main__':unittest.main()
