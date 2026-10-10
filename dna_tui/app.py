"""Terminal User Interface (TUI) for DNA-Linux.

Mirroring the DNA-Android layout:
- Home Menu: Project lifecycle, unzip ROM, doctor diagnostics
- Project Menu: Unpack, Repack, Conversion, ROM Menu, Patch Menu, Jar Menu, Plugins
"""

from __future__ import annotations

import curses
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from dna_core.config import get_active_project_name, set_active_project_name
from dna_core.paths import ProjectPaths, get_default_workspace_root
from dna_core.project import (
    Project,
    create_project,
    delete_project,
    get_current_project,
    list_projects,
)
from dna_core.tools import check_all_tools, detect_distribution


@dataclass
class MenuItem:
    """An entry in a TUI menu."""

    key: str
    label: str
    description: str
    handler: Optional[Callable[..., Any]] = None


@dataclass
class TUIState:
    """Runtime state for the TUI application."""

    active_project: Optional[Project] = None
    menu_stack: List[str] = field(default_factory=lambda: ["home"])
    cursor_index: int = 0
    status_message: str = "Ready"


def get_menu_items(state: TUIState) -> List[MenuItem]:
    """Return the list of MenuItem objects for the current active menu."""
    current_menu = state.menu_stack[-1]

    if current_menu == "home":
        items = [
            MenuItem("select_proj", "Select Project", "Switch the currently active workspace"),
            MenuItem("create_proj", "Create New Project", "Create a new project workspace directory"),
            MenuItem("list_proj", "List Projects", "View all project workspaces in ~/DNA"),
            MenuItem("delete_proj", "Delete Project", "Remove an existing workspace directory"),
            MenuItem("unzip_rom", "Unzip ROM Archive", "Extract a ROM ZIP into active project"),
            MenuItem("doctor", "Tool Doctor", "Inspect native tools and system diagnostics"),
        ]
        if state.active_project:
            items.insert(0, MenuItem("goto_project", f"Open Project: {state.active_project.name}", "Enter the active project workspace menu"))
        items.append(MenuItem("exit", "Exit DNA-Linux", "Quit the application"))
        return items

    if current_menu == "project":
        return [
            MenuItem("menu_unpack", "[1] Unpacking Menu", "Extract payload.bin, .br, .dat, .img, .zstd, super.img"),
            MenuItem("menu_repack", "[2] Repacking Menu", "Repack partition images, super.img, zstd, resize"),
            MenuItem("menu_convert", "[3] Format Conversion", "img <-> sparse, img -> dat/br, split/merge super"),
            MenuItem("menu_rom", "[4] ROM Menu", "Debloat, remove oat, make ROM-RW, decrypt fstab"),
            MenuItem("menu_patch", "[5] Patch Menu", "vbmeta, integrity fix, SafetyCore, priv-app, OTA, services"),
            MenuItem("menu_jar", "[6] Jar Menu", "services.jar: Core Patch DSV, APK protection, DSS"),
            MenuItem("menu_plugin", "[7] Plugins Menu", "Discover, run, import, and manage plugins"),
            MenuItem("switch_proj", "Switch Project", "Select a different project workspace"),
            MenuItem("back", "Back to Home Menu", "Return to main home screen"),
        ]

    if current_menu == "unpack":
        return [
            MenuItem("act_unpack_img", "Unpack Partition Image", "Auto-extract ext4 or erofs image"),
            MenuItem("act_unpack_super", "Unpack Super Image", "Extract dynamic partitions via lpunpack"),
            MenuItem("act_unpack_bin", "Unpack payload.bin", "Extract partitions from OTA payload.bin"),
            MenuItem("act_unpack_br", "Unpack Brotli (.br)", "Decompress brotli partition file"),
            MenuItem("act_unpack_dat", "Unpack .new.dat", "Convert .new.dat + transfer.list to raw img"),
            MenuItem("act_unpack_zstd", "Unpack .zst / .zstd", "Decompress zstandard image"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "repack":
        return [
            MenuItem("act_repack_img", "Repack Partition Image", "Build ext4 or erofs partition with SELinux contexts"),
            MenuItem("act_repack_super", "Repack super.img", "Assemble dynamic partitions using lpmake"),
            MenuItem("act_repack_zstd", "Repack zstd Image", "Compress partition image with zstandard"),
            MenuItem("act_resize_img", "Resize ext4 Image", "Expand partition size using resize2fs"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "convert":
        return [
            MenuItem("act_convert_simg", "Convert img <-> sparse", "Convert between raw ext4/erofs and sparse image"),
            MenuItem("act_convert_dat_br", "Convert img -> dat / br", "Convert raw image to .new.dat and brotli"),
            MenuItem("act_super_split", "Split super.img into Chunks", "Divide super.img into sparse chunks"),
            MenuItem("act_super_merge", "Merge Chunks into super.img", "Reassemble super chunks into single image"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "rom":
        return [
            MenuItem("act_rom_debloat_gl", "Debloat ROM (Global)", "Safely remove Global MIUI/HyperOS bloatware"),
            MenuItem("act_rom_debloat_cn", "Debloat ROM (China)", "Safely remove China MIUI/HyperOS bloatware"),
            MenuItem("act_rom_remove_oat", "Remove oat Directories", "Delete all oat optimization caches to free space"),
            MenuItem("act_rom_make_rw", "Make Full ROM-RW", "Remove overlay mounts in fstab and unshare ext4 blocks"),
            MenuItem("act_rom_decrypt", "Decrypt ROM (Disable force-encrypt)", "Modify fstab to allow dirty flashing without encryption"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "patch":
        return [
            MenuItem("act_patch_vbmeta", "Patch vbmeta.img", "Disable dm-verity and dm-verification in AVB header"),
            MenuItem("act_patch_integrity", "Apply Play Integrity Fix", "Spoof certified Pixel 7 Pro fingerprint across build.prop"),
            MenuItem("act_patch_safetycore", "Inject SafetyCore Placeholder", "Install placeholder Safetycore.apk into product/app"),
            MenuItem("act_patch_privapp", "Patch Priv-App Permissions", "Remove ro.control_privapp_permissions to skip enforcement"),
            MenuItem("act_patch_disable_ota", "Disable OTA Updates", "Set support_ota_validate to false in device feature XMLs"),
            MenuItem("act_patch_xiaomi_services", "Disable Xiaomi Telemetry & Services", "Remove MIUIAnalytics, Joyose, Daemon, CloudService"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "jar":
        return [
            MenuItem("act_jar_patch_all", "Apply All Jar Patches", "Single-pass: DSV + APK Protection + Secure Screenshot"),
            MenuItem("act_jar_dsv", "Core Patch — DSV", "Bypass package signature checks in services.jar"),
            MenuItem("act_jar_apk_prot", "Remove APK Protection", "Bypass package installer and downgrade restrictions"),
            MenuItem("act_jar_dss", "Disable Secure Screenshot", "Bypass FLAG_SECURE (includes Android 17 crash safeguard)"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    if current_menu == "plugin":
        return [
            MenuItem("act_plugin_list", "List Installed Plugins", "View all project and global plugins"),
            MenuItem("act_plugin_run", "Run Plugin", "Execute a plugin in the active workspace"),
            MenuItem("act_plugin_import", "Import Plugin Archive", "Install a plugin from a ZIP archive"),
            MenuItem("act_plugin_delete", "Delete Plugin", "Remove an installed plugin"),
            MenuItem("back", "Back to Project Menu", "Return to project menu"),
        ]

    return [MenuItem("back", "Back", "Return")]


def draw_tui(stdscr: curses.window, state: TUIState) -> None:
    """Render the full TUI screen using curses."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    if h < 16 or w < 60:
        stdscr.addstr(0, 0, "Terminal too small. Resize to at least 80x24.")
        stdscr.refresh()
        return

    # Header bar
    header_title = " DNA-Linux Toolkit v1.0.0 (Native x86_64) "
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, 0, header_title.ljust(w - 1))
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    # Active project info bar
    proj_name = state.active_project.name if state.active_project else "[None - Select a project]"
    proj_str = f" Active Workspace: {proj_name} "
    distro = detect_distribution().capitalize()
    distro_str = f" Distro: {distro} "
    info_bar = proj_str + " " * max(0, w - len(proj_str) - len(distro_str) - 1) + distro_str
    stdscr.attron(curses.color_pair(2))
    stdscr.addstr(1, 0, info_bar[: w - 1])
    stdscr.attroff(curses.color_pair(2))

    # Breadcrumb / Section Header
    breadcrumbs = " > ".join(s.upper() for s in state.menu_stack)
    stdscr.attron(curses.A_DIM)
    stdscr.addstr(3, 2, f"Navigation: {breadcrumbs}")
    stdscr.attroff(curses.A_DIM)

    # Menu items
    items = get_menu_items(state)
    start_y = 5
    max_visible_items = h - 9

    if state.cursor_index >= len(items):
        state.cursor_index = max(0, len(items) - 1)

    for idx, item in enumerate(items[:max_visible_items]):
        y = start_y + idx
        is_selected = idx == state.cursor_index
        prefix = " > " if is_selected else "   "

        line_str = f"{prefix}{item.label:<32} {item.description}"
        line_str = line_str[: w - 4]

        if is_selected:
            stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(y, 2, line_str.ljust(w - 4))
            stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
        else:
            stdscr.addstr(y, 2, f"{prefix}{item.label:<32}")
            stdscr.attron(curses.A_DIM)
            desc_room = max(0, w - 4 - 3 - 32)
            stdscr.addstr(y, 37, item.description[:desc_room])
            stdscr.attroff(curses.A_DIM)

    # Status / Footer
    status_bar = f" Status: {state.status_message} "
    stdscr.attron(curses.color_pair(3))
    stdscr.addstr(h - 2, 0, status_bar.ljust(w - 1))
    stdscr.attroff(curses.color_pair(3))

    footer = " [↑/↓] Navigate  [Enter] Select  [Esc/b] Back  [q] Quit "
    stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(h - 1, 0, footer.ljust(w - 1))
    stdscr.attroff(curses.A_REVERSE)

    stdscr.refresh()


def prompt_user_input(stdscr: curses.window, prompt_text: str) -> str:
    """Prompt the user for a single line of text input."""
    curses.echo()
    curses.curs_set(1)
    h, w = stdscr.getmaxyx()

    box_y = h // 2 - 2
    box_w = min(70, w - 4)
    box_x = (w - box_w) // 2

    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(box_y, box_x, " " + prompt_text.ljust(box_w - 2) + " ")
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    stdscr.attron(curses.color_pair(5))
    stdscr.addstr(box_y + 1, box_x, " " * box_w)
    stdscr.attroff(curses.color_pair(5))

    stdscr.refresh()

    raw = stdscr.getstr(box_y + 1, box_x + 2, box_w - 4)
    curses.noecho()
    curses.curs_set(0)
    return raw.decode("utf-8", errors="replace").strip()


def show_message_screen(stdscr: curses.window, title: str, text: str) -> None:
    """Display a full-screen scrollable output screen and wait for keypress."""
    curses.curs_set(0)
    h, w = stdscr.getmaxyx()
    lines = text.splitlines()
    scroll = 0

    while True:
        stdscr.clear()
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(0, 0, f" {title} (Press Enter / Esc to return)".ljust(w - 1))
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        visible_height = h - 3
        for i in range(visible_height):
            line_idx = scroll + i
            if line_idx < len(lines):
                stdscr.addstr(1 + i, 2, lines[line_idx][: w - 4])

        footer = f" Lines {scroll + 1}-{min(len(lines), scroll + visible_height)} of {len(lines)} [↑/↓ to scroll] "
        stdscr.attron(curses.A_REVERSE)
        stdscr.addstr(h - 1, 0, footer.ljust(w - 1))
        stdscr.attroff(curses.A_REVERSE)

        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            scroll = min(max(0, len(lines) - visible_height), scroll + 1)
        elif key in (ord("\n"), 27, ord("q"), ord("b")):
            break


def handle_menu_selection(stdscr: curses.window, state: TUIState, selected: MenuItem) -> bool:
    """Handle the user selection of a MenuItem. Returns False if should exit."""
    key = selected.key

    # Navigation / System
    if key == "exit":
        return False

    if key == "back":
        if len(state.menu_stack) > 1:
            state.menu_stack.pop()
            state.cursor_index = 0
            state.status_message = "Navigated back"
        return True

    if key.startswith("menu_"):
        target_menu = key.replace("menu_", "")
        state.menu_stack.append(target_menu)
        state.cursor_index = 0
        state.status_message = f"Entered {selected.label}"
        return True

    if key == "goto_project":
        state.menu_stack.append("project")
        state.cursor_index = 0
        state.status_message = f"Workspace: {state.active_project.name}"
        return True

    # Project lifecycle
    if key == "select_proj":
        projs = list_projects()
        if not projs:
            state.status_message = "No projects found. Create one first."
            return True
        proj_names = "\n".join(f"• {p.name}" for p in projs)
        chosen = prompt_user_input(stdscr, f"Enter project name (Available:\n{proj_names}):")
        if chosen:
            try:
                state.active_project = get_current_project(chosen)
                set_active_project_name(state.active_project.name)
                state.status_message = f"Selected project: {state.active_project.name}"
                state.menu_stack = ["home", "project"]
                state.cursor_index = 0
            except Exception as e:
                state.status_message = f"Error: {e}"
        return True

    if key == "switch_proj":
        state.menu_stack = ["home"]
        return handle_menu_selection(stdscr, state, MenuItem("select_proj", "", ""))

    if key == "create_proj":
        name = prompt_user_input(stdscr, "Enter new project name:")
        if name:
            try:
                p = create_project(name)
                state.active_project = p
                state.status_message = f"Created and activated project: {p.name}"
                state.menu_stack = ["home", "project"]
                state.cursor_index = 0
            except Exception as e:
                state.status_message = f"Error: {e}"
        return True

    if key == "delete_proj":
        projs = list_projects()
        proj_names = ", ".join(p.name for p in projs)
        target = prompt_user_input(stdscr, f"Enter project name to delete ({proj_names}):")
        if target:
            confirm = prompt_user_input(stdscr, f"Confirm deletion of '{target}'? (type 'yes'):")
            if confirm.lower() == "yes":
                try:
                    delete_project(target)
                    if state.active_project and state.active_project.name == target:
                        state.active_project = None
                    state.status_message = f"Deleted project: {target}"
                except Exception as e:
                    state.status_message = f"Error: {e}"
        return True

    if key == "list_proj":
        projs = list_projects()
        active = get_active_project_name()
        lines = []
        for p in projs:
            prefix = "[* ACTIVE] " if p.name == active else "[        ] "
            lines.append(f"{prefix}{p.name:<24} ({p.directory})")
        out_text = "\n".join(lines) if lines else "No projects found."
        show_message_screen(stdscr, "Project Workspaces", out_text)
        return True

    if key == "doctor":
        results = check_all_tools()
        lines = [f"Linux Distribution: {detect_distribution().capitalize()}\n"]
        for st in results:
            mark = "[✓ INSTALLED]" if st.installed else "[✗ MISSING  ]"
            ver = f"(v{st.version})" if st.version and st.version != "installed" else ""
            lines.append(f"{mark} {st.definition.name:<18} {ver}")
        show_message_screen(stdscr, "DNA-Linux Tool Doctor", "\n".join(lines))
        return True

    # ROM Menu actions
    if key in ("act_rom_debloat_gl", "act_rom_debloat_cn"):
        from dna_core.debloat import load_debloat_preset, run_debloat
        preset_name = "global" if "gl" in key else "china"
        if not state.active_project:
            state.status_message = "No active project selected."
            return True
        try:
            preset = load_debloat_preset(preset_name)
            res = run_debloat(state.active_project.paths.unpacked_dir, preset)
            show_message_screen(
                stdscr,
                f"Debloat {preset_name.capitalize()} Results",
                f"Removed {len(res.removed_directories)} directories\nFreed: {res.freed_bytes / (1024*1024):.1f} MB\n\nAffected components:\n" + "\n".join(res.packages_affected),
            )
        except Exception as e:
            state.status_message = f"Debloat Error: {e}"
        return True

    if key == "act_rom_remove_oat":
        from dna_core.rom_tweaks import remove_oat_directories
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = remove_oat_directories(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Remove OAT Results",
            f"Removed {len(res.removed_directories)} directories.\nFreed: {res.freed_bytes / (1024*1024):.1f} MB",
        )
        return True

    if key == "act_rom_make_rw":
        from dna_core.rom_tweaks import make_rom_rw
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = make_rom_rw(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Make ROM-RW Results",
            f"Fstab files patched: {len(res.modified_fstab_files)}\nInit scripts removed: {len(res.removed_init_files)}",
        )
        return True

    if key == "act_rom_decrypt":
        from dna_core.rom_tweaks import decrypt_rom
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = decrypt_rom(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Decrypt ROM Results",
            f"Fstab encryption disabled in {len(res.modified_fstab_files)} files:\n" + "\n".join(res.modified_fstab_files),
        )
        return True

    # Patch Menu actions
    if key == "act_patch_integrity":
        from dna_core.patch import patch_integrity_fix
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = patch_integrity_fix(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Play Integrity Fix Results",
            f"Spoofed Pixel 7 Pro fingerprint:\n{res['fingerprint']}\n\nModified {len(res['modified_files'])} property files:\n" + "\n".join(res['modified_files']),
        )
        return True

    if key == "act_patch_safetycore":
        from dna_core.patch import patch_safetycore
        if not state.active_project:
            state.status_message = "No active project."
            return True
        try:
            res = patch_safetycore(state.active_project.paths.unpacked_dir)
            show_message_screen(
                stdscr,
                "SafetyCore Patch Results",
                f"Installed placeholder Safetycore.apk into:\n{res['destination']}",
            )
        except Exception as e:
            state.status_message = f"Error: {e}"
        return True

    if key == "act_patch_privapp":
        from dna_core.patch import patch_privapp_permissions
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = patch_privapp_permissions(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Priv-App Permissions Results",
            f"Removed '{res['property_removed']}' from {len(res['modified_files'])} files:\n" + "\n".join(res['modified_files']),
        )
        return True

    if key == "act_patch_disable_ota":
        from dna_core.patch import patch_disable_ota
        if not state.active_project:
            state.status_message = "No active project."
            return True
        res = patch_disable_ota(state.active_project.paths.unpacked_dir)
        show_message_screen(
            stdscr,
            "Disable OTA Results",
            f"Disabled support_ota_validate in {res['count']} XML files:\n" + "\n".join(res['modified_files']),
        )
        return True

    if key == "act_patch_xiaomi_services":
        from dna_core.patch import patch_disable_xiaomi_services
        if not state.active_project:
            state.status_message = "No active project."
            return True
        try:
            res = patch_disable_xiaomi_services(state.active_project.paths.unpacked_dir)
            entries = [f"• {e['package']}: {e['path']}" for e in res["removed_entries"]]
            show_message_screen(
                stdscr,
                "Disable Xiaomi Services Results",
                f"Removed {res['total_removed']} service directories ({res['total_freed_bytes'] / (1024*1024):.1f} MB):\n\n" + "\n".join(entries),
            )
        except Exception as e:
            state.status_message = f"Error: {e}"
        return True

    # Jar Menu actions
    if key in ("act_jar_patch_all", "act_jar_dsv", "act_jar_apk_prot", "act_jar_dss"):
        from dna_core.jar import find_services_jar, patch_services_jar
        if not state.active_project:
            state.status_message = "No active project."
            return True
        target_jar = find_services_jar(state.active_project.paths.unpacked_dir)
        if not target_jar:
            state.status_message = "services.jar not found in unpacked project."
            return True

        dsv = key in ("act_jar_patch_all", "act_jar_dsv")
        prot = key in ("act_jar_patch_all", "act_jar_apk_prot")
        dss = key in ("act_jar_patch_all", "act_jar_dss")

        state.status_message = "Decompiling and patching services.jar... Please wait."
        stdscr.refresh()

        try:
            res = patch_services_jar(
                target_jar,
                patch_dsv=dsv,
                patch_apk_protection=prot,
                patch_dss=dss,
            )
            total = sum(p.get("methods_patched", 0) for p in res["patches_applied"])
            show_message_screen(
                stdscr,
                "Jar Patching Results",
                f"Successfully patched {total} methods in:\n{target_jar}\n(Backup saved to {target_jar}.bak)",
            )
        except Exception as e:
            state.status_message = f"Jar Patch Error: {e}"
        return True

    # Plugin actions
    if key == "act_plugin_list":
        from dna_core.plugin import list_plugins
        plugins = list_plugins(
            project_plugins_dir=state.active_project.paths.plugins_dir if state.active_project else None
        )
        lines = [f"{p.id:<18} v{p.version:<8} [{p.scope}] {p.name}" for p in plugins]
        show_message_screen(stdscr, "Installed Plugins", "\n".join(lines) if lines else "No plugins installed.")
        return True

    # Fallback
    state.status_message = f"Action '{selected.label}' selected."
    return True


def run_curses_loop(stdscr: curses.window) -> None:
    """Main curses event loop."""
    curses.curs_set(0)
    curses.use_default_colors()

    # Initialize colors
    if curses.has_colors():
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)

    state = TUIState()
    # Check if there is an active project
    active_name = get_active_project_name()
    if active_name:
        try:
            state.active_project = get_current_project(active_name)
        except Exception:
            pass

    running = True
    while running:
        draw_tui(stdscr, state)
        key = stdscr.getch()

        items = get_menu_items(state)

        if key in (curses.KEY_UP, ord("k")):
            state.cursor_index = max(0, state.cursor_index - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            state.cursor_index = min(len(items) - 1, state.cursor_index + 1)
        elif key in (ord("\n"), curses.KEY_ENTER):
            if items:
                selected = items[state.cursor_index]
                running = handle_menu_selection(stdscr, state, selected)
        elif key in (27, ord("b")):  # Esc or 'b'
            if len(state.menu_stack) > 1:
                state.menu_stack.pop()
                state.cursor_index = 0
                state.status_message = "Navigated back"
        elif key == ord("q"):
            running = False


def start_tui(force_text: bool = False) -> None:
    """Launch the DNA-Linux TUI."""
    if not sys.stdin.isatty() or force_text:
        # Non-interactive / piped environment fallback
        print("DNA-Linux TUI requires an interactive terminal (TTY). Use 'dna --help' for CLI mode.")
        return

    try:
        curses.wrapper(run_curses_loop)
    except KeyboardInterrupt:
        pass
