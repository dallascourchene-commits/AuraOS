#![forbid(unsafe_code)]

//! Bind one exact profiled nested Python scope to the exact-current-source review membrane.
//!
//! This crate composes existing owners. It does not mint scope identity, source currentness,
//! mutation authority, semantic correctness, runtime resolution, B-minus approval, commit
//! authority, or external effect.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_profiled_scopes::{
    ProfiledPythonScopesV1, ProfiledScopeError, build_profiled_python_scopes,
};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use aura_k27_astge_source_review::{SourceReviewAdmissionV1, SourceReviewError, admit_source_review};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

const GENERATION_REF_PREFIX: &str = "AURA_SOURCE_BODY_GENERATION_V1:";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfiledScopeReviewAdmissionV1 {
    pub syntax_graph_sha256: [u8; 32],
    pub source_owner_ref: String,
    pub source_generation: u64,
    pub source_generation_ref: String,
    pub source_sha256: [u8; 32],
    pub scope_id: u64,
    pub parent_scope_id: u64,
    pub scope_kind: String,
    pub scope_name: String,
    pub syntax_ordinal: u64,
    pub ast_local_node_id: u64,
    pub file_id: u32,
    pub byte_start: u32,
    pub byte_end: u32,
    pub semantic_handle_digest: [u8; 32],
    pub relative_path: String,
    pub explicit_authorized_span_covers_selected_scope: bool,
    pub scope_anchor_matches_persisted_node: bool,
    pub source_currentness_verified: bool,
    pub outside_authorized_scope_unchanged: bool,
    pub ready_for_profiled_scope_semantic_review: bool,
    pub scope_span_is_mutation_authority: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProfiledScopeReviewError {
    OriginalSourceNotUtf8,
    UnknownCatalogFileId(u32),
    Profiled(ProfiledScopeError),
    Review(SourceReviewError),
    ScopeMissing(u64),
    ScopeNotNested(u64),
    ScopeSyntaxAnchorMissing(u64),
    ScopeSemanticHandleMissing(u64),
    PersistedNodeMismatch(&'static str),
    ExplicitAuthorizedSpanDoesNotCoverSelectedScope {
        scope_start: u64,
        scope_end: u64,
    },
    SourceGenerationRefMismatch,
    ParentClaimCeilingViolated,
}

impl Display for ProfiledScopeReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for ProfiledScopeReviewError {}

impl From<ProfiledScopeError> for ProfiledScopeReviewError {
    fn from(value: ProfiledScopeError) -> Self {
        Self::Profiled(value)
    }
}

impl From<SourceReviewError> for ProfiledScopeReviewError {
    fn from(value: SourceReviewError) -> Self {
        Self::Review(value)
    }
}

pub fn canonical_source_generation_ref(source_generation: u64) -> String {
    format!("{GENERATION_REF_PREFIX}{source_generation}")
}

/// Admit one selected nested lexical scope for later semantic review.
///
/// The caller does not provide a separate source-generation reference. The exact generation
/// comes from the already-admitted source catalog and is encoded into the PR496 SyntaxGraph
/// source binding. The selected scope's syntax span is selection evidence only: at least one
/// independently supplied `AuthorizedSpanV1` must explicitly cover that scope before PR494's
/// source-review owner is invoked.
pub fn admit_profiled_scope_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    original_source: &[u8],
    candidate_source: &[u8],
    source_owner_ref: impl Into<String>,
    selected_scope_id: u64,
    semantic_handles: &HashMap<u64, [u8; 32]>,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<ProfiledScopeReviewAdmissionV1, ProfiledScopeReviewError> {
    let source = std::str::from_utf8(original_source)
        .map_err(|_| ProfiledScopeReviewError::OriginalSourceNotUtf8)?;
    let locator = catalog
        .locator(record.file_id)
        .ok_or(ProfiledScopeReviewError::UnknownCatalogFileId(record.file_id))?;
    let source_generation_ref = canonical_source_generation_ref(locator.source_generation);
    let source_owner_ref = source_owner_ref.into();

    let profiled = build_profiled_python_scopes(
        source,
        record.file_id,
        source_owner_ref.clone(),
        source_generation_ref.clone(),
        semantic_handles,
    )?;
    enforce_profiled_parent_ceiling(&profiled)?;

    let selected = profiled
        .profiled_scopes
        .iter()
        .find(|scope| scope.scope_id == selected_scope_id)
        .ok_or(ProfiledScopeReviewError::ScopeMissing(selected_scope_id))?;
    let parent_scope_id = selected
        .parent_scope_id
        .ok_or(ProfiledScopeReviewError::ScopeNotNested(selected_scope_id))?;
    let syntax_ordinal = selected
        .syntax_ordinal
        .ok_or(ProfiledScopeReviewError::ScopeSyntaxAnchorMissing(
            selected_scope_id,
        ))?;
    let ast_local_node_id = selected
        .ast_local_node_id
        .ok_or(ProfiledScopeReviewError::ScopeSyntaxAnchorMissing(
            selected_scope_id,
        ))?;
    let semantic_handle_digest = selected
        .semantic_handle_digest
        .ok_or(ProfiledScopeReviewError::ScopeSemanticHandleMissing(
            selected_scope_id,
        ))?;

    require_record_matches_selected_scope(
        record,
        ast_local_node_id,
        selected.file_id,
        selected.byte_start,
        selected.byte_end,
        semantic_handle_digest,
    )?;

    let scope_start = u64::from(selected.byte_start);
    let scope_end = u64::from(selected.byte_end);
    if !authorized_spans
        .iter()
        .any(|span| span.start <= scope_start && span.end >= scope_end)
    {
        return Err(
            ProfiledScopeReviewError::ExplicitAuthorizedSpanDoesNotCoverSelectedScope {
                scope_start,
                scope_end,
            },
        );
    }

    let review = admit_source_review(
        catalog,
        record,
        original_source,
        candidate_source,
        authorized_spans,
        replacements,
    )?;
    enforce_review_parent_ceiling(&review)?;

    if review.source_generation != locator.source_generation
        || source_generation_ref != canonical_source_generation_ref(review.source_generation)
    {
        return Err(ProfiledScopeReviewError::SourceGenerationRefMismatch);
    }
    if review.file_id != selected.file_id {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch("file_id"));
    }
    if review.byte_start != selected.byte_start || review.byte_end != selected.byte_end {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch("byte_span"));
    }
    if review.semantic_handle_digest != semantic_handle_digest {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch(
            "semantic_handle_digest",
        ));
    }

    Ok(ProfiledScopeReviewAdmissionV1 {
        syntax_graph_sha256: profiled.syntax_graph.graph_sha256,
        source_owner_ref,
        source_generation: review.source_generation,
        source_generation_ref,
        source_sha256: review.source_sha256,
        scope_id: selected_scope_id,
        parent_scope_id,
        scope_kind: selected.kind.clone(),
        scope_name: selected.name.clone(),
        syntax_ordinal,
        ast_local_node_id,
        file_id: selected.file_id,
        byte_start: selected.byte_start,
        byte_end: selected.byte_end,
        semantic_handle_digest,
        relative_path: review.relative_path,
        explicit_authorized_span_covers_selected_scope: true,
        scope_anchor_matches_persisted_node: true,
        source_currentness_verified: review.source_currentness_verified,
        outside_authorized_scope_unchanged: review.outside_authorized_scope_unchanged,
        ready_for_profiled_scope_semantic_review: true,
        scope_span_is_mutation_authority: false,
        runtime_name_resolution_proven: false,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    })
}

