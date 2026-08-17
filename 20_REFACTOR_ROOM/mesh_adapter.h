#ifndef AURA_MESH_ADAPTER_H
#define AURA_MESH_ADAPTER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AURA_MESH_WINDOW 9u

typedef struct {
    uint32_t ab[AURA_MESH_WINDOW];
    uint32_t bc[AURA_MESH_WINDOW];
    uint32_t ac[AURA_MESH_WINDOW];
    size_t count;
    size_t cursor;
} aura_mesh_rtt_monitor_t;

typedef struct {
    uint32_t median_ab_us;
    uint32_t median_bc_us;
    uint32_t median_ac_us;
    bool triangle_consistent;
} aura_mesh_snapshot_t;

void aura_mesh_init(aura_mesh_rtt_monitor_t *m);
bool aura_mesh_push(aura_mesh_rtt_monitor_t *m, uint32_t ab_us, uint32_t bc_us, uint32_t ac_us);
bool aura_mesh_snapshot(const aura_mesh_rtt_monitor_t *m, aura_mesh_snapshot_t *out);

/* Deterministic local UDP listen-port rotation every 300 ms. No packet send occurs here. */
uint16_t aura_udp_hop_port(uint64_t session_seed, uint64_t monotonic_ms, uint16_t base_port, uint16_t span);
int aura_udp_bind_hop_socket(uint64_t session_seed, uint64_t monotonic_ms, uint16_t base_port, uint16_t span, uint16_t *bound_port);

#ifdef __cplusplus
}
#endif

#endif
