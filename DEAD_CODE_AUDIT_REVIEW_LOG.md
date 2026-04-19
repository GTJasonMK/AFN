# 死代码逐文件审计过程日志

- 日期：2026-03-22
- 执行者：Codex
- 基线文件数：925
- 说明：以下记录按文件顺序回填，每条都表示该文件已被读取并完成当前轮复核。

## 审计过程

- 001/925 `.dockerignore` | text | 已读取 24 行，判定为非代码文件。
- 002/925 `.gitignore` | text | 已读取 162 行，判定为非代码文件。
- 003/925 `AGENTS.md` | text | 已读取 49 行，判定为非代码文件。
- 004/925 `DEAD_CODE_AUDIT_FILELIST.tsv` | text | 已读取 926 行，判定为非代码文件。
- 005/925 `DEAD_CODE_AUDIT_PROGRESS.md` | text | 已读取 27 行，判定为非代码文件。
- 006/925 `README.md` | text | 已读取 504 行，判定为非代码文件。
- 007/925 `backend/.env.example` | text | 已读取 38 行，判定为非代码文件。
- 008/925 `backend/README.md` | text | 已读取 183 行，判定为非代码文件。
- 009/925 `backend/app/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 010/925 `backend/app/api/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 011/925 `backend/app/api/routers/__init__.py` | py | 已读取 44 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 012/925 `backend/app/api/routers/admin_dashboard.py` | py | 已读取 766 行；顶层符号 28（AdminStatusCount, AdminOverviewSummary, AdminOverviewResponse, AdminProjectSummary, ...）；导入 17；首轮未确认死代码。
- 013/925 `backend/app/api/routers/admin_users.py` | py | 已读取 387 行；顶层符号 24（AdminUserItem, AdminUsersListResponse, AdminUserMetrics, AdminUserMonitorItem, ...）；导入 20；首轮未确认死代码。
- 014/925 `backend/app/api/routers/admin_utils.py` | py | 已读取 54 行；顶层符号 3（normalize_datetime, collect_count_map, collect_latest_map）；导入 4；首轮未确认死代码。
- 015/925 `backend/app/api/routers/auth.py` | py | 已读取 288 行；顶层符号 16（AuthStatusResponse, UserPublic, RegisterRequest, LoginRequest, ...）；导入 15；首轮未确认死代码。
- 016/925 `backend/app/api/routers/chapter_rag_helpers.py` | py | 已读取 149 行；顶层符号 4（get_project_display_title, ensure_chapter_summary, ensure_chapter_analysis_data_safely, ensure_chapter_summary_and_analysis_data_safely）；导入 6；首轮未确认死代码。
- 017/925 `backend/app/api/routers/character_portrait.py` | py | 已读取 353 行；顶层符号 11（get_portrait_service, get_project_portraits, get_active_portraits, get_character_portraits, ...）；导入 11；首轮未确认死代码。
- 018/925 `backend/app/api/routers/coding/__init__.py` | py | 已读取 24 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 019/925 `backend/app/api/routers/coding/files.py` | py | 已读取 36 行；顶层符号 0（无）；导入 10；首轮未确认死代码。
- 020/925 `backend/app/api/routers/coding/files_agent_state.py` | py | 已读取 136 行；顶层符号 5（AgentStateResponse, PauseAgentRequest, get_directory_agent_state, pause_directory_agent, ...）；导入 10；首轮未确认死代码。
- 021/925 `backend/app/api/routers/coding/files_dependencies.py` | py | 已读取 38 行；顶层符号 2（get_directory_service, get_file_prompt_service）；导入 4；首轮未确认死代码。
- 022/925 `backend/app/api/routers/coding/files_directory_crud.py` | py | 已读取 165 行；顶层符号 6（_to_flat_directory_node_response, create_directory, update_directory, delete_directory, ...）；导入 10；首轮未确认死代码。
- 023/925 `backend/app/api/routers/coding/files_directory_structure.py` | py | 已读取 113 行；顶层符号 2（get_directory_tree, generate_directory_structure）；导入 13；首轮未确认死代码。
- 024/925 `backend/app/api/routers/coding/files_plan_agent.py` | py | 已读取 219 行；顶层符号 3（PlanDirectoryAgentRequest, plan_directory_with_agent, _save_agent_result）；导入 14；首轮未确认死代码。
- 025/925 `backend/app/api/routers/coding/files_plan_v2.py` | py | 已读取 565 行；顶层符号 4（PlanDirectoryV2Request, plan_directory_structure_v2, _error_generator, _three_phase_pipeline）；导入 17；首轮未确认死代码。
- 026/925 `backend/app/api/routers/coding/files_planning_context.py` | py | 已读取 124 行；顶层符号 4（DirectoryPlanningContext, _dump_dict_or_model, _dump_list, load_directory_planning_context）；导入 4；首轮未确认死代码。
- 027/925 `backend/app/api/routers/coding/files_prompt_generation.py` | py | 已读取 145 行；顶层符号 3（generate_file_prompt, generate_file_prompt_stream, save_file_content）；导入 13；首轮未确认死代码。
- 028/925 `backend/app/api/routers/coding/files_review_prompt.py` | py | 已读取 137 行；顶层符号 3（generate_review_prompt, generate_review_prompt_stream, save_review_prompt）；导入 13；首轮未确认死代码。
- 029/925 `backend/app/api/routers/coding/files_source_files.py` | py | 已读取 140 行；顶层符号 5（list_files, get_file, create_file, update_file, ...）；导入 9；首轮未确认死代码。
- 030/925 `backend/app/api/routers/coding/files_versions.py` | py | 已读取 64 行；顶层符号 2（get_file_versions, select_file_version）；导入 8；首轮未确认死代码。
- 031/925 `backend/app/api/routers/coding/hierarchy.py` | py | 已读取 23 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 032/925 `backend/app/api/routers/coding/hierarchy_dependencies.py` | py | 已读取 231 行；顶层符号 6（CreateDependencyRequest, DependencyResponse, list_dependencies, create_dependency, ...）；导入 11；首轮未确认死代码。
- 033/925 `backend/app/api/routers/coding/hierarchy_generation.py` | py | 已读取 551 行；顶层符号 7（GenerateSystemsRequest, GenerateModulesRequest, GenerateAllModulesRequest, _get_architecture_context, ...）；导入 23；首轮未确认死代码。
- 034/925 `backend/app/api/routers/coding/hierarchy_modules.py` | py | 已读取 191 行；顶层符号 7（CreateModuleRequest, UpdateModuleRequest, list_modules, get_module, ...）；导入 14；首轮未确认死代码。
- 035/925 `backend/app/api/routers/coding/hierarchy_systems.py` | py | 已读取 191 行；顶层符号 7（CreateSystemRequest, UpdateSystemRequest, list_systems, get_system, ...）；导入 15；首轮未确认死代码。
- 036/925 `backend/app/api/routers/coding/inspiration.py` | py | 已读取 35 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 037/925 `backend/app/api/routers/coding/projects.py` | py | 已读取 289 行；顶层符号 7（list_coding_projects, create_coding_project, get_coding_project, update_coding_project, ...）；导入 13；首轮未确认死代码。
- 038/925 `backend/app/api/routers/coding/rag.py` | py | 已读取 610 行；顶层符号 18（_require_vector_store, _get_project_or_404, _get_default_source, ReindexResponse, ...）；导入 14；首轮未确认死代码。
- 039/925 `backend/app/api/routers/embedding_config.py` | py | 已读取 376 行；顶层符号 14（list_providers, list_embedding_configs, get_active_config, get_embedding_config_by_id, ...）；导入 14；首轮未确认死代码。
- 040/925 `backend/app/api/routers/image_generation.py` | py | 已读取 682 行；顶层符号 25（_ensure_novel_project_owner, get_image_configs, get_image_config, create_image_config, ...）；导入 21；首轮未确认死代码。
- 041/925 `backend/app/api/routers/inspiration_helpers.py` | py | 已读取 330 行；顶层符号 4（AiMessageJsonStreamExtractor, stream_inspiration_parsed_result_events, format_conversation_history_records, stream_inspiration_service_sse_events）；导入 4；首轮未确认死代码。
- 042/925 `backend/app/api/routers/inspiration_router_registry.py` | py | 已读取 124 行；顶层符号 1（register_inspiration_routes）；导入 11；首轮未确认死代码。
- 043/925 `backend/app/api/routers/llm_config.py` | py | 已读取 164 行；顶层符号 11（list_llm_configs, get_active_config, get_llm_config_by_id, create_llm_config, ...）；导入 9；首轮未确认死代码。
- 044/925 `backend/app/api/routers/novels/__init__.py` | py | 已读取 181 行；顶层符号 7（create_novel, list_novels, get_novel, get_novel_section, ...）；导入 16；首轮未确认死代码。
- 045/925 `backend/app/api/routers/novels/blueprints.py` | py | 已读取 576 行；顶层符号 7（generate_blueprint, save_blueprint, refine_blueprint, patch_blueprint, ...）；导入 29；首轮未确认死代码。
- 046/925 `backend/app/api/routers/novels/export.py` | py | 已读取 159 行；顶层符号 3（export_chapters, _generate_txt_export, _generate_markdown_export）；导入 13；首轮未确认死代码。
- 047/925 `backend/app/api/routers/novels/import_analysis.py` | py | 已读取 246 行；顶层符号 4（import_txt_file, start_analysis, get_analysis_status, cancel_analysis）；导入 10；首轮未确认死代码。
- 048/925 `backend/app/api/routers/novels/inspiration.py` | py | 已读取 32 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 049/925 `backend/app/api/routers/novels/outlines.py` | py | 已读取 448 行；顶层符号 2（generate_chapter_outlines, generate_chapter_outlines_stream）；导入 19；首轮未确认死代码。
- 050/925 `backend/app/api/routers/novels/rag.py` | py | 已读取 507 行；顶层符号 10（TypeDetail, CompletenessResponse, IngestionResultItem, FullIngestionResponse, ...）；导入 15；首轮未确认死代码。
- 051/925 `backend/app/api/routers/prompts.py` | py | 已读取 299 行；顶层符号 19（ResetAllResponse, RegistrySummaryResponse, ValidationResponse, PromptMetaResponse, ...）；导入 8；首轮未确认死代码。
- 052/925 `backend/app/api/routers/protagonist.py` | py | 已读取 783 行；顶层符号 26（get_profile_service, get_implicit_tracker, get_deletion_protection, get_analysis_service, ...）；导入 13；首轮未确认死代码。
- 053/925 `backend/app/api/routers/queue.py` | py | 已读取 93 行；顶层符号 3（get_queue_status, get_queue_config, update_queue_config）；导入 6；首轮未确认死代码。
- 054/925 `backend/app/api/routers/rag_helpers.py` | py | 已读取 51 行；顶层符号 2（build_type_details, run_completeness_check）；导入 1；首轮未确认死代码。
- 055/925 `backend/app/api/routers/rag_schemas.py` | py | 已读取 29 行；顶层符号 2（TypeDetailBase, CompletenessResponseBase）；导入 1；首轮未确认死代码。
- 056/925 `backend/app/api/routers/settings.py` | py | 已读取 26 行；顶层符号 0（无）；导入 7；首轮未确认死代码。
- 057/925 `backend/app/api/routers/settings_advanced.py` | py | 已读取 221 行；顶层符号 7（AdvancedConfigResponse, AdvancedConfigUpdate, AdvancedConfigExportData, get_advanced_config, ...）；导入 9；首轮未确认死代码。
- 058/925 `backend/app/api/routers/settings_all.py` | py | 已读取 376 行；顶层符号 3（AllConfigExportData, export_all_configs, import_all_configs）；导入 16；首轮未确认死代码。
- 059/925 `backend/app/api/routers/settings_max_tokens.py` | py | 已读取 217 行；顶层符号 7（MaxTokensConfigResponse, MaxTokensConfigUpdate, MaxTokensConfigExportData, get_max_tokens_config, ...）；导入 9；首轮未确认死代码。
- 060/925 `backend/app/api/routers/settings_models.py` | py | 已读取 21 行；顶层符号 1（ConfigImportResult）；导入 2；首轮未确认死代码。
- 061/925 `backend/app/api/routers/settings_queue.py` | py | 已读取 125 行；顶层符号 3（QueueConfigExportData, export_queue_config, import_queue_config）；导入 8；首轮未确认死代码。
- 062/925 `backend/app/api/routers/settings_temperature.py` | py | 已读取 185 行；顶层符号 7（TemperatureConfigResponse, TemperatureConfigUpdate, TemperatureConfigExportData, get_temperature_config, ...）；导入 9；首轮未确认死代码。
- 063/925 `backend/app/api/routers/settings_utils.py` | py | 已读取 102 行；顶层符号 6（get_config_file, load_config, save_config, persist_config_updates, ...）；导入 6；首轮未确认死代码。
- 064/925 `backend/app/api/routers/theme_config.py` | py | 已读取 288 行；顶层符号 21（list_theme_configs, get_theme_defaults, export_all_theme_configs, get_active_theme_config, ...）；导入 7；首轮未确认死代码。
- 065/925 `backend/app/api/routers/writer/__init__.py` | py | 已读取 41 行；顶层符号 0（无）；导入 10；首轮未确认死代码。
- 066/925 `backend/app/api/routers/writer/chapter_generation.py` | py | 已读取 524 行；顶层符号 4（generate_chapter, retry_chapter_version, preview_chapter_prompt, generate_chapter_stream）；导入 20；首轮未确认死代码。
- 067/925 `backend/app/api/routers/writer/chapter_management.py` | py | 已读取 846 行；顶层符号 8（_trigger_protagonist_sync, import_chapter, select_chapter_version, evaluate_chapter, ...）；导入 23；首轮未确认死代码。
- 068/925 `backend/app/api/routers/writer/chapter_outlines.py` | py | 已读取 717 行；顶层符号 3（generate_chapter_outlines_by_count, delete_latest_chapter_outlines, regenerate_chapter_outline）；导入 28；首轮未确认死代码。
- 069/925 `backend/app/api/routers/writer/character_state.py` | py | 已读取 151 行；顶层符号 7（CharacterStateResponse, ChapterCharacterStatesResponse, CharacterTimelineItem, CharacterTimelineResponse, ...）；导入 10；首轮未确认死代码。
- 070/925 `backend/app/api/routers/writer/content_optimization.py` | py | 已读取 269 行；顶层符号 7（optimize_chapter_content, preview_paragraphs, SessionActionResponse, ContinueSessionRequest, ...）；导入 16；首轮未确认死代码。
- 071/925 `backend/app/api/routers/writer/manga_prompt_v2.py` | py | 已读取 727 行；顶层符号 13（GenerateRequest, PanelResponse, PageResponse, SceneResponse, ...）；导入 16；首轮未确认死代码。
- 072/925 `backend/app/api/routers/writer/part_outlines.py` | py | 已读取 700 行；顶层符号 11（regenerate_part_outlines, regenerate_last_part_outline, regenerate_specific_part_outline, generate_part_outlines, ...）；导入 18；首轮未确认死代码。
- 073/925 `backend/app/api/routers/writer/project_workflow.py` | py | 已读取 509 行；顶层符号 11（_status_value, _find_rollback_path, _get_chapter_stats, _get_outline_stats, ...）；导入 17；首轮未确认死代码。
- 074/925 `backend/app/api/routers/writer/rag_query.py` | py | 已读取 202 行；顶层符号 5（RAGQueryRequest, ChunkResult, SummaryResult, RAGQueryResponse, ...）；导入 12；首轮未确认死代码。
- 075/925 `backend/app/core/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 076/925 `backend/app/core/config.py` | py | 已读取 749 行；顶层符号 9（_resolve_project_root, _resolve_storage_dir, _resolve_env_files, _preload_yaml_list_env_lines, ...）；导入 9；首轮未确认死代码。
- 077/925 `backend/app/core/constants.py` | py | 已读取 141 行；顶层符号 8（GenerationStatus, NovelConstants, LLMConstants, VectorConstants, ...）；导入 1；首轮未确认死代码。
- 078/925 `backend/app/core/dependencies.py` | py | 已读取 485 行；顶层符号 20（_extract_bearer_token, get_default_user, require_admin_user, get_vector_store, ...）；导入 8；首轮未确认死代码。
- 079/925 `backend/app/core/logging_config.py` | py | 已读取 446 行；顶层符号 11（_get_logs_dir, _get_config_path, _load_user_config, _get_domain_for_logger, ...）；导入 8；首轮未确认死代码。
- 080/925 `backend/app/core/security.py` | py | 已读取 26 行；顶层符号 2（hash_password, verify_password）；导入 1；首轮未确认死代码。
- 081/925 `backend/app/core/state_machine.py` | py | 已读取 255 行；顶层符号 3（ProjectStatus, ProjectType, ProjectStateMachine）；导入 4；首轮未确认死代码。
- 082/925 `backend/app/core/state_validators.py` | py | 已读取 182 行；顶层符号 11（validate_project_status, check_writing_coherence, get_max_generated_chapter, require_outline_generation_status, ...）；导入 3；首轮未确认死代码。
- 083/925 `backend/app/db/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 084/925 `backend/app/db/base.py` | py | 已读取 9 行；顶层符号 1（Base）；导入 1；首轮未确认死代码。
- 085/925 `backend/app/db/init_db.py` | py | 已读取 675 行；顶层符号 7（_parse_yaml_frontmatter, init_db, _ensure_database_exists, _ensure_default_prompts, ...）；导入 16；首轮未确认死代码。
- 086/925 `backend/app/db/session.py` | py | 已读取 46 行；顶层符号 1（get_session）；导入 5；首轮未确认死代码。
- 087/925 `backend/app/exceptions.py` | py | 已读取 238 行；顶层符号 17（AFNException, ResourceNotFoundError, PermissionDeniedError, InvalidParameterError, ...）；导入 1；首轮未确认死代码。
- 088/925 `backend/app/main.py` | py | 已读取 162 行；顶层符号 6（_preload_embedding_model_if_needed, lifespan, afn_exception_handler, global_exception_handler, ...）；导入 16；首轮未确认死代码。
- 089/925 `backend/app/models/__init__.py` | py | 已读取 84 行；顶层符号 0（无）；导入 12；首轮未确认死代码。
- 090/925 `backend/app/models/character_portrait.py` | py | 已读取 94 行；顶层符号 1（CharacterPortrait）；导入 5；首轮未确认死代码。
- 091/925 `backend/app/models/coding.py` | py | 已读取 192 行；顶层符号 5（CodingProject, CodingConversation, CodingBlueprint, CodingSystem, ...）；导入 7；首轮未确认死代码。
- 092/925 `backend/app/models/coding_files.py` | py | 已读取 259 行；顶层符号 4（CodingDirectoryNode, CodingSourceFile, CodingAgentState, CodingFileVersion）；导入 7；首轮未确认死代码。
- 093/925 `backend/app/models/embedding_config.py` | py | 已读取 38 行；顶层符号 1（EmbeddingConfig）；导入 4；首轮未确认死代码。
- 094/925 `backend/app/models/image_config.py` | py | 已读取 118 行；顶层符号 2（ImageGenerationConfig, GeneratedImage）；导入 6；首轮未确认死代码。
- 095/925 `backend/app/models/llm_config.py` | py | 已读取 23 行；顶层符号 1（LLMConfig）；导入 4；首轮未确认死代码。
- 096/925 `backend/app/models/mixins.py` | py | 已读取 38 行；顶层符号 3（ActivationStatusMixin, TestStatusMixin, TimestampsMixin）；导入 3；首轮未确认死代码。
- 097/925 `backend/app/models/novel.py` | py | 已读取 457 行；顶层符号 13（_MetadataAccessor, NovelProject, NovelConversation, NovelBlueprint, ...）；导入 8；首轮未确认死代码。
- 098/925 `backend/app/models/part_outline.py` | py | 已读取 55 行；顶层符号 1（PartOutline）；导入 6；首轮未确认死代码。
- 099/925 `backend/app/models/prompt.py` | py | 已读取 27 行；顶层符号 1（Prompt）；导入 5；首轮未确认死代码。
- 100/925 `backend/app/models/protagonist.py` | py | 已读取 278 行；顶层符号 5（ProtagonistProfile, ProtagonistAttributeChange, ProtagonistBehaviorRecord, ProtagonistDeletionMark, ...）；导入 7；首轮未确认死代码。
- 101/925 `backend/app/models/theme_config.py` | py | 已读取 132 行；顶层符号 1（ThemeConfig）；导入 6；首轮未确认死代码。
- 102/925 `backend/app/models/user.py` | py | 已读取 33 行；顶层符号 1（User）；导入 5；首轮未确认死代码。
- 103/925 `backend/app/repositories/__init__.py` | py | 已读取 46 行；顶层符号 0（无）；导入 11；首轮未确认死代码。
- 104/925 `backend/app/repositories/base.py` | py | 已读取 405 行；顶层符号 3（SequenceRepositoryMixin, RelationOptionsMixin, BaseRepository）；导入 4；首轮未确认死代码。
- 105/925 `backend/app/repositories/blueprint_repository.py` | py | 已读取 153 行；顶层符号 3（NovelBlueprintRepository, BlueprintCharacterRepository, BlueprintRelationshipRepository）；导入 4；首轮未确认死代码。
- 106/925 `backend/app/repositories/chapter_evaluation_repository.py` | py | 已读取 32 行；顶层符号 1（ChapterEvaluationRepository）；导入 4；首轮未确认死代码。
- 107/925 `backend/app/repositories/chapter_outline_repository.py` | py | 已读取 146 行；顶层符号 1（ChapterOutlineRepository）；导入 4；首轮未确认死代码。
- 108/925 `backend/app/repositories/chapter_repository.py` | py | 已读取 197 行；顶层符号 1（ChapterRepository）；导入 8；首轮未确认死代码。
- 109/925 `backend/app/repositories/chapter_version_repository.py` | py | 已读取 77 行；顶层符号 1（ChapterVersionRepository）；导入 4；首轮未确认死代码。
- 110/925 `backend/app/repositories/character_portrait_repository.py` | py | 已读取 223 行；顶层符号 1（CharacterPortraitRepository）；导入 5；首轮未确认死代码。
- 111/925 `backend/app/repositories/coding_files_repository.py` | py | 已读取 456 行；顶层符号 4（CodingDirectoryNodeRepository, CodingSourceFileRepository, CodingFileVersionRepository, CodingAgentStateRepository）；导入 6；首轮未确认死代码。
- 112/925 `backend/app/repositories/coding_repository.py` | py | 已读取 162 行；顶层符号 5（CodingProjectRepository, CodingConversationRepository, CodingBlueprintRepository, CodingSystemRepository, ...）；导入 6；首轮未确认死代码。
- 113/925 `backend/app/repositories/conversation_repository.py` | py | 已读取 101 行；顶层符号 2（NovelConversationRepository, CodingConversationRepository）；导入 5；首轮未确认死代码。
- 114/925 `backend/app/repositories/embedding_config_repository.py` | py | 已读取 58 行；顶层符号 1（EmbeddingConfigRepository）；导入 4；首轮未确认死代码。
- 115/925 `backend/app/repositories/llm_config_repository.py` | py | 已读取 59 行；顶层符号 1（LLMConfigRepository）；导入 4；首轮未确认死代码。
- 116/925 `backend/app/repositories/manga_prompt_repository.py` | py | 已读取 429 行；顶层符号 1（MangaPromptRepository）；导入 5；首轮未确认死代码。
- 117/925 `backend/app/repositories/novel_repository.py` | py | 已读取 132 行；顶层符号 1（NovelRepository）；导入 6；首轮未确认死代码。
- 118/925 `backend/app/repositories/part_outline_repository.py` | py | 已读取 61 行；顶层符号 1（PartOutlineRepository）；导入 4；首轮未确认死代码。
- 119/925 `backend/app/repositories/prompt_repository.py` | py | 已读取 19 行；顶层符号 1（PromptRepository）；导入 5；首轮未确认死代码。
- 120/925 `backend/app/repositories/protagonist_repository.py` | py | 已读取 442 行；顶层符号 5（ProtagonistProfileRepository, ProtagonistAttributeChangeRepository, ProtagonistBehaviorRecordRepository, ProtagonistDeletionMarkRepository, ...）；导入 5；首轮未确认死代码。
- 121/925 `backend/app/repositories/theme_config_repository.py` | py | 已读取 93 行；顶层符号 1（ThemeConfigRepository）；导入 4；首轮未确认死代码。
- 122/925 `backend/app/repositories/user_repository.py` | py | 已读取 91 行；顶层符号 1（UserRepository）；导入 4；首轮未确认死代码。
- 123/925 `backend/app/schemas/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 124/925 `backend/app/schemas/character_portrait.py` | py | 已读取 167 行；顶层符号 9（CharacterPortraitBase, GeneratePortraitRequest, RegeneratePortraitRequest, AutoGeneratePortraitsRequest, ...）；导入 3；首轮未确认死代码。
- 125/925 `backend/app/schemas/coding.py` | py | 已读取 280 行；顶层符号 28（CodingSystemStatus, TechComponent, TechDomain, TechStack, ...）；导入 3；首轮未确认死代码。
- 126/925 `backend/app/schemas/coding_files.py` | py | 已读取 305 行；顶层符号 31（DirectoryNodeType, FileType, FileGenerationStatus, DirectoryGenerationStatus, ...）；导入 4；首轮未确认死代码。
- 127/925 `backend/app/schemas/config.py` | py | 已读取 23 行；顶层符号 4（SystemConfigBase, SystemConfigCreate, SystemConfigUpdate, SystemConfigRead）；导入 2；首轮未确认死代码。
- 128/925 `backend/app/schemas/config_runtime_status.py` | py | 已读取 25 行；顶层符号 1（ConfigRuntimeStatus）；导入 3；首轮未确认死代码。
- 129/925 `backend/app/schemas/embedding_config.py` | py | 已读取 163 行；顶层符号 9（EmbeddingConfigBase, EmbeddingConfigCreate, EmbeddingConfigUpdate, EmbeddingConfigRead, ...）；导入 5；首轮未确认死代码。
- 130/925 `backend/app/schemas/llm_config.py` | py | 已读取 114 行；顶层符号 10（LLMConfigBase, LLMConfigCreate, LLMConfigUpdate, LLMConfigRead, ...）；导入 5；首轮未确认死代码。
- 131/925 `backend/app/schemas/model_download.py` | py | 已读取 29 行；顶层符号 1（DownloadDefaultLocalEmbeddingModelRequest）；导入 2；首轮未确认死代码。
- 132/925 `backend/app/schemas/novel.py` | py | 已读取 491 行；顶层符号 50（ChoiceOption, UIControl, ConverseResponse, ConverseRequest, ...）；导入 4；首轮未确认死代码。
- 133/925 `backend/app/schemas/project_workflow.py` | py | 已读取 85 行；顶层符号 5（ProjectWorkflowCleanupImpact, ProjectWorkflowRollbackStepPreview, ProjectWorkflowRollbackPreviewResponse, ProjectWorkflowRollbackRequest, ...）；导入 2；首轮未确认死代码。
- 134/925 `backend/app/schemas/prompt.py` | py | 已读取 64 行；顶层符号 4（PromptBase, PromptCreate, PromptUpdate, PromptRead）；导入 2；首轮未确认死代码。
- 135/925 `backend/app/schemas/protagonist.py` | py | 已读取 367 行；顶层符号 36（AttributeCategory, AttributeOperation, ClassificationResult, ProtagonistProfileBase, ...）；导入 4；首轮未确认死代码。
- 136/925 `backend/app/schemas/queue.py` | py | 已读取 42 行；顶层符号 4（QueueStatus, QueueStatusResponse, QueueConfigResponse, QueueConfigUpdate）；导入 2；首轮未确认死代码。
- 137/925 `backend/app/schemas/schema_utils.py` | py | 已读取 17 行；顶层符号 1（mask_api_key）；导入 2；首轮未确认死代码。
- 138/925 `backend/app/schemas/theme_config.py` | py | 已读取 490 行；顶层符号 27（PrimaryColorsSchema, AccentColorsSchema, SemanticColorsSchema, TextColorsSchema, ...）；导入 3；首轮未确认死代码。
- 139/925 `backend/app/schemas/user.py` | py | 已读取 19 行；顶层符号 1（UserInDB）；导入 3；首轮未确认死代码。
- 140/925 `backend/app/serializers/__init__.py` | py | 已读取 10 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 141/925 `backend/app/serializers/coding_files_serializer.py` | py | 已读取 62 行；顶层符号 2（build_source_file_response, build_directory_node_response）；导入 2；首轮未确认死代码。
- 142/925 `backend/app/serializers/coding_serializer.py` | py | 已读取 292 行；顶层符号 1（CodingSerializer）；导入 5；首轮未确认死代码。
- 143/925 `backend/app/serializers/novel_serializer.py` | py | 已读取 439 行；顶层符号 1（NovelSerializer）；导入 6；首轮未确认死代码。
- 144/925 `backend/app/serializers/part_outline_serializer.py` | py | 已读取 30 行；顶层符号 1（build_part_outline_schema）；导入 3；首轮未确认死代码。
- 145/925 `backend/app/services/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 146/925 `backend/app/services/agent_tool_executor_base.py` | py | 已读取 102 行；顶层符号 1（BaseToolExecutor）；导入 4；首轮未确认死代码。
- 147/925 `backend/app/services/avatar_service.py` | py | 已读取 250 行；顶层符号 1（AvatarService）；导入 10；首轮未确认死代码。
- 148/925 `backend/app/services/blueprint_base.py` | py | 已读取 118 行；顶层符号 1（BlueprintServiceBase）；导入 5；首轮未确认死代码。
- 149/925 `backend/app/services/blueprint_service.py` | py | 已读取 684 行；顶层符号 2（BlueprintGenerationResult, BlueprintService）；导入 20；首轮未确认死代码。
- 150/925 `backend/app/services/chapter_analysis_service.py` | py | 已读取 250 行；顶层符号 1（ChapterAnalysisService）；导入 8；首轮未确认死代码。
- 151/925 `backend/app/services/chapter_context_service.py` | py | 已读取 454 行；顶层符号 4（ChapterRAGContext, ChapterContextService, EnhancedRAGContext, EnhancedChapterContextService）；导入 12；首轮未确认死代码。
- 152/925 `backend/app/services/chapter_evaluation_service.py` | py | 已读取 443 行；顶层符号 3（EvaluationContext, ChapterEvaluationWorkflow, ChapterEvaluationService）；导入 12；首轮未确认死代码。
- 153/925 `backend/app/services/chapter_generation/__init__.py` | py | 已读取 32 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 154/925 `backend/app/services/chapter_generation/context.py` | py | 已读取 101 行；顶层符号 2（ChapterGenerationContext, ChapterGenerationResult）；导入 2；首轮未确认死代码。
- 155/925 `backend/app/services/chapter_generation/prompt_builder.py` | py | 已读取 484 行；顶层符号 2（ChapterPromptBuilder, get_chapter_prompt_builder）；导入 7；首轮未确认死代码。
- 156/925 `backend/app/services/chapter_generation/service.py` | py | 已读取 732 行；顶层符号 1（ChapterGenerationService）；导入 21；首轮未确认死代码。
- 157/925 `backend/app/services/chapter_generation/version_processor.py` | py | 已读取 150 行；顶层符号 2（ChapterVersionProcessor, get_version_processor）；导入 5；首轮未确认死代码。
- 158/925 `backend/app/services/chapter_generation/workflow.py` | py | 已读取 436 行；顶层符号 1（ChapterGenerationWorkflow）；导入 8；首轮未确认死代码。
- 159/925 `backend/app/services/chapter_ingest_service.py` | py | 已读取 426 行；顶层符号 2（ParagraphSplitter, ChapterIngestionService）；导入 9；首轮未确认死代码。
- 160/925 `backend/app/services/chapter_version_service.py` | py | 已读取 425 行；顶层符号 1（ChapterVersionService）；导入 11；首轮未确认死代码。
- 161/925 `backend/app/services/character_portrait_service.py` | py | 已读取 615 行；顶层符号 2（get_portraits_root, CharacterPortraitService）；导入 14；首轮未确认死代码。
- 162/925 `backend/app/services/coding/__init__.py` | py | 已读取 13 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 163/925 `backend/app/services/coding/blueprint_service.py` | py | 已读取 233 行；顶层符号 1（CodingBlueprintService）；导入 10；首轮未确认死代码。
- 164/925 `backend/app/services/coding/project_service.py` | py | 已读取 271 行；顶层符号 1（CodingProjectService）；导入 12；首轮未确认死代码。
- 165/925 `backend/app/services/coding_files/__init__.py` | py | 已读取 46 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 166/925 `backend/app/services/coding_files/architect/__init__.py` | py | 已读取 63 行；顶层符号 0（无）；导入 7；首轮未确认死代码。
- 167/925 `backend/app/services/coding_files/architect/decision_maker.py` | py | 已读取 363 行；顶层符号 1（ArchitectureDecisionMaker）；导入 5；首轮未确认死代码。
- 168/925 `backend/app/services/coding_files/architect/generator.py` | py | 已读取 690 行；顶层符号 1（ArchitectureBasedGenerator）；导入 7；首轮未确认死代码。
- 169/925 `backend/app/services/coding_files/architect/patterns.py` | py | 已读取 395 行；顶层符号 3（PatternTemplate, get_pattern_template, recommend_pattern）；导入 3；首轮未确认死代码。
- 170/925 `backend/app/services/coding_files/architect/profiler.py` | py | 已读取 419 行；顶层符号 1（ProjectProfiler）；导入 6；首轮未确认死代码。
- 171/925 `backend/app/services/coding_files/architect/quality_evaluator.py` | py | 已读取 595 行；顶层符号 1（QualityEvaluator）；导入 6；首轮未确认死代码。
- 172/925 `backend/app/services/coding_files/architect/refiner.py` | py | 已读取 453 行；顶层符号 1（RefinementAgent）；导入 6；首轮未确认死代码。
- 173/925 `backend/app/services/coding_files/architect/schemas.py` | py | 已读取 452 行；顶层符号 13（ArchitecturePattern, SystemSummary, ModuleSummary, DependencyGraph, ...）；导入 3；首轮未确认死代码。
- 174/925 `backend/app/services/coding_files/architect/utils.py` | py | 已读取 24 行；顶层符号 1（get_file_extension）；导入 1；首轮未确认死代码。
- 175/925 `backend/app/services/coding_files/directory_agent/__init__.py` | py | 已读取 48 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 176/925 `backend/app/services/coding_files/directory_agent/agent.py` | py | 已读取 581 行；顶层符号 2（DirectoryPlanningAgent, run_directory_planning_agent）；导入 6；首轮未确认死代码。
- 177/925 `backend/app/services/coding_files/directory_agent/evaluator.py` | py | 已读取 283 行；顶层符号 4（EvaluationDimension, FileEvaluation, OverallEvaluation, PlanningEvaluator）；导入 3；首轮未确认死代码。
- 178/925 `backend/app/services/coding_files/directory_agent/tool_executor.py` | py | 已读取 1020 行；顶层符号 5（OptimizationRecord, PlannedDirectory, PlannedFile, AgentState, ...）；导入 9；首轮未确认死代码。
- 179/925 `backend/app/services/coding_files/directory_agent/tools.py` | py | 已读取 508 行；顶层符号 11（ToolCategory, ToolDefinition, get_tool, get_tools_by_category, ...）；导入 5；首轮未确认死代码。
- 180/925 `backend/app/services/coding_files/directory_generator/__init__.py` | py | 已读取 23 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 181/925 `backend/app/services/coding_files/directory_generator/schemas.py` | py | 已读取 141 行；顶层符号 5（PlannedFile, PlannedDirectory, DirectorySpec, FileSpec, ...）；导入 3；首轮未确认死代码。
- 182/925 `backend/app/services/coding_files/directory_generator/tree_builder.py` | py | 已读取 232 行；顶层符号 1（DirectoryTreeBuilder）；导入 4；首轮未确认死代码。
- 183/925 `backend/app/services/coding_files/directory_service.py` | py | 已读取 778 行；顶层符号 1（DirectoryStructureService）；导入 13；首轮未确认死代码。
- 184/925 `backend/app/services/coding_files/file_prompt/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 185/925 `backend/app/services/coding_files/file_prompt/file_ops.py` | py | 已读取 299 行；顶层符号 1（FileOpsMixin）；导入 6；首轮未确认死代码。
- 186/925 `backend/app/services/coding_files/file_prompt/generation.py` | py | 已读取 395 行；顶层符号 1（GenerationMixin）；导入 6；首轮未确认死代码。
- 187/925 `backend/app/services/coding_files/file_prompt/ingestion.py` | py | 已读取 159 行；顶层符号 1（IngestionMixin）；导入 5；首轮未确认死代码。
- 188/925 `backend/app/services/coding_files/file_prompt/prompts.py` | py | 已读取 227 行；顶层符号 1（PromptsMixin）；导入 4；首轮未确认死代码。
- 189/925 `backend/app/services/coding_files/file_prompt/rag.py` | py | 已读取 121 行；顶层符号 1（RagMixin）；导入 6；首轮未确认死代码。
- 190/925 `backend/app/services/coding_files/file_prompt/review.py` | py | 已读取 128 行；顶层符号 1（ReviewMixin）；导入 5；首轮未确认死代码。
- 191/925 `backend/app/services/coding_files/file_prompt/workflows.py` | py | 已读取 207 行；顶层符号 2（FileReviewWorkflow, FilePromptGenerationWorkflow）；导入 6；首轮未确认死代码。
- 192/925 `backend/app/services/coding_files/file_prompt_service.py` | py | 已读取 44 行；顶层符号 1（FilePromptService）；导入 11；首轮未确认死代码。
- 193/925 `backend/app/services/coding_files/graph_utils.py` | py | 已读取 46 行；顶层符号 1（detect_cycles）；导入 2；首轮未确认死代码。
- 194/925 `backend/app/services/coding_rag/__init__.py` | py | 已读取 59 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 195/925 `backend/app/services/coding_rag/auto_ingestion.py` | py | 已读取 57 行；顶层符号 1（trigger_blueprint_ingestion）；导入 5；首轮未确认死代码。
- 196/925 `backend/app/services/coding_rag/chunk_strategy.py` | py | 已读取 233 行；顶层符号 6（ChunkMethod, ChunkConfig, ChunkStrategyManager, get_strategy_manager, ...）；导入 6；首轮未确认死代码。
- 197/925 `backend/app/services/coding_rag/content_splitter.py` | py | 已读取 607 行；顶层符号 3（Section, IngestionRecord, ContentSplitter）；导入 8；首轮未确认死代码。
- 198/925 `backend/app/services/coding_rag/data_types.py` | py | 已读取 86 行；顶层符号 1（CodingDataType）；导入 2；首轮未确认死代码。
- 199/925 `backend/app/services/coding_rag/ingestion_service.py` | py | 已读取 1245 行；顶层符号 1（CodingProjectIngestionService）；导入 11；首轮未确认死代码。
- 200/925 `backend/app/services/config_service_base.py` | py | 已读取 71 行；顶层符号 1（BaseConfigService）；导入 5；首轮未确认死代码。
- 201/925 `backend/app/services/content_optimization/__init__.py` | py | 已读取 47 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 202/925 `backend/app/services/content_optimization/agent.py` | py | 已读取 687 行；顶层符号 1（ContentOptimizationAgent）；导入 12；首轮未确认死代码。
- 203/925 `backend/app/services/content_optimization/coherence_checker.py` | py | 已读取 321 行；顶层符号 1（CoherenceChecker）；导入 4；首轮未确认死代码。
- 204/925 `backend/app/services/content_optimization/paragraph_analyzer.py` | py | 已读取 381 行；顶层符号 1（ParagraphAnalyzer）；导入 5；首轮未确认死代码。
- 205/925 `backend/app/services/content_optimization/schemas.py` | py | 已读取 413 行；顶层符号 25（CheckDimension, AnalysisScope, OptimizationMode, OptimizationEventType, ...）；导入 4；首轮未确认死代码。
- 206/925 `backend/app/services/content_optimization/service.py` | py | 已读取 162 行；顶层符号 1（ContentOptimizationService）；导入 6；首轮未确认死代码。
- 207/925 `backend/app/services/content_optimization/session_manager.py` | py | 已读取 309 行；顶层符号 3（OptimizationSession, OptimizationSessionManager, get_session_manager）；导入 7；首轮未确认死代码。
- 208/925 `backend/app/services/content_optimization/tool_executor.py` | py | 已读取 1038 行；顶层符号 2（AgentState, ToolExecutor）；导入 11；首轮未确认死代码。
- 209/925 `backend/app/services/content_optimization/tools.py` | py | 已读取 352 行；顶层符号 8（ToolName, ToolDefinition, ToolCall, ToolResult, ...）；导入 3；首轮未确认死代码。
- 210/925 `backend/app/services/content_optimization/workflow.py` | py | 已读取 260 行；顶层符号 1（ContentOptimizationWorkflow）；导入 9；首轮未确认死代码。
- 211/925 `backend/app/services/conversation_service.py` | py | 已读取 140 行；顶层符号 1（ConversationService）；导入 7；首轮未确认死代码。
- 212/925 `backend/app/services/embedding_config_service.py` | py | 已读取 490 行；顶层符号 1（EmbeddingConfigService）；导入 11；首轮未确认死代码。
- 213/925 `backend/app/services/embedding_service.py` | py | 已读取 888 行；顶层符号 10（_check_sentence_transformers, _get_package_version, _is_meta_tensor_error, _get_torch_device, ...）；导入 12；首轮未确认死代码。
- 214/925 `backend/app/services/evaluation_workflow_base.py` | py | 已读取 136 行；顶层符号 2（EvaluationPromptContext, EvaluationWorkflowBase）；导入 3；首轮未确认死代码。
- 215/925 `backend/app/services/foreshadowing_service.py` | py | 已读取 470 行；顶层符号 2（ForeshadowingSuggestion, ForeshadowingService）；导入 6；首轮未确认死代码。
- 216/925 `backend/app/services/hf_model_download_service.py` | py | 已读取 295 行；顶层符号 8（DownloadStoppedError, HFRepoFile, resolve_hf_endpoint, sanitize_model_dir_name, ...）；导入 10；首轮未确认死代码。
- 217/925 `backend/app/services/image_generation/__init__.py` | py | 已读取 42 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 218/925 `backend/app/services/image_generation/config_service.py` | py | 已读取 321 行；顶层符号 1（ImageConfigService）；导入 9；首轮未确认死代码。
- 219/925 `backend/app/services/image_generation/fs_utils.py` | py | 已读取 64 行；顶层符号 13（get_images_root, get_export_dir, async_exists, async_is_dir, ...）；导入 6；首轮未确认死代码。
- 220/925 `backend/app/services/image_generation/pdf_export.py` | py | 已读取 896 行；顶层符号 3（get_page_size, _register_chinese_font, PDFExportService）；导入 11；首轮未确认死代码。
- 221/925 `backend/app/services/image_generation/providers/__init__.py` | py | 已读取 21 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 222/925 `backend/app/services/image_generation/providers/base.py` | py | 已读取 938 行；顶层符号 4（ProviderTestResult, ProviderGenerateResult, ReferenceImageInfo, BaseImageProvider）；导入 11；首轮未确认死代码。
- 223/925 `backend/app/services/image_generation/providers/comfyui.py` | py | 已读取 825 行；顶层符号 1（ComfyUIProvider）；导入 12；首轮未确认死代码。
- 224/925 `backend/app/services/image_generation/providers/factory.py` | py | 已读取 95 行；顶层符号 1（ImageProviderFactory）；导入 3；首轮未确认死代码。
- 225/925 `backend/app/services/image_generation/providers/openai_compatible.py` | py | 已读取 431 行；顶层符号 1（OpenAICompatibleProvider）；导入 9；首轮未确认死代码。
- 226/925 `backend/app/services/image_generation/providers/stability.py` | py | 已读取 245 行；顶层符号 1（StabilityProvider）；导入 7；首轮未确认死代码。
- 227/925 `backend/app/services/image_generation/schemas.py` | py | 已读取 430 行；顶层符号 22（ProviderType, ImageStyle, AspectRatio, get_size_for_ratio, ...）；导入 4；首轮未确认死代码。
- 228/925 `backend/app/services/image_generation/service.py` | py | 已读取 1375 行；顶层符号 4（_is_complete_negative_prompt, smart_merge_negative_prompt, HTTPClientManager, ImageGenerationService）；导入 19；首轮未确认死代码。
- 229/925 `backend/app/services/import_analysis/__init__.py` | py | 已读取 63 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 230/925 `backend/app/services/import_analysis/models.py` | py | 已读取 32 行；顶层符号 2（ChapterSummary, ImportResult）；导入 2；首轮未确认死代码。
- 231/925 `backend/app/services/import_analysis/progress_tracker.py` | py | 已读取 320 行；顶层符号 1（ProgressTracker）；导入 6；首轮未确认死代码。
- 232/925 `backend/app/services/import_analysis/service.py` | py | 已读取 869 行；顶层符号 1（ImportAnalysisService）；导入 23；首轮未确认死代码。
- 233/925 `backend/app/services/import_analysis/txt_parser.py` | py | 已读取 531 行；顶层符号 7（count_chinese_characters, ParsedChapter, ParseResult, BaseTxtParser, ...）；导入 5；首轮未确认死代码。
- 234/925 `backend/app/services/incremental_indexer.py` | py | 已读取 594 行；顶层符号 1（IncrementalIndexer）；导入 7；首轮未确认死代码。
- 235/925 `backend/app/services/inspiration_service.py` | py | 已读取 541 行；顶层符号 2（InspirationResult, InspirationService）；导入 16；首轮未确认死代码。
- 236/925 `backend/app/services/llm_config_service.py` | py | 已读取 437 行；顶层符号 2（_invalidate_llm_config_cache, LLMConfigService）；导入 12；首轮未确认死代码。
- 237/925 `backend/app/services/llm_service.py` | py | 已读取 648 行；顶层符号 2（LLMConfigCache, LLMService）；导入 18；首轮未确认死代码。
- 238/925 `backend/app/services/llm_wrappers.py` | py | 已读取 361 行；顶层符号 5（LLMProfile, LLMCallConfig, get_profile_config, call_llm, ...）；导入 6；首轮未确认死代码。
- 239/925 `backend/app/services/manga_prompt/__init__.py` | py | 已读取 99 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 240/925 `backend/app/services/manga_prompt/core/__init__.py` | py | 已读取 35 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 241/925 `backend/app/services/manga_prompt/core/checkpoint_manager.py` | py | 已读取 105 行；顶层符号 1（CheckpointManager）；导入 4；首轮未确认死代码。
- 242/925 `backend/app/services/manga_prompt/core/models.py` | py | 已读取 18 行；顶层符号 1（MangaStyle）；导入 0；首轮未确认死代码。
- 243/925 `backend/app/services/manga_prompt/core/page_layout_utils.py` | py | 已读取 53 行；顶层符号 1（PageLayoutBase）；导入 2；首轮未确认死代码。
- 244/925 `backend/app/services/manga_prompt/core/page_prompt_builder.py` | py | 已读取 142 行；顶层符号 1（build_page_prompt_for_generation）；导入 2；首轮未确认死代码。
- 245/925 `backend/app/services/manga_prompt/core/result_persistence.py` | py | 已读取 128 行；顶层符号 1（ResultPersistence）；导入 5；首轮未确认死代码。
- 246/925 `backend/app/services/manga_prompt/core/service.py` | py | 已读取 1514 行；顶层符号 2（MangaPromptServiceV2, generate_manga_prompts）；导入 18；首轮未确认死代码。
- 247/925 `backend/app/services/manga_prompt/extraction/__init__.py` | py | 已读取 53 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 248/925 `backend/app/services/manga_prompt/extraction/chapter_info_extractor.py` | py | 已读取 766 行；顶层符号 1（ChapterInfoExtractor）；导入 8；首轮未确认死代码。
- 249/925 `backend/app/services/manga_prompt/extraction/models.py` | py | 已读取 479 行；顶层符号 11（EmotionType, EventType, CharacterRole, ImportanceLevel, ...）；导入 3；首轮未确认死代码。
- 250/925 `backend/app/services/manga_prompt/extraction/prompts.py` | py | 已读取 459 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 251/925 `backend/app/services/manga_prompt/planning/__init__.py` | py | 已读取 30 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 252/925 `backend/app/services/manga_prompt/planning/models.py` | py | 已读取 84 行；顶层符号 2（PagePlanItem, PagePlanResult）；导入 2；首轮未确认死代码。
- 253/925 `backend/app/services/manga_prompt/planning/page_planner.py` | py | 已读取 310 行；顶层符号 1（PagePlanner）；导入 10；首轮未确认死代码。
- 254/925 `backend/app/services/manga_prompt/planning/prompts.py` | py | 已读取 100 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 255/925 `backend/app/services/manga_prompt/prompt_builder/__init__.py` | py | 已读取 25 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 256/925 `backend/app/services/manga_prompt/prompt_builder/builder.py` | py | 已读取 602 行；顶层符号 6（_resolve_panel_value, _resolve_panel_int, build_layout_template, build_panel_summary, ...）；导入 5；首轮未确认死代码。
- 257/925 `backend/app/services/manga_prompt/prompt_builder/models.py` | py | 已读取 221 行；顶层符号 4（PanelPrompt, PagePrompt, PagePromptResult, MangaPromptResult）；导入 3；首轮未确认死代码。
- 258/925 `backend/app/services/manga_prompt/prompt_builder/page_prompt_generator.py` | py | 已读取 491 行；顶层符号 1（PagePromptGenerator）；导入 9；首轮未确认死代码。
- 259/925 `backend/app/services/manga_prompt/prompts_shared.py` | py | 已读取 16 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 260/925 `backend/app/services/manga_prompt/storyboard/__init__.py` | py | 已读取 45 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 261/925 `backend/app/services/manga_prompt/storyboard/designer.py` | py | 已读取 426 行；顶层符号 1（StoryboardDesigner）；导入 10；首轮未确认死代码。
- 262/925 `backend/app/services/manga_prompt/storyboard/models.py` | py | 已读取 266 行；顶层符号 8（ShotType, PanelShape, WidthRatio, AspectRatio, ...）；导入 4；首轮未确认死代码。
- 263/925 `backend/app/services/manga_prompt/storyboard/prompts.py` | py | 已读取 282 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 264/925 `backend/app/services/novel_rag/__init__.py` | py | 已读取 83 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 265/925 `backend/app/services/novel_rag/auto_ingestion.py` | py | 已读取 195 行；顶层符号 7（schedule_multiple_ingestions, trigger_blueprint_ingestion, trigger_inspiration_ingestion, trigger_part_outline_ingestion, ...）；导入 5；首轮未确认死代码。
- 266/925 `backend/app/services/novel_rag/chunk_strategy.py` | py | 已读取 356 行；顶层符号 6（NovelChunkMethod, NovelChunkConfig, NovelChunkStrategyManager, get_novel_strategy_manager, ...）；导入 6；首轮未确认死代码。
- 267/925 `backend/app/services/novel_rag/content_splitter.py` | py | 已读取 1051 行；顶层符号 3（Section, NovelIngestionRecord, NovelContentSplitter）；导入 8；首轮未确认死代码。
- 268/925 `backend/app/services/novel_rag/data_types.py` | py | 已读取 147 行；顶层符号 1（NovelDataType）；导入 2；首轮未确认死代码。
- 269/925 `backend/app/services/novel_rag/ingestion_service.py` | py | 已读取 1172 行；顶层符号 2（_convert_to_native_types, NovelProjectIngestionService）；导入 14；首轮未确认死代码。
- 270/925 `backend/app/services/novel_service.py` | py | 已读取 529 行；顶层符号 1（NovelService）；导入 14；首轮未确认死代码。
- 271/925 `backend/app/services/part_outline/__init__.py` | py | 已读取 41 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 272/925 `backend/app/services/part_outline/chapter_outline_workflow.py` | py | 已读取 260 行；顶层符号 3（GenerationCancelledException, ChapterOutlineWorkflow, get_chapter_outline_workflow）；导入 16；首轮未确认死代码。
- 273/925 `backend/app/services/part_outline/context_retriever.py` | py | 已读取 130 行；顶层符号 1（PartOutlineContextRetriever）；导入 3；首轮未确认死代码。
- 274/925 `backend/app/services/part_outline/model_factory.py` | py | 已读取 131 行；顶层符号 2（PartOutlineModelFactory, get_part_outline_factory）；导入 3；首轮未确认死代码。
- 275/925 `backend/app/services/part_outline/parser.py` | py | 已读取 259 行；顶层符号 2（PartOutlineParser, get_part_outline_parser）；导入 5；首轮未确认死代码。
- 276/925 `backend/app/services/part_outline/service.py` | py | 已读取 698 行；顶层符号 1（PartOutlineService）；导入 27；首轮未确认死代码。
- 277/925 `backend/app/services/part_outline/workflow.py` | py | 已读取 328 行；顶层符号 1（PartOutlineWorkflow）；导入 10；首轮未确认死代码。
- 278/925 `backend/app/services/project_factory.py` | py | 已读取 139 行；顶层符号 2（ProjectStage, ProjectTypeConfig）；导入 2；首轮未确认死代码。
- 279/925 `backend/app/services/project_service_base.py` | py | 已读取 103 行；顶层符号 1（ProjectServiceBase）；导入 5；首轮未确认死代码。
- 280/925 `backend/app/services/prompt_builder.py` | py | 已读取 259 行；顶层符号 1（PromptBuilder）；导入 5；首轮未确认死代码。
- 281/925 `backend/app/services/prompt_service.py` | py | 已读取 936 行；顶层符号 5（PromptCache, get_prompt_cache, PromptRegistry, get_prompt_registry, ...）；导入 12；首轮未确认死代码。
- 282/925 `backend/app/services/protagonist_profile/__init__.py` | py | 已读取 17 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 283/925 `backend/app/services/protagonist_profile/analysis_service.py` | py | 已读取 280 行；顶层符号 1（ProtagonistAnalysisService）；导入 9；首轮未确认死代码。
- 284/925 `backend/app/services/protagonist_profile/deletion_protection.py` | py | 已读取 198 行；顶层符号 1（DeletionProtectionService）；导入 5；首轮未确认死代码。
- 285/925 `backend/app/services/protagonist_profile/implicit_tracker.py` | py | 已读取 217 行；顶层符号 1（ImplicitAttributeTracker）；导入 5；首轮未确认死代码。
- 286/925 `backend/app/services/protagonist_profile/service.py` | py | 已读取 624 行；顶层符号 1（ProtagonistProfileService）；导入 8；首轮未确认死代码。
- 287/925 `backend/app/services/protagonist_profile/sync_service.py` | py | 已读取 324 行；顶层符号 1（ProtagonistSyncService）；导入 9；首轮未确认死代码。
- 288/925 `backend/app/services/queue/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 289/925 `backend/app/services/queue/base.py` | py | 已读取 190 行；顶层符号 2（RequestQueue, ConfigurableRequestQueue）；导入 4；首轮未确认死代码。
- 290/925 `backend/app/services/queue/image_queue.py` | py | 已读取 20 行；顶层符号 1（ImageRequestQueue）；导入 1；首轮未确认死代码。
- 291/925 `backend/app/services/queue/llm_queue.py` | py | 已读取 20 行；顶层符号 1（LLMRequestQueue）；导入 1；首轮未确认死代码。
- 292/925 `backend/app/services/rag/__init__.py` | py | 已读取 50 行；顶层符号 0（无）；导入 7；首轮未确认死代码。
- 293/925 `backend/app/services/rag/context_builder.py` | py | 已读取 402 行；顶层符号 4（GenerationContext, BlueprintInfo, RAGContext, SmartContextBuilder）；导入 5；首轮未确认死代码。
- 294/925 `backend/app/services/rag/context_compressor.py` | py | 已读取 540 行；顶层符号 2（ContextCompressor, AdaptiveCompressor）；导入 5；首轮未确认死代码。
- 295/925 `backend/app/services/rag/outline_retriever.py` | py | 已读取 209 行；顶层符号 2（OutlineRAGRetriever, get_outline_rag_retriever）；导入 5；首轮未确认死代码。
- 296/925 `backend/app/services/rag/query_builder.py` | py | 已读取 395 行；顶层符号 3（EnhancedQuery, EnhancedQueryBuilder, EntityAwareQueryEnhancer）；导入 5；首轮未确认死代码。
- 297/925 `backend/app/services/rag/scene_extractor.py` | py | 已读取 222 行；顶层符号 3（SceneState, SceneStateExtractor, get_scene_extractor）；导入 4；首轮未确认死代码。
- 298/925 `backend/app/services/rag/temporal_retriever.py` | py | 已读取 418 行；顶层符号 4（TemporalScoredChunk, TemporalScoredSummary, TemporalAwareRetriever, NearbyChapterPrioritizer）；导入 4；首轮未确认死代码。
- 299/925 `backend/app/services/rag/utils.py` | py | 已读取 338 行；顶层符号 10（extract_involved_characters, truncate_text, build_outline_text, format_chapter_reference, ...）；导入 1；首轮未确认死代码。
- 300/925 `backend/app/services/rag_common/__init__.py` | py | 已读取 45 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 301/925 `backend/app/services/rag_common/auto_ingestion.py` | py | 已读取 246 行；顶层符号 10（should_skip_auto_ingestion, log_skip_auto_ingestion, log_auto_ingestion_failure, log_auto_ingestion_exception, ...）；导入 4；首轮未确认死代码。
- 302/925 `backend/app/services/rag_common/chunk_strategy_base.py` | py | 已读取 188 行；顶层符号 4（clone_chunk_config, serialize_chunk_config, build_chunk_config, BaseChunkStrategyManager）；导入 4；首轮未确认死代码。
- 303/925 `backend/app/services/rag_common/content_splitter_utils.py` | py | 已读取 472 行；顶层符号 16（split_fixed_length_chunks, _choose_overlap_text, _add_overlap_prefix, split_paragraph_chunks, ...）；导入 5；首轮未确认死代码。
- 304/925 `backend/app/services/rag_common/data_type_mixin.py` | py | 已读取 39 行；顶层符号 1（RAGDataTypeMixin）；导入 2；首轮未确认死代码。
- 305/925 `backend/app/services/rag_common/ingestion_base.py` | py | 已读取 628 行；顶层符号 4（IngestionResult, TypeChangeDetail, CompletenessReport, BaseProjectIngestionService）；导入 3；首轮未确认死代码。
- 306/925 `backend/app/services/rag_common/markdown_split_mixin.py` | py | 已读取 38 行；顶层符号 1（MarkdownHeaderSplitMixin）；导入 3；首轮未确认死代码。
- 307/925 `backend/app/services/rag_common/markdown_splitter.py` | py | 已读取 74 行；顶层符号 1（split_markdown_sections）；导入 2；首轮未确认死代码。
- 308/925 `backend/app/services/rag_common/semantic_chunk_config_mixin.py` | py | 已读取 31 行；顶层符号 1（SemanticChunkConfigMixin）；导入 1；首轮未确认死代码。
- 309/925 `backend/app/services/rag_common/semantic_chunker.py` | py | 已读取 861 行；顶层符号 5（SemanticChunkConfig, ChunkResult, SemanticChunker, get_semantic_chunker, ...）；导入 6；首轮未确认死代码。
- 310/925 `backend/app/services/rag_common/text_split_utils.py` | py | 已读取 13 行；顶层符号 1（sentence_boundary_cut_length）；导入 1；首轮未确认死代码。
- 311/925 `backend/app/services/scene_descriptor.py` | py | 已读取 102 行；顶层符号 3（normalize_time_of_day, normalize_time_marker, SceneDescriptor）；导入 2；首轮未确认死代码。
- 312/925 `backend/app/services/summary_service.py` | py | 已读取 199 行；顶层符号 1（SummaryService）；导入 5；首轮未确认死代码。
- 313/925 `backend/app/services/theme_config_service.py` | py | 已读取 671 行；顶层符号 1（ThemeConfigService）；导入 9；首轮未确认死代码。
- 314/925 `backend/app/services/theme_defaults/__init__.py` | py | 已读取 21 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 315/925 `backend/app/services/theme_defaults/utils.py` | py | 已读取 35 行；顶层符号 2（get_theme_defaults, get_theme_v2_defaults）；导入 3；首轮未确认死代码。
- 316/925 `backend/app/services/theme_defaults/v1_defaults.py` | py | 已读取 226 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 317/925 `backend/app/services/theme_defaults/v2_defaults.py` | py | 已读取 513 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 318/925 `backend/app/services/vector_store_service.py` | py | 已读取 1184 行；顶层符号 3（RetrievedChunk, RetrievedSummary, VectorStoreService）；导入 10；首轮未确认死代码。
- 319/925 `backend/app/services/workflow_base.py` | py | 已读取 39 行；顶层符号 1（GenerationWorkflowBase）；导入 3；首轮未确认死代码。
- 320/925 `backend/app/utils/__init__.py` | py | 已读取 0 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 321/925 `backend/app/utils/api_format_utils.py` | py | 已读取 134 行；顶层符号 7（APIFormat, detect_api_format, fix_base_url, build_anthropic_endpoint, ...）；导入 4；首轮未确认死代码。
- 322/925 `backend/app/utils/blueprint_utils.py` | py | 已读取 176 行；顶层符号 5（prepare_blueprint_for_generation, extract_blueprint_characters, extract_world_setting, extract_full_synopsis, ...）；导入 1；首轮未确认死代码。
- 323/925 `backend/app/utils/config_import_utils.py` | py | 已读取 139 行；顶层符号 5（parse_import_data, ensure_export_data_version, resolve_unique_name, ConfigImportLoopResult, ...）；导入 4；首轮未确认死代码。
- 324/925 `backend/app/utils/content_fields.py` | py | 已读取 25 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 325/925 `backend/app/utils/content_normalizer.py` | py | 已读取 186 行；顶层符号 4（normalize_version_content, _coerce_text, _clean_string, count_chinese_characters）；导入 5；首轮未确认死代码。
- 326/925 `backend/app/utils/encryption.py` | py | 已读取 86 行；顶层符号 3（_derive_key, encrypt_api_key, decrypt_api_key）；导入 5；首轮未确认死代码。
- 327/925 `backend/app/utils/exception_helpers.py` | py | 已读取 232 行；顶层符号 5（log_exception, convert_to_http_exception, ExceptionContext, format_exception_chain, ...）；导入 5；首轮未确认死代码。
- 328/925 `backend/app/utils/field_mapping.py` | py | 已读取 50 行；顶层符号 2（build_update_data, apply_mapping_with_defaults）；导入 1；首轮未确认死代码。
- 329/925 `backend/app/utils/json_utils.py` | py | 已读取 634 行；顶层符号 16（remove_think_tags, unwrap_markdown_json, escape_control_chars_in_strings, normalize_chinese_quotes, ...）；导入 6；首轮未确认死代码。
- 330/925 `backend/app/utils/llm_request_logger.py` | py | 已读取 192 行；顶层符号 2（LLMRequestLogger, get_request_logger）；导入 6；首轮未确认死代码。
- 331/925 `backend/app/utils/llm_tool.py` | py | 已读取 649 行；顶层符号 4（ContentCollectMode, ChatMessage, StreamCollectResult, LLMClient）；导入 11；首轮未确认死代码。
- 332/925 `backend/app/utils/prompt_helpers.py` | py | 已读取 62 行；顶层符号 5（ensure_prompt, format_prompt_json, join_prompt_lines, build_prompt_section, ...）；导入 3；首轮未确认死代码。
- 333/925 `backend/app/utils/prompt_include.py` | py | 已读取 139 行；顶层符号 4（PromptFrontmatter, parse_yaml_frontmatter, _parse_include_target, resolve_prompt_includes）；导入 5；首轮未确认死代码。
- 334/925 `backend/app/utils/rag_helpers.py` | py | 已读取 48 行；顶层符号 2（build_query_text, get_query_embedding）；导入 1；首轮未确认死代码。
- 335/925 `backend/app/utils/sse_helpers.py` | py | 已读取 354 行；顶层符号 10（sse_event, create_sse_response, sse_event_stream, create_sse_stream_response, ...）；导入 6；首轮未确认死代码。
- 336/925 `backend/app/utils/text_utils.py` | py | 已读取 149 行；顶层符号 4（truncate, truncate_preview, truncate_middle, mask_sensitive）；导入 1；首轮未确认死代码。
- 337/925 `backend/app/utils/writer_helpers.py` | py | 已读取 72 行；顶层符号 2（extract_tail_excerpt, build_layered_summary）；导入 1；首轮未确认死代码。
- 338/925 `backend/install.bat` | text | 已读取 55 行，判定为非代码文件。
- 339/925 `backend/prompts/_partials/json_only_return_object.md` | text | 已读取 2 行，判定为非代码文件。
- 340/925 `backend/prompts/_partials/json_only_rule.md` | text | 已读取 2 行，判定为非代码文件。
- 341/925 `backend/prompts/_registry.yaml` | text | 已读取 491 行，判定为非代码文件。
- 342/925 `backend/prompts/coding/architecture_design.md` | text | 已读取 211 行，判定为非代码文件。
- 343/925 `backend/prompts/coding/context_compression.md` | text | 已读取 52 行，判定为非代码文件。
- 344/925 `backend/prompts/coding/directory_planning_agent.md` | text | 已读取 262 行，判定为非代码文件。
- 345/925 `backend/prompts/coding/directory_structure_generation.md` | text | 已读取 194 行，判定为非代码文件。
- 346/925 `backend/prompts/coding/file_description_generation.md` | text | 已读取 59 行，判定为非代码文件。
- 347/925 `backend/prompts/coding/file_prompt_generation.md` | text | 已读取 186 行，判定为非代码文件。
- 348/925 `backend/prompts/coding/file_review_generation.md` | text | 已读取 234 行，判定为非代码文件。
- 349/925 `backend/prompts/coding/modules_batch_design.md` | text | 已读取 144 行，判定为非代码文件。
- 350/925 `backend/prompts/coding/requirement_analysis.md` | text | 已读取 140 行，判定为非代码文件。
- 351/925 `backend/prompts/coding/system_design.md` | text | 已读取 124 行，判定为非代码文件。
- 352/925 `backend/prompts/novel/01_inspiration/inspiration.md` | text | 已读取 241 行，判定为非代码文件。
- 353/925 `backend/prompts/novel/02_blueprint/avatar_generation.md` | text | 已读取 351 行，判定为非代码文件。
- 354/925 `backend/prompts/novel/02_blueprint/blueprint.md` | text | 已读取 259 行，判定为非代码文件。
- 355/925 `backend/prompts/novel/02_blueprint/reverse_blueprint.md` | text | 已读取 264 行，判定为非代码文件。
- 356/925 `backend/prompts/novel/03_outline/outline.md` | text | 已读取 282 行，判定为非代码文件。
- 357/925 `backend/prompts/novel/03_outline/part_chapters.md` | text | 已读取 137 行，判定为非代码文件。
- 358/925 `backend/prompts/novel/03_outline/part_outline.md` | text | 已读取 254 行，判定为非代码文件。
- 359/925 `backend/prompts/novel/03_outline/part_outline_single.md` | text | 已读取 166 行，判定为非代码文件。
- 360/925 `backend/prompts/novel/03_outline/reverse_outline.md` | text | 已读取 130 行，判定为非代码文件。
- 361/925 `backend/prompts/novel/03_outline/reverse_part_outline.md` | text | 已读取 174 行，判定为非代码文件。
- 362/925 `backend/prompts/novel/04_writing/chapter_summary_batch.md` | text | 已读取 124 行，判定为非代码文件。
- 363/925 `backend/prompts/novel/04_writing/chapter_summary_single.md` | text | 已读取 112 行，判定为非代码文件。
- 364/925 `backend/prompts/novel/04_writing/extraction.md` | text | 已读取 118 行，判定为非代码文件。
- 365/925 `backend/prompts/novel/04_writing/writing.md` | text | 已读取 117 行，判定为非代码文件。
- 366/925 `backend/prompts/novel/05_analysis/chapter_analysis.md` | text | 已读取 192 行，判定为非代码文件。
- 367/925 `backend/prompts/novel/05_analysis/coherence_check.md` | text | 已读取 153 行，判定为非代码文件。
- 368/925 `backend/prompts/novel/05_analysis/content_optimization_agent.md` | text | 已读取 218 行，判定为非代码文件。
- 369/925 `backend/prompts/novel/05_analysis/evaluation.md` | text | 已读取 205 行，判定为非代码文件。
- 370/925 `backend/prompts/novel/06_manga/manga_extraction_step1.md` | text | 已读取 60 行，判定为非代码文件。
- 371/925 `backend/prompts/novel/06_manga/manga_extraction_step2.md` | text | 已读取 146 行，判定为非代码文件。
- 372/925 `backend/prompts/novel/06_manga/manga_extraction_step3.md` | text | 已读取 50 行，判定为非代码文件。
- 373/925 `backend/prompts/novel/06_manga/manga_extraction_step4.md` | text | 已读取 55 行，判定为非代码文件。
- 374/925 `backend/prompts/novel/06_manga/manga_page_planning.md` | text | 已读取 126 行，判定为非代码文件。
- 375/925 `backend/prompts/novel/06_manga/manga_page_prompt_generation.md` | text | 已读取 103 行，判定为非代码文件。
- 376/925 `backend/prompts/novel/06_manga/manga_storyboard_design.md` | text | 已读取 346 行，判定为非代码文件。
- 377/925 `backend/prompts/novel/07_protagonist/implicit_classification.md` | text | 已读取 108 行，判定为非代码文件。
- 378/925 `backend/prompts/novel/07_protagonist/implicit_update.md` | text | 已读取 109 行，判定为非代码文件。
- 379/925 `backend/prompts/novel/07_protagonist/protagonist_analysis.md` | text | 已读取 139 行，判定为非代码文件。
- 380/925 `backend/requirements.txt` | text | 已读取 26 行，判定为非代码文件。
- 381/925 `backend/run_server.py` | py | 已读取 62 行；顶层符号 1（main）；导入 3；首轮未确认死代码。
- 382/925 `backend/scripts/__init__.py` | py | 已读取 3 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 383/925 `backend/scripts/fix_real_summary.py` | py | 已读取 83 行；顶层符号 1（fix_real_summary）；导入 7；首轮未确认死代码。
- 384/925 `backend/scripts/migrate_add_avatar.py` | py | 已读取 79 行；顶层符号 3（get_db_path, check_column_exists, migrate）；导入 3；首轮未确认死代码。
- 385/925 `backend/scripts/migrate_add_layout_info.py` | py | 已读取 111 行；顶层符号 2（migrate_db, migrate）；导入 2；首轮未确认死代码。
- 386/925 `backend/scripts/smoke_local_embedding.py` | py | 已读取 101 行；顶层符号 2（_ensure_model_env, main）；导入 6；首轮未确认死代码。
- 387/925 `backend/start.bat` | text | 已读取 90 行，判定为非代码文件。
- 388/925 `backend/startup/__init__.py` | py | 已读取 104 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 389/925 `backend/startup/animation.py` | py | 已读取 679 行；顶层符号 2（print_banner, StartupProgress）；导入 10；首轮未确认死代码。
- 390/925 `backend/startup/animation_config.py` | py | 已读取 42 行；顶层符号 1（AnimationConfig）；导入 0；首轮未确认死代码。
- 391/925 `backend/startup/config.py` | py | 已读取 113 行；顶层符号 2（_enable_windows_ansi, Colors）；导入 3；首轮未确认死代码。
- 392/925 `backend/startup/installer.py` | py | 已读取 723 行；顶层符号 15（PackageSpec, DependencyDiff, _normalize_package_name, _parse_requirement_line, ...）；导入 10；首轮未确认死代码。
- 393/925 `backend/startup/logging_setup.py` | py | 已读取 77 行；顶层符号 2（_load_logging_config, setup_logging）；导入 4；首轮未确认死代码。
- 394/925 `backend/startup/port_utils.py` | py | 已读取 104 行；顶层符号 4（is_port_in_use, get_pid_using_port, kill_process_on_port, ensure_port_available）；导入 5；首轮未确认死代码。
- 395/925 `backend/startup/uv_manager.py` | py | 已读取 80 行；顶层符号 3（check_uv_available, install_uv, ensure_uv）；导入 4；首轮未确认死代码。
- 396/925 `deploy/.env.example` | text | 已读取 28 行，判定为非代码文件。
- 397/925 `deploy/Dockerfile.backend` | text | 已读取 26 行，判定为非代码文件。
- 398/925 `deploy/Dockerfile.web` | text | 已读取 21 行，判定为非代码文件。
- 399/925 `deploy/README.md` | text | 已读取 287 行，判定为非代码文件。
- 400/925 `deploy/caddy/Caddyfile` | text | 已读取 15 行，判定为非代码文件。
- 401/925 `deploy/docker-compose.https.caddy.yml` | text | 已读取 23 行，判定为非代码文件。
- 402/925 `deploy/docker-compose.yml` | text | 已读取 38 行，判定为非代码文件。
- 403/925 `deploy/nginx/nginx.conf` | text | 已读取 60 行，判定为非代码文件。
- 404/925 `deploy/scripts/backup.sh` | text | 已读取 38 行，判定为非代码文件。
- 405/925 `deploy/scripts/build.sh` | text | 已读取 8 行，判定为非代码文件。
- 406/925 `deploy/scripts/down.sh` | text | 已读取 8 行，判定为非代码文件。
- 407/925 `deploy/scripts/down_https_caddy.sh` | text | 已读取 8 行，判定为非代码文件。
- 408/925 `deploy/scripts/logs.sh` | text | 已读取 8 行，判定为非代码文件。
- 409/925 `deploy/scripts/logs_https_caddy.sh` | text | 已读取 8 行，判定为非代码文件。
- 410/925 `deploy/scripts/up.sh` | text | 已读取 22 行，判定为非代码文件。
- 411/925 `deploy/scripts/up_https_caddy.sh` | text | 已读取 31 行，判定为非代码文件。
- 412/925 `design-system/afn/MASTER.md` | text | 已读取 203 行，判定为非代码文件。
- 413/925 `design-system/afn/pages/settings.md` | text | 已读取 47 行，判定为非代码文件。
- 414/925 `frontend-web/.eslintrc.cjs` | cjs | 已读取 16 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 415/925 `frontend-web/ELECTRON.md` | text | 已读取 38 行，判定为非代码文件。
- 416/925 `frontend-web/electron/main.cjs` | cjs | 已读取 945 行；顶层符号 139（http, fs, path, net, ...）；导入 7；首轮未确认死代码。
- 417/925 `frontend-web/electron/preload.cjs` | cjs | 已读取 9 行；顶层符号 1（bridge）；导入 1；首轮未确认死代码。
- 418/925 `frontend-web/index.html` | text | 已读取 15 行，判定为非代码文件。
- 419/925 `frontend-web/package-lock.json` | text | 已读取 8556 行，判定为非代码文件。
- 420/925 `frontend-web/package.json` | text | 已读取 75 行，判定为非代码文件。
- 421/925 `frontend-web/postcss.config.js` | js | 已读取 6 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 422/925 `frontend-web/src/App.tsx` | tsx | 已读取 282 行；顶层符号 42（loadNovelList, loadInspirationChat, loadWritingDesk, loadNovelDetail, ...）；导入 15；首轮未确认死代码。
- 423/925 `frontend-web/src/api/adminDashboard.ts` | ts | 已读取 201 行；顶层符号 30（AdminStatusCount, AdminOverviewSummary, AdminOverviewResponse, AdminProjectSummary, ...）；导入 1；首轮未确认死代码。
- 424/925 `frontend-web/src/api/adminUsers.ts` | ts | 已读取 95 行；顶层符号 14（AdminUserMetrics, AdminUserItem, AdminUserMonitorItem, AdminUsersListResponse, ...）；导入 1；首轮未确认死代码。
- 425/925 `frontend-web/src/api/auth.ts` | ts | 已读取 52 行；顶层符号 10（AuthStatusResponse, UserPublic, AuthOkResponse, authApi, ...）；导入 1；首轮未确认死代码。
- 426/925 `frontend-web/src/api/client.ts` | ts | 已读取 114 行；顶层符号 19（API_BASE_URL, AUTH_UNAUTHORIZED_EVENT, LONG_TASK_TIMEOUT_MS, apiClient, ...）；导入 2；首轮未确认死代码。
- 427/925 `frontend-web/src/api/coding.ts` | ts | 已读取 459 行；顶层符号 57（CodingProject, CodingProjectSummary, CreateCodingProjectRequest, CodingChatMessage, ...）；导入 1；首轮未确认死代码。
- 428/925 `frontend-web/src/api/embeddingConfigs.ts` | ts | 已读取 98 行；顶层符号 14（EmbeddingProvider, EmbeddingProviderInfo, EmbeddingConfigRead, EmbeddingConfigCreate, ...）；导入 1；首轮未确认死代码。
- 429/925 `frontend-web/src/api/imageConfigs.ts` | ts | 已读取 71 行；顶层符号 13（ImageProviderType, ImageQualityPreset, ImageConfigBase, ImageConfigResponse, ...）；导入 1；首轮未确认死代码。
- 430/925 `frontend-web/src/api/imageGeneration.ts` | ts | 已读取 174 行；顶层符号 16（GeneratedImageInfo, ImageGenerationResult, ImageGenerationRequest, PageImageGenerationRequest, ...）；导入 2；首轮未确认死代码。
- 431/925 `frontend-web/src/api/llmConfigs.ts` | ts | 已读取 75 行；顶层符号 11（LLMConfigRead, LLMConfigCreate, LLMConfigUpdate, LLMConfigTestResponse, ...）；导入 1；首轮未确认死代码。
- 432/925 `frontend-web/src/api/novels.ts` | ts | 已读取 358 行；顶层符号 45（Novel, NovelProjectDetail, CharacterPortrait, CreateNovelRequest, ...）；导入 2；首轮未确认死代码。
- 433/925 `frontend-web/src/api/prompts.ts` | ts | 已读取 46 行；顶层符号 8（PromptRead, PromptUpdate, promptsApi, response, ...）；导入 1；首轮未确认死代码。
- 434/925 `frontend-web/src/api/protagonist.ts` | ts | 已读取 291 行；顶层符号 34（ProtagonistProfileSummary, ProtagonistProfileResponse, ProtagonistSyncResult, AttributeCategory, ...）；导入 1；首轮未确认死代码。
- 435/925 `frontend-web/src/api/queue.ts` | ts | 已读取 41 行；顶层符号 8（QueueStatus, QueueStatusResponse, QueueConfigResponse, QueueConfigUpdate, ...）；导入 1；首轮未确认死代码。
- 436/925 `frontend-web/src/api/settings.ts` | ts | 已读取 98 行；顶层符号 14（AdvancedConfig, MaxTokensConfig, TemperatureConfig, AllConfigExportData, ...）；导入 1；首轮未确认死代码。
- 437/925 `frontend-web/src/api/themeConfigs.ts` | ts | 已读取 201 行；顶层符号 24（ThemeMode, ThemeConfigListItem, ThemeConfigUnifiedRead, ThemeConfigUpdateV1, ...）；导入 1；首轮未确认死代码。
- 438/925 `frontend-web/src/api/writer.ts` | ts | 已读取 505 行；顶层符号 46（WRITER_PREFIX, Chapter, ChapterVersion, RAGStatistics, ...）；导入 2；首轮未确认死代码。
- 439/925 `frontend-web/src/components/admin/AdminAccessDenied.tsx` | tsx | 已读取 28 行；顶层符号 2（AdminAccessDenied, navigate）；导入 5；首轮未确认死代码。
- 440/925 `frontend-web/src/components/admin/AdminCharts.tsx` | tsx | 已读取 460 行；顶层符号 69（AdminChartDatum, DEFAULT_COLORS, normalizeValue, getColor, ...）；导入 1；首轮未确认死代码。
- 441/925 `frontend-web/src/components/admin/AdminPanelHeader.tsx` | tsx | 已读取 81 行；顶层符号 5（AdminTabKey, AdminPanelHeaderProps, tabs, AdminPanelHeader, ...）；导入 4；首轮未确认死代码。
- 442/925 `frontend-web/src/components/admin/LazyRender.tsx` | tsx | 已读取 74 行；顶层符号 7（LazyRenderProps, LazyRender, containerRef, target, ...）；导入 1；首轮未确认死代码。
- 443/925 `frontend-web/src/components/auth/AuthGate.tsx` | tsx | 已读取 33 行；顶层符号 2（AuthGateProps, AuthGate）；导入 4；首轮未确认死代码。
- 444/925 `frontend-web/src/components/business/AssistantPanel.tsx` | tsx | 已读取 552 行；顶层符号 30（AssistantMode, RagPane, ASSISTANT_MODE_STORAGE_KEY, ASSISTANT_RAG_PANE_STORAGE_KEY, ...）；导入 9；首轮未确认死代码。
- 445/925 `frontend-web/src/components/business/BatchGenerateModal.tsx` | tsx | 已读取 237 行；顶层符号 19（BatchGenerateModalProps, BatchGenerateModal, prevOpenRef, nextCountRaw, ...）；导入 7；首轮未确认死代码。
- 446/925 `frontend-web/src/components/business/BlueprintCard.tsx` | tsx | 已读取 135 行；顶层符号 3（BlueprintCardProps, BlueprintCard, progressPercent）；导入 3；首轮未确认死代码。
- 447/925 `frontend-web/src/components/business/ChapterAnalysisView.tsx` | tsx | 已读取 387 行；顶层符号 20（AnyObj, asArray, Chip, ChapterAnalysisViewProps, ...）；导入 6；首轮未确认死代码。
- 448/925 `frontend-web/src/components/business/ChapterList.tsx` | tsx | 已读取 495 行；顶层符号 66（ChapterListProps, INITIAL_CHAPTER_RENDER_LIMIT, CHAPTER_RENDER_BATCH_SIZE, PORTRAIT_CACHE_TTL_MS, ...）；导入 11；首轮未确认死代码。
- 449/925 `frontend-web/src/components/business/ChapterPromptPreviewView.tsx` | tsx | 已读取 258 行；顶层符号 10（ChapterPromptPreviewViewProps, ChapterPromptPreviewView, notes, setNotes, ...）；导入 7；首轮未确认死代码。
- 450/925 `frontend-web/src/components/business/ChapterReviewView.tsx` | tsx | 已读取 231 行；顶层符号 16（EvaluationJson, Chip, ChapterReviewViewProps, ChapterReviewView, ...）；导入 7；首轮未确认死代码。
- 451/925 `frontend-web/src/components/business/ChapterSummaryView.tsx` | tsx | 已读取 166 行；顶层符号 9（countChars, ChapterSummaryViewProps, ChapterSummaryView, fetchData, ...）；导入 6；首轮未确认死代码。
- 452/925 `frontend-web/src/components/business/ChapterVersionsView.tsx` | tsx | 已读取 330 行；顶层符号 17（countChars, ChapterVersionsViewProps, ChapterVersionsView, fetchData, ...）；导入 9；首轮未确认死代码。
- 453/925 `frontend-web/src/components/business/CharacterPortraitGallery.tsx` | tsx | 已读取 664 行；顶层符号 62（CharacterPortraitGalleryProps, PortraitStyle, DEFAULT_STYLE_OPTIONS, normalizeName, ...）；导入 11；首轮未确认死代码。
- 454/925 `frontend-web/src/components/business/ContentOptimizationView.tsx` | tsx | 已读取 1219 行；顶层符号 118（OptimizationMode, AnalysisScope, ParagraphPreview, ParagraphPreviewResponse, ...）；导入 10；首轮未确认死代码。
- 455/925 `frontend-web/src/components/business/CreateProjectModal.tsx` | tsx | 已读取 262 行；顶层符号 10（CreateProjectModalProps, CreateProjectModal, navigate, isNovel, ...）；导入 9；首轮未确认死代码。
- 456/925 `frontend-web/src/components/business/Editor.tsx` | tsx | 已读取 239 行；顶层符号 14（EditorHandle, EditorProps, Editor, textareaRef, ...）；导入 4；首轮未确认死代码。
- 457/925 `frontend-web/src/components/business/ImportChapterModal.tsx` | tsx | 已读取 243 行；顶层符号 17（Encoding, ImportChapterModal, wasOpenRef, fileInputRef, ...）；导入 8；首轮未确认死代码。
- 458/925 `frontend-web/src/components/business/ImportModal.tsx` | tsx | 已读取 143 行；顶层符号 8（ImportModalProps, ImportModal, handleFileChange, handleImport, ...）；导入 7；首轮未确认死代码。
- 459/925 `frontend-web/src/components/business/MangaPromptViewer.tsx` | tsx | 已读取 1702 行；顶层符号 159（MangaPromptViewerProps, safeJson, widthRatioToSpan, v, ...）；导入 11；首轮未确认死代码。
- 460/925 `frontend-web/src/components/business/OutlineEditModal.tsx` | tsx | 已读取 95 行；顶层符号 3（OutlineEditModalProps, OutlineEditModal, handleSave）；导入 7；首轮未确认死代码。
- 461/925 `frontend-web/src/components/business/PartOutlineDetailModal.tsx` | tsx | 已读取 268 行；顶层符号 27（PartOutlineDetailModalProps, safeJson, PartOutlineDetailModal, partNumber, ...）；导入 5；首轮未确认死代码。
- 462/925 `frontend-web/src/components/business/PartOutlineGenerateModal.tsx` | tsx | 已读取 289 行；顶层符号 26（PartOutlineGenerateMode, PartOutlineGenerateModalProps, clampInt, n, ...）；导入 7；首轮未确认死代码。
- 463/925 `frontend-web/src/components/business/ProjectLauncherRow.tsx` | tsx | 已读取 137 行；顶层符号 11（ProjectLauncherRowProps, statusToneMap, formatUpdatedAt, parsed, ...）；导入 5；首轮未确认死代码。
- 464/925 `frontend-web/src/components/business/ProjectListItem.tsx` | tsx | 已读取 8 行；顶层符号 1（ProjectListItemModel）；导入 0；首轮未确认死代码。
- 465/925 `frontend-web/src/components/business/ProtagonistProfilesModal.tsx` | tsx | 已读取 1394 行；顶层符号 97（LucideIcon, ProtagonistProfilesModalProps, DetailTab, DETAIL_TABS, ...）；导入 10；首轮未确认死代码。
- 466/925 `frontend-web/src/components/business/SettingsModal.tsx` | tsx | 已读取 252 行；顶层符号 24（LLMConfigsTab, EmbeddingConfigsTab, ImageConfigsTab, ThemeTab, ...）；导入 16；首轮未确认死代码。
- 467/925 `frontend-web/src/components/business/WorkspaceTabs.tsx` | tsx | 已读取 426 行；顶层符号 38（WorkspaceTabId, GenProgress, WorkspaceHandle, WorkspaceTabsProps, ...）；导入 12；首轮未确认死代码。
- 468/925 `frontend-web/src/components/business/chapter/components/InsightCard.tsx` | tsx | 已读取 36 行；顶层符号 2（InsightCardProps, InsightCard）；导入 2；首轮未确认死代码。
- 469/925 `frontend-web/src/components/business/manga-prompt-viewer/MangaGenerationParams.tsx` | tsx | 已读取 230 行；顶层符号 5（MangaGenerationParamsProps, MangaGenerationParams, v, v, ...）；导入 2；首轮未确认死代码。
- 470/925 `frontend-web/src/components/business/novel/NovelDialogPrimitives.tsx` | tsx | 已读取 118 行；顶层符号 8（NovelDialogTone, toneClassMap, NovelDialogStack, NovelDialogIntro, ...）；导入 1；首轮未确认死代码。
- 471/925 `frontend-web/src/components/business/settings/AdvancedTab.tsx` | tsx | 已读取 437 行；顶层符号 21（DEFAULT_CONFIG, AdvancedTabProps, clampIntFromText, parsed, ...）；导入 10；首轮未确认死代码。
- 472/925 `frontend-web/src/components/business/settings/EmbeddingConfigsTab.tsx` | tsx | 已读取 378 行；顶层符号 47（EditorMode, EditorState, PROVIDER_LABELS, EmbeddingConfigsTab, ...）；导入 11；首轮未确认死代码。
- 473/925 `frontend-web/src/components/business/settings/ImageConfigsTab.tsx` | tsx | 已读取 343 行；顶层符号 30（EditorMode, EditorState, PROVIDER_LABELS, safeString, ...）；导入 10；首轮未确认死代码。
- 474/925 `frontend-web/src/components/business/settings/ImportExportTab.tsx` | tsx | 已读取 470 行；顶层符号 26（ImportPreview, safeDateStringForFilename, dt, sanitizeFilename, ...）；导入 9；首轮未确认死代码。
- 475/925 `frontend-web/src/components/business/settings/LLMConfigsTab.tsx` | tsx | 已读取 248 行；顶层符号 31（EditorMode, EditorState, LLMConfigsTab, sorted, ...）；导入 10；首轮未确认死代码。
- 476/925 `frontend-web/src/components/business/settings/MaxTokensTab.tsx` | tsx | 已读取 125 行；顶层符号 9（DEFAULTS, MaxTokensTab, configRef, fetchConfig, ...）；导入 10；首轮未确认死代码。
- 477/925 `frontend-web/src/components/business/settings/PromptsTab.tsx` | tsx | 已读取 587 行；顶层符号 60（normalizeKey, s, PROJECT_TYPE_LABELS, CATEGORY_LABELS, ...）；导入 10；首轮未确认死代码。
- 478/925 `frontend-web/src/components/business/settings/QueueTab.tsx` | tsx | 已读取 184 行；顶层符号 15（QueueTab, isAdmin, llmMaxRef, imageMaxRef, ...）；导入 11；首轮未确认死代码。
- 479/925 `frontend-web/src/components/business/settings/TemperatureTab.tsx` | tsx | 已读取 160 行；顶层符号 10（DEFAULTS, TemperatureTab, configRef, fetchConfig, ...）；导入 8；首轮未确认死代码。
- 480/925 `frontend-web/src/components/business/settings/ThemeTab.tsx` | tsx | 已读取 1181 行；顶层符号 82（formatTime, formatDate, ThemeTab, appearanceRef, ...）；导入 17；首轮未确认死代码。
- 481/925 `frontend-web/src/components/business/settings/components/ConfigCardActions.tsx` | tsx | 已读取 48 行；顶层符号 2（ConfigCardActionsProps, ConfigCardActions）；导入 3；首轮未确认死代码。
- 482/925 `frontend-web/src/components/business/settings/components/ConfigCardShell.tsx` | tsx | 已读取 55 行；顶层符号 2（ConfigCardShellProps, ConfigCardShell）；导入 3；首轮未确认死代码。
- 483/925 `frontend-web/src/components/business/settings/components/ConfigsCardsList.tsx` | tsx | 已读取 53 行；顶层符号 3（BaseConfigItem, ConfigsCardsListProps, ConfigsCardsList）；导入 3；首轮未确认死代码。
- 484/925 `frontend-web/src/components/business/settings/components/ConfigsList.tsx` | tsx | 已读取 32 行；顶层符号 2（ConfigsListProps, ConfigsList）；导入 1；首轮未确认死代码。
- 485/925 `frontend-web/src/components/business/settings/components/LocalEmbeddingModelDownloadModal.tsx` | tsx | 已读取 260 行；顶层符号 28（DownloadStatus, LocalEmbeddingModelDownloadModalProps, formatBytes, n, ...）；导入 6；首轮未确认死代码。
- 486/925 `frontend-web/src/components/business/settings/components/SettingsEditorModal.tsx` | tsx | 已读取 74 行；顶层符号 3（SettingsEditorModalProps, SettingsEditorModal, isCreate）；导入 4；首轮未确认死代码。
- 487/925 `frontend-web/src/components/business/settings/components/SettingsFixedCard.tsx` | tsx | 已读取 71 行；顶层符号 2（SettingsFixedCardProps, SettingsFixedCard）；导入 3；首轮未确认死代码。
- 488/925 `frontend-web/src/components/business/settings/components/SettingsModalFooterContext.tsx` | tsx | 已读取 25 行；顶层符号 5（SettingsModalFooterApi, noopSetFooter, SettingsModalFooterContext, SettingsModalFooterProvider, ...）；导入 1；首轮未确认死代码。
- 489/925 `frontend-web/src/components/business/settings/components/SettingsTabPanel.tsx` | tsx | 已读取 25 行；顶层符号 2（SettingsTabPanelProps, SettingsTabPanel）；导入 1；首轮未确认死代码。
- 490/925 `frontend-web/src/components/business/settings/components/settingsLayout.ts` | ts | 已读取 6 行；顶层符号 1（SETTINGS_CARD_HEIGHTS）；导入 0；首轮未确认死代码。
- 491/925 `frontend-web/src/components/coding/DirectoryTree.tsx` | tsx | 已读取 157 行；顶层符号 11（TreeNode, DirectoryTreeProps, TreeItem, isDir, ...）；导入 2；首轮未确认死代码。
- 492/925 `frontend-web/src/components/feedback/ConfirmDialog.tsx` | tsx | 已读取 121 行；顶层符号 19（ConfirmDialogType, ConfirmDialogOptions, InternalConfirmDialog, ConfirmDialogStore, ...）；导入 4；首轮未确认死代码。
- 493/925 `frontend-web/src/components/feedback/ErrorBoundary.tsx` | tsx | 已读取 71 行；顶层符号 3（ErrorBoundaryProps, ErrorBoundaryState, ErrorBoundary）；导入 4；首轮未确认死代码。
- 494/925 `frontend-web/src/components/feedback/Toast.tsx` | tsx | 已读取 144 行；顶层符号 16（ToastType, Toast, ToastStore, DEFAULT_TOAST_MESSAGE, ...）；导入 2；首轮未确认死代码。
- 495/925 `frontend-web/src/components/layout/AppViewport.tsx` | tsx | 已读取 84 行；顶层符号 9（ViewportFrameSize, SegmentItem, cx, frameSizeClassName, ...）；导入 1；首轮未确认死代码。
- 496/925 `frontend-web/src/components/ui/BookButton.tsx` | tsx | 已读取 90 行；顶层符号 10（BookButtonProps, BookButton, base, variants, ...）；导入 1；首轮未确认死代码。
- 497/925 `frontend-web/src/components/ui/BookCard.tsx` | tsx | 已读取 41 行；顶层符号 5（BookCardProps, BookCard, baseStyles, variants, ...）；导入 1；首轮未确认死代码。
- 498/925 `frontend-web/src/components/ui/BookInput.tsx` | tsx | 已读取 72 行；顶层符号 4（BookInputProps, BookInput, BookTextareaProps, BookTextarea）；导入 1；首轮未确认死代码。
- 499/925 `frontend-web/src/components/ui/BookSlider.tsx` | tsx | 已读取 133 行；顶层符号 23（BookSliderChangeHandler, clampNumber, countDecimals, raw, ...）；导入 1；首轮未确认死代码。
- 500/925 `frontend-web/src/components/ui/Dropdown.tsx` | tsx | 已读取 157 行；顶层符号 17（DropdownItem, DropdownProps, Dropdown, buttonRef, ...）；导入 3；首轮未确认死代码。
- 501/925 `frontend-web/src/components/ui/Modal.tsx` | tsx | 已读取 181 行；顶层符号 19（ModalProps, FOCUSABLE_SELECTOR, getFocusableElements, focusFirstElement, ...）；导入 3；首轮未确认死代码。
- 502/925 `frontend-web/src/components/ui/ParticleBackground.tsx` | tsx | 已读取 388 行；顶层符号 74（RGB, Palette, clamp255, clamp01, ...）；导入 1；首轮未确认死代码。
- 503/925 `frontend-web/src/hooks/useConfirmTextModal.tsx` | tsx | 已读取 129 行；顶层符号 11（AddToast, OpenConfirmTextModalOptions, UseConfirmTextModalOptions, useConfirmTextModal, ...）；导入 5；首轮未确认死代码。
- 504/925 `frontend-web/src/hooks/usePdfPreviewUrl.ts` | ts | 已读取 104 行；顶层符号 11（UsePdfPreviewUrlOptions, safeRevokeObjectUrl, usePdfPreviewUrl, pdfPreviewUrlRef, ...）；导入 1；首轮未确认死代码。
- 505/925 `frontend-web/src/hooks/usePersistedMangaGenOptions.ts` | ts | 已读取 183 行；顶层符号 41（MangaGenStyle, MangaGenLanguage, MangaStartFromStage, MangaGenOptions, ...）；导入 2；首轮未确认死代码。
- 506/925 `frontend-web/src/hooks/usePersistedState.ts` | ts | 已读取 58 行；顶层符号 10（UsePersistedStateOptions, defaultParse, defaultSerialize, readPersisted, ...）；导入 2；首轮未确认死代码。
- 507/925 `frontend-web/src/hooks/usePersistedTab.ts` | ts | 已读取 21 行；顶层符号 3（usePersistedTab, isAllowed, parseTab）；导入 2；首轮未确认死代码。
- 508/925 `frontend-web/src/hooks/useSSE.ts` | ts | 已读取 189 行；顶层符号 37（UseSSEReturn, joinUrl, ep, base, ...）；导入 2；首轮未确认死代码。
- 509/925 `frontend-web/src/hooks/useTokenBuffer.ts` | ts | 已读取 44 行；顶层符号 8（useTokenBuffer, tokensRef, timerRef, flush, ...）；导入 1；首轮未确认死代码。
- 510/925 `frontend-web/src/index.css` | text | 已读取 609 行，判定为非代码文件。
- 511/925 `frontend-web/src/main.tsx` | tsx | 已读取 89 行；顶层符号 14（ensureBackendPortBridge, raw, envPort, defaultPort, ...）；导入 4；首轮未确认死代码。
- 512/925 `frontend-web/src/pages/AdminConfigs.tsx` | tsx | 已读取 744 行；顶层符号 62（ConfigTypeFilter, TestStatusFilter, emptyData, AdminConfigsBootstrapSnapshot, ...）；导入 16；首轮未确认死代码。
- 513/925 `frontend-web/src/pages/AdminOverview.tsx` | tsx | 已读取 574 行；顶层符号 41（emptyData, AdminOverviewBootstrapSnapshot, ADMIN_OVERVIEW_BOOTSTRAP_KEY, ADMIN_OVERVIEW_BOOTSTRAP_TTL_MS, ...）；导入 13；首轮未确认死代码。
- 514/925 `frontend-web/src/pages/AdminProjects.tsx` | tsx | 已读取 758 行；顶层符号 70（KindFilter, SortMode, emptyData, AdminProjectsBootstrapSnapshot, ...）；导入 16；首轮未确认死代码。
- 515/925 `frontend-web/src/pages/AdminUsers.tsx` | tsx | 已读取 1012 行；顶层符号 77（StatusFilter, SortMode, FocusFilter, formatDate, ...）；导入 19；首轮未确认死代码。
- 516/925 `frontend-web/src/pages/AuthPage.tsx` | tsx | 已读取 133 行；顶层符号 6（AuthPage, canRegister, effectiveMode, handleSubmit, ...）；导入 8；首轮未确认死代码。
- 517/925 `frontend-web/src/pages/BlueprintPreview.tsx` | tsx | 已读取 286 行；顶层符号 22（BlueprintData, INITIAL_PREVIEW_CHARACTER_LIMIT, PREVIEW_CHARACTER_BATCH_SIZE, BLUEPRINT_PREVIEW_BOOTSTRAP_TTL_MS, ...）；导入 10；首轮未确认死代码。
- 518/925 `frontend-web/src/pages/CodingDesk.tsx` | tsx | 已读取 1402 行；顶层符号 125（AssistantTab, StreamLogType, StreamLog, CodingDeskBootstrapSnapshot, ...）；导入 14；首轮未确认死代码。
- 519/925 `frontend-web/src/pages/CodingDetail.tsx` | tsx | 已读取 1972 行；顶层符号 132（DirectoryTreeLazy, EditorLazy, CodingTab, CODING_DETAIL_TABS, ...）；导入 16；首轮未确认死代码。
- 520/925 `frontend-web/src/pages/InspirationChat.tsx` | tsx | 已读取 1369 行；顶层符号 155（Message, InspirationChatProps, InspirationChatBootstrapSnapshot, INSPIRATION_CHAT_BOOTSTRAP_TTL_MS, ...）；导入 15；首轮未确认死代码。
- 521/925 `frontend-web/src/pages/NovelDetail.tsx` | tsx | 已读取 466 行；顶层符号 27（NOVEL_DETAIL_TABS, NovelDetailPageProps, NovelDetailPage, navigate, ...）；导入 33；首轮未确认死代码。
- 522/925 `frontend-web/src/pages/NovelList.tsx` | tsx | 已读取 557 行；顶层符号 36（ParticleBackgroundLazy, CreateProjectModalLazy, ImportModalLazy, NOVEL_LIST_BOOTSTRAP_TTL_MS, ...）；导入 19；首轮未确认死代码。
- 523/925 `frontend-web/src/pages/WritingDesk.tsx` | tsx | 已读取 1447 行；顶层符号 171（OutlineEditModalLazy, BatchGenerateModalLazy, ProtagonistProfilesModalLazy, DEFAULT_VERSION_CREATED_AT, ...）；导入 28；首轮未确认死代码。
- 524/925 `frontend-web/src/pages/novel-detail/ChaptersTab.tsx` | tsx | 已读取 198 行；顶层符号 6（ChaptersTabProps, ChaptersTab, openImportChapterModal, no, ...）；导入 6；首轮未确认死代码。
- 525/925 `frontend-web/src/pages/novel-detail/CharacterAndRelationshipModals.tsx` | tsx | 已读取 25 行；顶层符号 4（CharacterModalProps, RelationshipModalProps, CharacterAndRelationshipModalsProps, CharacterAndRelationshipModals）；导入 4；首轮未确认死代码。
- 526/925 `frontend-web/src/pages/novel-detail/CharacterEditModal.tsx` | tsx | 已读取 140 行；顶层符号 4（CharacterEditModalProps, CharacterEditModal, isEditing, relationshipWithProtagonist）；导入 5；首轮未确认死代码。
- 527/925 `frontend-web/src/pages/novel-detail/CharactersTab.tsx` | tsx | 已读取 148 行；顶层符号 4（CharacterPortraitGalleryLazy, CharactersView, CharactersTabProps, CharactersTab）；导入 5；首轮未确认死代码。
- 528/925 `frontend-web/src/pages/novel-detail/LatestChapterOutlineModals.tsx` | tsx | 已读取 207 行；顶层符号 2（LatestChapterOutlineModalsProps, LatestChapterOutlineModals）；导入 5；首轮未确认死代码。
- 529/925 `frontend-web/src/pages/novel-detail/LatestPartOutlineModals.tsx` | tsx | 已读取 211 行；顶层符号 2（LatestPartOutlineModalsProps, LatestPartOutlineModals）；导入 5；首轮未确认死代码。
- 530/925 `frontend-web/src/pages/novel-detail/NovelDetailHeader.tsx` | tsx | 已读取 196 行；顶层符号 12（NovelDetailHeaderProps, NovelDetailHeader, projectTitle, genre, ...）；导入 5；首轮未确认死代码。
- 531/925 `frontend-web/src/pages/novel-detail/NovelDetailLazyBusinessModals.tsx` | tsx | 已读取 168 行；顶层符号 7（OutlineEditModalLazy, BatchGenerateModalLazy, ProtagonistProfilesModalLazy, PartOutlineGenerateModalLazy, ...）；导入 6；首轮未确认死代码。
- 532/925 `frontend-web/src/pages/novel-detail/NovelDetailPageLayout.tsx` | tsx | 已读取 114 行；顶层符号 4（NovelDetailPageLayoutProps, NovelDetailPageLayout, runtime, paneItems）；导入 10；首轮未确认死代码。
- 533/925 `frontend-web/src/pages/novel-detail/NovelDetailTabBar.tsx` | tsx | 已读取 63 行；顶层符号 6（NovelDetailTab, NovelDetailTabItem, NOVEL_DETAIL_TAB_ITEMS, NovelDetailTabBar, ...）；导入 2；首轮未确认死代码。
- 534/925 `frontend-web/src/pages/novel-detail/NovelDetailTabContent.tsx` | tsx | 已读取 101 行；顶层符号 3（NovelDetailTabContentProps, NovelDetailTabContent, activeTabMeta）；导入 11；首轮未确认死代码。
- 535/925 `frontend-web/src/pages/novel-detail/OutlinesChapterCard.tsx` | tsx | 已读取 90 行；顶层符号 5（OutlinesChapterCardProps, OutlinesChapterCard, chapterNumber, status, ...）；导入 2；首轮未确认死代码。
- 536/925 `frontend-web/src/pages/novel-detail/OutlinesChapterSection.tsx` | tsx | 已读取 143 行；顶层符号 4（OutlinesChapterSectionProps, OutlinesChapterSection, chapterNumber, chapter）；导入 4；首轮未确认死代码。
- 537/925 `frontend-web/src/pages/novel-detail/OutlinesPartCard.tsx` | tsx | 已读取 101 行；顶层符号 9（OutlinesPartCardProps, OutlinesPartCard, start, end, ...）；导入 4；首轮未确认死代码。
- 538/925 `frontend-web/src/pages/novel-detail/OutlinesPartSection.tsx` | tsx | 已读取 187 行；顶层符号 2（OutlinesPartSectionProps, OutlinesPartSection）；导入 4；首轮未确认死代码。
- 539/925 `frontend-web/src/pages/novel-detail/OutlinesTab.tsx` | tsx | 已读取 71 行；顶层符号 8（OutlinesChapterSectionProps, OutlinesPartSectionProps, OutlinesTabProps, OutlinesTab, ...）；导入 6；首轮未确认死代码。
- 540/925 `frontend-web/src/pages/novel-detail/OverviewTab.tsx` | tsx | 已读取 162 行；顶层符号 5（OverviewTabProps, OverviewTab, status, canStart, ...）；导入 3；首轮未确认死代码。
- 541/925 `frontend-web/src/pages/novel-detail/RelationshipEditModal.tsx` | tsx | 已读取 135 行；顶层符号 5（RelationshipEditModalProps, CHARACTER_NAMES_DATA_LIST_ID, RelationshipEditModal, isEditing, ...）；导入 5；首轮未确认死代码。
- 542/925 `frontend-web/src/pages/novel-detail/RelationshipsTab.tsx` | tsx | 已读取 84 行；顶层符号 2（RelationshipsTabProps, RelationshipsTab）；导入 4；首轮未确认死代码。
- 543/925 `frontend-web/src/pages/novel-detail/TitleAndBlueprintModals.tsx` | tsx | 已读取 190 行；顶层符号 2（TitleAndBlueprintModalsProps, TitleAndBlueprintModals）；导入 5；首轮未确认死代码。
- 544/925 `frontend-web/src/pages/novel-detail/WorldTab.tsx` | tsx | 已读取 133 行；顶层符号 3（WorldEditMode, WorldTabProps, WorldTab）；导入 4；首轮未确认死代码。
- 545/925 `frontend-web/src/pages/novel-detail/bootstrapCache.ts` | ts | 已读取 91 行；顶层符号 23（NovelDetailBootstrapSnapshot, NovelDetailImportStatusSnapshot, NovelDetailPartProgressSnapshot, NovelDetailChapterDetailSnapshot, ...）；导入 1；首轮未确认死代码。
- 546/925 `frontend-web/src/pages/novel-detail/buildNovelDetailModalInput.ts` | ts | 已读取 37 行；顶层符号 4（DerivedDataState, ModalStates, BuildNovelDetailModalInputArgs, buildNovelDetailModalInput）；导入 3；首轮未确认死代码。
- 547/925 `frontend-web/src/pages/novel-detail/buildNovelDetailModalInputParams.ts` | ts | 已读取 63 行；顶层符号 4（LatestPartOutlineInputForModal, LatestChapterOutlineInputForModal, BuildNovelDetailModalInputParamsArgs, buildNovelDetailModalInputParams）；导入 1；首轮未确认死代码。
- 548/925 `frontend-web/src/pages/novel-detail/buildNovelDetailPageLayoutProps.ts` | ts | 已读取 132 行；顶层符号 8（HeaderProps, TitleAndBlueprintModalProps, CharacterAndRelationshipModalProps, CharacterRelationshipEditorState, ...）；导入 5；首轮未确认死代码。
- 549/925 `frontend-web/src/pages/novel-detail/buildNovelDetailTabInput.ts` | ts | 已读取 62 行；顶层符号 6（BlueprintDraftState, CharacterRelationshipEditorState, DerivedDataState, ModalStates, ...）；导入 5；首轮未确认死代码。
- 550/925 `frontend-web/src/pages/novel-detail/buildNovelDetailTabSources.ts` | ts | 已读取 50 行；顶层符号 4（LatestPartOutlineInputForTab, LatestChapterOutlineInputForTab, BuildNovelDetailTabSourcesArgs, buildNovelDetailTabSources）；导入 2；首轮未确认死代码。
- 551/925 `frontend-web/src/pages/novel-detail/derived-data/useNovelDetailCharacterDerived.ts` | ts | 已读取 99 行；顶层符号 18（CHARACTER_PROFILE_KEYS, UseNovelDetailCharacterDerivedParams, useNovelDetailCharacterDerived, charactersList, ...）；导入 1；首轮未确认死代码。
- 552/925 `frontend-web/src/pages/novel-detail/derived-data/useNovelDetailCompletedChapterDerived.ts` | ts | 已读取 66 行；顶层符号 19（UseNovelDetailCompletedChapterDerivedParams, useNovelDetailCompletedChapterDerived, chaptersByNumber, map, ...）；导入 1；首轮未确认死代码。
- 553/925 `frontend-web/src/pages/novel-detail/derived-data/useNovelDetailOutlineDerived.ts` | ts | 已读取 106 行；顶层符号 28（lowerBound, left, right, mid, ...）；导入 1；首轮未确认死代码。
- 554/925 `frontend-web/src/pages/novel-detail/modal-props/types.ts` | ts | 已读取 82 行；顶层符号 8（LazyBusinessModalProps, LatestPartOutlineModalProps, LatestChapterOutlineModalProps, BusinessModalInput, ...）；导入 4；首轮未确认死代码。
- 555/925 `frontend-web/src/pages/novel-detail/modal-props/useLatestChapterOutlineModalProps.ts` | ts | 已读取 61 行；顶层符号 2（useLatestChapterOutlineModalProps, chapterOutlineCount）；导入 2；首轮未确认死代码。
- 556/925 `frontend-web/src/pages/novel-detail/modal-props/useLatestPartOutlineModalProps.ts` | ts | 已读取 63 行；顶层符号 2（useLatestPartOutlineModalProps, partOutlineCount）；导入 2；首轮未确认死代码。
- 557/925 `frontend-web/src/pages/novel-detail/modal-props/useLazyBusinessModalProps.ts` | ts | 已读取 95 行；顶层符号 9（useLazyBusinessModalProps, chaptersPerPart, partOutlineCount, partGenerateTotalChapters, ...）；导入 2；首轮未确认死代码。
- 558/925 `frontend-web/src/pages/novel-detail/tab-props/types.ts` | ts | 已读取 42 行；顶层符号 11（CharactersTabInputProps, RelationshipsTabInputProps, OverviewWorldTabSource, CharacterRelationshipTabSource, ...）；导入 6；首轮未确认死代码。
- 559/925 `frontend-web/src/pages/novel-detail/tab-props/useChaptersTabProps.ts` | ts | 已读取 70 行；顶层符号 4（UseChaptersTabPropsParams, useChaptersTabProps, onChapterImported, chaptersTabProps）；导入 2；首轮未确认死代码。
- 560/925 `frontend-web/src/pages/novel-detail/tab-props/useCharacterRelationshipTabProps.ts` | ts | 已读取 89 行；顶层符号 5（UseCharacterRelationshipTabPropsResult, UseCharacterRelationshipTabPropsParams, useCharacterRelationshipTabProps, charactersTabProps, ...）；导入 2；首轮未确认死代码。
- 561/925 `frontend-web/src/pages/novel-detail/tab-props/useOutlinesTabProps.ts` | ts | 已读取 19 行；顶层符号 3（UseOutlinesTabPropsParams, useOutlinesTabProps, outlinesTabProps）；导入 2；首轮未确认死代码。
- 562/925 `frontend-web/src/pages/novel-detail/tab-props/useOverviewWorldTabProps.ts` | ts | 已读取 78 行；顶层符号 4（UseOverviewWorldTabPropsResult, useOverviewWorldTabProps, overviewTabProps, worldTabProps）；导入 2；首轮未确认死代码。
- 563/925 `frontend-web/src/pages/novel-detail/useNovelDetailAvatarManager.ts` | ts | 已读取 91 行；顶层符号 8（UseNovelDetailAvatarManagerParams, useNovelDetailAvatarManager, handleGenerateAvatar, result, ...）；导入 4；首轮未确认死代码。
- 564/925 `frontend-web/src/pages/novel-detail/useNovelDetailBlueprintDraft.ts` | ts | 已读取 212 行；顶层符号 41（UseNovelDetailBlueprintDraftParams, stableStringify, seen, normalize, ...）；导入 2；首轮未确认死代码。
- 565/925 `frontend-web/src/pages/novel-detail/useNovelDetailBlueprintRefine.ts` | ts | 已读取 97 行；顶层符号 11（UseNovelDetailBlueprintRefineParams, useNovelDetailBlueprintRefine, closeRefineModal, openRefineModal, ...）；导入 4；首轮未确认死代码。
- 566/925 `frontend-web/src/pages/novel-detail/useNovelDetailBlueprintSave.ts` | ts | 已读取 76 行；顶层符号 9（UseNovelDetailBlueprintSaveParams, parseWorldSettingDraft, txt, parsed, ...）；导入 4；首轮未确认死代码。
- 567/925 `frontend-web/src/pages/novel-detail/useNovelDetailBootstrap.ts` | ts | 已读取 150 行；顶层符号 10（UseNovelDetailBootstrapParams, useNovelDetailBootstrap, cached, importCached, ...）；导入 5；首轮未确认死代码。
- 568/925 `frontend-web/src/pages/novel-detail/useNovelDetailChapterExport.ts` | ts | 已读取 50 行；顶层符号 12（UseNovelDetailChapterExportParams, useNovelDetailChapterExport, exportSelectedChapter, chapterNo, ...）；导入 3；首轮未确认死代码。
- 569/925 `frontend-web/src/pages/novel-detail/useNovelDetailChapterOutlineRegenerate.ts` | ts | 已读取 73 行；顶层符号 9（OptionalPromptOptions, UseNovelDetailChapterOutlineRegenerateParams, useNovelDetailChapterOutlineRegenerate, handleRegenerateOutline, ...）；导入 3；首轮未确认死代码。
- 570/925 `frontend-web/src/pages/novel-detail/useNovelDetailChapterSelection.ts` | ts | 已读取 109 行；顶层符号 10（UseNovelDetailChapterSelectionParams, useNovelDetailChapterSelection, chapterNo, detailChapterNo, ...）；导入 4；首轮未确认死代码。
- 571/925 `frontend-web/src/pages/novel-detail/useNovelDetailCharacterEditor.ts` | ts | 已读取 88 行；顶层符号 12（EMPTY_CHAR_FORM, UseNovelDetailCharacterEditorParams, useNovelDetailCharacterEditor, handleEditChar, ...）；导入 3；首轮未确认死代码。
- 572/925 `frontend-web/src/pages/novel-detail/useNovelDetailCharacterRelationshipEditor.ts` | ts | 已读取 36 行；顶层符号 4（UseNovelDetailCharacterRelationshipEditorParams, useNovelDetailCharacterRelationshipEditor, characterEditor, relationshipEditor）；导入 4；首轮未确认死代码。
- 573/925 `frontend-web/src/pages/novel-detail/useNovelDetailDerivedData.ts` | ts | 已读取 53 行；顶层符号 5（UseNovelDetailDerivedDataParams, useNovelDetailDerivedData, outlineDerived, characterDerived, ...）；导入 3；首轮未确认死代码。
- 574/925 `frontend-web/src/pages/novel-detail/useNovelDetailExport.ts` | ts | 已读取 34 行；顶层符号 6（UseNovelDetailExportParams, useNovelDetailExport, handleExport, response, ...）；导入 4；首轮未确认死代码。
- 575/925 `frontend-web/src/pages/novel-detail/useNovelDetailImportStatus.ts` | ts | 已读取 123 行；顶层符号 12（UseNovelDetailImportStatusParams, useNovelDetailImportStatus, refreshImportStatus, hadImportSnapshot, ...）；导入 5；首轮未确认死代码。
- 576/925 `frontend-web/src/pages/novel-detail/useNovelDetailLatestChapterOutlineActions.ts` | ts | 已读取 134 行；顶层符号 16（UseNovelDetailLatestChapterOutlineActionsParams, useNovelDetailLatestChapterOutlineActions, handleDeleteLatestOutlines, count, ...）；导入 4；首轮未确认死代码。
- 577/925 `frontend-web/src/pages/novel-detail/useNovelDetailLatestPartOutlineActions.ts` | ts | 已读取 215 行；顶层符号 25（UseNovelDetailLatestPartOutlineActionsParams, useNovelDetailLatestPartOutlineActions, getRollbackPreviewIfNeeded, statusRaw, ...）；导入 5；首轮未确认死代码。
- 578/925 `frontend-web/src/pages/novel-detail/useNovelDetailLeaveGuard.ts` | ts | 已读取 106 行；顶层符号 15（UseNovelDetailLeaveGuardParams, useNovelDetailLeaveGuard, isBlueprintDirtyRef, dirtySummaryRef, ...）；导入 3；首轮未确认死代码。
- 579/925 `frontend-web/src/pages/novel-detail/useNovelDetailModalProps.ts` | ts | 已读取 34 行；顶层符号 4（useNovelDetailModalProps, lazyBusinessModalProps, latestPartOutlineModalProps, latestChapterOutlineModalProps）；导入 5；首轮未确认死代码。
- 580/925 `frontend-web/src/pages/novel-detail/useNovelDetailModalStates.ts` | ts | 已读取 33 行；顶层符号 2（PartGenerateMode, useNovelDetailModalStates）；导入 1；首轮未确认死代码。
- 581/925 `frontend-web/src/pages/novel-detail/useNovelDetailOutlineActions.ts` | ts | 已读取 203 行；顶层符号 13（OptionalPromptOptions, UseNovelDetailOutlineActionsParams, useNovelDetailOutlineActions, latestChapterOutlineActions, ...）；导入 10；首轮未确认死代码。
- 582/925 `frontend-web/src/pages/novel-detail/useNovelDetailOutlineEditor.ts` | ts | 已读取 36 行；顶层符号 5（EditingOutlineChapter, UseNovelDetailOutlineEditorParams, useNovelDetailOutlineEditor, openOutlineEditor, ...）；导入 1；首轮未确认死代码。
- 583/925 `frontend-web/src/pages/novel-detail/useNovelDetailPartOutlineChapterGenerate.ts` | ts | 已读取 74 行；顶层符号 10（UseNovelDetailPartOutlineChapterGenerateParams, useNovelDetailPartOutlineChapterGenerate, handleGeneratePartChapters, partNumber, ...）；导入 3；首轮未确认死代码。
- 584/925 `frontend-web/src/pages/novel-detail/useNovelDetailPartOutlineRegenerate.ts` | ts | 已读取 272 行；顶层符号 29（OptionalPromptOptions, UseNovelDetailPartOutlineRegenerateParams, useNovelDetailPartOutlineRegenerate, getRollbackPreviewIfNeeded, ...）；导入 4；首轮未确认死代码。
- 585/925 `frontend-web/src/pages/novel-detail/useNovelDetailPartProgressSync.ts` | ts | 已读取 64 行；顶层符号 6（UseNovelDetailPartProgressSyncParams, useNovelDetailPartProgressSync, fetchPartProgress, hadPartSnapshot, ...）；导入 4；首轮未确认死代码。
- 586/925 `frontend-web/src/pages/novel-detail/useNovelDetailProjectSync.ts` | ts | 已读取 105 行；顶层符号 5（UseNovelDetailProjectSyncParams, useNovelDetailProjectSync, applyProjectPayload, fetchProjectButton, ...）；导入 5；首轮未确认死代码。
- 587/925 `frontend-web/src/pages/novel-detail/useNovelDetailRagSync.ts` | ts | 已读取 60 行；顶层符号 6（UseNovelDetailRagSyncParams, useNovelDetailRagSync, handleRagSync, ok, ...）；导入 3；首轮未确认死代码。
- 588/925 `frontend-web/src/pages/novel-detail/useNovelDetailRelationshipEditor.ts` | ts | 已读取 106 行；顶层符号 21（RelForm, EMPTY_REL_FORM, UseNovelDetailRelationshipEditorParams, useNovelDetailRelationshipEditor, ...）；导入 3；首轮未确认死代码。
- 589/925 `frontend-web/src/pages/novel-detail/useNovelDetailRenderLimits.ts` | ts | 已读取 76 行；顶层符号 12（CHARACTERS_RENDER_BATCH_SIZE, RELATIONSHIPS_RENDER_BATCH_SIZE, CHAPTER_OUTLINES_RENDER_BATCH_SIZE, PART_OUTLINES_RENDER_BATCH_SIZE, ...）；导入 1；首轮未确认死代码。
- 590/925 `frontend-web/src/pages/novel-detail/useNovelDetailTabProps.ts` | ts | 已读取 44 行；顶层符号 3（useNovelDetailTabProps, outlinesTabProps, chaptersTabProps）；导入 5；首轮未确认死代码。
- 591/925 `frontend-web/src/pages/novel-detail/useNovelDetailTitleEditor.ts` | ts | 已读取 62 行；顶层符号 6（UseNovelDetailTitleEditorParams, useNovelDetailTitleEditor, openEditTitleModal, closeEditTitleModal, ...）；导入 2；首轮未确认死代码。
- 592/925 `frontend-web/src/pages/writing-desk/PromptPreviewModal.tsx` | tsx | 已读取 60 行；顶层符号 2（ChapterPromptPreviewViewLazy, PromptPreviewModal）；导入 5；首轮未确认死代码。
- 593/925 `frontend-web/src/pages/writing-desk/WritingDeskAssistant.tsx` | tsx | 已读取 143 行；顶层符号 2（AssistantPanelLazy, WritingDeskAssistant）；导入 3；首轮未确认死代码。
- 594/925 `frontend-web/src/pages/writing-desk/WritingDeskHeader.tsx` | tsx | 已读取 114 行；顶层符号 1（WritingDeskHeader）；导入 4；首轮未确认死代码。
- 595/925 `frontend-web/src/pages/writing-desk/WritingDeskSidebar.tsx` | tsx | 已读取 168 行；顶层符号 1（WritingDeskSidebar）；导入 4；首轮未确认死代码。
- 596/925 `frontend-web/src/pages/writing-desk/WritingNotesModal.tsx` | tsx | 已读取 93 行；顶层符号 5（WritingNotesModal, handleClear, ok, handleSave, ...）；导入 7；首轮未确认死代码。
- 597/925 `frontend-web/src/pages/writing-desk/useWritingDeskPanels.ts` | ts | 已读取 222 行；顶层符号 49（clamp, getSidebarWidthKey, getSidebarOpenKey, getAssistantWidthKey, ...）；导入 4；首轮未确认死代码。
- 598/925 `frontend-web/src/store/auth.ts` | ts | 已读取 241 行；顶层符号 21（AuthStore, AuthBootstrapSnapshot, AUTH_BOOTSTRAP_CACHE_KEY, AUTH_BOOTSTRAP_CACHE_TTL_MS, ...）；导入 4；首轮未确认死代码。
- 599/925 `frontend-web/src/store/ui.ts` | ts | 已读取 14 行；顶层符号 2（UIStore, useUIStore）；导入 1；首轮未确认死代码。
- 600/925 `frontend-web/src/theme/applyTheme.ts` | ts | 已读取 209 行；顶层符号 65（CssVarMap, THEME_APPLIED_EVENT, clampByte, hexToRgbTriplet, ...）；导入 1；首轮未确认死代码。
- 601/925 `frontend-web/src/theme/webAppearance.ts` | ts | 已读取 66 行；顶层符号 17（WebAppearanceConfig, WEB_APPEARANCE_STORAGE_KEY, WEB_APPEARANCE_CHANGED_EVENT, defaultWebAppearanceConfig, ...）；导入 0；首轮未确认死代码。
- 602/925 `frontend-web/src/utils/blueprintPending.ts` | ts | 已读取 63 行；顶层符号 17（BlueprintPendingKind, PendingEnvelope, KEY_PREFIX, DEFAULT_TTL_MS, ...）；导入 0；首轮未确认死代码。
- 603/925 `frontend-web/src/utils/bootstrapCache.ts` | ts | 已读取 99 行；顶层符号 17（CacheEnvelope, canUseStorage, BOOTSTRAP_WRITE_DEBOUNCE_MS, PendingBootstrapWrite, ...）；导入 1；首轮未确认死代码。
- 604/925 `frontend-web/src/utils/constants.ts` | ts | 已读取 38 行；顶层符号 5（CREATIVE_QUOTES, PROJECT_STATUS_MAP, getStatusText, normalized, ...）；导入 0；首轮未确认死代码。
- 605/925 `frontend-web/src/utils/csv.ts` | ts | 已读取 20 行；顶层符号 8（CsvCell, CsvRow, csvEscape, text, ...）；导入 1；首轮未确认死代码。
- 606/925 `frontend-web/src/utils/downloadFile.ts` | ts | 已读取 32 行；顶层符号 7（downloadBlob, safeName, url, link, ...）；导入 0；首轮未确认死代码。
- 607/925 `frontend-web/src/utils/projectRoutePrefetch.ts` | ts | 已读取 102 行；顶层符号 16（RoutePrefetchProjectInfo, prefetchedKeys, inflightKeys, HOVER_PREFETCH_DELAY_MS, ...）；导入 2；首轮未确认死代码。
- 608/925 `frontend-web/src/utils/projectRouting.ts` | ts | 已读取 113 行；顶层符号 19（RoutedProject, normalizeProjectStatus, isCodingProject, isDraftLikeProject, ...）；导入 2；首轮未确认死代码。
- 609/925 `frontend-web/src/utils/projectWorkflow.ts` | ts | 已读取 84 行；顶层符号 14（WorkflowStage, WorkflowCapabilities, normalizeProjectStatus, text, ...）；导入 1；首轮未确认死代码。
- 610/925 `frontend-web/src/utils/sanitizeFilename.ts` | ts | 已读取 8 行；顶层符号 1（sanitizeFilenamePart）；导入 0；首轮未确认死代码。
- 611/925 `frontend-web/src/utils/scheduleIdleTask.ts` | ts | 已读取 61 行；顶层符号 7（ScheduleIdleTaskOptions, WindowWithIdleCallback, scheduleIdleTask, win, ...）；导入 0；首轮未确认死代码。
- 612/925 `frontend-web/src/utils/workflowRollback.ts` | ts | 已读取 121 行；顶层符号 31（WorkflowRollbackImpact, WorkflowRollbackStep, WorkflowRollbackPreview, formatRange, ...）；导入 0；首轮未确认死代码。
- 613/925 `frontend-web/src/utils/writingDraft.ts` | ts | 已读取 98 行；顶层符号 25（LocalDraft, WRITING_DRAFT_PREFIX, projectDraftIndex, getWritingDraftKey, ...）；导入 0；首轮未确认死代码。
- 614/925 `frontend-web/src/vite-env.d.ts` | ts | 已读取 23 行；顶层符号 3（AxiosRequestConfig, ImportMetaEnv, ImportMeta）；导入 1；首轮未确认死代码。
- 615/925 `frontend-web/tailwind.config.js` | js | 已读取 92 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 616/925 `frontend-web/tsconfig.json` | text | 已读取 30 行，判定为非代码文件。
- 617/925 `frontend-web/tsconfig.node.json` | text | 已读取 10 行，判定为非代码文件。
- 618/925 `frontend-web/vite.config.ts` | ts | 已读取 44 行；顶层符号 6（parsePort, parsed, env, frontendPort, ...）；导入 3；首轮未确认死代码。
- 619/925 `frontend/README.md` | text | 已读取 243 行，判定为非代码文件。
- 620/925 `frontend/all_configs.json` | text | 已读取 408 行，判定为非代码文件。
- 621/925 `frontend/api/__init__.py` | py | 已读取 89 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 622/925 `frontend/api/client/__init__.py` | py | 已读取 23 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 623/925 `frontend/api/client/blueprint_mixin.py` | py | 已读取 168 行；顶层符号 1（BlueprintMixin）；导入 2；首轮未确认死代码。
- 624/925 `frontend/api/client/chapter_mixin.py` | py | 已读取 291 行；顶层符号 1（ChapterMixin）；导入 1；首轮未确认死代码。
- 625/925 `frontend/api/client/coding_mixin.py` | py | 已读取 1401 行；顶层符号 1（CodingMixin）；导入 1；首轮未确认死代码。
- 626/925 `frontend/api/client/config_mixin.py` | py | 已读取 472 行；顶层符号 1（ConfigMixin）；导入 1；首轮未确认死代码。
- 627/925 `frontend/api/client/constants.py` | py | 已读取 17 行；顶层符号 1（TimeoutConfig）；导入 0；首轮未确认死代码。
- 628/925 `frontend/api/client/core.py` | py | 已读取 482 行；顶层符号 1（AFNAPIClient）；导入 22；首轮未确认死代码。
- 629/925 `frontend/api/client/image_mixin.py` | py | 已读取 591 行；顶层符号 1（ImageMixin）；导入 2；首轮未确认死代码。
- 630/925 `frontend/api/client/import_mixin.py` | py | 已读取 125 行；顶层符号 1（ImportMixin）；导入 4；首轮未确认死代码。
- 631/925 `frontend/api/client/inspiration_mixin.py` | py | 已读取 51 行；顶层符号 1（InspirationMixin）；导入 1；首轮未确认死代码。
- 632/925 `frontend/api/client/manga_mixin.py` | py | 已读取 323 行；顶层符号 1（MangaMixin）；导入 3；首轮未确认死代码。
- 633/925 `frontend/api/client/novel_mixin.py` | py | 已读取 271 行；顶层符号 1（NovelMixin）；导入 1；首轮未确认死代码。
- 634/925 `frontend/api/client/optimization_mixin.py` | py | 已读取 184 行；顶层符号 1（OptimizationMixin）；导入 2；首轮未确认死代码。
- 635/925 `frontend/api/client/outline_mixin.py` | py | 已读取 309 行；顶层符号 1（OutlineMixin）；导入 2；首轮未确认死代码。
- 636/925 `frontend/api/client/portrait_mixin.py` | py | 已读取 247 行；顶层符号 1（PortraitMixin）；导入 2；首轮未确认死代码。
- 637/925 `frontend/api/client/protagonist_mixin.py` | py | 已读取 534 行；顶层符号 1（ProtagonistMixin）；导入 2；首轮未确认死代码。
- 638/925 `frontend/api/client/queue_mixin.py` | py | 已读取 55 行；顶层符号 1（QueueMixin）；导入 1；首轮未确认死代码。
- 639/925 `frontend/api/client/theme_config_mixin.py` | py | 已读取 282 行；顶层符号 1（ThemeConfigMixin）；导入 1；首轮未确认死代码。
- 640/925 `frontend/api/exceptions.py` | py | 已读取 349 行；顶层符号 21（APIError, ClientError, BadRequestError, NotFoundError, ...）；导入 0；首轮未确认死代码。
- 641/925 `frontend/api/manager.py` | py | 已读取 106 行；顶层符号 1（APIClientManager）；导入 5；首轮未确认死代码。
- 642/925 `frontend/components/__init__.py` | py | 已读取 66 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 643/925 `frontend/components/base/__init__.py` | py | 已读取 8 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 644/925 `frontend/components/base/animated_stacked_widget.py` | py | 已读取 87 行；顶层符号 1（AnimatedStackedWidget）；导入 2；首轮未确认死代码。
- 645/925 `frontend/components/base/theme_aware_widget.py` | py | 已读取 498 行；顶层符号 5（_ThemeRefreshManager, ThemeAwareMixin, ThemeAwareWidget, ThemeAwareFrame, ...）；导入 6；首轮未确认死代码。
- 646/925 `frontend/components/dialogs/__init__.py` | py | 已读取 77 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 647/925 `frontend/components/dialogs/base.py` | py | 已读取 51 行；顶层符号 1（BaseDialog）；导入 3；首轮未确认死代码。
- 648/925 `frontend/components/dialogs/common/__init__.py` | py | 已读取 35 行；顶层符号 0（无）；导入 8；首轮未确认死代码。
- 649/925 `frontend/components/dialogs/common/alert_dialog.py` | py | 已读取 172 行；顶层符号 1（AlertDialog）；导入 6；首轮未确认死代码。
- 650/925 `frontend/components/dialogs/common/confirm_dialog.py` | py | 已读取 165 行；顶层符号 1（ConfirmDialog）；导入 6；首轮未确认死代码。
- 651/925 `frontend/components/dialogs/common/input_dialog.py` | py | 已读取 154 行；顶层符号 1（InputDialog）；导入 6；首轮未确认死代码。
- 652/925 `frontend/components/dialogs/common/int_input_dialog.py` | py | 已读取 162 行；顶层符号 1（IntInputDialog）；导入 6；首轮未确认死代码。
- 653/925 `frontend/components/dialogs/common/loading_dialog.py` | py | 已读取 171 行；顶层符号 1（LoadingDialog）；导入 5；首轮未确认死代码。
- 654/925 `frontend/components/dialogs/common/regenerate_dialog.py` | py | 已读取 210 行；顶层符号 2（RegenerateDialog, get_regenerate_preference）；导入 6；首轮未确认死代码。
- 655/925 `frontend/components/dialogs/common/save_discard_dialog.py` | py | 已读取 215 行；顶层符号 2（SaveDiscardResult, SaveDiscardDialog）；导入 7；首轮未确认死代码。
- 656/925 `frontend/components/dialogs/common/text_input_dialog.py` | py | 已读取 155 行；顶层符号 1（TextInputDialog）；导入 6；首轮未确认死代码。
- 657/925 `frontend/components/dialogs/config/__init__.py` | py | 已读取 12 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 658/925 `frontend/components/dialogs/config/config_dialogs.py` | py | 已读取 570 行；顶层符号 1（PartOutlineConfigDialog）；导入 7；首轮未确认死代码。
- 659/925 `frontend/components/dialogs/special/__init__.py` | py | 已读取 21 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 660/925 `frontend/components/dialogs/special/book_style_dialog.py` | py | 已读取 76 行；顶层符号 1（BookStyleDialog）；导入 2；首轮未确认死代码。
- 661/925 `frontend/components/dialogs/special/coding_mode_dialog.py` | py | 已读取 255 行；顶层符号 1（CodingModeDialog）；导入 6；首轮未确认死代码。
- 662/925 `frontend/components/dialogs/special/create_mode_dialog.py` | py | 已读取 272 行；顶层符号 1（CreateModeDialog）；导入 6；首轮未确认死代码。
- 663/925 `frontend/components/dialogs/special/import_progress_dialog.py` | py | 已读取 455 行；顶层符号 1（ImportProgressDialog）；导入 7；首轮未确认死代码。
- 664/925 `frontend/components/dialogs/styles.py` | py | 已读取 710 行；顶层符号 1（DialogStyles）；导入 3；首轮未确认死代码。
- 665/925 `frontend/components/empty_state.py` | py | 已读取 267 行；顶层符号 2（EmptyState, EmptyStateWithIllustration）；导入 4；首轮未确认死代码。
- 666/925 `frontend/components/flow_layout.py` | py | 已读取 144 行；顶层符号 1（FlowLayout）；导入 2；首轮未确认死代码。
- 667/925 `frontend/components/inputs/__init__.py` | py | 已读取 22 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 668/925 `frontend/components/inputs/color_picker.py` | py | 已读取 191 行；顶层符号 1（ColorPickerWidget）；导入 7；首轮未确认死代码。
- 669/925 `frontend/components/inputs/font_selector.py` | py | 已读取 184 行；顶层符号 1（FontFamilySelector）；导入 5；首轮未确认死代码。
- 670/925 `frontend/components/inputs/image_picker.py` | py | 已读取 216 行；顶层符号 1（ImagePickerWidget）；导入 7；首轮未确认死代码。
- 671/925 `frontend/components/inputs/size_input.py` | py | 已读取 212 行；顶层符号 1（SizeInputWidget）；导入 7；首轮未确认死代码。
- 672/925 `frontend/components/inputs/slider_input.py` | py | 已读取 252 行；顶层符号 1（SliderInputWidget）；导入 5；首轮未确认死代码。
- 673/925 `frontend/components/inputs/switch_input.py` | py | 已读取 284 行；顶层符号 2（SwitchControl, SwitchWidget）；导入 6；首轮未确认死代码。
- 674/925 `frontend/components/lazy_tab_widget.py` | py | 已读取 279 行；顶层符号 1（LazyTabWidget）；导入 6；首轮未确认死代码。
- 675/925 `frontend/components/loading_spinner.py` | py | 已读取 827 行；顶层符号 8（CircularSpinner, DotsSpinner, LoadingOverlay, InlineLoadingState, ...）；导入 9；首轮未确认死代码。
- 676/925 `frontend/components/theme_transition.py` | py | 已读取 239 行；顶层符号 2（ThemeTransitionOverlay, ThemeSwitchHelper）；导入 4；首轮未确认死代码。
- 677/925 `frontend/components/virtual_list.py` | py | 已读取 337 行；顶层符号 1（VirtualListWidget）；导入 4；首轮未确认死代码。
- 678/925 `frontend/main.py` | py | 已读取 352 行；顶层符号 7（_get_storage_dir, _load_logging_config, _get_log_level, global_exception_handler, ...）；导入 13；首轮未确认死代码。
- 679/925 `frontend/models/__init__.py` | py | 已读取 75 行；顶层符号 5（NovelProject, Blueprint, Chapter, ChapterVersion, ...）；导入 4；首轮未确认死代码。
- 680/925 `frontend/models/project_status.py` | py | 已读取 30 行；顶层符号 1（ProjectStatus）；导入 1；首轮未确认死代码。
- 681/925 `frontend/pages/__init__.py` | py | 已读取 8 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 682/925 `frontend/pages/base_page.py` | py | 已读取 245 行；顶层符号 1（BasePage）；导入 5；首轮未确认死代码。
- 683/925 `frontend/pages/home_page/__init__.py` | py | 已读取 24 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 684/925 `frontend/pages/home_page/cards.py` | py | 已读取 358 行；顶层符号 3（RecentProjectCard, TabButton, TabBar）；导入 9；首轮未确认死代码。
- 685/925 `frontend/pages/home_page/constants.py` | py | 已读取 74 行；顶层符号 1（get_title_sort_key）；导入 0；首轮未确认死代码。
- 686/925 `frontend/pages/home_page/core.py` | py | 已读取 1114 行；顶层符号 1（HomePage）；导入 14；首轮未确认死代码。
- 687/925 `frontend/pages/home_page/particle_constants.py` | py | 已读取 180 行；顶层符号 7（ParticleConfig, BaseParticleConfig, InkParticleConfig, PaperParticleConfig, ...）；导入 1；首轮未确认死代码。
- 688/925 `frontend/pages/home_page/particles.py` | py | 已读取 418 行；顶层符号 6（FloatingParticle, InkParticle, PaperParticle, SparkleParticle, ...）；导入 7；首轮未确认死代码。
- 689/925 `frontend/requirements.txt` | text | 已读取 5 行，判定为非代码文件。
- 690/925 `frontend/resources/afn_svg_019c9984-b5e8-761f-9e57-62816676d110.svg` | text | 已读取 60 行，判定为非代码文件。
- 691/925 `frontend/resources/logo.png` | binary | 已读取资源文件，判定为非代码。
- 692/925 `frontend/resources/thelittleprince.png` | binary | 已读取资源文件，判定为非代码。
- 693/925 `frontend/themes/__init__.py` | py | 已读取 58 行；顶层符号 0（无）；导入 7；首轮未确认死代码。
- 694/925 `frontend/themes/accessibility.py` | py | 已读取 181 行；顶层符号 1（AccessibilityTheme）；导入 1；首轮未确认死代码。
- 695/925 `frontend/themes/book_theme_styler.py` | py | 已读取 391 行；顶层符号 2（BookThemeStyler, get_book_styler）；导入 2；首轮未确认死代码。
- 696/925 `frontend/themes/button_styles.py` | py | 已读取 564 行；顶层符号 2（ButtonSizes, ButtonStyles）；导入 2；首轮未确认死代码。
- 697/925 `frontend/themes/component_styles.py` | py | 已读取 752 行；顶层符号 9（CardStyles, InputStyles, LabelStyles, BadgeStyles, ...）；导入 3；首轮未确认死代码。
- 698/925 `frontend/themes/modern_effects.py` | py | 已读取 854 行；顶层符号 4（ModernEffects, gradient, shadow, transition）；导入 3；首轮未确认死代码。
- 699/925 `frontend/themes/svg_icons.py` | py | 已读取 336 行；顶层符号 3（SVGIcons, SVGIconWidget, icon）；导入 1；首轮未确认死代码。
- 700/925 `frontend/themes/theme_manager/__init__.py` | py | 已读取 38 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 701/925 `frontend/themes/theme_manager/book_styles_mixin.py` | py | 已读取 313 行；顶层符号 1（BookStylesMixin）；导入 1；首轮未确认死代码。
- 702/925 `frontend/themes/theme_manager/button_styles_mixin.py` | py | 已读取 438 行；顶层符号 1（ButtonStylesMixin）；导入 1；首轮未确认死代码。
- 703/925 `frontend/themes/theme_manager/component_styles_mixin.py` | py | 已读取 570 行；顶层符号 1（ComponentStylesMixin）；导入 1；首轮未确认死代码。
- 704/925 `frontend/themes/theme_manager/constants.py` | py | 已读取 105 行；顶层符号 1（DesignSystemConstants）；导入 0；首轮未确认死代码。
- 705/925 `frontend/themes/theme_manager/core.py` | py | 已读取 461 行；顶层符号 1（ThemeManager）；导入 9；首轮未确认死代码。
- 706/925 `frontend/themes/theme_manager/properties_mixin.py` | py | 已读取 500 行；顶层符号 1（ThemePropertiesMixin）；导入 0；首轮未确认死代码。
- 707/925 `frontend/themes/theme_manager/themes.py` | py | 已读取 242 行；顶层符号 4（BookPalette, ThemeMode, LightTheme, DarkTheme）；导入 3；首轮未确认死代码。
- 708/925 `frontend/themes/theme_manager/v2_config_mixin.py` | py | 已读取 521 行；顶层符号 1（V2ConfigMixin）；导入 2；首轮未确认死代码。
- 709/925 `frontend/themes/transparency_aware_mixin.py` | py | 已读取 382 行；顶层符号 1（TransparencyAwareMixin）；导入 4；首轮未确认死代码。
- 710/925 `frontend/themes/transparency_tokens.py` | py | 已读取 333 行；顶层符号 5（OpacityTokens, TransparencyPreset, TransparencyPresets, get_component_meta, ...）；导入 2；首轮未确认死代码。
- 711/925 `frontend/utils/__init__.py` | py | 已读取 33 行；顶层符号 0（无）；导入 9；首轮未确认死代码。
- 712/925 `frontend/utils/async_worker.py` | py | 已读取 286 行；顶层符号 4（_com_initialize, _com_uninitialize, AsyncAPIWorker, run_async_action）；导入 6；首轮未确认死代码。
- 713/925 `frontend/utils/chapter_cache.py` | py | 已读取 371 行；顶层符号 4（CacheEntry, ChapterCache, get_chapter_cache, reset_chapter_cache）；导入 6；首轮未确认死代码。
- 714/925 `frontend/utils/chapter_error_formatter.py` | py | 已读取 98 行；顶层符号 2（ChapterErrorFormatter, format_chapter_error）；导入 1；首轮未确认死代码。
- 715/925 `frontend/utils/component_pool.py` | py | 已读取 348 行；顶层符号 7（ComponentPool, PoolManager, get_pool, reset_chapter_card, ...）；导入 5；首轮未确认死代码。
- 716/925 `frontend/utils/config_manager.py` | py | 已读取 269 行；顶层符号 1（ConfigManager）；导入 1；首轮未确认死代码。
- 717/925 `frontend/utils/constants.py` | py | 已读取 144 行；顶层符号 7（WorkerTimeouts, UIConstants, PageConstants, VersionConstants, ...）；导入 0；首轮未确认死代码。
- 718/925 `frontend/utils/dpi_utils.py` | py | 已读取 323 行；顶层符号 4（DPIHelper, dp, sp, responsive）；导入 5；首轮未确认死代码。
- 719/925 `frontend/utils/error_handler.py` | py | 已读取 155 行；顶层符号 3（handle_errors, _get_parent_widget, handle_api_errors）；导入 3；首轮未确认死代码。
- 720/925 `frontend/utils/formatters.py` | py | 已读取 57 行；顶层符号 3（get_project_status_text, count_chinese_characters, format_word_count）；导入 0；首轮未确认死代码。
- 721/925 `frontend/utils/lazy_loader.py` | py | 已读取 265 行；顶层符号 3（lazy_property, LazyWidget, DeferredInitMixin）；导入 4；首轮未确认死代码。
- 722/925 `frontend/utils/message_service.py` | py | 已读取 328 行；顶层符号 5（MessageService, show_api_error, confirm, confirm_danger, ...）；导入 3；首轮未确认死代码。
- 723/925 `frontend/utils/page_registry.py` | py | 已读取 200 行；顶层符号 12（register_page, register_page_factory, create_page, is_page_registered, ...）；导入 3；首轮未确认死代码。
- 724/925 `frontend/utils/project_helpers.py` | py | 已读取 31 行；顶层符号 1（get_blueprint）；导入 1；首轮未确认死代码。
- 725/925 `frontend/utils/sse_worker.py` | py | 已读取 569 行；顶层符号 6（_com_initialize, _com_uninitialize, SSEWorker, start_sse_worker, ...）；导入 9；首轮未确认死代码。
- 726/925 `frontend/utils/system_blur.py` | py | 已读取 344 行；顶层符号 1（SystemBlurManager）；导入 3；首轮未确认死代码。
- 727/925 `frontend/utils/window_blur.py` | py | 已读取 632 行；顶层符号 1（WindowBlurManager）；导入 3；首轮未确认死代码。
- 728/925 `frontend/utils/worker_manager.py` | py | 已读取 357 行；顶层符号 1（WorkerManager）；导入 5；首轮未确认死代码。
- 729/925 `frontend/utils/worker_pool.py` | py | 已读取 287 行；顶层符号 5（_com_initialize, _com_uninitialize, PooledTask, WorkerPool, ...）；导入 7；首轮未确认死代码。
- 730/925 `frontend/windows/__init__.py` | py | 已读取 11 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 731/925 `frontend/windows/base/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 732/925 `frontend/windows/base/detail_page.py` | py | 已读取 359 行；顶层符号 1（BaseDetailPage）；导入 8；首轮未确认死代码。
- 733/925 `frontend/windows/base/sections/__init__.py` | py | 已读取 12 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 734/925 `frontend/windows/base/sections/base_section.py` | py | 已读取 320 行；顶层符号 2（BaseSection, toggle_expand_state）；导入 7；首轮未确认死代码。
- 735/925 `frontend/windows/base/workspace_page.py` | py | 已读取 267 行；顶层符号 1（BaseWorkspacePage）；导入 8；首轮未确认死代码。
- 736/925 `frontend/windows/coding_desk/__init__.py` | py | 已读取 9 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 737/925 `frontend/windows/coding_desk/agent_content.py` | py | 已读取 802 行；顶层符号 1（AgentPlanningContent）；导入 11；首轮未确认死代码。
- 738/925 `frontend/windows/coding_desk/assistant_panel.py` | py | 已读取 701 行；顶层符号 2（RAGResultCard, CodingAssistantPanel）；导入 12；首轮未确认死代码。
- 739/925 `frontend/windows/coding_desk/components/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 740/925 `frontend/windows/coding_desk/components/directory_tree.py` | py | 已读取 523 行；顶层符号 2（TreeNodeItem, DirectoryTree）；导入 10；首轮未确认死代码。
- 741/925 `frontend/windows/coding_desk/components/project_info_card.py` | py | 已读取 212 行；顶层符号 3（TechStackTag, FlowLayout, ProjectInfoCard）；导入 7；首轮未确认死代码。
- 742/925 `frontend/windows/coding_desk/header.py` | py | 已读取 209 行；顶层符号 1（CodingDeskHeader）；导入 7；首轮未确认死代码。
- 743/925 `frontend/windows/coding_desk/main.py` | py | 已读取 282 行；顶层符号 1（CodingDesk）；导入 13；首轮未确认死代码。
- 744/925 `frontend/windows/coding_desk/mixins/__init__.py` | py | 已读取 13 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 745/925 `frontend/windows/coding_desk/mixins/content_management_mixin.py` | py | 已读取 128 行；顶层符号 1（ContentManagementMixin）；导入 4；首轮未确认死代码。
- 746/925 `frontend/windows/coding_desk/mixins/file_generation_mixin.py` | py | 已读取 141 行；顶层符号 1（FileGenerationMixin）；导入 5；首轮未确认死代码。
- 747/925 `frontend/windows/coding_desk/sidebar.py` | py | 已读取 183 行；顶层符号 1（CodingSidebar）；导入 9；首轮未确认死代码。
- 748/925 `frontend/windows/coding_desk/workspace.py` | py | 已读取 313 行；顶层符号 1（CodingWorkspace）；导入 7；首轮未确认死代码。
- 749/925 `frontend/windows/coding_detail/__init__.py` | py | 已读取 17 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 750/925 `frontend/windows/coding_detail/main.py` | py | 已读取 326 行；顶层符号 1（CodingDetail）；导入 11；首轮未确认死代码。
- 751/925 `frontend/windows/coding_detail/mixins/__init__.py` | py | 已读取 17 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 752/925 `frontend/windows/coding_detail/mixins/edit_dispatcher.py` | py | 已读取 351 行；顶层符号 1（EditDispatcherMixin）；导入 3；首轮未确认死代码。
- 753/925 `frontend/windows/coding_detail/mixins/header_manager.py` | py | 已读取 333 行；顶层符号 1（HeaderManagerMixin）；导入 8；首轮未确认死代码。
- 754/925 `frontend/windows/coding_detail/mixins/save_manager.py` | py | 已读取 130 行；顶层符号 1（SaveManagerMixin）；导入 6；首轮未确认死代码。
- 755/925 `frontend/windows/coding_detail/mixins/section_loader.py` | py | 已读取 145 行；顶层符号 1（SectionLoaderMixin）；导入 5；首轮未确认死代码。
- 756/925 `frontend/windows/coding_detail/mixins/tab_manager.py` | py | 已读取 135 行；顶层符号 1（TabManagerMixin）；导入 6；首轮未确认死代码。
- 757/925 `frontend/windows/coding_detail/sections/__init__.py` | py | 已读取 32 行；顶层符号 0（无）；导入 7；首轮未确认死代码。
- 758/925 `frontend/windows/coding_detail/sections/architecture.py` | py | 已读取 619 行；顶层符号 1（ArchitectureSection）；导入 12；首轮未确认死代码。
- 759/925 `frontend/windows/coding_detail/sections/dependencies.py` | py | 已读取 457 行；顶层符号 3（group_dependencies_by_source, GroupedDependencyCard, DependenciesSection）；导入 10；首轮未确认死代码。
- 760/925 `frontend/windows/coding_detail/sections/directory.py` | py | 已读取 953 行；顶层符号 5（DirectoryEditDialog, FileEditDialog, DirectoryNodeWidget, FileNodeWidget, ...）；导入 10；首轮未确认死代码。
- 761/925 `frontend/windows/coding_detail/sections/generated.py` | py | 已读取 446 行；顶层符号 2（GeneratedItemCard, GeneratedSection）；导入 7；首轮未确认死代码。
- 762/925 `frontend/windows/coding_detail/sections/generation.py` | py | 已读取 642 行；顶层符号 1（GenerationSection）；导入 12；首轮未确认死代码。
- 763/925 `frontend/windows/coding_detail/sections/modules.py` | py | 已读取 295 行；顶层符号 2（ModuleCard, ModulesSection）；导入 7；首轮未确认死代码。
- 764/925 `frontend/windows/coding_detail/sections/overview.py` | py | 已读取 517 行；顶层符号 1（CodingOverviewSection）；导入 7；首轮未确认死代码。
- 765/925 `frontend/windows/coding_detail/sections/planning.py` | py | 已读取 535 行；顶层符号 1（ProjectPlanningSection）；导入 7；首轮未确认死代码。
- 766/925 `frontend/windows/coding_detail/sections/systems.py` | py | 已读取 713 行；顶层符号 3（ModuleNode, SystemNode, SystemsSection）；导入 11；首轮未确认死代码。
- 767/925 `frontend/windows/coding_inspiration/__init__.py` | py | 已读取 10 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 768/925 `frontend/windows/coding_inspiration/main.py` | py | 已读取 320 行；顶层符号 1（CodingInspirationMode）；导入 10；首轮未确认死代码。
- 769/925 `frontend/windows/inspiration_mode/__init__.py` | py | 已读取 53 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 770/925 `frontend/windows/inspiration_mode/components/__init__.py` | py | 已读取 25 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 771/925 `frontend/windows/inspiration_mode/components/blueprint_confirmation.py` | py | 已读取 655 行；顶层符号 1（BlueprintConfirmation）；导入 7；首轮未确认死代码。
- 772/925 `frontend/windows/inspiration_mode/components/blueprint_display.py` | py | 已读取 192 行；顶层符号 1（BlueprintDisplay）；导入 5；首轮未确认死代码。
- 773/925 `frontend/windows/inspiration_mode/components/chat_bubble.py` | py | 已读取 285 行；顶层符号 1（ChatBubble）；导入 7；首轮未确认死代码。
- 774/925 `frontend/windows/inspiration_mode/components/conversation_input.py` | py | 已读取 159 行；顶层符号 1（ConversationInput）；导入 6；首轮未确认死代码。
- 775/925 `frontend/windows/inspiration_mode/components/inspired_option_card.py` | py | 已读取 379 行；顶层符号 2（InspiredOptionCard, InspiredOptionsContainer）；导入 7；首轮未确认死代码。
- 776/925 `frontend/windows/inspiration_mode/main.py` | py | 已读取 254 行；顶层符号 1（InspirationMode）；导入 8；首轮未确认死代码。
- 777/925 `frontend/windows/inspiration_mode/mixins/__init__.py` | py | 已读取 18 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 778/925 `frontend/windows/inspiration_mode/mixins/base_ui_mixin.py` | py | 已读取 266 行；顶层符号 1（InspirationBaseUIMixin）；导入 6；首轮未确认死代码。
- 779/925 `frontend/windows/inspiration_mode/mixins/blueprint_handler.py` | py | 已读取 391 行；顶层符号 1（BlueprintHandlerMixin）；导入 2；首轮未确认死代码。
- 780/925 `frontend/windows/inspiration_mode/mixins/conversation_manager.py` | py | 已读取 412 行；顶层符号 1（ConversationManagerMixin）；导入 3；首轮未确认死代码。
- 781/925 `frontend/windows/inspiration_mode/services/__init__.py` | py | 已读取 12 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 782/925 `frontend/windows/inspiration_mode/services/conversation_state.py` | py | 已读取 70 行；顶层符号 1（ConversationState）；导入 2；首轮未确认死代码。
- 783/925 `frontend/windows/main_window.py` | py | 已读取 1222 行；顶层符号 1（MainWindow）；导入 16；首轮未确认死代码。
- 784/925 `frontend/windows/novel_detail/__init__.py` | py | 已读取 118 行；顶层符号 0（无）；导入 8；首轮未确认死代码。
- 785/925 `frontend/windows/novel_detail/chapter_outline/REFACTORING_SUMMARY.md` | text | 已读取 228 行，判定为非代码文件。
- 786/925 `frontend/windows/novel_detail/chapter_outline/__init__.py` | py | 已读取 60 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 787/925 `frontend/windows/novel_detail/chapter_outline/components/__init__.py` | py | 已读取 23 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 788/925 `frontend/windows/novel_detail/chapter_outline/components/action_bar.py` | py | 已读取 255 行；顶层符号 1（OutlineActionBar）；导入 6；首轮未确认死代码。
- 789/925 `frontend/windows/novel_detail/chapter_outline/components/empty_states.py` | py | 已读取 116 行；顶层符号 3（OutlineEmptyState, LongNovelEmptyState, ShortNovelEmptyState）；导入 5；首轮未确认死代码。
- 790/925 `frontend/windows/novel_detail/chapter_outline/components/outline_list.py` | py | 已读取 170 行；顶层符号 1（OutlineListView）；导入 7；首轮未确认死代码。
- 791/925 `frontend/windows/novel_detail/chapter_outline/components/outline_row.py` | py | 已读取 223 行；顶层符号 1（OutlineRow）；导入 5；首轮未确认死代码。
- 792/925 `frontend/windows/novel_detail/chapter_outline/dialogs/__init__.py` | py | 已读取 18 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 793/925 `frontend/windows/novel_detail/chapter_outline/dialogs/chapter_detail_dialog.py` | py | 已读取 288 行；顶层符号 1（ChapterOutlineDetailDialog）；导入 5；首轮未确认死代码。
- 794/925 `frontend/windows/novel_detail/chapter_outline/dialogs/chapter_edit_dialog.py` | py | 已读取 38 行；顶层符号 1（ChapterOutlineEditDialog）；导入 1；首轮未确认死代码。
- 795/925 `frontend/windows/novel_detail/chapter_outline/dialogs/part_detail_dialog.py` | py | 已读取 401 行；顶层符号 1（PartOutlineDetailDialog）；导入 5；首轮未确认死代码。
- 796/925 `frontend/windows/novel_detail/chapter_outline/handlers/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 797/925 `frontend/windows/novel_detail/chapter_outline/handlers/chapter_outline_handler.py` | py | 已读取 422 行；顶层符号 1（ChapterOutlineHandlerMixin）；导入 6；首轮未确认死代码。
- 798/925 `frontend/windows/novel_detail/chapter_outline/handlers/part_outline_handler.py` | py | 已读取 400 行；顶层符号 1（PartOutlineHandlerMixin）；导入 8；首轮未确认死代码。
- 799/925 `frontend/windows/novel_detail/chapter_outline/main.py` | py | 已读取 461 行；顶层符号 1（ChapterOutlineSection）；导入 14；首轮未确认死代码。
- 800/925 `frontend/windows/novel_detail/chapter_outline/utils/__init__.py` | py | 已读取 7 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 801/925 `frontend/windows/novel_detail/components/__init__.py` | py | 已读取 17 行；顶层符号 0（无）；导入 3；首轮未确认死代码。
- 802/925 `frontend/windows/novel_detail/components/character_portraits_widget.py` | py | 已读取 844 行；顶层符号 2（PortraitCard, CharacterPortraitsWidget）；导入 11；首轮未确认死代码。
- 803/925 `frontend/windows/novel_detail/components/character_row.py` | py | 已读取 356 行；顶层符号 2（CharacterDetailDialog, CharacterRow）；导入 5；首轮未确认死代码。
- 804/925 `frontend/windows/novel_detail/components/relationship_row.py` | py | 已读取 414 行；顶层符号 2（RelationshipDetailDialog, RelationshipRow）；导入 5；首轮未确认死代码。
- 805/925 `frontend/windows/novel_detail/dialogs/__init__.py` | py | 已读取 23 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 806/925 `frontend/windows/novel_detail/dialogs/base_book_list_edit_dialog.py` | py | 已读取 388 行；顶层符号 3（build_delete_button_style, build_index_and_field_label_style, BaseBookListEditDialog）；导入 7；首轮未确认死代码。
- 807/925 `frontend/windows/novel_detail/dialogs/character_edit_dialog.py` | py | 已读取 288 行；顶层符号 2（CharacterItemWidget, CharacterListEditDialog）；导入 6；首轮未确认死代码。
- 808/925 `frontend/windows/novel_detail/dialogs/edit_dialog.py` | py | 已读取 145 行；顶层符号 1（EditDialog）；导入 5；首轮未确认死代码。
- 809/925 `frontend/windows/novel_detail/dialogs/list_edit_dialog.py` | py | 已读取 177 行；顶层符号 2（ListItemWidget, ListEditDialog）；导入 5；首轮未确认死代码。
- 810/925 `frontend/windows/novel_detail/dialogs/refine_dialog.py` | py | 已读取 171 行；顶层符号 1（RefineDialog）；导入 5；首轮未确认死代码。
- 811/925 `frontend/windows/novel_detail/dialogs/relationship_edit_dialog.py` | py | 已读取 254 行；顶层符号 2（RelationshipItemWidget, RelationshipListEditDialog）；导入 5；首轮未确认死代码。
- 812/925 `frontend/windows/novel_detail/dirty_tracker.py` | py | 已读取 288 行；顶层符号 3（FieldChange, ChapterOutlineChange, DirtyTracker）；导入 3；首轮未确认死代码。
- 813/925 `frontend/windows/novel_detail/main.py` | py | 已读取 418 行；顶层符号 1（NovelDetail）；导入 14；首轮未确认死代码。
- 814/925 `frontend/windows/novel_detail/mixins/__init__.py` | py | 已读取 35 行；顶层符号 0（无）；导入 9；首轮未确认死代码。
- 815/925 `frontend/windows/novel_detail/mixins/avatar_handler.py` | py | 已读取 166 行；顶层符号 1（AvatarHandlerMixin）；导入 6；首轮未确认死代码。
- 816/925 `frontend/windows/novel_detail/mixins/blueprint_refiner.py` | py | 已读取 157 行；顶层符号 1（BlueprintRefinerMixin）；导入 5；首轮未确认死代码。
- 817/925 `frontend/windows/novel_detail/mixins/edit_dispatcher.py` | py | 已读取 290 行；顶层符号 1（EditDispatcherMixin）；导入 3；首轮未确认死代码。
- 818/925 `frontend/windows/novel_detail/mixins/header_manager.py` | py | 已读取 364 行；顶层符号 1（HeaderManagerMixin）；导入 7；首轮未确认死代码。
- 819/925 `frontend/windows/novel_detail/mixins/import_analyzer.py` | py | 已读取 154 行；顶层符号 1（ImportAnalyzerMixin）；导入 5；首轮未确认死代码。
- 820/925 `frontend/windows/novel_detail/mixins/rag_manager.py` | py | 已读取 159 行；顶层符号 1（RAGManagerMixin）；导入 4；首轮未确认死代码。
- 821/925 `frontend/windows/novel_detail/mixins/save_manager.py` | py | 已读取 321 行；顶层符号 5（select_save_file, select_open_file, read_text_file, write_text_file, ...）；导入 6；首轮未确认死代码。
- 822/925 `frontend/windows/novel_detail/mixins/section_loader.py` | py | 已读取 187 行；顶层符号 1（SectionLoaderMixin）；导入 5；首轮未确认死代码。
- 823/925 `frontend/windows/novel_detail/mixins/tab_manager.py` | py | 已读取 162 行；顶层符号 1（TabManagerMixin）；导入 5；首轮未确认死代码。
- 824/925 `frontend/windows/novel_detail/section_styles.py` | py | 已读取 97 行；顶层符号 1（SectionStyles）；导入 2；首轮未确认死代码。
- 825/925 `frontend/windows/novel_detail/sections/__init__.py` | py | 已读取 23 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 826/925 `frontend/windows/novel_detail/sections/chapter_list_model.py` | py | 已读取 238 行；顶层符号 3（ChapterRoles, ChapterListModel, ChapterItemDelegate）；导入 7；首轮未确认死代码。
- 827/925 `frontend/windows/novel_detail/sections/chapters_section.py` | py | 已读取 575 行；顶层符号 1（ChaptersSection）；导入 13；首轮未确认死代码。
- 828/925 `frontend/windows/novel_detail/sections/characters_section.py` | py | 已读取 318 行；顶层符号 1（CharactersSection）；导入 8；首轮未确认死代码。
- 829/925 `frontend/windows/novel_detail/sections/overview_section.py` | py | 已读取 337 行；顶层符号 1（OverviewSection）；导入 6；首轮未确认死代码。
- 830/925 `frontend/windows/novel_detail/sections/relationships_section.py` | py | 已读取 235 行；顶层符号 1（RelationshipsSection）；导入 7；首轮未确认死代码。
- 831/925 `frontend/windows/novel_detail/sections/world_setting_section.py` | py | 已读取 386 行；顶层符号 1（WorldSettingSection）；导入 5；首轮未确认死代码。
- 832/925 `frontend/windows/settings/__init__.py` | py | 已读取 51 行；顶层符号 0（无）；导入 2；首轮未确认死代码。
- 833/925 `frontend/windows/settings/advanced_settings_widget.py` | py | 已读取 349 行；顶层符号 1（AdvancedSettingsWidget）；导入 9；首轮未确认死代码。
- 834/925 `frontend/windows/settings/base_config_list_widget.py` | py | 已读取 422 行；顶层符号 1（BaseConfigListWidget）；导入 10；首轮未确认死代码。
- 835/925 `frontend/windows/settings/config_io_helper.py` | py | 已读取 119 行；顶层符号 3（_show_error, export_config_json, import_config_json）；导入 4；首轮未确认死代码。
- 836/925 `frontend/windows/settings/dialogs/__init__.py` | py | 已读取 21 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 837/925 `frontend/windows/settings/dialogs/config_dialog.py` | py | 已读取 152 行；顶层符号 1（LLMConfigDialog）；导入 4；首轮未确认死代码。
- 838/925 `frontend/windows/settings/dialogs/embedding_config_dialog.py` | py | 已读取 241 行；顶层符号 1（EmbeddingConfigDialog）；导入 4；首轮未确认死代码。
- 839/925 `frontend/windows/settings/dialogs/prompt_edit_dialog.py` | py | 已读取 237 行；顶层符号 1（PromptEditDialog）；导入 7；首轮未确认死代码。
- 840/925 `frontend/windows/settings/dialogs/test_result_dialog.py` | py | 已读取 202 行；顶层符号 1（TestResultDialog）；导入 5；首轮未确认死代码。
- 841/925 `frontend/windows/settings/embedding_settings_widget.py` | py | 已读取 128 行；顶层符号 1（EmbeddingSettingsWidget）；导入 4；首轮未确认死代码。
- 842/925 `frontend/windows/settings/image_settings_widget.py` | py | 已读取 474 行；顶层符号 2（ImageConfigDialog, ImageSettingsWidget）；导入 7；首轮未确认死代码。
- 843/925 `frontend/windows/settings/llm_settings_widget.py` | py | 已读取 89 行；顶层符号 1（LLMSettingsWidget）；导入 5；首轮未确认死代码。
- 844/925 `frontend/windows/settings/max_tokens_settings_widget.py` | py | 已读取 401 行；顶层符号 1（MaxTokensSettingsWidget）；导入 9；首轮未确认死代码。
- 845/925 `frontend/windows/settings/prompt_settings_widget.py` | py | 已读取 490 行；顶层符号 3（PromptListWidget, ProjectTypeWidget, PromptSettingsWidget）；导入 9；首轮未确认死代码。
- 846/925 `frontend/windows/settings/queue_settings_widget.py` | py | 已读取 412 行；顶层符号 1（QueueSettingsWidget）；导入 8；首轮未确认死代码。
- 847/925 `frontend/windows/settings/temperature_settings_widget.py` | py | 已读取 286 行；顶层符号 1（TemperatureSettingsWidget）；导入 9；首轮未确认死代码。
- 848/925 `frontend/windows/settings/theme_settings/__init__.py` | py | 已读取 68 行；顶层符号 0（无）；导入 8；首轮未确认死代码。
- 849/925 `frontend/windows/settings/theme_settings/config_editor.py` | py | 已读取 600 行；顶层符号 3（update_theme_config_list, ThemeEditorBaseMixin, ThemeConfigEditorMixin）；导入 9；首轮未确认死代码。
- 850/925 `frontend/windows/settings/theme_settings/config_groups.py` | py | 已读取 217 行；顶层符号 0（无）；导入 0；首轮未确认死代码。
- 851/925 `frontend/windows/settings/theme_settings/io_handler.py` | py | 已读取 119 行；顶层符号 1（ThemeIOHandlerMixin）；导入 5；首轮未确认死代码。
- 852/925 `frontend/windows/settings/theme_settings/styles.py` | py | 已读取 371 行；顶层符号 2（build_list_action_button_style, ThemeStylesMixin）；导入 5；首轮未确认死代码。
- 853/925 `frontend/windows/settings/theme_settings/unified_widget.py` | py | 已读取 302 行；顶层符号 1（UnifiedThemeSettingsWidget）；导入 8；首轮未确认死代码。
- 854/925 `frontend/windows/settings/theme_settings/v2_components.py` | py | 已读取 422 行；顶层符号 3（CollapsibleSection, VariantTabWidget, ComponentEditor）；导入 6；首轮未确认死代码。
- 855/925 `frontend/windows/settings/theme_settings/v2_config_groups.py` | py | 已读取 472 行；顶层符号 3（get_component_field_key, get_token_field_key, get_effect_field_key）；导入 1；首轮未确认死代码。
- 856/925 `frontend/windows/settings/theme_settings/v2_editor_widget.py` | py | 已读取 836 行；顶层符号 2（EffectsEditor, V2ThemeEditorWidget）；导入 13；首轮未确认死代码。
- 857/925 `frontend/windows/settings/theme_settings/widget.py` | py | 已读取 434 行；顶层符号 1（ThemeSettingsWidget）；导入 12；首轮未确认死代码。
- 858/925 `frontend/windows/settings/ui_helpers.py` | py | 已读取 381 行；顶层符号 14（build_import_export_reset_save_bar, build_settings_secondary_button_style, build_settings_primary_button_style, build_settings_group_box_style, ...）；导入 6；首轮未确认死代码。
- 859/925 `frontend/windows/settings/view.py` | py | 已读取 784 行；顶层符号 3（LoadingSpinner, SettingsLoadingOverlay, SettingsView）；导入 11；首轮未确认死代码。
- 860/925 `frontend/windows/writing_desk/__init__.py` | py | 已读取 76 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 861/925 `frontend/windows/writing_desk/assistant_panel.py` | py | 已读取 865 行；顶层符号 3（RAGResultCard, RAGResultSection, AssistantPanel）；导入 14；首轮未确认死代码。
- 862/925 `frontend/windows/writing_desk/components/__init__.py` | py | 已读取 19 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 863/925 `frontend/windows/writing_desk/components/chapter_card.py` | py | 已读取 420 行；顶层符号 1（ChapterCard）；导入 9；首轮未确认死代码。
- 864/925 `frontend/windows/writing_desk/components/flippable_blueprint_card.py` | py | 已读取 753 行；顶层符号 1（FlippableBlueprintCard）；导入 10；首轮未确认死代码。
- 865/925 `frontend/windows/writing_desk/components/paragraph_selector.py` | py | 已读取 493 行；顶层符号 3（parse_range_input, ParagraphItem, ParagraphSelector）；导入 7；首轮未确认死代码。
- 866/925 `frontend/windows/writing_desk/components/suggestion_card.py` | py | 已读取 501 行；顶层符号 1（SuggestionCard）；导入 8；首轮未确认死代码。
- 867/925 `frontend/windows/writing_desk/components/thinking_stream.py` | py | 已读取 969 行；顶层符号 2（ThinkingBlock, ThinkingStreamView）；导入 8；首轮未确认死代码。
- 868/925 `frontend/windows/writing_desk/dialogs/__init__.py` | py | 已读取 24 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 869/925 `frontend/windows/writing_desk/dialogs/attribute_evidence_dialog.py` | py | 已读取 458 行；顶层符号 2（ChangeRecordCard, AttributeEvidenceDialog）；导入 10；首轮未确认死代码。
- 870/925 `frontend/windows/writing_desk/dialogs/outline_edit_dialog.py` | py | 已读取 346 行；顶层符号 1（OutlineEditDialog）；导入 6；首轮未确认死代码。
- 871/925 `frontend/windows/writing_desk/dialogs/prompt_preview_dialog.py` | py | 已读取 618 行；顶层符号 1（PromptPreviewDialog）；导入 8；首轮未确认死代码。
- 872/925 `frontend/windows/writing_desk/dialogs/protagonist_create_dialog.py` | py | 已读取 496 行；顶层符号 2（AttributeInputCard, ProtagonistCreateDialog）；导入 10；首轮未确认死代码。
- 873/925 `frontend/windows/writing_desk/dialogs/protagonist_profile_dialog.py` | py | 已读取 1327 行；顶层符号 4（AttributeCard, AttributeCategoryPanel, CategoryTabButton, ProtagonistProfileDialog）；导入 12；首轮未确认死代码。
- 874/925 `frontend/windows/writing_desk/header.py` | py | 已读取 360 行；顶层符号 1（WDHeader）；导入 11；首轮未确认死代码。
- 875/925 `frontend/windows/writing_desk/main.py` | py | 已读取 426 行；顶层符号 1（WritingDesk）；导入 13；首轮未确认死代码。
- 876/925 `frontend/windows/writing_desk/mixins/__init__.py` | py | 已读取 21 行；顶层符号 0（无）；导入 4；首轮未确认死代码。
- 877/925 `frontend/windows/writing_desk/mixins/chapter_generation_mixin.py` | py | 已读取 378 行；顶层符号 1（ChapterGenerationMixin）；导入 13；首轮未确认死代码。
- 878/925 `frontend/windows/writing_desk/mixins/content_management_mixin.py` | py | 已读取 241 行；顶层符号 1（ContentManagementMixin）；导入 5；首轮未确认死代码。
- 879/925 `frontend/windows/writing_desk/mixins/evaluation_mixin.py` | py | 已读取 54 行；顶层符号 1（EvaluationMixin）；导入 4；首轮未确认死代码。
- 880/925 `frontend/windows/writing_desk/mixins/version_management_mixin.py` | py | 已读取 220 行；顶层符号 1（VersionManagementMixin）；导入 6；首轮未确认死代码。
- 881/925 `frontend/windows/writing_desk/optimization/__init__.py` | py | 已读取 27 行；顶层符号 0（无）；导入 5；首轮未确认死代码。
- 882/925 `frontend/windows/writing_desk/optimization/content.py` | py | 已读取 864 行；顶层符号 1（OptimizationContent）；导入 17；首轮未确认死代码。
- 883/925 `frontend/windows/writing_desk/optimization/mode_control.py` | py | 已读取 124 行；顶层符号 1（ModeControlMixin）；导入 2；首轮未确认死代码。
- 884/925 `frontend/windows/writing_desk/optimization/models.py` | py | 已读取 23 行；顶层符号 1（OptimizationMode）；导入 1；首轮未确认死代码。
- 885/925 `frontend/windows/writing_desk/optimization/sse_handler.py` | py | 已读取 211 行；顶层符号 1（SSEHandlerMixin）；导入 2；首轮未确认死代码。
- 886/925 `frontend/windows/writing_desk/optimization/suggestion_handler.py` | py | 已读取 125 行；顶层符号 1（SuggestionHandlerMixin）；导入 2；首轮未确认死代码。
- 887/925 `frontend/windows/writing_desk/optimization_content.py` | py | 已读取 23 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 888/925 `frontend/windows/writing_desk/panels/__init__.py` | py | 已读取 26 行；顶层符号 0（无）；导入 6；首轮未确认死代码。
- 889/925 `frontend/windows/writing_desk/panels/analysis_panel.py` | py | 已读取 757 行；顶层符号 1（AnalysisPanelBuilder）；导入 7；首轮未确认死代码。
- 890/925 `frontend/windows/writing_desk/panels/base.py` | py | 已读取 309 行；顶层符号 1（BasePanelBuilder）；导入 5；首轮未确认死代码。
- 891/925 `frontend/windows/writing_desk/panels/content_panel.py` | py | 已读取 273 行；顶层符号 1（ContentPanelBuilder）；导入 7；首轮未确认死代码。
- 892/925 `frontend/windows/writing_desk/panels/manga/__init__.py` | py | 已读取 9 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 893/925 `frontend/windows/writing_desk/panels/manga/builder.py` | py | 已读取 710 行；顶层符号 1（MangaPanelBuilder）；导入 11；首轮未确认死代码。
- 894/925 `frontend/windows/writing_desk/panels/manga/details_tab.py` | py | 已读取 1026 行；顶层符号 2（CollapsibleSection, DetailsTabMixin）；导入 6；首轮未确认死代码。
- 895/925 `frontend/windows/writing_desk/panels/manga/pdf_tab.py` | py | 已读取 490 行；顶层符号 1（PdfTabMixin）；导入 9；首轮未确认死代码。
- 896/925 `frontend/windows/writing_desk/panels/manga/prompt_preview_dialog.py` | py | 已读取 375 行；顶层符号 1（PromptPreviewDialog）；导入 5；首轮未确认死代码。
- 897/925 `frontend/windows/writing_desk/panels/manga/prompt_tab.py` | py | 已读取 1047 行；顶层符号 1（PromptTabMixin）；导入 7；首轮未确认死代码。
- 898/925 `frontend/windows/writing_desk/panels/manga/scene_card.py` | py | 已读取 512 行；顶层符号 1（SceneCardMixin）；导入 6；首轮未确认死代码。
- 899/925 `frontend/windows/writing_desk/panels/manga/toolbar.py` | py | 已读取 969 行；顶层符号 1（ToolbarMixin）；导入 6；首轮未确认死代码。
- 900/925 `frontend/windows/writing_desk/panels/review_panel.py` | py | 已读取 428 行；顶层符号 1（ReviewPanelBuilder）；导入 10；首轮未确认死代码。
- 901/925 `frontend/windows/writing_desk/panels/summary_panel.py` | py | 已读取 150 行；顶层符号 1（SummaryPanelBuilder）；导入 6；首轮未确认死代码。
- 902/925 `frontend/windows/writing_desk/panels/version_panel.py` | py | 已读取 259 行；顶层符号 1（VersionPanelBuilder）；导入 9；首轮未确认死代码。
- 903/925 `frontend/windows/writing_desk/sidebar.py` | py | 已读取 887 行；顶层符号 1（WDSidebar）；导入 20；首轮未确认死代码。
- 904/925 `frontend/windows/writing_desk/utils.py` | py | 已读取 43 行；顶层符号 1（extract_protagonist_name）；导入 1；首轮未确认死代码。
- 905/925 `frontend/windows/writing_desk/workspace/__init__.py` | py | 已读取 15 行；顶层符号 0（无）；导入 1；首轮未确认死代码。
- 906/925 `frontend/windows/writing_desk/workspace/chapter_display.py` | py | 已读取 584 行；顶层符号 1（ChapterDisplayMixin）；导入 12；首轮未确认死代码。
- 907/925 `frontend/windows/writing_desk/workspace/core.py` | py | 已读取 216 行；顶层符号 1（WDWorkspace）；导入 13；首轮未确认死代码。
- 908/925 `frontend/windows/writing_desk/workspace/generation_handlers.py` | py | 已读取 162 行；顶层符号 1（GenerationHandlersMixin）；导入 2；首轮未确认死代码。
- 909/925 `frontend/windows/writing_desk/workspace/inline_diff.py` | py | 已读取 606 行；顶层符号 1（InlineDiffMixin）；导入 8；首轮未确认死代码。
- 910/925 `frontend/windows/writing_desk/workspace/manga_handlers.py` | py | 已读取 1644 行；顶层符号 1（MangaHandlersMixin）；导入 9；首轮未确认死代码。
- 911/925 `frontend/windows/writing_desk/workspace/theme_refresh.py` | py | 已读取 929 行；顶层符号 1（ThemeRefreshMixin）；导入 8；首轮未确认死代码。
- 912/925 `run_app.py` | py | 已读取 504 行；顶层符号 10（setup_paths, ensure_storage_dir, start_backend_subprocess, start_backend_thread, ...）；导入 8；首轮未确认死代码。
- 913/925 `setup_env.py` | py | 已读取 277 行；顶层符号 7（is_interactive, safe_input, parse_args, _has_vite_binary, ...）；导入 7；首轮未确认死代码。
- 914/925 `start_electron.py` | py | 已读取 465 行；顶层符号 24（configure_windows_console_utf8, get_npm_executable, get_node_executable, get_local_bin, ...）；导入 9；首轮未确认死代码。
- 915/925 `start_web.py` | py | 已读取 434 行；顶层符号 21（get_npm_executable, get_node_executable, get_python_executable, get_local_vite_bin, ...）；导入 12；首轮未确认死代码。
- 916/925 `test/chunkSplitTest/output/coding_chunk_lengths.png` | binary | 已读取资源文件，判定为非代码。
- 917/925 `test/chunkSplitTest/output/coding_density_scores.png` | binary | 已读取资源文件，判定为非代码。
- 918/925 `test/chunkSplitTest/output/coding_similarity_matrix.png` | binary | 已读取资源文件，判定为非代码。
- 919/925 `test/chunkSplitTest/output/novel_chunk_lengths.png` | binary | 已读取资源文件，判定为非代码。
- 920/925 `test/chunkSplitTest/output/novel_density_scores.png` | binary | 已读取资源文件，判定为非代码。
- 921/925 `test/chunkSplitTest/output/novel_similarity_matrix.png` | binary | 已读取资源文件，判定为非代码。
- 922/925 `test/chunkSplitTest/semantic_chunker_gui.py` | py | 已读取 934 行；顶层符号 9（get_embedding_func, ChunkWorker, MatplotlibCanvas, SimilarityMatrixWidget, ...）；导入 10；首轮未确认死代码。
- 923/925 `test/chunkSplitTest/test_semantic_chunker.py` | py | 已读取 536 行；顶层符号 8（create_mock_embedding_func, try_load_sentence_transformer, visualize_similarity_matrix, visualize_chunk_lengths, ...）；导入 6；首轮未确认死代码。
- 924/925 `test/print_logo.py` | py | 已读取 51 行；顶层符号 2（print_file, main）；导入 2；首轮未确认死代码。
- 925/925 `tools/redundancy_scan.py` | py | 已读取 240 行；顶层符号 7（Occurrence, _iter_files, _normalize_lines, _is_low_signal, ...）；导入 10；首轮未确认死代码。

## 候选复核与清理

- 高置信零引用扫描：Python 顶层定义候选从 65 项收敛到 0 项。
- 已确认并清理：`backend/app/core/constants.py`、`backend/app/core/dependencies.py`、`backend/app/core/state_validators.py`、`backend/app/exceptions.py`、`backend/app/utils/json_utils.py`。
- 已确认并清理：`backend/app/schemas/character_portrait.py`、`backend/app/schemas/coding.py`、`backend/app/schemas/coding_files.py`、`backend/app/schemas/llm_config.py`、`backend/app/schemas/novel.py`、`backend/app/schemas/protagonist.py`、`backend/app/schemas/theme_config.py`。
- 已删除整文件：`backend/app/schemas/config.py`。
- 已确认并清理：`backend/app/services/content_optimization/schemas.py`、`backend/app/services/image_generation/schemas.py`、`backend/app/services/rag/context_compressor.py`、`backend/app/services/rag/query_builder.py`、`backend/app/services/rag/temporal_retriever.py`、`backend/app/api/routers/writer/character_state.py`。

## 第二轮追加复核

- R2-01 `backend/app/api/routers/protagonist.py` | 复读依赖注入段；`get_analysis_service()`、`get_sync_service()` 均被路由 `Depends(...)` 使用，判定保留。
- R2-02 `backend/app/utils/exception_helpers.py` | 复读异常工具；确认仅 `get_safe_error_message()`、`log_exception()` 有真实外部调用，删除 `convert_to_http_exception()`、`ExceptionContext`、`format_exception_chain()`。
- R2-03 `backend/app/utils/api_format_utils.py` | 复读 URL 构造工具；确认 `build_openai_image_generations_endpoint()` 仍被 `image_generation/providers/openai_compatible.py` 使用，判定保留。
- R2-04 `backend/app/utils/prompt_helpers.py` | 复读提示词辅助；`ensure_prompt()`、`format_prompt_json()`、`build_prompt_section()`、`build_prompt_block()` 均有跨模块调用，判定保留。
- R2-05 `backend/app/utils/writer_helpers.py` | 复读写作辅助；`extract_tail_excerpt()`、`build_layered_summary()` 均被章节生成链路使用，判定保留。
- R2-06 `backend/app/utils/prompt_include.py` | 复读 include 解析工具；`parse_yaml_frontmatter()`、`resolve_prompt_includes()` 仍在 `prompt_service.py` / `init_db.py` 使用，删除零引用数据类 `PromptFrontmatter`。
- R2-07 `backend/app/utils/rag_helpers.py` | 复读 RAG 辅助；`build_query_text()`、`get_query_embedding()` 均被评估/RAG 组装逻辑使用，判定保留。
- R2-08 `backend/app/utils/config_import_utils.py` | 复读配置导入辅助；`parse_import_data()`、`ensure_export_data_version()`、`import_configs_with_unique_names()` 均在配置服务层使用，判定保留。
- R2-09 `backend/app/utils/field_mapping.py` | 复读字段映射工具；`build_update_data()`、`apply_mapping_with_defaults()` 由 `blueprint_base.py` 调用，判定保留。
- R2-10 `backend/app/utils/blueprint_utils.py` | 复读蓝图工具；保留 `prepare_blueprint_for_generation()`，删除零引用 helper：`extract_blueprint_characters()`、`extract_world_setting()`、`extract_full_synopsis()`、`build_blueprint_info_dict()`。
- R2-11 `backend/app/services/rag/utils.py` | 复读 RAG 公共工具；删除零引用格式化函数 `format_rag_summary_line()`，其余格式化辅助仍有调用。
- R2-12 `backend/app/services/coding_files/directory_agent/evaluator.py` | 复读目录规划评估器；删除零引用数据类 `OverallEvaluation`，其余评估逻辑保留。
- R2-13 `backend/app/services/image_generation/schemas.py` | 复读图片生成 schema；删除零引用常量 `SUPPORTED_MODELS`，确认 `has_style_keywords()` 仍被 provider 基类使用，保留。
- R2-14 `backend/app/services/manga_prompt/prompt_builder/page_prompt_generator.py` | 复读整页提示词生成器；删除零引用常量 `SHOT_TYPE_CHINESE`。
- R2-15 `backend/app/services/llm_service.py` | 复读配置缓存段；`LLMConfigCache`、`_config_cache`、`invalidate_config_cache()` 仍被 `llm_config_service.py` 使用，判定保留。
- R2-16 `frontend/themes/svg_icons.py` | 复读 SVG 图标模块；删除零引用控件类 `SVGIconWidget`，保留 `SVGIcons` 与 `icon()`。
- R2-17 `frontend/themes/transparency_tokens.py` | 复读透明度 token 模块；`get_component_meta()`、`get_all_component_ids()` 仍被 `v2_config_mixin.py` 使用，判定保留。
- R2-18 `frontend/utils/component_pool.py` | 复读组件池；删除零引用 `PoolManager`、`get_pool()`，确认 `reset_outline_row()` 仍被 `chapter_outline/components/outline_list.py` 使用，保留。
- R2-19 `frontend/utils/constants.py` | 复读桌面端常量；删除零引用常量类 `UIConstants`、`PageConstants`、`ChapterConstants`，保留 `WorkerTimeouts`、`VersionConstants`、`NovelConstants`、`SSEConstants`。
- R2-20 `frontend/utils/error_handler.py` | 复读错误处理装饰器；删除零引用 `handle_api_errors()`，保留 `handle_errors()` 与 `_get_parent_widget()`。
- R2-21 `frontend/utils/page_registry.py` | 复读页面注册表；确认全仓仅工厂注册在用，删除零引用 `register_page()`、`_page_registry` 及对应无效分支。
- R2-22 `frontend/utils/project_helpers.py` | 复读项目辅助；`get_blueprint()` 仍被 `frontend/windows/novel_detail/main.py` 使用，判定保留。
- R2-23 `frontend/utils/formatters.py` | 复读格式化工具；`get_project_status_text()`、`count_chinese_characters()`、`format_word_count()` 均有 UI 调用，判定保留。
- R2-24 `frontend/utils/async_worker.py` | 复读异步 worker；`AsyncWorker` 别名与 `run_async_action()` 均有桌面端调用，判定保留。
- R2-25 `frontend/utils/sse_worker.py` | 复读 SSE worker；`start_sse_worker()`、`reset_sse_generation_state()`、`stop_sse_worker()` 均在写作台/编程台链路使用，判定保留。

## 第三轮追加复核

- R3-01 `backend/app/services/coding_files/directory_agent/tools.py` | 复读目录规划工具定义；`get_tools_by_category()` 被同文件 `get_tools_prompt()` 使用，判定保留。
- R3-02 `backend/app/services/chapter_evaluation_service.py` | 复读章节评估服务；`ChapterEvaluationWorkflow` 在同文件 `workflow = ChapterEvaluationWorkflow(...)` 处真实实例化，判定保留。
- R3-03 `backend/app/services/image_generation/service.py` | 复读图片生成服务；`_is_complete_negative_prompt()` 被 `smart_merge_negative_prompt()` 调用，`NEGATIVE_PROMPT_QUALITY_KEYWORDS` 为内部判定常量，判定保留。
- R3-04 `backend/app/services/scene_descriptor.py` | 复读场景描述工具；`normalize_time_of_day()`、`normalize_time_marker()` 均被 `SceneDescriptor` 构造器链路使用，判定保留。
- R3-05 `backend/app/services/embedding_service.py` | 复读嵌入服务；`_is_meta_tensor_error()` 在本文件异常恢复分支使用，判定保留。
- R3-06 `frontend/api/exceptions.py` | 复读前端 API 异常体系；`_detect_business_error()`、`_is_llm_service_error()` 均被同文件异常工厂使用，判定保留。
- R3-07 `frontend/main.py` | 复读桌面端入口；`_get_log_level()` 与 `load_active_theme_config()` 均由 `main()` 调用，判定保留。
- R3-08 `frontend/windows/settings/view.py` | 复读设置页主视图；`LoadingSpinner` 被 `SettingsLoadingOverlay` 使用，`SettingsLoadingOverlay` 被 `SettingsView` 初始化，判定保留。
- R3-09 `backend/app/schemas/protagonist.py` | 复读主角档案 schema；确认 `ChangeHistoryQuery`、`BehaviorRecordQuery`、`DeletionMarkQuery`、`ImplicitStatsQuery` 仅定义并仅被路由无效 import，删除。
- R3-10 `backend/app/api/routers/protagonist.py` | 复读主角档案路由 import；同步移除无效导入 `ChangeHistoryQuery`、`BehaviorRecordQuery`、`DeletionMarkQuery`、`ImplicitStatsQuery`。
- R3-11 `backend/app/schemas/llm_config.py` | 复读 LLM 配置 schema；确认 `LLMConfigTestRequest` 仅定义并仅被路由无效 import，删除。
- R3-12 `backend/app/api/routers/llm_config.py` | 复读 LLM 配置路由 import；同步移除无效导入 `LLMConfigTestRequest`。

## 第四轮追加复核

- R4-01 `backend/app/services/character_portrait_service.py` | 复读角色立绘服务；`CharacterPortraitResponse` 在本文件仅 import 一次、无任何引用，删除无效导入。
- R4-02 `backend/app/services/coding_files/directory_service.py` | 复读目录服务；`SourceFileResponse` 在本文件仅 import 一次、无任何引用，删除无效导入。
- R4-03 `backend/app/services/content_optimization/service.py` | 复读正文优化服务入口；`OptimizationMode` 在本文件仅 import 一次、无任何引用，删除无效导入。
- R4-04 `backend/app/services/content_optimization/workflow.py` | 复读正文优化工作流；`CheckDimension`、`OptimizationMode`、`RAGContext` 在本文件仅 import 一次、无任何引用，删除无效导入。
- R4-05 `backend/app/services/image_generation/providers/base.py` | 复读图片 provider 基类；`has_style_keywords` 在该分支仅 import 一次、无任何引用，删除无效导入。
- R4-06 `backend/app/services/rag/context_builder.py` | 复读上下文构建器；`CharacterState`、`ForeshadowingData` 在本文件仅 import 一次、无任何引用，删除无效导入。
- R4-07 `backend/app/services/rag/query_builder.py` | 复读查询构建器；`ForeshadowingItem` 在本文件仅 import 一次、无任何引用，删除无效导入。

## 第五轮追加复核

- R5-01 `backend/app/schemas/novel.py` | 复读零引用候选 `ChoiceOption`、`UIControl`、`ChapterMetadata`、`ChapterSummaries`、`ForeshadowingData`、`KeyEvent`、`PartOutlineStatus`、`Relationship`、`ChapterOutlineUpdate`；向上追到 `ConverseResponse`、`ChapterAnalysisData`、`Blueprint`、`BatchBlueprintUpdate`、`PartOutline` 均有真实外部使用，判定整组保留。
- R5-02 `backend/app/schemas/coding_files.py` | 复读 `DirectoryNodeType`、`FileType`、`FilePriority`；确认均被活跃请求模型 `DirectoryNodeCreate`、`SourceFileCreate`、`SourceFileUpdate` 作为字段类型使用，判定保留。
- R5-03 `backend/app/schemas/embedding_config.py` | 复读 `EmbeddingConfigBase`、`EmbeddingProviderInfo`；前者为 `EmbeddingConfigCreate` 基类，后者用于活跃常量 `EMBEDDING_PROVIDERS` 且被路由 `list_providers` 返回，判定保留。
- R5-04 `backend/app/services/image_generation/schemas.py` | 复读图片生成 schema 常量区；上一轮删除 `providers/base.py` 中的无效导入后，`has_style_keywords()` 与 `STYLE_DETECTION_KEYWORDS` 在全仓已无任何调用，删除。
- R5-05 `backend/app/core/logging_config.py` | 复读 `setup_exception_hook()`、`log_startup_info()`；确认均在 `backend/app/main.py` 启动流程中调用，判定保留。
- R5-06 `backend/app/core/state_validators.py` | 复读 `check_writing_coherence()`、`get_max_generated_chapter()`；确认均在 `api/routers/writer/chapter_outlines.py` 生成前校验链路使用，判定保留。
- R5-07 `backend/app/utils/sse_helpers.py` | 复读 `create_sse_stream_response()`、`sse_text_chunk_events()`；前者仍被章节/编码 Prompt 流式路由使用，后者仍被灵感对话辅助路由使用，判定保留。
- R5-08 `backend/app/services/hf_model_download_service.py` | 复读下载辅助函数 `sanitize_model_dir_name()`、`fetch_hf_model_manifest()`、`download_hf_repo_to_dir()`、`safe_rmtree()`；均被 `api/routers/embedding_config.py` 的本地模型下载链路使用，判定保留。
- R5-09 `全仓 Python 收口扫描` | 过滤路由入口、脚本、测试后，对顶层 class/function 执行“全仓单次出现”复扫；未发现新的高置信业务死代码候选。

## 第六轮追加复核

- R6-01 `backend/app/schemas/project_workflow.py` | 复读回滚预览/执行 schema；`ProjectWorkflowCleanupImpact`、`ProjectWorkflowRollbackStepPreview`、`ProjectWorkflowRollbackPreviewResponse`、`ProjectWorkflowRollbackRequest`、`ProjectWorkflowRollbackResponse` 均被 `api/routers/writer/project_workflow.py` 真实使用，判定保留。
- R6-02 `backend/app/schemas/character_portrait.py` | 复读角色立绘 schema；`AutoGeneratePortraitsRequest`、`CharacterPortraitListResponse`、`GeneratePortraitResponse` 均被 `api/routers/character_portrait.py` 真实使用，判定保留。
- R6-03 `backend/app/schemas/model_download.py` | 复读本地嵌入模型下载 schema；`DownloadDefaultLocalEmbeddingModelRequest` 被 `api/routers/embedding_config.py` 下载端点使用，判定保留。
- R6-04 `backend/app/schemas/queue.py` | 复读队列 schema；`QueueStatusResponse`、`QueueConfigResponse`、`QueueConfigUpdate` 均被 `api/routers/queue.py` 使用，判定保留。
- R6-05 `backend/app/schemas/theme_config.py` | 复读主题导入 schema；`ThemeConfigImportRequest` 被 `api/routers/theme_config.py` 使用，判定保留。
- R6-06 `backend/app/api/routers/llm_config.py` | 复读 LLM 配置路由；`AsyncSession`、`get_session` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-07 `backend/app/api/routers/coding/projects.py` | 复读 Coding 项目路由；`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-08 `backend/app/api/routers/inspiration_router_registry.py` | 复读灵感路由注册器；`Callable` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-09 `backend/app/api/routers/image_generation.py` | 复读图片生成路由；`Path` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-10 `backend/app/api/routers/novels/outlines.py` | 复读章节大纲路由；`PromptTemplateNotFoundError` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-11 `backend/app/api/routers/coding/files_plan_v2.py` | 复读目录规划 V2 路由；`Any`、`Dict`、`Tuple` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-12 `backend/app/api/routers/writer/chapter_generation.py` | 复读章节生成路由；`Dict` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R6-13 `backend/app/api/routers/writer/manga_prompt_v2.py` | 复读漫画提示词 V2 路由；`MangaStyle` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第七轮追加复核

