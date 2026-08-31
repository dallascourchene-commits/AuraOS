// AuraOS K27 ThinkPad portable SIMD dispatch contract.
//
// This executable deliberately separates build-host ISA from runtime ISA.
// Specialized functions carry their own target attributes; the translation
// unit must be compiled without -march=native/-mavx2/-mavx512*. Runtime
// selection also requires OS-managed extended-vector state, not CPUID bits
// alone. It is a capability/equivalence witness, not a performance claim.

#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string_view>

#if !defined(__x86_64__) && !defined(__i386__)
#error "This bounded witness currently targets x86/x86_64 only"
#endif

#include <cpuid.h>
#include <immintrin.h>

namespace aura::k27 {

constexpr std::size_t kWords = 16;
constexpr std::size_t kBits = 1024;

struct CpuVectorState {
    bool cpuid_popcnt = false;
    bool cpuid_avx2 = false;
    bool cpuid_avx512f = false;
    bool cpuid_avx512_vpopcntdq = false;
    bool osxsave = false;
    bool xmm_ymm_state = false;
    bool zmm_state = false;

    [[nodiscard]] bool avx2_popcnt_usable() const {
        return cpuid_popcnt && cpuid_avx2 && osxsave && xmm_ymm_state;
    }
    [[nodiscard]] bool avx512_vpopcntdq_usable() const {
        return cpuid_avx512f && cpuid_avx512_vpopcntdq && osxsave && zmm_state;
    }
};

static std::uint64_t xgetbv0() {
    std::uint32_t eax = 0;
    std::uint32_t edx = 0;
    __asm__ volatile("xgetbv" : "=a"(eax), "=d"(edx) : "c"(0));
    return (static_cast<std::uint64_t>(edx) << 32U) | eax;
}

[[nodiscard]] CpuVectorState detect_vector_state() {
    CpuVectorState out{};
    unsigned eax = 0, ebx = 0, ecx = 0, edx = 0;
    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx) == 0) {
        return out;
    }

    constexpr unsigned kPopcntBit = 1U << 23U;
    constexpr unsigned kOsxsaveBit = 1U << 27U;
    out.cpuid_popcnt = (ecx & kPopcntBit) != 0U;
    out.osxsave = (ecx & kOsxsaveBit) != 0U;

    if (out.osxsave) {
        const std::uint64_t xcr0 = xgetbv0();
        // XMM state bit 1 + YMM state bit 2.
        out.xmm_ymm_state = (xcr0 & 0x6U) == 0x6U;
        // XMM/YMM plus opmask, ZMM_hi256 and hi16_ZMM: bits 1,2,5,6,7.
        out.zmm_state = (xcr0 & 0xE6U) == 0xE6U;
    }

    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx) != 0) {
        constexpr unsigned kAvx2Bit = 1U << 5U;
        constexpr unsigned kAvx512fBit = 1U << 16U;
        constexpr unsigned kAvx512VpopcntdqBit = 1U << 14U;
        out.cpuid_avx2 = (ebx & kAvx2Bit) != 0U;
        out.cpuid_avx512f = (ebx & kAvx512fBit) != 0U;
        out.cpuid_avx512_vpopcntdq = (ecx & kAvx512VpopcntdqBit) != 0U;
    }
    return out;
}

[[nodiscard]] std::uint32_t hamming_scalar(
    const std::uint64_t* query,
    const std::uint64_t* centroid) {
    std::uint32_t distance = 0;
    for (std::size_t i = 0; i < kWords; ++i) {
        distance += static_cast<std::uint32_t>(
            __builtin_popcountll(query[i] ^ centroid[i]));
    }
    return distance;
}

__attribute__((target("avx2,popcnt")))
[[nodiscard]] std::uint32_t hamming_avx2_popcnt(
    const std::uint64_t* query,
    const std::uint64_t* centroid) {
    std::uint32_t distance = 0;
    alignas(32) std::uint64_t lanes[4]{};
    for (std::size_t i = 0; i < kWords; i += 4) {
        const auto q = _mm256_loadu_si256(
            reinterpret_cast<const __m256i*>(query + i));
        const auto c = _mm256_loadu_si256(
            reinterpret_cast<const __m256i*>(centroid + i));
        const auto x = _mm256_xor_si256(q, c);
        _mm256_store_si256(reinterpret_cast<__m256i*>(lanes), x);
        for (const auto lane : lanes) {
            distance += static_cast<std::uint32_t>(__builtin_popcountll(lane));
        }
    }
    return distance;
}

