from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from enum import Enum
from typing import Sequence
from atomic_absorption import Proposal, OwnerSnapshot, PublicationPlan, Disposition, plan, digest


class ResourceError(ValueError):
    pass


class LeaseMode(str, Enum):
    SHARED_READ = 'SHARED_READ'
    EXCLUSIVE = 'EXCLUSIVE'


class RequirementMode(str, Enum):
    READ = 'READ'
    WRITE = 'WRITE'


class ResourceDisposition(str, Enum):
    READY = 'READY'
    BASE_HOLD = 'BASE_HOLD'
    LEASE_MISSING_HOLD = 'LEASE_MISSING_HOLD'
    LEASE_STALE_HOLD = 'LEASE_STALE_HOLD'
    LEASE_CONFLICT_HOLD = 'LEASE_CONFLICT_HOLD'
    LEASE_IDENTITY_HOLD = 'LEASE_IDENTITY_HOLD'


@dataclass(frozen=True)
class Lease:
    lease_id: str
    resource_key: str
    holder_actor: str
    holder_lineage: str
    mode: LeaseMode
    issued_s: int
    expires_s: int
    generation: int
    released_s: int | None = None


@dataclass(frozen=True)
class LeaseRegistrySnapshot:
    generation: int
    leases: tuple[Lease, ...]
    authority_ceiling: str = 'D0'
    gate10: bool = False

    @property
    def root(self) -> str:
        return digest({
            'schema': 'AURA-RESOURCE-LEASE-REGISTRY-v1',
            'generation': self.generation,
            'leases': [asdict(x) for x in sorted(self.leases, key=lambda x: (x.resource_key, x.lease_id))],
            'authority_ceiling': self.authority_ceiling,
            'gate10': self.gate10,
        })


@dataclass(frozen=True)
class ResourceRequirement:
    resource_key: str
    mode: RequirementMode
    lease_id: str


@dataclass(frozen=True)
class ResourceProposal:
    proposal: Proposal
    resources: tuple[ResourceRequirement, ...] = ()


@dataclass(frozen=True)
class ResourcePublicationPlan:
    disposition: ResourceDisposition
    base_disposition: str
    expected_owner_head: str
    expected_lease_root: str
    accepted_proposals: tuple[str, ...]
    resource_bindings: tuple[tuple[str, str], ...]
    conflicts: tuple[str, ...]
    base_plan: PublicationPlan | None
    manifest_root: str
    evaluated_at_s: int
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class ResourcePublicationReceipt:
    committed: bool
    old_owner_head: str
    new_head: str | None
    observed_lease_root: str
    expected_lease_root: str
    manifest_root: str
    write_count: int
    resource_count: int
    lost_consequence_count: int
    effect_authority: bool = False
    gate10: bool = False


def _text(v, name):
    if type(v) is not str or not v or any(ord(c) < 32 for c in v):
        raise ResourceError(name)
    return v


def _nn(v, name):
    if type(v) is not int or v < 0:
        raise ResourceError(name)
    return v


def _validate_registry(reg: LeaseRegistrySnapshot, now_s: int):
    _nn(reg.generation, 'BAD_REGISTRY_GENERATION')
    _nn(now_s, 'BAD_NOW')
    if reg.authority_ceiling != 'D0' or reg.gate10:
        raise ResourceError('REGISTRY_AUTHORITY_WIDENING')
    ids = set()
    for l in reg.leases:
        for x, n in ((l.lease_id, 'BAD_LEASE_ID'), (l.resource_key, 'BAD_RESOURCE_KEY'), (l.holder_actor, 'BAD_HOLDER_ACTOR'), (l.holder_lineage, 'BAD_HOLDER_LINEAGE')):
            _text(x, n)
        _nn(l.issued_s, 'BAD_ISSUED')
        _nn(l.expires_s, 'BAD_EXPIRES')
        _nn(l.generation, 'BAD_LEASE_GENERATION')
        if l.released_s is not None:
            _nn(l.released_s, 'BAD_RELEASED')
        if l.issued_s > l.expires_s:
            raise ResourceError('LEASE_TIME_INVERSION')
        if l.released_s is not None and l.released_s < l.issued_s:
            raise ResourceError('LEASE_RELEASE_BEFORE_ISSUE')
        if l.issued_s > now_s:
            raise ResourceError('FUTURE_LEASE')
        if l.released_s is not None and l.released_s > now_s:
            raise ResourceError('FUTURE_RELEASE')
        if l.lease_id in ids:
            raise ResourceError('DUPLICATE_LEASE_ID')
        ids.add(l.lease_id)


