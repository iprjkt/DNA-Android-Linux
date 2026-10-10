"""CLI command: dna tui (Launch Terminal User Interface)."""

from __future__ import annotations

import click
from rich.console import Console

from dna_tui.app import start_tui


@click.command(name="tui", help="Launch interactive Terminal User Interface (TUI).")
@click.pass_obj
def tui_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]
    console.print("[dim]Launching DNA-Linux TUI...[/dim]")
    start_tui()
