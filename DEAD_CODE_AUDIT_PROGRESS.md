# 死代码审计进度台账

## 本轮目标

- 目标：基于当前干净代码库，重新完成一轮逐文件死代码复核。
- 范围：`git ls-files` 当前受管文件。
- 日期：2026-03-22
- 执行者：Codex

## 覆盖基线

- 基线文件总数：925
- 文件类型统计：代码 835，文本 82，二进制 8
- 主台账：`DEAD_CODE_AUDIT_FILELIST.tsv`
- 过程日志：`DEAD_CODE_AUDIT_REVIEW_LOG.md`
- 当前结果统计：
  - `reviewed-dead-code-cleaned`：236
  - `reviewed-dead-code-removed`：2
  - `reviewed-no-confirmed-dead-code`：597
  - `reviewed-noncode`：90
- 特别说明：本轮台账按基线 925 个文件建立；审计过程中确认并删除了 `backend/app/schemas/config.py` 与 `backend/app/utils/text_utils.py`，因此当前工作树实际源码文件数比基线少 2。

## 执行过程

- 已按基线顺序逐文件读取并记录，共回填 925 条首轮阅读记录。
- 首轮阅读过程已写入 `DEAD_CODE_AUDIT_REVIEW_LOG.md`，每条记录包含文件序号、路径、行数和首轮结论。
- 在全量逐文件阅读之后，补充执行高置信零引用扫描。
- Python 顶层零引用候选先收敛出 65 项，再逐文件人工复核。
- 首轮清理完成后继续执行第二轮低引用候选复核，重点回查 `utils`、`themes`、`desktop frontend` 公共模块以及误报较多的依赖注入/导出路径。
- 第二轮复核过程已追加写入 `DEAD_CODE_AUDIT_REVIEW_LOG.md`，逐条记录“文件 -> 结论 -> 是否清理/保留”。

## 审计结果

- 已确认并清理 236 个当前文件中的死代码。
- 已确认并删除 2 个整文件死文件：`backend/app/schemas/config.py`、`backend/app/utils/text_utils.py`。
- 累计移除 920 个零引用符号/无效导入、1 个未使用私有参数和 2 个零引用文件。
- 第二轮新增死代码分布在后端工具层、图片/漫画服务层，以及桌面端 `utils` / `themes` 公共模块。
- 第三轮新增死代码集中在后端 API 关联的遗留 schema，请求/查询模型“仅定义 + 仅被无效 import”是本轮主要来源。
- 第四轮新增清理集中在后端 service 层的历史残留无效 import，属于“定义仍存在，但当前文件已完全不再使用”的死代码。
- 第五轮新增清理集中在上一轮联动删 import 后暴露出的孤立常量/函数，属于“曾被使用，但当前仓库已无任何调用点”的残余死代码。
- 第六轮新增清理集中在 API 路由层的历史残留无效导入，属于“文件业务仍活跃，但 import 已失效”的死代码。
- 第七轮继续沿 API 路由层补扫无效导入，并开始记录静态扫描误报，避免后续重复误判。
- 第八轮继续深挖复杂路由文件，清理多项聚集出现的无效导入，说明路由层历史演进留下的死代码仍较多。
- 第九轮从基础模型、仓储、schema、服务层继续补扫无效导入，说明死代码并不只集中在路由层。
- 第十轮继续清理服务层与流程编排层的无效导入，`TYPE_CHECKING` 残留和历史兼容导入开始成为新来源。
- 第十一轮进一步深入 `protagonist_profile`、`rag`、`utils` 与基础服务模块，说明横向工具层也累积了不少零引用导入。
- 第十二轮开始收尾仓储层与剩余中等复杂服务模块，并显式记录静态扫描误报的局部导入场景。
- 第十三轮进入序列化层与章节生成核心链路，开始清理前向引用保留后遗留的 `TYPE_CHECKING` 空分支和兼容导入。
- 第十四轮继续攻克中高复杂度服务模块，特别是 `coding_files/architect` 与章节评估链路中的残余无效导入。
- 第十五轮继续清理剩余中等复杂服务模块，并开始把“模块导出用途的保留项”单独标注，避免与普通无效导入混淆。
- 第十六轮转入 `manga_prompt` 与主题配置链路，继续收掉首轮扫描后残留的高置信无效导入，并补记 `TYPE_CHECKING` 保留项。
- 第十七轮继续顺着包导出链与默认单例工厂回查，集中清理 `chapter_generation`、`rag`、`rag_common`、`coding_rag`、`novel_rag` 中“定义已失效 + `__init__` 仍残留导出”的历史死代码。
- 第十八轮回到桌面端主题与工具公共层，继续清理“单文件内部可见、但全仓无调用”的便捷函数/单例壳，以及它们在 `__init__.py` 中残留的转发导出。
- 第十九轮继续沿桌面端公共包装层回查，重点清理 `components` / `message_service` 这类“类方法仍存活，但顶层便捷包装已无人使用”的薄封装死代码。
- 第二十轮继续沿“便捷函数 + 包级转发”链路回查，收掉 `manga_prompt` 服务层的历史包装入口，以及前端 `svg_icons.py` 中未被导出的孤立便捷函数。
- 第二十一轮继续深挖同文件残留的顶层便捷包装，确认 `modern_effects.py` 中除已删除 `transition()` 外，还遗留 `gradient()`、`shadow()` 两个零调用壳函数。
- 第二十二轮转回后端基础服务层，继续清理“之前已清过一次的文件中残留的第二批死代码”，以及真正无人使用的测试辅助接口。
- 第二十三轮继续顺着自动入库链回查“闭包返回值赋给模块变量、但当前仓库没有任何外部导入”的死导出，集中清理 `coding_rag` / `novel_rag` 的残留包级 API 面。
- 第二十四轮切到后端聚合包导出层，清理 `import_analysis/__init__.py` 中“子模块内部自用，但包级 API 已无人导入”的历史转发导出。
- 第二十五轮继续横向清理基础聚合包 `rag_common/__init__.py` 中一整组无人导入的函数级转发导出，进一步压缩无效 API 面。
- 第三十二轮继续深入桌面端基础聚合层，集中清理 `frontend/api`、`components`、`pages`、`themes` 中“包入口仍存在，但大部分历史转发导出已无人导入”的残留 API 面。
- 第三十三轮继续在桌面端组件聚合层做符号级收口，移除 `dialogs` 与 `writing_desk/optimization` 中仅剩定义和内部实现、但再无任何包级导入点的残留导出。
- 第三十四轮继续细化桌面端输入组件聚合层，移除 `components.inputs` 中只作为内部实现存在、但不应暴露为包级 API 的 `SwitchControl`。
- 第三十五轮继续处理桌面端历史模型包，确认 `frontend/models/__init__.py` 整组数据类与状态转发在当前仓库完全无引用后，收缩为空包入口。
- 第三十六轮继续清理桌面端历史模型模块，确认 `frontend/models/project_status.py` 的前端状态枚举实现已完全脱离现有代码路径后，收缩为空占位模块。
- 第三十七轮回到后端基础聚合层，确认 `backend/app/serializers/__init__.py` 仅剩历史转发壳后，移除零包级引用的 `NovelSerializer` 导出。
- 第三十八轮继续收缩后端主题默认值聚合层，移除 `theme_defaults/__init__.py` 中仅供子模块内部使用、但未被任何包级调用依赖的四个默认值常量导出。
- 第三十九轮继续收缩图片生成服务聚合层，移除 `image_generation/__init__.py` 中已改走子模块直连的 PDF 导出与 Provider 类型残留导出。
- 第四十轮转回根脚本 `setup_env.py`，基于 AST 与全文检索双重确认，移除 15 个从 `backend.startup` 导入但当前脚本完全未引用的无效导入。
- 第四十一轮顺着上一轮继续收口启动包入口，移除 `backend/startup/__init__.py` 中已经没有任何包级消费者的 15 个历史转发导出，仅保留 `setup_env.py` 实际依赖的启动接口。
- 第四十二轮继续沿根脚本补扫，确认 `run_app.py` 中 `Path`、`WORK_DIR`、`BACKEND_VENV`、`FRONTEND_VENV`、`print_banner` 五项导入均无实际引用后，删除无效导入。
- 第四十三轮继续深入启动子模块，基于 AST 与全文检索确认 `animation.py`、`installer.py`、`port_utils.py`、`uv_manager.py` 中共 6 项导入为零引用残留并完成清理。
- 第四十四轮回到 RAG 与优化链路，按真实包级消费名单继续收缩 `coding_rag`、`novel_rag` 两个服务包，并同步清理 `fix_real_summary.py`、`content_optimization/agent.py`、`coding_rag/auto_ingestion.py`、两个 `ingestion_service.py` 中确认无任何调用的残留导入/导出。
- 第四十五轮继续做实现文件与服务包入口的二次精扫，新增清理 4 个真实零引用导入，并继续收缩 `chapter_generation`、`content_optimization` 的历史聚合导出；同时按 `DEAD_CODE_AUDIT_FILELIST.tsv` 重算并修正顶层摘要统计。
- 第四十六轮继续沿服务聚合包回查，新增收缩 `import_analysis`、`rag`、`rag_common` 的第二批零包级引用导出，并同步修正文档示例中的过期包级导入路径。
- 第四十七轮切到桌面端前端实现文件，集中清理一批 PyQt 组件与工具模块中的零引用导入，说明前端代码层仍有较多“首轮人工阅读未显式暴露、但二次 AST 补扫可稳定确认”的低风险死代码。
- 第四十八轮继续深入桌面端前端主题与工作台基础层，既补清多个实现文件中的零引用导入，也继续收缩 `frontend/utils` 这种当前已无任何包级消费者的历史聚合入口。
- 第四十九轮继续深入桌面端 `coding_detail/sections` 细部实现，新增清理 5 个文件中的零引用导入与零引用 `logger`，说明详情页分区组件仍存在一批低风险历史残留。
- 第五十轮继续沿 `coding_detail/sections` 与前端通用组件补扫，新增清理 5 个实现文件中的零引用导入，并额外移除 `virtual_list.py` 中一个未使用局部变量。
- 第五十一轮转到首页、懒加载工具、详情页 mixin 与编程工作台卡片组件，新增清理 5 个实现文件中的 11 个零引用符号，并补记 `theme_manager/core.py` 的 `TYPE_CHECKING` 保留结论。
- 第五十二轮转到小说详情页、设置页与写作台头部组件，新增清理 5 个实现文件中的零引用导入，说明桌面端较早期 UI 模块中仍有一批单点残留。
- 第五十三轮继续清理设置页与写作台组件中的单点残留导入，新增清理 5 个实现文件，说明桌面端配置页存在较多“组件演进后未回收的 import 噪音”。

