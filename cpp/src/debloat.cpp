#include "dna/debloat.hpp"
#include <iostream>

namespace dna {

static const std::string BANNER_DEBLOAT =
    "  ___       _     _             _   _            \n"
    " |   \\ ___ | |__ | | ___  __ _ | |_(_) _ _   __ _ \n"
    " | |) / -_)| '_ \\| |/ _ \\/ _` ||  _| || ' \\ / _` |\n"
    " |___/\\___||_.__/|_|\\___/\\__,_| \\__|_||_||_|\\__, |\n"
    "                                            |___/ ";

uint64_t calculate_directory_size(const std::string& path) {
    fs::path p(path);
    std::error_code ec;
    if (!fs::is_directory(p, ec)) return 0;

    uint64_t total = 0;
    for (const auto& entry : fs::recursive_directory_iterator(p, fs::directory_options::skip_permission_denied, ec)) {
        if (entry.is_regular_file(ec) && !entry.is_symlink(ec)) {
            total += entry.file_size(ec);
        }
    }
    return total;
}

DebloatResult run_debloat(
    const std::string& target_root,
    const DebloatPreset& preset,
    bool dry_run
) {
    std::cout << BANNER_DEBLOAT << "\n\n";
    std::cout << "Removing bloatware please wait...\n\n";

    fs::path root(target_root);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::error_code ec;
    if (!fs::is_directory(eff_root, ec)) {
        std::cout << "find: '" << base_dir.string() << "': No such file or directory\n\n";
        std::cout << "[✓] Debloating complete\n\n";
        return DebloatResult{preset.name, {}, 0, {}, dry_run};
    }

    // Check partitions
    for (const auto& p_name : {"system", "product"}) {
        bool has_part = fs::is_directory(eff_root / p_name, ec) ||
                        fs::is_directory(eff_root / (std::string(p_name) + "_a"), ec) ||
                        fs::is_directory(base_dir / p_name, ec) ||
                        fs::is_directory(base_dir / (std::string(p_name) + "_a"), ec);
        if (!has_part) {
            std::cout << "find: '" << (base_dir / p_name).string() << "': No such file or directory\n";
        }
    }

    std::vector<std::string> removed;
    std::vector<std::string> affected_packages;
    uint64_t total_freed = 0;

    // Scan patterns
    for (const auto& pkg : preset.packages) {
        bool pkg_matched = false;
        for (const auto& pattern : pkg.patterns) {
            // For each pattern, e.g. "product/priv-app/YellowPage"
            fs::path cand = eff_root / pattern;
            if (fs::is_directory(cand, ec) && std::find(removed.begin(), removed.end(), cand.string()) == removed.end()) {
                uint64_t size = calculate_directory_size(cand.string());
                total_freed += size;
                removed.push_back(cand.string());
                pkg_matched = true;
                std::cout << "Removing: ./" << fs::relative(cand, eff_root).string()
                          << " (Package: " << pkg.name << ")\n";
                if (!dry_run) {
                    fs::remove_all(cand, ec);
                }
            }
        }
        if (pkg_matched) {
            affected_packages.push_back(pkg.name);
        }
    }

    std::cout << "[✓] Debloating complete\n\n";

    return DebloatResult{
        .preset_name = preset.name,
        .removed_directories = removed,
        .freed_bytes = total_freed,
        .packages_affected = affected_packages,
        .dry_run = dry_run
    };
}

} // namespace dna
