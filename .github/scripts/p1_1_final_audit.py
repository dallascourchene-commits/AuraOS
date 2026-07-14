from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str, marker: str | None = None) -> None:
    text = read(path)
    if (marker or new) in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f"expected one exact span in {path}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def patch_secret_patterns(path: str) -> None:
    text = read(path)
    text = text.replace("        (?:bearer\\s+)?\n", "        (?:(?:bearer|basic)\\s+)?\n")
    if 're.compile(r"(?i)\\bbasic\\s+' not in text:
        text = text.replace(
            '    re.compile(r"(?i)\\bbearer\\s+[A-Za-z0-9._~+/=%\\-]+"),\n',
            '    re.compile(r"(?i)\\bbearer\\s+[A-Za-z0-9._~+/=%\\-]+"),\n'
            '    re.compile(r"(?i)\\bbasic\\s+[A-Za-z0-9+/=]+"),\n'
            '    re.compile(\n'
            '        r"(?is)-----BEGIN [^-\\r\\n]*PRIVATE KEY-----.*?"\n'
            '        r"-----END [^-\\r\\n]*PRIVATE KEY-----"\n'
            '    ),\n',
            1,
        )
    write(path, text)


def patch_event_contracts() -> None:
    patch_secret_patterns("aura_event_contracts.py")
    replace_once(
        "aura_event_contracts.py",
        '''def _enum(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:\n    raw = value.value if isinstance(value, Enum) else str(value)\n    if raw not in {item.value for item in enum_type}:\n        raise ValueError(f"unknown {field_name}: {raw}")\n    return raw\n\n\n''',
        '''def _enum(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:\n    raw = value.value if isinstance(value, Enum) else str(value)\n    if raw not in {item.value for item in enum_type}:\n        raise ValueError(f"unknown {field_name}: {raw}")\n    return raw\n\n\ndef _strict_bool(value: Any, field_name: str) -> bool:\n    if type(value) is not bool:\n        raise ValueError(f"{field_name} must be a boolean")\n    return value\n\n\n''',
        marker="def _strict_bool(value: Any, field_name: str) -> bool:",
    )
    replace_once(
        "aura_event_contracts.py",
        '''    if isinstance(value, bytes):\n        return {"__bytes_hex__": value.hex()}, True\n''',
        '''    if isinstance(value, (bytes, bytearray, memoryview)):\n        raw_bytes = bytes(value)\n        decoded = raw_bytes.decode("utf-8", errors="replace")\n        redacted = redact_secrets(decoded)\n        if redacted != decoded:\n            return {"__bytes_text__": redacted}, True\n        return {"__bytes_hex__": raw_bytes.hex()}, True\n''',
        marker='return {"__bytes_text__": redacted}, True',
    )
    text = read("aura_event_contracts.py")
    text = text.replace(
        '"proposal_only": bool(proposal_only),',
        '"proposal_only": _strict_bool(proposal_only, "proposal_only"),',
    )
    write("aura_event_contracts.py", text)


def patch_workflow_gates() -> None:
    text = read("aura_workflow_gates.py")
    text = text.replace(
        '"prior_state_agent_running_or_repair",  # VERIFIED or REPAIR_REQUIRED',
        '"prior_state_agent_running_or_repair",  # AGENT_RUNNING or REPAIR_REQUIRED',
    )
    text = text.replace(
        '    A verified :class:`GovernanceDecision` is preferred. The historical truthy\n'
        '    ``human_approval`` input remains available as an explicitly labeled\n',
        '    A verified :class:`GovernanceDecision` is preferred. The historical literal\n'
        '    boolean ``human_approval=True`` input remains as an explicitly labeled\n',
    )
    text = text.replace(
        '            else bool(evidence.get(key))\n',
        '            else evidence.get(key) is True\n',
    )
    write("aura_workflow_gates.py", text)


