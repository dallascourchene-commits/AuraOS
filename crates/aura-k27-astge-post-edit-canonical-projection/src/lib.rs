#![forbid(unsafe_code)]

//! Deterministic serialized projection of PR525's typed canonical definition-target receipt.
//! The projection is portable evidence only. It does not authenticate its producer, prove runtime
//! or semantic correctness, or grant review/mutation/execution/commit/merge/effect authority.

use aura_k27_astge_generation_domain::GenerationDomainV1;
use aura_k27_astge_post_edit_canonical_scope::PostEditCanonicalDefinitionTargetCurrentV1;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::fmt::{Display, Formatter, Write as _};

pub const PROJECTION_SCHEMA_V1: &str =
    "AURA_ASTGE_POST_EDIT_CANONICAL_DEFINITION_TARGET_PROJECTION_V1";
pub const CANONICALIZATION_PROFILE_V1: &str = "AURA_SERDE_JSON_STRUCT_ORDER_COMPACT_V1";

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CanonicalDefinitionTargetPayloadV1 {
    pub schema: String,
    pub version: u32,
    pub canonicalization_profile: String,
    pub source_generation_domain: String,
    pub source_generation_value: u64,
    pub source_owner_ref: String,
    pub relative_path: String,
    pub file_id: u64,
    pub source_sha256_hex: String,
    pub source_byte_len: u64,
    pub selected_target_scope_local_id: u64,
    pub selected_target_parent_scope_local_id: u64,
    pub selected_target_syntax_ordinal: u64,
    pub selected_target_byte_start: u32,
    pub selected_target_byte_end: u32,
    pub selected_target_semantic_handle_digest_hex: String,
    pub definition_name: String,
    pub definition_owner_scope_local_id: u64,
    pub definition_target_scope_local_id: u64,
    pub selected_current_scope_is_binding_target: bool,
    pub binding_owner_is_selected_parent: bool,
    pub local_scope_id_is_semantic_identity: bool,
    pub post_edit_profiled_scope_current: bool,
    pub canonical_definition_target_current: bool,
    pub runtime_name_resolution_proven: bool,
    pub call_graph_proven: bool,
    pub semantic_patch_correctness_proven: bool,
    pub b_minus_approved: bool,
    pub producer_authenticated: bool,
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
pub struct CanonicalDefinitionTargetProjectionV1 {
    pub payload: CanonicalDefinitionTargetPayloadV1,
    pub payload_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectionErrorV1 {
    CurrentnessNotProven,
    GenerationMismatch,
    MissingPath,
    MissingParent,
    MissingSyntaxOrdinal,
    MissingSemanticHandle,
    TargetMismatch,
    OwnerMismatch,
    DefinitionNameMismatch,
    LocalScopeSemanticIdentity,
    CeilingViolation(&'static str),
    WrongSchema,
    WrongCanonicalizationProfile,
    Serialization,
    DigestMismatch,
}

impl Display for ProjectionErrorV1 {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "{self:?}")
    }
}
impl Error for ProjectionErrorV1 {}

pub fn project_canonical_definition_target(
    receipt: &PostEditCanonicalDefinitionTargetCurrentV1,
) -> Result<CanonicalDefinitionTargetProjectionV1, ProjectionErrorV1> {
    require_owner_ceiling(receipt)?;
    if !receipt.post_edit_profiled_scope_current
        || !receipt.canonical_definition_target_current
        || !receipt.post_edit_current.post_edit_profiled_scope_current
    {
        return Err(ProjectionErrorV1::CurrentnessNotProven);
    }
    let coordinate = receipt.source_generation.coordinate();
    if coordinate.domain != GenerationDomainV1::Source
        || receipt.source_generation != receipt.post_edit_current.candidate_source_generation
        || receipt.source_generation
            != receipt
                .post_edit_current
                .candidate_current
                .source_generation
    {
        return Err(ProjectionErrorV1::GenerationMismatch);
    }

    let syntax = &receipt.post_edit_current.candidate_current.current_syntax;
    if syntax.relative_path.trim().is_empty() {
        return Err(ProjectionErrorV1::MissingPath);
    }
    let selected = &receipt.post_edit_current.selected_candidate_scope;
    let parent = selected
        .parent_scope_id
        .ok_or(ProjectionErrorV1::MissingParent)?;
    let ordinal = selected
        .syntax_ordinal
        .ok_or(ProjectionErrorV1::MissingSyntaxOrdinal)?;
    let handle = selected
        .semantic_handle_digest
        .ok_or(ProjectionErrorV1::MissingSemanticHandle)?;
    let relation = &receipt.relation;
    if relation.definition_target_scope_id != selected.scope_id {
        return Err(ProjectionErrorV1::TargetMismatch);
    }
    if relation.definition_owner_scope_id != parent {
        return Err(ProjectionErrorV1::OwnerMismatch);
    }
    if relation.definition_name != selected.name {
        return Err(ProjectionErrorV1::DefinitionNameMismatch);
    }
    if relation.local_scope_id_is_semantic_identity {
        return Err(ProjectionErrorV1::LocalScopeSemanticIdentity);
    }

    let payload = CanonicalDefinitionTargetPayloadV1 {
        schema: PROJECTION_SCHEMA_V1.to_owned(),
        version: 1,
        canonicalization_profile: CANONICALIZATION_PROFILE_V1.to_owned(),
        source_generation_domain: "SOURCE".to_owned(),
        source_generation_value: coordinate.value,
        source_owner_ref: syntax.anchor_owner_ref.clone(),
        relative_path: syntax.relative_path.clone(),
        file_id: syntax.file_id,
        source_sha256_hex: hex(&syntax.source_sha256),
        source_byte_len: syntax.source_byte_len,
        selected_target_scope_local_id: selected.scope_id,
        selected_target_parent_scope_local_id: parent,
        selected_target_syntax_ordinal: ordinal,
        selected_target_byte_start: selected.byte_start,
        selected_target_byte_end: selected.byte_end,
        selected_target_semantic_handle_digest_hex: hex(&handle),
        definition_name: relation.definition_name.clone(),
        definition_owner_scope_local_id: relation.definition_owner_scope_id,
        definition_target_scope_local_id: relation.definition_target_scope_id,
        selected_current_scope_is_binding_target: relation.selected_current_scope_is_binding_target,
        binding_owner_is_selected_parent: relation.binding_owner_is_selected_parent,
        local_scope_id_is_semantic_identity: false,
        post_edit_profiled_scope_current: true,
        canonical_definition_target_current: true,
        runtime_name_resolution_proven: false,
        call_graph_proven: false,
        semantic_patch_correctness_proven: false,
        b_minus_approved: false,
        producer_authenticated: false,
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
    Ok(CanonicalDefinitionTargetProjectionV1 {
        payload,
        payload_sha256,
    })
}

pub fn canonical_payload_bytes(
    payload: &CanonicalDefinitionTargetPayloadV1,
) -> Result<Vec<u8>, ProjectionErrorV1> {
    serde_json::to_vec(payload).map_err(|_| ProjectionErrorV1::Serialization)
}

pub fn verify_projection(
    projection: &CanonicalDefinitionTargetProjectionV1,
) -> Result<(), ProjectionErrorV1> {
    let payload = &projection.payload;
    if payload.schema != PROJECTION_SCHEMA_V1 || payload.version != 1 {
        return Err(ProjectionErrorV1::WrongSchema);
    }
    if payload.canonicalization_profile != CANONICALIZATION_PROFILE_V1 {
        return Err(ProjectionErrorV1::WrongCanonicalizationProfile);
    }
    require_payload_ceiling(payload)?;
    if digest_payload(payload)? != projection.payload_sha256 {
        return Err(ProjectionErrorV1::DigestMismatch);
    }
    Ok(())
}

fn require_owner_ceiling(
    receipt: &PostEditCanonicalDefinitionTargetCurrentV1,
) -> Result<(), ProjectionErrorV1> {
    let values = [
        (
            receipt.runtime_name_resolution_proven,
            "runtime_name_resolution_proven",
        ),
        (receipt.call_graph_proven, "call_graph_proven"),
        (
            receipt.semantic_patch_correctness_proven,
            "semantic_patch_correctness_proven",
        ),
        (receipt.b_minus_approved, "b_minus_approved"),
        (receipt.commit_authorized, "commit_authorized"),
        (receipt.execution_authorized, "execution_authorized"),
        (receipt.human_authority, "human_authority"),
        (
            receipt.external_effect_authorized,
            "external_effect_authorized",
        ),
        (
            receipt.post_edit_current.runtime_name_resolution_proven,
            "post_edit.runtime_name_resolution_proven",
        ),
        (
            receipt.post_edit_current.call_graph_proven,
            "post_edit.call_graph_proven",
        ),
        (
            receipt.post_edit_current.semantic_patch_correctness_proven,
            "post_edit.semantic_patch_correctness_proven",
        ),
        (
            receipt.post_edit_current.b_minus_approved,
            "post_edit.b_minus_approved",
        ),
        (
            receipt.post_edit_current.commit_authorized,
            "post_edit.commit_authorized",
        ),
        (
            receipt.post_edit_current.execution_authorized,
            "post_edit.execution_authorized",
        ),
        (
            receipt.post_edit_current.human_authority,
            "post_edit.human_authority",
        ),
        (
            receipt.post_edit_current.external_effect_authorized,
            "post_edit.external_effect_authorized",
        ),
        (
            receipt
                .post_edit_current
                .candidate_current
                .runtime_name_resolution_proven,
            "candidate_current.runtime_name_resolution_proven",
        ),
        (
            receipt
                .post_edit_current
                .candidate_current
                .call_graph_proven,
            "candidate_current.call_graph_proven",
        ),
        (
            receipt
                .post_edit_current
                .candidate_current
                .semantic_k27_derived,
            "candidate_current.semantic_k27_derived",
        ),
        (
            receipt.post_edit_current.candidate_current.human_authority,
            "candidate_current.human_authority",
        ),
        (
            receipt.post_edit_current.candidate_current.external_effect,
            "candidate_current.external_effect",
        ),
    ];
    if let Some((_, name)) = values.into_iter().find(|(value, _)| *value) {
        return Err(ProjectionErrorV1::CeilingViolation(name));
    }
    Ok(())
}

fn require_payload_ceiling(
    payload: &CanonicalDefinitionTargetPayloadV1,
) -> Result<(), ProjectionErrorV1> {
    if !payload.selected_current_scope_is_binding_target
        || !payload.binding_owner_is_selected_parent
        || payload.local_scope_id_is_semantic_identity
        || !payload.post_edit_profiled_scope_current
        || !payload.canonical_definition_target_current
    {
        return Err(ProjectionErrorV1::CurrentnessNotProven);
    }
    let values = [
        (
            payload.runtime_name_resolution_proven,
            "runtime_name_resolution_proven",
        ),
        (payload.call_graph_proven, "call_graph_proven"),
        (
            payload.semantic_patch_correctness_proven,
            "semantic_patch_correctness_proven",
        ),
        (payload.b_minus_approved, "b_minus_approved"),
        (payload.producer_authenticated, "producer_authenticated"),
        (payload.review_authorized, "review_authorized"),
        (payload.mutation_authorized, "mutation_authorized"),
        (payload.execution_authorized, "execution_authorized"),
        (payload.commit_authorized, "commit_authorized"),
        (payload.merge_authorized, "merge_authorized"),
        (payload.promotion_authorized, "promotion_authorized"),
        (
            payload.provider_effect_authorized,
            "provider_effect_authorized",
        ),
        (payload.public_effect_authorized, "public_effect_authorized"),
        (payload.human_authority, "human_authority"),
    ];
    if let Some((_, name)) = values.into_iter().find(|(value, _)| *value) {
        return Err(ProjectionErrorV1::CeilingViolation(name));
    }
    Ok(())
}

fn digest_payload(
    payload: &CanonicalDefinitionTargetPayloadV1,
) -> Result<String, ProjectionErrorV1> {
    Ok(hex(&Sha256::digest(canonical_payload_bytes(payload)?)))
}

fn hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut out, "{byte:02x}").expect("String writes do not fail");
    }
    out
}
