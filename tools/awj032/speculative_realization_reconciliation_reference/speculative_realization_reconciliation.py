from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = 'AURA-AWJ032-O5-SPECULATIVE-REALIZATION-RECONCILIATION-v1'
O_AVX14_CAMPAIGN_ROOT = '56f786e2e4a8a505a814886381aa92693df8e3e2e2d9ed548fcfd4e3c057645f'
O20_HOLD_EMPIRICAL = 'HOLD_EMPIRICAL_PORT_RUN'
O4_EFFECT_TIME_ADMIT = 'ADMIT_D0_EFFECT_TIME_ADAPTER_REALIZATION'
HEX = set('0123456789abcdef')


def _canon(v: object) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _root(v: object) -> str:
    return sha256(_canon(v)).hexdigest()


def _need_root(v: str, name: str) -> None:
    if not isinstance(v, str) or len(v) != 64 or not set(v) <= HEX:
        raise ValueError(f'{name}: sha256 required')


class MaterializationKind(str, Enum):
    QWEN_ADAPTER = 'QWEN_ADAPTER'
    GLM_EXPERT_SLICE_SET = 'GLM_EXPERT_SLICE_SET'


class AdoptionTarget(str, Enum):
    CACHE_REUSE = 'CACHE_REUSE'
    SERVING_ACTIVATION = 'SERVING_ACTIVATION'
    TRAINING_ACTIVATION = 'TRAINING_ACTIVATION'


class Disposition(str, Enum):
    REUSE_EXACT_SPECULATIVE_BYTES_D0 = 'REUSE_EXACT_SPECULATIVE_BYTES_D0'
    ADMIT_D0_EFFECT_TIME_REBOUND = 'ADMIT_D0_EFFECT_TIME_REBOUND'
    DISSOLVE_NONWINNING_CANDIDATE = 'DISSOLVE_NONWINNING_CANDIDATE'
    HOLD_PARENT_RECONCILIATION_PROOF = 'HOLD_PARENT_RECONCILIATION_PROOF'
    HOLD_PROJECT_BASE_CURRENTNESS = 'HOLD_PROJECT_BASE_CURRENTNESS'
    HOLD_SOURCE_CURRENTNESS = 'HOLD_SOURCE_CURRENTNESS'
    HOLD_RUNTIME_CURRENTNESS = 'HOLD_RUNTIME_CURRENTNESS'
    HOLD_PROOF_CURRENTNESS = 'HOLD_PROOF_CURRENTNESS'
    HOLD_CONSUMER_CURRENTNESS = 'HOLD_CONSUMER_CURRENTNESS'
    HOLD_MATERIALIZATION_IDENTITY = 'HOLD_MATERIALIZATION_IDENTITY'
    HOLD_O20_STATIC_ABI = 'HOLD_O20_STATIC_ABI'
    HOLD_NATIVE_ROUTE_BINDING = 'HOLD_NATIVE_ROUTE_BINDING'
    HOLD_SELECTED_SLICE_BINDING = 'HOLD_SELECTED_SLICE_BINDING'
    HOLD_FP8_SCALE_BINDING = 'HOLD_FP8_SCALE_BINDING'
    HOLD_EMPIRICAL_PORT_RUN = 'HOLD_EMPIRICAL_PORT_RUN'
    HOLD_O4_EFFECT_TIME_REBIND = 'HOLD_O4_EFFECT_TIME_REBIND'
    HOLD_UNSUPPORTED_ACTIVATION = 'HOLD_UNSUPPORTED_ACTIVATION'


@dataclass(frozen=True)
class SpeculativeMaterializationCapsule:
    kind: MaterializationKind
    project_base_root: str
    candidate_operation_root: str
    materialization_root: str
    source_generation_root: str
    runtime_root: str
    proof_root: str
    consumer_root: str
    reconciliation_parent_root: str
    adapter_realization_root: str | None = None
    adapter_cache_root: str | None = None
    native_route_root: str | None = None
    selected_slice_plan_root: str | None = None
    fp8_scale_plan_root: str | None = None
    project_truth: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MaterializationKind):
            raise TypeError('MATERIALIZATION_KIND_REQUIRED')
        for n in ('project_base_root','candidate_operation_root','materialization_root','source_generation_root',
                  'runtime_root','proof_root','consumer_root','reconciliation_parent_root'):
            _need_root(getattr(self, n), n)
        if self.reconciliation_parent_root != O_AVX14_CAMPAIGN_ROOT:
            raise ValueError('O_AVX14_PARENT_ROOT_MISMATCH')
        if self.project_truth or self.effect_authority or self.gate10:
            raise ValueError('SPECULATIVE_CAPSULE_CANNOT_MINT_TRUTH_OR_AUTHORITY')
        if self.kind is MaterializationKind.QWEN_ADAPTER:
            if not self.adapter_realization_root or not self.adapter_cache_root:
                raise ValueError('QWEN_ADAPTER_ROOTS_REQUIRED')
            _need_root(self.adapter_realization_root, 'adapter_realization_root')
            _need_root(self.adapter_cache_root, 'adapter_cache_root')
        else:
            for n in ('native_route_root','selected_slice_plan_root','fp8_scale_plan_root'):
                v = getattr(self, n)
                if v is None:
                    raise ValueError(f'{n.upper()}_REQUIRED')
                _need_root(v, n)

    @property
    def capsule_root(self) -> str:
        return _root({'schema':SCHEMA,'kind':'speculative_materialization',**asdict(self)})


