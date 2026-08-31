#![forbid(unsafe_code)]

//! Post-edit currentness for one exact profiled Python lexical scope.
//!
//! This membrane composes two independently verified owners:
//! - PR503 owns the admitted pre-edit nested-scope review and typed SourceGeneration boundary;
//! - PR501 owns independently witnessed CURRENT source-body + SyntaxGraph + profiled-scope hydration.
//!
//! Incremental parser reuse is deliberately not an authority input in V1. Candidate currentness is
//! earned by a fresh full parse/profile on the exact candidate body, followed by a second clean
//! full-profile execution through the lower profile owner. Runtime name resolution, semantic patch
//! correctness, B-minus approval, commit authority and external effect remain outside this crate.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_current_profiled_scopes::{
    CurrentProfiledScopeError, CurrentTypedProfiledScopesV1,
    admit_current_typed_profiled_python_scopes,
};
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_profiled_scopes::{
    ProfiledPythonScopesV1, ProfiledScopeAnchorV1, ProfiledScopeError,
    build_profiled_python_scopes,
};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::PythonLexicalScopeIndexV1;
use aura_k27_astge_typed_nested_scope_review::{
    TypedNestedScopeReviewErrorV1, TypedNestedScopeSourceReviewAdmissionV1,
    admit_typed_nested_scope_source_review,
};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateProfiledScopeSelectorV1 {
    pub syntax_ordinal: u64,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub semantic_handle_digest: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PostEditProfiledScopeCurrentV1 {
    pub pre_edit_review: TypedNestedScopeSourceReviewAdmissionV1,
    pub candidate_current: CurrentTypedProfiledScopesV1,
    pub clean_full_reparse_profile: ProfiledPythonScopesV1,
    pub selected_candidate_scope: ProfiledScopeAnchorV1,
    pub candidate_source_generation: SourceGenerationV1,
    pub candidate_source_generation_coordinate: GenerationCoordinateV1,
    pub post_edit_profiled_scope_current: bool,
    pub clean_full_reparse_profile_match: bool,
    pub candidate_scope_reselected_from_canonical_anchor: bool,
    pub old_local_scope_id_reused_as_currentness_authority: bool,
    pub incremental_parser_reuse_used: bool,
    pub changed_ranges_currentness_authority: bool,
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
pub enum PostEditProfiledScopeErrorV1 {
    PreEdit(TypedNestedScopeReviewErrorV1),
    CandidateSourceUtf8,
    NoSourceChange,
    PreEditScopeMissing(u64),
    CandidateGenerationNotAdvanced { pre_edit: u64, candidate: u64 },
    CandidateCurrent(CurrentProfiledScopeError),
    CandidateGenerationMismatch { expected: u64, observed: u64 },
    CleanProfile(ProfiledScopeError),
    CleanProfileMismatch,
    CandidateScopeMissing,
    CandidateScopeAmbiguous(usize),
    CandidateScopeIsModule,
    CandidateScopeTransitionMismatch {
        expected_start: u32,
        expected_end: u32,
        observed_start: u32,
        observed_end: u32,
    },
    ScopeSpanOverflow,
}

impl Display for PostEditProfiledScopeErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PostEditProfiledScopeErrorV1 {}

impl From<TypedNestedScopeReviewErrorV1> for PostEditProfiledScopeErrorV1 {
    fn from(value: TypedNestedScopeReviewErrorV1) -> Self {
        Self::PreEdit(value)
    }
}

impl From<CurrentProfiledScopeError> for PostEditProfiledScopeErrorV1 {
    fn from(value: CurrentProfiledScopeError) -> Self {
        Self::CandidateCurrent(value)
    }
}

impl From<ProfiledScopeError> for PostEditProfiledScopeErrorV1 {
    fn from(value: ProfiledScopeError) -> Self {
        Self::CleanProfile(value)
    }
}

/// Admit post-edit currentness for one exact candidate profiled lexical scope.
///
/// The pre-edit local scope ID is consumed only by the existing PR503 review owner. The candidate
/// scope is selected independently by canonical SyntaxGraph ordinal + exact candidate span +
/// higher-owner semantic-handle digest. A changed body must advance the SourceGeneration.
///
/// Placement generation cannot inhabit either SourceGeneration slot:
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::{PlacementGenerationV1, SourceGenerationV1};
/// use aura_k27_astge_post_edit_profiled_scope::{
///     CandidateProfiledScopeSelectorV1, admit_post_edit_profiled_scope_current,
/// };
/// # fn demo(
/// #   index: &aura_k27_astge_scopes::PythonLexicalScopeIndexV1,
/// #   catalog: &aura_k27_astge_materialize::AdmittedSourceCatalogV1,
/// #   record: &aura_k27_astge::NodeIndexRecordV1,
/// #   handles: &std::collections::HashMap<u64, [u8; 32]>,
/// #   selector: &CandidateProfiledScopeSelectorV1,
/// # ) {
/// let placement = PlacementGenerationV1::new(13);
/// let _ = admit_post_edit_profiled_scope_current(
///     index, 1, catalog, record, SourceGenerationV1::new(12),
///     b"old", b"new", &[], &[], "{}", "anchor", handles,
///     placement, selector,
/// );
/// # }
/// ```
#[allow(clippy::too_many_arguments)]
pub fn admit_post_edit_profiled_scope_current(
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
) -> Result<PostEditProfiledScopeCurrentV1, PostEditProfiledScopeErrorV1> {
    let pre_scope = pre_edit_scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == pre_edit_selected_scope_id)
        .ok_or(PostEditProfiledScopeErrorV1::PreEditScopeMissing(
            pre_edit_selected_scope_id,
        ))?;

    let pre_edit_review = admit_typed_nested_scope_source_review(
        pre_edit_scope_index,
        pre_edit_selected_scope_id,
        pre_edit_catalog,
        persisted_record,
        expected_pre_edit_source_generation,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;

    if original_source == candidate_source {
        return Err(PostEditProfiledScopeErrorV1::NoSourceChange);
    }

    if expected_candidate_source_generation.value() == pre_edit_review.source_generation.value() {
        return Err(
            PostEditProfiledScopeErrorV1::CandidateGenerationNotAdvanced {
                pre_edit: pre_edit_review.source_generation.value(),
                candidate: expected_candidate_source_generation.value(),
            },
        );
    }

    let candidate_text = std::str::from_utf8(candidate_source)
        .map_err(|_| PostEditProfiledScopeErrorV1::CandidateSourceUtf8)?;
    let candidate_current = admit_current_typed_profiled_python_scopes(
        candidate_hydration_json,
        candidate_anchor_id,
        candidate_text,
        persisted_record.file_id,
        candidate_semantic_handles,
    )?;

    if candidate_current.source_generation != expected_candidate_source_generation {
        return Err(PostEditProfiledScopeErrorV1::CandidateGenerationMismatch {
            expected: expected_candidate_source_generation.value(),
            observed: candidate_current.source_generation.value(),
        });
    }

    let clean_full_reparse_profile = build_profiled_python_scopes(
        candidate_text,
        persisted_record.file_id,
        candidate_current.profiled_scopes.source_owner_ref.clone(),
        candidate_current.profiled_scopes.source_generation_ref.clone(),
        candidate_semantic_handles,
    )?;
    if clean_full_reparse_profile != candidate_current.profiled_scopes {
        return Err(PostEditProfiledScopeErrorV1::CleanProfileMismatch);
    }

    let matches: Vec<_> = candidate_current
        .profiled_scopes
        .profiled_scopes
        .iter()
        .filter(|scope| {
            scope.syntax_ordinal == Some(candidate_selector.syntax_ordinal)
                && scope.file_id == candidate_selector.file_id
                && scope.byte_start == candidate_selector.byte_start
                && scope.byte_end == candidate_selector.byte_end
                && scope.semantic_handle_digest == Some(candidate_selector.semantic_handle_digest)
        })
        .collect();
    let selected_candidate_scope = match matches.as_slice() {
        [] => return Err(PostEditProfiledScopeErrorV1::CandidateScopeMissing),
        [scope] => (*scope).clone(),
        _ => {
            return Err(PostEditProfiledScopeErrorV1::CandidateScopeAmbiguous(
                matches.len(),
            ));
        }
    };
    if selected_candidate_scope.parent_scope_id.is_none() {
        return Err(PostEditProfiledScopeErrorV1::CandidateScopeIsModule);
    }

    let (expected_candidate_start, expected_candidate_end) = transformed_scope_span(
        pre_scope.byte_start,
        pre_scope.byte_end,
        replacements,
    )?;
    if selected_candidate_scope.byte_start != expected_candidate_start
        || selected_candidate_scope.byte_end != expected_candidate_end
    {
        return Err(
            PostEditProfiledScopeErrorV1::CandidateScopeTransitionMismatch {
                expected_start: expected_candidate_start,
                expected_end: expected_candidate_end,
                observed_start: selected_candidate_scope.byte_start,
                observed_end: selected_candidate_scope.byte_end,
            },
        );
    }

    Ok(PostEditProfiledScopeCurrentV1 {
        candidate_source_generation_coordinate: candidate_current.source_generation.coordinate(),
        candidate_source_generation: candidate_current.source_generation,
        pre_edit_review,
        clean_full_reparse_profile,
        selected_candidate_scope,
        candidate_current,
        post_edit_profiled_scope_current: true,
        clean_full_reparse_profile_match: true,
        candidate_scope_reselected_from_canonical_anchor: true,
        old_local_scope_id_reused_as_currentness_authority: false,
        incremental_parser_reuse_used: false,
        changed_ranges_currentness_authority: false,
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

fn transformed_scope_span(
    old_start: u32,
    old_end: u32,
    replacements: &[ReplacementV1],
) -> Result<(u32, u32), PostEditProfiledScopeErrorV1> {
    let mut delta: i128 = 0;
    for replacement in replacements {
        let removed = i128::from(replacement.end.saturating_sub(replacement.start));
        let inserted = i128::try_from(replacement.replacement.len())
            .map_err(|_| PostEditProfiledScopeErrorV1::ScopeSpanOverflow)?;
        delta += inserted - removed;
    }
    let new_end = i128::from(old_end) + delta;
    if new_end < i128::from(old_start) || new_end > i128::from(u32::MAX) {
        return Err(PostEditProfiledScopeErrorV1::ScopeSpanOverflow);
    }
    Ok((old_start, new_end as u32))
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_generation_domain::{GenerationDomainV1, PlacementGenerationV1};
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use serde_json::{Value, json};
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
        old_handles: HashMap<u64, [u8; 32]>,
        edit_start: usize,
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

    fn setup(label: &str, generation: u64) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-post-edit-profiled-{label}-{}-{n}",
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
        let encoded = encode_ast_to_splane(&graph, &old_handles, 0, 41, [0x91; 32]).unwrap();
        let record = encoded
            .records
            .iter()
            .find(|record| record.node_id == selected.ast_node_id.unwrap())
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
            selected_scope_id: selected.scope_id,
            record,
            catalog,
            old_handles,
            edit_start,
        }
    }

    fn sha256_hex(source: &[u8]) -> String {
        Sha256::digest(source)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect()
    }

    fn hydration(source: &[u8], file_id: u32, generation: u64, status: &str) -> String {
        let admitted = status == "CURRENT";
        let sha = sha256_hex(source);
        let locator = if admitted {
            json!({
                "file_id": file_id,
                "relative_path": "src/module.py",
                "source_generation": generation,
                "byte_len": source.len(),
                "sha256": sha,
            })
        } else {
            Value::Null
        };
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
                "body_currentness_status": status,
                "hydration_admitted": admitted,
                "reason": if admitted { "EXACT_SOURCE_BODY_WITNESS_MATCH" } else { "SOURCE_BODY_DIGEST_DRIFT" },
                "witness_ref": if admitted { "witness://post-edit/body" } else { "" },
                "expected_byte_len": source.len(),
                "observed_byte_len": source.len(),
                "expected_body_sha256": sha,
                "observed_body_sha256": sha,
                "locator": locator,
            }],
            "source_locators_v1": [],
        })
        .to_string()
    }

    fn changed_candidate(setup: &Setup) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = SOURCE.as_bytes().to_vec();
        candidate.splice(setup.edit_start..setup.edit_start + 1, b"100".iter().copied());
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

    fn selector(source: &str, file_id: u32, handles: &HashMap<u64, [u8; 32]>) -> CandidateProfiledScopeSelectorV1 {
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

    #[test]
    fn changed_body_requires_fresh_current_profile_and_reselected_scope() {
        let setup = setup("positive", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let receipt = admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap();
        assert!(receipt.post_edit_profiled_scope_current);
        assert!(receipt.clean_full_reparse_profile_match);
        assert!(receipt.candidate_scope_reselected_from_canonical_anchor);
        assert_eq!(receipt.candidate_source_generation.value(), 13);
        assert_eq!(
            receipt.candidate_source_generation_coordinate.domain,
            GenerationDomainV1::Source
        );
        assert!(!receipt.old_local_scope_id_reused_as_currentness_authority);
        assert!(!receipt.incremental_parser_reuse_used);
        assert!(!receipt.changed_ranges_currentness_authority);
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
    fn stale_pre_edit_scope_anchor_cannot_select_length_shifted_candidate_scope() {
        let setup = setup("stale-selector", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let old_profile = build_profiled_python_scopes(
            SOURCE,
            setup.file_id,
            "source-owner://post-edit-profiled",
            "old-generation",
            &setup.old_handles,
        )
        .unwrap();
        let old_scope = old_profile
            .profiled_scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let stale = CandidateProfiledScopeSelectorV1 {
            syntax_ordinal: old_scope.syntax_ordinal.unwrap(),
            file_id: old_scope.file_id,
            byte_start: old_scope.byte_start,
            byte_end: old_scope.byte_end,
            semantic_handle_digest: old_scope.semantic_handle_digest.unwrap(),
        };
        let error = admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &stale,
        )
        .unwrap_err();
        assert!(matches!(error, PostEditProfiledScopeErrorV1::CandidateScopeMissing));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn changed_body_cannot_reuse_pre_edit_source_generation() {
        let setup = setup("generation-not-advanced", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let error = admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 12, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(12),
            &selected,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            PostEditProfiledScopeErrorV1::CandidateGenerationNotAdvanced {
                pre_edit: 12,
                candidate: 12
            }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn candidate_generation_expectation_must_match_independent_current_witness() {
        let setup = setup("wrong-candidate-generation", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let error = admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "CURRENT"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(14),
            &selected,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            PostEditProfiledScopeErrorV1::CandidateGenerationMismatch {
                expected: 14,
                observed: 13
            }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn stale_candidate_body_witness_cannot_emit_post_edit_currentness() {
        let setup = setup("stale-candidate", 12);
        let (candidate, spans, replacements) = changed_candidate(&setup);
        let candidate_text = std::str::from_utf8(&candidate).unwrap();
        let candidate_handles = handles(candidate_text, setup.file_id);
        let selected = selector(candidate_text, setup.file_id, &candidate_handles);
        let error = admit_post_edit_profiled_scope_current(
            &setup.scope_index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(12),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
            &hydration(&candidate, setup.file_id, 13, "STALE"),
            "anchor.post-edit",
            &candidate_handles,
            SourceGenerationV1::new(13),
            &selected,
        )
        .unwrap_err();
        assert!(matches!(error, PostEditProfiledScopeErrorV1::CandidateCurrent(_)));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn equal_numeric_placement_coordinate_is_not_source_generation_identity() {
        let source = SourceGenerationV1::new(13).coordinate();
        let placement = PlacementGenerationV1::new(13).coordinate();
        assert_eq!(source.value, placement.value);
        assert_ne!(source, placement);
    }
}
