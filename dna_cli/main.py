"""Main CLI entrypoint for DNA-Linux."""

from __future__ import annotations

import sys
from pathlib import Path
import click
from rich.console import Console

from dna_cli import __version__
from dna_cli.commands.convert import convert_group
from dna_cli.commands.doctor import doctor_cmd
from dna_cli.commands.jar import jar_group
from dna_cli.commands.patch import patch_group
from dna_cli.commands.plugin import plugin_group
from dna_cli.commands.project import project_group
from dna_cli.commands.repack import repack_group
from dna_cli.commands.resize import resize_cmd
from dna_cli.commands.rom import rom_group, unzip_cmd
from dna_cli.commands.super import super_group
from dna_cli.commands.tui import tui_cmd
from dna_cli.commands.unpack import unpack_group
from dna_core.logger import setup_logger


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version", prog_name="dna")
@click.option(
    "--project",
    "-p",
    type=str,
    default=None,
    help="Target project name or explicit workspace directory path.",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    default=False,
    help="Simulate execution without modifying the filesystem.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable detailed debug output and logging.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Automatically confirm prompts for destructive operations.",
)
@click.option(
    "--log-file",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write detailed operation logs to an explicit file.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    project: str | None,
    dry_run: bool,
    verbose: bool,
    yes: bool,
    log_file: Path | None,
) -> None:
    """DNA-Linux: Native Linux (x86_64) Android ROM unpack, repack, and patch toolkit."""
    console = Console()
    logger = setup_logger(verbose=verbose, log_file=log_file)

    ctx.obj = {
        "console": console,
        "logger": logger,
        "project": project,
        "dry_run": dry_run,
        "verbose": verbose,
        "yes": yes,
        "log_file": log_file,
    }

    if ctx.invoked_subcommand is None:
        if sys.stdin.isatty():
            from dna_tui.app import start_tui
            start_tui()
        else:
            click.echo(ctx.get_help())


# Register command groups and commands
cli.add_command(tui_cmd)
cli.add_command(doctor_cmd)
cli.add_command(project_group)
cli.add_command(rom_group)
cli.add_command(patch_group)
cli.add_command(jar_group)
cli.add_command(plugin_group)
cli.add_command(unpack_group)
cli.add_command(repack_group)
cli.add_command(resize_cmd)
cli.add_command(convert_group)
cli.add_command(super_group)

# Convenience top-level alias: dna unzip-rom
@cli.command(name="unzip-rom", help="Alias for 'dna rom unzip'.")
@click.argument("rom_zip", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--delete", is_flag=True, help="Delete source ZIP archive after successful extraction.")
@click.pass_context
def unzip_rom_alias(ctx: click.Context, rom_zip: Path, delete: bool) -> None:
    ctx.invoke(unzip_cmd, rom_zip=rom_zip, delete=delete)


if __name__ == "__main__":
    cli()
