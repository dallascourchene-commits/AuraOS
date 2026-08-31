from __future__ import annotations

import random
import unittest

from tools.k27_xhdv_riscv_candidate_falsifier import (
    CUSTOM_0,
    MASK64,
    XhdvError,
    aligned_i_type_displacements,
    bind,
    decode_r,
    disposition,
    encode_r,
    hdist,
    pasted_scan_falsifier,
    perm,
    popcnt,
)


class XhdvCandidateFalsifierTests(unittest.TestCase):
    def test_custom0_and_r_encoding_roundtrip(self):
        self.assertEqual(CUSTOM_0, 0x0B)
        word = encode_r(funct7=0x55, rs2=31, rs1=17, funct3=7, rd=9)
        self.assertEqual(decode_r(word), {"funct7": 0x55, "rs2": 31, "rs1": 17, "funct3": 7, "rd": 9, "opcode": 0x0B})

    def test_register_fields_are_strict_five_bit_ids(self):
        with self.assertRaises(XhdvError):
            encode_r(funct7=0, rs2=32, rs1=0, funct3=0, rd=0)
        with self.assertRaises(XhdvError):
            encode_r(funct7=0, rs2=True, rs1=0, funct3=0, rd=0)

    def test_bind_is_exact_xor_and_hamming_extrema_fit_11_bits(self):
        zeros = tuple([0] * 16)
        ones = tuple([MASK64] * 16)
        self.assertEqual(bind(zeros, ones), ones)
        self.assertEqual(popcnt(ones), 1024)
        self.assertEqual(hdist(zeros, ones), 1024)
        self.assertLess(1024, 1 << 11)

    def test_rotate_roundtrip_edge_and_random_shifts(self):
        rng = random.Random(0xA17A)
        for _ in range(64):
            vector = tuple(rng.getrandbits(64) for _ in range(16))
            for shift in (0, 1, 63, 64, 65, 127, 128, 511, 512, 1023, rng.randrange(1024)):
                self.assertEqual(perm(perm(vector, shift), -shift), vector)

    def test_i_type_128byte_alignment_has_only_32_direct_displacements(self):
        displacements = aligned_i_type_displacements()
        self.assertEqual(len(displacements), 32)
        self.assertEqual(displacements[0], -2048)
        self.assertEqual(displacements[-1], 1920)
        self.assertTrue(all(value % 128 == 0 for value in displacements))

    def test_pasted_dataset_recovers_target_but_threshold_rejects_nothing(self):
        scan = pasted_scan_falsifier()
        self.assertEqual(scan["minimum_index"], 777_777)
        self.assertEqual(scan["minimum_distance"], 4)
        self.assertEqual(scan["vectors_below_threshold"], 1_000_000)

    def test_pasted_threshold_is_not_discriminative(self):
        self.assertFalse(disposition().pasted_threshold_discriminative)

    def test_shown_inline_asm_does_not_establish_hidden_h_register_abi(self):
        result = disposition()
        self.assertFalse(result.hidden_h_register_file_modeled_by_shown_gnu_insn)
        self.assertFalse(result.shown_inline_asm_compiler_sound_for_hidden_h_registers)

    def test_supplied_alu_is_not_the_claimed_six_instruction_architecture(self):
        result = disposition()
        self.assertFalse(result.rtl_hidden_h_register_file_implemented)
        self.assertFalse(result.rtl_hdv_load_store_implemented)
        self.assertFalse(result.rtl_decode_and_hazards_integrated)
        self.assertFalse(result.full_six_instruction_isa_implemented)

    def test_architectural_state_and_128byte_memory_semantics_are_unowned(self):
        result = disposition()
        self.assertFalse(result.architectural_context_switch_semantics_defined)
        self.assertFalse(result.debugger_and_abi_state_defined)
        self.assertFalse(result.precise_128byte_memory_exception_semantics_defined)
        self.assertFalse(result.memory_alignment_trap_semantics_defined)

    def test_rtl_and_two_cycle_timing_remain_unproven(self):
        result = disposition()
        self.assertFalse(result.rtl_synthesized)
        self.assertFalse(result.rtl_timing_closed)
        self.assertFalse(result.two_cycle_popcount_latency_proven)

    def test_performance_and_k27_authority_remain_false(self):
        result = disposition()
        self.assertFalse(result.pasted_scan_is_parallel_hardware_evidence)
        self.assertFalse(result.hardware_speedup_proven)
        self.assertFalse(result.semantic_k27_authority)


if __name__ == "__main__":
    unittest.main()
