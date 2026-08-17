#include "core_pipeline.h"

#include <string.h>

#define B3_CHUNK_START 1u
#define B3_CHUNK_END   2u
#define B3_ROOT        8u

static uint32_t load32_le(const uint8_t *p) {
    return ((uint32_t)p[0]) |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static void store32_le(uint8_t *p, uint32_t x) {
    p[0] = (uint8_t)x;
    p[1] = (uint8_t)(x >> 8);
    p[2] = (uint8_t)(x >> 16);
    p[3] = (uint8_t)(x >> 24);
}

static uint32_t rotr32(uint32_t x, unsigned n) {
    return (x >> n) | (x << (32u - n));
}

static void b3_g(uint32_t s[16], unsigned a, unsigned b, unsigned c, unsigned d, uint32_t mx, uint32_t my) {
    s[a] = s[a] + s[b] + mx;
    s[d] = rotr32(s[d] ^ s[a], 16);
    s[c] = s[c] + s[d];
    s[b] = rotr32(s[b] ^ s[c], 12);
    s[a] = s[a] + s[b] + my;
    s[d] = rotr32(s[d] ^ s[a], 8);
    s[c] = s[c] + s[d];
    s[b] = rotr32(s[b] ^ s[c], 7);
}

static void b3_round(uint32_t s[16], const uint32_t m[16]) {
    b3_g(s, 0, 4, 8, 12, m[0], m[1]);
    b3_g(s, 1, 5, 9, 13, m[2], m[3]);
    b3_g(s, 2, 6, 10, 14, m[4], m[5]);
    b3_g(s, 3, 7, 11, 15, m[6], m[7]);
    b3_g(s, 0, 5, 10, 15, m[8], m[9]);
    b3_g(s, 1, 6, 11, 12, m[10], m[11]);
    b3_g(s, 2, 7, 8, 13, m[12], m[13]);
    b3_g(s, 3, 4, 9, 14, m[14], m[15]);
}

static void b3_permute(uint32_t m[16]) {
    static const uint8_t p[16] = {2, 6, 3, 10, 7, 0, 4, 13, 1, 11, 12, 5, 9, 14, 15, 8};
    uint32_t tmp[16];
    unsigned i;
    for (i = 0; i < 16; ++i) {
        tmp[i] = m[p[i]];
    }
    memcpy(m, tmp, sizeof(tmp));
}

bool aura_blake3_hash_small(const uint8_t *input, size_t len, uint8_t out32[32]) {
    static const uint32_t iv[8] = {
        0x6A09E667u, 0xBB67AE85u, 0x3C6EF372u, 0xA54FF53Au,
        0x510E527Fu, 0x9B05688Cu, 0x1F83D9ABu, 0x5BE0CD19u
    };
    uint8_t block[64] = {0};
    uint32_t m[16];
    uint32_t s[16];
    unsigned r;
    unsigned i;

    if (out32 == NULL || (input == NULL && len != 0u) || len > sizeof(block)) {
        return false;
    }
    if (len != 0u) {
        memcpy(block, input, len);
    }
    for (i = 0; i < 16; ++i) {
        m[i] = load32_le(&block[i * 4u]);
    }
    for (i = 0; i < 8; ++i) {
        s[i] = iv[i];
    }
    s[8] = iv[0];
    s[9] = iv[1];
    s[10] = iv[2];
    s[11] = iv[3];
    s[12] = 0u;
    s[13] = 0u;
    s[14] = (uint32_t)len;
    s[15] = B3_CHUNK_START | B3_CHUNK_END | B3_ROOT;

    for (r = 0; r < 7; ++r) {
        b3_round(s, m);
        if (r != 6u) {
            b3_permute(m);
        }
    }
    for (i = 0; i < 8; ++i) {
        store32_le(&out32[i * 4u], s[i] ^ s[i + 8u]);
    }
    return true;
}

bool aura_state_pack(aura_state128_t *out, const aura_state_fields_t *f) {
    uint64_t lo;
    uint64_t hi;
    uint32_t delay;
    uint64_t seed48 = 0u;
    unsigned i;

    if (out == NULL || f == NULL || f->x_scope > 63u || f->y_lane > 31u || f->z_tier > 31u) {
        return false;
    }
    delay = ((uint32_t)(f->rtt_us[0] > 1023u ? 1023u : f->rtt_us[0])) |
            ((uint32_t)(f->rtt_us[1] > 1023u ? 1023u : f->rtt_us[1]) << 10) |
            ((uint32_t)(f->rtt_us[2] > 1023u ? 1023u : f->rtt_us[2]) << 20);
    for (i = 0; i < AURA_SEED_SLICE_BYTES; ++i) {
        seed48 |= ((uint64_t)f->seed_slice[i]) << (i * 8u);
    }
    lo = ((uint64_t)f->x_scope) |
         ((uint64_t)f->y_lane << 6) |
         ((uint64_t)f->z_tier << 11) |
         ((uint64_t)f->epoch_tick << 16) |
         ((uint64_t)delay << 32);
    hi = ((uint64_t)f->eta_eff_q16) | (seed48 << 16);
    out->value = _mm_set_epi64x((long long)hi, (long long)lo);
    return true;
}

bool aura_state_unpack(const aura_state128_t *state, aura_state_fields_t *out) {
    uint64_t lanes[2];
    uint32_t delay;
    uint64_t seed48;
    unsigned i;

    if (state == NULL || out == NULL) {
        return false;
    }
    _mm_storeu_si128((__m128i *)(void *)lanes, state->value);
    out->x_scope = (uint8_t)(lanes[0] & 0x3fu);
    out->y_lane = (uint8_t)((lanes[0] >> 6) & 0x1fu);
    out->z_tier = (uint8_t)((lanes[0] >> 11) & 0x1fu);
    out->epoch_tick = (uint16_t)((lanes[0] >> 16) & 0xffffu);
    delay = (uint32_t)(lanes[0] >> 32);
    out->rtt_us[0] = (uint16_t)(delay & 0x3ffu);
    out->rtt_us[1] = (uint16_t)((delay >> 10) & 0x3ffu);
    out->rtt_us[2] = (uint16_t)((delay >> 20) & 0x3ffu);
    out->eta_eff_q16 = (uint16_t)(lanes[1] & 0xffffu);
    seed48 = lanes[1] >> 16;
    for (i = 0; i < AURA_SEED_SLICE_BYTES; ++i) {
        out->seed_slice[i] = (uint8_t)(seed48 >> (i * 8u));
    }
    return true;
}

unsigned aura_state_hamming_distance(const aura_state128_t *a, const aura_state128_t *b) {
    __m128i x;
    uint64_t lanes[2];
    if (a == NULL || b == NULL) {
        return 129u;
    }
    x = _mm_xor_si128(a->value, b->value);
    _mm_storeu_si128((__m128i *)(void *)lanes, x);
    return (unsigned)__builtin_popcountll(lanes[0]) + (unsigned)__builtin_popcountll(lanes[1]);
}

bool aura_stage_step_valid(uint8_t current_stage, uint8_t next_stage) {
    if (current_stage < AURA_STAGE_MIN || current_stage > AURA_STAGE_MAX ||
        next_stage < AURA_STAGE_MIN || next_stage > AURA_STAGE_MAX) {
        return false;
    }
    return next_stage == (uint8_t)((current_stage % AURA_STAGE_MAX) + 1u);
}

aura_invariant_status_t aura_pipeline_check_transition(
    const aura_state128_t *current,
    const aura_state128_t *next,
    uint8_t current_stage,
    uint8_t next_stage
) {
    return aura_pipeline_check_transition_fast(current, next, current_stage, next_stage);
}

bool aura_pipeline_derive_seed(
    const uint8_t residual_digest[AURA_RESIDUAL_DIGEST_BYTES],
    const uint32_t mesh_rtt_us[AURA_MESH_RTT_COUNT],
    const uint8_t omega_coord[AURA_COORD_BYTES],
    uint8_t out_seed32[32]
) {
    uint8_t input[AURA_RESIDUAL_DIGEST_BYTES + AURA_MESH_RTT_COUNT * 4u + AURA_COORD_BYTES];
    size_t off = 0u;
    unsigned i;
    if (residual_digest == NULL || mesh_rtt_us == NULL || omega_coord == NULL || out_seed32 == NULL) {
        return false;
    }
    memcpy(&input[off], residual_digest, AURA_RESIDUAL_DIGEST_BYTES);
    off += AURA_RESIDUAL_DIGEST_BYTES;
    for (i = 0; i < AURA_MESH_RTT_COUNT; ++i) {
        store32_le(&input[off], mesh_rtt_us[i]);
        off += 4u;
    }
    memcpy(&input[off], omega_coord, AURA_COORD_BYTES);
    off += AURA_COORD_BYTES;
    return aura_blake3_hash_small(input, off, out_seed32);
}
