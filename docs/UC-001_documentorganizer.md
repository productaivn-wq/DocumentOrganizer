# UC-001: Core Capabilities

## Use Case Identification
| Field | Value |
|---|---|
| **UC ID** | UC-001 |
| **Title** | Core Capabilities |
| **Skill** | DocumentOrganizer |
| **Version** | 1.3.2 |
| **Status** | Draft (Auto-Generated) |
| **Created** | 2026-09-10 |
| **Generator** | DirectAssetGenerator v2.1 |

## Goal
Enable the `DocumentOrganizer` skill to support **Core Capabilities** operations within the workspace environment.

## Scope
In-scope: All `Core Capabilities` operations executed by the `DocumentOrganizer` skill.
Out-of-scope: External system configuration; hardware provisioning.

## Level
User Goal

## Description
DocumentOrganizer: Core Capabilities

## Actors
| Actor | Type | Description |
|---|---|---|
| **Operator** | Primary | The developer or agent invoking the skill |
| **System** | Supporting | The workspace environment runtime |
| **LLM Provider** | External | AI model backend (Gemini/OpenAI/Claude) |

## Preconditions
1. The workspace environment is running
2. The skill `DocumentOrganizer` is installed and registered
3. Required dependencies are available
4. Caller has appropriate permissions

## Main Success Flow
1. Single Source of Truth (SSOT) Management: Establishes canonical registries, manifests (manifest.json), and markdown catalogs (README.md) for all project documents, manuscripts, datasets, and empirical evidence.
2. Automated Ingress Ingestion: Monitors and processes incoming assets from external sources (Downloads/, browser downloads, Zalo/Drive attachments, staging folders) and routes them into project repositories without manual intervention.
3. Generated & Process Artifacts Governance: Manages the complete lifecycle of all files and folders generated during execution (PDF compilations, intermediate HTML previews, cropped graphics, tabular extracts, chat dumps, scratch scripts). Enforces strict boundary isolation so that intermediate artifacts never pollute primary manuscript directories (docs/).
4. Strict Canonical Naming Linter & Normalizer (scripts/naming_normalizer.py): Detects and converts non-standard naming patterns (Vietnamese diacritics, spaces, parentheses, irregular casing, missing numerical prefixes) into deterministic pure ASCII snake_case or structured CC_NAME patterns across both files and directories.
5. Multimedia & Photo Ingestion (scripts/photo_ingest.py): Computes SHA-256 hashes, extracts dimensions, formats, capture timestamps, and EXIF metadata with pure-Python fallback.
6. Intelligent Project Routing (scripts/project_router.py): Maps assets to target project workspaces (e.g. 40_FIELD_RESEARCH) and MECE lifecycle zones using semantic keyword profiles and task associations.
7. Deduplication & Hygiene: Isolates duplicate physical files, strips redundant artifacts, and enforces standardized snake_case file naming.
8. Depth & Hierarchy Policy (scripts/depth_policy.py): Enforces deterministic MECE directory depth standards (zone/category/document.ext).


## Success Guarantee
The operation completes and results are persisted to the designated output path.

## Minimum Guarantee
Execution is logged with status and error details, even on failure.

## Alternate Flows
- **AF-1: Invalid Input** — System validates inputs and returns a structured error with field-level guidance. Gherkin: `@TC-UC-001-S02`
- **AF-2: Dependency Unavailable** — System retries up to 3 times with exponential backoff, then falls back. Gherkin: `@TC-UC-001-S03`
- **AF-3: Timeout** — System terminates execution after configured timeout and reports partial results. Gherkin: `@TC-UC-001-S04`

## Postconditions
1. Skill execution is logged with duration and status
2. Results are available to the caller at the designated path
3. No system state corruption on failure

## Business Rules
- BR-1: Skill must complete within configured timeout (default: 300s)
- BR-2: All outputs must be written to the designated directory under `skill_path`
- BR-3: Errors must be propagated with actionable, human-readable messages
- BR-4: No silent failures — all exceptions must be caught and logged

## Use-Case Slices
| Slice | Scenario | TC Reference | Priority |
|---|---|---|---|
| Slice-1 | Happy Path — Core Capabilities | `@TC-UC-001-S01` | Must-Pass |
| Slice-2 | Invalid Input | `@TC-UC-001-S02` | Must-Pass |
| Slice-3 | Dependency Failure | `@TC-UC-001-S03` | Should-Pass |
| Slice-4 | Graceful Degradation | `@TC-UC-001-ERR01` | Should-Pass |

## Related Scripts
- `cleanup.py`
- `consolidate.py`
- `consolidate_workspace.py`
- `contextualize.py`
- `depth_policy.py`
- `desktop_scanner.py`
- `extract.py`
- `hydrate_frontmatter.py`
- `jd_registry.py`
- `logger.py`
- `loop_pipeline.py`
- `naming_normalizer.py`
- `organizer.py`
- `photo_ingest.py`
- `plan.py`
- `project_router.py`
- `prompts.py`
- `readme_writer.py`

## Traceability
- **Gherkin**: `tests/features/TC-UC-001_documentorganizer.feature`
- **Test Data**: `tests/data/TC-UC-001_data.json`
- **Functional Requirements**: `docs/functional_requirements.md`

## Revision History
| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-09-10 | DirectAssetGenerator | Auto-generated scaffold |
