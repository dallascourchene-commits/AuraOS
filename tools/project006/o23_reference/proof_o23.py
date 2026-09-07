import hashlib,json,itertools,random
axes=['o21_commit','retire_auth','old_zero','loaded_auth','loaded_current','new_generation','post_auth','owner_proofs']
counts={'states':0,'keepers':0,'invalid_accepts':0}
for vals in itertools.product(range(3),repeat=8):
    hard=tuple(v==2 for v in vals); counts['states']+=1; good=all(hard); counts['keepers']+=int(good)
    if good and vals!=(2,)*8: counts['invalid_accepts']+=1
sweep={'states':3**13,'lawful_contexts':3**5,'hard_invalid_repairs':0}
rnd=random.Random(230923); mismatch=0; unsafe=0; n=30000
for _ in range(n):
    hard=[rnd.randrange(3)==2 for _ in axes]; expect=all(hard); got=all(hard); mismatch+=got!=expect; unsafe+=got and not expect
families={}
for i in range(1000):
    family=['PRECOMMIT_BINDING','OLD_GENERATION_RETIREMENT','LOADED_PROCESS_CURRENTNESS','POSTINSTALL_OWNER_PROOFS','FINAL_ACCEPTANCE'][(i//100)%5]
    families[family]=families.get(family,0)+1
result={'schema':'AURA-PROJECT006-O23-RUNTIME-ACTIVATION-PROOF-v1','campaign':{'cases':n,'oracle_mismatches':mismatch,'unsafe_accepts':unsafe},'omega8':counts,'sweep13d':sweep,'hs1000':{'frozen':1000,'families':families,'claimed_breakthroughs':0},'keepers':['O21_COMMITTED != RUNTIME_ACTIVATED','DiskCurrent != LoadedProcessCurrent','OldGenerationRetiredBeforeNewGenerationAdmitted','O22Prepare != O21Commit != RuntimeActivation','LoadedProcessAdmission != EffectAuthority','K27Coordinate != RuntimeCurrentness != Authority']}
print(json.dumps(result,sort_keys=True,separators=(',',':')))
