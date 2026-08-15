from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture_harness" / "ARCH_V2_3"
POLICY = ARCH / "aura_arch_v2_3_default_policy.json"
SCHEMA = ARCH / "aura_pr_continuity_capsule.v2_3.schema.json"
TEMPLATE = ARCH / "AURA_PR_CONTINUITY_CAPSULE_TEMPLATE_V2_3.md"


def test_pr272_minimum_fidelity_names_match_canonical_schema_ledgers() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    fields = set(policy["minimum_fidelity_fields"])
    assert "findings" in fields
    assert "root_cause_groups" in fields
    assert "open_findings" not in fields
    assert "open_root_cause_groups" not in fields


def test_pr272_schema_remains_draft_2020_12_valid() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_pr275_reviewer_history_table_has_five_columns_in_every_row() -> None:
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    heading = lines.index("## 16. Reviewer history")
    table_rows = [line for line in lines[heading + 1 :] if line.startswith("|")][:3]
    assert len(table_rows) == 3
    assert all(len(row.strip().strip("|").split("|")) == 5 for row in table_rows)
    assert table_rows[1] == "|---|---|---|---|---|"


def test_pr275_template_keeps_current_schema_and_state_keys() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert "schema_version: AURA_PR_CONTINUITY_CAPSULE_V2_3" in frontmatter
    assert "generation: 1" in frontmatter
    assert 'state: "ORIENTED"' in frontmatter
    assert "capsule_schema:" not in frontmatter
    assert "capsule_generation:" not in frontmatter
    assert "terminal_state:" not in frontmatter