- R7-01 `backend/app/api/routers/character_portrait.py` | 复读角色立绘路由；`ResourceNotFoundError` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R7-02 `backend/app/api/routers/novels/export.py` | 复读章节导出路由；`AsyncSession`、`get_session` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R7-03 `backend/app/api/routers/novels/import_analysis.py` | 复读导入分析路由；`ResourceNotFoundError` 在文件内仅 import 一次、无任何引用，删除无效导入；静态扫描中的 `select` 为函数内延迟导入，判定保留。
- R7-04 `backend/app/api/routers/novels/outlines.py` | 复读章节大纲路由；静态扫描误报 `StreamingResponse`，当前文件并无该导入；补充确认 `AsyncSession`、`get_session` 仍被两个端点参数 `Depends(...)` 使用，保留。
- R7-05 `backend/app/api/routers/writer/part_outlines.py` | 复读部分大纲路由；`asyncio`、`ProjectStatus` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R7-06 `backend/app/api/routers/writer/rag_query.py` | 复读 RAG 查询路由；`RetrievedChunk`、`RetrievedSummary` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第八轮追加复核

- R8-01 `backend/app/api/routers/coding/rag.py` | 复读编程项目 RAG 路由；`CompletenessReport` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R8-02 `backend/app/api/routers/novels/blueprints.py` | 复读蓝图管理路由；`Any`、`Dict`、`List`、`PromptTemplateNotFoundError`、`PartOutline`、`ChapterOutline`、`PartOutlineRepository`、`ChapterIngestionService` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R8-03 `backend/app/api/routers/writer/chapter_management.py` | 复读章节管理路由；`settings`、`remove_think_tags` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R8-04 `backend/app/api/routers/writer/chapter_outlines.py` | 复读章节大纲管理路由；`List`、`PromptTemplateNotFoundError`、`sse_complete_event`、`sse_error_event`、`track_saved_items` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第九轮追加复核

