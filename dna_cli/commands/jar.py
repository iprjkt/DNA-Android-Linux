"""CLI commands for framework services.jar patching (dna jar ...)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import click
from rich.console import Console

from dna_core.jar import find_services_jar, patch_services_jar
from dna_core.project import get_current_project


@click.group(name="jar", help="Android framework services.jar smali patching commands.")
def jar_group() -> None:
    pass


def _resolve_jar(jar_arg: Optional[Path], ctx_obj) -> Path:
    """Resolve services.jar from explicit argument or active project workspace."""
    console: Console = ctx_obj["console"]

    if jar_arg is not None:
        found = find_services_jar(jar_arg)
        if found:
            return found
        console.print(f"[bold red]Error:[/bold red] Could not find a valid services.jar at: {jar_arg}")
        raise click.Abort()

    # Search in active project unpacked directory
    try:
        proj = get_current_project(ctx_obj.get("project"))
        found = find_services_jar(proj.paths.unpacked_dir)
        if found:
            return found
        console.print(
            f"[bold red]Error:[/bold red] services.jar not found under active project unpacked directory ({proj.paths.unpacked_dir})."
        )
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]Target Error:[/bold red] {e}")
        console.print("Please specify path to services.jar or activate a project.")
        raise click.Abort()


@jar_group.command(name="core-patch-dsv", help="Bypass complete APK signature verification (Core Patch DSV).")
@click.argument("jar", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--out", type=click.Path(path_type=Path), default=None, help="Output JAR file path (default: in-place).")
@click.option("--disable-invoke-custom", is_flag=True, default=False, help="Remove invoke-custom from smali methods.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate decompilation and patching without writing.")
@click.pass_obj
def core_patch_dsv_cmd(ctx_obj, jar: Optional[Path], out: Optional[Path], disable_invoke_custom: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_jar = _resolve_jar(jar, ctx_obj)

    console.print(f"Applying [bold cyan]Core Patch DSV[/bold cyan] to [dim]{target_jar}[/dim]...")
    if is_dry_run:
        console.print("[yellow][DRY-RUN][/yellow] Decompiling and simulating smali modifications...")

    try:
        res = patch_services_jar(
            target_jar,
            output_jar=out,
            patch_dsv=True,
            disable_invoke_custom=disable_invoke_custom,
            dry_run=is_dry_run,
        )
    except Exception as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        raise click.Abort()

    dsv_result = next((p for p in res["patches_applied"] if p["patch"] == "core-patch-dsv"), {})
    methods_count = dsv_result.get("methods_patched", 0)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would patch {methods_count} signature verification methods.")
    else:
        console.print(f"[bold green]✓ Successfully patched {methods_count} signature verification methods![/bold green]")
        console.print(f"Output: [cyan]{res['output_jar']}[/cyan]")


@jar_group.command(name="remove-apk-protection", help="Remove OEM package installer restrictions & downgrade blocks.")
@click.argument("jar", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--out", type=click.Path(path_type=Path), default=None, help="Output JAR file path (default: in-place).")
@click.option("--disable-invoke-custom", is_flag=True, default=False, help="Remove invoke-custom from smali methods.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate decompilation and patching without writing.")
@click.pass_obj
def remove_apk_protection_cmd(ctx_obj, jar: Optional[Path], out: Optional[Path], disable_invoke_custom: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_jar = _resolve_jar(jar, ctx_obj)

    console.print(f"Applying [bold cyan]Remove APK Protection[/bold cyan] to [dim]{target_jar}[/dim]...")
    if is_dry_run:
        console.print("[yellow][DRY-RUN][/yellow] Decompiling and simulating smali modifications...")

    try:
        res = patch_services_jar(
            target_jar,
            output_jar=out,
            patch_apk_protection=True,
            disable_invoke_custom=disable_invoke_custom,
            dry_run=is_dry_run,
        )
    except Exception as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        raise click.Abort()

    prot_result = next((p for p in res["patches_applied"] if p["patch"] == "remove-apk-protection"), {})
    methods_count = prot_result.get("methods_patched", 0)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would patch {methods_count} package installer check methods.")
    else:
        console.print(f"[bold green]✓ Successfully bypassed {methods_count} package protection methods![/bold green]")
        console.print(f"Output: [cyan]{res['output_jar']}[/cyan]")


@jar_group.command(name="disable-secure-screenshot", help="Disable FLAG_SECURE screenshot blocking with Android 17 safeguards.")
@click.argument("jar", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--out", type=click.Path(path_type=Path), default=None, help="Output JAR file path (default: in-place).")
@click.option("--disable-invoke-custom", is_flag=True, default=False, help="Remove invoke-custom from smali methods.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate decompilation and patching without writing.")
@click.pass_obj
def disable_secure_screenshot_cmd(ctx_obj, jar: Optional[Path], out: Optional[Path], disable_invoke_custom: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_jar = _resolve_jar(jar, ctx_obj)

    console.print(f"Applying [bold cyan]Disable Secure Screenshot (DSS)[/bold cyan] to [dim]{target_jar}[/dim]...")
    console.print("[dim]Using safe CompletableFuture handler to prevent Android 17 VerifyError bootloops.[/dim]")

    if is_dry_run:
        console.print("[yellow][DRY-RUN][/yellow] Decompiling and simulating smali modifications...")

    try:
        res = patch_services_jar(
            target_jar,
            output_jar=out,
            patch_dss=True,
            disable_invoke_custom=disable_invoke_custom,
            dry_run=is_dry_run,
        )
    except Exception as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        raise click.Abort()

    dss_result = next((p for p in res["patches_applied"] if p["patch"] == "disable-secure-screenshot"), {})
    methods_count = dss_result.get("methods_patched", 0)

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would patch {methods_count} window / policy security methods.")
    else:
        console.print(f"[bold green]✓ Successfully disabled secure screenshot enforcement ({methods_count} methods patched)![/bold green]")
        console.print(f"Output: [cyan]{res['output_jar']}[/cyan]")


@jar_group.command(name="patch-all", help="Apply DSV, APK Protection, and Disable Secure Screenshot in a single pass.")
@click.argument("jar", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--out", type=click.Path(path_type=Path), default=None, help="Output JAR file path (default: in-place).")
@click.option("--disable-invoke-custom", is_flag=True, default=False, help="Remove invoke-custom from smali methods.")
@click.option("-n", "--dry-run", is_flag=True, default=False, help="Simulate decompilation and patching without writing.")
@click.pass_obj
def patch_all_cmd(ctx_obj, jar: Optional[Path], out: Optional[Path], disable_invoke_custom: bool, dry_run: bool) -> None:
    console: Console = ctx_obj["console"]
    is_dry_run = dry_run or ctx_obj.get("dry_run", False)
    target_jar = _resolve_jar(jar, ctx_obj)

    console.print(f"Applying [bold cyan]All Jar Patches (DSV + Protection + DSS)[/bold cyan] to [dim]{target_jar}[/dim]...")

    if is_dry_run:
        console.print("[yellow][DRY-RUN][/yellow] Decompiling and simulating smali modifications...")

    try:
        res = patch_services_jar(
            target_jar,
            output_jar=out,
            patch_dsv=True,
            patch_apk_protection=True,
            patch_dss=True,
            disable_invoke_custom=disable_invoke_custom,
            dry_run=is_dry_run,
        )
    except Exception as e:
        console.print(f"[bold red]Patch Error:[/bold red] {e}")
        raise click.Abort()

    total_patched = sum(p.get("methods_patched", 0) for p in res["patches_applied"])

    if is_dry_run:
        console.print(f"[yellow][DRY-RUN][/yellow] Would patch {total_patched} methods across all patches.")
    else:
        console.print(f"[bold green]✓ Successfully applied all patches ({total_patched} methods patched)![/bold green]")
        console.print(f"Output: [cyan]{res['output_jar']}[/cyan]")
