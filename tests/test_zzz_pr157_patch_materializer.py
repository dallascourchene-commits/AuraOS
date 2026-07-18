from __future__ import annotations


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, f"{label}: expected one match, found {count}"
    return text.replace(old, new, 1)


def _patch_module(text: str) -> str:
    return _replace_once(
        text,
        '''    for field_name in ("packet_id", "packet_digest", "repo_head", "version", "target_arena"):
        _required_text(packet.get(field_name), field_name)
    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")
    _required_text(
        atomic_inventory.get("inventory_digest"), "atomic_inventory.inventory_digest"
    )
    capability = _mapping(
        packet.get("capability_connectome"), "capability_connectome"
    )
    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")''',
        '''    for field_name in ("packet_id", "packet_digest", "repo_head", "version", "target_arena"):
        _required_text(packet.get(field_name), field_name)
    if packet["version"] != "AURA_EMERGENT_EVIDENCE_SPINE_V1":
        raise ValueError("unsupported evidence packet version")
    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")
    if atomic_inventory.get("version") != "AURA_ATOMIC_FUNCTION_INVENTORY_V1":
        raise ValueError("unsupported atomic inventory version")
    _required_text(
        atomic_inventory.get("inventory_digest"), "atomic_inventory.inventory_digest"
    )
    capability = _mapping(
        packet.get("capability_connectome"), "capability_connectome"
    )
    if capability.get("version") != "AURA_CAPABILITY_CONNECTOME_V2":
        raise ValueError("unsupported capability connectome version")
    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")''',
        "version validation",
    )


def _patch_tests(text: str) -> str:
    return text + '''


def test_unsupported_evidence_contract_versions_fail_closed() -> None:
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
