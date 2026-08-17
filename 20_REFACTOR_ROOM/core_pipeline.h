#ifndef AURA_CORE_PIPELINE_H
#define AURA_CORE_PIPELINE_H

#include <immintrin.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AURA_STAGE_MIN 1u
#define AURA_STAGE_MAX 10u
#define AURA_ETA_Q16_MIN_095 62259u
#define AURA_SEED_SLICE_BYTES 6u
#define AURA_COORD_BYTES 16u
#define AURA_RESIDUAL_DIGEST_BYTES 32u
#define AURA_MESH_RTT_COUNT 3u

typedef struct {
    __m128i value;
} aura_state128_t;

typedef struct {
    uint8_t x_scope;
    uint8_t y_lane;
    uint8_t z_tier;
    uint16_t epoch_tick;
    uint16_t rtt_us[3];
    uint16_t eta_eff_q16;
    uint8_t seed_slice[6];
} aura_state_fields_t;

typedef enum {
    AURA_INV_PASS = 0,
    AURA_INV_FAIL_HAMMING = 1,
    AURA_INV_FAIL_STAGE = 2,
    AURA_INV_FAIL_EFFICIENCY = 3,
    AURA_INV_FAIL_ARGUMENT = 4
} aura_invariant_status_t;

bool aura_state_pack(aura_state128_t *out, const aura_state_fields_t *fields);
bool aura_state_unpack(const aura_state128_t *state, aura_state_fields_t *out);
unsigned aura_state_hamming_distance(const aura_state128_t *a, const aura_state128_t *b);
bool aura_stage_step_valid(uint8_t current_stage, uint8_t next_stage);
static inline aura_invariant_status_t aura_pipeline_check_transition_fast(
    const aura_state128_t *current,
    const aura_state128_t *next,
    uint8_t current_stage,
    uint8_t next_stage
) {
    __m128i x;
    uint64_t lo;
    uint64_t hi;
    uint64_t changed;
    uint16_t eta;
    if (current == NULL || next == NULL) {
        return AURA_INV_FAIL_ARGUMENT;
    }
    x = _mm_xor_si128(current->value, next->value);
    lo = (uint64_t)_mm_cvtsi128_si64(x);
    hi = (uint64_t)_mm_extract_epi64(x, 1);
    if (lo != 0u && hi != 0u) {
        return AURA_INV_FAIL_HAMMING;
    }
    changed = lo | hi;
    if (changed == 0u || (changed & (changed - 1u)) != 0u) {
        return AURA_INV_FAIL_HAMMING;
    }
    if (current_stage < AURA_STAGE_MIN || current_stage > AURA_STAGE_MAX ||
        next_stage != (uint8_t)((current_stage % AURA_STAGE_MAX) + 1u)) {
        return AURA_INV_FAIL_STAGE;
    }
    hi = (uint64_t)_mm_extract_epi64(next->value, 1);
    eta = (uint16_t)(hi & 0xffffu);
    if (eta < AURA_ETA_Q16_MIN_095) {
        return AURA_INV_FAIL_EFFICIENCY;
    }
    return AURA_INV_PASS;
}

aura_invariant_status_t aura_pipeline_check_transition(
    const aura_state128_t *current,
    const aura_state128_t *next,
    uint8_t current_stage,
    uint8_t next_stage
);

bool aura_blake3_hash_small(const uint8_t *input, size_t len, uint8_t out32[32]);

bool aura_pipeline_derive_seed(
    const uint8_t residual_digest[AURA_RESIDUAL_DIGEST_BYTES],
    const uint32_t mesh_rtt_us[AURA_MESH_RTT_COUNT],
    const uint8_t omega_coord[AURA_COORD_BYTES],
    uint8_t out_seed32[32]
);

#ifdef __cplusplus
}
#endif

#endif
