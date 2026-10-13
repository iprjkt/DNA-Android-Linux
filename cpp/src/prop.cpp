#include "dna/prop.hpp"
#include <fstream>
#include <stdexcept>

namespace dna {

std::optional<std::pair<std::string, std::string>> PropFile::parse_line(const std::string& line) {
    std::string trimmed = trim(line);
    if (trimmed.empty() || trimmed.front() == '#' || trimmed.front() == ';') {
        return std::nullopt;
    }
    auto eq_pos = trimmed.find('=');
    if (eq_pos == std::string::npos) {
        return std::nullopt;
    }
    std::string key = trim(trimmed.substr(0, eq_pos));
    std::string val = trim(trimmed.substr(eq_pos + 1));
    return std::make_pair(key, val);
}

PropFile PropFile::load(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Property file not found: " + path);
    }
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(file, line)) {
        lines.push_back(line);
    }
    return PropFile(lines, path);
}

PropFile PropFile::from_text(const std::string& text) {
    std::vector<std::string> lines;
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line)) {
        lines.push_back(line);
    }
    return PropFile(lines);
}

bool PropFile::has_key(const std::string& key) const {
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed && parsed->first == key) {
            return true;
        }
    }
    return false;
}

std::string PropFile::get(const std::string& key, const std::string& default_val) const {
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed && parsed->first == key) {
            return parsed->second;
        }
    }
    return default_val;
}

void PropFile::set(const std::string& key, const std::string& value) {
    for (auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed && parsed->first == key) {
            line = key + "=" + value;
            return;
        }
    }
    lines_.push_back(key + "=" + value);
}

bool PropFile::delete_key(const std::string& key) {
    bool found = false;
    std::vector<std::string> new_lines;
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed && parsed->first == key) {
            found = true;
            continue;
        }
        new_lines.push_back(line);
    }
    lines_ = std::move(new_lines);
    return found;
}

std::vector<std::string> PropFile::keys() const {
    std::vector<std::string> res;
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed) {
            res.push_back(parsed->first);
        }
    }
    return res;
}

std::vector<std::pair<std::string, std::string>> PropFile::items() const {
    std::vector<std::pair<std::string, std::string>> res;
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed) {
            res.push_back(*parsed);
        }
    }
    return res;
}

std::map<std::string, std::string> PropFile::to_dict() const {
    std::map<std::string, std::string> res;
    for (const auto& line : lines_) {
        auto parsed = parse_line(line);
        if (parsed) {
            res[parsed->first] = parsed->second;
        }
    }
    return res;
}

std::string PropFile::to_text() const {
    std::ostringstream ss;
    for (size_t i = 0; i < lines_.size(); ++i) {
        ss << lines_[i];
        if (i + 1 < lines_.size() || !lines_[i].empty()) {
            ss << "\n";
        }
    }
    return ss.str();
}

std::string PropFile::save(const std::string& path) {
    std::string target = path.empty() ? path_ : path;
    if (target.empty()) {
        throw std::runtime_error("No destination path provided for save()");
    }
    fs::path p(target);
    if (p.has_parent_path()) {
        fs::create_directories(p.parent_path());
    }
    std::ofstream out(target);
    if (!out.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + target);
    }
    out << to_text();
    path_ = target;
    return target;
}

std::vector<std::string> find_prop_files(const std::string& target_dir) {
    std::vector<std::string> results;
    fs::path root(target_dir);
    std::error_code ec;
    if (!fs::is_directory(root, ec)) {
        return results;
    }

    for (const auto& entry : fs::recursive_directory_iterator(root, fs::directory_options::skip_permission_denied, ec)) {
        if (entry.is_regular_file(ec)) {
            std::string name = entry.path().filename().string();
            if (name.ends_with(".prop") || name == "prop.default") {
                results.push_back(entry.path().string());
            }
        }
    }
    std::sort(results.begin(), results.end());
    return results;
}

} // namespace dna
