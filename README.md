# DNA-Linux — Porting DNA-Android to Linux

> **Instructions for Google Antigravity (AI coding agent).**
> Read this whole file before writing any code. Work phase by phase, verify each phase, and keep a running `PROGRESS.md`.

---

## 1. Goal

Port **DNA-Android** (an on-device Android ROM unpack/repack/patch toolkit, modded by @SoutaEver) to a **native Linux (x86_64) tool** called **DNA-Linux**.

The original app is a GUI front-end (Home + Others tabs, Project Menu) running bundled shell scripts and ARM binaries on the phone. The Linux version must reproduce the **same workflows and feature set** using native x86_64 tools, with a clean CLI first and an optional TUI/GUI afterwards.

**Primary target:** Arch Linux (KDE Plasma). Must also work on Debian/Ubuntu-based distros.

**Non-goals**
- Do not run or emulate the Android app (no Waydroid/Anbox wrapper).
- Do not require an Android device or root to operate.
- Do not copy proprietary or unlicensed code blindly (see Section 9).

---

## 2. Reference: DNA-Android feature map

The original UI is organized as below. Treat this as the **source of truth for scope**. (Some entries between "Repack zstd" and "Repack super.img" were not visible in the screenshots, so inspect the original app, scripts, and binaries to find anything missing, and list it in `docs/FEATURES.md`.)

### 2.1 Home
| Feature | Behavior |
|---|---|
| Select Project | Choose the active project directory (original: `/sdcard/DNA/DNA_<name>`) |
| Delete Project | Remove a project directory (with confirmation) |
| Create New Project | Create a new project workspace |
| Unzip ROM | Extract a ROM zip into the active project |
| Project Menu | Opens all project operations below |

### 2.2 Project Menu

**Plugin Functions**
- Import local plugins from a zip package (original text: "Local plugins can be imported using file.zip2").
- Linux version: define a documented plugin format (zip with `plugin.toml` + scripts) and an importer. Keep compatibility with the original format where it can be determined.

**Unpacking Menu**
- Unpack `bin` (payload.bin / OTA)
- Unpack `br` (brotli)
- Unpack `dat` (new.dat → img)
- Unpack `img` (ext4 / erofs / f2fs / sparse)
- Unpack `zstd`
- Unpack `super`

**Repacking Menu**
- Resize img partition
- Repack single img partition
- Repack `zstd`
- *(additional items not visible in screenshots — discover from the original)*
- Repack `super.img`

**Format Conversion**
- img ↔ simg (sparse image) conversion
- img ↔ dat ↔ br conversion
- Merge split img into `super.img` ("Restore the original super.img")
- Split `super.img` into parts ("Sparse super.img into evenly sized parts")

**Jar Menu** (framework/services patching)
- Core patch – DSV: enables direct installation of system apps by bypassing signature verification
- Remove APK Protection: disables the built-in APK protection of stock ROMs so modified system apps can be replaced
- Disable secure screenshot: removes screenshot/screenrecord restrictions for all apps (warn the user about the privacy implications)

**Patch Menu**
- Patch `vbmeta` (disable verity/verification flags)
- Integrity fix (change device fingerprint to Pixel 7 Pro)
- Patch SafetyCore (add a SafetyCore placeholder)
- Patch Priv-App Permissions (remove `ro.control_privapp_permissions` so privapp-permissions enforcement is skipped)
- Disable OTA Update (stop automatic OTA downloads/updates)
- Disable Xiaomi services (free background processes)

**Rom Menu**
- Debloat MIUI/HyperOS (MIUI 13/14, HyperOS 1.0/2.0/2.0.2 per the original description; make the debloat lists data-driven)
- Remove `oat` (delete `oat` folders to free space and prevent optimized ART files from being used)
- Make full ROM-RW (enable full read-write access on the ROM image)
- ROM decryption (modify `fstab` to allow dirty flash)

---

## 3. Architecture requirements

1. **Language:** Python 3.11+ for orchestration (or Rust/Go if you can justify it in `docs/DECISIONS.md`). Shell scripts only as thin wrappers.
2. **Core / UI separation:**
   - `dna_core/` — pure logic, no UI, fully unit-testable
   - `dna_cli/` — CLI (`dna <command>`), the first deliverable
   - `dna_tui/` — optional TUI (Textual or similar) mirroring the Home → Project Menu layout
   - `dna_gui/` — optional, only after CLI and TUI are stable
