# DNA-Linux Installation & Setup Guide

DNA-Linux is a native x86_64 toolkit for Android ROM unpack, repack, conversion, and patching. It is designed to run seamlessly on Arch Linux, Debian/Ubuntu, and modern Linux distributions with zero emulators.

---

## 1. Quick Requirements

- **Linux OS:** Arch Linux, Debian 12+, Ubuntu 22.04+, Fedora 39+ (x86_64)
- **Python:** Python 3.11 or newer
- **Display (Optional for GUI):** Wayland or X11 session with PyQt6

### Native Tool Dependencies
To perform full unpack/repack operations, ensure the standard Android and filesystem tools are installed:

| Tool | Arch Linux Package | Debian / Ubuntu Package | Purpose |
|---|---|---|---|
| `lpunpack`, `lpmake` | `android-tools` | `android-sdk-platform-tools` | Dynamic `super.img` operations |
| `simg2img`, `img2simg` | `android-tools` | `android-sdk-platform-tools` | Android sparse image conversions |
| `mke2fs`, `e2fsdroid` | `e2fsprogs` | `e2fsprogs` | ext4 partition filesystem handling |
| `fsck.erofs`, `mkfs.erofs` | `erofs-utils` | `erofs-utils` | EROFS partition filesystem handling |
| `brotli` | `brotli` | `brotli` | `.new.dat.br` decompression/compression |
| `zstd` | `zstd` | `zstd` | `.zst` image decompression/compression |
| `apktool` | `apktool` (AUR / manual) | `apktool` | Framework `services.jar` smali patching |
| `avbtool` | `avbtool` (AUR / git) | `avbtool` | AVB 2.0 image inspection |

---

## 2. Installation on Arch Linux

### Using PKGBUILD (Recommended)
```bash
git clone https://github.com/iprjkt/DNA-Linux.git
cd DNA-Linux/packaging/arch
makepkg -si
```

### Manual / Git Setup
```bash
# 1. Install system tools
sudo pacman -S android-tools e2fsprogs erofs-utils brotli zstd python-pyqt6 python-click python-rich jdk-openjdk

# 2. Clone and link launcher
git clone https://github.com/iprjkt/DNA-Linux.git
cd DNA-Linux
pip install -e .[gui]

# Or run directly via bin/
./bin/dna doctor
```

---

## 3. Installation on Debian & Ubuntu

### Building and Installing the `.deb` Package
```bash
git clone https://github.com/iprjkt/DNA-Linux.git
cd DNA-Linux
./packaging/debian/build_deb.sh

sudo apt install ./dist/dna-linux_0.1.0_amd64.deb
```

### Manual Setup via APT
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-click python3-rich python3-pyqt6 \
    android-sdk-platform-tools e2fsprogs erofs-utils brotli zstd openjdk-21-jre

git clone https://github.com/iprjkt/DNA-Linux.git
cd DNA-Linux
pip install -e .[gui]
```

---

## 4. Portable Standalone Bundle (Any Linux x86_64)

For users on Fedora, openSUSE, Alpine, or systems without root privileges:
```bash
tar -xzf dist/dna-linux-v0.1.0-linux-x86_64.tar.gz
cd dna-linux-v0.1.0-linux-x86_64

# Direct execution without installation:
./dna-gui         # Launch Desktop GUI
./dna doctor      # Check tool dependencies

# Optional system-wide installation:
sudo ./install.sh # Or ./install.sh --user
```

---

## 5. Verification

Run the environment health check to verify all tools are discovered:

```bash
dna doctor
```

Output:
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
│ apktool      ✓ Found   3.0.3                                                │
│ avbtool      ✓ Found   1.3.0                                                │
│ java         ✓ Found   openjdk 21                                           │
└─────────────────────────────────────────────────────────────────────────────┘
✓ All required tools detected! Environment ready for ROM manipulation.
```

---

## 6. Launching User Interfaces

DNA-Linux provides three interfaces:

1. **Desktop Graphical User Interface (GUI):**
   ```bash
   dna gui
   # or
   dna-gui
   ```
   Or click **DNA-Linux** in your desktop application menu.

2. **Interactive Terminal User Interface (TUI):**
   ```bash
   dna tui
   # or bare command in an interactive terminal
   dna
   ```

3. **Command Line Interface (CLI):**
   ```bash
   dna --help
   dna project create myrom
   dna rom unzip /path/to/rom.zip
   dna unpack super images/super.img
   dna jar disable-secure-screenshot
   dna repack super
   ```
