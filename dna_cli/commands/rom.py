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


@rom_group.command(name="debloat", help="Debloat MIUI or HyperOS applications safely using TOML presets.")
@click.option("--preset", default="global", help="Preset name ('global', 'china') or path to custom TOML.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate debloating without deleting files.")
@click.pass_obj
def debloat_cmd(ctx_obj, preset: str, target: Path | None, dry_run: bool) -> None:
    from dna_core.debloat import load_debloat_preset, run_debloat

    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    try:
        loaded_preset = load_debloat_preset(preset)
    except Exception as e:
        console.print(f"[bold red]Preset Error:[/bold red] {e}")
        raise click.Abort()

    if target:
        target_dir = target
    else:
        try:
            proj = get_current_project(proj_override)
            target_dir = proj.paths.unpacked_dir
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise click.Abort()

    console.print(f"Applying debloat preset: [bold cyan]{loaded_preset.title}[/bold cyan]...")
    console.print(f"Target directory:        [dim]{target_dir}[/dim]")

    res = run_debloat(target_dir, loaded_preset, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"\n[yellow][DRY-RUN][/yellow] Would remove {len(res.removed_directories)} directories ({res.freed_bytes / (1024*1024):.1f} MB):")
    else:
        console.print(f"\n[bold green]✓ Successfully removed {len(res.removed_directories)} directories[/bold green] (freed {res.freed_bytes / (1024*1024):.1f} MB):")

    for d in res.removed_directories:
        console.print(f"  • [dim]{d}[/dim]")

    if res.packages_affected:
        console.print(f"Debloated components: [cyan]{', '.join(res.packages_affected)}[/cyan]")


@rom_group.command(name="remove-oat", help="Delete all 'oat' directories to free space and reset ART optimization.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate deletion without removing directories.")
@click.pass_obj
def remove_oat_cmd(ctx_obj, target: Path | None, dry_run: bool) -> None:
    from dna_core.rom_tweaks import remove_oat_directories

    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if target:
        target_dir = target
    else:
        try:
            proj = get_current_project(proj_override)
            target_dir = proj.paths.unpacked_dir
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise click.Abort()

    console.print(f"Scanning for 'oat' directories in: [dim]{target_dir}[/dim]...")
    removed, freed = remove_oat_directories(target_dir, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would remove {len(removed)} 'oat' directories ({freed / (1024*1024):.1f} MB).")
    else:
        console.print(f"[bold green]✓ Removed {len(removed)} 'oat' directories[/bold green] (freed {freed / (1024*1024):.1f} MB).")

    for p in removed:
        console.print(f"  • [dim]{p}[/dim]")


@rom_group.command(name="make-rw", help="Enable full ROM read-write access (remove overlay mounts and unshare ext4 blocks).")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate without modifying fstab or deleting files.")
@click.pass_obj
def make_rw_cmd(ctx_obj, target: Path | None, dry_run: bool) -> None:
    from dna_core.rom_tweaks import make_rom_rw

    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if target:
        target_dir = target
    else:
        try:
            proj = get_current_project(proj_override)
            target_dir = proj.paths.unpacked_dir
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise click.Abort()

    console.print(f"Processing full ROM-RW modifications in: [dim]{target_dir}[/dim]...")
    res = make_rom_rw(target_dir, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would modify {len(res.fstab_files_modified)} fstab files (remove {res.overlay_lines_removed} overlay lines).")
    else:
        console.print(f"[bold green]✓ Modified {len(res.fstab_files_modified)} fstab files[/bold green] (removed {res.overlay_lines_removed} overlay lines):")

    for f in res.fstab_files_modified:
        console.print(f"  • [dim]{f}[/dim]")

    if res.init_scripts_removed:
        console.print(f"Removed overlay init scripts ({len(res.init_scripts_removed)}):")
        for i in res.init_scripts_removed:
            console.print(f"  • [dim]{i}[/dim]")

    if res.unshared_ext4_images:
        console.print(f"Unshared ext4 blocks in images ({len(res.unshared_ext4_images)}):")
        for img in res.unshared_ext4_images:
            console.print(f"  • [dim]{img}[/dim]")


@rom_group.command(name="decrypt", help="Disable ROM force-encryption in fstab to allow dirty flashing.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate without modifying fstab files.")
@click.pass_obj
def decrypt_cmd(ctx_obj, target: Path | None, dry_run: bool) -> None:
    from dna_core.rom_tweaks import decrypt_rom

    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if target:
        target_dir = target
    else:
        try:
            proj = get_current_project(proj_override)
            target_dir = proj.paths.unpacked_dir
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise click.Abort()

    console.print(f"Processing ROM decryption (fstab patch) in: [dim]{target_dir}[/dim]...")
    res = decrypt_rom(target_dir, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would update {len(res.fstab_files_modified)} fstab files ({res.lines_modified} encryption lines).")
    else:
        console.print(f"[bold green]✓ Updated {len(res.fstab_files_modified)} fstab files[/bold green] ({res.lines_modified} lines modified):")

    for f in res.fstab_files_modified:
        console.print(f"  • [dim]{f}[/dim]")
