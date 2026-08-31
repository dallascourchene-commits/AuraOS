#![forbid(unsafe_code)]

//! Reduce two independently green canonical/higher-owner conjunctions into one owner chain.
//!
//! PR535 is the outer constructor: it invokes PR525 and PR526 from one exact post-edit input set
//! and emits a canonical-definition-target + higher-owner-handle continuity receipt. PR534 is the
//! narrower canonical receipt verifier: it consumes the two parent receipts and proves they are one
//! identical post-edit structural consequence. This crate does not add a third conjunction rule.
//! It consumes a PR535 receipt, re-proves its embedded parents through PR534, and rejects any outer
//! field that diverges from the canonical inner verifier.

use aura_k27_astge_post_edit_canonical_higher_owner::{
    PostEditCanonicalHigherOwnerContinuityV1, PostEditCanonicalHigherOwnerErrorV1,
    require_post_edit_canonical_higher_owner_continuity,
};
use aura_k27_astge_post_edit_canonical_target_handle_continuity::PostEditCanonicalDefinitionTargetHandleContinuityV1;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CanonicalHigherOwnerOwnerReducedV1 {
    pub outer_constructor_receipt: PostEditCanonicalDefinitionTargetHandleContinuityV1,
    pub canonical_inner_verification: PostEditCanonicalHigherOwnerContinuityV1,
    pub outer_constructor_reproved_by_inner_owner: bool,
    pub one_canonical_post_edit_consequence: bool,
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

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CanonicalHigherOwnerOwnerReductionErrorV1 {
    OuterSameConsequenceNotProven,
    OuterContinuityNotProven,
    Inner(PostEditCanonicalHigherOwnerErrorV1),
    SelectedCandidateHandleMissing,
    OuterInnerHandleMismatch { outer: [u8; 32], inner: [u8; 32] },
    OuterAuthorityWidened,
    InnerAuthorityWidened,
}

impl Display for CanonicalHigherOwnerOwnerReductionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for CanonicalHigherOwnerOwnerReductionErrorV1 {}

impl From<PostEditCanonicalHigherOwnerErrorV1> for CanonicalHigherOwnerOwnerReductionErrorV1 {
    fn from(value: PostEditCanonicalHigherOwnerErrorV1) -> Self {
        Self::Inner(value)
    }
}

fn outer_authority_is_false(receipt: &PostEditCanonicalDefinitionTargetHandleContinuityV1) -> bool {
    !receipt.runtime_name_resolution_proven
        && !receipt.call_graph_proven
        && !receipt.semantic_patch_correctness_proven
        && !receipt.b_minus_approved
        && !receipt.commit_authorized
        && !receipt.execution_authorized
        && !receipt.human_authority
        && !receipt.external_effect_authorized
}

fn inner_authority_is_false(receipt: &PostEditCanonicalHigherOwnerContinuityV1) -> bool {
    !receipt.runtime_name_resolution_proven
        && !receipt.call_graph_proven
        && !receipt.semantic_patch_correctness_proven
        && !receipt.b_minus_approved
        && !receipt.commit_authorized
        && !receipt.execution_authorized
        && !receipt.human_authority
        && !receipt.external_effect_authorized
}

/// Re-prove a PR535 outer-constructor result through PR534's canonical receipt verifier.
///
/// The child deliberately accepts no raw parser/source/scope inputs and implements no target or
/// handle-continuity relation itself. The outer receipt's embedded PR525 and PR526 receipts are the
/// only inputs passed to PR534. A relying party can therefore use PR535 as the construction owner
/// and PR534 as the canonical conjunction verifier instead of trusting two parallel conjunctions.
pub fn reprove_canonical_higher_owner_owner_chain(
    outer: &PostEditCanonicalDefinitionTargetHandleContinuityV1,
) -> Result<CanonicalHigherOwnerOwnerReducedV1, CanonicalHigherOwnerOwnerReductionErrorV1> {
    if !outer.same_post_edit_consequence_instance {
        return Err(CanonicalHigherOwnerOwnerReductionErrorV1::OuterSameConsequenceNotProven);
    }
    if !outer.canonical_definition_target_handle_continuity_proven {
        return Err(CanonicalHigherOwnerOwnerReductionErrorV1::OuterContinuityNotProven);
    }
    if !outer_authority_is_false(outer) {
        return Err(CanonicalHigherOwnerOwnerReductionErrorV1::OuterAuthorityWidened);
    }

    let inner = require_post_edit_canonical_higher_owner_continuity(
        &outer.canonical_target,
        &outer.handle_continuity,
    )?;
    if !inner_authority_is_false(&inner) {
        return Err(CanonicalHigherOwnerOwnerReductionErrorV1::InnerAuthorityWidened);
    }

    let inner_handle = inner
        .canonical
        .post_edit_current
        .selected_candidate_scope
        .semantic_handle_digest
        .ok_or(CanonicalHigherOwnerOwnerReductionErrorV1::SelectedCandidateHandleMissing)?;
    if outer.continuous_semantic_handle_digest != inner_handle {
        return Err(
            CanonicalHigherOwnerOwnerReductionErrorV1::OuterInnerHandleMismatch {
                outer: outer.continuous_semantic_handle_digest,
                inner: inner_handle,
            },
        );
    }

    Ok(CanonicalHigherOwnerOwnerReducedV1 {
        outer_constructor_receipt: outer.clone(),
        canonical_inner_verification: inner,
        outer_constructor_reproved_by_inner_owner: true,
        one_canonical_post_edit_consequence: true,
        continuous_semantic_handle_digest: inner_handle,
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
    use aura_k27_astge::NodeIndexRecordV1;
    use aura_k27_astge_generation_domain::SourceGenerationV1;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, SourceLocatorV1};
    use aura_k27_astge_post_edit_canonical_target_handle_continuity::admit_post_edit_canonical_definition_target_handle_continuity;
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
            "aura-k27-owner-reduction-{label}-{}-{n}",
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

    fn outer_receipt(setup: &Setup) -> PostEditCanonicalDefinitionTargetHandleContinuityV1 {
        let (candidate, spans, replacements) = changed_candidate(setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = stable_handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let hydration = hydration(&candidate, setup.file_id, 13);
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
            &hydration,
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap()
    }

    #[test]
    fn outer_raw_constructor_is_reproved_by_canonical_inner_owner() {
        let setup = setup("positive", 12);
        let outer = outer_receipt(&setup);
        let reduced = reprove_canonical_higher_owner_owner_chain(&outer).unwrap();
        assert!(reduced.outer_constructor_reproved_by_inner_owner);
        assert!(reduced.one_canonical_post_edit_consequence);
        assert_eq!(
            reduced.continuous_semantic_handle_digest,
            outer.continuous_semantic_handle_digest
        );
        assert!(!reduced.runtime_name_resolution_proven);
        assert!(!reduced.semantic_patch_correctness_proven);
        assert!(!reduced.commit_authorized);
        assert!(!reduced.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn forged_outer_handle_cannot_bypass_inner_owner() {
        let setup = setup("outer-handle", 12);
        let mut outer = outer_receipt(&setup);
        outer.continuous_semantic_handle_digest[0] ^= 0x01;
        assert!(matches!(
            reprove_canonical_higher_owner_owner_chain(&outer),
            Err(CanonicalHigherOwnerOwnerReductionErrorV1::OuterInnerHandleMismatch { .. })
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn forged_embedded_higher_owner_receipt_is_rejected_by_inner_owner() {
        let setup = setup("inner-receipt", 12);
        let mut outer = outer_receipt(&setup);
        outer
            .handle_continuity
            .higher_owner_semantic_handle_continuity_proven = false;
        assert!(matches!(
            reprove_canonical_higher_owner_owner_chain(&outer),
            Err(CanonicalHigherOwnerOwnerReductionErrorV1::Inner(
                PostEditCanonicalHigherOwnerErrorV1::HigherOwnerContinuityNotProven
            ))
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn outer_authority_widening_is_rejected_before_conjunction_reproof() {
        let setup = setup("authority", 12);
        let mut outer = outer_receipt(&setup);
        outer.commit_authorized = true;
        assert_eq!(
            reprove_canonical_higher_owner_owner_chain(&outer).unwrap_err(),
            CanonicalHigherOwnerOwnerReductionErrorV1::OuterAuthorityWidened
        );
        fs::remove_dir_all(setup.root).unwrap();
    }
}
