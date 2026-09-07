import json,hashlib
BOUNDARIES=['cross_clock_mapping','calibration_currentness','deadline_admission','window_admission','route_composition','evidence_query_time','audio_render_control','worker_main_bridge','network_clock_translation','memory_city_route_time']
CONSEQUENCES=['false_ready','false_hold','excess_reproof','unnecessary_sync','stale_calibration','currentness_drift','deadline_miss','phase_violation','privacy_disclosure','authority_leak']
MECHANISMS=['interval_hull','affine_skew_envelope','calibration_lease','deadline_margin_proof','window_containment','uncertainty_triggered_reproof','relation_path_compiler','permutation_audit','coordinate_nonauthority_gate','exact_at_use_refresh']
C=[]
for bi,b in enumerate(BOUNDARIES):
  for ci,c in enumerate(CONSEQUENCES):
    for mi,m in enumerate(MECHANISMS):
      C.append({'candidate_id':f'O7-{bi:02d}{ci:02d}{mi:02d}','boundary':b,'consequence':c,'mechanism':m,'expected_gain':'UNSCORED_AT_FREEZE','claim_ceiling':'CANDIDATE_ONLY'})
raw=json.dumps(C,sort_keys=True,separators=(',',':')).encode(); root=hashlib.sha256(raw).hexdigest(); Q={}
for x in C: Q.setdefault((x['boundary'],x['consequence']),[]).append(x['candidate_id'])
out={'schema':'aura.astra.hs1000.v6.freeze.v1','raw_count':len(C),'freeze_root':root,'quotient_count':len(Q),'candidates':C,'quotients':[{'boundary':k[0],'consequence':k[1],'members':v} for k,v in sorted(Q.items())]}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
