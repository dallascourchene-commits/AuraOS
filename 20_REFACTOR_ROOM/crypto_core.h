#ifndef AURA_CRYPTO_CORE_H
#define AURA_CRYPTO_CORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AURA_MLKEM768_PUBLIC_KEY_BYTES 1184u
#define AURA_MLKEM768_SECRET_KEY_BYTES 2400u
#define AURA_MLKEM768_CIPHERTEXT_BYTES 1088u
#define AURA_MLKEM768_SHARED_SECRET_BYTES 32u
#define AURA_HDC_DIM 10000u
#define AURA_HDC_SCALARS (AURA_HDC_DIM * 2u)

typedef enum {
    AURA_CRYPTO_OK = 0,
    AURA_CRYPTO_UNSUPPORTED = 1,
    AURA_CRYPTO_INVALID = 2,
    AURA_CRYPTO_BACKEND_ERROR = 3
} aura_crypto_status_t;

typedef struct {
    void *provider_key;
} aura_mlkem768_keypair_t;

aura_crypto_status_t aura_mlkem768_keygen(aura_mlkem768_keypair_t *keypair);
aura_crypto_status_t aura_mlkem768_encaps(
    const aura_mlkem768_keypair_t *keypair,
    uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
    uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]
);
aura_crypto_status_t aura_mlkem768_decaps(
    const aura_mlkem768_keypair_t *keypair,
    const uint8_t ciphertext[AURA_MLKEM768_CIPHERTEXT_BYTES],
    uint8_t shared_secret[AURA_MLKEM768_SHARED_SECRET_BYTES]
);
void aura_mlkem768_keypair_free(aura_mlkem768_keypair_t *keypair);

bool aura_hdc_bind(
    const float *message,
    const float *unit_phasor_key,
    const uint32_t *fst_pad_words,
    uint32_t *cipher_words
);

bool aura_hdc_unbind(
    const uint32_t *cipher_words,
    const float *unit_phasor_key,
    const uint32_t *fst_pad_words,
    float *message_out
);

void aura_secure_bzero(void *ptr, size_t len);
bool aura_buffer_is_zero(const void *ptr, size_t len);

#ifdef __cplusplus
}
#endif

#endif
