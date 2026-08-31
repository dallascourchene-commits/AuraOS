//! Source-owned hydration producer/observer trust boundary.
//!
//! The lower-plane candidate validator lives in `producer_bound`; this module owns the
//! consequence-bearing producer trust step. Production intentionally has zero records.
//! A future trusted record must bind the exact hydration receipt plus a current producer and
//! distinct current observer. Caller data cannot populate or override this registry.

use crate::producer_bound::{
    CurrentProfiledScopeReviewCandidateV1, CurrentProfiledScopeReviewError,
    validate_current_profiled_scope_review_candidate,
};
use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::AdmittedSourceCatalogV1;
use aura_k27_astge_scope::{AuthorizedSpanV1, ReplacementV1};
use std::collections::HashMap;

pub const HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION: &str =
    "ASTGE_HYDRATION_PRODUCER_TRUST_REGISTRY_HOLD_V2";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct HydrationProducerTrustRecordV2 {
    producer_ref: &'static str,
    producer_generation: &'static str,
    producer_currentness_ref: &'static str,
    observer_ref: &'static str,
    observer_generation: &'static str,
    observer_currentness_ref: &'static str,
    anchor_id: &'static str,
    hydration_receipt_sha256: [u8; 32],
    active: bool,
    revoked: bool,
}

// Positive safety state: no source-owned producer/observer pair has been admitted yet.
const PRODUCTION_HYDRATION_PRODUCER_TRUST: &[HydrationProducerTrustRecordV2] = &[];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentProfiledScopeReviewAdmissionV2 {
    pub candidate: CurrentProfiledScopeReviewCandidateV1,
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

fn record_structurally_trust_eligible(row: &HydrationProducerTrustRecordV2) -> bool {
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

fn admit_candidate_from_trust_registry(
    candidate: CurrentProfiledScopeReviewCandidateV1,
    anchor_id: &str,
    registry: &[HydrationProducerTrustRecordV2],
) -> Result<CurrentProfiledScopeReviewAdmissionV2, CurrentProfiledScopeReviewError> {
    let matches: Vec<_> = registry
        .iter()
        .filter(|row| {
            record_structurally_trust_eligible(row)
                && row.anchor_id == anchor_id
                && row.hydration_receipt_sha256 == candidate.hydration_receipt_sha256
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

    Ok(CurrentProfiledScopeReviewAdmissionV2 {
        candidate,
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
/// Lower-plane validation executes first. Production then consults only repository-owned V2
/// producer/observer trust state, which is intentionally empty today. Callers cannot inject a
/// registry, expected producer, observer, trusted boolean, grammar/profile identity, graph digest,
/// source owner, expected generation, or raw lexical scope selector.
pub fn admit_current_profiled_scope_review(
    catalog: &AdmittedSourceCatalogV1,
    record: &NodeIndexRecordV1,
    hydration_json: &str,
    anchor_id: &str,
    candidate_source: &[u8],
    semantic_handles: &HashMap<u64, [u8; 32]>,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<CurrentProfiledScopeReviewAdmissionV2, CurrentProfiledScopeReviewError> {
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
    admit_candidate_from_trust_registry(candidate, anchor_id, PRODUCTION_HYDRATION_PRODUCER_TRUST)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn exact_row() -> HydrationProducerTrustRecordV2 {
        HydrationProducerTrustRecordV2 {
            producer_ref: "producer://fixture/hydration",
            producer_generation: "producer-gen://43",
            producer_currentness_ref: "current://producer/43",
            observer_ref: "observer://fixture/independent",
            observer_generation: "observer-gen://9",
            observer_currentness_ref: "current://observer/9",
            anchor_id: "anchor.fixture",
            hydration_receipt_sha256: [0x42; 32],
            active: true,
            revoked: false,
        }
    }

    #[test]
    fn production_v2_registry_is_empty_hold() {
        assert_eq!(
            HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION,
            "ASTGE_HYDRATION_PRODUCER_TRUST_REGISTRY_HOLD_V2"
        );
        assert!(PRODUCTION_HYDRATION_PRODUCER_TRUST.is_empty());
    }

    #[test]
    fn exact_distinct_current_producer_observer_shape_is_eligible() {
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
}
