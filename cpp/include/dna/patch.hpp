#pragma once

#include "dna/common.hpp"

namespace dna {

struct VbmetaPatchResult {
    std::string image;
    std::string mode;
    uint32_t old_flags;
    uint32_t new_flags;
    bool modified;
    bool dry_run;
};

struct IntegrityPatchResult {
    std::string target;
    std::string fingerprint;
    std::string model;
    std::vector<std::string> modified_files;
    bool dry_run;
};

struct PrivappPatchResult {
    std::string target;
    std::string property_removed;
    std::vector<std::string> modified_files;
    std::string error;
    bool dry_run;
};

struct OtaPatchResult {
    std::string target;
    std::vector<std::string> modified_files;
    int count;
    std::string error;
    bool dry_run;
};

struct XiaomiServicesResult {
    std::string target;
    int total_removed;
    uint64_t total_freed_bytes;
    bool dry_run;
};

std::string find_partition_dir(const std::string& root_dir, const std::string& part_name);

VbmetaPatchResult patch_vbmeta(
    const std::string& image_path,
    const std::string& mode = "both",
    bool dry_run = false
);

IntegrityPatchResult patch_integrity_fix(
    const std::string& target_dir,
    const std::string& fingerprint = "",
    const std::string& model = "",
    bool dry_run = false
);

PrivappPatchResult patch_privapp_permissions(
    const std::string& target_dir,
    bool dry_run = false
);

OtaPatchResult patch_disable_ota(
    const std::string& target_dir,
    bool dry_run = false
);

XiaomiServicesResult patch_disable_xiaomi_services(
    const std::string& target_dir,
    bool dry_run = false
);

} // namespace dna
