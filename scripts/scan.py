#!/usr/bin/env python3
"""
scan.py - Cross-platform directory scanner for DocumentOrganizer.

Emits a single unified scan.json containing inventory, anomalies, duplicates,
and (optionally) folder merge candidates. Replaces the prior scan_report.md /
scan_hashes.json pair and absorbs the former consolidate.py functionality via
the --merge-threshold flag.
"""

import argparse
import difflib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from utils import get_file_hash
except ImportError:
    try:
        from .utils import get_file_hash
    except ImportError:
        try:
            from scripts.utils import get_file_hash
        except ImportError:
            from DocumentOrganizer.scripts.utils import get_file_hash

DEFAULT_EXCLUDES = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "$RECYCLE.BIN",
    "System Volume Information",
    ".job",  # doc_reorg's own artifacts - never scan prior run output
    "_archive",
    "_duplicates",
    ".pytest_cache",
    "build",
    "dist",
}


# ---------------------------------------------------------------------------
# Walk error recording
# ---------------------------------------------------------------------------

_walk_errors: list[tuple[str, str]] = []

# Module-level quiet flag (set from CLI). Walker functions peek at this
# to suppress per-directory progress without plumbing a parameter through every
# signature. Per-directory [SCAN] output is ON by default; --quiet opts out.
_QUIET = False


