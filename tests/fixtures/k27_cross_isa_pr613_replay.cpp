/* Replay the frozen K27 Hamming corpus through exact PR613 source in one TU.

The workflow materializes PR613's exact semantic source as pr613_exact.cpp beside
this file. Renaming its main keeps every internal/anonymous-namespace Hamming
function in the same translation unit without copying or reimplementing it.
*/
#define main pr613_capability_original_main
#include "pr613_exact.cpp"
#undef main

#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::vector<std::string> split(const std::string& value, char delimiter) {
    std::vector<std::string> out;
    std::stringstream stream(value);
    std::string piece;
    while (std::getline(stream, piece, delimiter)) out.push_back(piece);
    return out;
}

std::array<std::uint64_t, 16> parse_words(const std::string& field) {
    const auto pieces = split(field, ',');
    if (pieces.size() != 16) throw std::runtime_error("expected 16 words");
    std::array<std::uint64_t, 16> result{};
    for (std::size_t i = 0; i < pieces.size(); ++i) {
        std::size_t consumed = 0;
        result[i] = std::stoull(pieces[i], &consumed, 16);
        if (consumed != pieces[i].size()) throw std::runtime_error("invalid hex word");
    }
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: replay <corpus.tsv>\n";
        return 2;
    }
    std::ifstream input(argv[1]);
    if (!input) {
        std::cerr << "cannot open corpus\n";
        return 2;
    }

    const CpuEvidence observed = detect_cpu_evidence();
    std::string line;
    std::size_t count = 0;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        const auto fields = split(line, '\t');
        if (fields.size() != 4) {
            std::cerr << "bad corpus row\n";
            return 3;
        }
        const auto expected = static_cast<std::uint32_t>(std::stoul(fields[1]));
        const auto a = parse_words(fields[2]);
        const auto b = parse_words(fields[3]);
        const auto scalar = hamming_scalar(a, b);
        std::string backend;
        const auto dispatched = hamming_dispatched(observed, a, b, &backend);
        if (scalar != expected || dispatched != scalar) {
            std::cerr << fields[0] << " mismatch expected=" << expected << " scalar=" << scalar << " dispatched=" << dispatched << "\n";
            return 4;
        }
        std::cout << fields[0] << '\t' << scalar << '\t' << dispatched << '\t' << backend << '\n';
        ++count;
    }
    if (count != 8) {
        std::cerr << "expected eight replay rows, got " << count << "\n";
        return 5;
    }
    return 0;
}
