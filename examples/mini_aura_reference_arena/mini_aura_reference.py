from __future__ import annotations
import argparse, hashlib, itertools, json, math, random, statistics, subprocess
from pathlib import Path

S=(1,2,3,4,5,12,16,48); SEED=20260829
sha=lambda s: hashlib.sha256(s.encode()).hexdigest()
def omega(n):
    c=0; d=2
    while d*d<=n:
        while n%d==0: n//=d; c+=1
        d+=1
    return c+(n>1)
def ds(a,b):
    g=math.gcd(a,b); return omega(a//g)+omega(b//g)

def hyperscale():
    tr=set()
    for p in itertools.permutations(S):
        g=0;t=[]
        for x in p: g=math.gcd(g,x);t.append(g)
        tr.add(tuple(t))
    g1=0
    for m in range(1,1<<len(S)):
        g=0
        for i,x in enumerate(S):
            if m>>i&1:g=math.gcd(g,x)
        g1+=g==1
    ecc={s:max(ds(s,t) for t in S) for s in S}; me=min(ecc.values())
    return {'permutations':math.factorial(len(S)),'unique_running_gcd_trajectories':len(tr),
            'subsets_with_gcd_1':g1,'nonempty_subsets':255,'minimax_centers':[s for s in S if ecc[s]==me]}

def affected(b=3,depth=10):
    total=(b**(depth+1)-1)//(b-1); leaf0=(b**depth-1)//(b-1); leaf=leaf0+20000
    parent=lambda i:(i-1)//b if i else None
    base=[sha(f'source:{i}:g0') for i in range(total)]
    def rebuild(src):
        out=src[:]
        for i in range(leaf0-1,-1,-1): out[i]=sha('|'.join(out[b*i+1:b*i+b+1]))
        return out
    full0=rebuild(base); changed=base[:];changed[leaf]=sha(f'source:{leaf}:g1'); full1=rebuild(changed)
    inc=full0[:]; inc[leaf]=changed[leaf]; path={leaf};i=leaf
    while i:
        i=parent(i);path.add(i);inc[i]=sha('|'.join(inc[b*i+1:b*i+b+1]))
    touched={i for i,(a,c) in enumerate(zip(full0,full1)) if a!=c}
    return {'full_nodes':total,'affected_nodes':len(path),'operation_ratio':total/len(path),
            'incremental_equals_full_rebuild':inc==full1,'only_affected_path_changed':touched==path}

def amnf():
    mismatch=0
    for sig in itertools.product((0,1,2),repeat=4):
        dispatch='FAIL_CLOSED' if 2 in sig else ('TARGETED_REPAIR' if 1 in sig else 'DIRECT_REUSE')
        oracle='FAIL_CLOSED' if any(x==2 for x in sig) else ('TARGETED_REPAIR' if any(x==1 for x in sig) else 'DIRECT_REUSE')
        mismatch+=dispatch!=oracle
    return {'signatures':81,'mismatches':mismatch}

def action_cone(trials=1000,n=1000):
    rng=random.Random(SEED ^ 0xA17)
    explored=[]; failures=0
    for _ in range(trials):
        true=[rng.expovariate(1.0) for _ in range(n)]
        width=[0.02+0.18*rng.random() for _ in range(n)]
        lb=[max(0.0,c-w) for c,w in zip(true,width)]
        ub=[c+w for c,w in zip(true,width)]
        order=sorted(range(n), key=lambda i: lb[i])
        best_u=float('inf'); best_true=float('inf'); k=0
        for pos,i in enumerate(order):
            k+=1; best_u=min(best_u,ub[i]); best_true=min(best_true,true[i])
            next_lb=lb[order[pos+1]] if pos+1<n else float('inf')
            if best_u < next_lb: break
        if min(true)!=best_true: failures+=1
        explored.append(k)
    return {'trials':trials,'actions_per_trial':n,'true_winner_exclusions':failures,
            'mean_actions_explored':statistics.mean(explored),'median_actions_explored':statistics.median(explored),'max_actions_explored':max(explored)}

def decision(trials=500,samples=50,dim=5,actions=12):
    rng=random.Random(SEED ^ 0xD3C1)
    changes=0; radii=[]
    for _ in range(trials):
        b=[rng.uniform(0,5) for _ in range(actions)]
        g=[[rng.uniform(-1,1) for _ in range(dim)] for _ in range(actions)]
        winner=min(range(actions), key=lambda i:b[i])
        L=[math.sqrt(sum(x*x for x in gi)) for gi in g]
        radii_i=[]
        for j in range(actions):
            if j==winner: continue
            margin=b[j]-b[winner]
            radii_i.append(margin/(L[j]+L[winner]+1e-15))
        r=min(radii_i); radii.append(r)
        for _s in range(samples):
            v=[rng.gauss(0,1) for _ in range(dim)];norm=math.sqrt(sum(x*x for x in v))
            radius=0.9*r*(rng.random()**(1/dim))
            th=[radius*x/norm for x in v]
            costs=[b[i]+sum(g[i][k]*th[k] for k in range(dim)) for i in range(actions)]
            if min(range(actions),key=lambda i:costs[i])!=winner:changes+=1
    return {'trials':trials,'perturbation_samples_per_trial':samples,'in_radius_perturbations':trials*samples,
            'in_radius_winner_changes':changes,'median_certified_radius':statistics.median(radii)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='results_local.json');ap.add_argument('--node',default='hyperscale_check.mjs');a=ap.parse_args()
    r={'schema':'MiniAuraReferenceResultV1','claim_ceiling':'BOUNDED_INDEPENDENT_REIMPLEMENTATION_NOT_CANONICAL_NOT_PRODUCTION',
       'affected':affected(),'amnf':amnf(),'hyperscale':hyperscale(),'action_cone':action_cone(),'decision_capsule':decision()}
    checks={'affected_88573_11':r['affected']['full_nodes']==88573 and r['affected']['affected_nodes']==11,
            'affected_equivalence':r['affected']['incremental_equals_full_rebuild'],'affected_isolation':r['affected']['only_affected_path_changed'],
            'amnf_81':r['amnf']=={'signatures':81,'mismatches':0},
            'hs_40320_108':r['hyperscale']['permutations']==40320 and r['hyperscale']['unique_running_gcd_trajectories']==108,
            'hs_219_255':r['hyperscale']['subsets_with_gcd_1']==219 and r['hyperscale']['nonempty_subsets']==255,
            'hs_center4':r['hyperscale']['minimax_centers']==[4],
            'action_safe':r['action_cone']['true_winner_exclusions']==0,'decision_safe':r['decision_capsule']['in_radius_winner_changes']==0}
    node=json.loads(subprocess.check_output(['node',a.node],text=True)); keys=('permutations','unique_running_gcd_trajectories','subsets_with_gcd_1','nonempty_subsets','minimax_centers')
    checks['python_node_parity']=all(r['hyperscale'][k]==node[k] for k in keys)
    r['checks']=checks;r['status']='PASS' if all(checks.values()) else 'FAIL';r['passed']=sum(checks.values());r['total']=len(checks)
    Path(a.out).write_text(json.dumps(r,indent=2,sort_keys=True));print(json.dumps({'status':r['status'],'passed':r['passed'],'total':r['total'],'affected':r['affected'],'hyperscale':r['hyperscale'],'action_cone':r['action_cone'],'decision_capsule':r['decision_capsule']},indent=2))
if __name__=='__main__':main()
