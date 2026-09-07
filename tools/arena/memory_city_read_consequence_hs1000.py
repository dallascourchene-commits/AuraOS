import hashlib,json
B=("coverage_envelope","positive_world_membership","hydration_cut","reproof_cut","read_trust_obligation","world_currentness","use_time_membership","coverage_currentness","k27_locality","authority_cut")
F=("generation_only_alias","full_identity_overconstraint","hydration_divergence","reproof_divergence","trust_divergence","stale_member","missing_projection","unknown_member","k27_crosscast","mutation_crosscast")
M=("explicit_world_envelope","positive_only_projection","behavioral_quotient","trust_exact_split","coverage_receipt_bind","use_time_revalidation","counterexample_receipt","h0_exact_rebind","noncompensatory_hold","separate_locator_identity")
def h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def build():
 raw=[];n=0
 for b in B:
  for f in F:
   for m in M:
    n+=1;raw.append({'id':f'MC-O11-HS-{n:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantic_class':'CANDIDATE_NOT_BREAKTHROUGH'})
 freeze=h(raw);groups={}
 for x in raw:groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
 q=[{'boundary':k[0],'failure':k[1],'members':tuple(v),'root':h(v)} for k,v in sorted(groups.items())]
 top=sorted(q,key=lambda x:h({'freeze':freeze,'q':x['root']}))[:27]
 return {'raw':len(raw),'freeze_root':freeze,'quotients':len(q),'quotient_root':h(q),'top27_count':len(top),'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__': print(json.dumps(build(),sort_keys=True,separators=(",",":")))
