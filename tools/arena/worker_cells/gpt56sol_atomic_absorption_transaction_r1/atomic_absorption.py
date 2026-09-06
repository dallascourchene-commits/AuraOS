from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from hashlib import sha256
import json, re
from typing import Mapping, Sequence

HEX64 = re.compile(r'^[0-9a-f]{64}$')
STAGING_MARKERS = ('.v5-stage-marker', '.stage-marker', '.tmp', '.staging')


def digest(v):
    return sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


class E(ValueError):
    pass


class Disposition(str, Enum):
    READY = 'READY'
    REBASE_REQUIRED = 'REBASE_REQUIRED'
    CONFLICT_HOLD = 'CONFLICT_HOLD'
    DEBRIS_HOLD = 'DEBRIS_HOLD'
    AUTHORITY_HOLD = 'AUTHORITY_HOLD'


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    actor_id: str
    lineage_root: str
    base_head: str
    consequence_root: str
    receipt_root: str
    files: Mapping[str, str]
    asks_effect_authority: bool = False


@dataclass(frozen=True)
class OwnerSnapshot:
    head: str
    tree_root: str


@dataclass(frozen=True)
class PublicationPlan:
    disposition: Disposition
    expected_head: str
    accepted_proposals: tuple[str, ...]
    collapsed_proposals: tuple[str, ...]
    conflicts: tuple[str, ...]
    debris: tuple[str, ...]
    writes: tuple[tuple[str, str], ...]
    manifest_root: str
    effect_authority: bool = False
    gate10: bool = False


@dataclass(frozen=True)
class PublicationReceipt:
    committed: bool
    old_head: str
    new_head: str | None
    plan_root: str
    manifest_root: str
    write_count: int
    lost_consequence_count: int
    effect_authority: bool = False
    gate10: bool = False


def _text(x, n):
    if type(x) is not str or not x or any(ord(c) < 32 for c in x):
        raise E(n)
    return x


def _hex(x, n):
    _text(x, n)
    if HEX64.fullmatch(x) is None:
        raise E(n)
    return x


def _path(p):
    _text(p, 'BAD_PATH')
    if p.startswith('/') or '..' in p.split('/'):
        raise E('BAD_PATH')
    return p


def _is_debris(p):
    low = p.lower()
    return any(m in low for m in STAGING_MARKERS)


def _proposal_binding(p: Proposal):
    return {
        'proposal_id': p.proposal_id,
        'actor_id': p.actor_id,
        'lineage_root': p.lineage_root,
        'base_head': p.base_head,
        'consequence_root': p.consequence_root,
        'receipt_root': p.receipt_root,
        'files': sorted(p.files.items()),
        'asks_effect_authority': p.asks_effect_authority,
    }


def _publication_payload_root(p: Proposal):
    return digest({
        'consequence_root': p.consequence_root,
        'receipt_root': p.receipt_root,
        'files': sorted(p.files.items()),
        'asks_effect_authority': p.asks_effect_authority,
    })


def validate_proposal(p: Proposal):
    for x, n in ((p.proposal_id, 'BAD_PROPOSAL_ID'), (p.actor_id, 'BAD_ACTOR'), (p.lineage_root, 'BAD_LINEAGE')):
        _text(x, n)
    for x, n in ((p.base_head, 'BAD_BASE_HEAD'), (p.consequence_root, 'BAD_CONSEQUENCE_ROOT'), (p.receipt_root, 'BAD_RECEIPT_ROOT')):
        _hex(x, n)
    if type(p.asks_effect_authority) is not bool:
        raise E('BAD_AUTHORITY_FLAG')
    if not p.files:
        raise E('EMPTY_PROPOSAL')
    for path, blob in p.files.items():
        _path(path)
        _hex(blob, 'BAD_BLOB_DIGEST')


