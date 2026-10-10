"""CLI commands for ROM and image patching (dna patch ...)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import click
from rich.console import Console

from dna_core.project import get_current_project
from dna_core.patch import (
    DEFAULT_FINGERPRINT,
    DEFAULT_MODEL,
    patch_disable_ota,
    patch_disable_xiaomi_services,
    patch_integrity_fix,
    patch_privapp_permissions,
    patch_safetycore,
    patch_vbmeta,
)


@click.group(name="patch", help="ROM and image patching commands.")
def patch_group() -> None:
    pass


def _resolve_target(target: Optional[Path], ctx_obj) -> Path:
    """Resolve target directory from option or active project unpacked directory."""
    console: Console = ctx_obj["console"]
    if target:
        return target
    try:
        proj = get_current_project(ctx_obj.get("project"))
        return proj.paths.unpacked_dir
    except Exception as e:
        console.print(f"[bold red]Target Error:[/bold red] {e}")
        console.print("Please specify --target or activate a project using 'dna project select <name>'.")
        raise click.Abort()


@patch_group.command(name="vbmeta", help="Patch AVB flags in vbmeta.img (disable verity/verification).")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--mode",
    type=click.Choice(["verity", "verification", "both", "enable"], case_sensitive=False),
    default="both",
    help="Flags to patch: 'verity' (bit 0), 'verification' (bit 1), 'both' (bits 0 & 1), or 'enable' (restore).",
)
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate patching without modifying image file.")
@click.pass_obj
def vbmeta_cmd(ctx_obj, image: Path, mode: str, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)

    console.print(f"Target VBMeta Image: [bold cyan]{image}[/bold cyan]")
    console.print(f"Requested Mode:      [bold yellow]{mode}[/bold yellow]")

    try:
        res = patch_vbmeta(image, mode=mode, dry_run=is_dry_run)
    except Exception as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        raise click.Abort()

    old_flags = res["old_flags"]
    new_flags = res["new_flags"]

    if is_dry_run:
        console.print(
            f"[yellow][DRY-RUN][/yellow] Would update flags: {old_flags} (0x{old_flags:02x}) -> {new_flags} (0x{new_flags:02x})"
        )
    else:
        if res["modified"]:
            console.print(
                f"[bold green]✓ Successfully patched vbmeta flags:[/bold green] {old_flags} (0x{old_flags:02x}) -> {new_flags} (0x{new_flags:02x})"
            )
        else:
            console.print(
                f"[dim]No changes needed. Flags already set to {new_flags} (0x{new_flags:02x}).[/dim]"
            )


@patch_group.command(name="integrity-fix", help="Spoof Google Pixel 7 Pro fingerprint to pass Play Integrity.")
@click.option("--fingerprint", default=None, help=f"Custom build fingerprint (default: {DEFAULT_FINGERPRINT}).")
@click.option("--model", default=None, help=f"Custom model string (default: {DEFAULT_MODEL}).")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate changes without writing files.")
@click.pass_obj
def integrity_fix_cmd(ctx_obj, fingerprint: Optional[str], model: Optional[str], target: Optional[Path], dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_dir = _resolve_target(target, ctx_obj)

    console.print(f"Applying Play Integrity spoofing...")
    console.print(f"Target directory: [dim]{target_dir}[/dim]")

    res = patch_integrity_fix(target_dir, fingerprint=fingerprint, model=model, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would modify {len(res['modified_files'])} property files:")
    else:
        console.print(f"[bold green]✓ Successfully updated {len(res['modified_files'])} property files:[/bold green]")

    for f in res["modified_files"]:
        console.print(f"  • [cyan]{f}[/cyan]")
    console.print(f"Spoofed fingerprint: [bold]{res['fingerprint']}[/bold]")
    console.print(f"Spoofed model:       [bold]{res['model']}[/bold]")


@patch_group.command(name="safetycore", help="Install SafetyCore placeholder APK to product/app tree.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("--apk", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Path to custom placeholder APK.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate installation without copying.")
@click.pass_obj
def safetycore_cmd(ctx_obj, target: Optional[Path], apk: Optional[Path], dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_dir = _resolve_target(target, ctx_obj)

    try:
        res = patch_safetycore(target_dir, placeholder_apk=apk, dry_run=is_dry_run)
    except Exception as e:
        console.print(f"[bold red]SafetyCore Error:[/bold red] {e}")
        raise click.Abort()

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would copy {res['source']} -> {res['destination']}")
    else:
        console.print(f"[bold green]✓ Installed SafetyCore placeholder:[/bold green] {res['destination']}")


@patch_group.command(name="privapp-permissions", help="Remove ro.control_privapp_permissions from build.prop.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate removal without modifying files.")
@click.pass_obj
def privapp_permissions_cmd(ctx_obj, target: Optional[Path], dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_dir = _resolve_target(target, ctx_obj)

    res = patch_privapp_permissions(target_dir, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would remove '{res['property_removed']}' from {len(res['modified_files'])} files:")
    else:
        console.print(f"[bold green]✓ Removed '{res['property_removed']}' from {len(res['modified_files'])} files:[/bold green]")

    for f in res["modified_files"]:
        console.print(f"  • [cyan]{f}[/cyan]")


@patch_group.command(name="disable-ota", help="Disable automatic OTA update validation in device feature XMLs.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate without modifying XML files.")
@click.pass_obj
def disable_ota_cmd(ctx_obj, target: Optional[Path], dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_dir = _resolve_target(target, ctx_obj)

    res = patch_disable_ota(target_dir, dry_run=is_dry_run)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would disable OTA validation in {res['count']} XML files:")
    else:
        console.print(f"[bold green]✓ Disabled OTA validation in {res['count']} XML files:[/bold green]")

    for f in res["modified_files"]:
        console.print(f"  • [cyan]{f}[/cyan]")


@patch_group.command(name="disable-xiaomi-services", help="Remove Xiaomi telemetry, tracking, and bloat services.")
@click.option("--target", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None, help="Target directory (default: active project unpacked/ directory).")
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Custom TOML services configuration.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate without deleting files.")
@click.pass_obj
def disable_xiaomi_services_cmd(ctx_obj, target: Optional[Path], config: Optional[Path], dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_dir = _resolve_target(target, ctx_obj)

    try:
        res = patch_disable_xiaomi_services(target_dir, config_path=config, dry_run=is_dry_run)
    except Exception as e:
        console.print(f"[bold red]Xiaomi Services Error:[/bold red] {e}")
        raise click.Abort()

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would remove {res['total_removed']} service directories ({res['total_freed_bytes'] / (1024*1024):.1f} MB):")
    else:
        console.print(f"[bold green]✓ Successfully removed {res['total_removed']} service directories[/bold green] (freed {res['total_freed_bytes'] / (1024*1024):.1f} MB):")

    for entry in res["removed_entries"]:
        console.print(f"  • [bold]{entry['package']}[/bold]: [dim]{entry['path']}[/dim]")
