"""AURA-ADOPT-001 ZF-03A: portable, zero-authority Arena Recipe kernel.

D0/reference implementation. An ArenaRecipeV1 is reusable composition knowledge,
not executable code, a planner, registry, rights owner, or effect authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


SCHEMA = "ArenaRecipeV1"
PLAN_SCHEMA = "ArenaRecipePlanV1"

IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,191}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
RIGHTS_STATES = frozenset({"UNKNOWN", "ALLOWED", "RESTRICTED", "DENIED"})
CURRENTNESS_STATES = frozenset({"CURRENT", "STALE", "UNKNOWN"})
EFFECT_CEILINGS = (
    "NONE",
    "LOCAL_DERIVATION_ONLY",
    "LOCAL_FILE_WRITE_PROPOSAL",
    "EXTERNAL_EFFECT_PROPOSAL",
)
FORBIDDEN_KEYS = frozenset({
    "api_key", "apikey", "credential", "credentials", "secret", "token",
    "access_token", "refresh_token", "password", "private_key",
    "shell", "shell_command", "command", "exec", "executable", "script",
    "javascript", "provider_url", "provider_endpoint", "endpoint",
    "download_url", "install_command",
})


class RecipeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_ident(name: str, value: Any) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise RecipeError("INVALID_IDENTIFIER", name)
    return value


def _require_sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise RecipeError("INVALID_SHA256", name)
    return value


def _scan_safe_data(value: Any, path: str = "$") -> None:
    """Reject authority-bearing / executable fields recursively."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise RecipeError("NONSTRING_KEY_FORBIDDEN", path)
            folded = key.casefold()
            if folded in FORBIDDEN_KEYS:
                raise RecipeError("FORBIDDEN_RECIPE_FIELD", f"{path}.{key}")
            _scan_safe_data(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            _scan_safe_data(child, f"{path}[{i}]")
    elif value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise RecipeError("NONFINITE_NUMBER_FORBIDDEN", path)
    else:
        raise RecipeError("UNSUPPORTED_RECIPE_VALUE", path)


@dataclass(frozen=True)
class BoundRef:
    ref: str
    digest: str
    source_generation: str
    currentness: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_ident("ref", self.ref)
        _require_sha("digest", self.digest)
        _require_ident("source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS_STATES:
            raise RecipeError("INVALID_CURRENTNESS", self.currentness)


@dataclass(frozen=True)
class Attribution:
    contributor_ref: str
    role: str
    contribution_ref: str | None = None

    def __post_init__(self) -> None:
        _require_ident("contributor_ref", self.contributor_ref)
        _require_ident("role", self.role)
        if self.contribution_ref is not None:
            _require_ident("contribution_ref", self.contribution_ref)


@dataclass(frozen=True)
class RightsEnvelope:
    use: str = "UNKNOWN"
    modify: str = "UNKNOWN"
    redistribute: str = "UNKNOWN"
    commercial: str = "UNKNOWN"
    attribution_required: bool = True
    license_ref: str | None = None

    def __post_init__(self) -> None:
        for name in ("use", "modify", "redistribute", "commercial"):
            value = getattr(self, name)
            if value not in RIGHTS_STATES:
                raise RecipeError("INVALID_RIGHTS_STATE", f"{name}:{value}")
        if self.license_ref is not None:
            _require_ident("license_ref", self.license_ref)


def _effect_rank(value: str) -> int:
    try:
        return EFFECT_CEILINGS.index(value)
    except ValueError as exc:
        raise RecipeError("INVALID_EFFECT_CEILING", value) from exc


@dataclass(frozen=True)
class ArenaRecipe:
    recipe_id: str
    version: str
    purpose: str
    publisher_ref: str
    source: BoundRef
    capabilities: tuple[BoundRef, ...]
    assets: tuple[BoundRef, ...]
    parameters: Mapping[str, Any]
    constraints: Mapping[str, Any]
    attribution: tuple[Attribution, ...]
    rights: RightsEnvelope
    effect_ceiling: str = "NONE"
    parent_recipe_digests: tuple[str, ...] = ()
    compatibility: Mapping[str, Any] | None = None
    reopen_conditions: tuple[str, ...] = ()
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise RecipeError("SCHEMA_MISMATCH")
        _require_ident("recipe_id", self.recipe_id)
        _require_ident("version", self.version)
        _require_ident("publisher_ref", self.publisher_ref)
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise RecipeError("PURPOSE_REQUIRED")
        if not self.capabilities:
            raise RecipeError("CAPABILITY_REQUIRED")
        refs = [r.ref for r in (*self.capabilities, *self.assets)]
        if len(refs) != len(set(refs)):
            raise RecipeError("DUPLICATE_BOUND_REF")
        for digest in self.parent_recipe_digests:
            _require_sha("parent_recipe_digest", digest)
        _effect_rank(self.effect_ceiling)
        object.__setattr__(self, "compatibility", dict(self.compatibility or {}))
        _scan_safe_data(self.parameters, "$.parameters")
        _scan_safe_data(self.constraints, "$.constraints")
        _scan_safe_data(self.compatibility, "$.compatibility")
        for condition in self.reopen_conditions:
            if not isinstance(condition, str) or not condition.strip():
                raise RecipeError("INVALID_REOPEN_CONDITION")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "recipe_id": self.recipe_id,
            "version": self.version,
            "purpose": self.purpose.strip(),
            "publisher_ref": self.publisher_ref,
            "source": asdict(self.source),
            "capabilities": [asdict(x) for x in sorted(self.capabilities, key=lambda x: x.ref)],
            "assets": [asdict(x) for x in sorted(self.assets, key=lambda x: x.ref)],
            "parameters": self.parameters,
            "constraints": self.constraints,
            "attribution": [
                asdict(x)
                for x in sorted(
                    self.attribution,
                    key=lambda x: (x.contributor_ref, x.role, x.contribution_ref or ""),
                )
            ],
            "rights": asdict(self.rights),
            "effect_ceiling": self.effect_ceiling,
            "parent_recipe_digests": sorted(set(self.parent_recipe_digests)),
            "compatibility": self.compatibility,
            "reopen_conditions": sorted(set(self.reopen_conditions)),
        }

    @property
    def digest(self) -> str:
        return _digest(self.canonical_payload())

    def export_json(self) -> str:
        return _canonical(self.canonical_payload()).decode("utf-8")


def _bound_ref(raw: Mapping[str, Any]) -> BoundRef:
    return BoundRef(
        ref=raw.get("ref"),
        digest=raw.get("digest"),
        source_generation=raw.get("source_generation"),
        currentness=raw.get("currentness", "UNKNOWN"),
    )


def _attribution(raw: Mapping[str, Any]) -> Attribution:
    return Attribution(
        contributor_ref=raw.get("contributor_ref"),
        role=raw.get("role"),
        contribution_ref=raw.get("contribution_ref"),
    )


def _rights(raw: Mapping[str, Any]) -> RightsEnvelope:
    return RightsEnvelope(
        use=raw.get("use", "UNKNOWN"),
        modify=raw.get("modify", "UNKNOWN"),
        redistribute=raw.get("redistribute", "UNKNOWN"),
        commercial=raw.get("commercial", "UNKNOWN"),
        attribution_required=raw.get("attribution_required", True),
        license_ref=raw.get("license_ref"),
    )


def import_recipe_json(text: str) -> ArenaRecipe:
    try:
        raw = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RecipeError("RECIPE_JSON_INVALID") from exc
    if not isinstance(raw, Mapping):
        raise RecipeError("RECIPE_OBJECT_REQUIRED")
    if raw.get("schema") != SCHEMA:
        raise RecipeError("SCHEMA_MISMATCH")
    allowed = {
        "schema", "recipe_id", "version", "purpose", "publisher_ref", "source",
        "capabilities", "assets", "parameters", "constraints", "attribution",
        "rights", "effect_ceiling", "parent_recipe_digests", "compatibility",
        "reopen_conditions",
    }
    extra = sorted(set(raw) - allowed)
    if extra:
        raise RecipeError("UNKNOWN_TOP_LEVEL_FIELDS", ",".join(extra))
    for seq_name in ("capabilities", "assets", "attribution", "parent_recipe_digests", "reopen_conditions"):
        value = raw.get(seq_name, [])
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise RecipeError("INVALID_SEQUENCE", seq_name)
    for map_name in ("source", "parameters", "constraints", "rights", "compatibility"):
        if not isinstance(raw.get(map_name, {}), Mapping):
            raise RecipeError("INVALID_MAPPING", map_name)
    return ArenaRecipe(
        recipe_id=raw.get("recipe_id"),
        version=raw.get("version"),
        purpose=raw.get("purpose"),
        publisher_ref=raw.get("publisher_ref"),
        source=_bound_ref(raw["source"]),
        capabilities=tuple(_bound_ref(x) for x in raw.get("capabilities", [])),
        assets=tuple(_bound_ref(x) for x in raw.get("assets", [])),
        parameters=dict(raw.get("parameters", {})),
        constraints=dict(raw.get("constraints", {})),
        attribution=tuple(_attribution(x) for x in raw.get("attribution", [])),
        rights=_rights(raw.get("rights", {})),
        effect_ceiling=raw.get("effect_ceiling", "NONE"),
        parent_recipe_digests=tuple(raw.get("parent_recipe_digests", [])),
        compatibility=dict(raw.get("compatibility", {})),
        reopen_conditions=tuple(raw.get("reopen_conditions", [])),
    )


_RIGHT_ORDER = {"DENIED": 0, "UNKNOWN": 1, "RESTRICTED": 2, "ALLOWED": 3}


def _assert_rights_not_widened(parent: RightsEnvelope, child: RightsEnvelope) -> None:
    for name in ("use", "modify", "redistribute", "commercial"):
        before = getattr(parent, name)
        after = getattr(child, name)
        if _RIGHT_ORDER[after] > _RIGHT_ORDER[before]:
            raise RecipeError("RIGHTS_WIDENING_FORBIDDEN", f"{name}:{before}->{after}")
    if parent.attribution_required and not child.attribution_required:
        raise RecipeError("ATTRIBUTION_REMOVAL_FORBIDDEN")


def remix_recipe(
    parent: ArenaRecipe,
    *,
    recipe_id: str,
    version: str,
    publisher_ref: str,
    parameter_patch: Mapping[str, Any] | None = None,
    constraint_patch: Mapping[str, Any] | None = None,
    rights: RightsEnvelope | None = None,
    effect_ceiling: str | None = None,
    attribution_add: Sequence[Attribution] = (),
) -> ArenaRecipe:
    parameter_patch = dict(parameter_patch or {})
    constraint_patch = dict(constraint_patch or {})
    _scan_safe_data(parameter_patch, "$.parameter_patch")
    _scan_safe_data(constraint_patch, "$.constraint_patch")
    child_rights = rights or parent.rights
    _assert_rights_not_widened(parent.rights, child_rights)
    child_ceiling = effect_ceiling or parent.effect_ceiling
    if _effect_rank(child_ceiling) > _effect_rank(parent.effect_ceiling):
        raise RecipeError("EFFECT_CEILING_WIDENING_FORBIDDEN")
    params = dict(parent.parameters)
    params.update(parameter_patch)
    constraints = dict(parent.constraints)
    constraints.update(constraint_patch)
    attribution = tuple(parent.attribution) + tuple(attribution_add)
    child = ArenaRecipe(
        recipe_id=recipe_id,
        version=version,
        purpose=parent.purpose,
        publisher_ref=publisher_ref,
        source=parent.source,
        capabilities=parent.capabilities,
        assets=parent.assets,
        parameters=params,
        constraints=constraints,
        attribution=attribution,
        rights=child_rights,
        effect_ceiling=child_ceiling,
        parent_recipe_digests=tuple(sorted(set((*parent.parent_recipe_digests, parent.digest)))),
        compatibility=parent.compatibility,
        reopen_conditions=parent.reopen_conditions,
    )
    if child.digest == parent.digest:
        raise RecipeError("REDUNDANT_REMIX")
    return child


def compile_recipe_plan(
    recipe: ArenaRecipe,
    *,
    current_bindings: Mapping[str, str],
) -> dict[str, Any]:
    """Validate exact bindings and emit a zero-authority composition plan."""
    if not isinstance(current_bindings, Mapping):
        raise RecipeError("CURRENT_BINDINGS_REQUIRED")
    blockers: list[str] = []
    for bound in (recipe.source, *recipe.capabilities, *recipe.assets):
        observed = current_bindings.get(bound.ref)
        if observed is None:
            blockers.append(f"MISSING_BINDING:{bound.ref}")
            continue
        if observed != bound.digest:
            blockers.append(f"STALE_OR_MISMATCHED_BINDING:{bound.ref}")
        if bound.currentness == "STALE":
            blockers.append(f"BOUND_REF_STALE:{bound.ref}")
        elif bound.currentness == "UNKNOWN":
            blockers.append(f"BOUND_REF_CURRENTNESS_UNKNOWN:{bound.ref}")
    status = "READY_FOR_ADMISSION" if not blockers else "BINDING_EVIDENCE_REQUIRED"
    payload = {
        "schema": PLAN_SCHEMA,
        "recipe_digest": recipe.digest,
        "recipe_id": recipe.recipe_id,
        "recipe_version": recipe.version,
        "purpose": recipe.purpose,
        "capability_refs": [x.ref for x in sorted(recipe.capabilities, key=lambda x: x.ref)],
        "asset_refs": [x.ref for x in sorted(recipe.assets, key=lambda x: x.ref)],
        "parameters": recipe.parameters,
        "constraints": recipe.constraints,
        "effect_ceiling": recipe.effect_ceiling,
        "rights": asdict(recipe.rights),
        "blockers": blockers,
        "status": status,
        "authority_owner_resolved": False,
        "effect_authorized": False,
        "execution_proven": False,
        "publication_authorized": False,
        "payment_authorized": False,
        "marketplace_listed": False,
    }
    payload["plan_digest"] = _digest(payload)
    return payload
