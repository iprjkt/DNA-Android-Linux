"""CLI commands: dna config show | set | get | reset."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console
from rich.table import Table

from dna_core.config import (
    GlobalConfig,
    get_workspace_roots,
    reset_workspace_roots,
    set_workspace_roots,
)


@click.group(name="config", help="Manage DNA-Linux global settings and workspace locations.")
def config_group() -> None:
    pass


@config_group.command(name="show", help="Display all active configuration settings.")
@click.pass_obj
def show_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]
    cfg = GlobalConfig.load()

    table = Table(title="DNA-Linux Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="bold cyan")
    table.add_column("Value", style="dim")

    table.add_row("io_root (Input/Output)", cfg.io_root)
    table.add_row("work_root (Working Dir)", cfg.work_root)
    table.add_row("active_project", str(cfg.active_project or "None"))
    table.add_row("auto_confirm", str(cfg.auto_confirm))
    table.add_row("verbose", str(cfg.verbose))
    table.add_row("background_image", str(cfg.background_image or "Default solid"))

    console.print(table)


@config_group.command(name="set", help="Update a configuration setting (e.g. io_root /mnt/detalmick).")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def set_cmd(ctx_obj, key: str, value: str) -> None:
    console: Console = ctx_obj["console"]
    cfg = GlobalConfig.load()
    clean_key = key.lower().strip()

    if clean_key in ("io_root", "io", "sdcard", "dna_dir"):
        set_workspace_roots(io_root=value)
        console.print(f"[bold green]✓ Updated io_root to:[/bold green] [dim]{value}[/dim]")
    elif clean_key in ("work_root", "work", "data", "dna_tmp"):
        set_workspace_roots(work_root=value)
        console.print(f"[bold green]✓ Updated work_root to:[/bold green] [dim]{value}[/dim]")
    elif clean_key in ("workspace_root", "root"):
        set_workspace_roots(io_root=value, work_root=Path(value) / "work")
        console.print(f"[bold green]✓ Updated workspace roots to:[/bold green] [dim]{value}[/dim]")
    elif clean_key == "active_project":
        cfg.active_project = value
        cfg.save()
        console.print(f"[bold green]✓ Updated active_project to:[/bold green] [dim]{value}[/dim]")
    elif clean_key == "auto_confirm":
        cfg.auto_confirm = value.lower() in ("true", "1", "yes")
        cfg.save()
        console.print(f"[bold green]✓ Updated auto_confirm to:[/bold green] {cfg.auto_confirm}")
    elif clean_key == "verbose":
        cfg.verbose = value.lower() in ("true", "1", "yes")
        cfg.save()
        console.print(f"[bold green]✓ Updated verbose to:[/bold green] {cfg.verbose}")
    elif clean_key == "background_image":
        cfg.background_image = value if value.lower() not in ("none", "clear", "") else None
        cfg.save()
        console.print(f"[bold green]✓ Updated background_image to:[/bold green] {cfg.background_image}")
    else:
        console.print(f"[bold red]Unknown configuration setting:[/bold red] '{key}'.")
        console.print("Available settings: io_root, work_root, active_project, auto_confirm, verbose, background_image")
        raise click.Abort()


@config_group.command(name="get", help="Retrieve the value of a configuration setting.")
@click.argument("key")
@click.pass_obj
def get_cmd(ctx_obj, key: str) -> None:
    console: Console = ctx_obj["console"]
    cfg = GlobalConfig.load()
    clean_key = key.lower().strip()

    if clean_key in ("io_root", "io", "sdcard", "dna_dir"):
        console.print(cfg.io_root)
    elif clean_key in ("work_root", "work", "data", "dna_tmp"):
        console.print(cfg.work_root)
    elif clean_key in ("workspace_root", "root"):
        console.print(cfg.workspace_root)
    elif clean_key == "active_project":
        console.print(cfg.active_project or "")
    elif clean_key == "auto_confirm":
        console.print(str(cfg.auto_confirm).lower())
    elif clean_key == "verbose":
        console.print(str(cfg.verbose).lower())
    elif clean_key == "background_image":
        console.print(cfg.background_image or "")
    else:
        console.print(f"[bold red]Unknown configuration setting:[/bold red] '{key}'.")
        raise click.Abort()


@config_group.command(name="reset", help="Reset IO and Work roots back to system defaults.")
@click.pass_obj
def reset_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]
    cfg = reset_workspace_roots()
    console.print("[bold green]✓ Reset workspace roots to system defaults:[/bold green]")
    console.print(f"  IO Root:   [dim]{cfg.io_root}[/dim]")
    console.print(f"  Work Root: [dim]{cfg.work_root}[/dim]")
