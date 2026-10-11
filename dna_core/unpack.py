"""Unpacking dispatcher and routines for Android ROM formats."""

from __future__ import annotations

import json
import os
import shutil
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dna_core.detection import ImageType, detect_image_type
from dna_core.fs_metadata import (
    scan_directory_fs_metadata,
    write_file_contexts_file,
    write_fs_config_file,
)
from dna_core.project import Project, get_current_project
from dna_core.sdat import sdat2img
from dna_core.sparse import sparse_to_raw
from dna_core.tools import run_tool


def _create_temp_raw_file(src: Path, preferred_dir: Path | None = None) -> Path:
    """Create a temporary .raw file on the storage volume with ample disk space.
    Avoids small RAM-backed /tmp mounts by prioritizing the directory with the most free space."""
    candidates: list[Path] = []
    seen: set[Path] = set()
    for cand in (preferred_dir, src.parent):
        if cand is not None:
            try:
                p = Path(cand).resolve()
                if p.is_dir() and os.access(p, os.W_OK) and p not in seen:
                    candidates.append(p)
                    seen.add(p)
            except OSError:
                pass

    if candidates:
        try:
            candidates.sort(key=lambda d: shutil.disk_usage(d).free, reverse=True)
        except OSError:
            pass

    for cand_dir in candidates:
        try:
            with tempfile.NamedTemporaryFile(dir=cand_dir, prefix=".tmp_raw_", suffix=".raw", delete=False) as tf:
                return Path(tf.name)
        except OSError:
            pass
    with tempfile.NamedTemporaryFile(prefix=".tmp_raw_", suffix=".raw", delete=False) as tf:
        return Path(tf.name)


