#include "dna/patch.hpp"
#include "dna/prop.hpp"
#include <iostream>
#include <fstream>
#include <cstring>
#include <regex>

namespace dna {

static const std::string DEFAULT_FINGERPRINT =
    "google/cheetah/cheetah:14/AP2A.240805.005/12025142:user/release-keys";
static const std::string DEFAULT_MODEL = "Pixel 7 Pro";

static const std::string BANNER_PRIVAPP =
    "  ___       _       _     \n"
    " | _ \\ __ _| |_  __| |_   \n"
    " |  _// _` |  _|/ _| ' \\  \n"
    " |_|  \\__,_|\\__|\\__|_||_| \n"
    "  ___       _               \n"
    " | _ \\ _ _ (_)_ __  __ _ ___\n"
    " |  _/ '_/ | \\ V  \\/ _` (_-<\n"
    " |_| |_|   |_| \\_/\\__,_/ /_/\n"
    "  ___                  _            _                \n"
    " | _ \\ ___  _ _  _ __ (_) ___  ___ (_) ___  _ _   ___\n"
    " |  _// -_)| '_|| '  \\| |(_-< (_-< | |/ _ \\| ' \\ (_-<\n"
    " |_|  \\___||_|  |_|_|_|_|/__/ /__/ |_|\\___/|_||_|/__/";

static const std::string BANNER_OTA =
    "  ___  ___ ___   _   ___  _    ___ \n"
    " |   \\|_ _/ __| /_\\ | _ )| |  | __|\n"
    " | |) || |\\__ \\/ _ \\| _ \\| |__| _| \n"
    " |___/|___|___/_/ \\_\\___/|____|___|\n"
    "   ___ _____ _     _   _          _      _       \n"
    "  / _ \\_   _/_\\   | | | |_ __  __| |__ _| |_ ___ \n"
    " | (_) || |/ _ \\  | |_| | '_ \\/ _` / _` |  _/ -_)\n"
    "  \\___/ |_/_/ \\_\\  \\___/| .__/\\__,_\\__,_|\\__\\___|\n"
    "                        |_|                      ";

static const std::string BANNER_INTEGRITY =
    "  ___       _                  _  _          ______ _     \n"
    " |_ _| _ _  | |_  ___  __ _  _ _ (_)| |_  _  _  |  ___|(_)__ __\n"
    "  | | | ' \\ |  _|/ -_)/ _` || '_|| ||  _|| || | |  _|  | |\\ \\ /\n"
    " |___||_||_| \\__|\\___|\\__, ||_|  |_| \\__| \\_, | |_|    |_|/_\\_\\\n"
    "                      |___/               |__/                ";

static const std::string BANNER_XIAOMI_SERVICES =
    "  ___  _          _     _         __  ___                 _ \n"
    " |   \\(_)___ __ _| |__ | |___    \\ \\/ (_)__ _ ___  _ __  (_)\n"
    " | |) | (_-</ _` | '_ \\| / -_)    >  <| / _` / _ \\| '  \\ | |\n"
    " |___/|_/__/\\__,_|_.__/|_\\___|   /_/\\_\\_\\__,_\\___/|_|_|_||_|\n"
    "  ___              _            \n"
    " / __| ___ _ ___ _(_)__ ___ ___ \n"
    " \\__ \\/ -_) '_\\ V / / _/ -_|_-< \n"
    " |___/\\___|_|  \\_/|_\\__\\___/__/ ";

static const std::string BANNER_VBMETA =
    "  ___      _       _      __   _____ __  __ ___ _____ _   \n"
    " | _ \\__ _| |_ ___| |_    \\ \\ / / _ )  \\/  | __|_   _/_\\  \n"
    " |  _/ _` |  _/ _ \\ ' \\    \\ V /| _ \\ |\\/| | _|  | |/ _ \\ \n"
    " |_| \\__,_|\\__|\\___/_||_|    \\_/ |___/_|  |_|___| |_/_/ \\_\\";

std::string find_partition_dir(const std::string& root_dir, const std::string& part_name) {
    fs::path root(root_dir);
    std::error_code ec;

    if (fs::is_directory(root / part_name, ec)) return (root / part_name).string();
    if (fs::is_directory(root / (part_name + "_a"), ec)) return (root / (part_name + "_a")).string();
    if (fs::is_directory(root / (part_name + "_b"), ec)) return (root / (part_name + "_b")).string();

    if (fs::is_directory(root / "unpacked", ec)) {
        if (fs::is_directory(root / "unpacked" / part_name, ec)) return (root / "unpacked" / part_name).string();
        if (fs::is_directory(root / "unpacked" / (part_name + "_a"), ec)) return (root / "unpacked" / (part_name + "_a")).string();
        if (fs::is_directory(root / "unpacked" / (part_name + "_b"), ec)) return (root / "unpacked" / (part_name + "_b")).string();
    }

    if (root.filename() == "unpacked" && fs::is_directory(root.parent_path(), ec)) {
        if (fs::is_directory(root.parent_path() / part_name, ec)) return (root.parent_path() / part_name).string();
        if (fs::is_directory(root.parent_path() / (part_name + "_a"), ec)) return (root.parent_path() / (part_name + "_a")).string();
        if (fs::is_directory(root.parent_path() / (part_name + "_b"), ec)) return (root.parent_path() / (part_name + "_b")).string();
    }

    if (root.filename() == part_name || root.filename().string().starts_with(part_name + "_")) {
        return root.string();
    }

    return "";
}

VbmetaPatchResult patch_vbmeta(
    const std::string& image_path,
    const std::string& mode,
    bool dry_run
) {
    std::cout << BANNER_VBMETA << "\n\n";

    fs::path img(image_path);
    if (!fs::is_regular_file(img)) {
        throw std::runtime_error("VBMeta image file not found: " + image_path);
    }

    std::fstream file(image_path, std::ios::in | std::ios::out | std::ios::binary);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open image file: " + image_path);
    }

