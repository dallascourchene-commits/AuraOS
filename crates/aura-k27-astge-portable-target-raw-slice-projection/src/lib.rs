#![forbid(unsafe_code)]

//! Deterministic cross-runtime projection of PR560 exact raw-target-slice evidence.
//!
//! The source owner remains `aura-k27-astge-portable-target-raw-slice`. This crate does not
//! rematerialize source bytes and does not derive semantic identity from them. It only serializes
//! an already-admitted raw-slice receipt under a closed, deterministic struct-order profile so a
//! heterogeneous consumer can verify one exact evidence object without duplicating the owner.

use aura_k27_astge_portable_target_raw_slice::{
    PortableTargetRawSliceV1, VERSION as RAW_SLICE_VERSION,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter, Write as _};

pub const PROJECTION_SCHEMA_V1: &str =
    "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_PROJECTION_V1";
pub const CANONICALIZATION_PROFILE_V1: &str = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PortableTargetRawSlicePayloadV1 {
    pub schema: String,
    pub version: u32,
    pub canonicalization_profile: String,
    pub raw_slice_version: String,
    pub projection_payload_sha256: String,
    pub file_id: u32,
    pub relative_path: String,
    pub source_generation: u64,
    pub full_source_sha256_hex: String,
    pub full_source_byte_len: u64,
    pub target_byte_start: u32,
    pub target_byte_end: u32,
    pub target_slice_byte_len: u64,
    pub target_slice_sha256_hex: String,
    pub selected_target_semantic_handle_digest_hex: String,
    pub portable_target_bound_to_exact_current_raw_slice: bool,
    pub source_currentness_revalidated_at_materialization: bool,
    pub synthetic_record_is_materialization_coordinate_only: bool,
    pub storage_node_identity_minted: bool,
    pub semantic_handle_carried_from_portable_owner: bool,
    pub semantic_handle_derived_from_raw_slice: bool,
    pub semantic_identity_proven_by_raw_slice: bool,
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
pub struct PortableTargetRawSliceProjectionV1 {
    pub payload: PortableTargetRawSlicePayloadV1,
    pub payload_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RawSliceProjectionErrorV1 {
    WrongRawSliceVersion,
    RawSliceOwnerNotProven,
    RawSliceCeilingWidened,
    InvalidDigestField(&'static str),
    InvalidSpan,
    WrongSchema,
    WrongCanonicalizationProfile,
    Serialization,
    DigestMismatch,
}

impl Display for RawSliceProjectionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for RawSliceProjectionErrorV1 {}

pub fn project_portable_target_raw_slice(
    raw_slice: &PortableTargetRawSliceV1,
) -> Result<PortableTargetRawSliceProjectionV1, RawSliceProjectionErrorV1> {
    require_raw_slice_owner(raw_slice)?;
    let payload = PortableTargetRawSlicePayloadV1 {
        schema: PROJECTION_SCHEMA_V1.to_owned(),
        version: 1,
        canonicalization_profile: CANONICALIZATION_PROFILE_V1.to_owned(),
        raw_slice_version: raw_slice.version.to_owned(),
        projection_payload_sha256: raw_slice.projection_payload_sha256.clone(),
        file_id: raw_slice.file_id,
        relative_path: raw_slice.relative_path.clone(),
        source_generation: raw_slice.source_generation,
        full_source_sha256_hex: raw_slice.full_source_sha256_hex.clone(),
        full_source_byte_len: raw_slice.full_source_byte_len,
        target_byte_start: raw_slice.target_byte_start,
        target_byte_end: raw_slice.target_byte_end,
        target_slice_byte_len: raw_slice.target_slice_byte_len,
        target_slice_sha256_hex: raw_slice.target_slice_sha256_hex.clone(),
        selected_target_semantic_handle_digest_hex: raw_slice
            .selected_target_semantic_handle_digest_hex
            .clone(),
        portable_target_bound_to_exact_current_raw_slice: true,
        source_currentness_revalidated_at_materialization: true,
        synthetic_record_is_materialization_coordinate_only: true,
        storage_node_identity_minted: false,
        semantic_handle_carried_from_portable_owner: true,
        semantic_handle_derived_from_raw_slice: false,
        semantic_identity_proven_by_raw_slice: false,
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
    Ok(PortableTargetRawSliceProjectionV1 {
        payload,
        payload_sha256,
    })
}

pub fn verify_portable_target_raw_slice_projection(
    projection: &PortableTargetRawSliceProjectionV1,
) -> Result<(), RawSliceProjectionErrorV1> {
    let payload = &projection.payload;
    if payload.schema != PROJECTION_SCHEMA_V1 || payload.version != 1 {
        return Err(RawSliceProjectionErrorV1::WrongSchema);
    }
    if payload.canonicalization_profile != CANONICALIZATION_PROFILE_V1 {
        return Err(RawSliceProjectionErrorV1::WrongCanonicalizationProfile);
    }
    require_payload(payload)?;
    if digest_payload(payload)? != projection.payload_sha256 {
        return Err(RawSliceProjectionErrorV1::DigestMismatch);
    }
    Ok(())
}

pub fn canonical_payload_bytes(
    payload: &PortableTargetRawSlicePayloadV1,
) -> Result<Vec<u8>, RawSliceProjectionErrorV1> {
    serde_json::to_vec(payload).map_err(|_| RawSliceProjectionErrorV1::Serialization)
}

fn require_raw_slice_owner(
    raw_slice: &PortableTargetRawSliceV1,
) -> Result<(), RawSliceProjectionErrorV1> {
    if raw_slice.version != RAW_SLICE_VERSION {
        return Err(RawSliceProjectionErrorV1::WrongRawSliceVersion);
    }
    if !raw_slice.portable_target_bound_to_exact_current_raw_slice
        || !raw_slice.source_currentness_revalidated_at_materialization
        || !raw_slice.synthetic_record_is_materialization_coordinate_only
        || !raw_slice.semantic_handle_carried_from_portable_owner
    {
        return Err(RawSliceProjectionErrorV1::RawSliceOwnerNotProven);
    }
    if raw_slice.storage_node_identity_minted
        || raw_slice.semantic_handle_derived_from_raw_slice
        || raw_slice.semantic_identity_proven_by_raw_slice
        || raw_slice.producer_authenticated
        || raw_slice.runtime_name_resolution_proven
        || raw_slice.call_graph_proven
        || raw_slice.semantic_patch_correctness_proven
        || raw_slice.b_minus_approved
        || raw_slice.review_authorized
        || raw_slice.mutation_authorized
        || raw_slice.execution_authorized
        || raw_slice.commit_authorized
        || raw_slice.merge_authorized
        || raw_slice.promotion_authorized
        || raw_slice.provider_effect_authorized
        || raw_slice.public_effect_authorized
        || raw_slice.human_authority
    {
        return Err(RawSliceProjectionErrorV1::RawSliceCeilingWidened);
    }
    if raw_slice.relative_path.trim().is_empty() {
        return Err(RawSliceProjectionErrorV1::RawSliceOwnerNotProven);
    }
    if raw_slice.target_byte_start >= raw_slice.target_byte_end
        || u64::from(raw_slice.target_byte_end) > raw_slice.full_source_byte_len
        || raw_slice.target_slice_byte_len
            != u64::from(raw_slice.target_byte_end - raw_slice.target_byte_start)
    {
        return Err(RawSliceProjectionErrorV1::InvalidSpan);
    }
    require_digest(
        "projection_payload_sha256",
        &raw_slice.projection_payload_sha256,
    )?;
    require_digest("full_source_sha256_hex", &raw_slice.full_source_sha256_hex)?;
    require_digest("target_slice_sha256_hex", &raw_slice.target_slice_sha256_hex)?;
    require_digest(
        "selected_target_semantic_handle_digest_hex",
        &raw_slice.selected_target_semantic_handle_digest_hex,
    )?;
    Ok(())
}

fn require_payload(
    payload: &PortableTargetRawSlicePayloadV1,
) -> Result<(), RawSliceProjectionErrorV1> {
    if payload.raw_slice_version != RAW_SLICE_VERSION {
        return Err(RawSliceProjectionErrorV1::WrongRawSliceVersion);
    }
    if !payload.portable_target_bound_to_exact_current_raw_slice
        || !payload.source_currentness_revalidated_at_materialization
        || !payload.synthetic_record_is_materialization_coordinate_only
        || !payload.semantic_handle_carried_from_portable_owner
    {
        return Err(RawSliceProjectionErrorV1::RawSliceOwnerNotProven);
    }
    if payload.storage_node_identity_minted
        || payload.semantic_handle_derived_from_raw_slice
        || payload.semantic_identity_proven_by_raw_slice
        || payload.producer_authenticated
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
        return Err(RawSliceProjectionErrorV1::RawSliceCeilingWidened);
    }
    if payload.relative_path.trim().is_empty() {
        return Err(RawSliceProjectionErrorV1::RawSliceOwnerNotProven);
    }
    if payload.target_byte_start >= payload.target_byte_end
        || u64::from(payload.target_byte_end) > payload.full_source_byte_len
        || payload.target_slice_byte_len
            != u64::from(payload.target_byte_end - payload.target_byte_start)
    {
        return Err(RawSliceProjectionErrorV1::InvalidSpan);
    }
    require_digest(
        "projection_payload_sha256",
        &payload.projection_payload_sha256,
    )?;
    require_digest("full_source_sha256_hex", &payload.full_source_sha256_hex)?;
    require_digest("target_slice_sha256_hex", &payload.target_slice_sha256_hex)?;
    require_digest(
        "selected_target_semantic_handle_digest_hex",
        &payload.selected_target_semantic_handle_digest_hex,
    )?;
    Ok(())
}

fn require_digest(name: &'static str, value: &str) -> Result<(), RawSliceProjectionErrorV1> {
    if value.len() != 64 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(RawSliceProjectionErrorV1::InvalidDigestField(name));
    }
    Ok(())
}

fn digest_payload(
    payload: &PortableTargetRawSlicePayloadV1,
) -> Result<String, RawSliceProjectionErrorV1> {
    Ok(hex(&Sha256::digest(canonical_payload_bytes(payload)?)))
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut out, "{byte:02x}").expect("String writes do not fail");
    }
    out
}
