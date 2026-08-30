import unittest

from tools.aura_adopt.owner_resolved_persistent_kv_reuse import (
    KVAdmissionError,
    KVReuseProjectionClaimV1,
    OwnerResolverProofV1,
    PersistentKVPathEvidenceV1,
    PersistentKVReuseTargetV1,
    ResolverDisposition,
    ResponsibilityClass,
    admit_persistent_kv_reuse,
    build_resolver_proof,
    resolved_projection_payload_digest,
)

A="a"*64; B="b"*64; C="c"*64; D="d"*64; E="e"*64; F="f"*64
KEY=b"local-test-only-resolver-key"
TRUST_KEYS={"resolver:kv-owner": KEY}
TRUST_STATE={"resolver:kv-owner": ("rg:2","rc:2")}

def target(**kw):
    data=dict(
        coordinate_ref="coord:kv:42", k27_cell=12, model_revision="model:r1",
        tokenizer_digest=A, chat_template_digest=B, system_tool_prefix_digest=C,
        prefix_token_digest=D, cache_abi="kvabi:v3", backend_cache_abi="backend:v7",
        principal_namespace_digest=E, workload_digest=F,
        host_epoch="host:e7", route_epoch="route:e9", source_generation="src:g4",
        source_currentness_ref="src:cur4",
        responsibility=ResponsibilityClass.TRANSFORMER_KV_CACHE,
    )
    data.update(kw)
    return PersistentKVReuseTargetV1(**data)

def path(t=None, **kw):
    t=t or target()
    data=dict(
        evidence_ref="measure:kv:path", evidence_generation=t.source_generation,
        evidence_currentness_ref=t.source_currentness_ref,
        target_digest=t.target_digest,
        responsibility=ResponsibilityClass.TRANSFORMER_KV_CACHE,
        model_revision=t.model_revision, tokenizer_digest=t.tokenizer_digest,
        chat_template_digest=t.chat_template_digest,
        system_tool_prefix_digest=t.system_tool_prefix_digest,
        prefix_token_digest=t.prefix_token_digest, cache_abi=t.cache_abi,
        backend_cache_abi=t.backend_cache_abi,
        principal_namespace_digest=t.principal_namespace_digest,
        workload_digest=t.workload_digest, host_epoch=t.host_epoch,
        route_epoch=t.route_epoch, persistent_restore_observed=True,
        cache_read_observed=True, cache_hit_tokens=4096, prefill_saved_us=10000,
        transfer_us=1000, restore_us=1000, queue_penalty_us=500,
        memory_penalty_us=250, security_isolation_us=250, invalidation_penalty_us=250,
    )
    data.update(kw)
    return PersistentKVPathEvidenceV1(**data)

def claim(t=None,e=None, **kw):
    t=t or target()
    e=e or path(t)
    data=dict(
        owner_ref="owner:kv-evidence", owner_generation="owner:g3", owner_head=A,
        owner_blob=B, owner_abi="PersistentKVReuseOwnerV1", subject_ref=t.coordinate_ref,
        subject_generation=t.source_generation, source_ref="source:runtime-evidence",
        source_generation=t.source_generation, source_currentness_ref=t.source_currentness_ref,
        projection_schema="PersistentKVReuseProjectionV1",
        projection_payload_digest=resolved_projection_payload_digest(t,e),
    )
    data.update(kw)
    return KVReuseProjectionClaimV1(**data)

def proof(c, **kw):
    data=dict(
        claim=c, resolver_ref="resolver:kv-owner", resolver_generation="rg:2",
        resolver_currentness_ref="rc:2",
        owner_recognized_projection_digest=c.projection_payload_digest,
        disposition=ResolverDisposition.OWNER_RESOLVED_CURRENT, key=KEY,
    )
    data.update(kw)
    return build_resolver_proof(**data)

def fixtures(**path_kw):
    t=target()
    e=path(t, **path_kw)
    c=claim(t,e)
    p=proof(c)
    ps={c.claim_digest: (p.proof_digest,)}
    return t,c,p,e,ps

def admit_raw(t,c,p,e,proof_state=None,keys=None,state=None):
    if proof_state is None:
        proof_state={c.claim_digest: (p.proof_digest,)}
    return admit_persistent_kv_reuse(
        target=t, claim=c, resolver_proof=p, path_evidence=e,
        trusted_resolver_keys=TRUST_KEYS if keys is None else keys,
        trusted_resolver_state=TRUST_STATE if state is None else state,
        trusted_resolver_proof_state=proof_state,
    )

