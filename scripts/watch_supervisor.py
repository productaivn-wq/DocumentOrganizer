#!/usr/bin/env python3
"""
watch_supervisor.py - Persistent monitor loop for the real-time file organizer daemon.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def get_windows_shell_folders() -> dict[str, Path]:
    """Retrieve Windows Shell Known Folders from registry to resolve OneDrive KFM redirections."""
    folders: dict[str, Path] = {}
    if sys.platform == "win32":
        try:
            import winreg

            key_path = (
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                name_map = {
                    "Desktop": "Desktop",
                    "Personal": "Documents",
                    "My Pictures": "Pictures",
                    "My Video": "Videos",
                    "My Music": "Music",
                    "{374DE290-123F-4565-9164-39C4925E467B}": "Downloads",
                }
                for reg_name, label in name_map.items():
                    try:
                        val, _ = winreg.QueryValueEx(key, reg_name)
                        if val:
                            expanded = Path(os.path.expandvars(val)).resolve()
                            folders[label] = expanded
                    except OSError:
                        pass
        except Exception:
            pass
    return folders


def discover_watch_directories(work_root: Path | str | None = None, projects_root: Path | str | None = None) -> list[str]:
    """Discover all primary, shell-redirected, media capture, and project-scoped ingress directories."""
    resolved_dirs: list[str] = []
    seen: set[str] = set()

    def add_dir(p: Path | str | None):
        if not p:
            return
        try:
            path_obj = Path(p).resolve()
            if (
                path_obj.exists()
                and path_obj.is_dir()
                and "_duplicates" not in path_obj.parts
            ):
                path_str = str(path_obj)
                if path_str.lower() not in seen:
                    seen.add(path_str.lower())
                    resolved_dirs.append(path_str)
        except Exception:
            pass

    # 1. Windows Known Folders / OneDrive KFM
    shell_folders = get_windows_shell_folders()
    home = Path.home()

    # Desktop (both OneDrive redirected and local)
    add_dir(shell_folders.get("Desktop", home / "Desktop"))
    add_dir(home / "Desktop")

    # Downloads
    add_dir(shell_folders.get("Downloads", home / "Downloads"))

    # Videos & Captures (Windows Game Bar, Snipping Tool recordings)
    videos_dir = shell_folders.get("Videos", home / "Videos")
    add_dir(videos_dir / "Captures")
    add_dir(videos_dir / "Screen Recordings")
    add_dir(home / "Videos" / "Captures")

    # Pictures & Screenshots (Snipping Tool, Win+PrtScn)
    pictures_dir = shell_folders.get("Pictures", home / "Pictures")
    add_dir(pictures_dir / "Screenshots")
    add_dir(home / "Pictures" / "Screenshots")

    # Documents specialized ingress (Viber, Zalo, Sound Recordings)
    documents_dir = shell_folders.get("Documents", home / "Documents")
    add_dir(documents_dir / "ViberDownloads")
    add_dir(documents_dir / "Zalo Received Files")
    add_dir(documents_dir / "Sound Recordings")
    add_dir(home / "Documents" / "ViberDownloads")
    add_dir(home / "Documents" / "Zalo Received Files")
    add_dir(home / "Downloads" / "Telegram Desktop")

    # 2. General Work Inboxes
    base_work = Path(work_root) if work_root else Path(os.environ.get("WORKSPACE_ROOT", str(home / "Workspace")))
    add_dir(base_work / "00_INBOX")
    add_dir(base_work / "_inbox")

    # 3. Monorepo Project Inboxes
    projects_root = Path(projects_root) if projects_root else Path(os.environ.get("WORKSPACE_PROJECTS_ROOT", str(base_work / "01_PROJECTS")))
    if projects_root.exists():
        for item in sorted(projects_root.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                for candidate in ("00_INBOX", "_inbox"):
                    inbox = item / candidate
                    if inbox.exists() and inbox.is_dir():
                        add_dir(inbox)
                        break

    return resolved_dirs


def main():
    watch_dirs = discover_watch_directories()
    target_root = os.environ.get("WORKSPACE_ROOT", str(Path.home() / "Workspace"))

    script_dir = Path(__file__).resolve().parent
    watch_py = script_dir / "watch.py"
    lock_file = script_dir / ".watch_supervisor.lock"
    if lock_file.exists():
        try:
            import psutil

            old_pid = lock_file.read_text(encoding="utf-8").strip()
            if (
                old_pid.isdigit()
                and int(old_pid) != os.getpid()
                and psutil.pid_exists(int(old_pid))
            ):
                sys.exit(0)
        except Exception:
            pass
    try:
        import atexit

        lock_file.write_text(str(os.getpid()), encoding="utf-8")
        atexit.register(lambda: lock_file.unlink(missing_ok=True))
    except Exception:
        pass

    CREATE_NO_WINDOW = 0x08000000

    log_file = Path(os.environ.get("DOCUMENT_ORGANIZER_LOG_FILE", str(Path.home() / ".cache" / "document-organizer" / "logs" / "supervisor.log")))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(msg):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        line = f"{timestamp} [SUPERVISOR] {msg}\n"
        if sys.stdout is not None:
            try:
                sys.stdout.write(line)
                sys.stdout.flush()
            except Exception:
                pass
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    log("Starting Watcher Supervisor...")
    for idx, d in enumerate(watch_dirs, 1):
        log(f"Watch Directory [{idx}]: {d}")
    log(f"Target Directory: {target_root}")
    log(f"Script: {watch_py}")

    cmd = [
        sys.executable,
        "-u",
        str(watch_py),
        "--watch",
        *watch_dirs,
        "--target",
        target_root,
        "--whitelist-only",
    ]

    while True:
        lf = None
        try:
            log("Launching watch.py process...")
            lf = open(log_file, "a", encoding="utf-8")
            lf.write("\n--- watch.py spawned ---\n")
            lf.flush()
            process = subprocess.Popen(
                cmd,
                stdout=lf,
                stderr=subprocess.STDOUT,
                cwd=str(script_dir),
                creationflags=CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            log(f"watch.py process started with PID: {process.pid}")
            exit_code = process.wait()
            log(f"watch.py process exited with code: {exit_code}")
        except Exception as e:
            log(f"Error executing watch.py: {e}")
        finally:
            if lf is not None and not lf.closed:
                try:
                    lf.close()
                except Exception:
                    pass

        log("Sleeping 5 seconds before restart...")
        time.sleep(5)


if __name__ == "__main__":
    main()
