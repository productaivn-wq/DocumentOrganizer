#!/usr/bin/env python3
"""
test_git_artifact_adapter.py — Unit tests for git-versioned document artifact adapter helper functions.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.git_artifact_adapter import (
    checkout_document_version,
    create_document_commit,
    create_document_snapshot,
    delete_document_snapshot,
    get_document_diff,
    get_document_history,
    get_document_status,
    get_document_version_at_commit,
    get_domain_adapter_contract,
    init_git_repository,
    is_git_available,
    is_git_repository,
    list_document_snapshots,
    rollback_document_snapshot,
    stage_document_change,
    unstage_document_change,
)


class TestGitArtifactAdapter(unittest.TestCase):
    """Test suite for git artifact adapter helper functions."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="git_adapter_test_"))
        self.addCleanup(shutil.rmtree, str(self.test_dir), ignore_errors=True)

    def test_domain_adapter_contract(self):
        """Verify domain adapter contract structure and requirements."""
        contract = get_domain_adapter_contract()
        self.assertEqual(contract["adapter_name"], "GitDocumentArtifactAdapter")
        self.assertIn("document_organization", contract["accepted_work_items"])
        self.assertIn("tasks.json", contract["accepted_artifacts"])
        self.assertEqual(contract["risk_classification"], "Low")
        self.assertIn("commit_hash", contract["telemetry_fields"])

    def test_git_availability(self):
        """Check git availability helper."""
        self.assertTrue(
            is_git_available(), "Git should be available in the test environment"
        )

    def test_init_and_check_git_repository(self):
        """Test initializing a new git repository and checking repository status."""
        non_repo = self.test_dir / "repo"
        self.assertFalse(is_git_repository(non_repo))

        res = init_git_repository(non_repo)
        self.assertTrue(res["is_repository"])
        self.assertTrue(is_git_repository(non_repo))

    def test_document_status_and_staging(self):
        """Test checking document status, staging, and unstaging changes."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        # Initial status should be clean
        status = get_document_status(repo)
        self.assertTrue(status["clean"])

        # Create a document file
        doc_path = repo / "doc1.md"
        doc_path.write_text("# Document 1\nContent", encoding="utf-8")

        status = get_document_status(repo)
        self.assertFalse(status["clean"])
        self.assertIn("doc1.md", status["untracked"])

        # Stage document change
        stage_res = stage_document_change(repo, "doc1.md")
        self.assertEqual(stage_res["total_staged_count"], 1)

        status_after_stage = get_document_status(repo)
        self.assertEqual(len(status_after_stage["staged"]), 1)
        self.assertEqual(status_after_stage["staged"][0]["path"], "doc1.md")

        # Unstage document change
        unstage_res = unstage_document_change(repo, "doc1.md")
        self.assertEqual(unstage_res["remaining_staged_count"], 0)

    def test_create_commit_and_history(self):
        """Test committing staged document changes and querying history."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc_path = repo / "report.md"
        doc_path.write_text("# Annual Report\nDraft v1", encoding="utf-8")

        stage_document_change(repo, doc_path)

        metadata = {"actor_id": "agent-123", "task_id": "task-abc"}
        commit_res = create_document_commit(
            repo,
            message="Add annual report draft",
            actor_metadata=metadata,
        )

        self.assertIsNotNone(commit_res["commit_hash"])
        self.assertEqual(commit_res["subject"], "Add annual report draft")
        self.assertIn("report.md", commit_res["committed_files"])

        history = get_document_history(repo)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["commit_hash"], commit_res["commit_hash"])

    def test_snapshot_and_rollback(self):
        """Test snapshot creation and rollback capabilities."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc_path = repo / "spec.md"
        doc_path.write_text("Version 1.0", encoding="utf-8")
        stage_document_change(repo, doc_path)
        create_document_commit(repo, "Initial spec v1.0")

        # Create snapshot
        snap_res = create_document_snapshot(repo, "v1_stable")
        self.assertEqual(snap_res["snapshot_name"], "v1_stable")

        # Modify document and commit v2
        doc_path.write_text("Version 2.0 - Breaking Changes", encoding="utf-8")
        stage_document_change(repo, doc_path)
        create_document_commit(repo, "Update spec v2.0")

        self.assertEqual(
            doc_path.read_text(encoding="utf-8"), "Version 2.0 - Breaking Changes"
        )

        # Rollback to snapshot v1_stable
        rb_res = rollback_document_snapshot(repo, "v1_stable")
        self.assertEqual(rb_res["status"], "restored")

        # Verify content rolled back
        self.assertEqual(doc_path.read_text(encoding="utf-8"), "Version 1.0")

    def test_error_handling(self):
        """Test error conditions for git artifact adapter functions."""
        non_repo = self.test_dir / "not_a_repo"
        non_repo.mkdir()

        with self.assertRaises(ValueError):
            get_document_status(non_repo)

        with self.assertRaises(ValueError):
            stage_document_change(non_repo, "file.txt")

        repo = self.test_dir / "valid_repo"
        init_git_repository(repo)

        # Commit with no staged changes should fail
        with self.assertRaises(RuntimeError):
            create_document_commit(repo, "Empty commit")

        # Rollback to non-existent snapshot should fail
        with self.assertRaises(ValueError):
            rollback_document_snapshot(repo, "non_existent_snapshot")

    def test_get_document_version_at_commit(self):
        """Test retrieving artifact content at a specific commit without modifying worktree."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc_path = repo / "notes.md"
        doc_path.write_text("Version 1 content", encoding="utf-8")
        stage_document_change(repo, doc_path)
        c1 = create_document_commit(repo, "v1 commit")

        doc_path.write_text("Version 2 content", encoding="utf-8")
        stage_document_change(repo, doc_path)
        c2 = create_document_commit(repo, "v2 commit")

        # Verify reading past version
        v1_text = get_document_version_at_commit(repo, "notes.md", c1["commit_hash"])
        self.assertEqual(v1_text, "Version 1 content")

        v2_text = get_document_version_at_commit(repo, "notes.md", c2["commit_hash"])
        self.assertEqual(v2_text, "Version 2 content")

        # Verify current worktree is unchanged
        self.assertEqual(doc_path.read_text(encoding="utf-8"), "Version 2 content")

    def test_get_document_diff(self):
        """Test generating diffs between commits and working tree."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc_path = repo / "doc.txt"
        doc_path.write_text("Line 1\nLine 2\n", encoding="utf-8")
        stage_document_change(repo, doc_path)
        c1 = create_document_commit(repo, "Initial commit")

        doc_path.write_text("Line 1\nLine 2 modified\nLine 3\n", encoding="utf-8")

        diff_res = get_document_diff(repo, "doc.txt")
        self.assertTrue(diff_res["has_changes"])
        self.assertIn("+Line 3", diff_res["diff"])

        stage_document_change(repo, doc_path)
        c2 = create_document_commit(repo, "Second commit")

        diff_commits = get_document_diff(
            repo, "doc.txt", commit_a=c1["commit_hash"], commit_b=c2["commit_hash"]
        )
        self.assertTrue(diff_commits["has_changes"])
        self.assertIn("-Line 2", diff_commits["diff"])

    def test_list_and_delete_document_snapshots(self):
        """Test listing and deleting snapshot tags."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc_path = repo / "file.md"
        doc_path.write_text("Content", encoding="utf-8")
        stage_document_change(repo, doc_path)
        create_document_commit(repo, "Initial file")

        create_document_snapshot(repo, "snap_alpha", "Alpha snapshot")
        create_document_snapshot(repo, "snap_beta", "Beta snapshot")

        snapshots = list_document_snapshots(repo)
        self.assertEqual(len(snapshots), 2)
        names = [s["snapshot_name"] for s in snapshots]
        self.assertIn("snap_alpha", names)
        self.assertIn("snap_beta", names)

        # Delete one snapshot
        del_res = delete_document_snapshot(repo, "snap_alpha")
        self.assertEqual(del_res["status"], "deleted")

        remaining = list_document_snapshots(repo)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["snapshot_name"], "snap_beta")

    def test_checkout_document_version(self):
        """Test restoring a single document to a specific commit."""
        repo = self.test_dir / "repo"
        init_git_repository(repo)

        doc1 = repo / "doc1.txt"
        doc2 = repo / "doc2.txt"
        doc1.write_text("Doc 1 V1", encoding="utf-8")
        doc2.write_text("Doc 2 V1", encoding="utf-8")
        stage_document_change(repo, [doc1, doc2])
        c1 = create_document_commit(repo, "V1 commit")

        doc1.write_text("Doc 1 V2", encoding="utf-8")
        doc2.write_text("Doc 2 V2", encoding="utf-8")
        stage_document_change(repo, [doc1, doc2])
        create_document_commit(repo, "V2 commit")

        # Checkout doc1 to V1 commit
        checkout_res = checkout_document_version(repo, "doc1.txt", c1["commit_hash"])
        self.assertEqual(checkout_res["status"], "restored")

        # doc1 should be V1, doc2 should remain V2
        self.assertEqual(doc1.read_text(encoding="utf-8"), "Doc 1 V1")
        self.assertEqual(doc2.read_text(encoding="utf-8"), "Doc 2 V2")


if __name__ == "__main__":
    unittest.main()
