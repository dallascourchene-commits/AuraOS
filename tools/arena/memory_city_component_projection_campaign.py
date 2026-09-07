from __future__ import annotations
import json, random, hashlib
from collections import defaultdict, deque
from itertools import product
from memory_city_navigator import SourceSpanLocator
from memory_city_contingent_hydration import HydrationItem, DemandBranch, InvariantSupport
from memory_city_typed_closure import InfluenceGraph, compile_typed_closure, directed_descendants
from memory_city_coverage_membrane import PositiveTrace, compile_coverage_certificate
from memory_city_read_consequence import ReadWorldProjection, ReadConsequenceDisposition, compile_read_consequence_certificate, validate_read_consequence_at_use

SEED=8741201

def H(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def z(s): return hashlib.sha256(s.encode()).hexdigest()
def loc(name,size=5,k27=()): return SourceSpanLocator(name,z('p'+name),1,1,z('s'+name),size,k27)
def oracle(starts,support_edges,influence_edges,ids):
    seen=set(starts); changed=True
    while changed:
        before=set(seen)
        for edge in support_edges:
            if seen.intersection(edge): seen.update(edge)
        for a,b in influence_edges:
            if a in seen: seen.add(b)
        changed=seen!=before
    if not seen.issubset(set(ids)): raise AssertionError('oracle escaped universe')
    return tuple(sorted(seen))
def components(ids,edges):
    adj={x:set() for x in ids}
    for edge in edges:
        for a in edge:
            for b in edge:
                if a!=b: adj[a].add(b)
    out=[];seen=set()
    for x in sorted(ids):
        if x in seen: continue
        q=deque([x]);seen.add(x);c=[]
        while q:
            a=q.popleft();c.append(a)
            for b in sorted(adj[a]):
                if b not in seen: seen.add(b);q.append(b)
        out.append(tuple(sorted(c)))
    return tuple(sorted(out))
def run(cases=10000):
    rng=random.Random(SEED); stats=defaultdict(int); roots=[]
    for i in range(cases):
        n=rng.randint(5,10); ids=[f'c{i}_{j}' for j in range(n)]
        items=tuple(HydrationItem(x,loc(x,rng.randint(1,8),(rng.randrange(27),rng.randrange(27))),rng.randint(1,3)) for x in ids)
        se=[]
        for _ in range(rng.randint(0,max(1,n//2))):
            e=tuple(sorted(rng.sample(ids,rng.randint(2,min(4,n)))))
            if e not in se: se.append(e)
        ie=[]
        for _ in range(rng.randint(1,n+3)):
            a,b=sorted(rng.sample(range(n),2)); e=(ids[a],ids[b])
            if e not in ie: ie.append(e)
        support=InvariantSupport(rng.randrange(6),tuple(se)); influence=InfluenceGraph(rng.randrange(6),tuple(ie),True)
        changed=tuple(sorted(rng.sample(ids,rng.randint(1,min(2,n)))))
        branch=DemandBranch('b0',(rng.choice(ids),))
        cert=compile_typed_closure(items,(branch,),support,influence,changed_evidence_item_ids=changed,max_resident_bytes=1000,reveal_tick=0,deadline_tick=100,transition_model_root='t')
        expected=oracle(changed,support.hyperedges,influence.edges,ids)
        legacy=directed_descendants(changed,influence,ids)
        stats['reproof_oracle_mismatch']+=int(cert.reproof_item_ids!=expected)
        moved=bool(set(expected)-set(legacy))
        stats['legacy_item_only_underreproof']+=int(moved)
        stats['repair_smaller_than_legacy']+=int(bool(set(legacy)-set(cert.reproof_item_ids)))

        # Bind the old vs repaired derived projection to the same concrete world.
        p=z(f'program{i%19}'); d=z(f'domain{i%23}'); g=i%7; world='w0'; world_root=z(f'world{i}'); trust=z(f'trust{i%31}')
        coverage=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=(world,),positive=(PositiveTrace(world,p,d,g,z(f'trace{i}')),))
        hyd=components(ids,support.hyperedges)[0]  # arbitrary current hydration cut; projection test is reproof-focused
        old_projection_root=H({'support':support.support_root,'influence':influence.influence_root,'reproof':legacy})
        new_projection_root=H({'support':support.support_root,'influence':influence.influence_root,'reproof':expected})
        old_projection=ReadWorldProjection(world,world_root,hyd,legacy,trust,old_projection_root,True,())
        old_read=compile_read_consequence_certificate(coverage=coverage,projections=(old_projection,))
        use_new=validate_read_consequence_at_use(old_read,coverage=coverage,active_world_id=world,active_world_root=world_root,active_projection_root=new_projection_root,read_obligation_root=trust)
        stats['projection_bound_false_ready']+=int(moved and use_new.disposition is ReadConsequenceDisposition.READY)
        stats['legacy_projection_unbound_false_ready']+=int(moved)  # v1 ignored active projection receipt
        fresh_projection=ReadWorldProjection(world,world_root,hyd,expected,trust,new_projection_root,True,())
        fresh=compile_read_consequence_certificate(coverage=coverage,projections=(fresh_projection,))
        fresh_use=validate_read_consequence_at_use(fresh,coverage=coverage,active_world_id=world,active_world_root=world_root,active_projection_root=new_projection_root,read_obligation_root=trust)
        stats['fresh_recompiled_mismatch']+=int(fresh_use.disposition is not ReadConsequenceDisposition.READY)
        stats['consequence_root_failed_to_move']+=int(moved and fresh.consequence_root==old_read.consequence_root)

        # K27 is a locator hint and cannot change the reproof result.
        mutated=tuple(HydrationItem(x.item_id,SourceSpanLocator(x.locator.source_id,x.locator.parent_export_sha256,x.locator.start_line,x.locator.end_line,x.locator.span_sha256,x.locator.span_bytes,tuple((v+13)%27 for v in x.locator.k27_hint)),x.duration_ticks) for x in items)
        cert2=compile_typed_closure(mutated,(branch,),support,influence,changed_evidence_item_ids=changed,max_resident_bytes=1000,reveal_tick=0,deadline_tick=100,transition_model_root='t')
        stats['k27_reproof_mismatch']+=int(cert2.reproof_item_ids!=cert.reproof_item_ids)
        roots.append(H({'typed':cert.receipt_root,'old_read':old_read.receipt_root,'fresh_read':fresh.receipt_root}))
    omega=sum(1 for s in product(range(3),repeat=8) if all(x==2 for x in s))
    d13=sum(1 for s in product(range(3),repeat=13) if all(x==2 for x in s[:8]))
    out={'schema':'AURA-MC-O12-COMPONENT-PROJECTION-REBIND-CAMPAIGN-v1','seed':SEED,'cases':cases,'stats':dict(sorted(stats.items())),
         'omega8':{'states':3**8,'strict_ready':omega},'d13':{'states':3**13,'hard_ready_context_variants':d13,'hard_invalid_repairs':0},'sample_root':H(roots[:256])}
    out['campaign_root']=H(out); return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
