from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

INF = 10**18


class ZoneDisposition(str, Enum):
    READY_D0 = "READY_D0"
    HOLD_INCONSISTENT = "HOLD_INCONSISTENT"


@dataclass(frozen=True)
class DifferenceConstraint:
    left: str
    right: str
    upper_bound: int  # left - right <= upper_bound

    def __post_init__(self) -> None:
        if not self.left or not self.right:
            raise ValueError("variable names required")
        if type(self.upper_bound) is not int:
            raise ValueError("upper_bound must be exact int")


@dataclass(frozen=True)
class ZoneCertificate:
    disposition: ZoneDisposition
    variables: tuple[str, ...]
    closure: tuple[tuple[int | None, ...], ...]
    contradiction_variables: tuple[str, ...]
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False


def compile_zone(variables, constraints):
    names = tuple(variables)
    if len(names) != len(set(names)) or any(not isinstance(x, str) or not x for x in names):
        raise ValueError("variables must be unique non-empty strings")
    idx = {v: i for i, v in enumerate(names)}
    size = len(names)
    distance = [[INF] * size for _ in range(size)]
    for i in range(size):
        distance[i][i] = 0
    for constraint in constraints:
        if constraint.left not in idx or constraint.right not in idx:
            raise ValueError("constraint variable not declared")
        left, right = idx[constraint.left], idx[constraint.right]
        distance[right][left] = min(distance[right][left], constraint.upper_bound)
    for k in range(size):
        for i in range(size):
            if distance[i][k] >= INF:
                continue
            prefix = distance[i][k]
            for j in range(size):
                candidate = prefix + distance[k][j]
                if candidate < distance[i][j]:
                    distance[i][j] = candidate
    bad = tuple(names[i] for i in range(size) if distance[i][i] < 0)
    closure = tuple(tuple(None if value >= INF else value for value in row) for row in distance)
    return ZoneCertificate(
        ZoneDisposition.HOLD_INCONSISTENT if bad else ZoneDisposition.READY_D0,
        names, closure, bad,
    )
