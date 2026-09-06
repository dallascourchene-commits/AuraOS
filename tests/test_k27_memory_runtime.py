import copy, json, os, shutil, sqlite3, sys, tempfile, unittest, types
from hashlib import sha1
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / 'tools' / 'arena'
sys.path.insert(0, str(ARENA))

from k27_memory_runtime import (
    K27MemoryRuntime, REGISTRY_SHA256, SEMANTIC_REGISTRY_ROOT, FRAME, GENERATION,
    SPATIAL_SEAM_PARENT_SHA, SPATIAL_ROUTE_BLOB, SPATIAL_SEAM_SOURCE_BLOB, SPATIAL_SEAM_MODULE_BLOB,
)
from k27_memory import MemoryConflict, MemoryStore, FrameAddress, K27Path

REGISTRY = Path(os.environ['AURA_K27_TEST_REGISTRY'])


def git_blob_sha1(path: Path) -> str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

class RuntimeTests(unittest.TestCase):
    def test_exact_seal(self):
        rt=K27MemoryRuntime(REGISTRY)
        self.assertEqual(rt.seal.database_sha256,REGISTRY_SHA256)
        self.assertEqual(rt.seal.semantic_registry_root,SEMANTIC_REGISTRY_ROOT)
        self.assertEqual(rt.seal.records,1115)
        self.assertFalse(rt.seal.authority_minted); self.assertFalse(rt.seal.gate10)

    def test_real_family_coordinate_not_synthetic(self):
        rt=K27MemoryRuntime(REGISTRY)
        b,r=rt.read('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertEqual(b.path,(1,0,0)); self.assertEqual(b.epoch,1)
        self.assertEqual(b.revision_id,'3342e295f42ff524fcd4976340f09cf395b20b50c2962cd231bb369fdf202936')
        self.assertEqual(r['payload']['family_id'],'BREADBOARD/ACCESSIBILITY')
        self.assertFalse(b.upstream_currentness_asserted); self.assertFalse(b.truth_authority)

    def test_route_prefix_is_1000(self):
        rt=K27MemoryRuntime(REGISTRY)
        self.assertEqual(len(rt.under((2,))),1000)

    def test_scene_shell_review_only(self):
        rt=K27MemoryRuntime(REGISTRY)
        out=rt.scene_shell((2,0,0),limit=10)
        self.assertEqual(out['schema'],'AURA-XR-SCENE-v1')
        self.assertEqual(len(out['entities']),10)
        self.assertTrue(out['review_only']); self.assertTrue(out['projection_only'])
        self.assertFalse(out['execution_authority']); self.assertFalse(out['truth_authority']); self.assertFalse(out['gate10'])

    def test_real_route_projection(self):
        rt=K27MemoryRuntime(REGISTRY)
        route=rt.under((2,0,0))[0]
        out=rt.route_projection(route.object_id)
        self.assertEqual(out['binding']['path'][:3],(2,0,0))
        self.assertEqual(out['payload']['claim'],'research route; not demonstrated advancement')
        self.assertFalse(out['execution_authority']); self.assertFalse(out['gate10'])

    def test_invalidation_cone_is_exactly_ten(self):
        rt=K27MemoryRuntime(REGISTRY)
        cone=rt.invalidation_cone('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertEqual(cone['root_path'],[1,0,0])
        self.assertEqual(len(cone['affected']),10)
        self.assertEqual({tuple(x['path_key'].strip('/').split('/')) for x in cone['affected']},
                         {('02','00','00',f'{i:02d}') for i in range(10)})
        self.assertFalse(cone['mutation_performed']); self.assertFalse(cone['authority_minted'])

    def test_readonly_publish_holds(self):
        rt=K27MemoryRuntime(REGISTRY)
        b,r=rt.read('FAMILY/BREADBOARD/ACCESSIBILITY')
        with self.assertRaises(PermissionError):
            rt.publish_cas(b.object_id,r['payload'],source_url=r['source_url'],source_version=r['source_version'],
                           expected_revision=b.revision_id,expected_epoch=b.epoch,dependencies=r['dependencies'])

    def test_environment_mount_contract(self):
        rt=K27MemoryRuntime.from_environment(env={'AURA_K27_MEMORY_REGISTRY_PATH':str(REGISTRY)})
        self.assertEqual(rt.seal.records,1115)
        with self.assertRaisesRegex(ValueError,'AURA_K27_MEMORY_REGISTRY_PATH'):
            K27MemoryRuntime.from_environment(env={})

    def test_binding_manifest_pins_existing_owners(self):
        m=json.loads((ROOT/'.aura/k27_memory/runtime_binding.v1.json').read_text())
        self.assertEqual(m['owners']['auraos_base_main'],'7a2c7a16f845752ffb7c16c68636d8d542ecd72e')
        self.assertEqual(m['owners']['consequence_admission_blob'],'70e90d834cf5e8f3c86789d07565119136dced58')
        self.assertEqual(m['owners']['spatial_seam_parent_sha'],SPATIAL_SEAM_PARENT_SHA)
        self.assertEqual(m['owners']['spatial_route_blob'],SPATIAL_ROUTE_BLOB)
        self.assertEqual(m['owners']['spatial_seam_source_blob'],SPATIAL_SEAM_SOURCE_BLOB)
        self.assertEqual(m['owners']['spatial_seam_module_blob'],SPATIAL_SEAM_MODULE_BLOB)
        route_path=ROOT/'.aura/arena_routes/spatial.v1.json'
        seam_path=ROOT/'tools/arena/k27_memory_city_spatial_seam/k27_memory_city_spatial_seam.py'
        self.assertEqual(git_blob_sha1(route_path),SPATIAL_ROUTE_BLOB)
        self.assertEqual(git_blob_sha1(seam_path),SPATIAL_SEAM_MODULE_BLOB)
        self.assertEqual(m['scene']['adapter_targets'],['desktop_webgl','webxr','openxr'])
        self.assertEqual(m['registry']['provenance_manifest_sha256'],'1c8c69ab9d3c8ed9a7badff9fb22da187cbc22c73019210b4dc2194690e1588b')
        self.assertEqual(m['owners']['spatial_transition'],'SPATIAL.GROUND.COMPILE_SCENE')
        self.assertEqual(m['registry']['lane1_exact_wave1_bundle_sha256'],'75316c79966cd95d22a72cf8a91bcf3e9452d78f2817a4ed1020220334b64e3c')
        self.assertFalse(m['authority']['execution_authority']); self.assertFalse(m['authority']['gate10'])

    def test_pr859_spatial_seam_binds_without_authority_widening(self):
        manifest={
            'transitions':[
                {'transition_id':'SPATIAL.GROUND.COMPILE_SCENE','memory_city_binding':{
                    'binding_schema':'AURA-K27-SPATIAL-SEAM-v1',
                    'provenance_archive_sha256':'042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319',
                    'scene_schema':'AURA-XR-SCENE-v1',
                    'read_apis':{name:'REVIEW_ONLY' for name in (
                        'CITY_K27_CONTEXT','CITY_SCENE_SHELL','CITY_ROUTE','CITY_WHY',
                        'CITY_ACTIVE_DOMAINS','CITY_INVALIDATION_CONE')},
                    'strict_hold_unknown':True,'projection_only':True,
                    'renderer_authority':False,'execution_authority':False,
                    'effect_authority':False,'gate10':False,
                }}
            ],
            'authority':{'execution_authority':False,'automatic_merge':False},
        }
        out=K27MemoryRuntime(REGISTRY).spatial_seam_binding_receipt(manifest)
        self.assertEqual(out['spatial_seam_parent_sha'],SPATIAL_SEAM_PARENT_SHA)
        self.assertEqual(out['spatial_route_blob'],SPATIAL_ROUTE_BLOB)
        self.assertEqual(out['spatial_seam_source_blob'],SPATIAL_SEAM_SOURCE_BLOB)
        self.assertEqual(out['spatial_seam_module_blob'],SPATIAL_SEAM_MODULE_BLOB)
        self.assertEqual(out['records'],1115)
        self.assertFalse(out['truth_authority']); self.assertFalse(out['execution_authority'])
        self.assertFalse(out['effect_authority']); self.assertFalse(out['authority_minted']); self.assertFalse(out['gate10'])

    def test_spatial_seam_authority_widening_holds(self):
        base={
            'transitions':[{'transition_id':'SPATIAL.GROUND.COMPILE_SCENE','memory_city_binding':{
                'binding_schema':'AURA-K27-SPATIAL-SEAM-v1',
                'provenance_archive_sha256':'042e78055f23def062e07aaf412524be01a590f969d8f474c143b34f6b45c319',
                'scene_schema':'AURA-XR-SCENE-v1',
                'read_apis':{name:'REVIEW_ONLY' for name in (
                    'CITY_K27_CONTEXT','CITY_SCENE_SHELL','CITY_ROUTE','CITY_WHY',
                    'CITY_ACTIVE_DOMAINS','CITY_INVALIDATION_CONE')},
                'strict_hold_unknown':True,'projection_only':True,
                'renderer_authority':False,'execution_authority':True,
                'effect_authority':False,'gate10':False,
            }}],
            'authority':{'execution_authority':False,'automatic_merge':False},
        }
        with self.assertRaisesRegex(ValueError,'execution_authority'):
            K27MemoryRuntime(REGISTRY).spatial_seam_binding_receipt(base)

    def test_consequence_source_exit_does_not_self_mint_external_currentness(self):
        mod=types.ModuleType('consequence_admission_kernel')
        @dataclass(frozen=True)
        class SourceExit:
            source_id:str; owner_ref:str; generation:str; semantic_root:str; current:bool=True
        mod.SourceExit=SourceExit
        old=sys.modules.get('consequence_admission_kernel'); sys.modules['consequence_admission_kernel']=mod
        try:
            rt=K27MemoryRuntime(REGISTRY)
            held=rt.consequence_source_exit('FAMILY/BREADBOARD/ACCESSIBILITY')
            admitted=rt.consequence_source_exit('FAMILY/BREADBOARD/ACCESSIBILITY',external_currentness_confirmed=True)
            self.assertFalse(held.current); self.assertTrue(admitted.current)
            self.assertEqual(held.semantic_root,'3342e295f42ff524fcd4976340f09cf395b20b50c2962cd231bb369fdf202936')
        finally:
            if old is None: sys.modules.pop('consequence_admission_kernel',None)
            else: sys.modules['consequence_admission_kernel']=old

    def test_byte_tamper_holds(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.sqlite'; shutil.copyfile(REGISTRY,p)
            data=bytearray(p.read_bytes()); data[-1]^=1; p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'SHA-256'):
                K27MemoryRuntime(p)

    def test_k27_path_is_locality_only(self):
        b,_=K27MemoryRuntime(REGISTRY).read('FAMILY/BREADBOARD/ACCESSIBILITY')
        self.assertIsInstance(b.k27,K27Path)
        self.assertEqual(b.k27.digits,(1,0,0))
        self.assertNotEqual(b.revision_id,b.k27.label())

    def test_hardened_spatial_seam_f1_f2_f4(self):
        seam_dir=ROOT/'tools/arena/k27_memory_city_spatial_seam'; sys.path.insert(0,str(seam_dir))
        from k27_memory_city_spatial_seam import validate_spatial_seam, SCENE_SOURCE_SHA256
        route=json.loads((ROOT/'.aura/arena_routes/spatial.v1.json').read_text())
        pm={'files':{'k27_memory/cold_sources/MC-SRC-O1O9.md':{'sha256':SCENE_SOURCE_SHA256}}}
        target=next(t for t in route['transitions'] if t['transition_id']=='SPATIAL.GROUND.COMPILE_SCENE')
        duplicate=copy.deepcopy(route); duplicate['transitions'].append(copy.deepcopy(target))
        r=validate_spatial_seam(json.dumps(duplicate,separators=(',',':')).encode(),pm)
        self.assertIn('COMPILE_SCENE_TRANSITION_CARDINALITY_NOT_ONE',r.reasons)
        malformed=copy.deepcopy(route); malformed['transitions']=7
        r=validate_spatial_seam(json.dumps(malformed,separators=(',',':')).encode(),pm)
        self.assertIn('TRANSITIONS_LIST_REQUIRED',r.reasons)
        unknown=copy.deepcopy(route); next(t for t in unknown['transitions'] if t['transition_id']=='SPATIAL.GROUND.COMPILE_SCENE')['memory_city_binding']['unknown_extension']=1
        r=validate_spatial_seam(json.dumps(unknown,separators=(',',':')).encode(),pm)
        self.assertIn('BINDING_KEYSET_MISMATCH',r.reasons)

    def test_exact_provider_bytes_gate_when_supplied(self):
        keys=('AURA_K27_PROVENANCE_ARCHIVE','AURA_K27_PROVENANCE_MANIFEST','AURA_K27_SCENE_SOURCE')
        if not all(os.environ.get(k) for k in keys): self.skipTest('Different-J provider-byte inputs not mounted')
        seam_dir=ROOT/'tools/arena/k27_memory_city_spatial_seam'; sys.path.insert(0,str(seam_dir))
        from k27_memory_city_spatial_seam import validate_files, SeamDisposition
        r=validate_files(ROOT/'.aura/arena_routes/spatial.v1.json',os.environ[keys[0]],os.environ[keys[1]],os.environ[keys[2]])
        self.assertEqual(r.disposition,SeamDisposition.READY_FOR_INDEPENDENT_REVIEW)
        self.assertTrue(r.provider_bytes_bound); self.assertEqual(r.manifest_payloads_verified,69)

if __name__=='__main__': unittest.main()
