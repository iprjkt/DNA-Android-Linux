"""CLI commands: dna project create | select | delete | list."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from dna_core.project import (
    create_project,
    delete_project,
    list_projects,
    select_project,
)


@click.group(name="project", help="Manage DNA-Linux project workspaces.")
def project_group() -> None:
    pass


@project_group.command(name="create", help="Create a new project workspace.")
@click.argument("name")
@click.option("--desc", default="", help="Optional project description.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate execution without creating directory.")
@click.pass_obj
def create_cmd(ctx_obj, name: str, desc: str, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would create project '[bold]{name}[/bold]'")
        return

    try:
        project = create_project(name=name, description=desc)
        console.print(f"[bold green]✓ Successfully created project:[/bold green] [bold cyan]{project.name}[/bold cyan]")
        console.print(f"  IO Directory:   [dim]{project.paths.io_dir}[/dim]")
        console.print(f"  Work Directory: [dim]{project.paths.work_dir}[/dim]")
        console.print(f"  Active project set to: [bold]{project.name}[/bold]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@project_group.command(name="select", help="Select active project workspace.")
@click.argument("name")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate execution without changing active state.")
@click.pass_obj
def select_cmd(ctx_obj, name: str, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would select project '[bold]{name}[/bold]'")
        return

    try:
        project = select_project(name)
        console.print(f"[bold green]✓ Active project selected:[/bold green] [bold cyan]{project.name}[/bold cyan]")
        console.print(f"  IO Directory:   [dim]{project.paths.io_dir}[/dim]")
        console.print(f"  Work Directory: [dim]{project.paths.work_dir}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@project_group.command(name="delete", help="Delete a project workspace.")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate execution without deleting.")
@click.pass_obj
def delete_cmd(ctx_obj, name: str, yes: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    auto_yes = yes or ctx_obj.get("yes", False)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would delete project '[bold]{name}[/bold]'")
        return

    if not auto_yes:
        confirmed = click.confirm(
            f"Are you sure you want to permanently delete project '{name}' and all its files?",
            default=False,
        )
        if not confirmed:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    try:
        removed_dir = delete_project(name)
        console.print(f"[bold green]✓ Deleted project directory:[/bold green] [dim]{removed_dir}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@project_group.command(name="list", help="List all project workspaces.")
@click.pass_obj
def list_cmd(ctx_obj) -> None:
    console: Console = ctx_obj["console"]
    projects = list_projects()

    if not projects:
        console.print("[yellow]No DNA projects found. Create one using 'dna project create <name>'[/yellow]")
        return

    table = Table(title="DNA-Linux Projects", show_header=True, header_style="bold magenta")
    table.add_column("Active", width=8, justify="center")
    table.add_column("Project Name", style="bold cyan")
    table.add_column("Created At", style="dim")
    table.add_column("Directory", style="dim")

    for proj, is_active in projects:
        active_badge = "[bold green]★ ACTIVE[/bold green]" if is_active else ""
        created_at = proj.metadata.get("created_at", "-")
        table.add_row(active_badge, proj.name, created_at[:19], str(proj.directory))

    console.print(table)
