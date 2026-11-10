# Function & Symbol Inventory — DocumentOrganizer

| ID | Symbol | File | Summary |
| :--- | :--- | :--- | :--- |
| FL-001 | main | __main__.py | Module symbol |
| FL-002 | get_headless_creation_flags | core/__init__.py | Return platform-appropriate headless creation flags. |
| FL-003 | enforce_token_budget | core/__init__.py | Truncate output text cleanly to comply with token budget caps. |
| FL-004 | __getattr__ | core/__init__.py | Lazily import core submodule attributes on demand. |
| FL-005 | GitRunError | core/git_artifact_adapter.py | Exception raised when a git command fails. |
| FL-006 | get_domain_adapter_contract | core/git_artifact_adapter.py | Return the registered domain adapter contract specification. |
| FL-007 | _get_creation_flags | core/git_artifact_adapter.py | Return Windows CREATE_NO_WINDOW flag for headless subprocess execution on Windows. |
| FL-008 | _run_git_command | core/git_artifact_adapter.py | Execute a git command headlessly with explicit UTF-8 encoding. |
| FL-009 | is_git_available | core/git_artifact_adapter.py | Verify if git executable is available in the current environment. |
| FL-010 | is_git_repository | core/git_artifact_adapter.py | Check whether the given path is a valid git repository. |
| FL-011 | init_git_repository | core/git_artifact_adapter.py | Initialize a new git repository at repo_path. |
| FL-012 | _verify_repo | core/git_artifact_adapter.py | Verify path is a repository; raise ValueError if not. |
| FL-013 | get_document_status | core/git_artifact_adapter.py | Inspect git repository working tree status. |
| FL-014 | stage_document_change | core/git_artifact_adapter.py | Stage document file changes into the git index. |
| FL-015 | unstage_document_change | core/git_artifact_adapter.py | Unstage document changes from the git index. |
| FL-016 | create_document_commit | core/git_artifact_adapter.py | Commit staged changes to the repository. |
| FL-017 | get_document_history | core/git_artifact_adapter.py | Retrieve commit history for the repository or a specific file. |
| FL-018 | create_document_snapshot | core/git_artifact_adapter.py | Create a tagged snapshot of the repository. |
| FL-019 | list_document_snapshots | core/git_artifact_adapter.py | List all snapshot tags in the repository. |
| FL-020 | delete_document_snapshot | core/git_artifact_adapter.py | Delete a snapshot tag. |
| FL-021 | rollback_document_snapshot | core/git_artifact_adapter.py | Roll back working directory and index to a snapshot tag. |
| FL-022 | get_document_version_at_commit | core/git_artifact_adapter.py | Retrieve content of a file at a specific commit hash. |
| FL-023 | get_document_diff | core/git_artifact_adapter.py | Compute diff between commits or against the working tree. |
| FL-024 | checkout_document_version | core/git_artifact_adapter.py | Restore a single document to the version at commit_hash. |
| FL-025 | GitArtifactAdapter | core/git_artifact_adapter.py | Object-oriented adapter for git-backed document repositories. |
| FL-026 | validate_zone | core/governance_engine.py | Validate if path conforms to the 5-zone MECE classification. |
| FL-027 | parse_pdca_prefix | core/governance_engine.py | Parse standard PDCA naming convention from filename. |
| FL-028 | _get_default_langgraph_checkpointer | core/organizer_graph.py | Module symbol |
| FL-029 | Node | core/organizer_graph.py | Graph node representing a document or task unit. |
| FL-030 | OrganizerGraph | core/organizer_graph.py | Directed graph representation for dependency management and topological ordering. |
| FL-031 | WorkflowCheckpointStatus | core/organizer_graph.py | Status enumeration for workflow checkpoints. |
| FL-032 | CheckpointMetadata | core/organizer_graph.py | Metadata recorded for every durable workflow checkpoint. |
| FL-033 | WorkflowCheckpoint | core/organizer_graph.py | Durable state snapshot at a workflow step boundary. |
| FL-034 | WorkflowCheckpointer | core/organizer_graph.py | Abstract protocol for durable asynchronous workflow checkpointing. |
| FL-035 | MemoryWorkflowCheckpointer | core/organizer_graph.py | In-memory thread-safe checkpointer for fast testing and ephemeral workflows. |
| FL-036 | FileWorkflowCheckpointer | core/organizer_graph.py | Durable file-backed checkpointer storing JSON snapshots on disk. |
| FL-037 | RetryPolicy | core/organizer_graph.py | Configurable exponential backoff retry policy inspired by Temporal workflows. |
| FL-038 | SagaCompensation | core/organizer_graph.py | Registered compensating activity to execute upon workflow cancellation or failure. |
| FL-039 | SagaCoordinator | core/organizer_graph.py | Saga coordinator tracking undo actions in LIFO order for transaction rollback. |
| FL-040 | CapabilityHook | core/organizer_graph.py | Base lifecycle hook for Open-SWE capabilities. |
| FL-041 | TelemetryCapability | core/organizer_graph.py | Tracks step latencies, execution metrics, and throughput. |
| FL-042 | IdempotencyCapability | core/organizer_graph.py | Ensures tasks and file operations are executed idempotently using hashed keys. |
| FL-043 | CapabilityFabric | core/organizer_graph.py | Registry and event dispatcher for workflow capability hooks. |
| FL-044 | OrganizerWorkflowState | core/organizer_graph.py | Schema for document reorganization workflow state. |
| FL-045 | _scan_target_node | core/organizer_graph.py | Scan target directory for candidate documents. |
| FL-046 | _resolve_traceability_node | core/organizer_graph.py | Resolve semantic project affinity and monorepo traceability for scanned files. |
| FL-047 | _generate_plan_node | core/organizer_graph.py | Build tasks.json plan based on resolved affinities and persist to job_dir. |
| FL-048 | DurableFallbackRunner | core/organizer_graph.py | Resilient execution engine providing Temporal retry, checkpoints, and Open-SWE fabric. |
| FL-049 | build_document_organizer_graph | core/organizer_graph.py | Build and compile the document organizer workflow graph. |
| FL-050 | ProjectAffinityMatch | core/traceability_resolver.py | Represents a matched project affinity outcome for a given document. |
| FL-051 | TraceabilityTag | core/traceability_resolver.py | Parsed traceability tags from document text or summary. |
| FL-052 | TraceabilityContextResolver | core/traceability_resolver.py | Discovers monorepo projects and resolves semantic project affinity for document files. |
| FL-053 | TraceabilityResolver | core/traceability_resolver.py | Extracts and resolves bi-directional traceability references between documents. |
| FL-054 | cleanup_directories | scripts/cleanup.py | Clean up specified directories. |
| FL-055 | cleanup_file | scripts/cleanup.py | Remove a specific file. |
| FL-056 | consolidate_documents | scripts/consolidate.py | Consolidate multiple documents into a single file. |
| FL-057 | find_files | scripts/consolidate_workspace.py | Find files in a directory tree with optional extension filtering. |
| FL-058 | main | scripts/consolidate_workspace.py | Module symbol |
| FL-059 | has_frontmatter | scripts/contextualize.py | Check if content already has YAML frontmatter. |
| FL-060 | format_frontmatter | scripts/contextualize.py | Format context dictionary as YAML frontmatter string. |
| FL-061 | add_context | scripts/contextualize.py | Add YAML frontmatter context to a file. |
| FL-062 | main | scripts/contextualize.py | Module symbol |
| FL-063 | DepthPolicy | scripts/depth_policy.py | Configuration for directory depth policy. |
| FL-064 | PathValidationError | scripts/depth_policy.py | Raised when a path pattern fails validation. |
| FL-065 | ManifestLoadError | scripts/depth_policy.py | Raised when exception manifest cannot be loaded or parsed. |
| FL-066 | _validate_path_pattern | scripts/depth_policy.py | Validate and normalize a path pattern, returning its parts. |
| FL-067 | normalize_exception | scripts/depth_policy.py | Normalizes and validates an opaque exception path pattern. |
| FL-068 | ExceptionManifestList | scripts/depth_policy.py | List subclass providing dict-like access for backwards compatibility. |
| FL-069 | _parse_exception_arg | scripts/depth_policy.py | Parse exception manifest arguments into (root, manifest_path). |
| FL-070 | load_exception_manifest | scripts/depth_policy.py | Loads and normalizes opaque depth exceptions from a manifest file. |
| FL-071 | _normalize_exceptions | scripts/depth_policy.py | Normalize exception patterns into tuple form for matching. |
| FL-072 | _is_exempted | scripts/depth_policy.py | Check if a path is exempted by any exception pattern. |
| FL-073 | audit | scripts/depth_policy.py | Audits directory hierarchy against the 3-layer MECE rule (root -> zone -> document). |
| FL-074 | _load_photo_extensions | scripts/desktop_scanner.py | Attempt to load photo extensions from photo_ingest module. |
| FL-075 | ScannedAsset | scripts/desktop_scanner.py | Represents an unorganized asset discovered on desktop or staging areas. |
| FL-076 | get_desktop_path | scripts/desktop_scanner.py | Discovers user desktop directory with OS fallback. |
| FL-077 | scan_desktop | scripts/desktop_scanner.py | Legacy helper: Returns list of file paths directly on desktop. |
| FL-078 | DesktopScanner | scripts/desktop_scanner.py | Scans desktop and staging paths for unorganized loose assets. |
| FL-079 | check_zero_desktop_invariant | scripts/desktop_scanner.py | Evaluates Zero-Desktop Invariant. |
| FL-080 | main | scripts/desktop_scanner.py | CLI entry point for desktop scanning. |
| FL-081 | ExtractedDocument | scripts/extract.py | Module symbol |
| FL-082 | DocumentExtractor | scripts/extract.py | Extracts text, multimedia metadata safely with size guards. |
| FL-083 | parse_args | scripts/hydrate_frontmatter.py | Module symbol |
| FL-084 | FrontmatterHydrator | scripts/hydrate_frontmatter.py | Standardizes YAML frontmatter across documentation files. |
| FL-085 | main | scripts/hydrate_frontmatter.py | Module symbol |
| FL-086 | WorkspaceHygieneEngine | scripts/hygiene.py | Clean-room hygiene and SQLite compaction engine. |
| FL-087 | JDCategory | scripts/jd_registry.py | Module symbol |
| FL-088 | JDRegistry | scripts/jd_registry.py | Manages Johnny Decimal categories and resolution logic. |
| FL-089 | discover_projects | scripts/jd_registry.py | Discover monorepo projects by scanning for PP_NAME folders. |
| FL-090 | load_registry | scripts/jd_registry.py | Load JD definitions and auto-discover monorepo projects. |
| FL-091 | resolve_project_for_file | scripts/jd_registry.py | Resolve project affinity based on filename, content summary, and registry. |
| FL-092 | _default_registry_path | scripts/jd_registry.py | Module symbol |
| FL-093 | save_registry | scripts/jd_registry.py | Save registry data to JSON file. |
| FL-094 | resolve_project | scripts/jd_registry.py | Walk up from a folder to find which project it belongs to. |
| FL-095 | scan_highest_sequence | scripts/jd_registry.py | Scan a project folder (recursively) to find the highest PP.SSS in use. |
| FL-096 | next_sequence | scripts/jd_registry.py | Get the next available sequence number for a project. |
| FL-097 | format_id | scripts/jd_registry.py | Format a JD_ID: PP.SSS |
| FL-098 | format_filename | scripts/jd_registry.py | Format the full PARA-Decimal filename. |
| FL-099 | extract_id | scripts/jd_registry.py | Extract (PP, SSS, [Tags]) from a filename, or None if no ID found. |
| FL-100 | extract_tag | scripts/jd_registry.py | Extract tags from PP.SSS.TT[.TT] format. |
| FL-101 | _llm_generate | scripts/llm_generation.py | Generate text via configured OpenAI-compatible endpoint, or return deterministic offline notice. |
| FL-102 | _is_rate_limit_error | scripts/llm_generation.py | Check whether an exception indicates HTTP 429 / rate limiting. |
| FL-103 | setup_logger | scripts/logger.py | Configure and return a structured logger instance. |
| FL-104 | get_logger | scripts/logger.py | Retrieve or configure a standardized logger instance. |
| FL-105 | emit_progress | scripts/logger.py | Emit formatted progress line and optionally persist to JSONL. |
| FL-106 | LoopPipeline | scripts/loop_pipeline.py | Headless loop pipeline for continuous workspace organization. |
| FL-107 | main | scripts/loop_pipeline.py | Module symbol |
| FL-108 | remove_vietnamese_diacritics | scripts/naming_normalizer.py | Replace Vietnamese accented characters with ASCII equivalents. |
| FL-109 | normalize_name | scripts/naming_normalizer.py | Normalize a file or directory name to strict canonical pure ASCII snake_case. |
| FL-110 | NamingNormalizer | scripts/naming_normalizer.py | Linter and normalizer for workspace naming and generated asset placement. |
| FL-111 | to_extended_win32_path | scripts/nightly_project_reorganizer.py | Normalize path with Win32 extended-length prefix (\\?\) if exceeding MAX_PATH. |
| FL-112 | compute_sha256 | scripts/nightly_project_reorganizer.py | Compute cryptographic SHA-256 hash of a file. |
| FL-113 | AtomicSharedResourceLock | scripts/nightly_project_reorganizer.py | Kernel-level atomic lock using O_CREAT | O_EXCL with PID and stale TTL breaker. |
| FL-114 | MECEZone | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-115 | ActionType | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-116 | DiscoveredFile | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-117 | ClassificationDecision | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-118 | RelocationResult | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-119 | safe_relocate_file | scripts/nightly_project_reorganizer.py | Execute non-destructive 6-step Copy-Verify-Replace-Unlink relocation (P=1). |
| FL-120 | is_git_dirty | scripts/nightly_project_reorganizer.py | Check if file has uncommitted staged or unstaged modifications in git. |
| FL-121 | is_active_draft_immune | scripts/nightly_project_reorganizer.py | Evaluate 4-Point Active Draft Immunity Guard to prevent false-positive archival. |
| FL-122 | ProjectOutputScanner | scripts/nightly_project_reorganizer.py | Discovers unorganized root clutter and daily delta files strictly confined to project root. |
| FL-123 | DocumentSemanticsClassifier | scripts/nightly_project_reorganizer.py | Classifies candidate files into MECE zones and determines obsolescence. |
| FL-124 | ProjectSummary | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-125 | ReorganizationManifest | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-126 | MultiProjectReorganizerOrchestrator | scripts/nightly_project_reorganizer.py | Coordinates parallel multi-project scanning, relocation, and manifest generation. |
| FL-127 | main | scripts/nightly_project_reorganizer.py | Module symbol |
| FL-128 | _to_snake_case | scripts/organizer.py | Convert camelCase or PascalCase to snake_case. |
| FL-129 | enforce_naming | scripts/organizer.py | Return (new_name, violation_description). |
| FL-130 | _file_hash | scripts/organizer.py | Module symbol |
| FL-131 | _dedup_target_path | scripts/organizer.py | Compute the canonical _duplicates/ target path for a given file. |
| FL-132 | _acquire_dedup_lock | scripts/organizer.py | Atomically claim a _duplicates/ target slot across processes. |
| FL-133 | _release_dedup_lock | scripts/organizer.py | Module symbol |
| FL-134 | _log_dedup_event | scripts/organizer.py | Module symbol |
| FL-135 | _resolve_collision | scripts/organizer.py | Module symbol |
| FL-136 | _handle_existing_dedup | scripts/organizer.py | Module symbol |
| FL-137 | _safe_dedup_move | scripts/organizer.py | Move src to a _duplicates/ target, safe across parallel processes. |
| FL-138 | _append_timestamp | scripts/organizer.py | Module symbol |
| FL-139 | _log_duplicate | scripts/organizer.py | Module symbol |
| FL-140 | _handle_dir_merge | scripts/organizer.py | Module symbol |
| FL-141 | _resolve_batch_collision | scripts/organizer.py | Module symbol |
| FL-142 | _resolve_disk_collision | scripts/organizer.py | Module symbol |
| FL-143 | _finalize_move | scripts/organizer.py | Module symbol |
| FL-144 | safe_move | scripts/organizer.py | Move src into dest_dir, enforcing naming conventions. |
| FL-145 | _norm | scripts/organizer.py | Module symbol |
| FL-146 | _is_within | scripts/organizer.py | Module symbol |
| FL-147 | _get_zone_pairs | scripts/organizer.py | Module symbol |
| FL-148 | _get_zone_srcs | scripts/organizer.py | Module symbol |
| FL-149 | _get_zone_dsts | scripts/organizer.py | Module symbol |
| FL-150 | _check_zone_conflicts | scripts/organizer.py | Module symbol |
| FL-151 | detect_conflicts | scripts/organizer.py | Return cross-zone conflict records for the given zone. |
| FL-152 | _append_conflicts_md | scripts/organizer.py | Module symbol |
| FL-153 | execute_zone | scripts/organizer.py | Execute a single zone's file moves. Returns a result dict. |
| FL-154 | _process_duplicate | scripts/organizer.py | Module symbol |
| FL-155 | run_global_dedup | scripts/organizer.py | Process the top-level 'dedup' array from tasks.json. |
| FL-156 | _write_dedup_log | scripts/organizer.py | Write dedup_log.md with a row for every duplicate move (global + batch + on-disk). |
| FL-157 | _write_rename_log | scripts/organizer.py | Module symbol |
| FL-158 | _write_move_log | scripts/organizer.py | Module symbol |
| FL-159 | _infer_target_root | scripts/organizer.py | Derive the workspace target root used for the _duplicates/ landing zone. |
| FL-160 | _load_tasks | scripts/organizer.py | Module symbol |
| FL-161 | _log_execution_start | scripts/organizer.py | Module symbol |
| FL-162 | _handle_global_dedup | scripts/organizer.py | Module symbol |
| FL-163 | _cleanup_stale_logs | scripts/organizer.py | Module symbol |
| FL-164 | _run_zones | scripts/organizer.py | Module symbol |
| FL-165 | _log_execution_finish | scripts/organizer.py | Module symbol |
| FL-166 | run_execute | scripts/organizer.py | Module symbol |
| FL-167 | _write_conflicts_summary | scripts/organizer.py | Module symbol |
| FL-168 | main | scripts/organizer.py | Module symbol |
| FL-169 | PhotoMetadata | scripts/photo_ingest.py | Module symbol |
| FL-170 | PhotoIngestEngine | scripts/photo_ingest.py | Engine for extracting metadata and content features from photo/image assets. |
| FL-171 | _is_organizer_artifact | scripts/plan.py | Return True if the file is a DocumentOrganizer-generated artifact. |
| FL-172 | RenameSuggestion | scripts/plan.py | Module symbol |
| FL-173 | FileRename | scripts/plan.py | Module symbol |
| FL-174 | BatchRenameSuggestion | scripts/plan.py | Module symbol |
| FL-175 | ClusterRoutingSuggestion | scripts/plan.py | Module symbol |
| FL-176 | _discover_existing_folders | scripts/plan.py | Walk the target root (depth 1) to find existing subfolder names. |
| FL-177 | _build_folder_context | scripts/plan.py | Module symbol |
| FL-178 | _clean_title | scripts/plan.py | Clean an LLM-generated title into a safe filename component. |
| FL-179 | _clean_tags | scripts/plan.py | Filter tags to only valid ones. Max 2 tags. |
| FL-180 | _build_tag_reference | scripts/plan.py | Module symbol |
| FL-181 | _normalize_suggested_folder | scripts/plan.py | Module symbol |
| FL-182 | _cosine_similarity | scripts/plan.py | Module symbol |
| FL-183 | cluster_files | scripts/plan.py | Module symbol |
| FL-184 | generate_atomic_summary | scripts/plan.py | Module symbol |
| FL-185 | compute_embedding | scripts/plan.py | Module symbol |
| FL-186 | generate_cluster_routing_suggestion | scripts/plan.py | Module symbol |
| FL-187 | generate_batch_title_suggestions | scripts/plan.py | Module symbol |
| FL-188 | generate_tasks | scripts/plan.py | Module symbol |
| FL-189 | generate_rename_suggestion | scripts/plan.py | Generate a semantic rename and folder suggestion for a file. |
| FL-190 | sanitize_mece_zone | scripts/project_router.py | Sanitizes and enforces that relative zone path strictly resides in a valid MECE zone. |
| FL-191 | ProjectRoute | scripts/project_router.py | Module symbol |
| FL-192 | _score_discrete_choice_profile | scripts/project_router.py | Evaluates project profiles using deterministic token-overlap discrete-choice scoring. |
| FL-193 | ProjectRouter | scripts/project_router.py | Matches files and multimedia assets to active project repositories following MECE SSOT. |
| FL-194 | _safe_rglob | scripts/readme_writer.py | Yield rglob results, logging any PermissionError/OSError and continuing. |
| FL-195 | _safe_iterdir | scripts/readme_writer.py | Module symbol |
| FL-196 | _is_excluded | scripts/readme_writer.py | Module symbol |
| FL-197 | _is_always_excluded | scripts/readme_writer.py | Module symbol |
| FL-198 | _file_type_icon | scripts/readme_writer.py | Module symbol |
| FL-199 | _is_project_folder | scripts/readme_writer.py | True if folder has at least one sub-folder containing doc files. |
| FL-200 | _describe_folder | scripts/readme_writer.py | Generate a simple 1-line description from folder name. |
| FL-201 | _check_staleness | scripts/readme_writer.py | Return True if target directory state differs from scan.json. |
| FL-202 | _try_is_file | scripts/readme_writer.py | Module symbol |
| FL-203 | _format_dir_row | scripts/readme_writer.py | Module symbol |
| FL-204 | _format_file_row | scripts/readme_writer.py | Module symbol |
| FL-205 | _check_empty_directory | scripts/readme_writer.py | Module symbol |
| FL-206 | _build_contents_table | scripts/readme_writer.py | Module symbol |
| FL-207 | _build_traceability_matrix | scripts/readme_writer.py | Module symbol |
| FL-208 | _build_readme_simple | scripts/readme_writer.py | Module symbol |
| FL-209 | _build_readme_project | scripts/readme_writer.py | Module symbol |
| FL-210 | _process_zone_path | scripts/readme_writer.py | Module symbol |
| FL-211 | _load_zone_dirs | scripts/readme_writer.py | Load zones from a tasks JSON file and expand to zone paths + all descendants. |
| FL-212 | _full_tree_dirs | scripts/readme_writer.py | Module symbol |
| FL-213 | _get_rel_display | scripts/readme_writer.py | Module symbol |
| FL-214 | _process_directory | scripts/readme_writer.py | Module symbol |
| FL-215 | _write_error_report | scripts/readme_writer.py | Module symbol |
| FL-216 | write_readmes | scripts/readme_writer.py | Write README.md for every eligible folder. Returns process exit code. |
| FL-217 | main | scripts/readme_writer.py | Module symbol |
| FL-218 | _walk_error_handler | scripts/scan.py | Called by os.walk when it can't read a directory. Records so the summary can surface it. |
| FL-219 | _filter_dirs | scripts/scan.py | Module symbol |
| FL-220 | _collect_files_fast | scripts/scan.py | Module symbol |
| FL-221 | _collect_dirs | scripts/scan.py | Module symbol |
| FL-222 | _calculate_hash | scripts/scan.py | Module symbol |
| FL-223 | _build_inventory | scripts/scan.py | Module symbol |
| FL-224 | _find_empty_folders | scripts/scan.py | Module symbol |
| FL-225 | _find_oversized | scripts/scan.py | Module symbol |
| FL-226 | _find_duplicates_fast | scripts/scan.py | Module symbol |
| FL-227 | _find_duplicates_hash | scripts/scan.py | Module symbol |
| FL-228 | _find_duplicates | scripts/scan.py | Module symbol |
| FL-229 | _get_folder_fingerprint | scripts/scan.py | Map filenames to their content hashes for a directory (non-recursive). |
| FL-230 | _calculate_overlap | scripts/scan.py | Module symbol |
| FL-231 | _find_merge_candidates | scripts/scan.py | Module symbol |
| FL-232 | _resolve_output_dir | scripts/scan.py | --output semantics: |
| FL-233 | _print_scan_summary | scripts/scan.py | Module symbol |
| FL-234 | _count_dirs_visited | scripts/scan.py | Module symbol |
| FL-235 | _build_payload | scripts/scan.py | Module symbol |
| FL-236 | _write_payload | scripts/scan.py | Module symbol |
| FL-237 | scan_directory | scripts/scan.py | Module symbol |
| FL-238 | _parse_args | scripts/scan.py | Module symbol |
| FL-239 | main | scripts/scan.py | Module symbol |
| FL-240 | generate_summary | scripts/summarize.py | Summarize document text via optional LLM or deterministic first-paragraph fallback. |
| FL-241 | summarize_content | scripts/summarize.py | Module symbol |
| FL-242 | WorkspaceSweepOrchestrator | scripts/sweep.py | Orchestrates multi-stage Ingest-then-Purge workspace lifecycle. |
| FL-243 | _read_context_file | scripts/task_decomposition.py | Read optional context file and return its contents. |
| FL-244 | _agent_context_decompose | scripts/task_decomposition.py | Stub decomposition when all external LLM providers are unavailable. |
| FL-245 | _parse_decompose_json | scripts/task_decomposition.py | Parse JSON from LLM decomposition output. Exits on failure. |
| FL-246 | _save_job_data | scripts/task_decomposition.py | Build and save tasks.json. Returns job_data dict. |
| FL-247 | topological_sort_subtasks | scripts/topological_sort.py | Sorts sub_tasks topologically based on their depends_on field. |
| FL-248 | get_file_hash | scripts/utils.py | Calculate hash of a file. |
| FL-249 | _is_abs | scripts/validate_tasks.py | Module symbol |
| FL-250 | _validate_top_level_optional | scripts/validate_tasks.py | Module symbol |
| FL-251 | _validate_top_level | scripts/validate_tasks.py | Module symbol |
| FL-252 | _validate_zone_moves | scripts/validate_tasks.py | Module symbol |
| FL-253 | _validate_zone_keys | scripts/validate_tasks.py | Module symbol |
| FL-254 | _validate_zones | scripts/validate_tasks.py | Module symbol |
| FL-255 | _validate_dedup_entry_dups | scripts/validate_tasks.py | Module symbol |
| FL-256 | _validate_dedup_entry | scripts/validate_tasks.py | Module symbol |
| FL-257 | _validate_dedup | scripts/validate_tasks.py | Module symbol |
| FL-258 | validate | scripts/validate_tasks.py | Module symbol |
| FL-259 | main | scripts/validate_tasks.py | Module symbol |
| FL-260 | calculate_sha256 | scripts/vault_manager.py | Compute SHA-256 hash of a file efficiently in 64KB chunks. |
| FL-261 | normalize_alias | scripts/vault_manager.py | Generate a clean, deterministic uppercase alias like DOC_IDENTITY_PASSPORT. |
| FL-262 | VaultManager | scripts/vault_manager.py | Core controller for Personal & Business Legal Vaults. |
| FL-263 | main | scripts/vault_manager.py | Module symbol |
| FL-264 | _resolve_path | scripts/verify.py | Resolve a path, treating it as relative to root unless absolute. |
| FL-265 | verify | scripts/verify.py | Verify a directory structure and expected paths after reorganization. |
| FL-266 | main | scripts/verify.py | Module symbol |
| FL-267 | log | scripts/verify_skill_health.py | Module symbol |
| FL-268 | check_tests | scripts/verify_skill_health.py | Run full pytest suite and verify minimum test count threshold. |
| FL-269 | check_known_folders_discovery | scripts/verify_skill_health.py | Verify that dynamic shell discovery correctly includes critical ingress paths. |
| FL-270 | check_active_daemons | scripts/verify_skill_health.py | Check whether watch_supervisor and watch daemons are actively running. |
| FL-271 | main | scripts/verify_skill_health.py | Module symbol |
| FL-272 | generate_mermaid_mindmap | scripts/visualize.py | Module symbol |
| FL-273 | main | scripts/visualize.py | Module symbol |
| FL-274 | AIDocumentHandler | scripts/watch.py | Module symbol |
| FL-275 | main | scripts/watch.py | Module symbol |
| FL-276 | get_windows_shell_folders | scripts/watch_supervisor.py | Retrieve Windows Shell Known Folders from registry to resolve OneDrive KFM redirections. |
| FL-277 | discover_watch_directories | scripts/watch_supervisor.py | Discover all primary, shell-redirected, media capture, and project-scoped ingress directories. |
| FL-278 | main | scripts/watch_supervisor.py | Module symbol |
| FL-279 | organize_task_and_conversation_files | src/document_organizer_interceptor.py | Archive reusable scratch scripts from an agent session into 40_ARCHIVE/scratch/. |