fn require_record_matches_selected_scope(
    record: &NodeIndexRecordV1,
    ast_local_node_id: u64,
    file_id: u32,
    byte_start: u32,
    byte_end: u32,
    semantic_handle_digest: [u8; 32],
) -> Result<(), ProfiledScopeReviewError> {
    if record.node_id != ast_local_node_id {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch("node_id"));
    }
    if record.file_id != file_id {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch("file_id"));
    }
    if record.byte_start != byte_start || record.byte_end != byte_end {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch("byte_span"));
    }
    if record.semantic_handle_digest != semantic_handle_digest {
        return Err(ProfiledScopeReviewError::PersistedNodeMismatch(
            "semantic_handle_digest",
        ));
    }
    Ok(())
}

fn enforce_profiled_parent_ceiling(
    profiled: &ProfiledPythonScopesV1,
) -> Result<(), ProfiledScopeReviewError> {
    if profiled.local_ast_node_id_is_semantic_identity
        || profiled.local_scope_id_is_semantic_identity
        || profiled.runtime_name_resolution_proven
        || profiled.call_graph_proven
        || profiled.semantic_k27_derived
        || profiled.external_effect_authorized
    {
        return Err(ProfiledScopeReviewError::ParentClaimCeilingViolated);
    }
    Ok(())
}

