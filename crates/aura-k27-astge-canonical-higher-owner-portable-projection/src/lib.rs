#![forbid(unsafe_code)]

//! Portable evidence for the canonical reduced higher-owner post-edit chain.
//!
//! PR538 proves one canonical owner chain for the post-edit definition target plus higher-owner
//! semantic-handle continuity. PR537 emits a deterministic serialized projection of the lower
//! typed canonical-target receipt. This crate composes those exact owners without reopening their
//! rules: it projects PR538's already-canonical inner target through PR537 and binds the portable
//! target handle to PR538's continuous higher-owner handle.
//!
//! This is transport evidence only. It does not authenticate a producer, prove runtime/semantic
//! correctness, or grant review, mutation, execution, commit, merge, promotion, provider, public,
//! human, K27, or other effect authority.

use aura_k27_astge_canonical_higher_owner_owner_reduction::CanonicalHigherOwnerOwnerReducedV1;
use aura_k27_astge_post_edit_canonical_projection::{
    project_canonical_definition_target, verify_projection, CanonicalDefinitionTargetProjectionV1,
    ProjectionErrorV1,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter, Write as _};

pub const PORTABLE_OWNER_CHAIN_SCHEMA_V1: &str =
    "AURA_ASTGE_CANONICAL_HIGHER_OWNER_OWNER_CHAIN_PROJECTION_V1";
pub const PORTABLE_OWNER_CHAIN_CANONICALIZATION_V1: &str =
    "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CanonicalHigherOwnerPortablePayloadV1 {
    pub schema: String,
    pub version: u32,
    pub canonicalization_profile: String,
    pub canonical_target_projection: CanonicalDefinitionTargetProjectionV1,
    pub continuous_semantic_handle_digest_hex: String,
    pub outer_constructor_reproved_by_inner_owner: bool,
    pub one_canonical_post_edit_consequence: bool,
    pub higher_owner_semantic_handle_continuity_proven: bool,
    pub producer_authenticated: bool,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub review_authorized: bool,
    pub mutation_authorized: bool,
    pub execution_authorized: bool,
    pub commit_authorized: bool,
    pub merge_authorized: bool,
    pub promotion_authorized: bool,
    pub provider_effect_authorized: bool,
    pub public_effect_authorized: bool,
    pub human_authority: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CanonicalHigherOwnerPortableProjectionV1 {
    pub payload: CanonicalHigherOwnerPortablePayloadV1,
    pub payload_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PortableOwnerChainProjectionErrorV1 {
    OwnerChainNotReproved,
    CanonicalConsequenceNotProven,
    OuterContinuityNotProven,
    OwnerChainAuthorityWidened,
    Projection(ProjectionErrorV1),
    HandleMismatch { projected: String, reduced: String },
    WrongSchema,
    WrongCanonicalizationProfile,
    PortableCeilingWidened,
    Serialization,
    DigestMismatch,
}

impl Display for PortableOwnerChainProjectionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}

impl Error for PortableOwnerChainProjectionErrorV1 {}

impl From<ProjectionErrorV1> for PortableOwnerChainProjectionErrorV1 {
    fn from(value: ProjectionErrorV1) -> Self {
        Self::Projection(value)
    }
}

pub fn project_reduced_higher_owner_owner_chain(
    reduced: &CanonicalHigherOwnerOwnerReducedV1,
) -> Result<CanonicalHigherOwnerPortableProjectionV1, PortableOwnerChainProjectionErrorV1> {
    if !reduced.outer_constructor_reproved_by_inner_owner {
        return Err(PortableOwnerChainProjectionErrorV1::OwnerChainNotReproved);
    }
    if !reduced.one_canonical_post_edit_consequence {
        return Err(PortableOwnerChainProjectionErrorV1::CanonicalConsequenceNotProven);
    }
    if !reduced
        .outer_constructor_receipt
        .canonical_definition_target_handle_continuity_proven
    {
        return Err(PortableOwnerChainProjectionErrorV1::OuterContinuityNotProven);
    }
    require_reduced_ceiling(reduced)?;

    let canonical_target = &reduced.canonical_inner_verification.canonical;
    let canonical_target_projection = project_canonical_definition_target(canonical_target)?;
    verify_projection(&canonical_target_projection)?;

    let projected_handle = canonical_target_projection
        .payload
        .selected_target_semantic_handle_digest_hex
        .clone();
    let reduced_handle = hex(&reduced.continuous_semantic_handle_digest);
    if projected_handle != reduced_handle {
        return Err(PortableOwnerChainProjectionErrorV1::HandleMismatch {
            projected: projected_handle,
            reduced: reduced_handle,
        });
    }

    let payload = CanonicalHigherOwnerPortablePayloadV1 {
        schema: PORTABLE_OWNER_CHAIN_SCHEMA_V1.to_owned(),
        version: 1,
        canonicalization_profile: PORTABLE_OWNER_CHAIN_CANONICALIZATION_V1.to_owned(),
        canonical_target_projection,
        continuous_semantic_handle_digest_hex: reduced_handle,
        outer_constructor_reproved_by_inner_owner: true,
        one_canonical_post_edit_consequence: true,
        higher_owner_semantic_handle_continuity_proven: true,
        producer_authenticated: false,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        review_authorized: false,
        mutation_authorized: false,
        execution_authorized: false,
        commit_authorized: false,
        merge_authorized: false,
        promotion_authorized: false,
        provider_effect_authorized: false,
        public_effect_authorized: false,
        human_authority: false,
    };
    let payload_sha256 = digest_payload(&payload)?;
    Ok(CanonicalHigherOwnerPortableProjectionV1 {
        payload,
        payload_sha256,
    })
}

