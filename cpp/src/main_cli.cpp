#include <iostream>
#include <string>
#include <vector>

#include "dna/detection.hpp"
#include "dna/prop.hpp"
#include "dna/sparse.hpp"
#include "dna/fs_metadata.hpp"
#include "dna/patch.hpp"
#include "dna/debloat.hpp"
#include "dna/rom_tweaks.hpp"

using namespace dna;

void print_help() {
    std::cout << "DNA-Android-Linux Native C++ Engine v0.1.2\n"
              << "Usage: dna_native_cli <command> [options]\n\n"
              << "Commands:\n"
              << "  detect <path>                     Detect filesystem/image format\n"
              << "  patch-vbmeta <path> [mode]        Patch AVB vbmeta header flags (both/verity/verification/enable)\n"
              << "  integrity <target_dir>            Spoof Play Integrity fingerprint to Pixel 7 Pro\n"
              << "  privapp <target_dir>              Remove priv-app enforcement\n"
              << "  ota <target_dir>                  Disable OTA update validation\n"
              << "  oat <target_dir>                  Remove oat bytecode directories\n"
              << "  rw <target_dir>                   Make ROM read-write (remove overlay fstabs)\n"
              << "  decrypt <target_dir>              Disable forced encryption in fstabs\n"
              << "  scan-meta <dir> [mount]           Extract fs_config & file_contexts metadata\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_help();
        return 1;
    }

    std::string cmd = argv[1];

    if (cmd == "--help" || cmd == "-h" || cmd == "help") {
        print_help();
        return 0;
    }

    if (cmd == "detect") {
        if (argc < 3) {
            std::cerr << "Error: detect requires image path argument\n";
            return 1;
        }
        auto info = inspect_image(argv[2]);
        std::cout << "Path: " << info.path << "\n"
                  << "Type: " << image_type_to_string(info.image_type) << "\n"
                  << "Size: " << info.size_bytes << " bytes\n"
                  << "Description: " << info.description << "\n";
        return 0;
    }

    if (cmd == "patch-vbmeta") {
        if (argc < 3) {
            std::cerr << "Error: patch-vbmeta requires image path argument\n";
            return 1;
        }
        std::string mode = (argc >= 4) ? argv[3] : "both";
        patch_vbmeta(argv[2], mode, false);
        return 0;
    }

    if (cmd == "integrity") {
        if (argc < 3) {
            std::cerr << "Error: integrity requires target directory\n";
            return 1;
        }
        patch_integrity_fix(argv[2], "", "", false);
        return 0;
    }

    if (cmd == "privapp") {
        if (argc < 3) {
            std::cerr << "Error: privapp requires target directory\n";
            return 1;
        }
        patch_privapp_permissions(argv[2], false);
        return 0;
    }

    if (cmd == "ota") {
        if (argc < 3) {
            std::cerr << "Error: ota requires target directory\n";
            return 1;
        }
        patch_disable_ota(argv[2], false);
        return 0;
    }

    if (cmd == "oat") {
        if (argc < 3) {
            std::cerr << "Error: oat requires target directory\n";
            return 1;
        }
        remove_oat_directories(argv[2], false);
        return 0;
    }

    if (cmd == "rw") {
        if (argc < 3) {
            std::cerr << "Error: rw requires target directory\n";
            return 1;
        }
        make_rom_rw(argv[2], false);
        return 0;
    }

    if (cmd == "decrypt") {
        if (argc < 3) {
            std::cerr << "Error: decrypt requires target directory\n";
            return 1;
        }
        decrypt_rom(argv[2], false);
        return 0;
    }

    if (cmd == "scan-meta") {
        if (argc < 3) {
            std::cerr << "Error: scan-meta requires target directory\n";
            return 1;
        }
        std::string mount = (argc >= 4) ? argv[3] : "system";
        auto meta = scan_directory_fs_metadata(argv[2], mount);
        std::cout << "Scanned " << meta.fs_entries.size() << " fs_config entries, "
                  << meta.fc_entries.size() << " file_contexts entries.\n";
        return 0;
    }

    std::cerr << "Unknown command: " << cmd << "\n";
    print_help();
    return 1;
}
