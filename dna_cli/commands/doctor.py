"""CLI command: dna doctor."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dna_core.tools import (
    check_all_tools,
    detect_distribution,
    get_install_command,
)


@click.command(name="doctor", help="Check native Linux tool dependencies and environment health.")
@click.pass_obj
def doctor_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]

    distro = detect_distribution()
    console.print(f"[bold cyan]DNA-Linux Environment Health & Tool Diagnostics[/bold cyan]")
    console.print(f"Detected Platform: [bold yellow]{distro.title()} Linux (x86_64)[/bold yellow]\n")

    tool_statuses = check_all_tools()

    table = Table(title="Native Linux Tool Status", show_header=True, header_style="bold magenta")
    table.add_column("Status", width=8, justify="center")
    table.add_column("Tool", style="bold")
    table.add_column("Category")
    table.add_column("Type", width=10)
    table.add_column("Version", style="dim")
    table.add_column("Path", style="dim")

    missing_required = []
    missing_optional = []

    for status in tool_statuses:
        defn = status.definition
        if status.installed:
            badge = "[green]✓ OK[/green]"
            ver_text = status.version or "available"
            path_text = str(status.path) if status.path else "-"
        else:
            if defn.required:
                badge = "[red]✗ MISSING[/red]"
                missing_required.append(defn)
            else:
                badge = "[yellow]! OPTIONAL[/yellow]"
                missing_optional.append(defn)
            ver_text = "-"
            path_text = "-"

        type_text = "[bold red]Required[/bold red]" if defn.required else "[dim]Optional[/dim]"
        table.add_row(badge, defn.name, defn.category, type_text, ver_text, path_text)

    console.print(table)
    console.print()

    if not missing_required and not missing_optional:
        console.print(
            Panel.fit(
                "[bold green]All required and optional tools are installed and ready to use![/bold green]",
                border_style="green",
            )
        )
    else:
        if missing_required:
            cmd = get_install_command(missing_required, distro)
            console.print(
                Panel(
                    f"[bold red]Missing Required Tools ({len(missing_required)}):[/bold red]\n"
                    f"To install them on {distro.title()}, run:\n\n"
                    f"  [bold green]{cmd}[/bold green]",
                    title="Action Required",
                    border_style="red",
                )
            )
        if missing_optional:
            opt_cmd = get_install_command(missing_optional, distro)
            console.print(
                Panel(
                    f"[bold yellow]Missing Optional Tools ({len(missing_optional)}):[/bold yellow]\n"
                    f"For full feature support (e.g. F2FS, Java APK patching), run:\n\n"
                    f"  [bold yellow]{opt_cmd}[/bold yellow]",
                    title="Optional Enhancements",
                    border_style="yellow",
                )
            )