pub fn verify_portable_higher_owner_owner_chain_projection(
    projection: &CanonicalHigherOwnerPortableProjectionV1,
) -> Result<(), PortableOwnerChainProjectionErrorV1> {
    let payload = &projection.payload;
    if payload.schema != PORTABLE_OWNER_CHAIN_SCHEMA_V1 || payload.version != 1 {
        return Err(PortableOwnerChainProjectionErrorV1::WrongSchema);
    }
    if payload.canonicalization_profile != PORTABLE_OWNER_CHAIN_CANONICALIZATION_V1 {
        return Err(PortableOwnerChainProjectionErrorV1::WrongCanonicalizationProfile);
    }
    if !payload.outer_constructor_reproved_by_inner_owner
        || !payload.one_canonical_post_edit_consequence
        || !payload.higher_owner_semantic_handle_continuity_proven
    {
        return Err(PortableOwnerChainProjectionErrorV1::OwnerChainNotReproved);
    }
    require_portable_ceiling(payload)?;
    verify_projection(&payload.canonical_target_projection)?;
    let projected_handle = &payload
        .canonical_target_projection
        .payload
        .selected_target_semantic_handle_digest_hex;
    if projected_handle != &payload.continuous_semantic_handle_digest_hex {
        return Err(PortableOwnerChainProjectionErrorV1::HandleMismatch {
            projected: projected_handle.clone(),
            reduced: payload.continuous_semantic_handle_digest_hex.clone(),
        });
    }
    if digest_payload(payload)? != projection.payload_sha256 {
        return Err(PortableOwnerChainProjectionErrorV1::DigestMismatch);
    }
    Ok(())
}

pub fn canonical_portable_payload_bytes(
    payload: &CanonicalHigherOwnerPortablePayloadV1,
) -> Result<Vec<u8>, PortableOwnerChainProjectionErrorV1> {
    serde_json::to_vec(payload).map_err(|_| PortableOwnerChainProjectionErrorV1::Serialization)
}

fn require_reduced_ceiling(
    reduced: &CanonicalHigherOwnerOwnerReducedV1,
) -> Result<(), PortableOwnerChainProjectionErrorV1> {
    if reduced.runtime_name_resolution_proven
        || reduced.call_graph_proven
        || reduced.semantic_patch_correctness_proven
        || reduced.b_minus_approved
        || reduced.commit_authorized
        || reduced.execution_authorized
        || reduced.human_authority
        || reduced.external_effect_authorized
    {
        return Err(PortableOwnerChainProjectionErrorV1::OwnerChainAuthorityWidened);
    }
    Ok(())
}

fn require_portable_ceiling(
    payload: &CanonicalHigherOwnerPortablePayloadV1,
) -> Result<(), PortableOwnerChainProjectionErrorV1> {
    if payload.producer_authenticated
        || payload.runtime_name_resolution_proven
        || payload.call_graph_proven
        || payload.semantic_patch_correctness_proven
        || payload.b_minus_approved
        || payload.review_authorized
        || payload.mutation_authorized
        || payload.execution_authorized
        || payload.commit_authorized
        || payload.merge_authorized
        || payload.promotion_authorized
        || payload.provider_effect_authorized
        || payload.public_effect_authorized
        || payload.human_authority
    {
        return Err(PortableOwnerChainProjectionErrorV1::PortableCeilingWidened);
    }
    Ok(())
}

fn digest_payload(
    payload: &CanonicalHigherOwnerPortablePayloadV1,
) -> Result<String, PortableOwnerChainProjectionErrorV1> {
    Ok(hex(&Sha256::digest(canonical_portable_payload_bytes(
        payload,
    )?)))
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut out, "{byte:02x}").expect("String writes do not fail");
    }
    out
}
