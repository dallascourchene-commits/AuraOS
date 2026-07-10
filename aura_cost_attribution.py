"""
Aura Cost Attribution — measure context at each transformation boundary.

Calculates exclusive stage deltas rather than assigning the same total saving
to multiple components. DREAM and QDKT savings are credited only when their
recorded decision changed retrieval or avoided a repeated computation.

Dependencies: stdlib only.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ATTRIBUTION_VERSION = "AURA_COST_ATTRIBUTION_V1"

# Transformation stages in pipeline order
STAGES = [
    "RAW_OBJECTIVE",
    "POLYSYNTHETIC_PACKET",
    "CODEMAP_LOCALIZED",
    "REGION_RANKED",
    "READ_SLICE",
    "CONTEXT_CRUSHED",
    "ST3GG_POINTERIZED",
    "AGENT_HANDOFF",
    "PROVIDER_PAYLOAD",
    "PROVIDER_USAGE",
    "REPAIR_PACKET",
]


def _estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _digest(text: str | None) -> str:
    if not text:
        return ""
    return hashlib.blake2b(text.encode(), digest_size=8).hexdigest()


class StageMeasurement:
    """Measurement at a single transformation boundary."""

    def __init__(
        self,
        stage: str,
        input_chars: int = 0,
        output_chars: int = 0,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tokenizer: str | None = None,
        elapsed_ms: float = 0.0,
        artifact_text: str | None = None,
    ) -> None:
        self.stage = stage
        self.input_chars = input_chars
        self.output_chars = output_chars
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.tokenizer = tokenizer
        self.elapsed_ms = elapsed_ms
        self.artifact_digest = _digest(artifact_text)
        self.timestamp = time.time()

    @property
    def input_tokens(self) -> int:
        return self._input_tokens if self._input_tokens is not None else _estimate_tokens("x" * self.input_chars)

    @property
    def output_tokens(self) -> int:
        return self._output_tokens if self._output_tokens is not None else _estimate_tokens("x" * self.output_chars)

    @property
    def measurement_class(self) -> str:
        if self._input_tokens is not None or self._output_tokens is not None:
            return "TOKENIZER_EXACT" if self.tokenizer else "MEASURED"
        if self.input_chars > 0 or self.output_chars > 0:
            return "ESTIMATED"
        return "UNAVAILABLE"

    @property
    def exclusive_tokens_saved(self) -> int:
        """Tokens saved at this stage = input_tokens - output_tokens."""
        return max(0, self.input_tokens - self.output_tokens)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "tokenizer": self.tokenizer,
            "measurement_class": self.measurement_class,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "exclusive_tokens_saved": self.exclusive_tokens_saved,
            "artifact_digest": self.artifact_digest,
        }


class AttributionLedger:
    """Records stage measurements and calculates exclusive attribution."""

    def __init__(self) -> None:
        self._stages: list[StageMeasurement] = []

    def record_stage(self, stage: str, **kwargs: Any) -> StageMeasurement:
        """Record a stage measurement."""
        sm = StageMeasurement(stage=stage, **kwargs)
        self._stages.append(sm)
        return sm

    def attribution_report(self) -> dict[str, Any]:
        """Generate waterfall attribution report with exclusive deltas."""
        if not self._stages:
            return {
                "ok": True, "version": ATTRIBUTION_VERSION,
                "stages": [], "total_exclusive_saved": 0,
                "protocol_overhead_tokens": 0,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            }

        stage_dicts = [s.to_dict() for s in self._stages]

        # Calculate exclusive savings (each stage saves relative to its input)
        total_exclusive_saved = sum(s.exclusive_tokens_saved for s in self._stages)

        # Protocol overhead = tokens added by Aura's contracts/metadata
        # = output_tokens of stages that add overhead (e.g., AGENT_HANDOFF adds contract text)
        protocol_overhead = 0
        for s in self._stages:
            if s.stage in ("AGENT_HANDOFF", "PROVIDER_PAYLOAD"):
                if s.output_tokens > s.input_tokens:
                    protocol_overhead += s.output_tokens - s.input_tokens

        # Repair overhead
        repair_overhead = 0
        for s in self._stages:
            if s.stage == "REPAIR_PACKET":
                repair_overhead += s.output_tokens

        # No double counting: each stage's saving is exclusive
        # DREAM/QDKT are only credited if they changed retrieval
        dream_credited = any(s.stage == "REGION_RANKED" and s.exclusive_tokens_saved > 0 for s in self._stages)
        qdkt_credited = False  # Only credited when a fast-path avoided computation

        return {
            "ok": True,
            "version": ATTRIBUTION_VERSION,
            "stages": stage_dicts,
            "total_exclusive_saved": total_exclusive_saved,
            "protocol_overhead_tokens": protocol_overhead,
            "repair_overhead_tokens": repair_overhead,
            "dream_credited": dream_credited,
            "qdkt_credited": qdkt_credited,
            "attribution_note": (
                "Savings are exclusive per-stage deltas. "
                "DREAM/QDKT credited only when their decision changed retrieval. "
                "Protocol overhead (contracts, metadata) is visible."
            ),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def waterfall_markdown(self) -> str:
        """Generate waterfall markdown report."""
        report = self.attribution_report()
        lines = ["# Cost Attribution Waterfall", ""]
        lines.append("```")
        lines.append("Raw repository context")
        for stage in report.get("stages", []):
            saved = stage.get("exclusive_tokens_saved", 0)
            if saved > 0:
                lines.append(f"  - {stage['stage']}: -{saved:,} tokens")
            elif stage.get("output_tokens", 0) > stage.get("input_tokens", 0):
                added = stage["output_tokens"] - stage["input_tokens"]
                lines.append(f"  + {stage['stage']}: +{added:,} tokens (overhead)")
            else:
                lines.append(f"    {stage['stage']}: {stage.get('output_tokens', 0):,} tokens")
        lines.append(f"= Aura total")
        lines.append("```")
        lines.append("")
        lines.append(f"- Total exclusive saved: {report.get('total_exclusive_saved', 0):,}")
        lines.append(f"- Protocol overhead: {report.get('protocol_overhead_tokens', 0):,}")
        lines.append(f"- Repair overhead: {report.get('repair_overhead_tokens', 0):,}")
        return "\n".join(lines)
