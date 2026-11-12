#!/usr/bin/env python3
"""
visualize.py - Generate a Mermaid.js mindmap of a directory structure.
Part of DocumentOrganizer v2.0.
"""

import argparse
import sys
from pathlib import Path

# Folders to always exclude from the visual tree
EXCLUDE_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    "$RECYCLE.BIN",
    "venv",
    ".venv",
    ".agent",
    ".vscode",
}


def generate_mermaid_mindmap(root: Path, max_depth: int = 4) -> str:
    lines = ["mindmap", f"  root(({root.name or root}))"]

    def _walk(current_path: Path, depth: int):
        if depth > max_depth:
            return

        try:
            # Sort: directories first, then files
            items = sorted(
                current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except (PermissionError, OSError):
            return

        indent = "  " * (depth + 1)
        for item in items:
            if item.name in EXCLUDE_DIRS:
                continue

            if item.is_dir():
                lines.append(f"{indent}{item.name}")
                _walk(item, depth + 1)
            elif (
                depth < max_depth
            ):  # Only show files at shallow depths to keep diagram clean
                lines.append(f"{indent}{item.name}")

    _walk(root, 1)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Mermaid.js mindmap of a directory"
    )
    parser.add_argument("--target", required=True, help="Directory to visualize")
    parser.add_argument(
        "--output", default="visual_tree.md", help="Output Markdown file"
    )
    parser.add_argument(
        "--max-depth", type=int, default=3, help="Max depth for visualization"
    )

    args = parser.parse_args()
    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"ERROR: {target} is not a directory")
        sys.exit(1)

    print(f"Generating visualization for {target}...")
    mindmap = generate_mermaid_mindmap(target, args.max_depth)

    output_content = (
        f"# Directory Visualization: {target.name}\n\n```mermaid\n{mindmap}\n```\n"
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Visualization saved to {args.output}")


if __name__ == "__main__":
    main()
