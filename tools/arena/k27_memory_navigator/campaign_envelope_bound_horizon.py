from __future__ import annotations
from hashlib import sha256
import json
try:
    from .demand_lease_handoff import DemandCellLease, DemandCellState, canonical_lease_root
    from .envelope_bound_horizon import ConsequenceWorld,PossibilityEnvelope,EnvelopeCompletenessReceipt,EnvelopeVerificationContext,HorizonDisposition,issue_horizon_certificate,admit_horizon_certificate
except ImportError:  # direct-script execution from this directory
    from demand_lease_handoff import DemandCellLease, DemandCellState, canonical_lease_root
    from envelope_bound_horizon import ConsequenceWorld,PossibilityEnvelope,EnvelopeCompletenessReceipt,EnvelopeVerificationContext,HorizonDisposition,issue_horizon_certificate,admit_horizon_certificate

def r(x): return sha256(x.encode()).hexdigest()
def lease(revision=4): return DemandCellLease('cell-11',revision,r('cfg'),8,17,'worker',100)
def cell(revision=4): return DemandCellState('cell-11',revision,r('cfg'),8,17,17)
def world(tag='a', *, support=None,reproof=None,authority=None,support_id=None,transition=None,irrelevant=None): return ConsequenceWorld(support or r('support-closure'),reproof or r('reproof-closure'),authority or r('authority'),support_id or r('support-id'),transition or r('transition-h3'),irrelevant or r('irrelevant-'+tag))
def envelope(*worlds,generation=5): return PossibilityEnvelope(tuple(worlds),generation)
def evidence(env, *, valid=True, verifier=None):
    authority=r('envelope-authority'); vr=verifier or r('envelope-verifier'); rec=EnvelopeCompletenessReceipt(env.consequence_envelope_root() if valid else r('wrong-envelope'),env.completeness_generation,authority,vr); ctx=EnvelopeVerificationContext(authority,r('envelope-verifier')); return rec,ctx
def legacy_ready(cert,current_lease,current_support,observation_epoch,horizon): return canonical_lease_root(current_lease)==cert.lease_root and current_support==cert.support_identity_root and observation_epoch==cert.observation_epoch and horizon==cert.horizon
def oracle(cert,current_lease,env,rec,ctx,current_support,obs,horizon):
    complete=(rec.consequence_envelope_root==env.consequence_envelope_root() and rec.completeness_generation==env.completeness_generation and rec.authority_source_root==ctx.authority_source_root and rec.verifier_receipt_root==ctx.verifier_receipt_root)
    if not complete: return False
    if canonical_lease_root(current_lease)!=cert.lease_root or current_support!=cert.support_identity_root or obs!=cert.observation_epoch or horizon!=cert.horizon: return False
    if env.completeness_generation!=cert.completeness_generation or env.consequence_envelope_root()!=cert.consequence_envelope_root or rec.canonical_receipt_root()!=cert.completeness_receipt_root: return False
    u=env.uniform_consequence_root(current_support); return u is not None and u==cert.uniform_consequence_root

def run(cases=14000):
    base=envelope(world('a'),world('b')); rec,ctx=evidence(base); _,cert=issue_horizon_certificate(lease(),cell(),base,rec,ctx,current_support_identity_root=r('support-id'),observation_epoch=9,horizon=3,now=50); assert cert
    c={k:0 for k in ['oracle_ready','oracle_hold','compiler_false_ready','compiler_false_hold','legacy_false_ready','full_hidden_false_hold','unsupported_completeness_false_ready']}; c['cases']=cases; issuance_full=base.full_hidden_root()
    for i in range(cases):
        mode=i%14; curlease=lease(); curcell=cell(); support=r('support-id'); obs=9; h=3; now=50; env=base; rec,ctx=evidence(env)
        if mode==1: env=envelope(world('a'),world('x',support=r('support-closure-x'))); rec,ctx=evidence(env)
        elif mode==2: env=envelope(world('a'),world('x',reproof=r('reproof-x'))); rec,ctx=evidence(env)
        elif mode==3: env=envelope(world('a'),world('x',authority=r('authority-x'))); rec,ctx=evidence(env)
        elif mode==4: env=envelope(world('a'),world('x',transition=r('transition-x'))); rec,ctx=evidence(env)
        elif mode==5: env=envelope(world('a'),world('x',support_id=r('support-id-x'))); rec,ctx=evidence(env)
        elif mode==6: env=envelope(world('a'),world('b'),generation=6); rec,ctx=evidence(env)
        elif mode==7: rec,ctx=evidence(env,valid=False)
        elif mode==8: obs=10
        elif mode==9: curcell=cell(5)
        elif mode==10: now=100
        elif mode==11: curcell=DemandCellState('cell-11',4,r('cfg'),8,17,16)
        elif mode==12: env=envelope(world('c',irrelevant=r('fresh-irrel-1')),world('d',irrelevant=r('fresh-irrel-2'))); rec,ctx=evidence(env)
        elif mode==13: env=envelope(world('a'),world('b'),world('c')); rec,ctx=evidence(env)
        lease_current=(now < curlease.expires_at and curlease.cell_id==curcell.cell_id and curlease.revision==curcell.revision and curlease.configuration_root==curcell.configuration_root and curlease.support_epoch==curcell.support_epoch and curlease.fence_generation==curcell.fence_generation and curlease.fence_generation==curcell.highest_accepted_fence); expected=(lease_current and oracle(cert,curlease,env,rec,ctx,support,obs,h)); actual=admit_horizon_certificate(cert,curlease,curcell,env,rec,ctx,current_support_identity_root=support,observation_epoch=obs,horizon=h,now=now).disposition is HorizonDisposition.READY_D0; legacy=legacy_ready(cert,curlease,support,obs,h)
        c['oracle_ready' if expected else 'oracle_hold']+=1; c['compiler_false_ready']+=int(actual and not expected); c['compiler_false_hold']+=int(expected and not actual); c['legacy_false_ready']+=int(legacy and not expected); c['unsupported_completeness_false_ready']+=int(mode==7 and actual); c['full_hidden_false_hold']+=int(expected and env.full_hidden_root()!=issuance_full)
    raw=json.dumps(c,sort_keys=True,separators=(',',':')).encode(); out={**c,'campaign_root':sha256(raw).hexdigest(),'schema':'aura.o11.envelope_bound_horizon.campaign.v2','authority':'D0_NONPROMOTING_GATE10_FALSE'}
    if c['compiler_false_ready'] or c['compiler_false_hold'] or c['unsupported_completeness_false_ready']: raise AssertionError(out)
    return out
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
