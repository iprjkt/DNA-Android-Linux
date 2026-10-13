"""Lossless Android build.prop parser and editor.

Preserves comments, empty lines, section headers, formatting,
and original line ordering while supporting querying, setting,
deleting, and searching property values.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


class PropFile:
    """Represents a parsed Android property file with formatting preservation."""

    def __init__(self, raw_lines: Optional[List[str]] = None, path: Optional[Path] = None):
        self._lines: List[str] = list(raw_lines) if raw_lines is not None else []
        self._path: Optional[Path] = path

    @classmethod
    def load(cls, path: Path | str) -> PropFile:
        """Load and parse a property file from disk."""
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"Property file not found: {p}")
        text = p.read_text(encoding="utf-8", errors="replace")
        return cls(raw_lines=text.splitlines(keepends=True), path=p)

    @classmethod
    def from_text(cls, text: str) -> PropFile:
        """Parse a property file directly from a string."""
        return cls(raw_lines=text.splitlines(keepends=True))

    def _parse_line(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse key-value pair from a single line, or return None if comment/empty."""
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            return None
        if "=" not in line:
            return None
        key, val = line.split("=", 1)
        return key.strip(), val.rstrip("\r\n")

    def has_key(self, key: str) -> bool:
        """Check if a property key exists in the file."""
        return any(self._parse_line(line) and self._parse_line(line)[0] == key for line in self._lines)  # type: ignore

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get the value of a property key."""
        for line in self._lines:
            kv = self._parse_line(line)
            if kv and kv[0] == key:
                return kv[1]
        return default

    def set(self, key: str, value: str) -> None:
        """Set or update a property key.

        If the key already exists, updates in-place preserving its position.
        Otherwise, appends it to the end of the file.
        """
        for i, line in enumerate(self._lines):
            kv = self._parse_line(line)
            if kv and kv[0] == key:
                newline = "\r\n" if line.endswith("\r\n") else "\n"
                self._lines[i] = f"{key}={value}{newline}"
                return

        # Key does not exist, append at the end
        if self._lines and not self._lines[-1].endswith(("\n", "\r")):
            self._lines[-1] += "\n"
        self._lines.append(f"{key}={value}\n")

    def delete(self, key: str) -> bool:
        """Delete a property key from the file.

        Returns True if the key was found and deleted, False otherwise.
        """
        found = False
        new_lines: List[str] = []
        for line in self._lines:
            kv = self._parse_line(line)
            if kv and kv[0] == key:
                found = True
                continue
            new_lines.append(line)
        self._lines = new_lines
        return found

    def keys(self) -> List[str]:
        """Return all property keys in order of appearance."""
        keys_list = []
        for line in self._lines:
            kv = self._parse_line(line)
            if kv:
                keys_list.append(kv[0])
        return keys_list

    def items(self) -> List[Tuple[str, str]]:
        """Return all (key, value) pairs in order of appearance."""
        items_list = []
        for line in self._lines:
            kv = self._parse_line(line)
            if kv:
                items_list.append(kv)
        return items_list

    def to_dict(self) -> Dict[str, str]:
        """Return property entries as a dictionary."""
        return dict(self.items())

    def search(self, pattern: str) -> List[Tuple[str, str]]:
        """Search for property keys matching a regex pattern or substring."""
        regex = re.compile(pattern, re.IGNORECASE)
        matches = []
        for line in self._lines:
            kv = self._parse_line(line)
            if kv and regex.search(kv[0]):
                matches.append(kv)
        return matches

    def to_text(self) -> str:
        """Serialize back to string."""
        return "".join(self._lines)

    def save(self, path: Optional[Path | str] = None) -> Path:
        """Save to file path."""
        target = Path(path) if path is not None else self._path
        if target is None:
            raise ValueError("No destination path provided for save()")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_text(), encoding="utf-8")
        self._path = target
        return target


try:
    from dna_core import dna_core_cpp
    _HAVE_CPP = True
except ImportError:
    _HAVE_CPP = False


def find_prop_files(target_dir: Path | str) -> List[Path]:
    """Find all Android property files (build.prop, default.prop) in a directory tree."""
    if _HAVE_CPP:
        try:
            return [Path(p) for p in dna_core_cpp.find_prop_files(str(target_dir))]
        except Exception:
            pass

    root = Path(target_dir)
    if not root.is_dir():
        return []

    prop_files: List[Path] = []
    # Search for files named build.prop or *.prop
    for p in root.rglob("*.prop"):
        if p.is_file():
            prop_files.append(p)

    for p in root.rglob("prop.default"):
        if p.is_file() and p not in prop_files:
            prop_files.append(p)

    return sorted(prop_files)