def _active(reg: LeaseRegistrySnapshot, now_s: int) -> tuple[Lease, ...]:
    return tuple(l for l in reg.leases if l.expires_s > now_s and l.released_s is None)


def _registry_conflicts(active: Sequence[Lease]) -> tuple[str, ...]:
    by = {}
    for l in active:
        by.setdefault(l.resource_key, []).append(l)
    out = []
    for key, ls in sorted(by.items()):
        exclusive = [x for x in ls if x.mode is LeaseMode.EXCLUSIVE]
        if len(exclusive) > 1 or (exclusive and len(ls) > 1):
            out.append('active-lease-conflict:' + key + ':' + ','.join(sorted(x.lease_id for x in ls)))
    return tuple(out)


def _match_requirement(rp: ResourceProposal, req: ResourceRequirement, registry: LeaseRegistrySnapshot, now_s: int):
    _text(req.resource_key, 'BAD_RESOURCE_KEY')
    _text(req.lease_id, 'BAD_LEASE_ID')
    matches = [l for l in registry.leases if l.lease_id == req.lease_id and l.resource_key == req.resource_key]
    if not matches:
        return None, 'missing:' + req.resource_key + ':' + req.lease_id
    l = matches[0]
    if l.expires_s <= now_s or l.released_s is not None:
        return None, 'stale:' + req.resource_key + ':' + req.lease_id
    p = rp.proposal
    if l.holder_actor != p.actor_id or l.holder_lineage != p.lineage_root:
        return None, 'identity:' + req.resource_key + ':' + req.lease_id
    if req.mode is RequirementMode.WRITE and l.mode is not LeaseMode.EXCLUSIVE:
        return None, 'mode:' + req.resource_key + ':WRITE_REQUIRES_EXCLUSIVE'
    return l, None


def plan_resource_absorption(owner: OwnerSnapshot, registry: LeaseRegistrySnapshot, proposals: Sequence[ResourceProposal], *, now_s: int) -> ResourcePublicationPlan:
    _validate_registry(registry, now_s)
    if not proposals:
        raise ResourceError('NO_RESOURCE_PROPOSALS')
    active = _active(registry, now_s)
    reg_conf = _registry_conflicts(active)
    if reg_conf:
        return _hold(ResourceDisposition.LEASE_CONFLICT_HOLD, owner, registry, reg_conf, now_s)
    bindings = []
    transformed = []
    seen_req = {}
    for rp in proposals:
        p = rp.proposal
        req_ids = set()
        lease_rows = []
        for req in rp.resources:
            key = (req.resource_key, req.lease_id, req.mode.value)
            if key in req_ids:
                raise ResourceError('DUPLICATE_RESOURCE_REQUIREMENT')
            req_ids.add(key)
            lease, err = _match_requirement(rp, req, registry, now_s)
            if err:
                disp = (
                    ResourceDisposition.LEASE_IDENTITY_HOLD
                    if err.startswith(('identity:', 'mode:'))
                    else ResourceDisposition.LEASE_STALE_HOLD
                    if err.startswith('stale:')
                    else ResourceDisposition.LEASE_MISSING_HOLD
                )
                return _hold(disp, owner, registry, (p.proposal_id + ':' + err,), now_s)
            lease_rows.append({'requirement': asdict(req), 'lease': asdict(lease)})
            seen_req.setdefault(req.resource_key, []).append((p.proposal_id, req.mode, req.lease_id))
        lease_root = digest({
            'actor_id': p.actor_id,
            'lineage_root': p.lineage_root,
            'resources': lease_rows,
            'registry_root': registry.root,
            'evaluated_at_s': now_s,
        })
        bindings.append((p.proposal_id, lease_root))
        transformed.append(replace(p, receipt_root=digest({'base_receipt_root': p.receipt_root, 'resource_binding_root': lease_root})))
    claim_conf = []
    for key, rows in sorted(seen_req.items()):
        if len({lease_id for _, _, lease_id in rows}) > 1 and any(mode is RequirementMode.WRITE for _, mode, _ in rows):
            claim_conf.append('proposal-resource-conflict:' + key + ':' + ','.join(sorted(pid for pid, _, _ in rows)))
    if claim_conf:
        return _hold(ResourceDisposition.LEASE_CONFLICT_HOLD, owner, registry, tuple(claim_conf), now_s)
    bp = plan(owner, transformed)
    if bp.disposition is not Disposition.READY:
        return ResourcePublicationPlan(
            ResourceDisposition.BASE_HOLD,
            bp.disposition.value,
            owner.head,
            registry.root,
            (),
            tuple(sorted(bindings)),
            tuple(bp.conflicts) + tuple(bp.debris),
            bp,
            digest({'base_manifest': bp.manifest_root, 'lease_root': registry.root, 'bindings': sorted(bindings), 'now_s': now_s}),
            now_s,
        )
    root = digest({
        'schema': 'AURA-ATOMIC-RESOURCE-ABSORPTION-v1.1',
        'base_manifest': bp.manifest_root,
        'owner_head': owner.head,
        'lease_root': registry.root,
        'registry_generation': registry.generation,
        'bindings': sorted(bindings),
        'accepted': list(bp.accepted_proposals),
        'now_s': now_s,
        'authority': 'D0_NONPROMOTING',
        'gate10': False,
    })
    return ResourcePublicationPlan(
        ResourceDisposition.READY,
        bp.disposition.value,
        owner.head,
        registry.root,
        bp.accepted_proposals,
        tuple(sorted(bindings)),
        (),
        bp,
        root,
        now_s,
    )


