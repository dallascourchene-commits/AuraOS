from __future__ import annotations


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    assert count == 1, f"{label}: expected one match, found {count}"
    return text.replace(old, new, 1)


def _patch_module(text: str) -> str:
    text = _replace_once(
        text,
        "from enum import Enum\nfrom typing import Any\n",
        "from enum import Enum\nfrom types import MappingProxyType\nfrom typing import Any\n",
        "MappingProxyType import",
    )
    text = _replace_once(
        text,
        '''def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    result = {str(key): item for key, item in value.items()}
    canonical_json(result)
    return result


def _enum''',
        '''def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    result = {str(key): item for key, item in value.items()}
    canonical_json(result)
    return result


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw_json(item) for item in value]
    return value


def _immutable_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    mutable = _mapping(value, field_name)
    frozen = _freeze_json(mutable)
    if not isinstance(frozen, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return frozen


def _mutable_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    mutable = _thaw_json(value)
    if not isinstance(mutable, dict):
        raise ValueError("expected immutable mapping")
    return mutable


def _enum''',
        "deep immutable helpers",
    )
    text = text.replace(
        "metadata: dict[str, Any] = field(default_factory=dict)",
        "metadata: Mapping[str, Any] = field(default_factory=dict)",
    )
    assert text.count("metadata: Mapping[str, Any] = field(default_factory=dict)") == 2
    text = _replace_once(
        text,
        'object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))',
        'object.__setattr__(\n            self, "metadata", _immutable_mapping(self.metadata, "metadata")\n        )',
        "participant metadata freeze",
    )
    text = _replace_once(
        text,
        '"metadata": dict(sorted(self.metadata.items())),',
        '"metadata": dict(sorted(_mutable_mapping(self.metadata).items())),',
        "participant metadata thaw",
    )
    text = _replace_once(
        text,
        'object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))',
        'object.__setattr__(\n            self, "metadata", _immutable_mapping(self.metadata, "metadata")\n        )',
        "relation metadata freeze",
    )
    text = _replace_once(
        text,
        '"metadata": dict(sorted(self.metadata.items())),',
        '"metadata": dict(sorted(_mutable_mapping(self.metadata).items())),',
        "relation metadata thaw",
    )
    text = _replace_once(
        text,
        "    omitted_reasons: dict[str, int]\n",
        "    omitted_reasons: Mapping[str, int]\n",
        "boundary annotation",
    )
    text = _replace_once(
        text,
        '''        object.__setattr__(
            self, "omitted_reasons", dict(sorted(normalized_reasons.items()))
        )''',
        '''        object.__setattr__(
            self,
            "omitted_reasons",
            _immutable_mapping(
                dict(sorted(normalized_reasons.items())),
                "omitted_reasons",
            ),
        )''',
        "boundary reasons freeze",
    )
    text = _replace_once(
        text,
        '"omitted_reasons": dict(self.omitted_reasons),',
        '"omitted_reasons": _mutable_mapping(self.omitted_reasons),',
        "boundary reasons thaw",
    )
    text = _replace_once(
        text,
        "    repository_identity: dict[str, Any]\n",
        "    repository_identity: Mapping[str, Any]\n",
        "repository identity annotation",
    )
    text = _replace_once(
        text,
        "    source_slices: tuple[dict[str, Any], ...]\n",
        "    source_slices: tuple[Mapping[str, Any], ...]\n",
        "source slices annotation",
    )
    text = _replace_once(
        text,
        '''        if self.intent_packet.objective_digest != self.objective_digest:
            raise ValueError("intent packet objective digest does not match capsule")
        object.__setattr__(
            self,
            "repository_identity",
            _mapping(self.repository_identity, "repository_identity"),
        )''',
        '''        if self.intent_packet.objective_digest != self.objective_digest:
            raise ValueError("intent packet objective digest does not match capsule")
        rebound_intent = PolysyntheticIntentPacket.from_slots(
            {name: filler for name, filler in self.intent_packet.slot_items()},
            adjuncts=self.intent_packet.adjuncts,
            objective=self.objective,
        )
        if rebound_intent.objective_digest != self.objective_digest:
            raise ValueError("intent packet does not bind the capsule objective")
        object.__setattr__(
            self,
            "repository_identity",
            _immutable_mapping(self.repository_identity, "repository_identity"),
        )''',
        "objective binding and repository freeze",
    )
    text = _replace_once(
        text,
        '''        group_ids = [item.group_id for item in self.groups]
        if not group_ids or len(group_ids) != len(set(group_ids)):
            raise ValueError("groups must be nonempty and contain unique IDs")''',
        '''        group_ids = [item.group_id for item in self.groups]
        if len(group_ids) < 3 or len(group_ids) != len(set(group_ids)):
            raise ValueError("groups must contain at least three unique IDs")''',
        "group cardinality",
    )
    text = _replace_once(
        text,
        "        normalized_slices: list[dict[str, Any]] = []\n",
        "        normalized_slices: list[Mapping[str, Any]] = []\n",
        "slice list annotation",
    )
    text = _replace_once(
        text,
        '''        for item in self.source_slices:
            data = _mapping(item, "source_slices[]")''',
        '''        for item in self.source_slices:
            data = _immutable_mapping(item, "source_slices[]")''',
        "source slice freeze",
    )
    text = _replace_once(
        text,
        '''            normalized_slices.append(data)
        object.__setattr__(
            self,
            "source_slices",''',
        '''            normalized_slices.append(data)
        if not normalized_slices:
            raise ValueError("source_slices must not be empty")
        object.__setattr__(
            self,
            "source_slices",''',
        "source slice cardinality",
    )
    text = _replace_once(
        text,
        '"repository_identity": self.repository_identity,',
        '"repository_identity": _mutable_mapping(self.repository_identity),',
        "expected id repository thaw",
    )
    text = _replace_once(
        text,
        '"repository_identity": dict(sorted(self.repository_identity.items())),',
        '"repository_identity": dict(\n                sorted(_mutable_mapping(self.repository_identity).items())\n            ),',
        "capsule repository serialization",
    )
    text = _replace_once(
        text,
        '"source_slices": [dict(item) for item in self.source_slices],',
        '"source_slices": [\n                _mutable_mapping(item) for item in self.source_slices\n            ],',
        "capsule slice serialization",
    )
    text = _replace_once(
        text,
        '''        repository_identity = {
            "repo_head": packet["repo_head"],
            "atomic_inventory_digest": packet["atomic_inventory"]["inventory_digest"],
            "capability_graph_digest": packet["capability_connectome"]["graph_digest"],
            "capability_path_digest": str(
                packet["capability_connectome"].get("path", {}).get(
                    "capability_path_digest"
                )
                or packet["capability_connectome"].get("path", {}).get("path_digest")
                or ""
            ),
            "evidence_packet_version": packet["version"],
        }
        if not repository_identity["capability_path_digest"]:
            repository_identity["capability_path_digest"] = stable_digest(
                packet["capability_connectome"].get("path", {}), digest_size=20
            )''',
        '''        capability_path = _mapping(
            packet["capability_connectome"].get("path"),
            "capability_connectome.path",
        )
        capability_path_digest = _required_text(
            capability_path.get("capability_path_digest")
            or capability_path.get("path_digest"),
            "capability_connectome.path.capability_path_digest",
        )
        repository_identity = {
            "repo_head": packet["repo_head"],
            "atomic_inventory_digest": packet["atomic_inventory"]["inventory_digest"],
            "capability_graph_digest": packet["capability_connectome"]["graph_digest"],
            "capability_path_digest": capability_path_digest,
            "evidence_packet_version": packet["version"],
        }''',
        "remove fabricated capability path digest",
    )
    text = _replace_once(
        text,
        '''    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")
    expected_repo_head = _required_text(expected_repo_head, "expected_repo_head")''',
        '''    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")
    capability_path = _mapping(
        capability.get("path"), "capability_connectome.path"
    )
    _required_text(
        capability_path.get("capability_path_digest")
        or capability_path.get("path_digest"),
        "capability_connectome.path.capability_path_digest",
    )
    expected_repo_head = _required_text(expected_repo_head, "expected_repo_head")''',
        "validate capability path digest",
    )
    return text


