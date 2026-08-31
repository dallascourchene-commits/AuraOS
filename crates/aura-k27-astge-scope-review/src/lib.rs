#![forbid(unsafe_code)]

//! Scope-aware current-source review admission for Aura K27 ASTGE.
//!
//! This membrane composes two independently owned proof planes without promoting either:
//! current-source + explicit byte-scope review admission, and conservative Python lexical-scope
//! inventory. A positive receipt means only that the explicitly selected persisted definition is
//! bound to the explicitly requested lexical owner scope in the exact current source. It does not
//! resolve identifier uses, choose a runtime binding winner, prove semantic correctness, approve
//! B-minus review, authorize commit/execution, or derive authority from K27 coordinates.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, MaterializeError};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_scopes::{index_python_nested_scopes, ScopeIndexError, ScopeKindV1};
use aura_k27_astge_source_review::{
    admit_source_review, SourceReviewAdmissionV1, SourceReviewError,
};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeAwareSourceReviewAdmissionV1 {
    pub source_review: SourceReviewAdmissionV1,
    pub owner_scope_id: u64,
    pub owner_scope_kind: ScopeKindV1,
    pub target_scope_id: u64,
    pub target_scope_kind: ScopeKindV1,
    pub definition_name: String,
    pub duplicate_same_owner_name_count: usize,
    pub lexical_owner_scope_bound: bool,
    pub selected_binding_explicit: bool,
    pub scope_topology_from_current_source: bool,
    pub identifier_use_resolution_proven: bool,
    pub runtime_binding_winner_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub execution_authorized: bool,
    pub human_authority: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum ScopeAwareReviewError {
    UnknownFileId(u32),
    SourceTooLarge(u64),
    Materialize(MaterializeError),
    SourceUtf8,
    SourceReview(SourceReviewError),
    ScopeIndex(ScopeIndexError),
    SelectedBindingMissing(u64),
    SelectedBindingAmbiguous { node_id: u64, matches: usize },
    OwnerScopeMissing(u64),
    TargetScopeMissing(u64),
    OwnerScopeMismatch { requested: u64, actual: u64 },
}

impl Display for ScopeAwareReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for ScopeAwareReviewError {}

impl From<MaterializeError> for ScopeAwareReviewError {
    fn from(value: MaterializeError) -> Self {
        Self::Materialize(value)
    }
}

impl From<SourceReviewError> for ScopeAwareReviewError {
    fn from(value: SourceReviewError) -> Self {
        Self::SourceReview(value)
    }
}

impl From<ScopeIndexError> for ScopeAwareReviewError {
    fn from(value: ScopeIndexError) -> Self {
        Self::ScopeIndex(value)
    }
}

/// Admit an exact persisted Python definition for scope-aware semantic review.
///
/// The caller supplies the selected persisted node and the lexical owner scope it expects. The
/// function obtains the whole file through the admitted source catalog's exact length/digest gate,
/// invokes the existing source-review owner using those current bytes, rebuilds the lexical-scope
/// inventory from those same current bytes, and requires one exact binding match on node ID,
/// file/span, and higher-owner semantic-handle digest.
///
/// `requested_owner_scope_id` is an expectation, not authority. A name match alone never selects a
/// binding, and duplicate names remain visible in the receipt.
pub fn admit_scope_aware_source_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    requested_owner_scope_id: u64,
) -> Result<ScopeAwareSourceReviewAdmissionV1, ScopeAwareReviewError> {
    let locator = catalog
        .locator(record.file_id)
        .ok_or(ScopeAwareReviewError::UnknownFileId(record.file_id))?;
    let full_len = u32::try_from(locator.byte_len)
        .map_err(|_| ScopeAwareReviewError::SourceTooLarge(locator.byte_len))?;

    // This synthetic record is only a source-materialization coordinate. The source owner ignores
    // its storage-local identity fields and revalidates file_id + full span against the admitted
    // length/digest before returning bytes.
    let full_source_record = NodeIndexRecordV1 {
        node_id: record.node_id,
        semantic_handle_digest: record.semantic_handle_digest,
        pbn: 0,
        row: 0,
        out_degree: 0,
        file_id: record.file_id,
        byte_start: 0,
        byte_end: full_len,
    };
    let full_source = catalog.materialize_node(&full_source_record)?;
    let source_text =
        std::str::from_utf8(&full_source.bytes).map_err(|_| ScopeAwareReviewError::SourceUtf8)?;

    let source_review = admit_source_review(
        catalog,
        record,
        &full_source.bytes,
        candidate_source,
        authorized_spans,
        replacements,
    )?;
    let scope_index = index_python_nested_scopes(source_text, record.file_id, semantic_handles)?;

    let matches: Vec<_> = scope_index
        .bindings
        .iter()
        .filter(|binding| {
            binding.ast_node_id == record.node_id
                && binding.file_id == record.file_id
                && binding.byte_start == record.byte_start
                && binding.byte_end == record.byte_end
                && binding.semantic_handle_digest == record.semantic_handle_digest
        })
        .collect();
    let binding = match matches.as_slice() {
        [] => {
            return Err(ScopeAwareReviewError::SelectedBindingMissing(
                record.node_id,
            ))
        }
        [binding] => *binding,
        _ => {
            return Err(ScopeAwareReviewError::SelectedBindingAmbiguous {
                node_id: record.node_id,
                matches: matches.len(),
            })
        }
    };

    let owner_scope = scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == binding.owner_scope_id)
        .ok_or(ScopeAwareReviewError::OwnerScopeMissing(
            binding.owner_scope_id,
        ))?;
    if owner_scope.scope_id != requested_owner_scope_id {
        return Err(ScopeAwareReviewError::OwnerScopeMismatch {
            requested: requested_owner_scope_id,
            actual: owner_scope.scope_id,
        });
    }
    let target_scope = scope_index
        .scopes
        .iter()
        .find(|scope| scope.scope_id == binding.target_scope_id)
        .ok_or(ScopeAwareReviewError::TargetScopeMissing(
            binding.target_scope_id,
        ))?;

    let duplicate_same_owner_name_count = scope_index
        .bindings
        .iter()
        .filter(|candidate| {
            candidate.owner_scope_id == binding.owner_scope_id && candidate.name == binding.name
        })
        .count();

    Ok(ScopeAwareSourceReviewAdmissionV1 {
        source_review,
        owner_scope_id: owner_scope.scope_id,
        owner_scope_kind: owner_scope.kind,
        target_scope_id: target_scope.scope_id,
        target_scope_kind: target_scope.kind,
        definition_name: binding.name.clone(),
        duplicate_same_owner_name_count,
        lexical_owner_scope_bound: true,
        selected_binding_explicit: true,
        scope_topology_from_current_source: full_source.source_currentness_verified,
        identifier_use_resolution_proven: false,
        runtime_binding_winner_proven: false,
        semantic_correctness_proven: false,
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
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-scope-review-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
    }

    fn fixture() -> String {
        String::from(
            "def target():\n    return 1\n\ndef outer():\n    def target():\n        return 2\n    def target():\n        return 3\n    return target\n\nSENTINEL = 'protected suffix'\n",
        )
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

    struct FixtureState {
        root: PathBuf,
        source: String,
        handles: HashMap<u64, [u8; 32]>,
        selected_record: NodeIndexRecordV1,
        selected_owner_scope: u64,
        selected_digit_start: usize,
    }

    fn state(label: &str) -> FixtureState {
        let root = temp_root(label);
        let source = fixture();
        let file_id = 77;
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let handles = handles(&source, file_id);
        let scopes = index_python_nested_scopes(&source, file_id, &handles).unwrap();
        let nested_targets: Vec<_> = scopes
            .bindings
            .iter()
            .filter(|binding| binding.name == "target" && binding.owner_scope_id != 0)
            .collect();
        assert_eq!(2, nested_targets.len());
        let selected = nested_targets[1];
        let encoded = encode_ast_to_splane(&graph, &handles, 0, 41, [0x71; 32]).unwrap();
        let selected_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == selected.ast_node_id)
            .unwrap()
            .clone();
        let selected_digit_start = source.rfind("return 3").unwrap() + "return ".len();
        FixtureState {
            root,
            source,
            handles,
            selected_record,
            selected_owner_scope: selected.owner_scope_id,
            selected_digit_start,
        }
    }

    fn catalog(state: &FixtureState, generation: u64) -> AdmittedSourceCatalogV1 {
        AdmittedSourceCatalogV1::admit(
            &state.root,
            [SourceLocatorV1::bind(
                state.selected_record.file_id,
                "src/module.py",
                generation,
                state.source.as_bytes(),
            )],
        )
        .unwrap()
    }

    fn candidate_and_scope(
        state: &FixtureState,
    ) -> (Vec<u8>, Vec<AuthorizedSpanV1>, Vec<ReplacementV1>) {
        let mut candidate = state.source.as_bytes().to_vec();
        candidate[state.selected_digit_start] = b'4';
        let start = state.selected_digit_start as u64;
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
    fn exact_nested_duplicate_definition_binds_requested_owner_scope_only() {
        let state = state("positive");
        let catalog = catalog(&state, 12);
        let (candidate, spans, replacements) = candidate_and_scope(&state);
        let receipt = admit_scope_aware_source_review(
            &catalog,
            &state.selected_record,
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.selected_owner_scope,
        )
        .unwrap();
        assert_eq!("target", receipt.definition_name);
        assert_eq!(state.selected_owner_scope, receipt.owner_scope_id);
        assert_eq!(ScopeKindV1::Function, receipt.owner_scope_kind);
        assert_eq!(ScopeKindV1::Function, receipt.target_scope_kind);
        assert_eq!(2, receipt.duplicate_same_owner_name_count);
        assert!(receipt.lexical_owner_scope_bound);
        assert!(receipt.selected_binding_explicit);
        assert!(receipt.scope_topology_from_current_source);
        assert!(receipt.source_review.source_currentness_verified);
        assert!(receipt.source_review.outside_authorized_scope_unchanged);
        assert!(!receipt.identifier_use_resolution_proven);
        assert!(!receipt.runtime_binding_winner_proven);
        assert!(!receipt.semantic_correctness_proven);
        assert!(!receipt.b_minus_approved);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.execution_authorized);
        assert!(!receipt.human_authority);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn same_identifier_in_module_scope_cannot_satisfy_nested_owner_expectation() {
        let state = state("owner-mismatch");
        let catalog = catalog(&state, 13);
        let (candidate, spans, replacements) = candidate_and_scope(&state);
        let error = admit_scope_aware_source_review(
            &catalog,
            &state.selected_record,
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            0,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            ScopeAwareReviewError::OwnerScopeMismatch { actual, .. }
                if actual == state.selected_owner_scope
        ));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn current_source_drift_fails_before_scope_topology_can_be_reused() {
        let state = state("source-drift");
        let catalog = catalog(&state, 14);
        fs::write(
            state.root.join("src/module.py"),
            state.source.replace("SENTINEL", "MUTATED!"),
        )
        .unwrap();
        let (candidate, spans, replacements) = candidate_and_scope(&state);
        let error = admit_scope_aware_source_review(
            &catalog,
            &state.selected_record,
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.selected_owner_scope,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            ScopeAwareReviewError::Materialize(MaterializeError::DigestMismatch(_))
                | ScopeAwareReviewError::Materialize(MaterializeError::LengthMismatch { .. })
        ));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn missing_scope_handle_fails_closed_even_when_source_review_inputs_are_valid() {
        let mut state = state("missing-handle");
        let catalog = catalog(&state, 15);
        state.handles.remove(&state.selected_record.node_id);
        let (candidate, spans, replacements) = candidate_and_scope(&state);
        let error = admit_scope_aware_source_review(
            &catalog,
            &state.selected_record,
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.selected_owner_scope,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            ScopeAwareReviewError::ScopeIndex(ScopeIndexError::MissingSemanticHandle(_))
        ));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn name_text_alone_cannot_select_a_different_definition() {
        let state = state("node-identity");
        let catalog = catalog(&state, 16);
        let (candidate, spans, replacements) = candidate_and_scope(&state);
        let mut wrong_record = state.selected_record.clone();
        wrong_record.semantic_handle_digest = [0xEE; 32];
        let error = admit_scope_aware_source_review(
            &catalog,
            &wrong_record,
            &candidate,
            &spans,
            &replacements,
            &state.handles,
            state.selected_owner_scope,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            ScopeAwareReviewError::SelectedBindingMissing(_)
        ));
        fs::remove_dir_all(state.root).unwrap();
    }
}