## 大型文件可读性治理进度

- 日期：2026-03-25
- 目标：继续对前端超大文件做职责拆分，降低单文件复杂度，并顺手清理拆分后暴露出的死代码。
- 已完成：
  - `frontend-web/src/pages/CodingDetail.tsx`
    主文件由 1972 行降到 1272 行，已拆出 overview / architecture / directory / generation / modals / shared 六个子模块；并修复架构页“生成模块”错误依赖全局目标系统状态的问题。
  - `frontend-web/src/components/business/MangaPromptViewer.tsx`
    主文件由 1702 行降到 1034 行，已拆出 progress / summary / details / storyboard / shared 五个子模块；并清理主文件中 8 个拆分后失效的无用导入。
  - `frontend-web/src/pages/WritingDesk.tsx`
    主文件由 1447 行降到 1301 行，已拆出 body / editor-workspace / modals / shared 四个子模块；页面主文件现在主要保留状态、请求、工作流门禁与章节操作逻辑。
  - `frontend-web/src/pages/CodingDesk.tsx`
    主文件由 1402 行降到 822 行，已拆出 header / sidebar / editor-panel / assistant-panel / shared 五个子模块；页面主文件现在主要保留状态、SSE、RAG 与目录规划 Agent 控制逻辑。
  - `frontend-web/src/components/business/ProtagonistProfilesModal.tsx`
    主文件由 1394 行降到 679 行，已拆出 sidebar / workspace / shared 三个子模块；主文件现在主要保留数据请求、操作流转与统计状态。
  - `frontend-web/src/pages/InspirationChat.tsx`
    主文件由 1369 行降到 795 行，已拆出 hero / guide-panel / conversation-panel / workspace / blueprint-preview-modal / shared 六个子模块；主文件现在主要保留对话流、蓝图生成与 SSE 状态编排逻辑。
  - `frontend-web/src/components/business/ContentOptimizationView.tsx`
    主文件由 1219 行降到 618 行，已拆出 status-card / inline-preview-card / controls-card / thinking-panel / suggestions-panel / preview-modal / shared 七个子模块；主文件现在主要保留优化会话状态、SSE 编排与编辑器交互逻辑。
  - `frontend-web/src/components/business/settings/ThemeTab.tsx`
    主文件由 1181 行降到 827 行，已拆出 sidebar / detail-panel / editor-modal / shared 四个子模块；主文件现在主要保留主题配置列表状态、接口动作、外观 Footer 注入与编辑流程编排。
- 验证记录：
  - `frontend-web/src/pages/CodingDetail.tsx` 相关拆分文件已通过定点 ESLint。
  - `frontend-web/src/components/business/MangaPromptViewer.tsx` 与 `frontend-web/src/components/business/manga-prompt-viewer/*.tsx` 已通过定点 ESLint。
  - `frontend-web/src/pages/WritingDesk.tsx` 与 `frontend-web/src/pages/writing-desk/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web/src/pages/CodingDesk.tsx` 与 `frontend-web/src/pages/coding-desk/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web/src/components/business/ProtagonistProfilesModal.tsx` 与 `frontend-web/src/components/business/protagonist-profiles-modal/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web/src/pages/InspirationChat.tsx` 与 `frontend-web/src/pages/inspiration-chat/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web/src/components/business/ContentOptimizationView.tsx` 与 `frontend-web/src/components/business/content-optimization/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web/src/components/business/settings/ThemeTab.tsx` 与 `frontend-web/src/components/business/settings/theme-tab/*.tsx`、`shared.ts` 已通过定点 ESLint。
  - `frontend-web` 已执行 `npm run build`，本轮拆分后的 `WritingDesk` 相关改动通过 TypeScript 与 Vite 构建验证。
  - `frontend-web` 已再次执行 `npm run build`，本轮拆分后的 `CodingDesk` 相关改动通过 TypeScript 与 Vite 构建验证。
  - `frontend-web` 已再次执行 `npm run build`，本轮拆分后的 `ProtagonistProfilesModal` 相关改动通过 TypeScript 与 Vite 构建验证。
  - `frontend-web` 已再次执行 `npm run build`，本轮拆分后的 `InspirationChat` 与 `ContentOptimizationView` 相关改动通过 TypeScript 与 Vite 构建验证。
  - `frontend-web` 已再次执行 `npm run build`，本轮拆分后的 `ThemeTab` 相关改动通过 TypeScript 与 Vite 构建验证。
- 下一批候选（按当前行数排序）：
  - `frontend-web/src/pages/WritingDesk.tsx` 1301 行（仍偏大，后续可继续把章节操作 / 草稿恢复 / 生成门禁抽到 hook）
  - `frontend-web/src/pages/CodingDetail.tsx` 1272 行（仍偏大，后续可继续把流程控制或数据适配层抽到 hook / service）
  - `frontend-web/src/components/business/MangaPromptViewer.tsx` 1034 行
  - `frontend-web/src/pages/AdminUsers.tsx` 1012 行
  - `frontend-web/src/pages/CodingDesk.tsx` 822 行（已进入可维护范围，后续可考虑把 Agent SSE 控制再抽成 hook）
  - `frontend-web/src/pages/InspirationChat.tsx` 795 行（已进入可维护范围，后续可考虑把对话编排抽成 hook）

## 已处理清单

- `backend/app/api/routers/writer/character_state.py`
  移除 `CharacterStateResponse`。
- `backend/app/core/constants.py`
  移除 `VectorConstants`、`HTTPConstants`、`ChapterConstants`。
- `backend/app/core/dependencies.py`
  移除 `get_chapter_generation_service()`。
- `backend/app/core/state_validators.py`
  移除 `PART_OUTLINE_STATES`、`WRITING_STATES`，以及 `require_outline_generation_status()`、`require_chapter_generation_status()`、`require_part_outline_status()`、`require_blueprint_edit_status()`、`is_in_writing_phase()`、`is_completed()`、`can_generate_outlines()`、`can_generate_chapters()`。
- `backend/app/exceptions.py`
  移除 `VectorStoreError`、`DailyLimitExceededError`。
- `backend/app/schemas/character_portrait.py`
  移除 `CharacterPortraitBase`。
- `backend/app/schemas/coding.py`
  移除 `CodingChoiceOption`、`CodingUIControl`、`CodingConverseResponse`、`CodingConverseRequest`、`CodingBlueprintGenerationResponse`、`CodingBlueprintRefineRequest`、`GenerateCodingSystemsRequest`、`GenerateCodingModulesRequest`。
- `backend/app/schemas/coding_files.py`
  移除 `FileGenerationStatus`、`DirectoryGenerationStatus`、`DirectoryNodeBase`、`SourceFileBase`、`BatchGenerateDirectoryRequest`、`GenerateFilePromptResponse`、`GenerateReviewPromptResponse`。
- `backend/app/schemas/config.py`
  整文件零引用，已删除。
- `backend/app/schemas/llm_config.py`
  移除 `LLMConfigImportRequest`、`LLMConfigTestRequest`。
- `backend/app/schemas/novel.py`
  移除 `PartKeyEvent`、`PartConflict`、`ChapterGenerationResponse`、`GenerateOutlineRequest`。
- `backend/app/schemas/protagonist.py`
  移除 `ClassificationResult`、`ChangeHistoryQuery`、`BehaviorRecordQuery`、`DeletionMarkQuery`、`ImplicitStatsQuery`。
- `backend/app/schemas/theme_config.py`
  移除 `PrimaryColorsSchema`、`AccentColorsSchema`、`SemanticColorsSchema`、`TextColorsSchema`、`BackgroundColorsSchema`、`BorderEffectsSchema`、`ButtonColorsSchema`、`TypographySchema`、`BorderRadiusSchema`、`SpacingSchema`、`AnimationSchema`、`ButtonSizesSchema`。
- `backend/app/services/content_optimization/schemas.py`
  移除 `SuggestionCategory`、`WorkflowStartEvent`、`WorkflowCompleteEvent`、`WorkflowPausedEvent`、`PlanReadyEvent`、`ParagraphStartEvent`、`ParagraphCompleteEvent`、`ThinkingEvent`、`ActionEvent`、`ObservationEvent`、`ErrorEvent`。
