#include <array>
#include <bit>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#if defined(__x86_64__) || defined(__i386__)
#include <cpuid.h>
#include <immintrin.h>
#endif

namespace {

constexpr std::size_t kWords = 16;
constexpr std::size_t kBits = 1024;
constexpr std::uint64_t kProposedTileBytes = 512ULL * 1024ULL;

struct CpuEvidence {
    bool x86 = false;
    bool cpuid_leaf1 = false;
    bool cpuid_leaf7 = false;
    bool osxsave = false;
    bool avx = false;
    bool popcnt = false;
    bool avx2 = false;
    bool avx512f = false;
    bool avx512_vpopcntdq = false;
    bool xgetbv_observed = false;
    std::uint64_t xcr0 = 0;
};

struct CacheEvidence {
    bool l2_observed = false;
    std::uint64_t l2_size_bytes = 0;
    std::string l2_type = "UNAVAILABLE";
    std::string l2_shared_cpu_list = "UNAVAILABLE";
};

bool xmm_ymm_os_enabled(const CpuEvidence& e) {
    return e.osxsave && e.xgetbv_observed && (e.xcr0 & 0x6ULL) == 0x6ULL;
}

bool avx2_execution_eligible(const CpuEvidence& e) {
    return e.x86 && e.avx && e.avx2 && e.popcnt && xmm_ymm_os_enabled(e);
}

bool avx512_vpopcnt_execution_eligible(const CpuEvidence& e) {
    // XCR0 bits: XMM=1, YMM=2, opmask=5, ZMM_hi256=6, hi16_ZMM=7.
    constexpr std::uint64_t required_xcr0 = 0xE6ULL;
    return e.x86 && e.avx && e.avx512f && e.avx512_vpopcntdq && e.osxsave &&
           e.xgetbv_observed && (e.xcr0 & required_xcr0) == required_xcr0;
}

#if defined(__x86_64__) || defined(__i386__)
std::uint64_t read_xcr0() {
    std::uint32_t eax = 0;
    std::uint32_t edx = 0;
#if defined(_MSC_VER)
    return static_cast<std::uint64_t>(_xgetbv(0));
#else
    // XGETBV is executed only after CPUID.OSXSAVE has been observed.
    __asm__ volatile(".byte 0x0f, 0x01, 0xd0" : "=a"(eax), "=d"(edx) : "c"(0));
    return (static_cast<std::uint64_t>(edx) << 32U) | eax;
#endif
}
#endif

CpuEvidence detect_cpu_evidence() {
    CpuEvidence e;
#if defined(__x86_64__) || defined(__i386__)
    e.x86 = true;
    const unsigned int max_leaf = __get_cpuid_max(0, nullptr);
    if (max_leaf >= 1) {
        unsigned int eax = 0, ebx = 0, ecx = 0, edx = 0;
        __cpuid_count(1, 0, eax, ebx, ecx, edx);
        e.cpuid_leaf1 = true;
        e.osxsave = (ecx & bit_OSXSAVE) != 0;
        e.avx = (ecx & bit_AVX) != 0;
        e.popcnt = (ecx & bit_POPCNT) != 0;
        if (e.osxsave) {
            e.xcr0 = read_xcr0();
            e.xgetbv_observed = true;
        }
    }
    if (max_leaf >= 7) {
        unsigned int eax = 0, ebx = 0, ecx = 0, edx = 0;
        __cpuid_count(7, 0, eax, ebx, ecx, edx);
        e.cpuid_leaf7 = true;
        e.avx2 = (ebx & bit_AVX2) != 0;
#ifdef bit_AVX512F
        e.avx512f = (ebx & bit_AVX512F) != 0;
#else
        e.avx512f = (ebx & (1U << 16U)) != 0;
#endif
        // CPUID.(EAX=7,ECX=0):ECX[14] = AVX512_VPOPCNTDQ.
        e.avx512_vpopcntdq = (ecx & (1U << 14U)) != 0;
    }
#endif
    return e;
}

std::optional<std::string> read_text(const std::filesystem::path& path) {
    std::ifstream in(path);
    if (!in) return std::nullopt;
    std::ostringstream out;
    out << in.rdbuf();
    std::string value = out.str();
    while (!value.empty() && (value.back() == '\n' || value.back() == '\r' || value.back() == ' ' || value.back() == '\t')) {
        value.pop_back();
    }
    return value;
}

std::optional<std::uint64_t> parse_cache_size_bytes(const std::string& text) {
    if (text.empty()) return std::nullopt;
    std::size_t pos = 0;
    std::uint64_t value = 0;
    try {
        value = std::stoull(text, &pos);
    } catch (...) {
        return std::nullopt;
    }
    std::uint64_t scale = 1;
    if (pos < text.size()) {
        const char suffix = text[pos];
        if (suffix == 'K' || suffix == 'k') scale = 1024ULL;
        else if (suffix == 'M' || suffix == 'm') scale = 1024ULL * 1024ULL;
        else if (suffix == 'G' || suffix == 'g') scale = 1024ULL * 1024ULL * 1024ULL;
        else return std::nullopt;
    }
    return value * scale;
}

CacheEvidence detect_l2_cache_evidence() {
    CacheEvidence best;
    const std::filesystem::path root("/sys/devices/system/cpu/cpu0/cache");
    std::error_code ec;
    if (!std::filesystem::exists(root, ec)) return best;
    for (const auto& entry : std::filesystem::directory_iterator(root, ec)) {
        if (ec || !entry.is_directory()) continue;
        const auto level = read_text(entry.path() / "level");
        const auto type = read_text(entry.path() / "type");
        const auto size = read_text(entry.path() / "size");
        if (!level || *level != "2" || !type || !size) continue;
        if (*type != "Data" && *type != "Unified") continue;
        const auto bytes = parse_cache_size_bytes(*size);
        if (!bytes || *bytes < best.l2_size_bytes) continue;
        best.l2_observed = true;
        best.l2_size_bytes = *bytes;
        best.l2_type = *type;
        best.l2_shared_cpu_list = read_text(entry.path() / "shared_cpu_list").value_or("UNAVAILABLE");
    }
    return best;
}

std::uint32_t hamming_scalar(const std::array<std::uint64_t, kWords>& a,
                             const std::array<std::uint64_t, kWords>& b) {
    std::uint32_t total = 0;
    for (std::size_t i = 0; i < kWords; ++i) {
        total += static_cast<std::uint32_t>(std::popcount(a[i] ^ b[i]));
    }
    return total;
}

#if (defined(__x86_64__) || defined(__i386__)) && (defined(__GNUC__) || defined(__clang__))
__attribute__((target("avx2,popcnt")))
std::uint32_t hamming_avx2(const std::array<std::uint64_t, kWords>& a,
                          const std::array<std::uint64_t, kWords>& b) {
    alignas(32) std::uint64_t lanes[4];
    std::uint32_t total = 0;
    for (std::size_t i = 0; i < kWords; i += 4) {
        const auto va = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(a.data() + i));
        const auto vb = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(b.data() + i));
        const auto vx = _mm256_xor_si256(va, vb);
        _mm256_store_si256(reinterpret_cast<__m256i*>(lanes), vx);
        for (std::uint64_t lane : lanes) {
            total += static_cast<std::uint32_t>(__builtin_popcountll(lane));
        }
    }
    return total;
}

