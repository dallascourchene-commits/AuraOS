#![forbid(unsafe_code)]

//! Patch-transaction input verification for Aura K27 ASTGE.
//!
//! This membrane composes two independently owned proof planes without promoting either one:
//! source-byte scope confinement and conservative graph-generation recovery/currentness. A
//! positive receipt means only that the declared candidate is scope-confined and that the exact
//! required graph generation is the currently validated serving generation. It does not prove
//! semantic correctness and grants no commit, execution, review, or external-effect authority.

use aura_k27_astge_recovery::{inspect_recovery_state, CurrentRecoveryStateV1};
use aura_k27_astge_scope::{
    verify_candidate_scope, AuthorizedSpanV1, ReplacementV1, ScopeError,
    ScopeVerificationReceiptV1, SourceBindingV1,
};
use std::error::Error;
use std::fmt::{Display, Formatter};
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PatchTransactionVerificationV1 {
    pub source_scope: ScopeVerificationReceiptV1,
    pub graph_serving_generation: u64,
    pub required_graph_generation: u64,
    pub source_scope_confined: bool,
    pub graph_generation_current: bool,
    pub ready_for_semantic_review: bool,
    pub semantic_correctness_proven: bool,
    pub commit_authorized: bool,
    pub execution_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TransactionVerificationError {
    Scope(ScopeError),
    RecoveryIo(String),
    RecoveryHold(CurrentRecoveryStateV1),
    GraphGenerationMismatch { required: u64, actual: u64 },
}

impl Display for TransactionVerificationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for TransactionVerificationError {}

impl From<ScopeError> for TransactionVerificationError {
    fn from(value: ScopeError) -> Self {
        Self::Scope(value)
    }
}

/// Verify the exact byte-scope and graph-generation inputs required before a later semantic
/// reviewer may consider a patch candidate.
///
/// The storage root is inspected through the recovery owner's validation path; callers cannot
/// serialize a pre-approved recovery state into this API. `required_graph_generation` is an
/// expectation to match, not authority: the current generation is independently recovered from
/// the validated CURRENT chain.
pub fn verify_patch_transaction_inputs(
    original: &[u8],
    candidate: &[u8],
    source_binding: &SourceBindingV1,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
    storage_root: impl AsRef<Path>,
    required_graph_generation: u64,
) -> Result<PatchTransactionVerificationV1, TransactionVerificationError> {
    let source_scope = verify_candidate_scope(
        original,
        candidate,
        source_binding,
        authorized_spans,
        replacements,
    )?;

    let inventory = inspect_recovery_state(storage_root)
        .map_err(|error| TransactionVerificationError::RecoveryIo(error.to_string()))?;
    let Some(actual_generation) = inventory.serving_generation else {
        return Err(TransactionVerificationError::RecoveryHold(
            inventory.current_state,
        ));
    };
    if actual_generation != required_graph_generation {
        return Err(TransactionVerificationError::GraphGenerationMismatch {
            required: required_graph_generation,
            actual: actual_generation,
        });
    }

    Ok(PatchTransactionVerificationV1 {
        source_scope_confined: source_scope.outside_authorized_scope_unchanged,
        graph_generation_current: true,
        ready_for_semantic_review: true,
        source_scope,
        graph_serving_generation: actual_generation,
        required_graph_generation,
        semantic_correctness_proven: false,
        commit_authorized: false,
        execution_authorized: false,
        external_effect_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge::{NodeIndexRecordV1, PageRow, PhysicalPageV1, StorageGenerationBindingV1};
    use aura_k27_astge_mmap::publish_generation;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    fn temp_root(label: &str) -> PathBuf {
        let n = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-k27-astge-transaction-{label}-{}-{n}",
            std::process::id()
        ));
        fs::create_dir(&root).unwrap();
        root
    }

    fn digest(byte: u8) -> [u8; 32] {
        [byte; 32]
    }

    fn publish_valid(root: &Path, generation: u64) {
        let placement_generation = 9;
        let scheme = digest(0x4A);
        let binding = StorageGenerationBindingV1 {
            node_count: 1,
            page_count: 1,
            placement_generation,
            placement_scheme_digest: scheme,
        };
        let record = NodeIndexRecordV1 {
            node_id: 1,
            semantic_handle_digest: digest(1),
            pbn: 0,
            row: 0,
            out_degree: 0,
            file_id: 3,
            byte_start: 0,
            byte_end: 5,
        };
        let page = PhysicalPageV1 {
            pbn: 0,
            placement_generation,
            placement_scheme_digest: scheme,
            rows: vec![PageRow {
                first_edge: 0,
                degree: 0,
            }],
            targets: vec![],
            edge_kinds: vec![],
        }
        .encode()
        .unwrap();
        publish_generation(root, generation, binding, &record.encode(), &page).unwrap();
    }

    fn scoped_edit<'a>() -> (
        &'a [u8],
        &'a [u8],
        SourceBindingV1,
        Vec<AuthorizedSpanV1>,
        Vec<ReplacementV1>,
    ) {
        let original: &'a [u8] = b"alpha=1\nbeta=2\n";
        let candidate: &'a [u8] = b"alpha=9\nbeta=2\n";
        (
            original,
            candidate,
            SourceBindingV1::bind(73, original),
            vec![AuthorizedSpanV1 { start: 6, end: 7 }],
            vec![ReplacementV1 {
                start: 6,
                end: 7,
                replacement: b"9".to_vec(),
            }],
        )
    }

    #[test]
    fn scope_confined_and_exact_current_generation_is_ready_only_for_semantic_review() {
        let root = temp_root("positive");
        publish_valid(&root, 41);
        let (original, candidate, binding, spans, replacements) = scoped_edit();
        let receipt = verify_patch_transaction_inputs(
            original,
            candidate,
            &binding,
            &spans,
            &replacements,
            &root,
            41,
        )
        .unwrap();
        assert!(receipt.source_scope_confined);
        assert!(receipt.graph_generation_current);
        assert!(receipt.ready_for_semantic_review);
        assert_eq!(41, receipt.graph_serving_generation);
        assert_eq!(41, receipt.required_graph_generation);
        assert_eq!(73, receipt.source_scope.source_generation);
        assert!(!receipt.semantic_correctness_proven);
        assert!(!receipt.commit_authorized);
        assert!(!receipt.execution_authorized);
        assert!(!receipt.external_effect_authorized);
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn unauthorized_suffix_change_fails_before_graph_currentness_can_help() {
        let root = temp_root("scope-fail");
        publish_valid(&root, 42);
        let original = b"alpha=1\nbeta=2\n";
        let candidate = b"alpha=9\nbeta=3\n";
        let binding = SourceBindingV1::bind(1, original);
        let error = verify_patch_transaction_inputs(
            original,
            candidate,
            &binding,
            &[AuthorizedSpanV1 { start: 6, end: 7 }],
            &[ReplacementV1 {
                start: 6,
                end: 7,
                replacement: b"9".to_vec(),
            }],
            &root,
            42,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            TransactionVerificationError::Scope(
                ScopeError::CandidateDoesNotMatchDeclaredReplacements
            )
        ));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn missing_current_holds_even_when_scope_is_valid() {
        let root = temp_root("missing-current");
        let (original, candidate, binding, spans, replacements) = scoped_edit();
        let error = verify_patch_transaction_inputs(
            original,
            candidate,
            &binding,
            &spans,
            &replacements,
            &root,
            51,
        )
        .unwrap_err();
        assert_eq!(
            error,
            TransactionVerificationError::RecoveryHold(CurrentRecoveryStateV1::Missing)
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn stale_expected_graph_generation_fails_closed() {
        let root = temp_root("generation-mismatch");
        publish_valid(&root, 61);
        let (original, candidate, binding, spans, replacements) = scoped_edit();
        let error = verify_patch_transaction_inputs(
            original,
            candidate,
            &binding,
            &spans,
            &replacements,
            &root,
            60,
        )
        .unwrap_err();
        assert_eq!(
            error,
            TransactionVerificationError::GraphGenerationMismatch {
                required: 60,
                actual: 61,
            }
        );
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn source_and_graph_generations_remain_distinct_domains() {
        let root = temp_root("generation-domains");
        publish_valid(&root, 91);
        let (original, candidate, mut binding, spans, replacements) = scoped_edit();
        binding.source_generation = 1234;
        let receipt = verify_patch_transaction_inputs(
            original,
            candidate,
            &binding,
            &spans,
            &replacements,
            &root,
            91,
        )
        .unwrap();
        assert_eq!(1234, receipt.source_scope.source_generation);
        assert_eq!(91, receipt.graph_serving_generation);
        assert_ne!(
            receipt.source_scope.source_generation,
            receipt.graph_serving_generation
        );
        fs::remove_dir_all(root).unwrap();
    }
}
