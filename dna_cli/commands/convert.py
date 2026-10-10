"""CLI command: dna convert img-simg|img-dat-br."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console

from dna_core.detection import detect_image_type, ImageType
from dna_core.sdat import img2sdat, sdat2img
from dna_core.sparse import is_sparse_image, raw_to_sparse, sparse_to_raw
from dna_core.tools import run_tool


@click.group(name="convert", help="Convert between Android image and archive formats.")
def convert_group() -> None:
    pass


@convert_group.command(name="img-simg", help="Convert raw image to sparse (simg) or sparse to raw.")
@click.argument("image_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output image file path.")
@click.option("--delete", is_flag=True, help="Delete source image.")
@click.pass_obj
def convert_simg_cmd(ctx_obj, image_file: Path, out: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    is_sparse = is_sparse_image(image_file)
    target_action = "sparse -> raw" if is_sparse else "raw -> sparse"

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would convert '{image_file.name}' ({target_action})")
        return

    console.print(f"Converting [bold cyan]{image_file.name}[/bold cyan] ({target_action})...")
    try:
        if is_sparse:
            dst = out or image_file.with_name(f"{image_file.stem}_raw.img")
            res = sparse_to_raw(image_file, dst)
        else:
            dst = out or image_file.with_name(f"{image_file.stem}_sparse.img")
            res = raw_to_sparse(image_file, dst)

        console.print(f"[bold green]✓ Conversion complete:[/bold green] [dim]{res}[/dim]")
        if delete:
            image_file.unlink()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@convert_group.command(name="img-dat-br", help="Convert raw partition image to/from .new.dat and .br formats.")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--to", "target_format", type=click.Choice(["dat", "br", "img"], case_sensitive=False), default="dat", help="Target format.")
@click.option("--br-level", type=int, default=3, help="Brotli compression level (1-7).")
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output file path.")
@click.option("--delete", is_flag=True, help="Delete source file.")
@click.pass_obj
def convert_dat_br_cmd(
    ctx_obj,
    input_file: Path,
    target_format: str,
    br_level: int,
    out: Path | None,
    delete: bool,
) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would convert '{input_file.name}' to {target_format.upper()}")
        return

    console.print(f"Converting [bold cyan]{input_file.name}[/bold cyan] -> {target_format.upper()}...")
    try:
        if target_format == "dat":
            trans, dat = img2sdat(input_file, out.parent if out else input_file.parent, partition_name=input_file.stem)
            console.print(f"[bold green]✓ Generated DAT files:[/bold green]\n  • [dim]{trans}[/dim]\n  • [dim]{dat}[/dim]")
            if delete:
                input_file.unlink()
        elif target_format == "br":
            trans, dat = img2sdat(input_file, out.parent if out else input_file.parent, partition_name=input_file.stem)
            br_file = dat.with_suffix(".dat.br")
            run_tool("brotli", [f"-q", str(br_level), "-f", str(dat), "-o", str(br_file)], check=True)
            dat.unlink()
            console.print(f"[bold green]✓ Generated Brotli DAT files:[/bold green]\n  • [dim]{trans}[/dim]\n  • [dim]{br_file}[/dim]")
            if delete:
                input_file.unlink()
        elif target_format == "img":
            # If brotli .br file passed, decompress to dat first
            src = input_file
            if src.suffix == ".br":
                decomp_dat = src.with_suffix("")
                run_tool("brotli", ["-d", "-f", str(src), "-o", str(decomp_dat)], check=True)
                src = decomp_dat

            name_root = src.name.replace(".new.dat", "").replace(".dat", "")
            trans_file = src.parent / f"{name_root}.transfer.list"
            out_img = out or src.parent / f"{name_root}.img"
            res = sdat2img(trans_file, src, out_img)
            console.print(f"[bold green]✓ Converted to raw image:[/bold green] [dim]{res}[/dim]")
            if delete:
                input_file.unlink()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
