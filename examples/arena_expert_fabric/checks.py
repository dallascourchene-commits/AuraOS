from expert_fabric import *

def ok(cond,msg):
    if not cond: raise AssertionError(msg)
    return msg

def run():
    results=[]
    t=Task('SID:X',1,'runtime_code','repair',tool_required=True,latency='normal')
    r=choose(t); results.append(ok(r['status']=='ROUTED','route exists'))
    results.append(ok(len(r['k27'])==27 and set(r['k27'])<=set('012'),'K27 exact 27-trit width'))
    results.append(ok(choose(t)==choose(t),'deterministic bundle'))
    t2=Task('SID:X',2,'runtime_code','repair',tool_required=True,latency='normal')
    r2=choose(t2); results.append(ok(r['stable_sid']==r2['stable_sid'] and r['expert_bundle_ref']!=r2['expert_bundle_ref'],'stable SID + generation-bound bundle'))
    p=Task('SID:P',1,'deep_private_reasoning','analysis',privacy='strict_local',latency='batch')
    rp=choose(p); results.append(ok(all('OPENROUTER' not in x for x in rp['selected']),'strict privacy excludes OpenRouter'))
    i=Task('SID:I',1,'runtime_code','repair',tool_required=True,latency='interactive')
    ri=choose(i); results.append(ok('AIRLLM_LARGE_LOCAL' not in ri['selected'],'interactive path excludes slow AirLLM'))
    b=Task('SID:B',1,'batch_falsification','benchmark',benchmark_mode=True,latency='normal')
    rb=choose(b); results.append(ok(rb['selected']==['OPENROUTER_PINNED'],'benchmark pins route'))
    m=Task('SID:M',1,'cross_domain_research','research',diversity_needed=True,latency='normal')
    rm=choose(m); results.append(ok(rm['selected']==['OPENROUTER_TRIAD'],'production diversity can select Triadic panel'))
    d=Task('SID:D',1,'source_currentness','lookup',deterministic_sufficient=True)
    rd=choose(d); results.append(ok(rd['selected']==['NO_MODEL'],'deterministic work avoids model'))
    ck1=cache_key(t,'modelA@v1','preset7','wc1'); ck2=cache_key(t,'modelB@v1','preset7','wc1')
    results.append(ok(ck1!=ck2,'cache key binds model identity'))
    ck3=cache_key(t2,'modelA@v1','preset7','wc1')
    results.append(ok(ck1!=ck3,'cache key binds source generation'))
    ck4=cache_key(t,'modelA@v1','preset8','wc1')
    results.append(ok(ck1!=ck4,'cache key binds preset generation'))
    ck5=cache_key(t,'modelA@v1','preset7','wc2')
    results.append(ok(ck1!=ck5,'cache key binds work capsule'))
    a=Task('SID:A',1,'runtime_code','x',latency='normal'); z=Task('SID:Z',1,'runtime_code','x',latency='normal')
    results.append(ok(choose(a)['expert_bundle_ref']!=choose(z)['expert_bundle_ref'],'semantic identity survives independent of shard'))
    u=Task('SID:U',1,'runtime_code','x',latency='normal'); v=Task('SID:U',1,'cross_domain_research','x',latency='normal',diversity_needed=True)
    results.append(ok(choose(u)['expert_bundle_ref']!=choose(v)['expert_bundle_ref'],'domain lens changes expert bundle'))
    q=Task('SID:Q',1,'deep_private_reasoning','x',privacy='strict_local',latency='interactive',tool_required=True)
    rq=choose(q,local_airllm_available=False)
    results.append(ok(rq['status']=='ROUTED' and rq['selected']==['LOCAL_FAST'],'local fallback stays local'))
    results.append(ok('K27_ROUTES_PHYSICAL_SHARD_NOT_EXPERT_SEMANTICS' in r['laws'],'K27 explicitly nonsemantic'))
    results.append(ok('PRIVACY_AND_AUTHORITY_GATE_BEFORE_COST_OR_SPEED' in r['laws'],'hard gates precede optimization'))
    return {'status':'PASS','passed':len(results),'total':len(results),'checks':results}

if __name__=='__main__':
    import json; print(json.dumps(run(),indent=2))