__attribute__((target("avx512f,avx512vpopcntdq")))
std::uint32_t hamming_avx512_vpopcnt(const std::array<std::uint64_t, kWords>& a,
                                    const std::array<std::uint64_t, kWords>& b) {
    alignas(64) std::uint64_t lanes[8];
    std::uint64_t total = 0;
    for (std::size_t i = 0; i < kWords; i += 8) {
        const auto va = _mm512_loadu_si512(reinterpret_cast<const void*>(a.data() + i));
        const auto vb = _mm512_loadu_si512(reinterpret_cast<const void*>(b.data() + i));
        const auto counts = _mm512_popcnt_epi64(_mm512_xor_si512(va, vb));
        _mm512_store_si512(reinterpret_cast<void*>(lanes), counts);
        for (std::uint64_t lane : lanes) total += lane;
    }
    return static_cast<std::uint32_t>(total);
}
#endif

std::uint32_t hamming_dispatched(const CpuEvidence& e,
                                 const std::array<std::uint64_t, kWords>& a,
                                 const std::array<std::uint64_t, kWords>& b,
                                 std::string* backend) {
#if (defined(__x86_64__) || defined(__i386__)) && (defined(__GNUC__) || defined(__clang__))
    if (avx512_vpopcnt_execution_eligible(e)) {
        if (backend) *backend = "AVX512F_VPOPCNTDQ";
        return hamming_avx512_vpopcnt(a, b);
    }
    if (avx2_execution_eligible(e)) {
        if (backend) *backend = "AVX2_POPCNT";
        return hamming_avx2(a, b);
    }
#endif
    if (backend) *backend = "SCALAR_PORTABLE";
    return hamming_scalar(a, b);
}

