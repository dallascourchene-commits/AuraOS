mod common;

use aura_k27_astge_post_edit_canonical_projection::{
    CanonicalDefinitionTargetProjectionV1, CANONICALIZATION_PROFILE_V1, PROJECTION_SCHEMA_V1,
    ProjectionErrorV1, project_canonical_definition_target, verify_projection,
};
use common::{owner_receipt, setup};
use serde_json::Value;
use std::fs;

#[test]
fn typed_owner_receipt_projects_to_stable_source_bound_envelope() {
    let setup = setup("positive");
    let receipt = owner_receipt(&setup);
    let first = project_canonical_definition_target(&receipt).unwrap();
    let second = project_canonical_definition_target(&receipt).unwrap();

    assert_eq!(first, second);
    assert_eq!(first.payload.schema, PROJECTION_SCHEMA_V1);
    assert_eq!(
        first.payload.canonicalization_profile,
        CANONICALIZATION_PROFILE_V1
    );
    assert_eq!(first.payload.source_generation_domain, "SOURCE");
    assert_eq!(first.payload.source_generation_value, 13);
    assert_eq!(first.payload.relative_path, "src/module.py");
    assert_eq!(first.payload.file_id, 177);
    assert_eq!(first.payload.definition_name, "inner");
    assert!(first.payload.selected_current_scope_is_binding_target);
    assert!(first.payload.binding_owner_is_selected_parent);
    assert!(!first.payload.local_scope_id_is_semantic_identity);
    assert!(!first.payload.producer_authenticated);
    verify_projection(&first).unwrap();

    let encoded = serde_json::to_vec(&first).unwrap();
    let decoded: CanonicalDefinitionTargetProjectionV1 = serde_json::from_slice(&encoded).unwrap();
    assert_eq!(decoded, first);
    verify_projection(&decoded).unwrap();
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn owner_relation_and_authority_substitutions_fail_closed() {
    let setup = setup("mutants");
    let receipt = owner_receipt(&setup);

    let mut wrong_target = receipt.clone();
    wrong_target.relation.definition_target_scope_id += 1;
    assert_eq!(
        project_canonical_definition_target(&wrong_target),
        Err(ProjectionErrorV1::TargetMismatch)
    );

    let mut semantic_local_id = receipt.clone();
    semantic_local_id.relation.local_scope_id_is_semantic_identity = true;
    assert_eq!(
        project_canonical_definition_target(&semantic_local_id),
        Err(ProjectionErrorV1::LocalScopeSemanticIdentity)
    );

    let mut elevated = receipt;
    elevated.commit_authorized = true;
    assert_eq!(
        project_canonical_definition_target(&elevated),
        Err(ProjectionErrorV1::CeilingViolation("commit_authorized"))
    );
    fs::remove_dir_all(setup.root).unwrap();
}

#[test]
fn payload_tamper_and_schema_widening_are_detected() {
    let setup = setup("transport");
    let receipt = owner_receipt(&setup);
    let projection = project_canonical_definition_target(&receipt).unwrap();

    let mut tampered = projection.clone();
    tampered.payload.definition_name.push_str("_tampered");
    assert_eq!(verify_projection(&tampered), Err(ProjectionErrorV1::DigestMismatch));

    let mut value: Value = serde_json::to_value(&projection).unwrap();
    value
        .as_object_mut()
        .unwrap()
        .insert("parallel_truth_plane".to_owned(), Value::Bool(true));
    assert!(serde_json::from_value::<CanonicalDefinitionTargetProjectionV1>(value).is_err());
    fs::remove_dir_all(setup.root).unwrap();
}
