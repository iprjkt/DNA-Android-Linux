"""CLI commands for DNA plugin management and execution (dna plugin ...)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.table import Table

from dna_core.plugin import (
    delete_plugin,
    get_global_plugins_dir,
    get_plugin,
    import_plugin,
    list_plugins,
    run_plugin,
)
from dna_core.project import get_current_project


@click.group(name="plugin", help="Plugin management and sandboxed execution commands.")
def plugin_group() -> None:
    pass


def _get_project_plugins_dir(ctx_obj) -> Optional[Path]:
    """Return active project plugins directory if a project is active."""
    try:
        proj = get_current_project(ctx_obj.get("project"))
        return proj.paths.plugins_dir
    except Exception:
        return None


@plugin_group.command(name="list", help="List all installed project and global plugins.")
@click.pass_obj
def list_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]
    proj_plugins_dir = _get_project_plugins_dir(ctx_obj)

    plugins = list_plugins(project_plugins_dir=proj_plugins_dir, include_global=True)

    if not plugins:
        console.print("[yellow]No plugins installed.[/yellow]")
        console.print("Import a plugin using: [cyan]dna plugin import <archive.zip>[/cyan]")
        return

    table = Table(title="Installed DNA Plugins", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="bold cyan")
    table.add_column("Name")
    table.add_column("Version", style="dim")
    table.add_column("Scope", style="green")
    table.add_column("Author", style="dim")
    table.add_column("Description")

    for p in plugins:
        table.add_row(
            p.id,
            p.name,
            p.version,
            p.scope,
            p.author,
            p.description,
        )

    console.print(table)


@plugin_group.command(name="info", help="Display details and metadata for a specific plugin.")
@click.argument("plugin_id", type=str)
@click.pass_obj
def info_cmd(ctx_obj, plugin_id: str) -> None:
    console: Console = ctx_obj["console"]
    proj_plugins_dir = _get_project_plugins_dir(ctx_obj)

    try:
        p = get_plugin(plugin_id, project_plugins_dir=proj_plugins_dir)
    except KeyError:
        console.print(f"[bold red]Error:[/bold red] Plugin '{plugin_id}' not found.")
        raise click.Abort()

    console.print(f"[bold cyan]{p.name}[/bold cyan] ([bold yellow]{p.id}[/bold yellow])")
    console.print(f"  • Version:     {p.version}")
    console.print(f"  • Scope:       [green]{p.scope}[/green]")
    console.print(f"  • Author:      {p.author}")
    console.print(f"  • Entrypoint:  {p.entrypoint}")
    console.print(f"  • Location:    [dim]{p.path}[/dim]")
    if p.description:
        console.print(f"  • Description: {p.description}")


@plugin_group.command(name="import", help="Import a plugin from a ZIP archive or directory.")
@click.argument("archive", type=click.Path(exists=True, path_type=Path))
@click.option("--global", "is_global", is_flag=True, default=False, help="Install to global plugin directory (~/.config/dna-linux/plugins/).")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite if plugin ID is already installed.")
@click.pass_obj
def import_cmd(ctx_obj, archive: Path, is_global: bool, overwrite: bool) -> None:
    console: Console = ctx_obj["console"]

    if is_global:
        target_dir = get_global_plugins_dir()
        scope = "global"
    else:
        proj_plugins_dir = _get_project_plugins_dir(ctx_obj)
        if not proj_plugins_dir:
            console.print(
                "[bold red]Error:[/bold red] No active project selected. "
                "Use --global to install globally, or select a project with 'dna project select <name>'."
            )
            raise click.Abort()
        target_dir = proj_plugins_dir
        scope = "project"

    try:
        p = import_plugin(archive, target_dir, scope=scope, overwrite=overwrite)
        console.print(f"[bold green]✓ Successfully imported plugin:[/bold green] [cyan]{p.name}[/cyan] ({p.id} v{p.version})")
        console.print(f"Scope:    [green]{p.scope}[/green]")
        console.print(f"Location: [dim]{p.path}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Import Error:[/bold red] {e}")
        raise click.Abort()


@plugin_group.command(name="run", context_settings={"ignore_unknown_options": True}, help="Execute a plugin within the active project workspace.")
@click.argument("plugin_id", type=str)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_obj
def run_cmd(ctx_obj, plugin_id: str, args: tuple[str, ...]) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")

    try:
        project = get_current_project(proj_override)
    except Exception as e:
        console.print(f"[bold red]Project Error:[/bold red] {e}")
        console.print("Running plugins requires an active workspace. Use 'dna project select <name>' first.")
        raise click.Abort()

    try:
        plugin = get_plugin(plugin_id, project_plugins_dir=project.paths.plugins_dir)
    except KeyError:
        console.print(f"[bold red]Error:[/bold red] Plugin '{plugin_id}' not found.")
        raise click.Abort()

    console.print(f"Executing plugin: [bold cyan]{plugin.name}[/bold cyan] ([yellow]{plugin.id}[/yellow])...")
    console.print(f"Target workspace: [dim]{project.paths.project_dir}[/dim]")

    res = run_plugin(plugin, project.paths, args=list(args))

    if res.stdout:
        console.print(res.stdout, end="")
    if res.stderr:
        console.print(f"[red]{res.stderr}[/red]", end="")

    if res.returncode == 0:
        console.print(f"\n[bold green]✓ Plugin '{plugin.id}' completed successfully (exit code 0).[/bold green]")
    else:
        console.print(f"\n[bold red]✗ Plugin '{plugin.id}' exited with error code {res.returncode}.[/bold red]")
        raise click.Abort()


@plugin_group.command(name="delete", help="Delete an installed plugin.")
@click.argument("plugin_id", type=str)
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.pass_obj
def delete_cmd(ctx_obj, plugin_id: str, yes: bool) -> None:
    console: Console = ctx_obj["console"]
    proj_plugins_dir = _get_project_plugins_dir(ctx_obj)

    try:
        p = get_plugin(plugin_id, project_plugins_dir=proj_plugins_dir)
    except KeyError:
        console.print(f"[bold red]Error:[/bold red] Plugin '{plugin_id}' not found.")
        raise click.Abort()

    if not yes and not ctx_obj.get("yes", False):
        if not click.confirm(f"Are you sure you want to delete plugin '{p.id}' ({p.path})?"):
            console.print("[dim]Aborted.[/dim]")
            return

    delete_plugin(p)
    console.print(f"[bold green]✓ Deleted plugin:[/bold green] [cyan]{p.id}[/cyan]")
