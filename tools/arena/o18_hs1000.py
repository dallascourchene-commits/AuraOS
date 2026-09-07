import hashlib,json
B=('delegation_chain','operation_identity','scope_attenuation','budget_attenuation','domain_admission','source_incarnation','workcell_currentness','lease_currentness','handoff_rebind','authority_ceiling')
F=('ancestor_stale','scope_escalation','budget_escalation','semantic_move','admission_shape_trust','source_move','workcell_move','lease_expiry','confused_deputy','result_authority_smuggle')
M=('ancestor_chain_proof','stable_operation_root','scope_intersection','budget_minimum','proof_bound_admission','source_incarnation_bind','workcell_generation_bind','attempt_lease_bind','attempt_rotation','d0_nonpromotion')
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 raw=[];i=0
 for b in B:
  for f in F:
   for m in M:
    i+=1;raw.append({'id':f'O18-HS-{i:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantics':'CANDIDATE_NOT_BREAKTHROUGH'})
 freeze=h(raw);groups={}
 for x in raw:groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
 q=[{'boundary':k[0],'failure':k[1],'members':v,'root':h(v)} for k,v in sorted(groups.items())];top=sorted(q,key=lambda x:h({'freeze':freeze,'q':x['root']}))[:27]
 return {'schema':'aura.o18.hs1000.v1','raw':1000,'freeze_root':freeze,'quotients':100,'quotient_root':h(q),'top27_count':27,'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__':print(json.dumps(run(),sort_keys=True,indent=2))