- R9-01 `backend/app/core/dependencies.py` | 复读认证依赖；静态扫描中的 `JWTError` 来自函数内惰性导入 `from jose import JWTError, jwt`，并在异常分支说明里对应 JWT 解析失败场景，判定保留。
- R9-02 `backend/app/models/theme_config.py` | 复读主题模型；`Text` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-03 `backend/app/models/user.py` | 复读用户模型；`ForeignKey`、`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-04 `backend/app/repositories/base.py` | 复读仓储基类；`Union` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-05 `backend/app/repositories/blueprint_repository.py` | 复读蓝图仓储；`Iterable` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-06 `backend/app/repositories/coding_files_repository.py` | 复读 Coding 文件仓储；`AsyncSession` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-07 `backend/app/repositories/coding_repository.py` | 复读 Coding 项目仓储；`AsyncSession` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-08 `backend/app/repositories/prompt_repository.py` | 复读 Prompt 仓储；`AsyncSession` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-09 `backend/app/schemas/embedding_config.py` | 复读嵌入配置 schema；`datetime` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-10 `backend/app/schemas/llm_config.py` | 复读 LLM 配置 schema；`HttpUrl`、`datetime` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-11 `backend/app/services/avatar_service.py` | 复读头像服务；`Tuple` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R9-12 `backend/app/services/blueprint_service.py` | 复读蓝图服务；`json` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第十轮追加复核

- R10-01 `backend/app/services/chapter_generation/prompt_builder.py` | 复读章节提示词构建器；`json` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-02 `backend/app/services/chapter_generation/workflow.py` | 复读章节生成工作流；`TYPE_CHECKING`、`AsyncSession`、`LLMService` 仅用于空的类型检查分支，实际注解均使用字符串前向引用，删除无效导入与空分支。
- R10-03 `backend/app/services/chapter_version_service.py` | 复读章节版本服务；`TYPE_CHECKING`、`LLMService` 仅用于空的类型检查分支，实际注解已使用字符串前向引用，删除无效导入与空分支。
- R10-04 `backend/app/services/character_portrait_service.py` | 复读角色立绘服务；`ImageConfigService`、`base64`、`hashlib`、`httpx` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-05 `backend/app/services/embedding_config_service.py` | 复读嵌入配置服务；`InvalidParameterError` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-06 `backend/app/services/embedding_service.py` | 复读嵌入服务；静态扫描中的 `Path` 来自函数内局部导入 `from pathlib import Path`，判定保留。
- R10-07 `backend/app/services/hf_model_download_service.py` | 复读 HuggingFace 下载服务；`asyncio` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-08 `backend/app/services/image_generation/providers/comfyui.py` | 复读 ComfyUI provider；`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-09 `backend/app/services/image_generation/service.py` | 复读图片生成服务；`shutil` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R10-10 `backend/app/services/import_analysis/progress_tracker.py` | 复读导入分析进度跟踪器；`List` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第十一轮追加复核

