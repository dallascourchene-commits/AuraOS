#![forbid(unsafe_code)]

//! Composition-only post-edit canonical definition-target handle continuity.
//!
//! PR525 owns post-edit canonical definition-target currentness. PR526 owns exact
//! cross-edit semantic-handle continuity for the selected post-edit scope. This
//! crate adds one relation only: both sibling consequences must describe the same
//! exact embedded PR515 post-edit currentness receipt before their claims may be
//! conjoined.
//!
//! No parser, scope, definition-binding, semantic-handle, runtime-resolution,
//! semantic-correctness, review, commit, execution, or effect owner is created here.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::SourceGenerationV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_post_edit_canonical_scope::{
    PostEditCanonicalDefinitionTargetCurrentV1, PostEditCanonicalScopeErrorV1,
    admit_post_edit_canonical_definition_target_current,
};
use aura_k27_astge_post_edit_higher_owner_continuity::{
    PostEditHigherOwnerContinuityErrorV1, PostEditHigherOwnerContinuityV1,
    admit_post_edit_higher_owner_continuity,
};
use aura_k27_astge_post_edit_profiled_scope::CandidateProfiledScopeSelectorV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::PythonLexicalScopeIndexV1;
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PostEditCanonicalDefinitionTargetHandleContinuityV1 {
    pub canonical_target: PostEditCanonicalDefinitionTargetCurrentV1,
    pub handle_continuity: PostEditHigherOwnerContinuityV1,
    pub same_post_edit_consequence_instance: bool,
    pub canonical_definition_target_handle_continuity_proven: bool,
    pub continuous_semantic_handle_digest: [u8; 32],
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub execution_authorized: bool,
    pub human_authority: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum PostEditCanonicalTargetHandleContinuityErrorV1 {
    CanonicalTarget(PostEditCanonicalScopeErrorV1),
    HandleContinuity(PostEditHigherOwnerContinuityErrorV1),
    CanonicalTargetCurrentnessNotProven,
    HigherOwnerContinuityNotProven,
    ParentPostEditReceiptMismatch,
    CanonicalTargetScopeMismatch {
        relation_target_scope_id: u64,
        selected_candidate_scope_id: u64,
    },
    CandidateSemanticHandleMissing,
}

impl Display for PostEditCanonicalTargetHandleContinuityErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PostEditCanonicalTargetHandleContinuityErrorV1 {}

impl From<PostEditCanonicalScopeErrorV1> for PostEditCanonicalTargetHandleContinuityErrorV1 {
    fn from(value: PostEditCanonicalScopeErrorV1) -> Self {
        Self::CanonicalTarget(value)
    }
}

impl From<PostEditHigherOwnerContinuityErrorV1>
    for PostEditCanonicalTargetHandleContinuityErrorV1
{
    fn from(value: PostEditHigherOwnerContinuityErrorV1) -> Self {
        Self::HandleContinuity(value)
    }
}

fn require_same_consequence_and_target(
    canonical_target: &PostEditCanonicalDefinitionTargetCurrentV1,
    handle_continuity: &PostEditHigherOwnerContinuityV1,
) -> Result<[u8; 32], PostEditCanonicalTargetHandleContinuityErrorV1> {
    if !canonical_target.post_edit_profiled_scope_current
        || !canonical_target.canonical_definition_target_current
    {
        return Err(
            PostEditCanonicalTargetHandleContinuityErrorV1::CanonicalTargetCurrentnessNotProven,
        );
    }
    if !handle_continuity.higher_owner_semantic_handle_continuity_proven {
        return Err(
            PostEditCanonicalTargetHandleContinuityErrorV1::HigherOwnerContinuityNotProven,
        );
    }
    if canonical_target.post_edit_current != handle_continuity.post_edit {
        return Err(
            PostEditCanonicalTargetHandleContinuityErrorV1::ParentPostEditReceiptMismatch,
        );
    }

    let selected_scope_id = canonical_target
        .post_edit_current
        .selected_candidate_scope
        .scope_id;
    if canonical_target.relation.definition_target_scope_id != selected_scope_id {
        return Err(
            PostEditCanonicalTargetHandleContinuityErrorV1::CanonicalTargetScopeMismatch {
                relation_target_scope_id: canonical_target.relation.definition_target_scope_id,
                selected_candidate_scope_id: selected_scope_id,
            },
        );
    }

    canonical_target
        .post_edit_current
        .selected_candidate_scope
        .semantic_handle_digest
        .ok_or(PostEditCanonicalTargetHandleContinuityErrorV1::CandidateSemanticHandleMissing)
}

/// Invoke PR525 and PR526 over one exact input set and admit their conjunction only
/// when both sibling receipts embed the same exact PR515 post-edit consequence.
#[allow(clippy::too_many_arguments)]
pub fn admit_post_edit_canonical_definition_target_handle_continuity(
    pre_edit_scope_index: &PythonLexicalScopeIndexV1,
    pre_edit_selected_scope_id: u64,
    pre_edit_catalog: &AdmittedSourceCatalogV1,
    persisted_record: &NodeIndexRecordV1,
    expected_pre_edit_source_generation: SourceGenerationV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
    candidate_hydration_json: &str,
    candidate_anchor_id: &str,
    candidate_semantic_handles: &HashMap<u64, [u8; 32]>,
    expected_candidate_source_generation: SourceGenerationV1,
    candidate_selector: &CandidateProfiledScopeSelectorV1,
) -> Result<
    PostEditCanonicalDefinitionTargetHandleContinuityV1,
    PostEditCanonicalTargetHandleContinuityErrorV1,
> {
    let canonical_target = admit_post_edit_canonical_definition_target_current(
        pre_edit_scope_index,
        pre_edit_selected_scope_id,
        pre_edit_catalog,
        persisted_record,
        expected_pre_edit_source_generation,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
        candidate_hydration_json,
        candidate_anchor_id,
        candidate_semantic_handles,
        expected_candidate_source_generation,
        candidate_selector,
    )?;

    let handle_continuity = admit_post_edit_higher_owner_continuity(
        pre_edit_scope_index,
        pre_edit_selected_scope_id,
        pre_edit_catalog,
        persisted_record,
        expected_pre_edit_source_generation,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
        candidate_hydration_json,
        candidate_anchor_id,
        candidate_semantic_handles,
        expected_candidate_source_generation,
        candidate_selector,
    )?;

    let continuous_semantic_handle_digest =
        require_same_consequence_and_target(&canonical_target, &handle_continuity)?;

    Ok(PostEditCanonicalDefinitionTargetHandleContinuityV1 {
        canonical_target,
        handle_continuity,
        same_post_edit_consequence_instance: true,
        canonical_definition_target_handle_continuity_proven: true,
        continuous_semantic_handle_digest,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        execution_authorized: false,
        human_authority: false,
        external_effect_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_post_edit_profiled_scope::CandidateProfiledScopeSelectorV1;
    use aura_k27_astge_profiled_scopes::build_profiled_python_scopes;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use serde_json::json;
    use sha2::{Digest, Sha256};
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

    fn setup(label: &str, generation: u64) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-post-edit-target-continuity-{label}-{}-{n}",
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
                generation,
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

    fn parent_receipts(
        setup: &Setup,
    ) -> (
        PostEditCanonicalDefinitionTargetCurrentV1,
        PostEditHigherOwnerContinuityV1,
    ) {
        let (candidate, spans, replacements) = changed_candidate(setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = stable_handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let hydration = hydration(&candidate, setup.file_id, 13);
        let canonical = admit_post_edit_canonical_definition_target_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration,
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap();
        let continuity = admit_post_edit_higher_owner_continuity(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration,
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap();
        (canonical, continuity)
    }

    #[test]
    fn exact_sibling_consequences_join_on_one_canonical_target() {
        let setup = setup("positive", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = stable_handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let receipt = admit_post_edit_canonical_definition_target_handle_continuity(
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
        .unwrap();
        assert!(receipt.same_post_edit_consequence_instance);
        assert!(receipt.canonical_definition_target_handle_continuity_proven);
        assert_eq!(receipt.continuous_semantic_handle_digest, [0x31; 32]);
        assert_eq!(
            receipt.canonical_target.relation.definition_target_scope_id,
            receipt
                .canonical_target
                .post_edit_current
                .selected_candidate_scope
                .scope_id
        );
        assert!(!receipt.runtime_name_resolution_proven);
        assert!(!receipt.call_graph_proven);
        assert!(!receipt.semantic_patch_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.execution_authorized);
        assert!(!receipt.human_authority);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn cross_receipt_post_edit_substitution_fails_closed() {
        let setup = setup("post-edit-substitution", 12);
        let (canonical, mut continuity) = parent_receipts(&setup);
        continuity.post_edit.candidate_source_generation = SourceGenerationV1::new(99);
        let error = require_same_consequence_and_target(&canonical, &continuity).unwrap_err();
        assert!(matches!(
            error,
            PostEditCanonicalTargetHandleContinuityErrorV1::ParentPostEditReceiptMismatch
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn forged_relation_target_cannot_join_even_with_same_parent_receipt() {
        let setup = setup("target-substitution", 12);
        let (mut canonical, continuity) = parent_receipts(&setup);
        canonical.relation.definition_target_scope_id += 1;
        let error = require_same_consequence_and_target(&canonical, &continuity).unwrap_err();
        assert!(matches!(
            error,
            PostEditCanonicalTargetHandleContinuityErrorV1::CanonicalTargetScopeMismatch { .. }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }
}
