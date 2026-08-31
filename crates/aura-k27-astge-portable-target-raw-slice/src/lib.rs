#![forbid(unsafe_code)]

//! Bind one verified portable canonical target projection to the exact current raw source bytes at
//! its declared target span.
//!
//! PR537 owns the portable target projection. PR480 owns file-ID/current-source materialization.
//! PR480 is already an earned ancestor of PR537, so this crate creates no duplicate source owner and
//! claims no new ancestry edge. It only closes the consumer relation between those two owner APIs.
//!
//! The opaque semantic-handle digest is carried as structural evidence from PR537. It is explicitly
//! **not** derived from, authenticated by, or semantically proven by the raw byte slice.

use aura_k27_astge::NodeIndexRecordV1;
use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, MaterializeError};
use aura_k27_astge_post_edit_canonical_projection::{
    CanonicalDefinitionTargetProjectionV1, ProjectionErrorV1, verify_projection,
};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter, Write as _};

pub const VERSION: &str = "AURA_K27_ASTGE_PORTABLE_TARGET_RAW_SLICE_V1";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PortableTargetRawSliceV1 {
    pub version: &'static str,
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

#[derive(Debug)]
pub enum PortableTargetRawSliceErrorV1 {
    Projection(ProjectionErrorV1),
    SourceGenerationDomainNotSource,
    FileIdOutOfRange(u64),
    UnknownFileId(u32),
    RelativePathMismatch,
    SourceGenerationMismatch { projection: u64, catalog: u64 },
    SourceLengthMismatch { projection: u64, catalog: u64 },
    SourceDigestMismatch,
    EmptyTargetSlice,
    Materialize(MaterializeError),
    MaterializedCoordinateMismatch,
    MaterializedSourceDigestMismatch,
}

impl Display for PortableTargetRawSliceErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for PortableTargetRawSliceErrorV1 {}

impl From<ProjectionErrorV1> for PortableTargetRawSliceErrorV1 {
    fn from(value: ProjectionErrorV1) -> Self {
        Self::Projection(value)
    }
}
impl From<MaterializeError> for PortableTargetRawSliceErrorV1 {
    fn from(value: MaterializeError) -> Self {
        Self::Materialize(value)
    }
}

/// Admit only a portable target whose source locator and exact raw span can be independently
/// revalidated through the current-source materialization owner.
pub fn admit_portable_target_raw_slice(
    catalog: &AdmittedSourceCatalogV1,
    projection: &CanonicalDefinitionTargetProjectionV1,
) -> Result<PortableTargetRawSliceV1, PortableTargetRawSliceErrorV1> {
    verify_projection(projection)?;
    let payload = &projection.payload;
    if payload.source_generation_domain != "SOURCE" {
        return Err(PortableTargetRawSliceErrorV1::SourceGenerationDomainNotSource);
    }
    let file_id = u32::try_from(payload.file_id)
        .map_err(|_| PortableTargetRawSliceErrorV1::FileIdOutOfRange(payload.file_id))?;
    if payload.selected_target_byte_start >= payload.selected_target_byte_end {
        return Err(PortableTargetRawSliceErrorV1::EmptyTargetSlice);
    }

    let locator = catalog
        .locator(file_id)
        .ok_or(PortableTargetRawSliceErrorV1::UnknownFileId(file_id))?;
    if locator.relative_path != payload.relative_path {
        return Err(PortableTargetRawSliceErrorV1::RelativePathMismatch);
    }
    if locator.source_generation != payload.source_generation_value {
        return Err(PortableTargetRawSliceErrorV1::SourceGenerationMismatch {
            projection: payload.source_generation_value,
            catalog: locator.source_generation,
        });
    }
    if locator.byte_len != payload.source_byte_len {
        return Err(PortableTargetRawSliceErrorV1::SourceLengthMismatch {
            projection: payload.source_byte_len,
            catalog: locator.byte_len,
        });
    }
    let locator_sha = hex(&locator.sha256);
    if locator_sha != payload.source_sha256_hex {
        return Err(PortableTargetRawSliceErrorV1::SourceDigestMismatch);
    }

    // PR480 materializes by file ID + byte span. The remaining storage fields are intentionally
    // neutral because this child does not mint a storage node identity from a portable target.
    let coordinate = NodeIndexRecordV1 {
        node_id: 0,
        semantic_handle_digest: [0; 32],
        pbn: 0,
        row: 0,
        out_degree: 0,
        file_id,
        byte_start: payload.selected_target_byte_start,
        byte_end: payload.selected_target_byte_end,
    };
    let materialized = catalog.materialize_node(&coordinate)?;
    if materialized.file_id != file_id
        || materialized.relative_path != payload.relative_path
        || materialized.source_generation != payload.source_generation_value
        || materialized.byte_start != payload.selected_target_byte_start
        || materialized.byte_end != payload.selected_target_byte_end
    {
        return Err(PortableTargetRawSliceErrorV1::MaterializedCoordinateMismatch);
    }
    if hex(&materialized.source_sha256) != payload.source_sha256_hex {
        return Err(PortableTargetRawSliceErrorV1::MaterializedSourceDigestMismatch);
    }

    Ok(PortableTargetRawSliceV1 {
        version: VERSION,
        projection_payload_sha256: projection.payload_sha256.clone(),
        file_id,
        relative_path: payload.relative_path.clone(),
        source_generation: payload.source_generation_value,
        full_source_sha256_hex: payload.source_sha256_hex.clone(),
        full_source_byte_len: payload.source_byte_len,
        target_byte_start: payload.selected_target_byte_start,
        target_byte_end: payload.selected_target_byte_end,
        target_slice_byte_len: materialized.bytes.len() as u64,
        target_slice_sha256_hex: hex(&Sha256::digest(&materialized.bytes)),
        selected_target_semantic_handle_digest_hex: payload
            .selected_target_semantic_handle_digest_hex
            .clone(),
        portable_target_bound_to_exact_current_raw_slice: true,
        source_currentness_revalidated_at_materialization: materialized
            .source_currentness_verified,
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
    })
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut out, "{byte:02x}").expect("String writes do not fail");
    }
    out
}
