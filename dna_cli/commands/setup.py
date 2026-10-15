"""CLI command: dna setup for external tool installation."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dna_core.setup import (
    get_setup_tools_status,
    install_apktool,
    install_java,
    install_payload_dumper_go,
    setup_all,
)
from dna_core.tools import check_all_tools


@click.command(name="setup", help="Setup mode: install and configure external tools (apktool, payload-dumper, Java).")
@click.argument("tool_name", required=False, type=click.Choice(["all", "apktool", "payload-dumper", "java"], case_sensitive=False))
@click.option("--status", "-s", is_flag=True, help="Display status of bundled and external tools without installing.")
@click.option("--all", "-a", "install_all", is_flag=True, help="Automatically install and configure all external tools.")
@click.pass_obj
def setup_cmd(ctx_obj, tool_name: str | None, status: bool, install_all: bool) -> None:
    console: Console = ctx_obj["console"]

    console.print("[bold cyan]DNA-Linux Setup Mode: External Tools & Dependencies[/bold cyan]\n")

    # If --status or no arguments given and not installing, show current status
    if status or (tool_name is None and not install_all):
        _display_status(console)
        if not status:
            console.print(
                "\n[dim]To install missing external tools, run:[/dim]\n"
                "  [bold green]dna setup --all[/bold green]                  # Install all external tools\n"
                "  [bold green]dna setup apktool[/bold green]                # Install apktool\n"
                "  [bold green]dna setup payload-dumper[/bold green]         # Install payload-dumper-go\n"
                "  [bold green]dna setup java[/bold green]                   # Check/install OpenJDK\n"
            )
        return

    target = "all" if install_all else (tool_name.lower() if tool_name else "all")

    if target in ("all",):
        console.print("[bold yellow]Starting complete external tools setup...[/bold yellow]\n")
        setup_all(callback=lambda msg: console.print(f"[cyan]{msg}[/cyan]"))
        console.print()
        _display_status(console)

    elif target in ("apktool",):
        console.print("[bold yellow]Installing apktool...[/bold yellow]")
        ok, msg = install_apktool(callback=lambda m: console.print(f"[cyan]{m}[/cyan]"))
        if ok:
            console.print(f"[bold green]✓ {msg}[/bold green]")
        else:
            console.print(f"[bold red]✗ {msg}[/bold red]")

    elif target in ("payload-dumper", "payload-dumper-go"):
        console.print("[bold yellow]Installing payload-dumper-go...[/bold yellow]")
        ok, msg = install_payload_dumper_go(callback=lambda m: console.print(f"[cyan]{m}[/cyan]"))
        if ok:
            console.print(f"[bold green]✓ {msg}[/bold green]")
        else:
            console.print(f"[bold red]✗ {msg}[/bold red]")

    elif target in ("java",):
        console.print("[bold yellow]Checking Java runtime environment...[/bold yellow]")
        ok, msg = install_java(interactive=True, callback=lambda m: console.print(f"[cyan]{m}[/cyan]"))
        if ok:
            console.print(f"[bold green]✓ {msg}[/bold green]")
        else:
            console.print(f"[bold yellow]! {msg}[/bold yellow]")


def _display_status(console: Console) -> None:
    # 1. Bundled tools summary
    all_statuses = check_all_tools()
    bundled = [s for s in all_statuses if s.definition.is_bundled]
    bundled_ready = sum(1 for s in bundled if s.installed and s.source == "bundled")

    console.print(
        Panel.fit(
            f"[bold green]✓ Core Image Unpack/Repack Tools:[/bold green] [bold white]{bundled_ready}/{len(bundled)} Bundled in DNA package[/bold white]\n"
            f"[dim]Includes: e2fsdroid, mke2fs, debugfs, resize2fs, e2fsck, fsck.erofs, mkfs.erofs, lpunpack, lpmake, simg2img, img2simg, brotli, zstd[/dim]",
            border_style="green",
        )
    )
    console.print()

    # 2. External setup tools table
    ext_tools = get_setup_tools_status()
    table = Table(title="External Setup Tools (Managed via Setup Mode)", show_header=True, header_style="bold magenta")
    table.add_column("Status", width=12, justify="center")
    table.add_column("Tool", style="bold")
    table.add_column("Source", width=10)
    table.add_column("Version", style="dim")
    table.add_column("Path / Install Location", style="dim")

    for name, info in ext_tools.items():
        installed = info["installed"]
        src = info["source"]
        ver = info.get("version") or "-"
        path_str = info.get("path") or "Not installed"

        if installed:
            if src == "setup":
                badge = "[green]✓ READY[/green]"
                src_badge = "[cyan]Setup[/cyan]"
            elif src == "bundled":
                badge = "[green]✓ READY[/green]"
                src_badge = "[blue]Bundled[/blue]"
            else:
                badge = "[green]✓ READY[/green]"
                src_badge = "[green]System[/green]"
        else:
            badge = "[yellow]! NOT SETUP[/yellow]"
            src_badge = "[red]Missing[/red]"

        table.add_row(badge, name, src_badge, ver, path_str)

    console.print(table)
