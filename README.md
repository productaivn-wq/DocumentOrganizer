# DocumentOrganizer (`v3.3.1`)

> **Governance-Driven 5-Zone MECE Workspace Organization, Clean-Room Hygiene, Legal Vault Management & Knowledge Graph Lineage Engine for Human-AI Workflows.**
> *(Formerly published as `FileGovernance-Skill` v1.0.0 — automatically redirected by GitHub)*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.3.1-success.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](pyproject.toml)
[![Architecture](https://img.shields.io/badge/Lifecycle-5--Zone_MECE-orange.svg)](SKILL.md)

---

## Executive Summary

Modern engineering teams and AI-assisted knowledge workers face two symmetrical failure modes:
1. **Workspace & Desktop Entropy**: Unstructured downloads, duplicate drafts (`spec_final_v3.docx`), and ephemeral build/agent caches scattered across `Desktop/`, `Downloads/`, and nested project folders where neither humans nor AI agents can tell active truth from obsolete debris.
2. **The Unstructured RAG / Knowledge Graph Illusion**: Indexing chaotic folders into Obsidian or vector databases produces noisy graphs without lifecycle state, artifact lineage, or authoritative Single Source of Truth (SSOT) boundaries.

> **Foundational Law**: *A Knowledge Graph cannot fix file chaos. Files require deterministic **governance** before they can become reliable **nodes**.*

**DocumentOrganizer (`v3.3.1`)** bridges operational file-system hygiene directly to AI coding agents and CLI workflows, LangGraph workflows, and GraphRAG / Obsidian vaults.

---

## Two-Axis Architecture & 5-Zone MECE Lifecycle

```text
       KNOWLEDGE AXIS (Domain Ontology, Johnny.Decimal & Artifact Lineage)
             ^
             |     [Specs, Decisions, Architectures, Deliverables, Vault Assets]
             |        - Primary Keys: {PROJECT_ID}.{STAGE}.{SEQ}
             |        - SHA-256 Content Provenance & Bidirectional Traceability
             |
-------------+----------------------------------------------------------> LIFECYCLE AXIS
             |  00_QUEUE/INBOX -> 10_PLANNING -> 20_EXECUTING -> 30_REFERENCE -> 40_ARCHIVE
             |    (Landing)        (Scoping)       (Active)        (SSOT)        (History)
```

### The 5 Self-Explanatory Workspace Zones (`Depth <= 2`)

| Zone (Standard / Harness Alias) | Role | Lifecycle Rule |
| :--- | :--- | :--- |
| **`00_QUEUE`** / **`00_INBOX`** | Incoming landing dock for downloads, client drops & raw notes | Transient only — triaged into `10_`, `20_`, or `30_` immediately |
| **`10_PLANNING`** / **`10_SPECS`** | Proposals, roadmaps, `SPEC-*.md`, Gherkin `.feature` & test plans | Promotes to `20_EXECUTING` once authorized |
| **`20_EXECUTING`** / **`20_DELIVERABLES`** *(+ `10_ACTIVE_TIMEBOUND` / `20_ACTIVE_CONTINUOUS`)* | Active sprint deliverables, living SOPs & operational evidence | Promotes reusable standards to `30_REFERENCE`; archives closed work to `40_ARCHIVE` |
| **`30_REFERENCE`** | Authoritative knowledge library, standards, blueprints & handbooks | Curated SSOT consulted by humans and RAG/GraphRAG indexers |
| **`40_ARCHIVE`** | Read-only historical records, superseded versions & session scratch | Immutable retention with SHA-256 integrity |

---

## Key Capabilities in `v3.3.1`

- **Intelligent Portfolio & Zone Router (`scripts/project_router.py`, `scripts/organizer.py`)**: Routes documents, screenshots, recordings, and archives into the right project and MECE zone using domain keyword profiles, Johnny.Decimal IDs (`scripts/jd_registry.py`), and discrete-choice confidence thresholds.
- **Typed LangGraph Workflow (`core/organizer_graph.py`, `core/traceability_resolver.py`)**: Durable `StateGraph` (`scan_target -> resolve_traceability -> generate_plan`) with checkpointing, bounded retries, Saga rollback compensation, and graceful zero-dependency fallback.
- **Clean-Room Hygiene & Unified Sweep (`scripts/hygiene.py`, `scripts/sweep.py`)**: Reclaims Python/test caches (`__pycache__`, `.pytest_cache`, `.ruff_cache`) and stale scratch debris while enforcing **Ingest-Before-Purge (`FR-ORG-10`)** and **Active Session Immunity (`FR-ORG-12`)**.
- **Personal & Legal Vault Manager (`scripts/vault_manager.py`)**: Scaffolds structured private vaults with semantic legal versioning (`v1.0` draft, `v2.0` filed, `v3.0` issued) and SHA-256 `manifest.json` sealing.
- **File Naming Normalizer & Depth Policy (`scripts/naming_normalizer.py`, `scripts/depth_policy.py`)**: Normalizes messy filenames into clean ASCII/PDCA conventions (`{PROJECT_ID}.{STAGE}.{SEQ} - {YYYYMMDD} - {Title}.{ext}`) and audits `Depth <= 2` compliance.
- **Multi-Directory Real-Time Watcher (`scripts/watch.py`, `scripts/watch_supervisor.py`)**: Optional background daemon watching `Downloads/`, `Desktop/`, and project `00_INBOX/` folders while ignoring partial downloads (`.crdownload`, `~$*`, `desktop.ini`).

---

## Installation & Quickstart

```bash
git clone https://github.com/productaivn-wq/DocumentOrganizer.git
cd DocumentOrganizer
pip install -e ".[dev,graph,watch]"
```

### CLI Usage

```bash
# 1. Check CLI version & subcommands (deterministic --json supported)
python -m DocumentOrganizer --version --json

# 2. Organize incoming files into 5-zone MECE project folders
python -m DocumentOrganizer organize --source "~/Downloads" --dest "~/Projects"

# 3. Preview a safe workspace cleanup sweep (dry-run by default)
python -m DocumentOrganizer sweep --root "~/Projects/MyWorkspace" --clean-projects

# 4. Execute workspace cleanup sweep after reviewing dry-run
python -m DocumentOrganizer sweep --root "~/Projects/MyWorkspace" --clean-projects --execute

# 5. Initialize & seal a SHA-256 versioned Personal / Legal Vault
python -m DocumentOrganizer vault init --vault "~/PersonalVault" --owner "Alex Example"
python -m DocumentOrganizer vault register --vault "~/PersonalVault"
python -m DocumentOrganizer vault list --vault "~/PersonalVault"
```

### Using as an AI Agent Skill

Symlink or copy this repository into your agent's skills directory:
- **Claude Code**: `~/.claude/skills/DocumentOrganizer`
- **Gemini / Generic Agent Skills**: `~/.config/agent-skills/DocumentOrganizer`
- **Codex**: `~/.codex/skills/DocumentOrganizer`

See [`SKILL.md`](SKILL.md), [`PROJECT_ORGANIZATION.md`](PROJECT_ORGANIZATION.md), and [`references/historical_lineage.md`](references/historical_lineage.md) for agent prompt contracts and theoretical foundations (*Ranganathan PMEST, ISO 15489, ISO 19650, Johnny.Decimal, Forte P.A.R.A, Deming PDCA*).

---

## Verification & Testing

Run the full portable test suite (`90+` unit, LangGraph workflow, hygiene, vault, and adversarial security tests) and linter:

```bash
pytest
ruff check .
```

---

## License

Released under the [MIT License](LICENSE). Contributions, issues, and architectural discussions are welcome!
