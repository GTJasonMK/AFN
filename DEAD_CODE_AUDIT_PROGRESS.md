# 死代码审计进度台账

## 审计目标

- 目标：按文件逐一覆盖仓库，排查并清理可确认的死代码、死文件、未使用导入、无引用工具与遗留实现。
- 日期：2026-03-22
- 执行者：Codex

## 覆盖基线

- 主台账：`DEAD_CODE_AUDIT_FILELIST.tsv`
- 记录方式：逐文件一条记录；已校验 `path` 唯一，无重复条目。
- 当前文件：930 个
- 历史删除记录：6 个已删除死文件，保留在台账中避免重复审计
- 台账总记录：936 条
- 当前文件类型：835 个代码文件，95 个非代码文件
- 状态分布：
  - `reviewed-dead-code-cleaned`：21
  - `reviewed-dead-code-removed`：6
  - `reviewed-no-confirmed-dead-code`：788
  - `reviewed-no-edit-user-dirty`：26
  - `reviewed-noncode`：95
- 排除目录：`.git`、`node_modules`、`dist`、`.venv`、`__pycache__`、`storage`
- 特别说明：存在 26 个用户活动文件，本轮只做死代码审计与引用核对，不直接改写，已在台账中标记为 `reviewed-no-edit-user-dirty`。

## 用户现有改动文件（只审不改）

- `backend/app/api/routers/embedding_config.py`
- `backend/app/api/routers/writer/__init__.py`
- `backend/app/api/routers/writer/chapter_generation.py`
- `backend/app/api/routers/writer/part_outlines.py`
- `backend/app/api/routers/writer/project_workflow.py`
- `backend/app/schemas/model_download.py`
- `backend/app/schemas/project_workflow.py`
- `backend/app/services/chapter_generation/context.py`
- `backend/app/services/chapter_generation/service.py`
- `backend/app/services/chapter_generation/workflow.py`
- `backend/app/services/embedding_config_service.py`
- `backend/app/services/hf_model_download_service.py`
- `backend/app/services/novel_service.py`
- `backend/app/services/part_outline/service.py`
- `backend/app/services/part_outline/workflow.py`
- `frontend-web/electron/main.cjs`
- `frontend-web/src/api/writer.ts`
- `frontend-web/src/components/business/settings/EmbeddingConfigsTab.tsx`
- `frontend-web/src/components/business/settings/components/LocalEmbeddingModelDownloadModal.tsx`
- `frontend-web/src/hooks/useSSE.ts`
- `frontend-web/src/pages/NovelDetail.tsx`
- `frontend-web/src/pages/WritingDesk.tsx`
- `frontend-web/src/pages/novel-detail/useNovelDetailLatestPartOutlineActions.ts`
- `frontend-web/src/pages/novel-detail/useNovelDetailOutlineActions.ts`
- `frontend-web/src/pages/novel-detail/useNovelDetailPartOutlineRegenerate.ts`
- `frontend-web/vite.config.ts`

## 批次状态

- [x] B01 根目录入口与仓库元文件：逐文件登记完成，结果已写入台账。
- [x] B02 后端基础层：完成 `backend/app/core`、`db`、`exceptions.py`、`main.py` 逐文件核对，并清理 `config.py`、`logging_config.py` 死代码。
- [x] B03 后端 API 层：完成 `backend/app/api` 逐文件核对；冲突文件只审计不改动。
- [x] B04 后端数据层：完成 `backend/app/models`、`repositories`、`schemas`、`serializers` 逐文件核对，未确认可安全清理项。
- [x] B05 后端服务与通用工具层：清理 `part_outline_service.py`、`llm_service.py`、`llm_wrappers.py`、`json_utils.py`、`encryption.py`、`text_utils.py`、`sse_helpers.py`。
- [x] B06 后端业务服务层：完成小说写作、分卷分章、人物、漫画、图片相关文件逐项核对；用户活动文件只登记不改。
- [x] B07 后端编码域、启动与脚本：完成 `backend/app/services/coding*`、`backend/scripts`、`backend/startup` 逐文件核对，并清理 `installer.py` 死代码。
- [x] B08 提示词、部署与文本资源：完成 `backend/prompts`、`deploy` 逐文件核对，未确认可安全清理项。
- [x] B09 桌面端基础层：清理 `accessibility.py`、`constants.py`、`formatters.py`、`page_registry.py`、`window_blur.py`。
- [x] B10 桌面端窗口层 A：完成 `frontend/windows/base`、`coding_*`、`inspiration_mode` 逐文件核对，未确认可安全清理项。
- [x] B11 桌面端窗口层 B：删除 `theme_settings_widget.py`，并同步修正 `frontend/windows/settings/__init__.py` 过时说明。
- [x] B12 Web 基础层：清理 `tokens.ts`、`client.ts`、`workflowRollback.ts`、`writingDraft.ts`、`projectRouting.ts`。
- [x] B13 Web 组件层：删除 `CharacterStateView.tsx`、`SettingsInfoBox.tsx`、`SettingsTabHeader.tsx`，并裁剪 `ProjectListItem.tsx` 中无引用实现。
- [x] B14 Web 页面与页面 hooks：清理 `useNovelDetailTabProps.ts` 无引用重导出，其余页面文件逐项核对完成。
- [x] B15 文档、测试与工具：完成 `design-system`、`test`、`tools` 逐文件核对，结果已回填台账。

