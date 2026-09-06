"""Independent full-scan oracles over the materialized local registry."""
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
import json, shutil, time
from persistent_memory import MemoryStore
from world_atlas import FrameAddress
from materialize_registry import OUT, FRAME, GENERATION

def verify():
    start=time.perf_counter();checks=[]
    with MemoryStore(OUT/'research_registry.sqlite') as db:
        all_rows=db.under(FRAME,GENERATION)
        routes=[r for r in all_rows if r['object_id'].startswith('MCXR-')]
        assert len(routes)==1000
        for i in range(10):
            prefix=(2,i)
            oracle={r['object_id'] for r in all_rows if tuple(r['address']['path'])[:len(prefix)]==prefix}
            observed={r['object_id'] for r in db.under(FRAME,GENERATION,prefix)}
            assert observed==oracle
            checks.append({'check':'prefix indexed equals full scan','prefix':prefix,'matches':len(observed),'pass':True})
    for entry in json.loads((OUT/'cold_source_manifest.json').read_text(encoding='utf-8')):
        assert sha256((OUT/entry['file']).read_bytes()).hexdigest()==entry['sha256']
    # Work on a copy: the external source itself has not been updated.
    with TemporaryDirectory(prefix='aura-registry-proof-') as tmp:
        copied=Path(tmp)/'copy.sqlite';shutil.copyfile(OUT/'research_registry.sqlite',copied)
        with MemoryStore(copied) as db:
            records={r['object_id']:r for r in db.under(FRAME,GENERATION)}
            changed='K27-EXT-005';expected={changed}
            while True:
                after=expected | {key for key,r in records.items() if set(r['dependencies']) & expected}
                if after==expected:break
                expected=after
            expected.remove(changed)
            record=records[changed];a=record['address'];payload={**record['payload'],'synthetic_validation_change':True}
            result=db.publish(changed,payload,FrameAddress(a['frame_id'],a['frame_generation'],tuple(a['path']),changed),
                source_url=record['source_url'],source_version=record['source_version']+'/synthetic-test',
                expected_revision=record['revision_id'],expected_epoch=record['epoch'])
            assert set(result['invalidated'])==expected
            for key, prior in records.items():
                now=db.get(key,allow_stale=True)
                if key in expected:assert now['state']=='stale' and now['revision_id']==prior['revision_id']
                elif key != changed:assert now['state']=='fresh' and now['revision_id']==prior['revision_id']
            checks.append({'check':'dependency invalidation equals independent fixed-point oracle',
                'changed_record':changed,'invalidated':len(expected),'unaffected':len(records)-len(expected)-1,'pass':True})
    receipt={'checks':checks,'checks_passed':len(checks),'checks_total':len(checks),'cold_source_hashes_verified':15,
        'records':len(all_rows),'research_routes':len(routes),'synthetic_mutation_on_copy_only':True,
        'wall_seconds':round(time.perf_counter()-start,6),
        'database_sha256':sha256((OUT/'research_registry.sqlite').read_bytes()).hexdigest()}
    (OUT/'registry_verification.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':verify()
