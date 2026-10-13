#pragma once

#include "dna/common.hpp"

namespace dna {

struct FsConfigEntry {
    std::string path;
    uint32_t uid;
    uint32_t gid;
    std::string mode;
    std::string capabilities;

    std::string serialize() const;
};

struct FsMetadataResult {
    std::vector<FsConfigEntry> fs_entries;
    std::vector<std::pair<std::string, std::string>> fc_entries;
};

FsMetadataResult scan_directory_fs_metadata(
    const std::string& root_dir,
    const std::string& mount_point = "system"
);

std::string write_fs_config_file(
    const std::vector<FsConfigEntry>& entries,
    const std::string& target_file
);

std::string write_file_contexts_file(
    const std::vector<std::pair<std::string, std::string>>& entries,
    const std::string& target_file
);

} // namespace dna