- `backend/app/services/image_generation/schemas.py`
  移除 `ImageStyle`、`QualityPreset`、`SUPPORTED_MODELS`、`STYLE_DETECTION_KEYWORDS`、`has_style_keywords()`。
- `backend/app/services/manga_prompt/prompt_builder/page_prompt_generator.py`
  移除 `SHOT_TYPE_CHINESE`。
- `backend/app/services/coding_files/directory_agent/evaluator.py`
  移除 `OverallEvaluation`。
- `backend/app/services/rag/context_compressor.py`
  移除 `AdaptiveCompressor`。
- `backend/app/services/rag/query_builder.py`
  移除 `EntityAwareQueryEnhancer`。
- `backend/app/services/rag/temporal_retriever.py`
  移除 `NearbyChapterPrioritizer`。
- `backend/app/services/rag/utils.py`
  移除 `format_rag_summary_line()`。
- `backend/app/utils/blueprint_utils.py`
  移除 `extract_blueprint_characters()`、`extract_world_setting()`、`extract_full_synopsis()`、`build_blueprint_info_dict()`。
- `backend/app/utils/exception_helpers.py`
  移除 `convert_to_http_exception()`、`ExceptionContext`、`format_exception_chain()`。
- `backend/app/utils/json_utils.py`
  移除 `fix_number_format()`、`format_number_chinese()`、`format_number_western()`。
- `backend/app/utils/prompt_include.py`
  移除 `PromptFrontmatter`。
- `frontend/themes/svg_icons.py`
  移除 `SVGIconWidget`。
- `frontend/utils/__init__.py`
  同步移除无效导出 `PoolManager`、`get_pool`。
- `frontend/utils/component_pool.py`
  移除 `PoolManager`、`get_pool()`。
- `frontend/utils/constants.py`
  移除 `UIConstants`、`PageConstants`、`ChapterConstants`。
- `frontend/utils/error_handler.py`
  移除 `handle_api_errors()`。
- `frontend/utils/page_registry.py`
  移除 `register_page()`、`_page_registry`，并删去对应无效分支。

## 第三轮追加清理

- `backend/app/api/routers/llm_config.py`
  同步移除无效导入 `LLMConfigTestRequest`。
- `backend/app/api/routers/protagonist.py`
  同步移除无效导入 `ChangeHistoryQuery`、`BehaviorRecordQuery`、`DeletionMarkQuery`、`ImplicitStatsQuery`。

## 第四轮追加清理

- `backend/app/services/character_portrait_service.py`
  移除无效导入 `CharacterPortraitResponse`。
- `backend/app/services/coding_files/directory_service.py`
  移除无效导入 `SourceFileResponse`。
- `backend/app/services/content_optimization/service.py`
  移除无效导入 `OptimizationMode`。
- `backend/app/services/content_optimization/workflow.py`
  移除无效导入 `CheckDimension`、`OptimizationMode`、`RAGContext`。
- `backend/app/services/image_generation/providers/base.py`
  移除无效导入 `has_style_keywords`。
- `backend/app/services/rag/context_builder.py`
  移除无效导入 `CharacterState`、`ForeshadowingData`。
- `backend/app/services/rag/query_builder.py`
  移除无效导入 `ForeshadowingItem`。

## 第五轮追加清理

- `backend/app/services/image_generation/schemas.py`
  基于复扫确认 `has_style_keywords()` 与 `STYLE_DETECTION_KEYWORDS` 已无任何调用，删除。

## 第六轮追加清理

- `backend/app/api/routers/llm_config.py`
  移除无效导入 `AsyncSession`、`get_session`。
- `backend/app/api/routers/coding/projects.py`
  移除无效导入 `Optional`。
- `backend/app/api/routers/inspiration_router_registry.py`
  移除无效导入 `Callable`。
- `backend/app/api/routers/image_generation.py`
  移除无效导入 `Path`。
- `backend/app/api/routers/novels/outlines.py`
  移除无效导入 `PromptTemplateNotFoundError`。
- `backend/app/api/routers/coding/files_plan_v2.py`
  移除无效导入 `Any`、`Dict`、`Tuple`。
- `backend/app/api/routers/writer/chapter_generation.py`
  移除无效导入 `Dict`。
- `backend/app/api/routers/writer/manga_prompt_v2.py`
  移除无效导入 `MangaStyle`。

## 第七轮追加清理

- `backend/app/api/routers/character_portrait.py`
  移除无效导入 `ResourceNotFoundError`。
- `backend/app/api/routers/novels/export.py`
  移除无效导入 `AsyncSession`、`get_session`。
- `backend/app/api/routers/novels/import_analysis.py`
  移除无效导入 `ResourceNotFoundError`。
- `backend/app/api/routers/writer/part_outlines.py`
  移除无效导入 `asyncio`、`ProjectStatus`。
- `backend/app/api/routers/writer/rag_query.py`
  移除无效导入 `RetrievedChunk`、`RetrievedSummary`。

## 第八轮追加清理

- `backend/app/api/routers/coding/rag.py`
  移除无效导入 `CompletenessReport`。
- `backend/app/api/routers/novels/blueprints.py`
  移除无效导入 `Any`、`Dict`、`List`、`PromptTemplateNotFoundError`、`PartOutline`、`ChapterOutline`、`PartOutlineRepository`、`ChapterIngestionService`。
- `backend/app/api/routers/writer/chapter_management.py`
  移除无效导入 `settings`、`remove_think_tags`。
- `backend/app/api/routers/writer/chapter_outlines.py`
  移除无效导入 `List`、`PromptTemplateNotFoundError`、`sse_complete_event`、`sse_error_event`、`track_saved_items`。

## 第九轮追加清理

- `backend/app/models/theme_config.py`
  移除无效导入 `Text`。
- `backend/app/models/user.py`
  移除无效导入 `ForeignKey`、`Optional`。
- `backend/app/repositories/base.py`
  移除无效导入 `Union`。
- `backend/app/repositories/blueprint_repository.py`
  移除无效导入 `Iterable`。
- `backend/app/repositories/coding_files_repository.py`
  移除无效导入 `AsyncSession`。
- `backend/app/repositories/coding_repository.py`
  移除无效导入 `AsyncSession`。
- `backend/app/repositories/prompt_repository.py`
  移除无效导入 `AsyncSession`。
- `backend/app/schemas/embedding_config.py`
  移除无效导入 `datetime`。
- `backend/app/schemas/llm_config.py`
  移除无效导入 `HttpUrl`、`datetime`。
- `backend/app/services/avatar_service.py`
  移除无效导入 `Tuple`。
- `backend/app/services/blueprint_service.py`
  移除无效导入 `json`。

## 第十轮追加清理

- `backend/app/services/chapter_generation/prompt_builder.py`
  移除无效导入 `json`。
- `backend/app/services/chapter_generation/workflow.py`
  移除无效导入 `TYPE_CHECKING`、`AsyncSession`、`LLMService`。
- `backend/app/services/chapter_version_service.py`
  移除无效导入 `TYPE_CHECKING`、`LLMService`。
- `backend/app/services/character_portrait_service.py`
  移除无效导入 `ImageConfigService`、`base64`、`hashlib`、`httpx`。
- `backend/app/services/embedding_config_service.py`
  移除无效导入 `InvalidParameterError`。
- `backend/app/services/hf_model_download_service.py`
  移除无效导入 `asyncio`。
- `backend/app/services/image_generation/providers/comfyui.py`
  移除无效导入 `Optional`。
- `backend/app/services/image_generation/service.py`
  移除无效导入 `shutil`。
- `backend/app/services/import_analysis/progress_tracker.py`
  移除无效导入 `List`。

## 第十一轮追加清理

- `backend/app/services/llm_config_service.py`
  移除无效导入 `InvalidParameterError`。
- `backend/app/services/project_factory.py`
  移除无效导入 `Optional`。
- `backend/app/services/prompt_service.py`
  移除无效导入 `Tuple`、`re`。
- `backend/app/services/protagonist_profile/analysis_service.py`
  移除无效导入 `Optional`。
- `backend/app/services/protagonist_profile/implicit_tracker.py`
  移除无效导入 `Optional`。
- `backend/app/services/protagonist_profile/service.py`
  移除无效导入 `datetime`。
- `backend/app/services/protagonist_profile/sync_service.py`
  移除无效导入 `Any`、`Optional`、`json`。
- `backend/app/services/rag/context_builder.py`
  移除无效导入 `build_outline_text`。
- `backend/app/services/rag/context_compressor.py`
  移除无效导入 `re`。
- `backend/app/services/rag/temporal_retriever.py`
  移除无效导入 `Optional`、`field`。
- `backend/app/services/rag_common/ingestion_base.py`
  移除无效导入 `Sequence`。
- `backend/app/services/rag_common/semantic_chunker.py`
  移除无效导入 `math`。
- `backend/app/utils/blueprint_utils.py`
  移除无效导入 `List`、`Optional`。
- `backend/app/utils/content_normalizer.py`
  移除无效导入 `re`。
- `backend/app/utils/llm_tool.py`
  移除无效导入 `LLMRequestLogger`、`fix_base_url`。

## 第十二轮追加清理

- `backend/app/repositories/chapter_outline_repository.py`
  移除无效导入 `delete`、`func`。
