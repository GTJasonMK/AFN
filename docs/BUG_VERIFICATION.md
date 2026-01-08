# Bug 验证报告

基于源代码分析，对 `BUG_REPORT.md` 中记录的 42 个潜在问题进行验证。

**验证时间**: 2026-01-07
**验证方式**: 源代码静态分析

## 验证结果汇总

| 状态 | 数量 | 说明 |
|------|------|------|
| 确认存在 | 42 | 所有问题在当前代码中仍然存在 |
| 已修复 | 0 | - |
| 无法复现 | 0 | - |

---

## 一、章节生成核心问题 (Bug 1-12)

### Bug 1: 空白项目无法生成章节 - 确认存在

**位置**: `backend/app/services/chapter_generation/workflow.py:179-183`

**验证结果**: 代码直接调用 `project_schema.blueprint.model_dump()` 无空值检查，空白项目会抛出 `AttributeError`。

### Bug 2: 用量统计逻辑覆盖过度 - 确认存在

**位置**: `backend/app/services/chapter_generation/service.py:230-243`

**验证结果**: `skip_usage_tracking` 仅由配置值决定，与实际是否并行执行无关。串行降级后仍跳过用量追踪。

### Bug 3: 重试版本后索引不会更新 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:188-218`

**验证结果**: `retry_chapter_version` 只更新 `target_version.content`，不触发 `IncrementalIndexer` 或 `select_chapter_version`，索引保持旧数据。

### Bug 4: 重试版本后摘要和字数不会同步 - 确认存在

**位置**: 同 Bug 3

**验证结果**: 重试只覆盖正文内容，`chapter.real_summary` 与 `chapter.word_count` 未更新。

### Bug 5: 提示词预览在空白项目下同样会异常 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:253-280`

**验证结果**: 与 Bug 1 相同，直接调用 `model_dump()` 无空值保护。

### Bug 6: 版本元数据在写入数据库时被丢弃 - 确认存在

**位置**: `backend/app/services/chapter_version_service.py:107-151`

**验证结果**: `versions_data.append({..., "metadata": None, ...})` 硬编码为 None，传入的 metadata 参数完全未使用。

### Bug 7: 重生成失败会永久丢失已选版本 - 确认存在

**位置**: `backend/app/services/chapter_generation/workflow.py:153-160`

**验证结果**: `_initialize` 在生成开始就清空 `selected_version_id` 并提交，失败时 `_reset_chapter_status` 不会恢复。

### Bug 8: 空白项目的版本重试依旧会崩溃 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:165-175`

**验证结果**: 与 Bug 1 相同，复制了相同的无空值保护代码。

### Bug 9: 未启用向量库时伏笔/主角档案完全丢失 - 确认存在

**位置**: `backend/app/services/chapter_generation/service.py:168-285`

**验证结果**: 当 `vector_store is None` 时不创建 `enhanced_rag_context`，导致 `ChapterPromptBuilder` 无法获取角色/伏笔信息。

### Bug 10: 缺少同章生成的互斥保护 - 确认存在

**位置**: `backend/app/services/chapter_generation/workflow.py:153-160`

**验证结果**: 没有检查 `chapter.status == 'generating'`，重复点击可触发多次生成。

### Bug 11: 提示词预览生成的摘要无法持久化 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:253-340`

**验证结果**: 调用 `collect_chapter_summaries` 后直接返回，没有 `session.commit()`，生成的摘要会被回滚。

### Bug 12: 流式生成接口缺少上一章内容校验 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:398-461`

**验证结果**: SSE 路由只做状态校验，没有复制同步接口 81-104 行的前一章正文检查逻辑。

---

## 二、状态机与评估问题 (Bug 13-16)

### Bug 13: 空白项目无法执行章节评估 - 确认存在

**位置**: `backend/app/services/chapter_evaluation_service.py:295-305`

**验证结果**: 与 Bug 1 相同模式，直接调用 `blueprint.model_dump()` 无空值保护。

### Bug 14: 章节大纲生成/重生成同样忽略空白蓝图 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_outlines.py:175-189, 605-621`

**验证结果**: 增量生成和重生成大纲都有相同的空值问题。

### Bug 15: 已完结项目无法重新生成章节 - 确认存在

**位置**: `backend/app/core/state_validators.py:27-30`

**验证结果**: `CHAPTER_GENERATION_STATES` 只包含 `CHAPTER_OUTLINES_READY` 和 `WRITING`，不含 `COMPLETED`，与 Workflow 允许完结项目生成的设计冲突。

### Bug 16: 已完结项目无法重试章节版本 - 确认存在

**位置**: `backend/app/api/routers/writer/chapter_generation.py:146-149`

