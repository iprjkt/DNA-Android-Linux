"""Image and filesystem type detection for DNA-Linux."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path


class ImageType(str, enum.Enum):
    SPARSE = "sparse"
    EXT4 = "ext4"
    EROFS = "erofs"
    F2FS = "f2fs"
    SUPER_LP = "super_lp"
    PAYLOAD_BIN = "payload_bin"
    BROTLI = "brotli"
    ZSTD = "zstd"
    DAT = "dat"
    UNKNOWN = "unknown"


# Magic byte constants
SPARSE_MAGIC = b"\x3a\xff\x26\xed"  # 0xed26ff3a
EXT4_MAGIC = b"\x53\xef"            # 0xef53 at offset 1080 (0x438)
EROFS_MAGIC = b"\xe2\xe1\xf5\xe0"    # 0xe0f5e1e2 at offset 1024 (0x400)
F2FS_MAGIC = b"\x10\x20\xf5\xf2"     # 0xf2f52010 at offset 1024 (0x400)
LP_GEOMETRY_MAGIC = b"gDla"          # 0x616c4467 at offset 4096 (0x1000)
LP_GEOMETRY_MAGIC_ALT = b"LDla"      # 0x616c444c at offset 4096 or 0
PAYLOAD_MAGIC = b"CrAU"              # Android OTA payload magic at offset 0
ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"     # 0xFD2FB528


@dataclass
class ImageInfo:
    """Detailed metadata about a detected image file."""

    path: Path
    image_type: ImageType
    size_bytes: int
    is_sparse: bool
    fs_type: str | None = None
    description: str = ""


def detect_image_type(file_path: Path | str) -> ImageType:
    """Examine header magic bytes to accurately detect the image/archive type."""
    p = Path(file_path)
    if not p.is_file():
        return ImageType.UNKNOWN

    size = p.stat().st_size
    if size < 4:
        return ImageType.UNKNOWN

    # Check extension hints first for archive containers
    suffix_lower = p.suffix.lower()
    if suffix_lower == ".br":
        return ImageType.BROTLI
    if suffix_lower in (".zst", ".zstd"):
        return ImageType.ZSTD
    if p.name.endswith(".new.dat"):
        return ImageType.DAT

    try:
        with open(p, "rb") as f:
            header_8k = f.read(8192)
    except OSError:
        return ImageType.UNKNOWN

    # 1. Android Sparse Image Magic at offset 0
    if len(header_8k) >= 4 and header_8k[:4] == SPARSE_MAGIC:
        return ImageType.SPARSE

    # 2. Android OTA payload.bin Magic at offset 0
    if len(header_8k) >= 4 and header_8k[:4] == PAYLOAD_MAGIC:
        return ImageType.PAYLOAD_BIN

    # 3. Zstandard Magic at offset 0
    if len(header_8k) >= 4 and header_8k[:4] == ZSTD_MAGIC:
        return ImageType.ZSTD

    # 4. Super LP Geometry Magic at offset 4096 or offset 0
    if len(header_8k) >= 4100:
        if header_8k[4096:4100] in (LP_GEOMETRY_MAGIC, LP_GEOMETRY_MAGIC_ALT):
            return ImageType.SUPER_LP
    if len(header_8k) >= 4 and header_8k[:4] in (LP_GEOMETRY_MAGIC, LP_GEOMETRY_MAGIC_ALT):
        return ImageType.SUPER_LP

    # 5. Superblock-based filesystems (offset 1024)
    if len(header_8k) >= 1084:
        # EROFS magic at offset 1024..1028
        if header_8k[1024:1028] == EROFS_MAGIC:
            return ImageType.EROFS

        # F2FS magic at offset 1024..1028
        if header_8k[1024:1028] == F2FS_MAGIC:
            return ImageType.F2FS

        # Ext4 magic at offset 1080..1082 (1024 + 0x38 = 1080)
        if header_8k[1080:1082] == EXT4_MAGIC:
            return ImageType.EXT4

    return ImageType.UNKNOWN


def inspect_image(file_path: Path | str) -> ImageInfo:
    """Inspect and return comprehensive metadata for an image file."""
    p = Path(file_path)
    img_type = detect_image_type(p)
    size = p.stat().st_size if p.is_file() else 0

    is_sparse = (img_type == ImageType.SPARSE)
    fs_type = None

    if img_type in (ImageType.EXT4, ImageType.EROFS, ImageType.F2FS):
        fs_type = img_type.value
    elif img_type == ImageType.SUPER_LP:
        fs_type = "super_lp"

    return ImageInfo(
        path=p,
        image_type=img_type,
        size_bytes=size,
        is_sparse=is_sparse,
        fs_type=fs_type,
        description=f"{img_type.value.upper()} image ({size / (1024*1024):.1f} MB)",
    )
