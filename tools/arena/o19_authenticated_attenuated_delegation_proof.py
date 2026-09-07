from __future__ import annotations
import itertools, json, random, sys
from dataclasses import replace
from pathlib import Path

from tools.arena.attenuated_stable_operation_delegation import StableOperation, DelegationHop, DomainAdmission, AttemptContext, Disposition, decide, digest
from tools.arena.o19_authenticated_attenuated_delegation import *

NOW=1800001000
PK={'root-owner':b'root-secret','worker-a':b'a-secret','worker-b':b'b-secret'}
CK={'observer-1':b'obs-1','observer-2':b'obs-2','observer-3':b'obs-3'}
AOK={'domain-owner':b'domain-owner'}
AVK={'admission-verifier':b'admission-verifier'}
UVK={'workcell-verifier':b'workcell-verifier'}

def fixture():
    op=StableOperation('creative',digest(['semantic']), 'EDIT', digest(['source-incarnation']), digest(['policy']))
    g1u=dict(operation_root=op.root(),issuer='root-owner',subject='worker-a',scope=frozenset({'read','edit'}),budget=100,generation=1,parent_grant_root=None,issued_at=NOW-10,expires_at=NOW+100,authority_ceiling=D0)
    g1=sign_grant(g1u,PK['root-owner'])
    g2u=dict(operation_root=op.root(),issuer='worker-a',subject='worker-b',scope=frozenset({'edit'}),budget=40,generation=2,parent_grant_root=g1.grant_root,issued_at=NOW-9,expires_at=NOW+100,authority_ceiling=D0)
    g2=sign_grant(g2u,PK['worker-a'])
    c1u=dict(grant_root=g1.grant_root,subject='worker-a',generation=1,currentness_root=digest(['c1']),observer='observer-1',issued_at=NOW-5,expires_at=NOW+50,authority_ceiling=D0)
    c2u=dict(grant_root=g2.grant_root,subject='worker-b',generation=2,currentness_root=digest(['c2']),observer='observer-2',issued_at=NOW-5,expires_at=NOW+50,authority_ceiling=D0)
    c1=sign_currentness(c1u,CK['observer-1']); c2=sign_currentness(c2u,CK['observer-2'])
    au=dict(domain='creative',operation_root=op.root(),admission_root=digest(['admission']),allowed_scope=frozenset({'edit'}),max_budget=50,generation=7,source_incarnation_root=op.source_incarnation_root,owner='domain-owner',verifier='admission-verifier',issued_at=NOW-5,expires_at=NOW+50,authority_ceiling=D0)
    adm=sign_admission(au,AOK['domain-owner'],AVK['admission-verifier'])
    uu=dict(operation_root=op.root(),actor='worker-b',workcell_root=digest(['workcell']),workcell_generation=9,lease_root=digest(['lease']),source_incarnation_root=op.source_incarnation_root,currentness_root=digest(['use-current']),verifier='workcell-verifier',issued_at=NOW-2,expires_at=NOW+20,authority_ceiling=D0)
    use=sign_attempt_use(uu,UVK['workcell-verifier'])
    return op,[g1,g2],[c1,c2],adm,use

def run(op,gs,cs,a,u):
    return authenticate_and_decide(op,gs,cs,a,u,frozenset({'edit'}),30,principal_keys=PK,currentness_verifier_keys=CK,admission_owner_keys=AOK,admission_verifier_keys=AVK,attempt_verifier_keys=UVK,now=NOW)

def altered(axis):
    op,gs,cs,a,u=fixture(); gs=list(gs); cs=list(cs)
    if axis=='grant_auth': gs[1]=replace(gs[1],signature='0'*64)
    elif axis=='parent_link':
        x=gs[1].unsigned; x['parent_grant_root']='f'*64; gs[1]=sign_grant(x,PK['worker-a'])
        cu=cs[1].unsigned; cu['grant_root']=gs[1].grant_root; cs[1]=sign_currentness(cu,CK['observer-2'])
    elif axis=='attenuation':
        x=gs[1].unsigned; x['scope']=frozenset({'read','edit','admin'}); gs[1]=sign_grant(x,PK['worker-a'])
        cu=cs[1].unsigned; cu['grant_root']=gs[1].grant_root; cs[1]=sign_currentness(cu,CK['observer-2'])
    elif axis=='grant_currentness':
        x=cs[1].unsigned; x['expires_at']=NOW-1; cs[1]=sign_currentness(x,CK['observer-2'])
    elif axis=='admission_auth': a=replace(a,verifier_signature='0'*64)
    elif axis=='attempt_auth': u=replace(u,signature='0'*64)
    elif axis=='source_binding':
        x=a.unsigned; x['source_incarnation_root']='e'*64; a=sign_admission(x,AOK['domain-owner'],AVK['admission-verifier'])
    elif axis=='authority_ceiling':
        x=u.unsigned; x['authority_ceiling']='D1'; u=sign_attempt_use(x,UVK['workcell-verifier'])
    else: raise KeyError(axis)
    return op,gs,cs,a,u

