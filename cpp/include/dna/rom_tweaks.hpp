#pragma once

#include "dna/common.hpp"

namespace dna {

struct RomRwResult {
    std::vector<std::string> fstab_files_modified;
    int overlay_lines_removed;
    std::vector<std::string> init_scripts_removed;
    std::vector<std::string> unshared_ext4_images;
    bool dry_run;
};

struct RomDecryptResult {
    std::vector<std::string> fstab_files_modified;
    int lines_modified;
    bool dry_run;
};

std::pair<std::vector<std::string>, uint64_t> remove_oat_directories(
    const std::string& target_root,
    bool dry_run = false
);

RomRwResult make_rom_rw(
    const std::string& target_root,
    bool dry_run = false
);

RomDecryptResult decrypt_rom(
    const std::string& target_root,
    bool dry_run = false
);

} // namespace dna
