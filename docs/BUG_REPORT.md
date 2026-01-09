# 小说生成工作流潜在问题记录

以下条目为 2026-01-04 复核后仍然存在的缺陷。此前文档中编号 1-9、11-15、18、21-25、30-33 所描述的 Bug 已在最新代码中修复或无法复现，故予以移除。

## 1. 删除章节后项目状态不会回退

- **位置**：`backend/app/api/routers/writer/chapter_management.py:528-590`、`backend/app/services/novel_service.py:458-503`
- **问题**：`NovelService.check_and_update_completion_status` 虽然新增了“completed → writing”的降级逻辑，但删除章节的路由完全没有调用它，也没有显式执行 `transition_project_status`。项目一旦到达 `ProjectStatus.COMPLETED`，删除章节只会清空版本/索引，不会触发任何状态更新，导致章节生成/重试接口一直因为 `validate_project_status(... CHAPTER_GENERATION_STATES)` 拒绝请求。
- **建议**：在 `delete_chapters` 成功后调用 `check_and_update_completion_status(project_id, user_id)`，或直接注入 `NovelService.transition_project_status` 在删除动作内检测并降级状态。
- **验证情况**：✅ `chapter_management.delete_chapters` 在执行 `novel_service.delete_chapters` 与索引/向量清理后直接 `return`；`NovelService.delete_chapters` 也只是代理到 `ChapterVersionService.delete_chapters`，整个调用链没有任何状态回退，验证了完结项目无法重新生成章节。

## 2. 生成漫画图片时永远不写入 `chapter_version_id`

- **位置**：`frontend/windows/writing_desk/workspace/manga_handlers.py:396-840`、`frontend/api/client/image_mixin.py:137-233`
- **问题**：后端的 `ImageGenerationRequest` 和 `GeneratedImage` 模型都支持 `chapter_version_id`，但前端 `_onGenerateImage`、`_processNextBatchImage`、`_onPreviewPrompt` 以及调用 `generate_scene_image` 的所有路径完全没有传入当前选中版本 ID。结果数据库中所有图片的 `chapter_version_id` 一直是 `NULL`，后端虽然具备按照版本过滤/清理的能力，却无法发挥作用。
- **建议**：在加载章节数据时缓存 `chapter.selected_version_id`，并在单张/批量生成、预览提示词等请求体中统一传入该 ID；同时保存到 UI 状态，以便导出或删除图片时也能识别所属版本。
- **验证情况**：✅ `generate_scene_image` 虽然在 `frontend/api/client/image_mixin.py:151-233` 已加入 `chapter_version_id` 参数，但 `manga_handlers.py:396-554`、`705-840` 的所有调用都没有提供该字段，导致后端始终收到 `None`。

## 3. 漫画 PDF 请求仍然无法指定章节版本

- **位置**：`frontend/windows/writing_desk/workspace/manga_handlers.py:600-624`、`frontend/api/client/image_mixin.py:420-452`
- **问题**：专业/简单 PDF 导出已经支持 `chapter_version_id` 过滤，但 `_onGenerateMangaPDF` 仍旧只传入 `project_id`、`chapter_number`，完全忽略版本信息。即便后端修复了 `generate_chapter_manga_pdf` 与 `generate_professional_manga_pdf` 的过滤逻辑，桌面端也无法触发，导出的永远是全部历史图片。
- **建议**：在漫画 Tab 中提供版本选择（至少默认使用当前选中章节的版本 ID），并在 `generate_chapter_manga_pdf` 请求体中附带 `chapter_version_id`。
- **验证情况**：✅ `frontend/api/client/image_mixin.py:420-452` 已接受 `chapter_version_id` 并写入 `data`，但 `_onGenerateMangaPDF`（`manga_handlers.py:600-624`）调用时只传递章节号，前端 UI 也没有任何版本下拉框，证明功能仍不可用。

## 4. 漫画 PDF 下载链接在远程环境依旧失效

