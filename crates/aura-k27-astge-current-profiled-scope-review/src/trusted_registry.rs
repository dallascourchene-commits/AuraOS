//! Source-owned hydration producer/observer and exact review-context trust boundary.
//!
//! The lower-plane candidate validator lives in `producer_bound`; this module owns the
//! consequence-bearing trust step. Production intentionally has zero records. A future trusted
//! record must bind the exact hydration receipt, the exact reviewed source/scope/edit context,
//! a current producer, and a distinct current observer. Caller data cannot populate or override
//! this registry.

use crate::producer_bound::{
    CurrentProfiledScopeReviewCandidateV1, CurrentProfiledScopeReviewError,
    validate_current_profiled_scope_review_candidate,
};
use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use sha2::{Digest, Sha256};
use std::collections::HashMap;

pub const HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION: &str =
    "ASTGE_HYDRATION_PRODUCER_TRUST_REGISTRY_HOLD_V3";

const REVIEW_CONTEXT_DIGEST_DOMAIN: &[u8] = b"ASTGE_CURRENT_PROFILED_SCOPE_REVIEW_CONTEXT_V1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct HydrationProducerTrustRecordV3 {
    producer_ref: &'static str,
    producer_generation: &'static str,
    producer_currentness_ref: &'static str,
    observer_ref: &'static str,
    observer_generation: &'static str,
    observer_currentness_ref: &'static str,
    anchor_id: &'static str,
    hydration_receipt_sha256: [u8; 32],
    review_context_sha256: [u8; 32],
    active: bool,
    revoked: bool,
}

// Positive safety state: no source-owned producer/observer/context record is admitted yet.
const PRODUCTION_HYDRATION_PRODUCER_TRUST: &[HydrationProducerTrustRecordV3] = &[];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentProfiledScopeReviewAdmissionV3 {
    pub candidate: CurrentProfiledScopeReviewCandidateV1,
    pub review_context_sha256: [u8; 32],
    pub hydration_producer_ref: &'static str,
    pub hydration_producer_generation: &'static str,
    pub hydration_producer_currentness_ref: &'static str,
    pub hydration_observer_ref: &'static str,
    pub hydration_observer_generation: &'static str,
    pub hydration_observer_currentness_ref: &'static str,
    pub hydration_producer_trust_registry_generation: &'static str,
    pub hydration_producer_trust_proven: bool,
    pub ready_for_current_profiled_scope_semantic_review: bool,
    pub runtime_name_resolution_proven: bool,
    pub semantic_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub commit_authorized: bool,
    pub external_effect_authorized: bool,
}

fn nonempty(value: &str) -> bool {
    !value.trim().is_empty()
}

fn record_structurally_trust_eligible(row: &HydrationProducerTrustRecordV3) -> bool {
    row.active
        && !row.revoked
        && nonempty(row.producer_ref)
        && nonempty(row.producer_generation)
        && nonempty(row.producer_currentness_ref)
        && nonempty(row.observer_ref)
        && nonempty(row.observer_generation)
        && nonempty(row.observer_currentness_ref)
        && row.producer_ref != row.observer_ref
}

fn hash_u64(hasher: &mut Sha256, value: u64) {
    hasher.update(value.to_le_bytes());
}

fn hash_bytes(hasher: &mut Sha256, value: &[u8]) {
    hash_u64(hasher, value.len() as u64);
    hasher.update(value);
}

