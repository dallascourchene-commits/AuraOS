"""Executable falsifier/rebase for the supplied Xhdv 1024-bit RISC-V proposal.

This module validates encoding math and functional HDV operations while keeping
compiler integration, architectural state, RTL integration/synthesis/timing,
hardware performance and semantic K27 authority explicitly unproven.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

SCHEMA = "AuraK27XhdvRiscvCandidateFalsifierV1"
SOURCE_SHA256 = "98bc8189027158a2cfbc0cb8eaf443836dd9e6ec125ac3fcadaeee9bcc8ba412"
CUSTOM_0 = 0x0B
MASK64 = (1 << 64) - 1
MASK1024 = (1 << 1024) - 1
HDV_BYTES = 128
I_IMMEDIATE_MIN = -(1 << 11)
I_IMMEDIATE_MAX = (1 << 11) - 1


class XhdvError(ValueError):
    pass


def _strict_u5(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value < 32:
        raise XhdvError(f"{name}_OUT_OF_RANGE")
    return value


def _strict_u3(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value < 8:
        raise XhdvError(f"{name}_OUT_OF_RANGE")
    return value


def _strict_u7(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value < 128:
        raise XhdvError(f"{name}_OUT_OF_RANGE")
    return value


def encode_r(*, funct7: int, rs2: int, rs1: int, funct3: int, rd: int, opcode: int = CUSTOM_0) -> int:
    _strict_u7("FUNCT7", funct7)
    _strict_u5("RS2", rs2)
    _strict_u5("RS1", rs1)
    _strict_u3("FUNCT3", funct3)
    _strict_u5("RD", rd)
    if type(opcode) is not int or not 0 <= opcode < 128:
        raise XhdvError("OPCODE_OUT_OF_RANGE")
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def decode_r(word: int) -> dict[str, int]:
    if type(word) is not int or not 0 <= word < (1 << 32):
        raise XhdvError("WORD_OUT_OF_RANGE")
    return {
        "funct7": (word >> 25) & 0x7F,
        "rs2": (word >> 20) & 0x1F,
        "rs1": (word >> 15) & 0x1F,
        "funct3": (word >> 12) & 0x7,
        "rd": (word >> 7) & 0x1F,
        "opcode": word & 0x7F,
    }


def aligned_i_type_displacements() -> tuple[int, ...]:
    """All 128-byte-aligned byte displacements representable by signed I-immediate."""
    return tuple(range(I_IMMEDIATE_MIN, I_IMMEDIATE_MAX + 1, HDV_BYTES))


def _words(value: tuple[int, ...]) -> tuple[int, ...]:
    if type(value) is not tuple or len(value) != 16:
        raise XhdvError("HDV1024_REQUIRES_16_U64_WORDS")
    for word in value:
        if type(word) is not int or not 0 <= word <= MASK64:
            raise XhdvError("HDV_WORD_OUT_OF_RANGE")
    return value


def bind(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    a = _words(a)
    b = _words(b)
    return tuple(x ^ y for x, y in zip(a, b))


def popcnt(a: tuple[int, ...]) -> int:
    return sum(word.bit_count() for word in _words(a))


def hdist(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return popcnt(bind(a, b))


def _to_int(a: tuple[int, ...]) -> int:
    return sum(word << (64 * i) for i, word in enumerate(_words(a)))


def _from_int(value: int) -> tuple[int, ...]:
    value &= MASK1024
    return tuple((value >> (64 * i)) & MASK64 for i in range(16))


def perm(a: tuple[int, ...], shift: int) -> tuple[int, ...]:
    a = _words(a)
    if type(shift) is not int:
        raise XhdvError("SHIFT_MUST_BE_INTEGER")
    shift %= 1024
    if shift == 0:
        return a
    value = _to_int(a)
    return _from_int(((value << shift) | (value >> (1024 - shift))) & MASK1024)


def pasted_centroid_word(index: int) -> int:
    if type(index) is not int or not 0 <= index < 1_000_000:
        raise XhdvError("CENTROID_INDEX_OUT_OF_RANGE")
    return (0xAAAAAAAAAAAAAAAA ^ ((index * 17) & MASK64)) & MASK64


def pasted_scan_falsifier(*, target_index: int = 777_777, threshold: int = 400) -> dict[str, int]:
    """Replay the pasted emulator's exact structured dataset without allocating 128 MB."""
    if type(threshold) is not int or not 0 <= threshold <= 1024:
        raise XhdvError("THRESHOLD_OUT_OF_RANGE")
    target_word = pasted_centroid_word(target_index)
    query_word0 = target_word ^ 0xF
    minimum = 1025
    minimum_index = -1
    below = 0
    for index in range(1_000_000):
        word = pasted_centroid_word(index)
        base = (target_word ^ word).bit_count()
        distance = (query_word0 ^ word).bit_count() + 15 * base
        if distance < threshold:
            below += 1
        if distance < minimum:
            minimum = distance
            minimum_index = index
    return {
        "minimum_distance": minimum,
        "minimum_index": minimum_index,
        "vectors_below_threshold": below,
        "vector_count": 1_000_000,
    }