fn enforce_review_parent_ceiling(
    review: &SourceReviewAdmissionV1,
) -> Result<(), ProfiledScopeReviewError> {
    if !review.source_currentness_verified
        || !review.outside_authorized_scope_unchanged
        || review.semantic_correctness_proven
        || review.b_minus_approved
        || review.commit_authorized
        || review.external_effect_authorized
    {
        return Err(ProfiledScopeReviewError::ParentClaimCeilingViolated);
    }
    Ok(())
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

    fn fixture() -> String {
        String::from(
            "def outer(x):\n    y = x + 1\n    def inner(z):\n        return y + z\n    return inner(x)\n\nSENTINEL = 'protected suffix'\n",
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
                (node.node_id, digest)
            })
            .collect()
    }

    fn temp_root(label: &str) -> PathBuf {
        let nonce = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-profiled-scope-review-{label}-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
    }

    struct FixtureState {
        root: PathBuf,
        source: String,
        catalog: AdmittedSourceCatalogV1,
        handles: HashMap<u64, [u8; 32]>,
        inner_scope_id: u64,
        inner_record: NodeIndexRecordV1,
        outer_record: NodeIndexRecordV1,
        inner_span: AuthorizedSpanV1,
    }

    fn setup(label: &str) -> FixtureState {
        let source = fixture();
        let file_id = 77;
        let handles = handles(&source, file_id);
        let profiled = build_profiled_python_scopes(
            &source,
            file_id,
            "source://fixture/current",
            canonical_source_generation_ref(12),
            &handles,
        )
        .unwrap();
        let inner = profiled
            .profiled_scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let outer = profiled
            .profiled_scopes
            .iter()
            .find(|scope| scope.name == "outer")
            .unwrap();

        let graph = parse_python_named_ast(&source, file_id).unwrap();
        let encoded = encode_ast_to_splane(&graph, &handles, 0, 41, [0x71; 32]).unwrap();
        let inner_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == inner.ast_local_node_id.unwrap())
            .unwrap()
            .clone();
        let outer_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == outer.ast_local_node_id.unwrap())
            .unwrap()
            .clone();

        let root = temp_root(label);
        fs::write(root.join("src/module.py"), source.as_bytes()).unwrap();
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

        FixtureState {
            root,
            source,
            catalog,
            handles,
            inner_scope_id: inner.scope_id,
            inner_record,
            outer_record,
            inner_span: AuthorizedSpanV1 {
                start: u64::from(inner.byte_start),
                end: u64::from(inner.byte_end),
            },
        }
    }

    #[test]
    fn exact_nested_scope_and_current_source_are_review_ready_only() {
        let state = setup("positive");
        let out = admit_profiled_scope_review(
            &state.catalog,
            &state.inner_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[state.inner_span],
            &[],
        )
        .unwrap();

        assert_eq!(out.scope_name, "inner");
        assert!(out.explicit_authorized_span_covers_selected_scope);
        assert!(out.scope_anchor_matches_persisted_node);
        assert!(out.source_currentness_verified);
        assert!(out.outside_authorized_scope_unchanged);
        assert!(out.ready_for_profiled_scope_semantic_review);
        assert!(!out.scope_span_is_mutation_authority);
        assert!(!out.runtime_name_resolution_proven);
        assert!(!out.semantic_correctness_proven);
        assert!(!out.b_minus_approved);
        assert!(!out.commit_authorized);
        assert!(!out.external_effect_authorized);
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn scope_span_does_not_auto_authorize_review() {
        let state = setup("no-auth");
        let err = admit_profiled_scope_review(
            &state.catalog,
            &state.inner_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[],
            &[],
        )
        .unwrap_err();
        assert_eq!(
            err,
            ProfiledScopeReviewError::ExplicitAuthorizedSpanDoesNotCoverSelectedScope {
                scope_start: state.inner_span.start,
                scope_end: state.inner_span.end,
            }
        );
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn persisted_node_must_be_the_selected_scope_anchor() {
        let state = setup("wrong-node");
        let err = admit_profiled_scope_review(
            &state.catalog,
            &state.outer_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[state.inner_span],
            &[],
        )
        .unwrap_err();
        assert_eq!(
            err,
            ProfiledScopeReviewError::PersistedNodeMismatch("node_id")
        );
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn explicit_authorization_may_be_wider_but_is_still_higher_owner_input() {
        let state = setup("wider");
        let wider = AuthorizedSpanV1 {
            start: 0,
            end: state.source.len() as u64,
        };
        let out = admit_profiled_scope_review(
            &state.catalog,
            &state.inner_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[wider],
            &[],
        )
        .unwrap();
        assert!(out.explicit_authorized_span_covers_selected_scope);
        assert!(!out.scope_span_is_mutation_authority);
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn mutation_outside_explicit_authorization_still_fails_in_parent_scope_verifier() {
        let state = setup("outside");
        let sentinel = state.source.find("SENTINEL").unwrap();
        let replacement = ReplacementV1 {
            start: sentinel as u64,
            end: (sentinel + "SENTINEL".len()) as u64,
            replacement: b"CHANGED!".to_vec(),
        };
        let mut candidate = state.source.as_bytes().to_vec();
        candidate.splice(
            sentinel..sentinel + "SENTINEL".len(),
            b"CHANGED!".iter().copied(),
        );
        let err = admit_profiled_scope_review(
            &state.catalog,
            &state.inner_record,
            state.source.as_bytes(),
            &candidate,
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[state.inner_span],
            &[replacement],
        )
        .unwrap_err();
        assert!(matches!(err, ProfiledScopeReviewError::Review(_)));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn source_drift_after_catalog_admission_fails_closed() {
        let state = setup("drift");
        fs::write(state.root.join("src/module.py"), b"changed after admission\n").unwrap();
        let err = admit_profiled_scope_review(
            &state.catalog,
            &state.inner_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            state.inner_scope_id,
            &state.handles,
            &[state.inner_span],
            &[],
        )
        .unwrap_err();
        assert!(matches!(err, ProfiledScopeReviewError::Review(_)));
        fs::remove_dir_all(state.root).unwrap();
    }

    #[test]
    fn module_root_is_not_a_nested_scope_review_target() {
        let state = setup("module");
        let profiled = build_profiled_python_scopes(
            &state.source,
            77,
            "source://fixture/current",
            canonical_source_generation_ref(12),
            &state.handles,
        )
        .unwrap();
        let module = profiled
            .profiled_scopes
            .iter()
            .find(|scope| scope.parent_scope_id.is_none())
            .unwrap();
        let graph = parse_python_named_ast(&state.source, 77).unwrap();
        let encoded = encode_ast_to_splane(&graph, &state.handles, 0, 41, [0x71; 32]).unwrap();
        let module_record = encoded
            .records
            .iter()
            .find(|record| record.node_id == module.ast_local_node_id.unwrap())
            .unwrap();
        let err = admit_profiled_scope_review(
            &state.catalog,
            module_record,
            state.source.as_bytes(),
            state.source.as_bytes(),
            "source://fixture/current",
            module.scope_id,
            &state.handles,
            &[AuthorizedSpanV1 {
                start: u64::from(module.byte_start),
                end: u64::from(module.byte_end),
            }],
            &[],
        )
        .unwrap_err();
        assert_eq!(err, ProfiledScopeReviewError::ScopeNotNested(module.scope_id));
        fs::remove_dir_all(state.root).unwrap();
    }
}
