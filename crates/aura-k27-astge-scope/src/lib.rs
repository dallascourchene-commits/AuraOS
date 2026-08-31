#![forbid(unsafe_code)]

//! Fail-closed source mutation confinement for Aura K27 ASTGE.
//!
//! This crate proves only a byte-level consequence: a candidate file is exactly
//! reconstructible from an admitted original by applying explicit replacement
//! operations wholly inside explicit authorized source spans. It does not infer
//! authority from diffs, syntax, K27 coordinates, tests, model output, or storage
//! placement, and it does not prove semantic correctness of an authorized edit.

use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct AuthorizedSpanV1 {
    /// Half-open source byte coordinate [start, end).
    /// A zero-width span authorizes insertion at exactly `start`.
    pub start: u64,
    pub end: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplacementV1 {
    /// Half-open original-source byte coordinate [start, end).
    /// start == end is an insertion.
    pub start: u64,
    pub end: u64,
    pub replacement: Vec<u8>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBindingV1 {
    /// Currentness/provenance generation supplied by the source owner.
    /// This verifier preserves it but does not mint or elevate its authority.
    pub source_generation: u64,
    pub original_len: u64,
    pub original_sha256: [u8; 32],
}

impl SourceBindingV1 {
    pub fn bind(source_generation: u64, original: &[u8]) -> Self {
        Self {
            source_generation,
            original_len: original.len() as u64,
            original_sha256: sha256(original),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeVerificationReceiptV1 {
    pub source_generation: u64,
    pub original_sha256: [u8; 32],
    pub candidate_sha256: [u8; 32],
    pub original_len: u64,
    pub candidate_len: u64,
    pub authorized_span_count: usize,
    pub replacement_count: usize,
    /// Number of original bytes outside non-zero authorized spans.
    pub protected_original_bytes: u64,
    pub outside_authorized_scope_unchanged: bool,
    pub semantic_correctness_proven: bool,
    pub authority_granted: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScopeError {
    OriginalLengthMismatch { bound: u64, actual: u64 },
    OriginalDigestMismatch,
    InvalidAuthorizedSpan { start: u64, end: u64, source_len: u64 },
    OverlappingAuthorizedSpans { left: AuthorizedSpanV1, right: AuthorizedSpanV1 },
    InvalidReplacementRange { start: u64, end: u64, source_len: u64 },
    AmbiguousReplacementOrdering,
    ReplacementOutsideAuthorizedScope { start: u64, end: u64 },
    CandidateDoesNotMatchDeclaredReplacements,
}

impl Display for ScopeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for ScopeError {}

/// Verify that `candidate` is exactly the result of applying `replacements` to
/// `original`, with every replacement fully confined to `authorized_spans`.
///
/// The verifier intentionally does not infer an edit script from a diff. The
/// producer must declare the exact original-source operations it requests.
/// This makes suffix, prefix, and protected gaps independently checkable even
/// when an authorized replacement changes file length.
pub fn verify_candidate_scope(
    original: &[u8],
    candidate: &[u8],
    binding: &SourceBindingV1,
    authorized_spans: &[AuthorizedSpanV1],
    replacements: &[ReplacementV1],
) -> Result<ScopeVerificationReceiptV1, ScopeError> {
    admit_original(original, binding)?;
    let spans = admit_authorized_spans(authorized_spans, original.len() as u64)?;
    let operations = admit_replacements(replacements, original.len() as u64, &spans)?;

    let reconstructed = reconstruct(original, &operations);
    if reconstructed != candidate {
        return Err(ScopeError::CandidateDoesNotMatchDeclaredReplacements);
    }

    let authorized_bytes = spans
        .iter()
        .map(|span| span.end.saturating_sub(span.start))
        .sum::<u64>();

    Ok(ScopeVerificationReceiptV1 {
        source_generation: binding.source_generation,
        original_sha256: binding.original_sha256,
        candidate_sha256: sha256(candidate),
        original_len: original.len() as u64,
        candidate_len: candidate.len() as u64,
        authorized_span_count: spans.len(),
        replacement_count: operations.len(),
        protected_original_bytes: original.len() as u64 - authorized_bytes,
        outside_authorized_scope_unchanged: true,
        semantic_correctness_proven: false,
        authority_granted: false,
    })
}

fn admit_original(original: &[u8], binding: &SourceBindingV1) -> Result<(), ScopeError> {
    let actual = original.len() as u64;
    if actual != binding.original_len {
        return Err(ScopeError::OriginalLengthMismatch {
            bound: binding.original_len,
            actual,
        });
    }
    if sha256(original) != binding.original_sha256 {
        return Err(ScopeError::OriginalDigestMismatch);
    }
    Ok(())
}

fn admit_authorized_spans(
    authorized_spans: &[AuthorizedSpanV1],
    source_len: u64,
) -> Result<Vec<AuthorizedSpanV1>, ScopeError> {
    let mut spans = authorized_spans.to_vec();
    spans.sort_unstable();
    for span in &spans {
        if span.start > span.end || span.end > source_len {
            return Err(ScopeError::InvalidAuthorizedSpan {
                start: span.start,
                end: span.end,
                source_len,
            });
        }
    }
    for pair in spans.windows(2) {
        let left = pair[0];
        let right = pair[1];
        let both_zero_at_same_point =
            left.start == left.end && right.start == right.end && left.start == right.start;
        if right.start < left.end || both_zero_at_same_point {
            return Err(ScopeError::OverlappingAuthorizedSpans { left, right });
        }
    }
    Ok(spans)
}

fn admit_replacements(
    replacements: &[ReplacementV1],
    source_len: u64,
    spans: &[AuthorizedSpanV1],
) -> Result<Vec<ReplacementV1>, ScopeError> {
    let mut operations = replacements.to_vec();
    operations.sort_by_key(|replacement| (replacement.start, replacement.end));

    for replacement in &operations {
        if replacement.start > replacement.end || replacement.end > source_len {
            return Err(ScopeError::InvalidReplacementRange {
                start: replacement.start,
                end: replacement.end,
                source_len,
            });
        }
        if !replacement_authorized(replacement, spans) {
            return Err(ScopeError::ReplacementOutsideAuthorizedScope {
                start: replacement.start,
                end: replacement.end,
            });
        }
    }

    for pair in operations.windows(2) {
        let left = &pair[0];
        let right = &pair[1];
        let overlaps = right.start < left.end;
        let shared_coordinate_with_insertion = right.start == left.end
            && (left.start == left.end || right.start == right.end);
        if overlaps || shared_coordinate_with_insertion {
            return Err(ScopeError::AmbiguousReplacementOrdering);
        }
    }
    Ok(operations)
}

fn replacement_authorized(replacement: &ReplacementV1, spans: &[AuthorizedSpanV1]) -> bool {
    if replacement.start == replacement.end {
        return spans.iter().any(|span| {
            let exact_insertion_point = span.start == span.end && span.start == replacement.start;
            let strict_inside_nonzero =
                span.start < replacement.start && replacement.start < span.end;
            exact_insertion_point || strict_inside_nonzero
        });
    }

    spans.iter().any(|span| {
        span.start < span.end
            && span.start <= replacement.start
            && replacement.end <= span.end
    })
}

fn reconstruct(original: &[u8], operations: &[ReplacementV1]) -> Vec<u8> {
    let growth = operations
        .iter()
        .map(|operation| operation.replacement.len())
        .sum::<usize>();
    let mut output = Vec::with_capacity(original.len().saturating_add(growth));
    let mut cursor = 0usize;
    for operation in operations {
        let start = operation.start as usize;
        let end = operation.end as usize;
        output.extend_from_slice(&original[cursor..start]);
        output.extend_from_slice(&operation.replacement);
        cursor = end;
    }
    output.extend_from_slice(&original[cursor..]);
    output
}

fn sha256(bytes: &[u8]) -> [u8; 32] {
    let digest = Sha256::digest(bytes);
    digest.into()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn replace(start: u64, end: u64, value: &[u8]) -> ReplacementV1 {
        ReplacementV1 {
            start,
            end,
            replacement: value.to_vec(),
        }
    }

    #[test]
    fn variable_length_authorized_replacement_preserves_prefix_and_suffix() {
        let original = b"prefix-OLD-suffix";
        let candidate = b"prefix-NEW-LONGER-suffix";
        let binding = SourceBindingV1::bind(7, original);
        let receipt = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[AuthorizedSpanV1 { start: 7, end: 10 }],
            &[replace(7, 10, b"NEW-LONGER")],
        )
        .unwrap();
        assert!(receipt.outside_authorized_scope_unchanged);
        assert!(!receipt.semantic_correctness_proven);
        assert!(!receipt.authority_granted);
        assert_eq!(15, receipt.protected_original_bytes);
    }

    #[test]
    fn gemini_prefix_only_regression_rejects_unauthorized_suffix_change() {
        let original = b"AAAallowedBBB";
        let candidate = b"AAAchanged!ZZZ";
        let binding = SourceBindingV1::bind(1, original);
        let error = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[AuthorizedSpanV1 { start: 3, end: 10 }],
            &[replace(3, 10, b"changed")],
        )
        .unwrap_err();
        assert_eq!(ScopeError::CandidateDoesNotMatchDeclaredReplacements, error);
    }

    #[test]
    fn protected_gap_between_two_authorized_spans_cannot_change() {
        let original = b"AA111GAP222ZZ";
        let candidate = b"AAxxxBADyyyZZ";
        let binding = SourceBindingV1::bind(2, original);
        let error = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[
                AuthorizedSpanV1 { start: 2, end: 5 },
                AuthorizedSpanV1 { start: 8, end: 11 },
            ],
            &[replace(2, 5, b"xxx"), replace(8, 11, b"yyy")],
        )
        .unwrap_err();
        assert_eq!(ScopeError::CandidateDoesNotMatchDeclaredReplacements, error);
    }

    #[test]
    fn replacement_outside_scope_fails_before_candidate_comparison() {
        let original = b"0123456789";
        let binding = SourceBindingV1::bind(3, original);
        let error = verify_candidate_scope(
            original,
            original,
            &binding,
            &[AuthorizedSpanV1 { start: 2, end: 4 }],
            &[replace(7, 8, b"7")],
        )
        .unwrap_err();
        assert_eq!(
            ScopeError::ReplacementOutsideAuthorizedScope { start: 7, end: 8 },
            error
        );
    }

    #[test]
    fn empty_authorization_only_allows_identical_candidate() {
        let original = b"immutable";
        let binding = SourceBindingV1::bind(4, original);
        let receipt = verify_candidate_scope(original, original, &binding, &[], &[]).unwrap();
        assert_eq!(original.len() as u64, receipt.protected_original_bytes);

        let error = verify_candidate_scope(original, b"immutablE", &binding, &[], &[]).unwrap_err();
        assert_eq!(ScopeError::CandidateDoesNotMatchDeclaredReplacements, error);
    }

    #[test]
    fn stale_or_wrong_original_binding_fails_closed() {
        let original = b"current";
        let stale = SourceBindingV1::bind(5, b"stale!!");
        let error = verify_candidate_scope(original, original, &stale, &[], &[]).unwrap_err();
        assert_eq!(ScopeError::OriginalDigestMismatch, error);
    }

    #[test]
    fn overlapping_replacements_are_rejected() {
        let original = b"abcdefghij";
        let binding = SourceBindingV1::bind(6, original);
        let error = verify_candidate_scope(
            original,
            original,
            &binding,
            &[AuthorizedSpanV1 { start: 1, end: 8 }],
            &[replace(2, 5, b"cde"), replace(4, 6, b"ef")],
        )
        .unwrap_err();
        assert_eq!(ScopeError::AmbiguousReplacementOrdering, error);
    }

    #[test]
    fn boundary_insertion_requires_explicit_zero_width_authorization() {
        let original = b"abcd";
        let candidate = b"abXcd";
        let binding = SourceBindingV1::bind(7, original);

        let error = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[AuthorizedSpanV1 { start: 2, end: 4 }],
            &[replace(2, 2, b"X")],
        )
        .unwrap_err();
        assert_eq!(
            ScopeError::ReplacementOutsideAuthorizedScope { start: 2, end: 2 },
            error
        );

        let receipt = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[AuthorizedSpanV1 { start: 2, end: 2 }],
            &[replace(2, 2, b"X")],
        )
        .unwrap();
        assert!(receipt.outside_authorized_scope_unchanged);
    }

    #[test]
    fn caller_operation_order_is_canonicalized() {
        let original = b"aa11bb22cc";
        let candidate = b"aaXXbbYYcc";
        let binding = SourceBindingV1::bind(8, original);
        let receipt = verify_candidate_scope(
            original,
            candidate,
            &binding,
            &[
                AuthorizedSpanV1 { start: 2, end: 4 },
                AuthorizedSpanV1 { start: 6, end: 8 },
            ],
            &[replace(6, 8, b"YY"), replace(2, 4, b"XX")],
        )
        .unwrap();
        assert_eq!(2, receipt.replacement_count);
    }

    #[test]
    fn duplicate_zero_width_authorization_is_rejected_as_ambiguous() {
        let original = b"abcd";
        let binding = SourceBindingV1::bind(9, original);
        let error = verify_candidate_scope(
            original,
            original,
            &binding,
            &[
                AuthorizedSpanV1 { start: 2, end: 2 },
                AuthorizedSpanV1 { start: 2, end: 2 },
            ],
            &[],
        )
        .unwrap_err();
        assert!(matches!(error, ScopeError::OverlappingAuthorizedSpans { .. }));
    }
}
