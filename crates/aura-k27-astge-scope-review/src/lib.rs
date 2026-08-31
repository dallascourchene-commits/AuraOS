#![forbid(unsafe_code)]

//! Nested lexical-scope restriction over source-current ASTGE review admission.
//!
//! A lexical scope is a restriction coordinate, never mutation authority. The higher source owner
//! must still provide every authorized byte span and declared replacement. This membrane requires
//! those spans to stay inside one exact current function/class scope and outside all descendant
//! function/class scopes, then delegates source currentness and candidate reconstruction to the
//! existing source-review owner.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::{PythonLexicalScopeIndexV1, PythonScopeV1, ScopeKindV1};
use aura_k27_astge_source_review::{
    admit_source_review, SourceReviewAdmissionV1, SourceReviewError,
};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NestedScopeSourceReviewAdmissionV1 {
    pub selected_scope: PythonScopeV1,
    pub source_review: SourceReviewAdmissionV1,
    pub pre_edit_scope_anchor_current: bool,
    pub higher_owner_authorization_required: bool,
    pub authorized_spans_confined_to_selected_scope: bool,
    pub descendant_scopes_protected: bool,
    pub duplicate_scope_name_selected_by_scope_id: bool,
    pub post_edit_scope_ast_currentness_proven: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NestedScopeReviewError {
    SelectedScopeMissing(u64),
    ModuleScopeCannotBeSelected,
    ScopeAstAnchorMissing(u64),
    ScopeSemanticHandleMissing(u64),
    ScopeRecordMismatch,
    AuthorizedSpanEscapesSelectedScope {
        start: u64,
        end: u64,
    },
    AuthorizedSpanIntersectsDescendantScope {
        start: u64,
        end: u64,
        descendant_scope_id: u64,
    },
    SourceReview(SourceReviewError),
}

impl Display for NestedScopeReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for NestedScopeReviewError {}

impl From<SourceReviewError> for NestedScopeReviewError {
    fn from(value: SourceReviewError) -> Self {
        Self::SourceReview(value)
    }
}

/// Admit an explicitly authorized candidate edit inside one exact current lexical scope.
///
/// The selected scope can only narrow higher-owner authorization. It cannot create an authorized
/// span, choose a runtime binding winner, approve semantic correctness, or make the post-edit AST
/// current. Descendant function/class scopes remain protected; editing one requires selecting that
/// descendant as the review scope in a separate admission.
#[allow(clippy::too_many_arguments)]
pub fn admit_nested_scope_source_review(
    scope_index: &PythonLexicalScopeIndexV1,
    selected_scope_id: u64,
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<NestedScopeSourceReviewAdmissionV1, NestedScopeReviewError> {
    let selected = scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == selected_scope_id)
        .ok_or(NestedScopeReviewError::SelectedScopeMissing(
            selected_scope_id,
        ))?;
    if selected.kind == ScopeKindV1::Module {
        return Err(NestedScopeReviewError::ModuleScopeCannotBeSelected);
    }
    let ast_node_id = selected
        .ast_node_id
        .ok_or(NestedScopeReviewError::ScopeAstAnchorMissing(
            selected_scope_id,
        ))?;
    let semantic_handle_digest = selected.semantic_handle_digest.ok_or(
        NestedScopeReviewError::ScopeSemanticHandleMissing(selected_scope_id),
    )?;

    if scope_index.file_id != selected.file_id
        || record.node_id != ast_node_id
        || record.file_id != selected.file_id
        || record.byte_start != selected.byte_start
        || record.byte_end != selected.byte_end
        || record.semantic_handle_digest != semantic_handle_digest
    {
        return Err(NestedScopeReviewError::ScopeRecordMismatch);
    }

    for span in authorized_spans {
        if !span_is_inside_selected_scope(span, selected) {
            return Err(NestedScopeReviewError::AuthorizedSpanEscapesSelectedScope {
                start: span.start,
                end: span.end,
            });
        }
        for descendant in scope_index
            .scopes
            .iter()
            .filter(|scope| is_descendant(scope_index, scope.scope_id, selected_scope_id))
        {
            if span_intersects_scope(span, descendant) {
                return Err(
                    NestedScopeReviewError::AuthorizedSpanIntersectsDescendantScope {
                        start: span.start,
                        end: span.end,
                        descendant_scope_id: descendant.scope_id,
                    },
                );
            }
        }
    }

    let source_review = admit_source_review(
        catalog,
        record,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;

    if source_review.node_id != ast_node_id
        || source_review.file_id != selected.file_id
        || source_review.byte_start != selected.byte_start
        || source_review.byte_end != selected.byte_end
        || source_review.semantic_handle_digest != semantic_handle_digest
    {
        return Err(NestedScopeReviewError::ScopeRecordMismatch);
    }

    let same_name_count = scope_index
        .scopes
        .iter()
        .filter(|scope| {
            scope.parent_scope_id == selected.parent_scope_id && scope.name == selected.name
        })
        .count();

    Ok(NestedScopeSourceReviewAdmissionV1 {
        selected_scope: selected.clone(),
        source_review,
        pre_edit_scope_anchor_current: true,
        higher_owner_authorization_required: true,
        authorized_spans_confined_to_selected_scope: true,
        descendant_scopes_protected: true,
        duplicate_scope_name_selected_by_scope_id: same_name_count > 1,
        post_edit_scope_ast_currentness_proven: false,
        runtime_name_resolution_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    })
}

fn span_is_inside_selected_scope(span: &AuthorizedSpanV1, selected: &PythonScopeV1) -> bool {
    let start = selected.byte_start as u64;
    let end = selected.byte_end as u64;
    if span.start > span.end {
        return false;
    }
    if span.start == span.end {
        start <= span.start && span.start < end
    } else {
        start <= span.start && span.end <= end
    }
}

fn span_intersects_scope(span: &AuthorizedSpanV1, scope: &PythonScopeV1) -> bool {
    let start = scope.byte_start as u64;
    let end = scope.byte_end as u64;
    if span.start == span.end {
        start <= span.start && span.start < end
    } else {
        span.start < end && start < span.end
    }
}

fn is_descendant(
    index: &PythonLexicalScopeIndexV1,
    candidate_scope_id: u64,
    ancestor_scope_id: u64,
) -> bool {
    let mut current = index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == candidate_scope_id)
        .and_then(|scope| scope.parent_scope_id);
    while let Some(parent) = current {
        if parent == ancestor_scope_id {
            return true;
        }
        current = index
            .scopes
            .iter()
            .find(|scope| scope.scope_id == parent)
            .and_then(|scope| scope.parent_scope_id);
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    const FIXTURE: &str = "def outer(flag):\n    def inner():\n        return 1\n    if flag:\n        def conditional():\n            return flag\n    def inner():\n        return 2\n    return inner\n\ndef sibling():\n    return 3\n";

    struct Setup {
        root: PathBuf,
        source: String,
        index: PythonLexicalScopeIndexV1,
        records: Vec<NodeIndexRecordV1>,
        catalog: AdmittedSourceCatalogV1,
    }

    fn setup(label: &str, file_id: u32) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-scope-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        let source = FIXTURE.to_owned();
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let handles: HashMap<u64, [u8; 32]> = graph
            .nodes
            .iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&file_id.to_le_bytes());
                (node.node_id, digest)
            })
            .collect();
        let index = index_python_nested_scopes(&source, file_id, &handles).unwrap();
        let encoded = encode_ast_to_splane(&graph, &handles, 0, 51, [0x91; 32]).unwrap();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                file_id,
                "src/module.py",
                21,
                source.as_bytes(),
            )],
        )
        .unwrap();
        Setup {
            root,
            source,
            index,
            records: encoded.records,
            catalog,
        }
    }

    fn second_inner(index: &PythonLexicalScopeIndexV1) -> &PythonScopeV1 {
        index
            .scopes
            .iter()
            .filter(|scope| scope.name == "inner")
            .nth(1)
            .unwrap()
    }

    fn record_for<'a>(setup: &'a Setup, scope: &PythonScopeV1) -> &'a NodeIndexRecordV1 {
        let node_id = scope.ast_node_id.unwrap();
        setup
            .records
            .iter()
            .find(|record| record.node_id == node_id)
            .unwrap()
    }

    fn replacement(source: &str, old: &str, new: &[u8]) -> (AuthorizedSpanV1, ReplacementV1) {
        let start = source.find(old).unwrap() as u64;
        let end = start + old.len() as u64;
        (
            AuthorizedSpanV1 { start, end },
            ReplacementV1 {
                start,
                end,
                replacement: new.to_vec(),
            },
        )
    }

    #[test]
    fn duplicate_nested_scope_is_selected_by_exact_scope_and_current_ast_anchor() {
        let setup = setup("positive", 101);
        let selected = second_inner(&setup.index);
        let record = record_for(&setup, selected);
        let (span, edit) = replacement(&setup.source, "return 2", b"return 20");
        let candidate = setup.source.replacen("return 2", "return 20", 1);

        let admission = admit_nested_scope_source_review(
            &setup.index,
            selected.scope_id,
            &setup.catalog,
            record,
            setup.source.as_bytes(),
            candidate.as_bytes(),
            &[span],
            &[edit],
        )
        .unwrap();

        assert_eq!(admission.selected_scope.scope_id, selected.scope_id);
        assert_eq!(
            admission.source_review.node_id,
            selected.ast_node_id.unwrap()
        );
        assert!(admission.pre_edit_scope_anchor_current);
        assert!(admission.higher_owner_authorization_required);
        assert!(admission.authorized_spans_confined_to_selected_scope);
        assert!(admission.descendant_scopes_protected);
        assert!(admission.duplicate_scope_name_selected_by_scope_id);
        assert!(!admission.post_edit_scope_ast_currentness_proven);
        assert!(!admission.runtime_name_resolution_proven);
        assert!(!admission.semantic_patch_correctness_proven);
        assert!(!admission.b_minus_approved);
        assert!(!admission.commit_authorized);
        assert!(!admission.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn sibling_duplicate_scope_cannot_be_edited_through_selected_scope() {
        let setup = setup("sibling", 102);
        let selected = second_inner(&setup.index);
        let record = record_for(&setup, selected);
        let (span, edit) = replacement(&setup.source, "return 1", b"return 9");
        let candidate = setup.source.replacen("return 1", "return 9", 1);
        let error = admit_nested_scope_source_review(
            &setup.index,
            selected.scope_id,
            &setup.catalog,
            record,
            setup.source.as_bytes(),
            candidate.as_bytes(),
            &[span],
            &[edit],
        )
        .unwrap_err();
        assert!(matches!(
            error,
            NestedScopeReviewError::AuthorizedSpanEscapesSelectedScope { .. }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn selecting_parent_scope_does_not_authorize_descendant_scope_edits() {
        let setup = setup("descendant", 103);
        let outer = setup
            .index
            .scopes
            .iter()
            .find(|scope| scope.name == "outer")
            .unwrap();
        let record = record_for(&setup, outer);
        let (span, edit) = replacement(&setup.source, "return 2", b"return 8");
        let candidate = setup.source.replacen("return 2", "return 8", 1);
        let error = admit_nested_scope_source_review(
            &setup.index,
            outer.scope_id,
            &setup.catalog,
            record,
            setup.source.as_bytes(),
            candidate.as_bytes(),
            &[span],
            &[edit],
        )
        .unwrap_err();
        assert!(matches!(
            error,
            NestedScopeReviewError::AuthorizedSpanIntersectsDescendantScope { .. }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn enclosing_scope_authorization_cannot_widen_nested_selection() {
        let setup = setup("enclosing", 104);
        let selected = second_inner(&setup.index);
        let record = record_for(&setup, selected);
        let (span, edit) = replacement(&setup.source, "def outer(flag):", b"def outer(flag=True):");
        let candidate = setup
            .source
            .replacen("def outer(flag):", "def outer(flag=True):", 1);
        let error = admit_nested_scope_source_review(
            &setup.index,
            selected.scope_id,
            &setup.catalog,
            record,
            setup.source.as_bytes(),
            candidate.as_bytes(),
            &[span],
            &[edit],
        )
        .unwrap_err();
        assert!(matches!(
            error,
            NestedScopeReviewError::AuthorizedSpanEscapesSelectedScope { .. }
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn sibling_record_cannot_impersonate_selected_scope() {
        let setup = setup("record", 105);
        let inners: Vec<_> = setup
            .index
            .scopes
            .iter()
            .filter(|scope| scope.name == "inner")
            .collect();
        let selected = inners[1];
        let wrong_record = record_for(&setup, inners[0]);
        let error = admit_nested_scope_source_review(
            &setup.index,
            selected.scope_id,
            &setup.catalog,
            wrong_record,
            setup.source.as_bytes(),
            setup.source.as_bytes(),
            &[],
            &[],
        )
        .unwrap_err();
        assert_eq!(error, NestedScopeReviewError::ScopeRecordMismatch);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn module_scope_cannot_be_converted_into_mutation_authority() {
        let setup = setup("module", 106);
        let record = &setup.records[0];
        let error = admit_nested_scope_source_review(
            &setup.index,
            0,
            &setup.catalog,
            record,
            setup.source.as_bytes(),
            setup.source.as_bytes(),
            &[],
            &[],
        )
        .unwrap_err();
        assert_eq!(error, NestedScopeReviewError::ModuleScopeCannotBeSelected);
        fs::remove_dir_all(setup.root).unwrap();
    }
}
