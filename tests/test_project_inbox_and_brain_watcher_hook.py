"""Unit tests for Project Inboxes Dynamic Discovery & Brain Watcher Lifecycle Hook."""

from __future__ import annotations

from pathlib import Path

import watch
import watch_supervisor

from document_organizer_interceptor import organize_task_and_conversation_files


def test_discover_watch_directories(tmp_path: Path) -> None:
    """Verify discover_watch_directories discovers primary folders and project inboxes portably."""
    work_root = tmp_path / "Workspace"
    (work_root / "00_INBOX").mkdir(parents=True)
    projects_root = work_root / "01_PROJECTS"
    for idx in range(1, 30):
        (projects_root / f"{idx:02d}_PROJ_{idx:02d}" / "00_INBOX").mkdir(parents=True)
    (projects_root / "10_PRODUCT_PLATFORM" / "00_INBOX").mkdir(parents=True, exist_ok=True)
    (projects_root / "20_CLOUD_INFRASTRUCTURE" / "00_INBOX").mkdir(parents=True, exist_ok=True)

    dirs = watch_supervisor.discover_watch_directories(
        work_root=work_root,
        projects_root=projects_root,
    )
    assert isinstance(dirs, list)
    assert len(dirs) >= 30, f"Expected >= 30 inboxes, got {len(dirs)}"
    assert any(d.endswith("00_INBOX") for d in dirs)
    assert any("20_CLOUD_INFRASTRUCTURE" in d and "00_INBOX" in d for d in dirs)
    assert any("10_PRODUCT_PLATFORM" in d and "00_INBOX" in d for d in dirs)


def test_resolve_target_root_for_project_file(tmp_path: Path) -> None:
    """Verify AIDocumentHandler resolves effective target root to enclosing project folder."""
    ws_root = tmp_path / "Workspace"
    proj_inbox = ws_root / "01_PROJECTS" / "10_PRODUCT_PLATFORM" / "00_INBOX"
    proj_inbox.mkdir(parents=True)

    handler = watch.AIDocumentHandler(
        target_root=ws_root,
        dry_run=True,
        whitelist_only=True,
        triage_mode=False,
    )

    proj_file = proj_inbox / "product_spec.pdf"
    resolved = handler._resolve_target_root_for_file(proj_file)
    assert resolved.name == "10_PRODUCT_PLATFORM"
    assert "01_PROJECTS" in resolved.parts

    dl_file = tmp_path / "Downloads" / "generic_guide.pdf"
    resolved_dl = handler._resolve_target_root_for_file(dl_file)
    assert resolved_dl == ws_root


def test_brain_watcher_organize_task_and_conversation_files(tmp_path: Path) -> None:
    """Verify organize_task_and_conversation_files migrates brain scratch files to 40_ARCHIVE/scratch."""
    ws = tmp_path / "mock_project"
    ws.mkdir()
    (ws / "10_ACTIVE_TIMEBOUND").mkdir()
    (ws / "40_ARCHIVE").mkdir()

    brain_root = tmp_path / "brain"
    conv_id = "test-conv-uuid-12345"
    scratch_dir = brain_root / conv_id / "scratch"
    scratch_dir.mkdir(parents=True)

    scratch_file = scratch_dir / "debug_extract.py"
    scratch_file.write_text("print('test scratch')", encoding="utf-8")

    res = organize_task_and_conversation_files(
        workspace_dir=ws,
        conversation_id=conv_id,
        task_id="TASK-TEST-001",
        brain_root=brain_root,
    )

    assert res.get("success") is True
    assert len(res.get("migrated_scratch_files", [])) == 1

    archived = ws / "40_ARCHIVE" / "scratch" / "debug_extract.py"
    assert archived.exists()
    assert archived.read_text(encoding="utf-8") == "print('test scratch')"
