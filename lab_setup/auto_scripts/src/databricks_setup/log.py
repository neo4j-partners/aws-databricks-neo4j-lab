"""Centralized dual-output logging: terminal console + plaintext log file.

Every module imports ``log`` (and optionally ``console``) from here instead
of creating its own ``Console`` instance.  ``log()`` writes to both the
terminal (full Rich formatting) and a timestamped plaintext log file.

Log levels control what appears on the terminal.  The log file always
receives everything (DEBUG and above).
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import IO, Any

from rich.console import Console

# Terminal console — same behaviour every module had before.
console = Console()


class Level(IntEnum):
    """Simple log levels (smaller = more verbose)."""

    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


# File-backed console — initialised lazily by ``init_log_file()``.
_file_handle: IO[str] | None = None
_file_console: Console | None = None
_log_path: Path | None = None
_terminal_level: Level = Level.INFO


def set_level(level: Level) -> None:
    """Set the minimum log level shown on the terminal.

    The log file always receives all messages regardless of this setting.
    """
    global _terminal_level  # noqa: PLW0603
    _terminal_level = level


def init_log_file(log_dir: Path | None = None) -> Path:
    """Open the log file and prepare the file console.

    Call once from the CLI entry point before any work begins.

    Args:
        log_dir: Directory for the log file.  Defaults to the current
            working directory.

    Returns:
        Absolute path to the newly created log file.
    """
    global _file_handle, _file_console, _log_path  # noqa: PLW0603

    if log_dir is None:
        log_dir = Path.cwd()
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_path = log_dir / f"databricks_setup_{timestamp}.log"

    _file_handle = open(_log_path, "w", encoding="utf-8")  # noqa: SIM115
    _file_console = Console(
        file=_file_handle,
        force_terminal=False,
        no_color=True,
        width=120,
    )

    return _log_path


def close_log_file() -> None:
    """Flush and close the log file.  Safe to call more than once."""
    global _file_handle, _file_console  # noqa: PLW0603

    if _file_handle is not None:
        _file_handle.flush()
        _file_handle.close()
        _file_handle = None
        _file_console = None


_LEVEL_TAG = {
    Level.DEBUG: "DEBUG",
    Level.INFO: "INFO",
    Level.WARNING: "WARN",
    Level.ERROR: "ERROR",
}


def _timestamp(level: Level) -> str:
    now = datetime.now()
    tag = _LEVEL_TAG.get(level, "INFO")
    return now.strftime("[%H:%M:%S.") + f"{now.microsecond // 1000:03d}] [{tag}]"


def _write_to_file(*args: Any, level: Level = Level.INFO, **kwargs: Any) -> None:
    """Write a timestamped line to the log file."""
    if _file_console is not None:
        _file_console.print(_timestamp(level), *args, **kwargs)
        if _file_handle is not None:
            _file_handle.flush()


def log(
    *args: Any,
    level: Level = Level.INFO,
    **kwargs: Any,
) -> None:
    """Print to both the terminal and the log file.

    Drop-in replacement for ``console.print()``.  Rich renderables
    (styled strings, ``Table``, ``Text``, etc.) are rendered with full
    colour on the terminal and as plain text in the log file.

    Args:
        *args: Passed through to ``Console.print()``.
        level: Log level for this message.  Messages below
            ``_terminal_level`` are written only to the log file.
        **kwargs: Passed through to ``Console.print()``.
    """
    if level >= _terminal_level:
        console.print(*args, **kwargs)

    _write_to_file(*args, level=level, **kwargs)


def log_to_file(*args: Any, level: Level = Level.INFO, **kwargs: Any) -> None:
    """Write only to the log file (skip the terminal).

    Useful for verbose detail that would clutter the console.
    """
    _write_to_file(*args, level=level, **kwargs)
