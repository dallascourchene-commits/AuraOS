#include "crypto_core.h"

#include <immintrin.h>
#include <openssl/evp.h>
#include <string.h>

static EVP_PKEY *as_pkey(const aura_mlkem768_keypair_t *keypair) {
    return keypair == NULL ? NULL : (EVP_PKEY *)keypair->provider_key;
}

aura_crypto_status_t aura_mlkem768_keygen(aura_mlkem768_keypair_t *keypair) {
    EVP_PKEY *pkey;
    if (keypair == NULL) {
        return AURA_CRYPTO_INVALID;
    }
    keypair->provider_key = NULL;
    pkey = EVP_PKEY_Q_keygen(NULL, NULL, "ML-KEM-768");
    if (pkey == NULL) {
        return AURA_CRYPTO_UNSUPPORTED;
    }
    keypair->provider_key = pkey;
    return AURA_CRYPTO_OK;
}

aura_crypto_status_t aura_mlkem768_encaps(
    const aura_mlkem768_keypair_t *keypair,
    uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
    uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]
) {
    EVP_PKEY *pkey = as_pkey(keypair);
    EVP_PKEY_CTX *ctx;
    size_t ct_len = AURA_MLKEM768_CIPHERTEXT_BYTES;
    size_t ss_len = AURA_MLKEM768_SHARED_SECRET_BYTES;
    int ok;
    if (pkey == NULL || ciphertext == NULL || shared_secret == NULL) {
        return AURA_CRYPTO_INVALID;
    }
    ctx = EVP_PKEY_CTX_new_from_pkey(NULL, pkey, NULL);
    if (ctx == NULL) {
        return AURA_CRYPTO_BACKEND_ERROR;
    }
    ok = EVP_PKEY_encapsulate_init(ctx, NULL) > 0 &&
         EVP_PKEY_encapsulate(ctx, ciphertext, &ct_len, shared_secret, &ss_len) > 0 &&
         ct_len == AURA_MLKEM768_CIPHERTEXT_BYTES &&
         ss_len == AURA_MLKEM768_SHARED_SECRET_BYTES;
    EVP_PKEY_CTX_free(ctx);
    return ok ? AURA_CRYPTO_OK : AURA_CRYPTO_BACKEND_ERROR;
}

aura_crypto_status_t aura_mlkem768_decaps(
    const aura_mlkem768_keypair_t *keypair,
    const uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
    uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]
) {
    EVP_PKEY *pkey = as_pkey(keypair);
    EVP_PKEY_CTX *ctx;
    size_t ss_len = AURA_MLKEM768_SHARED_SECRET_BYTES;
    int ok;
    if (pkey == NULL || ciphertext == NULL || shared_secret == NULL) {
        return AURA_CRYPTO_INVALID;
    }
    ctx = EVP_PKEY_CTX_new_from_pkey(NULL, pkey, NULL);
    if (ctx == NULL) {
        return AURA_CRYPTO_BACKEND_ERROR;
    }
    ok = EVP_PKEY_decapsulate_init(ctx, NULL) > 0 &&
         EVP_PKEY_decapsulate(ctx, shared_secret, &ss_len, ciphertext, AURA_MLKEM768_CIPHERTEXT_BYTES) > 0 &&
         ss_len == AURA_MLKEM768_SHARED_SECRET_BYTES;
    EVP_PKEY_CTX_free(ctx);
    return ok ? AURA_CRYPTO_OK : AURA_CRYPTO_BACKEND_ERROR;
}

void aura_mlkem768_keypair_free(aura_mlkem768_keypair_t *keypair) {
    if (keypair != NULL && keypair->provider_key != NULL) {
        EVP_PKEY_free((EVP_PKEY *)keypair->provider_key);
        keypair->provider_key = NULL;
    }
}

static inline __m256 swap_complex_pairs(__m256 x) {
    return _mm256_permute_ps(x, 0xB1);
}

static inline __m256 complex_mul4(__m256 m, __m256 k) {
    const __m256 sign = _mm256_castsi256_ps(_mm256_set_epi32(
        0, (int)0x80000000u, 0, (int)0x80000000u,
        0, (int)0x80000000u, 0, (int)0x80000000u));
    __m256 k_re = _mm256_moveldup_ps(k);
    __m256 k_im = _mm256_movehdup_ps(k);
    __m256 m_sw = swap_complex_pairs(m);
    __m256 cross = _mm256_mul_ps(m_sw, k_im);
    cross = _mm256_xor_ps(cross, sign);
    return _mm256_add_ps(_mm256_mul_ps(m, k_re), cross);
}

static inline __m256 complex_mul_conj4(__m256 m, __m256 k) {
    const __m256 conj_mask = _mm256_castsi256_ps(_mm256_set_epi32(
        (int)0x80000000u, 0, (int)0x80000000u, 0,
        (int)0x80000000u, 0, (int)0x80000000u, 0));
    return complex_mul4(m, _mm256_xor_ps(k, conj_mask));
}

bool aura_hdc_bind(const float *message, const float *key, const uint32_t *pad, uint32_t *cipher) {
    size_t i;
    if (message == NULL || key == NULL || pad == NULL || cipher == NULL) {
        return false;
    }
    for (i = 0; i < AURA_HDC_SCALARS; i += 8u) {
        __m256 m = _mm256_loadu_ps(&message[i]);
        __m256 k = _mm256_loadu_ps(&key[i]);
        __m256 bound = complex_mul4(m, k);
        __m256i bits = _mm256_castps_si256(bound);
        __m256i p = _mm256_loadu_si256((const __m256i *)(const void *)&pad[i]);
        _mm256_storeu_si256((__m256i *)(void *)&cipher[i], _mm256_xor_si256(bits, p));
    }
    return true;
}

bool aura_hdc_unbind(const uint32_t *cipher, const float *key, const uint32_t *pad, float *out) {
    size_t i;
    if (cipher == NULL || key == NULL || pad == NULL || out == NULL) {
        return false;
    }
    for (i = 0; i < AURA_HDC_SCALARS; i += 8u) {
        __m256i c = _mm256_loadu_si256((const __m256i *)(const void *)&cipher[i]);
        __m256i p = _mm256_loadu_si256((const __m256i *)(const void *)&pad[i]);
        __m256 bound = _mm256_castsi256_ps(_mm256_xor_si256(c, p));
        __m256 k = _mm256_loadu_ps(&key[i]);
        _mm256_storeu_ps(&out[i], complex_mul_conj4(bound, k));
    }
    return true;
}

void aura_secure_bzero(void *ptr, size_t len) {
    volatile uint8_t *p = (volatile uint8_t *)ptr;
    if (p == NULL) {
        return;
    }
    while (len-- != 0u) {
        *p++ = 0u;
    }
    __asm__ __volatile__("" ::: "memory");
}

bool aura_buffer_is_zero(const void *ptr, size_t len) {
    const uint8_t *p = (const uint8_t *)ptr;
    uint8_t acc = 0u;
    size_t i;
    if (p == NULL && len != 0u) {
        return false;
    }
    for (i = 0; i < len; ++i) {
        acc |= p[i];
    }
    return acc == 0u;
}
