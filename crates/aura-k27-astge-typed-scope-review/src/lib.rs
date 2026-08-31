#![forbid(unsafe_code)]

//! Typed SourceGeneration boundary for lexical-owner-aware current-source review.
//!
//! PR500 remains the owner of current source + lexical owner-scope admission. PR499 remains the
//! owner of generation-domain typing. This crate composes them without resolving identifier uses,
//! proving semantic correctness, approving B-minus review, or granting commit/effect authority.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scope_review::{
    admit_scope_aware_source_review, ScopeAwareReviewError, ScopeAwareSourceReviewAdmissionV1,
};
use aura_k27_astge_typed_source_review::{
    require_source_review_generation, TypedSourceReviewErrorV1,
};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedScopeAwareSourceReviewAdmissionV1 {
    pub owner_admission: ScopeAwareSourceReviewAdmissionV1,
    pub source_generation: SourceGenerationV1,
    pub source_generation_coordinate: GenerationCoordinateV1,
    pub typed_source_generation_bound: bool,
    pub lexical_owner_scope_bound: bool,
    pub identifier_use_resolution_proven: bool,
    pub runtime_binding_winner_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub execution_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum TypedScopeAwareReviewErrorV1 {
    Owner(ScopeAwareReviewError),
    SourceGeneration(TypedSourceReviewErrorV1),
}

impl Display for TypedScopeAwareReviewErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for TypedScopeAwareReviewErrorV1 {}

impl From<ScopeAwareReviewError> for TypedScopeAwareReviewErrorV1 {
    fn from(value: ScopeAwareReviewError) -> Self {
        Self::Owner(value)
    }
}

impl From<TypedSourceReviewErrorV1> for TypedScopeAwareReviewErrorV1 {
    fn from(value: TypedSourceReviewErrorV1) -> Self {
        Self::SourceGeneration(value)
    }
}

/// Bind lexical-owner-aware review to the Source generation axis.
///
/// A placement generation cannot inhabit the source-generation parameter even when its numeric
/// value equals the current source generation.
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::PlacementGenerationV1;
/// use aura_k27_astge_typed_scope_review::admit_typed_scope_aware_source_review;
/// # fn demo(catalog: &aura_k27_astge_materialize::AdmittedSourceCatalogV1,
/// #         record: &aura_k27_astge::NodeIndexRecordV1,
/// #         handles: &std::collections::HashMap<u64, [u8; 32]>) {
/// let placement = PlacementGenerationV1::new(12);
/// let _ = admit_typed_scope_aware_source_review(
///     catalog, record, placement, b"", &[], &[], handles, 0
/// );
/// # }
/// ```
///
/// A graph-serving generation is equally non-substitutable.
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::GraphServingGenerationV1;
/// use aura_k27_astge_typed_scope_review::admit_typed_scope_aware_source_review;
/// # fn demo(catalog: &aura_k27_astge_materialize::AdmittedSourceCatalogV1,
/// #         record: &aura_k27_astge::NodeIndexRecordV1,
/// #         handles: &std::collections::HashMap<u64, [u8; 32]>) {
/// let graph = GraphServingGenerationV1::new(12);
/// let _ = admit_typed_scope_aware_source_review(
///     catalog, record, graph, b"", &[], &[], handles, 0
/// );
/// # }
/// ```
#[allow(clippy::too_many_arguments)]
pub fn admit_typed_scope_aware_source_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    expected_source_generation: SourceGenerationV1,
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    requested_owner_scope_id: u64,
) -> Result<TypedScopeAwareSourceReviewAdmissionV1, TypedScopeAwareReviewErrorV1> {
    let owner_admission = admit_scope_aware_source_review(
        catalog,
        record,
        candidate_source,
        authorized_spans,
        replacements,
        semantic_handles,
        requested_owner_scope_id,
    )?;
    let source_generation = require_source_review_generation(
        expected_source_generation,
        owner_admission.source_review.source_generation,
    )?;

    Ok(TypedScopeAwareSourceReviewAdmissionV1 {
        source_generation_coordinate: source_generation.coordinate(),
        source_generation,
        typed_source_generation_bound: true,
        lexical_owner_scope_bound: owner_admission.lexical_owner_scope_bound,
        identifier_use_resolution_proven: false,
        runtime_binding_winner_proven: false,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        execution_authorized: false,
        external_effect_authorized: false,
        owner_admission,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_generation_domain::{
        GenerationDomainV1, GraphServingGenerationV1, PlacementGenerationV1,
    };
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_scopes::index_python_nested_scopes;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    struct State {
        root: PathBuf,
        source: String,
        handles: HashMap<u64, [u8; 32]>,
        record: NodeIndexRecordV1,
        owner_scope_id: u64,
        edit_start: usize,
    }

    fn state(label: &str) -> State {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-typed-scope-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        let source = String::from(
            "def target():\n    return 1\n\ndef outer():\n    def target():\n        return 2\n    def target():\n        return 3\n    return target\n",
        );
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let file_id = 71;
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
        let scopes = index_python_nested_scopes(&source, file_id, &handles).unwrap();
        let selected = scopes
            .bindings
            .iter()
            .filter(|binding| binding.name == "target" && binding.owner_scope_id != 0)
            .nth(1)
            .unwrap();
        let encoded = encode_ast_to_splane(&graph, &handles, 0, 41, [0x71; 32]).unwrap();
        let record = encoded
            .records
            .iter()
            .find(|record| record.node_id == selected.ast_node_id)
            .unwrap()
            .clone();
        let edit_start = source.rfind("return 3").unwrap() + "return ".len();
        State {
            root,
            source,
            handles,
            record,
            owner_scope_id: selected.owner_scope_id,
            edit_start,
        }
    }

    fn catalog(state: &State, generation: u64) -> AdmittedSourceCatalogV1 {
        AdmittedSourceCatalogV1::admit(
            &state.root,
            [SourceLocatorV1::bind(
                state.record.file_id,
                "src/module.py",
                generation,
                state.source.as_bytes(),
            )],
        )
        .unwrap()
    }

    fn edit(state: &State) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = state.source.as_bytes().to_vec();
        candidate[state.edit_start] = b'4';
        let start = state.edit_start as u64;
        (
            candidate,
            vec![AuthorizedSpanV1 {
                start,
                end: start + 1,
            }],
            vec![ReplacementV1 {
                start,
                end: start + 1,
                replacement: b"4".to_vec(),
            }],
        )
    }

    #[test]
    fn exact_scope_aware_review_binds_typed_source_generation() {
        let state = state("positive");
        let generation = 23;
        let catalog = catalog(&state, generation);
        let (candidate, spans, replacements) = edit(&state);
        let receipt = admit_typed_scope_aware_source_review(
            &catalog,
            &state.record,
            SourceGenerationV1::new(generation),
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.owner_scope_id,
        )
        .unwrap();
        assert_eq!(receipt.source_generation.value(), generation);
        assert_eq!(
            receipt.source_generation_coordinate.domain,
            GenerationDomainV1::Source
        );
        assert_eq!(receipt.owner_admission.owner_scope_id, state.owner_scope_id);
        assert_eq!(receipt.owner_admission.definition_name, "target");
        assert_eq!(receipt.owner_admission.duplicate_same_owner_name_count, 2);
        assert!(receipt.typed_source_generation_bound);
        assert!(receipt.lexical_owner_scope_bound);
        assert!(!receipt.identifier_use_resolution_proven);
        assert!(!receipt.runtime_binding_winner_proven);
        assert!(!receipt.semantic_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.execution_authorized);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn wrong_source_generation_fails_after_owner_currentness_and_scope_binding() {
        let state = state("wrong-generation");
        let catalog = catalog(&state, 23);
        let (candidate, spans, replacements) = edit(&state);
        let error = admit_typed_scope_aware_source_review(
            &catalog,
            &state.record,
            SourceGenerationV1::new(24),
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.owner_scope_id,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            TypedScopeAwareReviewErrorV1::SourceGeneration(
                TypedSourceReviewErrorV1::SourceGenerationMismatch {
                    expected: 24,
                    observed: 23
                }
            )
        ));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn lexical_owner_mismatch_remains_fail_closed_before_generation_promotion() {
        let state = state("wrong-owner");
        let catalog = catalog(&state, 23);
        let (candidate, spans, replacements) = edit(&state);
        let error = admit_typed_scope_aware_source_review(
            &catalog,
            &state.record,
            SourceGenerationV1::new(23),
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            0,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            TypedScopeAwareReviewErrorV1::Owner(ScopeAwareReviewError::OwnerScopeMismatch { .. })
        ));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn equal_numeric_cross_axis_coordinates_remain_distinct_from_source() {
        let source = SourceGenerationV1::new(23).coordinate();
        let placement = PlacementGenerationV1::new(23).coordinate();
        let graph = GraphServingGenerationV1::new(23).coordinate();
        assert_ne!(source, placement);
        assert_ne!(source, graph);
        assert_eq!(source.value, placement.value);
    }
}
