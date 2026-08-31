use aura_k27_astge_materialize::{AdmittedSourceCatalogV1, MaterializeError, SourceLocatorV1};
use aura_k27_astge_portable_target_raw_slice::{
    admit_portable_target_raw_slice, PortableTargetRawSliceErrorV1,
};
use aura_k27_astge_post_edit_canonical_projection::{
    canonical_payload_bytes, CanonicalDefinitionTargetPayloadV1,
    CanonicalDefinitionTargetProjectionV1, ProjectionErrorV1, CANONICALIZATION_PROFILE_V1,
    PROJECTION_SCHEMA_V1,
};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);
const SOURCE: &[u8] = b"prefix TARGET suffix\n";
const TARGET_START: u32 = 7;
const TARGET_END: u32 = 13;

fn root(label: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let root = std::env::temp_dir().join(format!(
        "aura-portable-target-raw-slice-{label}-{}-{n}",
        std::process::id()
    ));
    fs::create_dir_all(root.join("src")).unwrap();
    root
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn projection_for(source: &[u8]) -> CanonicalDefinitionTargetProjectionV1 {
    let payload = CanonicalDefinitionTargetPayloadV1 {
        schema: PROJECTION_SCHEMA_V1.to_owned(),
        version: 1,
        canonicalization_profile: CANONICALIZATION_PROFILE_V1.to_owned(),
        source_generation_domain: "SOURCE".to_owned(),
        source_generation_value: 9,
        source_owner_ref: "OWNER:CURRENT-SOURCE".to_owned(),
        relative_path: "src/module.py".to_owned(),
        file_id: 77,
        source_sha256_hex: hex(&Sha256::digest(source)),
        source_byte_len: source.len() as u64,
        selected_target_scope_local_id: 11,
        selected_target_parent_scope_local_id: 3,
        selected_target_syntax_ordinal: 8,
        selected_target_byte_start: TARGET_START,
        selected_target_byte_end: TARGET_END,
        selected_target_semantic_handle_digest_hex: "ab".repeat(32),
        definition_name: "target".to_owned(),
        definition_owner_scope_local_id: 3,
        definition_target_scope_local_id: 11,
        selected_current_scope_is_binding_target: true,
        binding_owner_is_selected_parent: true,
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
    reseal(payload)
}

fn reseal(payload: CanonicalDefinitionTargetPayloadV1) -> CanonicalDefinitionTargetProjectionV1 {
    let payload_sha256 = hex(&Sha256::digest(canonical_payload_bytes(&payload).unwrap()));
    CanonicalDefinitionTargetProjectionV1 {
        payload,
        payload_sha256,
    }
}

#[test]
fn exact_projection_materializes_exact_current_target_slice() {
    let root = root("exact");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, SOURCE)],
    )
    .unwrap();
    let projection = projection_for(SOURCE);

    let receipt = admit_portable_target_raw_slice(&catalog, &projection).unwrap();
    assert!(receipt.portable_target_bound_to_exact_current_raw_slice);
    assert!(receipt.source_currentness_revalidated_at_materialization);
    assert!(receipt.synthetic_record_is_materialization_coordinate_only);
    assert!(!receipt.storage_node_identity_minted);
    assert!(receipt.semantic_handle_carried_from_portable_owner);
    assert!(!receipt.semantic_handle_derived_from_raw_slice);
    assert!(!receipt.semantic_identity_proven_by_raw_slice);
    assert_eq!(6, receipt.target_slice_byte_len);
    assert_eq!(
        hex(&Sha256::digest(b"TARGET")),
        receipt.target_slice_sha256_hex
    );
    assert_eq!(
        "ab".repeat(32),
        receipt.selected_target_semantic_handle_digest_hex
    );
    assert!(!receipt.producer_authenticated);
    assert!(!receipt.semantic_patch_correctness_proven);
    assert!(!receipt.commit_authorized);
    assert!(!receipt.human_authority);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn independently_valid_catalog_with_wrong_generation_is_rejected() {
    let root = root("generation");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 10, SOURCE)],
    )
    .unwrap();
    let err = admit_portable_target_raw_slice(&catalog, &projection_for(SOURCE)).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::SourceGenerationMismatch {
            projection: 9,
            catalog: 10
        }
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn independently_valid_catalog_for_other_path_is_rejected() {
    let root = root("path");
    fs::write(root.join("src/other.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/other.py", 9, SOURCE)],
    )
    .unwrap();
    let err = admit_portable_target_raw_slice(&catalog, &projection_for(SOURCE)).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::RelativePathMismatch
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn independently_valid_catalog_for_other_body_is_rejected() {
    let root = root("body");
    let other = b"prefix TARGXT suffix\n";
    assert_eq!(SOURCE.len(), other.len());
    fs::write(root.join("src/module.py"), other).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, other)],
    )
    .unwrap();
    let err = admit_portable_target_raw_slice(&catalog, &projection_for(SOURCE)).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::SourceDigestMismatch
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn source_drift_after_catalog_admission_fails_at_materialization() {
    let root = root("drift");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, SOURCE)],
    )
    .unwrap();
    fs::write(root.join("src/module.py"), b"prefix TARGXT suffix\n").unwrap();
    let err = admit_portable_target_raw_slice(&catalog, &projection_for(SOURCE)).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::Materialize(MaterializeError::DigestMismatch(77))
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn resealed_out_of_bounds_target_span_still_fails_source_materializer() {
    let root = root("span");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, SOURCE)],
    )
    .unwrap();
    let mut payload = projection_for(SOURCE).payload;
    payload.selected_target_byte_end = 500;
    let projection = reseal(payload);
    let err = admit_portable_target_raw_slice(&catalog, &projection).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::Materialize(MaterializeError::InvalidNodeSpan { .. })
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn source_generation_domain_cannot_be_resealed_away_from_source() {
    let root = root("domain");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, SOURCE)],
    )
    .unwrap();
    let mut payload = projection_for(SOURCE).payload;
    payload.source_generation_domain = "PLACEMENT".to_owned();
    let projection = reseal(payload);
    let err = admit_portable_target_raw_slice(&catalog, &projection).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::SourceGenerationDomainNotSource
    ));
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn portable_authority_widening_is_rejected_before_raw_slice_admission() {
    let root = root("authority");
    fs::write(root.join("src/module.py"), SOURCE).unwrap();
    let catalog = AdmittedSourceCatalogV1::admit(
        &root,
        [SourceLocatorV1::bind(77, "src/module.py", 9, SOURCE)],
    )
    .unwrap();
    let mut payload = projection_for(SOURCE).payload;
    payload.commit_authorized = true;
    let projection = reseal(payload);
    let err = admit_portable_target_raw_slice(&catalog, &projection).unwrap_err();
    assert!(matches!(
        err,
        PortableTargetRawSliceErrorV1::Projection(ProjectionErrorV1::CeilingViolation(_))
    ));
    fs::remove_dir_all(root).unwrap();
}
