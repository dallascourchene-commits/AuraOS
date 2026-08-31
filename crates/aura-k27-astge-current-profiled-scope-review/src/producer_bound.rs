#![forbid(unsafe_code)]

//! Producer-bound consequence membrane for current profiled Python scope review.
//!
//! Shape-valid/current hydration evidence is preserved as a lower-plane candidate, but it
//! cannot mint review readiness until the exact hydration receipt is admitted by this crate's
//! source-owned producer registry. Production intentionally starts with an empty registry.
//! No caller can supply a registry, expected producer, trusted boolean, grammar/profile ref,
//! graph digest, source-owner ref, generation expectation, or raw lexical scope selector.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_current_profiled_scopes::{
    CurrentProfiledScopeError, CurrentTypedProfiledScopesV1,
    admit_current_typed_profiled_python_scopes,
};
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, MaterializeError};
use aura_k27_astge_profiled_scope_review::{
    ProfiledScopeReviewAdmissionV1, ProfiledScopeReviewError, admit_profiled_scope_review,
};
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::error::Error;
use std::fmt::{Display, Formatter};

pub const HYDRATION_PRODUCER_REGISTRY_GENERATION: &str =
    "ASTGE_HYDRATION_PRODUCER_REGISTRY_HOLD_V1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct HydrationProducerRecordV1 {
    producer_ref: &'static str,
    anchor_id: &'static str,
    hydration_receipt_sha256: [u8; 32],
    active: bool,
}

