"""Git artifact adapter module for versioned document storage and state management.

Provides both the GitArtifactAdapter class and top-level domain adapter functions
with headless subprocess execution and structured audit logging.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


class GitRunError(RuntimeError):
    """Exception raised when a git command fails."""


DOMAIN_ADAPTER_CONTRACT: dict[str, Any] = {
    "adapter_name": "GitDocumentArtifactAdapter",
    "version": "1.0.0",
    "accepted_work_items": [
        "document_organization",
        "artifact_versioning",
        "workspace_hygiene",
    ],
    "accepted_artifacts": [
        "tasks.json",
        "scan.json",
        "traceability_matrix.json",
        "document_nodes.json",
    ],
    "risk_classification": "Low",
    "telemetry_fields": [
        "commit_hash",
        "author",
        "date",
        "files_affected",
        "execution_duration_ms",
    ],
}


def get_domain_adapter_contract() -> dict[str, Any]:
    """Return the registered domain adapter contract specification."""
    return DOMAIN_ADAPTER_CONTRACT.copy()


def _get_creation_flags() -> int:
    """Return Windows CREATE_NO_WINDOW flag for headless subprocess execution on Windows."""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return 0


def _run_git_command(
    args: list[str],
    cwd: Path | str,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Execute a git command headlessly with explicit UTF-8 encoding."""
    cmd = ["git"] + args
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
            creationflags=_get_creation_flags(),
        )
    except subprocess.CalledProcessError as exc:
        raise GitRunError(
            f"Git command failed: {' '.join(cmd)}\nStderr: {exc.stderr}"
        ) from exc
    except FileNotFoundError as exc:
        raise GitRunError("git executable not found on system PATH") from exc


def is_git_available() -> bool:
    """Verify if git executable is available in the current environment."""
    try:
        res = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            creationflags=_get_creation_flags(),
        )
        return res.returncode == 0
    except Exception:
        return False


def is_git_repository(repo_path: Path | str) -> bool:
    """Check whether the given path is a valid git repository."""
    path = Path(repo_path)
    if not path.exists():
        return False
    git_dir = path / ".git"
    if git_dir.exists():
        return True
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path),
            capture_output=True,
            text=True,
            creationflags=_get_creation_flags(),
        )
        return res.returncode == 0 and "true" in res.stdout.strip().lower()
    except Exception:
        return False


def init_git_repository(repo_path: Path | str) -> dict[str, Any]:
    """Initialize a new git repository at repo_path."""
    path = Path(repo_path)
    path.mkdir(parents=True, exist_ok=True)
    _run_git_command(["init"], cwd=path)

    # Configure local git user to ensure commit operations pass in isolated test sandboxes
    _run_git_command(["config", "user.name", "DocumentOrganizer"], cwd=path)
    _run_git_command(["config", "user.email", "organizer@localhost"], cwd=path)

    return {
        "is_repository": True,
        "path": str(path.resolve()),
        "status": "initialized",
    }


def _verify_repo(repo_path: Path | str) -> Path:
    """Verify path is a repository; raise ValueError if not."""
    path = Path(repo_path)
    if not is_git_repository(path):
        raise ValueError(f"Path is not a valid git repository: {repo_path}")
    return path


def get_document_status(repo_path: Path | str) -> dict[str, Any]:
    """Inspect git repository working tree status."""
    path = _verify_repo(repo_path)
    proc = _run_git_command(["status", "--porcelain"], cwd=path)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]

    staged: list[dict[str, str]] = []
    untracked: list[str] = []
    modified: list[str] = []

    for line in lines:
        if len(line) < 3:
            continue
        idx_status = line[0]
        work_status = line[1]
        file_path = line[3:].strip().strip('"')

        if idx_status == "?" and work_status == "?":
            untracked.append(file_path)
        else:
            if idx_status in ("A", "M", "D", "R"):
                staged.append({"path": file_path, "status": idx_status})
            if work_status in ("M", "D"):
                modified.append(file_path)

    is_clean = len(lines) == 0
    return {
        "clean": is_clean,
        "staged": staged,
        "untracked": untracked,
        "modified": modified,
    }


