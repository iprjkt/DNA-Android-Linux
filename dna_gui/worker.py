"""Asynchronous worker thread for non-blocking task execution in DNA-Linux GUI."""

from __future__ import annotations

import io
import logging
import subprocess
import sys
import traceback
from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class SignalLogHandler(logging.Handler):
    """Logging handler that emits log records through a Qt signal."""

    def __init__(self, emitter: Callable[[str], None]) -> None:
        super().__init__()
        self.emitter = emitter
        self.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.emitter(msg)
        except Exception:
            self.handleError(record)


class StreamEmitter(io.TextIOBase):
    """Text stream proxy that redirects written lines to a Qt signal callback."""

    def __init__(self, emitter: Callable[[str], None], original_stream: Any) -> None:
        super().__init__()
        self.emitter = emitter
        self.original_stream = original_stream

    def write(self, s: str) -> int:
        if s:
            # Emit line-by-line or non-empty chunks
            stripped = s.rstrip("\r\n")
            if stripped:
                self.emitter(stripped)
            try:
                self.original_stream.write(s)
            except Exception:
                pass
        return len(s)

    def flush(self) -> None:
        try:
            self.original_stream.flush()
        except Exception:
            pass


class WorkerThread(QThread):
    """Worker thread that executes long-running operations in the background."""

    started_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(object)
    failed_signal = pyqtSignal(str)

    def __init__(
        self,
        task_name: str,
        target: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.task_name = task_name
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.result: Any = None
        self.error: str | None = None

    def run(self) -> None:
        self.started_signal.emit(self.task_name)

        # Hook into root logger and DNA logger
        handler = SignalLogHandler(self.log_signal.emit)
        root_logger = logging.getLogger()
        dna_logger = logging.getLogger("dna")
        root_logger.addHandler(handler)
        dna_logger.addHandler(handler)

        # Redirect stdout and stderr temporarily
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        stream_out = StreamEmitter(self.log_signal.emit, orig_stdout)
        stream_err = StreamEmitter(self.log_signal.emit, orig_stderr)
        sys.stdout = stream_out  # type: ignore[assignment]
        sys.stderr = stream_err  # type: ignore[assignment]

        try:
            self.result = self.target(*self.args, **self.kwargs)
            self.finished_signal.emit(self.result)
        except Exception as exc:
            err_trace = traceback.format_exc()
            self.error = f"{exc}\n{err_trace}"

            details = []
            if isinstance(exc, subprocess.CalledProcessError):
                cmd_repr = " ".join(str(a) for a in exc.cmd) if isinstance(exc.cmd, (list, tuple)) else str(exc.cmd)
                details.append(f"> Command failed with exit code: {exc.returncode}")
                details.append(f"> Failed command: {cmd_repr}")
                err_out = (exc.stderr or "").strip()
                std_out = (exc.output or "").strip()
                if err_out:
                    details.append(f"> Command error output:\n{err_out}")
                elif std_out:
                    details.append(f"> Command output:\n{std_out}")

            detail_msg = ("\n" + "\n".join(details)) if details else ""
            self.log_signal.emit(f"=== Task Error: {exc} ==={detail_msg}\n{err_trace}")
            self.failed_signal.emit(str(exc))
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            root_logger.removeHandler(handler)
            dna_logger.removeHandler(handler)