@dataclass(frozen=True)
class CanonicalSelectionV1:
    project_base_root: str
    winning_candidate_operation_root: str
    materialization_root: str
    source_generation_root: str
    runtime_root: str
    proof_root: str
    consumer_root: str

    def __post_init__(self) -> None:
        for n in asdict(self):
            _need_root(getattr(self, n), n)

    @property
    def selection_root(self) -> str:
        return _root({'schema':SCHEMA,'kind':'canonical_selection',**asdict(self)})


@dataclass(frozen=True)
class O20PortBindingV1:
    port_abi_root: str
    static_abi_ready: bool
    decision: str
    native_router_owns_selection: bool
    native_route_root: str
    selected_slice_plan_root: str
    fp8_scale_plan_root: str
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ('port_abi_root','native_route_root','selected_slice_plan_root','fp8_scale_plan_root'):
            _need_root(getattr(self,n), n)
        if self.effect_authority or self.gate10:
            raise ValueError('O20_BINDING_CANNOT_MINT_AUTHORITY')

    @property
    def binding_root(self) -> str:
        return _root({'schema':SCHEMA,'kind':'o20_binding',**asdict(self)})


@dataclass(frozen=True)
class O4EffectTimeBindingV1:
    admitted_d0: bool
    reason: str
    realization_root: str
    cache_root: str
    process_witness_root: str
    effect_time_root: str
    effect_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ('realization_root','cache_root','process_witness_root','effect_time_root'):
            _need_root(getattr(self,n), n)
        if self.effect_authority or self.checkpoint_authority or self.gate10:
            raise ValueError('O4_BINDING_AUTHORITY_ESCALATION')

    @property
    def binding_root(self) -> str:
        return _root({'schema':SCHEMA,'kind':'o4_effect_time_binding',**asdict(self)})


@dataclass(frozen=True)
class ReconciliationDecisionV1:
    disposition: Disposition
    reason: str
    speculative_capsule_root: str
    canonical_selection_root: str
    materialization_root: str
    reuse_or_effect_root: str | None
    effect_authority: bool = False
    training_authority: bool = False
    checkpoint_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ('speculative_capsule_root','canonical_selection_root','materialization_root'):
            _need_root(getattr(self,n), n)
        if self.reuse_or_effect_root is not None:
            _need_root(self.reuse_or_effect_root, 'reuse_or_effect_root')
        if self.effect_authority or self.training_authority or self.checkpoint_authority or self.gate10:
            raise ValueError('O5_DECISION_CANNOT_MINT_AUTHORITY')


