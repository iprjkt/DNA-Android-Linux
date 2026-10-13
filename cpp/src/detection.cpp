#include "dna/detection.hpp"
#include <fstream>
#include <cstring>
#include <iomanip>

namespace dna {

static constexpr uint8_t SPARSE_MAGIC[4] = {0x3a, 0xff, 0x26, 0xed}; // 0xed26ff3a
static constexpr uint8_t EXT4_MAGIC[2] = {0x53, 0xef};               // 0xef53 at 1080 (0x438)
static constexpr uint8_t EROFS_MAGIC[4] = {0xe2, 0xe1, 0xf5, 0xe0};  // 0xe0f5e1e2 at 1024 (0x400)
static constexpr uint8_t F2FS_MAGIC[4] = {0x10, 0x20, 0xf5, 0xf2};   // 0xf2f52010 at 1024 (0x400)
static constexpr char LP_GEOMETRY_MAGIC[4] = {'g', 'D', 'l', 'a'};   // 0x616c4467 at 4096 (0x1000)
static constexpr char LP_GEOMETRY_MAGIC_ALT[4] = {'L', 'D', 'l', 'a'}; // 0x616c444c at 4096 or 0
static constexpr char PAYLOAD_MAGIC[4] = {'C', 'r', 'A', 'U'};       // CrAU at 0
static constexpr uint8_t ZSTD_MAGIC[4] = {0x28, 0xb5, 0x2f, 0xfd};   // 0xFD2FB528 at 0

ImageType detect_image_type(const std::string& file_path) {
    fs::path p(file_path);
    std::error_code ec;
    if (!fs::is_regular_file(p, ec)) {
        return ImageType::UNKNOWN;
    }

    auto size = fs::file_size(p, ec);
    if (ec || size < 4) {
        return ImageType::UNKNOWN;
    }

    std::string ext = p.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (ext == ".br") return ImageType::BROTLI;
    if (ext == ".zst" || ext == ".zstd") return ImageType::ZSTD;

    std::string filename = p.filename().string();
    if (filename.ends_with(".new.dat")) return ImageType::DAT;

    std::ifstream file(file_path, std::ios::binary);
    if (!file.is_open()) {
        return ImageType::UNKNOWN;
    }

    uint8_t header[8192];
    file.read(reinterpret_cast<char*>(header), sizeof(header));
    std::streamsize bytes_read = file.gcount();

    // 1. Android Sparse Image Magic
    if (bytes_read >= 4 && std::memcmp(header, SPARSE_MAGIC, 4) == 0) {
        return ImageType::SPARSE;
    }

    // 2. Android OTA payload.bin Magic
    if (bytes_read >= 4 && std::memcmp(header, PAYLOAD_MAGIC, 4) == 0) {
        return ImageType::PAYLOAD_BIN;
    }

    // 3. Zstandard Magic
    if (bytes_read >= 4 && std::memcmp(header, ZSTD_MAGIC, 4) == 0) {
        return ImageType::ZSTD;
    }

    // 4. Super LP Geometry Magic at 4096 or 0
    if (bytes_read >= 4100) {
        if (std::memcmp(header + 4096, LP_GEOMETRY_MAGIC, 4) == 0 ||
            std::memcmp(header + 4096, LP_GEOMETRY_MAGIC_ALT, 4) == 0) {
            return ImageType::SUPER_LP;
        }
    }
    if (bytes_read >= 4) {
        if (std::memcmp(header, LP_GEOMETRY_MAGIC, 4) == 0 ||
            std::memcmp(header, LP_GEOMETRY_MAGIC_ALT, 4) == 0) {
            return ImageType::SUPER_LP;
        }
    }

    // 5. Superblock filesystems at 1024
    if (bytes_read >= 1084) {
        if (std::memcmp(header + 1024, EROFS_MAGIC, 4) == 0) {
            return ImageType::EROFS_FS;
        }
        if (std::memcmp(header + 1024, F2FS_MAGIC, 4) == 0) {
            return ImageType::F2FS_FS;
        }
        if (std::memcmp(header + 1080, EXT4_MAGIC, 2) == 0) {
            return ImageType::EXT4;
        }
    }

    return ImageType::UNKNOWN;
}

ImageInfo inspect_image(const std::string& file_path) {
    fs::path p(file_path);
    ImageType type = detect_image_type(file_path);
    std::error_code ec;
    uint64_t size = fs::is_regular_file(p, ec) ? fs::file_size(p, ec) : 0;

    std::string fs_type = "";
    if (type == ImageType::EXT4) fs_type = "ext4";
    else if (type == ImageType::EROFS_FS) fs_type = "erofs";
    else if (type == ImageType::F2FS_FS) fs_type = "f2fs";
    else if (type == ImageType::SUPER_LP) fs_type = "super_lp";

    std::ostringstream desc;
    desc << image_type_to_string(type) << " image ("
         << std::fixed << std::setprecision(1)
         << (static_cast<double>(size) / (1024.0 * 1024.0)) << " MB)";

    return ImageInfo{
        .path = file_path,
        .image_type = type,
        .size_bytes = size,
        .is_sparse = (type == ImageType::SPARSE),
        .fs_type = fs_type,
        .description = desc.str()
    };
}

} // namespace dna
