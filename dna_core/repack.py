"""Repacking routines for Android partitions, super.img, and archives."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from dna_core.fs_metadata import (
    scan_directory_fs_metadata,
    sync_file_contexts_file,
    sync_fs_config_file,
    write_file_contexts_file,
    write_fs_config_file,
)
from dna_core.project import Project, get_current_project
from dna_core.sdat import img2sdat
from dna_core.sparse import raw_to_sparse
from dna_core.tools import run_tool


def calculate_directory_size_bytes(directory: Path | str) -> int:
    """Calculate the total size of all regular files in a directory tree."""
    total = 0
    for root, _, files in os.walk(directory):
        for f in files:
            fp = Path(root) / f
            try:
                if not fp.is_symlink():
                    total += fp.stat().st_size
            except OSError:
                pass
    return total


def repack_image(
    src_dir: Path | str,
    out_img: Path | str | None = None,
    fs_type: str = "ext4",
    output_format: str = "raw",  # raw, sparse, dat, br
    label: str | None = None,
    fs_config: Path | str | None = None,
    file_contexts: Path | str | None = None,
    size_bytes: int | None = None,
    compress_erofs: str = "lz4hc",
    erofs_level: int = 8,
    brotli_level: int = 3,
    project: Project | None = None,
) -> Path:
    """Repack an unpacked directory tree into an Android filesystem partition image."""
    src = Path(src_dir).resolve()
    if not src.is_dir():
        raise NotADirectoryError(f"Source directory '{src}' does not exist.")

    part_name = label or src.name.replace("_unpacked", "")
    proj = project
    if not proj:
        try:
            proj = get_current_project()
        except Exception:
            proj = None

    if out_img:
        destination = Path(out_img).resolve()
    elif proj:
        p_paths = getattr(proj, "paths", proj)
        destination = p_paths.out_dir / f"{part_name}.img"
    else:
        destination = src.parent / f"{part_name}.img"

    destination.parent.mkdir(parents=True, exist_ok=True)

    print(f"> Start repacking partition image: {part_name}")
    print(f"> Source directory: {src}")
    print(f"> Destination image: {destination}")
    print(f"> Target filesystem: <{fs_type}>, Output format: <{output_format}>")

    # Locate or generate fs_config and file_contexts
    config_dir_candidates: list[Path] = []
    if proj:
        p_paths = getattr(proj, "paths", proj)
        cfg_dir = getattr(p_paths, "config_dir", None)
        if callable(cfg_dir):
            cfg_dir = cfg_dir()
        if cfg_dir and isinstance(cfg_dir, Path):
            config_dir_candidates.append(cfg_dir)
        elif hasattr(p_paths, "config"):
            config_dir_candidates.append(p_paths.config)
    config_dir_candidates.append(src.parent / "config")
    if src.parent.name == "unpacked":
        config_dir_candidates.append(src.parent.parent / "config")
    config_dir_candidates.append(destination.parent / "config")

    fc_file: Path | None = Path(file_contexts).resolve() if file_contexts else None
    fs_file: Path | None = Path(fs_config).resolve() if fs_config else None

    if not fc_file or not fc_file.is_file():
        for cd in config_dir_candidates:
            cand = cd / f"{part_name}_file_contexts"
            if cand.is_file():
                fc_file = cand
                break

    if not fs_file or not fs_file.is_file():
        for cd in config_dir_candidates:
            cand = cd / f"{part_name}_fs_config"
            if cand.is_file():
                fs_file = cand
                break

    target_config_dir = config_dir_candidates[0]
    target_config_dir.mkdir(parents=True, exist_ok=True)
    if not fc_file:
        fc_file = target_config_dir / f"{part_name}_file_contexts"
    if not fs_file:
        fs_file = target_config_dir / f"{part_name}_fs_config"

    if not fs_file.is_file() or not fc_file.is_file():
        print(f"> Scanning directory to generate fs_config and file_contexts...")
        fs_entries, fc_entries = scan_directory_fs_metadata(src, mount_point=part_name)
        if not fs_file.is_file():
            write_fs_config_file(fs_entries, fs_file)
            print(f"  • fs_config entries: {len(fs_entries)} -> {fs_file}")
        if not fc_file.is_file():
            write_file_contexts_file(fc_entries, fc_file)
            print(f"  • file_contexts entries: {len(fc_entries)} -> {fc_file}")
    else:
        print(f"> Using existing SELinux metadata:")
        print(f"  • fs_config: {fs_file}")
        print(f"  • file_contexts: {fc_file}")

    # Synchronize and sanitize fs_config and file_contexts for ext4/erofs
    sync_fs_config_file(src, mount_point=part_name, fs_file=fs_file)
    sync_file_contexts_file(mount_point=part_name, fc_file=fc_file)

    if fs_type == "ext4":
        # Calculate size: sum of directory sizes + 25% safety overhead + 16MB minimum
        content_size = calculate_directory_size_bytes(src)
        if size_bytes:
            total_bytes = size_bytes
        else:
            total_bytes = max(int(content_size * 1.25) + (16 * 1024 * 1024), 32 * 1024 * 1024)

        blocks = (total_bytes + 4095) // 4096
        content_mb = content_size / (1024 * 1024)
        total_mb = total_bytes / (1024 * 1024)
        print(f"> Content size: {content_mb:.1f} MB, Allocated partition size: {total_mb:.1f} MB ({blocks} blocks)")

        # Step 1: mke2fs
        print(f"> Creating EXT4 partition filesystem with mke2fs...")
        mke2fs_args = [
            "-O",
            "^has_journal,^metadata_csum,extent,huge_file,^flex_bg,^64bit,uninit_bg,dir_nlink,extra_isize",
            "-t",
            "ext4",
            "-b",
            "4096",
            "-L",
            part_name,
            "-I",
            "256",
            "-M",
            f"/{part_name}",
            "-m",
            "0",
            "-F",
            str(destination),
            str(blocks),
        ]
        run_tool("mke2fs", mke2fs_args, check=True)

        # Step 2: e2fsdroid
        print(f"> Populating filesystem and applying SELinux permissions with e2fsdroid...")
        e2fsdroid_args = [
            "-e",
            "-T",
            "1230768000",
            "-C",
            str(fs_file),
            "-S",
            str(fc_file),
            "-f",
            str(src),
            "-a",
            f"/{part_name}",
            str(destination),
        ]
        run_tool("e2fsdroid", e2fsdroid_args, check=True)

    elif fs_type == "erofs":
        print(f"> Creating EROFS filesystem with mkfs.erofs (algorithm: {compress_erofs}, level: {erofs_level})...")
        erofs_args = [
            "-T",
            "1230768000",
            f"-z{compress_erofs},{erofs_level}",
            f"--mount-point=/{part_name}",
            str(destination),
            str(src),
        ]
        run_tool("mkfs.erofs", erofs_args, check=True)

    else:
        raise ValueError(f"Unsupported filesystem type '{fs_type}'. Supported: ext4, erofs")

    # Format conversions if requested
    if output_format == "sparse":
        print(f"> Converting raw partition image to Android sparse format...")
        sparse_out = destination.with_suffix(".simg")
        raw_to_sparse(destination, sparse_out)
        shutil.move(str(sparse_out), str(destination))
        s_mb = destination.stat().st_size / (1024 * 1024)
        print(f"> Sparse conversion completed: {destination.name} ({s_mb:.1f} MB)")
    elif output_format in ("dat", "br"):
        print(f"> Converting partition image to Android sparse DAT...")
        out_dir = destination.parent
        trans_file, dat_file = img2sdat(destination, out_dir, partition_name=part_name)
        print(f"> Generated sparse DAT: {dat_file.name}, {trans_file.name}")
        if output_format == "br":
            print(f"> Compressing sparse DAT with Brotli (level: {brotli_level})...")
            br_out = dat_file.with_suffix(".dat.br")
            run_tool("brotli", [f"-q", str(brotli_level), "-f", str(dat_file), "-o", str(br_out)], check=True)
            dat_file.unlink()
            br_mb = br_out.stat().st_size / (1024 * 1024)
            print(f"> Brotli compression completed: {br_out.name} ({br_mb:.1f} MB)")

    final_mb = destination.stat().st_size / (1024 * 1024)
    print(f"> Repack partition completed successfully: {destination.name} ({final_mb:.1f} MB)")
    return destination


def repack_super(
    partition_images: list[Path | str],
    out_super: Path | str | None = None,
    device_size: int = 8589934592,  # 8.0 GB / 8.5 GB default
    group_name: str = "qti_dynamic_partitions",
    slot_type: str = "vab",  # a_only, ab, vab
    sparse: bool = False,
    project: Project | None = None,
) -> Path:
    """Repack partition images into dynamic super.img using lpmake."""
    proj = project or (get_current_project() if not out_super else None)
    if out_super:
        dst = Path(out_super).resolve()
    elif proj:
        dst = proj.paths.out_dir / "super.img"
    else:
        dst = Path("out/super.img").resolve()

    dst.parent.mkdir(parents=True, exist_ok=True)

    slot_count = 3 if slot_type in ("vab", "virtual_ab") else (2 if slot_type in ("ab",) else 1)
    group_a = f"{group_name}_a" if slot_count > 1 else group_name

    lpmake_args = [
        "--metadata-size=65536",
        "--super-name=super",
        f"--metadata-slots={slot_count}",
        f"--device=super:{device_size}",
        f"--group={group_a}:{device_size}",
    ]

    if slot_type in ("vab", "virtual_ab"):
        lpmake_args.append("--virtual-ab")

    if sparse:
        lpmake_args.append("--sparse")

    print(f"> Start repacking dynamic super.img: {dst.name}")
    print(f"> Destination: {dst}")
    print(f"> Slot configuration: <{slot_type.upper()}> (slots: {slot_count}), Group: {group_a}")
    print(f"> Device size: {device_size / (1024 * 1024 * 1024):.2f} GB ({device_size} bytes)")
    print(f"> Input partition images ({len(partition_images)}):")

    # Add each partition image
    for img_ref in partition_images:
        img_p = Path(img_ref).resolve()
        if not img_p.is_file():
            raise FileNotFoundError(f"Partition image '{img_p}' not found.")

        raw_name = img_p.stem
        # Slot suffix handling
        part_name = f"{raw_name}_a" if (slot_count > 1 and not raw_name.endswith(("_a", "_b"))) else raw_name
        size = img_p.stat().st_size
        print(f"  • {part_name}: {size / (1024 * 1024):.1f} MB ({img_p.name})")

        lpmake_args.append(f"--partition={part_name}:readonly:{size}:{group_a}")
        lpmake_args.append(f"--image={part_name}={img_p}")

    lpmake_args.extend(["--output", str(dst)])
    print(f"> Running lpmake to build super image...")
    run_tool("lpmake", lpmake_args, check=True)
    if dst.is_file():
        dst_mb = dst.stat().st_size / (1024 * 1024)
        print(f"> Super image repacked successfully: {dst.name} ({dst_mb:.1f} MB)")
    return dst


def repack_zstd(
    in_file: Path | str,
    out_file: Path | str | None = None,
    level: int = 3,
    delete_source: bool = False,
) -> Path:
    """Compress a file using zstd."""
    src = Path(in_file).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file '{src}' not found.")

    dst = Path(out_file).resolve() if out_file else src.with_suffix(src.suffix + ".zst")
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"> Compressing file with Zstandard (level {level}): {src.name} -> {dst.name}")
    run_tool("zstd", [f"-{level}", "-T0", "-f", str(src), "-o", str(dst)], check=True)
    if dst.is_file():
        sz_mb = dst.stat().st_size / (1024 * 1024)
        print(f"> Zstandard compression completed: {dst.name} ({sz_mb:.1f} MB)")
    if delete_source:
        print(f"> Removing source file: {src.name}")
        src.unlink()
    return dst