double bipolar_similarity_from_hamming(std::uint32_t distance) {
    if (distance > kBits) throw std::invalid_argument("distance exceeds 1024 bits");
    return 1.0 - (2.0 * static_cast<double>(distance) / static_cast<double>(kBits));
}

std::string json_escape(const std::string& input) {
    std::string out;
    for (char c : input) {
        switch (c) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) out += '?';
                else out += c;
        }
    }
    return out;
}

std::string bool_json(bool value) { return value ? "true" : "false"; }

bool self_test() {
    CpuEvidence synthetic;
    synthetic.x86 = true;
    synthetic.avx = true;
    synthetic.avx2 = true;
    synthetic.popcnt = true;
    synthetic.osxsave = true;
    synthetic.xgetbv_observed = true;
    synthetic.xcr0 = 0x6;
    if (!avx2_execution_eligible(synthetic)) return false;
    synthetic.xcr0 = 0x2;
    if (avx2_execution_eligible(synthetic)) return false;

    synthetic.xcr0 = 0xE6;
    synthetic.avx512f = true;
    synthetic.avx512_vpopcntdq = true;
    if (!avx512_vpopcnt_execution_eligible(synthetic)) return false;
    synthetic.xcr0 = 0x66;
    if (avx512_vpopcnt_execution_eligible(synthetic)) return false;
    synthetic.xcr0 = 0xE6;
    synthetic.avx512_vpopcntdq = false;
    if (avx512_vpopcnt_execution_eligible(synthetic)) return false;

    std::array<std::uint64_t, kWords> a{};
    std::array<std::uint64_t, kWords> b{};
    for (std::size_t i = 0; i < kWords; ++i) {
        a[i] = 0x5555555555555555ULL ^ static_cast<std::uint64_t>(i * 0x0101010101010101ULL);
        b[i] = a[i];
    }
    b[0] ^= 0xFULL;
    const auto scalar = hamming_scalar(a, b);
    if (scalar != 4) return false;
    if (bipolar_similarity_from_hamming(scalar) != 1.0 - 8.0 / 1024.0) return false;

    const CpuEvidence observed = detect_cpu_evidence();
    std::string backend;
    const auto dispatched = hamming_dispatched(observed, a, b, &backend);
    if (dispatched != scalar) return false;
    if (backend != "SCALAR_PORTABLE" && backend != "AVX2_POPCNT" && backend != "AVX512F_VPOPCNTDQ") return false;
    return true;
}