// Source-owned trust root. Intentionally empty until a separately owned producer/currentness
// lane exists and a source change binds an exact producer receipt. Caller data cannot populate it.
const PRODUCTION_HYDRATION_PRODUCERS: &[HydrationProducerRecordV1] = &[];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentProfiledScopeReviewCandidateV1 {
    pub current_profiled: CurrentTypedProfiledScopesV1,
    pub profiled_review: ProfiledScopeReviewAdmissionV1,
    pub canonical_syntax_ordinal: u64,
    /// Inventory-local witness only. Never a public selector or semantic identity.
    pub local_target_scope_id_witness: u64,
    pub hydration_receipt_sha256: [u8; 32],
    pub hydration_producer_registry_generation: &'static str,
    pub current_profiled_identity_bound: bool,
    pub explicit_edit_authority_preserved: bool,
    pub lower_review_context_validated: bool,
    pub hydration_producer_trust_proven: bool,
    pub ready_for_current_profiled_scope_semantic_review: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentProfiledScopeReviewAdmissionV1 {
    pub candidate: CurrentProfiledScopeReviewCandidateV1,
    pub hydration_producer_ref: &'static str,
    pub hydration_producer_registry_generation: &'static str,
    pub hydration_producer_trust_proven: bool,
    pub ready_for_current_profiled_scope_semantic_review: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

#[derive(Debug)]
pub enum CurrentProfiledScopeReviewError {
    UnknownFileId(u32),
    SourceTooLarge(u64),
    Materialize(MaterializeError),
    SourceUtf8,
    CurrentProfiled(CurrentProfiledScopeError),
    SelectedBindingMissing(u64),
    SelectedBindingAmbiguous { node_id: u64, matches: usize },
    TargetScopeMissing(u64),
    TargetScopeNotNested(u64),
    CatalogSourceGenerationMismatch { catalog: u64, witnessed: u64 },
    Review(ProfiledScopeReviewError),
    CrossOwnerMismatch(&'static str),
    ClaimCeilingViolated,
    HydrationProducerTrustUnproven {
        registry_generation: &'static str,
        hydration_receipt_sha256: [u8; 32],
    },
    HydrationProducerTrustAmbiguous { matches: usize },
}

impl Display for CurrentProfiledScopeReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for CurrentProfiledScopeReviewError {}

impl From<MaterializeError> for CurrentProfiledScopeReviewError {
    fn from(value: MaterializeError) -> Self {
        Self::Materialize(value)
    }
}

impl From<CurrentProfiledScopeError> for CurrentProfiledScopeReviewError {
    fn from(value: CurrentProfiledScopeError) -> Self {
        Self::CurrentProfiled(value)
    }
}

impl From<ProfiledScopeReviewError> for CurrentProfiledScopeReviewError {
    fn from(value: ProfiledScopeReviewError) -> Self {
        Self::Review(value)
    }
}

fn hydration_receipt_sha256(hydration_json: &str) -> [u8; 32] {
    Sha256::digest(hydration_json.as_bytes()).into()
}

/// Validate all current/profile/scope/edit-authorization relations while preserving the
/// producer-provenance ceiling. A successful return is a candidate, not review readiness.
pub fn validate_current_profiled_scope_review_candidate(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    hydration_json: &str,
    anchor_id: &str,
    candidate_source: &[u8],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<CurrentProfiledScopeReviewCandidateV1, CurrentProfiledScopeReviewError> {
    let locator = catalog
        .locator(record.file_id)
        .ok_or(CurrentProfiledScopeReviewError::UnknownFileId(record.file_id))?;
    let full_len = u32::try_from(locator.byte_len)
        .map_err(|_| CurrentProfiledScopeReviewError::SourceTooLarge(locator.byte_len))?;

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
    let source_text = std::str::from_utf8(&full_source.bytes)
        .map_err(|_| CurrentProfiledScopeReviewError::SourceUtf8)?;

    // This proves only the existing shape/currentness/profile contract. Producer provenance is
    // deliberately decided later from the source-owned exact-receipt registry.
    let current_profiled = admit_current_typed_profiled_python_scopes(
        hydration_json,
        anchor_id,
        source_text,
        record.file_id,
        semantic_handles,
    )?;

    if locator.source_generation != current_profiled.source_generation.value() {
        return Err(CurrentProfiledScopeReviewError::CatalogSourceGenerationMismatch {
            catalog: locator.source_generation,
            witnessed: current_profiled.source_generation.value(),
        });
    }

    let matches: Vec<_> = current_profiled
        .profiled_scopes
        .profiled_bindings
        .iter()
        .filter(|binding| {
            binding.ast_local_node_id == record.node_id
                && binding.file_id == record.file_id
                && binding.byte_start == record.byte_start
                && binding.byte_end == record.byte_end
                && binding.semantic_handle_digest == record.semantic_handle_digest
        })
        .collect();
    let binding = match matches.as_slice() {
        [] => {
            return Err(CurrentProfiledScopeReviewError::SelectedBindingMissing(
                record.node_id,
            ));
        }
        [binding] => *binding,
        _ => {
            return Err(CurrentProfiledScopeReviewError::SelectedBindingAmbiguous {
                node_id: record.node_id,
                matches: matches.len(),
            });
        }
    };

    let target_scope = current_profiled
        .profiled_scopes
        .profiled_scopes
        .iter()
        .find(|scope| scope.scope_id == binding.target_scope_id)
        .ok_or(CurrentProfiledScopeReviewError::TargetScopeMissing(
            binding.target_scope_id,
        ))?;
    if target_scope.parent_scope_id.is_none() {
        return Err(CurrentProfiledScopeReviewError::TargetScopeNotNested(
            binding.target_scope_id,
        ));
    }
    if target_scope.syntax_ordinal != Some(binding.syntax_ordinal)
        || target_scope.ast_local_node_id != Some(binding.ast_local_node_id)
        || target_scope.file_id != binding.file_id
        || target_scope.byte_start != binding.byte_start
        || target_scope.byte_end != binding.byte_end
        || target_scope.semantic_handle_digest != Some(binding.semantic_handle_digest)
    {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "profiled_binding_target_scope",
        ));
    }

    let profiled_review = admit_profiled_scope_review(
        catalog,
        record,
        &full_source.bytes,
        candidate_source,
        current_profiled.current_syntax.anchor_owner_ref.clone(),
        binding.target_scope_id,
        semantic_handles,
        authorized_spans,
        replacements,
    )?;

    if profiled_review.syntax_graph_sha256 != current_profiled.syntax_graph.graph_sha256 {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "syntax_graph_sha256",
        ));
    }
    if profiled_review.syntax_ordinal != binding.syntax_ordinal {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "syntax_ordinal",
        ));
    }
    if profiled_review.source_generation != current_profiled.source_generation.value() {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "source_generation",
        ));
    }
    if profiled_review.source_owner_ref != current_profiled.current_syntax.anchor_owner_ref {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "source_owner_ref",
        ));
    }
    if profiled_review.file_id != record.file_id
        || profiled_review.byte_start != record.byte_start
        || profiled_review.byte_end != record.byte_end
        || profiled_review.semantic_handle_digest != record.semantic_handle_digest
    {
        return Err(CurrentProfiledScopeReviewError::CrossOwnerMismatch(
            "persisted_record_witness",
        ));
    }

    if !current_profiled.current_body_bound
        || !current_profiled.profiled_scope_identity_bound
        || current_profiled.runtime_name_resolution_proven
        || current_profiled.call_graph_proven
        || current_profiled.semantic_k27_derived
        || current_profiled.human_authority
        || current_profiled.external_effect
        || !profiled_review.explicit_authorized_span_covers_selected_scope
        || !profiled_review.scope_anchor_matches_persisted_node
        || !profiled_review.source_currentness_verified
        || !profiled_review.outside_authorized_scope_unchanged
        || profiled_review.scope_span_is_mutation_authority
        || profiled_review.runtime_name_resolution_proven
        || profiled_review.semantic_correctness_proven
        || profiled_review.b_minus_approved
        || profiled_review.commit_authorized
        || profiled_review.external_effect_authorized
    {
        return Err(CurrentProfiledScopeReviewError::ClaimCeilingViolated);
    }

    Ok(CurrentProfiledScopeReviewCandidateV1 {
        canonical_syntax_ordinal: binding.syntax_ordinal,
        local_target_scope_id_witness: binding.target_scope_id,
        hydration_receipt_sha256: hydration_receipt_sha256(hydration_json),
        hydration_producer_registry_generation: HYDRATION_PRODUCER_REGISTRY_GENERATION,
        current_profiled,
        profiled_review,
        current_profiled_identity_bound: true,
        explicit_edit_authority_preserved: true,
        lower_review_context_validated: true,
        hydration_producer_trust_proven: false,
        ready_for_current_profiled_scope_semantic_review: false,
        runtime_name_resolution_proven: false,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    })
}