def stage_document_change(
    repo_path: Path | str,
    file_paths: str | Path | list[str | Path],
) -> dict[str, Any]:
    """Stage document file changes into the git index."""
    path = _verify_repo(repo_path)
    if isinstance(file_paths, (str, Path)):
        files = [file_paths]
    else:
        files = list(file_paths)

    staged_relative: list[str] = []
    for fp in files:
        fpath = Path(fp)
        if fpath.is_absolute():
            try:
                rel = fpath.relative_to(path).as_posix()
            except ValueError:
                rel = str(fp)
        else:
            rel = fpath.as_posix()
        _run_git_command(["add", rel], cwd=path)
        staged_relative.append(rel)

    status = get_document_status(path)
    return {
        "total_staged_count": len(status["staged"]),
        "staged_files": staged_relative,
    }


def unstage_document_change(
    repo_path: Path | str,
    file_paths: str | Path | list[str | Path],
) -> dict[str, Any]:
    """Unstage document changes from the git index."""
    path = _verify_repo(repo_path)
    if isinstance(file_paths, (str, Path)):
        files = [file_paths]
    else:
        files = list(file_paths)

    for fp in files:
        fpath = Path(fp)
        if fpath.is_absolute():
            try:
                rel = fpath.relative_to(path).as_posix()
            except ValueError:
                rel = str(fp)
        else:
            rel = fpath.as_posix()
        res = _run_git_command(["restore", "--staged", rel], cwd=path, check=False)
        if res.returncode != 0:
            _run_git_command(["rm", "--cached", rel], cwd=path, check=False)

    status = get_document_status(path)
    return {
        "remaining_staged_count": len(status["staged"]),
    }


def create_document_commit(
    repo_path: Path | str,
    message: str,
    actor_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Commit staged changes to the repository."""
    path = _verify_repo(repo_path)
    status = get_document_status(path)
    if not status["staged"]:
        raise RuntimeError("No staged changes to commit")

    staged_paths = [item["path"] for item in status["staged"]]
    full_message = message
    if actor_metadata:
        trailer = "\n\nMetadata:\n" + "\n".join(
            f"  {k}: {v}" for k, v in actor_metadata.items()
        )
        full_message += trailer

    _run_git_command(["commit", "-m", full_message], cwd=path)
    rev_proc = _run_git_command(["rev-parse", "HEAD"], cwd=path)
    commit_hash = rev_proc.stdout.strip()

    return {
        "commit_hash": commit_hash,
        "subject": message,
        "committed_files": staged_paths,
        "actor_metadata": actor_metadata or {},
    }


def get_document_history(
    repo_path: Path | str,
    file_path: str | None = None,
    max_count: int = 100,
) -> list[dict[str, Any]]:
    """Retrieve commit history for the repository or a specific file."""
    path = _verify_repo(repo_path)
    args = ["log", f"-n{max_count}", "--format=%H|%an|%ai|%s"]
    if file_path:
        posix_rel = Path(file_path).as_posix()
        args += ["--follow", "--", posix_rel]

    proc = _run_git_command(args, cwd=path)
    adapter = GitArtifactAdapter(str(path))
    return adapter._parse_commit_output(proc.stdout)


def create_document_snapshot(
    repo_path: Path | str,
    snapshot_name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a tagged snapshot of the repository."""
    path = _verify_repo(repo_path)
    tag_args = [
        "tag",
        "-a",
        snapshot_name,
        "-m",
        description or f"Snapshot {snapshot_name}",
    ]
    _run_git_command(tag_args, cwd=path)
    return {
        "snapshot_name": snapshot_name,
        "status": "created",
        "description": description,
    }


def list_document_snapshots(repo_path: Path | str) -> list[dict[str, Any]]:
    """List all snapshot tags in the repository."""
    path = _verify_repo(repo_path)
    proc = _run_git_command(
        ["tag", "-l", "--format=%(refname:short)|%(subject)"], cwd=path
    )
    snapshots: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 1)
        name = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        snapshots.append({"snapshot_name": name, "description": desc})
    return snapshots


