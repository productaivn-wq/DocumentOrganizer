---
id: SKILL
title: "DocumentOrganizer Skill"
status: active
version: 1.0.0
tags: [docs, skill]
last_verified: 2026-09-08
---
# DocumentOrganizer Skill

Systematically organize any directory tree — local drives, cloud drives (OneDrive, Google Drive), network shares, or project repos. Scans folder-by-folder, file-by-file, designs a zone-based structure, moves content, and documents everything with README files and traceability matrices.

---

## 🎯 Capabilities

| Capability | Description |
|---|---|
| **Deep Scan** | Recursively scan all folders/files, report sizes, types, anomalies |
| **Visual Capture** | Generate Mermaid.js mindmaps of the directory structure |
| **Zone Design** | Propose a zone structure from presets or custom definition |
| **File-level Planning** | Per-folder plan: what moves where, what deduplicates, what stays |
| **Parallel Execution** | Execute independent zone cleanups in parallel |
| **README Generation** | Write a README.md for every folder created or significantly modified |
| **Traceability Matrices** | Project folders get a document ↔ UC ↔ status traceability table |
| **Deep Validation** | Verify directory and traceability integrity post-move |
| **Verification** | File count before/after, structural checks on all new paths |
| **Walkthrough Report** | Full before/after summary with every action taken |

---

## 📦 Zone Architecture (MECE)

Zones follow a strict MECE (Mutually Exclusive, Collectively Exhaustive) structure, designed for automated routing. Every file must logically fit into exactly one zone based on its *actionability* and *lifecycle state*.

### The Core MECE Structure
```
Workspace/
├── 00_INBOX/             # Staging area. Unsorted, raw, or pending triage.
├── 10_ACTIVE_TIMEBOUND/  # ACTIVE + TIME-BOUND: Work with a clear deadline/goal (e.g. Projects).
├── 20_ACTIVE_CONTINUOUS/ # ACTIVE + CONTINUOUS: Ongoing responsibilities with no end date (e.g. Areas).
├── 30_REFERENCE/         # INACTIVE + REFERENCE: Shared assets, templates, general knowledge.
└── 40_ARCHIVE/           # INACTIVE + HISTORICAL: Completed items, deprecated assets.
```

### Why this is MECE:
- **Actionable vs Non-Actionable:** Active zones require action. Reference & Archives do not. (Mutually Exclusive)
- **Time-bound vs Continuous:** Timebound work ends. Continuous responsibilities persist. (Mutually Exclusive)
- **Reference vs Historical:** References are useful now. Archives are historical records. (Mutually Exclusive)
- **Inbox:** Captures anything not yet processed. (Collectively Exhaustive)

### The Universal Application of MECE
Unlike older versions of this skill which used arbitrary presets (`team_shared`, `project_repo`, `personal_drive`), this core MECE structure is now **universal**. 

Whether you are organizing a local hard drive, a shared corporate Google Drive, or a software git repository, the top-level zones remain exactly the same. This ensures mental scalability and compatibility with the `PP.SSS.TT.TT` document naming standard.

---

## 📋 Process

### Phase 0 — Registry Engine
1. Initialize and maintain `registry.json` via `jd_registry.py` (The Master Map).
2. Auto-discover project folders and map them to a 2-digit Project ID (`PP`).
3. Manage the auto-increment sequence (`SSS`) to ensure no ID collisions across the entire ecosystem.

### Phase 1 — Scan & Visualize
1. Run scanner script (`scan.py` or `scan.ps1`) on target directory
2. Run visualization script (`visualize.py`) to generate `visual_tree.md`
3. Identify large files (> 50 MB), duplicates (same name + size), empty folders, misplaced files
4. Map current folder → proposed zone for each item

### Phase 2 — Plan
1. Write `implementation_plan.md` grouping actions by zone
2. For each zone: list exact moves (From → To), README targets, traceability targets
3. **Require user review before execution**

### Phase 3 — Execute (Parallel)
Run independent zones concurrently:
- Use PowerShell jobs on Windows, or Python `concurrent.futures` cross-platform
- Each zone is an independent work stream

### Phase 4 — Document
Write README.md for every folder that was created or substantially changed:
- **Simple folders**: 1-paragraph description + file inventory table
- **Project folders**: description + subfolders table + **Traceability Matrix**
- **Master Registry**: Update `99/01_Registry.md` with all new assignments

### Phase 5 — Verify
- File count before vs after
- Structural checks: confirm all expected directories exist
- Confirm empty folders removed, duplicates eliminated

---

## 🏷️ Naming Standard & Classification (PP.SSS.TT.TT)

DocumentOrganizer enforces a **Faceted Classification** system inspired by **ISO 19650** and **Ranganathan's PMEST**, adapted for knowledge work using **Bloom's Taxonomy**.

**Format:** `PP.SSS.TT.TT - YYYYMMDD - Semantic_Title.ext`

- `PP` = Project ID (2 digits, managed by registry)
- `SSS` = Sequence (3 digits, auto-incrementing per project)
- `TT` = Purpose Tag (1-2 tags from the MECE vocabulary below)
- `YYYYMMDD` = Creation/Event Date
- `Semantic_Title` = Clean, underscore-separated title (NO spaces)

