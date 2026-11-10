#!/usr/bin/env python3
"""
watch.py - Real-time AI File Organizer Daemon

Watches a specified directory (e.g., INBOX) for new files.
Extracts content, queries local LLM for PARA-Decimal classification,
and safely moves the file to the target workspace root.
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

import organizer

WHITELIST_EXTS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".txt",
    ".md",
    ".webp",
    ".rtf",
    ".pptx",
    ".mp4",
    ".mkv",
    ".mov",
    ".webm",
    ".avi",
    ".m4a",
    ".mp3",
    ".wav",
    ".aac",
    ".flac",
    ".zip",
}

IGNORE_EXTS = {
    ".crdownload",
    ".part",
    ".tmp",
    ".download",
    ".exe",
    ".msi",
    ".rar",
    ".7z",
    ".iso",
    ".dll",
    ".ini",
    ".sys",
    ".lnk",
}

BLACKLIST_DIRS = {
    "zoom",
    "adobe",
    "my games",
    "custom office templates",
    "wondershare",
    "desktop.ini",
    "appdata",
    "local",
}


class AIDocumentHandler(FileSystemEventHandler):
    def __init__(
        self, target_root: Path, dry_run: bool, whitelist_only: bool, triage_mode: bool
    ):
        self.target_root = target_root
        self.dry_run = dry_run
        self.whitelist_only = whitelist_only
        self.triage_mode = triage_mode
        self.processing = set()

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(Path(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(Path(event.dest_path))

    def _is_blacklisted_dir(self, file_path: Path) -> bool:
        # Check if any parent part is in the blacklist
        parts = [p.lower() for p in file_path.parts]
        for b_dir in BLACKLIST_DIRS:
            if b_dir in parts:
                return True
        return False

    def _resolve_target_root_for_file(self, file_path: Path) -> Path:
        """Resolve enclosing project root if file belongs to a monorepo project inbox."""
        try:
            parts = file_path.resolve().parts
            for i, part in enumerate(parts):
                if part.lower() == "01_projects" and i + 1 < len(parts):
                    project_root = Path(*parts[: i + 2])
                    if project_root.exists() and project_root.is_dir():
                        return project_root
        except Exception:
            pass
        return self.target_root

    def process_file(self, file_path: Path):
        ext = file_path.suffix.lower()

        # 1. Immediate Ignores
        name_lower = file_path.name.lower()
        if name_lower in {
            "desktop.ini",
            "thumbs.db",
            ".ds_store",
        } or name_lower.startswith("~$"):
            return

        if ext in IGNORE_EXTS:
            return

        if self.whitelist_only and ext not in WHITELIST_EXTS:
            return

        if self._is_blacklisted_dir(file_path):
            return

        # Prevent double-processing
        if file_path in self.processing:
            return

        self.processing.add(file_path)
        try:
            self._wait_for_file_stable(file_path)
            if not file_path.exists():
                return

            print(f"\n[WATCH] New file detected: {file_path.name}")

            # 1. Extract content & metadata
            content = self._extract_content(file_path)

            # 2. Resolve destination via ProjectRouter
            from project_router import ProjectRouter

            effective_root = self._resolve_target_root_for_file(file_path)
            projects_base = (
                effective_root / "01_PROJECTS"
                if (effective_root / "01_PROJECTS").exists()
                else (
                    effective_root
                    if effective_root.name == "01_PROJECTS"
                    else self.target_root / "01_PROJECTS"
                )
            )
            router = ProjectRouter(workspace_base=projects_base)
            route = router.resolve_destination(
                filename=file_path.name,
                source_dir_name=file_path.parent.name,
                content_hint=content[:1000] if content else "",
            )

            if route:
                dest_folder = route.target_full_path.parent
                dest_name = route.standardized_filename
                print(
                    f"  [ROUTER] {route.matched_rule} -> {route.project_name}/{route.relative_zone_path}/{dest_name}"
                )
            else:
                dest_folder = effective_root / "00_INBOX"
                dest_name = router.standardize_filename(file_path.name)
                print(f"  [FALLBACK] Routing to 00_INBOX / {dest_name}")

            if self.triage_mode:
                dest_folder = (
                    effective_root / "00_INBOX" / f"{dest_folder.name}_Pending"
                )

            # 3. Safe Move
            rename_log = []
            move_log = []
            dup_log = []

            dest = organizer.safe_move(
                src=file_path,
                dest_dir=dest_folder,
                dry_run=self.dry_run,
                rename_log=rename_log,
                move_log=move_log,
                dup_log=dup_log,
                target_root=effective_root,
                custom_name=dest_name,
            )

            if dest:
                print(f"  [SUCCESS] Moved to {dest}")
            else:
                print("  [SKIP] Move failed or duplicate handled.")

        except Exception as e:
            print(f"  [ERR] Exception processing {file_path}: {e}")
        finally:
            self.processing.discard(file_path)

    def _wait_for_file_stable(
        self, file_path: Path, wait_sec: int = 2, max_retries: int = 30
    ) -> bool:
        """Wait until file size stops changing and exclusive read handle can be acquired."""
        retries = 0
        last_size = -1
        while retries < max_retries:
            try:
                if not file_path.exists():
                    return False
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    # Test if external writer lock is released
                    try:
                        with open(file_path, "rb") as f:
                            f.seek(0, os.SEEK_END)
                        return True
                    except (OSError, PermissionError):
                        pass
                last_size = current_size
            except OSError:
                pass
            time.sleep(wait_sec)
            retries += 1
        return file_path.exists()

    def _extract_content(self, file_path: Path) -> str:
        """Extract text or synthesized metadata using DocumentExtractor with fallback."""
        try:
            from extract import DocumentExtractor

            doc = DocumentExtractor.extract(file_path)
            if doc and doc.content:
                return doc.content
        except Exception as e:
            print(f"  [WARN] DocumentExtractor failed on {file_path.name}: {e}")

        # Fallback reading for plain text files
        ext = file_path.suffix.lower()
        if ext in {
            ".txt",
            ".md",
            ".csv",
            ".json",
            ".py",
            ".js",
            ".yaml",
            ".yml",
            ".html",
        }:
            try:
                return file_path.read_text(encoding="utf-8", errors="replace")[:4000]
            except Exception:
                pass

        size_str = (
            f"{file_path.stat().st_size} bytes"
            if file_path.exists()
            else "unknown size"
        )
        return f"[File: {file_path.name}, Size: {size_str}]"


def main():
    if not HAS_WATCHDOG:
        print("ERROR: 'watchdog' library is required. Please run: pip install watchdog")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Real-time AI File Organizer Daemon")
    parser.add_argument(
        "--watch",
        nargs="+",
        required=True,
        help="One or more directories to watch (e.g. ~/Downloads ~/Desktop)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target workspace root for organizing files (e.g. ~/Workspace)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview moves without actually moving files",
    )
    parser.add_argument(
        "--whitelist-only",
        action="store_true",
        help="Only process actionable document/image extensions (ignore all else)",
    )
    parser.add_argument(
        "--triage-mode",
        action="store_true",
        help="Move files to 00_INBOX/{Folder}_Pending instead of final destination",
    )

    args = parser.parse_args()

    watch_dirs = [Path(w).resolve() for w in args.watch]
    target_root = Path(args.target).resolve()

    if not target_root.exists():
        print(f"ERROR: Target root does not exist: {target_root}")
        sys.exit(1)

    event_handler = AIDocumentHandler(
        target_root, args.dry_run, args.whitelist_only, args.triage_mode
    )
    observer = Observer()
    valid_watch_dirs = []

    for wdir in watch_dirs:
        if not wdir.exists():
            print(f"Creating watch directory: {wdir}")
            try:
                wdir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"WARN: Could not create {wdir}: {e}")
                continue
        observer.schedule(event_handler, str(wdir), recursive=False)
        valid_watch_dirs.append(wdir)

    if not valid_watch_dirs:
        print("ERROR: No valid watch directories could be scheduled.")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("  AI DocumentOrganizer Daemon Started")
    for idx, w in enumerate(valid_watch_dirs, 1):
        print(f"  Watching [{idx}]: {w}")
    print(f"  Target:       {target_root}")
    print(f"  Mode:         {'DRY-RUN' if args.dry_run else 'LIVE'}")
    print(f"  Triage:       {'ON' if args.triage_mode else 'OFF'}")
    print(f"  Filter:       {'WHITELIST' if args.whitelist_only else 'ALL'}")
    print(f"{'=' * 60}\n")
    print("Press Ctrl+C to exit...")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
