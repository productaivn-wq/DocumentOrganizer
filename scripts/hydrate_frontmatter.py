"""
DocumentOrganizer YAML Frontmatter Standardization Engine.

Scans Markdown specifications across projects and skills, injecting or
enriching structured YAML frontmatter (id, title, status, version, tags)
to enable O(1) attribute indexing and eradicate unstructured documentation debt.

Implements: UC-003
Traces: FR-001
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any


def parse_args():
    parser = argparse.ArgumentParser(
        description="Standardize Markdown files with canonical YAML frontmatter."
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target file or directory path containing Markdown files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate frontmatter injection without writing to disk.",
    )
    return parser.parse_args()


class FrontmatterHydrator:
    """Standardizes YAML frontmatter across documentation files."""

    def __init__(self):
        self.processed_count: int = 0

    @staticmethod
    def extract_title_and_id(filepath: Path, content: str) -> tuple[str, str]:
        stem = filepath.stem
        # Try finding JD or REF identifier in stem (e.g. 10.REF.01 or PP.SSS.TT or UC-001)
        id_match = re.search(
            r"(\d{2}\.[A-Z]{3,4}\.\d{2,3}|\d{2}\.\d{3}\.\d{2}|UC-\d{3}|FR-\d{3}|TC-[A-Z0-9_-]+)",
            stem,
            re.IGNORECASE,
        )
        doc_id = id_match.group(1).upper() if id_match else stem

        # Find first Markdown H1 title
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Clean title from markdown links or formatting
            title = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", title)
            title = title.replace("`", "").replace("*", "")
        else:
            # Fallback to cleaned stem
            clean_stem = re.sub(r"^\d{2}\.[A-Z0-9._-]+\s*[-_]\s*", "", stem)
            title = clean_stem.replace("_", " ").replace("-", " ").title()

        return doc_id, title

    @staticmethod
    def derive_tags(filepath: Path) -> list[str]:
        parts = [p.lower() for p in filepath.parts]
        tags = set()
        for p in parts:
            if p in (
                "docs",
                "reference",
                "30_reference",
                "10_active_timebound",
                "20_active_continuous",
            ):
                tags.add(p.replace("30_", "").replace("10_", "").replace("20_", ""))
            elif p.startswith("skills"):
                tags.add("skill")
            elif p.startswith("projects") or "01_projects" in p:
                tags.add("project")

        # Filename cues
        name_lower = filepath.name.lower()
        for kw in [
            "spec",
            "guide",
            "architecture",
            "test",
            "plan",
            "report",
            "workflow",
            "matrix",
        ]:
            if kw in name_lower:
                tags.add(kw)

        if not tags:
            tags.add("documentation")
        return sorted(list(tags))

    def hydrate_content(
        self, filepath: Path, content: str
    ) -> tuple[str, dict[str, Any]]:
        # Check if already has frontmatter
        if content.startswith("---\n"):
            end_fm = content.find("\n---\n", 4)
            if end_fm != -1:
                # Already has frontmatter, verify essentials
                fm_block = content[4:end_fm]
                has_id = bool(re.search(r"^id:", fm_block, re.MULTILINE))
                has_title = bool(re.search(r"^title:", fm_block, re.MULTILINE))
                has_status = bool(re.search(r"^status:", fm_block, re.MULTILINE))

                if has_id and has_title and has_status:
                    return content, {"updated": False, "reason": "already_compliant"}

        doc_id, title = self.extract_title_and_id(filepath, content)
        tags = self.derive_tags(filepath)
        tags_str = ", ".join(tags)

        # Build clean frontmatter
        fm = [
            "---",
            f"id: {doc_id}",
            f'title: "{title}"',
            "status: active",
            "version: 1.0.0",
            f"tags: [{tags_str}]",
            "last_verified: 2026-09-08",
            "---",
            "",
        ]
        new_fm_str = "\n".join(fm)

        # If it had malformed frontmatter, strip it
        if content.startswith("---\n"):
            end_fm = content.find("\n---\n", 4)
            if end_fm != -1:
                body = content[end_fm + 5 :]
            else:
                body = content
        else:
            body = content

        hydrated = new_fm_str + body.lstrip("\n")
        return hydrated, {"updated": True, "doc_id": doc_id, "title": title}

    def hydrate_file(self, filepath: Path, dry_run: bool = False) -> dict[str, Any]:
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            return {"error": str(e), "path": str(filepath)}

        hydrated, stats = self.hydrate_content(filepath, content)
        stats["path"] = str(filepath)

        if stats.get("updated") and not dry_run:
            filepath.write_text(hydrated, encoding="utf-8")
        return stats


def main():
    args = parse_args()
    if not args.target:
        print("Please provide --target directory or file.")
        sys.exit(1)

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"Target does not exist: {target}")
        sys.exit(1)

    hydrator = FrontmatterHydrator()
    md_files = []
    if target.is_file() and target.suffix.lower() == ".md":
        md_files.append(target)
    elif target.is_dir():
        for root, _, files in os.walk(target):
            if any(
                x in root for x in [".git", ".venv", "node_modules", ".pytest_cache"]
            ):
                continue
            for f in files:
                if f.lower().endswith(".md"):
                    md_files.append(Path(root) / f)

    print(
        "================================================================================"
    )
    print("      DOCUMENT ORGANIZER YAML FRONTMATTER HYDRATOR (OPT-APEX)")
    print(
        "================================================================================"
    )
    print(f"Target: {target}")
    print(f"Found Markdown Files: {len(md_files)}")
    print(f"Dry run: {args.dry_run}")
    print(
        "--------------------------------------------------------------------------------"
    )

    total_updated = 0
    total_compliant = 0

    for f in md_files:
        res = hydrator.hydrate_file(f, dry_run=args.dry_run)
        if res.get("updated"):
            total_updated += 1
            print(f"  [FRONTMATTER ADDED] {f.name:<35} | ID: {res.get('doc_id')}")
        else:
            total_compliant += 1

    print(
        "================================================================================"
    )
    print(f"Total Files Inspected : {len(md_files)}")
    print(f"Frontmatter Added     : {total_updated}")
    print(f"Already Compliant     : {total_compliant}")
    print(
        "================================================================================"
    )


if __name__ == "__main__":
    main()
