import hashlib,json
B=('read_cert_auth','binding_identity','reproof_semantics','coverage_admission','effect_refinement','mutation_identity','lease_holder_time','owner_verifier','context_noncompensation','authority_ceiling')
F=('schema_substitution','missing_authority','authority_smuggling','consequence_substitution','legacy_binding','detached_effect','obligation_move','holder_zombie','negative_time','context_repair')
M=('exact_schema','explicit_false','cert_recompute','owner_binding_recompute','effect_subclass','escalation_root','holder_rebind','nonnegative_time','tecc_only','executable_lattice')
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build():
    raw=[]; n=0
    for b in B:
        for f in F:
            for m in M:
                n+=1; raw.append({'id':f'MC-O13-HS-{n:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantic_class':'CANDIDATE_NOT_BREAKTHROUGH'})
    freeze=h(raw); groups={}
    for x in raw: groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
    q=[{'boundary':k[0],'failure':k[1],'members':tuple(v),'root':h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({'freeze':freeze,'q':x['root']}))[:27]
    return {'raw':len(raw),'freeze_root':freeze,'quotients':len(q),'quotient_root':h(q),'top27_count':len(top),'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__': print(json.dumps(build(),sort_keys=True,separators=(',',':')))
