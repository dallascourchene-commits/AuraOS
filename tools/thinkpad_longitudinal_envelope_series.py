"""Bind three time-scoped ThinkPad operating envelopes to benchmark phases.

This module correlates PROCESS_COLD, PROCESS_WARM, and RESTART observations. It does
not infer thermal throttling, battery limits, memory-pressure causality, same-host
identity, benchmark execution, or performance authority from those correlations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from tools.thinkpad_sustained_operating_envelope import (
    CURRENTNESS_DOMAIN as ENVELOPE_CURRENTNESS_DOMAIN,
    SustainedOperatingEnvelope,
)

SCHEMA = "AuraThinkPadLongitudinalEnvelopeSeriesV1"
CURRENTNESS_DOMAIN = "thinkpad-longitudinal-envelope-series-generation"
PHASES = ("PROCESS_COLD", "PROCESS_WARM", "RESTART")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LongitudinalEnvelopeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LongitudinalEnvelopeError("NONCANONICAL_SERIES") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise LongitudinalEnvelopeError("INVALID_SHA256", name)


def _parse_time(value: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise LongitudinalEnvelopeError("OBSERVATION_TIME_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LongitudinalEnvelopeError("OBSERVATION_TIME_INVALID", value) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LongitudinalEnvelopeError("OBSERVATION_TIME_MUST_BE_OFFSET_AWARE", value)
    return parsed


def _max_temp(envelope: SustainedOperatingEnvelope) -> int | None:
    values = [
        item.temperature_millicelsius
        for item in envelope.thermal_zones
        if type(item.temperature_millicelsius) is int
    ]
    return max(values) if values else None


def _min_current_khz(envelope: SustainedOperatingEnvelope) -> int | None:
    values = [
        item.current_khz
        for item in envelope.cpu_frequency_policies
        if type(item.current_khz) is int
    ]
    return min(values) if values else None


def _ac_online(envelope: SustainedOperatingEnvelope) -> int | None:
    values = [
        item.online
        for item in envelope.power_supplies
        if item.kind == "Mains" and item.online in (0, 1)
    ]
    if not values:
        return None
    return 1 if any(values) else 0


def _battery_capacity(envelope: SustainedOperatingEnvelope) -> int | None:
    values = [
        item.capacity_percent
        for item in envelope.power_supplies
        if item.kind == "Battery" and type(item.capacity_percent) is int
    ]
    return min(values) if values else None


def _delta(a: int | float | None, b: int | float | None) -> int | float | None:
    if a is None or b is None:
        return None
    return b - a


def _summary(phase: str, envelope: SustainedOperatingEnvelope) -> dict[str, Any]:
    return {
        "phase": phase,
        "observed_at_utc": envelope.observed_at_utc,
        "observation_digest": envelope.observation_digest,
        "evidence_ref": envelope.evidence_ref,
        "memory_available_ratio": envelope.memory_available_ratio,
        "swap_free_ratio": envelope.swap_free_ratio,
        "memory_psi": envelope.memory_psi,
        "max_temperature_millicelsius": _max_temp(envelope),
        "min_observed_current_cpu_khz": _min_current_khz(envelope),
        "ac_online": _ac_online(envelope),
        "battery_capacity_percent": _battery_capacity(envelope),
    }


@dataclass(frozen=True)
class ThinkPadLongitudinalEnvelopeSeries:
    benchmark_request_digest: str
    query_sequence_sha256: str
    phase_summaries: tuple[dict[str, Any], ...]
    first_to_last_memory_available_ratio_delta: float | None
    first_to_last_swap_free_ratio_delta: float | None
    first_to_last_max_temperature_millicelsius_delta: int | None
    first_to_last_min_current_cpu_khz_delta: int | None
    first_to_last_battery_capacity_percent_delta: int | None
    ac_online_changed: bool | None
    source_envelope_currentness_domain: str = ENVELOPE_CURRENTNESS_DOMAIN
    currentness_domain: str = CURRENTNESS_DOMAIN
    historical_series_only: bool = True
    same_host_proven: bool = False
    benchmark_execution_proven: bool = False
    thermal_throttling_proven: bool = False
    temperature_caused_performance_change: bool = False
    memory_pressure_caused_performance_change: bool = False
    battery_state_caused_performance_change: bool = False
    performance_winner_proven: bool = False
    current_now_proven: bool = False
    producer_authenticated: bool = False
    g2_admitted: bool = False
    effect_authority_proven: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def series_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def evidence_ref(self) -> str:
        return f"thinkpad-longitudinal-envelope-series-sha256:{self.series_digest}"


def build_longitudinal_envelope_series(
    *,
    benchmark_request_digest: str,
    query_sequence_sha256: str,
    process_cold: SustainedOperatingEnvelope,
    process_warm: SustainedOperatingEnvelope,
    restart: SustainedOperatingEnvelope,
) -> ThinkPadLongitudinalEnvelopeSeries:
    """Build an ordered three-phase observation series without causal promotion."""
    _require_sha256("benchmark_request_digest", benchmark_request_digest)
    _require_sha256("query_sequence_sha256", query_sequence_sha256)
    envelopes = (process_cold, process_warm, restart)
    for phase, envelope in zip(PHASES, envelopes, strict=True):
        if type(envelope) is not SustainedOperatingEnvelope:
            raise LongitudinalEnvelopeError("EXACT_ENVELOPE_TYPE_REQUIRED", phase)
        if envelope.currentness_domain != ENVELOPE_CURRENTNESS_DOMAIN:
            raise LongitudinalEnvelopeError("ENVELOPE_CURRENTNESS_DOMAIN_MISMATCH", phase)
        if envelope.current_at_observation_time_only is not True:
            raise LongitudinalEnvelopeError("OBSERVATION_TIME_SCOPING_REQUIRED", phase)
        if (
            envelope.thermal_throttling_proven
            or envelope.battery_power_limit_proven
            or envelope.memory_pressure_safe_for_model
            or envelope.performance_effect_proven
            or envelope.model_execution_observed
            or envelope.producer_authenticated
            or envelope.effect_authority_proven
            or envelope.g2_admitted
        ):
            raise LongitudinalEnvelopeError("PARENT_ENVELOPE_CEILING_WIDENED", phase)

    times = tuple(_parse_time(item.observed_at_utc) for item in envelopes)
    if not (times[0] < times[1] < times[2]):
        raise LongitudinalEnvelopeError("PHASE_TIMESTAMPS_NOT_STRICTLY_INCREASING")
    digests = tuple(item.observation_digest for item in envelopes)
    if len(set(digests)) != 3:
        raise LongitudinalEnvelopeError("DISTINCT_PHASE_OBSERVATIONS_REQUIRED")

    summaries = tuple(_summary(phase, item) for phase, item in zip(PHASES, envelopes, strict=True))
    first = summaries[0]
    last = summaries[-1]
    ac_changed: bool | None
    if first["ac_online"] is None or last["ac_online"] is None:
        ac_changed = None
    else:
        ac_changed = first["ac_online"] != last["ac_online"]

    return ThinkPadLongitudinalEnvelopeSeries(
        benchmark_request_digest=benchmark_request_digest,
        query_sequence_sha256=query_sequence_sha256,
        phase_summaries=summaries,
        first_to_last_memory_available_ratio_delta=_delta(
            first["memory_available_ratio"], last["memory_available_ratio"]
        ),
        first_to_last_swap_free_ratio_delta=_delta(first["swap_free_ratio"], last["swap_free_ratio"]),
        first_to_last_max_temperature_millicelsius_delta=_delta(
            first["max_temperature_millicelsius"], last["max_temperature_millicelsius"]
        ),
        first_to_last_min_current_cpu_khz_delta=_delta(
            first["min_observed_current_cpu_khz"], last["min_observed_current_cpu_khz"]
        ),
        first_to_last_battery_capacity_percent_delta=_delta(
            first["battery_capacity_percent"], last["battery_capacity_percent"]
        ),
        ac_online_changed=ac_changed,
    )
