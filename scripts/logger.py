"""Centralized structured logger for DocumentOrganizer pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "DocumentOrganizer",
    log_file: Path | str | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure and return a structured logger instance."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def get_logger(
    name: str = "DocumentOrganizer",
    level: int | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Retrieve or configure a standardized logger instance."""
    resolved_level = level if level is not None else logging.INFO
    return setup_logger(name=name, log_file=log_file, level=resolved_level)


def emit_progress(
    source: str,
    phase: str,
    message: str,
    level: str = "INFO",
    progress: str | None = None,
    log_file: str | None = None,
) -> None:
    """Emit formatted progress line and optionally persist to JSONL."""
    import json
    from datetime import datetime

    prefix = f"[{level}] [{source}/{phase}]"
    prog_str = f" ({progress})" if progress else ""
    print(f"{prefix} {message}{prog_str}", flush=True)

    if log_file:
        try:
            p = Path(log_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "ts": datetime.now().astimezone().isoformat(),
                "level": level,
                "source": source,
                "phase": phase,
                "msg": message,
            }
            if progress:
                event["progress"] = progress
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass
