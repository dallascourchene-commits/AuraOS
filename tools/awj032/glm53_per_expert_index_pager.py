"""AWJ032 GLM-5.3 per-expert physical-checkpoint paging bridge.

D0 metadata/synthetic implementation only. The official checkpoint index is the
source of truth: this module never guesses that a checkpoint is per-expert. The
standard GLM key resolver succeeds only when the supplied weight map contains a
complete set of per-expert gate/up/down keys (and FP8 scale companions when
required). Selected experts are then requested by exact tensor key; physical I/O
remains UNKNOWN unless the backend supplies binding-matched evidence. G2 is never
admitted by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Protocol, Sequence


WEIGHT_ROLES = ("gate", "up", "down")
SCALE_ROLES = ("gate_scale", "up_scale", "down_scale")
_PROJECTION_BY_ROLE = {"gate": "gate_proj", "up": "up_proj", "down": "down_proj"}
BACKEND_IO_ATTESTATION_SCHEMA = "AuraExpertPagerBackendIOAttestationV1"


class PerExpertPagerError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class PerExpertSourceError(PerExpertPagerError):
    pass


class PerExpertRangeError(PerExpertPagerError):
    pass


class PerExpertReadError(PerExpertPagerError):
    pass


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PerExpertSourceError(code)
    return value.strip()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def canonical_expert_ids(expert_ids: Sequence[int], num_experts: int) -> tuple[int, ...]:
    if not expert_ids:
        raise PerExpertRangeError("EXPERT_SELECTION_EMPTY")
    selected: set[int] = set()
    for expert_id in expert_ids:
        if isinstance(expert_id, bool) or not isinstance(expert_id, int):
            raise PerExpertRangeError("EXPERT_ID_INVALID", repr(expert_id))
        if expert_id < 0 or expert_id >= num_experts:
            raise PerExpertRangeError("EXPERT_ID_OUT_OF_RANGE", str(expert_id))
        selected.add(expert_id)
    return tuple(sorted(selected))


@dataclass(frozen=True)
class ExpertPhysicalKeys:
    expert_id: int
    weight_keys: Mapping[str, str]
    scale_keys: Mapping[str, str]
    shard_by_key: Mapping[str, str]

    def __post_init__(self) -> None:
        if isinstance(self.expert_id, bool) or not isinstance(self.expert_id, int) or self.expert_id < 0:
            raise PerExpertSourceError("EXPERT_ID_INVALID")
        if set(self.weight_keys) != set(WEIGHT_ROLES):
            raise PerExpertSourceError("EXPERT_WEIGHT_ROLE_SET_INVALID", str(self.expert_id))
        if self.scale_keys and set(self.scale_keys) != set(SCALE_ROLES):
            raise PerExpertSourceError("EXPERT_SCALE_ROLE_SET_INVALID", str(self.expert_id))
        keys = list(self.weight_keys.values()) + list(self.scale_keys.values())
        if not keys or any(not isinstance(key, str) or not key for key in keys):
            raise PerExpertSourceError("EXPERT_TENSOR_KEY_INVALID", str(self.expert_id))
        if len(set(keys)) != len(keys):
            raise PerExpertSourceError("EXPERT_TENSOR_KEY_AMBIGUOUS", str(self.expert_id))
        for key in keys:
            shard = self.shard_by_key.get(key)
            if not isinstance(shard, str) or not shard:
                raise PerExpertSourceError("EXPERT_SHARD_BINDING_MISSING", key)

    def logical(self) -> dict[str, Any]:
        return {
            "expert_id": self.expert_id,
            "weight_keys": dict(sorted(self.weight_keys.items())),
            "scale_keys": dict(sorted(self.scale_keys.items())),
            "shard_by_key": {key: self.shard_by_key[key] for key in sorted(self.shard_by_key)},
        }


@dataclass(frozen=True)
class PerExpertIndexBinding:
    model_revision: str
    index_digest: str
    layer_id: str
    num_experts: int
    experts: Mapping[int, ExpertPhysicalKeys]
    require_fp8_scales: bool = True
    representation: str = "PER_EXPERT_PHYSICAL_LAYOUT"

    def __post_init__(self) -> None:
        _text(self.model_revision, "MODEL_REVISION_REQUIRED")
        _text(self.index_digest, "INDEX_DIGEST_REQUIRED")
        _text(self.layer_id, "LAYER_ID_REQUIRED")
        if isinstance(self.num_experts, bool) or not isinstance(self.num_experts, int) or self.num_experts <= 0:
            raise PerExpertSourceError("NUM_EXPERTS_INVALID")
        expected = set(range(self.num_experts))
        if set(self.experts) != expected:
            missing = sorted(expected - set(self.experts))
            extra = sorted(set(self.experts) - expected)
            raise PerExpertSourceError("PER_EXPERT_COVERAGE_INCOMPLETE", f"missing={missing},extra={extra}")
        for expert_id, keys in self.experts.items():
            if keys.expert_id != expert_id:
                raise PerExpertSourceError("EXPERT_BINDING_ID_MISMATCH", str(expert_id))
            if self.require_fp8_scales and set(keys.scale_keys) != set(SCALE_ROLES):
                raise PerExpertSourceError("FP8_SCALE_KEYS_UNRESOLVED", str(expert_id))

    @property
    def digest(self) -> str:
        return _digest(
            {
                "model_revision": self.model_revision,
                "index_digest": self.index_digest,
                "layer_id": self.layer_id,
                "num_experts": self.num_experts,
                "require_fp8_scales": self.require_fp8_scales,
                "representation": self.representation,
                "experts": {str(i): self.experts[i].logical() for i in range(self.num_experts)},
            }
        )


def build_standard_glm_per_expert_binding(
    *,
    weight_map: Mapping[str, str],
    model_revision: str,
    index_digest: str,
    layer_id: str,
    num_experts: int,
    require_fp8_scales: bool = True,
) -> PerExpertIndexBinding:
    """Bind the standard per-expert GLM key family only when the index proves it.

    This is a detector, not an assumption. Any missing weight/scale key fails before
    a pager/backend is created. ``weight_map`` values are exact shard filenames from
    model.safetensors.index.json.
    """
    _text(model_revision, "MODEL_REVISION_REQUIRED")
    _text(index_digest, "INDEX_DIGEST_REQUIRED")
    layer_id = _text(layer_id, "LAYER_ID_REQUIRED")
    if isinstance(num_experts, bool) or not isinstance(num_experts, int) or num_experts <= 0:
        raise PerExpertSourceError("NUM_EXPERTS_INVALID")

    experts: dict[int, ExpertPhysicalKeys] = {}
    for expert_id in range(num_experts):
        weights: dict[str, str] = {}
        scales: dict[str, str] = {}
        shards: dict[str, str] = {}
        for role, projection in _PROJECTION_BY_ROLE.items():
            weight_key = f"{layer_id}.mlp.experts.{expert_id}.{projection}.weight"
            shard = weight_map.get(weight_key)
            if not isinstance(shard, str) or not shard:
                raise PerExpertSourceError("PER_EXPERT_WEIGHT_KEY_MISSING", weight_key)
            weights[role] = weight_key
            shards[weight_key] = shard

            scale_key = f"{layer_id}.mlp.experts.{expert_id}.{projection}.weight_scale_inv"
            scale_shard = weight_map.get(scale_key)
            if require_fp8_scales:
                if not isinstance(scale_shard, str) or not scale_shard:
                    raise PerExpertSourceError("FP8_SCALE_KEYS_UNRESOLVED", scale_key)
                scale_role = f"{role}_scale"
                scales[scale_role] = scale_key
                shards[scale_key] = scale_shard
            elif isinstance(scale_shard, str) and scale_shard:
                scale_role = f"{role}_scale"
                scales[scale_role] = scale_key
                shards[scale_key] = scale_shard

        experts[expert_id] = ExpertPhysicalKeys(
            expert_id=expert_id,
            weight_keys=weights,
            scale_keys=scales,
            shard_by_key=shards,
        )

    return PerExpertIndexBinding(
        model_revision=model_revision,
        index_digest=index_digest,
        layer_id=layer_id,
        num_experts=num_experts,
        experts=experts,
        require_fp8_scales=require_fp8_scales,
    )


class TensorKeyBackend(Protocol):
    """Logical exact-key request contract; not itself physical-I/O evidence."""

    def read_tensor(self, shard: str, key: str) -> Any: ...


@dataclass(frozen=True)
class PerExpertPage:
    expert_ids: tuple[int, ...]
    weights_by_expert: Mapping[int, Mapping[str, Any]]
    scales_by_expert: Mapping[int, Mapping[str, Any]]
    binding_digest: str
    tensor_reads: int


@dataclass(frozen=True)
class PerExpertPagerReceipt:
    schema: str
    binding_digest: str
    layer_id: str
    selected_experts: tuple[int, ...]
    tensor_reads: int
    logical_selected_expert_key_requests_only: bool
    physical_io_attested: bool
    selected_expert_tensor_reads_only: bool | None
    whole_bank_reads: int | None
    whole_expert_bank_materialized: bool | None
    backend_attestation_id: str | None
    all_experts_addressable: bool
    g2_admitted: bool = False
    claim_ceiling: str = "D0_PER_EXPERT_INDEX_PAGER_ONLY_NO_FLAGSHIP_RUNTIME_OR_G2_PROOF"


def _backend_io_attestation(backend: Any, binding_digest: str) -> dict[str, Any] | None:
    """Return validated source-bound physical-I/O evidence, or UNKNOWN when absent."""
    attestor = getattr(backend, "io_attestation", None)
    if not callable(attestor):
        return None
    raw = attestor(binding_digest)
    if not isinstance(raw, Mapping):
        raise PerExpertSourceError("BACKEND_IO_ATTESTATION_INVALID")
    if raw.get("schema") != BACKEND_IO_ATTESTATION_SCHEMA:
        raise PerExpertSourceError("BACKEND_IO_ATTESTATION_SCHEMA_MISMATCH")
    if raw.get("binding_digest") != binding_digest:
        raise PerExpertSourceError("BACKEND_IO_ATTESTATION_BINDING_MISMATCH")
    attestation_id = raw.get("attestation_id")
    selected_only = raw.get("physical_selected_only")
    whole_bank_reads = raw.get("whole_bank_reads")
    whole_bank_materialized = raw.get("whole_bank_materialized")
    if not isinstance(attestation_id, str) or not attestation_id.strip():
        raise PerExpertSourceError("BACKEND_IO_ATTESTATION_ID_REQUIRED")
    if not isinstance(selected_only, bool):
        raise PerExpertSourceError("BACKEND_PHYSICAL_SELECTED_ONLY_INVALID")
    if isinstance(whole_bank_reads, bool) or not isinstance(whole_bank_reads, int) or whole_bank_reads < 0:
        raise PerExpertSourceError("BACKEND_WHOLE_BANK_READS_INVALID")
    if not isinstance(whole_bank_materialized, bool):
        raise PerExpertSourceError("BACKEND_WHOLE_BANK_MATERIALIZED_INVALID")
    return {
        "attestation_id": attestation_id.strip(),
        "physical_selected_only": selected_only,
        "whole_bank_reads": whole_bank_reads,
        "whole_bank_materialized": whole_bank_materialized,
    }


class PerExpertIndexPager:
    def __init__(self, binding: PerExpertIndexBinding, backend: TensorKeyBackend) -> None:
        self.binding = binding
        self.backend = backend
        self._last_receipt: PerExpertPagerReceipt | None = None

    def _assert_current(self, model_revision: str, index_digest: str) -> None:
        if model_revision != self.binding.model_revision:
            raise PerExpertSourceError("MODEL_REVISION_STALE")
        if index_digest != self.binding.index_digest:
            raise PerExpertSourceError("INDEX_DIGEST_STALE")

    def load_selected(
        self,
        expert_ids: Sequence[int],
        *,
        model_revision: str,
        index_digest: str,
    ) -> PerExpertPage:
        self._assert_current(model_revision, index_digest)
        selected = canonical_expert_ids(expert_ids, self.binding.num_experts)
        if len(selected) == self.binding.num_experts:
            raise PerExpertReadError(
                "WHOLE_EXPERT_BANK_SINGLE_CALL_FORBIDDEN",
                "full reopenability must be exercised across bounded selections",
            )
        weight_payloads: dict[int, dict[str, Any]] = {}
        scale_payloads: dict[int, dict[str, Any]] = {}
        reads = 0

        for expert_id in selected:
            source = self.binding.experts[expert_id]
            weights: dict[str, Any] = {}
            scales: dict[str, Any] = {}
            # Stage a complete expert before publishing it into the result.
            try:
                for role in WEIGHT_ROLES:
                    key = source.weight_keys[role]
                    weights[role] = self.backend.read_tensor(source.shard_by_key[key], key)
                    reads += 1
                for role in SCALE_ROLES:
                    key = source.scale_keys.get(role)
                    if key is None:
                        if self.binding.require_fp8_scales:
                            raise PerExpertReadError("FP8_SCALE_KEYS_UNRESOLVED", f"expert={expert_id},role={role}")
                        continue
                    scales[role] = self.backend.read_tensor(source.shard_by_key[key], key)
                    reads += 1
            except PerExpertPagerError:
                raise
            except (KeyError, FileNotFoundError, IndexError, OSError) as exc:
                raise PerExpertReadError("SELECTED_EXPERT_TENSOR_READ_FAILED", f"expert={expert_id}") from exc

            weight_payloads[expert_id] = weights
            scale_payloads[expert_id] = scales

        page = PerExpertPage(
            expert_ids=selected,
            weights_by_expert=weight_payloads,
            scales_by_expert=scale_payloads,
            binding_digest=self.binding.digest,
            tensor_reads=reads,
        )
        physical = _backend_io_attestation(self.backend, self.binding.digest)
        self._last_receipt = PerExpertPagerReceipt(
            schema="AuraPerExpertIndexPagerReceiptV1",
            binding_digest=self.binding.digest,
            layer_id=self.binding.layer_id,
            selected_experts=selected,
            tensor_reads=reads,
            logical_selected_expert_key_requests_only=True,
            physical_io_attested=physical is not None,
            selected_expert_tensor_reads_only=None if physical is None else physical["physical_selected_only"],
            whole_bank_reads=None if physical is None else physical["whole_bank_reads"],
            whole_expert_bank_materialized=None if physical is None else physical["whole_bank_materialized"],
            backend_attestation_id=None if physical is None else physical["attestation_id"],
            all_experts_addressable=(set(self.binding.experts) == set(range(self.binding.num_experts))),
        )
        return page

    def receipt(self) -> PerExpertPagerReceipt:
        if self._last_receipt is None:
            raise PerExpertPagerError("NO_SUCCESSFUL_PAGE")
        return self._last_receipt


def fuse_gate_up_rows(gate: Sequence[Any], up: Sequence[Any]) -> tuple[Any, ...]:
    """Tiny/reference helper matching Transformers' gate-rows then up-rows packing order."""
    return tuple(gate) + tuple(up)
