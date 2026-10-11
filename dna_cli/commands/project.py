"""CLI commands: dna project create | select | delete | list."""

from __future__ import annotations

from pathlib import Path
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
@click.option("--io-root", type=click.Path(path_type=Path), default=None, help="Custom input/output directory root (e.g. /mnt/detalmick).")
@click.option("--work-root", type=click.Path(path_type=Path), default=None, help="Custom working directory root (e.g. /mnt/detalmick/work).")
@click.option("--root", type=click.Path(path_type=Path), default=None, help="Custom root directory for both IO and work directories.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate execution without creating directory.")
@click.pass_obj
def create_cmd(
    ctx_obj,
    name: str,
    desc: str,
    io_root: Path | None,
    work_root: Path | None,
    root: Path | None,
    dry_run: bool,
) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    eff_io = io_root or root
    eff_work = work_root or root

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would create project '[bold]{name}[/bold]'")
        if eff_io:
            console.print(f"  Target IO: [dim]{eff_io}[/dim]")
        if eff_work:
            console.print(f"  Target Work: [dim]{eff_work}[/dim]")
        return

    try:
        project = create_project(
            name=name,
            description=desc,
            io_root=eff_io,
            work_root=eff_work,
        )
        console.print(f"[bold green]✓ Successfully created project:[/bold green] [bold cyan]{project.name}[/bold cyan]")
        console.print(f"  IO Directory:   [dim]{project.paths.io_dir}[/dim]")
        console.print(f"  Work Directory: [dim]{project.paths.work_dir}[/dim]")
        console.print(f"  Active project set to: [bold]{project.name}[/bold]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@project_group.command(name="roots", help="View or update default workspace root directories.")
@click.option("--set-io", type=click.Path(path_type=Path), default=None, help="Set default input/output directory.")
@click.option("--set-work", type=click.Path(path_type=Path), default=None, help="Set default working directory.")
@click.option("--reset", is_flag=True, default=False, help="Reset directories to system defaults.")
@click.pass_obj
def roots_cmd(ctx_obj, set_io: Path | None, set_work: Path | None, reset: bool) -> None:
    console: Console = ctx_obj["console"]
    from dna_core.config import get_workspace_roots, reset_workspace_roots, set_workspace_roots

    if reset:
        cfg = reset_workspace_roots()
        console.print("[bold green]✓ Reset workspace roots to system defaults.[/bold green]")
    elif set_io is not None or set_work is not None:
        cfg = set_workspace_roots(io_root=set_io, work_root=set_work)
        console.print("[bold green]✓ Updated workspace roots:[/bold green]")
    else:
        io_r, work_r = get_workspace_roots()
        console.print("[bold cyan]Current Workspace Roots:[/bold cyan]")
        console.print(f"  IO Root:   [dim]{io_r}[/dim]")
        console.print(f"  Work Root: [dim]{work_r}[/dim]")
        return

    console.print(f"  IO Root:   [dim]{cfg.io_root}[/dim]")
    console.print(f"  Work Root: [dim]{cfg.work_root}[/dim]")


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