- R11-01 `backend/app/services/llm_config_service.py` | 复读 LLM 配置服务；`InvalidParameterError` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-02 `backend/app/services/project_factory.py` | 复读项目工厂；`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-03 `backend/app/services/prompt_service.py` | 复读提示词服务；`Tuple`、`re` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-04 `backend/app/services/protagonist_profile/analysis_service.py` | 复读主角分析服务；`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-05 `backend/app/services/protagonist_profile/implicit_tracker.py` | 复读隐性属性追踪器；`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-06 `backend/app/services/protagonist_profile/service.py` | 复读主角档案服务；`datetime` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-07 `backend/app/services/protagonist_profile/sync_service.py` | 复读主角同步服务；`Any`、`Optional`、`json` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-08 `backend/app/services/rag/context_builder.py` | 复读上下文构建器；`build_outline_text` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-09 `backend/app/services/rag/context_compressor.py` | 复读上下文压缩器；`re` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-10 `backend/app/services/rag/temporal_retriever.py` | 复读时序检索器；`Optional`、`field` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-11 `backend/app/services/rag_common/ingestion_base.py` | 复读通用入库基类；`Sequence` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-12 `backend/app/services/rag_common/semantic_chunker.py` | 复读语义分块器；`math` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-13 `backend/app/utils/blueprint_utils.py` | 复读蓝图工具；`List`、`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-14 `backend/app/utils/content_normalizer.py` | 复读内容标准化工具；`re` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R11-15 `backend/app/utils/llm_tool.py` | 复读 LLM 工具封装；`LLMRequestLogger`、`fix_base_url` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第十二轮追加复核