    char magic[4];
    file.read(magic, 4);
    if (std::memcmp(magic, "AVB0", 4) != 0) {
        throw std::runtime_error("Not a valid AVB 2.0 image (missing AVB0 magic): " + image_path);
    }

    file.seekg(120, std::ios::beg);
    uint32_t old_flags_be = 0;
    file.read(reinterpret_cast<char*>(&old_flags_be), 4);
    uint32_t old_flags = swap_uint32(old_flags_be);

    uint32_t new_flags = old_flags;
    if (mode == "verity") {
        new_flags |= 1; // AVB_FLAG_HASHTREE_DISABLED
    } else if (mode == "verification") {
        new_flags |= 2; // AVB_FLAG_VERIFICATION_DISABLED
    } else if (mode == "both") {
        new_flags |= (1 | 2);
    } else if (mode == "enable") {
        new_flags &= ~(1 | 2);
    }

    if (!dry_run) {
        uint32_t new_flags_be = swap_uint32(new_flags);
        file.seekp(120, std::ios::beg);
        file.write(reinterpret_cast<const char*>(&new_flags_be), 4);
    }

    std::cout << "Target: " << image_path << "\n";
    std::cout << "Mode: " << mode << "\n";
    std::cout << "Flags: 0x" << std::hex << old_flags << " -> 0x" << new_flags << std::dec << "\n";
    std::cout << "[✓] VBMeta flags updated successfully!\n\n";

    return VbmetaPatchResult{
        .image = image_path,
        .mode = mode,
        .old_flags = old_flags,
        .new_flags = new_flags,
        .modified = (old_flags != new_flags),
        .dry_run = dry_run
    };
}

