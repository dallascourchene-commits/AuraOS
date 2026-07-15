"""Small exact-copy identity helper for bounded compatibility adapters."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class ExactRecordIdentityError(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"copied field does not preserve its source: {field}")
        self.field = field


def require_exact_copied_fields(
    source: Mapping[str, Any],
    copied: Mapping[str, Any],
    field_pairs: Sequence[tuple[str, str]],
) -> None:
    for source_field, copied_field in field_pairs:
        if copied.get(copied_field) != source.get(source_field):
            raise ExactRecordIdentityError(copied_field)


__all__ = ["ExactRecordIdentityError", "require_exact_copied_fields"]
