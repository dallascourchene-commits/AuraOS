#![forbid(unsafe_code)]

//! Fail-closed post-edit continuity for one exact higher-owner semantic handle.
//!
//! PR515 owns fresh post-edit profiled-scope currentness. PR508 independently establishes that
//! canonical definition ownership and the selected definition-target scope are explicit relations,
//! not name-text or local-ID coincidences. This membrane composes those exact owners and adds one
//! invariant only: the selected post-edit scope must retain the semantic handle admitted for the
//! pre-edit selected scope. Candidate-local handle maps cannot mint continuity.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::SourceGenerationV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_post_edit_profiled_scope::{
    CandidateProfiledScopeSelectorV1, PostEditProfiledScopeCurrentV1,
    PostEditProfiledScopeErrorV1, admit_post_edit_profiled_scope_current,
};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::PythonLexicalScopeIndexV1;
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PostEditHigherOwnerContinuityV1 {
    pub post_edit: PostEditProfiledScopeCurrentV1,
    pub higher_owner_semantic_handle_continuity_proven: bool,
    pub candidate_local_handle_authority: bool,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum PostEditHigherOwnerContinuityErrorV1 {
    PostEdit(PostEditProfiledScopeErrorV1),
    PreEditHigherOwnerHandleMissing,
    CandidateHigherOwnerHandleMissing,
    HigherOwnerHandleMismatch {
        pre_edit: [u8; 32],
        candidate: [u8; 32],
    },
}

impl Display for PostEditHigherOwnerContinuityErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PostEditHigherOwnerContinuityErrorV1 {}

impl From<PostEditProfiledScopeErrorV1> for PostEditHigherOwnerContinuityErrorV1 {
    fn from(value: PostEditProfiledScopeErrorV1) -> Self {
        Self::PostEdit(value)
    }
}

fn require_same_higher_owner_handle(
    pre_edit: [u8; 32],
    candidate: [u8; 32],
) -> Result<(), PostEditHigherOwnerContinuityErrorV1> {
    if pre_edit != candidate {
        return Err(
            PostEditHigherOwnerContinuityErrorV1::HigherOwnerHandleMismatch {
                pre_edit,
                candidate,
            },
        );
    }
    Ok(())
}

/// Admit PR515 post-edit structural currentness only when the semantic handle carried by the
/// selected candidate scope is exactly the semantic handle previously admitted by the higher-owner
/// pre-edit scope review.
///
/// This proves continuity of that exact handle only. It does not prove runtime name resolution,
/// call targets, semantic patch correctness, B-minus approval, commit authority, or external effect.
#[allow(clippy::too_many_arguments)]
pub fn admit_post_edit_higher_owner_continuity(
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
) -> Result<PostEditHigherOwnerContinuityV1, PostEditHigherOwnerContinuityErrorV1> {
    let post_edit = admit_post_edit_profiled_scope_current(
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

    let pre_edit_handle = post_edit
        .pre_edit_review
        .owner_admission
        .selected_scope
        .semantic_handle_digest
        .ok_or(PostEditHigherOwnerContinuityErrorV1::PreEditHigherOwnerHandleMissing)?;
    let candidate_handle = post_edit
        .selected_candidate_scope
        .semantic_handle_digest
        .ok_or(PostEditHigherOwnerContinuityErrorV1::CandidateHigherOwnerHandleMissing)?;

    require_same_higher_owner_handle(pre_edit_handle, candidate_handle)?;

    Ok(PostEditHigherOwnerContinuityV1 {
        post_edit,
        higher_owner_semantic_handle_continuity_proven: true,
        candidate_local_handle_authority: false,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_higher_owner_handle_continuity_is_admitted() {
        let digest = [0x31; 32];
        require_same_higher_owner_handle(digest, digest).unwrap();
    }

    #[test]
    fn candidate_local_coherent_substitution_cannot_mint_continuity() {
        let pre_edit = [0x31; 32];
        let candidate_local = [0x47; 32];
        let error = require_same_higher_owner_handle(pre_edit, candidate_local).unwrap_err();
        assert!(matches!(
            error,
            PostEditHigherOwnerContinuityErrorV1::HigherOwnerHandleMismatch {
                pre_edit: observed_pre,
                candidate: observed_candidate,
            } if observed_pre == pre_edit && observed_candidate == candidate_local
        ));
    }

    #[test]
    fn one_byte_handle_drift_fails_closed() {
        let pre_edit = [0xA5; 32];
        let mut candidate = pre_edit;
        candidate[17] ^= 0x01;
        assert!(matches!(
            require_same_higher_owner_handle(pre_edit, candidate),
            Err(PostEditHigherOwnerContinuityErrorV1::HigherOwnerHandleMismatch { .. })
        ));
    }
}
