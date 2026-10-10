"""CLI command: dna gui (Launch Desktop Graphical User Interface)."""

from __future__ import annotations

import os
import sys
import click
from rich.console import Console


@click.command(name="gui", help="Launch interactive Desktop Graphical User Interface (GUI).")
@click.pass_obj
def gui_cmd(ctx_obj) -> None:
    """Launch the modern PyQt6 desktop GUI application."""
    console: Console = ctx_obj.get("console", Console())

    # Check display environment
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        console.print(
            "[bold red]Error:[/bold red] No graphical display session detected (DISPLAY or WAYLAND_DISPLAY not set).\n"
            "If running over SSH, use [cyan]ssh -X[/cyan] or run [green]dna tui[/green] instead."
        )
        sys.exit(1)

    try:
        from dna_gui.app import start_gui
    except ImportError as exc:
        console.print(
            f"[bold red]Error loading GUI:[/bold red] {exc}\n\n"
            "Please ensure PyQt6 is installed:\n"
            "  Arch Linux:    [cyan]sudo pacman -S python-pyqt6[/cyan]\n"
            "  Ubuntu/Debian: [cyan]sudo apt install python3-pyqt6[/cyan]\n"
            "  Pip:           [cyan]pip install PyQt6[/cyan]"
        )
        sys.exit(1)

    console.print("[dim]Launching DNA-Linux Desktop GUI...[/dim]")
    exit_code = start_gui()
    sys.exit(exit_code)
