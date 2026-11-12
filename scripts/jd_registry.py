"""Johnny Decimal Registry and Category Resolution for DocumentOrganizer."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class JDCategory:
    area_code: str
    category_code: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)


class JDRegistry:
    """Manages Johnny Decimal categories and resolution logic."""

    def __init__(self, registry_path: Path | str | None = None) -> None:
        self.registry_path = Path(registry_path) if registry_path else None
        self.categories: dict[str, JDCategory] = {}
        if self.registry_path and self.registry_path.exists():
            self.load_registry(self.registry_path)

    def load_registry(self, path: Path) -> None:
        """Load JD definitions from a JSON file."""
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for key, item in data.get("categories", {}).items():
                    self.categories[key] = JDCategory(
                        area_code=item.get("area_code", key[:2]),
                        category_code=item.get("category_code", key),
                        name=item.get("name", ""),
                        description=item.get("description", ""),
                        tags=item.get("tags", []),
                    )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load JD registry from {path}: {exc}"
            ) from exc

    def get_category(self, code: str) -> JDCategory | None:
        """Retrieve category by Johnny Decimal code."""
        return self.categories.get(code)

    def register_category(self, category: JDCategory) -> None:
        """Register or update category entry."""
        self.categories[category.category_code] = category


def discover_projects(projects_root: Path | str) -> dict[str, dict[str, Any]]:
    """Discover monorepo projects by scanning for PP_NAME folders."""
    root = Path(projects_root)
    projects: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return projects
    for p in root.iterdir():
        if p.is_dir():
            parts = p.name.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit():
                pp = parts[0]
                name = parts[1]
                projects[pp] = {
                    "pp": pp,
                    "name": name,
                    "folder": p.name,
                    "path": str(p),
                }
    return projects


def load_registry(
    path: Path | str | None = None, projects_root: Path | str | None = None
) -> dict[str, Any]:
    """Load JD definitions and auto-discover monorepo projects."""
    registry_data: dict[str, Any] = {"categories": {}, "projects": {}}
    if projects_root:
        registry_data["projects"] = discover_projects(projects_root)
    if path:
        p = Path(path)
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    registry_data["categories"] = data.get("categories", {})
                    if "projects" in data:
                        registry_data["projects"].update(data["projects"])
            except Exception:
                pass
    return registry_data


def resolve_project_for_file(
    filepath: str,
    content_summary: str = "",
    registry: dict[str, Any] | None = None,
) -> tuple[str | None, str | None, list[str]]:
    """Resolve project affinity based on filename, content summary, and registry."""
    text = f"{filepath} {content_summary}".lower()
    compact_text = re.sub(r"[\s_-]+", "", text)
    if registry and "projects" in registry:
        for pp, info in registry["projects"].items():
            raw_name = info.get("name", "")
            name = raw_name.lower()
            if not name:
                continue
            compact_name = re.sub(r"[\s_-]+", "", name)
            spaced_name = re.sub(r"[_-]+", " ", name)
            if name in text or spaced_name in text or (len(compact_name) >= 4 and compact_name in compact_text):
                return pp, raw_name, []
    return None, None, []


# ---------------------------------------------------------------------------
# Valid tags, Regex patterns, and Formatting
# ---------------------------------------------------------------------------
VALID_TAGS = {
    "PR",  # Project
    "AR",  # Area
    "RE",  # Resource / Record
    "TR",  # Tracking / Telemetry
    "BK",  # Book / Reference
    "MN",  # Manual / Guide
    "DT",  # Dataset
    "EV",  # Evidence
}

_ID_RE = re.compile(r"^(\d{2})\.(\d{3})\.([A-Z]{2})(?:\.([A-Z]{2}))?")
_ID_RE_LEGACY = re.compile(r"^(\d{2})\.(\d{3})")


def _default_registry_path() -> Path:
    return Path(__file__).resolve().parent.parent / "registry.json"


def save_registry(registry: dict, path: Path | None = None) -> None:
    """Save registry data to JSON file."""
    target_path = Path(path) if path else _default_registry_path()
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def resolve_project(folder_path: Path, registry: dict | None = None) -> str | None:
    """Walk up from a folder to find which project it belongs to."""
    projects = registry.get("projects", {}) if registry else {}
    for part in folder_path.parts:
        match = re.match(r"^(\d{2})_", part)
        if match:
            pp = match.group(1)
            if not projects or pp in projects:
                return pp
    return None


def scan_highest_sequence(project_dir: Path, pp: str) -> int:
    """Scan a project folder (recursively) to find the highest PP.SSS in use."""
    highest = 0
    if not project_dir.exists():
        return highest

    exclude_dirs = {
        ".git",
        "node_modules",
        ".next",
        "dist",
        "build",
        "_archive",
        "_duplicates",
        ".tmp.driveupload",
        "venv",
        ".venv",
    }

    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for name in files:
            m = _ID_RE.match(name)
            if m and m.group(1) == pp:
                seq = int(m.group(2))
                highest = max(highest, seq)
            else:
                m_leg = _ID_RE_LEGACY.match(name)
                if m_leg and m_leg.group(1) == pp:
                    seq = int(m_leg.group(2))
                    highest = max(highest, seq)
    return highest


def next_sequence(registry: dict, pp: str, project_dir: Path | None = None) -> int:
    """Get the next available sequence number for a project."""
    if "sequences" not in registry:
        registry["sequences"] = {}
    if pp not in registry["sequences"]:
        if project_dir and project_dir.exists():
            highest = scan_highest_sequence(project_dir, pp)
        else:
            highest = 0
        registry["sequences"][pp] = highest

    registry["sequences"][pp] += 1
    return registry["sequences"][pp]


def format_id(pp: str, sss: int) -> str:
    """Format a JD_ID: PP.SSS"""
    return f"{pp}.{sss:03d}"


def format_filename(
    pp: str, sss: int, date: str, title: str, ext: str, tags: list[str] | None = None
) -> str:
    """Format the full PARA-Decimal filename.

    Pattern: PP.SSS.TT[.TT] - YYYYMMDD - Semantic_Title.ext
    """
    tags = tags or []
    valid_tags = [t.upper() for t in tags if t.upper() in VALID_TAGS]
    if not valid_tags:
        valid_tags = ["RE"]

    selected_tags = valid_tags[:2]
    tag_str = ".".join(selected_tags)
    jd_id = f"{pp}.{sss:03d}.{tag_str}"

    title = re.sub(r"[\s]+", "_", title)
    title = re.sub(r"[^A-Za-z0-9_-]", "", title)
    title = title.strip("_-") or "Untitled"

    return f"{jd_id} - {date} - {title}{ext}"


def extract_id(filename: str) -> tuple[str, int, list[str]] | None:
    """Extract (PP, SSS, [Tags]) from a filename, or None if no ID found."""
    m = _ID_RE.match(filename)
    if m:
        tags = [m.group(3)]
        if m.group(4):
            tags.append(m.group(4))
        return m.group(1), int(m.group(2)), tags
    m = _ID_RE_LEGACY.match(filename)
    if m:
        return m.group(1), int(m.group(2)), []
    return None


def extract_tag(filename: str) -> list[str]:
    """Extract tags from PP.SSS.TT[.TT] format."""
    m = _ID_RE.match(filename)
    if m:
        tags = [m.group(3)]
        if m.group(4):
            tags.append(m.group(4))
        return tags
    return []
