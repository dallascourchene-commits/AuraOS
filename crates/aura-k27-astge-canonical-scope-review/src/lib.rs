#![forbid(unsafe_code)]

//! Canonical convergence of two independently green scope-review contracts.
//!
//! A function/class definition is declared in one lexical owner scope and creates a distinct
//! target scope for its body. PR500 proves exact definition -> owner/target binding. PR503 proves
//! that edits inside a selected nested target scope remain confined by higher-owner authorization
//! and preserve typed SourceGeneration. This membrane requires both views to identify the same
//! definition edge without treating owner and target scopes as interchangeable.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::{PythonLexicalScopeIndexV1, ScopeKindV1};
use aura_k27_astge_typed_nested_scope_review::{
    admit_typed_nested_scope_source_review, TypedNestedScopeReviewErrorV1,
    TypedNestedScopeSourceReviewAdmissionV1,
};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CanonicalDefinitionScopeReviewAdmissionV1 {
    pub typed_nested_review: TypedNestedScopeSourceReviewAdmissionV1,
    pub definition_name: String,
    pub definition_owner_scope_id: u64,
    pub definition_owner_scope_kind: ScopeKindV1,
    pub definition_target_scope_id: u64,
    pub definition_target_scope_kind: ScopeKindV1,
    pub duplicate_same_owner_name_count: usize,
    pub selected_review_scope_is_binding_target: bool,
    pub binding_owner_is_selected_parent: bool,
    pub source_generation: SourceGenerationV1,
    pub source_generation_coordinate: GenerationCoordinateV1,
    pub post_edit_scope_ast_currentness_proven: bool,
    pub identifier_use_resolution_proven: bool,
    pub runtime_binding_winner_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub human_authority: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum CanonicalScopeReviewErrorV1 {
    SelectedScopeMissing(u64),
    SelectedScopeHasNoParent(u64),
    DefinitionBindingMissing { selected_scope_id: u64, node_id: u64 },
    DefinitionBindingAmbiguous { selected_scope_id: u64, matches: usize },
    BindingOwnerParentMismatch { binding_owner_scope_id: u64, selected_parent_scope_id: u64 },
    OwnerScopeMissing(u64),
    TypedNestedReview(TypedNestedScopeReviewErrorV1),
}

impl Display for CanonicalScopeReviewErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for CanonicalScopeReviewErrorV1 {}

impl From<TypedNestedScopeReviewErrorV1> for CanonicalScopeReviewErrorV1 {
    fn from(value: TypedNestedScopeReviewErrorV1) -> Self {
        Self::TypedNestedReview(value)
    }
}

/// Bind an exact function/class definition edge to the nested scope whose body is reviewed.
///
/// `selected_scope_id` is the definition's **target** scope, not its lexical owner. The exact
/// binding that targets it must carry the same persisted AST node/file/span/semantic-handle
/// witness, and its owner must equal the selected scope's parent. Only then is PR503's typed nested
/// review executed.
///
/// A Placement generation cannot inhabit the Source-generation slot:
/// ```compile_fail
/// use aura_k27_astge_canonical_scope_review::admit_canonical_definition_scope_review;
/// use aura_k27_astge_generation_domain::PlacementGenerationV1;
/// let placement = PlacementGenerationV1::new(12);
/// let _ = admit_canonical_definition_scope_review(
///     todo!(), 1, todo!(), todo!(), placement, b"", b"", &[], &[]
/// );
/// ```
#[allow(clippy::too_many_arguments)]
pub fn admit_canonical_definition_scope_review(
    scope_index: &PythonLexicalScopeIndexV1,
    selected_scope_id: u64,
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    expected_source_generation: SourceGenerationV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<CanonicalDefinitionScopeReviewAdmissionV1, CanonicalScopeReviewErrorV1> {
    let selected = scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == selected_scope_id)
        .ok_or(CanonicalScopeReviewErrorV1::SelectedScopeMissing(selected_scope_id))?;
    let selected_parent_scope_id = selected
        .parent_scope_id
        .ok_or(CanonicalScopeReviewErrorV1::SelectedScopeHasNoParent(selected_scope_id))?;

    let matches: Vec<_> = scope_index
        .bindings
        .iter()
        .filter(|binding| {
            binding.target_scope_id == selected_scope_id
                && binding.ast_node_id == record.node_id
                && binding.file_id == record.file_id
                && binding.byte_start == record.byte_start
                && binding.byte_end == record.byte_end
                && binding.semantic_handle_digest == record.semantic_handle_digest
        })
        .collect();
    let binding = match matches.as_slice() {
        [] => {
            return Err(CanonicalScopeReviewErrorV1::DefinitionBindingMissing {
                selected_scope_id,
                node_id: record.node_id,
            })
        }
        [binding] => *binding,
        _ => {
            return Err(CanonicalScopeReviewErrorV1::DefinitionBindingAmbiguous {
                selected_scope_id,
                matches: matches.len(),
            })
        }
    };

    if binding.owner_scope_id != selected_parent_scope_id {
        return Err(CanonicalScopeReviewErrorV1::BindingOwnerParentMismatch {
            binding_owner_scope_id: binding.owner_scope_id,
            selected_parent_scope_id,
        });
    }
    let owner = scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == binding.owner_scope_id)
        .ok_or(CanonicalScopeReviewErrorV1::OwnerScopeMissing(binding.owner_scope_id))?;

    let typed_nested_review = admit_typed_nested_scope_source_review(
        scope_index,
        selected_scope_id,
        catalog,
        record,
        expected_source_generation,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;

    let duplicate_same_owner_name_count = scope_index
        .bindings
        .iter()
        .filter(|candidate| {
            candidate.owner_scope_id == binding.owner_scope_id && candidate.name == binding.name
        })
        .count();
    let source_generation = typed_nested_review.source_generation;

    Ok(CanonicalDefinitionScopeReviewAdmissionV1 {
        definition_name: binding.name.clone(),
        definition_owner_scope_id: owner.scope_id,
        definition_owner_scope_kind: owner.kind,
        definition_target_scope_id: selected.scope_id,
        definition_target_scope_kind: selected.kind,
        duplicate_same_owner_name_count,
        selected_review_scope_is_binding_target: true,
        binding_owner_is_selected_parent: true,
        source_generation_coordinate: source_generation.coordinate(),
        source_generation,
        post_edit_scope_ast_currentness_proven: false,
        identifier_use_resolution_proven: false,
        runtime_binding_winner_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        human_authority: false,
        external_effect_authorized: false,
        typed_nested_review,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_generation_domain::{GenerationDomainV1, PlacementGenerationV1};
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    const SOURCE: &str = "def outer():\n    def inner():\n        return 1\n    def inner():\n        return 2\n    return inner\n";

    struct Setup {
        root: PathBuf,
        index: PythonLexicalScopeIndexV1,
        records: Vec<NodeIndexRecordV1>,
        catalog: AdmittedSourceCatalogV1,
        selected_scope_id: u64,
        selected_record: NodeIndexRecordV1,
        first_inner_record: NodeIndexRecordV1,
        generation: u64,
        edit_start: usize,
    }

    fn handles(source: &str, file_id: u32) -> HashMap<u64, [u8; 32]> {
        let graph = parse_python_named_ast(source, file_id).unwrap();
        graph
            .nodes
            .iter()
            .map(|node| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&node.node_id.to_le_bytes());
                digest[8..12].copy_from_slice(&file_id.to_le_bytes());
                (node.node_id, digest)
            })
            .collect()
    }

    fn setup(label: &str) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-canonical-scope-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();
        let file_id = 77;
        let generation = 31;
        let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
        let supplied = handles(SOURCE, file_id);
        let index = index_python_nested_scopes(SOURCE, file_id, &supplied).unwrap();
        let inners: Vec<_> = index
            .scopes
            .iter()
            .filter(|scope| scope.name == "inner")
            .collect();
        assert_eq!(inners.len(), 2);
        let selected_scope_id = inners[1].scope_id;
        let encoded = encode_ast_to_splane(&graph, &supplied, 0, 41, [0xA1; 32]).unwrap();
        let selected_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == inners[1].ast_node_id.unwrap())
            .unwrap()
            .clone();
        let first_inner_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == inners[0].ast_node_id.unwrap())
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
        let edit_start = SOURCE.rfind("return 2").unwrap() + "return ".len();
        Setup {
            root,
            index,
            records: encoded.records,
            catalog,
            selected_scope_id,
            selected_record,
            first_inner_record,
            generation,
            edit_start,
        }
    }

    fn edit(setup: &Setup) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = SOURCE.as_bytes().to_vec();
        candidate[setup.edit_start] = b'3';
        let start = setup.edit_start as u64;
        (
            candidate,
            vec![AuthorizedSpanV1 { start, end: start + 1 }],
            vec![ReplacementV1 {
                start,
                end: start + 1,
                replacement: b"3".to_vec(),
            }],
        )
    }

    #[test]
    fn exact_definition_owner_to_target_edge_selects_nested_review_scope() {
        let setup = setup("positive");
        let (candidate, spans, replacements) = edit(&setup);
        let receipt = admit_canonical_definition_scope_review(
            &setup.index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.selected_record,
            SourceGenerationV1::new(setup.generation),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap();

        assert_eq!(receipt.definition_name, "inner");
        assert_eq!(receipt.definition_target_scope_id, setup.selected_scope_id);
        assert_ne!(receipt.definition_owner_scope_id, receipt.definition_target_scope_id);
        assert_eq!(
            setup.index.scopes.iter().find(|s| s.scope_id == setup.selected_scope_id).unwrap().parent_scope_id,
            Some(receipt.definition_owner_scope_id)
        );
        assert_eq!(receipt.duplicate_same_owner_name_count, 2);
        assert!(receipt.selected_review_scope_is_binding_target);
        assert!(receipt.binding_owner_is_selected_parent);
        assert!(receipt.typed_nested_review.lexical_scope_restriction_proven);
        assert_eq!(receipt.source_generation.value(), setup.generation);
        assert_eq!(receipt.source_generation_coordinate.domain, GenerationDomainV1::Source);
        assert!(!receipt.post_edit_scope_ast_currentness_proven);
        assert!(!receipt.identifier_use_resolution_proven);
        assert!(!receipt.runtime_binding_winner_proven);
        assert!(!receipt.call_graph_proven);
        assert!(!receipt.semantic_patch_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.human_authority);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn definition_owner_scope_cannot_be_substituted_for_target_review_scope() {
        let setup = setup("owner-not-target");
        let selected = setup.index.scopes.iter().find(|s| s.scope_id == setup.selected_scope_id).unwrap();
        let owner_scope_id = selected.parent_scope_id.unwrap();
        let (candidate, spans, replacements) = edit(&setup);
        let error = admit_canonical_definition_scope_review(
            &setup.index,
            owner_scope_id,
            &setup.catalog,
            &setup.selected_record,
            SourceGenerationV1::new(setup.generation),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap_err();
        assert!(matches!(error, CanonicalScopeReviewErrorV1::DefinitionBindingMissing { .. }));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn same_name_sibling_definition_cannot_impersonate_selected_target_scope() {
        let setup = setup("sibling");
        let (candidate, spans, replacements) = edit(&setup);
        let error = admit_canonical_definition_scope_review(
            &setup.index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.first_inner_record,
            SourceGenerationV1::new(setup.generation),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap_err();
        assert!(matches!(error, CanonicalScopeReviewErrorV1::DefinitionBindingMissing { .. }));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn wrong_typed_source_generation_is_rejected_after_exact_owner_target_binding() {
        let setup = setup("generation");
        let (candidate, spans, replacements) = edit(&setup);
        let error = admit_canonical_definition_scope_review(
            &setup.index,
            setup.selected_scope_id,
            &setup.catalog,
            &setup.selected_record,
            SourceGenerationV1::new(setup.generation + 1),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap_err();
        assert!(matches!(error, CanonicalScopeReviewErrorV1::TypedNestedReview(_)));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn equal_numeric_source_and_placement_values_remain_different_coordinates() {
        let source = SourceGenerationV1::new(31).coordinate();
        let placement = PlacementGenerationV1::new(31).coordinate();
        assert_eq!(source.value, placement.value);
        assert_ne!(source, placement);
    }
}
