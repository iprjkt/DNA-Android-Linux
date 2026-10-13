#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "dna/detection.hpp"
#include "dna/prop.hpp"
#include "dna/sparse.hpp"
#include "dna/fs_metadata.hpp"
#include "dna/patch.hpp"
#include "dna/debloat.hpp"
#include "dna/rom_tweaks.hpp"

namespace py = pybind11;
using namespace dna;

PYBIND11_MODULE(dna_core_cpp, m) {
    m.doc() = "High-performance native C++ core backend engine for DNA-Android-Linux";

    // --- Detection ---
    py::enum_<ImageType>(m, "ImageType")
        .value("SPARSE", ImageType::SPARSE)
        .value("EXT4", ImageType::EXT4)
        .value("EROFS", ImageType::EROFS_FS)
        .value("F2FS", ImageType::F2FS_FS)
        .value("SUPER_LP", ImageType::SUPER_LP)
        .value("PAYLOAD_BIN", ImageType::PAYLOAD_BIN)
        .value("BROTLI", ImageType::BROTLI)
        .value("ZSTD", ImageType::ZSTD)
        .value("DAT", ImageType::DAT)
        .value("UNKNOWN", ImageType::UNKNOWN)
        .export_values();

    py::class_<ImageInfo>(m, "ImageInfo")
        .def_readonly("path", &ImageInfo::path)
        .def_readonly("image_type", &ImageInfo::image_type)
        .def_readonly("size_bytes", &ImageInfo::size_bytes)
        .def_readonly("is_sparse", &ImageInfo::is_sparse)
        .def_readonly("fs_type", &ImageInfo::fs_type)
        .def_readonly("description", &ImageInfo::description);

    m.def("detect_image_type", &detect_image_type, py::arg("file_path"));
    m.def("inspect_image", &inspect_image, py::arg("file_path"));

    // --- PropFile ---
    py::class_<PropFile>(m, "PropFile")
        .def(py::init<>())
        .def_static("load", &PropFile::load, py::arg("path"))
        .def_static("from_text", &PropFile::from_text, py::arg("text"))
        .def("has_key", &PropFile::has_key, py::arg("key"))
        .def("get", &PropFile::get, py::arg("key"), py::arg("default_val") = "")
        .def("set", &PropFile::set, py::arg("key"), py::arg("value"))
        .def("delete", &PropFile::delete_key, py::arg("key"))
        .def("keys", &PropFile::keys)
        .def("items", &PropFile::items)
        .def("to_dict", &PropFile::to_dict)
        .def("to_text", &PropFile::to_text)
        .def("save", &PropFile::save, py::arg("path") = "")
        .def_property_readonly("path", &PropFile::path);

    m.def("find_prop_files", &find_prop_files, py::arg("target_dir"));

    // --- Sparse ---
    m.def("is_sparse_image", &is_sparse_image, py::arg("file_path"));
    m.def("merge_sparse_chunks", &merge_sparse_chunks, py::arg("chunk_paths"), py::arg("out_image"));
    m.def("split_sparse_image", &split_sparse_image,
          py::arg("file_path"), py::arg("out_dir"), py::arg("parts") = 12, py::arg("prefix") = "");

    // --- Filesystem Metadata ---
    py::class_<FsConfigEntry>(m, "FsConfigEntry")
        .def(py::init<std::string, uint32_t, uint32_t, std::string, std::string>(),
             py::arg("path"), py::arg("uid"), py::arg("gid"), py::arg("mode"), py::arg("capabilities") = "")
        .def_readwrite("path", &FsConfigEntry::path)
        .def_readwrite("uid", &FsConfigEntry::uid)
        .def_readwrite("gid", &FsConfigEntry::gid)
        .def_readwrite("mode", &FsConfigEntry::mode)
        .def_readwrite("capabilities", &FsConfigEntry::capabilities)
        .def("serialize", &FsConfigEntry::serialize);

    py::class_<FsMetadataResult>(m, "FsMetadataResult")
        .def_readwrite("fs_entries", &FsMetadataResult::fs_entries)
        .def_readwrite("fc_entries", &FsMetadataResult::fc_entries);

    m.def("scan_directory_fs_metadata", &scan_directory_fs_metadata,
          py::arg("root_dir"), py::arg("mount_point") = "system");
    m.def("write_fs_config_file", &write_fs_config_file,
          py::arg("entries"), py::arg("target_file"));
    m.def("write_file_contexts_file", &write_file_contexts_file,
          py::arg("entries"), py::arg("target_file"));

    // --- Patching ---
    m.def("find_partition_dir", &find_partition_dir, py::arg("root_dir"), py::arg("part_name"));

    py::class_<VbmetaPatchResult>(m, "VbmetaPatchResult")
        .def_readwrite("image", &VbmetaPatchResult::image)
        .def_readwrite("mode", &VbmetaPatchResult::mode)
        .def_readwrite("old_flags", &VbmetaPatchResult::old_flags)
        .def_readwrite("new_flags", &VbmetaPatchResult::new_flags)
        .def_readwrite("modified", &VbmetaPatchResult::modified)
        .def_readwrite("dry_run", &VbmetaPatchResult::dry_run);

    m.def("patch_vbmeta", &patch_vbmeta,
          py::arg("image_path"), py::arg("mode") = "both", py::arg("dry_run") = false);

    py::class_<IntegrityPatchResult>(m, "IntegrityPatchResult")
        .def_readwrite("target", &IntegrityPatchResult::target)
        .def_readwrite("fingerprint", &IntegrityPatchResult::fingerprint)
        .def_readwrite("model", &IntegrityPatchResult::model)
        .def_readwrite("modified_files", &IntegrityPatchResult::modified_files)
        .def_readwrite("dry_run", &IntegrityPatchResult::dry_run);

    m.def("patch_integrity_fix", &patch_integrity_fix,
          py::arg("target_dir"), py::arg("fingerprint") = "", py::arg("model") = "", py::arg("dry_run") = false);

    py::class_<PrivappPatchResult>(m, "PrivappPatchResult")
        .def_readwrite("target", &PrivappPatchResult::target)
        .def_readwrite("property_removed", &PrivappPatchResult::property_removed)
        .def_readwrite("modified_files", &PrivappPatchResult::modified_files)
        .def_readwrite("error", &PrivappPatchResult::error)
        .def_readwrite("dry_run", &PrivappPatchResult::dry_run);

    m.def("patch_privapp_permissions", &patch_privapp_permissions,
          py::arg("target_dir"), py::arg("dry_run") = false);

    py::class_<OtaPatchResult>(m, "OtaPatchResult")
        .def_readwrite("target", &OtaPatchResult::target)
        .def_readwrite("modified_files", &OtaPatchResult::modified_files)
        .def_readwrite("count", &OtaPatchResult::count)
        .def_readwrite("error", &OtaPatchResult::error)
        .def_readwrite("dry_run", &OtaPatchResult::dry_run);

    m.def("patch_disable_ota", &patch_disable_ota,
          py::arg("target_dir"), py::arg("dry_run") = false);

    py::class_<XiaomiServicesResult>(m, "XiaomiServicesResult")
        .def_readwrite("target", &XiaomiServicesResult::target)
        .def_readwrite("total_removed", &XiaomiServicesResult::total_removed)
        .def_readwrite("total_freed_bytes", &XiaomiServicesResult::total_freed_bytes)
        .def_readwrite("dry_run", &XiaomiServicesResult::dry_run);

    m.def("patch_disable_xiaomi_services", &patch_disable_xiaomi_services,
          py::arg("target_dir"), py::arg("dry_run") = false);

    // --- Debloat ---
    py::class_<DebloatPackage>(m, "DebloatPackage")
        .def(py::init<std::string, std::vector<std::string>, std::string>(),
             py::arg("name"), py::arg("patterns"), py::arg("description") = "")
        .def_readwrite("name", &DebloatPackage::name)
        .def_readwrite("patterns", &DebloatPackage::patterns)
        .def_readwrite("description", &DebloatPackage::description);

    py::class_<DebloatPreset>(m, "DebloatPreset")
        .def(py::init<std::string, std::string, std::vector<DebloatPackage>>(),
             py::arg("name"), py::arg("description"), py::arg("packages"))
        .def_readwrite("name", &DebloatPreset::name)
        .def_readwrite("description", &DebloatPreset::description)
        .def_readwrite("packages", &DebloatPreset::packages);

    py::class_<DebloatResult>(m, "DebloatResult")
        .def_readwrite("preset_name", &DebloatResult::preset_name)
        .def_readwrite("removed_directories", &DebloatResult::removed_directories)
        .def_readwrite("freed_bytes", &DebloatResult::freed_bytes)
        .def_readwrite("packages_affected", &DebloatResult::packages_affected)
        .def_readwrite("dry_run", &DebloatResult::dry_run);

    m.def("calculate_directory_size", &calculate_directory_size, py::arg("path"));
    m.def("run_debloat", &run_debloat,
          py::arg("target_root"), py::arg("preset"), py::arg("dry_run") = false);

    // --- ROM Tweaks ---
    m.def("remove_oat_directories", &remove_oat_directories,
          py::arg("target_root"), py::arg("dry_run") = false);

    py::class_<RomRwResult>(m, "RomRwResult")
        .def_readwrite("fstab_files_modified", &RomRwResult::fstab_files_modified)
        .def_readwrite("overlay_lines_removed", &RomRwResult::overlay_lines_removed)
        .def_readwrite("init_scripts_removed", &RomRwResult::init_scripts_removed)
        .def_readwrite("unshared_ext4_images", &RomRwResult::unshared_ext4_images)
        .def_readwrite("dry_run", &RomRwResult::dry_run);

    m.def("make_rom_rw", &make_rom_rw,
          py::arg("target_root"), py::arg("dry_run") = false);

    py::class_<RomDecryptResult>(m, "RomDecryptResult")
        .def_readwrite("fstab_files_modified", &RomDecryptResult::fstab_files_modified)
        .def_readwrite("lines_modified", &RomDecryptResult::lines_modified)
        .def_readwrite("dry_run", &RomDecryptResult::dry_run);

    m.def("decrypt_rom", &decrypt_rom,
          py::arg("target_root"), py::arg("dry_run") = false);
}
