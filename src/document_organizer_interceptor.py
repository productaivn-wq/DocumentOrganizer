"""Deterministic pre-finish workspace & session scratch organizer."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

DISPOSABLE_NAMES: set[str] = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "playwright_profile",
    "chrome_junc",
    "edge_junc",
    "cdp_chrome",
    "chrome_session",
    "edge_session",
    "edge_profile",
    "chrome_profile",
}


def organize_task_and_conversation_files(
    workspace_dir: str | Path,
    conversation_id: str | None = None,
    task_id: str | None = None,
    brain_root: str | Path | None = None,
) -> dict[str, Any]:
    """Archive reusable scratch scripts from an agent session into 40_ARCHIVE/scratch/."""
    ws = Path(workspace_dir).resolve()
    migrated_scratch: list[str] = []

    if conversation_id:
        if brain_root:
            session_dir = Path(brain_root) / conversation_id
        else:
            default_sessions = Path(
                os.environ.get(
                    "AGENT_SESSIONS_ROOT",
                    str(Path.home() / ".cache" / "document-organizer" / "sessions"),
                )
            )
            session_dir = default_sessions / conversation_id

        scratch_dir = session_dir / "scratch"
        if scratch_dir.exists() and scratch_dir.is_dir():
            target_archive_scratch = ws / "40_ARCHIVE" / "scratch"
            target_archive_scratch.mkdir(parents=True, exist_ok=True)

            for item in scratch_dir.iterdir():
                lower = item.name.lower()
                if (
                    lower in DISPOSABLE_NAMES
                    or "frames" in lower
                    or lower.endswith(".tmp")
                ):
                    continue
                if item.is_file():
                    dest_file = target_archive_scratch / item.name
                    shutil.copy2(item, dest_file)
                    migrated_scratch.append(str(dest_file))

    return {
        "success": True,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "migrated_scratch_files": migrated_scratch,
    }
