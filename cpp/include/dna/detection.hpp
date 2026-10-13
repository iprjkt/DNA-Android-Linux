#pragma once

#include "dna/common.hpp"

#ifdef EROFS
#undef EROFS
#endif

namespace dna {

enum class ImageType {
    SPARSE,
    EXT4,
    EROFS_FS,
    F2FS_FS,
    SUPER_LP,
    PAYLOAD_BIN,
    BROTLI,
    ZSTD,
    DAT,
    UNKNOWN
};

inline std::string image_type_to_string(ImageType type) {
    switch (type) {
        case ImageType::SPARSE: return "sparse";
        case ImageType::EXT4: return "ext4";
        case ImageType::EROFS_FS: return "erofs";
        case ImageType::F2FS_FS: return "f2fs";
        case ImageType::SUPER_LP: return "super_lp";
        case ImageType::PAYLOAD_BIN: return "payload_bin";
        case ImageType::BROTLI: return "brotli";
        case ImageType::ZSTD: return "zstd";
        case ImageType::DAT: return "dat";
        default: return "unknown";
    }
}

inline ImageType string_to_image_type(const std::string& str) {
    if (str == "sparse") return ImageType::SPARSE;
    if (str == "ext4") return ImageType::EXT4;
    if (str == "erofs") return ImageType::EROFS_FS;
    if (str == "f2fs") return ImageType::F2FS_FS;
    if (str == "super_lp") return ImageType::SUPER_LP;
    if (str == "payload_bin") return ImageType::PAYLOAD_BIN;
    if (str == "brotli") return ImageType::BROTLI;
    if (str == "zstd") return ImageType::ZSTD;
    if (str == "dat") return ImageType::DAT;
    return ImageType::UNKNOWN;
}

struct ImageInfo {
    std::string path;
    ImageType image_type;
    uint64_t size_bytes;
    bool is_sparse;
    std::string fs_type;
    std::string description;
};

ImageType detect_image_type(const std::string& file_path);
ImageInfo inspect_image(const std::string& file_path);

} // namespace dna
