"""
test_hygiene_integration.py — MinTC automated verification suite for DocumentOrganizer hygiene engine.

Implements: UC-001 (DocumentOrganizer SSOT)
Traces: FR-ORG-10, FR-ORG-11
Verifies: TC-ORG-HYGIENE-01 .. TC-ORG-HYGIENE-08
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys_path = str(SKILL_ROOT / "scripts")
import sys

if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from hygiene import WorkspaceHygieneEngine
from sweep import WorkspaceSweepOrchestrator


@pytest.fixture
def sandbox_env():
    """Creates an isolated temporary test sandbox with dummy files and databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create test mock structure
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "test.cpython-311.pyc").write_bytes(
            b"PYC_BYTECODE_DUMMY" * 50
        )

        (tmp_path / ".browser-test-profile").mkdir()
        (tmp_path / ".browser-test-profile" / "cookies.tmp").write_bytes(
            b"COOKIE_DATA" * 20
        )

        # Create mock SQLite database
        db_path = tmp_path / "test_app.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        for i in range(100):
            conn.execute("INSERT INTO users VALUES (?, ?)", (i, f"user_{i}"))
        conn.commit()
        conn.close()

        # Inviolable mock files
        (tmp_path / "NTUSER.DAT").write_bytes(b"CRITICAL_REGISTRY_HIVE")
        (tmp_path / "SKILL.md").write_text("SKILL SPEC", encoding="utf-8")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("GIT CONFIG", encoding="utf-8")

        yield tmp_path


# =========================================================================
# POSITIVE TEST CASES (TC-ORG-HYGIENE-01 .. 04)
# =========================================================================


def test_hygiene_rules_load():
    """TC-ORG-HYGIENE-01: Verifies cleaner_rules.json loads with expected recipes."""
    engine = WorkspaceHygieneEngine(root_dir=".")
    assert "recipes" in engine.rules
    assert "python" in engine.rules["recipes"]
    assert "browser" in engine.rules["recipes"]
    assert "temp" in engine.rules["recipes"]
    assert "sqlite" in engine.rules["recipes"]


def test_dry_run_does_not_delete(sandbox_env):
    """TC-ORG-HYGIENE-02: Verifies dry-run preview measures bytes without deleting files."""
    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env))
    pyc_file = sandbox_env / "__pycache__" / "test.cpython-311.pyc"
    assert pyc_file.exists()

    res = engine.run_hygiene_sweep(targets=["python"], dry_run=True)
    assert res["total_bytes"] > 0
    assert res["total_files"] >= 1
    # File must still exist in dry-run
    assert pyc_file.exists()


def test_physical_purge_execution(sandbox_env):
    """TC-ORG-HYGIENE-03: Verifies physical execution purges targeted cache files."""
    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env))
    pyc_file = sandbox_env / "__pycache__" / "test.cpython-311.pyc"
    assert pyc_file.exists()

    res = engine.run_hygiene_sweep(targets=["python"], dry_run=False)
    assert res["total_bytes"] > 0
    assert not pyc_file.exists()


def test_sqlite_vacuum_compaction(sandbox_env):
    """TC-ORG-HYGIENE-04: Verifies SQLite vacuum runs without corrupting database."""
    db_path = sandbox_env / "test_app.db"
    assert db_path.exists()

    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env))
    engine.vacuum_sqlite(db_path, dry_run=False)

    # Re-open and verify query integrity
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT count(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 100


# =========================================================================
# ADVERSARIAL & INVIOLABLE SAFETY TESTS (TC-ORG-HYGIENE-05 .. 08)
# =========================================================================


def test_inviolable_guard_blocks_system_files(sandbox_env):
    """TC-ORG-HYGIENE-05: Inviolable system hives, .git, and SKILL.md are protected."""
    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env))

    hive = sandbox_env / "NTUSER.DAT"
    skill = sandbox_env / "SKILL.md"
    git_dir = sandbox_env / ".git"

    assert engine.is_inviolable(hive) is True
    assert engine.is_inviolable(skill) is True
    assert engine.is_inviolable(git_dir) is True

    # Purge attempts must be rejected and delete 0 bytes
    b1 = engine.purge_file(hive, dry_run=False)
    b2 = engine.purge_file(skill, dry_run=False)
    b3, c3 = engine.purge_directory(git_dir, dry_run=False)

    assert b1 == 0
    assert b2 == 0
    assert b3 == 0
    assert hive.exists()
    assert skill.exists()
    assert git_dir.exists()