**验证结果**: 与 Bug 15 相同，`retry_chapter_version` 使用同一组状态校验。

---

## 三、PDF 导出问题 (Bug 17, 20-21, 26, 28-29, 32-33, 42)

### Bug 17: PDF 导出文件名可被用户输入污染 - 确认存在

**位置**: `backend/app/services/image_generation/pdf_export.py:174-182`

**验证结果**: `title` 直接拼接进文件名，未做路径遍历过滤。

### Bug 20: 专业漫画PDF忽略章节版本过滤 - 确认存在

**位置**: `backend/app/services/image_generation/pdf_export.py:553-575`

**验证结果**: 专业模式查询只按 `project_id` + `chapter_number` 过滤，完全忽略 `request.chapter_version_id`。

### Bug 21: layout 参数无效 - 确认存在

**位置**: `backend/app/api/routers/image_generation.py:475-498`

**验证结果**: 路由始终调用专业模式，`request.layout` 从未被引用。

### Bug 26: 漫画 PDF 导出无法选择章节版本 - 确认存在

**位置**: `frontend/api/client/image_mixin.py:420-452`

**验证结果**: `generate_chapter_manga_pdf` 只发送 `page_size` 和 `include_prompts`，不发送 `chapter_version_id`。

### Bug 28: PDF 下载 URL 在真实网络环境下无效 - 确认存在

**位置**: `backend/app/api/routers/image_generation.py:542-544`

**验证结果**: 返回相对路径 URL，前端拼接 `base_url` 时远程环境会失效。

### Bug 29: PDF 预览依赖后端本地路径 - 确认存在

**位置**: `frontend/windows/writing_desk/panels/manga/pdf_tab.py:265-309`

**验证结果**: 直接使用 `fitz.open(pdf_path)` 打开服务端磁盘路径，远程环境必然失败。

### Bug 32: 漫画 PDF 导出完全忽略图片选中状态与最新生成结果 - 确认存在

**位置**: `backend/app/services/image_generation/pdf_export.py:561-638`

**验证结果**: 查询无 `is_selected` 条件，专业模式 `panel_image_map` 只保留第一张图片。

### Bug 33: 刷新图片后 PDF 信息会被清空 - 确认存在

**位置**: `frontend/windows/writing_desk/panels/manga/pdf_tab.py:422-426`

**验证结果**: `_on_refresh_images` 只刷新图片列表，不传递 `pdf_info`，重建 Tab 时信息丢失。

### Bug 42: 一页一图 PDF 在未筛选版本时只返回 legacy 图片 - 确认存在

**位置**: `backend/app/services/image_generation/pdf_export.py:345-379`

**验证结果**: 未指定版本时查询 `chapter_version_id IS NULL`，有版本 ID 的新图片无法获取。

---

## 四、图片生成与本地存储问题 (Bug 18-19, 25, 27, 38-41)

### Bug 18: 前端漫画面板无法加载本地生成图片 - 确认存在

**位置**: `frontend/windows/writing_desk/workspace/manga_handlers.py:225-228`

**验证结果**: `base_dir` 只回退到 `frontend` 目录，拼接出的路径 `frontend/backend/...` 不存在。

### Bug 19: 删除章节后项目无法从 completed 状态回退 - 确认存在

**位置**: `backend/app/services/novel_service.py:435-461`

**验证结果**: 删除接口不调用 `transition_project_status`，`check_and_update_completion_status` 只有升级逻辑无降级逻辑。

### Bug 25: 前端从未传递 chapter_version_id - 确认存在

**位置**: `frontend/api/client/image_mixin.py:137-172`

**验证结果**: `generate_scene_image` 方法签名完全没有 `chapter_version_id` 参数。

### Bug 27: 删除漫画分镜不会清理已生成的图片 - 确认存在

**位置**: `backend/app/services/manga_prompt/core/service.py:455-468`

**验证结果**: `delete_result` 只删除 `ChapterMangaPrompt` 记录，不调用 `ImageGenerationService.delete_chapter_images`。

### Bug 38: 图片生成与 PDF 导出无法识别章节版本 - 确认存在

**位置**: 同 Bug 25

**验证结果**: 与 Bug 25 相同，前端所有调用点都不传 `chapter_version_id`。

### Bug 39: "已生成图片"总是展示最旧的一张 - 确认存在

**位置**: `frontend/windows/writing_desk/workspace/manga_handlers.py:104-119`

**验证结果**: 后端按 `created_at.desc()` 排序（最新在前），前端用 `[-1]` 取最后一个即最旧图片。

### Bug 40: 章节图片 API 无法按版本过滤 - 确认存在

**位置**: `backend/app/api/routers/image_generation.py:399-427`

