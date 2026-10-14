# DNA-Linux — Native Android ROM Toolkit

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20x86__64-orange.svg)](https://github.com/iprjkt/DNA-Android-Linux)
[![Python](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://www.python.org/)
[![C++](https://img.shields.io/badge/C%2B%2B-20%20(Native%20Engine)-blueviolet.svg)](cpp/)
[![Tests](https://img.shields.io/badge/Tests-120%2F120%20Passing-brightgreen.svg)](tests/)

**DNA-Linux** is a high-performance native Linux (x86_64) port of **DNA-Android** (the popular Android ROM unpack/repack/patch toolkit modded by [@SoutaEver](https://github.com/SoutaEver)).

Engineered specifically for Linux environments (Arch Linux, KDE Plasma, Ubuntu, Debian, Fedora), DNA-Linux eliminates the need for Android emulators (Waydroid/Anbox) or on-device execution by executing all partition transformations, file extraction, SELinux metadata tracking, and bytecode patches directly on the Linux host with maximum speed and reliability.

---

## 🌟 Key Features

### 🚀 High-Performance Native C++20 Acceleration
- **Native Backend (`libdna`)**: High-speed C++20 engine with pybind11 integration for instantaneous Android sparse detection, canned `fs_config` / `file_contexts` extraction, lossless `build.prop` editing, and batch recursive directory scanning.
- **Standalone Native CLI (`dna-native`)**: Lightweight native binary runner compiled directly for high-throughput batch operations without Python startup overhead.

### 📦 Filesystem Unpack, Repack & Conversion
- **Auto-Detection**: Automatic filesystem sniffing for `EXT4`, `EROFS`, `F2FS`, `SPARSE`, `SUPER_LP`, `PAYLOAD_BIN`, `ZSTD`, `BROTLI`, and `DAT`.
- **Rootless ext4 Extraction & Repack**: Userspace partition extraction via `debugfs` and pristine reconstruction via `mke2fs` + `e2fsdroid` with full preservation of SELinux labels, file capabilities, timestamps, permissions, and symlink targets.
- **EROFS Support**: Full decompression and rebuilding with `fsck.erofs` and `mkfs.erofs` supporting lz4, lz4hc, and lzma compression modes.
- **Dynamic Super Partitions**: Extraction of dynamic partitions from `super.img` with `lpunpack` and rebuilding with `lpmake` (supports A-only, Virtual A/B, sparse outputs, and custom group size constraints).
- **Partition Conversions**: Seamless conversions between `img ↔ simg` (sparse), `img ↔ dat ↔ br`, and split/merge for multi-part super images.
- **Partition Resizing**: Resize ext4 filesystem partitions with automatic block calculation and `resize2fs`.

### ⚡ ROM Customization & Optimizations
- **Data-Driven Debloat**: Debloat stock MIUI and HyperOS ROMs using customizable presets ([`data/debloat/global.toml`](file:///mnt/detalmick/DNA-Android-Linux/data/debloat/global.toml) and [`data/debloat/china.toml`](file:///mnt/detalmick/DNA-Android-Linux/data/debloat/china.toml)).
- **OAT Removal**: Clean and remove precompiled OAT cache directories across partition hierarchies to free disk space.
- **Make Full ROM-RW**: Strip overlay filesystem fstab lines, cleanup init mount hooks, and unshare ext4 shared blocks (`e2fsck -E unshare_blocks`) to allow read-write root.
- **ROM Decryption**: Neutralize forced encryption flags in vendor and system fstabs to allow seamless dirty flashing.

### 🛡️ One-Click Patches & Fixes
- **AVB `vbmeta` Header Patch**: Direct binary patching of Verified Boot 2.0 flags at byte offset 120 (disable verity, verification, or both).
- **Play Integrity Fix**: Certified Pixel 7 Pro (`cheetah`) device fingerprint and model spoofing applied losslessly across all `build.prop` files.
- **SafetyCore Placeholder**: Automatic injection of clean placeholder SafetyCore APK into `product/app/Safetycore/`.
- **Priv-App Permissions**: Strip `ro.control_privapp_permissions` enforcement to prevent permission denial bootloops.
- **Disable OTA**: Patch Xiaomi `device_features/*.xml` configuration to disable automatic OTA validation and background downloads.
- **Disable Xiaomi Telemetry**: Remove analytics, cloud daemons, Joyose, MSA, and tracking services based on [`data/patches/xiaomi_services.toml`](file:///mnt/detalmick/DNA-Android-Linux/data/patches/xiaomi_services.toml).

### ☕ Framework Smali Bytecode Patching (`services.jar`)
- **Signature Bypass (Core Patch DSV)**: Rewrites signature verification logic in framework bytecode to enable direct installation and modification of system apps.
- **Remove APK Protection**: Neutralizes installer downgrade restrictions and package check exceptions in `InstallPackageHelper`.
- **Disable Secure Screenshot (DSS)**: Removes FLAG_SECURE restrictions on screen recording and capture, including an **Android 17 / Android U crash fix** that prevents bootloops caused by invalid method return descriptors.

### 🎨 3 Flexible Interfaces
1. **Desktop GUI (`dna-gui` / `dna gui`)**: Modern PyQt6 interface featuring an authentic AMOLED dark theme (`#0f1015`), tactile card-based navigation, live collapsible console log drawer, and background worker threads.
2. **Terminal UI (`dna tui`)**: Full-screen curses interface for remote SSH sessions, lightweight setups, and headless terminal workflows.
3. **Command Line Interface (`dna`)**: Scriptable, modular CLI with `--dry-run`, `--verbose`, structured logging, and non-interactive confirmation flags (`--yes`).

---

## 📥 Installation & Release Packages

Pre-built release packages are located in [`dist/`](file:///mnt/detalmick/DNA-Android-Linux/dist/):

### 1. Arch Linux (`.pkg.tar.zst`)
Directly install the native Arch package using `pacman`:
```bash
sudo pacman -U dist/dna-linux-0.1.0-1-x86_64.pkg.tar.zst
```
*Or build and install using `makepkg`:*
```bash
cd packaging/arch
makepkg -si
```

### 2. Debian & Ubuntu (`.deb`)
Install the standard Debian package (amd64) using `dpkg` or `apt`:
```bash
sudo dpkg -i dist/dna-linux_0.1.0_amd64.deb
sudo apt-get install -f # Install any missing dependencies if needed
```

### 3. Portable Standalone Bundle (Run Anywhere)
No root installation required. Extract and run directly on any x86_64 Linux distribution:
```bash
tar -xzf dist/dna-linux-v0.1.0-linux-x86_64.tar.gz
cd dna-linux-v0.1.0-linux-x86_64

# Run Desktop GUI
./dna-gui

# Run CLI
./dna --help

# Run Native C++ Engine
./dna-native --help

# (Optional) Install to /usr/local or ~/.local
sudo ./install.sh        # System-wide installation
./install.sh --user      # User-level installation to ~/.local
```

### 4. Python Wheel & PIP
Install into your active Python environment:
```bash
pip install dist/dna_linux-0.1.0-py3-none-any.whl[gui]
```

---

## 🩺 System Verification (`dna doctor`)

Run `dna doctor` at any time to verify that host tools and dependencies are detected:

```bash
dna doctor
```

Example diagnostics output:
```text
┌─────────────────────────── DNA-Linux Tool Doctor ───────────────────────────┐
│ Tool         Status    Version / Location                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ lpunpack     ✓ Found   /usr/bin/lpunpack                                    │
│ lpmake       ✓ Found   /usr/bin/lpmake                                      │
│ simg2img     ✓ Found   /usr/bin/simg2img                                    │
│ img2simg     ✓ Found   /usr/bin/img2simg                                    │
│ e2fsdroid    ✓ Found   /usr/bin/e2fsdroid                                   │
│ mke2fs       ✓ Found   /usr/bin/mke2fs                                      │
│ resize2fs    ✓ Found   /usr/bin/resize2fs                                   │
│ fsck.erofs   ✓ Found   /usr/bin/fsck.erofs                                  │
│ mkfs.erofs   ✓ Found   /usr/bin/mkfs.erofs                                  │
│ brotli       ✓ Found   /usr/bin/brotli                                      │
│ zstd         ✓ Found   /usr/bin/zstd                                        │
│ apktool      ✓ Found   /usr/bin/apktool                                     │
│ avbtool      ✓ Found   /usr/bin/avbtool                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Launching the GUI
Launch the PyQt6 Desktop Graphical User Interface:
```bash
dna-gui
# or
dna gui
```

### 2. Basic Workspace Workflow (CLI)

```bash
# 1. Create and select a project workspace
dna project create my_rom
dna project select my_rom

# 2. Extract a stock ROM zip
dna rom unzip /path/to/HyperOS_ROM.zip

# 3. Extract dynamic super.img
dna unpack super images/super.img

# 4. Extract individual partitions (ext4 / erofs auto-detected)
dna unpack img images/system.img
dna unpack img images/product.img

# 5. Apply debloat and patches
dna rom debloat --preset global
dna patch integrity-fix
dna patch vbmeta images/vbmeta.img --mode both

# 6. Repack partition images with preserved SELinux contexts
dna repack img unpacked/system --filesystem ext4
dna repack img unpacked/product --filesystem erofs

# 7. Rebuild dynamic super.img
dna repack super --slot a_only
```

---

## 🛠️ CLI Command Reference

```text
dna doctor                         Check tool dependencies & system health
dna project create <name>          Create a new project workspace
dna project select <name>          Set active workspace
dna project list                   List all workspaces
dna rom unzip <rom.zip>            Extract stock ROM zip package

dna unpack  bin|br|dat|img|zstd|super <file>
dna repack  img|zstd|super [options]
dna resize  <partition> --size <bytes|MiB>
dna convert img-simg|img-dat-br <file>
dna super   split|merge [options]

dna jar     core-patch-dsv | remove-apk-protection | disable-secure-screenshot | patch-all
dna patch   vbmeta | integrity-fix | safetycore | privapp-permissions | disable-ota | disable-xiaomi-services
dna rom     debloat | remove-oat | make-rw | decrypt

dna plugin  import <file.zip> | list | info <name> | run <name> | delete <name>
dna gui                            Launch Desktop Graphical Interface
dna tui                            Launch Terminal User Interface
```

Global Flags: `--project <path>`, `--dry-run` (`-n`), `--verbose` (`-v`), `--yes` (`-y`), `--log-file <file>`.

---

## 🏗️ Building from Source & Release Packaging

### Building the Native C++ Engine
```bash
./build_backend.sh
```

### Building the Complete Multi-Distribution Release Pipeline
To generate Arch packages, Debian packages, Portable bundles, Python wheels, and SHA256 checksums in [`dist/`](file:///mnt/detalmick/DNA-Android-Linux/dist/):
```bash
./packaging/build_release.sh
```

### Running Automated Test Suite
DNA-Linux includes 120 unit and end-to-end integration tests:
```bash
python3 -m unittest discover -s tests -v
```

---

## 📁 Repository Structure

```text
DNA-Android-Linux/
├── bin/                 # Native executables & wrapper scripts (dna, dna-gui)
├── build_backend.sh     # C++ CMake + Ninja compilation script
├── CMakeLists.txt       # Native build system for libdna & pybind11
├── cpp/                 # Native C++20 engine source code & headers
│   ├── include/dna/     # C++ header files
│   ├── src/             # Core C++ modules (sparse, detection, prop, debloat, patch)
│   └── bindings/        # pybind11 Python bindings
├── completions/         # Shell completions for Bash, Zsh, and Fish
├── data/                # Presets, icons, desktop file, patch TOML configs
│   ├── debloat/         # HyperOS / MIUI debloat package lists
│   ├── patches/         # Patch rules & telemetry configs
│   └── icons/           # High-resolution application icons (SVG, PNG)
├── dna_cli/             # Click command-line interface & subcommands
├── dna_core/            # Core library (filesystem, SELinux, repacker, patches)
├── dna_gui/             # PyQt6 Desktop GUI (views, theme, widgets, worker threads)
├── dna_tui/             # Full-screen curses Terminal UI
├── docs/                # Extended documentation (FEATURES.md, INSTALL.md, DECISIONS.md)
├── packaging/           # Packaging scripts
│   ├── arch/            # Arch Linux PKGBUILD & build_pkg.sh
│   ├── debian/          # Debian/Ubuntu build_deb.sh
│   └── build_release.sh # Master release packaging pipeline
└── tests/               # 120 unit & round-trip verification tests
```

---

## 📄 License & Credits

- **License**: GNU General Public License v3.0 or later ([LICENSE](LICENSE)).
- **Credits**:
  - Original **DNA-Android** toolkit modded by **[@SoutaEver](https://github.com/SoutaEver)**.
  - Native Linux architecture and enhancements developed by **[@iprjkt](https://github.com/iprjkt)**.
  - See [`CREDITS.md`](file:///mnt/detalmick/DNA-Android-Linux/CREDITS.md) and [`docs/THIRD_PARTY.md`](file:///mnt/detalmick/DNA-Android-Linux/docs/THIRD_PARTY.md) for full third-party acknowledgments.
