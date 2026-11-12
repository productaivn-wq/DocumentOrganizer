#!/usr/bin/env python3
"""Generate concise content summaries for extracted workspace documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .llm_generation import _llm_generate
    from .logger import emit_progress
except ImportError:
    from llm_generation import _llm_generate
    from logger import emit_progress


def generate_summary(filename: str, content: str) -> str:
    """Summarize document text via optional LLM or deterministic first-paragraph fallback."""
    snippet = content[:1500].strip()
    if not snippet:
        return f"Document: {filename}"
    res = _llm_generate(
        system_prompt="Summarize the document in 1-2 concise sentences.",
        user_prompt=f"Filename: {filename}\n\nContent:\n{snippet}",
        max_tokens=256,
    )
    if res and not res.startswith("[ERROR]"):
        return res
    first_lines = " ".join(line.strip() for line in snippet.splitlines() if line.strip())
    return first_lines[:240]


def summarize_content(extract_file: Path, metadata_file: Path) -> None:
    emit_progress("DocumentOrganizer", "SUMMARIZE", f"Loading {extract_file.name}")

    with open(extract_file, encoding="utf-8") as f:
        data = json.load(f)

    content_summaries = data.get("content_summaries", {})
    if not content_summaries:
        emit_progress(
            "DocumentOrganizer",
            "SUMMARIZE",
            "No content summaries found in extract.json",
            level="ERROR",
        )
        return

    metadata: dict[str, dict[str, dict[str, str]]] = {"files": {}}
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = json.load(f)

    files_dict = metadata.setdefault("files", {})
    total = len(content_summaries)
    emit_progress("DocumentOrganizer", "SUMMARIZE", f"Found {total} files to summarize.")

    for i, (filepath, content) in enumerate(content_summaries.items()):
        if i % 5 == 0:
            emit_progress(
                "DocumentOrganizer",
                "SUMMARIZE",
                f"Generating summaries ({i}/{total})",
            )

        rel_path = Path(filepath).name
        if rel_path in files_dict and files_dict[rel_path].get("content_summary"):
            continue

        summary = generate_summary(rel_path, content)
        files_dict.setdefault(rel_path, {})["content_summary"] = summary

        if i % 10 == 0:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    emit_progress("DocumentOrganizer", "SUMMARIZE", "Finished generating content summaries.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", required=True)
    parser.add_argument("--metadata", required=True)
    args = parser.parse_args()
    summarize_content(Path(args.extract), Path(args.metadata))