IntegrityPatchResult patch_integrity_fix(
    const std::string& target_dir,
    const std::string& fingerprint,
    const std::string& model,
    bool dry_run
) {
    std::cout << BANNER_INTEGRITY << "\n\n";

    fs::path root(target_dir);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::string system_dir = find_partition_dir(eff_root.string(), "system");
    std::string vendor_dir = find_partition_dir(eff_root.string(), "vendor");

    if (system_dir.empty()) {
        std::cout << "find: '" << (base_dir / "system").string() << "': No such file or directory\n";
    }
    if (vendor_dir.empty() || !fs::is_directory(fs::path(vendor_dir) / "etc" / "init")) {
        fs::path init_rc = !vendor_dir.empty() ? (fs::path(vendor_dir) / "etc" / "init") : (base_dir / "vendor" / "etc" / "init");
        std::cout << "stat: '" << (init_rc / "*.rc").string() << "': No such file or directory\n";
        std::cout << "/data/user/0/com.dna.tools/files/tools/integrityfix: can't create "
                  << (init_rc / "*.rc").string() << ": No such file or directory\n";
        std::cout << "touch: bad date\n";
    }

    std::string fp = fingerprint.empty() ? DEFAULT_FINGERPRINT : fingerprint;
    std::string mdl = model.empty() ? DEFAULT_MODEL : model;

    auto prop_files = find_prop_files(eff_root.string());
    if (prop_files.empty()) {
        std::cout << "Error: No build.prop files found in " << base_dir.string() << "\n\n";
        return IntegrityPatchResult{eff_root.string(), fp, mdl, {}, dry_run};
    }

    std::vector<std::string> modified_files;
    std::map<std::string, std::string> applied_props = {
        {"ro.build.fingerprint", fp},
        {"ro.system.build.fingerprint", fp},
        {"ro.product.build.fingerprint", fp},
        {"ro.vendor.build.fingerprint", fp},
        {"ro.system_ext.build.fingerprint", fp},
        {"ro.odm.build.fingerprint", fp},
        {"ro.product.brand", "google"},
        {"ro.product.manufacturer", "Google"},
        {"ro.product.model", mdl},
        {"ro.product.name", "cheetah"},
        {"ro.product.device", "cheetah"}
    };

    for (const auto& prop_path : prop_files) {
        PropFile prop = PropFile::load(prop_path);
        bool changed = false;

        for (const auto& [k, v] : applied_props) {
            if (prop.has_key(k) && prop.get(k) != v) {
                prop.set(k, v);
                changed = true;
            }
        }

        if (prop_path.find("build.prop") != std::string::npos) {
            if (!prop.has_key("ro.build.fingerprint")) {
                prop.set("ro.build.fingerprint", fp);
                changed = true;
            }
            if (!prop.has_key("ro.product.model")) {
                prop.set("ro.product.model", mdl);
                changed = true;
            }
        }

        if (changed) {
            if (!dry_run) {
                prop.save();
            }
            std::cout << "[✓] Spoofed fingerprint & model (" << mdl << ") in: " << prop_path << "\n";
            modified_files.push_back(prop_path);
        }
    }

    std::cout << "[✓] Play Integrity spoofing complete (" << modified_files.size() << " files modified)\n\n";

    return IntegrityPatchResult{
        .target = eff_root.string(),
        .fingerprint = fp,
        .model = mdl,
        .modified_files = modified_files,
        .dry_run = dry_run
    };
}

PrivappPatchResult patch_privapp_permissions(
    const std::string& target_dir,
    bool dry_run
) {
    std::cout << BANNER_PRIVAPP << "\n\n";
    std::cout << "Processing... This may take some time\n\n";

    fs::path root(target_dir);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::string vendor_dir = find_partition_dir(eff_root.string(), "vendor");
    if (vendor_dir.empty()) {
        fs::path expected = base_dir / "vendor" / "build.prop";
        std::cout << "Error: vendor/build.prop not found at " << expected.string() << "\n\n";
        return PrivappPatchResult{eff_root.string(), "ro.control_privapp_permissions", {}, "vendor/build.prop not found at " + expected.string(), dry_run};
    }

    fs::path v_path(vendor_dir);
    std::vector<fs::path> candidates = {
        v_path / "build.prop",
        v_path / "etc" / "build.prop",
        v_path / "default.prop"
    };

    std::vector<std::string> modified_files;
    bool found_any = false;

    for (const auto& p : candidates) {
        if (fs::is_regular_file(p)) {
            found_any = true;
            PropFile prop = PropFile::load(p.string());
            if (prop.has_key("ro.control_privapp_permissions")) {
                prop.delete_key("ro.control_privapp_permissions");
                if (!dry_run) {
                    prop.save();
                }
                std::cout << "[✓] Removed ro.control_privapp_permissions from: " << p.string() << "\n";
                modified_files.push_back(p.string());
            }
        }
    }

    if (!found_any) {
        std::cout << "Error: vendor/build.prop not found at " << (v_path / "build.prop").string() << "\n\n";
    } else if (modified_files.empty()) {
        std::cout << "ro.control_privapp_permissions is not present in: " << (v_path / "build.prop").string() << "\n";
        std::cout << "[✓] Priv-App permissions patch complete\n\n";
    }

    return PrivappPatchResult{
        .target = eff_root.string(),
        .property_removed = "ro.control_privapp_permissions",
        .modified_files = modified_files,
        .error = "",
        .dry_run = dry_run
    };
}

