"""Build a replayable local research registry and compatible K27 lookup fragment."""
from hashlib import sha256
from pathlib import Path
import json, os, shutil, tempfile, time
from datetime import datetime, timezone
from build_research_registry import build, OUT, SOURCE
from persistent_memory import MemoryStore, canonical
from world_atlas import FrameAddress

FRAME = 'aura-memory-city-research'
GENERATION = '20260906-v1'
INTERNAL = [
 ('MC-SRC-O1O9','1cSfomuQTT1yvbQtbHojpz8kccDbGT3g7D6mqWIqqPQM'),
 ('MC-SRC-J189','1J3OeKG0aFR6FwWI6rnZKPBgyXMvf-PiMDiIUd7YlZPA'),
 ('MC-SRC-QUOTIENT','1rfXgADuAX6L9tcfPVcUNuKcj1iM0PCITKdPkmQT0FxM'),
 ('MC-SRC-SEMANTIC','1U17o_5GL4aYMyn5y1_z6Xa3W9AcFHaRBB4UKjOMTr7o'),
 ('MC-SRC-PRINCIPAL','1T7koDLfEJqg1FJFJfF99fOEfCMupemHuOo6IsRYYmbY'),
]

def materialize():
    started=time.perf_counter(); routes,families,hot=build()
    cold=OUT/'cold_sources';cold.mkdir(exist_ok=True)
    root=OUT.parents[1]
    retained=[]; observations=[]
    for key, fid in INTERNAL:
        existing=root/'work/k27_memory/sources'/f'{fid}.md'
        target=cold/f'{key}.md'
        if existing.exists(): shutil.copyfile(existing,target)
        elif not target.exists(): raise FileNotFoundError(f'required retained source: {target}')
        first=target.read_text(encoding='utf-8').splitlines()[:4]
        version=next(line.split(': ',1)[1] for line in first if line.startswith('Provider modified time:'))
        retained.append({'object_id':key,'url':f'https://docs.google.com/document/d/{fid}/edit',
            'version':version,'file':target.relative_to(OUT).as_posix(),
            'sha256':sha256(target.read_bytes()).hexdigest(),
            'scope':'complete retained connector text snapshot, including retrieval header; not original provider raw bytes'})
    external=json.loads((OUT/'external_sources.json').read_text(encoding='utf-8'))
    for source in external['sources']:
        entry=dict(source); observed=entry.pop('retrieved_at_utc',None)
        key=source['source_id'];target=cold/f'{key}.json'
        target.write_text(canonical(entry)+'\n',encoding='utf-8')
        retained.append({'object_id':key,'url':source['url'],'version':source['version'],
            'file':target.relative_to(OUT).as_posix(),'sha256':sha256(target.read_bytes()).hexdigest(),
            'scope':'retained bibliographic/evidence record only; full external document bytes were not captured'})
        observations.append({'object_id':key,'observed_at_utc':observed,'external_currentness':'not reauthenticated by this build'})
    keys={}; coords=[]
    with tempfile.TemporaryDirectory(prefix='memory-registry-',dir=OUT) as temp:
        dbpath=Path(temp)/'research_registry.sqlite'
        with MemoryStore(dbpath) as store:
            store.register_frame(FRAME,GENERATION)
            for i,source in enumerate(retained):
                # All cold bytes are verified immediately before their binding is published.
                actual=sha256((OUT/source['file']).read_bytes()).hexdigest()
                if actual != source['sha256']:raise ValueError('cold source changed during registry build')
                key=source['object_id'];address=FrameAddress(FRAME,GENERATION,(0,i),key)
                keys[key]=store.publish(key,source,address,source_url=source['url'],source_version=source['version'])['revision_id']
            primitives=list(dict.fromkeys(t['primitive'] for t in sorted(routes,key=lambda r:r['family_id'])))
            concerns=list(dict.fromkeys(t['concern'] for t in sorted(routes,key=lambda r:r['family_id'])))
            operators=sorted({r['operator'] for r in routes})
            for family_id,f in families.items():
                key='FAMILY/'+family_id
                deps={sid:keys[sid] for sid in ['MC-SRC-O1O9',*f['external_source_keys']]}
                address=FrameAddress(FRAME,GENERATION,(1,primitives.index(f['primitive']),concerns.index(f['concern'])),key)
                keys[key]=store.publish(key,f,address,source_url=SOURCE,source_version='O7-enriched-candidate-v1',dependencies=deps)['revision_id']
            for r in routes:
                key=r['id'];family='FAMILY/'+r['family_id']
                address=FrameAddress(FRAME,GENERATION,(2,primitives.index(r['primitive']),concerns.index(r['concern']),operators.index(r['operator'])),key)
                keys[key]=store.publish(key,r,address,source_url=SOURCE,source_version='O7-route-enriched-v1',dependencies={family:keys[family]})['revision_id']
            rows=store.under(FRAME,GENERATION)
            assert len(rows)==1115
            for record in rows:
                coords.append({'object_id':record['object_id'],'revision_id':record['revision_id'],
                    'payload_sha256':record['payload_sha256'],'address':record['address'],'epoch':record['epoch']})
            assert len(store.under(FRAME,GENERATION,(2,)))==1000
            assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        with MemoryStore(dbpath) as reopened:
            assert len(reopened.under(FRAME,GENERATION,(2,)))==1000
            assert all(reopened.get(key)['revision_id']==rev for key,rev in keys.items())
        os.replace(dbpath,OUT/'research_registry.sqlite')
    kv=[]
    for entry in sorted(coords,key=lambda x:x['object_id']):
        key=entry['object_id'];is_route=key.startswith('MCXR-')
        kv.append({'K':'α0/triad-3/MEMCITY-REGISTRY/'+key,'V':{
            'cell':'MEMCITY-RESEARCH-REGISTRY-V1','digest':entry['revision_id'][:16],
            'standing':'candidate research route; not verified advancement' if is_route else 'local persisted reference; external currentness not asserted',
            'reopen':'Reopen exact full revision and retained source hash; recheck upstream source/frame generations before consequential reuse.',
            'successor':'research_registry.sqlite object '+key+'; full revision '+entry['revision_id']}})
    cache={'schema':{'name':'aura-coordinate-memory-kv-v1','version':'1.0.0'},
        'metadata':{'row_count':len(kv),'scope':'separate local research fragment; original frozen cache unchanged'},
        'rows':kv,'validation':{'checks':[],'result':'No stored validation assertions; use the reader and executed build receipt.'}}
    (OUT/'external-world-k27-memory-city.json').write_text(json.dumps(cache,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'persistent_coordinates.json').write_text(json.dumps(coords,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'cold_source_manifest.json').write_text(json.dumps(retained,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'source_observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    receipt={'created_at_utc':datetime.now(timezone.utc).isoformat(),'database_records':len(coords),'source_records':len(retained),
        'change_families':len(families),'research_routes':len(routes),'hot_families':len(hot),
        'implemented_advancements_inferred_from_route_count':0,'sqlite_integrity':'ok','exact_revision_restart_roundtrips':len(keys),
        'build_wall_seconds':round(time.perf_counter()-started,6),'frame':FRAME,'frame_generation':GENERATION,
        'semantic_registry_root':sha256(canonical(sorted(coords,key=lambda x:x['object_id'])).encode()).hexdigest(),
        'database_sha256':sha256((OUT/'research_registry.sqlite').read_bytes()).hexdigest(),
        'logical_cache_only':True,'external_currentness_reauthenticated':False}
    (OUT/'registry_build_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':materialize()
