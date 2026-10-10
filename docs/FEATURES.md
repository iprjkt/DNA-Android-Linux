# DNA-Linux Feature & Command Mapping (Phase 0 Recon)

This document provides the complete mapping from the original **DNA-Android** (v9.0.0 modded by @SoutaEver) features, UI actions, scripts, and ARM binaries to their native Linux equivalents in **DNA-Linux**.

---

## 1. Home Menu

| Original Feature | Original Trigger / Script | Original Android Mechanism | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Select Project** | `echo $TSL > $TMPDIR/DNA.ini` | Stores project name in `$TMPDIR/DNA.ini`, targeting `/sdcard/DNA/DNA_<name>` | `dna project select <name>` | Updates active project state in `~/.config/dna-linux/config.toml` or workspace pointer. |
| **Delete Project** | `samples/project.sh SC` | `rm -rf $DNA_DIR/$i` and `rm -rf $DNA_TMP/$i`, clears `DNA.ini` if deleted | `dna project delete <name>` | Safely deletes `~/DNA/DNA_<name>` with confirmation prompt (bypassed with `--yes`). |
| **Create New Project** | `samples/project.sh XJ` | `mkdir -p $DNA_DIR/DNA_$T` (adds timestamp if exists) and writes `DNA.ini` | `dna project create <name>` | Creates standard project layout (`rom/`, `images/`, `unpacked/`, `out/`, `plugins/`, `logs/`, `project.toml`). |
| **List Projects** | `samples/project.sh CK` | Lists subdirectories matching `DNA_*` in `/sdcard/DNA` | `dna project list` | Lists all workspaces in `~/DNA/` and indicates the active one. |
| **Unzip ROM** | `dna unzip --delete $silence $DNA_DIR/$ZIP $DNA_DIR` | Extracts zip into DNA workspace, optionally deletes zip | `dna rom unzip <rom.zip> [--delete]` | Python `zipfile` / `unzip` with streaming extraction and progress bar into `<project>/rom/`. |

---

## 2. Project Menu — Unpacking Menu

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Unpack bin** | `dna dumper --partition "$img" --delete $silence --auto $auto $DNA_PRO/payload.bin` | Extracts partitions from OTA `payload.bin` | `dna unpack bin <file> [--partition <list>] [--auto] [--delete]` | Native `payload-dumper-go` or pure Python OTA protobuf dumper. |
| **Unpack br** | `dna extract $BR --delete $silence` | Invokes `brotli -df <file>` | `dna unpack br <file> [--delete]` | Native `brotli -d` (via CLI or `brotli` Python module). |
| **Unpack dat** | `dna extract $DAT --delete $silence` | Reads `<name>.transfer.list` + `<name>.new.dat` and writes `<name>.img` via `sdat2img` | `dna unpack dat <file> [--delete]` | Pure Python `sdat2img` implementation inside `dna_core`. |
| **Unpack img** | `dna extract $IMG --delete $silence` | Auto-detects FS type (`ext`, `erofs`, `f2fs`, `sparse`), extracts tree and dumps `fs_config` / `file_contexts` | `dna unpack img <file> [--out <dir>] [--delete]` | Auto-detects filesystem magic: <br>• Sparse: `simg2img`<br>• ext4: `debugfs rdump` or pure Python ext4 reader<br>• erofs: `fsck.erofs --extract=<dir>`<br>• f2fs: `extract.f2fs`<br>Preserves permissions, contexts, and capabilities. |
| **Unpack zstd** | `samples/u_zstd_img.sh` | Invokes `zstd -d -k -f <file> -o out/<name>.img` | `dna unpack zstd <file> [--delete]` | Native `zstd -d` CLI or Python `zstandard` / `pyzstd`. |
| **Unpack super** | `dna lpunpack --partition "$img" --delete $silence --auto $auto $DNA_PRO/super.img` | Extracts dynamic partitions (`system`, `vendor`, `product`, etc.) from `super.img` | `dna unpack super <file> [--partition <list>] [--auto] [--delete]` | Native `lpunpack` (from `android-tools`). Auto-unpack optionally unpacks resulting imgs. |

---

## 3. Project Menu — Repacking Menu

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Resize img partition** | `Resize img partition` script in `dna.xml` | Appends zero-bytes with `dd`, then runs `resize2fs` | `dna resize <img_file> --size <bytes|MiB>` | `truncate`/`dd` + `e2fsck -f` + `resize2fs` for ext4. |
| **Repack single img partition** | `dna repack $IMG_DIR ...` | Uses `mke2fs` + `e2fsdroid` (ext4), `mkfs.erofs` (erofs), or `mkfs.f2fs` + `sload_f2fs` (f2fs) using saved `fs_config` & `file_contexts` | `dna repack img <dir> [--fs ext4|erofs|f2fs] [--sparse|--raw] [--format img|dat|br] ...` | Executes native toolchain with exact SELinux labels, capabilities, uid/gid, and timestamp (1230768000). Optional conversion to sparse or `.new.dat[.br]`. |
| **Repack zstd** | `samples/zstd_img.sh` | Invokes `zstd -$level -T4 -f <in> -o <out>` | `dna repack zstd <file> [--level 0-19] [--delete]` | Native `zstd` with configurable compression level and multi-threading. |
| **Repack super.img** | `dna lpmake --type $type --format $from --super_size $size --super_group $super_group $IMG_NAME` | Runs `lpmake` with partition geometry, dynamic group, and image paths | `dna repack super [--type A|AB|VAB] [--format raw|sparse] [--size <GB|bytes>] [--group <name>] <images...>` | Runs native `lpmake` with computed metadata size, slot geometry, dynamic partition groups, and partition entries. |

---