@dataclass(frozen=True)
class XhdvCandidateDisposition:
    source_sha256: str
    custom_0_opcode_valid: bool
    r_type_encoding_roundtrip_proven: bool
    xor_binding_functional: bool
    rotate_functional: bool
    popcount_hamming_functional: bool
    eleven_bit_distance_width_sufficient: bool
    i_type_aligned_displacement_count: int
    i_type_aligned_min_displacement: int
    i_type_aligned_max_displacement: int
    pasted_emulator_target_recovered: bool
    pasted_threshold_discriminative: bool
    pasted_scan_is_parallel_hardware_evidence: bool
    hidden_h_register_file_modeled_by_shown_gnu_insn: bool
    shown_inline_asm_compiler_sound_for_hidden_h_registers: bool
    rtl_hidden_h_register_file_implemented: bool
    rtl_hdv_load_store_implemented: bool
    rtl_decode_and_hazards_integrated: bool
    architectural_context_switch_semantics_defined: bool
    debugger_and_abi_state_defined: bool
    precise_128byte_memory_exception_semantics_defined: bool
    full_six_instruction_isa_implemented: bool
    rtl_synthesized: bool
    rtl_timing_closed: bool
    two_cycle_popcount_latency_proven: bool
    memory_alignment_trap_semantics_defined: bool
    hardware_speedup_proven: bool
    semantic_k27_authority: bool
    recommended_v0: str
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(payload).hexdigest()


def disposition() -> XhdvCandidateDisposition:
    a = tuple(((0x0123456789ABCDEF + i * 0x1111111111111111) & MASK64) for i in range(16))
    b = tuple(((0xFEDCBA9876543210 ^ (i * 0x0101010101010101)) & MASK64) for i in range(16))
    encoded = encode_r(funct7=0, rs2=7, rs1=5, funct3=2, rd=3)
    scan = pasted_scan_falsifier()
    displacements = aligned_i_type_displacements()
    return XhdvCandidateDisposition(
        source_sha256=SOURCE_SHA256,
        custom_0_opcode_valid=(CUSTOM_0 == 0x0B),
        r_type_encoding_roundtrip_proven=(decode_r(encoded) == {"funct7": 0, "rs2": 7, "rs1": 5, "funct3": 2, "rd": 3, "opcode": CUSTOM_0}),
        xor_binding_functional=(bind(a, b) == tuple(x ^ y for x, y in zip(a, b))),
        rotate_functional=(perm(a, 0) == a and perm(perm(a, 1), 1023) == a and perm(a, 64)[1] == a[0]),
        popcount_hamming_functional=(hdist(a, a) == 0 and hdist(tuple([0] * 16), tuple([MASK64] * 16)) == 1024),
        eleven_bit_distance_width_sufficient=(1024 < (1 << 11)),
        i_type_aligned_displacement_count=len(displacements),
        i_type_aligned_min_displacement=displacements[0],
        i_type_aligned_max_displacement=displacements[-1],
        pasted_emulator_target_recovered=(scan["minimum_index"] == 777_777 and scan["minimum_distance"] == 4),
        pasted_threshold_discriminative=(scan["vectors_below_threshold"] < scan["vector_count"]),
        pasted_scan_is_parallel_hardware_evidence=False,
        hidden_h_register_file_modeled_by_shown_gnu_insn=False,
        shown_inline_asm_compiler_sound_for_hidden_h_registers=False,
        rtl_hidden_h_register_file_implemented=False,
        rtl_hdv_load_store_implemented=False,
        rtl_decode_and_hazards_integrated=False,
        architectural_context_switch_semantics_defined=False,
        debugger_and_abi_state_defined=False,
        precise_128byte_memory_exception_semantics_defined=False,
        full_six_instruction_isa_implemented=False,
        rtl_synthesized=False,
        rtl_timing_closed=False,
        two_cycle_popcount_latency_proven=False,
        memory_alignment_trap_semantics_defined=False,
        hardware_speedup_proven=False,
        semantic_k27_authority=False,
        recommended_v0=(
            "Keep CUSTOM_0 + exact 1024-bit XOR/rotate/Hamming semantics as a golden functional reference. "
            "Treat h0-h31, hdv.ld/st, decode/hazards, context-switch/debugger state and precise 128-byte memory behavior as unimplemented ISA/toolchain contracts. "
            "For first hardware bring-up, prefer a compiler-visible pointer-based hdist primitive; add architectural HDV registers only after assembler/compiler/simulator/OS ABI ownership exists."
        ),
    )


def main() -> None:
    result = disposition()
    print(json.dumps(result.to_dict() | {"receipt_digest": result.digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
