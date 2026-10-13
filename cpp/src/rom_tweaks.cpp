#include "dna/rom_tweaks.hpp"
#include "dna/debloat.hpp"
#include <iostream>
#include <fstream>
#include <regex>

namespace dna {

static const std::string BANNER_OAT =
    "  ___                                ___    _ _____ \n"
    " | _ \\___ _ __  _____ _____ ___     / _ \\  /_\\_   _|\n"
    " |   / -_) '  \\/ _ \\ V / -_) -_)   | (_) |/ _ \\| |  \n"
    " |_|_\\___|_|_|_\\___/\\_/\\___|___|    \\___//_/ \\_\\_|  ";

static const std::string BANNER_ROM_RW =
    "  __  __      _         ___  ___  __  __     _____      __\n"
    " |  \\/  |__ _| |_____  | _ \\/ _ \\|  \\/  |___ | _ \\ \\    / /\n"
    " | |\\/| / _` | / / -_) |   / (_) | |\\/| |___||   /\\ \\/\\/ / \n"
    " |_|  |_\\__,_|_\\_\\___| |_|_\\\\___/|_|  |_|    |_|_\\ \\_/\\_/  ";

static const std::string BANNER_DECRYPT =
    "  ___                          _      ___  ___  __  __ \n"
    " |   \\ ___  __ _ _ _  _ _  ___| |_   | _ \\/ _ \\|  \\/  |\n"
    " | |) / -_)/ _| '_| || | '_ \\  _|    |   / (_) | |\\/| |\n"
    " |___/\\___|\\__|_|  \\_, | .__/\\__|    |_|_\\\\___/|_|  |_|\n"
    "                   |__/|_|                             ";

std::pair<std::vector<std::string>, uint64_t> remove_oat_directories(
    const std::string& target_root,
    bool dry_run
) {
    std::cout << BANNER_OAT << "\n\n";
    std::cout << "Searching for oat directories...\n\n";

    fs::path root(target_root);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::error_code ec;
    if (!fs::is_directory(eff_root, ec)) {
        std::cout << "find: '" << base_dir.string() << "': No such file or directory\n\n";
        std::cout << "No oat directories found in: " << base_dir.string() << "\n\n";
        return {{}, 0};
    }

    std::vector<std::string> removed;
    uint64_t freed_bytes = 0;

    for (const auto& entry : fs::recursive_directory_iterator(eff_root, fs::directory_options::skip_permission_denied, ec)) {
        if (entry.is_directory(ec) && entry.path().filename() == "oat") {
            uint64_t size = calculate_directory_size(entry.path().string());
            freed_bytes += size;
            removed.push_back(entry.path().string());
            double mb = static_cast<double>(size) / (1024.0 * 1024.0);
            std::cout << "Removing: " << fs::relative(entry.path(), eff_root).string()
                      << " (" << mb << " MB)\n";
            if (!dry_run) {
                fs::remove_all(entry.path(), ec);
            }
        }
    }

    if (!removed.empty()) {
        double total_mb = static_cast<double>(freed_bytes) / (1024.0 * 1024.0);
        std::cout << "[✓] Removed " << removed.size() << " oat directories (" << total_mb << " MB freed)\n\n";
    } else {
        std::cout << "No oat directories found in: " << eff_root.string() << "\n\n";
    }

    return {removed, freed_bytes};
}

RomRwResult make_rom_rw(
    const std::string& target_root,
    bool dry_run
) {
    std::cout << BANNER_ROM_RW << "\n\n";

    fs::path root(target_root);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::error_code ec;
    if (!fs::is_directory(eff_root, ec)) {
        std::cout << "find: '" << base_dir.string() << "': No such file or directory\n";
        std::cout << "stat: '" << (base_dir / "vendor" / "etc" / "fstab*").string() << "': No such file or directory\n";
        std::cout << "Error: fstab files not found at " << (base_dir / "vendor" / "etc" / "fstab*").string() << "\n\n";
        return RomRwResult{{}, 0, {}, {}, dry_run};
    }

    std::vector<std::string> modified_fstabs;
    int total_overlay_lines = 0;
    std::vector<std::string> removed_inits;

    std::vector<fs::path> fstabs;
    for (const auto& entry : fs::recursive_directory_iterator(eff_root, fs::directory_options::skip_permission_denied, ec)) {
        if (entry.is_regular_file(ec)) {
            std::string name = entry.path().filename().string();
            if (name.rfind("fstab", 0) == 0 && !name.ends_with(".bak")) {
                fstabs.push_back(entry.path());
            }
        }
    }

    if (fstabs.empty()) {
        std::cout << "stat: '" << (base_dir / "vendor" / "etc" / "fstab*").string() << "': No such file or directory\n";
        std::cout << "Error: fstab files not found at " << (base_dir / "vendor" / "etc" / "fstab*").string() << "\n";
    }

    for (const auto& fstab : fstabs) {
        std::ifstream in(fstab);
        std::vector<std::string> lines;
        std::string line;
        int changed = 0;
        while (std::getline(in, line)) {
            if (line.find("overlay") != std::string::npos && !line.starts_with("#")) {
                changed++;
                total_overlay_lines++;
                continue; // strip overlay line
            }
            lines.push_back(line);
        }
        in.close();

        if (changed > 0) {
            modified_fstabs.push_back(fstab.string());
            if (!dry_run) {
                std::ofstream out(fstab);
                for (const auto& l : lines) out << l << "\n";
            }
            std::cout << "Removed " << changed << " overlay mount lines in: " << fstab.filename().string() << "\n";
        }
    }

    return RomRwResult{
        .fstab_files_modified = modified_fstabs,
        .overlay_lines_removed = total_overlay_lines,
        .init_scripts_removed = removed_inits,
        .unshared_ext4_images = {},
        .dry_run = dry_run
    };
}

RomDecryptResult decrypt_rom(
    const std::string& target_root,
    bool dry_run
) {
    std::cout << BANNER_DECRYPT << "\n\n";

    fs::path root(target_root);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::error_code ec;
    if (!fs::is_directory(eff_root, ec)) {
        std::cout << "find: '" << base_dir.string() << "': No such file or directory\n";
        std::cout << "stat: '" << (base_dir / "vendor" / "etc" / "fstab*").string() << "': No such file or directory\n";
        std::cout << "Error: fstab files not found at " << (base_dir / "vendor" / "etc" / "fstab*").string() << "\n\n";
        return RomDecryptResult{{}, 0, dry_run};
    }

    std::vector<std::string> modified_fstabs;
    int total_lines_changed = 0;

    std::vector<fs::path> fstabs;
    for (const auto& entry : fs::recursive_directory_iterator(eff_root, fs::directory_options::skip_permission_denied, ec)) {
        if (entry.is_regular_file(ec)) {
            std::string name = entry.path().filename().string();
            if (name.rfind("fstab", 0) == 0 && !name.ends_with(".bak")) {
                fstabs.push_back(entry.path());
            }
        }
    }

    if (fstabs.empty()) {
        std::cout << "stat: '" << (base_dir / "vendor" / "etc" / "fstab*").string() << "': No such file or directory\n";
        std::cout << "Error: fstab files not found at " << (base_dir / "vendor" / "etc" / "fstab*").string() << "\n";
    }

    std::regex fe_regex("fileencryption=[^,\\s]+");
    std::regex fe_plain("fileencryption");
    std::regex fo_regex("forceencrypt=[^,\\s]+");

    for (const auto& fstab : fstabs) {
        std::ifstream in(fstab);
        std::vector<std::string> lines;
        std::string line;
        int changed = 0;

        while (std::getline(in, line)) {
            if (!line.starts_with("#") && (line.find("fileencryption") != std::string::npos || line.find("forceencrypt") != std::string::npos)) {
                std::string updated = std::regex_replace(line, fe_regex, "fileencryptable");
                updated = std::regex_replace(updated, fe_plain, "fileencryptable");
                updated = std::regex_replace(updated, fo_regex, "encryptable");
                if (updated != line) {
                    changed++;
                    total_lines_changed++;
                    line = updated;
                }
            }
            lines.push_back(line);
        }
        in.close();

        if (changed > 0) {
            modified_fstabs.push_back(fstab.string());
            std::cout << "Disabling encryption in fstab: " << fstab.filename().string() << " (" << changed << " flags)\n";
            if (!dry_run) {
                std::ofstream out(fstab);
                for (const auto& l : lines) out << l << "\n";
            }
        }
    }

    if (!modified_fstabs.empty()) {
        std::cout << "[✓] ROM Decryption patch applied (" << total_lines_changed << " encryption lines disabled)\n\n";
    } else {
        std::cout << "ROM Decryption complete (no encryption flags found to modify)\n\n";
    }

    return RomDecryptResult{
        .fstab_files_modified = modified_fstabs,
        .lines_modified = total_lines_changed,
        .dry_run = dry_run
    };
}

} // namespace dna