## 审计记录

- 2026-03-22 初始化：建立批次台账，按模块分批推进。
- 2026-03-22 逐文件覆盖：建立 `DEAD_CODE_AUDIT_FILELIST.tsv`，为 930 个当前文件逐一登记状态，并补录 6 个已删除死文件历史记录。
- 2026-03-22 第一轮清理：删除 6 个零入口死文件；移除 `get_embedding_dimension()`、`repair_truncated_json()`、`escape_inner_quotes()`；同步修正文档说明。
- 2026-03-22 第二轮清理：处理 `encryption.py`、`llm_wrappers.py`、`text_utils.py`、`sse_helpers.py`、`installer.py`、`accessibility.py`、`constants.py`、`formatters.py`、`client.ts`、`workflowRollback.ts`、`writingDraft.ts`、`useNovelDetailTabProps.ts`、`ProjectListItem.tsx`、`projectRouting.ts`。
- 2026-03-22 第三轮清理：处理 `window_blur.py`、`page_registry.py`、`config.py`、`logging_config.py`、`json_utils.py` 新确认的死代码。
- 2026-03-22 最终复核：确认台账路径无重复；保留用户活动文件的只审不改标记，避免遗漏和重复清理。

## 已确认并处理的死代码

- `backend/app/services/part_outline_service.py`：删除。仓库内无模块级导入，属于拆分后遗留兼容 shim。
- `frontend/windows/settings/theme_settings_widget.py`：删除。桌面端旧主题设置入口，无运行时导入。
- `frontend-web/src/components/business/CharacterStateView.tsx`：删除。组件入度为 0。
- `frontend-web/src/components/business/settings/components/SettingsInfoBox.tsx`：删除。组件入度为 0。
- `frontend-web/src/components/business/settings/components/SettingsTabHeader.tsx`：删除。组件入度为 0。
- `frontend-web/src/theme/tokens.ts`：删除。主题令牌文件无引用。
- `backend/app/services/llm_service.py`：移除未引用兼容方法 `get_embedding_dimension()`。
- `backend/app/utils/json_utils.py`：移除未引用函数 `repair_truncated_json()`、`escape_inner_quotes()`、`normalize_number_display()`。
- `backend/app/utils/encryption.py`：移除未引用辅助函数 `is_encrypted()`。
- `backend/app/services/llm_wrappers.py`：移除未引用辅助函数 `build_conversation_history()`。
- `backend/app/utils/text_utils.py`：移除未引用辅助函数 `safe_slice()`。
- `backend/app/utils/sse_helpers.py`：移除未引用辅助函数 `sse_message()`、`sse_comment()`。
- `backend/startup/installer.py`：移除未引用辅助函数 `_load_previous_requirements()`、`_save_current_requirements()`。
- `backend/app/core/config.py`：移除未引用函数 `reload_settings()`。
- `backend/app/core/logging_config.py`：移除未引用函数 `set_domain_level()`、`get_domain_level()`、`get_logger()`。
- `frontend/themes/accessibility.py`：移除未引用类 `KeyboardShortcuts`、`ARIALabels`。
- `frontend/utils/constants.py`：移除未引用类 `APIConstants`、`ConversationConstants`。
- `frontend/utils/formatters.py`：移除未引用函数 `get_chapter_status_text()`、`get_status_badge_style()`。
- `frontend/utils/window_blur.py`：移除未引用函数 `_safe_dwm_call()`。
- `frontend/utils/page_registry.py`：移除未引用函数 `get_registered_page_types()`。
- `frontend-web/src/api/client.ts`：移除未引用接口 `ApiResponse`。
- `frontend-web/src/utils/workflowRollback.ts`：移除未引用类型 `WorkflowRollbackTargetStatus`。
- `frontend-web/src/utils/writingDraft.ts`：移除未引用函数 `hasWritingDraft()`。
- `frontend-web/src/pages/novel-detail/useNovelDetailTabProps.ts`：移除未引用 `NovelDetailTabSources` 重导出。
- `frontend-web/src/components/business/ProjectListItem.tsx`：删除未使用项目卡片组件实现，仅保留 `ProjectListItemModel` 类型定义。
- `frontend-web/src/utils/projectRouting.ts`：移除未引用函数 `getProjectSecondaryEntryRoute()`、`getProjectSecondaryEntryLabel()`。

## 同步修正

- `frontend/windows/settings/__init__.py`：移除对已删除兼容入口的过时目录说明。

## 验证结果

- 已通过：`python3 -m py_compile backend/app/core/config.py backend/app/core/logging_config.py backend/app/services/llm_service.py backend/app/services/llm_wrappers.py backend/app/utils/encryption.py backend/app/utils/json_utils.py backend/app/utils/sse_helpers.py backend/app/utils/text_utils.py backend/startup/installer.py frontend/themes/accessibility.py frontend/utils/constants.py frontend/utils/formatters.py frontend/utils/page_registry.py frontend/utils/window_blur.py frontend/windows/settings/__init__.py`
- 已通过：`cd frontend-web && npm run lint`
- 已通过：`cd frontend-web && npm run build`
- `ts-prune` 复核结果：只剩 `frontend-web/src/vite-env.d.ts` 中 `ImportMeta` 环境声明误报，已判定不继续清理。