def test_nonexistent_directory_resilience():
    """TC-ORG-HYGIENE-06: Verifies engine handles non-existent paths gracefully."""
    engine = WorkspaceHygieneEngine(root_dir="C:/NonExistentPath_XYZ123")
    res = engine.clean_target_recipe("python", dry_run=True)
    assert res["reclaimed_bytes"] == 0
    assert res["files_count"] == 0


def test_corrupted_rules_fallback(sandbox_env):
    """TC-ORG-HYGIENE-07: Verifies engine falls back to hardcoded safety rules if JSON missing."""
    engine = WorkspaceHygieneEngine(
        root_dir=str(sandbox_env), rules_path="C:/NonExistentRules.json"
    )
    assert "NTUSER.DAT" in engine.inviolable_paths
    assert engine.is_inviolable(Path("NTUSER.DAT")) is True


def test_unified_sweep_orchestrator(sandbox_env):
    """TC-ORG-HYGIENE-08: Verifies unified two-stage sweep completes and generates manifest."""
    orchestrator = WorkspaceSweepOrchestrator(workspace_root=str(sandbox_env))
    report = orchestrator.run_sweep(dry_run=True)

    assert report["orchestrator"] == "DocumentOrganizer.WorkspaceSweepOrchestrator"
    assert "stage_1_ingress" in report
    assert "stage_2_hygiene" in report
    assert report["stage_2_hygiene"]["total_files_purged"] >= 1


def test_conversation_scratch_cleanup_preserves_active_and_transcripts(sandbox_env):
    """TC-ORG-HYGIENE-09: Verifies active session and transcripts are strictly protected while scratch is cleaned."""
    brain_root = sandbox_env / "brain"
    brain_root.mkdir()

    # Active conversation
    active_id = "active_conv_123"
    active_dir = brain_root / active_id
    active_dir.mkdir()
    (active_dir / "task.md").write_text("ACTIVE TASK", encoding="utf-8")
    (active_dir / "scratch").mkdir()
    (active_dir / "scratch" / "keep_me.py").write_text(
        "print('active')", encoding="utf-8"
    )

    # Historical conversation
    hist_id = "hist_conv_456"
    hist_dir = brain_root / hist_id
    hist_dir.mkdir()
    (hist_dir / "task.md").write_text("HISTORICAL TASK", encoding="utf-8")
    logs_dir = hist_dir / ".system_generated" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "transcript.jsonl").write_text('{"event": "step"}', encoding="utf-8")

    hist_scratch = hist_dir / "scratch"
    hist_scratch.mkdir()
    (hist_scratch / "playwright_profile").mkdir()
    (hist_scratch / "playwright_profile" / "state.json").write_text(
        "{}", encoding="utf-8"
    )
    (hist_scratch / "plan_extraction.json").write_text("[]", encoding="utf-8")

    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env), active_conv_id=active_id)
    res = engine.clean_conversation_scratch(brain_root=brain_root, dry_run=False)

    # Historical scratch purged
    assert res["files_count"] >= 2
    assert not (hist_scratch / "playwright_profile").exists()

    # Historical transcripts and task.md preserved!
    assert (logs_dir / "transcript.jsonl").exists()
    assert (hist_dir / "task.md").exists()

    # Active conversation strictly immune!
    assert (active_dir / "scratch" / "keep_me.py").exists()
    assert (active_dir / "task.md").exists()


def test_project_workspace_cache_purging(sandbox_env):
    """TC-ORG-HYGIENE-10: Verifies project build caches are purged while source and git remain intact."""
    projects_root = sandbox_env / "projects"
    projects_root.mkdir()

    proj1 = projects_root / "01_TEST_PROJ"
    proj1.mkdir()
    (proj1 / "README.md").write_text("# Project 1", encoding="utf-8")
    (proj1 / ".git").mkdir()
    (proj1 / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

    # Caches and stray files
    (proj1 / "__pycache__").mkdir()
    (proj1 / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"PYC")
    (proj1 / ".coverage").write_bytes(b"COV")
    (proj1 / "scan.json").write_text("{}", encoding="utf-8")

    engine = WorkspaceHygieneEngine(root_dir=str(sandbox_env))
    res = engine.clean_project_workspace_caches(
        projects_root=projects_root, dry_run=False
    )

    assert res["files_count"] >= 3
    assert not (proj1 / "__pycache__" / "mod.cpython-311.pyc").exists()
    assert not (proj1 / ".coverage").exists()
    assert not (proj1 / "scan.json").exists()

    # Source and git intact
    assert (proj1 / "README.md").exists()
    assert (proj1 / ".git" / "HEAD").exists()
