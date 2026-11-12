#!/usr/bin/env python3
"""Task decomposition utilities for orchestrator.

This module extracts task decomposition logic from orchestrator.py
into a separate module for better separation of concerns.
"""

import json
import os
import re
import sys
from datetime import datetime

# Ensure scripts/ is importable
sys.path.insert(0, os.path.dirname(__file__))


def _read_context_file(context_path: str | None) -> str:
    """Read optional context file and return its contents.

    Args:
        context_path: Path to context file, or None.

    Returns:
        File contents as string, or empty string if file doesn't exist.
    """
    if not context_path or not os.path.exists(context_path):
        return ""
    with open(context_path, encoding="utf-8") as f:
        return f.read()


def _agent_context_decompose(task: str, job_dir: str) -> dict:
    """Stub decomposition when all external LLM providers are unavailable.

    Writes a minimal tasks.json + STUB_DECOMPOSE.md so the calling AI
    Agent (which has its own LLM context) can populate the sub_tasks manually
    rather than letting the orchestrator hard-exit and be bypassed entirely.

    Note: This is NOT a true agent-context LLM call. The orchestrator subprocess
    cannot invoke the parent agent's inference directly. The stub signals to the
    agent that decomposition is needed via the generated instruction file.

    Args:
        task: The original task description.
        job_dir: Directory to write stub files.

    Returns:
        Stub job data dictionary.
    """
    print("\n[FALLBACK] All external LLM providers failed.")
    print("  Writing stub tasks.json for agent-context decomposition.")
    print("  The AI Agent should populate sub_tasks before running 'execute'.")
    stub = {
        "job_id": f"job-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "original_task": task,
        "created_at": datetime.now().isoformat(),
        "decomposition_rationale": (
            "STUB — all API providers unavailable. "
            "Calling agent must populate sub_tasks before running 'execute'."
        ),
        "sub_tasks": [
            {
                "id": "T001",
                "title": f"[STUB] {task[:80]}",
                "prompt": task,
                "profile": "explorer",
                "_stub": True,
            }
        ],
    }
    tasks_path = os.path.join(job_dir, "tasks.json")
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(stub, f, indent=2, ensure_ascii=False)

    stub_note = os.path.join(job_dir, "STUB_DECOMPOSE.md")
    with open(stub_note, "w", encoding="utf-8") as f:
        f.write(
            f"# STUB Decomposition\n\n"
            f"All LLM API providers were unavailable at decompose time.\n\n"
            f"**Task**: {task}\n\n"
            f"**Action required**: Edit `tasks.json` and replace the stub `sub_tasks` "
            f"with real decomposed tasks, then run:\n\n"
            f"```\npython orchestrator.py execute {job_dir}\n```\n"
        )
    print(f"  Stub tasks.json : {tasks_path}")
    print(f"  Instructions   : {stub_note}")
    return stub


def _parse_decompose_json(raw_result: str, job_dir: str) -> dict:
    """Parse JSON from LLM decomposition output. Exits on failure.

    Args:
        raw_result: Raw LLM response string.
        job_dir: Directory to write debug output.

    Returns:
        Parsed JSON dictionary.

    Raises:
        SystemExit: If JSON parsing fails.
    """
    cleaned = raw_result.strip()
    match = re.search(
        r"^```(?:json)?\s*(.*)\s*```$", cleaned, re.DOTALL | re.IGNORECASE
    )
    if match:
        cleaned = match.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"\nFailed to parse decomposition JSON: {e}")
        debug_path = os.path.join(job_dir, "decompose_raw.txt")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(raw_result)
        print(f"Raw response saved to: {debug_path}")
        sys.exit(1)


def _save_job_data(
    args_task: str, decomposition: dict, job_dir: str, domain: str = "general"
) -> dict:
    """Build and save tasks.json. Returns job_data dict.

    Args:
        args_task: Original task string from command line.
        decomposition: Parsed decomposition dictionary.
        job_dir: Directory to write tasks.json.
        domain: Domain category for tasks.

    Returns:
        Job data dictionary with metadata and sub-tasks.
    """
    sub_tasks = decomposition.get("sub_tasks", [])
    for task in sub_tasks:
        if "domain" not in task:
            task["domain"] = domain
        if "depends_on" not in task or not isinstance(task["depends_on"], list):
            task["depends_on"] = []

    job_data = {
        "job_id": f"job-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "original_task": args_task,
        "created_at": datetime.now().isoformat(),
        "domain": domain,
        "decomposition_rationale": decomposition.get("decomposition_rationale", ""),
        "sub_tasks": sub_tasks,
    }
    tasks_path = os.path.join(job_dir, "tasks.json")
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)
    return job_data