/// Canonical digest of the exact consequence surface that a future source-owned trust record
/// must approve. This prevents one trusted hydration receipt for an anchor from being replayed
/// onto a different persisted definition, lexical target, candidate edit, or authorization span.
fn canonical_review_context_sha256(
    candidate: &CurrentProfiledScopeReviewCandidateV1,
    anchor_id: &str,
    candidate_source: &[u8],
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> [u8; 32] {
    let review = &candidate.profiled_review;
    let mut hasher = Sha256::new();
    hash_bytes(&mut hasher, REVIEW_CONTEXT_DIGEST_DOMAIN);
    hash_bytes(&mut hasher, anchor_id.as_bytes());
    hasher.update(candidate.hydration_receipt_sha256);
    hasher.update(review.syntax_graph_sha256);
    hasher.update(review.source_sha256);
    hash_bytes(&mut hasher, review.source_owner_ref.as_bytes());
    hash_bytes(&mut hasher, review.source_generation_ref.as_bytes());
    hash_u64(&mut hasher, review.source_generation);
    hash_u64(&mut hasher, u64::from(review.file_id));
    hash_bytes(&mut hasher, review.relative_path.as_bytes());
    hash_u64(&mut hasher, review.ast_local_node_id);
    hash_u64(&mut hasher, u64::from(review.byte_start));
    hash_u64(&mut hasher, u64::from(review.byte_end));
    hasher.update(review.semantic_handle_digest);
    hash_u64(&mut hasher, review.scope_id);
    hash_u64(&mut hasher, review.parent_scope_id);
    hash_u64(&mut hasher, review.syntax_ordinal);
    hash_u64(&mut hasher, candidate.canonical_syntax_ordinal);
    hash_u64(&mut hasher, candidate.local_target_scope_id_witness);
    hash_bytes(&mut hasher, candidate_source);

    let mut spans = authorized_spans.to_vec();
    spans.sort_unstable();
    hash_u64(&mut hasher, spans.len() as u64);
    for span in spans {
        hash_u64(&mut hasher, span.start);
        hash_u64(&mut hasher, span.end);
    }

    let mut operations = replacements.to_vec();
    operations.sort_by(|left, right| {
        left.start
            .cmp(&right.start)
            .then_with(|| left.end.cmp(&right.end))
            .then_with(|| left.replacement.cmp(&right.replacement))
    });
    hash_u64(&mut hasher, operations.len() as u64);
    for replacement in operations {
        hash_u64(&mut hasher, replacement.start);
        hash_u64(&mut hasher, replacement.end);
        hash_bytes(&mut hasher, &replacement.replacement);
    }

    hasher.finalize().into()
}

fn admit_candidate_from_trust_registry(
    candidate: CurrentProfiledScopeReviewCandidateV1,
    anchor_id: &str,
    review_context_sha256: [u8; 32],
    registry: &[HydrationProducerTrustRecordV3],
) -> Result<CurrentProfiledScopeReviewAdmissionV3, CurrentProfiledScopeReviewError> {
    let matches: Vec<_> = registry
        .iter()
        .filter(|row| {
            record_structurally_trust_eligible(row)
                && row.anchor_id == anchor_id
                && row.hydration_receipt_sha256 == candidate.hydration_receipt_sha256
                && row.review_context_sha256 == review_context_sha256
        })
        .collect();

    let record = match matches.as_slice() {
        [] => {
            return Err(CurrentProfiledScopeReviewError::HydrationProducerTrustUnproven {
                registry_generation: HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION,
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

    Ok(CurrentProfiledScopeReviewAdmissionV3 {
        candidate,
        review_context_sha256,
        hydration_producer_ref: record.producer_ref,
        hydration_producer_generation: record.producer_generation,
        hydration_producer_currentness_ref: record.producer_currentness_ref,
        hydration_observer_ref: record.observer_ref,
        hydration_observer_generation: record.observer_generation,
        hydration_observer_currentness_ref: record.observer_currentness_ref,
        hydration_producer_trust_registry_generation: HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION,
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
/// Lower-plane validation executes first. Production then computes one canonical digest over the
/// exact selected source/scope/edit context and consults only repository-owned V3 producer/observer
/// trust state, which is intentionally empty today. Callers cannot inject a registry, expected
/// producer/observer, trusted boolean, grammar/profile identity, graph digest, source owner,
/// expected generation, raw lexical scope selector, or trusted review-context digest.
pub fn admit_current_profiled_scope_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    hydration_json: &str,
    anchor_id: &str,
    candidate_source: &[u8],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<CurrentProfiledScopeReviewAdmissionV3, CurrentProfiledScopeReviewError> {
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
    let review_context_sha256 = canonical_review_context_sha256(
        &candidate,
        anchor_id,
        candidate_source,
        authorized_spans,
        replacements,
    );
    admit_candidate_from_trust_registry(
        candidate,
        anchor_id,
        review_context_sha256,
        PRODUCTION_HYDRATION_PRODUCER_TRUST,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn exact_row() -> HydrationProducerTrustRecordV3 {
        HydrationProducerTrustRecordV3 {
            producer_ref: "producer://fixture/hydration",
            producer_generation: "producer-gen://43",
            producer_currentness_ref: "current://producer/43",
            observer_ref: "observer://fixture/independent",
            observer_generation: "observer-gen://9",
            observer_currentness_ref: "current://observer/9",
            anchor_id: "anchor.fixture",
            hydration_receipt_sha256: [0x42; 32],
            review_context_sha256: [0x24; 32],
            active: true,
            revoked: false,
        }
    }

    #[test]
    fn production_v3_registry_is_empty_hold() {
        assert_eq!(
            HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION,
            "ASTGE_HYDRATION_PRODUCER_TRUST_REGISTRY_HOLD_V3"
        );
        assert!(PRODUCTION_HYDRATION_PRODUCER_TRUST.is_empty());
    }

    #[test]
    fn exact_distinct_current_producer_observer_context_shape_is_eligible() {
        assert!(record_structurally_trust_eligible(&exact_row()));
    }

    #[test]
    fn same_principal_producer_and_observer_is_ineligible() {
        let mut row = exact_row();
        row.observer_ref = row.producer_ref;
        assert!(!record_structurally_trust_eligible(&row));
    }

    #[test]
    fn revoked_inactive_or_missing_currentness_is_ineligible() {
        let mut revoked = exact_row();
        revoked.revoked = true;
        assert!(!record_structurally_trust_eligible(&revoked));

        let mut inactive = exact_row();
        inactive.active = false;
        assert!(!record_structurally_trust_eligible(&inactive));

        let mut missing = exact_row();
        missing.observer_currentness_ref = "";
        assert!(!record_structurally_trust_eligible(&missing));
    }

    #[test]
    fn review_context_digest_is_part_of_source_owned_match_key() {
        let row = exact_row();
        assert_eq!(row.hydration_receipt_sha256, [0x42; 32]);
        assert_eq!(row.review_context_sha256, [0x24; 32]);
        assert_ne!(row.hydration_receipt_sha256, row.review_context_sha256);
    }
}
