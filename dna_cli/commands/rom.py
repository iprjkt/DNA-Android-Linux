"""CLI command: dna rom unzip <rom.zip>."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from dna_core.project import get_current_project
from dna_core.rom import unzip_rom


@click.group(name="rom", help="ROM archive and image operations.")
def rom_group() -> None:
    pass


@rom_group.command(name="unzip", help="Unzip a ROM archive into the active project workspace.")
@click.argument("rom_zip", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--delete", is_flag=True, help="Delete source ZIP archive after successful extraction.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate extraction without writing to disk.")
@click.pass_obj
def unzip_cmd(ctx_obj, rom_zip: Path, delete: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    project_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    try:
        project = get_current_project(project_override)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()

    console.print(f"Target Project: [bold cyan]{project.name}[/bold cyan] ([dim]{project.directory}[/dim])")
    console.print(f"Source ROM:     [bold yellow]{rom_zip.name}[/bold yellow] ([dim]{rom_zip.stat().st_size / (1024*1024):.1f} MB[/dim])")

    if dry_run:
        res = unzip_rom(rom_zip, project, delete_source=delete, dry_run=True)
        console.print(f"[yellow][DRY-RUN][/yellow] Would extract {res.total_files} files ({res.total_uncompressed_bytes / (1024*1024):.1f} MB) to {res.destination}")
        if delete:
            console.print(f"[yellow][DRY-RUN][/yellow] Would delete source archive: {rom_zip}")
        return

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting ROM...", total=None)

        def on_progress(filename: str, current_bytes: int, total_bytes: int):
            progress.update(task, total=total_bytes, completed=current_bytes, description=f"Extracting [cyan]{filename[:30]}[/cyan]")

        res = unzip_rom(
            zip_path=rom_zip,
            project=project,
            delete_source=delete,
            dry_run=False,
            progress_callback=on_progress,
        )

    console.print(
        f"[bold green]✓ Successfully extracted {res.total_files} files[/bold green] "
        f"({res.total_uncompressed_bytes / (1024*1024):.1f} MB) to [dim]{res.destination}[/dim]"
    )
    if res.deleted_source:
        console.print(f"[bold yellow]✓ Deleted source archive:[/bold yellow] [dim]{rom_zip}[/dim]")