- **位置**：`backend/app/api/routers/image_generation.py:536-568`、`frontend/api/client/core.py:91-104`、`frontend/windows/writing_desk/workspace/manga_handlers.py:640-672`
- **问题**：后端依然返回形如 `/api/image-generation/export/download/{name}` 的相对路径，同时桌面端 `_onDownloadPDF` 忽略响应里的 `download_url`，一律调用 `self.api_client.get_export_download_url(file_name)`，而 `AFNAPIClient` 的 `base_url` 在 `APIClientManager` 中固定为 `http://127.0.0.1:8123`。一旦用户把后端部署到远程服务器或通过反向代理公开服务，桌面端仍然会在本机拼出 `http://127.0.0.1:8123/api/...` 并尝试用系统浏览器打开，下载请求自然失败。
- **建议**：后端直接返回绝对 URL，或前端改为复用响应中的 `download_url` 并允许用户配置 API 基础地址；同时在设置页暴露 base_url，而不是写死 localhost。
- **验证情况**：✅ `image_generation.py:558` 只提供相对路径；`frontend/api/client/core.py:91-104` 把 `base_url` 写死在 `AFNAPIClient()` 构造函数里，`APIClientManager` 的所有调用都未覆盖该参数；`_onDownloadPDF` 最终执行 `subprocess.Popen(['start','', download_url])`，其中 `download_url` 永远是 `http://127.0.0.1:8123/...`，证实远程环境无法下载。

## 5. 漫画 PDF 预览依赖服务端本地路径

- **位置**：`backend/app/api/routers/image_generation.py:536-568`、`frontend/windows/writing_desk/panels/manga/pdf_tab.py:150-360`
- **问题**：`get_latest_chapter_manga_pdf` 返回的 `file_path` 是服务端磁盘路径，`PdfTabMixin` 直接在本地调用 `fitz.open(pdf_path)`。当后端运行在 Docker/云服务器或 Windows/Linux 混合环境时，前端根本无法访问该文件，PDF 区域只会报错“文件不存在”。
- **建议**：返回可下载的 HTTP 链接并在前端先下载到临时目录，再交给 PyMuPDF 渲染，或提供单独的预览 API。
- **验证情况**：✅ `pdf_tab.py:150-200` 直接将 `pdf_info['file_path']` 交给 `_create_pdf_preview` 并由 `fitz.open(pdf_path)` 打开；`get_latest_chapter_manga_pdf` 不提供任何可访问的 URL，说明前端永远需要共享文件系统才能预览。

## 6. PDF 导出完全忽略图片选中状态

- **位置**：`backend/app/services/image_generation/pdf_export.py:320-420, 561-638`、`backend/app/api/routers/image_generation.py:445-458`
- **问题**：后端提供 `/images/{id}/toggle-selection` 接口维护 `GeneratedImage.is_selected`，但简单模式与专业模式的查询都只按 `project_id/chapter_number` 排序，既不筛选 `is_selected=True`，也不会优先使用最新图片。专业模式更是在构建 `panel_image_map` 时一旦遇到某个 `panel_id` 的第一张图片就终止后续图片，用户手动选中的高质量图片完全不会出现在 PDF 中。
- **建议**：查询图片时优先取 `is_selected=True` 的记录，若不存在再回退到最新图片；专业模式应按 `panel_id` 聚合并根据选中/更新顺序选择图像。
- **验证情况**：✅ `pdf_export.py:332-420` 与 `561-638` 的查询语句都没有 `is_selected` 条件；专业模式的 `panel_image_map` 只在 `panel_id not in panel_image_map` 时写入第一张图片，证明用户的选中操作全部被忽略。

## 7. 场景摘要与情感等元数据在持久化过程中被丢弃

