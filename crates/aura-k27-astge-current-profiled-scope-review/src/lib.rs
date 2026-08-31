#![forbid(unsafe_code)]

//! Producer-bound current profiled Python scope review.
//!
//! Lower-plane current/profile/scope validation may succeed, while production semantic-review
//! readiness remains blocked until the repository-owned hydration-producer registry contains an
//! exact active producer receipt. Caller data cannot populate or override that trust root.

mod producer_bound;

pub use producer_bound::*;
