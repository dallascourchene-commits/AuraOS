use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, SourceLocatorV1};
use aura_k27_astge_portable_target_raw_slice::admit_portable_target_raw_slice;
use aura_k27_astge_portable_target_raw_slice_projection::{
    project_portable_target_raw_slice, verify_portable_target_raw_slice_projection,
};
use aura_k27_astge_post_edit_canonical_projection::{
    canonical_payload_bytes, CanonicalDefinitionTargetPayloadV1,
    CanonicalDefinitionTargetProjectionV1, CANONICALIZATION_PROFILE_V1, PROJECTION_SCHEMA_V1,
};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::PathBuf;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 6 {
        return Err("usage: probe <root> <file_id> <relative_path> <generation> <opaque_handle_sha256>".into());
    }
    let root = PathBuf::from(&args[1]);
    let file_id: u32 = args[2].parse()?;
    let relative_path = args[3].clone();
    let generation: u64 = args[4].parse()?;
    let handle = args[5].clone();
    if handle.len() != 64 || !handle.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("opaque handle must be 64 hex characters".into());
    }

    let source = fs::read(root.join(&relative_path))?;
    if source.is_empty() {
        return Err("causal POST source is empty".into());
    }
    let target_end = usize::min(6, source.len()) as u32;
    let payload = CanonicalDefinitionTargetPayloadV1 {
        schema: PROJECTION_SCHEMA_V1.to_owned(),
        version: 1,
        canonicalization_profile: CANONICALIZATION_PROFILE_V1.to_owned(),
        source_generation_domain: "SOURCE".to_owned(),
        source_generation_value: generation,
        source_owner_ref: "PR556:LIVE-CAUSAL-POST".to_owned(),
        relative_path: relative_path.clone(),
        file_id: u64::from(file_id),
        source_sha256_hex: hex(&Sha256::digest(&source)),
        source_byte_len: source.len() as u64,
        selected_target_scope_local_id: 1,
        selected_target_parent_scope_local_id: 0,
        selected_target_syntax_ordinal: 1,
        selected_target_byte_start: 0,
        selected_target_byte_end: target_end,
        selected_target_semantic_handle_digest_hex: handle,
        definition_name: "o38_live_causal_post_slice".to_owned(),
        definition_owner_scope_local_id: 0,
        definition_target_scope_local_id: 1,
        selected_current_scope_is_binding_target: true,
        binding_owner_is_selected_parent: true,
        local_scope_id_is_semantic_identity: false,
        post_edit_profiled_scope_current: true,
        canonical_definition_target_current: true,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        producer_authenticated: false,
        review_authorized: false,
        mutation_authorized: false,
        execution_authorized: false,
        commit_authorized: false,
        merge_authorized: false,
        promotion_authorized: false,
        provider_effect_authorized: false,
        public_effect_authorized: false,
        human_authority: false,
    };
    let payload_sha256 = hex(&Sha256::digest(canonical_payload_bytes(&payload)?));
    let projection = CanonicalDefinitionTargetProjectionV1 { payload, payload_sha256 };

    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(file_id, &relative_path, generation, &source)],
    )?;
    let raw_slice = admit_portable_target_raw_slice(&catalog, &projection)?;
    let portable = project_portable_target_raw_slice(&raw_slice)?;
    verify_portable_target_raw_slice_projection(&portable)?;
    println!("{}", serde_json::to_string(&portable)?);
    Ok(())
}