- R12-01 `backend/app/repositories/chapter_outline_repository.py` | 复读章节大纲仓储；`delete`、`func` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-02 `backend/app/repositories/novel_repository.py` | 复读小说项目仓储；`load_only` 在 `_summary_load_options()` 中被多处真实使用，判定保留。
- R12-03 `backend/app/repositories/protagonist_repository.py` | 复读主角档案仓储；`Any`、`AsyncSession` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-04 `backend/app/services/coding_rag/auto_ingestion.py` | 复读 Coding 自动入库触发器；`CodingDataType` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-05 `backend/app/services/content_optimization/tool_executor.py` | 复读正文优化工具执行器；`Sequence` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-06 `backend/app/services/content_optimization/workflow.py` | 复读正文优化工作流；`List` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-07 `backend/app/services/foreshadowing_service.py` | 复读伏笔服务；`Chapter` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R12-08 `backend/app/services/embedding_service.py` | 复读嵌入服务；静态扫描中的 `Path` 来自函数内局部导入 `from pathlib import Path`，判定保留。

## 第十三轮追加复核

- R13-01 `backend/app/repositories/chapter_repository.py` | 复读章节仓储；`ChapterVersionRepository`、`ChapterEvaluationRepository`、`ChapterOutlineRepository` 的导入承担向后兼容导出职责，判定保留；其余模型/`delete` 是否可进一步收缩需结合兼容策略再判。
- R13-02 `backend/app/serializers/coding_serializer.py` | 复读 Coding 序列化器；`CodingBlueprintModel`、`Dict`、`List`、`json` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R13-03 `backend/app/services/chapter_generation/context.py` | 复读章节生成上下文；`TYPE_CHECKING` 分支内的 `BlueprintInfo`、`ChapterRAGContext`、`EnhancedRAGContext` 仅服务于字符串前向引用，删除无效导入与空分支。
- R13-04 `backend/app/services/chapter_generation/service.py` | 复读章节生成服务；`TYPE_CHECKING` 分支内的 `BlueprintInfo`、`ChapterRAGContext`、`EnhancedRAGContext`、`VectorStoreService` 仅服务于字符串前向引用，连同零引用导入 `Union`、`unwrap_markdown_json` 一并删除。
- R13-05 `backend/app/services/coding_files/directory_service.py` | 复读目录服务；`List` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第十四轮追加复核