- `backend/app/repositories/protagonist_repository.py`
  移除无效导入 `Any`、`AsyncSession`。
- `backend/app/services/coding_rag/auto_ingestion.py`
  移除无效导入 `CodingDataType`。
- `backend/app/services/content_optimization/tool_executor.py`
  移除无效导入 `Sequence`。
- `backend/app/services/content_optimization/workflow.py`
  移除无效导入 `List`。
- `backend/app/services/foreshadowing_service.py`
  移除无效导入 `Chapter`。

## 第十三轮追加清理

- `backend/app/serializers/coding_serializer.py`
  移除无效导入 `CodingBlueprintModel`、`Dict`、`List`、`json`。
- `backend/app/services/chapter_generation/context.py`
  移除无效导入 `TYPE_CHECKING`、`BlueprintInfo`、`ChapterRAGContext`、`EnhancedRAGContext`。
- `backend/app/services/chapter_generation/service.py`
  移除无效导入 `TYPE_CHECKING`、`Union`、`unwrap_markdown_json`、`BlueprintInfo`、`ChapterRAGContext`、`EnhancedRAGContext`、`VectorStoreService`。
- `backend/app/services/coding_files/directory_service.py`
  移除无效导入 `List`。

## 第十四轮追加清理

- `backend/app/services/chapter_evaluation_service.py`
  移除无效导入 `settings`、`LLMConstants`、`ChapterOutline`、`TYPE_CHECKING`、`LLMService`、`VectorStoreService`。
- `backend/app/services/coding_files/architect/decision_maker.py`
  移除无效导入 `Any`、`Dict`。
- `backend/app/services/coding_files/architect/generator.py`
  移除无效导入 `ArchitecturePattern`、`Optional`、`Tuple`。
- `backend/app/services/coding_files/architect/patterns.py`
  移除无效导入 `field`。
- `backend/app/services/coding_files/architect/profiler.py`
  移除无效导入 `ArchitecturePattern`、`Set`。
- `backend/app/services/coding_files/architect/quality_evaluator.py`
  移除无效导入 `Any`、`Optional`。
- `backend/app/services/coding_files/architect/refiner.py`
  移除无效导入 `ArchitecturePattern`、`StructureIssue`。
- `backend/app/services/coding_files/architect/schemas.py`
  移除无效导入 `Set`。
- `backend/app/services/coding_files/directory_agent/agent.py`
  移除无效导入 `Optional`、`ToolCall`。

## 第十五轮追加清理

- `backend/app/services/coding_files/file_prompt/review.py`
  移除无效导入 `Any`、`CodingSourceFile`。
- `backend/app/services/coding_rag/ingestion_service.py`
  移除无效导入 `AsyncSession`、`BLUEPRINT_INGESTION_TYPES`、`CodingFileVersion`、`CodingProject`、`Set`。
- `backend/app/services/content_optimization/agent.py`
  移除无效导入 `Any`、`ToolCall`。
- `backend/app/services/image_generation/pdf_export.py`
  移除无效导入 `Any`、`ChapterMangaPrompt`。
- `backend/app/services/image_generation/providers/openai_compatible.py`
  移除无效导入 `Any`、`httpx`。

## 第十六轮追加清理

- `backend/app/services/manga_prompt/core/page_prompt_builder.py`
  移除无效导入 `List`。
- `backend/app/services/manga_prompt/storyboard/models.py`
  移除无效导入 `Any`。
- `backend/app/services/theme_config_service.py`
  移除无效导入 `Any`、`LIGHT_THEME_DEFAULTS`、`DARK_THEME_DEFAULTS`、`LIGHT_THEME_V2_DEFAULTS`、`DARK_THEME_V2_DEFAULTS`。
- `backend/app/services/manga_prompt/extraction/chapter_info_extractor.py`
  移除无效导入 `CharacterRole`、`ImportanceLevel`、`EmotionType`、`EventType`、`PROMPT_NAME`、`EXTRACTION_SYSTEM_PROMPT`，并删除零调用私有方法 `_build_prompt()`、`_get_system_prompt()`、`_parse_chapter_info()`。
- `backend/app/services/manga_prompt/planning/page_planner.py`
  移除 `_simple_plan()` 的未使用私有参数 `min_pages`，并同步收紧调用点。
- `backend/app/services/manga_prompt/storyboard/designer.py`
  移除无效导入 `DialogueBubble`、`PanelShape`、`ShotType`、`WidthRatio`、`AspectRatio`。
- `backend/app/services/inspiration_service.py`
  移除无效导入 `NovelConversation`、`CodingConversation`、`Optional`。
- `backend/app/services/part_outline/chapter_outline_workflow.py`
  移除无效导入 `log_exception`。
- `backend/app/services/part_outline/service.py`
  移除无效导入 `Any`、`Dict`、`TYPE_CHECKING`、`PartOutlineParser`、`PartOutlineModelFactory`、`ChapterOutlineWorkflow`，并删除空 `TYPE_CHECKING` 分支。
- `backend/app/services/novel_rag/ingestion_service.py`
  移除无效导入 `AsyncSession`、`BLUEPRINT_INGESTION_TYPES`、`ChapterVersion`、`NovelProject`、`Set`、`Union`、`func`。
- `backend/app/repositories/chapter_repository.py`
  移除无效导入 `delete`、`ChapterVersion`、`ChapterEvaluation`、`ChapterOutline`。
- `backend/app/api/routers/novels/import_analysis.py`
  移除函数内无效导入 `select`。
- `backend/app/api/routers/novels/outlines.py`
  移除函数内无效导入 `StreamingResponse`。
- `backend/app/core/dependencies.py`
  移除零引用依赖注入函数 `get_vector_ingestion_service()`、`get_part_outline_service()`、`get_avatar_service()`。
- `backend/app/utils/content_normalizer.py`
  移除零调用函数 `normalize_version_content()`、`_coerce_text()`、`_clean_string()`，以及连带失效的 `logger`、`_PREFERRED_CONTENT_KEYS` 和相关导入。
- `backend/app/utils/sse_helpers.py`
  移除零调用函数 `sse_generator_error_handler()`、`track_saved_items()`、`SSEProgressTracker`，以及连带失效的 `wraps`、`TypeVar`、`T`。
- `backend/app/utils/text_utils.py`
  整文件零引用，已删除。
- `frontend/themes/transparency_tokens.py`
  移除零调用函数 `get_component_meta()`。
- `frontend/themes/theme_manager/v2_config_mixin.py`
  移除无效导入 `get_component_meta`。
- `frontend/utils/dpi_utils.py`
  移除零调用便捷函数 `responsive()`。

## 第十七轮追加清理

- `backend/app/services/chapter_generation/prompt_builder.py`
  在此前已清理无效导入 `json` 的基础上，继续移除零调用模块级单例 `_default_builder` 与工厂函数 `get_chapter_prompt_builder()`。
- `backend/app/services/chapter_generation/version_processor.py`
  移除零调用模块级单例 `_default_processor` 与工厂函数 `get_version_processor()`。
- `backend/app/services/chapter_generation/__init__.py`
  同步移除已失效导入/导出 `get_chapter_prompt_builder`、`get_version_processor`。
- `backend/app/services/novel_rag/auto_ingestion.py`
  移除零调用触发器 `trigger_protagonist_ingestion()`，并删除连带失效导入 `PROTAGONIST_INGESTION_TYPES`。
- `backend/app/services/novel_rag/__init__.py`
  同步移除已失效导出 `trigger_protagonist_ingestion`、`set_novel_strategy_manager`、`switch_novel_global_preset`。
- `backend/app/services/novel_rag/chunk_strategy.py`
  移除零调用策略切换函数 `set_novel_strategy_manager()`、`switch_novel_global_preset()`。
- `backend/app/services/rag/scene_extractor.py`
  移除零调用模块级单例 `_default_extractor` 与工厂函数 `get_scene_extractor()`。
- `backend/app/services/rag/utils.py`
  在此前已清理 `format_rag_summary_line()` 的基础上，继续移除零调用辅助函数 `format_chapter_reference()`。
- `backend/app/services/rag/__init__.py`
  同步移除已失效导出 `get_scene_extractor`、`format_chapter_reference`。
- `backend/app/services/rag_common/semantic_chunker.py`
  在此前已清理无效导入 `math` 的基础上，继续移除零调用模块级单例 `_default_chunker` 与工厂函数 `get_semantic_chunker()`、`set_semantic_chunker()`。
- `backend/app/services/rag_common/__init__.py`
  同步移除已失效导出 `get_semantic_chunker`、`set_semantic_chunker`。
- `backend/app/services/coding_rag/chunk_strategy.py`
  移除零调用策略切换函数 `set_strategy_manager()`、`switch_global_preset()`。
- `backend/app/services/coding_rag/__init__.py`
  同步移除已失效导出 `set_strategy_manager`、`switch_global_preset`。

## 第十八轮追加清理

- `frontend/themes/modern_effects.py`
  移除零调用便捷函数 `transition()`。
- `frontend/utils/worker_pool.py`
  移除零调用便捷函数 `submit_task()`。
- `frontend/utils/chapter_cache.py`
  移除零调用测试辅助函数 `reset_chapter_cache()`。
- `frontend/utils/__init__.py`
  同步移除已失效导入/导出 `submit_task`、`reset_chapter_cache`。