def admit(**path_kw):
    t,c,p,e,ps=fixtures(**path_kw)
    return admit_raw(t,c,p,e,proof_state=ps)

class PCK2Tests(unittest.TestCase):
    def test_positive_control(self):
        out=admit()
        self.assertEqual("TRANSFORMER_KV_REUSE_ADMISSIBLE",out["disposition"])
        self.assertTrue(out["transformer_kv_reuse_admissible"])
        self.assertEqual(6750,out["net_reuse_us"])

    def test_k27_is_not_authority(self):
        self.assertFalse(admit()["coordinate_nomination_is_authority"])

    def test_deterministic_admission_digest(self):
        self.assertEqual(admit()["admission_digest"],admit()["admission_digest"])

    def test_all_effect_authority_false(self):
        out=admit()
        for field in (
            "monetary_credit_authorized","provider_authorized",
            "execution_authorized","performance_superiority_claimed",
        ):
            self.assertFalse(out[field])

    def test_trust_roots_not_proven_by_module(self):
        out=admit()
        self.assertFalse(out["resolver_trust_root_proven_by_this_module"])
        self.assertFalse(out["proof_registry_authority_proven_by_this_module"])
        self.assertFalse(out["runtime_observation_authenticity_proven_by_this_module"])
        self.assertFalse(out["live_kv_access_performed"])

    def test_untrusted_resolver(self):
        t,c,p,e,ps=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_UNTRUSTED"):
            admit_raw(t,c,p,e,proof_state=ps,keys={},state={})

    def test_bad_signature(self):
        t,c,p,e,ps=fixtures()
        bad=OwnerResolverProofV1(**{**p.__dict__,"resolver_signature":"0"*64})
        bad_ps={c.claim_digest:(bad.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_SIGNATURE_INVALID"):
            admit_raw(t,c,bad,e,proof_state=bad_ps)

    def test_stale_resolver_generation(self):
        t,c,p,e,ps=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_GENERATION_STALE"):
            admit_raw(t,c,p,e,proof_state=ps,state={"resolver:kv-owner":("rg:99","rc:2")})

    def test_stale_resolver_currentness(self):
        t,c,p,e,ps=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_CURRENTNESS_STALE"):
            admit_raw(t,c,p,e,proof_state=ps,state={"resolver:kv-owner":("rg:2","rc:99")})

    def test_malformed_resolver_state_record(self):
        t,c,p,e,ps=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_STATE_RECORD_INVALID"):
            admit_raw(t,c,p,e,proof_state=ps,state={"resolver:kv-owner":"rg:2"})

    def test_revoked_proof(self):
        t=target(); e=path(t); c=claim(t,e); p=proof(c,revoked=True)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_PROOF_REVOKED"):
            admit_raw(t,c,p,e,proof_state=ps)

    def test_historical_proof(self):
        t=target(); e=path(t); c=claim(t,e)
        p=proof(c,disposition=ResolverDisposition.OWNER_RESOLVED_HISTORICAL)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_NOT_CURRENT"):
            admit_raw(t,c,p,e,proof_state=ps)

    def test_missing_external_proof_registration(self):
        t,c,p,e,_=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_PROOF_NOT_REGISTERED"):
            admit_raw(t,c,p,e,proof_state={})

    def test_old_proof_rejected_after_external_supersession(self):
        t=target(); e=path(t); c=claim(t,e); old=proof(c)
        newer=proof(c,supersedes_proof_digest=old.proof_digest)
        ps={c.claim_digest:(newer.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_PROOF_SUPERSEDED_OR_REVOKED"):
            admit_raw(t,c,old,e,proof_state=ps)

    def test_superseding_proof_passes_when_current_registry_selects_it(self):
        t=target(); e=path(t); c=claim(t,e); old=proof(c)
        newer=proof(c,supersedes_proof_digest=old.proof_digest)
        ps={c.claim_digest:(newer.proof_digest,)}
        out=admit_raw(t,c,newer,e,proof_state=ps)
        self.assertTrue(out["resolver_proof_current_in_external_registry"])
        self.assertTrue(out["transformer_kv_reuse_admissible"])

    def test_malformed_external_proof_registry(self):
        t,c,p,e,_=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_PROOF_STATE_INVALID"):
            admit_raw(t,c,p,e,proof_state={c.claim_digest:p.proof_digest})

    def test_duplicate_external_proof_registry_entries_rejected(self):
        t,c,p,e,_=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_PROOF_STATE_DUPLICATE"):
            admit_raw(t,c,p,e,proof_state={c.claim_digest:(p.proof_digest,p.proof_digest)})

    def test_wrong_claim_digest(self):
        t,c,p,e,ps=fixtures()
        c2=claim(t,e,owner_generation="owner:g4")
        p2=proof(c2)
        ps2={c.claim_digest:(p2.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_CLAIM_DIGEST_MISMATCH"):
            admit_raw(t,c,p2,e,proof_state=ps2)

    def test_wrong_recognized_projection(self):
        t=target(); e=path(t); c=claim(t,e)
        p=proof(c,owner_recognized_projection_digest=F)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_RECOGNIZED_PROJECTION_MISMATCH"):
            admit_raw(t,c,p,e,proof_state=ps)

    def test_projection_payload_binds_path_evidence(self):
        t,c,p,e,ps=fixtures()
        changed=path(t,cache_hit_tokens=e.cache_hit_tokens+1)
        with self.assertRaisesRegex(KVAdmissionError,"PROJECTION_PAYLOAD_DIGEST_MISMATCH"):
            admit_raw(t,c,p,changed,proof_state=ps)

    def test_projection_coordinate_subject_mismatch(self):
        t=target(); e=path(t); c=claim(t,e,subject_ref="coord:other"); p=proof(c)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"PROJECTION_COORDINATE_SUBJECT_MISMATCH"):
            admit_raw(t,c,p,e,proof_state=ps)

    def test_projection_source_generation_mismatch(self):
        t=target(); e=path(t); c=claim(t,e,source_generation="src:old"); p=proof(c)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"PROJECTION_SOURCE_GENERATION_MISMATCH"):
            admit_raw(t,c,p,e,proof_state=ps)

    def test_model_mismatch_blocks_even_when_owner_resolved(self):
        self.assertIn("PATH_MODEL_REVISION_MISMATCH",admit(model_revision="model:other")["blockers"])

    def test_tokenizer_mismatch_blocks(self):
        self.assertIn("PATH_TOKENIZER_DIGEST_MISMATCH",admit(tokenizer_digest=F)["blockers"])

    def test_chat_template_mismatch_blocks(self):
        self.assertIn("PATH_CHAT_TEMPLATE_DIGEST_MISMATCH",admit(chat_template_digest=F)["blockers"])

    def test_system_tool_prefix_mismatch_blocks(self):
        self.assertIn("PATH_SYSTEM_TOOL_PREFIX_DIGEST_MISMATCH",admit(system_tool_prefix_digest=F)["blockers"])

    def test_prefix_token_mismatch_blocks(self):
        self.assertIn("PATH_PREFIX_TOKEN_DIGEST_MISMATCH",admit(prefix_token_digest=F)["blockers"])

    def test_cache_abi_mismatch_blocks(self):
        self.assertIn("PATH_CACHE_ABI_MISMATCH",admit(cache_abi="kvabi:v4")["blockers"])

    def test_backend_cache_abi_mismatch_blocks(self):
        self.assertIn("PATH_BACKEND_CACHE_ABI_MISMATCH",admit(backend_cache_abi="backend:v8")["blockers"])

    def test_cross_principal_blocks(self):
        self.assertIn("PATH_PRINCIPAL_NAMESPACE_DIGEST_MISMATCH",admit(principal_namespace_digest=F)["blockers"])

    def test_workload_target_seam_mismatch_blocks(self):
        self.assertIn("PATH_WORKLOAD_DIGEST_MISMATCH",admit(workload_digest=A)["blockers"])

    def test_host_epoch_mismatch_blocks(self):
        self.assertIn("PATH_HOST_EPOCH_MISMATCH",admit(host_epoch="host:new")["blockers"])

    def test_route_epoch_mismatch_blocks(self):
        self.assertIn("PATH_ROUTE_EPOCH_MISMATCH",admit(route_epoch="route:new")["blockers"])

    def test_path_generation_mismatch_blocks(self):
        self.assertIn("PATH_SOURCE_GENERATION_MISMATCH",admit(evidence_generation="src:old")["blockers"])

    def test_path_currentness_mismatch_blocks(self):
        self.assertIn("PATH_CURRENTNESS_MISMATCH",admit(evidence_currentness_ref="src:old")["blockers"])

    def test_restore_must_be_observed(self):
        self.assertIn("PERSISTENT_RESTORE_NOT_OBSERVED",admit(persistent_restore_observed=False)["blockers"])

    def test_read_must_be_observed(self):
        self.assertIn("CACHE_READ_NOT_OBSERVED",admit(cache_read_observed=False)["blockers"])

    def test_hit_tokens_positive(self):
        self.assertIn("CACHE_HIT_TOKENS_NOT_POSITIVE",admit(cache_hit_tokens=0)["blockers"])

    def test_zero_net_benefit_not_admissible(self):
        out=admit(
            prefill_saved_us=3250, transfer_us=1000, restore_us=1000,
            queue_penalty_us=500, memory_penalty_us=250,
            security_isolation_us=250, invalidation_penalty_us=250,
        )
        self.assertEqual("KV_REUSE_OBSERVED_NO_POSITIVE_NET_BENEFIT",out["disposition"])
        self.assertFalse(out["transformer_kv_reuse_admissible"])

    def test_security_isolation_cost_can_make_net_reuse_negative(self):
        out=admit(security_isolation_us=9000)
        self.assertLess(out["net_reuse_us"],0)
        self.assertFalse(out["transformer_kv_reuse_admissible"])

    def test_negative_net_benefit_not_admissible(self):
        out=admit(prefill_saved_us=1000,transfer_us=2000)
        self.assertLess(out["net_reuse_us"],0)
        self.assertFalse(out["transformer_kv_reuse_admissible"])

    def test_coordinate_memory_path_cannot_cross_credit(self):
        out=admit(responsibility=ResponsibilityClass.COORDINATE_MEMORY)
        self.assertIn("PATH_NOT_TRANSFORMER_KV_CACHE",out["blockers"])
        self.assertFalse(out["coordinate_memory_equated_to_transformer_kv"])

    def test_semantic_cache_path_cannot_cross_credit(self):
        out=admit(responsibility=ResponsibilityClass.SEMANTIC_RESPONSE_CACHE)
        self.assertIn("PATH_NOT_TRANSFORMER_KV_CACHE",out["blockers"])
        self.assertFalse(out["semantic_response_cache_equated_to_transformer_kv"])

    def test_invalid_k27_rejected(self):
        with self.assertRaisesRegex(KVAdmissionError,"K27_CELL_INVALID"):
            target(k27_cell=27)

    def test_target_digest_is_part_of_path(self):
        t=target(); e=path(t,target_digest=F); c=claim(t,e); p=proof(c)
        ps={c.claim_digest:(p.proof_digest,)}
        out=admit_raw(t,c,p,e,proof_state=ps)
        self.assertIn("PATH_TARGET_DIGEST_MISMATCH",out["blockers"])

    def test_projection_digest_requires_typed_target_and_path(self):
        with self.assertRaisesRegex(KVAdmissionError,"KV_TARGET_AND_PATH_REQUIRED"):
            resolved_projection_payload_digest({}, {})

    def test_build_resolver_rejects_untyped_disposition(self):
        t=target(); e=path(t); c=claim(t,e)
        with self.assertRaisesRegex(KVAdmissionError,"RESOLVER_DISPOSITION_INVALID"):
            build_resolver_proof(
                claim=c,resolver_ref="resolver:kv-owner",resolver_generation="rg:2",
                resolver_currentness_ref="rc:2",
                owner_recognized_projection_digest=c.projection_payload_digest,
                disposition="OWNER_RESOLVED_CURRENT",key=KEY,
            )

    def test_admission_rejects_untyped_inputs(self):
        t=target(); e=path(t); c=claim(t,e); p=proof(c)
        ps={c.claim_digest:(p.proof_digest,)}
        with self.assertRaisesRegex(KVAdmissionError,"KV_TARGET_REQUIRED"):
            admit_raw({},c,p,e,proof_state=ps)
        with self.assertRaisesRegex(KVAdmissionError,"OWNER_RESOLVER_PROOF_REQUIRED"):
            admit_raw(t,c,{},e,proof_state=ps)

    def test_admission_requires_external_trust_state_mappings(self):
        t,c,p,e,ps=fixtures()
        with self.assertRaisesRegex(KVAdmissionError,"TRUSTED_RESOLVER_STATE_REQUIRED"):
            admit_persistent_kv_reuse(
                target=t,claim=c,resolver_proof=p,path_evidence=e,
                trusted_resolver_keys=None,trusted_resolver_state=TRUST_STATE,
                trusted_resolver_proof_state=ps,
            )
        with self.assertRaisesRegex(KVAdmissionError,"TRUSTED_RESOLVER_STATE_REQUIRED"):
            admit_persistent_kv_reuse(
                target=t,claim=c,resolver_proof=p,path_evidence=e,
                trusted_resolver_keys=TRUST_KEYS,trusted_resolver_state=TRUST_STATE,
                trusted_resolver_proof_state=None,
            )

if __name__=="__main__":
    unittest.main()
