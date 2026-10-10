"""CLI commands: dna unpack bin|br|dat|img|zstd|super."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console

from dna_core.project import get_current_project
from dna_core.unpack import (
    unpack_bin,
    unpack_brotli,
    unpack_dat,
    unpack_image,
    unpack_super,
    unpack_zstd,
)


@click.group(name="unpack", help="Unpack partition images, archives, and super partitions.")
def unpack_group() -> None:
    pass


@unpack_group.command(name="img", help="Unpack ext4, erofs, f2fs, or sparse filesystem image.")
@click.argument("image_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output directory.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate extraction without writing to disk.")
@click.option("--delete", is_flag=True, help="Delete source image upon successful extraction.")
@click.pass_obj
def unpack_img_cmd(ctx_obj, image_file: Path, out: Path | None, dry_run: bool, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would unpack filesystem image '[bold]{image_file.name}[/bold]'")
        return

    try:
        project = get_current_project(proj_override)
    except Exception:
        project = None

    console.print(f"Unpacking image: [bold cyan]{image_file.name}[/bold cyan]...")
    try:
        dest = unpack_image(image_file, out_dir=out, delete_source=delete, project=project)
        console.print(f"[bold green]✓ Successfully extracted to:[/bold green] [dim]{dest}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@unpack_group.command(name="super", help="Unpack partition images from dynamic super.img.")
@click.argument("super_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output directory.")
@click.option("-p", "--partition", "partitions", multiple=True, help="Specific partition(s) to extract.")
@click.option("--auto", is_flag=True, help="Automatically unpack extracted partition images.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate extraction without writing to disk.")
@click.option("--delete", is_flag=True, help="Delete source super.img upon successful extraction.")
@click.pass_obj
def unpack_super_cmd(
    ctx_obj,
    super_file: Path,
    out: Path | None,
    partitions: tuple[str, ...],
    auto: bool,
    dry_run: bool,
    delete: bool,
) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would unpack super image '[bold]{super_file.name}[/bold]'")
        return

    try:
        project = get_current_project(proj_override)
    except Exception:
        project = None

    console.print(f"Unpacking super partition: [bold cyan]{super_file.name}[/bold cyan]...")
    try:
        extracted = unpack_super(
            super_file,
            out_dir=out,
            partitions=list(partitions) if partitions else None,
            auto_unpack_imgs=auto,
            delete_source=delete,
            project=project,
        )
        console.print(f"[bold green]✓ Extracted {len(extracted)} partition images:[/bold green]")
        for img in extracted:
            console.print(f"  • {img.name} ([dim]{img.stat().st_size / (1024*1024):.1f} MB[/dim])")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@unpack_group.command(name="bin", help="Unpack partition images from OTA payload.bin.")
@click.argument("payload_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output directory.")
@click.option("-p", "--partition", "partitions", multiple=True, help="Specific partition(s) to extract.")
@click.option("--auto", is_flag=True, help="Automatically unpack extracted partition images.")
@click.option("--delete", is_flag=True, help="Delete source payload.bin upon successful extraction.")
@click.pass_obj
def unpack_bin_cmd(
    ctx_obj,
    payload_file: Path,
    out: Path | None,
    partitions: tuple[str, ...],
    auto: bool,
    delete: bool,
) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would unpack OTA payload '[bold]{payload_file.name}[/bold]'")
        return

    try:
        project = get_current_project(proj_override)
    except Exception:
        project = None

    console.print(f"Unpacking OTA payload: [bold cyan]{payload_file.name}[/bold cyan]...")
    try:
        extracted = unpack_bin(
            payload_file,
            out_dir=out,
            partitions=list(partitions) if partitions else None,
            auto_unpack_imgs=auto,
            delete_source=delete,
            project=project,
        )
        console.print(f"[bold green]✓ Extracted {len(extracted)} partition images.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@unpack_group.command(name="br", help="Decompress brotli (.br) file.")
@click.argument("br_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output file path.")
@click.option("--delete", is_flag=True, help="Delete source file.")
@click.pass_obj
def unpack_br_cmd(ctx_obj, br_file: Path, out: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would decompress brotli file '[bold]{br_file.name}[/bold]'")
        return

    try:
        res = unpack_brotli(br_file, out_file=out, delete_source=delete)
        console.print(f"[bold green]✓ Decompressed to:[/bold green] [dim]{res}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@unpack_group.command(name="zstd", help="Decompress Zstandard (.zst) file.")
@click.argument("zstd_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output file path.")
@click.option("--delete", is_flag=True, help="Delete source file.")
@click.pass_obj
def unpack_zstd_cmd(ctx_obj, zstd_file: Path, out: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would decompress zstd file '[bold]{zstd_file.name}[/bold]'")
        return

    try:
        res = unpack_zstd(zstd_file, out_file=out, delete_source=delete)
        console.print(f"[bold green]✓ Decompressed to:[/bold green] [dim]{res}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@unpack_group.command(name="dat", help="Convert .new.dat + .transfer.list to raw partition image.")
@click.argument("dat_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-t", "--transfer-list", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Explicit transfer.list path.")
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output image file path.")
@click.option("--delete", is_flag=True, help="Delete source dat and transfer list files.")
@click.pass_obj
def unpack_dat_cmd(ctx_obj, dat_file: Path, transfer_list: Path | None, out: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would convert DAT '[bold]{dat_file.name}[/bold]' to raw image")
        return

    try:
        res = unpack_dat(dat_file, transfer_list=transfer_list, out_file=out, delete_source=delete)
        console.print(f"[bold green]✓ Converted to partition image:[/bold green] [dim]{res}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