- `frontend/themes/book_theme_styler.py`
  移除零调用全局单例 `_global_styler` 与工厂函数 `get_book_styler()`。
- `frontend/themes/__init__.py`
  同步移除已失效导入/导出 `get_book_styler`。

## 第十九轮追加清理

- `frontend/utils/message_service.py`
  移除零调用便捷函数 `confirm_danger()`，保留仍被业务可直接调用的 `MessageService.confirm_danger()`。
- `frontend/components/loading_spinner.py`
  移除零调用上下文包装函数 `loading_context()`。
- `frontend/components/__init__.py`
  同步移除已失效导入/导出 `loading_context`。

## 第二十轮追加清理

- `frontend/themes/svg_icons.py`
  在此前已删除零引用控件类 `SVGIconWidget` 的基础上，继续移除零调用便捷函数 `icon()`。
- `backend/app/services/manga_prompt/core/service.py`
  移除零调用便捷函数 `generate_manga_prompts()`。
- `backend/app/services/manga_prompt/core/__init__.py`
  同步移除已失效导入/导出 `generate_manga_prompts`。
- `backend/app/services/manga_prompt/__init__.py`
  同步移除已失效导入/导出 `generate_manga_prompts`。

## 第二十一轮追加清理

- `frontend/themes/modern_effects.py`
  在第十八轮已删除 `transition()` 的基础上，继续移除零调用便捷函数 `gradient()`、`shadow()`。

## 第二十二轮追加清理

- `backend/app/services/queue/base.py`
  移除零调用测试辅助类方法 `reset_instance()`。
- `backend/app/services/coding_rag/auto_ingestion.py`
  在此前已清理无效导入 `CodingDataType` 的基础上，继续移除零调用触发器 `trigger_blueprint_ingestion()`。
- `backend/app/services/coding_rag/__init__.py`
  在此前已清理已失效导出 `set_strategy_manager`、`switch_global_preset` 的基础上，继续移除 `trigger_blueprint_ingestion` 的失效导入/导出。

## 第二十三轮追加清理

- `backend/app/services/coding_rag/auto_ingestion.py`
  在第二十二轮已删除 `trigger_blueprint_ingestion()` 的基础上，继续移除无外部调用的闭包绑定 `trigger_async_ingestion`。
- `backend/app/services/coding_rag/__init__.py`
  继续移除 `trigger_async_ingestion` 的失效导入/导出。
- `backend/app/services/novel_rag/auto_ingestion.py`
  移除无外部调用的闭包绑定 `trigger_async_ingestion`。
- `backend/app/services/novel_rag/__init__.py`
  继续移除 `trigger_async_ingestion`、`schedule_ingestion`、`schedule_multiple_ingestions` 的失效导入/导出。

## 第二十四轮追加清理

- `backend/app/services/import_analysis/__init__.py`
  移除 `count_chinese_characters`、`cn_to_arabic` 的失效导入/导出，保留 `txt_parser.py` 内部真实使用的实现。

## 第二十五轮追加清理

- `backend/app/services/rag_common/__init__.py`
  移除 `run_ingestion_task`、`split_markdown_sections`、`build_chunk_config`、`clone_chunk_config`、`serialize_chunk_config` 的失效导入/导出。

## 第二十六轮追加清理

- `backend/app/services/rag/__init__.py`
  在第十七轮已清理旧导出 `get_scene_extractor`、`format_chapter_reference` 的基础上，继续移除 `extract_involved_characters`、`truncate_text`、`build_outline_text` 的失效导入/导出。
- `backend/app/services/content_optimization/__init__.py`
  移除 `get_tools_prompt` 的失效导入/导出，保留 `tools.py` / `agent.py` 内部真实调用链。
- `backend/app/services/coding/__init__.py`
  移除 `CodingBlueprintService` 的失效导出，保留子模块实现。
- `backend/app/services/coding_files/__init__.py`
  移除 `DirectoryTreeBuilder`、`BruteForceOutput`、`PlannedDirectory`、`PlannedFile`、`ArchitecturePattern`、`ProjectProfiler`、`ArchitectureDecisionMaker`、`ArchitectureBasedGenerator`、`QualityEvaluator`、`RefinementAgent`、`ProjectProfile`、`ArchitectureDecision`、`QualityMetrics` 的失效导入/导出，仅保留真实包级入口 `DirectoryStructureService`、`FilePromptService`。
- `backend/app/services/part_outline/__init__.py`
  移除 `PartOutlineParser`、`get_part_outline_parser`、`PartOutlineModelFactory`、`get_part_outline_factory`、`PartOutlineContextRetriever`、`ChapterOutlineWorkflow`、`get_chapter_outline_workflow`、`GenerationCancelledException` 的失效导入/导出，仅保留真实包级入口 `PartOutlineWorkflow`、`PartOutlineService`。
- `backend/app/services/queue/__init__.py`
  移除 `RequestQueue` 的失效导入/导出，保留真实包级入口 `LLMRequestQueue`、`ImageRequestQueue`。

## 第二十七轮追加清理

- `backend/app/services/coding_files/architect/__init__.py`
  移除 `ProjectProfile`、`ArchitectureDecision`、`QualityMetrics`、`LayerDefinition`、`ModulePlacement`、`SystemSummary`、`ModuleSummary`、`DependencyGraph`、`SharedModuleStrategy`、`IssueType`、`IssueSeverity`、`StructureIssue`、`PatternTemplate`、`PATTERN_TEMPLATES`、`get_pattern_template`、`recommend_pattern` 的失效导入/导出，仅保留 `files_plan_v2.py` 真实使用的 6 个架构入口。
- `backend/app/services/coding_files/directory_generator/__init__.py`
  移除 `DirectorySpec`、`FileSpec`、`PlannedDirectory`、`PlannedFile` 的失效导入/导出，仅保留真实包级入口 `BruteForceOutput`、`DirectoryTreeBuilder`。
- `backend/app/services/coding_files/directory_agent/__init__.py`
  移除 `DirectoryPlanningAgent`、`AgentState`、`ToolExecutor`、`PlannedDirectory`、`PlannedFile`、`ToolCall`、`ToolResult`、`ToolCallParseResult`、`ToolCategory`、`ToolDefinition`、`TOOLS`、`get_tool`、`get_tools_prompt`、`parse_tool_call` 的失效导入/导出，仅保留真实包级入口 `run_directory_planning_agent`。
- `backend/app/services/image_generation/providers/__init__.py`
  移除 `BaseImageProvider`、`ProviderTestResult`、`ProviderGenerateResult`、`OpenAICompatibleProvider`、`StabilityProvider`、`ComfyUIProvider` 的失效导入/导出，仅保留真实包级入口 `ImageProviderFactory`。
- `backend/app/services/manga_prompt/__init__.py`
  在第二十轮已清理 `generate_manga_prompts` 的基础上，继续移除 `MangaStyle`、`ChapterInfoExtractor`、`ChapterInfo`、`CharacterInfo`、`DialogueInfo`、`EventInfo`、`SceneInfo`、`ItemInfo`、`PagePlanner`、`PagePlanResult`、`PagePlanItem`、`StoryboardDesigner`、`StoryboardResult`、`PageStoryboard`、`PanelDesign`、`DialogueBubble`、`ShotType`、`PanelShape`、`WidthRatio`、`AspectRatio`、`PromptBuilder`、`PagePromptResult`、`PanelPrompt` 的失效导入/导出，仅保留路由真实使用的 `MangaPromptServiceV2`、`MangaPromptResult`。
- `backend/app/services/manga_prompt/core/__init__.py`
  移除 `MangaStyle`、`CheckpointManager`、`ResultPersistence` 的失效导入/导出，仅保留 `MangaPromptServiceV2`。
- `backend/app/services/manga_prompt/extraction/__init__.py`
  移除 `EmotionType`、`EventType`、`CharacterRole`、`ImportanceLevel`、`CharacterInfo`、`DialogueInfo`、`NarrationInfo`、`SceneInfo`、`EventInfo`、`ItemInfo`、`PROMPT_NAME`、`CHAPTER_INFO_EXTRACTION_PROMPT`、`EXTRACTION_SYSTEM_PROMPT` 的失效导入/导出，仅保留内部真实通过包入口使用的 `ChapterInfo`、`ChapterInfoExtractor`。
- `backend/app/services/manga_prompt/planning/__init__.py`
  移除 `PROMPT_NAME`、`PAGE_PLANNING_PROMPT`、`PLANNING_SYSTEM_PROMPT` 的失效导入/导出，保留 `PagePlanner`、`PagePlanItem`、`PagePlanResult`。
- `backend/app/services/manga_prompt/storyboard/__init__.py`
  移除 `PROMPT_NAME`、`STORYBOARD_DESIGN_PROMPT`、`STORYBOARD_SYSTEM_PROMPT` 的失效导入/导出，保留内部真实通过包入口使用的分镜模型与 `StoryboardDesigner`。
- `backend/app/services/manga_prompt/prompt_builder/__init__.py`
  移除 `PanelPrompt`、`PagePromptResult` 的失效导入/导出，保留内部真实通过包入口使用的 `PagePrompt`、`MangaPromptResult`、`PromptBuilder`、`PagePromptGenerator`。

## 第二十八轮追加清理

- `backend/app/repositories/__init__.py`
  当前仓库不存在任何 `from ...repositories import ...` 包级导入点，移除整组仓储聚合导出，保留空包入口。
