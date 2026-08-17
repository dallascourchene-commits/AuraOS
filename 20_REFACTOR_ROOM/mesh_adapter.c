#include "mesh_adapter.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static uint32_t median_u32(const uint32_t *src, size_t n) {
    uint32_t v[AURA_MESH_WINDOW];
    size_t i;
    size_t j;
    for (i = 0; i < n; ++i) {
        v[i] = src[i];
    }
    for (i = 1; i < n; ++i) {
        uint32_t key = v[i];
        j = i;
        while (j > 0u && v[j - 1u] > key) {
            v[j] = v[j - 1u];
            --j;
        }
        v[j] = key;
    }
    return v[n / 2u];
}

void aura_mesh_init(aura_mesh_rtt_monitor_t *m) {
    if (m != NULL) {
        memset(m, 0, sizeof(*m));
    }
}

bool aura_mesh_push(aura_mesh_rtt_monitor_t *m, uint32_t ab_us, uint32_t bc_us, uint32_t ac_us) {
    if (m == NULL) {
        return false;
    }
    m->ab[m->cursor] = ab_us;
    m->bc[m->cursor] = bc_us;
    m->ac[m->cursor] = ac_us;
    m->cursor = (m->cursor + 1u) % AURA_MESH_WINDOW;
    if (m->count < AURA_MESH_WINDOW) {
        ++m->count;
    }
    return true;
}

bool aura_mesh_snapshot(const aura_mesh_rtt_monitor_t *m, aura_mesh_snapshot_t *out) {
    uint64_t lhs;
    if (m == NULL || out == NULL || m->count == 0u) {
        return false;
    }
    out->median_ab_us = median_u32(m->ab, m->count);
    out->median_bc_us = median_u32(m->bc, m->count);
    out->median_ac_us = median_u32(m->ac, m->count);
    lhs = (uint64_t)out->median_ab_us + (uint64_t)out->median_bc_us;
    out->triangle_consistent = lhs >= out->median_ac_us;
    return true;
}

static uint64_t mix64(uint64_t x) {
    x ^= x >> 30;
    x *= UINT64_C(0xbf58476d1ce4e5b9);
    x ^= x >> 27;
    x *= UINT64_C(0x94d049bb133111eb);
    x ^= x >> 31;
    return x;
}

uint16_t aura_udp_hop_port(uint64_t seed, uint64_t ms, uint16_t base, uint16_t span) {
    uint64_t epoch;
    uint64_t mixed;
    if (span == 0u) {
        return base;
    }
    epoch = ms / 300u;
    mixed = mix64(seed ^ epoch);
    return (uint16_t)(base + (uint16_t)(mixed % span));
}

int aura_udp_bind_hop_socket(uint64_t seed, uint64_t ms, uint16_t base, uint16_t span, uint16_t *bound_port) {
    struct sockaddr_in addr;
    uint16_t port = aura_udp_hop_port(seed, ms, base, span);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        return -1;
    }
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (bind(fd, (const struct sockaddr *)&addr, sizeof(addr)) != 0) {
        close(fd);
        return -1;
    }
    if (bound_port != NULL) {
        *bound_port = port;
    }
    return fd;
}
