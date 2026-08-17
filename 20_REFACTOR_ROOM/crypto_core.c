#define _DEFAULT_SOURCE 1
#include "crypto_core.h"

#include <limits.h>
#include <string.h>
#include <openssl/crypto.h>
#include <openssl/opensslv.h>

#if defined(__AVX2__)
#include <immintrin.h>
#endif

#if OPENSSL_VERSION_MAJOR < 3 || \
    (OPENSSL_VERSION_MAJOR == 3 && OPENSSL_VERSION_MINOR < 5)
#error "crypto_core.c requires OpenSSL 3.5+ for FIPS-203 ML-KEM support"
#endif

static void aura_ctx_reset(aura_mlkem768_ctx *ctx)
{
    if (ctx != NULL) {
        memset(ctx, 0, sizeof(*ctx));
    }
}

void aura_secure_zero(void *ptr, size_t len)
{
    if (ptr == NULL || len == 0u) {
        return;
    }

#if defined(__GLIBC__) || defined(__FreeBSD__) || defined(__OpenBSD__) || \
    defined(__NetBSD__) || defined(__APPLE__)
    explicit_bzero(ptr, len);
#else
    {
        volatile unsigned char *p = (volatile unsigned char *)ptr;
        size_t i;
        for (i = 0u; i < len; ++i) {
            p[i] = 0u;
        }
    }
#endif
}

int aura_stage8_zeroize(void *ptr, size_t len)
{
    volatile const unsigned char *p;
    unsigned char observed = 0u;
    size_t i;

    if (ptr == NULL && len != 0u) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    if (len == 0u) {
        return AURA_CRYPTO_OK;
    }

    aura_secure_zero(ptr, len);
    p = (volatile const unsigned char *)ptr;
    for (i = 0u; i < len; ++i) {
        observed = (unsigned char)(observed | p[i]);
    }
    return observed == 0u ? AURA_CRYPTO_OK : AURA_CRYPTO_ERR_ZEROIZE;
}

static int aura_mlkem768_prepare_contexts(aura_mlkem768_ctx *ctx,
                                          const char *propq,
                                          int need_encap,
                                          int need_decap)
{
    if (ctx == NULL || ctx->pkey == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }

    if (need_encap != 0) {
        ctx->encap_ctx = EVP_PKEY_CTX_new_from_pkey(NULL, ctx->pkey, propq);
        if (ctx->encap_ctx == NULL ||
            EVP_PKEY_encapsulate_init(ctx->encap_ctx, NULL) <= 0) {
            return AURA_CRYPTO_ERR_OPENSSL;
        }
    }

    if (need_decap != 0) {
        ctx->decap_ctx = EVP_PKEY_CTX_new_from_pkey(NULL, ctx->pkey, propq);
        if (ctx->decap_ctx == NULL ||
            EVP_PKEY_decapsulate_init(ctx->decap_ctx, NULL) <= 0) {
            return AURA_CRYPTO_ERR_OPENSSL;
        }
    }

    return AURA_CRYPTO_OK;
}

void aura_mlkem768_destroy(aura_mlkem768_ctx *ctx)
{
    if (ctx == NULL) {
        return;
    }

    EVP_PKEY_CTX_free(ctx->encap_ctx);
    EVP_PKEY_CTX_free(ctx->decap_ctx);
    EVP_PKEY_free(ctx->pkey);
    aura_secure_zero(ctx, sizeof(*ctx));
}

int aura_mlkem768_available(const char *propq)
{
    EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_from_name(NULL, "ML-KEM-768", propq);
    if (ctx == NULL) {
        return 0;
    }
    EVP_PKEY_CTX_free(ctx);
    return 1;
}