- `frontend/windows/settings/__init__.py`
  当前仓库仅通过包级入口导入 `SettingsView`，移除 `TestResultDialog`、`LLMConfigDialog`、`EmbeddingConfigDialog`、`PromptEditDialog` 的残留转发导出。
- `frontend/windows/settings/theme_settings/__init__.py`
  当前仓库仅通过包级入口导入 `UnifiedThemeSettingsWidget`，移除其余 V1/V2 配置编辑器、配置组与组件类的残留转发导出。
- `frontend/windows/writing_desk/__init__.py`
  当前仓库仅通过包级入口导入 `WritingDesk`，移除 Mixins、Dialogs、Components 的残留顶层转发导出。
- `frontend/windows/novel_detail/__init__.py`
  当前仓库仅通过包级入口导入 `NovelDetail`，移除 Mixins、Sections、Dialogs、Components、工具类与 `ChapterOutlineSection` 的残留顶层转发导出。
- `frontend/windows/__init__.py`
  当前仓库不存在任何 `from windows import ...` 包级导入点，移除整组窗口聚合导出，保留空包入口。

## 第二十九轮追加清理

- `frontend/windows/writing_desk/dialogs/__init__.py`
  当前仓库仅通过包级入口使用 `OutlineEditDialog`、`PromptPreviewDialog`、`ProtagonistProfileDialog`，移除 `ProtagonistCreateDialog`、`AttributeEvidenceDialog` 的残留转发导出。
- `frontend/windows/writing_desk/components/__init__.py`
  当前仓库仅通过包级入口使用 `ChapterCard`、`FlippableBlueprintCard`，移除 `ThinkingStreamView`、`SuggestionCard`、`ParagraphSelector` 的残留转发导出。
- `frontend/windows/novel_detail/chapter_outline/__init__.py`
  当前仓库仅通过包级入口使用 `ChapterOutlineSection`，移除 Handlers、Dialogs、Components 的 10 个残留顶层转发导出。

## 第三十轮追加清理

- `frontend/windows/writing_desk/panels/__init__.py`
  当前仓库仅通过包级入口使用 `AnalysisPanelBuilder`、`VersionPanelBuilder`、`ReviewPanelBuilder`、`SummaryPanelBuilder`、`ContentPanelBuilder`，移除 `BasePanelBuilder` 的残留转发导出。
- `frontend/windows/novel_detail/chapter_outline/dialogs/__init__.py`
  当前仓库仅通过包级入口使用 `ChapterOutlineEditDialog`，移除 `PartOutlineDetailDialog`、`ChapterOutlineDetailDialog` 的残留转发导出。
- `frontend/windows/novel_detail/chapter_outline/components/__init__.py`
  当前仓库仅通过包级入口使用 `OutlineListView`、`OutlineActionBar`、`LongNovelEmptyState`、`ShortNovelEmptyState`，移除 `OutlineRow` 的残留转发导出。

## 第三十一轮追加清理

- `frontend/windows/base/__init__.py`
  当前仓库仅通过包级入口使用 `BaseWorkspacePage`，移除 `BaseDetailPage`、`BaseSection` 的残留转发导出。
- `frontend/windows/inspiration_mode/__init__.py`
  当前仓库仅通过包级入口使用 `InspirationMode`，移除 Mixins、Components、Services 的 9 个残留顶层转发导出。
- `frontend/windows/inspiration_mode/components/__init__.py`
  当前仓库仅通过包级入口使用 `ChatBubble`、`ConversationInput`、`BlueprintDisplay`、`BlueprintConfirmation`、`InspiredOptionsContainer`，移除 `InspiredOptionCard` 的残留转发导出。
- `frontend/windows/coding_desk/components/__init__.py`
  当前仓库仅通过包级入口使用 `DirectoryTree`、`ProjectInfoCard`，移除 `TreeNodeItem`、`TechStackTag` 的残留转发导出。
- `frontend/windows/coding_detail/sections/__init__.py`
  当前仓库仅通过包级入口使用 4 个主 Section，移除 `SystemNode`、`ModuleNode`、`GroupedDependencyCard`、`GeneratedItemCard` 的残留转发导出。

## 第三十二轮追加清理

- `frontend/components/__init__.py`
  当前仓库仅通过包级入口使用 `LoadingOverlay`，移除其余 18 个历史组件/工具的残留转发导出。
- `frontend/components/base/__init__.py`
  当前仓库仅通过包级入口使用 `ThemeAwareWidget`、`ThemeAwareFrame`、`ThemeAwareButton`，移除 `AnimatedStackedWidget` 的残留转发导出。
- `frontend/api/__init__.py`
  当前仓库不存在任何 `from frontend.api import ...` 业务导入点，删除整组 20 个历史包级转发导出，保留精简包入口。
- `frontend/api/client/__init__.py`
  当前仓库仅通过包级入口使用 `AFNAPIClient`，移除 `TimeoutConfig` 的残留转发导出。
- `frontend/pages/__init__.py`
  当前仓库不存在任何 `from frontend.pages import ...` 业务导入点，删除顶层页面包的残留转发导出，保留精简包入口。
- `frontend/pages/home_page/__init__.py`
  当前仓库仅通过包级入口使用 `HomePage`，移除 6 个首页卡片/粒子/常量相关残留转发导出。
- `frontend/themes/__init__.py`
  当前仓库仅通过包级入口使用 `ButtonStyles`、`ModernEffects`，移除主题管理、组件样式、无障碍、SVG 图标和书籍主题等 15 个残留转发导出。
- `frontend/themes/theme_manager/__init__.py`
  当前仓库仅通过包级入口使用 `theme_manager`、`ThemeMode`，移除 `ThemeManager`、主题类、调色板与 `V2ConfigMixin` 等 6 个残留转发导出。

## 第三十三轮追加清理

- `frontend/components/dialogs/common/__init__.py`
  当前仓库仅通过父包和业务入口使用 `get_regenerate_preference`，移除零包级引用的 `RegenerateDialog` 残留转发导出。
- `frontend/components/dialogs/__init__.py`
  当前仓库仅通过包级入口使用 `get_regenerate_preference`，移除零包级引用的 `RegenerateDialog` 残留转发导出。
- `frontend/windows/writing_desk/optimization/__init__.py`
  当前仓库仅通过兼容层 `optimization_content.py` 从包级入口导入 `OptimizationContent`、`OptimizationMode`，移除 `SSEHandlerMixin`、`SuggestionHandlerMixin`、`ModeControlMixin` 的残留转发导出。

## 第三十四轮追加清理

- `frontend/components/inputs/__init__.py`
  当前仓库仅通过包级入口使用 `SwitchWidget`，`SwitchControl` 只作为 `switch_input.py` 内部实现存在，移除其残留包级导出。

## 第三十五轮追加清理

- `frontend/models/__init__.py`
  当前仓库不存在任何 `from models import ...` 或 `from models.project_status import ...` 真实导入点，删除 `ProjectStatus` 转发以及 5 个历史数据类，保留精简包入口。

## 第三十六轮追加清理

- `frontend/models/project_status.py`
  当前仓库不存在任何 `from models.project_status import ...` 真实导入点，删除零引用的 `ProjectStatus` 枚举实现与无效 `Enum` 导入，保留兼容占位模块。

## 第三十七轮追加清理

- `backend/app/serializers/__init__.py`
  当前仓库不存在任何 `from ...serializers import ...` 包级导入点，删除零包级引用的 `NovelSerializer` 转发导出并保留精简包入口。

## 第三十八轮追加清理

- `backend/app/services/theme_defaults/__init__.py`
  当前仓库仅通过包级入口使用 `get_theme_defaults`、`get_theme_v2_defaults`，移除四个零包级引用的主题默认值常量导出。

## 第三十九轮追加清理

- `backend/app/services/image_generation/__init__.py`
  当前仓库仅通过包级入口使用 `ImageGenerationService`、`ImageConfigService` 与核心请求/响应 schema，移除零包级引用的 `PDFExportService`、`ProviderType`、`PDFExportRequest`、`PDFExportResult` 导出。

## 第四十轮追加清理

- `setup_env.py`
  基于 AST 与全文检索确认 `Colors`、`WORK_DIR`、`STORAGE_DIR`、`BACKEND_PORT`、`setup_logging`、`_load_logging_config`、`is_port_in_use`、`get_pid_using_port`、`kill_process_on_port`、`ensure_port_available`、`check_uv_available`、`install_uv`、`StartupProgress`、`startup_progress`、`check_dependencies_installed` 均无任何实际引用，删除无效导入。

## 第四十一轮追加清理

- `backend/startup/__init__.py`
  当前仓库唯一包级使用者 `setup_env.py` 已不再导入 `Colors`、`WORK_DIR`、`STORAGE_DIR`、`BACKEND_PORT`、`setup_logging`、`_load_logging_config`、`is_port_in_use`、`get_pid_using_port`、`kill_process_on_port`、`ensure_port_available`、`check_uv_available`、`install_uv`、`StartupProgress`、`startup_progress`、`check_dependencies_installed`，删除这 15 个零包级引用的历史转发导出。

## 第四十二轮追加清理

- `run_app.py`
  基于 AST 与全文检索确认 `Path`、`WORK_DIR`、`BACKEND_VENV`、`FRONTEND_VENV`、`print_banner` 均无任何实际引用，删除无效导入。

## 第四十三轮追加清理