void print_receipt() {
    const CpuEvidence cpu = detect_cpu_evidence();
    const CacheEvidence cache = detect_l2_cache_evidence();
    std::array<std::uint64_t, kWords> q{};
    std::array<std::uint64_t, kWords> c{};
    c.fill(~0ULL);
    std::string backend;
    const auto sample_distance = hamming_dispatched(cpu, q, c, &backend);
    const auto product_name = read_text("/sys/class/dmi/id/product_name").value_or("UNAVAILABLE");
    const bool thinkpad_name_observed = product_name.find("ThinkPad") != std::string::npos;
    const bool tile_le_l2 = cache.l2_observed && kProposedTileBytes <= cache.l2_size_bytes;

    std::cout << "{\n";
    std::cout << "  \"schema\": \"AuraK27ThinkPadSimdCapabilityObservationV1\",\n";
    std::cout << "  \"active_backend\": \"" << backend << "\",\n";
    std::cout << "  \"cpu_x86_observed\": " << bool_json(cpu.x86) << ",\n";
    std::cout << "  \"cpuid_osxsave\": " << bool_json(cpu.osxsave) << ",\n";
    std::cout << "  \"cpuid_avx\": " << bool_json(cpu.avx) << ",\n";
    std::cout << "  \"cpuid_popcnt\": " << bool_json(cpu.popcnt) << ",\n";
    std::cout << "  \"cpuid_avx2\": " << bool_json(cpu.avx2) << ",\n";
    std::cout << "  \"cpuid_avx512f\": " << bool_json(cpu.avx512f) << ",\n";
    std::cout << "  \"cpuid_avx512_vpopcntdq\": " << bool_json(cpu.avx512_vpopcntdq) << ",\n";
    std::cout << "  \"xgetbv_observed\": " << bool_json(cpu.xgetbv_observed) << ",\n";
    std::cout << "  \"xcr0\": " << cpu.xcr0 << ",\n";
    std::cout << "  \"avx2_execution_eligible\": " << bool_json(avx2_execution_eligible(cpu)) << ",\n";
    std::cout << "  \"avx512_vpopcnt_execution_eligible\": " << bool_json(avx512_vpopcnt_execution_eligible(cpu)) << ",\n";
    std::cout << "  \"l2_observed\": " << bool_json(cache.l2_observed) << ",\n";
    std::cout << "  \"l2_size_bytes\": " << cache.l2_size_bytes << ",\n";
    std::cout << "  \"l2_type\": \"" << json_escape(cache.l2_type) << "\",\n";
    std::cout << "  \"l2_shared_cpu_list\": \"" << json_escape(cache.l2_shared_cpu_list) << "\",\n";
    std::cout << "  \"proposed_tile_bytes\": " << kProposedTileBytes << ",\n";
    std::cout << "  \"proposed_tile_le_observed_l2_capacity\": " << bool_json(tile_le_l2) << ",\n";
    std::cout << "  \"l2_residency_proven\": false,\n";
    std::cout << "  \"p_core_only_proven\": false,\n";
    std::cout << "  \"thermal_reduction_proven\": false,\n";
    std::cout << "  \"performance_superiority_proven\": false,\n";
    std::cout << "  \"real_owner_thinkpad_benchmark_proven\": false,\n";
    std::cout << "  \"thinkpad_product_name_observed\": " << bool_json(thinkpad_name_observed) << ",\n";
    std::cout << "  \"product_name\": \"" << json_escape(product_name) << "\",\n";
    std::cout << "  \"sample_distance_1024\": " << sample_distance << ",\n";
    std::cout << "  \"effect_authority\": false,\n";
    std::cout << "  \"claim_ceiling\": \"HOST_OBSERVATION_AND_SAFE_DISPATCH_ONLY_NO_SPEED_THERMAL_CACHE_RESIDENCY_OR_AUTHORITY\"\n";
    std::cout << "}\n";
}

}  // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            if (!self_test()) {
                std::cerr << "SIMD_CAPABILITY_SELF_TEST=false\n";
                return 1;
            }
            std::cout << "SIMD_CAPABILITY_SELF_TEST=true\n";
            return 0;
        }
        if (argc != 1) {
            std::cerr << "usage: k27_thinkpad_simd_capability [--self-test]\n";
            return 2;
        }
        print_receipt();
        return 0;
    } catch (const std::exception& exc) {
        std::cerr << "typed_failure=" << exc.what() << "\n";
        return 1;
    }
}
