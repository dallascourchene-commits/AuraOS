// K27 ThinkPad SIMD benchmark evidence harness.
//
// This file does not own a Hamming implementation. The exact PR608 source is
// injected at compile time through K27_PR608_SOURCE and is then exercised on a
// deterministic, matched workload. Timings are descriptive evidence for the
// host that executed this process; they do not prove ThinkPad performance,
// cache residency, P-core placement, thermal/power effects, or superiority.

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <string_view>
#include <sys/utsname.h>
#include <vector>

#ifndef K27_PR608_SOURCE
#error "K27_PR608_SOURCE must name the exact PR608 source file"
#endif

#define main aura_pr608_embedded_main
#include K27_PR608_SOURCE
#undef main

namespace {

using aura::k27::CpuVectorState;
using aura::k27::DispatchPath;
using aura::k27::kWords;

constexpr std::size_t kCentroids = 4096;
constexpr std::size_t kWarmupRounds = 4;
constexpr std::size_t kMeasureSamples = 11;
constexpr std::size_t kRepetitionsPerSample = 64;
constexpr std::uint64_t kSeed = 0xA8275EED20260831ULL;
constexpr std::string_view kPr608Head =
    "bb7d8849112c1c992c64b3078f3df0d84b8ff60b";
constexpr std::string_view kPr608Blob =
    "96e523682b7d6a0b3e2c3d850bc4d8bafa58b97c";
constexpr std::string_view kWorkloadId =
    "K27_HDV1024_SIMD_MATCHED_COMPUTE_V1_SEED_A8275EED20260831_C4096";

using Vector = std::array<std::uint64_t, kWords>;
using HammingFn = std::uint32_t (*)(const std::uint64_t*, const std::uint64_t*);

std::uint64_t splitmix64(std::uint64_t& state) {
    std::uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30U)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27U)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31U);
}

struct Workload {
    Vector query{};
    std::vector<Vector> centroids;
};

Workload make_workload() {
    Workload out;
    out.centroids.resize(kCentroids);
    std::uint64_t state = kSeed;
    for (auto& word : out.query) {
        word = splitmix64(state);
    }
    for (auto& centroid : out.centroids) {
        for (auto& word : centroid) {
            word = splitmix64(state);
        }
    }
    return out;
}

std::uint64_t run_batch(
    HammingFn fn,
    const Workload& workload,
    std::size_t repetitions) {
    std::uint64_t checksum = 0;
    for (std::size_t r = 0; r < repetitions; ++r) {
        for (std::size_t i = 0; i < workload.centroids.size(); ++i) {
            const auto d = fn(workload.query.data(), workload.centroids[i].data());
            checksum += static_cast<std::uint64_t>(d) * (i + 1U) + r;
        }
    }
    return checksum;
}

struct TimedResult {
    std::uint64_t elapsed_ns = 0;
    std::uint64_t checksum = 0;
};

TimedResult time_batch(HammingFn fn, const Workload& workload) {
    const auto start = std::chrono::steady_clock::now();
    const auto checksum = run_batch(fn, workload, kRepetitionsPerSample);
    const auto stop = std::chrono::steady_clock::now();
    return {
        static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::nanoseconds>(stop - start).count()),
        checksum,
    };
}

std::uint64_t median(std::vector<std::uint64_t> values) {
    std::sort(values.begin(), values.end());
    return values.at(values.size() / 2U);
}

std::string cpu_model() {
    std::ifstream in("/proc/cpuinfo");
    std::string line;
    while (std::getline(in, line)) {
        constexpr std::string_view key = "model name";
        if (line.rfind(key, 0) == 0) {
            const auto pos = line.find(':');
            if (pos != std::string::npos) {
                auto value = line.substr(pos + 1U);
                while (!value.empty() && value.front() == ' ') {
                    value.erase(value.begin());
                }
                return value;
            }
        }
    }
    return "UNKNOWN";
}

std::string uname_string() {
    struct utsname u {};
    if (uname(&u) != 0) {
        return "UNKNOWN";
    }
    std::ostringstream out;
    out << u.sysname << ' ' << u.release << ' ' << u.machine;
    return out.str();
}

HammingFn selected_function(DispatchPath path) {
    using namespace aura::k27;
    switch (path) {
        case DispatchPath::Avx512Vpopcntdq:
            return &hamming_avx512_vpopcntdq;
        case DispatchPath::Avx2Popcnt:
            return &hamming_avx2_popcnt;
        case DispatchPath::Scalar:
        default:
            return &hamming_scalar;
    }
}

}  // namespace

