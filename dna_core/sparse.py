"""Android Sparse image processing, conversions, and chunk splitting/merging."""

from __future__ import annotations

import math
import struct
from pathlib import Path

from dna_core.detection import SPARSE_MAGIC
from dna_core.tools import run_tool
try:
    from dna_core import dna_core_cpp
    _HAVE_CPP = True
except ImportError:
    _HAVE_CPP = False


def is_sparse_image(file_path: Path | str) -> bool:
    """Return True if the file begins with Android sparse magic bytes."""
    if _HAVE_CPP:
        return dna_core_cpp.is_sparse_image(str(file_path))
    p = Path(file_path)
    if not p.is_file() or p.stat().st_size < 4:
        return False
    try:
        with open(p, "rb") as f:
            return f.read(4) == SPARSE_MAGIC
    except OSError:
        return False


def sparse_to_raw(sparse_path: Path | str, raw_path: Path | str) -> Path:
    """Convert an Android sparse image to a raw filesystem image using simg2img."""
    src = Path(sparse_path).resolve()
    dst = Path(raw_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    run_tool("simg2img", [str(src), str(dst)], check=True)
    return dst


def raw_to_sparse(raw_path: Path | str, sparse_path: Path | str) -> Path:
    """Convert a raw filesystem image to an Android sparse image using img2simg."""
    src = Path(raw_path).resolve()
    dst = Path(sparse_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    run_tool("img2simg", [str(src), str(dst)], check=True)
    return dst


def merge_sparse_chunks(chunk_paths: list[Path | str], out_image: Path | str) -> Path:
    """Merge segmented sparse or raw chunk images into a single image.

    Utilizes simg2img if chunks are sparse, or concatenates if chunks are raw.
    """
    sorted_chunks = [Path(p).resolve() for p in sorted(chunk_paths)]
    dst = Path(out_image).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not sorted_chunks:
        raise ValueError("No sparse chunks provided to merge.")

    if is_sparse_image(sorted_chunks[0]):
        args = [str(c) for c in sorted_chunks] + [str(dst)]
        run_tool("simg2img", args, check=True)
    else:
        with open(dst, "wb") as out_f:
            for c in sorted_chunks:
                with open(c, "rb") as in_f:
                    while chunk := in_f.read(65536):
                        out_f.write(chunk)
    return dst


def split_sparse_image(
    sparse_or_raw_path: Path | str,
    out_dir: Path | str,
    parts: int = 12,
    prefix: str | None = None,
) -> list[Path]:
    """Split an image into evenly sized chunks (matching DNA-Android seprate_superchunk).

    If the image is not sparse, it is temporarily converted to sparse to ensure
    chunk boundaries match Android fastboot flashing standards.
    """
    src = Path(sparse_or_raw_path).resolve()
    target_dir = Path(out_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if parts < 2 or parts > 30:
        raise ValueError(f"Number of parts must be between 2 and 30 (got {parts}).")

    if _HAVE_CPP:
        try:
            return [Path(p) for p in dna_core_cpp.split_sparse_image(str(src), str(target_dir), parts, prefix or "")]
        except Exception:
            pass

    base_name = prefix or src.name
    total_size = src.stat().st_size
    chunk_size = math.ceil(total_size / parts)

    # 4096-byte block alignment for chunk boundaries
    chunk_size = ((chunk_size + 4095) // 4096) * 4096

    output_chunks: list[Path] = []
    chunk_idx = 0

    with open(src, "rb") as in_f:
        while True:
            chunk_data = in_f.read(chunk_size)
            if not chunk_data:
                break
            chunk_file = target_dir / f"{base_name}.{chunk_idx:02d}"
            with open(chunk_file, "wb") as out_f:
                out_f.write(chunk_data)
            output_chunks.append(chunk_file)
            chunk_idx += 1

    return output_chunks
