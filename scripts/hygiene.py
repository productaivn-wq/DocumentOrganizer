"""
hygiene.py — Clean-room workspace hygiene and storage reclamation engine for DocumentOrganizer.
Provides safe, declarative ephemeral cache pruning, temp file sanitization, SQLite vacuuming,
multi-project workspace build cache purging, and conversation brain scratch reclamation.

Implements: UC-001 (DocumentOrganizer SSOT)
Traces: FR-ORG-10 (Pre-Purge Asset Ingestion Safeguard), FR-ORG-11 (Ephemeral Sanitization)
Safety: Zero external dependencies (pure Python stdlib), dry-run default, inviolable path locks,
and strict NTFS junction / active conversation immunity.
"""

import argparse
import fnmatch
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "cleaner_rules.json"
)


class WorkspaceHygieneEngine:
    """Clean-room hygiene and SQLite compaction engine."""

    def __init__(
        self,
        root_dir: str,
        rules_path: str | None = None,
        active_conv_id: str | None = None,
    ):
        self.root_dir = Path(root_dir).resolve()
        self.rules_path = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self.active_conv_id = active_conv_id or os.environ.get("ACTIVE_CONVERSATION_ID")
        self.rules = self._load_rules()
        self.inviolable_paths = set(self.rules.get("inviolable_paths", []))
        self.inviolable_patterns = self.rules.get("inviolable_patterns", [])

    def _load_rules(self) -> dict[str, Any]:
        if self.rules_path.exists():
            try:
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(
                    f"[WARN] Failed loading cleaner_rules.json ({e}), using default fallback.",
                    flush=True,
                )
        return {
            "inviolable_paths": [
                "NTUSER.DAT",
                ".ssh",
                ".system_generated",
                ".config",
                ".gitconfig",
            ],
            "inviolable_patterns": [
                "*.git*",
                "SKILL.md",
                "AGENTS.md",
                "CLAUDE.md",
                "README.md",
                "hot.md",
                "log.md",
                "task.md",
                "walkthrough.md",
                "implementation_plan.md",
                "transcript*.jsonl",
                "manifest.json",
            ],
            "recipes": {},
        }

    def is_inviolable(self, target_path: Path) -> bool:
        """Enforces deterministic protection over critical files, configs, repos, and active conversations."""
        # 1. Active conversation immunity
        if self.active_conv_id and self.active_conv_id in target_path.parts:
            return True

        norm_str = str(target_path).replace("\\", "/").lower()
        parts = [p.lower() for p in target_path.parts]

        # 2. Inviolable path subpath checks
        for inv in self.inviolable_paths:
            inv_norm = inv.replace("\\", "/").lower()
            if "/" in inv_norm:
                if inv_norm in norm_str:
                    return True
            else:
                if inv_norm in parts:
                    return True

        # 3. Filename / pattern check
        name_lower = target_path.name.lower()
        for pat in self.inviolable_patterns:
            if fnmatch.fnmatch(name_lower, pat.lower()):
                return True

        # 4. Never touch git internals
        if ".git" in parts:
            return True

        # 5. Never touch system generated transcripts or .system_generated/logs/
        if "transcript" in name_lower or (
            ".system_generated" in parts and "logs" in parts
        ):
            return True

        return False

    def purge_directory(
        self, target_dir: Path, dry_run: bool = True
    ) -> tuple[int, int]:
        """Recursively removes a directory if safe, returning (reclaimed_bytes, files_count).
        Correctly handles Windows NTFS junctions / directory symlinks without recursing into targets.
        """
        if self.is_inviolable(target_dir):
            return 0, 0
        if not target_dir.exists():
            return 0, 0

        # Safe junction / symlink handling: unlink link without recursing into target!
        if target_dir.is_symlink() or os.path.islink(str(target_dir)):
            try:
                if not dry_run:
                    os.rmdir(str(target_dir))
                return 0, 1
            except Exception:
                return 0, 0

        total_bytes = 0
        file_count = 0

        for root, dirs, files in os.walk(str(target_dir), topdown=False):
            for f in files:
                fp = Path(root) / f
                if self.is_inviolable(fp):
                    continue
                try:
                    sz = fp.stat().st_size
                    if not dry_run:
                        fp.unlink(missing_ok=True)
                    total_bytes += sz
                    file_count += 1
                except Exception:
                    pass

            for d in dirs:
                dp = Path(root) / d
                if not dry_run:
                    try:
                        if dp.is_symlink() or os.path.islink(str(dp)):
                            os.rmdir(str(dp))
                        else:
                            dp.rmdir()
                    except Exception:
                        pass

        if not dry_run:
            try:
                target_dir.rmdir()
            except Exception:
                pass

        return total_bytes, file_count

    def purge_file(self, target_file: Path, dry_run: bool = True) -> int:
        """Safely removes a single file, returning reclaimed bytes."""
        if self.is_inviolable(target_file):
            return 0
        if not target_file.exists() or not (
            target_file.is_file() or target_file.is_symlink()
        ):
            return 0

        try:
            sz = target_file.stat().st_size
            if not dry_run:
                target_file.unlink(missing_ok=True)
            return sz
        except Exception:
            return 0

    def vacuum_sqlite(self, db_path: Path, dry_run: bool = True) -> int:
        """Performs SQLite database compaction and WAL vacuuming."""
        if self.is_inviolable(db_path) or not db_path.is_file():
            return 0

        wal_path = db_path.with_name(db_path.name + "-wal")
        before_sz = db_path.stat().st_size
        if wal_path.exists():
            before_sz += wal_path.stat().st_size

        if dry_run:
            return 0

        try:
            conn = sqlite3.connect(str(db_path), timeout=3.0)
            conn.execute("VACUUM")
            conn.close()

            after_sz = db_path.stat().st_size
            if wal_path.exists():
                after_sz += wal_path.stat().st_size

            return max(0, before_sz - after_sz)
        except Exception:
            return 0

    def clean_target_recipe(
        self, recipe_name: str, dry_run: bool = True
    ) -> dict[str, Any]:
        """Executes a named recipe from cleaner_rules.json."""
        recipe = self.rules.get("recipes", {}).get(recipe_name, {})
        if not recipe:
            return {
                "recipe": recipe_name,
                "reclaimed_bytes": 0,
                "files_count": 0,
                "status": "unknown_recipe",
            }

        reclaimed_bytes = 0
        files_count = 0
        dirs_scanned = 0

        # Process directories
        for dir_target in recipe.get("directories", []):
            expanded = os.path.expandvars(dir_target)
            p = (
                Path(expanded)
                if Path(expanded).is_absolute()
                else self.root_dir / expanded
            )
            if p.exists() and p.is_dir():
                dirs_scanned += 1
                b, cnt = self.purge_directory(p, dry_run=dry_run)
                reclaimed_bytes += b
                files_count += cnt

        # Process glob_directories (e.g. %LOCALAPPDATA%/Temp/pytest-of-*)
        import glob as _glob

        for glob_target in recipe.get("glob_directories", []):
            expanded = os.path.expandvars(glob_target)
            for matched in _glob.glob(expanded):
                mp = Path(matched)
                if mp.exists() and mp.is_dir():
                    dirs_scanned += 1
                    b, cnt = self.purge_directory(mp, dry_run=dry_run)
                    reclaimed_bytes += b
                    files_count += cnt

        # Process file patterns
        patterns = recipe.get("file_patterns", [])
        if patterns:
            for root, dirs, files in os.walk(str(self.root_dir)):
                dirs[:] = [d for d in dirs if not self.is_inviolable(Path(root) / d)]
                for f in files:
                    fp = Path(root) / f
                    for pat in patterns:
                        if fnmatch.fnmatch(f.lower(), pat.lower()):
                            if (
                                recipe_name == "sqlite"
                                and recipe.get("action") == "vacuum"
                            ):
                                b = self.vacuum_sqlite(fp, dry_run=dry_run)
                                reclaimed_bytes += b
                                files_count += 1
                            else:
                                b = self.purge_file(fp, dry_run=dry_run)
                                if b > 0:
                                    reclaimed_bytes += b
                                    files_count += 1
                            break

        return {
            "recipe": recipe_name,
            "reclaimed_bytes": reclaimed_bytes,
            "reclaimed_mb": round(reclaimed_bytes / (1024 * 1024), 2),
            "files_count": files_count,
            "dirs_scanned": dirs_scanned,
            "dry_run": dry_run,
        }

    def clean_conversation_scratch(
        self,
        brain_root: Path | None = None,
        dry_run: bool = True,
        max_age_days: int = 0,
    ) -> dict[str, Any]:
        """Scans all conversation brain directories, purging disposable scratch while
        strictly preserving active sessions, transcripts, and deliverable artifacts.
        """
        root = brain_root or Path(os.environ.get("AGENT_SESSIONS_ROOT", str(Path.home() / ".cache" / "document-organizer" / "sessions")))
        if not root.exists():
            return {
                "status": "brain_not_found",
                "reclaimed_bytes": 0,
                "reclaimed_mb": 0,
                "files_count": 0,
            }

        recipe = self.rules.get("recipes", {}).get("conversation_scratch", {})
        target_subdirs = set(recipe.get("target_subdirs", []))
        file_patterns = recipe.get(
            "file_patterns",
            ["plan_*.json", "extracted_*.json", "slice_*.json", "*.tmp"],
        )

        total_bytes = 0
        total_files = 0
        convs_cleaned = 0
        now = time.time()
        age_limit = max_age_days * 86400

        print(
            f"[START] Conversation Brain Scratch Hygiene | Active Conv Immune: {self.active_conv_id}",
            flush=True,
        )

        for entry in os.scandir(str(root)):
            if not entry.is_dir():
                continue
            conv_id = entry.name

            # STRICT IMMUNITY: Skip active session
            if self.active_conv_id and conv_id.lower() == self.active_conv_id.lower():
                continue

            conv_reclaimed = 0
            conv_files = 0
            conv_path = Path(entry.path)

            # 0a. Zero-byte log truncation on closed .system_generated/tasks/*.log
            tasks_log_dir = conv_path / ".system_generated" / "tasks"
            if tasks_log_dir.exists() and tasks_log_dir.is_dir():
                for lf in tasks_log_dir.glob("*.log"):
                    try:
                        sz = lf.stat().st_size
                        if sz > 0:
                            if not dry_run:
                                with open(
                                    lf, "r+", encoding="utf-8", errors="ignore"
                                ) as f:
                                    f.truncate(0)
                            conv_reclaimed += sz
                            conv_files += 1
                    except Exception:
                        pass

            # 0b. Purge closed conversation .tempmediaStorage
            temp_media_dir = conv_path / ".tempmediaStorage"
            if temp_media_dir.exists() and temp_media_dir.is_dir():
                b, f_cnt = self.purge_directory(temp_media_dir, dry_run=dry_run)
                conv_reclaimed += b
                conv_files += f_cnt

            scratch_path = conv_path / "scratch"
            if not scratch_path.exists() or not scratch_path.is_dir():
                if conv_files > 0:
                    convs_cleaned += 1
                    total_bytes += conv_reclaimed
                    total_files += conv_files
                continue

            # Optional TTL filter
            if max_age_days > 0:
                try:
                    mtime = scratch_path.stat().st_mtime
                    if now - mtime < age_limit:
                        continue
                except OSError:
                    pass

            # 1. Clean designated disposable subdirectories
            for sub_entry in os.scandir(str(scratch_path)):
                sub_name = sub_entry.name.lower()
                is_target = any(
                    fnmatch.fnmatch(sub_name, pat.lower()) for pat in target_subdirs
                )

                if (
                    sub_entry.is_dir()
                    or sub_entry.is_symlink()
                    or os.path.islink(sub_entry.path)
                ):
                    if is_target or sub_name in ["__pycache__"]:
                        b, f_cnt = self.purge_directory(
                            Path(sub_entry.path), dry_run=dry_run
                        )
                        conv_reclaimed += b
                        conv_files += f_cnt
                elif sub_entry.is_file():
                    if any(
                        fnmatch.fnmatch(sub_name, pat.lower()) for pat in file_patterns
                    ) or sub_name.endswith(".tmp"):
                        b = self.purge_file(Path(sub_entry.path), dry_run=dry_run)
                        conv_reclaimed += b
                        conv_files += 1

            # 2. If scratch directory is now empty, remove it
            if not dry_run and scratch_path.exists():
                try:
                    if not any(scratch_path.iterdir()):
                        scratch_path.rmdir()
                except OSError:
                    pass

            if conv_files > 0:
                convs_cleaned += 1
                total_bytes += conv_reclaimed
                total_files += conv_files

        total_mb = round(total_bytes / (1024 * 1024), 2)
        print(
            f"[CONVERSATION BRAIN HYGIENE] Cleaned {convs_cleaned} sessions | Reclaimed: {total_mb:.2f} MB ({total_files} files)",
            flush=True,
        )

        return {
            "reclaimed_bytes": total_bytes,
            "reclaimed_mb": total_mb,
            "files_count": total_files,
            "conversations_cleaned": convs_cleaned,
            "dry_run": dry_run,
        }

    def clean_project_workspace_caches(
        self, projects_root: Path | None = None, dry_run: bool = True
    ) -> dict[str, Any]:
        """Scans all monorepo project directories, purging build/test caches and loose root debris."""
        root = projects_root or Path(os.environ.get("WORKSPACE_PROJECTS_ROOT", str(Path.home() / "Projects")))
        if not root.exists():
            return {
                "status": "projects_root_not_found",
                "reclaimed_bytes": 0,
                "reclaimed_mb": 0,
                "files_count": 0,
            }

        cache_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            ".tox",
        }
        cache_files = {"*.pyc", "*.pyo", "*.coverage", ".coverage"}
        stray_root_files = {"scan.json", "find_logging.txt", "find_scoring.txt"}

        total_bytes = 0
        total_files = 0
        projects_cleaned = 0

        print(f"[START] Multi-Project Workspace Cache Hygiene on {root}", flush=True)

        for proj_entry in os.scandir(str(root)):
            if not proj_entry.is_dir():
                # Check loose files in root of 01_PROJECTS itself
                if proj_entry.is_file() and proj_entry.name in stray_root_files:
                    b = self.purge_file(Path(proj_entry.path), dry_run=dry_run)
                    total_bytes += b
                    total_files += 1
                continue

            proj_path = Path(proj_entry.path)
            proj_bytes = 0
            proj_file_count = 0

            # 1. Clean root stray debris in each project
            for item in proj_path.iterdir():
                if item.is_file() and item.name in stray_root_files:
                    b = self.purge_file(item, dry_run=dry_run)
                    proj_bytes += b
                    proj_file_count += 1

            # 2. Traverse project for cache dirs and file patterns
            for r, dirs, files in os.walk(str(proj_path), topdown=False):
                if self.is_inviolable(Path(r)):
                    continue

                for f in files:
                    fp = Path(r) / f
                    if any(
                        fnmatch.fnmatch(f.lower(), pat.lower()) for pat in cache_files
                    ):
                        b = self.purge_file(fp, dry_run=dry_run)
                        proj_bytes += b
                        proj_file_count += 1

                for d in list(dirs):
                    if d in cache_dirs:
                        dp = Path(r) / d
                        b, cnt = self.purge_directory(dp, dry_run=dry_run)
                        proj_bytes += b
                        proj_file_count += cnt

            if proj_file_count > 0:
                projects_cleaned += 1
                total_bytes += proj_bytes
                total_files += proj_file_count

        total_mb = round(total_bytes / (1024 * 1024), 2)
        print(
            f"[PROJECT WORKSPACE HYGIENE] Cleaned {projects_cleaned} projects | Reclaimed: {total_mb:.2f} MB ({total_files} files)",
            flush=True,
        )

        return {
            "reclaimed_bytes": total_bytes,
            "reclaimed_mb": total_mb,
            "files_count": total_files,
            "projects_cleaned": projects_cleaned,
            "dry_run": dry_run,
        }

    @staticmethod
    def verify_skills_junction_integrity(
        canonical_dir: Path | str | None = None,
        candidate_dirs: list[Path | str] | None = None,
    ) -> dict[str, Any]:
        """Single-Store Pattern: Verifies skill link directories resolve to a canonical SSOT directory."""
        base_ssot = canonical_dir or os.environ.get(
            "SKILLS_SSOT_DIR", str(Path.home() / ".local" / "share" / "agent-skills")
        )
        canonical = os.path.normcase(os.path.realpath(str(base_ssot)))
        candidates = (
            [Path(p) for p in candidate_dirs]
            if candidate_dirs is not None
            else []
        )
        checked = {}
        passed = True
        for candidate in candidates:
            if candidate.exists():
                resolved = os.path.normcase(os.path.realpath(str(candidate)))
                is_ok = resolved == canonical
                checked[str(candidate)] = {
                    "resolved": resolved,
                    "is_junction_ok": is_ok,
                }
                if not is_ok:
                    passed = False
        return {"passed": passed, "canonical": canonical, "checked": checked}

    def run_hygiene_sweep(
        self,
        targets: list[str] | None = None,
        dry_run: bool = True,
        clean_brains: bool = False,
        clean_projects: bool = False,
    ) -> dict[str, Any]:
        """Runs hygiene sweep across specified recipes, with optional brain scratch and project caches."""
        mode = "DRY-RUN PREVIEW" if dry_run else "PHYSICAL PURGE"
        print(
            f"[START] DocumentOrganizer Hygiene Sweep ({mode}) on {self.root_dir}",
            flush=True,
        )

        if not targets:
            targets = [
                "python",
                "browser",
                "editor",
                "temp",
                "pytest_system_temp",
                "agent_worktrees",
                "raw_ingestion_staging",
                "crashdumps",
                "sqlite",
            ]

        results = []
        total_bytes = 0
        total_files = 0

        for target in targets:
            res = self.clean_target_recipe(target, dry_run=dry_run)
            results.append(res)
            total_bytes += res["reclaimed_bytes"]
            total_files += res["files_count"]
            print(
                f"  [{target:<12}] Reclaimed: {res['reclaimed_mb']:>8.2f} MB ({res['files_count']:>5} files)",
                flush=True,
            )

        # Extended Scope: Multi-Project Workspace Caches
        if clean_projects:
            proj_res = self.clean_project_workspace_caches(dry_run=dry_run)
            results.append({"recipe": "project_build_caches", **proj_res})
            total_bytes += proj_res["reclaimed_bytes"]
            total_files += proj_res["files_count"]

        # Extended Scope: Conversation Brain Scratch
        if clean_brains:
            brain_res = self.clean_conversation_scratch(dry_run=dry_run)
            results.append({"recipe": "conversation_scratch", **brain_res})
            total_bytes += brain_res["reclaimed_bytes"]
            total_files += brain_res["files_count"]

        total_mb = round(total_bytes / (1024 * 1024), 2)
        print(
            f"\n[HYGIENE SUMMARY] Mode: {mode} | Total Reclaimed: {total_mb:.2f} MB ({total_files} files)",
            flush=True,
        )

        return {
            "root": str(self.root_dir),
            "dry_run": dry_run,
            "total_bytes": total_bytes,
            "total_mb": total_mb,
            "total_files": total_files,
            "recipes": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DocumentOrganizer Hygiene Engine")
    parser.add_argument("--root", default=os.getcwd(), help="Target root directory")
    parser.add_argument(
        "--targets", default=None, help="Comma-separated recipe targets"
    )
    parser.add_argument(
        "--clean-brains",
        action="store_true",
        help="Reclaim historical conversation scratch",
    )
    parser.add_argument(
        "--clean-projects", action="store_true", help="Purge multi-project build caches"
    )
    parser.add_argument(
        "--active-conv", default=None, help="Active conversation ID to strictly protect"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute physical purge (default is dry-run)",
    )
    args = parser.parse_args()

    target_list = [t.strip() for t in args.targets.split(",")] if args.targets else None
    engine = WorkspaceHygieneEngine(args.root, active_conv_id=args.active_conv)
    engine.run_hygiene_sweep(
        targets=target_list,
        dry_run=not args.execute,
        clean_brains=args.clean_brains,
        clean_projects=args.clean_projects,
    )
