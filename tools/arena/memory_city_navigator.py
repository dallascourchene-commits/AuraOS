from __future__ import annotations

"""Read-only Memory City Navigator over the existing K27 runtime owner.

D0/non-promoting. K27MemoryRuntime remains the source/store/currentness owner.
This module consumes route_projection() and compiles deterministic RouteCards
and exact source-span reopen handles. It never invokes mutation APIs and never
mints truth, execution, effect, or Gate-10 authority.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol

SCHEMA = "AURA-MEMORY-CITY-NAVIGATOR-v1"
ROUTE_PROJECTION_SCHEMA = "AURA-K27-ROUTE-PROJECTION-v1"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


class NavigatorError(ValueError):
    pass


class RouteProjectionRuntime(Protocol):
    consumed: bool
    def route_projection(self, object_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OwnerCut:
    owner_pr: int
    owner_head: str
    map_lifecycle_epoch: int
    owner_incarnation: str

    def __post_init__(self) -> None:
        if type(self.owner_pr) is not int or self.owner_pr <= 0:
            raise NavigatorError("owner_pr must be positive")
        if not isinstance(self.owner_head, str) or len(self.owner_head) != 40:
            raise NavigatorError("owner_head must be a Git SHA")
        if type(self.map_lifecycle_epoch) is not int or self.map_lifecycle_epoch < 0:
            raise NavigatorError("map_lifecycle_epoch must be nonnegative")
        if not isinstance(self.owner_incarnation, str) or not self.owner_incarnation.strip():
            raise NavigatorError("owner_incarnation is required")


@dataclass(frozen=True)
class RouteCard:
    objective: str
    target_object_id: str
    target_k27: tuple[int, ...]
    source_revision_id: str
    source_epoch: int
    payload_root: str
    dependency_root: str
    owner_cut: OwnerCut
    upstream_currentness_asserted: bool
    review_only: bool = True
    projection_only: bool = True
    truth_authority: bool = False
    execution_authority: bool = False
    effect_authority: bool = False
    authority_minted: bool = False
    gate10: bool = False
    receipt_root: str = ""

    def receipt_payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("receipt_root", None)
        data["target_k27"] = list(self.target_k27)
        return data


def compile_route_card(runtime: RouteProjectionRuntime, *, objective: str,
                       object_id: str, owner_cut: OwnerCut) -> RouteCard:
    if not isinstance(objective, str) or not objective.strip():
        raise NavigatorError("objective is required")
    if not isinstance(object_id, str) or not object_id.startswith("MCXR-"):
        raise NavigatorError("target must be an MCXR route object")
    if getattr(runtime, "consumed", False):
        raise NavigatorError("runtime consumed; exact reopen required")

    projection = runtime.route_projection(object_id)
    if projection.get("schema") != ROUTE_PROJECTION_SCHEMA:
        raise NavigatorError("unexpected route projection schema")
    if projection.get("review_only") is not True:
        raise NavigatorError("route projection must remain review-only")
    if projection.get("execution_authority") is not False or projection.get("gate10") is not False:
        raise NavigatorError("route projection attempted authority escalation")

    binding = projection.get("binding")
    if not isinstance(binding, Mapping) or binding.get("object_id") != object_id:
        raise NavigatorError("projection identity mismatch")
    if binding.get("local_registry_current") is not True:
        raise NavigatorError("target is not current in bound local registry")
    for key in ("truth_authority", "effect_authority", "gate10"):
        if binding.get(key) not in (None, False):
            raise NavigatorError(f"binding attempted {key}")

    path = binding.get("path")
    if not isinstance(path, (list, tuple)) or any(type(x) is not int or not 0 <= x <= 26 for x in path):
        raise NavigatorError("invalid K27 path")
    revision = binding.get("revision_id")
    epoch = binding.get("epoch")
    if not isinstance(revision, str) or not revision:
        raise NavigatorError("source revision missing")
    if type(epoch) is not int or epoch < 0:
        raise NavigatorError("source epoch invalid")

    deps = projection.get("dependencies") or {}
    dep_epochs = projection.get("dependency_epochs")
    if not isinstance(deps, Mapping) or (dep_epochs is not None and not isinstance(dep_epochs, Mapping)):
        raise NavigatorError("invalid dependency surface")
    dependency_root = digest({
        "dependencies": dict(sorted(deps.items())),
        "dependency_epochs": None if dep_epochs is None else dict(sorted(dep_epochs.items())),
    })
    card = RouteCard(
        objective=objective.strip(), target_object_id=object_id, target_k27=tuple(path),
        source_revision_id=revision, source_epoch=epoch, payload_root=digest(projection.get("payload")),
        dependency_root=dependency_root, owner_cut=owner_cut,
        upstream_currentness_asserted=bool(binding.get("upstream_currentness_asserted", False)),
    )
    root = digest({"schema": SCHEMA, "route_card": card.receipt_payload()})
    return RouteCard(**{**asdict(card), "target_k27": tuple(path), "owner_cut": owner_cut, "receipt_root": root})


@dataclass(frozen=True)
class SourceSpanLocator:
    source_id: str
    parent_export_sha256: str
    start_line: int
    end_line: int
    span_sha256: str
    span_bytes: int
    k27_hint: tuple[int, ...] = ()
    authority_minted: bool = False

    def __post_init__(self) -> None:
        if not self.source_id:
            raise NavigatorError("source_id is required")
        for name, value in (("parent", self.parent_export_sha256), ("span", self.span_sha256)):
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise NavigatorError(f"{name} digest must be lowercase SHA-256")
        if type(self.start_line) is not int or type(self.end_line) is not int or self.start_line < 1 or self.end_line < self.start_line:
            raise NavigatorError("invalid line span")
        if type(self.span_bytes) is not int or self.span_bytes < 0:
            raise NavigatorError("span_bytes must be nonnegative")
        if self.authority_minted:
            raise NavigatorError("span locator cannot mint authority")
        if any(type(x) is not int or not 0 <= x <= 26 for x in self.k27_hint):
            raise NavigatorError("invalid K27 hint")


class SpanDisposition(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    REBIND_PARENT_CURRENTNESS = "REBIND_PARENT_CURRENTNESS"
    REHYDRATE_SPAN = "REHYDRATE_SPAN"
    HOLD_SOURCE_IDENTITY = "HOLD_SOURCE_IDENTITY"


def _span(text: str, start_line: int, end_line: int) -> bytes:
    if not isinstance(text, str):
        raise NavigatorError("provider text must be str")
    lines = text.splitlines(keepends=True)
    if start_line < 1 or end_line < start_line or end_line > len(lines):
        raise NavigatorError("span outside provider text")
    return "".join(lines[start_line - 1:end_line]).encode("utf-8")


def capture_source_span(*, source_id: str, provider_text: str, start_line: int,
                        end_line: int, k27_hint: tuple[int, ...] = ()) -> SourceSpanLocator:
    parent = provider_text.encode("utf-8")
    selected = _span(provider_text, start_line, end_line)
    return SourceSpanLocator(source_id, sha256(parent).hexdigest(), start_line, end_line,
                             sha256(selected).hexdigest(), len(selected), k27_hint)


def evaluate_source_span_at_use(locator: SourceSpanLocator, *, source_id: str,
                                provider_text: str) -> tuple[SpanDisposition, str]:
    if source_id != locator.source_id:
        return SpanDisposition.HOLD_SOURCE_IDENTITY, "source_id_changed"
    try:
        selected = _span(provider_text, locator.start_line, locator.end_line)
    except NavigatorError:
        return SpanDisposition.REHYDRATE_SPAN, "span_bounds_invalidated"
    if sha256(selected).hexdigest() != locator.span_sha256:
        return SpanDisposition.REHYDRATE_SPAN, "span_content_changed"
    if sha256(provider_text.encode("utf-8")).hexdigest() != locator.parent_export_sha256:
        return SpanDisposition.REBIND_PARENT_CURRENTNESS, "parent_changed_span_equal"
    return SpanDisposition.REUSE_EXACT, "exact_parent_and_span"


@dataclass(frozen=True)
class RouteUseLimits:
    max_hydration_bytes: int
    max_route_steps: int
    max_lawfield_transitions: int
    max_source_reopens: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) is not int or value < 0:
                raise NavigatorError(f"{name} must be nonnegative integer")


@dataclass(frozen=True)
class RouteUseObservation:
    hydration_bytes: int
    route_steps: int
    lawfield_transitions: int
    source_reopens: int


class RouteUseDisposition(str, Enum):
    REUSE_EXACT = "REUSE_EXACT"
    RECONSTRUCT_EVENT_TIME = "RECONSTRUCT_EVENT_TIME"
    REBIND_CURRENTNESS = "REBIND_CURRENTNESS"
    REPROVE_OWNER = "REPROVE_OWNER"
    REPROVE_CONE = "REPROVE_CONE"
    HOLD_BUDGET = "HOLD_BUDGET"


def evaluate_route_at_use(card: RouteCard, *, compiled_event_time: str, use_event_time: str,
                          current_owner_cut: OwnerCut, current_dependency_root: str,
                          compiled_validity_epoch: int, use_validity_epoch: int,
                          limits: RouteUseLimits, observation: RouteUseObservation) -> tuple[RouteUseDisposition, tuple[str, ...]]:
    reasons: list[str] = []
    disposition = RouteUseDisposition.REUSE_EXACT
    if use_event_time != compiled_event_time:
        disposition = RouteUseDisposition.RECONSTRUCT_EVENT_TIME; reasons.append("EVENT_TIME_CHANGED")
    elif (current_owner_cut.owner_pr, current_owner_cut.owner_head, current_owner_cut.owner_incarnation) != (card.owner_cut.owner_pr, card.owner_cut.owner_head, card.owner_cut.owner_incarnation):
        disposition = RouteUseDisposition.REPROVE_OWNER; reasons.append("OWNER_CHANGED")
    elif current_dependency_root != card.dependency_root:
        disposition = RouteUseDisposition.REPROVE_CONE; reasons.append("DEPENDENCY_ROOT_CHANGED")
    elif current_owner_cut.map_lifecycle_epoch != card.owner_cut.map_lifecycle_epoch or use_validity_epoch != compiled_validity_epoch:
        disposition = RouteUseDisposition.REBIND_CURRENTNESS; reasons.append("CURRENTNESS_CHANGED")

    pairs = (("HYDRATION_BYTES", observation.hydration_bytes, limits.max_hydration_bytes),
             ("ROUTE_STEPS", observation.route_steps, limits.max_route_steps),
             ("LAWFIELD_TRANSITIONS", observation.lawfield_transitions, limits.max_lawfield_transitions),
             ("SOURCE_REOPENS", observation.source_reopens, limits.max_source_reopens))
    for name, value, limit in pairs:
        if type(value) is not int or value < 0 or value > limit:
            reasons.append("OVER_" + name)
    if any(x.startswith("OVER_") for x in reasons):
        disposition = RouteUseDisposition.HOLD_BUDGET
    return disposition, tuple(sorted(set(reasons)))
