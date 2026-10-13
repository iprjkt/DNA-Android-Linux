#include "dna/sparse.hpp"
#include <fstream>
#include <cstring>
#include <cmath>
#include <iomanip>
#include <stdexcept>
#include <cstdlib>

namespace dna {

static constexpr uint8_t SPARSE_MAGIC[4] = {0x3a, 0xff, 0x26, 0xed};

bool is_sparse_image(const std::string& file_path) {
    fs::path p(file_path);
    std::error_code ec;
    if (!fs::is_regular_file(p, ec) || fs::file_size(p, ec) < 4) {
        return false;
    }
    std::ifstream file(file_path, std::ios::binary);
    if (!file.is_open()) return false;
    uint8_t magic[4];
    file.read(reinterpret_cast<char*>(magic), 4);
    return file.gcount() == 4 && std::memcmp(magic, SPARSE_MAGIC, 4) == 0;
}

std::string merge_sparse_chunks(
    const std::vector<std::string>& chunk_paths,
    const std::string& out_image
) {
    if (chunk_paths.empty()) {
        throw std::invalid_argument("No sparse chunks provided to merge.");
    }
    std::vector<std::string> sorted_chunks = chunk_paths;
    std::sort(sorted_chunks.begin(), sorted_chunks.end());

    fs::path dst(out_image);
    if (dst.has_parent_path()) {
        fs::create_directories(dst.parent_path());
    }

    if (is_sparse_image(sorted_chunks.front())) {
        std::string cmd = "simg2img";
        for (const auto& c : sorted_chunks) {
            cmd += " \"" + c + "\"";
        }
        cmd += " \"" + out_image + "\"";
        int ret = std::system(cmd.c_str());
        if (ret != 0) {
            throw std::runtime_error("simg2img failed to merge sparse chunks with exit code: " + std::to_string(ret));
        }
    } else {
        std::ofstream out_f(out_image, std::ios::binary);
        if (!out_f.is_open()) {
            throw std::runtime_error("Failed to open destination image for writing: " + out_image);
        }
        std::vector<char> buffer(1024 * 1024); // 1 MB buffer for fast I/O
        for (const auto& c : sorted_chunks) {
            std::ifstream in_f(c, std::ios::binary);
            if (!in_f.is_open()) {
                throw std::runtime_error("Failed to open chunk file: " + c);
            }
            while (in_f.read(buffer.data(), buffer.size()) || in_f.gcount() > 0) {
                out_f.write(buffer.data(), in_f.gcount());
            }
        }
    }
    return out_image;
}

std::vector<std::string> split_sparse_image(
    const std::string& file_path,
    const std::string& out_dir,
    int parts,
    const std::string& prefix
) {
    fs::path src(file_path);
    fs::path target_dir(out_dir);
    fs::create_directories(target_dir);

    if (parts < 2 || parts > 30) {
        throw std::invalid_argument("Number of parts must be between 2 and 30 (got " + std::to_string(parts) + ")");
    }

    std::string base_name = prefix.empty() ? src.filename().string() : prefix;
    std::error_code ec;
    uint64_t total_size = fs::file_size(src, ec);
    if (ec) {
        throw std::runtime_error("Cannot get size of file: " + file_path);
    }

    uint64_t chunk_size = (total_size + parts - 1) / parts;
    // 4096-byte block alignment
    chunk_size = ((chunk_size + 4095) / 4096) * 4096;

    std::ifstream in_f(file_path, std::ios::binary);
    if (!in_f.is_open()) {
        throw std::runtime_error("Failed to open source image for splitting: " + file_path);
    }

    std::vector<std::string> output_chunks;
    std::vector<char> buffer(65536);
    int chunk_idx = 0;

    while (in_f.peek() != EOF) {
        std::ostringstream filename;
        filename << base_name << "." << std::setfill('0') << std::setw(2) << chunk_idx;
        fs::path chunk_path = target_dir / filename.str();

        std::ofstream out_f(chunk_path, std::ios::binary);
        if (!out_f.is_open()) {
            throw std::runtime_error("Failed to create chunk file: " + chunk_path.string());
        }

        uint64_t written = 0;
        while (written < chunk_size && in_f.peek() != EOF) {
            uint64_t to_read = std::min<uint64_t>(buffer.size(), chunk_size - written);
            in_f.read(buffer.data(), to_read);
            std::streamsize bytes = in_f.gcount();
            if (bytes <= 0) break;
            out_f.write(buffer.data(), bytes);
            written += bytes;
        }

        output_chunks.push_back(chunk_path.string());
        chunk_idx++;
    }

    return output_chunks;
}

} // namespace dna
