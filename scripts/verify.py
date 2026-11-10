#!/usr/bin/env python3
"""Cross-platform directory structure verification for DocumentOrganizer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _resolve_path(root: Path, p: str) -> Path:
    """Resolve a path, treating it as relative to root unless absolute."""
    path = Path(p)
    return path if path.is_absolute() else root / p


def verify(root: Path, check_paths: list[str] | None = None) -> bool:
    """Verify a directory structure and expected paths after reorganization."""
    root = root.resolve()

    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return False

    file_count = sum(1 for f in root.rglob("*") if f.is_file())
    print(f"File count: {file_count}")

    resolved = [_resolve_path(root, p) for p in (check_paths or [])]
    missing = [fp for fp in resolved if not fp.exists()]
    for fp in resolved:
        status = "MISSING" if fp in missing else "OK"
        print(f"  [{status}] {fp}")

    return not missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify directory structure after reorganization"
    )
    parser.add_argument("--root", required=True, help="Root directory to verify")
    parser.add_argument(
        "--check-paths",
        nargs="*",
        default=None,
        help="Paths to check (relative to root or absolute)",
    )

    args = parser.parse_args()
    if verify(Path(args.root), args.check_paths):
        print("\nVerification passed.")
    else:
        print("\nVerification FAILED — missing paths detected.")
        sys.exit(1)


if __name__ == "__main__":
    main()