3. **Workspace layout** (mirror the original idea):
   ```
   ~/DNA/
   └── DNA_<project-name>/
       ├── rom/            # extracted zip contents
       ├── images/         # raw/sparse img, super parts
       ├── unpacked/       # per-partition extracted trees (system, vendor, product, ...)
       ├── out/            # repacked results
       ├── plugins/
       └── project.toml    # project metadata and state
   ```
4. **Idempotent & safe:** every destructive step must support `--dry-run`, create a backup or work on a copy, and never write outside the project directory.
5. **Logging:** structured log per operation in `<project>/logs/`, plus readable console output.
6. **Config:** user config in `~/.config/dna-linux/config.toml`.
7. **No hardcoded paths** such as `/sdcard`. Use a `Paths` abstraction.

---

## 4. Tool mapping (Android binaries → Linux equivalents)

Do **not** ship ARM binaries. Detect native tools at startup (`dna doctor`) and print the exact install command per distro. Bundle nothing that is not redistributable.

| DNA-Android function | Linux tool(s) |
|---|---|
| Unpack bin (OTA payload) | `payload-dumper-go` or `payload_dumper` |
| Unpack / convert br | `brotli` |
| Unpack / convert dat | `sdat2img` (unpack), `img2sdat` (repack) |
| Unpack zstd / repack zstd | `zstd` |
| Sparse ↔ raw | `simg2img`, `img2simg`, `simg2simg` (`android-tools` / `android-sdk-libsparse-utils`) |
| Unpack super / repack super / split / merge | `lpunpack`, `lpmake`, `lpdump`, `simg2img` |
| Unpack img: ext4 | `debugfs rdump` (no root needed) or loop mount when root is available |
| Unpack img: erofs | `erofs-utils` (`fsck.erofs --extract`) |
| Unpack img: f2fs | `f2fs-tools` (`extract.f2fs`) |
| Repack img: ext4 | `mke2fs` + `e2fsdroid` (or `make_ext4fs`), `resize2fs`, `e2fsck` |
| Repack img: erofs | `mkfs.erofs` |
| Resize partition | `resize2fs`/`e2fsck` (ext4), rebuild with new size (erofs) |
| Make full ROM-RW | `e2fsck -E unshare_blocks` + `resize2fs` for ext4; convert erofs → ext4 |
| vbmeta patch | `avbtool` or direct flags patch in the vbmeta header |
| Jar/APK patching | `apktool` / `smali` + `baksmali`, `zipalign`, `apksigner`, JDK 17+ |
| Zip handling | `zip`, `unzip`, Python `zipfile` |

Add an abstraction layer (`dna_core/tools.py`) so each backend can be swapped without touching feature code.

---

## 5. Implementation phases

Complete and verify each phase before the next. After each phase, update `PROGRESS.md` and commit.

### Phase 0 — Recon
- Inspect the original DNA-Android APK and its assets (scripts, binaries, configs, plugin format) to document every command it runs.
- Produce `docs/FEATURES.md`: every menu item → original script/command → Linux equivalent.
- Produce `docs/DECISIONS.md`.

### Phase 1 — Foundation
- Project scaffold, packaging (`pyproject.toml`), `dna doctor`, logging, config, `Paths`.
- Project commands: `dna project create | select | delete | list`, `dna unzip-rom`.

### Phase 2 — Unpack / Repack / Convert
- Implement every item of **Unpacking Menu**, **Repacking Menu**, and **Format Conversion**.
- Auto-detect the filesystem type (ext4 / erofs / f2fs / sparse) instead of asking the user.
- Preserve **file contexts (SELinux labels), permissions, ownership, symlinks, and capabilities** when unpacking and repacking. Save them to `fs_config` / `file_contexts` files for repack.

### Phase 3 — ROM Menu
- Debloat (data-driven lists in `data/debloat/*.toml`), Remove oat, Make full ROM-RW, ROM decryption.

### Phase 4 — Patch Menu
- vbmeta, Integrity fix, SafetyCore placeholder, Priv-App permissions, Disable OTA, Disable Xiaomi services.
- All property edits go through one `build.prop` editor module that preserves ordering and comments.

### Phase 5 — Jar Menu
- Core patch DSV, Remove APK Protection, Disable secure screenshot.
- Implement as **patch descriptors** (target jar/apk, class, method, smali change) so patches survive ROM version changes. Fail clearly when a signature is not found; never patch blindly.

