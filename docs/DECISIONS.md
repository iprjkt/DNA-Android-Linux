# DNA-Linux Architectural Decisions (Phase 0)

This document records the foundational architectural decisions made for **DNA-Linux**.

---

## ADR-001: Language and Orchestration Platform
* **Decision:** Use **Python 3.11+** for core logic, file management, data transformations, and CLI orchestration.
* **Rationale:**
  - Python 3.11+ provides native type annotations, dataclasses, tomllib for standard configuration parsing, and fast standard library execution.
  - Avoids brittle shell scripts while enabling full unit-testing with `pytest`.
  - Android ROM tooling on Linux heavily interfaces with Python scripts (e.g., `avbtool`, `sdat2img`, `payload_dumper`).
  - Cross-distro portability on Arch Linux, Debian/Ubuntu, and Fedora without requiring compilation steps for the core CLI.

---

## ADR-002: Architecture & Core / UI Separation
* **Decision:** Strict modular separation into four distinct layers:
  1. `dna_core/`: Pure business logic, filesystem abstractions, binary tool wrappers, ROM parsers, patch engines. Zero UI dependencies. Fully unit-testable.
  2. `dna_cli/`: CLI presentation layer using `click` or standard `argparse` with `rich` for formatting, progress bars, and colored output.
  3. `dna_tui/`: (Phase 7) Terminal User Interface (mirroring the original app tabs and menu hierarchy).
  4. `dna_gui/`: (Future phase) Optional desktop GUI.
* **Rationale:** Decoupling UI from core operations ensures CLI scripts, automated pipelines, and interactive interfaces can share identical, reliable backend routines.

---

## ADR-003: Workspace & State Management
* **Decision:** Mirror the Android app's concept using structured workspace directories:
  ```
  ~/DNA/
  └── DNA_<project-name>/
      ├── rom/            # Extracted ZIP contents
      ├── images/         # Raw / sparse partition images (.img)
      ├── unpacked/       # Extracted directory trees per partition (system/, vendor/, etc.)
      ├── config/         # SELinux file_contexts and fs_config files
      ├── out/            # Repacked results (images, super.img, flashable zips)
      ├── plugins/        # Project-level plugins
      ├── logs/           # Operation-specific log files
      └── project.toml    # Project metadata, source ROM info, active state
  ```
  Global configuration and active project pointer stored in `~/.config/dna-linux/config.toml`.
* **Rationale:** Provides strict project isolation. No operations write outside the active project folder, preventing accidental damage to the host system.

---

## ADR-004: Native Linux Toolchain Integration & Userspace Safety
* **Decision:**
  - Reject all bundled ARM binaries.
  - Rely exclusively on native x86_64 binaries (`brotli`, `zstd`, `simg2img`, `img2simg`, `lpunpack`, `lpmake`, `e2fsdroid`, `mke2fs`, `resize2fs`, `e2fsck`, `fsck.erofs`, `mkfs.erofs`, `extract.f2fs`, `sload_f2fs`, `avbtool`, `apktool`, `smali`, `baksmali`).
  - Provide a tool abstraction layer (`dna_core/tools.py`) that checks availability, validates paths, and provides clear distro-specific installation instructions via `dna doctor`.
  - **No root/sudo requirement:** Use userspace tools (`fsck.erofs --extract`, `debugfs rdump`, `mke2fs` + `e2fsdroid`) to extract and build filesystem images without mounting or requiring elevated root privileges.

---

## ADR-005: Preservation of Android Security Attributes
* **Decision:** Always dump and recreate exact filesystem metadata:
  - Extract SELinux file contexts to `<partition>_file_contexts`.
  - Extract permissions, uid, gid, and file capabilities to `<partition>_fs_config`.
  - Set Android build epoch timestamp (`1230768000`) for reproducible builds.
  - Re-inject these files using `e2fsdroid -C ... -S ...` and `mkfs.erofs --fs-config-file ... --file-contexts ...`.
* **Rationale:** Preserving exact SELinux contexts and permissions is critical to ensure repacked ROMs boot successfully and do not bootloop due to permission denials.

---

## ADR-006: Data-Driven Configuration for Debloating and Property Edits
* **Decision:**
  - Store debloating definitions in structured TOML files (`data/debloat/global.toml`, `china.toml`).
  - Implement a lossless `build.prop` editor in `dna_core/prop.py` that parses, modifies, and serializes property files while preserving line order, comments, and spacing.
* **Rationale:** Eliminates brittle hardcoded lists, allows users to provide custom debloat presets, and prevents `build.prop` corruption.

---

## ADR-007: Resilient Smali Bytecode Patching
* **Decision:** Implement framework patches (`services.jar`, etc.) using target class and method signature descriptors rather than static line offsets.
* **Rationale:** Android framework bytecode shifts between OS versions (Android 13, 14, 15, 16) and OEM revisions (HyperOS, MIUI). Descriptor-based matching with fallback pattern detection ensures safe, targeted patching and fails cleanly if a method signature is not recognized.

---

## ADR-008: Licensing & Independent Clean-Room Implementation
* **Decision:**
  - Re-implement all features purely based on observed behavior, menu options, and standard Android ROM modding specifications.
  - Maintain clean separation from third-party code.
  - Track third-party native tools and their licenses in `docs/THIRD_PARTY.md` and authors in `CREDITS.md`.
  - Solicit user preference for project license (`LICENSE`).
