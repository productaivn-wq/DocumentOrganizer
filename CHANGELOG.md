# Changelog

## [3.3.1] - 2026-11-10

### Changed & Hardened
- **Standalone Open-Source Portability**: Configured `[tool.setuptools.package-dir]` and `document-organizer` console script in `pyproject.toml` so `pip install -e .` and `python -m DocumentOrganizer` work out of the box from any working directory.
- **Generic Starter Domain Profiles**: Standardized default `ProjectRouter` and `TraceabilityContextResolver` domain profiles (`10_PRODUCT_PLATFORM` .. `60_DEV_EXPERIENCE`) with zero-dependency discrete-choice token scoring (`scripts/project_router.py`).
- **Clean-Room Module Trim**: Removed unused legacy experimental adapters and external sibling-tool hooks, leaving a focused, portable standard-library + Pydantic/PyYAML/LangGraph core.

## [3.3.1] - 2026-11-10

### Changed & Hardened
- **Standalone Open-Source Portability**: Configured `[tool.setuptools.package-dir]` and `document-organizer` console script in `pyproject.toml` so `pip install -e .` and `python -m DocumentOrganizer` work out of the box from any working directory.
- **Generic Starter Domain Profiles**: Standardized default `ProjectRouter` and `TraceabilityContextResolver` domain profiles (`10_PRODUCT_PLATFORM` .. `60_DEV_EXPERIENCE`) with zero-dependency discrete-choice token scoring (`scripts/project_router.py`).
- **Clean-Room Module Trim**: Removed unused legacy experimental adapters and external sibling-tool hooks, leaving a focused, portable standard-library + Pydantic/PyYAML/LangGraph core.

## [3.3.0] - 2026-11-10

### Renamed & Unified
- **Repository Renamed**: `FileGovernance-Skill` (`v1.0.0`) -> **`DocumentOrganizer`** (`v3.3.0`), unifying the open-source Two-Axis File Governance & Knowledge Graph framework with the full autonomous 5-Zone MECE Workspace Lifecycle Engine.

### Added
- **5-Stage MECE Lifecycle Engine (`scripts/organizer.py`, `scripts/project_router.py`, `templates/zone_presets.yaml`)**: Automated routing across `00_QUEUE` / `00_INBOX`, `10_PLANNING` / `10_SPECS`, `20_EXECUTING` / `20_DELIVERABLES`, `30_REFERENCE`, and `40_ARCHIVE` with Depth <= 2 enforcement (`scripts/depth_policy.py`).
- **Typed LangGraph Workflow & Traceability Resolver (`core/organizer_graph.py`, `core/traceability_resolver.py`)**: Durable `StateGraph` orchestration with checkpointing, retry policies, Saga compensation, Johnny.Decimal sequence allocation (`scripts/jd_registry.py`), and semantic project affinity matching.
- **Clean-Room Workspace Hygiene & Multi-Stage Sweep (`scripts/hygiene.py`, `scripts/sweep.py`, `config/cleaner_rules.json`)**: Ingest-Before-Purge safeguard (`FR-ORG-10`), Active Session Immunity (`FR-ORG-12`), cache reclamation (`__pycache__`, `.pytest_cache`, `.ruff_cache`), and junction integrity checks.
- **Personal & Legal Vault Manager (`scripts/vault_manager.py`)**: Semantic document versioning (`v1.0` draft -> `v2.0` filed -> `v3.0` issued) with SHA-256 cryptographic manifest sealing.
- **Unified Package & CLI (`python -m DocumentOrganizer`, `pyproject.toml`)**: Deterministic `--json` CLI interface (`organize`, `sweep`, `hygiene`, `vault`, `watch`, `reorganize`) and portable `pytest` suite (`90+` unit, integration, and adversarial tests).

---

: DocumentOrganizer

All notable changes to this skill are documented here.

