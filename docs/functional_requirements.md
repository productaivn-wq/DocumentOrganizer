# Functional Requirements — DocumentOrganizer

| Field | Value |
|---|---|
| **Skill** | DocumentOrganizer |
| **UC Coverage** | UC-001 |
| **Generated** | 2026-09-10 |
| **Standard** | UC 3.0 / RequirementsTraceKit |

## FR Catalog

| FR-ID | Requirement (The system SHALL...) | Type | UC | Priority |
|---|---|---|---|---|
| FR-001 | The system SHALL Authoritative Single Source of Truth (SSOT) for document, multimedia photo, and digital asset lifecycle management across project MECE zones. Enforces automated ingress ingestion, generated process artifact governance, strict canonical naming normalization, taxonomy routing, deduplication, metadata . | Mandatory | UC-001 | High |
| FR-002 | The system SHALL Single Source of Truth (SSOT) Management: Establishes canonical registries, manifests (manifest.json), and markdown catalogs (README.md) for all project documents, manuscripts, datasets, and empirical evidence. | Mandatory | UC-001 | High |
| FR-003 | The system SHALL Automated Ingress Ingestion: Monitors and processes incoming assets from external sources (Downloads/, browser downloads, Zalo/Drive attachments, staging folders) and routes them into project repositories without manual intervention. | Mandatory | UC-001 | High |
| FR-004 | The system SHALL Generated & Process Artifacts Governance: Manages the complete lifecycle of all files and folders generated during execution (PDF compilations, intermediate HTML previews, cropped graphics, tabular extracts, chat dumps, scratch scripts). Enforces strict boundary isolation so that. | Mandatory | UC-001 | High |
| FR-005 | The system SHALL Strict Canonical Naming Linter & Normalizer (scripts/naming_normalizer.py): Detects and converts non-standard naming patterns (Vietnamese diacritics, spaces, parentheses, irregular casing, missing numerical prefixes) into deterministic pure ASCII snake_case or structured CC_NAME . | Mandatory | UC-001 | High |
| FR-ORG-13 | The system SHALL integrate Discrete-Choice discrete choice routing in project_router.py with confidence gates (>=0.65 probability, >=0.20 margin) for autonomous asset placement into project MECE zones. | Mandatory | UC-005 | High |
| FR-ORG-14 | The system SHALL execute an autonomous library custodian review after asset placement to evaluate unfiled assets in 00_INBOX against the destination cluster and re-file candidates with similarity >=0.80. | Mandatory | UC-005 | High |

## Non-Functional Requirements

| NFR-ID | Requirement | Category |
|---|---|---|
| NFR-001 | The system SHALL complete within the configured timeout. | Performance |
| NFR-002 | The system SHALL log all execution events for auditability. | Observability |
| NFR-003 | The system SHALL NOT modify state without explicit user approval where required. | Safety |
| NFR-004 | The system SHALL degrade gracefully when dependencies are unavailable. | Resilience |
| NFR-005 | The system SHALL implement strict validation on all input payloads. | Security |

## Verification
- Each FR maps to at least one Gherkin scenario in the corresponding `.feature` file
- UC distribution: UC-001
- Priority: High = must-have, Medium = should-have, Low = nice-to-have
