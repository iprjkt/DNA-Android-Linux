"""Structured logging system for DNA-Linux."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dna_core.paths import ProjectPaths

_LOGGER_NAME = "dna"


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return the base logger."""
    return logging.getLogger(name)


def setup_logger(
    name: str = _LOGGER_NAME,
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Configure console and optional file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_format = logging.Formatter(
        "[%(levelname)s] %(message)s" if not verbose else "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Optional File Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def create_operation_logger(
    project_paths: ProjectPaths,
    operation_name: str,
    verbose: bool = False,
) -> tuple[logging.Logger, Path]:
    """Create a structured operation log inside <project>/logs/<op>_<timestamp>.log."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_op = operation_name.lower().replace(" ", "_")
    log_file = project_paths.logs_dir / f"{clean_op}_{timestamp}.log"
    logger = setup_logger(
        name=f"dna.{clean_op}",
        log_file=log_file,
        verbose=verbose,
    )
    logger.info("Started operation '%s' in project '%s'", operation_name, project_paths.project_name)
    return logger, log_file
