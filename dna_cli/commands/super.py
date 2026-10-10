"""CLI command: dna super split|merge."""

from __future__ import annotations

from pathlib import Path
import click
from rich.console import Console

from dna_core.sparse import merge_sparse_chunks, split_sparse_image


@click.group(name="super", help="Split and merge dynamic super.img chunks.")
def super_group() -> None:
    pass


@super_group.command(name="split", help="Split super.img into evenly sized chunk files.")
@click.argument("super_img", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-p", "--parts", type=int, default=12, help="Number of parts to split into (4-25).")
@click.option("-o", "--out-dir", type=click.Path(file_okay=False, path_type=Path), default=None, help="Output directory for chunks.")
@click.option("--delete", is_flag=True, help="Delete source super.img upon successful split.")
@click.pass_obj
def split_cmd(ctx_obj, super_img: Path, parts: int, out_dir: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would split '{super_img.name}' into {parts} chunks")
        return

    dst_dir = out_dir or super_img.parent
    console.print(f"Splitting [bold cyan]{super_img.name}[/bold cyan] into {parts} parts...")
    try:
        chunks = split_sparse_image(super_img, out_dir=dst_dir, parts=parts)
        console.print(f"[bold green]✓ Successfully generated {len(chunks)} chunks in:[/bold green] [dim]{dst_dir}[/dim]")
        for c in chunks:
            console.print(f"  • {c.name} ([dim]{c.stat().st_size / (1024*1024):.1f} MB[/dim])")
        if delete:
            super_img.unlink()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()


@super_group.command(name="merge", help="Merge segmented super chunks into a single super.img.")
@click.argument("chunks", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("-o", "--out", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Output super.img path.")
@click.option("--delete", is_flag=True, help="Delete chunk files after successful merge.")
@click.pass_obj
def merge_cmd(ctx_obj, chunks: tuple[Path, ...], out: Path | None, delete: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would merge {len(chunks)} chunks into single super.img")
        return

    dst = out or chunks[0].parent / "super.img"
    console.print(f"Merging {len(chunks)} chunk files into [bold cyan]{dst.name}[/bold cyan]...")
    try:
        res = merge_sparse_chunks(list(chunks), dst)
        size_mb = res.stat().st_size / (1024 * 1024)
        console.print(f"[bold green]✓ Merged super image created:[/bold green] [dim]{res}[/dim] ({size_mb:.1f} MB)")
        if delete:
            for c in chunks:
                c.unlink()
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
