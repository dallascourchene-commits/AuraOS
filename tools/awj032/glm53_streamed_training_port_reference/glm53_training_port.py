from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable, Sequence


class PortDecision(str, Enum):
    BLOCK_SECURITY = "BLOCK_SECURITY"
    BLOCK_ARCHITECTURE = "BLOCK_ARCHITECTURE"
    BLOCK_EXPERT_BANK = "BLOCK_EXPERT_BANK"
    BLOCK_ROUTER = "BLOCK_ROUTER"
    BLOCK_FP8 = "BLOCK_FP8"
    BLOCK_TRAINING_SKELETON = "BLOCK_TRAINING_SKELETON"
    HOLD_EMPIRICAL_PORT_RUN = "HOLD_EMPIRICAL_PORT_RUN"


@dataclass(frozen=True)
class StaticObservation:
    architecture: str
    model_type: str
    layer_count: int
    num_experts: int
    top_k: int
    first_dense_layers: int
    gate_up_rank: int
    down_rank: int
    experts_interface: bool
    native_router_owns_selection: bool
    fp8_format: str
    fp8_block_shape: tuple[int, int]
    remote_code_false: bool
    layer_topology: tuple[str, str, str, str]
    transformers_version: str
    airllm_revision: str


@dataclass(frozen=True)
class TrainingSkeleton:
    stream_one_decoder_layer: bool
    cpu_hidden_graph: bool
    backward_recompute: bool
    adapter_only_gradients: bool
    use_cache: bool
    gradient_checkpointing: bool
    lora_dropout: float


@dataclass(frozen=True)
class PortReceipt:
    decision: PortDecision
    static_abi_ready: bool
    reason: str
    port_abi_root: str
    y13: tuple[str, ...]
    k27: tuple[int, int, int]
    empirical_obligation: str
    claim_ceiling: str = "D0_NONPROMOTING"


EXPECTED = {
    "architecture": "GlmMoeDsaForCausalLM",
    "model_type": "glm_moe_dsa",
    "layer_count": 78,
    "num_experts": 256,
    "top_k": 8,
    "first_dense_layers": 3,
    "gate_up_rank": 3,
    "down_rank": 3,
    "fp8_format": "e4m3",
    "fp8_block_shape": (128, 128),
    "layer_topology": ("model.embed_tokens", "model.layers", "model.norm", "lm_head"),
    "transformers_version": "5.15",
    "airllm_revision": "55e435087d951da8c25ab3672e969025241a398e",
}


def _hash(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def selected_expert_slice_plan(
    top_k_indices: Iterable[Iterable[int]],
    *,
    num_experts: int = 256,
    include_fp8_scales: bool = True,
) -> tuple[str, ...]:
    selected = sorted({int(i) for row in top_k_indices for i in row})
    if any(i < 0 or i >= num_experts for i in selected):
        raise ValueError("expert id out of range")
    keys: list[str] = []
    for i in selected:
        # Explicit first-axis slices: never return an unindexed whole-bank key.
        keys.extend((f"gate_up_proj[{i}]", f"down_proj[{i}]"))
        if include_fp8_scales:
            keys.extend((f"gate_up_proj_scale[{i}]", f"down_proj_scale[{i}]"))
    return tuple(keys)


def _skeleton_ok(s: TrainingSkeleton) -> bool:
    return (
        s.stream_one_decoder_layer
        and s.cpu_hidden_graph
        and s.backward_recompute
        and s.adapter_only_gradients
        and not s.use_cache
        and not s.gradient_checkpointing
        and s.lora_dropout == 0.0
    )


def assess_port(obs: StaticObservation, skeleton: TrainingSkeleton) -> PortReceipt:
    security_ok = obs.remote_code_false
    architecture_ok = (
        obs.architecture == EXPECTED["architecture"]
        and obs.model_type == EXPECTED["model_type"]
        and obs.layer_count == EXPECTED["layer_count"]
        and obs.first_dense_layers == EXPECTED["first_dense_layers"]
        and obs.layer_topology == EXPECTED["layer_topology"]
        and obs.transformers_version.startswith(EXPECTED["transformers_version"])
        and obs.airllm_revision == EXPECTED["airllm_revision"]
    )
    expert_ok = (
        obs.num_experts == EXPECTED["num_experts"]
        and obs.gate_up_rank == EXPECTED["gate_up_rank"]
        and obs.down_rank == EXPECTED["down_rank"]
        and obs.experts_interface
    )
    router_ok = obs.top_k == EXPECTED["top_k"] and obs.native_router_owns_selection
    fp8_ok = obs.fp8_format == EXPECTED["fp8_format"] and obs.fp8_block_shape == EXPECTED["fp8_block_shape"]
    skeleton_ok = _skeleton_ok(skeleton)

    if not security_ok:
        decision, reason = PortDecision.BLOCK_SECURITY, "trust_remote_code=False is mandatory"
    elif not architecture_ok:
        decision, reason = PortDecision.BLOCK_ARCHITECTURE, "GLM/AirLLM source or ordinary layer topology mismatch"
    elif not expert_ok:
        decision, reason = PortDecision.BLOCK_EXPERT_BANK, "packed 3-D expert-bank / ExpertsInterface contract mismatch"
    elif not router_ok:
        decision, reason = PortDecision.BLOCK_ROUTER, "native GLM router must own top-k expert selection"
    elif not fp8_ok:
        decision, reason = PortDecision.BLOCK_FP8, "FP8 format/block-scale slicing contract mismatch"
    elif not skeleton_ok:
        decision, reason = PortDecision.BLOCK_TRAINING_SKELETON, "AirLLM streamed backward-recompute invariants are incomplete"
    else:
        decision, reason = PortDecision.HOLD_EMPIRICAL_PORT_RUN, "static ABI closed; exact owner-host/model smoke receipt still required"

    static_ready = decision is PortDecision.HOLD_EMPIRICAL_PORT_RUN
    payload = {
        "observation": obs.__dict__,
        "skeleton": skeleton.__dict__,
        "decision": decision.value,
        "slice_semantics": "unique-native-topk-first-axis-expert-and-fp8-scale-slices",
        "experts_impl": "aura_airllm_streaming via Transformers ExpertsInterface",
    }
    root = _hash(payload)
    # X12 consequence state + derived W0 witness. W0 is not a free axis.
    x12 = (
        obs.architecture,
        obs.model_type,
        str(obs.layer_count),
        str(obs.num_experts),
        str(obs.top_k),
        str(obs.first_dense_layers),
        f"ranks:{obs.gate_up_rank}/{obs.down_rank}",
        f"fp8:{obs.fp8_format}:{obs.fp8_block_shape}",
        obs.transformers_version,
        obs.airllm_revision,
        "D0_NONPROMOTING",
        decision.value,
    )
    y13 = x12 + (_hash({"x12": x12, "port_abi_root": root}),)
    k27 = tuple(1 if x else -1 for x in (security_ok and architecture_ok, expert_ok and router_ok, fp8_ok and skeleton_ok))
    return PortReceipt(
        decision=decision,
        static_abi_ready=static_ready,
        reason=reason,
        port_abi_root=root,
        y13=y13,
        k27=k27,
        empirical_obligation=(
            "instantiate exact GLM-5.3 + pinned Transformers/AirLLM on updated owner-host; "
            "prove selected expert+scale materialization, native-route equality, forward/backward recompute, "
            "adapter-only gradients, bounded peak memory, checkpoint proposal bytes, and teardown receipts"
        ),
    )
