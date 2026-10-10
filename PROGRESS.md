# DNA-Linux Implementation Progress

Tracking progress across phases as defined in `README.md`.

---

## Phases Overview

| Phase | Description | Status | Notes |
|---|---|---|---|
| **Phase 0 — Recon** | APK inspection, menu/command mapping, docs | **Completed** | Discovered all commands, scripts, assets, and mapped to Linux equivalents. Produced `docs/FEATURES.md` and `docs/DECISIONS.md`. |
| **Phase 1 — Foundation** | Project scaffold, packaging, `dna doctor`, config, `Paths`, project commands | **Completed** | Full Python 3.11+ scaffold (`dna_core`, `dna_cli`), `pyproject.toml`, native launcher `bin/dna`, `dna doctor`, `dna project create/select/delete/list`, `dna rom unzip`, and unit test suite (15/15 passing). |
| **Phase 2 — Unpack / Repack / Convert** | Unpack bin/br/dat/img/zstd/super, repack img/zstd/super, format conversions | **Completed** | Full unpack/repack/convert pipeline. Magic-based filesystem auto-detection, ext4/erofs userspace extraction & repacking, SELinux/fs_config preservation, sdat2img/img2sdat, sparse conversions, super.img split/merge, resize2fs partition expansion, and 31/31 unit & round-trip tests passing. |
| **Phase 3 — ROM Menu** | Debloat, remove oat, make ROM-RW, ROM decrypt | **Completed** | Data-driven debloat presets (global/china), oat directory cleanup, make-rw (fstab overlay and init cleanup), decrypt (force-encrypt removal), and 36/36 tests passing. |
| **Phase 4 — Patch Menu** | vbmeta, integrity fix, SafetyCore, priv-app permissions, disable OTA, Xiaomi services | Pending | `build.prop` editor, AVB header patcher, SafetyCore placeholder. |
| **Phase 5 — Jar Menu** | Core patch DSV, remove APK protection, disable secure screenshot | Pending | Descriptor-based smali patching with apktool/baksmali/smali. |
| **Phase 6 — Plugins** | Plugin spec, importer, sandboxed execution, example plugin | Pending | TOML-based plugin format with sandboxed workspace execution. |
| **Phase 7 — TUI** | Terminal UI mirroring Home -> Project Menu | Pending | Dark-themed Textual or curses interface. |
| **Phase 8 — Docs & Release** | Packaging, man page, shell completions, PKGBUILD, .deb script | Pending | Distribution packages for Arch Linux and Debian/Ubuntu. |

---

## Current Status & Verification
- **Host System Diagnostics**:
  - Distro: Arch Linux (x86_64)
  - Installed tools detected: `brotli`, `zstd`, `simg2img`, `img2simg`, `lpunpack`, `lpmake`, `e2fsdroid`, `mke2fs`, `resize2fs`, `e2fsck`, `fsck.erofs`, `mkfs.erofs`, `sload_f2fs`, `java` (JDK 21), `apktool`, `avbtool`, `python3` (3.14).
  - Test testbed confirmed: `/run/media/fxxyz73/sigeonpex/ROM_Fastboot_Recovery_ISO` (contains HyperOS zip ROMs, Fastboot images, super.img).
- **Phase 1 Verification**:
  - `dna doctor`: passes, identifies all installed and optional tools on Arch Linux.
  - Project workspace lifecycle: create, list, select, delete, layout integrity, and path safety verified.
  - ROM Zip extraction: tested with unit tests and verified with `--dry-run` on real 4.2GB `HyperOS3.0.303.0...zip`.
  - Automated tests: 15/15 tests passing.
- **Phase 2 Verification**:
  - Magic byte sniffing accurately identifies `SPARSE`, `EXT4`, `EROFS`, `F2FS`, `SUPER_LP`, `PAYLOAD_BIN`, `ZSTD`, `BROTLI`, `DAT`.
  - Ext4 unpack (`debugfs`) and repack (`mke2fs` + `e2fsdroid`) verified with SELinux contexts and permissions preservation.
  - EROFS unpack (`fsck.erofs`) and repack (`mkfs.erofs`) verified with round-trip content matching.
  - Super partition extraction (`lpunpack`) and reconstruction (`lpmake`) verified with synthetic and real images.
  - Sparse <-> raw conversions, `sdat2img` / `img2sdat` round-trip, and `super.img` split/merge verified.
  - Partition resizing (`resize2fs`) verified on ext4.
  - Automated tests: 31/31 tests passing via `python3 -m unittest discover tests`.
- **Phase 3 Verification**:
  - Debloat: `data/debloat/global.toml` and `china.toml` loaded cleanly; dry-run and actual removal verified with directory scanning.
  - Remove OAT: Scans and removes all `oat` directories inside partition hierarchies; dry-run and execution verified.
  - Make ROM-RW: Strips overlay mount lines from `fstab*` files, unshares ext4 blocks via `e2fsck -E unshare_blocks` when needed, removes `init.miui.mi_ext.rc` and overlay init scripts; dry-run verified.
  - Decrypt ROM: Modifies `fileencryption=` options in `fstab*` to `fileencryptable` or strips force-encryption flags safely; dry-run verified.
  - CLI: `dna rom debloat`, `dna rom remove-oat`, `dna rom make-rw`, `dna rom decrypt` all functional with `--target` and `-n/--dry-run`.
  - Automated tests: 36/36 tests passing via `python3 -m unittest discover tests`.