- R14-01 `backend/app/services/chapter_evaluation_service.py` | 复读章节评估服务；`settings`、`LLMConstants`、`ChapterOutline` 在文件内仅 import 一次、无任何引用；`TYPE_CHECKING` 分支中的 `LLMService`、`VectorStoreService` 仅服务于字符串前向引用，删除无效导入与空分支。
- R14-02 `backend/app/services/coding_files/architect/decision_maker.py` | 复读架构决策器；`Any`、`Dict` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-03 `backend/app/services/coding_files/architect/generator.py` | 复读架构生成器；`ArchitecturePattern`、`Optional`、`Tuple` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-04 `backend/app/services/coding_files/architect/patterns.py` | 复读架构模式模板；`field` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-05 `backend/app/services/coding_files/architect/profiler.py` | 复读项目画像构建器；`ArchitecturePattern`、`Set` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-06 `backend/app/services/coding_files/architect/quality_evaluator.py` | 复读质量评估器；`Any`、`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入；`ArchitecturePattern` 在分支判断中仍被真实使用，保留。
- R14-07 `backend/app/services/coding_files/architect/refiner.py` | 复读目录精化 Agent；`ArchitecturePattern`、`StructureIssue` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-08 `backend/app/services/coding_files/architect/schemas.py` | 复读架构设计 schema；`Set` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R14-09 `backend/app/services/coding_files/directory_agent/agent.py` | 复读目录规划 Agent；`Optional`、`ToolCall` 在文件内仅 import 一次、无任何引用，删除无效导入。

## 第十五轮追加复核

- R15-01 `backend/app/services/coding_files/file_prompt/review.py` | 复读文件审查 Prompt 混入；`Any`、`CodingSourceFile` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R15-02 `backend/app/services/content_optimization/agent.py` | 复读正文优化 Agent；`Any`、`ToolCall` 在文件内仅 import 一次、无任何引用，删除无效导入；`ToolCallParseResult` 通过函数内局部导入使用，保留。
- R15-03 `backend/app/services/image_generation/pdf_export.py` | 复读 PDF 导出服务；`Any`、`ChapterMangaPrompt` 在文件内仅 import 一次、无任何引用，删除无效导入；`ImageReader` 通过函数内局部导入使用，保留。
- R15-04 `backend/app/services/image_generation/providers/openai_compatible.py` | 复读 OpenAI 兼容 provider；`Any`、`httpx` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R15-05 `backend/app/services/coding_rag/ingestion_service.py` | 复读 Coding RAG 入库服务；`AsyncSession`、`BLUEPRINT_INGESTION_TYPES`、`CodingFileVersion`、`CodingProject`、`Set` 在文件内仅 import 一次、无任何引用，删除无效导入；`CompletenessReport` 通过 `__all__` 对外导出，保留。

## 第十六轮追加复核

- R16-01 `backend/app/services/manga_prompt/core/page_prompt_builder.py` | 复读整页提示词构建器；`List` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-02 `backend/app/services/manga_prompt/storyboard/models.py` | 复读分镜数据模型；`Any` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-03 `backend/app/services/theme_config_service.py` | 复读主题配置服务；`Any` 与 `LIGHT_THEME_DEFAULTS`、`DARK_THEME_DEFAULTS`、`LIGHT_THEME_V2_DEFAULTS`、`DARK_THEME_V2_DEFAULTS` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-04 `backend/app/services/summary_service.py` | 复读摘要服务；`Chapter`、`ChapterOutlineRepository`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，仍服务于静态类型检查，判定保留。
- R16-05 `backend/app/services/manga_prompt/extraction/chapter_info_extractor.py` | 复读章节信息提取器；`CharacterRole`、`ImportanceLevel`、`EmotionType`、`EventType`、`PROMPT_NAME`、`EXTRACTION_SYSTEM_PROMPT` 在文件内仅 import 一次、无任何引用，删除无效导入；`_build_prompt()`、`_get_system_prompt()`、`_parse_chapter_info()` 在仓库内无任何调用点，删除零调用私有方法；`PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- R16-06 `backend/app/services/manga_prompt/planning/page_planner.py` | 复读页面规划器；`PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留；`_simple_plan()` 的私有参数 `min_pages` 在文件内无任何读取，删除未使用参数并同步收紧调用点。
- R16-07 `backend/app/services/manga_prompt/storyboard/designer.py` | 复读分镜设计器；`DialogueBubble`、`PanelShape`、`ShotType`、`WidthRatio`、`AspectRatio` 在文件内仅 import 一次、无任何引用，删除无效导入；`PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- R16-08 `backend/app/services/inspiration_service.py` | 复读灵感对话服务；`NovelConversation`、`CodingConversation`、`Optional` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-09 `backend/app/services/part_outline/chapter_outline_workflow.py` | 复读章节大纲工作流；`log_exception` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-10 `backend/app/services/part_outline/context_retriever.py` | 复读部分大纲上下文检索器；`ChapterOutlineRepository`、`LLMService`、`VectorStoreService` 属于 `TYPE_CHECKING` 前向引用导入，仍服务于静态类型检查，判定保留。
- R16-11 `backend/app/services/part_outline/service.py` | 复读部分大纲服务；`Any`、`Dict`、`TYPE_CHECKING`、`PartOutlineParser`、`PartOutlineModelFactory`、`ChapterOutlineWorkflow` 在文件内仅 import 一次、无任何引用，删除无效导入；空 `TYPE_CHECKING` 分支同步删除。
- R16-12 `backend/app/services/part_outline/workflow.py` | 复读部分大纲工作流；`AsyncSession` 属于 `TYPE_CHECKING` 前向引用导入，仍服务于静态类型检查，判定保留。
- R16-13 `backend/app/services/novel_rag/ingestion_service.py` | 复读 Novel RAG 入库服务；`AsyncSession`、`BLUEPRINT_INGESTION_TYPES`、`ChapterVersion`、`NovelProject`、`Set`、`Union`、`func` 在文件内仅 import 一次、无任何引用，删除无效导入；`CompletenessReport` 通过 `__all__` 对外导出，保留。
- R16-14 `backend/app/repositories/chapter_repository.py` | 复读章节仓储；`ChapterVersionRepository`、`ChapterEvaluationRepository`、`ChapterOutlineRepository` 仍承担向后兼容导出职责，保留；`delete`、`ChapterVersion`、`ChapterEvaluation`、`ChapterOutline` 在文件内仅 import 一次、无任何引用，删除无效导入。
- R16-15 `backend/app/db/init_db.py` | 复读数据库初始化；`from ..models import ...` 的模型导入虽未在本文件直接读取，但依赖 `models/__init__.py` 的导入副作用注册 SQLAlchemy 元数据，供 `Base.metadata.create_all()` 初始化表结构，判定保留。
- R16-16 `backend/app/api/routers/novels/import_analysis.py` | 复读导入分析路由；函数内局部导入 `select` 无任何调用点，删除无效导入；同函数内 `update` 仍用于失败状态回写，保留。
- R16-17 `backend/app/api/routers/novels/outlines.py` | 复读章节大纲路由；`StreamingResponse` 在函数内仅 import 一次、无任何引用，删除无效导入；SSE 返回仍由 `create_sse_response()` 承担。
- R16-18 `backend/app/core/dependencies.py` | 复读依赖注入模块；`get_vector_ingestion_service()`、`get_part_outline_service()`、`get_avatar_service()` 在仓库内仅剩文档示例引用，删除零引用依赖工厂；`JWTError` 仍属函数内惰性导入误报，保留。
- R16-19 `backend/app/utils/content_normalizer.py` | 复读内容标准化工具；`normalize_version_content()`、`_coerce_text()`、`_clean_string()` 在仓库内无任何调用点，删除零调用函数；连带删除失效的 `logger`、`_PREFERRED_CONTENT_KEYS` 与相关导入，保留仍被后端使用的 `count_chinese_characters()`。
- R16-20 `backend/app/utils/sse_helpers.py` | 复读 SSE 工具；`sse_generator_error_handler()`、`track_saved_items()`、`SSEProgressTracker` 仅在模块文档示例中出现，删除零调用实现；连带移除失效的 `wraps`、`TypeVar`、`T`。
- R16-21 `backend/app/utils/text_utils.py` | 复读文本工具；整文件未被任何模块导入，`truncate()`、`truncate_preview()`、`truncate_middle()`、`mask_sensitive()` 全部零引用，删除整文件。
- R16-22 `frontend/themes/transparency_tokens.py` | 复读透明度 token 配置；`get_component_meta()` 在仓库内无任何调用点，删除零调用函数；`get_all_component_ids()` 仍被 `v2_config_mixin.py` 使用，保留。
- R16-23 `frontend/themes/theme_manager/v2_config_mixin.py` | 复读 V2 主题配置混入；`get_component_meta` 导入未被使用，删除无效导入。
- R16-24 `frontend/utils/dpi_utils.py` | 复读 DPI 工具；`responsive()` 在仓库内无任何调用点，删除零调用便捷函数。
- R16-25 `backend/app/services/chapter_version_service.py` | 复读章节版本服务；同步清理对已删除 `normalize_version_content()` 的陈旧注释引用，避免后续误读。
- R16-26 `backend/app/services/part_outline/service.py` | 复读部分大纲服务；同步清理对已删除 `get_part_outline_service()` 的陈旧文档引用，避免后续误判。

