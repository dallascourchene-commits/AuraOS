#![forbid(unsafe_code)]

//! Join two independently earned post-edit ASTGE consequences without reimplementing either owner.
//!
//! PR525 owns post-edit canonical definition-target currentness. PR526 owns exact higher-owner
//! semantic-handle continuity across the edit. This membrane accepts only those two receipts and
//! proves they are the same post-edit structural consequence before emitting the conjunction.
//! Runtime name resolution, call-graph truth, semantic patch correctness, review approval, commit
//! authority and external effect remain explicitly false.

use aura_k27_astge_post_edit_canonical_scope::PostEditCanonicalDefinitionTargetCurrentV1;
use aura_k27_astge_post_edit_higher_owner_continuity::PostEditHigherOwnerContinuityV1;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PostEditCanonicalHigherOwnerContinuityV1 {
    pub canonical: PostEditCanonicalDefinitionTargetCurrentV1,
    pub higher_owner: PostEditHigherOwnerContinuityV1,
    pub shared_post_edit_receipt_proven: bool,
    pub canonical_target_matches_selected_scope: bool,
    pub higher_owner_handle_matches_selected_scope: bool,
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
pub enum PostEditCanonicalHigherOwnerErrorV1 {
    CanonicalCurrentnessNotProven,
    HigherOwnerContinuityNotProven,
    PostEditReceiptMismatch,
    CanonicalTargetMismatch {
        selected_scope_id: u64,
        relation_target_scope_id: u64,
    },
    SelectedCandidateHandleMissing,
    PreEditHigherOwnerHandleMissing,
    HigherOwnerHandleMismatch {
        pre_edit: [u8; 32],
        candidate: [u8; 32],
    },
}

impl Display for PostEditCanonicalHigherOwnerErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PostEditCanonicalHigherOwnerErrorV1 {}

fn require_shared_handle(
    pre_edit: [u8; 32],
    candidate: [u8; 32],
) -> Result<(), PostEditCanonicalHigherOwnerErrorV1> {
    if pre_edit != candidate {
        return Err(PostEditCanonicalHigherOwnerErrorV1::HigherOwnerHandleMismatch {
            pre_edit,
            candidate,
        });
    }
    Ok(())
}

/// Require PR525 and PR526 to describe one identical post-edit structural receipt.
///
/// This is a receipt-conjunction boundary only. It does not replay raw source inputs and does not
/// upgrade either parent's consequence into runtime, semantic, review, mutation or effect authority.
pub fn require_post_edit_canonical_higher_owner_continuity(
    canonical: &PostEditCanonicalDefinitionTargetCurrentV1,
    higher_owner: &PostEditHigherOwnerContinuityV1,
) -> Result<PostEditCanonicalHigherOwnerContinuityV1, PostEditCanonicalHigherOwnerErrorV1> {
    if !canonical.post_edit_profiled_scope_current || !canonical.canonical_definition_target_current {
        return Err(PostEditCanonicalHigherOwnerErrorV1::CanonicalCurrentnessNotProven);
    }
    if !higher_owner.higher_owner_semantic_handle_continuity_proven {
        return Err(PostEditCanonicalHigherOwnerErrorV1::HigherOwnerContinuityNotProven);
    }
    if canonical.post_edit_current != higher_owner.post_edit {
        return Err(PostEditCanonicalHigherOwnerErrorV1::PostEditReceiptMismatch);
    }

    let selected = &canonical.post_edit_current.selected_candidate_scope;
    if canonical.relation.definition_target_scope_id != selected.scope_id {
        return Err(PostEditCanonicalHigherOwnerErrorV1::CanonicalTargetMismatch {
            selected_scope_id: selected.scope_id,
            relation_target_scope_id: canonical.relation.definition_target_scope_id,
        });
    }

    let candidate_handle = selected
        .semantic_handle_digest
        .ok_or(PostEditCanonicalHigherOwnerErrorV1::SelectedCandidateHandleMissing)?;
    let pre_edit_handle = higher_owner
        .post_edit
        .pre_edit_review
        .owner_admission
        .selected_scope
        .semantic_handle_digest
        .ok_or(PostEditCanonicalHigherOwnerErrorV1::PreEditHigherOwnerHandleMissing)?;
    require_shared_handle(pre_edit_handle, candidate_handle)?;

    Ok(PostEditCanonicalHigherOwnerContinuityV1 {
        canonical: canonical.clone(),
        higher_owner: higher_owner.clone(),
        shared_post_edit_receipt_proven: true,
        canonical_target_matches_selected_scope: true,
        higher_owner_handle_matches_selected_scope: true,
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

    #[test]
    fn exact_shared_handle_is_accepted() {
        let handle = [0x51; 32];
        require_shared_handle(handle, handle).unwrap();
    }

    #[test]
    fn coherent_but_different_handle_is_rejected() {
        let pre_edit = [0x51; 32];
        let candidate = [0x52; 32];
        assert!(matches!(
            require_shared_handle(pre_edit, candidate),
            Err(PostEditCanonicalHigherOwnerErrorV1::HigherOwnerHandleMismatch {
                pre_edit: observed_pre,
                candidate: observed_candidate,
            }) if observed_pre == pre_edit && observed_candidate == candidate
        ));
    }

    #[test]
    fn one_byte_drift_is_rejected() {
        let pre_edit = [0xA7; 32];
        let mut candidate = pre_edit;
        candidate[9] ^= 0x01;
        assert!(matches!(
            require_shared_handle(pre_edit, candidate),
            Err(PostEditCanonicalHigherOwnerErrorV1::HigherOwnerHandleMismatch { .. })
        ));
    }
}
