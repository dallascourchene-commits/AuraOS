#define _POSIX_C_SOURCE 200809L
#include "core_pipeline.h"
#include "crypto_core.h"
#include "mesh_adapter.h"

#include <immintrin.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define ITER_INV 5000000u
#define ITER_HDC 2000u
#define ITER_EPOCH 200000u
#define FUZZ_CASES 100000u

static uint64_t nsec_now(void) {
    struct timespec ts;
    (void)clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * UINT64_C(1000000000) + (uint64_t)ts.tv_nsec;
}

static uint64_t tsc_now(void) {
    unsigned aux;
    _mm_lfence();
    return __rdtscp(&aux);
}

static uint64_t splitmix64(uint64_t *s) {
    uint64_t z = (*s += UINT64_C(0x9e3779b97f4a7c15));
    z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
    return z ^ (z >> 31);
}

static bool hex_eq(const uint8_t hash[32], const char *hex) {
    static const char digits[] = "0123456789abcdef";
    size_t i;
    for (i = 0; i < 32u; ++i) {
        if (digits[hash[i] >> 4] != hex[2u * i] || digits[hash[i] & 15u] != hex[2u * i + 1u]) {
            return false;
        }
    }
    return true;
}

int main(void) {
    aura_state_fields_t f = {0};
    aura_state128_t a;
    aura_state128_t b;
    aura_state128_t valid_next[128];
    uint64_t t0;
    uint64_t t1;
    double bm01_ns;
    double bm02_cpb;
    double bm03_us;
    bool bm04;
    bool bm05;
    bool bm06;
    bool hdc_roundtrip;
    double hdc_max_abs_error = 0.0;
    bool blake3_vectors;
    bool mlkem_roundtrip;
    aura_mlkem768_keypair_t mlkem_key = {0};
    uint8_t mlkem_ct[AURA_MLKEM768_CIPHERTEXT_BYTES];
    uint8_t mlkem_ss1[AURA_MLKEM768_SHARED_SECRET_BYTES];
    uint8_t mlkem_ss2[AURA_MLKEM768_SHARED_SECRET_BYTES];
    uint64_t seed = UINT64_C(0x123456789abcdef0);
    static float message[AURA_HDC_SCALARS];
    static float key[AURA_HDC_SCALARS];
    static float recovered[AURA_HDC_SCALARS];
    static uint32_t pad[AURA_HDC_SCALARS];
    static uint32_t cipher[AURA_HDC_SCALARS];
    uint8_t residual[32] = {0};
    uint8_t omega[16] = {0};
    uint32_t rtt[3] = {100u, 120u, 180u};
    uint8_t out_seed[32];
    uint8_t hash[32];
    aura_mesh_rtt_monitor_t mon;
    aura_mesh_snapshot_t snap;
    unsigned i;
    unsigned failures = 0u;
    volatile aura_invariant_status_t sink = AURA_INV_PASS;
    volatile uint8_t seed_sink = 0u;

    f.x_scope = 1u;
    f.y_lane = 2u;
    f.z_tier = 3u;
    f.epoch_tick = 7u;
    f.rtt_us[0] = 10u;
    f.rtt_us[1] = 20u;
    f.rtt_us[2] = 25u;
    f.eta_eff_q16 = 65535u;
    (void)aura_state_pack(&a, &f);
    b = a;
    b.value = _mm_xor_si128(b.value, _mm_set_epi64x(0, 1));
    for (i = 0; i < 128u; ++i) {
        uint64_t lanes[2];
        _mm_storeu_si128((__m128i *)(void *)lanes, a.value);
        lanes[i >> 6] ^= UINT64_C(1) << (i & 63u);
        valid_next[i].value = _mm_loadu_si128((const __m128i *)(const void *)lanes);
    }

    blake3_vectors = aura_blake3_hash_small(NULL, 0u, hash) &&
        hex_eq(hash, "af1349b9f5f9a1a6a0404dea36dcc9499bcb25c9adc112b7cc9a93cae41f3262");
    blake3_vectors = blake3_vectors && aura_blake3_hash_small((const uint8_t *)"abc", 3u, hash) &&
        hex_eq(hash, "6437b3ac38465133ffb63b75273a8db548c558465d79db03fd359c6cd5bd9d85");

    t0 = nsec_now();
    for (i = 0; i < ITER_INV; ++i) {
        sink = aura_pipeline_check_transition_fast(&a, &valid_next[i & 127u], 1u, 2u);
    }
    t1 = nsec_now();
    bm01_ns = (double)(t1 - t0) / (double)ITER_INV;

    for (i = 0; i < AURA_HDC_DIM; ++i) {
        const float theta = (float)(i % 1024u) * 0.006135923151542565f;
        message[2u * i] = (float)((int)(i % 97u) - 48) / 64.0f;
        message[2u * i + 1u] = (float)((int)(i % 89u) - 44) / 64.0f;
        key[2u * i] = cosf(theta);
        key[2u * i + 1u] = sinf(theta);
        pad[2u * i] = (uint32_t)splitmix64(&seed);
        pad[2u * i + 1u] = (uint32_t)splitmix64(&seed);
    }

    t0 = tsc_now();
    for (i = 0; i < ITER_HDC; ++i) {
        (void)aura_hdc_bind(message, key, pad, cipher);
        (void)aura_hdc_unbind(cipher, key, pad, recovered);
    }
    t1 = tsc_now();
    bm02_cpb = (double)(t1 - t0) / ((double)ITER_HDC * 2.0 * (double)(AURA_HDC_SCALARS * sizeof(float)));
    for (i = 0; i < AURA_HDC_SCALARS; ++i) {
        double err = fabs((double)recovered[i] - (double)message[i]);
        if (err > hdc_max_abs_error) {
            hdc_max_abs_error = err;
        }
    }
    hdc_roundtrip = hdc_max_abs_error < 1.0e-5;

    t0 = nsec_now();
    for (i = 0; i < ITER_EPOCH; ++i) {
        rtt[0] = 100u + (i & 7u);
        (void)aura_pipeline_derive_seed(residual, rtt, omega, out_seed);
        seed_sink ^= out_seed[0];
    }
    t1 = nsec_now();
    bm03_us = ((double)(t1 - t0) / (double)ITER_EPOCH) / 1000.0;

    aura_mesh_init(&mon);
    for (i = 0; i < AURA_MESH_WINDOW; ++i) {
        uint32_t jitter = (i % 3u) * 10000u;
        (void)aura_mesh_push(&mon, 10000u + jitter, 12000u + jitter, 20000u + jitter);
    }
    bm04 = aura_mesh_snapshot(&mon, &snap) && snap.triangle_consistent &&
           snap.median_ab_us >= 10000u && snap.median_ab_us <= 60000u;

    for (i = 0; i < FUZZ_CASES; ++i) {
        aura_state128_t mutant = a;
        uint64_t bits[2];
        unsigned bit1 = (unsigned)(splitmix64(&seed) & 127u);
        unsigned bit2 = (unsigned)(splitmix64(&seed) & 127u);
        while (bit2 == bit1) {
            bit2 = (unsigned)(splitmix64(&seed) & 127u);
        }
        _mm_storeu_si128((__m128i *)(void *)bits, mutant.value);
        bits[bit1 >> 6] ^= UINT64_C(1) << (bit1 & 63u);
        bits[bit2 >> 6] ^= UINT64_C(1) << (bit2 & 63u);
        mutant.value = _mm_loadu_si128((const __m128i *)(const void *)bits);
        if (aura_pipeline_check_transition_fast(&a, &mutant, 1u, 2u) == AURA_INV_PASS) {
            ++failures;
        }
    }
    f.eta_eff_q16 = 60000u;
    (void)aura_state_pack(&b, &f);
    if (aura_pipeline_check_transition(&a, &b, 1u, 2u) == AURA_INV_PASS) {
        ++failures;
    }
    if (aura_pipeline_check_transition(&a, &a, 1u, 3u) == AURA_INV_PASS) {
        ++failures;
    }
    bm05 = failures == 0u;

    memset(out_seed, 0xA5, sizeof(out_seed));
    memset(key, 0x5A, sizeof(key));
    aura_secure_bzero(out_seed, sizeof(out_seed));
    aura_secure_bzero(key, sizeof(key));
    bm06 = aura_buffer_is_zero(out_seed, sizeof(out_seed)) && aura_buffer_is_zero(key, sizeof(key));

    mlkem_roundtrip = aura_mlkem768_keygen(&mlkem_key) == AURA_CRYPTO_OK &&
        aura_mlkem768_encaps(&mlkem_key, mlkem_ct, mlkem_ss1) == AURA_CRYPTO_OK &&
        aura_mlkem768_decaps(&mlkem_key, mlkem_ct, mlkem_ss2) == AURA_CRYPTO_OK &&
        memcmp(mlkem_ss1, mlkem_ss2, sizeof(mlkem_ss1)) == 0;
    aura_mlkem768_keypair_free(&mlkem_key);
    aura_secure_bzero(mlkem_ss1, sizeof(mlkem_ss1));
    aura_secure_bzero(mlkem_ss2, sizeof(mlkem_ss2));

    if (sink == (aura_invariant_status_t)255 || seed_sink == 255u) {
        fputs("unreachable\n", stderr);
    }

    printf("{\n");
    printf("  \"work_order_id\": \"WO-AURA-PQ-AMTD-006\",\n");
    printf("  \"claim_ceiling\": \"Local staging benchmark; OpenSSL default-provider ML-KEM-768 conforms to FIPS 203 but no CMVP/FIPS-provider validation is claimed; BM-06 verifies designated buffers only, not caches/registers/physical remanence\",\n");
    printf("  \"compile_flags\": \"gcc -O3 -march=native -Wall -Werror\",\n");
    printf("  \"blake3_short_vectors\": {\"pass\": %s},\n", blake3_vectors ? "true" : "false");
    printf("  \"ml_kem_768\": {\"provider\": \"OpenSSL-3.5-default\", \"fips203_conforming_algorithm\": true, \"cmvp_validated_provider_claimed\": false, \"roundtrip_pass\": %s},\n", mlkem_roundtrip ? "true" : "false");
    printf("  \"BM-01\": {\"value_ns\": %.6f, \"threshold_ns\": 1.5, \"pass\": %s},\n", bm01_ns, bm01_ns < 1.5 ? "true" : "false");
    printf("  \"BM-02\": {\"value_cycles_per_byte\": %.6f, \"threshold_cycles_per_byte\": 1.2, \"roundtrip_max_abs_error\": %.9g, \"roundtrip_pass\": %s, \"pass\": %s},\n", bm02_cpb, hdc_max_abs_error, hdc_roundtrip ? "true" : "false", (bm02_cpb <= 1.2 && hdc_roundtrip) ? "true" : "false");
    printf("  \"BM-03\": {\"value_us\": %.6f, \"threshold_us\": 2.5, \"pass\": %s},\n", bm03_us, bm03_us < 2.5 ? "true" : "false");
    printf("  \"BM-04\": {\"synthetic_jitter_window_ms\": 50, \"triangle_consistent\": %s, \"pass\": %s},\n", snap.triangle_consistent ? "true" : "false", bm04 ? "true" : "false");
    printf("  \"BM-05\": {\"fuzz_cases\": %u, \"unsafe_passes\": %u, \"pass\": %s},\n", FUZZ_CASES + 2u, failures, bm05 ? "true" : "false");
    printf("  \"BM-06\": {\"scope\": \"designated_key_buffers_after_aura_secure_bzero\", \"pass\": %s}\n", bm06 ? "true" : "false");
    printf("}\n");

    return (blake3_vectors && mlkem_roundtrip && hdc_roundtrip && bm05 && bm06) ? 0 : 1;
}
