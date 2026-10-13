#pragma once

#include "dna/common.hpp"
#include <map>

namespace dna {

class PropFile {
public:
    PropFile() = default;
    explicit PropFile(const std::vector<std::string>& lines, const std::string& path = "")
        : lines_(lines), path_(path) {}

    static PropFile load(const std::string& path);
    static PropFile from_text(const std::string& text);

    bool has_key(const std::string& key) const;
    std::string get(const std::string& key, const std::string& default_val = "") const;
    void set(const std::string& key, const std::string& value);
    bool delete_key(const std::string& key);

    std::vector<std::string> keys() const;
    std::vector<std::pair<std::string, std::string>> items() const;
    std::map<std::string, std::string> to_dict() const;

    std::string to_text() const;
    std::string save(const std::string& path = "");

    const std::string& path() const { return path_; }

private:
    std::vector<std::string> lines_;
    std::string path_;

    static std::optional<std::pair<std::string, std::string>> parse_line(const std::string& line);
};

std::vector<std::string> find_prop_files(const std::string& target_dir);

} // namespace dna
