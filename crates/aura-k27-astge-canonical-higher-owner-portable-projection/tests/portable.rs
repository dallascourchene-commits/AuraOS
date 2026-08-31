use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_canonical_higher_owner_owner_reduction::{
    reprove_canonical_higher_owner_owner_chain, CanonicalHigherOwnerOwnerReducedV1,
};
use aura_k27_astge_canonical_higher_owner_portable_projection::{
    project_reduced_higher_owner_owner_chain, verify_portable_higher_owner_owner_chain_projection,
    CanonicalHigherOwnerPortableProjectionV1, PortableOwnerChainProjectionErrorV1,
    PORTABLE_OWNER_CHAIN_SCHEMA_V1,
};
use aura_k27_astge_generation_domain::SourceGenerationV1;
use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, SourceLocatorV1};
use aura_k27_astge_post_edit_canonical_projection::ProjectionErrorV1;
use aura_k27_astge_post_edit_canonical_target_handle_continuity::{
    admit_post_edit_canonical_definition_target_handle_continuity,
    PostEditCanonicalDefinitionTargetHandleContinuityV1,
};
use aura_k27_astge_post_edit_profiled_scope::CandidateProfiledScopeSelectorV1;
use aura_k27_astge_profiled_scopes::build_profiled_python_scopes;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::{index_python_nested_scopes, PythonLexicalScopeIndexV1};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);
const SOURCE: &str = "def outer():\n    def inner():\n        return 1\n    return inner\n";

struct Setup {
    root: PathBuf,
    file_id: u32,
    scope_index: PythonLexicalScopeIndexV1,
    selected_scope_id: u64,
    record: NodeIndexRecordV1,
    catalog: AdmittedSourceCatalogV1,
    edit_start: usize,
}

fn stable_handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
    parse_python_named_ast(source, file_id)
        .unwrap()
        .nodes
        .into_iter()
        .map(|node| (node.node_id, [0x31; 32]))
        .collect()
}

fn setup(label: &str) -> Setup {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let root = std::env::temp_dir().join(format!(
        "aura-k27-portable-owner-chain-{label}-{}-{n}",
        std::process::id()
    ));
    fs::create_dir_all(root.join("src")).unwrap();
    fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();
    let file_id = 177;
    let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
    let old_handles = stable_handles(SOURCE, file_id);
    let scope_index = index_python_nested_scopes(SOURCE, file_id, &old_handles).unwrap();
    let selected = scope_index
        .scopes
        .iter()
        .find(|scope| scope.name == "inner")
        .unwrap();
    let selected_scope_id = selected.scope_id;
    let selected_ast_node_id = selected.ast_node_id.unwrap();
    let encoded = encode_ast_to_splane(&graph, &old_handles, 0, 41, [0x91; 32]).unwrap();
    let record = encoded
        .records
        .iter()
        .find(|record| record.node_id == selected_ast_node_id)
        .unwrap()
        .clone();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(
            file_id,
            "src/module.py",
            12,
            SOURCE.as_bytes(),
        )],
    )
    .unwrap();
    let edit_start = SOURCE.find("return 1").unwrap() + "return ".len();
    Setup {
        root,
        file_id,
        scope_index,
        selected_scope_id,
        record,
        catalog,
        edit_start,
    }
}

fn sha256_hex(source: &[u8]) -> String {
    Sha256::digest(source)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn hydration(source: &[u8], file_id: u32, generation: u64) -> String {
    let sha = sha256_hex(source);
    json!({
        "version": "AURA_ASTGE_ANCHOR_HYDRATION_V1",
        "anchor_owner_reused": "source-owner://post-edit-profiled",
        "source_body_witness_required": true,
        "unknown_or_stale_hydration_admitted": false,
        "codemap_digest8_currentness_authority": false,
        "source_authority_minted": false,
        "project007_runtime_implemented": false,
        "anchor_receipts": [{
            "anchor_id": "anchor.post-edit",
            "path": "src/module.py",
            "semantic_id": "SEM:POSTEDIT",
            "signature_hash": "sig",
            "anchor_projection_resolved": true,
            "semantic_identity_minted_by_bridge": false,
            "source_authority_minted": false,
            "body_currentness_status": "CURRENT",
            "hydration_admitted": true,
            "reason": "EXACT_SOURCE_BODY_WITNESS_MATCH",
            "witness_ref": "witness://post-edit/body",
            "expected_byte_len": source.len(),
            "observed_byte_len": source.len(),
            "expected_body_sha256": sha,
            "observed_body_sha256": sha,
            "locator": {
                "file_id": file_id,
                "relative_path": "src/module.py",
                "source_generation": generation,
                "byte_len": source.len(),
                "sha256": sha,
            },
        }],
        "source_locators_v1": [],
    })
    .to_string()
}

fn changed_candidate(setup: &Setup) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
    let mut candidate = SOURCE.as_bytes().to_vec();
    candidate.splice(
        setup.edit_start..setup.edit_start + 1,
        b"100".iter().copied(),
    );
    let start = setup.edit_start as u64;
    (
        candidate,
        vec![AuthorizedSpanV1 {
            start,
            end: start + 1,
        }],
        vec![ReplacementV1 {
            start,
            end: start + 1,
            replacement: b"100".to_vec(),
        }],
    )
}

fn selector(
    source: &str,
    file_id: u32,
    handles: &HashMap<u64, [u8; 32]>,
) -> CandidateProfiledScopeSelectorV1 {
    let profiled = build_profiled_python_scopes(
        source,
        file_id,
        "source-owner://post-edit-profiled",
        "candidate-generation",
        handles,
    )
    .unwrap();
    let scope = profiled
        .profiled_scopes
        .iter()
        .find(|scope| scope.name == "inner")
        .unwrap();
    CandidateProfiledScopeSelectorV1 {
        syntax_ordinal: scope.syntax_ordinal.unwrap(),
        file_id: scope.file_id,
        byte_start: scope.byte_start,
        byte_end: scope.byte_end,
        semantic_handle_digest: scope.semantic_handle_digest.unwrap(),
    }
}