fn admit_candidate_from_registry(
    candidate: CurrentProfiledScopeReviewCandidateV1,
    anchor_id: &str,
    registry: &[HydrationProducerRecordV1],
) -> Result<CurrentProfiledScopeReviewAdmissionV1, CurrentProfiledScopeReviewError> {
    let matches: Vec<_> = registry
        .iter()
        .filter(|row| {
            row.active
                && row.anchor_id == anchor_id
                && row.hydration_receipt_sha256 == candidate.hydration_receipt_sha256
        })
        .collect();
    let record = match matches.as_slice() {
        [] => {
            return Err(CurrentProfiledScopeReviewError::HydrationProducerTrustUnproven {
                registry_generation: HYDRATION_PRODUCER_REGISTRY_GENERATION,
                hydration_receipt_sha256: candidate.hydration_receipt_sha256,
            });
        }
        [record] => *record,
        _ => {
            return Err(CurrentProfiledScopeReviewError::HydrationProducerTrustAmbiguous {
                matches: matches.len(),
            });
        }
    };

    if candidate.hydration_producer_trust_proven
        || candidate.ready_for_current_profiled_scope_semantic_review
        || candidate.runtime_name_resolution_proven
        || candidate.semantic_correctness_proven
        || candidate.b_minus_approved
        || candidate.commit_authorized
        || candidate.external_effect_authorized
    {
        return Err(CurrentProfiledScopeReviewError::ClaimCeilingViolated);
    }

    Ok(CurrentProfiledScopeReviewAdmissionV1 {
        candidate,
        hydration_producer_ref: record.producer_ref,
        hydration_producer_registry_generation: HYDRATION_PRODUCER_REGISTRY_GENERATION,
        hydration_producer_trust_proven: true,
        ready_for_current_profiled_scope_semantic_review: true,
        runtime_name_resolution_proven: false,
        semantic_correctness_proven: false,
        b_minus_approved: false,
        commit_authorized: false,
        external_effect_authorized: false,
    })
}

/// Canonical production consequence boundary.
///
/// Production currently fails closed because `PRODUCTION_HYDRATION_PRODUCERS` is empty. A future
/// source-owned registry update may bind exact producer receipts; callers cannot inject that state.
pub fn admit_current_profiled_scope_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    hydration_json: &str,
    anchor_id: &str,
    candidate_source: &[u8],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<CurrentProfiledScopeReviewAdmissionV1, CurrentProfiledScopeReviewError> {
    let candidate = validate_current_profiled_scope_review_candidate(
        catalog,
        record,
        hydration_json,
        anchor_id,
        candidate_source,
        semantic_handles,
        authorized_spans,
        replacements,
    )?;
    admit_candidate_from_registry(candidate, anchor_id, PRODUCTION_HYDRATION_PRODUCERS)
}

