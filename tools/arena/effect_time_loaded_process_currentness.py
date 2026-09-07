from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-O20R-EFFECT-TIME-LOADED-PROCESS-CURRENTNESS-v1"

def digest(x):
    return sha256(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

class MutationModel(str, Enum):
    IMMUTABLE_FOR_CUT = "IMMUTABLE_FOR_CUT"
    MUTATION_OBSERVED_AND_VERSIONED = "MUTATION_OBSERVED_AND_VERSIONED"
    MUTATION_UNOBSERVABLE = "MUTATION_UNOBSERVABLE"

class Disposition(str, Enum):
    ADMIT_D0 = "ADMIT_EFFECT_TIME_PROCESS_D0"
    HOLD = "HOLD"

@dataclass(frozen=True)
class InstalledRuntimeAttestation:
    host_id: str
    installed_runtime_root: str
    generation: int
    observed_at: int
    valid_until: int
    authenticated: bool
    current: bool

@dataclass(frozen=True)
class LoadedProcessWitness:
    host_id: str
    installed_runtime_root: str
    process_id: str
    process_start_nonce: str
    process_generation: int
    load_generation: int
    loaded_units: tuple[tuple[str, str], ...]
    dispatch_root: str
    mutation_model: MutationModel
    mutation_generation: int
    unresolved_answer_bearing_units: tuple[str, ...]
    serving_population_root: str
    worker_id: str
    population_complete: bool
    observed_at: int
    valid_until: int
    authenticated: bool
    immutable_cut_root: str | None = None
    def loaded_units_root(self):
        return digest(sorted(self.loaded_units))
    def binding_root(self):
        return digest({
            "schema": SCHEMA,
            "host_id": self.host_id,
            "installed_runtime_root": self.installed_runtime_root,
            "process_id": self.process_id,
            "process_start_nonce": self.process_start_nonce,
            "process_generation": self.process_generation,
            "load_generation": self.load_generation,
            "loaded_units_root": self.loaded_units_root(),
            "dispatch_root": self.dispatch_root,
            "mutation_model": self.mutation_model.value,
            "mutation_generation": self.mutation_generation,
            "unresolved": sorted(self.unresolved_answer_bearing_units),
            "serving_population_root": self.serving_population_root,
            "worker_id": self.worker_id,
            "population_complete": self.population_complete,
            "immutable_cut_root": self.immutable_cut_root,
        })

@dataclass(frozen=True)
class AtUseObservation:
    now: int
    host_id: str
    installed_runtime_root: str
    process_id: str
    process_start_nonce: str
    process_generation: int
    load_generation: int
    loaded_units_root: str
    dispatch_root: str
    mutation_generation: int
    serving_population_root: str
    selected_worker_id: str
    immutable_cut_root: str | None
    immutable_cut_current: bool

@dataclass(frozen=True)
class Decision:
    disposition: Disposition
    reason: str
    installed_attestation_root: str
    process_binding_root: str
    effect_time_witness_root: str | None = None
    effect_authority: bool = False
    checkpoint_authority: bool = False
    project_write_authority: bool = False
    gate10: bool = False

def installed_root(a: InstalledRuntimeAttestation):
    return digest({"host_id":a.host_id,"installed_runtime_root":a.installed_runtime_root,"generation":a.generation,
                   "observed_at":a.observed_at,"valid_until":a.valid_until,"authenticated":a.authenticated,"current":a.current})

def decide(installed: InstalledRuntimeAttestation, process: LoadedProcessWitness, at_use: AtUseObservation):
    ir = installed_root(installed); br = process.binding_root()
    def hold(reason): return Decision(Disposition.HOLD, reason, ir, br)
    if at_use.now < 0 or installed.observed_at < 0 or installed.valid_until < 0 or process.observed_at < 0 or process.valid_until < 0:
        return hold("MALFORMED_TIME")
    if not installed.authenticated or not installed.current: return hold("INSTALLED_ATTESTATION_NOT_CURRENT_AUTHENTIC")
    if at_use.now > installed.valid_until: return hold("INSTALLED_ATTESTATION_EXPIRED")
    if not process.authenticated: return hold("PROCESS_WITNESS_NOT_AUTHENTICATED")
    if at_use.now > process.valid_until: return hold("PROCESS_WITNESS_EXPIRED")
    if process.host_id != installed.host_id or at_use.host_id != installed.host_id: return hold("HOST_IDENTITY_MISMATCH")
    if process.installed_runtime_root != installed.installed_runtime_root or at_use.installed_runtime_root != installed.installed_runtime_root:
        return hold("INSTALLED_RUNTIME_ROOT_MISMATCH")
    if process.unresolved_answer_bearing_units: return hold("UNRESOLVED_ANSWER_BEARING_UNIT")
    if not process.population_complete: return hold("SERVING_POPULATION_INCOMPLETE")
    if at_use.serving_population_root != process.serving_population_root or at_use.selected_worker_id != process.worker_id:
        return hold("SERVING_WORKER_SELECTION_MOVED")
    if (at_use.process_id != process.process_id or at_use.process_start_nonce != process.process_start_nonce or
        at_use.process_generation != process.process_generation):
        return hold("PROCESS_INCARNATION_MOVED")
    if at_use.load_generation != process.load_generation: return hold("LOAD_GENERATION_MOVED")
    if at_use.loaded_units_root != process.loaded_units_root(): return hold("LOADED_ANSWER_BEARING_UNITS_MOVED")
    if at_use.dispatch_root != process.dispatch_root: return hold("DISPATCH_IDENTITY_MOVED")
    if process.mutation_model == MutationModel.MUTATION_UNOBSERVABLE:
        return hold("UNOBSERVABLE_RUNTIME_MUTATION")
    if process.mutation_model == MutationModel.MUTATION_OBSERVED_AND_VERSIONED:
        if at_use.mutation_generation != process.mutation_generation: return hold("MUTATION_GENERATION_MOVED")
    elif process.mutation_model == MutationModel.IMMUTABLE_FOR_CUT:
        if not process.immutable_cut_root or at_use.immutable_cut_root != process.immutable_cut_root or not at_use.immutable_cut_current:
            return hold("IMMUTABILITY_CUT_NOT_CURRENT")
    else:
        return hold("UNKNOWN_MUTATION_MODEL")
    wr = digest({"schema":SCHEMA,"installed_attestation_root":ir,"process_binding_root":br,"now":at_use.now,
                 "process_id":at_use.process_id,"process_start_nonce":at_use.process_start_nonce,"process_generation":at_use.process_generation,
                 "load_generation":at_use.load_generation,"loaded_units_root":at_use.loaded_units_root,"dispatch_root":at_use.dispatch_root,
                 "mutation_generation":at_use.mutation_generation,"serving_population_root":at_use.serving_population_root,
                 "selected_worker_id":at_use.selected_worker_id,"immutable_cut_root":at_use.immutable_cut_root})
    return Decision(Disposition.ADMIT_D0, "CURRENT_EFFECT_TIME_PROCESS_D0", ir, br, wr)