def delete_document_snapshot(
    repo_path: Path | str, snapshot_name: str
) -> dict[str, Any]:
    """Delete a snapshot tag."""
    path = _verify_repo(repo_path)
    _run_git_command(["tag", "-d", snapshot_name], cwd=path)
    return {
        "snapshot_name": snapshot_name,
        "status": "deleted",
    }


def rollback_document_snapshot(
    repo_path: Path | str, snapshot_name: str
) -> dict[str, Any]:
    """Roll back working directory and index to a snapshot tag."""
    path = _verify_repo(repo_path)
    tag_check = _run_git_command(["tag", "-l", snapshot_name], cwd=path)
    if not tag_check.stdout.strip():
        raise ValueError(f"Snapshot tag does not exist: {snapshot_name}")

    _run_git_command(["reset", "--hard", snapshot_name], cwd=path)
    return {
        "status": "restored",
        "snapshot_name": snapshot_name,
    }


def get_document_version_at_commit(
    repo_path: Path | str,
    file_path: str,
    commit_hash: str,
) -> str | None:
    """Retrieve content of a file at a specific commit hash."""
    path = _verify_repo(repo_path)
    posix_path = Path(file_path).as_posix()
    try:
        proc = _run_git_command(["show", f"{commit_hash}:{posix_path}"], cwd=path)
        return proc.stdout
    except GitRunError:
        return None


def get_document_diff(
    repo_path: Path | str,
    file_path: str | None = None,
    commit_a: str | None = None,
    commit_b: str | None = None,
) -> dict[str, Any]:
    """Compute diff between commits or against the working tree."""
    path = _verify_repo(repo_path)
    args = ["diff"]
    if commit_a and commit_b:
        args += [commit_a, commit_b]
    elif commit_a:
        args += [commit_a]

    if file_path:
        args += ["--", Path(file_path).as_posix()]

    proc = _run_git_command(args, cwd=path)
    diff_text = proc.stdout
    return {
        "has_changes": bool(diff_text.strip()),
        "diff": diff_text,
    }


def checkout_document_version(
    repo_path: Path | str,
    file_path: str,
    commit_hash: str,
) -> dict[str, Any]:
    """Restore a single document to the version at commit_hash."""
    path = _verify_repo(repo_path)
    posix_path = Path(file_path).as_posix()
    _run_git_command(["checkout", commit_hash, "--", posix_path], cwd=path)
    return {
        "status": "restored",
        "file_path": file_path,
        "commit_hash": commit_hash,
    }


class GitArtifactAdapter:
    """Object-oriented adapter for git-backed document repositories."""

    def __init__(self, repo_path: str | Path):
        self.repo_path = str(Path(repo_path).resolve())

    def get_commit_history(self, file_path: str) -> list[dict[str, Any]]:
        """Retrieve commit history for a specific file."""
        return get_document_history(self.repo_path, file_path=file_path)

    def _parse_commit_output(self, output: str) -> list[dict[str, Any]]:
        """Parse git log output into structured commit dictionaries."""
        commits: list[dict[str, Any]] = []
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                hash_, author, date, message = parts
            else:
                hash_ = parts[0]
                author = parts[1] if len(parts) > 1 else ""
                date = parts[2] if len(parts) > 2 else ""
                message = parts[3] if len(parts) > 3 else ""
            commits.append(
                {
                    "commit_hash": hash_,
                    "hash": hash_,
                    "author": author,
                    "date": date,
                    "message": message,
                }
            )
        return commits

    def get_file_at_commit(self, commit_hash: str, file_path: str) -> str | None:
        """Get file content at a specific commit."""
        return get_document_version_at_commit(self.repo_path, file_path, commit_hash)
