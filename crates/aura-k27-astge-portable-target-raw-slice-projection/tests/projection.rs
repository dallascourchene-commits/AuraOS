use aura_k27_astge_portable_target_raw_slice::{
    PortableTargetRawSliceV1, VERSION as RAW_SLICE_VERSION,
};
use aura_k27_astge_portable_target_raw_slice_projection::{
    canonical_payload_bytes, project_portable_target_raw_slice,
    verify_portable_target_raw_slice_projection, RawSliceProjectionErrorV1,
};

fn receipt() -> PortableTargetRawSliceV1 {
    PortableTargetRawSliceV1 {
        version: RAW_SLICE_VERSION,
        projection_payload_sha256: "11".repeat(32),
        file_id: 7,
        relative_path: "src/a.py".to_owned(),
        source_generation: 43,
        full_source_sha256_hex: "22".repeat(32),
        full_source_byte_len: 18,
        target_byte_start: 4,
        target_byte_end: 10,
        target_slice_byte_len: 6,
        target_slice_sha256_hex: "33".repeat(32),
        selected_target_semantic_handle_digest_hex: "44".repeat(32),
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
    }
}

#[test]
fn exact_raw_slice_projects_deterministically_without_authority_widening() {
    let projection = project_portable_target_raw_slice(&receipt()).unwrap();
    verify_portable_target_raw_slice_projection(&projection).unwrap();
    let again = project_portable_target_raw_slice(&receipt()).unwrap();
    assert_eq!(projection, again);
    assert_eq!(
        canonical_payload_bytes(&projection.payload).unwrap(),
        canonical_payload_bytes(&again.payload).unwrap()
    );
    assert_eq!(6, projection.payload.target_slice_byte_len);
    assert_eq!("33".repeat(32), projection.payload.target_slice_sha256_hex);
    assert!(projection.payload.semantic_handle_carried_from_portable_owner);
    assert!(!projection.payload.semantic_handle_derived_from_raw_slice);
    assert!(!projection.payload.semantic_identity_proven_by_raw_slice);
    assert!(!projection.payload.producer_authenticated);
    assert!(!projection.payload.execution_authorized);
}

#[test]
fn digest_tamper_fails_closed() {
    let mut projection = project_portable_target_raw_slice(&receipt()).unwrap();
    projection.payload_sha256 = "aa".repeat(32);
    assert!(matches!(
        verify_portable_target_raw_slice_projection(&projection),
        Err(RawSliceProjectionErrorV1::DigestMismatch)
    ));
}

#[test]
fn semantic_or_effect_authority_widening_fails_before_projection() {
    let mut widened = receipt();
    widened.semantic_handle_derived_from_raw_slice = true;
    assert!(matches!(
        project_portable_target_raw_slice(&widened),
        Err(RawSliceProjectionErrorV1::RawSliceCeilingWidened)
    ));

    let mut effect = receipt();
    effect.commit_authorized = true;
    assert!(matches!(
        project_portable_target_raw_slice(&effect),
        Err(RawSliceProjectionErrorV1::RawSliceCeilingWidened)
    ));
}

#[test]
fn malformed_or_out_of_bounds_span_fails_closed() {
    let mut bad_len = receipt();
    bad_len.target_slice_byte_len = 5;
    assert!(matches!(
        project_portable_target_raw_slice(&bad_len),
        Err(RawSliceProjectionErrorV1::InvalidSpan)
    ));

    let mut out_of_bounds = receipt();
    out_of_bounds.target_byte_end = 19;
    out_of_bounds.target_slice_byte_len = 15;
    assert!(matches!(
        project_portable_target_raw_slice(&out_of_bounds),
        Err(RawSliceProjectionErrorV1::InvalidSpan)
    ));
}

#[test]
fn malformed_digest_fails_closed() {
    let mut bad_digest = receipt();
    bad_digest.target_slice_sha256_hex = "zz".repeat(32);
    assert!(matches!(
        project_portable_target_raw_slice(&bad_digest),
        Err(RawSliceProjectionErrorV1::InvalidDigestField(
            "target_slice_sha256_hex"
        ))
    ));
}
