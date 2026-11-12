#!/usr/bin/env python3
"""
readme_writer.py - Phase 4b README generation for DocumentOrganizer.

Usage:
    python readme_writer.py --target <path> [--dry-run] [--overwrite]
                            [--tasks <path>] [--fail-on-error]
                            [--output-dir <path>]

For every folder in the target tree (or filtered by --tasks zones):
  - Selects README_project.md template if folder has sub-folders with docs
  - Selects README_simple.md template for leaf folders
  - Fills in folder description, contents table, naming convention note
  - Appends traceability matrix stub for project folders

Rules:
  - Never overwrites an existing README.md unless --overwrite is set
  - Skips excluded dirs (.git, node_modules, etc.) in full-tree mode
  - When --tasks is provided, zone paths take priority over the exclude list
  - Writes a summary of all READMEs generated
  - Processes deepest folders first so parents see freshly generated children
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import jd_registry

# ---------------------------------------------------------------------------
# Safe rglob / iterdir helpers - swallow and log permission errors instead of
# aborting traversal silently. Matches scan.py's walk error pattern so
# diagnostics stay consistent across the DocumentOrganizer skill.
# ---------------------------------------------------------------------------

_rglob_errors: list[tuple[str, str]] = []


def _safe_rglob(directory: Path, pattern: str = "*"):
    """Yield rglob results, logging any PermissionError/OSError and continuing.

    Python's Path.rglob raises on the first unreadable subtree and abandons
    the rest. We trap those so one locked folder does not zero out the
    whole traversal.
    """
    try:
        iterator = directory.rglob(pattern)
    except (PermissionError, OSError) as exc:
        _rglob_errors.append((str(directory), exc.__class__.__name__))
        print(
            f"  [WARN] rglob failed at {directory}: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            return
        except (PermissionError, OSError) as exc:
            _rglob_errors.append((str(directory), exc.__class__.__name__))
            print(
                f"  [WARN] rglob skipped entry under {directory}: {exc.__class__.__name__}",
                file=sys.stderr,
            )
            continue
        yield item


def _safe_iterdir(directory: Path):
    try:
        yield from directory.iterdir()
    except (PermissionError, OSError) as exc:
        _rglob_errors.append((str(directory), exc.__class__.__name__))
        print(
            f"  [WARN] iterdir failed at {directory}: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXCLUDE_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    "$RECYCLE.BIN",
    "venv",
    ".venv",
    "site-packages",
    ".pytest_cache",
    ".eggs",
    "build",
    "dist",
    "browser-profile",
    ".agent",
    ".vscode",
    ".idea",
    "logs",
    "temp",
    "tmp",
    "dist-packages",
    "_archive",
    "_duplicates",
}
# Hard-excluded even under --tasks: never want READMEs here.
_ALWAYS_EXCLUDE = {".git", "node_modules", "__pycache__", ".job"}

_DOC_SUFFIXES = {".md", ".txt", ".rst", ".pdf", ".docx", ".xlsx", ".pptx", ".doc"}
_CODE_SUFFIXES = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cs", ".cpp", ".h"}
_ASSET_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".mp3",
    ".zip",
    ".tar",
    ".gz",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
        return any(part in _EXCLUDE_DIRS for part in rel.parts)
    except ValueError:
        return False


def _is_always_excluded(path: Path) -> bool:
    return any(part in _ALWAYS_EXCLUDE for part in path.parts)


def _file_type_icon(suffix: str) -> str:
    s = suffix.lower()
    if s in _DOC_SUFFIXES:
        return "[DOC]"
    if s in _CODE_SUFFIXES:
        return "[SRC]"
    if s in _ASSET_SUFFIXES:
        return "[AST]"
    return "[DIR]"


def _is_project_folder(directory: Path) -> bool:
    """True if folder has at least one sub-folder containing doc files."""
    for child in _safe_iterdir(directory):
        if child.is_dir() and child.name not in _ALWAYS_EXCLUDE:
            for f in _safe_rglob(child, "*"):
                try:
                    if f.is_file() and f.suffix.lower() in _DOC_SUFFIXES:
                        return True
                except OSError:
                    continue
    return False


def _describe_folder(name: str) -> str:
    """Generate a simple 1-line description from folder name."""
    descriptions = {
        "current": "Active, in-use documents for this project",
        "archive": "Historical versions and superseded documents",
        "drafts": "Work-in-progress documents not yet finalized",
        "assets": "Images, media, and supporting files",
        "analysis": "Research, analysis, and evaluation documents",
        "templates": "Reusable document templates - copy before editing",
        "docs": "Project documentation and specifications",
        "src": "Source code and primary content",
        "tests": "Test files and fixtures",
        "_duplicates": "Duplicate files detected during reorganization - review and delete if confirmed",
        "_inbox": "Unsorted files pending placement - nothing lives here permanently",
    }
    return descriptions.get(name.lower(), f"Contents of `{name}/`")


# ---------------------------------------------------------------------------
# Staleness Check
# ---------------------------------------------------------------------------


def _check_staleness(target: Path, scan_json_path: Path) -> bool:
    """Return True if target directory state differs from scan.json."""
    if not scan_json_path.exists():
        return False

    try:
        with open(scan_json_path, encoding="utf-8") as f:
            data = json.load(f)

        old_count = data.get("inventory", {}).get("total_files", 0)
        current_files = [
            f for f in target.rglob("*") if f.is_file() and not _is_excluded(f, target)
        ]
        current_count = len(current_files)

        if old_count != current_count:
            print(f"  [STALE] File count changed: {old_count} -> {current_count}")
            return True

        # Check for large size/mtime drift on a sample
        return False
    except Exception as exc:
        print(f"  [WARN] Staleness check failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# README content builders
# ---------------------------------------------------------------------------


def _try_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _format_dir_row(item: Path) -> str:
    count = sum(1 for sub in _safe_rglob(item, "*") if _try_is_file(sub))
    desc = f"{_describe_folder(item.name)} ({count} files)"
    return f"| [DIR] `{item.name}` | Folder | — | {desc} |\n"


def _format_file_row(item: Path, metadata: dict) -> str:
    icon = _file_type_icon(item.suffix)
    kind = item.suffix.lstrip(".").upper() or "File"

    file_meta = metadata.get("files", {}).get(item.name, {})
    usage_context = file_meta.get("usage_context")
    content_summary = file_meta.get("content_summary")

    if usage_context and content_summary:
        return (
            f"| {icon} `{item.name}` | {kind} | {usage_context} | {content_summary} |\n"
        )
    else:
        # Fallback to parsing from filename
        parsed = jd_registry.extract_id(item.name)
        if parsed:
            _, _, tags = parsed
            valid_meanings = []
            for t in tags:
                t_upper = t.upper()
                if t_upper in jd_registry.VALID_TAGS:
                    meaning = jd_registry.VALID_TAGS[t_upper].split(" — ")[0]
                    valid_meanings.append(meaning)
            usage = ", ".join(valid_meanings) if valid_meanings else "Record"

            match = re.match(
                r"^\d{2}\.\d{3}(?:\.[A-Za-z]{2}){0,2} - \d{8} - (.*?)(\.[a-zA-Z0-9]+)?$",
                item.name,
            )
            if match:
                raw_title = match.group(1)
                content = raw_title.replace("_", " ").capitalize()
            else:
                content = item.stem.split(" - ")[-1].replace("_", " ").capitalize()

            return f"| {icon} `{item.name}` | {kind} | {usage} | {content} |\n"
        else:
            try:
                size_str = f"{item.stat().st_size / 1024:.1f} KB"
            except OSError:
                size_str = "— KB"
            return f"| {icon} `{item.name}` | {kind} | — | {size_str} |\n"


def _check_empty_directory(directory: Path, lines: list) -> None:
    try:
        if not any(i for i in directory.iterdir() if i.name not in {"README.md"}):
            lines.append("| (empty) | — | — | — |\n")
    except (PermissionError, OSError):
        pass


def _build_contents_table(directory: Path, metadata: dict) -> str:
    lines = [
        "## Contents\n\n",
        "| Name | Type | Usage | Content Summary |\n",
        "|---|---|---|---|\n",
    ]
    try:
        items = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except (PermissionError, OSError) as exc:
        _rglob_errors.append((str(directory), exc.__class__.__name__))
        print(
            f"  [WARN] iterdir failed at {directory}: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return ""

    for item in items:
        if item.name in _ALWAYS_EXCLUDE or item.name == "README.md":
            continue
        lines.append(
            _format_dir_row(item) if item.is_dir() else _format_file_row(item, metadata)
        )

    _check_empty_directory(directory, lines)
    return "".join(lines)


def _build_traceability_matrix() -> str:
    return (
        "## Traceability Matrix\n\n"
        "> Populate document traceability references after reorganization.\n\n"
        "| Document | Use Case / Program | Linked To | Status |\n"
        "|---|---|---|---|\n"
        "| — | — | — | — |\n\n"
    )


def _build_readme_simple(directory: Path, metadata: dict, registry: dict) -> str:
    name = directory.name
    desc = _describe_folder(name)
    ts = datetime.now().strftime("%Y-%m-%d")

    project_identity = ""
    pp = jd_registry.resolve_project(directory, registry)
    if pp and pp in registry.get("projects", {}):
        p_name = registry["projects"][pp].get("name", "Unknown")
        p_path = registry["projects"][pp].get("folder", "Unknown")
        project_identity = (
            "## Project Identity\n\n"
            f"- **Project ID (PP):** {pp}\n"
            f"- **Project Name:** {p_name}\n"
            f"- **Path:** {p_path}\n\n"
        )

    return (
        f"# {name}/\n\n"
        f"> {desc}\n\n"
        f"_Last updated: {ts}_\n\n"
        f"{project_identity}"
        f"{_build_contents_table(directory, metadata)}\n"
        "## Naming Convention\n\n"
        "Files in this folder follow `snake_case.md` naming. "
        "README files use `README.md` (UPPERCASE).\n\n"
        "## Retention\n\n"
        "- Archive files older than 2 years to `archive/`\n"
        "- Keep only the latest version of each document\n"
    )


def _build_readme_project(directory: Path, metadata: dict, registry: dict) -> str:
    name = directory.name
    desc = _describe_folder(name)
    ts = datetime.now().strftime("%Y-%m-%d")

    project_identity = ""
    pp = jd_registry.resolve_project(directory, registry)
    if pp and pp in registry.get("projects", {}):
        p_name = registry["projects"][pp].get("name", "Unknown")
        p_path = registry["projects"][pp].get("folder", "Unknown")
        project_identity = (
            "## Project Identity\n\n"
            f"- **Project ID (PP):** {pp}\n"
            f"- **Project Name:** {p_name}\n"
            f"- **Path:** {p_path}\n\n"
        )

    return (
        f"# {name}/\n\n"
        f"> {desc}\n\n"
        f"_Last updated: {ts}_\n\n"
        f"{project_identity}"
        f"{_build_contents_table(directory, metadata)}\n"
        f"{_build_traceability_matrix()}"
        "## Naming Convention\n\n"
        "Files in this folder follow `snake_case.md` naming. "
        "README files use `README.md` (UPPERCASE).\n\n"
        "## Retention\n\n"
        "- Archive superseded files to `archive/`\n"
        "- Keep only the latest version of each document in `current/`\n"
    )


# ---------------------------------------------------------------------------
# Directory selection
# ---------------------------------------------------------------------------


def _process_zone_path(zp: Path, collected: list, seen: set) -> None:
    if not zp.is_dir():
        print(f"  [WARN] zone path not found: {zp}")
        return

    if zp not in seen and not _is_always_excluded(zp):
        collected.append(zp)
        seen.add(zp)

    for d in _safe_rglob(zp, "*"):
        try:
            is_dir = d.is_dir()
        except OSError:
            continue
        if is_dir and not _is_always_excluded(d) and d not in seen:
            collected.append(d)
            seen.add(d)


def _load_zone_dirs(target: Path, tasks_path: Path) -> list[Path]:
    """Load zones from a tasks JSON file and expand to zone paths + all descendants."""
    with tasks_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    zones = data.get("zones", [])
    if not isinstance(zones, list):
        raise ValueError(f"--tasks file missing 'zones' array: {tasks_path}")

    collected: list[Path] = []
    seen: set[Path] = set()

    for zone in zones:
        raw = zone.get("path") if isinstance(zone, dict) else None
        if not raw:
            continue
        zp = Path(raw)
        zp = zp.resolve() if zp.is_absolute() else (target / zp).resolve()
        _process_zone_path(zp, collected, seen)

    return collected


def _full_tree_dirs(target: Path) -> list[Path]:
    out = [target]
    for d in _safe_rglob(target, "*"):
        try:
            is_dir = d.is_dir()
        except OSError:
            continue
        if is_dir and not _is_excluded(d, target):
            out.append(d)
    return out


# ---------------------------------------------------------------------------
# Main writer loop
# ---------------------------------------------------------------------------


def _get_rel_display(directory: Path, target: Path) -> Path:
    try:
        rel_display = (
            directory.relative_to(target)
            if directory == target or target in directory.parents
            else directory
        )
    except ValueError:
        rel_display = directory
    if str(rel_display) in ("", "."):
        rel_display = Path(".")
    return rel_display


def _process_directory(
    directory: Path,
    target: Path,
    dry_run: bool,
    overwrite: bool,
    stats: dict,
    metadata: dict,
    registry: dict,
) -> None:
    readme_path = directory / "README.md"
    rel_display = _get_rel_display(directory, target)

    if readme_path.exists() and not overwrite:
        print(f"  [SKIP] {rel_display} — README.md exists (use --overwrite to replace)")
        stats["skipped_existing"] += 1
        return

    try:
        is_project = _is_project_folder(directory)
        content = (
            _build_readme_project(directory, metadata, registry)
            if is_project
            else _build_readme_simple(directory, metadata, registry)
        )
        template_type = "project" if is_project else "simple"

        action = "[DRY]" if dry_run else "[WRITE]"
        print(f"  {action} {rel_display}/README.md  [{template_type} template]")

        if not dry_run:
            readme_path.write_text(content, encoding="utf-8")
        stats["generated"] += 1

    except Exception as exc:
        stats["errored"].append((directory, str(exc)))
        try:
            print(f"  [ERR]  {directory}: {exc}")
        except UnicodeEncodeError:
            print(f"  [ERR]  (unicode error in path name representation): {exc}")


def _write_error_report(errored: list, target: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "missing_readmes.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Missing READMEs Report\n\n",
        f"_Generated: {ts}_\n\n",
        f"Target: `{target}`\n\n",
        f"Failures: **{len(errored)}**\n\n",
        "| Folder | Error |\n",
        "|---|---|\n",
    ]
    for d, msg in errored:
        safe_msg = msg.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{d}` | {safe_msg} |\n")
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"  Wrote failure report: {report_path}")


def write_readmes(
    target: Path,
    dry_run: bool,
    overwrite: bool,
    tasks_path: Path | None,
    fail_on_error: bool,
    output_dir: Path,
    scan_json: Path | None = None,
) -> int:
    """Write README.md for every eligible folder. Returns process exit code."""
    stats = {"generated": 0, "skipped_existing": 0, "errored": []}

    if scan_json and _check_staleness(target, scan_json):
        print("\n[WARNING] Directory state has changed since the initial scan.")
        print("Documentation might be stale. Consider re-scanning.\n")

    if tasks_path is not None:
        dirs_to_process = _load_zone_dirs(target, tasks_path)
    else:
        dirs_to_process = _full_tree_dirs(target)

    # Leaves first: deepest paths generated before their parents so parent
    # Contents tables observe child READMEs and accurate child counts.
    dirs_to_process.sort(key=lambda p: len(p.parts), reverse=True)

    print(f"\n{'=' * 60}")
    print("  readme_writer - Phase 4b")
    print(f"  Target: {target}")
    if tasks_path is not None:
        print(f"  Tasks:  {tasks_path}")
    print(f"  Folders to process: {len(dirs_to_process)}")
    print(
        f"  Mode: {'DRY-RUN' if dry_run else 'LIVE'}  |  Overwrite: {overwrite}  |  Fail-on-error: {fail_on_error}"
    )
    print(f"{'=' * 60}\n")

    registry = jd_registry.load_registry()
    print(
        f"  [INFO] Loaded registry.json with {len(registry.get('projects', {}))} projects"
    )

    metadata = {}
    metadata_path = target / "99_SYSTEM" / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)
            print(
                f"  [INFO] Loaded metadata.json with {len(metadata.get('files', {}))} entries"
            )
        except Exception as e:
            print(f"  [WARN] Failed to load metadata.json: {e}")

    for directory in dirs_to_process:
        _process_directory(
            directory, target, dry_run, overwrite, stats, metadata, registry
        )

    print(f"\n{'=' * 60}")
    print(
        f"  Done. generated={stats['generated']}  skipped_existing={stats['skipped_existing']}  errored={len(stats['errored'])}"
    )
    if _rglob_errors:
        print(
            f"  [SUMMARY] Skipped {len(_rglob_errors)} unreadable paths during traversal",
            file=sys.stderr,
        )
    print(f"{'=' * 60}\n")

    if stats["errored"] and fail_on_error:
        _write_error_report(stats["errored"], target, output_dir)
        return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate README.md files for every folder in a reorganized tree"
    )
    parser.add_argument(
        "--target", required=True, help="Root directory to generate READMEs for"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing README.md files"
    )
    parser.add_argument(
        "--tasks",
        default=None,
        help="Path to tasks JSON with zones[].path to restrict generation to",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Write missing_readmes.md and exit 1 if any folder fails",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Where to write missing_readmes.md (default: parent of --target)",
    )
    parser.add_argument(
        "--scan-json", default=None, help="Path to scan.json for staleness check"
    )

    args = parser.parse_args()
    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"ERROR: Target directory not found: {target}")
        sys.exit(1)

    tasks_path: Path | None = None
    if args.tasks:
        tasks_path = Path(args.tasks).resolve()
        if not tasks_path.is_file():
            print(f"ERROR: --tasks file not found: {tasks_path}")
            sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else target.parent

    scan_json = Path(args.scan_json).resolve() if args.scan_json else None

    exit_code = write_readmes(
        target=target,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        tasks_path=tasks_path,
        fail_on_error=args.fail_on_error,
        output_dir=output_dir,
        scan_json=scan_json,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
