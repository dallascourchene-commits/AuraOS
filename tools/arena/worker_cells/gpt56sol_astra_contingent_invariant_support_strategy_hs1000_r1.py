import json,hashlib
B=['contingent_sensing','branch_activation','invariant_support_hyperedge','dynamic_deadline','static_union','resource_only_parallelism','stale_sensor','stale_task','k27_strategy_route','memory_city_contingent_execution']
C=['false_ready','false_hold','unnecessary_branch_work','hidden_coupling','deadline_miss','global_coordination','stale_evidence','overcoupling','authority_leak','strategy_explosion']
M=['outcome_policy','interval_upper_envelope','conditional_hyperedge','branch_pruning','component_parallelism','support_serialization','currentness_hold','permutation_canonicalization','coordinate_nonauthority_gate','exact_strategy_replay']
xs=[]
for bi,b in enumerate(B):
 for ci,c in enumerate(C):
  for mi,m in enumerate(M):
   xs.append({'candidate_id':f'O10-{bi:02d}{ci:02d}{mi:02d}','boundary':b,'consequence':c,'mechanism':m,'expected_gain':'UNSCORED_AT_FREEZE','claim_ceiling':'CANDIDATE_ONLY'})
raw=json.dumps(xs,sort_keys=True,separators=(',',':')).encode();root=hashlib.sha256(raw).hexdigest();q={}
for x in xs:q.setdefault((x['boundary'],x['consequence']),[]).append(x['candidate_id'])
out={'schema':'aura.astra.hs1000.v6.freeze.v1','raw_count':len(xs),'freeze_root':root,'quotient_count':len(q),'candidates':xs,'quotients':[{'boundary':k[0],'consequence':k[1],'members':v} for k,v in sorted(q.items())]}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