### The 6 Purpose Categories (Controlled Vocabulary)
| Tag | Verb | Bloom's Root | Classification Rule (Why does this exist?) |
|---|---|---|---|
| `IN` | **Investigate** | Analyze | Created to **LEARN** something new (Research, data). |
| `PL` | **Plan** | Create | Created to **DECIDE** a course of action (Strategy, PRDs). |
| `BU` | **Build** | Apply | Created to **MAKE** something work (Code, designs). |
| `CH` | **Check** | Evaluate | Created to **VERIFY** correctness (QA, test results). |
| `SH` | **Share** | - | Created to **TELL** someone something (Meetings, memos). |
| `RE` | **Record** | Remember | Created to **PRESERVE** for future lookup (Reference, finance). |

**Multi-Tagging:** A file must have 1 Primary Tag. It may have 1 Secondary Tag if it strongly serves a dual purpose (e.g., `11.048.IN.RE` for financial research).

---

## 📝 README Templates

See `templates/README_simple.md` and `templates/README_project.md`.

---

## 🔧 Cross-Platform Patterns

### PowerShell (Windows)
```powershell
# Safe move with LiteralPath (handles Unicode names, brackets)
Move-Item -LiteralPath "C:\path\[file].docx" -Destination "C:\dest\" -Force

# Move entire directory tree
robocopy $source $dest /E /MOVE /NP /NFL /NDL /NJH /NJS

# Create directory before moving into it
New-Item -ItemType Directory -Path "C:\dest\NewFolder" -Force | Out-Null
```

### Python (Cross-Platform)
```python
from pathlib import Path
import shutil

# Safe move (handles Unicode, special chars)
shutil.move(str(source_path), str(dest_path))

# Create directory tree
dest_path.mkdir(parents=True, exist_ok=True)

# Count files recursively
file_count = sum(1 for _ in root.rglob("*") if _.is_file())
```

---

## ⚠️ Rules (Non-Negotiable)

1. **Never delete** — only move. Exception: exact duplicates (same filename + size)
2. **Use safe path handling** — `LiteralPath` (PS) or `pathlib` (Python) for Unicode/special chars
3. **Create target dir first** before moving files
4. **Respect exclusions** — honor `exclude_patterns` from config (game saves, system folders, `.git`, etc.)
5. **Archive zones are read-only** — never modify their contents
6. **_inbox is temporary** — nothing lives there permanently
7. **Always get user approval** before executing Phase 3

---

## 🚫 Default Exclusion Patterns

These paths are skipped unless explicitly overridden:
- `.git/`, `.svn/`, `node_modules/`, `__pycache__/`
- `$RECYCLE.BIN/`, `System Volume Information/`
- Application and media cache folders in `Documents/`
- Windows system folders (Desktop, Music) — left at root

---

## 💡 Usage Examples

### Trigger Phrases
- "Organize my documents in [path]"
- "Clean up [drive/folder] folder by folder"
- "Structure [path] and add README files"
- "Deep scan [path] and propose a zone plan"
- "Reorganize my G Drive / OneDrive / project folder"

### Invocation Pattern
```
1. Read SKILL.md (this file)
2. Scan the target directory  (Phase 1 - scan.py)
3. Extract text content via LiteParseSkill  (Phase 2 - extract.py)
4. LLM parses content and presents zone plan in implementation_plan.md  (Phase 3 - plan.py)
5. Wait for user approval
6. Execute all zones in parallel  (Phase 4 - organizer.py)
7. Write READMEs + traceability matrices  (Phase 5 - readme_writer.py)
8. Run verification  (Phase 6 - verify.py)
9. Present walkthrough.md
```

---

## 🗂️ Key Files

| File | Purpose |
|---|---|
| `SKILL.md` | This file — skill definition and process |
| `scripts/scan.ps1` | PowerShell: scan a directory, output anomaly report |
| `scripts/scan.py` | Python: cross-platform scan with same output |
| `scripts/extract.py` | Python: bridge script that extracts text using LiteParseSkill |
| `scripts/plan.py` | Python: generates tasks.json with LLM semantics |
| `scripts/organizer.py` | Python: executes multi-threaded deduplication and moves |
| `scripts/verify.ps1` | PowerShell: count files, check structural integrity |
| `scripts/verify.py` | Python: cross-platform verification |
| `templates/zone_presets.yaml` | Predefined zone configurations |
| `templates/README_simple.md` | Template for simple folder READMEs |
| `templates/README_project.md` | Template for project folder READMEs with traceability |
| `examples/onedrive_personal_2026.md` | Reference: OneDrive reorganization (4,971 files) |
| `examples/gdrive_personal_2026.md` | Reference: G Drive reorganization |

---

## 📦 Prerequisites

- **Option A (Windows)**: PowerShell 5.1+ and `robocopy` (built-in)
- **Option B (Cross-platform)**: Python 3.8+ with `pathlib` and `shutil` (stdlib)
- Write access to the target directory
- No external dependencies required

---

## 🔗 Related Skills

- **SourceSynth** — for deeper document synthesis and revision control
- **Knowledge Graph Indexers** — consumes generated READMEs and traceability matrices
- **CI Linters** — validates generated Markdown and directory depth invariants
