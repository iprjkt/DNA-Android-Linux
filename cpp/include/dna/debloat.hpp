#pragma once

#include "dna/common.hpp"

namespace dna {

struct DebloatPackage {
    std::string name;
    std::vector<std::string> patterns;
    std::string description;
};

struct DebloatPreset {
    std::string name;
    std::string description;
    std::vector<DebloatPackage> packages;
};

struct DebloatResult {
    std::string preset_name;
    std::vector<std::string> removed_directories;
    uint64_t freed_bytes;
    std::vector<std::string> packages_affected;
    bool dry_run;
};

uint64_t calculate_directory_size(const std::string& path);

DebloatResult run_debloat(
    const std::string& target_root,
    const DebloatPreset& preset,
    bool dry_run = false
);

} // namespace dna