int main() {
    using namespace aura::k27;

    const Workload workload = make_workload();
    const CpuVectorState state = detect_vector_state();
    const DispatchPath selected_path = choose_path(state);
    const HammingFn scalar_fn = &hamming_scalar;
    const HammingFn selected_fn = selected_function(selected_path);

    const auto scalar_one = run_batch(scalar_fn, workload, 1);
    const auto selected_one = run_batch(selected_fn, workload, 1);
    if (scalar_one != selected_one) {
        std::cerr << "MATCHED_WORKLOAD_CONSEQUENCE_MISMATCH\n";
        return EXIT_FAILURE;
    }

    for (std::size_t i = 0; i < kWarmupRounds; ++i) {
        if (run_batch(scalar_fn, workload, 1) != scalar_one ||
            run_batch(selected_fn, workload, 1) != selected_one) {
            std::cerr << "WARMUP_CONSEQUENCE_DRIFT\n";
            return EXIT_FAILURE;
        }
    }

    std::vector<std::uint64_t> scalar_times;
    std::vector<std::uint64_t> selected_times;
    scalar_times.reserve(kMeasureSamples);
    selected_times.reserve(kMeasureSamples);
    std::uint64_t expected_sample_checksum = 0;

    for (std::size_t sample = 0; sample < kMeasureSamples; ++sample) {
        TimedResult scalar{};
        TimedResult selected{};
        if ((sample & 1U) == 0U) {
            scalar = time_batch(scalar_fn, workload);
            selected = time_batch(selected_fn, workload);
        } else {
            selected = time_batch(selected_fn, workload);
            scalar = time_batch(scalar_fn, workload);
        }
        if (scalar.checksum != selected.checksum) {
            std::cerr << "TIMED_CONSEQUENCE_MISMATCH sample=" << sample << '\n';
            return EXIT_FAILURE;
        }
        if (sample == 0) {
            expected_sample_checksum = scalar.checksum;
        } else if (scalar.checksum != expected_sample_checksum) {
            std::cerr << "TIMED_CHECKSUM_DRIFT sample=" << sample << '\n';
            return EXIT_FAILURE;
        }
        scalar_times.push_back(scalar.elapsed_ns);
        selected_times.push_back(selected.elapsed_ns);
    }

    const auto scalar_median = median(scalar_times);
    const auto selected_median = median(selected_times);
    const double observed_ratio = selected_median == 0
        ? 0.0
        : static_cast<double>(scalar_median) / static_cast<double>(selected_median);

    std::cout << "SCHEMA=AURA_K27_THINKPAD_SIMD_BENCHMARK_EVIDENCE_V1\n";
    std::cout << "PR608_EXACT_HEAD=" << kPr608Head << '\n';
    std::cout << "PR608_SOURCE_BLOB=" << kPr608Blob << '\n';
    std::cout << "WORKLOAD_ID=" << kWorkloadId << '\n';
    std::cout << "CENTROIDS=" << kCentroids << '\n';
    std::cout << "CENTROID_PAYLOAD_BYTES="
              << (kCentroids * kWords * sizeof(std::uint64_t)) << '\n';
    std::cout << "WARMUP_ROUNDS=" << kWarmupRounds << '\n';
    std::cout << "MEASURE_SAMPLES=" << kMeasureSamples << '\n';
    std::cout << "REPETITIONS_PER_SAMPLE=" << kRepetitionsPerSample << '\n';
    std::cout << "SELECTED_PATH=" << path_name(selected_path) << '\n';
    std::cout << "CPUID_AVX2=" << state.cpuid_avx2 << '\n';
    std::cout << "CPUID_AVX512F=" << state.cpuid_avx512f << '\n';
    std::cout << "CPUID_AVX512_VPOPCNTDQ=" << state.cpuid_avx512_vpopcntdq << '\n';
    std::cout << "OSXSAVE=" << state.osxsave << '\n';
    std::cout << "XMM_YMM_STATE=" << state.xmm_ymm_state << '\n';
    std::cout << "ZMM_STATE=" << state.zmm_state << '\n';
    std::cout << "CPU_MODEL=" << cpu_model() << '\n';
    std::cout << "UNAME=" << uname_string() << '\n';
    std::cout << "SEMANTIC_CHECKSUM=" << expected_sample_checksum << '\n';
    std::cout << "SCALAR_MEDIAN_NS=" << scalar_median << '\n';
    std::cout << "SELECTED_MEDIAN_NS=" << selected_median << '\n';
    std::cout << std::fixed << std::setprecision(6)
              << "OBSERVED_SCALAR_OVER_SELECTED_MEDIAN_RATIO=" << observed_ratio << '\n';
    std::cout << "MATCHED_WORKLOAD_CONSEQUENCE_EQUIVALENT=true\n";
    std::cout << "WARMUP_PERFORMED=true\n";
    std::cout << "CACHE_STATE_CONTROLLED=false\n";
    std::cout << "HOSTED_RUNNER_COMPUTE_TIMING_OBSERVED=true\n";
    std::cout << "OWNER_THINKPAD_HOST_AUTHENTICATED=false\n";
    std::cout << "THINKPAD_PERFORMANCE_PROVEN=false\n";
    std::cout << "PERFORMANCE_SUPERIORITY_PROVEN=false\n";
    std::cout << "P_CORE_ONLY_OBSERVED=false\n";
    std::cout << "CACHE_RESIDENCY_PROVEN=false\n";
    std::cout << "THERMAL_POWER_EFFECT_PROVEN=false\n";
    std::cout << "PHYSICAL_NVME_EFFECT_PROVEN=false\n";
    std::cout << "SEMANTIC_K27_AUTHORITY=false\n";
    std::cout << "NATIVE_PRIVATE_TRANSFORMER_KV_ACCESSED=false\n";
    std::cout << "GATE10_PROMOTED=false\n";
    return EXIT_SUCCESS;
}