**验证结果**: 路由不接受 `chapter_version_id` 查询参数，服务层的版本过滤功能无法触发。

### Bug 41: 图片接口返回的下载 URL 根本不存在 - 确认存在

**位置**: `backend/app/services/image_generation/service.py:612`

**验证结果**: URL 硬编码为 `/api/images/...`，但实际路由是 `/api/image-generation/files/...`，URL 为死链。

---

## 五、漫画提示词数据问题 (Bug 22-24, 30-31, 34-36)

### Bug 22: 前端完全忽略 dialogues 列表 - 确认存在

**位置**: `frontend/windows/writing_desk/workspace/manga_handlers.py:435-445`

**验证结果**: 后端返回 `dialogues` 列表，前端读取 `panel.get('dialogue')` 扁平字段，永远为空。

### Bug 23: 音效细节只保存第一条 - 确认存在

**位置**: `frontend/windows/writing_desk/workspace/manga_handlers.py:446-465`

**验证结果**: `if not sound_effect_details: sound_effect_details.append(sfx)` 只在第一次循环追加。

### Bug 24: API 响应缺少 dialogue_language - 确认存在

**位置**: `backend/app/api/routers/writer/manga_prompt_v2.py:92-101`

**验证结果**: `GenerateResponse` 类型定义中没有 `dialogue_language` 字段。

### Bug 30: 漫画提示词语言在持久化后被重置为中文 - 确认存在

**位置**: `backend/app/repositories/manga_prompt_repository.py:250-305`

**验证结果**: `save_result` 不保存 `dialogue_language`，`get_result` 返回时该字段缺失，回退到默认值 `"chinese"`。

### Bug 31: 漫画提示词永远无法记录生成所基于的章节版本 - 确认存在

**位置**: `backend/app/services/manga_prompt/core/service.py:408-432`

**验证结果**: `_save_result` 不传递 `source_version_id`，数据库字段永远为 NULL。

### Bug 34: 正文版本切换后漫画内容不刷新 - 确认存在

**位置**: `frontend/windows/writing_desk/mixins/version_management_mixin.py:47-189`

**验证结果**: 版本切换只刷新正文，不调用 `_loadMangaDataAsync()`，漫画数据仍显示旧版本。

### Bug 35: 场景摘要/情感等元数据在生成结果中全部丢失 - 确认存在

**位置**: `backend/app/services/manga_prompt/prompt_builder/models.py:150-174`

**验证结果**: `PagePromptResult.to_dict()` 只保留 4 个字段，`scene_summary`/`mood` 等元数据未保存。

### Bug 36: 画格卡片的"P{页}-slot"标签永远显示为 -0 - 确认存在

**位置**: `backend/app/api/routers/writer/manga_prompt_v2.py:52-101`

**验证结果**: `PanelResponse` 没有 `slot_id` 字段，前端 `panel.get('slot_id', 0)` 始终返回 0。

---

## 六、UI 交互问题 (Bug 37)

### Bug 37: 场景卡片的"生成图片"按钮会直接崩溃 - 确认存在

**位置**: `frontend/windows/writing_desk/panels/manga/scene_card.py:99-116`

**验证结果**: 回调传递 `(scene_id, prompt_en, negative_prompt)` 三个参数，但 `_onGenerateImage` 期望接收 panel 字典并调用 `.get()`，导致 `'int' object has no attribute 'get'` 异常。

---

## 优先级建议

### P0 - 阻塞性问题（立即修复）
- Bug 1, 5, 8, 13, 14: 空白项目崩溃（影响核心功能）
- Bug 15, 16, 19: 完结项目无法编辑（用户体验严重受损）
- Bug 37: 场景卡片崩溃（界面直接报错）

### P1 - 数据一致性问题
- Bug 3, 4: 重试后数据不同步
- Bug 7: 生成失败丢失已选版本
- Bug 6, 31: 元数据丢失
- Bug 22, 24, 30, 35, 36: 漫画元数据丢失

### P2 - 功能缺失
- Bug 9: 无向量库时伏笔丢失
- Bug 10, 12: 缺少校验
- Bug 11: 摘要不持久化
- Bug 25, 26, 38, 40, 42: 版本过滤失效
- Bug 27: 删除分镜不清理图片

### P3 - 体验优化
- Bug 2: 用量统计不准确
- Bug 17: 文件名安全
- Bug 18, 28, 29, 41: 路径/URL 问题
- Bug 20, 21, 32: PDF 导出优化
- Bug 23, 33, 34, 39: 前端数据处理

---

## 结论

当前代码库中 **全部 42 个问题均确认存在**。建议按优先级分批修复，优先处理 P0 级别的阻塞性问题。