fn outer_receipt(setup: &Setup) -> PostEditCanonicalDefinitionTargetHandleContinuityV1 {
    let (candidate, spans, replacements) = changed_candidate(setup);
    let candidate_text = std::str::from_utf8(&candidate).unwrap();
    let candidate_handles = stable_handles(candidate_text, setup.file_id);
    let selected = selector(candidate_text, setup.file_id, &candidate_handles);
    admit_post_edit_canonical_definition_target_handle_continuity(
        &setup.scope_index,
        setup.selected_scope_id,
        &setup.catalog,
        &setup.record,
        SourceGenerationV1::new(12),
        SOURCE.as_bytes(),
        &candidate,
        &spans,
        &replacements,
        &hydration(&candidate, setup.file_id, 13),
        "anchor.post-edit",
        &candidate_handles,
        SourceGenerationV1::new(13),
        &selected,
    )
    .unwrap()
}

fn reduced_receipt(setup: &Setup) -> CanonicalHigherOwnerOwnerReducedV1 {
    let outer = outer_receipt(setup);
    reprove_canonical_higher_owner_owner_chain(&outer).unwrap()
}

#[test]
fn reduced_owner_chain_projects_to_stable_portable_envelope() {
    let setup = setup("positive");
    let reduced = reduced_receipt(&setup);
    let first = project_reduced_higher_owner_owner_chain(&reduced).unwrap();
    let second = project_reduced_higher_owner_owner_chain(&reduced).unwrap();
    assert_eq!(first, second);
    assert_eq!(first.payload.schema, PORTABLE_OWNER_CHAIN_SCHEMA_V1);
    assert!(first.payload.outer_constructor_reproved_by_inner_owner);
    assert!(first.payload.one_canonical_post_edit_consequence);
    assert!(first.payload.higher_owner_semantic_handle_continuity_proven);
    assert_eq!(
        first
            .payload
            .canonical_target_projection
            .payload
            .selected_target_semantic_handle_digest_hex,
        first.payload.continuous_semantic_handle_digest_hex
    );
    assert!(!first.payload.producer_authenticated);
    assert!(!first.payload.semantic_patch_correctness_proven);
    assert!(!first.payload.commit_authorized);
    verify_portable_higher_owner_owner_chain_projection(&first).unwrap();
    let bytes = serde_json::to_vec(&first).unwrap();
    let decoded: CanonicalHigherOwnerPortableProjectionV1 = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(decoded, first);
    verify_portable_higher_owner_owner_chain_projection(&decoded).unwrap();
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn reduced_handle_divergence_is_rejected_before_transport() {
    let setup = setup("handle");
    let mut reduced = reduced_receipt(&setup);
    reduced.continuous_semantic_handle_digest[0] ^= 0x01;
    assert!(matches!(
        project_reduced_higher_owner_owner_chain(&reduced),
        Err(PortableOwnerChainProjectionErrorV1::HandleMismatch { .. })
    ));
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn missing_owner_reproof_and_authority_widening_fail_closed() {
    let setup = setup("owner-flags");
    let reduced = reduced_receipt(&setup);

    let mut missing = reduced.clone();
    missing.outer_constructor_reproved_by_inner_owner = false;
    assert_eq!(
        project_reduced_higher_owner_owner_chain(&missing),
        Err(PortableOwnerChainProjectionErrorV1::OwnerChainNotReproved)
    );

    let mut widened = reduced;
    widened.commit_authorized = true;
    assert_eq!(
        project_reduced_higher_owner_owner_chain(&widened),
        Err(PortableOwnerChainProjectionErrorV1::OwnerChainAuthorityWidened)
    );
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn nested_projection_tamper_and_portable_handle_tamper_are_rejected() {
    let setup = setup("tamper");
    let reduced = reduced_receipt(&setup);
    let projection = project_reduced_higher_owner_owner_chain(&reduced).unwrap();

    let mut nested = projection.clone();
    nested
        .payload
        .canonical_target_projection
        .payload
        .definition_name
        .push_str("_tampered");
    assert_eq!(
        verify_portable_higher_owner_owner_chain_projection(&nested),
        Err(PortableOwnerChainProjectionErrorV1::Projection(
            ProjectionErrorV1::DigestMismatch
        ))
    );

    let mut handle = projection;
    handle.payload.continuous_semantic_handle_digest_hex = "00".repeat(32);
    assert!(matches!(
        verify_portable_higher_owner_owner_chain_projection(&handle),
        Err(PortableOwnerChainProjectionErrorV1::HandleMismatch { .. })
    ));
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn unknown_fields_and_portable_authority_widening_are_rejected() {
    let setup = setup("schema");
    let reduced = reduced_receipt(&setup);
    let projection = project_reduced_higher_owner_owner_chain(&reduced).unwrap();

    let mut value: Value = serde_json::to_value(&projection).unwrap();
    value
        .as_object_mut()
        .unwrap()
        .insert("parallel_truth_plane".to_owned(), Value::Bool(true));
    assert!(serde_json::from_value::<CanonicalHigherOwnerPortableProjectionV1>(value).is_err());

    let mut widened = projection;
    widened.payload.execution_authorized = true;
    assert_eq!(
        verify_portable_higher_owner_owner_chain_projection(&widened),
        Err(PortableOwnerChainProjectionErrorV1::PortableCeilingWidened)
    );
    fs::remove_dir_all(setup.root).unwrap();
}
