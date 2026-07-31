from pascal_spatial_presentation_test_support import *  # noqa: F401,F403


def test_exact_pinned_pascal_fixture_and_spatial_scene_are_valid():
    lock, manifest, coordinate, scene = fixture()
    assert (lock.repository, lock.commit, lock.license) == (
        PASCAL_REPOSITORY,
        PASCAL_COMMIT,
        PASCAL_LICENSE,
    )
    assert lock.lock_digest == FIXTURE_DIGESTS["lock"]
    assert manifest.artifact_digest == FIXTURE_DIGESTS["artifact"]
    assert coordinate.spatial_scene_digest == FIXTURE_DIGESTS["scene"]
    assert coordinate.receipt_digest == FIXTURE_DIGESTS["coordinate"]
    assert scene["external_asset_fetch"] is False
    assert scene["persistent_canonical_storage"] is False
    assert {item.name: item.version for item in lock.packages} == {
        "@pascal-app/core": "0.9.2",
        "@pascal-app/viewer": "0.9.2",
        "@pascal-app/editor": "0.9.2",
        "@pascal-app/nodes": "0.1.1",
    }


@pytest.mark.parametrize(
    "schema_name,document_path",
    [
        ("aura_pascal_source_lock_v1.schema.json", "third_party/pascal/pascal-lock.json"),
        (
            "aura_pascal_scene_artifact_manifest_v1.schema.json",
            "aura_showcase/pascal-workbench/artifact-manifest.json",
        ),
        (
            "aura_pascal_coordinate_receipt_v1.schema.json",
            "aura_showcase/pascal-workbench/coordinate-receipt.json",
        ),
    ],
)
def test_committed_pascal_contracts_validate_against_schemas(
    schema_name,
    document_path,
):
    schema = json.loads((ROOT / "schemas" / schema_name).read_text())
    document = json.loads((ROOT / document_path).read_text())
    Draft202012Validator(schema).validate(document)


def test_scene_asset_tampering_fails_closed(tmp_path):
    copy = tmp_path / "repo"
    shutil.copytree(ROOT / "third_party", copy / "third_party")
    shutil.copytree(
        ROOT / "aura_showcase/pascal-workbench",
        copy / "aura_showcase/pascal-workbench",
    )
    for name in (
        "pascal-construction-foundry.js",
        "pascal-construction-foundry.css",
    ):
        shutil.copy2(
            ROOT / "aura_showcase" / name,
            copy / "aura_showcase" / name,
        )
    (copy / "aura_showcase/pascal-workbench/fixture.json").write_text(
        '{"tampered":true}\n'
    )
    with pytest.raises(PascalPresentationError, match="digest mismatch"):
        load_pascal_compatibility_fixture(str(copy))


def test_source_lock_rejects_recomputed_but_unapproved_package_identity():
    raw = json.loads((ROOT / "third_party/pascal/pascal-lock.json").read_text())
    raw["packages"][0]["version"] = "999.0.0"
    body = {key: value for key, value in raw.items() if key != "lock_digest"}
    raw["lock_digest"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    with pytest.raises(PascalPresentationError, match="approved source lock"):
        PascalSourceLock.from_mapping(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("storey_ids", 7),
        ("node_bindings", {"bad": "shape"}),
    ],
)
def test_manifest_structural_type_errors_fail_as_contract_errors(field, value):
    raw = json.loads(
        (ROOT / "aura_showcase/pascal-workbench/artifact-manifest.json").read_text()
    )
    raw[field] = value
    with pytest.raises(PascalPresentationError):
        PascalSceneArtifactManifest.from_mapping(raw)


def test_cross_runtime_bridge_number_digest_vector_is_stable():
    vector = {
        "small": 1e-7,
        "negative_zero": -0.0,
        "integer": 42,
        "text": "é",
        "nested": [True, None, 0.5],
    }
    assert bridge_sha256(vector) == (
        "ae7ac10cc242d18afe68d4a911cdb6a28de1739e2acc0fe7c31f8b5f803ce3cf"
    )


@pytest.mark.parametrize("delta", [1, 16])
def test_bridge_payload_byte_ceiling_is_enforced(delta):
    active = session()
    with pytest.raises(PascalPresentationError, match="MAX_BRIDGE_PAYLOAD_BYTES"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload={"data": "x" * (MAX_BRIDGE_PAYLOAD_BYTES + delta)},
        )


def test_bridge_payload_depth_and_non_mapping_are_rejected():
    active = session()
    deep = {}
    cursor = deep
    for _ in range(MAX_BRIDGE_DEPTH + 2):
        cursor["level"] = {}
        cursor = cursor["level"]
    with pytest.raises(PascalPresentationError, match="MAX_BRIDGE_DEPTH"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload=deep,
        )
    with pytest.raises(PascalPresentationError, match="mapping"):
        AuraPascalBridgeMessage.build(
            session_id=active.session_id,
            sequence=1,
            spatial_scene_digest=active.spatial_scene_digest,
            render_plan_digest=active.render_plan_digest,
            pascal_artifact_digest=active.manifest.artifact_digest,
            coordinate_receipt_digest=active.coordinate_receipt.receipt_digest,
            state_binding_digest=active.state_binding_digest,
            direction=BridgeDirection.PARENT_TO_PASCAL,
            action=PascalBridgeAction.LOAD_ARTIFACT,
            payload=["not", "a", "mapping"],
        )


def test_ready_is_required_and_actual_origin_is_exact():
    active = session()
    with pytest.raises(PascalPresentationError, match="not_admitted"):
        active.issue_parent_message(PascalBridgeAction.LOAD_ARTIFACT, {})
    message = child_message(
        active,
        PascalBridgeAction.READY,
        {"renderer_kind": "test", "external_requests": 0, "working_copy_only": True},
        sequence=1,
        nonce="wrong-origin",
    )
    with pytest.raises(PascalPresentationError, match="origin"):
        active.accept(message, origin="http://localhost:8000")
    result = active.accept(message, origin=active.expected_origin)
    assert result["state"] == "READY"
    assert set(result["spatial_interaction"]["intent_slots"]) == {
        "DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM",
    }


def test_parent_sequence_advances_only_after_exact_postcondition():
    active = session()
    ready(active)
    _, manifest, _, scene = fixture()
    command = active.issue_parent_message(
        PascalBridgeAction.LOAD_ARTIFACT,
        {
            "scene": scene,
            "artifact_manifest": manifest.to_dict(),
            "initial_view": "2D",
            "dimensions_visible": True,
        },
    )
    contradictory = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "3D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="contradictory",
    )
    with pytest.raises(PascalPresentationError, match="differs"):
        active.accept(contradictory, origin=active.expected_origin)
    exact = child_message(
        active,
        PascalBridgeAction.LOAD_RECEIPT,
        {
            "command_message_digest": command.message_digest,
            "loaded": True,
            "view": "2D",
            "storey_id": "L1",
            "node_id": manifest.root_node_id,
            "dimensions_visible": True,
            "node_count": len(manifest.node_bindings),
            "external_requests": 0,
        },
        sequence=2,
        nonce="exact",
    )
    assert active.accept(exact, origin=active.expected_origin)["state"] == "ACTIVE"