def _hold(d, owner, registry, conflicts, now_s):
    root = digest({
        'schema': 'AURA-ATOMIC-RESOURCE-ABSORPTION-v1.1',
        'disposition': d.value,
        'owner_head': owner.head,
        'lease_root': registry.root,
        'conflicts': list(conflicts),
        'now_s': now_s,
    })
    return ResourcePublicationPlan(d, 'NOT_RUN', owner.head, registry.root, (), (), tuple(conflicts), None, root, now_s)


def _no_resource_commit(submitted, observed_owner_head, observed_lease_root, *, lost=None):
    return ResourcePublicationReceipt(
        False,
        observed_owner_head,
        None,
        observed_lease_root,
        submitted.expected_lease_root,
        submitted.manifest_root,
        0,
        0,
        len(submitted.accepted_proposals) if lost is None else lost,
    )


def commit_resource_absorption(
    submitted: ResourcePublicationPlan,
    *,
    observed_owner_head: str,
    observed_lease_root: str,
    owner: OwnerSnapshot | None = None,
    registry: LeaseRegistrySnapshot | None = None,
    proposals: Sequence[ResourceProposal] | None = None,
    now_s: int | None = None,
) -> ResourcePublicationReceipt:
    """Authenticate plan provenance, CAS current state, then revalidate lease liveness."""
    if owner is None or registry is None or proposals is None or now_s is None:
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root)
    if now_s < submitted.evaluated_at_s:
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root)
    if observed_owner_head != owner.head or observed_lease_root != registry.root:
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root)
    if observed_owner_head != submitted.expected_owner_head or observed_lease_root != submitted.expected_lease_root:
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root)
    canonical_at_plan = plan_resource_absorption(owner, registry, proposals, now_s=submitted.evaluated_at_s)
    if asdict(canonical_at_plan) != asdict(submitted):
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root, lost=len(canonical_at_plan.accepted_proposals))
    canonical_now = plan_resource_absorption(owner, registry, proposals, now_s=now_s)
    if canonical_now.disposition is not ResourceDisposition.READY or canonical_now.base_plan is None:
        return _no_resource_commit(submitted, observed_owner_head, observed_lease_root, lost=len(canonical_now.accepted_proposals))
    new_head = digest({
        'parent': observed_owner_head,
        'resource_manifest': canonical_now.manifest_root,
        'base_manifest': canonical_now.base_plan.manifest_root,
        'writes': list(canonical_now.base_plan.writes),
        'lease_root': observed_lease_root,
        'commit_observed_at_s': now_s,
    })
    return ResourcePublicationReceipt(
        True,
        observed_owner_head,
        new_head,
        observed_lease_root,
        canonical_now.expected_lease_root,
        canonical_now.manifest_root,
        len(canonical_now.base_plan.writes),
        len(canonical_now.resource_bindings),
        0,
    )


def omega8_resource_keeper(axes):
    return len(axes) == 8 and all(type(x) is int and x == 2 for x in axes)


def context13_resource_preserves_invalid(core8, tail5):
    if len(tail5) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in tail5):
        raise ResourceError('BAD_13D_TAIL')
    return omega8_resource_keeper(core8)
