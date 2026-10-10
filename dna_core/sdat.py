"""Android sparse data (sdat2img and img2sdat) conversion engine."""

from __future__ import annotations

import os
from pathlib import Path


def parse_rangeset(range_str: str) -> list[tuple[int, int]]:
    """Parse an Android transfer list range string (e.g. '2,0,2048,4096,8192')."""
    tokens = [int(x) for x in range_str.strip().split(",")]
    count = tokens[0]
    if len(tokens) - 1 != count:
        raise ValueError(f"Invalid RangeSet format: expected {count} elements, got {len(tokens)-1}")

    pairs: list[tuple[int, int]] = []
    for i in range(1, len(tokens), 2):
        pairs.append((tokens[i], tokens[i + 1]))
    return pairs


def format_rangeset(pairs: list[tuple[int, int]]) -> str:
    """Format list of (start, end) block pairs into Android RangeSet string."""
    tokens = [str(len(pairs) * 2)]
    for start, end in pairs:
        tokens.extend([str(start), str(end)])
    return ",".join(tokens)


def sdat2img(
    transfer_list_path: Path | str,
    new_dat_path: Path | str,
    output_img_path: Path | str,
) -> Path:
    """Convert Android sparse new.dat and transfer.list into raw partition image."""
    trans_p = Path(transfer_list_path).resolve()
    dat_p = Path(new_dat_path).resolve()
    out_p = Path(output_img_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)

    with open(trans_p, "r", encoding="utf-8") as tf:
        lines = [line.strip() for line in tf if line.strip()]

    if len(lines) < 2:
        raise ValueError(f"Invalid transfer list format in '{trans_p}'.")

    version = int(lines[0])
    total_blocks = int(lines[1])
    cmd_start_line = 4 if version >= 2 else 2

    BLOCK_SIZE = 4096

    with open(dat_p, "rb") as dat_f, open(out_p, "wb") as out_f:
        # Pre-allocate or truncate output file to full size
        out_f.truncate(total_blocks * BLOCK_SIZE)

        for line in lines[cmd_start_line:]:
            parts = line.split()
            if not parts:
                continue
            cmd = parts[0]
            if cmd == "new":
                ranges = parse_rangeset(parts[1])
                for start, end in ranges:
                    blocks = end - start
                    chunk_bytes = blocks * BLOCK_SIZE
                    data = dat_f.read(chunk_bytes)
                    if len(data) != chunk_bytes:
                        raise EOFError(
                            f"Unexpected end of file in {dat_p}: expected {chunk_bytes} bytes, read {len(data)}"
                        )
                    out_f.seek(start * BLOCK_SIZE)
                    out_f.write(data)
            elif cmd == "zero":
                ranges = parse_rangeset(parts[1])
                for start, end in ranges:
                    blocks = end - start
                    out_f.seek(start * BLOCK_SIZE)
                    out_f.write(b"\x00" * (blocks * BLOCK_SIZE))
            elif cmd in ("erase", "stash", "free"):
                pass  # Ignored for unpacking fresh image

    return out_p


def img2sdat(
    input_img_path: Path | str,
    output_dir: Path | str,
    partition_name: str = "system",
    version: int = 4,
) -> tuple[Path, Path]:
    """Convert raw partition image into Android transfer.list and new.dat."""
    img_p = Path(input_img_path).resolve()
    out_d = Path(output_dir).resolve()
    out_d.mkdir(parents=True, exist_ok=True)

    trans_out = out_d / f"{partition_name}.transfer.list"
    dat_out = out_d / f"{partition_name}.new.dat"

    BLOCK_SIZE = 4096
    total_size = img_p.stat().st_size
    total_blocks = (total_size + BLOCK_SIZE - 1) // BLOCK_SIZE

    non_zero_ranges: list[tuple[int, int]] = []
    current_start: int | None = None

    zero_block = b"\x00" * BLOCK_SIZE

    # Phase 1: Scan for non-empty block ranges
    with open(img_p, "rb") as in_f:
        for block_idx in range(total_blocks):
            buf = in_f.read(BLOCK_SIZE)
            if not buf:
                break
            is_zero = (buf == zero_block or buf == b"\x00" * len(buf))
            if not is_zero:
                if current_start is None:
                    current_start = block_idx
            else:
                if current_start is not None:
                    non_zero_ranges.append((current_start, block_idx))
                    current_start = None

        if current_start is not None:
            non_zero_ranges.append((current_start, total_blocks))

    if not non_zero_ranges:
        non_zero_ranges = [(0, total_blocks)]

    # Phase 2: Write transfer.list
    with open(trans_out, "w", encoding="utf-8") as tf:
        tf.write(f"{version}\n")
        tf.write(f"{total_blocks}\n")
        if version >= 2:
            tf.write("0\n")
            tf.write("0\n")
        # Global erase
        all_ranges = format_rangeset([(0, total_blocks)])
        tf.write(f"erase {all_ranges}\n")
        for start, end in non_zero_ranges:
            range_str = format_rangeset([(start, end)])
            tf.write(f"new {range_str}\n")

    # Phase 3: Write new.dat
    with open(img_p, "rb") as in_f, open(dat_out, "wb") as out_dat:
        for start, end in non_zero_ranges:
            blocks = end - start
            in_f.seek(start * BLOCK_SIZE)
            data = in_f.read(blocks * BLOCK_SIZE)
            if len(data) < blocks * BLOCK_SIZE:
                data = data.ljust(blocks * BLOCK_SIZE, b"\x00")
            out_dat.write(data)

    return trans_out, dat_out
