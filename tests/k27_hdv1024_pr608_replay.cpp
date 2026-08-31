// Adapter that reuses PR608's actual scalar/SIMD implementation for corpus replay.
// This does not define byte/ISA mapping; argv values are already logical u64 words.
#define main aura_pr608_original_main
#include "../tools/k27/thinkpad_portable_simd_dispatch.cpp"
#undef main

#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    using namespace aura::k27;
    if (argc != 33) {
        std::cerr << "expected 32 lowercase/uppercase hexadecimal u64 words\n";
        return EXIT_FAILURE;
    }

    std::array<std::uint64_t, kWords> a{};
    std::array<std::uint64_t, kWords> b{};
    try {
        for (std::size_t i = 0; i < kWords; ++i) {
            std::size_t used = 0;
            a[i] = std::stoull(argv[1 + i], &used, 16);
            if (used != std::string(argv[1 + i]).size()) throw std::invalid_argument("a");
            used = 0;
            b[i] = std::stoull(argv[17 + i], &used, 16);
            if (used != std::string(argv[17 + i]).size()) throw std::invalid_argument("b");
        }
    } catch (...) {
        std::cerr << "invalid hexadecimal word\n";
        return EXIT_FAILURE;
    }

    const auto state = detect_vector_state();
    const auto scalar = hamming_scalar(a.data(), b.data());
    const auto selected = hamming_selected(state, a.data(), b.data());
    std::cout << scalar << ' ' << selected << ' ' << path_name(choose_path(state)) << '\n';
    return scalar == selected ? EXIT_SUCCESS : EXIT_FAILURE;
}
