# DNA-Linux Installation & Setup Guide

DNA-Linux is a native x86_64 toolkit for Android ROM unpack, repack, conversion, and patching. It is designed to run seamlessly on Arch Linux, Debian/Ubuntu, and modern Linux distributions with zero emulators.

---

## 1. Quick Requirements

- **Linux OS:** Arch Linux, Debian 12+, Ubuntu 22.04+, Fedora 39+ (x86_64)
- **Python:** Python 3.11 or newer
- **Display (Optional for GUI):** Wayland or X11 session with PyQt6

### Native Tool Architecture & Bundled Binaries
DNA-Linux bundles **16 core native partition and filesystem binaries** directly inside the package (`data/bin/`). You do **not** need to hunt for distro packages or deal with incompatible library versions for basic partition unpacking and repacking.

| Tool | Category | Distribution Status | Purpose |
|---|---|---|---|
| `lpunpack`, `lpmake`, `lpdump` | Super Partition | **Bundled** | Dynamic `super.img` operations |
| `simg2img`, `img2simg` | Sparse Image | **Bundled** | Android sparse image conversions |
| `mke2fs`, `e2fsdroid`, `debugfs`, `resize2fs`, `e2fsck` | ext4 Filesystem | **Bundled** | ext4 partition rootless unpack & repack |
| `fsck.erofs`, `mkfs.erofs` | EROFS Filesystem | **Bundled** | EROFS decompression and rebuilding |
| `sload_f2fs` | F2FS Filesystem | **Bundled** | F2FS SELinux metadata injection |
| `brotli`, `zstd` | Compression | **Bundled** | `.br` and `.zst` compression/decompression |
| `avbtool` | AVB 2.0 | **Bundled** | Verified Boot 2.0 inspection |
| `java` | Framework | System / Setup | OpenJDK Runtime (JRE 17+) for APK/JAR patching |
| `apktool` | Framework | **Setup Mode** | `services.jar` bytecode decompiler/recompiler |
| `payload-dumper-go` | OTA Firmware | **Setup Mode** | Direct extraction of `payload.bin` |

---

### Setup Mode for External Dependencies (`dna setup`)
To configure optional external dependencies (`apktool`, `payload-dumper-go`, `java`):

```bash
# Check status of external tools
dna setup --status

# Automatically install all external tools
dna setup --all

# Or install individual components
dna setup apktool
dna setup payload-dumper-go
dna setup java
```
In the GUI, simply click the **⚙ Setup** button in the header bar.

---

## 2. Installation on Arch Linux

### Using PKGBUILD (Recommended)
```bash
git clone https://github.com/iprjkt/DNA-Android-Linux.git
cd DNA-Android-Linux/packaging/arch
makepkg -si
```

### Manual / Git Setup
```bash
# 1. Install system tools
sudo pacman -S android-tools e2fsprogs erofs-utils brotli zstd python-pyqt6 python-click python-rich jdk-openjdk

# 2. Clone and link launcher
git clone https://github.com/iprjkt/DNA-Android-Linux.git
cd DNA-Android-Linux
pip install -e .[gui]

# Or run directly via bin/
./bin/dna doctor
```

---

## 3. Installation on Debian & Ubuntu

### Building and Installing the `.deb` Package
```bash
git clone https://github.com/iprjkt/DNA-Android-Linux.git
cd DNA-Android-Linux
./packaging/debian/build_deb.sh

sudo apt install ./dist/dna-linux_0.1.0_amd64.deb
```

### Manual Setup via APT
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-click python3-rich python3-pyqt6 \
    android-sdk-platform-tools e2fsprogs erofs-utils brotli zstd openjdk-21-jre

git clone https://github.com/iprjkt/DNA-Android-Linux.git
cd DNA-Android-Linux
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
                            Native Linux Tool Status                            
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃  Status  ┃ Tool              ┃ Category ┃ Source     ┃ Type       ┃ Version ┃ Path             ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│   ✓ OK   │ lpunpack          │ Super    │ Bundled    │ Required   │ bundled │ .../data/bin/... │
│   ✓ OK   │ lpmake            │ Super    │ Bundled    │ Required   │ bundled │ .../data/bin/... │
│   ✓ OK   │ simg2img          │ Sparse   │ Bundled    │ Required   │ bundled │ .../data/bin/... │
│   ✓ OK   │ img2simg          │ Sparse   │ Bundled    │ Required   │ bundled │ .../data/bin/... │
│   ✓ OK   │ e2fsdroid         │ Ext4     │ Bundled    │ Required   │ 1.47.4  │ .../data/bin/... │
│   ✓ OK   │ mke2fs            │ Ext4     │ Bundled    │ Required   │ 1.47.4  │ .../data/bin/... │
│   ✓ OK   │ resize2fs         │ Ext4     │ Bundled    │ Required   │ 1.47.4  │ .../data/bin/... │
│   ✓ OK   │ fsck.erofs        │ EROFS    │ Bundled    │ Required   │ 1.9.4   │ .../data/bin/... │
│   ✓ OK   │ mkfs.erofs        │ EROFS    │ Bundled    │ Required   │ 1.9.4   │ .../data/bin/... │
│   ✓ OK   │ brotli            │ Compress │ Bundled    │ Required   │ 1.2.0   │ .../data/bin/... │
│   ✓ OK   │ zstd              │ Compress │ Bundled    │ Required   │ 1.5.7   │ .../data/bin/... │
│   ✓ OK   │ java              │ Framework│ System     │ Optional   │ 21.0.1  │ /usr/bin/java    │
│   ✓ OK   │ apktool           │ Framework│ Setup      │ Optional   │ 3.0.3   │ ~/.local/...     │
│   ✓ OK   │ payload-dumper-go │ OTA      │ Setup      │ Optional   │ 2.1.0   │ ~/.local/...     │
│   ✓ OK   │ avbtool           │ AVB      │ Bundled    │ Optional   │ bundled │ .../data/bin/... │
└──────────┴━━━━━━━━━━━━━━━━━━━┴━━━━━━━━━━┴━━━━━━━━━━━━┴━━━━━━━━━━━━┴━━━━━━━━━┴━━━━━━━━━━━━━━━━━━┘
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
