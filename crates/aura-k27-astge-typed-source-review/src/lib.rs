#![forbid(unsafe_code)]

//! Compile-time SourceGeneration binding for the existing ASTGE source-review owner.
//!
//! This crate does not reimplement source materialization, byte-scope verification, or review
//! admission. It composes the exact PR494 owner with PR490's typed generation-domain invariant.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_generation_domain::{GenerationCoordinateV1, SourceGenerationV1};
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_source_review::{
    admit_source_review, SourceReviewAdmissionV1, SourceReviewError,
};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedSourceReviewAdmissionV1 {
    pub owner_admission: SourceReviewAdmissionV1,
    pub source_generation: SourceGenerationV1,
    pub source_generation_coordinate: GenerationCoordinateV1,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TypedSourceReviewErrorV1 {
    Owner(SourceReviewError),
    SourceGenerationMismatch { expected: u64, observed: u64 },
}

impl Display for TypedSourceReviewErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for TypedSourceReviewErrorV1 {}

impl From<SourceReviewError> for TypedSourceReviewErrorV1 {
    fn from(value: SourceReviewError) -> Self {
        Self::Owner(value)
    }
}

/// Require a source-axis generation. A snapshot, placement, or graph-serving generation cannot
/// inhabit this parameter even when its numeric value is identical.
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::PlacementGenerationV1;
/// use aura_k27_astge_typed_source_review::require_source_review_generation;
/// let placement = PlacementGenerationV1::new(12);
/// require_source_review_generation(placement, 12).unwrap();
/// ```
///
/// ```compile_fail
/// use aura_k27_astge_generation_domain::GraphServingGenerationV1;
/// use aura_k27_astge_typed_source_review::require_source_review_generation;
/// let graph = GraphServingGenerationV1::new(12);
/// require_source_review_generation(graph, 12).unwrap();
/// ```
pub fn require_source_review_generation(
    expected: SourceGenerationV1,
    observed_raw: u64,
) -> Result<SourceGenerationV1, TypedSourceReviewErrorV1> {
    if expected.value() != observed_raw {
        return Err(TypedSourceReviewErrorV1::SourceGenerationMismatch {
            expected: expected.value(),
            observed: observed_raw,
        });
    }
    Ok(SourceGenerationV1::new(observed_raw))
}

/// Replay the canonical source-review owner and bind its admitted generation to the Source axis.
///
/// The caller supplies a typed source-generation expectation. The underlying owner still resolves
/// the current source through its admitted catalog and performs exact materialization/scope checks.
/// No generation type is allowed to substitute for those owner checks.
pub fn admit_typed_source_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    expected_source_generation: SourceGenerationV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<TypedSourceReviewAdmissionV1, TypedSourceReviewErrorV1> {
    let owner_admission = admit_source_review(
        catalog,
        record,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;
    let source_generation = require_source_review_generation(
        expected_source_generation,
        owner_admission.source_generation,
    )?;

    Ok(TypedSourceReviewAdmissionV1 {
        source_generation_coordinate: source_generation.coordinate(),
        source_generation,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
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
    use aura_k27_astge_symbols::index_python_module_symbols;
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-typed-source-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
    }

    fn fixture() -> String {
        "def target(x):\n    return x + 1\n\ndef target(y):\n    return y * 2\n".to_owned()
    }

    fn handles(node_count: usize) -> HashMap<u64, [u8; 32]> {
        (0..node_count)
            .map(|id| {
                let mut digest = [0u8; 32];
                digest[..8].copy_from_slice(&(id as u64).to_le_bytes());
                (id as u64, digest)
            })
            .collect()
    }

    fn replacement(start: u64, end: u64, value: &[u8]) -> ReplacementV1 {
        ReplacementV1 {
            start,
            end,
            replacement: value.to_vec(),
        }
    }

    #[test]
    fn source_generation_roundtrip_preserves_owner_review_and_authority_ceiling() {
        let root = temp_root("positive");
        let source = fixture();
        let file_id = 91;
        let generation = 12;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();

        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let supplied = handles(graph.nodes.len());
        let symbols = index_python_module_symbols(&source, file_id, &supplied).unwrap();
        let selected = symbols
            .symbols
            .iter()
            .filter(|symbol| symbol.name == "target")
            .nth(1)
            .unwrap();
        let encoded = encode_ast_to_splane(&graph, &supplied, 0, 41, [0x91; 32]).unwrap();
        let record = encoded
            .records
            .iter()
            .find(|record| record.node_id == selected.node_id)
            .unwrap();
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                file_id,
                "src/module.py",
                generation,
                source.as_bytes(),
            )],
        )
        .unwrap();

        let old = "return y * 2";
        let start = source.find(old).unwrap() as u64;
        let end = start + old.len() as u64;
        let candidate = source.replacen(old, "return y * 3", 1);
        let receipt = admit_typed_source_review(
            &catalog,
            record,
            SourceGenerationV1::new(generation),
            source.as_bytes(),
            candidate.as_bytes(),
            &[AuthorizedSpanV1 {
                start: selected.byte_start as u64,
                end: selected.byte_end as u64,
            }],
            &[replacement(start, end, b"return y * 3")],
        )
        .unwrap();

        assert_eq!(receipt.source_generation, SourceGenerationV1::new(generation));
        assert_eq!(receipt.source_generation_coordinate.domain, GenerationDomainV1::Source);
        assert_eq!(receipt.source_generation_coordinate.value, generation);
        assert!(receipt.owner_admission.source_currentness_verified);
        assert!(receipt.owner_admission.outside_authorized_scope_unchanged);
        assert!(!receipt.semantic_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn wrong_source_generation_value_fails_after_owner_currentness_without_cross_axis_alias() {
        assert_eq!(
            require_source_review_generation(SourceGenerationV1::new(13), 12),
            Err(TypedSourceReviewErrorV1::SourceGenerationMismatch {
                expected: 13,
                observed: 12,
            })
        );
    }

    #[test]
    fn equal_numeric_cross_axis_coordinates_remain_distinct() {
        let source = SourceGenerationV1::new(12).coordinate();
        let placement = PlacementGenerationV1::new(12).coordinate();
        let graph = GraphServingGenerationV1::new(12).coordinate();
        assert_ne!(source, placement);
        assert_ne!(source, graph);
        assert_eq!(source.value, placement.value);
    }

    #[test]
    fn typed_membrane_does_not_widen_owner_claims() {
        let observed = require_source_review_generation(SourceGenerationV1::new(7), 7).unwrap();
        assert_eq!(observed.coordinate().domain, GenerationDomainV1::Source);
    }
}
