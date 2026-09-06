import copy, json, os, shutil, sys, tempfile, unittest, types
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / 'tools' / 'arena'
sys.path.insert(0, str(ARENA))

from k27_memory_runtime import (
    K27MemoryRuntime, RuntimeBindingError, REGISTRY_SHA256, SEMANTIC_REGISTRY_ROOT,
    SPATIAL_SEAM_PARENT_SHA, SPATIAL_ROUTE_BLOB, SPATIAL_SEAM_SOURCE_BLOB,
    SPATIAL_SEAM_MODULE_BLOB,
)
from k27_memory import MemoryConflict, MemoryStore, FrameAddress, K27Path, StaleMemory
from k27_memory.k27_city import K27City, Cell, OverlayRule, digit_from_xyz, xyz_from_digit
from k27_memory.world_atlas import FrameTransform
from k27_memory_city_spatial_seam.k27_memory_city_spatial_seam import (
    SCENE_SOURCE_SHA256, SeamDisposition, validate_spatial_seam, validate_files,
)

REGISTRY_ENV = os.environ.get('AURA_K27_TEST_REGISTRY')
REGISTRY = Path(REGISTRY_ENV) if REGISTRY_ENV else None
REGISTRY_AVAILABLE = bool(REGISTRY is not None and REGISTRY.is_file())
ROUTE = ROOT / '.aura/arena_routes/spatial.v1.json'


def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def provenance_leaf_manifest():
    return {'files':{'k27_memory/cold_sources/MC-SRC-O1O9.md':{'sha256':SCENE_SOURCE_SHA256}}}