def patch_relational_authority() -> None:
    patch_secret_patterns("aura_relational_authority.py")
    replace_once(
        "aura_relational_authority.py",
        '''def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:\n    raw = value.value if isinstance(value, Enum) else str(value).upper()\n    permitted = {item.value for item in enum_type}\n    if raw not in permitted:\n        raise ValueError(f"unknown {field_name}: {raw}")\n    return raw\n\n\n''',
        '''def _enum_value(value: str | Enum, enum_type: type[Enum], field_name: str) -> str:\n    raw = value.value if isinstance(value, Enum) else str(value).upper()\n    permitted = {item.value for item in enum_type}\n    if raw not in permitted:\n        raise ValueError(f"unknown {field_name}: {raw}")\n    return raw\n\n\ndef _strict_bool(value: Any, field_name: str) -> bool:\n    if type(value) is not bool:\n        raise ValueError(f"{field_name} must be a boolean")\n    return value\n\n\n''',
        marker="def _strict_bool(value: Any, field_name: str) -> bool:",
    )
    text = read("aura_relational_authority.py")
    text = text.replace(
        'proposal_only=bool(data.get("proposal_only", True))',
        'proposal_only=_strict_bool(data.get("proposal_only", True), "proposal_only")',
    )
    text = text.replace(
        'vsa_patch_authority=bool(data.get("vsa_patch_authority", False))',
        'vsa_patch_authority=_strict_bool(\n                data.get("vsa_patch_authority", False), "vsa_patch_authority"\n            )',
    )
    text = text.replace(
        'authorized=bool(data.get("authorized", False))',
        'authorized=_strict_bool(data.get("authorized", False), "authorized")',
    )
    text = text.replace(
        '''emergency_review_required=bool(\n                data.get("emergency_review_required", False)\n            )''',
        '''emergency_review_required=_strict_bool(\n                data.get("emergency_review_required", False),\n                "emergency_review_required",\n            )''',
    )
    text = text.replace(
        '"rejection_blocks_authorization": bool(rejection_blocks_authorization),',
        '"rejection_blocks_authorization": _strict_bool(\n                rejection_blocks_authorization, "rejection_blocks_authorization"\n            ),',
    )
    text = text.replace(
        '"preserve_abstentions": bool(preserve_abstentions),',
        '"preserve_abstentions": _strict_bool(\n                preserve_abstentions, "preserve_abstentions"\n            ),',
    )
    text = text.replace(
        '"proposer_approval_allowed": bool(proposer_approval_allowed),',
        '"proposer_approval_allowed": _strict_bool(\n                proposer_approval_allowed, "proposer_approval_allowed"\n            ),',
    )
    text = text.replace(
        '"mandatory_post_event_review": bool(mandatory_post_event_review),',
        '"mandatory_post_event_review": _strict_bool(\n                mandatory_post_event_review, "mandatory_post_event_review"\n            ),',
    )
    write("aura_relational_authority.py", text)


def append_tests() -> None:
    path = "tests/test_p1_1_adversarial_review.py"
    text = read(path)
    marker = "def test_binary_credentials_are_redacted_before_hex_encoding"
    if marker in text:
        return
    text += '''\n\ndef test_basic_authorization_header_is_fully_redacted() -> None:\n    payload = "Authorization: Basic dXNlcjpwYXNzd29yZA=="\n    sanitized = sanitize_payload(payload)\n    assert "dXNlcjpwYXNzd29yZA==" not in sanitized\n    assert "[REDACTED]" in sanitized\n\n\ndef test_binary_credentials_are_redacted_before_hex_encoding() -> None:\n    secret = b"Authorization: Bearer abc/DEF+ghi~=123"\n    sanitized = sanitize_payload({"blob": secret})\n    encoded = str(sanitized)\n    assert "abc/DEF+ghi~=123" not in encoded\n    assert secret.hex() not in encoded\n    assert "[REDACTED]" in encoded\n\n\ndef test_string_false_does_not_satisfy_non_authority_evidence() -> None:\n    result = evaluate_gate(\n        "HUMAN_APPROVED_FOR_COMMIT",\n        {\n            "human_approval": True,\n            "verified": "false",\n            "tests_pass": "false",\n        },\n    )\n    assert result["can_proceed"] is False\n    assert "verified" in result["missing_requirements"]\n    assert "tests_pass" in result["missing_requirements"]\n\n\ndef test_serialized_governance_boolean_fields_are_strict() -> None:\n    decision = make_decision().to_dict()\n    decision["authorized"] = "false"\n    with pytest.raises(ValueError, match="authorized must be a boolean"):\n        from aura_relational_authority import GovernanceDecision\n\n        GovernanceDecision.from_dict(decision)\n\n\ndef test_quorum_policy_boolean_parameters_are_strict() -> None:\n    with pytest.raises(ValueError, match="proposer_approval_allowed must be a boolean"):\n        QuorumPolicy.create(\n            risk_class=RiskClass.LOW,\n            minimum_approval_count=1,\n            required_functional_roles=("APPROVE",),\n            minimum_distinct_principals=1,\n            proposer_approval_allowed="false",  # type: ignore[arg-type]\n        )\n'''
    write(path, text)


def main() -> None:
    patch_event_contracts()
    patch_workflow_gates()
    patch_relational_authority()
    append_tests()
    print("final P1.1 audit repairs applied")


if __name__ == "__main__":
    main()
