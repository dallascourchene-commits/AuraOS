#!/usr/bin/env python3
from creator_studio_gemini_delta_reference import *

tests=[]
def check(name, cond, detail=None): tests.append({"name":name,"pass":bool(cond),"detail":detail})

long_script="x"*5000
check("INLINE_LONG_SCRIPT_SAFE", resolve_script(script_text=long_script)==long_script)
try:
    resolve_script(script_text="x",script_file="/tmp/nope"); check("EXACTLY_ONE_SCRIPT_SOURCE",False)
except ValueError: check("EXACTLY_ONE_SCRIPT_SOURCE",True)

escaped=ass_escape(r"a{b}\c"+"\n"+"d")
check("ASS_ESCAPE_BRACES",r"\{" in escaped and r"\}" in escaped)
check("ASS_ESCAPE_BACKSLASH",r"\\" in escaped)
check("ASS_ESCAPE_NEWLINE",r"\N" in escaped)

plan=build_audio_plan(video_path="v",voice_path="vo",sfx_path="s",bgm_path="b",duration_s=2.0)
indices={x["role"]:x["index"] for x in plan["inputs"]}
check("INPUT_INDEX_VIDEO",indices["video"]==0,indices); check("INPUT_INDEX_VOICE",indices["voice"]==1,indices)
check("INPUT_INDEX_SFX",indices["sfx"]==2,indices); check("INPUT_INDEX_BGM",indices["bgm"]==3,indices)
check("AUDIO_LONGEST_NOT_FIRST","duration=longest" in plan["filter_complex"])
check("AUDIO_TRIM_BOUND","atrim=0:2.000000" in plan["filter_complex"])
try:
    build_audio_plan(video_path="v",voice_path="vo",duration_s=2,preserve_source_audio=True,source_has_audio=False); check("MISSING_SOURCE_AUDIO_FAIL_CLOSED",False)
except ValueError: check("MISSING_SOURCE_AUDIO_FAIL_CLOSED",True)

r=research_source_record(url="x",http_status=200,body_sha256="a")
check("HTTP_200_IS_NOT_VERIFIED",r["state"]=="FETCHED",r)
r2=research_source_record(url="x",http_status=200,parsed_claims=["c"],source_identity_bound=True)
check("PARSED_SOURCE_BOUND_NOT_AUTO_VERIFIED",r2["state"]=="SOURCE_BOUND",r2)
r3=research_source_record(url="x",http_status=200,parsed_claims=["c"],source_identity_bound=True,independently_verified=True)
check("VERIFICATION_REQUIRES_EXPLICIT_EVIDENCE",r3["state"]=="VERIFIED",r3)
try:
    research_source_record(url="x",http_status=200,independently_verified=True); check("VERIFY_WITHOUT_SOURCE_REJECTED",False)
except ValueError: check("VERIFY_WITHOUT_SOURCE_REJECTED",True)

cleared=RightsState("a","CLEARED",True,"CLEARED","NOT_APPLICABLE"); unknown=RightsState("b","UNKNOWN",True,"UNKNOWN","NOT_APPLICABLE")
check("CLEARED_ASSET_ADMITTED",admit_public_asset(cleared)); check("UNKNOWN_ASSET_BLOCKED",not admit_public_asset(unknown))
recipe=commons_recipe(template_id="T",recipe_author="A",recipe_license="CC-BY-4.0",source_rights=[unknown])
check("RECIPE_LICENSE_SEPARATE_FROM_SOURCE_RIGHTS",recipe["recipe_license"]=="CC-BY-4.0" and recipe["source_media_rights"][0]["reuse_status"]=="UNKNOWN")
check("NO_DEFAULT_ECONOMIC_ENTITLEMENT",recipe["economic_entitlements"].startswith("UNSPECIFIED"))

auth=EffectAuthorization("h",("youtube",),("channel-1",),"rh",None,1100,"nonce-1","APPROVE_PUBLICATION")
check("BOUND_AUTH_ALLOWS_EXACT_EFFECT",authorization_allows_publish(auth,artifact_sha256="h",destination="youtube",account_id="channel-1",rights_manifest_sha256="rh",now_epoch=1000))
check("WRONG_ARTIFACT_BLOCKED",not authorization_allows_publish(auth,artifact_sha256="x",destination="youtube",account_id="channel-1",rights_manifest_sha256="rh",now_epoch=1000))
check("WRONG_ACCOUNT_BLOCKED",not authorization_allows_publish(auth,artifact_sha256="h",destination="youtube",account_id="channel-2",rights_manifest_sha256="rh",now_epoch=1000))
check("WRONG_RIGHTS_MANIFEST_BLOCKED",not authorization_allows_publish(auth,artifact_sha256="h",destination="youtube",account_id="channel-1",rights_manifest_sha256="x",now_epoch=1000))
check("EXPIRED_AUTH_BLOCKED",not authorization_allows_publish(auth,artifact_sha256="h",destination="youtube",account_id="channel-1",rights_manifest_sha256="rh",now_epoch=1200))

metrics={"hook_s":2.4,"cut_times":[0,2.4,3.0]}
t1=deterministic_template_id(source_ref="u",source_digest="d",extractor_version="1",editorial_metrics=metrics)
t2=deterministic_template_id(source_ref="u",source_digest="d",extractor_version="1",editorial_metrics=metrics)
check("TEMPLATE_ID_IDEMPOTENT",t1==t2,t1)
check("SOURCE_CHANGE_INVALIDATES_TEMPLATE_ID",t1!=deterministic_template_id(source_ref="u",source_digest="d2",extractor_version="1",editorial_metrics=metrics))
a=canonical_batch_summary([{"recipe_id":"b","status":"OK"},{"recipe_id":"a","status":"OK"}]); b=canonical_batch_summary([{"recipe_id":"a","status":"OK"},{"recipe_id":"b","status":"OK"}])
check("BATCH_DIGEST_COMPLETION_ORDER_INVARIANT",a["digest"]==b["digest"])

cand=trend_candidate(source_ref="u",source_digest="d",cut_times=[0,1,2.5],measured_bpm=None,extractor_version="1",rights=unknown)
check("TREND_CANDIDATE_NOT_AUTO_PUBLIC",cand["public_commons_admitted"] is False)
check("TREND_BPM_UNKNOWN_NOT_HARDCODED",cand["metrics"]["measured_bpm"] is None)
check("TREND_RIGHTS_PRESERVED",cand["rights"]["reuse_status"]=="UNKNOWN")
check("VERIFIED_BADGE_TYPED",claim_badge("VERIFIED")=="SOURCE VERIFIED")
check("SCENARIO_BADGE_TYPED",claim_badge("SCENARIO")=="SCENARIO")
check("UNKNOWN_BADGE_FAILS_CLOSED",claim_badge("garbage")=="UNVERIFIED")
check("CANONICAL_DIGEST_KEY_ORDER",digest({"a":1,"b":2})==digest({"b":2,"a":1}))

passed=sum(x["pass"] for x in tests)
print(__import__("json").dumps({"status":"PASS" if passed==len(tests) else "FAIL","passed":passed,"total":len(tests),"tests":tests},indent=2))
raise SystemExit(0 if passed==len(tests) else 1)