- `backend/startup/animation.py`
  基于 AST 与全文检索确认 `BASE_DIR` 无任何实际引用，删除无效导入。
- `backend/startup/installer.py`
  基于 AST 与全文检索确认 `Set`、`BACKEND_DIR`、`FRONTEND_DIR` 均无任何实际引用，删除无效导入。
- `backend/startup/port_utils.py`
  基于 AST 与全文检索确认 `logger` 无任何实际引用，删除无效导入。
- `backend/startup/uv_manager.py`
  基于 AST 与全文检索确认 `logger` 无任何实际引用，删除无效导入。

## 第四十四轮追加清理

- `backend/scripts/fix_real_summary.py`
  基于 AST 与全文检索确认 `selectinload` 无任何实际引用，删除无效导入。
- `backend/app/services/content_optimization/agent.py`
  基于 AST 与全文检索确认顶层 `json` 导入与 `_parse_response()` 内部的 `ToolCallParseResult` 局部导入均无任何实际引用，删除无效导入。
- `backend/app/services/coding_rag/auto_ingestion.py`
  基于 AST 与全文检索确认 `Any`、`Optional`、`BLUEPRINT_INGESTION_TYPES`、`schedule_multiple_ingestions` 均无任何实际引用，删除无效导入。
- `backend/app/services/coding_rag/ingestion_service.py`
  确认 `CompletenessReport` 已无任何模块级导入点，移除残留导入与 `__all__` 导出。
- `backend/app/services/coding_rag/__init__.py`
  当前仓库仅通过包级入口使用 `CodingDataType`、`CodingProjectIngestionService`、`schedule_ingestion`，移除其余 12 个零包级引用的历史导出。
- `backend/app/services/novel_rag/ingestion_service.py`
  确认 `CompletenessReport` 已无任何模块级导入点，移除残留导入与 `__all__` 导出。
- `backend/app/services/novel_rag/__init__.py`
  当前仓库仅通过包级入口使用 `NovelDataType`、`NovelProjectIngestionService` 与 5 个 `trigger_*_ingestion` 入口，移除其余 16 个零包级引用的历史导出。

## 第四十五轮追加清理

- `backend/app/services/embedding_service.py`
  基于 AST 与全文检索确认 `_find_local_model_path()` 内部 `Path` 导入无任何实际引用，删除无效导入。
- `backend/app/services/image_generation/pdf_export.py`
  基于 AST 与全文检索确认 `generate_chapter_manga_pdf()` 内部 `ImageReader` 导入无任何实际引用，删除无效导入。
- `backend/app/core/dependencies.py`
  复核确认 JWT 解码局部导入中的 `JWTError` 仅存于注释语义、无任何实际引用，删除无效导入并保留 `jwt`。
- `backend/app/repositories/novel_repository.py`
  复核确认顶层 `load_only` 函数导入未被调用，当前文件实际使用的是 `selectinload(...).load_only()` 链式方法，删除无效导入。
- `backend/app/services/chapter_generation/__init__.py`
  当前仓库仅通过包级入口使用 `ChapterGenerationService`、`ChapterGenerationWorkflow`，移除 `ChapterGenerationContext`、`ChapterGenerationResult`、`ChapterPromptBuilder`、`ChapterVersionProcessor` 4 个零包级引用导出。
- `backend/app/services/content_optimization/__init__.py`
  当前仓库已全部改为子模块直连，删除 12 个零包级引用的历史导出并保留精简包入口。

## 第四十六轮追加清理

- `backend/app/services/import_analysis/__init__.py`
  当前仓库仅通过包级入口使用 `ImportAnalysisService`，删除 9 个零包级引用导出，并将文档示例改为子模块直连导入。
- `backend/app/services/rag/__init__.py`
  当前仓库仅通过包级入口使用 `EnhancedQueryBuilder`、`EnhancedQuery`、`TemporalAwareRetriever`、`SmartContextBuilder`、`GenerationContext`、`ContextCompressor`、`get_outline_rag_retriever`，删除其余 5 个零包级引用导出。
- `backend/app/services/rag_common/__init__.py`
  当前仓库不存在任何 `rag_common` 包级入口消费者，删除 8 个零包级引用导出并保留精简包入口。

## 第四十七轮追加清理

- `frontend/api/client/import_mixin.py`
  基于 AST 与全文检索确认 `Optional` 无任何实际引用，删除无效导入。
- `frontend/components/base/animated_stacked_widget.py`
  基于 AST 与全文检索确认 `QWidget`、`Qt`、`QPoint` 均无任何实际引用，删除无效导入。
- `frontend/components/empty_state.py`
  基于 AST 与全文检索确认顶层 `QWidget` 导入无任何实际引用，删除无效导入。
- `frontend/components/flow_layout.py`
  基于 AST 与全文检索确认 `QWidgetItem`、`QSizePolicy` 均无任何实际引用，删除无效导入。
- `frontend/components/inputs/slider_input.py`
  基于 AST 与全文检索确认 `QFrame` 导入无任何实际引用，删除无效导入。
- `frontend/components/inputs/switch_input.py`
  基于 AST 与全文检索确认 `QFrame`、`QRect`、`QSize` 均无任何实际引用，删除无效导入。
- `frontend/components/loading_spinner.py`
  在此前已移除 `loading_context()` 后继续确认 `Any`、`QSizePolicy`、`QFrame`、`QRect` 均无任何实际引用，删除无效导入。
- `frontend/components/lazy_tab_widget.py`
  基于 AST 与全文检索确认 `Optional` 导入无任何实际引用，删除无效导入。
- `frontend/utils/chapter_cache.py`
  在此前已移除 `reset_chapter_cache()` 后继续确认 `List` 导入无任何实际引用，删除无效导入。
- `frontend/utils/component_pool.py`
  在此前已移除全局池管理接口后继续确认 `Any` 导入无任何实际引用，删除无效导入。
- `frontend/utils/window_blur.py`
  基于 AST 与全文检索确认 `Optional` 导入无任何实际引用，删除无效导入。
- `frontend/windows/base/detail_page.py`
  基于 AST 与全文检索确认 `Callable` 导入无任何实际引用，删除无效导入。

## 第四十八轮追加清理

- `frontend/components/theme_transition.py`
  基于 AST 与全文检索确认 `QParallelAnimationGroup` 导入无任何实际引用，删除无效导入。
- `frontend/themes/modern_effects.py`
  在此前已移除 `transition()`、`gradient()`、`shadow()` 后继续确认 `Tuple`、`QLinearGradient`、`QRadialGradient`、`QConicalGradient` 均无任何实际引用，删除无效导入。
- `frontend/themes/svg_icons.py`
  在此前已移除 `SVGIconWidget` 与 `icon()` 后继续确认 `Optional` 导入无任何实际引用，删除无效导入。
- `frontend/windows/base/workspace_page.py`
  基于 AST 与全文检索确认 `List` 导入无任何实际引用，删除无效导入。
- `frontend/windows/coding_desk/header.py`
  基于 AST 与全文检索确认 `Optional`、`QWidget` 均无任何实际引用，删除无效导入。
- `frontend/windows/coding_desk/sidebar.py`
  基于 AST 与全文检索确认 `QFrame` 导入无任何实际引用，删除无效导入。
- `frontend/windows/coding_desk/workspace.py`
  基于 AST 与全文检索确认 `QFrame` 导入无任何实际引用，删除无效导入。
- `frontend/utils/__init__.py`
  当前仓库不存在任何 `from utils import ...` 或 `import utils` 的真实消费者，删除 13 个历史聚合导出并保留精简包入口。

## 第四十九轮追加清理

- `frontend/themes/transparency_tokens.py`
  在第十六轮已移除零调用函数 `get_component_meta()` 后继续确认 `Tuple` 导入无任何实际引用，删除无效导入；`get_all_component_ids()` 仍被 `v2_config_mixin.py` 使用，保留。
- `frontend/windows/coding_detail/sections/overview.py`
  基于 AST 与全文检索确认 `logging`、`List` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- `frontend/windows/coding_detail/sections/generated.py`
  基于 AST 与全文检索确认 `logging`、`QScrollArea`、`QSizePolicy` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- `frontend/windows/coding_detail/sections/modules.py`
  基于 AST 与全文检索确认 `logging`、`QScrollArea`、`QSizePolicy` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- `frontend/windows/coding_detail/sections/systems.py`
  基于 AST 与全文检索确认 `Optional`、`QScrollArea`、`QSizePolicy`、`QMenu`、`QAction` 均无任何实际引用，删除无效导入。

## 第五十轮追加清理

- `frontend/windows/coding_detail/sections/architecture.py`
  基于 AST 与全文检索确认 `QGridLayout` 导入无任何实际引用，删除无效导入。
- `frontend/windows/coding_detail/sections/dependencies.py`
  基于 AST 与全文检索确认 `QGridLayout` 导入无任何实际引用，删除无效导入。
- `frontend/windows/coding_detail/sections/directory.py`
  基于 AST 与全文检索确认 `Optional`、`QFrame`、`QHeaderView`、`QSizePolicy` 均无任何实际引用，删除无效导入。
- `frontend/windows/coding_detail/sections/generation.py`
  基于 AST 与全文检索确认 `Any` 导入无任何实际引用，删除无效导入。
- `frontend/components/virtual_list.py`
  基于 AST 与全文检索确认 `logging`、`Generic`、`Optional`、`QSizePolicy` 导入以及模块级 `logger` 与局部变量 `total_height` 均无任何实际引用，删除无效导入与零引用变量。

