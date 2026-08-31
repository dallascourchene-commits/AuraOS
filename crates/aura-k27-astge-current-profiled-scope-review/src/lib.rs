#![forbid(unsafe_code)]

//! Producer-bound current profiled Python scope review.
//!
//! Lower-plane current/profile/scope validation may succeed, while production semantic-review
//! readiness remains blocked until the repository-owned hydration producer + independent observer
//! registry contains one exact active, non-revoked receipt binding. Caller data cannot populate
//! or override that trust root.

mod producer_bound;
mod trusted_registry;

pub use producer_bound::{
    CurrentProfiledScopeReviewCandidateV1, CurrentProfiledScopeReviewError,
    validate_current_profiled_scope_review_candidate,
};
pub use trusted_registry::{
    CurrentProfiledScopeReviewAdmissionV2, HYDRATION_PRODUCER_TRUST_REGISTRY_GENERATION,
    admit_current_profiled_scope_review,
};
