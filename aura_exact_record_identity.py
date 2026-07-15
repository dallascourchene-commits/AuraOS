"""Exact copied-record comparison for bounded compatibility adapters."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from aura_event_contracts import canonical_json


class ExactRecordIdentityError(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(f"copied field differs from source: {field}")
        self.field = field


def require_exact_copied_fields(
    source: Mapping[str, Any],
    copied: Mapping[str, Any],
    field_pairs: Sequence[tuple[str, str]],
) -> None:
    for source_field, copied_field in field_pairs:
        if source_field not in source or copied_field not in copied:
            raise ExactRecordIdentityError(copied_field)
        try:
            left = canonical_json(source[source_field])
            right = canonical_json(copied[copied_field])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ExactRecordIdentityError(copied_field) from exc
        if left != right:
            raise ExactRecordIdentityError(copied_field)


__all__ = ["ExactRecordIdentityError", "require_exact_copied_fields"]
