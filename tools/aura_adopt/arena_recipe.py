"""AURA-ADOPT-001 ZF-03A: portable, zero-authority Arena Recipe kernel.

D0/reference implementation. ArenaRecipeV1 is reusable composition knowledge,
not executable code, a planner, registry, rights owner, or effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib, json, re
from typing import Any, Mapping, Sequence

SCHEMA = "ArenaRecipeV1"
PLAN_SCHEMA = "ArenaRecipePlanV1"
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,191}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
RIGHTS_STATES = frozenset({"UNKNOWN", "ALLOWED", "RESTRICTED", "DENIED"})
CURRENTNESS_STATES = frozenset({"CURRENT", "STALE", "UNKNOWN"})
EFFECT_CEILINGS = ("NONE", "LOCAL_DERIVATION_ONLY", "LOCAL_FILE_WRITE_PROPOSAL", "EXTERNAL_EFFECT_PROPOSAL")
FORBIDDEN_KEYS = frozenset({
    "api_key", "apikey", "credential", "credentials", "secret", "token",
    "access_token", "refresh_token", "password", "private_key", "shell",
    "shell_command", "command", "exec", "executable", "script", "javascript",
    "provider_url", "provider_endpoint", "endpoint", "download_url", "install_command",
})

class RecipeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail

def _canonical(v: Any) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def _digest(v: Any) -> str:
    return hashlib.sha256(_canonical(v)).hexdigest()

def _ident(name: str, v: Any) -> str:
    if not isinstance(v, str) or not IDENT.fullmatch(v): raise RecipeError("INVALID_IDENTIFIER", name)
    return v

def _sha(name: str, v: Any) -> str:
    if not isinstance(v, str) or not SHA256.fullmatch(v): raise RecipeError("INVALID_SHA256", name)
    return v

def _safe(v: Any, path: str = "$") -> None:
    if isinstance(v, Mapping):
        for k, x in v.items():
            if not isinstance(k, str): raise RecipeError("NONSTRING_KEY_FORBIDDEN", path)
            if k.casefold() in FORBIDDEN_KEYS: raise RecipeError("FORBIDDEN_RECIPE_FIELD", f"{path}.{k}")
            _safe(x, f"{path}.{k}")
    elif isinstance(v, (list, tuple)):
        for i, x in enumerate(v): _safe(x, f"{path}[{i}]")
    elif v is None or isinstance(v, (str, int, float, bool)):
        if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))): raise RecipeError("NONFINITE_NUMBER_FORBIDDEN", path)
    else: raise RecipeError("UNSUPPORTED_RECIPE_VALUE", path)

@dataclass(frozen=True)
class BoundRef:
    ref: str; digest: str; source_generation: str; currentness: str = "UNKNOWN"
    def __post_init__(self) -> None:
        _ident("ref", self.ref); _sha("digest", self.digest); _ident("source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS_STATES: raise RecipeError("INVALID_CURRENTNESS", self.currentness)

@dataclass(frozen=True)
class BindingEvidence:
    digest: str; source_generation: str; currentness: str
    def __post_init__(self) -> None:
        _sha("binding.digest", self.digest); _ident("binding.source_generation", self.source_generation)
        if self.currentness not in CURRENTNESS_STATES: raise RecipeError("INVALID_CURRENTNESS", self.currentness)

@dataclass(frozen=True)
class Attribution:
    contributor_ref: str; role: str; contribution_ref: str | None = None
    def __post_init__(self) -> None:
        _ident("contributor_ref", self.contributor_ref); _ident("role", self.role)
        if self.contribution_ref is not None: _ident("contribution_ref", self.contribution_ref)

@dataclass(frozen=True)
class RightsEnvelope:
    use: str = "UNKNOWN"; modify: str = "UNKNOWN"; redistribute: str = "UNKNOWN"; commercial: str = "UNKNOWN"
    attribution_required: bool = True; license_ref: str | None = None
    def __post_init__(self) -> None:
        for n in ("use", "modify", "redistribute", "commercial"):
            if getattr(self, n) not in RIGHTS_STATES: raise RecipeError("INVALID_RIGHTS_STATE", f"{n}:{getattr(self,n)}")
        if self.license_ref is not None: _ident("license_ref", self.license_ref)

def _effect_rank(v: str) -> int:
    try: return EFFECT_CEILINGS.index(v)
    except ValueError as e: raise RecipeError("INVALID_EFFECT_CEILING", v) from e

@dataclass(frozen=True)
class ArenaRecipe:
    recipe_id: str; version: str; purpose: str; publisher_ref: str; source: BoundRef
    capabilities: tuple[BoundRef, ...]; assets: tuple[BoundRef, ...]; parameters: Mapping[str, Any]
    constraints: Mapping[str, Any]; attribution: tuple[Attribution, ...]; rights: RightsEnvelope
    effect_ceiling: str = "NONE"; parent_recipe_digests: tuple[str, ...] = ()
    compatibility: Mapping[str, Any] | None = None; reopen_conditions: tuple[str, ...] = (); schema: str = SCHEMA
    def __post_init__(self) -> None:
        if self.schema != SCHEMA: raise RecipeError("SCHEMA_MISMATCH")
        _ident("recipe_id", self.recipe_id); _ident("version", self.version); _ident("publisher_ref", self.publisher_ref)
        if not isinstance(self.purpose, str) or not self.purpose.strip(): raise RecipeError("PURPOSE_REQUIRED")
        if not self.capabilities: raise RecipeError("CAPABILITY_REQUIRED")
        refs = [x.ref for x in (*self.capabilities, *self.assets)]
        if len(refs) != len(set(refs)): raise RecipeError("DUPLICATE_BOUND_REF")
        for d in self.parent_recipe_digests: _sha("parent_recipe_digest", d)
        _effect_rank(self.effect_ceiling)
        object.__setattr__(self, "compatibility", dict(self.compatibility or {}))
        _safe(self.parameters, "$.parameters"); _safe(self.constraints, "$.constraints"); _safe(self.compatibility, "$.compatibility")
        if any(not isinstance(x, str) or not x.strip() for x in self.reopen_conditions): raise RecipeError("INVALID_REOPEN_CONDITION")
    def canonical_payload(self) -> dict[str, Any]:
        return {"schema": self.schema, "recipe_id": self.recipe_id, "version": self.version, "purpose": self.purpose.strip(),
                "publisher_ref": self.publisher_ref, "source": asdict(self.source),
                "capabilities": [asdict(x) for x in sorted(self.capabilities, key=lambda x:x.ref)],
                "assets": [asdict(x) for x in sorted(self.assets, key=lambda x:x.ref)],
                "parameters": self.parameters, "constraints": self.constraints,
                "attribution": [asdict(x) for x in sorted(self.attribution, key=lambda x:(x.contributor_ref,x.role,x.contribution_ref or ""))],
                "rights": asdict(self.rights), "effect_ceiling": self.effect_ceiling,
                "parent_recipe_digests": sorted(set(self.parent_recipe_digests)), "compatibility": self.compatibility,
                "reopen_conditions": sorted(set(self.reopen_conditions))}
    @property
    def digest(self) -> str: return _digest(self.canonical_payload())
    def export_json(self) -> str: return _canonical(self.canonical_payload()).decode()

def _b(raw: Mapping[str, Any]) -> BoundRef:
    return BoundRef(raw.get("ref"), raw.get("digest"), raw.get("source_generation"), raw.get("currentness", "UNKNOWN"))
def _a(raw: Mapping[str, Any]) -> Attribution:
    return Attribution(raw.get("contributor_ref"), raw.get("role"), raw.get("contribution_ref"))
def _r(raw: Mapping[str, Any]) -> RightsEnvelope:
    return RightsEnvelope(raw.get("use","UNKNOWN"), raw.get("modify","UNKNOWN"), raw.get("redistribute","UNKNOWN"), raw.get("commercial","UNKNOWN"), raw.get("attribution_required",True), raw.get("license_ref"))

def import_recipe_json(text: str) -> ArenaRecipe:
    try: raw = json.loads(text)
    except (TypeError, json.JSONDecodeError) as e: raise RecipeError("RECIPE_JSON_INVALID") from e
    if not isinstance(raw, Mapping): raise RecipeError("RECIPE_OBJECT_REQUIRED")
    if raw.get("schema") != SCHEMA: raise RecipeError("SCHEMA_MISMATCH")
    allowed = {"schema","recipe_id","version","purpose","publisher_ref","source","capabilities","assets","parameters","constraints","attribution","rights","effect_ceiling","parent_recipe_digests","compatibility","reopen_conditions"}
    extra = sorted(set(raw)-allowed)
    if extra: raise RecipeError("UNKNOWN_TOP_LEVEL_FIELDS", ",".join(extra))
    for n in ("capabilities","assets","attribution","parent_recipe_digests","reopen_conditions"):
        v=raw.get(n,[])
        if not isinstance(v, Sequence) or isinstance(v,(str,bytes)): raise RecipeError("INVALID_SEQUENCE", n)
    for n in ("source","parameters","constraints","rights","compatibility"):
        if not isinstance(raw.get(n,{}), Mapping): raise RecipeError("INVALID_MAPPING", n)
    return ArenaRecipe(raw.get("recipe_id"), raw.get("version"), raw.get("purpose"), raw.get("publisher_ref"), _b(raw["source"]),
        tuple(_b(x) for x in raw.get("capabilities",[])), tuple(_b(x) for x in raw.get("assets",[])), dict(raw.get("parameters",{})),
        dict(raw.get("constraints",{})), tuple(_a(x) for x in raw.get("attribution",[])), _r(raw.get("rights",{})), raw.get("effect_ceiling","NONE"),
        tuple(raw.get("parent_recipe_digests",[])), dict(raw.get("compatibility",{})), tuple(raw.get("reopen_conditions",[])))

_RIGHT_ORDER={"DENIED":0,"UNKNOWN":1,"RESTRICTED":2,"ALLOWED":3}
def _no_rights_widen(parent: RightsEnvelope, child: RightsEnvelope) -> None:
    for n in ("use","modify","redistribute","commercial"):
        if _RIGHT_ORDER[getattr(child,n)] > _RIGHT_ORDER[getattr(parent,n)]: raise RecipeError("RIGHTS_WIDENING_FORBIDDEN", f"{n}:{getattr(parent,n)}->{getattr(child,n)}")
    if parent.attribution_required and not child.attribution_required: raise RecipeError("ATTRIBUTION_REMOVAL_FORBIDDEN")

def remix_recipe(parent: ArenaRecipe, *, recipe_id: str, version: str, publisher_ref: str, parameter_patch: Mapping[str,Any]|None=None,
                 constraint_patch: Mapping[str,Any]|None=None, rights: RightsEnvelope|None=None, effect_ceiling: str|None=None,
                 attribution_add: Sequence[Attribution]=()) -> ArenaRecipe:
    pp, cp = dict(parameter_patch or {}), dict(constraint_patch or {}); _safe(pp,"$.parameter_patch"); _safe(cp,"$.constraint_patch")
    cr = rights or parent.rights; _no_rights_widen(parent.rights, cr); ceiling = effect_ceiling or parent.effect_ceiling
    if _effect_rank(ceiling) > _effect_rank(parent.effect_ceiling): raise RecipeError("EFFECT_CEILING_WIDENING_FORBIDDEN")
    params, constraints = dict(parent.parameters), dict(parent.constraints); params.update(pp); constraints.update(cp)
    child = ArenaRecipe(recipe_id, version, parent.purpose, publisher_ref, parent.source, parent.capabilities, parent.assets, params, constraints,
        tuple(parent.attribution)+tuple(attribution_add), cr, ceiling, tuple(sorted(set((*parent.parent_recipe_digests,parent.digest)))), parent.compatibility, parent.reopen_conditions)
    if child.digest == parent.digest: raise RecipeError("REDUNDANT_REMIX")
    return child

def compile_recipe_plan(recipe: ArenaRecipe, *, current_bindings: Mapping[str, BindingEvidence]) -> dict[str, Any]:
    if not isinstance(current_bindings, Mapping): raise RecipeError("CURRENT_BINDINGS_REQUIRED")
    blockers=[]
    for bound in (recipe.source,*recipe.capabilities,*recipe.assets):
        obs=current_bindings.get(bound.ref)
        if obs is None: blockers.append(f"MISSING_BINDING:{bound.ref}"); continue
        if not isinstance(obs, BindingEvidence): blockers.append(f"BINDING_EVIDENCE_INVALID:{bound.ref}"); continue
        if obs.digest != bound.digest: blockers.append(f"BINDING_DIGEST_MISMATCH:{bound.ref}")
        if obs.source_generation != bound.source_generation: blockers.append(f"BINDING_GENERATION_MISMATCH:{bound.ref}")
        if obs.currentness != "CURRENT": blockers.append(f"BINDING_NOT_CURRENT:{bound.ref}:{obs.currentness}")
        if bound.currentness != "CURRENT": blockers.append(f"RECIPE_BOUND_REF_NOT_CURRENT:{bound.ref}:{bound.currentness}")
    payload={"schema":PLAN_SCHEMA,"recipe_digest":recipe.digest,"recipe_id":recipe.recipe_id,"recipe_version":recipe.version,"purpose":recipe.purpose,
        "capability_refs":[x.ref for x in sorted(recipe.capabilities,key=lambda x:x.ref)],"asset_refs":[x.ref for x in sorted(recipe.assets,key=lambda x:x.ref)],
        "parameters":recipe.parameters,"constraints":recipe.constraints,"effect_ceiling":recipe.effect_ceiling,"rights":asdict(recipe.rights),"blockers":blockers,
        "status":"READY_FOR_ADMISSION" if not blockers else "BINDING_EVIDENCE_REQUIRED","authority_owner_resolved":False,"effect_authorized":False,
        "execution_proven":False,"publication_authorized":False,"payment_authorized":False,"marketplace_listed":False}
    payload["plan_digest"]=_digest(payload); return payload