__attribute__((target("avx512f,avx512vpopcntdq")))
[[nodiscard]] std::uint32_t hamming_avx512_vpopcntdq(
    const std::uint64_t* query,
    const std::uint64_t* centroid) {
    std::uint32_t distance = 0;
    alignas(64) std::uint64_t lanes[8]{};
    for (std::size_t i = 0; i < kWords; i += 8) {
        const auto q = _mm512_loadu_si512(
            reinterpret_cast<const void*>(query + i));
        const auto c = _mm512_loadu_si512(
            reinterpret_cast<const void*>(centroid + i));
        const auto counts = _mm512_popcnt_epi64(_mm512_xor_si512(q, c));
        _mm512_store_si512(reinterpret_cast<void*>(lanes), counts);
        for (const auto lane_count : lanes) {
            distance += static_cast<std::uint32_t>(lane_count);
        }
    }
    return distance;
}

enum class DispatchPath {
    Scalar,
    Avx2Popcnt,
    Avx512Vpopcntdq,
};

[[nodiscard]] DispatchPath choose_path(const CpuVectorState& state) {
    if (state.avx512_vpopcntdq_usable()) {
        return DispatchPath::Avx512Vpopcntdq;
    }
    if (state.avx2_popcnt_usable()) {
        return DispatchPath::Avx2Popcnt;
    }
    return DispatchPath::Scalar;
}

[[nodiscard]] std::string_view path_name(DispatchPath path) {
    switch (path) {
        case DispatchPath::Avx512Vpopcntdq:
            return "AVX512_VPOPCNTDQ";
        case DispatchPath::Avx2Popcnt:
            return "AVX2_POPCNT64";
        case DispatchPath::Scalar:
        default:
            return "SCALAR_PORTABLE";
    }
}

[[nodiscard]] std::uint32_t hamming_selected(
    const CpuVectorState& state,
    const std::uint64_t* query,
    const std::uint64_t* centroid) {
    switch (choose_path(state)) {
        case DispatchPath::Avx512Vpopcntdq:
            return hamming_avx512_vpopcntdq(query, centroid);
        case DispatchPath::Avx2Popcnt:
            return hamming_avx2_popcnt(query, centroid);
        case DispatchPath::Scalar:
        default:
            return hamming_scalar(query, centroid);
    }
}

}  // namespace aura::k27

int main() {
    using namespace aura::k27;

    std::array<std::uint64_t, kWords> query{};
    std::array<std::uint64_t, kWords> centroid{};
    for (std::size_t i = 0; i < kWords; ++i) {
        query[i] = 0x5555555555555555ULL ^ (0x0101010101010101ULL * i);
        centroid[i] = query[i];
    }
    centroid[0] ^= 0xFULL;  // Exactly four differing bits.
    centroid[7] ^= 0x100000000ULL;  // One more bit.

    const CpuVectorState state = detect_vector_state();
    const auto scalar = hamming_scalar(query.data(), centroid.data());
    const auto selected = hamming_selected(state, query.data(), centroid.data());
    if (scalar != 5U || selected != scalar) {
        std::cerr << "SIMD_CONSEQUENCE_MISMATCH scalar=" << scalar
                  << " selected=" << selected << '\n';
        return EXIT_FAILURE;
    }

    // This receipt intentionally does not infer P/E-core placement, thermal
    // behavior, cache residency, or speed from ISA availability.
    std::cout << "SCHEMA=AURA_K27_THINKPAD_PORTABLE_SIMD_DISPATCH_V1\n";
    std::cout << "SELECTED_PATH=" << path_name(choose_path(state)) << '\n';
    std::cout << "CPUID_POPCNT=" << state.cpuid_popcnt << '\n';
    std::cout << "CPUID_AVX2=" << state.cpuid_avx2 << '\n';
    std::cout << "CPUID_AVX512F=" << state.cpuid_avx512f << '\n';
    std::cout << "CPUID_AVX512_VPOPCNTDQ=" << state.cpuid_avx512_vpopcntdq << '\n';
    std::cout << "OSXSAVE=" << state.osxsave << '\n';
    std::cout << "XMM_YMM_STATE=" << state.xmm_ymm_state << '\n';
    std::cout << "ZMM_STATE=" << state.zmm_state << '\n';
    std::cout << "SCALAR_SELECTED_EQUIVALENT=true\n";
    std::cout << "GLOBAL_MARCH_NATIVE_REQUIRED=false\n";
    std::cout << "P_CORE_ONLY_OBSERVED=false\n";
    std::cout << "CACHE_RESIDENCY_PROVEN=false\n";
    std::cout << "THERMAL_POWER_REDUCTION_PROVEN=false\n";
    std::cout << "PERFORMANCE_SUPERIORITY_PROVEN=false\n";
    std::cout << "SEMANTIC_K27_AUTHORITY=false\n";
    std::cout << "NATIVE_TRANSFORMER_KV_ACCESSED=false\n";
    return EXIT_SUCCESS;
}