def _patch_tests(text: str) -> str:
    text = _replace_once(
        text,
        '''    assert "authority_guard" in binding_roles
    assert all(item.status.value == "OPEN" for item in scope_group.proof_obligations)''',
        '''    assert "authority_guard" in binding_roles
    authority_binding = next(
        item for item in scope_group.role_bindings
        if item.role == "authority_guard"
    )
    authority_participant = next(
        item for item in capsule.participants
        if item.participant_id == authority_binding.participant_id
    )
    assert authority_participant.role == "authority_guard"
    assert authority_participant.canonical_ref == "packet.authority.patch_authority"
    assert all(item.status.value == "OPEN" for item in scope_group.proof_obligations)''',
        "authority identity regression assertion",
    )
    return text + '''


def test_capability_path_freshness_identity_is_not_fabricated() -> None:
    packet = _packet()
    packet["capability_connectome"]["path"] = {}
    with pytest.raises(ValueError, match="capability_path_digest"):
        _compile(packet)


def test_capsule_create_binds_objective_to_intent() -> None:
    capsule = _compile()
    with pytest.raises(ValueError, match="does not bind the capsule objective"):
        RelationalSynthesisCapsule.create(
            objective="A different objective.",
            intent_packet=_intent(),
            repository_identity=capsule.repository_identity,
            source_packet_id=capsule.source_packet_id,
            source_packet_digest=capsule.source_packet_digest,
            participants=capsule.participants,
            groups=capsule.groups,
            source_slices=capsule.source_slices,
            tests=capsule.tests,
            active_arena=capsule.active_arena,
            boundary=capsule.boundary,
        )


def test_capsule_schema_cardinalities_are_enforced_in_python() -> None:
    too_few_groups = _compile().to_dict()
    too_few_groups["groups"] = too_few_groups["groups"][:2]
    with pytest.raises(ValueError, match="at least three"):
        RelationalSynthesisCapsule.from_dict(too_few_groups)

    no_source_slices = _compile().to_dict()
    no_source_slices["source_slices"] = []
    with pytest.raises(ValueError, match="source_slices must not be empty"):
        RelationalSynthesisCapsule.from_dict(no_source_slices)


def test_frozen_contract_mappings_are_deeply_immutable() -> None:
    capsule = _compile()
    with pytest.raises(TypeError):
        capsule.repository_identity["repo_head"] = "0" * 40
    with pytest.raises(TypeError):
        capsule.source_slices[0]["file_path"] = "mutated.py"

    participant = RelationalParticipant.create(
        participant_type=ParticipantType.STATE,
        role="immutable_fixture",
        truth_class=TruthClass.UNRESOLVED,
        canonical_owner="fixture",
        canonical_ref="fixture:immutable",
        digest=None,
        evidence_refs=("fixture",),
        freshness=Freshness.UNRESOLVED,
        metadata={"nested": {"items": ["a", "b"]}},
    )
    with pytest.raises(TypeError):
        participant.metadata["nested"]["new"] = "value"
    with pytest.raises(TypeError):
        participant.metadata["nested"]["items"][0] = "mutated"

    boundary = next(
        group.boundary for group in capsule.groups if group.boundary.omitted_reasons
    )
    with pytest.raises(TypeError):
        boundary.omitted_reasons["new_reason"] = 1
'''