## 4. Project Menu — Format Conversion

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **img-simg Conversion** | `samples/img_ov_simg.sh` | Converts raw ext/erofs to sparse (`img2simg`), or sparse to raw (`simg2img`) | `dna convert img-simg <file> [--out <file>] [--delete]` | Native `img2simg` / `simg2img` based on detected magic bytes. |
| **img-dat-br Conversion** | `dna convert $IMG --type $from --br $brze` | Runs `img2sdat` to generate `.new.dat` and optional `brotli -q` | `dna convert img-dat-br <file> [--to dat|br] [--br-level 1-7] [--delete]` | Python `img2sdat` implementation followed by native `brotli`. |
| **Merge split img into super.img** | `tools/merge_superchunk` | Reconstructs single `super.img` from chunk files `super.img.00`, `.01`... | `dna super merge <chunk_files...> [--out super.img] [--delete]` | Native `simg2img` chunk merging. |
| **Split super.img into parts** | `tools/seprate_superchunk` | Splits `super.img` into 4 to 25 sparse chunks | `dna super split <super.img> [--parts <N>] [--chunk-size <size>] [--delete]` | Native `simg2simg` splitting. |

---

## 5. Project Menu — Jar Menu

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Core patch — DSV** | `tools/dsv_a13+` / `dsv_a15+` | Decompiles `services.jar`, patches signature verification methods to always return true, recompiles | `dna jar core-patch-dsv [--version a13+|a15+] [--disable-invoke-custom]` | Descriptor-based smali patcher using native `baksmali` / `smali` (or `apktool`) targeting signature check methods in `services.jar`. |
| **Remove APK Protection** | `tools/apk_protection_a13+` / `a15+` | Disables OEM/stock APK verification in `services.jar` | `dna jar remove-apk-protection [--version a13+|a15+] [--disable-invoke-custom]` | Descriptor-based patcher targeting installer verification methods. |
| **Disable secure screenshot** | `tools/dss_a13+` / `a15+` | Disables `FLAG_SECURE` checks in `WindowState.smali` / `WindowManagerService.smali` | `dna jar disable-secure-screenshot [--version a13+|a15+] [--disable-invoke-custom]` | Descriptor-based smali patcher overriding `isSecureLocked()` / secure flag evaluation. Includes safety warning. |

---

## 6. Project Menu — Patch Menu

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Patch vbmeta** | `tools/patch_vbmeta` | Sets flags at offset 120/123 in `vbmeta.img` (disable verity: 1, disable verification: 2, both: 3) | `dna patch vbmeta <file> [--mode verity|verification|both]` | AVB header patcher (modifies AVB header flags directly or uses `avbtool`). |
| **Integrity fix** | `tools/integrityfix` | Edits `build.prop` files to spoof Google Pixel 7 Pro fingerprint | `dna patch integrity-fix [--fingerprint <fp>]` | `build.prop` editor applying certified fingerprint values (`ro.build.fingerprint`, etc.). |
| **Patch SafetyCore** | `samples/safetycore.sh` | Installs placeholder `Safetycore.apk` into `product/app/Safetycore/` | `dna patch safetycore` | Copies bundled clean placeholder `Safetycore.apk` into target product app tree. |
| **Patch Priv-App Permissions** | `samples/patch_enforce.sh` | Removes `ro.control_privapp_permissions` line from `vendor/build.prop` | `dna patch privapp-permissions` | Dedicated `build.prop` editor cleanly removing the property while preserving comments and order. |
| **Disable OTA Update** | `samples/remove_ota_update.sh` | Sets `support_ota_validate` to `false` in `product/etc/device_features/*.xml` | `dna patch disable-ota` | XML parser/updater for Xiaomi device feature XMLs. |
| **Disable Xiaomi services** | `tools/xiaomi_tweaks` | Removes or disables Xiaomi background telemetry and analytics packages | `dna patch disable-xiaomi-services` | Config-driven remover for bloat services (`MIUIAnalytics`, `CloudService`, `Joyose`). |

---

## 7. Project Menu — ROM Menu

| Original Feature | Original Trigger / Binary | Original Behavior / Logic | DNA-Linux Equivalent | Linux Implementation Details |
|---|---|---|---|---|
| **Debloat MIUI / HyperOS** | `tools/debloat_cn` / `debloat_gl` | Deletes predefined lists of bloat packages from `system`, `product`, `system_ext` | `dna rom debloat [--preset global|china|<custom.toml>]` | Data-driven debloater driven by TOML package lists in `data/debloat/`. |
| **Remove oat** | `samples/rm_oat.sh` | `find . -type d -name "oat" -exec rm -rf {} +` | `dna rom remove-oat` | Pure Python directory walker removing all `oat` folders from unpacked trees. |
| **Make full ROM-RW** | `samples/rw_full_rom.sh` | Removes `overlay` from `vendor/etc/fstab*`, deletes `init.miui.mi_ext.rc`, unshares ext4 blocks | `dna rom make-rw` | Edits `fstab*` to remove overlay mounts, removes init script, and handles ext4 `unshare_blocks`. |
| **ROM decryption** | `samples/decrypt_rom.sh` | Replaces `fileencryption` with `fileencryptable` in `vendor/etc/fstab*` | `dna rom decrypt` | Smart `fstab` parser replacing encryption flags. |

---

## 8. Plugins

| Original Feature | Original Format | DNA-Linux Specification |
|---|---|---|
| **Plugin Packaging** | `.zip2` archive with shell script | `.zip` archive containing `plugin.toml` metadata and executable script/entrypoint |
| **Plugin Execution** | Unzipped into `$START_DIR/module/` and executed directly | Sandboxed execution restricted to active workspace directory with environment variables (`DNA_PROJECT`, `DNA_UNPACKED`, `DNA_OUT`, `DNA_IMAGES`). |
