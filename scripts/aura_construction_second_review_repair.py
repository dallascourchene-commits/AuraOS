#!/usr/bin/env python3
"""Apply the bounded PR #187 second deep-review repairs."""

from __future__ import annotations

from pathlib import Path
import textwrap


def formatted_block(value: str, indent: int = 0) -> str:
    normalized = textwrap.dedent(value).lstrip("\n")
    return textwrap.indent(normalized, " " * indent)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"already repaired: {label}")
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one old span, found {count}")
    print(f"repairing: {label}")
    return text.replace(old, new, 1)


def repair_projection() -> None:
    path = Path("aura_construction_demo_projection.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    zone_entities: dict[str, str] = {}\n"
        "    package_entities: dict[str, str] = {}\n"
        "    for package in fixture.work_packages:\n"
        "        storey_entity_id = storey_entities[package.storey_id]\n",
        "    zone_entities: dict[str, str] = {}\n"
        "    package_entities: dict[str, str] = {}\n"
        "    package_frames: dict[str, str] = {}\n"
        "    for package in fixture.work_packages:\n"
        "        storey_entity_id = storey_entities[package.storey_id]\n"
        "        package_frame_id = next(\n"
        "            item.frame_id for item in storeys if item.storey_id == package.storey_id\n"
        "        )\n"
        "        package_frames[package.work_package_id] = package_frame_id\n",
        "package frame index",
    )
    frame_lookup = (
        "                    next(item.frame_id for item in storeys if item.storey_id == package.storey_id),\n"
    )
    if "                    package_frame_id,\n" not in text:
        count = text.count(frame_lookup)
        if count != 2:
            raise RuntimeError(f"package frame lookup: expected two spans, found {count}")
        print("repairing: package frame consumers")
        text = text.replace(frame_lookup, "                    package_frame_id,\n", 2)

    owner_replacements = {
        "                activity.note,\n                building_frame_id,\n":
            "                activity.note,\n                package_frames[activity.work_package_id],\n",
        "                budget.description,\n                building_frame_id,\n":
            "                budget.description,\n                package_frames[budget.work_package_id],\n",
        "                inspection.title,\n                building_frame_id,\n":
            "                inspection.title,\n                package_frames[inspection.work_package_id],\n",
        "                hazard.title,\n                building_frame_id,\n":
            "                hazard.title,\n                package_frames[hazard.work_package_id],\n",
    }
    for old, new in owner_replacements.items():
        text = replace_once(text, old, new, new.splitlines()[1].strip())

    if '"work_package_ref": _ref(package_id, privacy),' not in text:
        start = text.index("    for rule in fixture.rules:\n")
        end = text.index("\n    for inspection in fixture.inspections:\n", start)
        replacement = formatted_block(
            '''
            for rule in fixture.rules:
                for package_id in rule.applies_to_work_package_ids:
                    entity_id = _id(
                        "construction-rule",
                        {"rule_id": rule.rule_id, "work_package_id": package_id},
                    )
                    entities.append(
                        _entity(
                            entity_id,
                            SpatialEntityType.DOMAIN_NODE,
                            rule.title,
                            package_frames[package_id],
                            source_refs=(_ref(f"construction-demo-rule:{rule.rule_id}", privacy),)
                            if privacy is not SpatialPrivacyClass.PROJECT
                            else (f"construction-demo-rule:{rule.rule_id}",),
                            metadata={
                                "rule_ref": _ref(rule.rule_id, privacy),
                                "work_package_ref": _ref(package_id, privacy),
                                "requirement": rule.requirement,
                                "truth_class": rule.truth_class,
                                "legal_authority": False,
                                "regulatory_authority": False,
                                "jurisdiction_claimed": "none",
                                "projection_only": True,
                            },
                        )
                    )
                    links.append(
                        _link(
                            package_entities[package_id],
                            entity_id,
                            "REQUIRES_SYNTHETIC_RULE",
                            source_refs=(_ref(f"construction-demo-rule:{rule.rule_id}", privacy),)
                            if privacy is not SpatialPrivacyClass.PROJECT
                            else (f"construction-demo-rule:{rule.rule_id}",),
                        )
                    )
            ''',
            4,
        )
        print("repairing: per-package synthetic rule overlays")
        text = text[:start] + replacement + text[end:]

    if "    scene_source_refs = (\n" not in text:
        refs = formatted_block(
            '''
            scene_source_refs = (
                "owner:aura_construction_state.ConstructionProjectState",
                "owner:aura_construction_adapter.ConstructionArenaAdapter",
                "owner:aura_construction_demo_contracts.ConstructionDemoAssetPack",
                "projection:aura_spatial_construction.project_construction_state_to_scene",
                "projection:aura_construction_demo_projection.project_construction_demo_to_scene",
                f"canonical-base-scene:{baseline.scene_digest}",
                f"construction-state:{fixture.state.state_digest}",
                f"construction-runtime:{packet['evaluation']['evaluation_digest']}",
                f"construction-demo-fixture:{fixture.fixture_digest}",
                f"construction-demo-asset-pack:{asset_pack.asset_pack_digest}",
            )
            if privacy is not SpatialPrivacyClass.PROJECT:
                scene_source_refs = tuple(_ref(ref, privacy) for ref in scene_source_refs)

            ''',
            4,
        )
        print("repairing: scene-level PUBLIC provenance")
        text = text.replace("    return compile_spatial_scene(\n", refs + "    return compile_spatial_scene(\n", 1)
    raw_source_start = (
        '        source_refs=(\n            "owner:aura_construction_state.ConstructionProjectState",\n'
    )
    if "        source_refs=scene_source_refs,\n" not in text:
        start = text.index(raw_source_start)
        end = text.index("        renderer_hints={\n", start)
        text = text[:start] + "        source_refs=scene_source_refs,\n" + text[end:]

    path.write_text(text, encoding="utf-8")