## [2026-09-26] - v2.2.0
### Fixed
- **SSOT MECE Zone Routing Bug**: Fixed critical flaw in `scripts/project_router.py` where destination paths generated non-MECE root folders (`docs/`, `data/photos/`, `media/`) rather than routing to canonical MECE zones (`20_ACTIVE_CONTINUOUS/docs`, `20_ACTIVE_CONTINUOUS/media/photos`, `20_ACTIVE_CONTINUOUS/data`).
- **Dynamic Portfolio Discovery**: Upgraded `ProjectRouter` to dynamically discover projects from `portfolio_manifest.json` and directory inspection.
- **MECE Invariant Guard (`sanitize_mece_zone`)**: Guaranteed that 100% of generated routes reside strictly within `VALID_MECE_ZONES` (`00_INBOX`, `10_ACTIVE_TIMEBOUND`, `20_ACTIVE_CONTINUOUS`, `30_REFERENCE`, `40_ARCHIVE`).
- **Stopword Filtering & Matching Precision**: Prevented false positive project routing on generic keywords (`file`, `skill`, `tools`, `module`).
- **Unit Test Verification**: Added `tests/test_project_router.py` asserting dynamic discovery, MECE zone validation, and photo/doc routing across projects.

## [2026-09-09] - v1.3.2
### Changed
- Harmonize organizer graph, git adapter, and depth policy

## [2026-09-09] - v1.3.1
### Changed
- Harmonize organizer graph, git adapter, and depth policy

## [2026-09-08] - v1.3.0
### Added
- `scripts/naming_normalizer.py`: High-performance canonical naming linter and normalizer enforcing pure ASCII, standardized `snake_case`, zero spaces, diacritic normalization, and structured prefix conventions (`FR-ORG-09`).
- **Generated Assets & Process Artifacts Governance** (`FR-ORG-08`): Extended SSOT governance from external downloads to internally generated files and folders created during workflow processes (HTML previews, compiled PDFs, cropped graphics, tabular extracts, raw data dumps). Prevents pollution of root documentation directories.

### Changed
- Upgraded `SKILL.md`, `UC-001`, and `functional_requirements.md` to formalize dual governance (Ingress + Generated Assets) and strict naming rules.

## [2026-09-08] - v1.2.0
### Changed
- Re-architected skill identity from narrow "Zero Desktop Invariant" tool to the **authoritative Single Source of Truth (SSOT) for Document & Digital Asset Management** across all project lifecycles and MECE zones.
- Updated `SKILL.md`, `docs/UC-001_documentorganizer.md`, and `docs/functional_requirements.md` to enshrine SSOT mandate (`FR-ORG-06`).
- Established the **Automated Ingress Invocation Invariant** (`FR-ORG-07`): Mandates automatic execution of DocumentOrganizer during Phase 6 (`Approve & Integrate`) whenever new external files or media enter the workspace before lifecycle closure.

## [2026-09-08] - v1.1.0

### Changed
- OPT-APEX: YAML frontmatter mass-standardization and AST docstring hydration

## [2026-09-07] - v1.0.0
### Added
- `scripts/photo_ingest.py`: Multimedia and photo ingestion engine extracting dimensions, format, SHA-256 hashes, and EXIF metadata with pure-Python binary fallback.
- `scripts/desktop_scanner.py`: Windows Desktop and OneDrive Desktop ingress scanner enforcing the Zero Desktop Invariant.
- `scripts/project_router.py`: Intelligent project routing engine mapping files and fieldwork evidence to canonical project MECE zones.
- `scripts/depth_policy.py`: 3-layer MECE document depth standard auditor.
- `tests/test_photo_ingest_and_desktop_scanner.py`: Comprehensive test suite for multimedia extraction and desktop scanning.

### Changed
- `scripts/extract.py`: Integrated `PhotoIngestEngine` for first-class citizen image extraction.
- `scripts/scan.py` & `scripts/organizer.py`: Resilient import path handling for `get_file_hash`.

## [2026-07-07] - v0.1.2
### Changed
- Refactor watcher task registration script to use python.exe with hidden window style in Startup folder

## [2026-07-07] - v0.1.1
### Changed
- Fix nightly execution failures with --graceful-no-op flag and daemonize file watcher

## [2026-06-25] - v0.1.0
### Changed
- Aligned version with SKILL.md.

## [2026-05-19] - v1.0.6856
### Added
- Initial changelog created for `DocumentOrganizer` at v1.0.6856.
