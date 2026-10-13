#pragma once

#include "dna/common.hpp"

namespace dna {

bool is_sparse_image(const std::string& file_path);

std::string merge_sparse_chunks(
    const std::vector<std::string>& chunk_paths,
    const std::string& out_image
);

std::vector<std::string> split_sparse_image(
    const std::string& file_path,
    const std::string& out_dir,
    int parts = 12,
    const std::string& prefix = ""
);

} // namespace dna
