#!/usr/bin/env python3
"""Apply the fourth exact-head Codex repair set for PR #187."""

from __future__ import annotations

import io
from pathlib import Path
import tokenize


ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


def absolute_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def scope_project_ref_calls(text: str) -> str:
    """Add the export scope to every _ref call inside the projection function."""

    marker = "def project_construction_demo_to_scene("
    marker_index = text.index(marker)
    marker_line = text.count("\n", 0, marker_index) + 1
    offsets = absolute_offsets(text)

    def absolute(position: tuple[int, int]) -> int:
        line, column = position
        return offsets[line - 1] + column

    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    insertions: list[int] = []
    for index, token in enumerate(tokens[:-1]):
        if token.type != tokenize.NAME or token.string != "_ref" or token.start[0] < marker_line:
            continue
        open_token = tokens[index + 1]
        if open_token.type != tokenize.OP or open_token.string != "(":
            continue
        depth = 0
        close_token = None
        for candidate in tokens[index + 1 :]:
            if candidate.type != tokenize.OP:
                continue
            if candidate.string == "(":
                depth += 1
            elif candidate.string == ")":
                depth -= 1
                if depth == 0:
                    close_token = candidate
                    break
        if close_token is None:
            raise RuntimeError("unterminated _ref call")
        call_body = text[absolute(open_token.end) : absolute(close_token.start)]
        if "public_export_scope" not in call_body:
            insertions.append(absolute(close_token.start))

    for insertion in reversed(insertions):
        text = text[:insertion] + ", public_export_scope" + text[insertion:]
    return text


