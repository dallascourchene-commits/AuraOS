use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::SourceGenerationV1;
use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, SourceLocatorV1};
use aura_k27_astge_post_edit_canonical_scope::{
    PostEditCanonicalDefinitionTargetCurrentV1,
    admit_post_edit_canonical_definition_target_current,
};
use aura_k27_astge_post_edit_profiled_scope::CandidateProfiledScopeSelectorV1;
use aura_k27_astge_profiled_scopes::build_profiled_python_scopes;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::{PythonLexicalScopeIndexV1, index_python_nested_scopes};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);
const SOURCE: &str = "def outer():\n    def inner():\n        return 1\n    return inner\n";

pub struct Setup {
    pub root: PathBuf,
    file_id: u32,
    scope_index: PythonLexicalScopeIndexV1,
    selected_scope_id: u64,
    record: NodeIndexRecordV1,
    catalog: AdmittedSourceCatalogV1,
    edit_start: usize,
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
    parse_python_named_ast(source, file_id)
        .unwrap()
        .nodes
        .into_iter()
        .map(|node| {
            let mut digest = [0u8; 32];
            digest[..8].copy_from_slice(&node.node_id.to_le_bytes());
            digest[8..12].copy_from_slice(&file_id.to_le_bytes());
            (node.node_id, digest)
        })
        .collect()
}

pub fn setup(label: &str) -> Setup {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let root = std::env::temp_dir().join(format!(
        "aura-k27-canonical-projection-{label}-{}-{n}",
        std::process::id()
    ));
    fs::create_dir_all(root.join("src")).unwrap();
    fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();
    let file_id = 177;
    let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
    let old_handles = handles(SOURCE, file_id);
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

fn hydration(source: &[u8], file_id: u32, generation: u64) -> String {
    let sha = hex(&Sha256::digest(source));
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
    supplied: &HashMap<u64, [u8; 32]>,
) -> CandidateProfiledScopeSelectorV1 {
    let profiled = build_profiled_python_scopes(
        source,
        file_id,
        "source-owner://post-edit-profiled",
        "candidate-generation",
        supplied,
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

pub fn owner_receipt(setup: &Setup) -> PostEditCanonicalDefinitionTargetCurrentV1 {
    let (candidate, spans, replacements) = changed_candidate(setup);
    let candidate_text = std::str::from_utf8(&candidate).unwrap();
    let candidate_handles = handles(candidate_text, setup.file_id);
    let selected = selector(candidate_text, setup.file_id, &candidate_handles);
    admit_post_edit_canonical_definition_target_current(
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
