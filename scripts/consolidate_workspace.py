import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.consolidate import consolidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_files(root: Path, extensions: set[str] | None = None) -> list[Path]:
    """Find files in a directory tree with optional extension filtering.

    Args:
        root: Root directory to search.
        extensions: Set of file extensions to include (e.g., {'.txt', '.md'}).
                   If None, includes all files.

    Returns:
        List of file paths matching the criteria.
    """
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file():
            if extensions is None or p.suffix.lower() in extensions:
                files.append(p)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Consolidate workspace files")
    parser.add_argument("workspace", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument(
        "--extensions",
        nargs="*",
        help="File extensions to include (e.g., .txt .md). If not specified, includes all files.",
    )
    parser.add_argument(
        "--encoding", default="utf-8", help="File encoding (default: utf-8)"
    )
    args = parser.parse_args()

    ext_set: set[str] | None = set(args.extensions) if args.extensions else None
    files = find_files(args.workspace, extensions=ext_set)
    consolidate(files, args.output, encoding=args.encoding)


if __name__ == "__main__":
    main()
