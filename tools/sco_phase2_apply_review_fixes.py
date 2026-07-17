from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"{path}: expected {count} exact matches, found {actual}: {old[:80]!r}"
        )
    target.write_text(text.replace(old, new), encoding="utf-8")


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"{path}: replacement anchors are not unique")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    target.write_text(before + replacement + end + after, encoding="utf-8")


def append_once(path: str, marker: str, body: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + body.strip() + "\n", encoding="utf-8")


def patch_contracts() -> None:
    path = "aura_construction_contracts.py"
    replace_exact(
        path,
        '''def _normalized_unique(values: Iterable[Any], name: str) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    return tuple(sorted(result))
''',
        '''def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _normalized_unique(values: Iterable[Any], name: str) -> tuple[str, ...]:
    items = _sequence_input(values, name)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    return tuple(sorted(result))
''',
    )
    replace_exact(
        path,
        '''    def __post_init__(self) -> None:
        _scope_component(self.project_id, "scope.project_id")
        if self.zone_id:
            _scope_component(self.zone_id, "scope.zone_id")
        if self.work_package_id:
            _scope_component(self.work_package_id, "scope.work_package_id")
            if not self.zone_id:
                raise ValueError("scope.work_package_id requires scope.zone_id")
''',
        '''    def __post_init__(self) -> None:
        _scope_component(self.project_id, "scope.project_id")
        if type(self.zone_id) is not str:
            raise ValueError("scope.zone_id must be a string")
        if type(self.work_package_id) is not str:
            raise ValueError("scope.work_package_id must be a string")
        if self.zone_id:
            _scope_component(self.zone_id, "scope.zone_id")
        if self.work_package_id:
            _scope_component(self.work_package_id, "scope.work_package_id")
            if not self.zone_id:
                raise ValueError("scope.work_package_id requires scope.zone_id")
''',
    )
    replace_exact(
        path,
        '''    @property
    def scope_key(self) -> str:
        return "/".join((self.project_id, self.zone_id or "*", self.work_package_id or "*"))
''',
        '''    @property
    def scope_key(self) -> str:
        return "/".join((self.project_id, self.zone_id or "*", self.work_package_id or "*"))

    @property
    def policy_scope(self) -> str:
        return "/".join(
            component
            for component in (
                "construction",
                self.project_id,
                self.zone_id,
                self.work_package_id,
            )
            if component
        )
''',
    )
    for old, new in (
        ('consent_refs=tuple(data.get("consent_refs", ())),',
         'consent_refs=_sequence_input(data.get("consent_refs", ()), "evidence.consent_refs"),'),
        ('evidence_refs=tuple(data.get("evidence_refs", ())),',
         'evidence_refs=_sequence_input(data.get("evidence_refs", ()), "claim.evidence_refs"),'),
        ('consent_refs=tuple(data.get("consent_refs", ())),',
         'consent_refs=_sequence_input(data.get("consent_refs", ()), "claim.consent_refs"),'),
        ('parent_event_ids=tuple(data.get("parent_event_ids", ())),',
         'parent_event_ids=_sequence_input(data.get("parent_event_ids", ()), "event.parent_event_ids"),'),
        ('supersedes_event_ids=tuple(data.get("supersedes_event_ids", ())),',
         'supersedes_event_ids=_sequence_input(data.get("supersedes_event_ids", ()), "event.supersedes_event_ids"),'),
    ):
        replace_exact(path, old, new)
    replace_exact(
        path,
        '''        _text(self.ledger_id, "event.ledger_id")
        expected_ledger = f"construction/{self.record.scope.project_id}"
''',
        '''        if type(self.record) not in {ConstructionClaim, ConstructionEvidence}:
            raise ValueError(
                "event record must be an exact ConstructionClaim or ConstructionEvidence"
            )
        _text(self.ledger_id, "event.ledger_id")
        expected_ledger = f"construction/{self.record.scope.project_id}"
''',
    )
    replace_exact(
        path,
        '            policy_scope=f"construction/{self.record.scope.scope_key}",',
        '            policy_scope=self.record.scope.policy_scope,',
    )