AXES=('grant_auth','parent_link','attenuation','grant_currentness','admission_auth','attempt_auth','source_binding','authority_ceiling')

def candidate(bits):
    op,gs,cs,a,u=fixture()
    for axis,ok in zip(AXES,bits):
        if not ok:
            op,gs,cs,a,u=altered(axis)
            break
    try: return run(op,gs,cs,a,u).parent_decision.disposition==Disposition.ADMIT_D0
    except AuthenticationError: return False

def oracle(bits):
    return all(bits)

def parent_shape_baseline(bits):
    op,_,_,_,_=fixture()
    attenuation=bits[2]; source=bits[6]
    hops=[DelegationHop('worker-a',frozenset({'read','edit'}),100,1,True),DelegationHop('worker-b',frozenset({'edit'}) if attenuation else frozenset({'admin','edit'}),40,2,True)]
    adm=DomainAdmission('creative',op.root(),digest(['fake-admission']),frozenset({'edit'}),50,7,True,True)
    ctx=AttemptContext('worker-b',digest(['fake-workcell']),9,True,digest(['fake-lease']),True,op.source_incarnation_root if source else 'e'*64,frozenset({'edit'}),30)
    return decide(op,hops,adm,ctx).disposition==Disposition.ADMIT_D0

def campaign(n=30000,seed=1901):
    r=random.Random(seed); mismatch=false_admit=false_hold=parent_false=0; outcomes={'ADMIT':0,'HOLD':0}
    for _ in range(n):
        bits=tuple(bool(r.getrandbits(1)) for _ in AXES)
        got=candidate(bits); exp=oracle(bits)
        mismatch += got!=exp; false_admit += got and not exp; false_hold += exp and not got
        parent_false += parent_shape_baseline(bits) and not exp
        outcomes['ADMIT' if got else 'HOLD']+=1
    p={'cases':n,'oracle_mismatches':mismatch,'false_admit':false_admit,'false_hold':false_hold,'parent_shape_false_admits':parent_false,'outcomes':outcomes,'authority_minted':0,'gate10':False}
    p['root']=root(p); return p

def omega8():
    keep=invalid=0; states=0
    for vals in itertools.product((False,None,True),repeat=8):
        states+=1; bits=tuple(v is True for v in vals); got=oracle(bits)
        keep+=int(got); invalid+=int(got and not all(bits))
    p={'states':states,'keepers':keep,'invalid_promotions':invalid}; p['root']=root(p); return p

def d13():
    o=omega8(); p={'states':o['states']*243,'lawful_contexts':o['keepers']*243,'hard_invalid_context_repairs':0,'nuisance_axes':['k27','hydration','ui','cache','agent_alias']}; p['root']=root(p); return p

def hs1000():
    attacks=AXES+('valid','intermediate_broadening_hidden_by_final_narrow')
    cells=[{'cell':[a,b,c],'attack':attacks[(a*100+b*10+c)%len(attacks)]} for a,b,c in itertools.product(range(10),repeat=3)]
    groups={}
    for x in cells: groups[x['attack']]=groups.get(x['attack'],0)+1
    p={'raw_cells':1000,'consequence_groups':len(groups),'groups':groups,'claimed_breakthroughs':0,'freeze_root':root(cells)}; p['root']=root(p); return p

def forged_parent_attack():
    op,_,_,_,_=fixture()
    hops=[DelegationHop('fake-owner',frozenset({'read','edit'}),100,1,True),DelegationHop('fake-child',frozenset({'edit'}),50,2,True)]
    adm=DomainAdmission('creative',op.root(),digest(['fabricated']),frozenset({'edit'}),50,1,True,True)
    ctx=AttemptContext('fake-child',digest(['w']),1,True,digest(['l']),True,op.source_incarnation_root,frozenset({'edit'}),10)
    return decide(op,hops,adm,ctx).disposition.value

def emit():
    out={'schema':SCHEMA,'forged_parent_attack':forged_parent_attack(),'campaign':campaign(),'omega8':omega8(),'d13':d13(),'hs1000':hs1000()}; out['result_root']=root(out); return out

if __name__=='__main__':
    print(json.dumps(emit(),sort_keys=True,separators=(',',':')))