- **位置**：`backend/app/services/manga_prompt/prompt_builder/models.py:140-200`、`backend/app/repositories/manga_prompt_repository.py:273-320`、`frontend/windows/writing_desk/panels/manga/scene_card.py:160-220`
- **问题**：`PageStoryboard` 原本生成 `scene_summary`、`mood`、`importance` 等字段，但 `PagePromptResult.to_dict()` 仅保留 `layout_description/reading_flow`，`MangaPromptRepository.save_result` 写入 `scenes` 时也只保存这四个字段。前端 `scene_card` 需要展示“场景摘要”“情感标签”等信息，却永远读不到任何数据，导致 UI 始终空白。
- **建议**：在模型/持久层/API 中同步支持 `scene_summary`、`mood`、`importance`、`page_purpose`、`panel_info` 等字段，读取时端到端返回这些元数据。
- **验证情况**：✅ `PagePromptResult.to_dict()`（`prompt_builder/models.py:150-175`）只返回 4 个字段；`MangaPromptRepository.save_result`（`273-320` 行）保存的 scene 信息同样只有页码和布局；而 `scene_card.py:160-220` 多处访问 `scene_summary`、`emotion` 等键，证实数据链路中被丢弃。

## 8. 画格槽位 `slot_id` 仍然缺失

- **位置**：`frontend/windows/writing_desk/panels/manga/prompt_tab.py:317-344`、`backend/app/api/routers/writer/manga_prompt_v2.py:52-120`
- **问题**：前端画格标签展示 `P{page_number}-{slot_id}`，但 `PanelResponse` 仍未提供 `slot_id` 字段，也没有任何地方推导该值。即使后端数据库 `ChapterMangaPrompt.panels` 中含有 `slot_id`，在 `_convert_to_response` 阶段被完全忽略，导致界面始终显示 `P1-0, P2-0`，用户无法判断画格在页面中的位置。
- **建议**：在 `PanelPrompt`/`PanelResponse` 中增加 `slot_id`（或由 `layout_slot` 推导一个稳定编号），并在前端/导出逻辑中统一使用，确保 UI 与 PDF 排版一致。
- **验证情况**：✅ `PanelResponse`（`manga_prompt_v2.py:52-105`）没有 `slot_id` 字段，`_convert_to_response` 也没有写入；`prompt_tab.py:317-344` 仍旧调用 `panel.get('slot_id', 0)`，因此标签永远是 `-0`。

## 9. 章节图片加载接口仍然混合所有版本

- **位置**：`frontend/windows/writing_desk/workspace/manga_handlers.py:201-234`、`frontend/api/client/image_mixin.py:304-318`、`backend/app/api/routers/image_generation.py:399-427`
- **问题**：后端 `GET /novels/{project_id}/chapters/{chapter_number}/images` 已经支持 `chapter_version_id` 和 `include_legacy` 查询参数（默认只返回匹配版本的图片），但 `_loadChapterImages` 始终调用 `self.api_client.get_chapter_images(project_id, chapter_number)`，API 客户端也没有参数用于传入版本 ID。即便用户在新版本下重新生成图片，加载列表时仍会把所有历史版本的图片一起返回，画格卡片与 PDF 导出界面永远无法区分“当前正文版本”与旧版本，前面 Bug #2/#3 的版本追溯工作也无法验证。
- **建议**：为 `get_chapter_images` 加入可选的 `chapter_version_id`（以及 `include_legacy`）参数，`WDWorkspace` 应该读取当前章节的 `selected_version_id`（`ChapterDisplayMixin.displayChapter` 已缓存 `_current_version_id`），并在加载图片、刷新图片等场景统一传入，从而只展示当前版本的图片。
- **验证情况**：✅ 路由定义（`image_generation.py:399-427`）接受 `chapter_version_id` 并传给 `ImageGenerationService.get_chapter_images`；前端 `_loadChapterImages` 在 `manga_handlers.py:201-234` 只传递项目和章节；API 客户端 `get_chapter_images` 的签名也没有版本参数，确认现状下永远返回混合数据。

## 10. 桌面端无法连接自定义后端地址