def _walk_error_handler(exc: OSError) -> None:
    """Called by os.walk when it can't read a directory. Records so the summary can surface it."""
    _walk_errors.append(
        (str(exc.filename) if exc.filename else "<unknown>", exc.__class__.__name__)
    )
    print(
        f"  [WARN] skipped unreadable path: {exc.filename} ({exc.__class__.__name__})",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Filesystem traversal helpers
# ---------------------------------------------------------------------------


def _filter_dirs(dirnames: list[str], excludes_lower: set[str]) -> list[str]:
    return [d for d in dirnames if d.lower() not in excludes_lower]


def _collect_files_fast(root: Path, excludes: set[str]) -> list[Path]:
    excludes_lower = {e.lower() for e in excludes}
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(
        root, onerror=_walk_error_handler, followlinks=False
    ):
        dirnames[:] = _filter_dirs(dirnames, excludes_lower)
        dp = Path(dirpath)
        kept = [f for f in filenames if f.lower() not in excludes_lower]
        if not _QUIET:
            print(f"  [SCAN] {dp} ({len(kept)} files)", file=sys.stderr)
        for f in kept:
            out.append(dp / f)
    return out


def _collect_dirs(root: Path, excludes: set[str]) -> list[Path]:
    excludes_lower = {e.lower() for e in excludes}
    out: list[Path] = []
    for dirpath, dirnames, _filenames in os.walk(
        root, onerror=_walk_error_handler, followlinks=False
    ):
        dirnames[:] = _filter_dirs(dirnames, excludes_lower)
        dp = Path(dirpath)
        if dp != root:
            out.append(dp)
    return out


def _calculate_hash(path: Path, chunk_size: int = 8192) -> str:
    res = get_file_hash(path, algo="md5", chunk_size=chunk_size)
    return res if res is not None else "ERROR"


# ---------------------------------------------------------------------------
# Inventory / anomaly / duplicate analysis
# ---------------------------------------------------------------------------


def _build_inventory(all_files: list[Path]) -> dict:
    total_size = 0
    by_ext: dict[str, int] = defaultdict(int)
    for f in all_files:
        try:
            sz = os.path.getsize(f)
        except OSError:
            sz = 0
        total_size += sz
        ext = f.suffix.lower() if f.suffix else ""
        by_ext[ext] += 1
    return {
        "total_files": len(all_files),
        "total_size_bytes": total_size,
        "by_ext": dict(sorted(by_ext.items(), key=lambda x: x[1], reverse=True)),
    }


def _find_empty_folders(root: Path, excludes: set[str]) -> list[str]:
    excludes_lower = {e.lower() for e in excludes}
    empties: list[str] = []
    for dirpath, dirnames, filenames in os.walk(
        root, onerror=_walk_error_handler, followlinks=False
    ):
        dirnames[:] = _filter_dirs(dirnames, excludes_lower)
        if not dirnames and not filenames:
            empties.append(str(Path(dirpath).resolve()))
    return sorted(empties)


def _find_oversized(all_files: list[Path], large_mb: int) -> list[dict]:
    threshold = large_mb * 1024 * 1024
    oversized: list[dict] = []
    for f in all_files:
        try:
            sz = os.path.getsize(f)
        except OSError:
            continue
        if sz > threshold:
            oversized.append({"path": str(f.resolve()), "size_bytes": sz})
    oversized.sort(key=lambda x: x["size_bytes"], reverse=True)
    return oversized


def _find_duplicates_fast(all_files: list[Path]) -> list[dict]:
    groups: dict[tuple[str, int], list[Path]] = defaultdict(list)
    for f in all_files:
        try:
            sz = os.path.getsize(f)
        except OSError:
            continue
        groups[(f.name, sz)].append(f)
    entries: list[dict] = []
    for (_name, sz), paths in groups.items():
        if len(paths) > 1:
            entries.append(
                {
                    "hash": "",
                    "size_bytes": sz,
                    "paths": [str(p.resolve()) for p in paths],
                }
            )
    entries.sort(key=lambda x: len(x["paths"]), reverse=True)
    return entries


def _find_duplicates_hash(all_files: list[Path]) -> list[dict]:
    hash_groups: dict[str, list[Path]] = defaultdict(list)
    total = len(all_files)
    for i, f in enumerate(all_files):
        h = _calculate_hash(f)
        if h != "ERROR":
            hash_groups[h].append(f)
        if i > 0 and i % 500 == 0:
            print(f"  Indexed {i}/{total} files...", file=sys.stderr)

    entries: list[dict] = []
    for h, paths in hash_groups.items():
        if len(paths) <= 1:
            continue
        size_bytes = 0
        for p in paths:
            try:
                size_bytes = os.path.getsize(p)
                break
            except OSError:
                continue
        entries.append(
            {
                "hash": h,
                "size_bytes": size_bytes,
                "paths": [str(p.resolve()) for p in paths],
            }
        )
    entries.sort(key=lambda x: len(x["paths"]), reverse=True)
    return entries


def _find_duplicates(all_files: list[Path], fast: bool) -> list[dict]:
    if fast:
        return _find_duplicates_fast(all_files)
    return _find_duplicates_hash(all_files)


# ---------------------------------------------------------------------------
# Folder merge-candidate analysis (absorbed from consolidate.py)
# ---------------------------------------------------------------------------


def _get_folder_fingerprint(directory: Path) -> dict[str, str]:
    """Map filenames to their content hashes for a directory (non-recursive)."""
    fingerprint: dict[str, str] = {}
    try:
        for item in directory.iterdir():
            if item.is_file():
                h = _calculate_hash(item)
                if h != "ERROR":
                    fingerprint[item.name] = h
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return fingerprint


def _calculate_overlap(fp1: dict[str, str], fp2: dict[str, str]) -> float:
    if not fp1 or not fp2:
        return 0.0
    hashes1 = set(fp1.values())
    hashes2 = set(fp2.values())
    intersection = hashes1 & hashes2
    return len(intersection) / max(len(hashes1), len(hashes2))


def _find_merge_candidates(
    root: Path, threshold: float, excludes: set[str]
) -> list[dict]:
    all_dirs = _collect_dirs(root, excludes)
    print(
        f"  Checking {len(all_dirs)} directories for merge candidates...",
        file=sys.stderr,
    )
    fingerprints = {d: _get_folder_fingerprint(d) for d in all_dirs}

    candidates: list[dict] = []
    n = len(all_dirs)
    for i in range(n):
        for j in range(i + 1, n):
            d1, d2 = all_dirs[i], all_dirs[j]
            name_sim = difflib.SequenceMatcher(
                None, d1.name.lower(), d2.name.lower()
            ).ratio()
            overlap = _calculate_overlap(fingerprints[d1], fingerprints[d2])
            if name_sim >= threshold or overlap >= threshold:
                reason = "name" if name_sim >= threshold else "content"
                similarity = max(name_sim, overlap)
                candidates.append(
                    {
                        "folders": [str(d1.resolve()), str(d2.resolve())],
                        "similarity": round(similarity, 4),
                        "reason": reason,
                    }
                )
    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _resolve_output_dir(output_arg: str | None, target: Path) -> Path:
    """
    --output semantics:
      - None           -> ERROR: --output is required to prevent polluting the target.
      - dir path       -> write scan.json into that dir.
      - ends in .json  -> use that exact file path.
      - ends in .md    -> deprecation warning; use its parent dir.
    Returns the directory that will contain scan.json (caller appends filename)
    unless an explicit .json file path was given, in which case caller respects it.
    """
    if output_arg is None:
        print(
            f"  [WARNING] No --output specified. Writing scan.json into target dir {target}. "
            f"Use --output <dir> to avoid polluting your workspace.",
            file=sys.stderr,
        )
        return target
    p = Path(output_arg)
    suffix = p.suffix.lower()
    if suffix == ".md":
        print(
            f"  [DEPRECATED] --output={output_arg}: markdown output has been removed; "
            f"writing scan.json into parent dir {p.parent}.",
            file=sys.stderr,
        )
        return p.parent if str(p.parent) else Path(".")
    if suffix == ".json":
        # Treat as explicit file path; caller detects via suffix.
        return p
    return p


def _print_scan_summary(
    inventory: dict,
    anomalies: dict,
    duplicates: list,
    merge_candidates: list,
    dirs_visited: int,
    walk_errors_payload: list,
) -> None:
    print(
        f"  files={inventory['total_files']} "
        f"dupes={len(duplicates)} "
        f"empty_dirs={len(anomalies['empty_folders'])} "
        f"oversized={len(anomalies['oversized'])} "
        f"merge_candidates={len(merge_candidates)}",
        file=sys.stderr,
    )
    print(
        f"  dirs_visited={dirs_visited} "
        f"duplicate_hash_groups={len(duplicates)} "
        f"walk_errors={len(walk_errors_payload)}",
        file=sys.stderr,
    )
    if walk_errors_payload:
        print(
            f"[SUMMARY] Skipped {len(walk_errors_payload)} unreadable paths - check scan.json walk_errors",
            file=sys.stderr,
        )


def _count_dirs_visited(root: Path, excludes: set[str]) -> int:
    dirs_visited = 0
    excludes_lower = {e.lower() for e in excludes}
    for _dp, dns, _fns in os.walk(root, onerror=_walk_error_handler, followlinks=False):
        dns[:] = _filter_dirs(dns, excludes_lower)
        dirs_visited += 1
    return dirs_visited


def _build_payload(
    root: Path,
    inventory: dict,
    anomalies: dict,
    duplicates: list,
    merge_candidates: list,
    walk_errors_payload: list,
) -> dict:
    return {
        "target": str(root),
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inventory": inventory,
        "anomalies": anomalies,
        "duplicates": duplicates,
        "merge_candidates": merge_candidates,
        "walk_errors": walk_errors_payload,
    }


def _write_payload(payload: dict, out_target: Path) -> Path:
    if out_target.suffix.lower() == ".json":
        out_path = out_target
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_target.mkdir(parents=True, exist_ok=True)
        out_path = out_target / "scan.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def scan_directory(
    root: Path,
    large_mb: int,
    excludes: set[str],
    output_arg: str | None,
    fast: bool,
    merge_threshold: float | None,
) -> Path:
    root = root.resolve()
    # Reset walk-error registry so reruns do not accumulate stale entries.
    _walk_errors.clear()
    print(f"scan.py: scanning {root}", file=sys.stderr)

    all_files = _collect_files_fast(root, excludes)
    print(f"  Collected {len(all_files)} files.", file=sys.stderr)

    dirs_visited = _count_dirs_visited(root, excludes)

    inventory = _build_inventory(all_files)
    anomalies = {
        "empty_folders": _find_empty_folders(root, excludes),
        "oversized": _find_oversized(all_files, large_mb),
        "misplaced": [],
    }
    duplicates = _find_duplicates(all_files, fast=fast)

    merge_candidates: list[dict] = []
    if merge_threshold is not None:
        merge_candidates = _find_merge_candidates(root, merge_threshold, excludes)

    walk_errors_payload = [{"path": p, "error": e} for p, e in _walk_errors]
    payload = _build_payload(
        root, inventory, anomalies, duplicates, merge_candidates, walk_errors_payload
    )

    out_target = _resolve_output_dir(output_arg, root)
    out_path = _write_payload(payload, out_target)

    print(f"  Wrote {out_path}", file=sys.stderr)
    _print_scan_summary(
        inventory,
        anomalies,
        duplicates,
        merge_candidates,
        dirs_visited,
        walk_errors_payload,
    )
    return out_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan a directory and emit a unified scan.json."
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target")
    target_group.add_argument("--root")
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (preferred) or explicit .json path. "
        "Legacy .md paths trigger a deprecation warning and use the parent dir.",
    )
    parser.add_argument("--large-mb", type=int, default=50)
    parser.add_argument("--exclude", nargs="*", default=None)
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip expensive hashing on whole workspace (name+size duplicate grouping only).",
    )
    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=None,
        nargs="?",
        const=0.8,
        help="Enable folder merge-candidate analysis with the given similarity "
        "threshold (0.0-1.0). Default when flag is present without a value: 0.8.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-directory [SCAN] lines (errors and summary still printed).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    excludes = set(DEFAULT_EXCLUDES)
    if args.exclude:
        excludes.update(args.exclude)

    global _QUIET
    _QUIET = bool(args.quiet)

    scan_directory(
        root=Path(args.target or args.root),
        large_mb=args.large_mb,
        excludes=excludes,
        output_arg=args.output,
        fast=args.fast,
        merge_threshold=args.merge_threshold,
    )


if __name__ == "__main__":
    main()
