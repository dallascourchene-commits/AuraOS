import json,hashlib
B=['preprobe_cut_admission','probe_side_effect_topology','postprobe_independence','coupling_join','independence_certificate','changed_cone_reproof','read_only_observation','shared_resource_probe','k27_topology_route','memory_city_dynamic_dependency']
C=['false_independence','false_join','global_reproof','stale_cut','probe_currentness','hidden_coupling','evidence_budget_exhaustion','authority_leak','topology_alias','recovery_scope']
M=['postprobe_closure','complete_cut_certificate','trusted_partition_witness','conservative_join','changed_component_cone','read_only_fast_path','probe_coupling_delta','stale_probe_hold','coordinate_nonauthority_gate','exact_at_effect_topology_recheck']
xs=[]
for bi,b in enumerate(B):
 for ci,c in enumerate(C):
  for mi,m in enumerate(M):xs.append({'candidate_id':f'O9-{bi:02d}{ci:02d}{mi:02d}','boundary':b,'consequence':c,'mechanism':m,'expected_gain':'UNSCORED_AT_FREEZE','claim_ceiling':'CANDIDATE_ONLY'})
raw=json.dumps(xs,sort_keys=True,separators=(',',':')).encode();root=hashlib.sha256(raw).hexdigest();q={}
for x in xs:q.setdefault((x['boundary'],x['consequence']),[]).append(x['candidate_id'])
print(json.dumps({'schema':'aura.astra.hs1000.v6.freeze.v1','raw_count':len(xs),'freeze_root':root,'quotient_count':len(q),'candidates':xs,'quotients':[{'boundary':k[0],'consequence':k[1],'members':v} for k,v in sorted(q.items())]},sort_keys=True,separators=(',',':')))
