"""AURA-ADOPT ZF-03A -> ZF-04 recipe/distribution identity membrane.

D0 coordination only. ArenaRecipeV1 is portable composition knowledge, not
executable authority. TrustedDistributionManifestV1 is a separate trust/currentness
admission surface. This module binds the two without becoming the recipe owner,
distribution verifier, installer, publisher, marketplace, or effect authority.

For an ARENA_RECIPE artifact the canonical ArenaRecipe JSON is the artifact bytes.
Because ArenaRecipe.digest is SHA-256(canonical export JSON), recipe identity and
distribution artifact identity collapse to one digest rather than inventing a
second package identity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

try:
    from .arena_recipe import ArenaRecipe
except ImportError:
    from arena_recipe import ArenaRecipe

BINDING_SCHEMA = "RecipeDistributionBindingV1"
ADMISSION_SCHEMA = "RecipeDistributionAdmissionV1"
RECIPE_PLAN_SCHEMA = "ArenaRecipePlanV1"
DISTRIBUTION_SCHEMA = "TrustedDistributionManifestV1"


class RecipeDistributionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _enum_value(value: Any) -> Any:
    raw = getattr(value, "value", None)
    return raw if raw is not None else value


def _normalize(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    value = _enum_value(value)
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            _normalize(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RecipeDistributionError("NONCANONICAL_RECIPE_DISTRIBUTION_STATE") from exc


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _sha(_canonical(value))


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RecipeDistributionError(code)
    return value.strip()


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    normalized = _normalize(value)
    if not isinstance(normalized, Mapping):
        raise RecipeDistributionError(code)
    return normalized


def manifest_id_from_view(manifest: Any) -> str:
    row = dict(_mapping(manifest, "DISTRIBUTION_MANIFEST_MAPPING_REQUIRED"))
    row["manifest_id"] = ""
    return "tdm1:" + _digest(row)


def recipe_plan_digest(plan: Mapping[str, Any]) -> str:
    row = dict(_mapping(plan, "RECIPE_PLAN_MAPPING_REQUIRED"))
    row.pop("plan_digest", None)
    return _digest(row)


@dataclass(frozen=True)
class RecipeDistributionBinding:
    recipe_id: str
    recipe_version: str
    recipe_digest: str
    canonical_recipe_size_bytes: int
    recipe_plan_digest: str
    manifest_id: str
    distribution_artifact_id: str
    distribution_artifact_version: str
    capability_refs: tuple[str, ...]
    redistribution_right: str
    attribution_required: bool
    attribution_digest: str
    effect_ceiling: str
    status: str = "READY_FOR_TRUSTED_DISTRIBUTION_ADMISSION"
    schema: str = BINDING_SCHEMA
    install_authorized: bool = False
    public_distribution_authorized: bool = False
    effect_authorized: bool = False
    execution_proven: bool = False
    payment_authorized: bool = False
    marketplace_listed: bool = False
    binding_digest: str = ""

    def __post_init__(self) -> None:
        if self.schema != BINDING_SCHEMA:
            raise RecipeDistributionError("BINDING_SCHEMA_MISMATCH")
        expected = self.compute_digest()
        supplied = str(self.binding_digest or "").strip()
        if supplied and supplied != expected:
            raise RecipeDistributionError("BINDING_DIGEST_MISMATCH")
        object.__setattr__(self, "binding_digest", expected)

    def logical_payload(self) -> dict[str, Any]:
        row = asdict(self)
        row.pop("binding_digest", None)
        return row

    def compute_digest(self) -> str:
        return _digest(self.logical_payload())


def compile_recipe_distribution_binding(
    *,
    recipe: ArenaRecipe,
    recipe_plan: Mapping[str, Any],
    distribution_manifest: Any,
) -> RecipeDistributionBinding:
    if not isinstance(recipe, ArenaRecipe):
        raise RecipeDistributionError("ARENA_RECIPE_REQUIRED")
    plan = _mapping(recipe_plan, "RECIPE_PLAN_MAPPING_REQUIRED")
    if plan.get("schema") != RECIPE_PLAN_SCHEMA:
        raise RecipeDistributionError("RECIPE_PLAN_SCHEMA_MISMATCH")
    if plan.get("recipe_digest") != recipe.digest:
        raise RecipeDistributionError("RECIPE_PLAN_RECIPE_DIGEST_MISMATCH")
    supplied_plan_digest = _text(plan.get("plan_digest"), "RECIPE_PLAN_DIGEST_REQUIRED")
    if supplied_plan_digest != recipe_plan_digest(plan):
        raise RecipeDistributionError("RECIPE_PLAN_DIGEST_MISMATCH")
    if plan.get("status") != "READY_FOR_ADMISSION" or plan.get("blockers") != []:
        raise RecipeDistributionError("RECIPE_PLAN_NOT_READY")
    for field in (
        "authority_owner_resolved",
        "effect_authorized",
        "execution_proven",
        "publication_authorized",
        "payment_authorized",
        "marketplace_listed",
    ):
        if plan.get(field) is not False:
            raise RecipeDistributionError("RECIPE_PLAN_AUTHORITY_WIDENING", field)

    canonical_recipe = recipe.export_json().encode("utf-8")
    canonical_digest = _sha(canonical_recipe)
    if canonical_digest != recipe.digest:
        raise RecipeDistributionError("RECIPE_EXPORT_IDENTITY_MISMATCH")

    manifest = _mapping(distribution_manifest, "DISTRIBUTION_MANIFEST_MAPPING_REQUIRED")
    if manifest.get("schema_version") != DISTRIBUTION_SCHEMA:
        raise RecipeDistributionError("DISTRIBUTION_SCHEMA_MISMATCH")
    supplied_manifest_id = _text(manifest.get("manifest_id"), "DISTRIBUTION_MANIFEST_ID_REQUIRED")
    if supplied_manifest_id != manifest_id_from_view(manifest):
        raise RecipeDistributionError("DISTRIBUTION_MANIFEST_ID_MISMATCH")
    artifact = _mapping(manifest.get("artifact"), "DISTRIBUTION_ARTIFACT_REQUIRED")
    if _enum_value(artifact.get("kind")) != "ARENA_RECIPE":
        raise RecipeDistributionError("DISTRIBUTION_ARTIFACT_KIND_NOT_RECIPE")
    if _enum_value(artifact.get("channel")) != "RECIPE":
        raise RecipeDistributionError("DISTRIBUTION_CHANNEL_NOT_RECIPE")
    if artifact.get("artifact_id") != recipe.recipe_id:
        raise RecipeDistributionError("RECIPE_ARTIFACT_ID_MISMATCH")
    if artifact.get("version") != recipe.version:
        raise RecipeDistributionError("RECIPE_ARTIFACT_VERSION_MISMATCH")
    if artifact.get("sha256_hex") != recipe.digest:
        raise RecipeDistributionError("RECIPE_ARTIFACT_DIGEST_MISMATCH")
    if artifact.get("size_bytes") != len(canonical_recipe):
        raise RecipeDistributionError("RECIPE_ARTIFACT_SIZE_MISMATCH")

    plan_capabilities = tuple(sorted(_text(v, "RECIPE_CAPABILITY_REF_INVALID") for v in plan.get("capability_refs", ())))
    manifest_capabilities = tuple(sorted(_text(v, "DISTRIBUTION_CAPABILITY_ID_INVALID") for v in artifact.get("capability_ids", ())))
    if manifest_capabilities != plan_capabilities:
        raise RecipeDistributionError("RECIPE_DISTRIBUTION_CAPABILITY_MISMATCH")

    # ArenaRecipeV1 is knowledge/data. Distribution of the recipe itself must not
    # smuggle installer/device permissions into a zero-authority recipe package.
    if tuple(artifact.get("required_permissions", ())) != ():
        raise RecipeDistributionError("RECIPE_REQUIRED_PERMISSION_FORBIDDEN")
    if tuple(artifact.get("optional_permissions", ())) != ():
        raise RecipeDistributionError("RECIPE_OPTIONAL_PERMISSION_FORBIDDEN")

    rights = _mapping(plan.get("rights"), "RECIPE_RIGHTS_REQUIRED")
    redistribution = _text(rights.get("redistribute"), "RECIPE_REDISTRIBUTION_RIGHT_REQUIRED")
    if redistribution != "ALLOWED":
        raise RecipeDistributionError("RECIPE_REDISTRIBUTION_NOT_ALLOWED", redistribution)
    attribution_required = rights.get("attribution_required")
    if type(attribution_required) is not bool:
        raise RecipeDistributionError("RECIPE_ATTRIBUTION_REQUIREMENT_INVALID")
    attribution_payload = recipe.canonical_payload().get("attribution", [])
    if attribution_required and not attribution_payload:
        raise RecipeDistributionError("REQUIRED_ATTRIBUTION_MISSING")

    return RecipeDistributionBinding(
        recipe_id=recipe.recipe_id,
        recipe_version=recipe.version,
        recipe_digest=recipe.digest,
        canonical_recipe_size_bytes=len(canonical_recipe),
        recipe_plan_digest=supplied_plan_digest,
        manifest_id=supplied_manifest_id,
        distribution_artifact_id=_text(artifact.get("artifact_id"), "DISTRIBUTION_ARTIFACT_ID_REQUIRED"),
        distribution_artifact_version=_text(artifact.get("version"), "DISTRIBUTION_ARTIFACT_VERSION_REQUIRED"),
        capability_refs=plan_capabilities,
        redistribution_right=redistribution,
        attribution_required=attribution_required,
        attribution_digest=_digest(attribution_payload),
        effect_ceiling=_text(plan.get("effect_ceiling"), "RECIPE_EFFECT_CEILING_REQUIRED"),
    )


def verify_trusted_recipe_distribution(
    *,
    binding: RecipeDistributionBinding,
    trusted_distribution_receipt_resolver: Callable[[str], Any] | None,
) -> dict[str, Any]:
    if not isinstance(binding, RecipeDistributionBinding):
        raise RecipeDistributionError("RECIPE_DISTRIBUTION_BINDING_REQUIRED")
    if not callable(trusted_distribution_receipt_resolver):
        raise RecipeDistributionError("TRUSTED_DISTRIBUTION_RECEIPT_RESOLVER_REQUIRED")
    receipt = _mapping(
        trusted_distribution_receipt_resolver(binding.manifest_id),
        "DISTRIBUTION_ADMISSION_RECEIPT_REQUIRED",
    )
    if receipt.get("manifest_id") != binding.manifest_id:
        raise RecipeDistributionError("DISTRIBUTION_ADMISSION_MANIFEST_MISMATCH")
    if receipt.get("artifact_id") != binding.distribution_artifact_id:
        raise RecipeDistributionError("DISTRIBUTION_ADMISSION_ARTIFACT_MISMATCH")
    if receipt.get("version") != binding.distribution_artifact_version:
        raise RecipeDistributionError("DISTRIBUTION_ADMISSION_VERSION_MISMATCH")
    if _enum_value(receipt.get("status")) != "ADMISSIBLE":
        raise RecipeDistributionError("DISTRIBUTION_NOT_ADMISSIBLE", str(_enum_value(receipt.get("status"))))
    if tuple(receipt.get("reasons", ())) != ():
        raise RecipeDistributionError("DISTRIBUTION_ADMISSION_HAS_REASONS")
    if tuple(receipt.get("added_required_permissions", ())) != ():
        raise RecipeDistributionError("DISTRIBUTION_ADMISSION_PERMISSION_DELTA")
    for field in (
        "install_authorized",
        "update_authorized",
        "public_distribution_authorized",
        "effect_authorized",
        "execution_proven",
    ):
        if receipt.get(field) is not False:
            raise RecipeDistributionError("DISTRIBUTION_ADMISSION_AUTHORITY_WIDENING", field)

    body = {
        "schema": ADMISSION_SCHEMA,
        "decision": "RECIPE_PACKAGE_ADMISSIBLE_FOR_SEPARATE_DISTRIBUTION_EFFECT_GATE",
        "binding_digest": binding.binding_digest,
        "recipe_digest": binding.recipe_digest,
        "manifest_id": binding.manifest_id,
        "distribution_receipt_digest": _digest(receipt),
        "effect_ceiling": binding.effect_ceiling,
        "redistribution_right": binding.redistribution_right,
        "install_authorized": False,
        "update_authorized": False,
        "public_distribution_authorized": False,
        "effect_authorized": False,
        "execution_proven": False,
        "payment_authorized": False,
        "marketplace_listed": False,
    }
    body["admission_id"] = "rda-" + _digest(body)[:32]
    return body
