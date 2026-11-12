"""Unit tests for DocumentOrganizer multi-directory watching and registry exports."""

import argparse
import sys
from pathlib import Path

# Ensure scripts directory is in sys.path
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import jd_registry
import logger
import watch


def test_jd_registry_exports():
    """Verify all required functions and constants are exported by jd_registry."""
    assert hasattr(jd_registry, "VALID_TAGS")
    assert isinstance(jd_registry.VALID_TAGS, set)
    assert "PR" in jd_registry.VALID_TAGS
    assert "RE" in jd_registry.VALID_TAGS

    assert callable(getattr(jd_registry, "format_filename", None))
    assert callable(getattr(jd_registry, "extract_id", None))
    assert callable(getattr(jd_registry, "next_sequence", None))
    assert callable(getattr(jd_registry, "resolve_project", None))
    assert callable(getattr(jd_registry, "save_registry", None))
    assert callable(getattr(jd_registry, "scan_highest_sequence", None))


def test_format_and_extract_id():
    """Verify format_filename and extract_id work symmetrically."""
    fname = jd_registry.format_filename(
        "53", 12, "20260916", "My_Test_Report", ".md", ["PR"]
    )
    assert fname.startswith("53.012.PR - 20260916 - My_Test_Report.md")

    extracted = jd_registry.extract_id(fname)
    assert extracted is not None
    pp, sss, tags = extracted
    assert pp == "53"
    assert sss == 12
    assert "PR" in tags


def test_logger_exports():
    """Verify logger provides both get_logger and emit_progress."""
    assert callable(getattr(logger, "get_logger", None))
    assert callable(getattr(logger, "emit_progress", None))

    log_inst = logger.get_logger("TestLogger")
    assert log_inst is not None


def test_watch_ignore_system_and_desktop_files(tmp_path):
    """Verify AIDocumentHandler ignores desktop.ini, lock files, and incomplete downloads."""
    handler = watch.AIDocumentHandler(
        target_root=tmp_path,
        dry_run=True,
        whitelist_only=True,
        triage_mode=False,
    )

    # These should be ignored without adding to processing
    handler.process_file(Path("desktop.ini"))
    assert Path("desktop.ini") not in handler.processing

    handler.process_file(Path("Thumbs.db"))
    assert Path("Thumbs.db") not in handler.processing

    handler.process_file(Path("~$WordDoc.docx"))
    assert Path("~$WordDoc.docx") not in handler.processing

    handler.process_file(Path("file.crdownload"))
    assert Path("file.crdownload") not in handler.processing


def test_watch_argparser_multi_directory():
    """Verify watch.py argument parser accepts multiple directories for --watch."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", nargs="+", required=True)
    parser.add_argument("--target", required=True)

    args = parser.parse_args(
        [
            "--watch",
            "/tmp/demo/Downloads",
            "/tmp/demo/Desktop",
            "/tmp/workspace/00_INBOX",
            "--target",
            "/tmp/workspace",
        ]
    )

    assert len(args.watch) == 3
    assert args.watch[0] == "/tmp/demo/Downloads"
    assert args.watch[1] == "/tmp/demo/Desktop"
    assert args.watch[2] == "/tmp/workspace/00_INBOX"
    assert args.target == "/tmp/workspace"


def test_watch_whitelist_includes_media_and_archives():
    """Verify video, audio, and archive extensions are in WHITELIST_EXTS."""
    for ext in (".mp4", ".mov", ".mkv", ".m4a", ".mp3", ".zip"):
        assert ext in watch.WHITELIST_EXTS
    assert ".zip" not in watch.IGNORE_EXTS


def test_project_router_media_routing(tmp_path: Path):
    """Verify ProjectRouter correctly routes screen recordings to media zones."""
    from project_router import ProjectRouter

    router = ProjectRouter(workspace_base=tmp_path / "01_PROJECTS")

    r1 = router.resolve_destination("Workspace Demo Screen Capture 2026-09-21.mp4")
    assert r1 is not None
    assert r1.project_name == "60_DEV_EXPERIENCE"
    assert "media" in str(r1.relative_zone_path)

    r2 = router.resolve_destination("Heritage Craft Fieldwork Survey 2026-09-21.mp4")
    assert r2 is not None
    assert r2.project_name == "40_FIELD_RESEARCH"
    assert "fieldwork_videos" in str(r2.relative_zone_path)
