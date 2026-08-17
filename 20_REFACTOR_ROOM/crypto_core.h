#ifndef AURA_CRYPTO_CORE_H
#define AURA_CRYPTO_CORE_H

#include <stddef.h>
#include <stdint.h>
#include <openssl/evp.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AURA_MLKEM768_PUBLIC_KEY_BYTES 1184u
#define AURA_MLKEM768_PRIVATE_KEY_BYTES 2400u
#define AURA_MLKEM768_CIPHERTEXT_BYTES 1088u
#define AURA_MLKEM768_SHARED_SECRET_BYTES 32u

#define AURA_HDC_DIMENSIONS 10000u
#define AURA_HDC_SCALARS (AURA_HDC_DIMENSIONS * 2u)
#define AURA_HDC_UNIT_EPSILON 0.0005f

typedef enum aura_crypto_status {
    AURA_CRYPTO_OK = 0,
    AURA_CRYPTO_ERR_INVALID_ARGUMENT = -1,
    AURA_CRYPTO_ERR_PROVIDER_UNAVAILABLE = -2,
    AURA_CRYPTO_ERR_OPENSSL = -3,
    AURA_CRYPTO_ERR_SIZE = -4,
    AURA_CRYPTO_ERR_INVALID_PHASOR = -5,
    AURA_CRYPTO_ERR_ZEROIZE = -6
} aura_crypto_status;

typedef struct aura_mlkem768_ctx {
    EVP_PKEY *pkey;
    EVP_PKEY_CTX *encap_ctx;
    EVP_PKEY_CTX *decap_ctx;
} aura_mlkem768_ctx;

/*
 * ML-KEM-768 integration through OpenSSL 3.5+ EVP.
 * propq may be NULL for the default provider or e.g. "fips=yes" when a
 * separately validated/configured FIPS provider is available.
 *
 * No application-owned dynamic allocation calls are made by this module. OpenSSL
 * provider internals may allocate memory; callers requiring a globally allocation-free
 * hot path must separately prove the selected provider's allocation behavior.
 */
int aura_mlkem768_available(const char *propq);
int aura_mlkem768_keygen(aura_mlkem768_ctx *ctx, const char *propq);
int aura_mlkem768_import_public(aura_mlkem768_ctx *ctx,
                                const uint8_t public_key[AURA_MLKEM768_PUBLIC_KEY_BYTES],
                                const char *propq);
int aura_mlkem768_import_private(aura_mlkem768_ctx *ctx,
                                 const uint8_t private_key[AURA_MLKEM768_PRIVATE_KEY_BYTES],
                                 const char *propq);
int aura_mlkem768_export_public(const aura_mlkem768_ctx *ctx,
                                uint8_t public_key[AURA_MLKEM768_PUBLIC_KEY_BYTES]);
int aura_mlkem768_encapsulate(aura_mlkem768_ctx *ctx,
                              uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
                              uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]);
int aura_mlkem768_decapsulate(aura_mlkem768_ctx *ctx,
                              const uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
                              uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]);
void aura_mlkem768_destroy(aura_mlkem768_ctx *ctx);
int aura_mlkem768_selftest(const char *propq);

/* Stage-8 memory eviction for application-owned ephemeral material. */
void aura_secure_zero(void *ptr, size_t len);
int aura_stage8_zeroize(void *ptr, size_t len);

/*
 * 10,000-D complex phasor binding. message_ri and key_ri are interleaved
 * [real, imag] float pairs. cipher_bits and fst_mask contain the raw IEEE-754
 * lane bits so the FST permutation is a reversible bitwise XOR, not arithmetic
 * on possibly-NaN float values.
 *
 * Security note: this is a reversible HDC binding transform, not an AEAD or a
 * replacement for a standard symmetric cipher. Authentication/key derivation
 * must be supplied by a separate cryptographic construction.
 */
int aura_hdc_phasor_validate(const float key_ri[AURA_HDC_SCALARS]);
int aura_hdc_phasor_bind(uint32_t cipher_bits[AURA_HDC_SCALARS],
                         const float message_ri[AURA_HDC_SCALARS],
                         const float key_ri[AURA_HDC_SCALARS],
                         const uint32_t fst_mask[AURA_HDC_SCALARS]);
int aura_hdc_phasor_unbind(float message_ri[AURA_HDC_SCALARS],
                           const uint32_t cipher_bits[AURA_HDC_SCALARS],
                           const float key_ri[AURA_HDC_SCALARS],
                           const uint32_t fst_mask[AURA_HDC_SCALARS]);

#ifdef __cplusplus
}
#endif

#endif /* AURA_CRYPTO_CORE_H */