- **位置**：`frontend/api/client/core.py:91-105`、`frontend/api/manager.py:41-60`、`frontend/utils/config_manager.py:61-75`
- **问题**：`AFNAPIClient` 的构造函数把 `base_url` 默认写死为 `http://127.0.0.1:8123`，`APIClientManager.get_client()` 也从未注入用户配置。虽然 `ConfigManager` 暴露了 `get_api_base_url/set_api_base_url`，设置页面也允许填写 API 地址，但整个代码库没有任何地方读取这个值，导致桌面端只能访问本机 FastAPI，无法连接远程部署或容器化后的后端。前面 Bug #4 针对 PDF 下载链接已经暴露该问题，但更根本的是所有 REST/SSE 请求都固定在 localhost，用户在不同机器运行前后端时根本无法使用应用。
- **建议**：在应用启动时读取 `ConfigManager.get_api_base_url()`，将其传递给 `AFNAPIClient`（`APIClientManager` 持有单例时也要监听设置变更），同时在设置界面提供保存按钮以便实时更新 `base_url`。此外，生成下载 URL、SSE 等地方都应基于该配置。
- **验证情况**：✅ `frontend/api/client/core.py:91-105` 直接使用默认参数；`APIClientManager.get_client` 在创建实例时没有引用任何配置；`ConfigManager.get_api_base_url` 以及对应的 settings UI 从未被调用，证明当前版本无法连接远程后端。

## 11. 漫画图片和缩略图只能在本机读取文件，远程后端无法显示

- **位置**：`frontend/windows/writing_desk/workspace/manga_handlers.py:201-255`、`frontend/windows/writing_desk/panels/manga/pdf_tab.py:423-446`、`backend/app/api/routers/image_generation.py:363-420`
- **问题**：`_loadChapterImages` 忽略后端返回的 `GeneratedImageInfo.url`，而是硬编码从前端源码目录回到 `backend/storage/generated_images/...` 获取 `local_path`。这要求前后端共享同一文件系统（甚至是相对目录结构一致）。一旦后端部署到远程服务器或 Docker 容器，桌面应用本地并不存在这些图片文件，`local_path` 会指向一个不存在的路径，漫画卡片和图片预览因此全部失效。同时，PDF Tab 中预览单张图片仍然依赖 `image_data['local_path']`，完全没有网络回退。
- **建议**：前端应优先使用接口返回的 `url`（通过 `self.api_client.base_url` 拼接）来加载/下载图片；只有在本地共享文件系统时才使用 `local_path`。同时在 PDF Tab 的缩略图和预览中也要支持 HTTP 下载，避免远程部署无法查看任何内容。
- **验证情况**：✅ `backend/app/api/routers/image_generation.py:363-420` 已在 `GeneratedImageInfo` 中提供 `url=f"/api/image-generation/files/{project_id}/chapter_{chapter_number}/scene_{img.scene_id}/{img.file_name}"`；但 `_loadChapterImages`（`manga_handlers.py:201-255`）始终尝试 `os.path.join(base_dir, 'backend', 'storage', 'generated_images', file_path)` 并写入 `local_path`，`pdf_tab.py:438` 以及卡片渲染全部读取 `local_path`。远程环境下该路径不存在，导致图片永远无法显示。

## 12. 小说详情的章节列表阻塞主线程，加载或导入时整个 UI 卡死

