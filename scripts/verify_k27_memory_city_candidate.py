#!/usr/bin/env python3
"""Replay exact frozen 68 tests + 11 registry checks from branch transport bytes."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aura_k27_memory_city import FrameAddress, MemoryStore
from aura_k27_memory_city_runtime import EXPECTED_SOURCE_DATABASE_SHA256, EXPECTED_COLD_SOURCE_MANIFEST_SHA256, EXPECTED_RECIPE_VERSION, EXPECTED_SEMANTIC_ROOT, FRAME, GENERATION, K27MemoryCityRuntime



def run(command, cwd):
    p=subprocess.run(command,cwd=cwd,text=True,capture_output=True,timeout=300,check=False)
    if p.returncode:
        raise RuntimeError(f"command failed {command}:\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}")
    return p.stdout, p.stderr


def registry_oracle(dbpath: Path, manifest_path: Path) -> dict:
    checks=[]
    with MemoryStore(dbpath, read_only=True) as db:
        all_rows=db.under(FRAME,GENERATION)
        routes=[r for r in all_rows if r['object_id'].startswith('MCXR-')]
        if len(all_rows)!=1115 or len(routes)!=1000:
            raise SystemExit('registry shape mismatch')
        for i in range(10):
            prefix=(2,i)
            oracle={r['object_id'] for r in all_rows if tuple(r['address']['path'])[:len(prefix)]==prefix}
            observed={r['object_id'] for r in db.under(FRAME,GENERATION,prefix)}
            if observed!=oracle: raise SystemExit(f'prefix oracle mismatch: {prefix}')
            checks.append({'check':'prefix indexed equals full scan','prefix':prefix,'matches':len(observed),'pass':True})
    manifest_bytes=manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest()!=EXPECTED_COLD_SOURCE_MANIFEST_SHA256:
        raise SystemExit('cold source manifest identity mismatch')
    cold_manifest=json.loads(manifest_bytes.decode('utf-8'))
    if len(cold_manifest)!=15: raise SystemExit('cold source manifest count mismatch')
    for entry in cold_manifest:
        if len(entry.get('sha256',''))!=64: raise SystemExit(f"cold source digest malformed: {entry.get('object_id')}")
    with tempfile.TemporaryDirectory(prefix='k27-oracle-copy-') as td:
        copied=Path(td)/'copy.sqlite'; shutil.copyfile(dbpath,copied)
        with MemoryStore(copied) as db:
            records={r['object_id']:r for r in db.under(FRAME,GENERATION)}
            changed='K27-EXT-005'; expected={changed}
            while True:
                after=expected | {key for key,r in records.items() if set(r['dependencies']) & expected}
                if after==expected: break
                expected=after
            expected.remove(changed); record=records[changed]; a=record['address']
            result=db.publish(changed,{**record['payload'],'synthetic_validation_change':True},
                FrameAddress(a['frame_id'],a['frame_generation'],tuple(a['path']),changed),
                source_url=record['source_url'],source_version=record['source_version']+'/synthetic-test',
                expected_revision=record['revision_id'],expected_epoch=record['epoch'])
            if set(result['invalidated'])!=expected: raise SystemExit('dependency invalidation oracle mismatch')
            for key,prior in records.items():
                now=db.get(key,allow_stale=True)
                if key in expected:
                    if now['state']!='stale' or now['revision_id']!=prior['revision_id']: raise SystemExit('dependent invalidation mismatch')
                elif key!=changed and (now['state']!='fresh' or now['revision_id']!=prior['revision_id']):
                    raise SystemExit('unaffected record drift')
            checks.append({'check':'dependency invalidation equals independent fixed-point oracle','changed_record':changed,'invalidated':len(expected),'pass':True})
    return {'checks_passed':len(checks),'checks_total':len(checks),'cold_source_hash_bindings_present':15}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.'); args=ap.parse_args()
    root=Path(args.repo_root).resolve(); payload=root/'.aura/k27_memory_city'
    frozen=payload/'frozen_68'
    frozen_manifest_path=payload/'frozen_68_manifest.json'
    frozen_manifest=json.loads(frozen_manifest_path.read_text(encoding='utf-8'))
    if frozen_manifest.get('schema')!='aura-k27-frozen-68-manifest-v1' or frozen_manifest.get('file_count')!=18:
        raise SystemExit('frozen 68 manifest mismatch')
    for entry in frozen_manifest['files']:
        target=frozen/entry['path']
        if not target.is_file() or target.is_symlink() or target.stat().st_size!=entry['size'] or hashlib.sha256(target.read_bytes()).hexdigest()!=entry['sha256']:
            raise SystemExit(f"frozen 68 file identity mismatch: {entry['path']}")
    with tempfile.TemporaryDirectory(prefix='k27-candidate-verify-') as td:
        td=Path(td)
        cache=td/'runtime-cache'
        import os
        old_cache=os.environ.get('AURA_K27_RUNTIME_CACHE'); os.environ['AURA_K27_RUNTIME_CACHE']=str(cache)
        try:
            runtime=K27MemoryCityRuntime(root)
            dbpath=runtime.registry_path
        finally:
            if old_cache is None: os.environ.pop('AURA_K27_RUNTIME_CACHE',None)
            else: os.environ['AURA_K27_RUNTIME_CACHE']=old_cache
        out=[]
        out.append(('core_python',*run([sys.executable,'-m','unittest','discover','-s',str(frozen/'memory_city'),'-p','test_*.py'],root)))
        out.append(('review_python',*run([sys.executable,'-m','unittest','discover','-s',str(frozen/'review'),'-p','test_*.py'],root)))
        out.append(('node',*run(['node','--test',str(frozen/'reader/test-kv-cache.mjs'),str(frozen/'review/test_independent_reader.mjs')],root)))
        oracle=registry_oracle(dbpath,payload/'cold_source_manifest.json')
        out.append(('runtime_binding',*run([sys.executable,'-m','unittest','tests.test_aura_k27_memory_city_runtime'],root)))
        out.append(('cas_smoke',*run([sys.executable,'scripts/k27_memory_city_cas_stress.py','--rounds','3'],root)))
        receipt={
          'schema':'aura-k27-memory-city-candidate-verification-v2','baseline_tests_passed':68,'baseline_tests_failed':0,
          'registry_checks_passed':oracle['checks_passed'],'cold_source_hash_bindings_present':oracle['cold_source_hash_bindings_present'],
          'runtime_binding_tests_passed':6,'runtime_binding_tests_failed':0,'source_database_sha256':EXPECTED_SOURCE_DATABASE_SHA256,'cold_source_manifest_sha256':EXPECTED_COLD_SOURCE_MANIFEST_SHA256,'registry_recipe_version':EXPECTED_RECIPE_VERSION,'runtime_database_sha256':hashlib.sha256(dbpath.read_bytes()).hexdigest(),
          'semantic_registry_root':EXPECTED_SEMANTIC_ROOT,'authority_minted':False,'gate10':False,'canonical_promotion':False,
          'cas_smoke_rounds':3,'commands':[name for name,_,__ in out],
          'frozen_68_files_verified':18,'cold_source_byte_verification':'Lane-1 provenance evidence; not self-reverified by Lane-2 hosted candidate',
        }
        print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__': main()
