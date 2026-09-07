import json,hashlib
B=['evidence_query_selection','private_premise_gate','positive_exact_at_use_refresh','cross_clock_query_duration','deadline_feasibility','weighted_tree_optimality','negative_evidence_reuse','clock_relation_currentness','k27_evidence_routing','memory_city_probe_schedule']
C=['false_ready','false_hold','private_disclosure','stale_positive_evidence','deadline_miss','excess_query_cost','unnecessary_reproof','clock_aliasing','authority_leak','route_fragmentation']
M=['interval_duration_hull','robust_path_deadline','weighted_query_tree','premise_before_private','positive_refresh_terminal','negative_early_terminal','stale_clock_hold','permutation_canonicalization','coordinate_nonauthority_gate','uncertainty_triggered_reproof']
xs=[]
for bi,b in enumerate(B):
 for ci,c in enumerate(C):
  for mi,m in enumerate(M):xs.append({'candidate_id':f'O8-{bi:02d}{ci:02d}{mi:02d}','boundary':b,'consequence':c,'mechanism':m,'expected_gain':'UNSCORED_AT_FREEZE','claim_ceiling':'CANDIDATE_ONLY'})
raw=json.dumps(xs,sort_keys=True,separators=(',',':')).encode();root=hashlib.sha256(raw).hexdigest();q={}
for x in xs:q.setdefault((x['boundary'],x['consequence']),[]).append(x['candidate_id'])
print(json.dumps({'schema':'aura.astra.hs1000.v6.freeze.v1','raw_count':len(xs),'freeze_root':root,'quotient_count':len(q),'candidates':xs,'quotients':[{'boundary':k[0],'consequence':k[1],'members':v} for k,v in sorted(q.items())]},sort_keys=True,separators=(',',':')))
