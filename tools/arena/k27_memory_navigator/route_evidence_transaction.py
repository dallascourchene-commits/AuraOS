from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .reflexive_topology import TopologyCertificate, TopologyDisposition
from .temporal_zone import ZoneCertificate, ZoneDisposition


class TransactionDisposition(str, Enum):
    READY_D0 = "READY_D0"
    HOLD_TOPOLOGY = "HOLD_TOPOLOGY"
    HOLD_TEMPORAL_ZONE = "HOLD_TEMPORAL_ZONE"


@dataclass(frozen=True)
class RouteEvidenceTransaction:
    disposition: TransactionDisposition
    post_partition: tuple[tuple[str, ...], ...]
    reasons: tuple[str, ...]
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def certify(topology: TopologyCertificate, zone: ZoneCertificate) -> RouteEvidenceTransaction:
    if topology.disposition is not TopologyDisposition.READY_POST_PROGRAM:
        return RouteEvidenceTransaction(
            TransactionDisposition.HOLD_TOPOLOGY, (), ("topology_program_not_certified",))
    if zone.disposition is not ZoneDisposition.READY_D0:
        return RouteEvidenceTransaction(
            TransactionDisposition.HOLD_TEMPORAL_ZONE, topology.post_partition,
            ("relational_time_zone_inconsistent",))
    return RouteEvidenceTransaction(
        TransactionDisposition.READY_D0, topology.post_partition,
        ("post_program_partition_and_relational_zone_certified",))
