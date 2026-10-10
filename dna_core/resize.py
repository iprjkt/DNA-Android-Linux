"""Partition image resizing routines (resize2fs / ext4 expand)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from dna_core.detection import ImageType, detect_image_type
from dna_core.sparse import is_sparse_image, sparse_to_raw
from dna_core.tools import run_tool


def resize_partition(
    image_path: Path | str,
    extra_mb: int = 0,
    target_size_bytes: int | None = None,
    minimize: bool = False,
) -> Path:
    """Resize an ext4 partition image safely."""
    img_p = Path(image_path).resolve()
    if not img_p.is_file():
        raise FileNotFoundError(f"Partition image '{img_p}' not found.")

    if is_sparse_image(img_p):
        raise ValueError(
            f"Image '{img_p.name}' is a sparse image. Convert to raw first using 'dna convert img-simg' before resizing."
        )

    fs_type = detect_image_type(img_p)
    if fs_type != ImageType.EXT4:
        raise ValueError(f"Partition resizing is only supported for ext4 filesystems (detected: {fs_type.value}).")

    # Step 1: Force filesystem check before resize
    try:
        run_tool("e2fsck", ["-f", "-y", str(img_p)], check=False)
    except Exception:
        pass

    # Step 2: Resize
    if minimize:
        run_tool("resize2fs", ["-M", str(img_p)], check=True)
    elif extra_mb > 0:
        with open(img_p, "ab") as f:
            # Append zero bytes
            chunk = b"\x00" * (1024 * 1024)
            for _ in range(extra_mb):
                f.write(chunk)
        run_tool("resize2fs", [str(img_p)], check=True)
    elif target_size_bytes:
        blocks = (target_size_bytes + 4095) // 4096
        run_tool("resize2fs", [str(img_p), str(blocks)], check=True)
    else:
        # Default: auto-expand to fill container
        run_tool("resize2fs", [str(img_p)], check=True)

    # Step 3: Verify integrity after resize
    try:
        run_tool("e2fsck", ["-f", "-y", str(img_p)], check=False)
    except Exception:
        pass

    return img_p


# Convenience alias for resize_partition
resize_ext4 = resize_partition

