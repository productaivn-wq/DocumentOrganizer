# Auto-generated Gherkin — DocumentOrganizer (Function-level)
# Generated: 2026-05-18

@skill @documentorganizer
Feature: DocumentOrganizer — Function-level BDD
  As a developer
  I want each public function in DocumentOrganizer to behave correctly
  So that dependents can rely on its contract

  Background:
    Given the workspace environment is running
    And the "DocumentOrganizer" skill is registered


  @TC-001 @documentorganizer @cleanup
  Scenario: cleanup_directory — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `cleanup.py` is importable
    When `cleanup_directory()` is called with valid params {"target_dir": "<example_target_dir>", "archive_root": "<example_archive_root>", "days": "<example_days>", "dry_run": "<example_dry_run>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-001-ERR @documentorganizer
  Scenario: cleanup_directory — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `cleanup_directory()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-002 @documentorganizer @cleanup
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `cleanup.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-002-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-003 @documentorganizer @consolidate
  Scenario: get_folder_fingerprint — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate.py` is importable
    When `get_folder_fingerprint()` is called with valid params {"directory": "<example_directory>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-003-ERR @documentorganizer
  Scenario: get_folder_fingerprint — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `get_folder_fingerprint()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-004 @documentorganizer @consolidate
  Scenario: calculate_overlap — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate.py` is importable
    When `calculate_overlap()` is called with valid params {"fp1": "<example_fp1>", "fp2": "<example_fp2>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-004-ERR @documentorganizer
  Scenario: calculate_overlap — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `calculate_overlap()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-005 @documentorganizer @consolidate
  Scenario: find_merge_candidates — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate.py` is importable
    When `find_merge_candidates()` is called with valid params {"root": "<example_root>", "threshold": "<example_threshold>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-005-ERR @documentorganizer
  Scenario: find_merge_candidates — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `find_merge_candidates()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-006 @documentorganizer @consolidate
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-006-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-007 @documentorganizer @consolidate_workspace
  Scenario: get_hash — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate_workspace.py` is importable
    When `get_hash()` is called with valid params {"file_path": "<example_file_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-007-ERR @documentorganizer
  Scenario: get_hash — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `get_hash()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-008 @documentorganizer @consolidate_workspace
  Scenario: is_auto_generated — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate_workspace.py` is importable
    When `is_auto_generated()` is called with valid params {"file_path": "<example_file_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-008-ERR @documentorganizer
  Scenario: is_auto_generated — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `is_auto_generated()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-009 @documentorganizer @consolidate_workspace
  Scenario: normalize_name — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate_workspace.py` is importable
    When `normalize_name()` is called with valid params {"name": "<example_name>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-009-ERR @documentorganizer
  Scenario: normalize_name — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `normalize_name()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-010 @documentorganizer @consolidate_workspace
  Scenario: aggressive_move — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate_workspace.py` is importable
    When `aggressive_move()` is called with valid params {"src": "<example_src>", "dest": "<example_dest>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-010-ERR @documentorganizer
  Scenario: aggressive_move — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `aggressive_move()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-011 @documentorganizer @consolidate_workspace
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `consolidate_workspace.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-011-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-012 @documentorganizer @logger
  Scenario: emit_progress — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `logger.py` is importable
    When `emit_progress()` is called with valid params {"source": "<example_source>", "phase": "<example_phase>", "message": "<example_message>", "level": "<example_level>", "progress": "<example_progress>", "log_file": "<example_log_file>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-012-ERR @documentorganizer
  Scenario: emit_progress — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `emit_progress()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-013 @documentorganizer @organizer
  Scenario: enforce_naming — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `enforce_naming()` is called with valid params {"filename": "<example_filename>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-013-ERR @documentorganizer
  Scenario: enforce_naming — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `enforce_naming()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-014 @documentorganizer @organizer
  Scenario: safe_move — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `safe_move()` is called with valid params {"src": "<example_src>", "dest_dir": "<example_dest_dir>", "dry_run": "<example_dry_run>", "rename_log": "<example_rename_log>", "move_log": "<example_move_log>", "dup_log": "<example_dup_log>", "target_root": "<example_target_root>", "custom_name": "<example_custom_name>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-014-ERR @documentorganizer
  Scenario: safe_move — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `safe_move()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-015 @documentorganizer @organizer
  Scenario: detect_conflicts — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `detect_conflicts()` is called with valid params {"tasks": "<example_tasks>", "zone": "<example_zone>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-015-ERR @documentorganizer
  Scenario: detect_conflicts — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `detect_conflicts()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-016 @documentorganizer @organizer
  Scenario: execute_zone — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `execute_zone()` is called with valid params {"zone": "<example_zone>", "job_dir": "<example_job_dir>", "dry_run": "<example_dry_run>", "rename_log": "<example_rename_log>", "move_log": "<example_move_log>", "dup_log": "<example_dup_log>", "target_root": "<example_target_root>", "tasks": "<example_tasks>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-016-ERR @documentorganizer
  Scenario: execute_zone — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `execute_zone()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-017 @documentorganizer @organizer
  Scenario: run_global_dedup — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `run_global_dedup()` is called with valid params {"dedup_entries": "<example_dedup_entries>", "target_root": "<example_target_root>", "dry_run": "<example_dry_run>", "dup_log": "<example_dup_log>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-017-ERR @documentorganizer
  Scenario: run_global_dedup — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `run_global_dedup()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-018 @documentorganizer @organizer
  Scenario: run_execute — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `run_execute()` is called with valid params {"job_dir": "<example_job_dir>", "max_concurrent": "<example_max_concurrent>", "dry_run": "<example_dry_run>", "target_override": "<example_target_override>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-018-ERR @documentorganizer
  Scenario: run_execute — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `run_execute()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-019 @documentorganizer @organizer
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-019-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-020 @documentorganizer @plan
  Scenario: generate_rename_suggestion — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `plan.py` is importable
    When `generate_rename_suggestion()` is called with valid params {"filepath": "<example_filepath>", "content": "<example_content>", "existing_folders": "<example_existing_folders>", "target_root": "<example_target_root>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-020-ERR @documentorganizer
  Scenario: generate_rename_suggestion — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `generate_rename_suggestion()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-021 @documentorganizer @plan
  Scenario: generate_tasks — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `plan.py` is importable
    When `generate_tasks()` is called with valid params {"scan_file": "<example_scan_file>", "out_dir": "<example_out_dir>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-021-ERR @documentorganizer
  Scenario: generate_tasks — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `generate_tasks()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-022 @documentorganizer @readme_writer
  Scenario: write_readmes — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `readme_writer.py` is importable
    When `write_readmes()` is called with valid params {"target": "<example_target>", "dry_run": "<example_dry_run>", "overwrite": "<example_overwrite>", "tasks_path": "<example_tasks_path>", "fail_on_error": "<example_fail_on_error>", "output_dir": "<example_output_dir>", "scan_json": "<example_scan_json>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-022-ERR @documentorganizer
  Scenario: write_readmes — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `write_readmes()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-023 @documentorganizer @readme_writer
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `readme_writer.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-023-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-024 @documentorganizer @organizer
  Scenario: rescue_zone — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `rescue_zone()` is called with valid params {"zone_path": "<example_zone_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-024-ERR @documentorganizer
  Scenario: rescue_zone — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `rescue_zone()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-025 @documentorganizer @organizer
  Scenario: unnest_folders — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `unnest_folders()` is called with valid params {"zone_path": "<example_zone_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-025-ERR @documentorganizer
  Scenario: unnest_folders — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `unnest_folders()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-026 @documentorganizer @organizer
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `organizer.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-026-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-027 @documentorganizer @scan
  Scenario: scan_directory — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `scan.py` is importable
    When `scan_directory()` is called with valid params {"root": "<example_root>", "large_mb": "<example_large_mb>", "excludes": "<example_excludes>", "output_arg": "<example_output_arg>", "fast": "<example_fast>", "merge_threshold": "<example_merge_threshold>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-027-ERR @documentorganizer
  Scenario: scan_directory — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `scan_directory()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-028 @documentorganizer @scan
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `scan.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-028-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-029 @documentorganizer @validate_tasks
  Scenario: validate — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `validate_tasks.py` is importable
    When `validate()` is called with valid params {"tasks_path": "<example_tasks_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-029-ERR @documentorganizer
  Scenario: validate — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `validate()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-030 @documentorganizer @validate_tasks
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `validate_tasks.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-030-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-031 @documentorganizer @verify
  Scenario: verify — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `verify.py` is importable
    When `verify()` is called with valid params {"root": "<example_root>", "check_paths": "<example_check_paths>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-031-ERR @documentorganizer
  Scenario: verify — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `verify()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-032 @documentorganizer @verify
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `verify.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-032-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-033 @documentorganizer @visualize
  Scenario: generate_mermaid_mindmap — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `visualize.py` is importable
    When `generate_mermaid_mindmap()` is called with valid params {"root": "<example_root>", "max_depth": "<example_max_depth>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-033-ERR @documentorganizer
  Scenario: generate_mermaid_mindmap — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `generate_mermaid_mindmap()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-034 @documentorganizer @visualize
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `visualize.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-034-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-035 @documentorganizer @watch
  Scenario: main — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `watch.py` is importable
    When `main()` is called with valid params {}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-035-ERR @documentorganizer
  Scenario: main — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `main()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-036 @documentorganizer @watch
  Scenario: on_created — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `watch.py` is importable
    When `on_created()` is called with valid params {"event": "<example_event>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-036-ERR @documentorganizer
  Scenario: on_created — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `on_created()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-037 @documentorganizer @watch
  Scenario: on_moved — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `watch.py` is importable
    When `on_moved()` is called with valid params {"event": "<example_event>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-037-ERR @documentorganizer
  Scenario: on_moved — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `on_moved()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable

  @TC-038 @documentorganizer @watch
  Scenario: process_file — happy path
    Given the "DocumentOrganizer" skill is initialized
    And `watch.py` is importable
    When `process_file()` is called with valid params {"file_path": "<example_file_path>"}
    Then it returns a result without raising an exception
    And the result conforms to the documented contract

  @TC-038-ERR @documentorganizer
  Scenario: process_file — invalid input
    Given the "DocumentOrganizer" skill is initialized
    When `process_file()` is called with invalid params
    Then a typed exception is raised
    And the error message is actionable