class SafetyRegressionTests(unittest.TestCase):
    def _new_store(self, path):
        store=MemoryStore(path)
        store.register_frame('f','g',expected_generation=None)
        return store

    def test_ci_collection_does_not_require_external_registry(self):
        self.assertIn(REGISTRY_AVAILABLE, (True, False))

    def test_bool_coordinates_are_rejected_everywhere(self):
        for value in (True, False):
            with self.assertRaises(ValueError): K27Path((value,))
            with self.assertRaises(ValueError): FrameAddress('f','g',(value,),'obj')
            with self.assertRaises(ValueError): xyz_from_digit(value)
        with self.assertRaises(ValueError): digit_from_xyz(True,0,0)

    def test_hard_nondelegable_rule_cannot_be_weakened_then_changed(self):
        city=K27City()
        city.add(Cell(K27Path(()),'root',rules={'x':OverlayRule('x','A',hard=True,delegable=False)}))
        city.add(Cell(K27Path((1,)),'child',rules={'x':OverlayRule('x','A',hard=False,delegable=False)}))
        city.add(Cell(K27Path((1,2)),'grand',rules={'x':OverlayRule('x','B',hard=False,delegable=True)}))
        with self.assertRaisesRegex(ValueError,'weakening'):
            city.effective_rules(K27Path((1,2)))

    def test_nondelegable_rule_cannot_widen_delegation_with_same_value(self):
        city=K27City()
        city.add(Cell(K27Path(()),'root',rules={'x':OverlayRule('x','A',hard=True,delegable=False)}))
        city.add(Cell(K27Path((1,)),'child',rules={'x':OverlayRule('x','A',hard=True,delegable=True)}))
        with self.assertRaisesRegex(ValueError,'delegation'):
            city.effective_rules(K27Path((1,)))

    def test_invalid_transforms_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            FrameTransform('a','1','b','1',axis_perm=(0,0,0))
        with self.assertRaises(ValueError):
            FrameTransform('a','1','b','1',axis_perm=(0,1,True))
        with self.assertRaises(ValueError):
            FrameTransform('a','1','b','1',invert=(False,False,0))

    def test_dependency_aba_requires_observed_epoch(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.sqlite'
            with self._new_store(p) as store:
                src_addr=FrameAddress('f','g',(1,),'src')
                dep_addr=FrameAddress('f','g',(2,),'dep')
                src=store.publish('src',{'v':1},src_addr,source_url='u',source_version='1')
                store.publish('dep',{'v':1},dep_addr,source_url='u',source_version='1',
                              dependencies={'src':src['revision_id']},dependency_epochs={'src':src['epoch']})
                store.retract('src',expected_revision=src['revision_id'],expected_epoch=src['epoch'])
                src_aba=store.publish('src',{'v':1},src_addr,source_url='u',source_version='1',
                                      expected_revision=src['revision_id'],expected_epoch=2)
                self.assertEqual(src_aba['revision_id'],src['revision_id'])
                self.assertEqual(src_aba['epoch'],3)
                with self.assertRaises(StaleMemory):
                    store.publish('late',{'v':1},FrameAddress('f','g',(3,),'late'),
                                  source_url='u',source_version='1',
                                  dependencies={'src':src['revision_id']},dependency_epochs={'src':1})

    def test_nonempty_dependencies_cannot_omit_epochs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.sqlite'
            with self._new_store(p) as store:
                src=store.publish('src',{'v':1},FrameAddress('f','g',(1,),'src'),source_url='u',source_version='1')
                with self.assertRaisesRegex(ValueError,'lifecycle epoch'):
                    store.publish('dep',{'v':1},FrameAddress('f','g',(2,),'dep'),source_url='u',source_version='1',
                                  dependencies={'src':src['revision_id']})

    def test_store_root_cas_rejects_unrelated_concurrent_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'m.sqlite'
            with self._new_store(p) as store:
                root=store.state_root()
                store.publish('a',{'v':1},FrameAddress('f','g',(1,),'a'),source_url='u',source_version='1',
                              expected_store_root=root)
                with self.assertRaisesRegex(MemoryConflict,'registry state changed'):
                    store.publish('b',{'v':1},FrameAddress('f','g',(2,),'b'),source_url='u',source_version='1',
                                  expected_store_root=root)

    def test_duplicate_malformed_and_unknown_spatial_seams_hold(self):
        route=json.loads(ROUTE.read_text())
        target=next(t for t in route['transitions'] if t['transition_id']=='SPATIAL.GROUND.COMPILE_SCENE')
        duplicate=copy.deepcopy(route); duplicate['transitions'].append(copy.deepcopy(target))
        r=validate_spatial_seam(json.dumps(duplicate,separators=(',',':')).encode(),provenance_leaf_manifest())
        self.assertIn('COMPILE_SCENE_TRANSITION_CARDINALITY_NOT_ONE',r.reasons)
        malformed=copy.deepcopy(route); malformed['transitions']=7
        r=validate_spatial_seam(json.dumps(malformed,separators=(',',':')).encode(),provenance_leaf_manifest())
        self.assertIn('TRANSITIONS_LIST_REQUIRED',r.reasons)
        unknown=copy.deepcopy(route)
        next(t for t in unknown['transitions'] if t['transition_id']=='SPATIAL.GROUND.COMPILE_SCENE')['memory_city_binding']['unknown_extension']=1
        r=validate_spatial_seam(json.dumps(unknown,separators=(',',':')).encode(),provenance_leaf_manifest())
        self.assertIn('BINDING_KEYSET_MISMATCH',r.reasons)

    def test_exact_provider_bytes_gate_when_supplied(self):
        keys=('AURA_K27_PROVENANCE_ARCHIVE','AURA_K27_PROVENANCE_MANIFEST','AURA_K27_SCENE_SOURCE')
        if not all(os.environ.get(k) for k in keys): self.skipTest('Different-J provider-byte inputs not mounted')
        r=validate_files(ROUTE,os.environ[keys[0]],os.environ[keys[1]],os.environ[keys[2]])
        self.assertEqual(r.disposition,SeamDisposition.READY_FOR_INDEPENDENT_REVIEW)
        self.assertTrue(r.provider_bytes_bound); self.assertEqual(r.manifest_payloads_verified,69)


@unittest.skipUnless(REGISTRY_AVAILABLE, 'sealed K27 registry fixture is not mounted')
class SealedRegistryRuntimeTests(unittest.TestCase):
    def test_exact_seal(self):
        rt=K27MemoryRuntime(REGISTRY)
        self.assertEqual(rt.seal.database_sha256,REGISTRY_SHA256)
        self.assertEqual(rt.seal.semantic_registry_root,SEMANTIC_REGISTRY_ROOT)
        self.assertEqual(rt.seal.records,1115)
        self.assertEqual(rt.seal.seal_scope,'canonical_seed')
        self.assertFalse(rt.seal.authority_minted); self.assertFalse(rt.seal.gate10)

    def test_real_family_coordinate_not_synthetic(self):
        rt=K27MemoryRuntime(REGISTRY)
        b,r=rt.read('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertEqual(b.path,(1,0,0)); self.assertEqual(b.epoch,1)
        self.assertEqual(b.revision_id,'3342e295f42ff524fcd4976340f09cf395b20b50c2962cd231bb369fdf202936')
        self.assertEqual(r['payload']['family_id'],'BREADBOARD/ACCESSIBILITY')
        self.assertFalse(b.upstream_currentness_asserted); self.assertFalse(b.truth_authority)

    def test_route_prefix_is_1000(self):
        self.assertEqual(len(K27MemoryRuntime(REGISTRY).under((2,))),1000)

    def test_scene_shell_review_only(self):
        out=K27MemoryRuntime(REGISTRY).scene_shell((2,0,0),limit=10)
        self.assertEqual(out['schema'],'AURA-XR-SCENE-v1'); self.assertEqual(len(out['entities']),10)
        self.assertTrue(out['review_only']); self.assertTrue(out['projection_only'])
        self.assertFalse(out['execution_authority']); self.assertFalse(out['truth_authority']); self.assertFalse(out['gate10'])

    def test_invalidation_cone_is_exactly_ten(self):
        cone=K27MemoryRuntime(REGISTRY).invalidation_cone('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertEqual(cone['root_path'],[1,0,0]); self.assertEqual(len(cone['affected']),10)
        self.assertFalse(cone['mutation_performed']); self.assertFalse(cone['authority_minted'])

    def test_readonly_publish_holds(self):
        rt=K27MemoryRuntime(REGISTRY)
        b,r=rt.read('FAMILY/BREADBOARD/ACCESSIBILITY')
        with self.assertRaises(PermissionError):
            rt.publish_cas(b.object_id,r['payload'],source_url=r['source_url'],source_version=r['source_version'],
                           expected_revision=b.revision_id,expected_epoch=b.epoch)

    def test_environment_mount_contract(self):
        rt=K27MemoryRuntime.from_environment(env={'AURA_K27_MEMORY_REGISTRY_PATH':str(REGISTRY)})
        self.assertEqual(rt.seal.records,1115)
        with self.assertRaisesRegex(ValueError,'AURA_K27_MEMORY_REGISTRY_PATH'):
            K27MemoryRuntime.from_environment(env={})

    def test_binding_manifest_pins_existing_owners(self):
        m=json.loads((ROOT/'.aura/k27_memory/runtime_binding.v1.json').read_text())
        self.assertEqual(m['owners']['auraos_base_main'],'7a2c7a16f845752ffb7c16c68636d8d542ecd72e')
        self.assertEqual(m['owners']['spatial_seam_parent_sha'],SPATIAL_SEAM_PARENT_SHA)
        self.assertEqual(m['owners']['spatial_route_blob'],SPATIAL_ROUTE_BLOB)
        self.assertEqual(m['owners']['spatial_seam_source_blob'],SPATIAL_SEAM_SOURCE_BLOB)
        self.assertEqual(m['owners']['spatial_seam_module_blob'],SPATIAL_SEAM_MODULE_BLOB)
        self.assertEqual(git_blob_sha1(ROUTE),SPATIAL_ROUTE_BLOB)
        seam_path=ROOT/'tools/arena/k27_memory_city_spatial_seam/k27_memory_city_spatial_seam.py'
        self.assertEqual(git_blob_sha1(seam_path),SPATIAL_SEAM_MODULE_BLOB)
        self.assertEqual(m['scene']['adapter_targets'],['desktop_webgl','webxr','openxr'])
        self.assertFalse(m['authority']['execution_authority']); self.assertFalse(m['authority']['gate10'])

    def test_runtime_seam_receipt_delegates_to_exact_validator_and_route_blob(self):
        rt=K27MemoryRuntime(REGISTRY)
        out=rt.spatial_seam_binding_receipt(ROUTE.read_bytes(),provenance_leaf_manifest())
        self.assertEqual(out['spatial_route_blob'],SPATIAL_ROUTE_BLOB)
        self.assertFalse(out['provider_bytes_bound']); self.assertFalse(out['authority_minted']); self.assertFalse(out['gate10'])
        modified=ROUTE.read_bytes()+b'\n'
        with self.assertRaisesRegex(RuntimeBindingError,'Git blob'):
            rt.spatial_seam_binding_receipt(modified,provenance_leaf_manifest())

    def test_consequence_source_exit_is_unconditionally_noncurrent(self):
        mod=types.ModuleType('consequence_admission_kernel')
        @dataclass(frozen=True)
        class SourceExit:
            source_id:str; owner_ref:str; generation:str; semantic_root:str; current:bool=True
        mod.SourceExit=SourceExit
        old=sys.modules.get('consequence_admission_kernel'); sys.modules['consequence_admission_kernel']=mod
        try:
            rt=K27MemoryRuntime(REGISTRY)
            held=rt.consequence_source_exit('FAMILY/BREADBOARD/ACCESSIBILITY')
            self.assertFalse(held.current)
            with self.assertRaises(TypeError):
                rt.consequence_source_exit('FAMILY/BREADBOARD/ACCESSIBILITY',external_currentness_confirmed=True)
        finally:
            if old is None: sys.modules.pop('consequence_admission_kernel',None)
            else: sys.modules['consequence_admission_kernel']=old

    def test_external_byte_mutation_after_init_holds_before_read_or_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'registry.sqlite'; shutil.copyfile(REGISTRY,p)
            rt=K27MemoryRuntime(p)
            data=bytearray(p.read_bytes()); data[-1]^=1; p.write_bytes(data)
            with self.assertRaisesRegex(RuntimeBindingError,'changed outside'):
                rt.read('FAMILY/BREADBOARD/ACCESSIBILITY')
            with self.assertRaisesRegex(RuntimeBindingError,'changed outside'):
                _=rt.seal

    def test_owned_write_refreshes_seal_and_stale_dependent_can_be_repaired(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'registry.sqlite'; shutil.copyfile(REGISTRY,p)
            rt=K27MemoryRuntime(p,writable=True)
            source='FAMILY/BREADBOARD/ACCESSIBILITY'
            cone=rt.invalidation_cone(source)
            dependent=cone['affected'][0]['object_id']
            src_b,src_r=rt.read(source); dep_b,dep_r=rt.read(dependent)
            payload=dict(src_r['payload']); payload['gate10_repair_probe']='r1'
            src_out=rt.publish_cas(source,payload,source_url=src_r['source_url'],source_version=src_r['source_version'],
                                   expected_revision=src_b.revision_id,expected_epoch=src_b.epoch,
                                   dependencies={},dependency_epochs={})
            self.assertEqual(rt.seal.seal_scope,'working_registry_state')
            self.assertNotEqual(rt.seal.database_sha256,REGISTRY_SHA256)
            with self.assertRaises(StaleMemory): rt.read(dependent)
            dep_epochs={}
            for key in dep_r['dependencies']:
                dep_epochs[key]=rt.read(key)[0].epoch
            repaired=rt.publish_cas(dependent,dep_r['payload'],source_url=dep_r['source_url'],source_version=dep_r['source_version'],
                                    expected_revision=dep_b.revision_id,expected_epoch=dep_b.epoch+1,
                                    dependencies=dep_r['dependencies'],dependency_epochs=dep_epochs)
            self.assertGreater(repaired['epoch'],dep_b.epoch)
            self.assertEqual(rt.read(dependent)[0].state,'fresh')

    def test_k27_path_is_locality_only(self):
        b,_=K27MemoryRuntime(REGISTRY).read('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertIsInstance(b.k27,K27Path); self.assertEqual(b.k27.digits,(1,0,0))
        self.assertNotEqual(b.revision_id,b.k27.label())

if __name__=='__main__': unittest.main()
