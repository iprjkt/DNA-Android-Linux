"""ROM extraction and archive handling routines for DNA-Linux."""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dna_core.project import Project


@dataclass
class RomExtractResult:
    """Outcome of a ROM unzip operation."""

    zip_file: Path
    destination: Path
    total_files: int
    total_uncompressed_bytes: int
    deleted_source: bool
    dry_run: bool


def unzip_rom(
    zip_path: Path | str,
    project: Project,
    delete_source: bool = False,
    dry_run: bool = False,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> RomExtractResult:
    """Extract a flashable/fastboot ROM ZIP into the project's rom/ directory safely."""
    source_zip = Path(zip_path).expanduser().resolve()
    if not source_zip.is_file():
        raise FileNotFoundError(f"ROM archive '{source_zip}' does not exist.")

    if not zipfile.is_zipfile(source_zip):
        raise ValueError(f"File '{source_zip}' is not a valid ZIP archive.")

    target_dir = project.paths.rom_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip, "r") as zf:
        infolist = zf.infolist()
        total_files = len(infolist)
        total_bytes = sum(info.file_size for info in infolist)

        # Pre-check for zip slip / path traversal vulnerabilities
        target_dir_resolved = target_dir.resolve()
        for info in infolist:
            target_path = (target_dir / info.filename).resolve()
            if not (target_dir_resolved == target_path or target_dir_resolved in target_path.parents):
                raise PermissionError(
                    f"Security Error: Archive member '{info.filename}' traverses outside destination '{target_dir}'."
                )

        if dry_run:
            return RomExtractResult(
                zip_file=source_zip,
                destination=target_dir,
                total_files=total_files,
                total_uncompressed_bytes=total_bytes,
                deleted_source=False,
                dry_run=True,
            )

        extracted_bytes = 0
        for info in infolist:
            zf.extract(info, path=target_dir)
            extracted_bytes += info.file_size
            if progress_callback:
                progress_callback(info.filename, extracted_bytes, total_bytes)

    # Update project metadata
    project.metadata["source_rom"] = source_zip.name
    project.metadata["rom_extracted"] = True
    project.metadata["rom_file_count"] = total_files
    project.save_metadata()

    deleted = False
    if delete_source:
        source_zip.unlink()
        deleted = True

    return RomExtractResult(
        zip_file=source_zip,
        destination=target_dir,
        total_files=total_files,
        total_uncompressed_bytes=total_bytes,
        deleted_source=deleted,
        dry_run=False,
    )
