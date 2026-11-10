---
name: DocumentOrganizer
status: active
version: 3.3.1
changed_at: 2026-11-10
description: Authoritative workspace file governance and cleanup assistant. Automatically
  sorts incoming files from Queue (00_QUEUE) into 4 lifecycle folders (Planning for
  scoping & roadmaps, Executing for active delivery & live SOPs, Reference for knowledge
  libraries, and Archive for completed work), keeps your desktop clutter-free, and
  safely cleans temporary caches.
capabilities:
- automated-queue-sorting
- zero-desktop-file-governance
- workspace-cache-cleanup
- personal-and-legal-vault-management
risk_class: TIER_1
approval_checkpoints:
- scope_confirmation
- security_confirmation
---

# DocumentOrganizer Skill Catalog

## Overview
DocumentOrganizer is the **authoritative workspace file governance and cleanup engine**. It ensures that every project document has one clear, intuitive home across a 5-stage lifecycle, keeps desktops and download folders completely free of clutter, and safely removes temporary caches.

### The 5-Stage Workspace Lifecycle Folders
Every file in the workspace belongs to one of five self-explanatory lifecycle folders:

```text
00_QUEUE  ──►  10_PLANNING  ──►  20_EXECUTING  ──►  30_REFERENCE  ──►  40_ARCHIVE
(Waiting)       (Scoping)         (Doing)            (Lookup)          (History)
```

1. **`00_QUEUE` — Queue (Incoming Files Waiting to Sort)**:
   - **Purpose**: Temporary landing dock for new downloads, incoming files, or unreviewed notes.
   - **Rule**: Nothing stays in the queue permanently. Files are sorted and moved into `10_PLANNING`, `20_EXECUTING`, or `30_REFERENCE` right away.
2. **`10_PLANNING` — Planning (Proposals, Specs & Scoping)**:
   - **Purpose**: Work in the design, scoping, and planning phase.
   - **Examples**: Project proposals, rough drafts, sprint roadmaps, architecture specifications (`SPEC-*.md`), test plans.
   - **Lifecycle**: When approved to build or run, files move to `20_EXECUTING`.
3. **`20_EXECUTING` — Executing (Active Delivery & Live Operations)**:
   - **Purpose**: Active sprint execution, in-progress deliverables, and live operational workflows.
   - **Examples**: Active sprint deliverables, milestones, Standard Operating Procedures (SOPs), standing policies, live evidence.
   - **Lifecycle**: Completed deliverables move to `40_ARCHIVE`; reusable standards promote to `30_REFERENCE`.
4. **`30_REFERENCE` — Reference (Knowledge Library & Standards)**:
   - **Purpose**: Reference library, architectural blueprints, guides, and standards consulted for information.
   - **Examples**: Architecture diagrams, API specifications, engineering standards, cheat sheets, handbooks.
   - **Lifecycle**: Authoritative Single Source of Truth (SSOT) consulted for learning and fact-checking.
5. **`40_ARCHIVE` — Archive (Completed Work & Historical Records)**:
   - **Purpose**: Digital filing cabinet for past projects and retired documentation.
   - **Examples**: Completed sprints, retired versions, closed initiatives.
   - **Lifecycle**: Read-only historical storage ensuring past work is never accidentally lost.

### Backward-Compatible Zone Aliases
DocumentOrganizer supports common engineering and P.A.R.A-style zone aliases seamlessly via `templates/zone_presets.yaml`:
- `00_INBOX` -> `00_QUEUE`
- `10_SPECS` / `10_ACTIVE_TIMEBOUND` -> `10_PLANNING`
- `20_DELIVERABLES` / `20_ACTIVE_CONTINUOUS` -> `20_EXECUTING`
- `30_REFERENCE_AND_SOPS` -> `30_REFERENCE`
- `40_ARCHIVE` -> `40_ARCHIVE`

---

## Core Capabilities

- **Automatic Queue Sorting (`scripts/organizer.py`, `scripts/project_router.py`)**: Scans incoming files in `00_QUEUE` / `00_INBOX` and routes them into their proper project and destination zone based on file content and domain profiles.
- **Zero Desktop Clutter (`scripts/desktop_scanner.py`)**: Prevents files from accumulating across `Desktop/` or `Downloads/`.
- **Clean Workspace Maintenance (`scripts/hygiene.py`)**: Safe cleaner that purges temporary Python build caches (`__pycache__`, `.pytest_cache`, `.ruff_cache`), expired browser test profiles, and scratch folders while strictly protecting active work and transcripts.
- **Secure Personal & Legal Document Filing (`scripts/vault_manager.py`)**: Scaffolds and manages structured document vaults (`01_identity_personal` .. `05_dispatch_registry`) with semantic versions (`v1.0` draft, `v2.0` filed, `v3.0` issued) and SHA-256 manifest verification.
- **File Naming Standards (`scripts/naming_normalizer.py`)**: Normalizes messy file names into clean, readable ASCII names.
- **Unified Cleanup Sweeps (`scripts/sweep.py`)**: Multi-stage routine: Ingest & Protect -> Clean Ephemeral Caches -> Reclaim Scratch Debris -> Compact Local SQLite Databases.

---

## Mandatory Automation Safeguards

> [!IMPORTANT]
> **INGEST BEFORE PURGE SAFEGUARD (`FR-ORG-10`)**:
> Before running any disk cleanup or cache purge, loose files in `Downloads/` and `Desktop/` are analyzed, classified, and protected into workspace folders *prior* to cleaning temporary files.

> [!IMPORTANT]
> **ACTIVE SESSION IMMUNITY (`FR-ORG-12`)**:
> During scratch cleanup sweeps, active sessions and immutable conversation transcripts (`transcript*.jsonl`), task records (`task.md`), and walkthroughs (`walkthrough.md`) are strictly immune from modification or deletion.

---

## CLI Usage Reference

```bash
# 1. Ingress & File Sorting
python -m DocumentOrganizer organize --source "~/Downloads" --dest "~/Projects"

# 2. Workspace Cleanup Sweep (Preview Mode - Default)
python -m DocumentOrganizer sweep --root "~/Projects/MyWorkspace" --clean-projects

# 3. Workspace Cleanup Sweep (Execute Purge)
python -m DocumentOrganizer sweep --root "~/Projects/MyWorkspace" --clean-projects --execute

# 4. Personal & Legal Vault Management
python -m DocumentOrganizer vault init --vault "~/PersonalVault" --owner "Alex Example"
python -m DocumentOrganizer vault register --vault "~/PersonalVault"
python -m DocumentOrganizer vault list --vault "~/PersonalVault"
```

---

## Artifacts
- `docs/UC-001_documentorganizer.md`: Use case specification for Workspace Document Management.
- `docs/MODULE.md`: Architecture and multi-phase operational guide.
- `config/cleaner_rules.json`: Declarative rules for safe workspace cleanup.
- `templates/zone_presets.yaml`: Declarative folder templates (`mece_universal`, `personal_legal_vault`, `engineering_spec_driven`).
- `scripts/vault_manager.py`: Legal vault scaffolder and SHA-256 version registrar.
- `scripts/naming_normalizer.py`: Naming convention linter and normalizer.
- `scripts/hygiene.py`: Clean-room temporary cache and scratch engine.
- `scripts/sweep.py`: Unified multi-stage asset ingress and cleanup sweep orchestrator.
