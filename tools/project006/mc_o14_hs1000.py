import hashlib,json
B=('producer_identity','consumer_admission','verifier_authorization','proof_semantics','operation_lineage','journal_binding','at_use_currentness','post_effect_monotonicity','k27_context','authority_ceiling')
F=('schema_substitution','receipt_forgery','same_lineage_auth','generation_move','intent_move','contract_move','expiry','durable_sidecar_gap','context_compensation','authority_smuggling')
M=('exact_owner_root','independent_observer','hmac_reference_auth','generation_rebind','operation_root','sidecar_guard','at_use_revalidation','post_result_no_reauth','structural_context_exclusion','d0_only')
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def build():
    raw=[];n=0
    for b in B:
      for f in F:
       for m in M:
        n+=1;raw.append({'id':f'MC-O14-HS-{n:04d}','boundary':b,'failure':f,'mechanism':m,'status':'UNSCORED_AT_FREEZE','semantic_class':'CANDIDATE_NOT_BREAKTHROUGH'})
    freeze=h(raw);groups={}
    for x in raw:groups.setdefault((x['boundary'],x['failure']),[]).append(x['id'])
    q=[{'boundary':k[0],'failure':k[1],'members':tuple(v),'root':h(v)} for k,v in sorted(groups.items())]
    top=sorted(q,key=lambda x:h({'freeze':freeze,'q':x['root']}))[:27]
    return {'raw':len(raw),'freeze_root':freeze,'quotients':len(q),'quotient_root':h(q),'top27_count':len(top),'top27_root':h(top),'candidate_semantics':'frozen advancement candidates, not promoted breakthroughs'}
if __name__=='__main__':print(json.dumps(build(),sort_keys=True,separators=(',',':')))