- **位置**：`frontend/windows/novel_detail/sections/chapters_section.py:320-338`、`frontend/windows/novel_detail/sections/chapters_section.py:520-554`
- **问题**：章节列表在选中章节或导入章节时直接调用 `self.api_client.get_chapter` / `import_chapter`，而这两个方法内部使用 `requests` 同步阻塞网络。Unlike 写作台 `ChapterDisplayMixin`，这里没有使用 `AsyncAPIWorker` 或后台线程。只要后端响应慢、网络抖动、章节内容较大，整个 PyQt UI 就会冻结，所有窗口无法响应，严重影响体验。
- **建议**：与写作台章节加载一致，使用 `AsyncAPIWorker` 在后台线程调用 API，并在回调里更新 UI；导入章节也应该在任务完成后通知 UI，避免阻塞事件循环。
- **验证情况**：✅ `_loadChapterDetail`（`chapters_section.py:320-338`）直接在主线程调用 `self.api_client.get_chapter` 并缓存结果，没有任何异步处理；`_onImportChapter`（`520-554`）同样在按钮回调中同步执行 `self.api_client.import_chapter`。这与写作台 `ChapterDisplayMixin._do_load_chapter`（使用 `AsyncAPIWorker`）形成对比，证明小说详情页的网络请求会锁死 UI。

## 13. 新生成图片的下载 URL 仍然指向不存在的 `/api/images/...`

- **位置**：`backend/app/services/image_generation/service.py:613-621`、`backend/app/api/routers/image_generation.py:674-693`
- **问题**：图片生成服务在返回 `GeneratedImageInfo` 时硬编码 `url=f"/api/images/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}"`，但路由实际暴露在 `/api/image-generation/files/...`。调用 `/api/image-generation/novels/.../generate` 或批量生成接口后，响应中的 `images[i].url` 永远 404，前端若尝试直接预览刚生成的图片会立即失败，只能重新加载列表并依赖后端在列表响应里重新拼出的正确 URL。
- **建议**：与 `get_scene_images`/`get_chapter_images` 保持一致，统一通过 `f"/api/image-generation/files/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}"`（或统一的 helper）构造访问路径，确保实时生成的返回值即可使用。
- **验证情况**：✅ 路由文件（`image_generation.py:674-693`）只注册了 `/api/image-generation/files/...` 和 `/api/image-generation/files/{image_path}` 两条路径，项目中不存在 `/api/images/...`；而 `ImageGenerationService.save_generated_images`（`service.py:613-621`）仍返回旧的 `/api/images/...` URL，说明新生成图片的链接必然指向不存在的路由。

## 14. 项目接口不返回 `selected_version_id`，前端无法得知真实章节版本 ID

- **位置**：`backend/app/serializers/novel_serializer.py:332-382`、`backend/app/schemas/novel.py:164-172`、`frontend/windows/writing_desk/workspace/chapter_display.py:234-252`
- **问题**：`ChapterSchema` 仅包含 `selected_version`（版本索引）与 `versions`（纯文本列表），序列化时根本没有输出 `chapter.selected_version_id` 或每个版本的数据库 ID。写作台在 `displayChapter` 中试图读取 `chapter_data['selected_version_id']` 来缓存当前版本并传递给漫画图片/PDF 接口，但该字段永远不存在，只能得到 `None`。结果前端即使补齐了 `chapter_version_id` 参数，也没有任何来源可以获取有效 ID，所有需要“按正文版本过滤”的接口都无法工作（Bug #2/#3/#9/#10/#11/#13 都依赖这一字段）。
- **建议**：在 `ChapterSchema` 中增加 `selected_version_id`（以及版本列表的 `version_ids` 或 `versions: List[Dict]`），序列化时直接写入 `chapter.selected_version_id`，使前端能拿到真实 ID 并在生成图片、导出 PDF、清理旧图等场景中传入。必要时为每个版本附带 `version_id` 与元数据，避免只剩文本内容。
- **验证情况**：✅ `ChapterSchema`（`backend/app/schemas/novel.py:164-172`）只有 `selected_version` 整数索引，没有任何 ID 字段；`NovelSerializer.build_chapter_schema`（`serializers/novel_serializer.py:332-382`）也只计算 `selected_version_idx` 并返回，不曾把 `chapter.selected_version_id` 放入响应。写作台 `displayChapter`（`chapter_display.py:234-252`）调用 `chapter_data.get('selected_version_id')` 时恒为 `None`，证实当前 API 无法提供章节版本 ID。