def patch_state() -> None:
    path = "aura_construction_state.py"
    replace_exact(
        path,
        '''def _tuple_strings(value: Any, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} contains an invalid value")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    if value != tuple(sorted(value)):
        raise ValueError(f"{name} must use canonical sorted order")
    return value
''',
        '''def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _tuple_strings(value: Any, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(" ".join(item.split()) if type(item) is str else item for item in value)
    if any(type(item) is not str or not item for item in normalized):
        raise ValueError(f"{name} contains an invalid value")
    if normalized != value:
        raise ValueError(f"{name} must contain canonical normalized strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{name} must use canonical sorted order")
    return normalized
''',
    )
    replace_exact(
        path,
        "        missing_parents = set(event.parent_event_ids) - set(seen)",
        "        missing_parents = set(event.parent_event_ids).difference(seen)",
    )
    for old, new in (
        ('active_event_ids=tuple(data.get("active_event_ids", ())),',
         'active_event_ids=_sequence_input(data.get("active_event_ids", ()), "state.active_event_ids"),'),
        ('superseded_event_ids=tuple(data.get("superseded_event_ids", ())),',
         'superseded_event_ids=_sequence_input(data.get("superseded_event_ids", ()), "state.superseded_event_ids"),'),
        ('blockers=tuple(data.get("blockers", ())),',
         'blockers=_sequence_input(data.get("blockers", ()), "readiness.blockers"),'),
        ('active_evidence_ids=tuple(data.get("active_evidence_ids", ())),',
         'active_evidence_ids=_sequence_input(data.get("active_evidence_ids", ()), "readiness.active_evidence_ids"),'),
        ('conflict_event_ids=tuple(data.get("conflict_event_ids", ())),',
         'conflict_event_ids=_sequence_input(data.get("conflict_event_ids", ()), "readiness.conflict_event_ids"),'),
    ):
        replace_exact(path, old, new)
    replace_exact(
        path,
        '''            active_event_ids=tuple(data.get("active_event_ids", ())),
            record_digests=tuple(data.get("record_digests", ())),
''',
        '''            active_event_ids=_sequence_input(
                data.get("active_event_ids", ()), "conflict.active_event_ids"
            ),
            record_digests=_sequence_input(
                data.get("record_digests", ()), "conflict.record_digests"
            ),
''',
    )
    replace_between(
        path,
        "def query_claim_readiness(\n",
        "def query_project_conflicts(\n",
        '''def _readiness_indexes(
    state: ConstructionProjectState,
) -> tuple[
    dict[str, tuple[ConstructionEvent, ...]],
    dict[str, ConstructionEvidence],
    dict[tuple[str, str], tuple[ConstructionConflict, ...]],
]:
    claims: dict[str, list[ConstructionEvent]] = {}
    for event in state.active_claim_events:
        if type(event.record) is ConstructionClaim:
            claims.setdefault(event.record.claim_id, []).append(event)
    evidence = {
        event.record.evidence_id: event.record
        for event in state.active_evidence_events
        if type(event.record) is ConstructionEvidence
    }
    conflicts: dict[tuple[str, str], list[ConstructionConflict]] = {}
    for item in state.conflicts:
        conflicts.setdefault((item.record_kind, item.state_key), []).append(item)
    return (
        {key: tuple(value) for key, value in claims.items()},
        evidence,
        {key: tuple(value) for key, value in conflicts.items()},
    )


def _query_claim_readiness_validated(
    state: ConstructionProjectState,
    *,
    claim_id: str,
    evaluated: float,
    claim_events_by_id: dict[str, tuple[ConstructionEvent, ...]],
    evidence_by_id: dict[str, ConstructionEvidence],
    conflicts_by_key: dict[tuple[str, str], tuple[ConstructionConflict, ...]],
) -> ConstructionReadinessReport:
    active_claim_events = claim_events_by_id.get(claim_id, ())
    if len(active_claim_events) != 1:
        return ConstructionReadinessReport(
            claim_id=claim_id,
            ready=False,
            blockers=("claim_not_uniquely_active",),
            active_evidence_ids=(),
            conflict_event_ids=(),
            state_digest=state.state_digest,
            evaluated_at=evaluated,
        )

    claim_event = active_claim_events[0]
    claim = claim_event.record
    assert type(claim) is ConstructionClaim
    blockers: list[str] = []
    conflict_ids: list[str] = []

    for conflict in conflicts_by_key.get(
        (ConstructionRecordKind.CLAIM.value, claim.state_key), ()
    ):
        blockers.append("conflicting_active_claims")
        conflict_ids.extend(conflict.active_event_ids)

    if claim.expires_at is not None and evaluated >= claim.expires_at:
        blockers.append("claim_expired")
    if not claim.evidence_refs:
        blockers.append("claim_has_no_evidence")

    active_evidence: list[ConstructionEvidence] = []
    for evidence_id in claim.evidence_refs:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            blockers.append(f"missing_evidence:{evidence_id}")
            continue
        active_evidence.append(evidence)
        if evidence.scope != claim.scope:
            blockers.append(f"evidence_scope_mismatch:{evidence_id}")
        if evidence.subject_id != claim.subject_id:
            blockers.append(f"evidence_subject_mismatch:{evidence_id}")
        if _PRIVACY_RANK[evidence.privacy_class] > _PRIVACY_RANK[claim.privacy_class]:
            blockers.append(f"privacy_class_downgrade:{evidence_id}")
        if not set(evidence.consent_refs).issubset(claim.consent_refs):
            blockers.append(f"missing_consent_propagation:{evidence_id}")
        if evidence.observed_at > claim.created_at:
            blockers.append(f"evidence_postdates_claim:{evidence_id}")
        if evidence.expires_at is not None and evaluated >= evidence.expires_at:
            blockers.append(f"evidence_expired:{evidence_id}")
        for conflict in conflicts_by_key.get(
            (ConstructionRecordKind.EVIDENCE.value, evidence.state_key), ()
        ):
            blockers.append(f"conflicting_evidence:{evidence_id}")
            conflict_ids.extend(conflict.active_event_ids)

    if active_evidence and all(
        item.evidence_class in _NON_DISPOSITIVE for item in active_evidence
    ):
        blockers.append("non_dispositive_evidence_only")

    blocker_tuple = tuple(sorted(set(blockers)))
    return ConstructionReadinessReport(
        claim_id=claim_id,
        ready=not blocker_tuple,
        blockers=blocker_tuple,
        active_evidence_ids=tuple(sorted(item.evidence_id for item in active_evidence)),
        conflict_event_ids=tuple(sorted(set(conflict_ids))),
        state_digest=state.state_digest,
        evaluated_at=evaluated,
    )


def query_claim_readiness(
    state: ConstructionProjectState,
    *,
    claim_id: str,
    now: float,
) -> ConstructionReadinessReport:
    state.__post_init__()
    evaluated = _timestamp(now, "now")
    claims, evidence, conflicts = _readiness_indexes(state)
    return _query_claim_readiness_validated(
        state,
        claim_id=claim_id,
        evaluated=evaluated,
        claim_events_by_id=claims,
        evidence_by_id=evidence,
        conflicts_by_key=conflicts,
    )


''',
    )
    replace_between(
        path,
        "def query_project_readiness(\n",
        "__all__ = [\n",
        '''def query_project_readiness(
    state: ConstructionProjectState,
    *,
    now: float,
) -> tuple[ConstructionReadinessReport, ...]:
    state.__post_init__()
    evaluated = _timestamp(now, "now")
    claims, evidence, conflicts = _readiness_indexes(state)
    return tuple(
        _query_claim_readiness_validated(
            state,
            claim_id=claim_id,
            evaluated=evaluated,
            claim_events_by_id=claims,
            evidence_by_id=evidence,
            conflicts_by_key=conflicts,
        )
        for claim_id in sorted(claims)
    )


''',
    )