def repair_renderer() -> None:
    path = Path("aura_spatial_web/construction_scene_renderer.js")
    text = path.read_text(encoding="utf-8")
    if "function resolveWorldTransform(" not in text:
        helpers = formatted_block(
            '''
            function quaternionMultiply(left, right) {
              const [lx, ly, lz, lw] = left;
              const [rx, ry, rz, rw] = right;
              return Object.freeze([
                lw * rx + lx * rw + ly * rz - lz * ry,
                lw * ry - lx * rz + ly * rw + lz * rx,
                lw * rz + lx * ry - ly * rx + lz * rw,
                lw * rw - lx * rx - ly * ry - lz * rz,
              ]);
            }

            function rotateVector(rotation, vector) {
              const [x, y, z, w] = rotation;
              const [vx, vy, vz] = vector;
              const tx = 2 * (y * vz - z * vy);
              const ty = 2 * (z * vx - x * vz);
              const tz = 2 * (x * vy - y * vx);
              return [
                vx + w * tx + (y * tz - z * ty),
                vy + w * ty + (z * tx - x * tz),
                vz + w * tz + (x * ty - y * tx),
              ];
            }

            function composeTransforms(parent, local) {
              const scaledLocal = local.translation.map((value, index) => value * parent.scale[index]);
              const rotatedLocal = rotateVector(parent.rotation_xyzw, scaledLocal);
              return Object.freeze({
                translation: Object.freeze(
                  parent.translation.map((value, index) => value + rotatedLocal[index]),
                ),
                rotation_xyzw: quaternionMultiply(parent.rotation_xyzw, local.rotation_xyzw),
                scale: Object.freeze(
                  parent.scale.map((value, index) => value * local.scale[index]),
                ),
              });
            }

            function resolveWorldTransform(frames, frameId, cache, active = new Set()) {
              if (cache.has(frameId)) return cache.get(frameId);
              if (active.has(frameId)) throw new TypeError("Construction coordinate-frame cycle detected");
              const frame = frames.get(frameId);
              if (!frame) throw new TypeError(`Construction frame is missing: ${frameId}`);
              active.add(frameId);
              const local = canonicalTransform(frame, `frame ${frameId}`);
              const world = frame.parent_frame_id
                ? composeTransforms(
                    resolveWorldTransform(frames, frame.parent_frame_id, cache, active),
                    local,
                  )
                : local;
              active.delete(frameId);
              cache.set(frameId, world);
              return world;
            }

            ''',
        )
        print("repairing: parent coordinate-frame composition")
        text = text.replace("function viewProjection(renderer) {\n", helpers + "function viewProjection(renderer) {\n", 1)
    text = replace_once(
        text,
        "    const rawFrames = new Map(scenePayload.frames.map((frame) => [frame.frame_id, frame]));\n"
        "    for (const frameId of this.storeyFrames) {\n"
        "      const frame = rawFrames.get(frameId);\n"
        "      if (!frame) throw new TypeError(\"Construction storey frame is missing\");\n"
        "      const transform = canonicalTransform(frame, `frame ${frameId}`);\n"
        "      this.basePresentationTransforms.set(frameId, transform);\n"
        "      this.presentationTransforms.set(frameId, transform);\n"
        "    }\n",
        "    const rawFrames = new Map(scenePayload.frames.map((frame) => [frame.frame_id, frame]));\n"
        "    const worldTransforms = new Map();\n"
        "    for (const frameId of this.storeyFrames) {\n"
        "      const transform = resolveWorldTransform(rawFrames, frameId, worldTransforms);\n"
        "      this.basePresentationTransforms.set(frameId, transform);\n"
        "      this.presentationTransforms.set(frameId, transform);\n"
        "    }\n",
        "world transform resolution",
    )
    path.write_text(text, encoding="utf-8")


