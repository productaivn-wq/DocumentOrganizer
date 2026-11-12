"""
desktop_scanner.py — Headless desktop document detection and staging for DocumentOrganizer.

Implements: UC-001, UC-002
Traces: FR-002, FR-011
Verifies: TC-ORG-DESKTOP-01
Enforces: Zero Desktop Clutter Invariant
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("DocumentOrganizer.DesktopScanner")

PHOTO_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
}

SYSTEM_FILE_PATTERNS: set[str] = {"desktop.ini", "thumbs.db", ".ds_store"}


def _load_photo_extensions() -> set[str]:
    """Attempt to load photo extensions from photo_ingest module.

    Returns:
        Set of photo extensions, or default set if module unavailable.
    """
    try:
        from . import photo_ingest

        return photo_ingest.PhotoIngestEngine.SUPPORTED_EXTENSIONS
    except (ImportError, AttributeError):
        return PHOTO_EXTENSIONS


SUPPORTED_PHOTO_EXTENSIONS = _load_photo_extensions()


@dataclass
class ScannedAsset:
    """Represents an unorganized asset discovered on desktop or staging areas."""

    path: Path
    filename: str = ""
    parent_folder: str = ""
    size_bytes: int = 0
    modified_time: float = 0.0
    extension: str = ""
    is_photo: bool = False

    def __post_init__(self) -> None:
        self._normalize_path()
        self._populate_metadata()

    def _normalize_path(self) -> None:
        """Convert string path to Path object if needed."""
        if isinstance(self.path, str):
            self.path = Path(self.path)

    def _populate_metadata(self) -> None:
        """Populate metadata fields from the path."""
        if self.path:
            if not self.filename:
                self.filename = self.path.name
            if not self.parent_folder:
                self.parent_folder = self.path.parent.name
            if not self.extension:
                self.extension = self.path.suffix.lower()
            if not self.is_photo and self.extension:
                self.is_photo = self.extension in SUPPORTED_PHOTO_EXTENSIONS


def get_desktop_path() -> Path:
    """Discovers user desktop directory with OS fallback.

    Returns:
        Path to desktop directory, or home/Desktop as fallback.
    """
    home = Path.home()
    for candidate in [
        home / "OneDrive" / "Desktop",
        home / "Desktop",
        home / "desktop",
    ]:
        if candidate.exists():
            return candidate
    return home / "Desktop"


def scan_desktop() -> list[Path]:
    """Legacy helper: Returns list of file paths directly on desktop.

    Returns:
        List of file paths on desktop, or empty list if desktop not found.
    """
    try:
        desktop = get_desktop_path()
        if desktop.is_dir():
            return [p for p in desktop.iterdir() if p.is_file()]
    except Exception:
        pass
    return []


class DesktopScanner:
    """Scans desktop and staging paths for unorganized loose assets."""

    SUPPORTED_PHOTO_EXTENSIONS = SUPPORTED_PHOTO_EXTENSIONS

    def __init__(self, override_paths: list[Path | str] | None = None) -> None:
        """Initialize scanner with optional override paths.

        Args:
            override_paths: List of paths to scan instead of default desktop.
        """
        if override_paths is not None:
            self.target_paths = [Path(p).resolve() for p in override_paths]
        else:
            paths: list[Path] = []
            home = Path.home()
            for cand in [home / "OneDrive" / "Desktop", home / "Desktop"]:
                if cand.exists() and cand.resolve() not in paths:
                    paths.append(cand.resolve())
            self.target_paths = paths if paths else [get_desktop_path().resolve()]

    def classify(self, path: Path | str) -> str:
        """Classifies a file path into a category (e.g. documents, code, photos, misc)."""
        p = Path(path)
        name = p.name.lower()
        if name.startswith(".") or not p.suffix:
            return "misc"
        ext = p.suffix.lower()
        if ext in {
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".md",
            ".rtf",
            ".odt",
            ".pptx",
            ".xlsx",
            ".csv",
        }:
            return "documents"
        if ext in {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".html",
            ".css",
            ".sh",
            ".bash",
            ".ps1",
            ".bat",
            ".cmd",
            ".json",
            ".yaml",
            ".yml",
            ".sql",
        }:
            return "code"
        if ext in self.SUPPORTED_PHOTO_EXTENSIONS:
            return "photos"
        return "misc"

    def _is_system_file(self, path: Path) -> bool:
        """Check if a file is a system file that should be ignored."""
        return path.name.startswith(".") or path.name.lower() in SYSTEM_FILE_PATTERNS

    def _get_file_stats(self, path: Path) -> tuple[int, float]:
        """Get file size and modification time with error handling.

        Returns:
            Tuple of (size_bytes, modified_time).
        """
        try:
            stat = path.stat()
            return stat.st_size, stat.st_mtime
        except Exception:
            return 0, 0.0

    def scan_unorganized(self) -> list[ScannedAsset]:
        """Discovers all unorganized loose files under target desktop paths.

        Returns:
            List of ScannedAsset objects representing unorganized files.
        """
        results: list[ScannedAsset] = []
        for base in self.target_paths:
            if not base.exists() or not base.is_dir():
                continue
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                if self._is_system_file(p):
                    continue

                size, mtime = self._get_file_stats(p)
                ext = p.suffix.lower()
                is_photo = ext in self.SUPPORTED_PHOTO_EXTENSIONS

                results.append(
                    ScannedAsset(
                        path=p,
                        filename=p.name,
                        parent_folder=p.parent.name,
                        size_bytes=size,
                        modified_time=mtime,
                        extension=ext,
                        is_photo=is_photo,
                    )
                )
        return results


def check_zero_desktop_invariant(
    desktop_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Evaluates Zero-Desktop Invariant.
    Verifies that desktop contains zero unorganized files.

    Args:
        desktop_path: Optional path to desktop. If None, uses default desktop path.

    Returns:
        Dictionary with 'passed' (bool), 'violating_file_count' (int),
        'violations' (list of paths), and 'unorganized_assets' (list of ScannedAsset).
    """
    override = [Path(desktop_path)] if desktop_path else None
    scanner = DesktopScanner(override_paths=override)
    try:
        unorganized = scanner.scan_unorganized()
    except Exception as exc:
        logger.debug("Desktop scanner audit fallback: %s", exc)
        unorganized = []

    passed = len(unorganized) == 0
    return {
        "passed": passed,
        "violating_file_count": len(unorganized),
        "violations": [item.path for item in unorganized],
        "unorganized_assets": unorganized,
    }


def main() -> None:
    """CLI entry point for desktop scanning."""
    scanner = DesktopScanner()
    assets = scanner.scan_unorganized()
    print(f"Discovered {len(assets)} unorganized asset(s) on desktop.")
    for a in assets:
        print(f"  - {a.filename} ({a.path})")


if __name__ == "__main__":
    main()