## 第十七轮追加复核

- R17-01 `backend/app/services/chapter_generation/prompt_builder.py` | 复读章节提示词构建器；在前序已删除无效导入 `json` 的基础上，确认 `_default_builder` 与 `get_chapter_prompt_builder()` 在仓库内已无任何调用点，删除零调用模块级单例与工厂函数。
- R17-02 `backend/app/services/chapter_generation/version_processor.py` | 复读章节版本处理器；确认 `_default_processor` 与 `get_version_processor()` 在仓库内无任何调用点，删除零调用模块级单例与工厂函数。
- R17-03 `backend/app/services/chapter_generation/__init__.py` | 复读章节生成包导出；确认 `get_chapter_prompt_builder`、`get_version_processor` 的转发导入和 `__all__` 导出已全部失效，删除残留包导出。
- R17-04 `backend/app/services/novel_rag/auto_ingestion.py` | 复读小说自动入库触发器；`trigger_protagonist_ingestion()` 在仓库内无任何调用点，删除零调用触发器；连带失效导入 `PROTAGONIST_INGESTION_TYPES` 一并删除。
- R17-05 `backend/app/services/novel_rag/__init__.py` | 复读 Novel RAG 包导出；确认 `trigger_protagonist_ingestion`、`set_novel_strategy_manager`、`switch_novel_global_preset` 对外转发均已失效，删除残留导出。
- R17-06 `backend/app/services/novel_rag/chunk_strategy.py` | 复读 Novel RAG 分块策略；`set_novel_strategy_manager()`、`switch_novel_global_preset()` 在仓库内无任何调用点，删除零调用策略切换函数。
- R17-07 `backend/app/services/rag/scene_extractor.py` | 复读场景状态提取器；确认 `_default_extractor` 与 `get_scene_extractor()` 在仓库内无任何调用点，删除零调用模块级单例与工厂函数。
- R17-08 `backend/app/services/rag/utils.py` | 复读 RAG 公共工具；在前序已删除 `format_rag_summary_line()` 的基础上，确认 `format_chapter_reference()` 同样已无任何调用点，继续删除零调用辅助函数。
- R17-09 `backend/app/services/rag/__init__.py` | 复读 RAG 包导出；确认 `get_scene_extractor`、`format_chapter_reference` 的转发导出已失效，删除残留导出。
- R17-10 `backend/app/services/rag_common/semantic_chunker.py` | 复读语义分块器；在前序已删除无效导入 `math` 的基础上，确认 `_default_chunker`、`get_semantic_chunker()`、`set_semantic_chunker()` 在仓库内无任何调用点，删除零调用单例与工厂/切换函数。
- R17-11 `backend/app/services/rag_common/__init__.py` | 复读 RAG 通用包导出；确认 `get_semantic_chunker`、`set_semantic_chunker` 的转发导出已失效，删除残留导出。
- R17-12 `backend/app/services/coding_rag/chunk_strategy.py` | 复读 Coding RAG 分块策略；`set_strategy_manager()`、`switch_global_preset()` 在仓库内无任何调用点，删除零调用策略切换函数。
- R17-13 `backend/app/services/coding_rag/__init__.py` | 复读 Coding RAG 包导出；确认 `set_strategy_manager`、`switch_global_preset` 的转发导出已失效，删除残留导出。

## 第十八轮追加复核

- R18-01 `frontend/themes/modern_effects.py` | 复读现代效果库尾段；确认模块级便捷函数 `transition()` 在仓库内无任何调用点，删除零调用包装函数，保留仍被组件使用的 `ModernEffects.TRANSITIONS` 常量。
- R18-02 `frontend/utils/worker_pool.py` | 复读线程池工具；确认 `submit_task()` 在仓库内仅剩定义、自注释示例与聚合导出，未被任何业务模块调用，删除零调用便捷函数。
- R18-03 `frontend/utils/chapter_cache.py` | 复读章节缓存工具；确认 `reset_chapter_cache()` 在仓库内无任何调用点，删除零调用测试辅助函数，保留运行期实际使用的 `get_chapter_cache()`。
- R18-04 `frontend/utils/__init__.py` | 复读工具聚合导出；确认 `submit_task`、`reset_chapter_cache` 的转发导入和 `__all__` 导出均已失效，删除残留聚合导出。
- R18-05 `frontend/themes/book_theme_styler.py` | 复读书香样式器尾段；确认全局单例 `_global_styler` 与工厂函数 `get_book_styler()` 在仓库内无任何调用点，删除零调用单例壳。
- R18-06 `frontend/themes/__init__.py` | 复读主题聚合导出；确认 `get_book_styler` 的转发导入和 `__all__` 导出均已失效，删除残留聚合导出。

## 第十九轮追加复核

- R19-01 `frontend/utils/message_service.py` | 复读消息服务便捷函数区；确认顶层包装函数 `confirm_danger()` 在仓库内无任何调用点，删除零调用包装层，保留仍被其他模块可直接使用的 `MessageService.confirm_danger()` 静态方法。
- R19-02 `frontend/components/loading_spinner.py` | 复读加载动画模块尾段；确认 `loading_context()` 在仓库内仅剩定义、示例注释与聚合导出，删除零调用上下文包装函数。
- R19-03 `frontend/components/__init__.py` | 复读组件聚合导出；确认 `loading_context` 的转发导入和 `__all__` 导出均已失效，删除残留聚合导出。

## 第二十轮追加复核

- R20-01 `frontend/themes/svg_icons.py` | 复读 SVG 图标模块尾段；在前序已删除 `SVGIconWidget` 的基础上，确认顶层便捷函数 `icon()` 既未被 `themes/__init__.py` 导出，也无任何业务导入点，删除零调用包装函数。
- R20-02 `backend/app/services/manga_prompt/core/service.py` | 复读漫画提示词核心服务尾段；确认便捷函数 `generate_manga_prompts()` 在仓库内仅剩定义与包级转发导出，删除零调用包装函数，保留核心类 `MangaPromptServiceV2`。
- R20-03 `backend/app/services/manga_prompt/core/__init__.py` | 复读漫画提示词核心包导出；确认 `generate_manga_prompts` 的转发导入和 `__all__` 导出已失效，删除残留导出。
- R20-04 `backend/app/services/manga_prompt/__init__.py` | 复读漫画提示词服务包导出；确认 `generate_manga_prompts` 的转发导入和 `__all__` 导出已失效，删除残留导出。

## 第二十一轮追加复核

- R21-01 `frontend/themes/modern_effects.py` | 复读现代效果库尾段；在第十八轮已删除 `transition()` 的基础上，继续确认顶层便捷函数 `gradient()`、`shadow()` 既无导入点也无业务调用，删除同类零调用包装函数。

## 第二十二轮追加复核

- R22-01 `backend/app/services/queue/base.py` | 复读请求队列基类；确认 `reset_instance()` 注释虽标为“仅用于测试”，但当前仓库不存在任何测试或业务调用点，删除零调用测试辅助类方法。
- R22-02 `backend/app/services/coding_rag/auto_ingestion.py` | 复读编程项目自动入库触发器；确认 `trigger_blueprint_ingestion()` 在仓库内仅剩定义与包级导出，删除零调用触发器。
- R22-03 `backend/app/services/coding_rag/__init__.py` | 复读 Coding RAG 包导出；在前序已清理旧导出后，继续确认 `trigger_blueprint_ingestion` 的转发导入与 `__all__` 导出均已失效，删除残留导出。

## 第二十三轮追加复核

- R23-01 `backend/app/services/coding_rag/auto_ingestion.py` | 复读编程项目自动入库触发器头部；确认闭包返回值绑定 `trigger_async_ingestion` 在仓库内无任何业务导入点，删除零调用模块级绑定，保留仍被路由和服务实际使用的 `schedule_ingestion`。
- R23-02 `backend/app/services/coding_rag/__init__.py` | 复读 Coding RAG 包导出；确认 `trigger_async_ingestion` 的转发导入与 `__all__` 导出已失效，删除残留导出。
- R23-03 `backend/app/services/novel_rag/auto_ingestion.py` | 复读小说自动入库触发器头部；确认闭包返回值绑定 `trigger_async_ingestion` 在仓库内无任何业务导入点，删除零调用模块级绑定，保留文件内部仍在使用的 `schedule_ingestion` / `schedule_multiple_ingestions`。
- R23-04 `backend/app/services/novel_rag/__init__.py` | 复读 Novel RAG 包导出；确认 `trigger_async_ingestion`、`schedule_ingestion`、`schedule_multiple_ingestions` 的包级转发导入与 `__all__` 导出均无任何业务导入点，删除残留导出。

## 第二十四轮追加复核

- R24-01 `backend/app/services/import_analysis/__init__.py` | 复读导入分析聚合包；确认 `count_chinese_characters`、`cn_to_arabic` 仅在 `txt_parser.py` 内部真实使用，当前仓库没有任何 `from services.import_analysis import ...` 外部导入点，删除包级残留导出。

## 第二十五轮追加复核

- R25-01 `backend/app/services/rag_common/__init__.py` | 复读 RAG 通用聚合包；确认 `run_ingestion_task`、`split_markdown_sections`、`build_chunk_config`、`clone_chunk_config`、`serialize_chunk_config` 当前仓库均无任何 `from services.rag_common import ...` 外部导入点，删除整组残留包级导出。

## 第二十六轮追加复核

- R26-01 `backend/app/services/rag/__init__.py` | 复读 RAG 聚合包；确认 `extract_involved_characters`、`truncate_text`、`build_outline_text` 当前仅被子模块通过 `.utils` 直接导入，仓库内不存在任何 `from services.rag import ...` 包级导入点，删除残留包级导出。
- R26-02 `backend/app/services/content_optimization/__init__.py` | 复读正文优化聚合包；确认 `get_tools_prompt` 仅在 `tools.py` / `agent.py` 链路内部真实使用，当前仓库不存在任何 `from services.content_optimization import get_tools_prompt` 包级导入点，删除残留包级导出。
- R26-03 `backend/app/services/coding/__init__.py` | 复读 Coding 聚合包；确认当前仓库仅通过包级入口导入 `CodingProjectService`，`CodingBlueprintService` 不存在任何包级导入点，删除残留包级导出，保留子模块实现以避免误伤潜在动态引用。
- R26-04 `backend/app/services/coding_files/__init__.py` | 复读 Coding 文件服务聚合包；确认当前仓库仅通过包级入口导入 `DirectoryStructureService`、`FilePromptService`，其余目录生成/架构设计类型均通过子包 `directory_generator`、`architect` 直接导入，删除父包层残留导出以收缩无效 API 面。
- R26-05 `backend/app/services/part_outline/__init__.py` | 复读部分大纲聚合包；确认当前仓库仅通过包级入口导入 `PartOutlineService`、`PartOutlineWorkflow`，其余解析器/工厂/上下文检索/章节工作流相关符号均在子模块内部直接导入，删除父包层残留导出，保留底层实现。
- R26-06 `backend/app/services/queue/__init__.py` | 复读请求队列聚合包；确认当前仓库仅通过包级入口导入 `LLMRequestQueue`、`ImageRequestQueue`，`RequestQueue` 基类没有任何包级导入点，删除残留包级导出。
- R26-07 `backend/app/services/theme_defaults/__init__.py` | 复读主题默认配置聚合包；确认 `get_theme_defaults`、`get_theme_v2_defaults` 被 `theme_config_service.py` 真实通过包级入口导入使用，保留。
- R26-08 `backend/app/services/image_generation/__init__.py` | 复读图片生成聚合包；确认 `ImageConfigService`、`ImageGenerationService` 以及公开 schema 被依赖注入与路由真实通过包级入口导入使用，保留。
- R26-09 `backend/app/services/protagonist_profile/__init__.py` | 复读主角档案聚合包；确认导出的五个服务/追踪器类均被 `protagonist.py` 路由通过包级入口导入使用，保留。

## 第二十七轮追加复核