## 第五十一轮追加清理

- `frontend/pages/home_page/cards.py`
  基于 AST 与全文检索确认 `QWidget` 导入无任何实际引用，删除无效导入。
- `frontend/pages/home_page/core.py`
  基于 AST 与全文检索确认 `ImportProgressDialog` 包级导入，以及 `_apply_theme()` 内部重复导入的 `Qt`、`QWidget` 均无任何实际必要，删除冗余导入。
- `frontend/utils/lazy_loader.py`
  基于 AST 与全文检索确认 `QSizePolicy` 导入无任何实际引用，删除无效导入。
- `frontend/windows/coding_detail/mixins/header_manager.py`
  基于 AST 与全文检索确认 `logging`、`QProgressBar` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。
- `frontend/windows/coding_desk/components/project_info_card.py`
  基于 AST 与全文检索确认 `logging`、`List` 导入以及模块级 `logger` 变量均无任何实际引用，删除无效导入与零引用变量。

## 第五十二轮追加清理

- `frontend/windows/writing_desk/header.py`
  基于 AST 与全文检索确认 `QWidget` 导入无任何实际引用，删除无效导入。
- `frontend/windows/novel_detail/sections/world_setting_section.py`
  基于 AST 与全文检索确认 `QScrollArea` 导入无任何实际引用，删除无效导入。
- `frontend/windows/novel_detail/dialogs/edit_dialog.py`
  基于 AST 与全文检索确认 `QWidget`、`Any` 导入无任何实际引用，删除无效导入。
- `frontend/windows/novel_detail/dirty_tracker.py`
  基于 AST 与全文检索确认 `Optional`、`Tuple` 导入无任何实际引用，删除无效导入。
- `frontend/windows/settings/advanced_settings_widget.py`
  基于 AST 与全文检索确认 `QPushButton`、`QFrame`、`Qt` 导入无任何实际引用，删除无效导入。

## 第五十三轮追加清理

- `frontend/windows/settings/max_tokens_settings_widget.py`
  基于 AST 与全文检索确认 `QPushButton`、`sp` 导入无任何实际引用，删除无效导入。
- `frontend/windows/settings/prompt_settings_widget.py`
  基于 AST 与全文检索确认 `QStackedWidget` 导入无任何实际引用，删除无效导入。
- `frontend/windows/settings/temperature_settings_widget.py`
  基于 AST 与全文检索确认 `QPushButton` 导入无任何实际引用，删除无效导入。
- `frontend/windows/writing_desk/components/chapter_card.py`
  基于 AST 与全文检索确认 `QPoint` 导入无任何实际引用，删除无效导入。
- `frontend/windows/writing_desk/dialogs/prompt_preview_dialog.py`
  基于 AST 与全文检索确认 `QFont` 导入无任何实际引用，删除无效导入。

## 二轮复核保留项

- `backend/app/api/routers/protagonist.py`
  复核后确认 `get_analysis_service()`、`get_sync_service()` 仍被路由 `Depends(...)` 使用，保留。
- `backend/app/services/llm_service.py`
  复核后确认 `LLMConfigCache`、`_config_cache`、`invalidate_config_cache()` 仍被 `llm_config_service.py` 使用，保留。
- `backend/app/utils/api_format_utils.py`
  复核后确认 `build_openai_image_generations_endpoint()` 仍被 `image_generation/providers/openai_compatible.py` 使用，保留。
- `frontend/utils/component_pool.py`
  复核后确认 `reset_outline_row()` 仍被 `chapter_outline/components/outline_list.py` 使用，保留。
- `frontend/utils/project_helpers.py`
  复核后确认 `get_blueprint()` 仍被 `frontend/windows/novel_detail/main.py` 使用，保留。
- `backend/app/services/summary_service.py`
  复核后确认 `Chapter`、`ChapterOutlineRepository`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/manga_prompt/extraction/chapter_info_extractor.py`
  复核后确认 `PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/manga_prompt/planning/page_planner.py`
  复核后确认 `PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/manga_prompt/storyboard/designer.py`
  复核后确认 `PromptService`、`LLMService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/part_outline/context_retriever.py`
  复核后确认 `ChapterOutlineRepository`、`LLMService`、`VectorStoreService` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/part_outline/workflow.py`
  复核后确认 `AsyncSession` 属于 `TYPE_CHECKING` 前向引用导入，保留。
- `backend/app/services/novel_rag/ingestion_service.py`
  复核后确认 `CompletenessReport` 通过 `__all__` 对外导出，保留。
- `backend/app/repositories/chapter_repository.py`
  复核后确认 `ChapterVersionRepository`、`ChapterEvaluationRepository`、`ChapterOutlineRepository` 仍承担向后兼容导出职责，保留。
- `backend/app/db/init_db.py`
  复核后确认 `from ..models import ...` 依赖导入副作用注册 SQLAlchemy 元数据，供 `Base.metadata.create_all()` 使用，保留。
- `backend/app/core/dependencies.py`
  复核后确认 `JWTError` 仍属函数内惰性导入误报，保留。
- `backend/app/utils/content_normalizer.py`
  复核后确认 `count_chinese_characters()` 仍被章节管理、章节版本与导入分析链路使用，保留。
- `frontend/themes/transparency_tokens.py`
  复核后确认 `get_all_component_ids()` 仍被 `v2_config_mixin.py` 使用，保留。
- `frontend/themes/theme_manager/core.py`
  复核后确认 `ConfigManager` 属于 `TYPE_CHECKING` 前向引用导入，供 `set_config_manager()` 注解使用，保留。
- AST 补扫收口后剩余候选仅为既有误报保留项：
  `backend/app/core/dependencies.py` 的 `JWTError`、`backend/app/repositories/novel_repository.py` 的 `load_only`、`backend/app/services/embedding_service.py` 的函数内局部导入 `Path`、`backend/app/services/image_generation/pdf_export.py` 的函数内局部导入 `ImageReader`、以及 `backend/app/db/init_db.py` 的模型注册导入。

## 验证结果

- 已通过：对当前 62 个已修改 Python 文件执行 `python3 -m py_compile`
- 已通过：`cd frontend-web && npm run lint`
- 已通过：`cd frontend-web && npm run build`
- 已通过：对本轮已删符号执行 `rg` 残留引用复扫，未发现残留调用点
- 已通过：第三轮新增 4 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查均通过
- 已通过：第四轮新增 7 个 Python 文件局部复核，`python3 -m py_compile` 通过
- 已通过：第五轮新增 1 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第五轮对非路由/非脚本 Python 顶层符号执行“全仓单次出现”收口扫描，未发现新的高置信业务死代码候选
- 已通过：第六轮新增 8 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第七轮新增 6 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第八轮新增 4 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第九轮新增 11 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十轮新增 10 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十一轮新增 15 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十二轮新增 6 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十三轮新增 4 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十四轮新增 9 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十五轮新增 5 个 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十六轮新增 21 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过；另有 4 个复核保留文件已完成人工确认
- 已通过：第十六轮补跑 AST 级 unused-import 补扫，当前仅剩既有误报保留项，无新的高置信候选
- 已通过：第十七轮新增 13 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十八轮新增 6 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第十九轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十轮新增 4 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十一轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十二轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十三轮新增 4 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十四轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十五轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十六轮新增 6 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十七轮新增 10 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十八轮新增 6 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第二十九轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十一轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十二轮新增 8 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十三轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十四轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十五轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十六轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十七轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十八轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第三十九轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第四十轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 AST 级 unused-import 复核通过
- 已通过：第四十一轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 通过
- 已通过：第四十二轮新增 1 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 AST 级 unused-import 复核通过
- 已通过：第四十三轮新增 4 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 AST 级 unused-import 复核通过
- 已通过：第四十四轮新增 7 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 残留引用检查通过
- 已通过：第四十五轮新增 6 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 包级/符号级残留引用检查通过
- 已通过：第四十六轮新增 3 个已修改 Python 文件局部复核，`python3 -m py_compile` 与 `rg` 包级/符号级残留引用检查通过
- 已通过：第四十六轮补跑 AST 级 unused-import 补扫，当前仅剩 `TYPE_CHECKING` / 字符串注解保留项与已确认存在消费者的兼容导出，无新的高置信候选
- 已通过：第四十七轮新增 12 个已修改 Python 文件局部复核，`python3 -m py_compile` 与同文件残留符号检查通过
- 已通过：第四十八轮新增 8 个已修改 Python 文件局部复核，`python3 -m py_compile` 与包级/同文件残留符号检查通过
- 已通过：第四十九轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与同文件残留符号检查通过
- 已通过：第五十轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与同文件残留符号检查通过
- 已通过：第五十一轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与同文件残留符号检查通过；另完成 `frontend/themes/theme_manager/core.py` 的 `TYPE_CHECKING` 保留复核
- 已通过：第五十二轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与同文件残留符号检查通过
- 已通过：第五十三轮新增 5 个已修改 Python 文件局部复核，`python3 -m py_compile` 与精确符号残留检查通过

## 结论

- 本轮已经完成“按当前代码库基线逐文件完整覆盖”。
- 逐文件阅读过程可在 `DEAD_CODE_AUDIT_REVIEW_LOG.md` 查看。
- 每个文件的最终状态可在 `DEAD_CODE_AUDIT_FILELIST.tsv` 查看。
