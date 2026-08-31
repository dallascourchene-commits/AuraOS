#![forbid(unsafe_code)]

//! Preserve PR499's typed SourceGeneration invariant across PR498 nested-scope review.
//!
//! PR498 remains the sole owner of lexical-scope restriction and source-review execution. This
//! membrane invokes that owner exactly once, then reuses PR499's public generation binder on the
//! already-admitted raw source generation. It does not replay materialization or mutation checks.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scope_review::{
    admit_nested_scope_source_review, NestedScopeReviewError, NestedScopeSourceReviewAdmissionV1,
};
use aura_k27_astge_scopes::PythonLexicalScopeIndexV1;
use aura_k27_astge_typed_source_review::{
    require_source_review_generation, TypedSourceReviewErrorV1,
};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedNestedScopeSourceReviewAdmissionV1 {
    pub owner_admission: NestedScopeSourceReviewAdmissionV1,
    pub source_generation: SourceGenerationV1,
    pub source_generation_coordinate: GenerationCoordinateV1,
    pub lexical_scope_restriction_proven: bool,
    pub post_edit_scope_ast_currentness_proven: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum TypedNestedScopeReviewErrorV1 {
    Owner(NestedScopeReviewError),
    SourceGeneration(TypedSourceReviewErrorV1),
}

impl Display for TypedNestedScopeReviewErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for TypedNestedScopeReviewErrorV1 {}

impl From<NestedScopeReviewError> for TypedNestedScopeReviewErrorV1 {
    fn from(value: NestedScopeReviewError) -> Self {
        Self::Owner(value)
    }
}

impl From<TypedSourceReviewErrorV1> for TypedNestedScopeReviewErrorV1 {
    fn from(value: TypedSourceReviewErrorV1) -> Self {
        Self::SourceGeneration(value)
    }
}

/// Admit one exact current nested lexical scope while retaining SourceGeneration type identity.
///
/// A PlacementGeneration cannot inhabit the source-generation slot even when the raw value is the
/// same:
/// ```compile_fail
/// use aura_k27_astge_generation_domain::PlacementGenerationV1;
/// use aura_k27_astge_typed_nested_scope_review::admit_typed_nested_scope_source_review;
/// let placement = PlacementGenerationV1::new(12);
/// let _ = admit_typed_nested_scope_source_review(
///     todo!(), 1, todo!(), todo!(), placement, b"", b"", &[], &[]
/// );
/// ```
#[allow(clippy::too_many_arguments)]
pub fn admit_typed_nested_scope_source_review(
    scope_index: &PythonLexicalScopeIndexV1,
    selected_scope_id: u64,
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    expected_source_generation: SourceGenerationV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<TypedNestedScopeSourceReviewAdmissionV1, TypedNestedScopeReviewErrorV1> {
    let owner_admission = admit_nested_scope_source_review(
        scope_index,
        selected_scope_id,
        catalog,
        record,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;

    let source_generation = require_source_review_generation(
        expected_source_generation,
        owner_admission.source_review.source_generation,
    )?;

    Ok(TypedNestedScopeSourceReviewAdmissionV1 {
        source_generation_coordinate: source_generation.coordinate(),
        source_generation,
        lexical_scope_restriction_proven: owner_admission
            .authorized_spans_confined_to_selected_scope
            && owner_admission.descendant_scopes_protected,
        post_edit_scope_ast_currentness_proven: false,
        runtime_name_resolution_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
        owner_admission,
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
    const SOURCE: &str = "def outer():\n    def inner():\n        return 1\n    return inner\n";

    struct Setup {
        root: PathBuf,
        index: PythonLexicalScopeIndexV1,
        record: NodeIndexRecordV1,
        catalog: AdmittedSourceCatalogV1,
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

    fn setup(label: &str, generation: u64) -> Setup {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-typed-nested-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();

        let file_id = 77;
        let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
        let supplied = handles(SOURCE, file_id);
        let index = index_python_nested_scopes(SOURCE, file_id, &supplied).unwrap();
        let selected = index
            .scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let encoded = encode_ast_to_splane(&graph, &supplied, 0, 41, [0x81; 32]).unwrap();
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
            index,
            record,
            catalog,
            edit_start,
        }
    }

    fn edit(setup: &Setup) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = SOURCE.as_bytes().to_vec();
        candidate[setup.edit_start] = b'2';
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
                replacement: b"2".to_vec(),
            }],
        )
    }

    #[test]
    fn typed_source_generation_survives_exact_nested_scope_restriction() {
        let generation = 12;
        let setup = setup("positive", generation);
        let selected_scope = setup
            .index
            .scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let (candidate, spans, replacements) = edit(&setup);
        let receipt = admit_typed_nested_scope_source_review(
            &setup.index,
            selected_scope.scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(generation),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap();

        assert_eq!(receipt.source_generation.value(), generation);
        assert_eq!(
            receipt.source_generation_coordinate.domain,
            GenerationDomainV1::Source
        );
        assert!(receipt.owner_admission.pre_edit_scope_anchor_current);
        assert!(receipt.lexical_scope_restriction_proven);
        assert!(!receipt.post_edit_scope_ast_currentness_proven);
        assert!(!receipt.runtime_name_resolution_proven);
        assert!(!receipt.semantic_patch_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn wrong_source_generation_fails_after_scope_and_source_owner_admission() {
        let setup = setup("wrong-generation", 12);
        let selected_scope = setup
            .index
            .scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let (candidate, spans, replacements) = edit(&setup);
        let error = admit_typed_nested_scope_source_review(
            &setup.index,
            selected_scope.scope_id,
            &setup.catalog,
            &setup.record,
            SourceGenerationV1::new(13),
            SOURCE.as_bytes(),
            &candidate,
            &spans,
            &replacements,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            TypedNestedScopeReviewErrorV1::SourceGeneration(
                TypedSourceReviewErrorV1::SourceGenerationMismatch {
                    expected: 13,
                    observed: 12
                }
            )
        ));
        fs::remove_dir_all(setup.root).unwrap();
    }

    #[test]
    fn equal_numeric_source_and_placement_remain_domain_distinct() {
        let source = SourceGenerationV1::new(12).coordinate();
        let placement = PlacementGenerationV1::new(12).coordinate();
        assert_eq!(source.value, placement.value);
        assert_ne!(source, placement);
    }
}
