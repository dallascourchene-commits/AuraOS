from __future__ import annotations


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, f"{label}: expected one match, found {count}"
    return text.replace(old, new, 1)


def _patch_module(text: str) -> str:
    text = _replace_once(
        text,
        '        _required_text(packet.get(field_name), field_name)\n    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")',
        '        _required_text(packet.get(field_name), field_name)\n    if packet["version"] != "AURA_EMERGENT_EVIDENCE_SPINE_V1":\n        raise ValueError("unsupported evidence packet version")\n    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")',
        "evidence packet version",
    )
    text = _replace_once(
        text,
        '    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")\n    _required_text(',
        '    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")\n    if atomic_inventory.get("version") != "AURA_ATOMIC_FUNCTION_INVENTORY_V1":\n        raise ValueError("unsupported atomic inventory version")\n    _required_text(',
        "atomic inventory version",
    )
    text = _replace_once(
        text,
        '    capability = _mapping(\n        packet.get("capability_connectome"), "capability_connectome"\n    )\n    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")',
        '    capability = _mapping(\n        packet.get("capability_connectome"), "capability_connectome"\n    )\n    if capability.get("version") != "AURA_CAPABILITY_CONNECTOME_V2":\n        raise ValueError("unsupported capability connectome version")\n    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")',
        "capability connectome version",
    )
    return text


def _patch_tests(text: str) -> str:
    return text + '''


def test_unsupported_upstream_contract_versions_fail_closed() -> None:
    packet = _packet()
    packet["version"] = "AURA_EMERGENT_EVIDENCE_SPINE_V999"
    with pytest.raises(ValueError, match="unsupported evidence packet version"):
        _compile(packet)

    packet = _packet()
    packet["atomic_inventory"]["version"] = "AURA_ATOMIC_FUNCTION_INVENTORY_V999"
    with pytest.raises(ValueError, match="unsupported atomic inventory version"):
        _compile(packet)

    packet = _packet()
    packet["capability_connectome"]["version"] = "AURA_CAPABILITY_CONNECTOME_V999"
    with pytest.raises(ValueError, match="unsupported capability connectome version"):
        _compile(packet)
'''