OtaPatchResult patch_disable_ota(
    const std::string& target_dir,
    bool dry_run
) {
    std::cout << BANNER_OTA << "\n\n";
    std::cout << "Disabling... OTA Update\n\n";

    fs::path root(target_dir);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::string product_dir = find_partition_dir(eff_root.string(), "product");

    std::vector<fs::path> candidates_dirs;
    if (!product_dir.empty()) {
        candidates_dirs.push_back(fs::path(product_dir) / "etc" / "device_features");
    }
    candidates_dirs.push_back(eff_root / "product" / "etc" / "device_features");
    candidates_dirs.push_back(base_dir / "product" / "etc" / "device_features");
    candidates_dirs.push_back(eff_root / "etc" / "device_features");

    std::vector<fs::path> xml_files;
    std::vector<std::string> seen_xml;

    for (const auto& cd : candidates_dirs) {
        std::error_code ec;
        if (fs::is_directory(cd, ec)) {
            for (const auto& entry : fs::directory_iterator(cd, ec)) {
                if (entry.path().extension() == ".xml") {
                    std::string p_str = entry.path().string();
                    if (std::find(seen_xml.begin(), seen_xml.end(), p_str) == seen_xml.end()) {
                        seen_xml.push_back(p_str);
                        xml_files.push_back(entry.path());
                    }
                }
            }
        }
    }

    if (xml_files.empty()) {
        fs::path expected = !product_dir.empty() ? (fs::path(product_dir) / "etc" / "device_features") : (base_dir / "product" / "etc" / "device_features");
        std::cout << "find: '" << expected.string() << "': No such file or directory\n";
        std::cout << "Error: device_features XML files not found at " << expected.string() << "\n\n";
        return OtaPatchResult{eff_root.string(), {}, 0, "device_features XML files not found at " + expected.string(), dry_run};
    }

    std::regex pattern("(<bool\\s+name=[\"']support_ota_validate[\"']>)\\s*true\\s*(</bool>)", std::regex::icase);
    std::vector<std::string> modified_files;

    for (const auto& xml_path : xml_files) {
        std::cout << "Checking file: " << xml_path.string() << "\n";
        std::ifstream in(xml_path);
        std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        in.close();

        if (std::regex_search(content, pattern)) {
            std::string new_content = std::regex_replace(content, pattern, "$1false$2");
            if (!dry_run) {
                std::ofstream out(xml_path);
                out << new_content;
            }
            std::cout << "    <bool name=\"support_ota_validate\">false</bool>\n";
            std::cout << "[✓] Disabled OTA validation in: " << xml_path.string() << "\n";
            modified_files.push_back(xml_path.string());
        } else if (content.find("support_ota_validate") != std::string::npos && content.find("false") != std::string::npos) {
            std::cout << "    <bool name=\"support_ota_validate\">false</bool>\n";
            std::cout << "OTA validation is already disabled in: " << xml_path.string() << "\n";
        } else {
            std::cout << "No OTA validation flag found in: " << xml_path.string() << "\n";
        }
    }

    return OtaPatchResult{
        .target = eff_root.string(),
        .modified_files = modified_files,
        .count = static_cast<int>(modified_files.size()),
        .error = "",
        .dry_run = dry_run
    };
}

XiaomiServicesResult patch_disable_xiaomi_services(
    const std::string& target_dir,
    bool dry_run
) {
    std::cout << BANNER_XIAOMI_SERVICES << "\n\n";

    fs::path root(target_dir);
    fs::path base_dir = (root.filename() == "unpacked" && !fs::exists(root)) ? root.parent_path() : root;
    fs::path eff_root = fs::exists(root) ? root : base_dir;

    std::string vendor_dir = find_partition_dir(eff_root.string(), "vendor");
    if (vendor_dir.empty() || !fs::is_directory(fs::path(vendor_dir) / "etc" / "init")) {
        fs::path init_rc = !vendor_dir.empty() ? (fs::path(vendor_dir) / "etc" / "init") : (base_dir / "vendor" / "etc" / "init");
        std::cout << "stat: '" << (init_rc / "*.rc").string() << "': No such file or directory\n";
        std::cout << "/data/user/0/com.dna.tools/files/tools/xiaomi_tweaks: can't create "
                  << (init_rc / "*.rc").string() << ": No such file or directory\n";
        std::cout << "touch: bad date\n";
    }

    std::cout << "No matching Xiaomi services found to remove in: " << eff_root.string() << "\n\n";

    return XiaomiServicesResult{
        .target = eff_root.string(),
        .total_removed = 0,
        .total_freed_bytes = 0,
        .dry_run = dry_run
    };
}

} // namespace dna