def reconcile_speculative_materialization(*,
    speculative: SpeculativeMaterializationCapsule,
    current: CanonicalSelectionV1,
    target: AdoptionTarget,
    o20: O20PortBindingV1 | None = None,
    o4: O4EffectTimeBindingV1 | None = None,
) -> ReconciliationDecisionV1:
    if not isinstance(target, AdoptionTarget):
        raise TypeError('ADOPTION_TARGET_REQUIRED')

    def decide(d: Disposition, reason: str, derived: str | None = None) -> ReconciliationDecisionV1:
        return ReconciliationDecisionV1(d, reason, speculative.capsule_root, current.selection_root,
                                        speculative.materialization_root, derived)

    # O-AVX14 keeper: same bytes do not rescue a losing candidate.
    if current.winning_candidate_operation_root != speculative.candidate_operation_root:
        return decide(Disposition.DISSOLVE_NONWINNING_CANDIDATE, 'winner moved; speculative bytes remain noncanonical')
    if current.project_base_root != speculative.project_base_root:
        return decide(Disposition.HOLD_PROJECT_BASE_CURRENTNESS, 'canonical project base moved')
    if current.source_generation_root != speculative.source_generation_root:
        return decide(Disposition.HOLD_SOURCE_CURRENTNESS, 'source generation moved')
    if current.runtime_root != speculative.runtime_root:
        return decide(Disposition.HOLD_RUNTIME_CURRENTNESS, 'runtime generation moved')
    if current.proof_root != speculative.proof_root:
        return decide(Disposition.HOLD_PROOF_CURRENTNESS, 'proof generation moved')
    if current.consumer_root != speculative.consumer_root:
        return decide(Disposition.HOLD_CONSUMER_CURRENTNESS, 'proof consumer generation moved')
    if current.materialization_root != speculative.materialization_root:
        return decide(Disposition.HOLD_MATERIALIZATION_IDENTITY, 'materialization bytes moved')

    if speculative.kind is MaterializationKind.GLM_EXPERT_SLICE_SET:
        if o20 is None or not o20.static_abi_ready or o20.decision != O20_HOLD_EMPIRICAL or not o20.native_router_owns_selection:
            return decide(Disposition.HOLD_O20_STATIC_ABI, 'O20 GLM static port ABI is absent/not current')
        if o20.native_route_root != speculative.native_route_root:
            return decide(Disposition.HOLD_NATIVE_ROUTE_BINDING, 'native GLM route binding moved')
        if o20.selected_slice_plan_root != speculative.selected_slice_plan_root:
            return decide(Disposition.HOLD_SELECTED_SLICE_BINDING, 'selected expert-slice plan moved')
        if o20.fp8_scale_plan_root != speculative.fp8_scale_plan_root:
            return decide(Disposition.HOLD_FP8_SCALE_BINDING, 'FP8 scale-slice plan moved')
        if target is AdoptionTarget.TRAINING_ACTIVATION:
            # O20 explicitly stops at static ABI closure. Materialization reuse cannot promote that state.
            return decide(Disposition.HOLD_EMPIRICAL_PORT_RUN, 'exact owner-host GLM streamed-training smoke remains required')
        if target is AdoptionTarget.SERVING_ACTIVATION:
            return decide(Disposition.HOLD_UNSUPPORTED_ACTIVATION, 'O20 training-port evidence does not own serving activation')
        reuse = _root({'schema':SCHEMA,'kind':'glm_speculative_bytes_reuse_d0',
                       'speculative_capsule_root':speculative.capsule_root,
                       'selection_root':current.selection_root,'o20_binding_root':o20.binding_root})
        return decide(Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,
                      'exact winning GLM slice bytes may be reused as D0 material for the empirical owner-host proof only', reuse)

    # Qwen adapter lineage.
    if target is AdoptionTarget.TRAINING_ACTIVATION:
        return decide(Disposition.HOLD_UNSUPPORTED_ACTIVATION, 'realized adapter bytes do not grant training activation')
    if target is AdoptionTarget.CACHE_REUSE:
        reuse = _root({'schema':SCHEMA,'kind':'qwen_adapter_cache_reuse_d0',
                       'speculative_capsule_root':speculative.capsule_root,'selection_root':current.selection_root,
                       'adapter_realization_root':speculative.adapter_realization_root,
                       'adapter_cache_root':speculative.adapter_cache_root})
        return decide(Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,
                      'exact winning adapter bytes reusable as immutable D0 cache material; serving currentness remains separate', reuse)
    if (o4 is None or not o4.admitted_d0 or o4.reason != O4_EFFECT_TIME_ADMIT
            or o4.realization_root != speculative.adapter_realization_root
            or o4.cache_root != speculative.adapter_cache_root):
        return decide(Disposition.HOLD_O4_EFFECT_TIME_REBIND,
                      'serving activation requires exact current O4 realization/cache/process rebind')
    effect = _root({'schema':SCHEMA,'kind':'qwen_effect_time_rebound_d0',
                    'speculative_capsule_root':speculative.capsule_root,'selection_root':current.selection_root,
                    'o4_binding_root':o4.binding_root})
    return decide(Disposition.ADMIT_D0_EFFECT_TIME_REBOUND,
                  'winning adapter realization is rebound to exact O4 effect-time D0 process evidence', effect)


# Dependency-closed consumer map for proof-consumer Customs. A producer-field change must reopen
# at least the focused tests and deterministic campaign; fields that affect higher-order proof
# geometry additionally reopen the state-space receipts.
PROOF_CONSUMER_MATRIX: dict[str, tuple[str, ...]] = {
    'candidate_operation_root': ('focused_tests','random_campaign','oracle_customs','omega8','13d','hs1000'),
    'project_base_root': ('focused_tests','random_campaign','oracle_customs','omega8','13d'),
    'source_generation_root': ('focused_tests','random_campaign','oracle_customs','omega8','13d'),
    'runtime_root': ('focused_tests','random_campaign','oracle_customs','omega8','13d'),
    'proof_root': ('focused_tests','random_campaign','oracle_customs','proof_receipt'),
    'consumer_root': ('focused_tests','random_campaign','proof_consumer_audit','proof_receipt'),
    'materialization_root': ('focused_tests','random_campaign','oracle_customs','hs1000'),
    'native_route_root': ('focused_tests','random_campaign','oracle_customs','omega8','hs1000'),
    'selected_slice_plan_root': ('focused_tests','random_campaign','oracle_customs','omega8','hs1000'),
    'fp8_scale_plan_root': ('focused_tests','random_campaign','oracle_customs','omega8','hs1000'),
    'adapter_realization_root': ('focused_tests','random_campaign','oracle_customs','13d','hs1000'),
    'adapter_cache_root': ('focused_tests','random_campaign','oracle_customs','13d','hs1000'),
    'o20_binding': ('focused_tests','random_campaign','proof_consumer_audit','hs1000'),
    'o4_binding': ('focused_tests','random_campaign','proof_consumer_audit','hs1000'),
}
