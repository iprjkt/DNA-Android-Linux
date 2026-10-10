"""CLI command: dna resize <partition> --size <bytes|MiB>."""

from __future__ import annotations

import re
from pathlib import Path
import click
from rich.console import Console

from dna_core.resize import resize_partition


def parse_size_str(val: str) -> int:
    """Parse size strings like '200M', '1G', '1048576' into bytes."""
    v = val.strip().upper()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$", v)
    if not match:
        raise ValueError(f"Invalid size string: '{val}'. Examples: '200M', '1G', '1048576'.")
    num = float(match.group(1))
    unit = match.group(2)

    multipliers = {
        "": 1,
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024 * 1024,
        "MB": 1024 * 1024,
        "G": 1024 * 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
    }
    return int(num * multipliers.get(unit, 1))


@click.command(name="resize", help="Resize an ext4 partition image.")
@click.argument("partition_img", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--size", default=None, help="New target size or extra space (e.g. '200M', '+500M', '2G').")
@click.option("--extra-mb", type=int, default=0, help="Extra space in MB to append.")
@click.option("-M", "--minimize", is_flag=True, help="Shrink filesystem to minimum possible size.")
@click.pass_obj
def resize_cmd(ctx_obj, partition_img: Path, size: str | None, extra_mb: int, minimize: bool) -> None:
    console: Console = ctx_obj["console"]
    dry_run = ctx_obj.get("dry_run", False)

    if dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would resize image '{partition_img.name}'")
        return

    target_bytes = None
    extra = extra_mb

    if size:
        s = size.strip()
        if s.startswith("+"):
            extra = parse_size_str(s[1:]) // (1024 * 1024)
        else:
            target_bytes = parse_size_str(s)

    console.print(f"Resizing partition: [bold cyan]{partition_img.name}[/bold cyan]...")
    try:
        res = resize_partition(
            image_path=partition_img,
            extra_mb=extra,
            target_size_bytes=target_bytes,
            minimize=minimize,
        )
        new_size_mb = res.stat().st_size / (1024 * 1024)
        console.print(f"[bold green]✓ Successfully resized:[/bold green] [dim]{res}[/dim] ({new_size_mb:.1f} MB)")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