int aura_mlkem768_keygen(aura_mlkem768_ctx *ctx, const char *propq)
{
    EVP_PKEY *generated = NULL;
    EVP_PKEY *expanded = NULL;
    uint8_t dk[AURA_MLKEM768_PRIVATE_KEY_BYTES];
    size_t dk_len = sizeof(dk);
    int rc = AURA_CRYPTO_ERR_OPENSSL;

    if (ctx == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    aura_ctx_reset(ctx);
    memset(dk, 0, sizeof(dk));

    generated = EVP_PKEY_Q_keygen(NULL, propq, "ML-KEM-768");
    if (generated == NULL) {
        rc = AURA_CRYPTO_ERR_PROVIDER_UNAVAILABLE;
        goto done;
    }

    /*
     * Harden long-lived ownership: OpenSSL-generated ML-KEM keys retain the
     * 64-byte (d,z) seed by default. Export the FIPS-203 expanded dk, re-import
     * that explicit dk, then immediately scrub the temporary application copy.
     */
    if (EVP_PKEY_get_raw_private_key(generated, dk, &dk_len) <= 0 ||
        dk_len != AURA_MLKEM768_PRIVATE_KEY_BYTES) {
        rc = AURA_CRYPTO_ERR_SIZE;
        goto done;
    }

    expanded = EVP_PKEY_new_raw_private_key_ex(NULL, "ML-KEM-768", propq,
                                               dk, dk_len);
    if (expanded == NULL) {
        goto done;
    }

    ctx->pkey = expanded;
    expanded = NULL;
    rc = aura_mlkem768_prepare_contexts(ctx, propq, 1, 1);
    if (rc != AURA_CRYPTO_OK) {
        aura_mlkem768_destroy(ctx);
    }

done:
    aura_secure_zero(dk, sizeof(dk));
    EVP_PKEY_free(expanded);
    EVP_PKEY_free(generated);
    return rc;
}

int aura_mlkem768_import_public(aura_mlkem768_ctx *ctx,
                                const uint8_t public_key[AURA_MLKEM768_PUBLIC_KEY_BYTES],
                                const char *propq)
{
    int rc;

    if (ctx == NULL || public_key == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    aura_ctx_reset(ctx);

    ctx->pkey = EVP_PKEY_new_raw_public_key_ex(NULL, "ML-KEM-768", propq,
                                               public_key,
                                               AURA_MLKEM768_PUBLIC_KEY_BYTES);
    if (ctx->pkey == NULL) {
        return AURA_CRYPTO_ERR_OPENSSL;
    }

    rc = aura_mlkem768_prepare_contexts(ctx, propq, 1, 0);
    if (rc != AURA_CRYPTO_OK) {
        aura_mlkem768_destroy(ctx);
    }
    return rc;
}

int aura_mlkem768_import_private(aura_mlkem768_ctx *ctx,
                                 const uint8_t private_key[AURA_MLKEM768_PRIVATE_KEY_BYTES],
                                 const char *propq)
{
    int rc;

    if (ctx == NULL || private_key == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    aura_ctx_reset(ctx);

    ctx->pkey = EVP_PKEY_new_raw_private_key_ex(NULL, "ML-KEM-768", propq,
                                                private_key,
                                                AURA_MLKEM768_PRIVATE_KEY_BYTES);
    if (ctx->pkey == NULL) {
        return AURA_CRYPTO_ERR_OPENSSL;
    }

    rc = aura_mlkem768_prepare_contexts(ctx, propq, 1, 1);
    if (rc != AURA_CRYPTO_OK) {
        aura_mlkem768_destroy(ctx);
    }
    return rc;
}

int aura_mlkem768_export_public(const aura_mlkem768_ctx *ctx,
                                uint8_t public_key[AURA_MLKEM768_PUBLIC_KEY_BYTES])
{
    size_t len = AURA_MLKEM768_PUBLIC_KEY_BYTES;

    if (ctx == NULL || ctx->pkey == NULL || public_key == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    if (EVP_PKEY_get_raw_public_key(ctx->pkey, public_key, &len) <= 0) {
        return AURA_CRYPTO_ERR_OPENSSL;
    }
    return len == AURA_MLKEM768_PUBLIC_KEY_BYTES ?
        AURA_CRYPTO_OK : AURA_CRYPTO_ERR_SIZE;
}

int aura_mlkem768_encapsulate(aura_mlkem768_ctx *ctx,
                              uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
                              uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES])
{
    size_t ciphertext_len = AURA_MLKEM768_CIPHERTEXT_BYTES;
    size_t secret_len = AURA_MLKEM768_SHARED_SECRET_BYTES;

    if (ctx == NULL || ctx->encap_ctx == NULL ||
        ciphertext == NULL || shared_secret == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }

    if (EVP_PKEY_encapsulate(ctx->encap_ctx,
                             ciphertext, &ciphertext_len,
                             shared_secret, &secret_len) <= 0) {
        aura_secure_zero(shared_secret, AURA_MLKEM768_SHARED_SECRET_BYTES);
        aura_secure_zero(ciphertext, AURA_MLKEM768_CIPHERTEXT_BYTES);
        return AURA_CRYPTO_ERR_OPENSSL;
    }

    if (ciphertext_len != AURA_MLKEM768_CIPHERTEXT_BYTES ||
        secret_len != AURA_MLKEM768_SHARED_SECRET_BYTES) {
        aura_secure_zero(shared_secret, AURA_MLKEM768_SHARED_SECRET_BYTES);
        aura_secure_zero(ciphertext, AURA_MLKEM768_CIPHERTEXT_BYTES);
        return AURA_CRYPTO_ERR_SIZE;
    }

    return AURA_CRYPTO_OK;
}

int aura_mlkem768_decapsulate(aura_mlkem768_ctx *ctx,
                              const uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
                              uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES])
{
    size_t secret_len = AURA_MLKEM768_SHARED_SECRET_BYTES;

    if (ctx == NULL || ctx->decap_ctx == NULL ||
        ciphertext == NULL || shared_secret == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }

    if (EVP_PKEY_decapsulate(ctx->decap_ctx,
                             shared_secret, &secret_len,
                             ciphertext,
                             AURA_MLKEM768_CIPHERTEXT_BYTES) <= 0) {
        aura_secure_zero(shared_secret, AURA_MLKEM768_SHARED_SECRET_BYTES);
        return AURA_CRYPTO_ERR_OPENSSL;
    }

    if (secret_len != AURA_MLKEM768_SHARED_SECRET_BYTES) {
        aura_secure_zero(shared_secret, AURA_MLKEM768_SHARED_SECRET_BYTES);
        return AURA_CRYPTO_ERR_SIZE;
    }

    /*
     * Per KEM semantics, successful decapsulation is not peer authentication.
     * A well-formed invalid ciphertext may produce a synthetic secret. The
     * caller must authenticate subsequent traffic using a derived key.
     */
    return AURA_CRYPTO_OK;
}

int aura_mlkem768_selftest(const char *propq)
{
    aura_mlkem768_ctx ctx;
    uint8_t ct[AURA_MLKEM768_CIPHERTEXT_BYTES];
    uint8_t ss_enc[AURA_MLKEM768_SHARED_SECRET_BYTES];
    uint8_t ss_dec[AURA_MLKEM768_SHARED_SECRET_BYTES];
    int rc;
    unsigned diff = 0u;
    size_t i;

    aura_ctx_reset(&ctx);
    memset(ct, 0, sizeof(ct));
    memset(ss_enc, 0, sizeof(ss_enc));
    memset(ss_dec, 0, sizeof(ss_dec));

    rc = aura_mlkem768_keygen(&ctx, propq);
    if (rc != AURA_CRYPTO_OK) {
        goto done;
    }
    rc = aura_mlkem768_encapsulate(&ctx, ct, ss_enc);
    if (rc != AURA_CRYPTO_OK) {
        goto done;
    }
    rc = aura_mlkem768_decapsulate(&ctx, ct, ss_dec);
    if (rc != AURA_CRYPTO_OK) {
        goto done;
    }

    for (i = 0u; i < AURA_MLKEM768_SHARED_SECRET_BYTES; ++i) {
        diff |= (unsigned)(ss_enc[i] ^ ss_dec[i]);
    }
    rc = diff == 0u ? AURA_CRYPTO_OK : AURA_CRYPTO_ERR_OPENSSL;

done:
    aura_secure_zero(ss_enc, sizeof(ss_enc));
    aura_secure_zero(ss_dec, sizeof(ss_dec));
    aura_secure_zero(ct, sizeof(ct));
    aura_mlkem768_destroy(&ctx);
    return rc;
}

static int aura_abs_within(float value, float target, float epsilon)
{
    float delta = value - target;
    if (delta < 0.0f) {
        delta = -delta;
    }
    return delta <= epsilon;
}

int aura_hdc_phasor_validate(const float key_ri[AURA_HDC_SCALARS])
{
    size_t i;
    unsigned bad = 0u;

    if (key_ri == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }

    for (i = 0u; i < AURA_HDC_SCALARS; i += 2u) {
        const float re = key_ri[i];
        const float im = key_ri[i + 1u];
        const float norm2 = (re * re) + (im * im);
        bad |= (unsigned)(aura_abs_within(norm2, 1.0f,
                                          AURA_HDC_UNIT_EPSILON) == 0);
    }
    return bad == 0u ? AURA_CRYPTO_OK : AURA_CRYPTO_ERR_INVALID_PHASOR;
}

#if defined(__AVX2__)
static __m256 aura_complex_mul4(__m256 a, __m256 b)
{
    const __m256 a_re = _mm256_moveldup_ps(a);
    const __m256 a_im = _mm256_movehdup_ps(a);
    const __m256 b_swap = _mm256_permute_ps(b, 0xB1);
    const __m256 p1 = _mm256_mul_ps(a_re, b);
    const __m256 p2 = _mm256_mul_ps(a_im, b_swap);
    return _mm256_addsub_ps(p1, p2);
}
#endif

int aura_hdc_phasor_bind(uint32_t cipher_bits[AURA_HDC_SCALARS],
                         const float message_ri[AURA_HDC_SCALARS],
                         const float key_ri[AURA_HDC_SCALARS],
                         const uint32_t fst_mask[AURA_HDC_SCALARS])
{
    size_t i = 0u;
    int rc;

    if (cipher_bits == NULL || message_ri == NULL ||
        key_ri == NULL || fst_mask == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    rc = aura_hdc_phasor_validate(key_ri);
    if (rc != AURA_CRYPTO_OK) {
        return rc;
    }

#if defined(__AVX2__)
    for (; i + 8u <= AURA_HDC_SCALARS; i += 8u) {
        const __m256 m = _mm256_loadu_ps(message_ri + i);
        const __m256 k = _mm256_loadu_ps(key_ri + i);
        const __m256 bound = aura_complex_mul4(m, k);
        const __m256i bits = _mm256_castps_si256(bound);
        const __m256i mask = _mm256_loadu_si256((const __m256i *)(fst_mask + i));
        _mm256_storeu_si256((__m256i *)(cipher_bits + i),
                            _mm256_xor_si256(bits, mask));
    }
#endif

    for (; i < AURA_HDC_SCALARS; i += 2u) {
        const float mr = message_ri[i];
        const float mi = message_ri[i + 1u];
        const float kr = key_ri[i];
        const float ki = key_ri[i + 1u];
        const float br = (mr * kr) - (mi * ki);
        const float bi = (mr * ki) + (mi * kr);
        uint32_t br_bits;
        uint32_t bi_bits;
        memcpy(&br_bits, &br, sizeof(br_bits));
        memcpy(&bi_bits, &bi, sizeof(bi_bits));
        cipher_bits[i] = br_bits ^ fst_mask[i];
        cipher_bits[i + 1u] = bi_bits ^ fst_mask[i + 1u];
    }

    return AURA_CRYPTO_OK;
}

int aura_hdc_phasor_unbind(float message_ri[AURA_HDC_SCALARS],
                           const uint32_t cipher_bits[AURA_HDC_SCALARS],
                           const float key_ri[AURA_HDC_SCALARS],
                           const uint32_t fst_mask[AURA_HDC_SCALARS])
{
    size_t i = 0u;
    int rc;

    if (message_ri == NULL || cipher_bits == NULL ||
        key_ri == NULL || fst_mask == NULL) {
        return AURA_CRYPTO_ERR_INVALID_ARGUMENT;
    }
    rc = aura_hdc_phasor_validate(key_ri);
    if (rc != AURA_CRYPTO_OK) {
        return rc;
    }

#if defined(__AVX2__)
    {
        /* Conjugation is a single SIMD XOR sign-flip per four complex lanes. */
        const __m256i imag_sign = _mm256_set_epi32(
            INT32_MIN, 0, INT32_MIN, 0, INT32_MIN, 0, INT32_MIN, 0);

        for (; i + 8u <= AURA_HDC_SCALARS; i += 8u) {
            const __m256i c = _mm256_loadu_si256((const __m256i *)(cipher_bits + i));
            const __m256i mask = _mm256_loadu_si256((const __m256i *)(fst_mask + i));
            const __m256 bound = _mm256_castsi256_ps(_mm256_xor_si256(c, mask));
            const __m256 k = _mm256_loadu_ps(key_ri + i);
            const __m256 k_conj = _mm256_castsi256_ps(
                _mm256_xor_si256(_mm256_castps_si256(k), imag_sign));
            const __m256 recovered = aura_complex_mul4(bound, k_conj);
            _mm256_storeu_ps(message_ri + i, recovered);
        }
    }
#endif

    for (; i < AURA_HDC_SCALARS; i += 2u) {
        uint32_t br_bits = cipher_bits[i] ^ fst_mask[i];
        uint32_t bi_bits = cipher_bits[i + 1u] ^ fst_mask[i + 1u];
        float br;
        float bi;
        const float kr = key_ri[i];
        const float ki = key_ri[i + 1u];
        memcpy(&br, &br_bits, sizeof(br));
        memcpy(&bi, &bi_bits, sizeof(bi));
        message_ri[i] = (br * kr) + (bi * ki);
        message_ri[i + 1u] = (bi * kr) - (br * ki);
    }

    return AURA_CRYPTO_OK;
}