def patch_authority() -> None:
    path = "aura_construction_authority.py"
    replace_exact(
        path,
        '''def _tuple_strings(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} contains an invalid value")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} must not contain duplicates")
    if value != tuple(sorted(value)):
        raise ValueError(f"{name} must use canonical sorted order")
    if not allow_empty and not value:
        raise ValueError(f"{name} must not be empty")
    return value
''',
        '''def _tuple_strings(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(_text(item, f"{name}[]") for item in value)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{name} must use canonical sorted order")
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized
''',
    )
    replace_exact(
        path,
        '''def _normalized_unique(values: Iterable[Any], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return tuple(sorted(result))
''',
        '''def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _normalized_unique(values: Iterable[Any], name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    items = _sequence_input(values, name)
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        if type(raw) is not str:
            raise ValueError(f"{name} contains a non-string value")
        normalized = " ".join(raw.split())
        if not normalized:
            raise ValueError(f"{name} contains an empty value")
        if normalized in seen:
            raise ValueError(f"{name} contains duplicate or normalization-colliding values")
        seen.add(normalized)
        result.append(normalized)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    return tuple(sorted(result))
''',
    )
    replace_exact(
        path,
        '''        if any(item.state_digest != self.state_digest for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another state")
''',
        '''        if any(item.state_digest != self.state_digest for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another state")
        if any(item.evaluated_at != self.evaluated_at for item in self.readiness_reports):
            raise ValueError("authority result mixes readiness reports from another evaluation")
''',
    )
    replace_exact(
        path,
        '''        evidence_ready = all(item.ready for item in readiness_reports)
        reasons: set[str] = set()
''',
        '''        evidence_ready = all(item.ready for item in readiness_reports)
        readiness_expiries: list[float] = []
        active_claims = {
            event.record.claim_id: event.record
            for event in state.active_claim_events
            if type(event.record) is ConstructionClaim
        }
        active_evidence = {
            event.record.evidence_id: event.record
            for event in state.active_evidence_events
            if type(event.record) is ConstructionEvidence
        }
        for claim_id in request.required_claim_ids:
            claim = active_claims.get(claim_id)
            if claim is None:
                continue
            if claim.expires_at is not None:
                readiness_expiries.append(claim.expires_at)
            for evidence_id in claim.evidence_refs:
                evidence = active_evidence.get(evidence_id)
                if evidence is not None and evidence.expires_at is not None:
                    readiness_expiries.append(evidence.expires_at)
        reasons: set[str] = set()
''',
    )
    replace_exact(
        path,
        '''            "expires_at": _timestamp(
                min(request.expires_at, governance_decision.expires_at)
                if governance_decision.authorized
                else request.expires_at,
                "expires_at",
            ),
''',
        '''            "expires_at": _timestamp(
                min(
                    request.expires_at,
                    governance_decision.expires_at,
                    *readiness_expiries,
                )
                if ready
                else request.expires_at,
                "expires_at",
            ),
''',
    )
    replace_between(
        path,
        "    @classmethod\n    def from_dict(cls, value: Mapping[str, Any]) -> \"ConstructionAuthorityResult\":\n",
        "    @staticmethod\n    def _payload_from_values",
        '''    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        request: ConstructionActionRequest | None = None,
        state: ConstructionProjectState | None = None,
        governance_decision: GovernanceDecision | None = None,
    ) -> "ConstructionAuthorityResult":
        data = dict(value)
        result = cls(
            result_id=data.get("result_id"),
            result_digest=data.get("result_digest"),
            project_id=data.get("project_id"),
            scope_key=data.get("scope_key"),
            request_id=data.get("request_id"),
            request_digest=data.get("request_digest"),
            required_claim_ids=_sequence_input(
                data.get("required_claim_ids", ()), "result.required_claim_ids"
            ),
            state_digest=data.get("state_digest"),
            governance_decision_id=data.get("governance_decision_id"),
            governance_decision_digest=data.get("governance_decision_digest"),
            governance_authorized=data.get("governance_authorized"),
            evidence_ready=data.get("evidence_ready"),
            digitally_ready=data.get("digitally_ready"),
            readiness_reports=tuple(
                ConstructionReadinessReport.from_dict(dict(item))
                for item in _sequence_input(
                    data.get("readiness_reports", ()), "result.readiness_reports"
                )
            ),
            missing_reasons=_sequence_input(
                data.get("missing_reasons", ()), "result.missing_reasons"
            ),
            evaluated_at=data.get("evaluated_at"),
            expires_at=data.get("expires_at"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            human_release_required=data.get("human_release_required"),
            physical_work_authorized=data.get("physical_work_authorized"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )
        contexts = (request, state, governance_decision)
        if any(item is not None for item in contexts):
            if any(item is None for item in contexts):
                raise ValueError(
                    "authority result contextual validation requires request, state, and decision"
                )
            result.validate_against(
                request=request,
                state=state,
                governance_decision=governance_decision,
                now=result.evaluated_at,
            )
        elif result.digitally_ready:
            raise ValueError(
                "digitally ready authority results require contextual lineage validation"
            )
        return result

''',
    )
    replace_exact(
        path,
        '''    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_decision_binding(
''',
        '''    def validate_against(
        self,
        *,
        request: ConstructionActionRequest,
        state: ConstructionProjectState,
        governance_decision: GovernanceDecision,
        now: float,
    ) -> None:
        _validate_result_bindings(
            self,
            request=request,
            state=state,
            governance_decision=governance_decision,
            now=_timestamp(now, "now"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_decision_binding(
''',
        count=1,
    )
    replace_exact(
        path,
        '''    decision.validate_integrity()
''',
        '''    if type(decision) is not GovernanceDecision:
        raise ValueError("decision must be an exact GovernanceDecision")
    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    decision.validate_integrity()
''',
        count=1,
    )
    replace_exact(
        path,
        '''    result.__post_init__()
    request.__post_init__()
    state.__post_init__()
''',
        '''    if type(result) is not ConstructionAuthorityResult:
        raise ValueError("result must be an exact ConstructionAuthorityResult")
    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    if type(governance_decision) is not GovernanceDecision:
        raise ValueError("governance_decision must be an exact GovernanceDecision")
    result.__post_init__()
    request.__post_init__()
    state.__post_init__()
''',
        count=1,
    )
    replace_exact(
        path,
        '''    request.__post_init__()
    state.__post_init__()
    current = _timestamp(now, "now")
''',
        '''    if type(request) is not ConstructionActionRequest:
        raise ValueError("request must be an exact ConstructionActionRequest")
    if type(state) is not ConstructionProjectState:
        raise ValueError("state must be an exact ConstructionProjectState")
    if type(quorum_policy) is not QuorumPolicy:
        raise ValueError("quorum_policy must be an exact QuorumPolicy")
    if normal_policy is not None and type(normal_policy) is not QuorumPolicy:
        raise ValueError("normal_policy must be an exact QuorumPolicy")
    grant_items = tuple(grants)
    attestation_items = tuple(attestations)
    if not all(type(item) is AuthorityGrant for item in grant_items):
        raise ValueError("grants must contain exact AuthorityGrant values")
    if not all(type(item) is ApprovalAttestation for item in attestation_items):
        raise ValueError("attestations must contain exact ApprovalAttestation values")
    request.__post_init__()
    state.__post_init__()
    current = _timestamp(now, "now")
''',
        count=1,
    )
    replace_exact(path, "        grants=tuple(grants),", "        grants=grant_items,", count=1)
    replace_exact(path, "        attestations=tuple(attestations),", "        attestations=attestation_items,", count=1)

    predecessor_helper = '''def _validate_receipt_predecessor(
    *,
    ledger_id: str,
    sequence_number: int,
    previous_chain_digest: str,
    created_at: float,
    previous_receipt: ChainedAuthorityReceipt | None,
    trusted_checkpoint: TrustedCheckpoint | None,
    verified_checkpoint_refs: Iterable[str],
) -> None:
    if sequence_number == 1:
        if previous_receipt is not None or trusted_checkpoint is not None:
            raise ValueError("genesis receipt cannot declare a predecessor")
        if previous_chain_digest != GENESIS_CHAIN_DIGEST:
            raise ValueError("first construction receipt must use the genesis digest")
        return
    if (previous_receipt is None) == (trusted_checkpoint is None):
        raise ValueError(
            "non-genesis receipt requires exactly one previous receipt or trusted checkpoint"
        )
    if previous_receipt is not None:
        if type(previous_receipt) is not ChainedAuthorityReceipt:
            raise ValueError("previous_receipt must be an exact ChainedAuthorityReceipt")
        previous_receipt.validate_integrity()
        if previous_receipt.ledger_id != ledger_id:
            raise ValueError("previous receipt belongs to another ledger")
        if sequence_number != previous_receipt.sequence_number + 1:
            raise ValueError("receipt sequence does not follow its previous receipt")
        if previous_chain_digest != previous_receipt.chain_digest:
            raise ValueError("receipt previous digest does not match its previous receipt")
        if created_at < previous_receipt.created_at:
            raise ValueError("receipt predates its previous receipt")
        return
    if type(trusted_checkpoint) is not TrustedCheckpoint:
        raise ValueError("trusted_checkpoint must be an exact TrustedCheckpoint")
    trusted_checkpoint.validate_integrity(
        verified_checkpoint_refs=_trusted_refs(
            verified_checkpoint_refs, "verified_checkpoint_refs"
        )
    )
    if trusted_checkpoint.ledger_id != ledger_id:
        raise ValueError("trusted checkpoint belongs to another ledger")
    if sequence_number != trusted_checkpoint.sequence_number + 1:
        raise ValueError("receipt sequence does not follow its trusted checkpoint")
    if previous_chain_digest != trusted_checkpoint.chain_digest:
        raise ValueError("receipt previous digest does not match its trusted checkpoint")
    if created_at < trusted_checkpoint.created_at:
        raise ValueError("receipt predates its trusted checkpoint")


'''
    replace_exact(
        path,
        "def create_construction_receipt(\n",
        predecessor_helper + "def create_construction_receipt(\n",
        count=1,
    )
    replace_exact(
        path,
        '''    previous_chain_digest: str = GENESIS_CHAIN_DIGEST,
    externally_verified_receipt_ref: str,
''',
        '''    previous_chain_digest: str = GENESIS_CHAIN_DIGEST,
    previous_receipt: ChainedAuthorityReceipt | None = None,
    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
    externally_verified_receipt_ref: str,
''',
        count=1,
    )
    replace_exact(
        path,
        '''    if sequence_number == 1:
        if previous_chain_digest != GENESIS_CHAIN_DIGEST:
            raise ValueError("first construction receipt must use the genesis digest")
    else:
        _digest(previous_chain_digest, "previous_chain_digest")
''',
        '''    if sequence_number > 1:
        _digest(previous_chain_digest, "previous_chain_digest")
    _validate_receipt_predecessor(
        ledger_id=ledger_id,
        sequence_number=sequence_number,
        previous_chain_digest=previous_chain_digest,
        created_at=created,
        previous_receipt=previous_receipt,
        trusted_checkpoint=trusted_checkpoint,
        verified_checkpoint_refs=verified_checkpoint_refs,
    )
''',
        count=1,
    )
    replace_exact(
        path,
        '''        verified_receipt_bindings=verified_receipt_bindings,
        created_at=created,
    )
''',
        '''        verified_receipt_bindings=verified_receipt_bindings,
        created_at=created,
        previous_receipt=previous_receipt,
        trusted_checkpoint=trusted_checkpoint,
        verified_checkpoint_refs=verified_checkpoint_refs,
    )
''',
        count=1,
    )
    replace_exact(
        path,
        '''        verified_receipt_bindings: Mapping[str, str],
        created_at: float,
    ) -> "ConstructionReceiptBinding":
''',
        '''        verified_receipt_bindings: Mapping[str, str],
        created_at: float,
        previous_receipt: ChainedAuthorityReceipt | None = None,
        trusted_checkpoint: TrustedCheckpoint | None = None,
        verified_checkpoint_refs: Iterable[str] = (),
    ) -> "ConstructionReceiptBinding":
''',
        count=1,
    )
    replace_exact(
        path,
        '''        chain_receipt.validate_integrity()
        expected_ledger = f"construction-authority/{authority_result.project_id}"
''',
        '''        chain_receipt.validate_integrity()
        _validate_receipt_predecessor(
            ledger_id=chain_receipt.ledger_id,
            sequence_number=chain_receipt.sequence_number,
            previous_chain_digest=chain_receipt.previous_chain_digest,
            created_at=chain_receipt.created_at,
            previous_receipt=previous_receipt,
            trusted_checkpoint=trusted_checkpoint,
            verified_checkpoint_refs=verified_checkpoint_refs,
        )
        expected_ledger = f"construction-authority/{authority_result.project_id}"
''',
        count=1,
    )
    replace_exact(
        path,
        '''        verified_receipt_bindings: Mapping[str, str],
    ) -> None:
''',
        '''        verified_receipt_bindings: Mapping[str, str],
        previous_receipt: ChainedAuthorityReceipt | None = None,
        trusted_checkpoint: TrustedCheckpoint | None = None,
        verified_checkpoint_refs: Iterable[str] = (),
    ) -> None:
''',
        count=1,
    )
    replace_exact(
        path,
        '''            verified_receipt_bindings=verified_receipt_bindings,
            created_at=self.created_at,
        )
''',
        '''            verified_receipt_bindings=verified_receipt_bindings,
            created_at=self.created_at,
            previous_receipt=previous_receipt,
            trusted_checkpoint=trusted_checkpoint,
            verified_checkpoint_refs=verified_checkpoint_refs,
        )
''',
        count=1,
    )
    replace_exact(
        path,
        '''    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
):
''',
        '''    trusted_checkpoint: TrustedCheckpoint | None = None,
    verified_checkpoint_refs: Iterable[str] = (),
    require_digitally_ready: bool = True,
):
''',
        count=1,
    )
    replace_exact(
        path,
        '''    record_digests: dict[str, str] = {}
''',
        '''    if type(require_digitally_ready) is not bool:
        raise ValueError("require_digitally_ready must be boolean")
    if trusted_checkpoint is not None and type(trusted_checkpoint) is not TrustedCheckpoint:
        raise ValueError("trusted_checkpoint must be an exact TrustedCheckpoint")
    record_digests: dict[str, str] = {}
''',
        count=1,
    )
    replace_exact(
        path,
        '''        if key != result.result_id:
            raise ValueError("results_by_id key does not match result identity")
        record_digests[key] = result.result_digest
''',
        '''        if key != result.result_id:
            raise ValueError("results_by_id key does not match result identity")
        if require_digitally_ready and not result.digitally_ready:
            raise ValueError("receipt verification requires digitally ready authority results")
        record_digests[key] = result.result_digest
''',
        count=1,
    )