def patch_projection() -> None:
    path = ROOT / "aura_construction_demo_projection.py"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''def _ref(value: str, privacy: SpatialPrivacyClass) -> str:\n    if privacy is SpatialPrivacyClass.PROJECT:\n        return value\n    return stable_digest({"construction_demo_public_ref": value})[:16]\n''',
        '''def _ref(\n    value: str,\n    privacy: SpatialPrivacyClass,\n    export_scope: str | None = None,\n) -> str:\n    if privacy is SpatialPrivacyClass.PROJECT:\n        return value\n    if export_scope is not None:\n        return _export_ref(value, export_scope)\n    return stable_digest({"construction_demo_public_ref": value})[:16]\n''',
        "export-scoped public refs",
    )

    scope_anchor = '''    public_export_scope = stable_digest(\n        {\n            "projection_version": CONSTRUCTION_DEMO_PROJECTION_VERSION,\n            "scene_id": scene_id,\n            "purpose_digest": purpose_digest,\n        },\n        digest_size=32,\n    )\n\n'''
    scope_helpers = scope_anchor + '''    def graph_id(prefix: str, payload: Any) -> str:\n        if privacy is SpatialPrivacyClass.PROJECT:\n            return _id(prefix, payload)\n        return _id(\n            f"public-{prefix}",\n            {"export_scope": public_export_scope, "payload": payload},\n        )\n\n    def graph_frame_id(kind: str, value: str) -> str:\n        if privacy is SpatialPrivacyClass.PROJECT:\n            return value\n        return _id(\n            f"public-{kind}-frame",\n            {"export_scope": public_export_scope, "value": value},\n        )\n\n    def public_text(value: str, generic: str) -> str:\n        return value if privacy is SpatialPrivacyClass.PROJECT else generic\n\n'''
    text = replace_once(text, scope_anchor, scope_helpers, "public graph helper insertion")

    text = replace_once(
        text,
        '''    root_frame_id = "construction-site-root"\n    building_frame_id = asset_pack.building_frame_id\n''',
        '''    root_frame_id = graph_frame_id("site-root", "construction-site-root")\n    building_frame_id = graph_frame_id("building", asset_pack.building_frame_id)\n    storey_frame_ids = {\n        item.storey_id: graph_frame_id("storey", item.frame_id) for item in storeys\n    }\n''',
        "public frame aliases",
    )
    text = replace_count(
        text,
        "                frame_id=storey.frame_id,",
        "                frame_id=storey_frame_ids[storey.storey_id],",
        2,
        "storey frame references",
    )
    text = replace_once(
        text,
        "            frame_id=next(item.frame_id for item in storeys if item.storey_id == binding.storey_id),",
        "            frame_id=storey_frame_ids[binding.storey_id],",
        "asset frame alias",
    )
    text = replace_once(
        text,
        "        package_frame_id = next(item.frame_id for item in storeys if item.storey_id == package.storey_id)",
        "        package_frame_id = storey_frame_ids[package.storey_id]",
        "package frame alias",
    )

    graph_replacements = (
        (
            '    building_entity_id = _id("construction-building", asset_pack.building_id)',
            '    building_entity_id = graph_id("construction-building", asset_pack.building_id)',
            "building entity alias",
        ),
        (
            '        entity_id = _id("construction-storey", storey.storey_id)',
            '        entity_id = graph_id("construction-storey", storey.storey_id)',
            "storey entity alias",
        ),
        (
            '            zone_entity_id = _id("construction-zone", package.zone_id)',
            '            zone_entity_id = graph_id("construction-zone", package.zone_id)',
            "zone entity alias",
        ),
        (
            '        package_entity_id = _id("construction-work-package", package.work_package_id)',
            '        package_entity_id = graph_id("construction-work-package", package.work_package_id)',
            "package entity alias",
        ),
        (
            '                evidence_entity_id = _id("construction-evidence-requirement", evidence_ref)',
            '                evidence_entity_id = graph_id("construction-evidence-requirement", evidence_ref)',
            "evidence entity alias",
        ),
        (
            '        entity_id = _id("construction-trade", trade.trade_id)',
            '        entity_id = graph_id("construction-trade", trade.trade_id)',
            "trade entity alias",
        ),
        (
            '        activity_entity_id = _id("construction-activity", activity.activity_id)',
            '        activity_entity_id = graph_id("construction-activity", activity.activity_id)',
            "activity entity alias",
        ),
        (
            '        entity_id = _id("construction-budget", budget.budget_line_id)',
            '        entity_id = graph_id("construction-budget", budget.budget_line_id)',
            "budget entity alias",
        ),
        (
            '''            entity_id = _id(\n                "construction-rule",\n                {"rule_id": rule.rule_id, "work_package_id": package_id},\n            )''',
            '''            entity_id = graph_id(\n                "construction-rule",\n                {"rule_id": rule.rule_id, "work_package_id": package_id},\n            )''',
            "rule entity alias",
        ),
        (
            '        entity_id = _id("construction-inspection", inspection.inspection_id)',
            '        entity_id = graph_id("construction-inspection", inspection.inspection_id)',
            "inspection entity alias",
        ),
        (
            '        entity_id = _id("construction-hazard", hazard.hazard_id)',
            '        entity_id = graph_id("construction-hazard", hazard.hazard_id)',
            "hazard entity alias",
        ),
        (
            '    crane_entity_id = _id("construction-crane-window", "crane-window-01")',
            '    crane_entity_id = graph_id("construction-crane-window", "crane-window-01")',
            "crane entity alias",
        ),
        (
            '        entity_id = _id("construction-alternative", alternative.alternative_id)',
            '        entity_id = graph_id("construction-alternative", alternative.alternative_id)',
            "alternative entity alias",
        ),
        (
            '        scene_id=_id("construction-demo-scene-v2", scene_id),',
            '        scene_id=graph_id("construction-demo-scene-v2", scene_id),',
            "scene alias",
        ),
    )
    for old, new, label in graph_replacements:
        text = replace_once(text, old, new, label)

    label_replacements = (
        (
            '            f"Construction building {_ref(asset_pack.building_id, privacy)}",',
            '            public_text(f"Construction building {asset_pack.building_id}", "Construction building"),',
            "building public label",
        ),
        (
            '                    f"Zone {_ref(package.zone_id, privacy)}",',
            '                    public_text(f"Zone {package.zone_id}", "Zone"),',
            "zone public label",
        ),
        (
            '                        f"Evidence requirement {_ref(evidence_ref, privacy)}",',
            '                        public_text(f"Evidence requirement {evidence_ref}", "Evidence requirement"),',
            "evidence public label",
        ),
        ("                package.title,", '                public_text(package.title, "Work package"),', "package label"),
        ("                trade.name.title(),", '                public_text(trade.name.title(), "Trade"),', "trade label"),
        ("                activity.note,", '                public_text(activity.note, "Work activity"),', "activity label"),
        ("                budget.description,", '                public_text(budget.description, "Budget line"),', "budget label"),
        ("                    rule.title,", '                    public_text(rule.title, "Synthetic rule"),', "rule label"),
        (
            '                        "requirement": rule.requirement,',
            '                        "requirement": public_text(rule.requirement, ""),',
            "rule requirement redaction",
        ),
        (
            "                inspection.title,",
            '                public_text(inspection.title, "Inspection"),',
            "inspection label",
        ),
        ("                hazard.title,", '                public_text(hazard.title, "Hazard"),', "hazard label"),
        (
            "                alternative.title,",
            '                public_text(alternative.title, "Review alternative"),',
            "alternative label",
        ),
        (
            '                    "blocker_codes": list(alternative.blocker_codes),',
            '                    "blocker_codes": (\n                        list(alternative.blocker_codes)\n                        if privacy is SpatialPrivacyClass.PROJECT\n                        else []\n                    ),',
            "alternative blocker redaction",
        ),
        (
            '                "crane_window_ref": "crane-window-01",',
            '                "crane_window_ref": _ref("crane-window-01", privacy),',
            "crane metadata alias",
        ),
    )
    for old, new, label in label_replacements:
        text = replace_once(text, old, new, label)

    text = replace_once(
        text,
        '''                metadata={\n                    "budget_line_ref": _ref(budget.budget_line_id, privacy),''',
        '''                metadata={\n                    "overlay_kind": "BUDGET",\n                    "budget_line_ref": _ref(budget.budget_line_id, privacy),''',
        "budget overlay classification",
    )

    text = scope_project_ref_calls(text)
    path.write_text(text, encoding="utf-8")


def patch_overlay_pass() -> None:
    path = ROOT / "aura_spatial_web/construction_overlay_pass.js"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''  "blockers",\n  "inspections",''',
        '''  "blockers",\n  "budgets",\n  "inspections",''',
        "budget layer registration",
    )
    anchor = '''      blockers: this.layers.get("blockers")\n        ? links\n            .filter((item) => ["BLOCKED_BY", "HAS_BLOCKED_PROPOSAL"].includes(item.relation))\n            .map((item) => ({\n              link_id: item.link_id,\n              source_entity_id: item.source_entity_id,\n              target_entity_id: item.target_entity_id,\n              relation: item.relation,\n            }))\n        : [],\n'''
    budget_model = anchor + '''      budgets: this.layers.get("budgets")\n        ? entities\n            .filter((item) => hasOverlayKind(item, "BUDGET"))\n            .map((item) => ({\n              entity_id: item.entity_id,\n              frame_id: item.frame_id,\n              label: item.label,\n              committed_cad: item.metadata?.committed_cad ?? 0,\n              forecast_cad: item.metadata?.forecast_cad ?? 0,\n              actual_cad: item.metadata?.actual_cad ?? 0,\n              truth_class: item.metadata?.truth_class || "",\n              presentation_transform: presentationTransform(item.frame_id),\n            }))\n        : [],\n'''
    text = replace_once(text, anchor, budget_model, "budget overlay model")
    path.write_text(text, encoding="utf-8")


def patch_python_tests() -> None:
    path = ROOT / "tests/test_aura_construction_demo_projection.py"
    text = path.read_text(encoding="utf-8")
    alias_anchor = '''    assert all(item.startswith("public-asset-") for item in first_aliases)\n    assert all(item["uri"] == f"aura://public/{item['asset_id']}" for item in first_assets)\n\n'''
    alias_checks = alias_anchor + '''    for collection, identifier in (\n        ("frames", "frame_id"),\n        ("entities", "entity_id"),\n        ("links", "link_id"),\n    ):\n        first_ids = {item[identifier] for item in first_payload[collection]}\n        second_ids = {item[identifier] for item in second_payload[collection]}\n        assert first_ids\n        assert first_ids.isdisjoint(second_ids)\n    assert first_payload["scene_id"] != second_payload["scene_id"]\n    assert first_payload["root_frame_id"] != second_payload["root_frame_id"]\n\n'''
    text = replace_once(text, alias_anchor, alias_checks, "public graph alias regression")

    raw_anchor = '''    raw_values.update(storey.name for storey in fixture.asset_pack.storeys)\n    serialized = str(first_payload)\n'''
    raw_checks = '''    raw_values.update(storey.name for storey in fixture.asset_pack.storeys)\n    raw_values.update(\n        {\n            fixture.asset_pack.building_id,\n            fixture.asset_pack.building_frame_id,\n            "construction-site-root",\n            "crane-window-01",\n        }\n    )\n    raw_values.update(storey.frame_id for storey in fixture.asset_pack.storeys)\n    raw_values.update(package.title for package in fixture.work_packages)\n    raw_values.update(trade.name.title() for trade in fixture.trades)\n    raw_values.update(activity.note for activity in fixture.work_history)\n    raw_values.update(budget.description for budget in fixture.budget_lines)\n    raw_values.update(rule.title for rule in fixture.rules)\n    raw_values.update(rule.requirement for rule in fixture.rules)\n    raw_values.update(inspection.title for inspection in fixture.inspections)\n    raw_values.update(hazard.title for hazard in fixture.hazards)\n    raw_values.update(alternative.title for alternative in fixture.alternatives)\n    raw_values.update(code for alternative in fixture.alternatives for code in alternative.blocker_codes)\n    serialized = str(first_payload)\n'''
    text = replace_once(text, raw_anchor, raw_checks, "public free-text regression")

    budget_anchor = '''        assert len(matches) == 1\n        assert matches[0]["frame_id"] == package_frames[budget.work_package_id]\n'''
    budget_check = '''        assert len(matches) == 1\n        assert matches[0]["frame_id"] == package_frames[budget.work_package_id]\n        assert matches[0]["metadata"]["overlay_kind"] == "BUDGET"\n'''
    text = replace_once(text, budget_anchor, budget_check, "budget classification regression")
    path.write_text(text, encoding="utf-8")


def patch_browser_tests() -> None:
    path = ROOT / "tests/js/spatial-construction-demo.test.mjs"
    text = path.read_text(encoding="utf-8")
    entity_anchor = '''    {\n      entity_id: "entity:inspection",\n      entity_type: "DOMAIN_NODE",\n'''
    budget_entity = '''    {\n      entity_id: "entity:budget",\n      entity_type: "DOMAIN_NODE",\n      label: "Budget line",\n      frame_id: "frame:storey",\n      asset_ids: [],\n      source_refs: ["construction-demo-budget:fixture"],\n      position: [0, 0, 0],\n      rotation_xyzw: [0, 0, 0, 1],\n      scale: [1, 1, 1],\n      truth_class: "PRESENTATION",\n      selectable: true,\n      projection_only: true,\n      patch_authority: false,\n      metadata: {\n        overlay_kind: "BUDGET",\n        committed_cad: 100,\n        forecast_cad: 120,\n        actual_cad: 80,\n        truth_class: "SYNTHETIC_DEMO_BUDGET",\n      },\n    },\n''' + entity_anchor
    text = replace_once(text, entity_anchor, budget_entity, "browser budget fixture")

    assertion_anchor = '''  assert.equal(model.floor_plans.length, 1);\n  assert.equal(model.blockers.length, 1);\n'''
    assertion_replacement = '''  assert.equal(model.floor_plans.length, 1);\n  assert.equal(model.blockers.length, 1);\n  assert.equal(model.budgets.length, 1);\n  assert.deepEqual(\n    {\n      committed_cad: model.budgets[0].committed_cad,\n      forecast_cad: model.budgets[0].forecast_cad,\n      actual_cad: model.budgets[0].actual_cad,\n    },\n    { committed_cad: 100, forecast_cad: 120, actual_cad: 80 },\n  );\n'''
    text = replace_once(text, assertion_anchor, assertion_replacement, "browser budget assertions")

    toggle_anchor = '''  pass.setTimelineDay(5);\n  pass.setLayer("dependencies", false);\n  pass.setVisibleFrameIds(["frame:storey"]);\n'''
    toggle_replacement = '''  pass.setTimelineDay(5);\n  pass.setLayer("dependencies", false);\n  pass.setLayer("budgets", false);\n  pass.setVisibleFrameIds(["frame:storey"]);\n'''
    text = replace_once(text, toggle_anchor, toggle_replacement, "browser budget layer toggle")
    text = replace_once(
        text,
        '''  assert.equal(model.dependencies.length, 0);\n  assert.equal(model.source_geometry_mutated, false);\n''',
        '''  assert.equal(model.dependencies.length, 0);\n  assert.equal(model.budgets.length, 0);\n  assert.equal(model.source_geometry_mutated, false);\n''',
        "browser hidden budget assertion",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_projection()
    patch_overlay_pass()
    patch_python_tests()
    patch_browser_tests()
    print("Applied fourth Codex repair set")


if __name__ == "__main__":
    main()
