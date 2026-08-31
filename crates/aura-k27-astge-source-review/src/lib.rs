#![forbid(unsafe_code)]

//! Source-bound review admission for Aura K27 ASTGE.
//!
//! This membrane composes two independently verified proof planes:
//! 1. file_id -> exact current source materialization; and
//! 2. exact candidate reconstruction inside explicitly authorized original-byte spans.
//!
//! It deliberately does not derive mutation authority from Tree-Sitter spans, symbols,
//! semantic handles, K27 coordinates, or physical storage placement. A higher owner must
//! supply the authorized spans and declared replacements.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::{
    AdmittedSourceCatalogV1, MaterializeError, MaterializedSourceSliceV1,
};
use aura_k27_astge_scope::{
    AuthorizedSpanV1, ReplacementV1, ScopeError, ScopeVerificationReceiptV1, SourceBindingV1,
    verify_candidate_scope,
};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceReviewAdmissionV1 {
    pub node_id: u64,
    pub semantic_handle_digest: [u8; 32],
    pub file_id: u32,
    pub relative_path: String,
    pub source_generation: u64,
    pub source_sha256: [u8; 32],
    pub byte_start: u32,
    pub byte_end: u32,
    pub materialized_bytes: Vec<u8>,
    pub scope_receipt: ScopeVerificationReceiptV1,
    pub source_currentness_verified: bool,
    pub outside_authorized_scope_unchanged: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SourceReviewError {
    UnknownFileId(u32),
    Materialize(MaterializeError),
    Scope(ScopeError),
    MaterializedSliceMismatch,
}

impl Display for SourceReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for SourceReviewError {}

impl From<MaterializeError> for SourceReviewError {
    fn from(value: MaterializeError) -> Self {
        Self::Materialize(value)
    }
}
impl From<ScopeError> for SourceReviewError {
    fn from(value: ScopeError) -> Self {
        Self::Scope(value)
    }
}

/// Admit one source-backed edit candidate for later semantic review.
///
/// The node record selects a source only through the already-admitted catalog. The full
/// original source supplied here must match the catalog's source-owner generation/length/hash.
/// Authorized spans are explicit higher-owner input; this function never turns the node span
/// into mutation authority automatically.
pub fn admit_source_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    original_source: &[u8],
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<SourceReviewAdmissionV1, SourceReviewError> {
    let locator = catalog
        .locator(record.file_id)
        .ok_or(SourceReviewError::UnknownFileId(record.file_id))?;
    let materialized = catalog.materialize_node(record)?;

    let source_binding = SourceBindingV1 {
        source_generation: locator.source_generation,
        original_len: locator.byte_len,
        original_sha256: locator.sha256,
    };
    let scope_receipt = verify_candidate_scope(
        original_source,
        candidate_source,
        &source_binding,
        authorized_spans,
        replacements,
    )?;

    let start = record.byte_start as usize;
    let end = record.byte_end as usize;
    if original_source
        .get(start..end)
        .is_none_or(|bytes| bytes != materialized.bytes)
    {
        return Err(SourceReviewError::MaterializedSliceMismatch);
    }

    Ok(admission_from_parts(record, materialized, scope_receipt))
}

fn admission_from_parts(
    record: &NodeIndexRecordV1,
    materialized: MaterializedSourceSliceV1,
    scope_receipt: ScopeVerificationReceiptV1,
) -> SourceReviewAdmissionV1 {
    SourceReviewAdmissionV1 {
        node_id: record.node_id,
        semantic_handle_digest: record.semantic_handle_digest,
        file_id: record.file_id,
        relative_path: materialized.relative_path,
        source_generation: materialized.source_generation,
        source_sha256: materialized.source_sha256,
        byte_start: materialized.byte_start,
        byte_end: materialized.byte_end,
        materialized_bytes: materialized.bytes,
        source_currentness_verified: materialized.source_currentness_verified,
        outside_authorized_scope_unchanged: scope_receipt.outside_authorized_scope_unchanged,
        scope_receipt,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_scope::ScopeError;
    use aura_k27_astge_symbols::index_python_module_symbols;
    use std::collections::HashMap;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-source-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
    }

    fn fixture() -> String {
        String::from(
            "def target(x):\n    return x + 1\n\ndef target(y):\n    return y * 2\n\nSENTINEL = 'protected suffix'\n",
        )
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

    fn replace(start: u64, end: u64, value: &[u8]) -> ReplacementV1 {
        ReplacementV1 {
            start,
            end,
            replacement: value.to_vec(),
        }
    }

    #[test]
    fn duplicate_symbol_explicit_node_resolves_current_source_and_confined_edit() {
        let root = temp_root("positive");
        let source = fixture();
        let file_id = 77;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();

        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let semantic_handles = handles(graph.nodes.len());
        let symbols = index_python_module_symbols(&source, file_id, &semantic_handles).unwrap();
        let duplicate_targets: Vec<_> = symbols
            .symbols
            .iter()
            .filter(|symbol| symbol.name == "target")
            .collect();
        assert_eq!(duplicate_targets.len(), 2);
        let selected = duplicate_targets[1];

        let encoded = encode_ast_to_splane(&graph, &semantic_handles, 0, 41, [0x71; 32]).unwrap();
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
                12,
                source.as_bytes(),
            )],
        )
        .unwrap();

        let old = b"return y * 2";
        let start = source.find(std::str::from_utf8(old).unwrap()).unwrap() as u64;
        let end = start + old.len() as u64;
        assert!(selected.byte_start as u64 <= start && end <= selected.byte_end as u64);

        let candidate = source.replacen("return y * 2", "return y * 3", 1);
        let admission = admit_source_review(
            &catalog,
            record,
            source.as_bytes(),
            candidate.as_bytes(),
            &[AuthorizedSpanV1 {
                start: selected.byte_start as u64,
                end: selected.byte_end as u64,
            }],
            &[replace(start, end, b"return y * 3")],
        )
        .unwrap();

        assert_eq!(admission.node_id, selected.node_id);
        assert_eq!(admission.file_id, file_id);
        assert_eq!(admission.relative_path, "src/module.py");
        assert_eq!(admission.source_generation, 12);
        assert_eq!(admission.semantic_handle_digest, selected.semantic_handle_digest);
        assert_eq!(admission.byte_start, selected.byte_start);
        assert_eq!(admission.byte_end, selected.byte_end);
        assert_eq!(
            admission.materialized_bytes,
            source.as_bytes()[selected.byte_start as usize..selected.byte_end as usize]
        );
        assert!(admission.source_currentness_verified);
        assert!(admission.outside_authorized_scope_unchanged);
        assert!(!admission.semantic_correctness_proven);
        assert!(!admission.b_minus_approved);
        assert!(!admission.commit_authorized);
        assert!(!admission.external_effect_authorized);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn unauthorized_suffix_mutation_fails_even_when_declared_symbol_edit_is_valid() {
        let root = temp_root("suffix");
        let source = fixture();
        let file_id = 78;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let semantic_handles = handles(graph.nodes.len());
        let symbols = index_python_module_symbols(&source, file_id, &semantic_handles).unwrap();
        let selected = symbols
            .symbols
            .iter()
            .filter(|symbol| symbol.name == "target")
            .nth(1)
            .unwrap();
        let encoded = encode_ast_to_splane(&graph, &semantic_handles, 0, 42, [0x72; 32]).unwrap();
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
                13,
                source.as_bytes(),
            )],
        )
        .unwrap();
        let old = "return y * 2";
        let start = source.find(old).unwrap() as u64;
        let end = start + old.len() as u64;
        let mut candidate = source.replacen(old, "return y * 3", 1);
        candidate.push_str("# unauthorized suffix\n");

        let error = admit_source_review(
            &catalog,
            record,
            source.as_bytes(),
            candidate.as_bytes(),
            &[AuthorizedSpanV1 {
                start: selected.byte_start as u64,
                end: selected.byte_end as u64,
            }],
            &[replace(start, end, b"return y * 3")],
        )
        .unwrap_err();
        assert_eq!(
            error,
            SourceReviewError::Scope(ScopeError::CandidateDoesNotMatchDeclaredReplacements)
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn edit_in_other_duplicate_symbol_fails_selected_symbol_scope() {
        let root = temp_root("duplicate-scope");
        let source = fixture();
        let file_id = 79;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let semantic_handles = handles(graph.nodes.len());
        let symbols = index_python_module_symbols(&source, file_id, &semantic_handles).unwrap();
        let duplicate_targets: Vec<_> = symbols
            .symbols
            .iter()
            .filter(|symbol| symbol.name == "target")
            .collect();
        let selected = duplicate_targets[1];
        let other = duplicate_targets[0];
        let encoded = encode_ast_to_splane(&graph, &semantic_handles, 0, 43, [0x73; 32]).unwrap();
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
                14,
                source.as_bytes(),
            )],
        )
        .unwrap();
        let old = "return x + 1";
        let start = source.find(old).unwrap() as u64;
        let end = start + old.len() as u64;
        assert!(other.byte_start as u64 <= start && end <= other.byte_end as u64);
        let candidate = source.replacen(old, "return x + 9", 1);

        let error = admit_source_review(
            &catalog,
            record,
            source.as_bytes(),
            candidate.as_bytes(),
            &[AuthorizedSpanV1 {
                start: selected.byte_start as u64,
                end: selected.byte_end as u64,
            }],
            &[replace(start, end, b"return x + 9")],
        )
        .unwrap_err();
        assert!(matches!(
            error,
            SourceReviewError::Scope(ScopeError::ReplacementOutsideAuthorizedScope { .. })
        ));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn source_drift_after_catalog_admission_blocks_review_before_scope_claim() {
        let root = temp_root("drift");
        let source = fixture();
        let file_id = 80;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let semantic_handles = handles(graph.nodes.len());
        let encoded = encode_ast_to_splane(&graph, &semantic_handles, 0, 44, [0x74; 32]).unwrap();
        let record = &encoded.records[0];
        let catalog = AdmittedSourceCatalogV1::admit(
            &root,
            [SourceLocatorV1::bind(
                file_id,
                "src/module.py",
                15,
                source.as_bytes(),
            )],
        )
        .unwrap();
        fs::write(root.join("src/module.py"), source.replace("x + 1", "x - 1")).unwrap();

        let error = admit_source_review(
            &catalog,
            record,
            source.as_bytes(),
            source.as_bytes(),
            &[],
            &[],
        )
        .unwrap_err();
        assert!(matches!(error, SourceReviewError::Materialize(_)));
        fs::remove_dir_all(root).unwrap();
    }
}
