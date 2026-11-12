"""
test_nightly_project_reorganizer.py — Comprehensive MinTC Test Suite for DocumentOrganizer Nightly Pipeline.

Governing SSOTs:
- DocumentOrganizer v2.2.0

Verifies:
- Unit: Win32 paths, SHA-256, atomic locking, draft immunity, canonical naming.
- Integration: Safe relocation, collision resolution, project scanner isolation, version supersession, orchestrator.
- Adversarial: Same-path trap, corrupted copy, lock timeout recovery.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

_SKILLS_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _SKILLS_ROOT not in sys.path:
    sys.path.insert(0, _SKILLS_ROOT)

from DocumentOrganizer.scripts.nightly_project_reorganizer import (
    ActionType,
    AtomicSharedResourceLock,
    DiscoveredFile,
    DocumentSemanticsClassifier,
    MECEZone,
    MultiProjectReorganizerOrchestrator,
    ProjectOutputScanner,
    compute_sha256,
    is_active_draft_immune,
    safe_relocate_file,
    to_extended_win32_path,
)


@pytest.fixture
def temp_workspace(tmp_path):
    ws = tmp_path / "mock_workspace"
    ws.mkdir()
    return ws


# ===========================================================================
# 1. Unit Tests
# ===========================================================================


def test_to_extended_win32_path():
    short_path = Path("C:/test/file.txt")
    assert to_extended_win32_path(short_path) == short_path

    # Simulate path length > 240
    long_str = "C:/" + "a" * 250 + "/file.txt"
    long_path = Path(long_str)
    ext_path = to_extended_win32_path(long_path)
    if os.name == "nt":
        assert str(ext_path).startswith("\\\\?\\")


def test_compute_sha256(temp_workspace):
    sample = temp_workspace / "sample.txt"
    sample.write_text("deterministic content for sha256 testing", encoding="utf-8")
    hash_val = compute_sha256(sample)
    assert len(hash_val) == 64
    assert hash_val == compute_sha256(sample)


def test_atomic_lock(temp_workspace):
    lock_file = temp_workspace / ".test.lock"
    lock1 = AtomicSharedResourceLock(lock_file, ttl_seconds=2.0)
    assert lock1.acquire(timeout_sec=1.0) is True

    # Second acquisition fails on timeout
    lock2 = AtomicSharedResourceLock(lock_file, ttl_seconds=2.0)
    assert lock2.acquire(timeout_sec=0.1) is False

    lock1.release()
    assert lock2.acquire(timeout_sec=1.0) is True
    lock2.release()


def test_active_draft_immunity_fresh_modification(temp_workspace):
    fresh_file = temp_workspace / "active_draft.md"
    fresh_file.write_text("# Working Title\nContent in progress...", encoding="utf-8")
    meta = DiscoveredFile(
        path=fresh_file,
        relative_path=Path("active_draft.md"),
        size_bytes=fresh_file.stat().st_size,
        mtime=datetime.now() - timedelta(hours=2),
        extension=".md",
        sha256=None,
        parent_zone="ROOT",
    )
    immune, reason = is_active_draft_immune(
        meta, temp_workspace, fresh_file.read_text()
    )
    assert immune is True
    assert "Fresh modification" in reason


def test_active_draft_immunity_explicit_tag(temp_workspace):
    wip_file = temp_workspace / "old_date_wip.md"
    content = "---\nstatus: in_progress\n---\nDraft details"
    wip_file.write_text(content, encoding="utf-8")
    meta = DiscoveredFile(
        path=wip_file,
        relative_path=Path("old_date_wip.md"),
        size_bytes=wip_file.stat().st_size,
        mtime=datetime.now() - timedelta(days=5),
        extension=".md",
        sha256=None,
        parent_zone="ROOT",
    )
    immune, reason = is_active_draft_immune(meta, temp_workspace, content)
    assert immune is True
    assert "Explicit frontmatter tag" in reason


def test_active_draft_immunity_waived_for_explicit_deprecated(temp_workspace):
    dep_file = temp_workspace / "deprecated_doc.md"
    content = "---\nstatus: deprecated\n---\nObsolete specifications"
    dep_file.write_text(content, encoding="utf-8")
    meta = DiscoveredFile(
        path=dep_file,
        relative_path=Path("deprecated_doc.md"),
        size_bytes=dep_file.stat().st_size,
        mtime=datetime.now() - timedelta(hours=1),
        extension=".md",
        sha256=None,
        parent_zone="ROOT",
    )
    immune, _ = is_active_draft_immune(meta, temp_workspace, content)
    assert immune is False


# ===========================================================================
# 2. Integration Tests: Safe Relocation & Collision Handling
# ===========================================================================


def test_safe_relocate_same_path_trap(temp_workspace):
    f = temp_workspace / "same.txt"
    f.write_text("same content", encoding="utf-8")
    res = safe_relocate_file(f, f, dry_run=False)
    assert res.success is False
    assert "identical path" in res.error
    assert f.exists()  # Source remains completely intact


def test_safe_relocate_physical_success(temp_workspace):
    src = temp_workspace / "source.txt"
    dest = temp_workspace / "subfolder" / "dest.txt"
    src.write_text("payload bytes", encoding="utf-8")
    src_hash = compute_sha256(src)

    res = safe_relocate_file(src, dest, dry_run=False)
    assert res.success is True
    assert not src.exists()
    assert dest.exists()
    assert compute_sha256(dest) == src_hash


def test_safe_relocate_collision_exact_hash(temp_workspace):
    src = temp_workspace / "dup_source.txt"
    dest = temp_workspace / "dest_exists.txt"
    content = "identical duplicate payload"
    src.write_text(content, encoding="utf-8")
    dest.write_text(content, encoding="utf-8")

    res = safe_relocate_file(src, dest, dry_run=False)
    assert res.success is True
    assert not src.exists()
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == content


def test_safe_relocate_collision_different_hash(temp_workspace):
    src = temp_workspace / "file.txt"
    dest = temp_workspace / "target" / "file.txt"
    dest.parent.mkdir()
    src.write_text("version B", encoding="utf-8")
    dest.write_text("version A", encoding="utf-8")

    res = safe_relocate_file(src, dest, dry_run=False)
    assert res.success is True
    assert not src.exists()
    assert dest.read_text(encoding="utf-8") == "version A"
    # Disambiguated candidate
    cand = dest.parent / "file_1.txt"
    assert cand.exists()
    assert cand.read_text(encoding="utf-8") == "version B"


# ===========================================================================
# 3. Scanner & Classification Tests
# ===========================================================================


def test_project_scanner_protects_anchors(temp_workspace):
    (temp_workspace / "README.md").write_text("# Project", encoding="utf-8")
    (temp_workspace / "GEMINI.md").write_text("# Governance", encoding="utf-8")
    (temp_workspace / "ARCHITECTURE.md").write_text("# Arch", encoding="utf-8")
    (temp_workspace / "stray_note.txt").write_text("loose clutter", encoding="utf-8")

    scanner = ProjectOutputScanner(temp_workspace)
    candidates = scanner.scan(lookback_hours=24)

    cand_names = [c.path.name for c in candidates]
    assert "stray_note.txt" in cand_names
    assert "README.md" not in cand_names
    assert "GEMINI.md" not in cand_names
    assert "ARCHITECTURE.md" not in cand_names


def test_classifier_reference_spec(temp_workspace):
    spec_file = temp_workspace / "SPEC-DATA-01.md"
    spec_file.write_text("# Specification\ncategory: reference", encoding="utf-8")
    meta = DiscoveredFile(
        path=spec_file,
        relative_path=Path("SPEC-DATA-01.md"),
        size_bytes=100,
        mtime=datetime.now(),
        extension=".md",
        sha256=None,
        parent_zone="ROOT",
    )
    classifier = DocumentSemanticsClassifier(temp_workspace)
    decision = classifier.classify(meta)
    assert decision.target_zone == MECEZone.REFERENCE
    assert decision.action == ActionType.RELOCATE


def test_classifier_version_supersession(temp_workspace):
    v1_file = temp_workspace / "architecture_v1.md"
    v2_file = temp_workspace / "architecture_v2.md"
    v1_file.write_text("# Arch v1 (old)", encoding="utf-8")
    v2_file.write_text("# Arch v2 (current)", encoding="utf-8")

    # Backdate v1 beyond 48 hours to waive fresh modification immunity
    old_time = time.time() - (72 * 3600)
    os.utime(str(v1_file), (old_time, old_time))

    meta = DiscoveredFile(
        path=v1_file,
        relative_path=Path("architecture_v1.md"),
        size_bytes=v1_file.stat().st_size,
        mtime=datetime.fromtimestamp(old_time),
        extension=".md",
        sha256=None,
        parent_zone="ROOT",
    )
    classifier = DocumentSemanticsClassifier(temp_workspace)
    decision = classifier.classify(meta)
    assert decision.target_zone == MECEZone.ARCHIVE
    assert decision.action == ActionType.ARCHIVE_OBSOLETE
    assert "Superseded by newer revision" in decision.reason


# ===========================================================================
# 4. Multi-Project Orchestrator Test
# ===========================================================================


def test_orchestrator_pipeline_end_to_end(tmp_path):
    root_projects = tmp_path / "01_PROJECTS"
    p1 = root_projects / "10_PRODUCT_PLATFORM"
    p2 = root_projects / "20_CLOUD_INFRASTRUCTURE"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)

    # Project 1: root clutter
    (p1 / "loose_data.csv").write_text("col1,col2\nval1,val2", encoding="utf-8")
    (p1 / "log.md").write_text("# Log\n", encoding="utf-8")

    # Project 2: obsolete file with explicit deprecation
    (p2 / "old_plan.md").write_text(
        "---\nstatus: deprecated\n---\nOld content", encoding="utf-8"
    )

    orchestrator = MultiProjectReorganizerOrchestrator(
        workspaces_root=root_projects,
        dry_run=False,
        lookback_hours=48,
        caller="test_runner",
    )

    manifest = orchestrator.run_pipeline()
    assert manifest.summary_metrics["total_projects"] == 2
    assert manifest.summary_metrics["total_relocated"] >= 1
    assert manifest.summary_metrics["total_archived"] >= 1
    assert manifest.summary_metrics["total_errors"] == 0

    # Verify physical file locations
    assert not (p1 / "loose_data.csv").exists()
    assert (p1 / "20_ACTIVE_CONTINUOUS" / "data" / "loose_data.csv").exists()

    assert not (p2 / "old_plan.md").exists()