### Phase 6 — Plugins
- Plugin spec, importer (`dna plugin import file.zip`), sandboxed execution (restricted to the project directory), and one example plugin.

### Phase 7 — TUI (and optional GUI)
- Mirror the original navigation: Home → Project Menu → sections above. Dark theme.

### Phase 8 — Docs and release
- User README, man page, shell completions, `PKGBUILD` for Arch, and `.deb` build script.

---

## 6. CLI design

```
dna doctor
dna project create <name> | select <name> | delete <name> | list
dna rom unzip <rom.zip>

dna unpack  bin|br|dat|img|zstd|super <file>
dna repack  img|zstd|super [options]
dna resize  <partition> --size <bytes|MiB>
dna convert img-simg|img-dat-br <file>
dna super   split|merge [options]

dna jar     core-patch-dsv | remove-apk-protection | disable-secure-screenshot
dna patch   vbmeta | integrity-fix | safetycore | privapp-permissions | disable-ota | disable-xiaomi-services
dna rom     debloat | remove-oat | make-rw | decrypt

dna plugin  import <file.zip> | list | run <name>
```

Global flags: `--project <path>`, `--dry-run`, `--verbose`, `--yes`, `--log-file`.

---

## 7. Quality requirements

- Unit tests for `dna_core` (pytest). Use small synthetic images (tiny ext4/erofs) in CI, not real ROMs.
- Round-trip tests: unpack → repack → unpack must produce identical trees (content, perms, contexts).
- Lint/format: `ruff`, `mypy` (strict on `dna_core`).
- GitHub Actions: run tests on Ubuntu and an Arch container.
- Clear, actionable error messages (which tool is missing, which file failed, and what to try).

---

## 8. Safety and UX rules

- Confirm before any destructive or irreversible operation unless `--yes` is passed.
- Show a short warning for privacy/security-sensitive patches (secure screenshot, signature bypass, vbmeta, integrity fix) and require explicit opt-in.
- Never touch anything outside the active project directory.
- Include the original disclaimer in spirit: the tool does not intentionally damage anything, but the user is responsible for what they flash.

---

## 9. Licensing and credits

- DNA-Android is a third-party tool (modded by @SoutaEver). **Check its license before reusing any scripts, assets, or binaries.** If reuse isn't clearly permitted, **re-implement** behavior from scratch based on observed functionality only.
- Credit the original authors in `CREDITS.md`.
- Each bundled/third-party tool keeps its own license; list them in `THIRD_PARTY.md`.

---

## 10. Definition of done

- [ ] `dna doctor` reports tool status and install hints on Arch and Ubuntu
- [ ] Every feature in Section 2 has a working CLI command and a test
- [ ] Round-trip unpack/repack verified on at least one ext4 and one erofs image
- [ ] A super.img can be unpacked, modified, repacked, and split/merged without corruption
- [ ] Patches are descriptor-based and fail safely when targets aren't found
- [ ] TUI mirrors the original Home / Project Menu structure
- [ ] Docs, packaging (`PKGBUILD`), and CI are in place

---

## 11. Repository and GitHub

- **Owner:** `iprjkt`
- **Repository:** `https://github.com/iprjkt/DNA-Linux`
- **Default branch:** `main`
- Initialize git at the project root and add a proper `.gitignore` (Python caches, `*.img`, `*.bin`, `*.dat`, `*.br`, ROM zips, `~/DNA` workspaces, and any bundled third-party binaries). **Never commit ROM files or large binaries.**
- Add a `LICENSE` file. Ask the user which license to use, and make sure it is compatible with the licenses of the tools and any reused code (see Section 9).
- Commit style: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`), one logical change per commit, one PR/branch per phase (`phase-1-foundation`, `phase-2-unpack-repack`, ...).
- GitHub Actions: run lint and tests on every push and pull request (see Section 7).
- Releases: tag with SemVer (`v0.1.0`, ...) and attach the built package.
- **Do not push on your own.** Prepare commits locally and ask the user to confirm before `git push`. Never store tokens or credentials in the repo.

---

## 12. How to work (for the agent)

1. Start with **Phase 0** and show the feature/command mapping before coding.
2. Ask before making decisions that change scope or add dependencies.
3. Keep commits small and phase-scoped; update `PROGRESS.md` after each.
4. If a required tool or sample file is missing, stop and ask the user instead of guessing.
