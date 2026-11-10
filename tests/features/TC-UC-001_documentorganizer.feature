# Auto-generated Gherkin feature for DocumentOrganizer — UC-001: Core Capabilities
# UC Reference: UC-001
# Generated: 2026-09-10

@skill @documentorganizer @uc-001
Feature: DocumentOrganizer — Core Capabilities
  As a user of the workspace environment
  I want to use the DocumentOrganizer skill for 'Core Capabilities'
  So that I can authoritative single source of truth (ssot) for document, multimedia photo, and digital asset lifecycle management across project mece zones. enforces automated ingress ingestion, generated process ar

  Background:
    Given the workspace environment is running
    And the "DocumentOrganizer" skill is registered and available


  @TC-UC-001-S01 @happy-path
  Scenario: Happy Path - Core Capabilities
    Given the "DocumentOrganizer" skill is initialized
    And the system has valid configuration
    When Single Source of Truth (SSOT) Management: Establishes canonical registries, manifests (manifest.json), and markdown catalogs (README.md) for all project documents, manuscripts, datasets, and empirical evidence.
    And Automated Ingress Ingestion: Monitors and processes incoming assets from external sources (Downloads/, browser downloads, Zalo/Drive attachments, staging folders) and routes them into project repositories without manual intervention.
    And Generated & Process Artifacts Governance: Manages the complete lifecycle of all files and folders generated during execution (PDF compilations, intermediate HTML previews, cropped graphics, tabular extracts, chat dumps, scratch scripts). Enforces strict boundary isolation so that intermediate artifacts never pollute primary manuscript directories (docs/).
    And Strict Canonical Naming Linter & Normalizer (scripts/naming_normalizer.py): Detects and converts nonstandard naming patterns (Vietnamese diacritics, spaces, parentheses, irregular casing, missing numerical prefixes) into deterministic pure ASCII snake_case or structured CC_NAME patterns across both files and directories.
    And Multimedia & Photo Ingestion (scripts/photo_ingest.py): Computes SHA256 hashes, extracts dimensions, formats, capture timestamps, and EXIF metadata with purePython fallback.
    And Intelligent Project Routing (scripts/project_router.py): Maps assets to target project workspaces (e.g. 40_FIELD_RESEARCH) and MECE lifecycle zones using semantic keyword profiles and task associations.
    And Deduplication & Hygiene: Isolates duplicate physical files, strips redundant artifacts, and enforces standardized snake_case file naming.
    And Depth & Hierarchy Policy (scripts/depth_policy.py): Enforces deterministic MECE directory depth standards (zone/category/document.ext).
    Then the system completes 'Core Capabilities' successfully

  @TC-UC-001-S02 @error-handling
  Scenario: Alternate Flow - Invalid Input — System validates inputs and returns a structured error with field-level guidance. Gherkin: `@TC-UC-001-S02`
    Given the "DocumentOrganizer" skill is initialized
    When the user triggers alternate flow "Invalid Input — System validates inputs and returns a structured error with field-level guidance. Gherkin: `@TC-UC-001-S02`"
    Then the system handles the scenario correctly

  @TC-UC-001-S03 @error-handling
  Scenario: Alternate Flow - Dependency Unavailable — System retries up to 3 times with exponential backoff, then falls back. Gherkin: `@TC-UC-001-S03`
    Given the "DocumentOrganizer" skill is initialized
    When the user triggers alternate flow "Dependency Unavailable — System retries up to 3 times with exponential backoff, then falls back. Gherkin: `@TC-UC-001-S03`"
    Then the system handles the scenario correctly

  @TC-UC-001-S04 @error-handling
  Scenario: Alternate Flow - Timeout — System terminates execution after configured timeout and reports partial results. Gherkin: `@TC-UC-001-S04`
    Given the "DocumentOrganizer" skill is initialized
    When the user triggers alternate flow "Timeout — System terminates execution after configured timeout and reports partial results. Gherkin: `@TC-UC-001-S04`"
    Then the system handles the scenario correctly

  @TC-UC-001-ERR01
  Scenario: Graceful degradation on dependency failure during Core Capabilities
    Given the "DocumentOrganizer" skill is initialized
    And a required dependency is unavailable
    When the user invokes the skill for 'Core Capabilities'
    Then the system attempts a fallback mechanism
    And reports the degradation to the caller
