#include "dna/fs_metadata.hpp"
#include <sys/stat.h>
#include <sys/xattr.h>
#include <fstream>
#include <iomanip>

namespace dna {

std::string FsConfigEntry::serialize() const {
    std::string base = path + " " + std::to_string(uid) + " " + std::to_string(gid) + " " + mode;
    if (!capabilities.empty()) {
        return base + " capabilities=" + capabilities;
    }
    return base;
}

static std::string format_octal_mode(mode_t mode) {
    std::ostringstream ss;
    ss << std::oct << (mode & 07777);
    return ss.str();
}

static std::string get_selinux_context(const std::string& path) {
    char buf[256];
    ssize_t len = lgetxattr(path.c_str(), "security.selinux", buf, sizeof(buf) - 1);
    if (len > 0) {
        buf[len] = '\0';
        std::string s(buf);
        while (!s.empty() && (s.back() == '\0' || s.back() == '\n' || s.back() == '\r')) {
            s.pop_back();
        }
        return s;
    }
    return "";
}

FsMetadataResult scan_directory_fs_metadata(
    const std::string& root_dir,
    const std::string& mount_point
) {
    fs::path root(root_dir);
    std::string clean_mount = mount_point;
    while (!clean_mount.empty() && clean_mount.front() == '/') clean_mount.erase(clean_mount.begin());
    while (!clean_mount.empty() && clean_mount.back() == '/') clean_mount.pop_back();

    FsMetadataResult res;

    // Root entries
    res.fs_entries.push_back(FsConfigEntry{"/", 0, 0, "755", ""});
    if (!clean_mount.empty()) {
        res.fs_entries.push_back(FsConfigEntry{clean_mount, 0, 0, "755", ""});
        res.fc_entries.push_back({"/" + clean_mount + "/lost\\+found", "u:object_r:rootfs:s0"});
        std::string def_label = (clean_mount == "vendor" || clean_mount == "odm")
            ? "u:object_r:vendor_file:s0"
            : "u:object_r:system_file:s0";
        res.fc_entries.push_back({"/" + clean_mount + "(/.*)?", def_label});
    } else {
        res.fc_entries.push_back({"/lost\\+found", "u:object_r:rootfs:s0"});
        res.fc_entries.push_back({"/init", "u:object_r:init_exec:s0"});
        res.fc_entries.push_back({"/system/bin/init", "u:object_r:init_exec:s0"});
        res.fc_entries.push_back({"/system(/.*)?", "u:object_r:system_file:s0"});
        res.fc_entries.push_back({"/(.*)?", "u:object_r:rootfs:s0"});
    }

    std::error_code ec;
    if (!fs::is_directory(root, ec)) {
        return res;
    }

    // Traverse directory tree using std::filesystem
    for (const auto& entry : fs::recursive_directory_iterator(root, fs::directory_options::skip_permission_denied, ec)) {
        if (ec) {
            ec.clear();
            continue;
        }
        auto rel_p = entry.path().lexically_relative(root);
        if (rel_p.empty() || rel_p == ".") continue;

        std::string rel_str = rel_p.string();
        std::string target_path = clean_mount.empty() ? rel_str : (clean_mount + "/" + rel_str);

        struct stat st;
        std::string mode_str = "644";
        uint32_t uid = 0;
        uint32_t gid = 0;

        if (lstat(entry.path().c_str(), &st) == 0) {
            uid = (st.st_uid >= 1000) ? 0 : st.st_uid;
            if (st.st_gid >= 1000) {
                bool is_bin = (target_path.find("bin/") != std::string::npos || target_path.rfind("bin", 0) == 0);
                bool is_init = (target_path == "init" || target_path == "system/bin/init" || target_path == "bin/init");
                if (is_bin && !is_init && S_ISREG(st.st_mode) && (st.st_mode & 0111)) {
                    gid = 2000;
                } else {
                    gid = 0;
                }
            } else {
                gid = st.st_gid;
            }

            if (target_path == "init" || target_path == "system/bin/init" || target_path == "bin/init") {
                mode_str = "755";
                uid = 0;
                gid = 0;
            } else if (target_path.size() >= 6 && target_path.rfind("run-as") == target_path.size() - 6) {
                mode_str = "4750";
                uid = 0;
                gid = 2000;
            } else {
                mode_str = format_octal_mode(st.st_mode);
            }
        } else {
            if (entry.is_directory(ec)) mode_str = "755";
        }

        res.fs_entries.push_back(FsConfigEntry{
            .path = target_path,
            .uid = uid,
            .gid = gid,
            .mode = mode_str,
            .capabilities = ""
        });

        std::string selinux_ctx = get_selinux_context(entry.path().string());
        if (!selinux_ctx.empty()) {
            res.fc_entries.push_back({"/" + target_path, selinux_ctx});
        }
    }

    return res;
}

std::string write_fs_config_file(
    const std::vector<FsConfigEntry>& entries,
    const std::string& target_file
) {
    fs::path dst(target_file);
    if (dst.has_parent_path()) {
        fs::create_directories(dst.parent_path());
    }
    std::ofstream out(target_file);
    if (!out.is_open()) {
        throw std::runtime_error("Failed to open fs_config file for writing: " + target_file);
    }
    for (const auto& entry : entries) {
        out << entry.serialize() << "\n";
    }
    return target_file;
}

std::string write_file_contexts_file(
    const std::vector<std::pair<std::string, std::string>>& entries,
    const std::string& target_file
) {
    fs::path dst(target_file);
    if (dst.has_parent_path()) {
        fs::create_directories(dst.parent_path());
    }
    std::ofstream out(target_file);
    if (!out.is_open()) {
        throw std::runtime_error("Failed to open file_contexts file for writing: " + target_file);
    }
    for (const auto& [pattern, label] : entries) {
        out << pattern << " " << label << "\n";
    }
    return target_file;
}

} // namespace dna
