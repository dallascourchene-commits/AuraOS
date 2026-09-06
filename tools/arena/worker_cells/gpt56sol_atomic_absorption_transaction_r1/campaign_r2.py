from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hashlib,itertools,json
from dataclasses import replace
from atomic_absorption import Proposal,OwnerSnapshot,Disposition,plan,commit,omega8_keeper,context13_preserves_invalid,digest

H=hashlib.sha256(b'AuraOS-main:7a2c7a16f845752ffb7c16c68636d8d542ecd72e').hexdigest(); T=hashlib.sha256(b'ResearchTestSpec-owner-tree-v0').hexdigest()
SNAP=OwnerSnapshot(H,T); LINE=hashlib.sha256(b'line').hexdigest()
def hx(s): return hashlib.sha256(s.encode()).hexdigest()
def P(pid,cons,rec,files,base=H,auth=False,actor='a',line=LINE): return Proposal(pid,actor,line,base,cons,rec,files,auth)
def oracle(kind): return {0:Disposition.READY,1:Disposition.READY,2:Disposition.CONFLICT_HOLD,3:Disposition.CONFLICT_HOLD,4:Disposition.CONFLICT_HOLD,5:Disposition.REBASE_REQUIRED,6:Disposition.DEBRIS_HOLD,7:Disposition.AUTHORITY_HOLD,8:Disposition.CONFLICT_HOLD,9:Disposition.READY}[kind]
def case(i,kind):
    c=hx(f'cons-{i//10}'); r=hx(f'rec-{i//10}'); blob=hx(f'blob-{i}'); files={f'pkg/f{i%7}.py':blob}; a=P(f'A{i}',c,r,files)
    if kind==0: return [a]
    if kind==1: return [a,P(f'B{i}',c,r,files,actor='relay',line=hx('relay'))]
    if kind==2: return [a,P(f'B{i}',c,hx(f'alt-rec-{i}'),files)]
    if kind==3:
        f=dict(files); f[next(iter(f))]=hx(f'alt-blob-{i}'); return [a,P(f'B{i}',c,r,f)]
    if kind==4: return [a,P(f'A{i}',hx(f'other-cons-{i}'),hx(f'other-rec-{i}'),{f'alt/g{i%5}.py':hx('x'+str(i))})]
    if kind==5: return [P(f'A{i}',c,r,files,base=hx('stale'))]
    if kind==6: return [P(f'A{i}',c,r,{f'pkg/x{i}.tmp':blob})]
    if kind==7: return [P(f'A{i}',c,r,files,auth=True)]
    if kind==8: return [a,P(f'B{i}',hx(f'other-{i}'),hx(f'r2-{i}'),{next(iter(files)):hx(f'alt-{i}')})]
    if kind==9: return [a,P(f'B{i}',hx(f'other-{i}'),hx(f'r2-{i}'),{f'pkg/other{i}.py':hx(f'alt-{i}')})]
    raise ValueError(kind)

def run(n=100000):
    mismatches=false_ready=exact_redelivery_fail=0; roots=[]
    for i in range(n):
        k=i%10; pl=plan(SNAP,case(i,k)); exp=oracle(k)
        mismatches += pl.disposition!=exp
        false_ready += k in (2,3,4,5,6,7,8) and pl.disposition==Disposition.READY
        exact_redelivery_fail += k==1 and (pl.disposition!=Disposition.READY or not pl.collapsed_proposals)
        if i<1000: roots.append(pl.manifest_root)
    hs_mismatch=forged_commit_escape=legacy_commit_escape=0
    for i in range(1000):
        ps=case(i,0); pl=plan(SNAP,ps)
        hs_mismatch += not commit(pl,H,snapshot=SNAP,proposals=ps).committed
        forged=replace(pl,writes=((f'evil/{i}.py','f'*64),),manifest_root='e'*64,effect_authority=True,gate10=True)
        forged_commit_escape += commit(forged,H,snapshot=SNAP,proposals=ps).committed
        legacy_commit_escape += commit(pl,H).committed
    om=sum(omega8_keeper(x) for x in itertools.product(range(3),repeat=8))
    tails=sum(context13_preserves_invalid((2,2,2,2,2,2,1,1),t) for t in itertools.product(range(3),repeat=5))
    bridge_files={'tools/arena/research_testspec/hs1000_testspec_bridge.py':'722042d9963f51e4bf44d8ceb3cfc50ad7093edb1a35898d8a1867a5fb8b28ab','tools/arena/research_testspec/test_hs1000_testspec_bridge.py':'2f8cc918ad7874960310efe97497686fe60240c4eeb46b3236b6447cd4595525','tools/arena/research_testspec/hs1000_testspec_campaign.py':'83e2939cc01a982dc5dd3ffbbfa9e37d614d0f1efc5874a02eeded2971d96b13','tools/arena/research_testspec/HS1000_TOP27_TESTSPECS.jsonl':'af5e8517aef5161c5c28938f502d9c8b06faf95720f64068e2cd9a6aed883153','tools/arena/research_testspec/HS1000_TESTSPEC_BRIDGE.md':'4e2debe910a6f9a2fd4e41939908a8f656bb3c202aba2665ec090e27ad4f7f30'}
    bridge=P('HS1000-TESTSPEC-BRIDGE','24bff04a0eb14449f4fd03f796516f602b959e3eeca5b5d666295a8378692b25','30b7aeb9b5f520f7532631603f30e3660052492e59f5847aa89579c993bb63be',bridge_files,actor='GPT56SOL',line=hx('GPT56SOL-HS1000-TestSpec-Bridge'))
    bp=plan(SNAP,[bridge]); br=commit(bp,H,snapshot=SNAP,proposals=[bridge])
    out={'random_cases':n,'mismatches':mismatches,'false_ready':false_ready,'exact_redelivery_fail':exact_redelivery_fail,'hs1000_cases':1000,'hs1000_mismatches':hs_mismatch,'forged_commit_escapes':forged_commit_escape,'legacy_commit_escapes':legacy_commit_escape,'omega8_states':6561,'omega8_keepers':om,'tail13_states':243,'invalid_repairs':tails,'bridge_fixture_disposition':bp.disposition.value,'bridge_fixture_write_count':len(bp.writes),'bridge_fixture_commit':br.committed,'bridge_fixture_manifest_root':bp.manifest_root,'sample_manifest_root':digest(roots),'campaign_root':''}
    out['campaign_root']=digest({k:v for k,v in out.items() if k!='campaign_root'})
    print(json.dumps(out,sort_keys=True,indent=2))
    assert mismatches==false_ready==exact_redelivery_fail==hs_mismatch==forged_commit_escape==legacy_commit_escape==tails==0
    assert om==1 and br.committed and bp.disposition is Disposition.READY
    return out
if __name__=='__main__': run()