- R27-01 `backend/app/services/coding_files/architect/__init__.py` | 复读架构设计子包聚合层；确认 `files_plan_v2.py` 仅通过包级入口导入 `ArchitecturePattern`、`ProjectProfiler`、`ArchitectureDecisionMaker`、`ArchitectureBasedGenerator`、`QualityEvaluator`、`RefinementAgent`，其余 schema / 模板辅助符号均无任何包级导入点，删除父包层残留导出。
- R27-02 `backend/app/services/coding_files/directory_generator/__init__.py` | 复读目录生成子包聚合层；确认 `files_plan_v2.py` 仅通过包级入口导入 `BruteForceOutput`、`DirectoryTreeBuilder`，`DirectorySpec`、`FileSpec`、`PlannedDirectory`、`PlannedFile` 当前均无任何包级导入点，删除残留导出。
- R27-03 `backend/app/services/coding_files/directory_agent/__init__.py` | 复读目录规划 Agent 子包聚合层；确认当前仓库仅通过包级入口导入 `run_directory_planning_agent`，其余 Agent 状态、工具类型、执行器和便捷函数均无任何包级导入点，删除残留导出。
- R27-04 `backend/app/services/image_generation/providers/__init__.py` | 复读图片供应商子包聚合层；确认 `service.py`、`config_service.py` 仅通过包级入口导入 `ImageProviderFactory`，其余 provider 基类、结果模型和具体实现类均通过子模块直连或装饰器注册使用，删除残留导出。
- R27-05 `backend/app/services/manga_prompt/__init__.py` | 复读漫画提示词顶层聚合包；确认 `manga_prompt_v2.py` 当前仅通过包级入口导入 `MangaPromptServiceV2`、`MangaPromptResult`，其余提取/规划/分镜/提示词构建类型均无任何外部包级导入点，删除顶层残留导出。
- R27-06 `backend/app/services/manga_prompt/core/__init__.py` | 复读漫画提示词核心聚合包；确认顶层包当前仅需从 `core` 取出 `MangaPromptServiceV2`，`MangaStyle`、`CheckpointManager`、`ResultPersistence` 无任何包级导入点，删除残留导出。
- R27-07 `backend/app/services/manga_prompt/extraction/__init__.py` | 复读漫画信息提取子包聚合层；确认内部真实通过包入口使用的仅有 `ChapterInfo`、`ChapterInfoExtractor`，其余枚举、明细数据类和提示词常量均无任何包级导入点，删除残留导出。
- R27-08 `backend/app/services/manga_prompt/planning/__init__.py` | 复读页面规划子包聚合层；确认 `PagePlanner`、`PagePlanItem`、`PagePlanResult` 仍被内部通过包入口使用，提示词常量 `PROMPT_NAME`、`PAGE_PLANNING_PROMPT`、`PLANNING_SYSTEM_PROMPT` 无任何包级导入点，删除残留导出。
- R27-09 `backend/app/services/manga_prompt/storyboard/__init__.py` | 复读分镜设计子包聚合层；确认分镜模型与 `StoryboardDesigner` 仍被内部通过包入口使用，提示词常量 `PROMPT_NAME`、`STORYBOARD_DESIGN_PROMPT`、`STORYBOARD_SYSTEM_PROMPT` 无任何包级导入点，删除残留导出。
- R27-10 `backend/app/services/manga_prompt/prompt_builder/__init__.py` | 复读提示词构建子包聚合层；确认 `PromptBuilder`、`PagePromptGenerator`、`PagePrompt`、`MangaPromptResult` 仍被内部通过包入口使用，`PanelPrompt`、`PagePromptResult` 无任何包级导入点，删除残留导出。

## 第二十八轮追加复核

- R28-01 `backend/app/repositories/__init__.py` | 复读仓储聚合包；确认当前仓库不存在任何 `from ...repositories import ...` 包级导入点，整组导出均为残留聚合壳，删除父包层导出并保留空包入口。
- R28-02 `frontend/windows/settings/__init__.py` | 复读设置窗口顶层聚合包；确认当前仓库仅通过包级入口导入 `SettingsView`，4 个对话框类无任何 `from windows.settings import ...` 使用点，删除残留顶层导出。
- R28-03 `frontend/windows/settings/theme_settings/__init__.py` | 复读主题设置子包聚合层；确认 `view.py` 当前仅通过包级入口导入 `UnifiedThemeSettingsWidget`，其余 V1/V2 编辑器、配置组与组件类均无任何包级导入点，删除残留导出。
- R28-04 `frontend/windows/writing_desk/__init__.py` | 复读写作台顶层聚合包；确认 `windows/__init__.py` 与 `page_registry.py` 当前仅通过包级入口导入 `WritingDesk`，其余 Mixins、Dialogs、Components 均无任何 `from windows.writing_desk import ...` 使用点，删除残留顶层导出。
- R28-05 `frontend/windows/novel_detail/__init__.py` | 复读项目详情顶层聚合包；确认 `windows/__init__.py` 与 `page_registry.py` 当前仅通过包级入口导入 `NovelDetail`，其余 Mixins、Sections、Dialogs、Components、工具类与 `ChapterOutlineSection` 均无任何 `from windows.novel_detail import ...` 使用点，删除残留顶层导出。
- R28-06 `frontend/windows/__init__.py` | 复读前端窗口总聚合包；确认当前仓库不存在任何 `from windows import ...` 包级导入点，`MainWindow`、`InspirationMode`、`NovelDetail`、`WritingDesk`、`SettingsView` 的残留顶层导出全部删除，保留空包入口。

## 第二十九轮追加复核

- R29-01 `frontend/windows/writing_desk/dialogs/__init__.py` | 复读写作台对话框聚合包；确认当前仓库仅通过包级入口导入 `OutlineEditDialog`、`PromptPreviewDialog`、`ProtagonistProfileDialog`，`ProtagonistCreateDialog`、`AttributeEvidenceDialog` 仅在对话框实现文件内部通过子模块直连使用，删除残留包级导出。
- R29-02 `frontend/windows/writing_desk/components/__init__.py` | 复读写作台组件聚合包；确认当前仓库仅通过包级入口导入 `ChapterCard`、`FlippableBlueprintCard`，`ThinkingStreamView`、`SuggestionCard`、`ParagraphSelector` 均通过子模块直连使用，删除残留包级导出。
- R29-03 `frontend/windows/novel_detail/chapter_outline/__init__.py` | 复读章节大纲子模块顶层聚合包；确认当前仓库仅通过包级入口导入 `ChapterOutlineSection`，其余 Handlers、Dialogs、Components 均在子模块内部直接导入，删除 10 个残留顶层导出。

## 第三十轮追加复核

- R30-01 `frontend/windows/writing_desk/panels/__init__.py` | 复读写作台面板聚合包；确认 `workspace/core.py` 当前仅通过包级入口导入 5 个具体 `*PanelBuilder`，`BasePanelBuilder` 无任何包级导入点，删除残留导出。
- R30-02 `frontend/windows/novel_detail/chapter_outline/dialogs/__init__.py` | 复读章节大纲对话框聚合包；确认当前仅 `ChapterOutlineEditDialog` 通过包级入口使用，`PartOutlineDetailDialog`、`ChapterOutlineDetailDialog` 均在组件中通过子模块直连使用，删除残留包级导出。
- R30-03 `frontend/windows/novel_detail/chapter_outline/components/__init__.py` | 复读章节大纲组件聚合包；确认 `main.py` 与 `writing_desk/sidebar.py` 当前仅通过包级入口使用 `OutlineListView`、`OutlineActionBar`、`LongNovelEmptyState`、`ShortNovelEmptyState`，`OutlineRow` 无任何包级导入点，删除残留包级导出。

## 第三十一轮追加复核

- R31-01 `frontend/windows/base/__init__.py` | 复读通用页面基类聚合包；确认 `writing_desk/main.py`、`coding_desk/main.py` 当前仅通过包级入口导入 `BaseWorkspacePage`，`BaseDetailPage`、`BaseSection` 无任何 `from windows.base import ...` 使用点，删除残留导出。
- R31-02 `frontend/windows/inspiration_mode/__init__.py` | 复读灵感模式顶层聚合包；确认 `page_registry.py` 当前仅通过包级入口导入 `InspirationMode`，其余 Mixins、Components、Services 全部无任何 `from windows.inspiration_mode import ...` 使用点，删除 9 个残留顶层导出。
- R31-03 `frontend/windows/inspiration_mode/components/__init__.py` | 复读灵感模式组件聚合包；确认 `ConversationInput`、`ChatBubble`、`BlueprintDisplay`、`BlueprintConfirmation`、`InspiredOptionsContainer` 仍被本系统和编程灵感页通过包级入口使用，`InspiredOptionCard` 无任何包级导入点，删除残留导出。
- R31-04 `frontend/windows/coding_desk/components/__init__.py` | 复读编程工作台组件聚合包；确认 `coding_desk/sidebar.py` 当前仅通过包级入口导入 `DirectoryTree`、`ProjectInfoCard`，`TreeNodeItem`、`TechStackTag` 无任何包级导入点，删除残留导出。
- R31-05 `frontend/windows/coding_detail/sections/__init__.py` | 复读编程详情页 Sections 聚合包；确认 `section_loader.py` 当前仅通过包级入口导入 4 个主 Section，历史兼容导出的 `SystemNode`、`ModuleNode`、`GroupedDependencyCard`、`GeneratedItemCard` 无任何包级导入点，删除残留导出。

## 第三十二轮追加复核

- R32-01 `frontend/components/__init__.py` | 复读通用组件聚合包；确认当前仓库仅通过包级入口导入 `LoadingOverlay`，其余 18 个组件/工具均无任何 `from frontend.components import ...` 使用点，删除残留包级导出。
- R32-02 `frontend/components/base/__init__.py` | 复读基础组件聚合包；确认当前仓库仅通过包级入口导入 `ThemeAwareWidget`、`ThemeAwareFrame`、`ThemeAwareButton`，`AnimatedStackedWidget` 无任何 `from frontend.components.base import ...` 使用点，删除残留导出。
- R32-03 `frontend/api/__init__.py` | 复读前端 API 顶层聚合包；确认当前仓库不存在任何 `from frontend.api import ...` 业务导入点，删除整组 20 个历史转发导出并保留精简包入口。
- R32-04 `frontend/api/client/__init__.py` | 复读 API Client 聚合包；确认当前仓库仅通过包级入口导入 `AFNAPIClient`，`TimeoutConfig` 无任何包级导入点，删除残留导出。
- R32-05 `frontend/pages/__init__.py` | 复读页面顶层聚合包；确认当前仓库不存在任何 `from frontend.pages import ...` 业务导入点，删除顶层残留转发导出并保留精简包入口。
- R32-06 `frontend/pages/home_page/__init__.py` | 复读首页聚合包；确认当前仓库仅通过包级入口导入 `HomePage`，`FeatureCard`、`ProjectCard`、粒子系统与常量相关导出均无任何包级导入点，删除 6 个残留导出。
- R32-07 `frontend/themes/__init__.py` | 复读主题顶层聚合包；确认当前仓库仅通过包级入口导入 `ButtonStyles`、`ModernEffects`，其余主题管理、组件样式、无障碍、SVG 图标和书籍样式相关导出均无任何包级导入点，删除 15 个残留导出。
- R32-08 `frontend/themes/theme_manager/__init__.py` | 复读主题管理器聚合包；确认当前仓库仅通过包级入口导入 `theme_manager`、`ThemeMode`，`ThemeManager`、`BookPalette`、`LightTheme`、`DarkTheme`、`V2ConfigMixin` 等均无任何包级导入点，删除残留导出。

## 第三十三轮追加复核

- R33-01 `frontend/components/dialogs/common/__init__.py` | 复读通用对话框子包聚合层；确认当前仓库和父包入口仅实际使用 `get_regenerate_preference`，`RegenerateDialog` 无任何 `from components.dialogs(.common) import ...` 包级导入点，删除残留导出。
- R33-02 `frontend/components/dialogs/__init__.py` | 复读对话框顶层聚合包；确认 `get_regenerate_preference` 仍被架构页与系统页通过包级入口使用，但 `RegenerateDialog` 无任何包级导入点，删除残留导出。
- R33-03 `frontend/windows/writing_desk/optimization/__init__.py` | 复读正文优化聚合包；确认兼容层 `optimization_content.py` 当前仅通过包级入口导入 `OptimizationContent`、`OptimizationMode`，3 个 mixin 类均无任何 `from ...optimization import ...` 使用点，删除残留导出。

## 第三十四轮追加复核

- R34-01 `frontend/components/inputs/__init__.py` | 复读输入组件聚合包；确认主题设置链路仅通过包级入口导入 `SwitchWidget`，`SwitchControl` 只作为 `switch_input.py` 内部实现存在，无任何 `from components.inputs import SwitchControl` 使用点，删除残留导出。

## 第三十五轮追加复核

- R35-01 `frontend/models/__init__.py` | 复读前端模型包入口；确认当前仓库不存在任何 `from models import ...` 或 `from models.project_status import ...` 真实导入点，`ProjectStatus` 转发与 `NovelProject`、`Blueprint`、`Chapter`、`ChapterVersion`、`LLMConfig` 五个历史数据类均为零引用残留，删除并保留精简包入口。

## 第三十六轮追加复核

- R36-01 `frontend/models/project_status.py` | 复读前端项目状态模块；确认当前仓库不存在任何 `from models.project_status import ...` 真实导入点，`ProjectStatus` 枚举与 `Enum` 导入均为零引用残留，删除实现并保留兼容占位模块。

## 第三十七轮追加复核

- R37-01 `backend/app/serializers/__init__.py` | 复读序列化器包入口；确认当前仓库不存在任何 `from ...serializers import ...` 包级导入点，`NovelSerializer` 的聚合转发已完全失效，删除残留导出并保留精简包入口。

## 第三十八轮追加复核

- R38-01 `backend/app/services/theme_defaults/__init__.py` | 复读主题默认值聚合包；确认当前仓库仅通过包级入口使用 `get_theme_defaults`、`get_theme_v2_defaults`，四个 V1/V2 默认值常量均无任何包级导入点，删除残留导出。

## 第三十九轮追加复核

- R39-01 `backend/app/services/image_generation/__init__.py` | 复读图片生成服务聚合包；确认当前仓库仅通过包级入口使用 `ImageGenerationService`、`ImageConfigService` 与核心请求/响应 schema，`PDFExportService`、`ProviderType`、`PDFExportRequest`、`PDFExportResult` 已全部改走子模块直连，无任何包级导入点，删除残留导出。

## 第四十轮追加复核

- R40-01 `setup_env.py` | 复读环境初始化脚本的 `backend.startup` 导入块；经 AST 与全文检索确认 `Colors`、`WORK_DIR`、`STORAGE_DIR`、`BACKEND_PORT`、`setup_logging`、`_load_logging_config`、`is_port_in_use`、`get_pid_using_port`、`kill_process_on_port`、`ensure_port_available`、`check_uv_available`、`install_uv`、`StartupProgress`、`startup_progress`、`check_dependencies_installed` 均无任何实际引用，删除整组无效导入。

## 第四十一轮追加复核

- R41-01 `backend/startup/__init__.py` | 复读启动包入口；结合第四十轮对 `setup_env.py` 的 AST 复核结果，确认 `Colors`、`WORK_DIR`、`STORAGE_DIR`、`BACKEND_PORT`、`setup_logging`、`_load_logging_config`、`is_port_in_use`、`get_pid_using_port`、`kill_process_on_port`、`ensure_port_available`、`check_uv_available`、`install_uv`、`StartupProgress`、`startup_progress`、`check_dependencies_installed` 已无任何包级消费者，删除这 15 个历史转发导出。

## 第四十二轮追加复核

- R42-01 `run_app.py` | 复读应用启动脚本；经 AST 与全文检索确认 `Path`、`WORK_DIR`、`BACKEND_VENV`、`FRONTEND_VENV`、`print_banner` 在当前脚本中均无任何实际引用，删除整组无效导入。

## 第四十三轮追加复核

- R43-01 `backend/startup/animation.py` | 复读启动动画模块；经 AST 与全文检索确认 `BASE_DIR` 在当前文件中无任何实际引用，删除无效导入。
- R43-02 `backend/startup/installer.py` | 复读依赖安装模块；经 AST 与全文检索确认 `Set`、`BACKEND_DIR`、`FRONTEND_DIR` 在当前文件中均无任何实际引用，删除整组无效导入。
- R43-03 `backend/startup/port_utils.py` | 复读端口工具模块；经 AST 与全文检索确认 `logger` 在当前文件中无任何实际引用，删除无效导入。
- R43-04 `backend/startup/uv_manager.py` | 复读 UV 管理模块；经 AST 与全文检索确认 `logger` 在当前文件中无任何实际引用，删除无效导入。

## 第四十四轮追加复核

- R44-01 `backend/scripts/fix_real_summary.py` | 复读 real_summary 修复脚本；经 AST 与全文检索确认 `selectinload` 在当前脚本中无任何实际引用，删除无效导入。
- R44-02 `backend/app/services/content_optimization/agent.py` | 复读正文优化 Agent；经 AST 与全文检索确认顶层 `json` 导入与 `_parse_response()` 内部的 `ToolCallParseResult` 局部导入均无任何实际引用，删除无效导入。
- R44-03 `backend/app/services/coding_rag/auto_ingestion.py` | 复读编程项目自动入库触发器；经 AST 与全文检索确认 `Any`、`Optional`、`BLUEPRINT_INGESTION_TYPES`、`schedule_multiple_ingestions` 均无任何实际引用，删除无效导入。
- R44-04 `backend/app/services/coding_rag/ingestion_service.py` | 复读编程项目入库服务；确认 `CompletenessReport` 已无任何模块级导入点，仅剩历史 `__all__` 暴露，删除残留导入与导出。
- R44-05 `backend/app/services/coding_rag/__init__.py` | 复读编程项目 RAG 聚合包；确认当前仓库仅通过包级入口使用 `CodingDataType`、`CodingProjectIngestionService`、`schedule_ingestion`，删除其余 12 个零包级引用的历史导出。
- R44-06 `backend/app/services/novel_rag/ingestion_service.py` | 复读小说项目入库服务；确认 `CompletenessReport` 已无任何模块级导入点，仅剩历史 `__all__` 暴露，删除残留导入与导出。
- R44-07 `backend/app/services/novel_rag/__init__.py` | 复读小说项目 RAG 聚合包；确认当前仓库仅通过包级入口使用 `NovelDataType`、`NovelProjectIngestionService` 与 5 个 `trigger_*_ingestion` 入口，删除其余 16 个零包级引用的历史导出。

## 第四十五轮追加复核

- R45-01 `backend/app/services/embedding_service.py` | 复读嵌入服务模块；经 AST 与全文检索确认 `_find_local_model_path()` 内部 `Path` 导入无任何实际引用，删除无效导入。
- R45-02 `backend/app/services/image_generation/pdf_export.py` | 复读 PDF 导出服务；经 AST 与全文检索确认 `generate_chapter_manga_pdf()` 内部 `ImageReader` 导入无任何实际引用，删除无效导入。
- R45-03 `backend/app/core/dependencies.py` | 复读依赖注入模块；确认 JWT 解码局部导入中的 `JWTError` 仅存于注释语义、无任何实际引用，删除无效导入并保留 `jwt`。
- R45-04 `backend/app/repositories/novel_repository.py` | 复读小说仓储；确认顶层 `load_only` 函数导入未被调用，当前文件实际使用的是 `selectinload(...).load_only()` 链式方法，删除无效导入。
- R45-05 `backend/app/services/chapter_generation/__init__.py` | 复读章节生成聚合包；确认当前仓库仅通过包级入口使用 `ChapterGenerationService`、`ChapterGenerationWorkflow`，删除 `ChapterGenerationContext`、`ChapterGenerationResult`、`ChapterPromptBuilder`、`ChapterVersionProcessor` 4 个零包级引用导出。
- R45-06 `backend/app/services/content_optimization/__init__.py` | 复读正文优化聚合包；确认当前仓库已全部改为子模块直连，`ContentOptimizationService`、`ContentOptimizationWorkflow`、`ContentOptimizationAgent`、`ToolName`、`ToolCall`、`ToolResult`、`ToolExecutor`、`AgentState`、`OptimizeContentRequest`、`CheckDimension`、`AnalysisScope`、`OptimizationEventType` 均无任何包级导入点，删除整组历史导出并保留精简包入口。

## 第四十六轮追加复核

- R46-01 `backend/app/services/import_analysis/__init__.py` | 复读导入分析聚合包；确认当前仓库仅通过包级入口使用 `ImportAnalysisService`，删除 `BaseTxtParser`、`DefaultTxtParser`、`SimpleSplitParser`、`TxtParser`、`ParsedChapter`、`ParseResult`、`ProgressTracker`、`ChapterSummary`、`ImportResult` 9 个零包级引用导出，并将文档示例改为子模块直连导入。
- R46-02 `backend/app/services/rag/__init__.py` | 复读 RAG 聚合包；确认当前仓库仅通过包级入口使用 `EnhancedQueryBuilder`、`EnhancedQuery`、`TemporalAwareRetriever`、`SmartContextBuilder`、`GenerationContext`、`ContextCompressor`、`get_outline_rag_retriever`，删除 `BlueprintInfo`、`RAGContext`、`OutlineRAGRetriever`、`SceneState`、`SceneStateExtractor` 5 个零包级引用导出。
- R46-03 `backend/app/services/rag_common/__init__.py` | 复读 RAG 通用聚合包；确认当前仓库不存在任何 `rag_common` 包级入口消费者，删除 `SemanticChunkConfig`、`ChunkResult`、`SemanticChunker`、`IngestionResult`、`TypeChangeDetail`、`CompletenessReport`、`BaseProjectIngestionService`、`BaseChunkStrategyManager` 8 个零包级引用导出并保留精简包入口。

## 第四十七轮追加复核

- R47-01 `frontend/api/client/import_mixin.py` | 复读导入分析客户端 mixin；经 AST 与全文检索确认 `Optional` 无任何实际引用，删除无效导入。
- R47-02 `frontend/components/base/animated_stacked_widget.py` | 复读动画堆叠组件；确认 `QWidget`、`Qt`、`QPoint` 在当前文件均无任何实际引用，删除无效导入。
- R47-03 `frontend/components/empty_state.py` | 复读空状态组件；确认顶层 `QWidget` 导入无任何实际引用，删除无效导入。
- R47-04 `frontend/components/flow_layout.py` | 复读流式布局组件；确认 `QWidgetItem`、`QSizePolicy` 在当前文件中无任何实际引用，删除无效导入。
- R47-05 `frontend/components/inputs/slider_input.py` | 复读滑块输入组件；确认 `QFrame` 导入无任何实际引用，删除无效导入。
- R47-06 `frontend/components/inputs/switch_input.py` | 复读开关输入组件；确认 `QFrame`、`QRect`、`QSize` 在当前文件均无任何实际引用，删除无效导入。
- R47-07 `frontend/components/loading_spinner.py` | 复读加载动画组件；在第十九轮已移除 `loading_context()` 后继续确认 `Any`、`QSizePolicy`、`QFrame`、`QRect` 均无任何实际引用，删除无效导入。
- R47-08 `frontend/components/lazy_tab_widget.py` | 复读懒加载 Tab 组件；确认 `Optional` 导入无任何实际引用，删除无效导入。
- R47-09 `frontend/utils/chapter_cache.py` | 复读章节缓存工具；在第十八轮已移除 `reset_chapter_cache()` 后继续确认 `List` 导入无任何实际引用，删除无效导入。
- R47-10 `frontend/utils/component_pool.py` | 复读组件对象池；在此前已移除全局池管理接口后继续确认 `Any` 导入无任何实际引用，删除无效导入。
- R47-11 `frontend/utils/window_blur.py` | 复读窗口模糊效果管理器；确认 `Optional` 导入无任何实际引用，删除无效导入。
- R47-12 `frontend/windows/base/detail_page.py` | 复读详情页基类；确认 `Callable` 导入无任何实际引用，删除无效导入。

## 第四十八轮追加复核

- R48-01 `frontend/components/theme_transition.py` | 复读主题切换过渡组件；确认 `QParallelAnimationGroup` 导入无任何实际引用，删除无效导入。
- R48-02 `frontend/themes/modern_effects.py` | 复读现代效果库；在此前已移除 `transition()`、`gradient()`、`shadow()` 后继续确认 `Tuple`、`QLinearGradient`、`QRadialGradient`、`QConicalGradient` 均无任何实际引用，删除无效导入。
- R48-03 `frontend/themes/svg_icons.py` | 复读 SVG 图标库；在此前已移除 `SVGIconWidget` 与 `icon()` 后继续确认 `Optional` 导入无任何实际引用，删除无效导入。
- R48-04 `frontend/windows/base/workspace_page.py` | 复读工作台页面基类；确认 `List` 导入无任何实际引用，删除无效导入。
- R48-05 `frontend/windows/coding_desk/header.py` | 复读编程工作台 Header；确认 `Optional`、`QWidget` 在当前文件均无任何实际引用，删除无效导入。
- R48-06 `frontend/windows/coding_desk/sidebar.py` | 复读编程工作台侧边栏；确认 `QFrame` 导入无任何实际引用，删除无效导入。
- R48-07 `frontend/windows/coding_desk/workspace.py` | 复读编程工作台工作区；确认 `QFrame` 导入无任何实际引用，删除无效导入。
- R48-08 `frontend/utils/__init__.py` | 复读工具包入口；确认当前仓库不存在任何 `from utils import ...` 或 `import utils` 的真实消费者，删除 `AsyncAPIWorker`、`ChapterCache`、`get_chapter_cache`、`ComponentPool`、`ConfigManager`、`WorkerTimeouts`、`LazyWidget`、`lazy_property`、`DeferredInitMixin`、`SSEWorker`、`WorkerManager`、`WorkerPool`、`PooledTask` 共 13 个历史聚合导出并保留精简包入口。

## 第四十九轮追加复核

- R49-01 `frontend/themes/transparency_tokens.py` | 复读透明度 Token 配置；在第十六轮已移除 `get_component_meta()` 后继续确认 `Tuple` 导入无任何实际引用，删除无效导入；`get_all_component_ids()` 仍被 `v2_config_mixin.py` 使用，保留。
- R49-02 `frontend/windows/coding_detail/sections/overview.py` | 复读编程项目概览 Section；确认 `logging`、`List` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- R49-03 `frontend/windows/coding_detail/sections/generated.py` | 复读已生成内容 Section；确认 `logging`、`QScrollArea`、`QSizePolicy` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- R49-04 `frontend/windows/coding_detail/sections/modules.py` | 复读模块列表 Section；确认 `logging`、`QScrollArea`、`QSizePolicy` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- R49-05 `frontend/windows/coding_detail/sections/systems.py` | 复读系统/模块两层结构 Section；确认 `Optional`、`QScrollArea`、`QSizePolicy`、`QMenu`、`QAction` 均无任何实际引用，删除无效导入。

## 第五十轮追加复核

- R50-01 `frontend/windows/coding_detail/sections/architecture.py` | 复读架构设计 Section；确认 `QGridLayout` 导入无任何实际引用，删除无效导入。
- R50-02 `frontend/windows/coding_detail/sections/dependencies.py` | 复读模块依赖 Section；确认 `QGridLayout` 导入无任何实际引用，删除无效导入。
- R50-03 `frontend/windows/coding_detail/sections/directory.py` | 复读目录结构 Section；确认 `Optional`、`QFrame`、`QHeaderView`、`QSizePolicy` 导入均无任何实际引用，删除无效导入。
- R50-04 `frontend/windows/coding_detail/sections/generation.py` | 复读生成管理 Section；确认 `Any` 导入无任何实际引用，删除无效导入。
- R50-05 `frontend/components/virtual_list.py` | 复读虚拟滚动列表组件；确认 `logging`、`Generic`、`Optional`、`QSizePolicy` 导入以及模块级 `logger` 与局部变量 `total_height` 均无任何实际引用，删除无效导入与零引用变量。

## 第五十一轮追加复核

- R51-01 `frontend/pages/home_page/cards.py` | 复读首页卡片组件；确认 `QWidget` 导入无任何实际引用，删除无效导入。
- R51-02 `frontend/pages/home_page/core.py` | 复读首页核心页面；确认 `ImportProgressDialog` 包级导入，以及 `_apply_theme()` 内部重复导入的 `Qt`、`QWidget` 均无任何实际必要，删除冗余导入。
- R51-03 `frontend/utils/lazy_loader.py` | 复读懒加载工具；确认 `QSizePolicy` 导入无任何实际引用，删除无效导入。
- R51-04 `frontend/windows/coding_detail/mixins/header_manager.py` | 复读详情页 Header 管理 mixin；确认 `logging`、`QProgressBar` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- R51-05 `frontend/windows/coding_desk/components/project_info_card.py` | 复读编程工作台项目信息卡片；确认 `logging`、`List` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- R51-06 `frontend/themes/theme_manager/core.py` | 复读主题管理器核心实现；确认 `ConfigManager` 属于 `TYPE_CHECKING` 前向引用导入，供 `set_config_manager()` 注解使用，保留。

## 第五十二轮追加复核

- R52-01 `frontend/windows/writing_desk/header.py` | 复读写作台顶部导航栏；确认 `QWidget` 导入无任何实际引用，删除无效导入。
- R52-02 `frontend/windows/novel_detail/sections/world_setting_section.py` | 复读世界设定 Section；确认 `QScrollArea` 导入无任何实际引用，删除无效导入。
- R52-03 `frontend/windows/novel_detail/dialogs/edit_dialog.py` | 复读通用编辑对话框；确认 `QWidget`、`Any` 导入无任何实际引用，删除无效导入。
- R52-04 `frontend/windows/novel_detail/dirty_tracker.py` | 复读脏数据追踪器；确认 `Optional`、`Tuple` 导入无任何实际引用，删除无效导入。
- R52-05 `frontend/windows/settings/advanced_settings_widget.py` | 复读高级配置界面；确认 `QPushButton`、`QFrame`、`Qt` 导入无任何实际引用，删除无效导入。

## 第五十三轮追加复核

- R53-01 `frontend/windows/settings/max_tokens_settings_widget.py` | 复读 Max Tokens 配置界面；确认 `QPushButton`、`sp` 导入无任何实际引用，删除无效导入。
- R53-02 `frontend/windows/settings/prompt_settings_widget.py` | 复读提示词管理界面；确认 `QStackedWidget` 导入无任何实际引用，删除无效导入。
- R53-03 `frontend/windows/settings/temperature_settings_widget.py` | 复读 Temperature 配置界面；确认 `QPushButton` 导入无任何实际引用，删除无效导入。
- R53-04 `frontend/windows/writing_desk/components/chapter_card.py` | 复读章节卡片组件；确认 `QPoint` 导入无任何实际引用，删除无效导入。
- R53-05 `frontend/windows/writing_desk/dialogs/prompt_preview_dialog.py` | 复读提示词预览对话框；确认 `QFont` 导入无任何实际引用，删除无效导入。

## 第五十四轮追加复核

- R54-01 `frontend-web/src/pages/CodingDetail.tsx` | 复读 Web 编程详情页；按 tab / modal / shared 职责拆分为 6 个子模块，主文件从 1972 行降到 1272 行；并修复架构页“生成模块”误用全局目标系统状态的问题；定点 ESLint 通过。
- R54-02 `frontend-web/src/components/business/MangaPromptViewer.tsx` | 复读漫画提示词查看器；按 progress / summary / details / storyboard / shared 职责拆分为 5 个子模块，主文件从 1702 行降到 1034 行；并清理拆分后残留的 8 个零引用导入；定点 ESLint 通过。
- R54-03 `frontend-web/src/pages/WritingDesk.tsx` | 复读 Web 写作台页面；按 body / editor-workspace / modals / shared 职责拆分为 4 个子模块，主文件从 1447 行降到 1301 行；定点 ESLint 与 `frontend-web npm run build` 均通过，确认拆分未引入类型或打包回归。

## 第五十五轮追加复核

- R55-01 `frontend-web/src/pages/CodingDesk.tsx` | 复读 Web 编程工作台页面；按 header / sidebar / editor-panel / assistant-panel / shared 职责拆分为 5 个子模块，主文件从 1402 行降到 822 行；定点 ESLint 与 `frontend-web npm run build` 均通过，确认拆分未引入类型或打包回归。

## 第五十六轮追加复核

- R56-01 `frontend-web/src/components/business/ProtagonistProfilesModal.tsx` | 复读角色档案工作台弹窗；按 sidebar / workspace / shared 职责拆分为 3 个子模块，主文件从 1394 行降到 679 行；并清理拆分后暴露的无用导入 `Camera` 与 `DETAIL_TABS` 残留；定点 ESLint 与 `frontend-web npm run build` 均通过。

## 第五十七轮追加复核

- R57-01 `frontend-web/src/pages/InspirationChat.tsx` | 复读灵感对话页；按 hero / guide-panel / conversation-panel / workspace / blueprint-preview-modal / shared 职责拆分为 6 个子模块，主文件从 1369 行降到 795 行；补齐 shared 中 JSON 解析辅助函数导出与 ref 类型收口后，定点 ESLint 与 `frontend-web npm run build` 均通过。
- R57-02 `frontend-web/src/components/business/ContentOptimizationView.tsx` | 复读正文优化面板；按 status-card / inline-preview-card / controls-card / thinking-panel / suggestions-panel / preview-modal / shared 职责拆分为 7 个子模块，主文件从 1219 行降到 618 行；同时把段落替换、范围解析、差异计算等纯函数收敛到 shared，避免后续继续积累渲染层死代码；定点 ESLint 与 `frontend-web npm run build` 均通过。

## 第五十八轮追加复核

- R58-01 `frontend-web/src/components/business/settings/ThemeTab.tsx` | 复读主题配置页签；按 sidebar / detail-panel / editor-modal / shared 职责拆分为 4 个子模块，主文件从 1181 行降到 827 行；同时把日期格式化、文件名清洗与编辑 JSON 载荷拼装收敛到 shared，避免主文件继续累积展示层与工具层混写；定点 ESLint 与 `frontend-web npm run build` 均通过。
