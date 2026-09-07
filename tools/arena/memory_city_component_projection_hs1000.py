import hashlib,json
B=('changed_hard_component','influence_component_lift','reproof_projection_identity','coverage_envelope','active_world_projection','read_consequence_root','transition_horizon','read_trust','k27_locator','authority_cut')
F=('item_only_underreproof','support_peer_omission','destination_peer_omission','stale_projection_reuse','same_world_semantics_aba','full_identity_overconstraint','horizon_projection_move','trust_crosscast','k27_crosscast','effect_crosscast')
M=('component_seed','directed_component_dag','independent_fixedpoint_oracle','projection_receipt_bind','use_time_projection_rebind','consequence_root_recompute','counterexample_receipt','h0_exact_rebind','noncompensatory_hold','separate_locator_identity')
def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build():
 raw=[];n=0
 for b in B:
  for f in F:
   for m in M:
    n+=1;raw.append({'id':f'MC-O12-HS-{n:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantic_class':'CANDIDATE_NOT_BREAKTHROUGH'})
 freeze=h(raw); groups={}
 for x in raw: groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
 q=[{'boundary':k[0],'failure':k[1],'members':tuple(v),'root':h(v)} for k,v in sorted(groups.items())]
 top=sorted(q,key=lambda x:h({'freeze':freeze,'q':x['root']}))[:27]
 return {'raw':len(raw),'freeze_root':freeze,'quotients':len(q),'quotient_root':h(q),'top27_count':len(top),'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__': print(json.dumps(build(),sort_keys=True,separators=(',',':')))
