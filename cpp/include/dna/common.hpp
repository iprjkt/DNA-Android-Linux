#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <filesystem>
#include <functional>
#include <optional>
#include <memory>
#include <sstream>
#include <algorithm>

namespace fs = std::filesystem;

namespace dna {

inline std::string trim(const std::string& str) {
    const auto str_begin = str.find_first_not_of(" \t\r\n");
    if (str_begin == std::string::npos) return "";
    const auto str_end = str.find_last_not_of(" \t\r\n");
    return str.substr(str_begin, str_end - str_begin + 1);
}

inline std::vector<std::string> split(const std::string& s, char delimiter) {
    std::vector<std::string> tokens;
    std::string token;
    std::istringstream tokenStream(s);
    while (std::getline(tokenStream, token, delimiter)) {
        tokens.push_back(token);
    }
    return tokens;
}

inline uint32_t swap_uint32(uint32_t val) {
    return ((val >> 24) & 0xff) |
           ((val << 8) & 0xff0000) |
           ((val >> 8) & 0xff00) |
           ((val << 24) & 0xff000000);
}

inline uint16_t swap_uint16(uint16_t val) {
    return (val << 8) | (val >> 8);
}

} // namespace dna
