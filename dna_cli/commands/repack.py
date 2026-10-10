"""CLI commands: dna repack img|zstd|super."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console

from dna_core.project import get_current_project
from dna_core.repack import repack_image, repack_super, repack_zstd


@click.group(name="repack", help="Repack filesystem partitions, dynamic super.img, and archives.")
def repack_group() -> None:
    pass


@repack_group.command(name="img", help="Repack an unpacked partition directory into ext4 or erofs image.")
@click.argument("src_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--fs", "fs_type", type=click.Choice(["ext4", "erofs"], case_sensitive=False), default="ext4", help="Filesystem type.")
@click.option("--format", "out_format", type=click.Choice(["raw", "sparse", "dat", "br"], case_sensitive=False), default="raw", help="Output format.")
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output image file path.")
@click.option("--label", default=None, help="Partition mount label.")
@click.option("--size", type=int, default=None, help="Explicit partition size in bytes.")
@click.option("--erofs-mode", default="lz4hc", help="EROFS compression algorithm.")
@click.option("--erofs-level", type=int, default=8, help="EROFS compression level (0-9).")
@click.option("--br-level", type=int, default=3, help="Brotli compression level (1-7).")
@click.pass_obj
def repack_img_cmd(
    ctx_obj,
    src_dir: Path,
    fs_type: str,
    out_format: str,
    out: Path | None,
    label: str | None,
    size: int | None,
    erofs_mode: str,
    erofs_level: int,
    br_level: int,
) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would repack '{src_dir.name}' to {fs_type} ({out_format})")
        return

    try:
        project = get_current_project(proj_override)
    except Exception:
        project = None

    console.print(f"Repacking partition: [bold cyan]{src_dir.name}[/bold cyan] -> {fs_type.upper()} ({out_format})...")
    try:
        dest = repack_image(
            src_dir=src_dir,
            out_img=out,
            fs_type=fs_type.lower(),
            output_format=out_format.lower(),
            label=label,
            size_bytes=size,
            compress_erofs=erofs_mode,
            erofs_level=erofs_level,
            brotli_level=br_level,
            project=project,
        )
        console.print(f"[bold green]✓ Successfully repacked image:[/bold green] [dim]{dest}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@repack_group.command(name="super", help="Repack multiple partition images into dynamic super.img.")
@click.argument("images", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output super.img path.")
@click.option("--size", "size_gb", type=float, default=8.5, help="Total super partition device size in GB.")
@click.option("--group", default="qti_dynamic_partitions", help="Dynamic partition group name.")
@click.option("--type", "slot_type", type=click.Choice(["vab", "ab", "a_only"], case_sensitive=False), default="vab", help="Partition slot layout.")
@click.option("--sparse", is_flag=True, help="Build sparse fastboot-flashable super.img.")
@click.pass_obj
def repack_super_cmd(
    ctx_obj,
    images: tuple[Path, ...],
    out: Path | None,
    size_gb: float,
    group: str,
    slot_type: str,
    sparse: bool,
) -> None:
    console: Console = ctx_obj["console"]
    proj_override = ctx_obj.get("project")
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would repack {len(images)} partitions into super.img ({size_gb} GB)")
        return

    try:
        project = get_current_project(proj_override)
    except Exception:
        project = None

    device_size = int(size_gb * 1024 * 1024 * 1024)
    console.print(f"Repacking super.img ({size_gb:.2f} GB, {slot_type.upper()}, {len(images)} partitions)...")
    try:
        dest = repack_super(
            partition_images=list(images),
            out_super=out,
            device_size=device_size,
            group_name=group,
            slot_type=slot_type.lower(),
            sparse=sparse,
            project=project,
        )
        console.print(f"[bold green]✓ Successfully repacked super image:[/bold green] [dim]{dest}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@repack_group.command(name="zstd", help="Compress a file using Zstandard.")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output compressed path.")
@click.option("-l", "--level", type=int, default=3, help="Zstandard compression level (0-19).")
@click.option("--delete", is_flag=True, help="Delete source file after compression.")
@click.pass_obj
def repack_zstd_cmd(ctx_obj, input_file: Path, out: Path | None, level: int, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would compress '{input_file.name}' with zstd level {level}")
        return

    try:
        res = repack_zstd(input_file, out_file=out, level=level, delete_source=delete)
        console.print(f"[bold green]✓ Compressed with zstd:[/bold green] [dim]{res}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
