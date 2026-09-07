import hashlib,json
B=("program_identity","sealed_domain","obligation_partition","positive_trace","negative_proof","proof_currentness","support_influence_binding","transition_horizon","k27_locator","authority_cut")
F=("unseen_branch","stale_trace","unsound_negative","domain_widen","program_move","generation_move","sampled_subset","no_observation","forged_completeness","mutation_crosscast")
M=("positive_discharge","negative_discharge","pending_membrane","identity_rebind","currentness_rebind","proof_receipt","coverage_quotient","h0_rebind","counterexample","noncompensatory_hold")
def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build():
 raw=[];n=0
 for b in B:
  for f in F:
   for m in M:
    n+=1;raw.append({'id':f'MC-O10-HS-{n:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantic_class':'CANDIDATE_NOT_BREAKTHROUGH'})
 freeze=h(raw); groups={}
 for x in raw: groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
 q=[{'boundary':k[0],'failure':k[1],'members':tuple(v),'root':h(v)} for k,v in sorted(groups.items())]
 top=sorted(q,key=lambda x:h({'f':freeze,'q':x['root']}))[:27]
 return {'raw':1000,'freeze_root':freeze,'quotients':100,'quotient_root':h(q),'top27_count':27,'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__': print(json.dumps(build(),sort_keys=True,separators=(",",":")))