def repair_python_tests() -> None:
    path = Path("tests/test_aura_construction_demo_projection.py")
    text = path.read_text(encoding="utf-8")
    if 'len(ref) == 16 and set(ref) <= set("0123456789abcdef")' not in text:
        anchor = "    all_source_refs.extend(payload.get(\"source_refs\", []))\n\n"
        assertion = formatted_block(
            '''
            assert payload["source_refs"]
            assert all(
                len(ref) == 16 and set(ref) <= set("0123456789abcdef")
                for ref in payload["source_refs"]
            )

            ''',
            4,
        )
        text = replace_once(text, anchor, anchor + assertion, "PUBLIC scene-level source refs test")
    if "def test_g5_package_owned_overlays_use_package_storey_frames" not in text:
        test_block = formatted_block(
            '''

            def test_g5_package_owned_overlays_use_package_storey_frames() -> None:
                fixture, scene = _scene()
                entities = scene.to_dict()["entities"]
                storey_frames = {item.storey_id: item.frame_id for item in fixture.asset_pack.storeys}
                package_frames = {
                    item.work_package_id: storey_frames[item.storey_id]
                    for item in fixture.work_packages
                }

                for activity in fixture.work_history:
                    matches = [item for item in entities if item["metadata"].get("activity_ref") == activity.activity_id]
                    assert len(matches) == 1
                    assert matches[0]["frame_id"] == package_frames[activity.work_package_id]
                for budget in fixture.budget_lines:
                    matches = [item for item in entities if item["metadata"].get("budget_line_ref") == budget.budget_line_id]
                    assert len(matches) == 1
                    assert matches[0]["frame_id"] == package_frames[budget.work_package_id]
                for inspection in fixture.inspections:
                    matches = [item for item in entities if item["metadata"].get("inspection_ref") == inspection.inspection_id]
                    assert len(matches) == 1
                    assert matches[0]["frame_id"] == package_frames[inspection.work_package_id]
                for hazard in fixture.hazards:
                    matches = [item for item in entities if item["metadata"].get("hazard_ref") == hazard.hazard_id]
                    assert len(matches) == 1
                    assert matches[0]["frame_id"] == package_frames[hazard.work_package_id]
                for rule in fixture.rules:
                    actual_frames = sorted(
                        item["frame_id"]
                        for item in entities
                        if item["metadata"].get("rule_ref") == rule.rule_id
                    )
                    expected_frames = sorted(
                        package_frames[package_id]
                        for package_id in rule.applies_to_work_package_ids
                    )
                    assert actual_frames == expected_frames
            ''',
        )
        marker = "\ndef test_g5_rejects_restricted_or_sensitive_geometry_projection() -> None:\n"
        text = replace_once(text, marker, test_block + marker, "package overlay regression")
    path.write_text(text, encoding="utf-8")


def repair_javascript_tests() -> None:
    path = Path("tests/js/spatial-construction-review-regressions.test.mjs")
    text = path.read_text(encoding="utf-8")
    if "composes translated rotated and scaled parent frames" not in text:
        test_block = formatted_block(
            '''

            test("Construction renderer composes translated rotated and scaled parent frames", async () => {
              const { scene, plan } = meshScene();
              const root = scene.frames.find((item) => item.frame_id === "frame:root");
              root.translation = [10, 0, 0];
              root.rotation_xyzw = [0, 0, 1, 0];
              root.scale = [2, 2, 2];
              const presentation = new PresentationRenderer();
              const renderer = new ConstructionSceneRenderer({
                presentationRenderer: presentation,
                meshPass: new ConstructionMeshPass({ drawMeshPass: async () => () => {} }),
                overlayPass: new ConstructionOverlayPass(),
              });
              await renderer.initialize(scene, plan, {
                meshPayloads: [
                  {
                    asset_id: "asset:mesh:one",
                    source_digest: "1".repeat(64),
                    decoded_byte_length: 128,
                    resource: { local: true },
                  },
                  {
                    asset_id: "asset:mesh:two",
                    source_digest: "2".repeat(64),
                    decoded_byte_length: 128,
                    resource: { local: true },
                  },
                ],
              });
              assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").translation, [10, -8, 0]);
              assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").rotation_xyzw, [0, 0, 1, 0]);
              assert.deepEqual(renderer.getAssetRenderTransform("asset:mesh:one").scale, [2, 2, 2]);
              await renderer.dispose();
            });
            ''',
        )
        marker = '\ntest("Construction renderer rejects higher-order splats before initializing owners", async () => {\n'
        text = replace_once(text, marker, test_block + marker, "parent frame regression")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    print("repair_projection")
    repair_projection()
    print("repair_renderer")
    repair_renderer()
    print("repair_python_tests")
    repair_python_tests()
    print("repair_javascript_tests")
    repair_javascript_tests()
    print("repair script completed")


if __name__ == "__main__":
    main()