def plan(snapshot: OwnerSnapshot, proposals: Sequence[Proposal]) -> PublicationPlan:
    _hex(snapshot.head, 'BAD_OWNER_HEAD')
    _hex(snapshot.tree_root, 'BAD_TREE_ROOT')
    if not proposals:
        raise E('NO_PROPOSALS')
    for p in proposals:
        validate_proposal(p)
    if any(p.asks_effect_authority for p in proposals):
        return _plan_hold(Disposition.AUTHORITY_HOLD, snapshot, proposals, (), ())
    stale = tuple(sorted(p.proposal_id for p in proposals if p.base_head != snapshot.head))
    if stale:
        return _plan_hold(Disposition.REBASE_REQUIRED, snapshot, proposals, stale, ())
    debris = tuple(sorted({path for p in proposals for path in p.files if _is_debris(path)}))
    if debris:
        return _plan_hold(Disposition.DEBRIS_HOLD, snapshot, proposals, (), debris)
    ids = [p.proposal_id for p in proposals]
    if len(set(ids)) != len(ids):
        dup = tuple(sorted({x for x in ids if ids.count(x) > 1}))
        return _plan_hold(
            Disposition.CONFLICT_HOLD,
            snapshot,
            proposals,
            tuple(f'duplicate-proposal-id:{x}' for x in dup),
            (),
        )
    by_cons = {}
    collapsed = []
    consequence_conflicts = []
    for p in sorted(proposals, key=lambda x: x.proposal_id):
        prev = by_cons.get(p.consequence_root)
        if prev is None:
            by_cons[p.consequence_root] = p
            continue
        if _publication_payload_root(prev) == _publication_payload_root(p):
            collapsed.append(p.proposal_id)
        else:
            a, b = sorted((prev.proposal_id, p.proposal_id))
            consequence_conflicts.append(f'consequence-divergence:{p.consequence_root}:{a}:{b}')
    if consequence_conflicts:
        return _plan_hold(Disposition.CONFLICT_HOLD, snapshot, proposals, tuple(sorted(consequence_conflicts)), ())
    accepted = tuple(by_cons.values())
    path_owner = {}
    conflicts = []
    writes = {}
    for p in accepted:
        for path, blob in sorted(p.files.items()):
            if path not in path_owner:
                path_owner[path] = (p.proposal_id, blob)
                writes[path] = blob
            else:
                prev_id, prev_blob = path_owner[path]
                if prev_blob != blob:
                    conflicts.append(f'{path}:{prev_id}:{p.proposal_id}')
    if conflicts:
        return _plan_hold(Disposition.CONFLICT_HOLD, snapshot, accepted, tuple(sorted(conflicts)), ())
    body = {
        'schema': 'AURA-ATOMIC-ABSORPTION-v1.2',
        'expected_head': snapshot.head,
        'tree_root': snapshot.tree_root,
        'accepted': [p.proposal_id for p in accepted],
        'collapsed': sorted(collapsed),
        'writes': sorted(writes.items()),
        'consequences': sorted(p.consequence_root for p in accepted),
        'receipts': sorted(p.receipt_root for p in accepted),
        'proposal_bindings': [_proposal_binding(p) for p in sorted(proposals, key=lambda x: x.proposal_id)],
        'authority': 'D0_NONPROMOTING',
        'gate10': False,
    }
    root = digest(body)
    return PublicationPlan(
        Disposition.READY,
        snapshot.head,
        tuple(p.proposal_id for p in accepted),
        tuple(sorted(collapsed)),
        (),
        (),
        tuple(sorted(writes.items())),
        root,
    )


def _plan_hold(d, snapshot, proposals, conflicts, debris):
    body = {
        'schema': 'AURA-ATOMIC-ABSORPTION-v1.2',
        'disposition': d.value,
        'expected_head': snapshot.head,
        'proposals': sorted(p.proposal_id for p in proposals),
        'conflicts': list(conflicts),
        'debris': list(debris),
        'proposal_bindings': [_proposal_binding(p) for p in sorted(proposals, key=lambda x: x.proposal_id)],
    }
    return PublicationPlan(d, snapshot.head, (), (), tuple(conflicts), tuple(debris), (), digest(body))


def _no_commit_receipt(submitted: PublicationPlan, observed_head: str, lost: int | None = None) -> PublicationReceipt:
    return PublicationReceipt(
        False,
        observed_head,
        None,
        digest(asdict(submitted)),
        submitted.manifest_root,
        0,
        len(submitted.accepted_proposals) if lost is None else lost,
    )


def commit(
    submitted: PublicationPlan,
    observed_head: str,
    *,
    snapshot: OwnerSnapshot | None = None,
    proposals: Sequence[Proposal] | None = None,
) -> PublicationReceipt:
    """Point-of-use commit fence.

    A PublicationPlan is a transport object, never commit authority. Consequential
    commit requires authoritative planner inputs so the exact canonical plan can be
    reconstructed at the boundary. The legacy two-argument call fails closed.
    """
    _hex(observed_head, 'BAD_OBSERVED_HEAD')
    if snapshot is None or proposals is None:
        return _no_commit_receipt(submitted, observed_head)
    canonical = plan(snapshot, proposals)
    if digest(asdict(submitted)) != digest(asdict(canonical)):
        return _no_commit_receipt(submitted, observed_head, len(canonical.accepted_proposals))
    if canonical.disposition is not Disposition.READY:
        return _no_commit_receipt(submitted, observed_head, 0)
    if observed_head != canonical.expected_head:
        return _no_commit_receipt(submitted, observed_head, len(canonical.accepted_proposals))
    new_head = digest({
        'parent': observed_head,
        'manifest': canonical.manifest_root,
        'writes': list(canonical.writes),
    })
    return PublicationReceipt(
        True,
        observed_head,
        new_head,
        digest(asdict(canonical)),
        canonical.manifest_root,
        len(canonical.writes),
        0,
    )


def omega8_keeper(axes):
    return len(axes) == 8 and all(type(x) is int and x == 2 for x in axes)


def context13_preserves_invalid(core8, tail5):
    if len(tail5) != 5 or any(type(x) is not int or x not in (0, 1, 2) for x in tail5):
        raise E('BAD_13D_TAIL')
    return omega8_keeper(core8)