def patch_tests() -> None:
    append_once(
        "tests/test_aura_construction_contracts.py",
        "test_review_hardening_scalar_reference_collections_fail_closed",
        r'''
def test_review_hardening_scalar_reference_collections_fail_closed():
    item = evidence()
    payload = item.to_dict()
    payload["consent_refs"] = "consent-ref"
    with pytest.raises(ValueError, match="list or tuple"):
        ConstructionEvidence.from_dict(payload)

    claimed = claim(item)
    payload = claimed.to_dict()
    payload["evidence_refs"] = item.evidence_id
    with pytest.raises(ValueError, match="list or tuple"):
        ConstructionClaim.from_dict(payload)


def test_review_hardening_scope_rejects_falsy_non_string_components():
    for value in (None, False, 0):
        with pytest.raises(ValueError, match="must be a string"):
            ConstructionScope("P1", value)
        with pytest.raises(ValueError, match="must be a string"):
            ConstructionScope("P1", "Z1", value)


def test_review_hardening_event_rejects_invalid_record_before_dereference():
    item = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace",
        record=evidence(),
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=3.0,
    )
    with pytest.raises(ValueError, match="exact ConstructionClaim or ConstructionEvidence"):
        replace(item, record=object())


def test_review_hardening_policy_scope_omits_state_wildcards():
    item = evidence(scope=ConstructionScope("P1"))
    event = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace",
        record=item,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=3.0,
    )
    assert event.to_aura_event_envelope().policy_scope == "construction/P1"
''',
    )
    append_once(
        "tests/test_aura_construction_authority.py",
        "test_review_hardening_result_expiry_is_capped_by_evidence_freshness",
        r'''
def _freshness_fixture():
    scope = ConstructionScope("P1", "Z1", "WP1")
    evidence = ConstructionEvidence.create(
        scope=scope,
        subject_id="wall",
        evidence_class=ConstructionEvidenceClass.DOCUMENT,
        source_ref="doc",
        payload_digest=D,
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.9,
        authority_class=ConstructionAuthorityClass.INFORMATIVE,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        observed_at=1,
        expires_at=12,
    )
    event1 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        trace_id="trace-freshness",
        record=evidence,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        created_at=2,
    )
    claim = ConstructionClaim.create(
        scope=scope,
        subject_id="wall",
        predicate="installed",
        value_digest=D2,
        claimant_id="contractor",
        evidence_refs=(evidence.evidence_id,),
        measurement_class=MeasurementClass.EMPIRICAL,
        confidence=0.8,
        authority_class=ConstructionAuthorityClass.CONTRACTOR,
        privacy_class=ConstructionPrivacyClass.PROJECT,
        created_at=3,
        expires_at=20,
    )
    event2 = ConstructionEvent.create(
        ledger_id="construction/P1",
        sequence_number=2,
        previous_chain_digest=event1.chain_digest,
        trace_id="trace-freshness",
        record=claim,
        actor_id="human",
        actor_type=ActorType.HUMAN,
        parent_event_ids=(event1.event_id,),
        created_at=4,
    )
    state = replay_construction_events((event1, event2))
    request = ConstructionActionRequest.create(
        scope=scope,
        action_kind="release work package",
        policy_scope="construction/P1/Z1",
        capability_scope="construction.release",
        risk_class=RiskClass.HIGH,
        required_claim_ids=(claim.claim_id,),
        created_at=5,
        expires_at=40,
    )
    return state, request


def test_review_hardening_result_expiry_is_capped_by_evidence_freshness():
    state, request = _freshness_fixture()
    result, _ = evaluate_ready(state, request)
    assert result.digitally_ready is True
    assert result.expires_at == 12.0


def test_review_hardening_ready_result_deserialization_requires_context():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    with pytest.raises(ValueError, match="contextual lineage"):
        ConstructionAuthorityResult.from_dict(result.to_dict())
    loaded = ConstructionAuthorityResult.from_dict(
        result.to_dict(), request=request, state=state, governance_decision=decision
    )
    assert loaded == result


def test_review_hardening_evaluator_requires_exact_canonical_types():
    state, request, _ = fixtures()
    grants, attestations, _ = authority_material(request)
    with pytest.raises(ValueError, match="exact QuorumPolicy"):
        evaluate_construction_authority(
            request=request,
            state=state,
            grants=grants,
            attestations=attestations,
            quorum_policy=object(),
            verified_authority_refs=("authority-ref",),
            verified_attestation_refs=("attestation-ref",),
            now=10,
        )


def test_review_hardening_non_genesis_receipt_requires_verified_predecessor():
    state, request, _ = fixtures()
    result, decision = evaluate_ready(state, request)
    first, _ = receipt_for(state, request, result, decision)
    with pytest.raises(ValueError, match="previous receipt or trusted checkpoint"):
        receipt_for(
            state,
            request,
            result,
            decision,
            sequence_number=2,
            previous_chain_digest=first.chain_digest,
            created_at=12,
        )
    second, binding = receipt_for(
        state,
        request,
        result,
        decision,
        sequence_number=2,
        previous_chain_digest=first.chain_digest,
        previous_receipt=first,
        created_at=12,
    )
    binding.validate_against(
        authority_result=result,
        request=request,
        state=state,
        governance_decision=decision,
        governance_replay=governance_replay(request),
        chain_receipt=second,
        verified_receipt_bindings={"receipt-ref": result.result_digest},
        previous_receipt=first,
    )


def test_review_hardening_receipt_verification_rejects_non_ready_results_by_default():
    state, request, _ = fixtures()
    grants, attestations, policy = authority_material(
        request, decision=AttestationDecision.REJECT
    )
    result, _ = evaluate_construction_authority(
        request=request,
        state=state,
        grants=grants,
        attestations=attestations,
        quorum_policy=policy,
        verified_authority_refs=("authority-ref",),
        verified_attestation_refs=("attestation-ref",),
        now=10,
    )
    receipt = __import__("aura_relational_authority").ChainedAuthorityReceipt.create(
        ledger_id="construction-authority/P1",
        sequence_number=1,
        previous_chain_digest=GENESIS_CHAIN_DIGEST,
        record_id=result.result_id,
        record_digest=result.result_digest,
        created_at=11,
    )
    with pytest.raises(ValueError, match="digitally ready"):
        verify_construction_receipts((receipt,), results_by_id={result.result_id: result})
    continuity = verify_construction_receipts(
        (receipt,),
        results_by_id={result.result_id: result},
        require_digitally_ready=False,
    )
    assert continuity.valid is True
''',
    )
    replace_exact(
        "tests/test_aura_construction_authority.py",
        '''    assert not decision.authorized
    assert not result.digitally_ready
''',
        '''    assert not decision.authorized
    assert not result.digitally_ready
    assert any("invalid_attestation" in reason for reason in result.missing_reasons)
''',
        count=1,
    )


def patch_docs() -> None:
    block = '''
## CodeRabbit and manual adversarial review continuation

- CodeRabbit review: 15 actionable threads examined individually.
- Confirmed repairs: canonical materialization, strict collection containers,
  canonical policy scopes, evidence-freshness expiry, exact canonical authority
  types, deterministic result revalidation, verified receipt predecessors,
  non-ready receipt rejection, state-query indexing, and fail-closed event order.
- Staging payloads and one-time tools are removed only after exact-branch tests.
- Construction remains proposal-only and never authorizes physical work.
'''
    for path in (
        "docs/AURA_CROSS_ARENA_CHANGE_HANDOFF_LOG.md",
        "docs/AURA_SCO_CONSTRUCTION_ARENA_EMERGENT_REFACTOR_ADDENDUM.md",
        "docs/AURA_SCO_PHASE2_E4_E6_REVIEW_EVIDENCE.md",
    ):
        append_once(path, "CodeRabbit and manual adversarial review continuation", block)


def main() -> None:
    patch_contracts()
    patch_state()
    patch_authority()
    patch_tests()
    patch_docs()
    print("SCO_PHASE2_REVIEW_FIXES_APPLIED")


if __name__ == "__main__":
    main()