def unpack_image(
    image_path: Path | str,
    out_dir: Path | str | None = None,
    delete_source: bool = False,
    project: Project | None = None,
) -> Path:
    """Auto-detect filesystem (ext4, erofs, f2fs, sparse) and unpack into directory tree."""
    src = Path(image_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Image file '{src}' not found.")

    proj = project or (get_current_project() if not out_dir else None)
    part_name = src.stem

    if out_dir:
        destination = Path(out_dir).resolve()
    elif proj:
        destination = proj.paths.unpacked_dir / part_name
    else:
        destination = src.parent / f"{part_name}_unpacked"

    destination.mkdir(parents=True, exist_ok=True)
    img_type = detect_image_type(src)

    print(f"> Start unpacking partition: {src.name} <{img_type.value}>")
    print(f"> Source path: {src}")
    print(f"> Destination directory: {destination}")

    raw_temp: Path | None = None
    target_img = src

    try:
        # Step 1: If sparse image, unsparse it first
        if img_type == ImageType.SPARSE:
            raw_temp = _create_temp_raw_file(src, preferred_dir=destination)
            src_mb = src.stat().st_size / (1024 * 1024)
            print(f"> Image is Android sparse ({src_mb:.1f} MB). Unsparsing to temporary raw file...")
            sparse_to_raw(src, raw_temp)
            target_img = raw_temp
            img_type = detect_image_type(target_img)
            raw_mb = raw_temp.stat().st_size / (1024 * 1024)
            print(f"> Unsparse complete ({raw_mb:.1f} MB raw). Detected filesystem: <{img_type.value}>")

        # Step 2: Extract based on filesystem type
        if img_type == ImageType.EXT4:
            print(f"> Extracting EXT4 filesystem tree using debugfs...")
            run_tool("debugfs", ["-R", f"rdump / {destination}", str(target_img)], check=True)
            lost_found = destination / "lost+found"
            if lost_found.is_dir() and not any(lost_found.iterdir()):
                try:
                    lost_found.rmdir()
                except OSError:
                    pass
        elif img_type == ImageType.EROFS:
            print(f"> Extracting EROFS filesystem tree using fsck.erofs...")
            run_tool("fsck.erofs", [f"--extract={destination}", "--overwrite", str(target_img)], check=True)
        elif img_type == ImageType.F2FS:
            print(f"> Extracting F2FS filesystem tree using extract.f2fs...")
            run_tool("extract.f2fs", ["-i", str(target_img), "-o", str(destination)], check=True)
        elif img_type == ImageType.SUPER_LP:
            raise ValueError(
                f"'{src.name}' is a dynamic super partition. Use 'dna unpack super' instead."
            )
        else:
            raise ValueError(
                f"Unsupported or unrecognized filesystem format for '{src.name}' (detected: {img_type.value})."
            )

        # Count extracted items
        extracted_count = sum(1 for _ in destination.rglob("*"))
        print(f"> Extraction completed: {extracted_count} items extracted.")

        # Step 3: Preserve SELinux file_contexts and fs_config
        print(f"> Scanning and preserving SELinux file_contexts and fs_config metadata...")
        config_dir = proj.paths.config_dir if proj else destination.parent / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        fs_entries, fc_entries = scan_directory_fs_metadata(destination, mount_point=part_name)
        write_fs_config_file(fs_entries, config_dir / f"{part_name}_fs_config")
        write_file_contexts_file(fc_entries, config_dir / f"{part_name}_file_contexts")
        print(f"  • fs_config entries: {len(fs_entries)} -> {config_dir / f'{part_name}_fs_config'}")
        print(f"  • file_contexts entries: {len(fc_entries)} -> {config_dir / f'{part_name}_file_contexts'}")
        print(f"> Partition successfully unpacked into: {destination}")

    finally:
        if raw_temp and raw_temp.exists():
            print(f"> Cleaning up temporary raw image: {raw_temp.name}")
            try:
                raw_temp.unlink()
            except OSError:
                pass

    if delete_source:
        print(f"> Deleting source image: {src}")
        src.unlink()

    return destination


def unpack_super(
    super_path: Path | str,
    out_dir: Path | str | None = None,
    partitions: list[str] | None = None,
    auto_unpack_imgs: bool = False,
    delete_source: bool = False,
    project: Project | None = None,
) -> list[Path]:
    """Unpack partition images from super.img using lpunpack."""
    src = Path(super_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Super image '{src}' not found.")

    proj = project or (get_current_project() if not out_dir else None)
    if out_dir:
        destination = Path(out_dir).resolve()
    elif proj:
        destination = proj.paths.images_dir
    else:
        destination = src.parent / "super_unpacked"

    destination.mkdir(parents=True, exist_ok=True)

    print(f"> Start unpacking dynamic super.img: {src.name}")
    print(f"> Source path: {src}")
    print(f"> Output destination: {destination}")
    if partitions:
        print(f"> Target partitions ({len(partitions)}): {', '.join(partitions)}")
    else:
        print("> Target partitions: extracting all available partitions")

    raw_temp: Path | None = None
    target_img = src

    try:
        # Check if super.img is sparse
        img_type = detect_image_type(src)
        print(f"> Super image format: <{img_type.value}>")
        if img_type == ImageType.SPARSE:
            raw_temp = _create_temp_raw_file(src, preferred_dir=destination)
            src_mb = src.stat().st_size / (1024 * 1024)
            print(f"> Super image is Android sparse ({src_mb:.1f} MB). Unsparsing to raw format...")
            sparse_to_raw(src, raw_temp)
            target_img = raw_temp
            raw_mb = raw_temp.stat().st_size / (1024 * 1024)
            print(f"> Unsparse complete ({raw_mb:.1f} MB raw).")

        args: list[str] = []
        if partitions:
            for p in partitions:
                args.extend(["-p", p])
        args.append(str(target_img))
        args.append(str(destination))

        print(f"> Running lpunpack to extract partition images...")
        run_tool("lpunpack", args, check=True)

        extracted_imgs = [p for p in destination.glob("*.img") if p.is_file() and p.resolve() != src.resolve()]
        if partitions:
            req_set = set(partitions)
            extracted_imgs = [
                p for p in extracted_imgs
                if p.stem in req_set
                or p.stem.removesuffix("_a") in req_set
                or p.stem.removesuffix("_b") in req_set
                or f"{p.stem}_a" in req_set
                or f"{p.stem}_b" in req_set
            ]

        print(f"> Successfully extracted {len(extracted_imgs)} partition image(s):")
        for img in extracted_imgs:
            sz_mb = img.stat().st_size / (1024 * 1024)
            print(f"  • {img.name} ({sz_mb:.1f} MB)")

        if auto_unpack_imgs:
            print(f"> Automatically unpacking {len(extracted_imgs)} extracted partition image(s)...")
            for idx, img in enumerate(extracted_imgs, start=1):
                print(f"> [{idx}/{len(extracted_imgs)}] Processing {img.name}...")
                unpack_image(img, project=proj)

        if delete_source:
            print(f"> Removing source super image: {src.name}")
            src.unlink()

        print(f"> Super image unpack completed successfully.")
        return extracted_imgs

    finally:
        if raw_temp and raw_temp.exists():
            print(f"> Cleaning up temporary raw image: {raw_temp.name}")
            try:
                raw_temp.unlink()
            except OSError:
                pass


@dataclass
class SuperPartitionInfo:
    """Represents a dynamic partition stored inside super.img."""

    name: str              # Actual partition identifier for lpunpack (e.g. "system_a" or "system")
    display_name: str      # Clean label (e.g. "system")
    size_bytes: int        # Partition size in bytes
    formatted_size: str    # Human-readable size string (e.g. "340.0K", "2.2G", "870.8M")

    @property
    def label(self) -> str:
        return f"{self.display_name}({self.formatted_size})"


def format_partition_size(size_bytes: int) -> str:
    """Format partition size into K, M, G string matching Android DNA tool: e.g. 340.0K, 870.8M, 2.2G."""
    if size_bytes >= 1024 * 1024 * 1024:
        val = size_bytes / (1024 * 1024 * 1024)
        return f"{val:.1f}G"
    elif size_bytes >= 1024 * 1024:
        val = size_bytes / (1024 * 1024)
        return f"{val:.1f}M"
    elif size_bytes >= 1024:
        val = size_bytes / 1024
        return f"{val:.1f}K"
    else:
        return f"{size_bytes}B"


def get_super_partitions_info(super_path: Path | str) -> list[SuperPartitionInfo]:
    """Inspect dynamic partition metadata inside super.img (sparse or raw) using lpdump."""
    super_p = Path(super_path).resolve()
    if not super_p.is_file():
        return []

    try:
        with open(super_p, "rb") as f:
            magic = f.read(4)
    except OSError:
        return []

    raw_path = str(super_p)
    temp_raw: Path | None = None

    if magic == b"\x3a\xff\x26\xed":  # 0xed26ff3a: Android Sparse Image
        # Extract small prefix (first 8MB) to read partition table geometry without full unsparse
        temp_raw = _create_temp_raw_file(super_p)
        try:
            with open(super_p, "rb") as f, open(temp_raw, "wb") as out:
                hdr = f.read(28)
                if len(hdr) >= 28:
                    magic_u, maj, min_, f_sz, c_sz, blk_sz, tot_blk, tot_chk, crc = struct.unpack("<I4H4I", hdr)
                    written = 0
                    for _ in range(tot_chk):
                        if written >= 8 * 1024 * 1024:
                            break
                        ch_data = f.read(c_sz)
                        if len(ch_data) < c_sz:
                            break
                        c_type, _, c_sz_blks, total_sz = struct.unpack("<2H2I", ch_data)
                        data_sz = total_sz - c_sz
                        out_sz = c_sz_blks * blk_sz
                        if c_type == 0xCAC1:  # RAW
                            d = f.read(data_sz)
                            out.write(d)
                            written += len(d)
                        elif c_type == 0xCAC2:  # FILL
                            fill = f.read(4)
                            if data_sz > 4:
                                f.seek(data_sz - 4, 1)
                            pattern = fill * (blk_sz // 4)
                            for _ in range(c_sz_blks):
                                out.write(pattern)
                                written += len(pattern)
                                if written >= 8 * 1024 * 1024:
                                    break
                        elif c_type == 0xCAC3:  # DONT_CARE
                            out.write(b"\x00" * out_sz)
                            written += out_sz
                        elif c_type == 0xCAC4:  # CRC32
                            f.read(4)
            raw_path = str(temp_raw)
        except Exception:
            if temp_raw and temp_raw.exists():
                try:
                    temp_raw.unlink()
                except OSError:
                    pass
            return []

    try:
        res = run_tool("lpdump", ["--json", raw_path], check=False, capture_output=True, log_cmd=False, stream=False)
        if res.returncode != 0 or not res.stdout:
            return []

        data = json.loads(res.stdout)
        raw_parts = data.get("partitions", [])

        # Filter partitions that have a positive size (active dynamic partitions)
        active_parts: list[tuple[str, int]] = []
        for p in raw_parts:
            name = p.get("name", "")
            size_str = p.get("size", "0")
            try:
                size_bytes = int(size_str)
            except (ValueError, TypeError):
                size_bytes = 0
            if name and size_bytes > 0:
                active_parts.append((name, size_bytes))

        if not active_parts:
            return []

        # Determine display name: if all active partitions end with '_a' and no active '_b' partitions exist, strip '_a'
        names = [n for n, _ in active_parts]
        has_a = any(n.endswith("_a") for n in names)
        has_b = any(n.endswith("_b") for n in names)
        strip_slot_a = has_a and not has_b

        result: list[SuperPartitionInfo] = []
        for name, size_bytes in active_parts:
            if strip_slot_a and name.endswith("_a"):
                disp = name[:-2]
            else:
                disp = name
            result.append(
                SuperPartitionInfo(
                    name=name,
                    display_name=disp,
                    size_bytes=size_bytes,
                    formatted_size=format_partition_size(size_bytes),
                )
            )

        return result
    except Exception:
        return []
    finally:
        if temp_raw and temp_raw.exists():
            try:
                temp_raw.unlink()
            except OSError:
                pass


def unpack_brotli(
    br_path: Path | str,
    out_file: Path | str | None = None,
    delete_source: bool = False,
) -> Path:
    """Decompress a brotli (.br) file."""
    src = Path(br_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Brotli file '{src}' not found.")

    dst = Path(out_file).resolve() if out_file else src.with_suffix("")
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"> Decompressing Brotli archive: {src.name} -> {dst.name}")
    run_tool("brotli", ["-d", "-f", str(src), "-o", str(dst)], check=True)
    if dst.is_file():
        sz_mb = dst.stat().st_size / (1024 * 1024)
        print(f"> Brotli decompression completed: {dst.name} ({sz_mb:.1f} MB)")
    if delete_source:
        print(f"> Removing source archive: {src.name}")
        src.unlink()
    return dst


def unpack_zstd(
    zstd_path: Path | str,
    out_file: Path | str | None = None,
    delete_source: bool = False,
) -> Path:
    """Decompress a Zstandard (.zst / .zstd) file."""
    src = Path(zstd_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Zstd file '{src}' not found.")

    dst = Path(out_file).resolve() if out_file else src.with_suffix("")
    dst.parent.mkdir(parents=True, exist_ok=True)

    print(f"> Decompressing Zstandard archive: {src.name} -> {dst.name}")
    run_tool("zstd", ["-d", "-k", "-f", str(src), "-o", str(dst)], check=True)
    if dst.is_file():
        sz_mb = dst.stat().st_size / (1024 * 1024)
        print(f"> Zstandard decompression completed: {dst.name} ({sz_mb:.1f} MB)")
    if delete_source:
        print(f"> Removing source archive: {src.name}")
        src.unlink()
    return dst


def unpack_dat(
    dat_path: Path | str,
    transfer_list: Path | str | None = None,
    out_file: Path | str | None = None,
    delete_source: bool = False,
) -> Path:
    """Unpack Android .new.dat + .transfer.list into raw partition image."""
    src_dat = Path(dat_path).resolve()
    if not src_dat.is_file():
        raise FileNotFoundError(f"DAT file '{src_dat}' not found.")

    if transfer_list:
        trans_file = Path(transfer_list).resolve()
    else:
        name_root = src_dat.name
        if name_root.endswith(".new.dat"):
            name_root = name_root[:-8]
        elif name_root.endswith(".dat"):
            name_root = name_root[:-4]
        trans_file = src_dat.parent / f"{name_root}.transfer.list"

    if not trans_file.is_file():
        raise FileNotFoundError(
            f"Corresponding transfer list '{trans_file}' not found for '{src_dat.name}'."
        )

    dst_img = Path(out_file).resolve() if out_file else src_dat.parent / f"{trans_file.stem.replace('.transfer', '')}.img"
    print(f"> Converting Android sparse DAT: {src_dat.name} -> {dst_img.name}")
    print(f"> Using transfer list: {trans_file.name}")
    sdat2img(trans_file, src_dat, dst_img)
    if dst_img.is_file():
        sz_mb = dst_img.stat().st_size / (1024 * 1024)
        print(f"> Conversion completed: {dst_img.name} ({sz_mb:.1f} MB)")

    if delete_source:
        print(f"> Removing source files: {src_dat.name}, {trans_file.name}")
        src_dat.unlink()
        if trans_file.exists():
            trans_file.unlink()

    return dst_img


def unpack_bin(
    payload_path: Path | str,
    out_dir: Path | str | None = None,
    partitions: list[str] | None = None,
    auto_unpack_imgs: bool = False,
    delete_source: bool = False,
    project: Project | None = None,
) -> list[Path]:
    """Extract partitions from an OTA payload.bin."""
    src = Path(payload_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Payload file '{src}' not found.")

    proj = project or (get_current_project() if not out_dir else None)
    if out_dir:
        destination = Path(out_dir).resolve()
    elif proj:
        destination = proj.paths.images_dir
    else:
        destination = src.parent / "payload_extracted"

    destination.mkdir(parents=True, exist_ok=True)

    print(f"> Extracting OTA payload partitions from: {src.name}")
    print(f"> Destination directory: {destination}")
    if partitions:
        print(f"> Filter partitions: {', '.join(partitions)}")

    args = ["-o", str(destination)]
    if partitions:
        args.extend(["-p", ",".join(partitions)])
    args.append(str(src))

    print(f"> Running payload-dumper-go...")
    run_tool("payload-dumper-go", args, check=True)
    extracted = [p for p in destination.glob("*.img") if p.is_file()]
    print(f"> Extracted {len(extracted)} partition image(s):")
    for img in extracted:
        sz_mb = img.stat().st_size / (1024 * 1024)
        print(f"  • {img.name} ({sz_mb:.1f} MB)")

    if auto_unpack_imgs:
        print(f"> Automatically unpacking {len(extracted)} extracted partition image(s)...")
        for idx, img in enumerate(extracted, start=1):
            print(f"> [{idx}/{len(extracted)}] Unpacking {img.name}...")
            unpack_image(img, project=proj)

    if delete_source:
        print(f"> Removing source payload: {src.name}")
        src.unlink()

    print(f"> Payload extraction completed successfully.")
    return extracted
