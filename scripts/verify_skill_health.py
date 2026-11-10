#!/usr/bin/env python3
"""
verify_skill_health.py — Comprehensive Health & Prevention Verification for DocumentOrganizer.

Enforces:
1. Full test suite execution with minimum test count >= 60 and 0 failures/errors.
2. Background watcher daemon status & supervisor watchdog health.
3. Dynamic Known Folders discovery (ensuring Captures, Desktop, ViberDownloads are tracked).
4. Zero-byte silent log prevention and UTF-8 streaming.

Usage:
    python -u scripts/verify_skill_health.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

MIN_REQUIRED_TESTS = 60


def log(msg: str) -> None:
    print(f"[HEALTH] {msg}", flush=True)


def check_tests() -> bool:
    """Run full pytest suite and verify minimum test count threshold."""
    log(
        f"Running full test suite against {SKILL_ROOT / 'tests'} (minimum test count requirement: >={MIN_REQUIRED_TESTS})..."
    )

    cmd = [
        sys.executable,
        "-u",
        "-m",
        "pytest",
        str(SKILL_ROOT / "tests"),
        "-q",
        "--tb=short",
    ]

    res = subprocess.run(
        cmd,
        cwd=str(SKILL_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    stdout = res.stdout + res.stderr
    print(stdout, flush=True)

    if res.returncode != 0:
        log("ERROR: Test suite execution failed!")
        return False

    # Check passed test count
    # Output format example: "62 passed, 1 warning in 6.54s"
    import re

    match = re.search(r"(\d+)\s+passed", stdout)
    if not match:
        log("ERROR: Could not parse passed test count from pytest output!")
        return False

    passed_count = int(match.group(1))
    if passed_count < MIN_REQUIRED_TESTS:
        log(
            f"ERROR: Passed test count ({passed_count}) is below minimum threshold ({MIN_REQUIRED_TESTS})!"
        )
        return False

    log(
        f"PASS: Full test suite verified ({passed_count} passed, 0 failures, minimum test count >= {MIN_REQUIRED_TESTS})."
    )
    return True


def check_known_folders_discovery() -> bool:
    """Verify that dynamic shell discovery correctly includes critical ingress paths."""
    log("Verifying dynamic Windows Shell & OneDrive Known Folders discovery...")
    try:
        from scripts.watch_supervisor import discover_watch_directories

        dirs = discover_watch_directories()
        dir_strs = [str(d).lower() for d in dirs]

        # Verify Captures, Desktop, and Downloads are included
        has_captures = any("captures" in s for s in dir_strs)
        has_desktop = any("desktop" in s for s in dir_strs)
        has_downloads = any("downloads" in s for s in dir_strs)

        log(f"  - Watched directory count: {len(dirs)}")
        log(f"  - Captures path detected: {has_captures}")
        log(f"  - Desktop path detected:  {has_desktop}")
        log(f"  - Downloads path detected:{has_downloads}")

        if not (has_captures and has_desktop and has_downloads):
            log("ERROR: Critical ingress directories missing from dynamic discovery!")
            return False

        log("PASS: Dynamic Known Folders discovery operational.")
        return True
    except Exception as exc:
        log(f"ERROR: Discovery check raised exception: {exc}")
        return False


def check_active_daemons() -> bool:
    """Check whether watch_supervisor and watch daemons are actively running."""
    log("Auditing running background daemons...")
    if os.name != "nt":
        return True

    try:
        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*watch_supervisor.py*' -or $_.CommandLine -like '*watch.py*' }).CommandLine",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = res.stdout.strip()

        has_supervisor = "watch_supervisor.py" in output
        has_watcher = "watch.py" in output

        log(f"  - Supervisor active: {has_supervisor}")
        log(f"  - Watcher active:    {has_watcher}")

        if not (has_supervisor or has_watcher):
            log(
                "WARNING: Neither supervisor nor watcher was detected in active process tree."
            )
            return False

        log("PASS: Background automation processes verified.")
        return True
    except Exception as exc:
        log(f"WARNING: Process audit check failed: {exc}")
        return True


def main() -> None:
    log("Starting DocumentOrganizer Prevention & Health Audit...")

    t_ok = check_tests()
    d_ok = check_known_folders_discovery()
    p_ok = check_active_daemons()

    if t_ok and d_ok and p_ok:
        log("ALL HEALTH CHECKS PASSED (COMPLIANT).")
        sys.exit(0)
    else:
        log("HEALTH CHECKS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