#[cfg(test)]
mod tests {
    use super::*;
    use aura_k27_astge_ingest::{encode_ast_to_splane, parse_python_named_ast};
    use aura_k27_astge_materialize::SourceLocatorV1;
    use aura_k27_astge_profiled_scopes::build_profiled_python_scopes;
    use serde_json::{Value, json};
    use sha2::{Digest, Sha256};
    use std::fs;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);
    const SOURCE_OWNER: &str = "source-owner://current-profiled-review";
    const ANCHOR_ID: &str = "anchor.current-profiled-review";
    const SOURCE: &str = "def outer(x):\n    y = x + 1\n    def inner(z):\n        return y + z\n    return inner(x)\n\nSENTINEL = 'protected'\n";

    fn temp_root(label: &str) -> PathBuf {
        let nonce = COUNTER.fetch_add(1, Ordering::Relaxed);
        let root = std::env::temp_dir().join(format!(
            "aura-current-profiled-review-{label}-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir_all(root.join("src")).unwrap();
        root
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

    fn body_sha(source: &str) -> String {
        let digest: [u8; 32] = Sha256::digest(source.as_bytes()).into();
        digest.iter().map(|byte| format!("{byte:02x}")).collect()
    }

    fn hydration(source: &str, file_id: u32, generation: u64, status: &str, admitted: bool) -> String {
        let sha = body_sha(source);
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
            "anchor_owner_reused": SOURCE_OWNER,
            "source_body_witness_required": true,
            "unknown_or_stale_hydration_admitted": false,
            "codemap_digest8_currentness_authority": false,
            "source_authority_minted": false,
            "project007_runtime_implemented": false,
            "anchor_receipts": [{
                "anchor_id": ANCHOR_ID,
                "path": "src/module.py",
                "semantic_id": "SEM:CURRENT-PROFILED-REVIEW",
                "signature_hash": "sig",
                "anchor_projection_resolved": true,
                "semantic_identity_minted_by_bridge": false,
                "source_authority_minted": false,
                "body_currentness_status": status,
                "hydration_admitted": admitted,
                "reason": if status == "CURRENT" { "EXACT_SOURCE_BODY_WITNESS_MATCH" } else if status == "STALE" { "SOURCE_BODY_DIGEST_DRIFT" } else { "MISSING_SOURCE_BODY_WITNESS" },
                "witness_ref": if admitted { "witness://current-profiled-review/body" } else { "" },
                "expected_byte_len": if admitted { source.len() } else { 0 },
                "observed_byte_len": if admitted { source.len() } else { 0 },
                "expected_body_sha256": if admitted { sha.clone() } else { String::new() },
                "observed_body_sha256": if admitted { sha.clone() } else { String::new() },
                "locator": locator,
            }],
            "source_locators_v1": [],
        })
        .to_string()
    }

    struct Fixture {
        root: PathBuf,
        catalog: AdmittedSourceCatalogV1,
        record: NodeIndexRecordV1,
        handles: HashMap<u64, [u8; 32]>,
        authorized: AuthorizedSpanV1,
        generation: u64,
    }

    fn setup(label: &str, generation: u64) -> Fixture {
        let file_id = 401;
        let handles = handles(SOURCE, file_id);
        let profiled = build_profiled_python_scopes(
            SOURCE,
            file_id,
            SOURCE_OWNER,
            format!("AURA_SOURCE_BODY_GENERATION_V1:{generation}"),
            &handles,
        )
        .unwrap();
        let inner = profiled
            .profiled_scopes
            .iter()
            .find(|scope| scope.name == "inner")
            .unwrap();
        let graph = parse_python_named_ast(SOURCE, file_id).unwrap();
        let encoded = encode_ast_to_splane(&graph, &handles, 0, 41, [0x42; 32]).unwrap();
        let record = encoded
            .records
            .iter()
            .find(|record| record.node_id == inner.ast_local_node_id.unwrap())
            .unwrap()
            .clone();
        let root = temp_root(label);
        fs::write(root.join("src/module.py"), SOURCE.as_bytes()).unwrap();
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
        Fixture {
            root,
            catalog,
            record,
            handles,
            authorized: AuthorizedSpanV1 {
                start: u64::from(inner.byte_start),
                end: u64::from(inner.byte_end),
            },
            generation,
        }
    }

    fn current_candidate(fixture: &Fixture) -> CurrentProfiledScopeReviewCandidateV1 {
        validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &fixture.record,
            &hydration(SOURCE, fixture.record.file_id, fixture.generation, "CURRENT", true),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap()
    }

    #[test]
    fn shape_current_profile_is_preserved_but_not_promoted() {
        let fixture = setup("candidate", 41);
        let candidate = current_candidate(&fixture);
        assert!(candidate.lower_review_context_validated);
        assert!(candidate.current_profiled_identity_bound);
        assert!(!candidate.hydration_producer_trust_proven);
        assert!(!candidate.ready_for_current_profiled_scope_semantic_review);
        assert!(!candidate.runtime_name_resolution_proven);
        assert!(!candidate.semantic_correctness_proven);
        assert!(!candidate.b_minus_approved);
        assert!(!candidate.commit_authorized);
        assert!(!candidate.external_effect_authorized);
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn production_registry_is_source_owned_empty_hold() {
        assert_eq!(HYDRATION_PRODUCER_REGISTRY_GENERATION, "ASTGE_HYDRATION_PRODUCER_REGISTRY_HOLD_V1");
        assert!(PRODUCTION_HYDRATION_PRODUCERS.is_empty());
        let fixture = setup("hold", 42);
        let err = admit_current_profiled_scope_review(
            &fixture.catalog,
            &fixture.record,
            &hydration(SOURCE, fixture.record.file_id, fixture.generation, "CURRENT", true),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(
            err,
            CurrentProfiledScopeReviewError::HydrationProducerTrustUnproven { .. }
        ));
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn test_private_exact_receipt_registry_proves_future_promotion_semantics() {
        let fixture = setup("private-registry", 43);
        let candidate = current_candidate(&fixture);
        let registry = [HydrationProducerRecordV1 {
            producer_ref: "producer://fixture/exact-hydration",
            anchor_id: ANCHOR_ID,
            hydration_receipt_sha256: candidate.hydration_receipt_sha256,
            active: true,
        }];
        let admitted = admit_candidate_from_registry(candidate, ANCHOR_ID, &registry).unwrap();
        assert!(admitted.hydration_producer_trust_proven);
        assert!(admitted.ready_for_current_profiled_scope_semantic_review);
        assert!(!admitted.semantic_correctness_proven);
        assert!(!admitted.b_minus_approved);
        assert!(!admitted.commit_authorized);
        assert!(!admitted.external_effect_authorized);
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn self_consistent_caller_hydration_cannot_self_promote() {
        let fixture = setup("forged-shape", 44);
        let forged = hydration(SOURCE, fixture.record.file_id, fixture.generation, "CURRENT", true);
        let candidate = validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &fixture.record,
            &forged,
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap();
        assert!(candidate.lower_review_context_validated);
        assert!(!candidate.hydration_producer_trust_proven);
        assert!(!candidate.ready_for_current_profiled_scope_semantic_review);
        let err = admit_current_profiled_scope_review(
            &fixture.catalog,
            &fixture.record,
            &forged,
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(
            err,
            CurrentProfiledScopeReviewError::HydrationProducerTrustUnproven { .. }
        ));
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn stale_independent_body_shape_fails_before_producer_trust() {
        let fixture = setup("stale", 45);
        let err = validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &fixture.record,
            &hydration(SOURCE, fixture.record.file_id, fixture.generation, "STALE", false),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(err, CurrentProfiledScopeReviewError::CurrentProfiled(_)));
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn catalog_generation_must_equal_shape_witnessed_source_generation() {
        let fixture = setup("generation", 46);
        let err = validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &fixture.record,
            &hydration(SOURCE, fixture.record.file_id, 47, "CURRENT", true),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(
            err,
            CurrentProfiledScopeReviewError::CatalogSourceGenerationMismatch {
                catalog: 46,
                witnessed: 47
            }
        ));
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn persisted_handle_substitution_cannot_select_profiled_scope() {
        let fixture = setup("handle", 48);
        let mut substituted = fixture.record.clone();
        substituted.semantic_handle_digest[31] ^= 0xff;
        let err = validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &substituted,
            &hydration(SOURCE, substituted.file_id, fixture.generation, "CURRENT", true),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(
            err,
            CurrentProfiledScopeReviewError::SelectedBindingMissing(_)
        ));
        fs::remove_dir_all(fixture.root).unwrap();
    }

    #[test]
    fn source_drift_after_catalog_admission_fails_closed() {
        let fixture = setup("drift", 49);
        fs::write(fixture.root.join("src/module.py"), b"changed after admission\n").unwrap();
        let err = validate_current_profiled_scope_review_candidate(
            &fixture.catalog,
            &fixture.record,
            &hydration(SOURCE, fixture.record.file_id, fixture.generation, "CURRENT", true),
            ANCHOR_ID,
            SOURCE.as_bytes(),
            &fixture.handles,
            &[fixture.authorized],
            &[],
        )
        .unwrap_err();
        assert!(matches!(err, CurrentProfiledScopeReviewError::Materialize(_)));
        fs::remove_dir_all(fixture.root).unwrap();
    }
}
