# 空项目分析功能 - 实现计划

## 一、功能概述

为AFN添加"外部小说导入分析"功能，允许用户：
1. 创建空项目并上传TXT文件
2. 系统自动识别章节分隔并解析
3. 手动触发分析流程，从章节内容反推蓝图信息
4. 分析完成后项目进入WRITING状态，可续写或转漫画

### 用户确认的需求
- **导入方式**：上传TXT文件，系统自动识别章节分隔
- **分析触发**：手动点击"分析项目"按钮开始分析
- **目标状态**：分析完成后直接进入WRITING状态
- **分析数据**：生成每章的analysis_data，但暂不进行RAG向量化入库

---

## 二、分析流程设计

```
上传TXT文件
    ↓
解析章节（识别"第X章"等分隔符）
    ↓
创建Chapter + ChapterVersion（状态：pending分析）
    ↓
用户点击"开始分析"
    ↓
阶段1: 批量生成章节摘要（每批5章）
    ↓
阶段2: 根据摘要生成章节大纲(ChapterOutline)
    ↓
阶段3: 如果>=50章，生成分部大纲(PartOutline)
    ↓
阶段4: 根据所有信息反推蓝图（概览、世界观、角色、关系）
    ↓
阶段5: 生成每章的analysis_data（不入库RAG）
    ↓
更新项目状态为WRITING
```

---

## 三、后端实现

### 3.1 数据模型变更

**文件**: `backend/app/models/novel.py`

在 `NovelProject` 类中添加字段：

```python
# 导入分析相关字段
is_imported: Mapped[bool] = mapped_column(Boolean, default=False, doc="是否为外部导入项目")
import_analysis_status: Mapped[Optional[str]] = mapped_column(
    String(32), nullable=True, doc="导入分析状态: pending/analyzing/completed/failed"
)
import_analysis_progress: Mapped[Optional[dict]] = mapped_column(
    JSON, nullable=True, doc="分析进度信息"
)
```

### 3.2 新增API端点

**文件**: `backend/app/api/routers/novels/import_analysis.py` (新建)

| HTTP方法 | 端点 | 功能 |
|---------|------|------|
| POST | `/api/novels/{project_id}/import-txt` | 上传TXT文件，解析并创建章节 |
| POST | `/api/novels/{project_id}/analyze` | 启动分析任务 |
| GET | `/api/novels/{project_id}/analyze/status` | 获取分析进度 |
| POST | `/api/novels/{project_id}/analyze/cancel` | 取消分析任务 |

#### 3.2.1 TXT导入端点

```python
@router.post("/{project_id}/import-txt")
async def import_txt(
    project_id: str,
    file: UploadFile = File(...),
    novel_service: NovelService = Depends(get_novel_service),
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
):
    """
    上传TXT文件并解析章节

    返回:
    {
        "total_chapters": 50,
        "chapters": [
            {"chapter_number": 1, "title": "第一章 开端", "word_count": 3000},
            ...
        ],
        "parse_info": {
            "encoding": "utf-8",
            "pattern_used": "第X章",
            "warnings": []
        }
    }
    """
```

#### 3.2.2 分析启动端点

```python
@router.post("/{project_id}/analyze")
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    user: UserInDB = Depends(get_default_user),
):
    """
    启动项目分析（后台任务）

    返回:
    {
        "status": "started",
        "message": "分析任务已启动"
    }
    """
```

### 3.3 新增服务层

**目录**: `backend/app/services/import_analysis/` (新建)

```
import_analysis/
├── __init__.py
├── service.py              # 主服务，协调分析流程
├── txt_parser.py           # TXT解析器，章节分隔识别
├── chapter_summarizer.py   # 批量章节摘要生成
├── outline_generator.py    # 大纲生成服务
├── blueprint_extractor.py  # 蓝图反推服务
└── progress_tracker.py     # 进度跟踪
```

#### 3.3.1 TXT解析器 (`txt_parser.py`)

```python
class TxtParser:
    """TXT文件解析器"""

    # 章节分隔正则表达式（优先级从高到低）
    CHAPTER_PATTERNS = [
        (r'^第[一二三四五六七八九十百千\d]+章\s*[：:·\s]?\s*(.*)$', 'cn_chapter'),
        (r'^第[一二三四五六七八九十百千\d]+回\s*[：:·\s]?\s*(.*)$', 'cn_hui'),
        (r'^Chapter\s*(\d+)[：:.\s]*(.*)$', 'en_chapter'),
        (r'^【第[一二三四五六七八九十百千\d]+章】\s*(.*)$', 'cn_bracket'),
        (r'^(\d+)[\.、]\s*(.+)$', 'numbered'),
    ]

    def parse(self, content: str) -> ParseResult:
        """解析TXT内容"""

    def detect_encoding(self, file_bytes: bytes) -> str:
        """检测文件编码（使用chardet）"""

    def _cn_to_arabic(self, cn_str: str) -> int:
        """中文数字转阿拉伯数字"""
```

#### 3.3.2 主分析服务 (`service.py`)

```python
class ImportAnalysisService:
    """导入分析主服务"""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService,
    ):
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.parser = TxtParser()
        self.progress = ProgressTracker(session)

    async def import_txt(
        self,
        project_id: str,
        file_content: bytes,
        user_id: int,
    ) -> ImportResult:
        """
        导入TXT文件

        流程:
        1. 检测编码并解码
        2. 识别章节分隔
        3. 创建ChapterOutline + Chapter + ChapterVersion
        4. 设置 is_imported=True, import_analysis_status='pending'
        """

    async def start_analysis(
        self,
        project_id: str,
        user_id: int,
    ) -> None:
        """
        执行完整分析流程

        阶段:
        1. analyzing_chapters - 批量生成章节摘要
        2. generating_outlines - 更新章节大纲
        3. generating_part_outlines - 生成分部大纲（仅长篇）
        4. extracting_blueprint - 反推蓝图
        5. generating_analysis_data - 生成分析数据
        """

    async def _analyze_chapters_batch(
        self,
        chapters: List[Chapter],
        batch_size: int = 5,
    ) -> List[ChapterSummary]:
        """批量分析章节，每批5章"""

    async def _generate_outlines_from_summaries(
        self,
        summaries: List[ChapterSummary],
    ) -> None:
        """根据摘要更新章节大纲"""

    async def _generate_part_outlines(
        self,
        chapter_outlines: List[ChapterOutline],
        total_chapters: int,
    ) -> List[PartOutline]:
        """长篇小说：根据章节大纲生成分部大纲"""

    async def _extract_blueprint(
        self,
        chapters: List[Chapter],
        summaries: List[ChapterSummary],
        part_outlines: Optional[List[PartOutline]],
    ) -> Blueprint:
        """从章节内容反推蓝图"""

    async def _generate_analysis_data_batch(
        self,
        chapters: List[Chapter],
        user_id: int,
    ) -> None:
        """批量生成章节分析数据（不入库RAG）"""
```

#### 3.3.3 进度跟踪 (`progress_tracker.py`)

```python
class ProgressTracker:
    """分析进度跟踪"""

    STAGES = [
        'analyzing_chapters',
        'generating_outlines',
        'generating_part_outlines',
        'extracting_blueprint',
        'generating_analysis_data',
    ]

    async def update(
        self,
        project_id: str,
        stage: str,
        completed: int,
        total: int,
        message: str = None,
    ) -> None:
        """更新进度"""

    async def get_status(self, project_id: str) -> dict:
        """获取当前进度"""

    async def mark_completed(self, project_id: str) -> None:
        """标记完成"""

    async def mark_failed(self, project_id: str, error: str) -> None:
        """标记失败"""
```

进度数据结构：
```python
{
    "status": "analyzing",  # pending/analyzing/completed/failed
    "current_stage": "analyzing_chapters",
    "stages": {
        "analyzing_chapters": {"completed": 25, "total": 50, "status": "in_progress"},
        "generating_outlines": {"completed": 0, "total": 1, "status": "pending"},
        "generating_part_outlines": {"completed": 0, "total": 1, "status": "pending"},
        "extracting_blueprint": {"completed": 0, "total": 1, "status": "pending"},
        "generating_analysis_data": {"completed": 0, "total": 50, "status": "pending"}
    },
    "message": "正在分析第25/50章...",
    "started_at": "2024-01-01T00:00:00Z",
    "error": null
}
```

### 3.4 新增提示词模板

**目录**: `backend/prompts/`

#### 3.4.1 `chapter_summary_batch.md` - 批量章节摘要

```markdown
# 角色：高效章节摘要师

你是一位专业的小说编辑，需要为多个章节生成简短摘要。

## 输入格式
```json
{
  "novel_title": "小说标题",
  "chapters": [
    {"chapter_number": 1, "title": "章节标题", "content": "章节内容（前8000字）"},
    ...
  ]
}
```

## 输出格式
```json
{
  "summaries": [
    {
      "chapter_number": 1,
      "title": "章节标题",
      "summary": "100-150字摘要，包含核心情节、主要角色行动、重要信息披露"
    },
    ...
  ]
}
```

## 要求
1. 每个摘要100-150字
2. 保留核心情节转折
3. 记录主要角色行动
4. 标注重要信息披露
```

#### 3.4.2 `reverse_blueprint.md` - 蓝图反推

```markdown
# 角色：资深小说分析师

从完整的小说内容中提炼项目蓝图信息。

## 输入信息
- novel_title: 小说标题
- total_chapters: 总章节数
- chapter_summaries: 所有章节摘要列表
- part_outlines: 分部大纲（如有）
- sample_chapters: 抽样章节内容（首章、中间章、末章）

## 输出格式
```json
{
  "title": "小说标题",
  "genre": "题材类型（如：玄幻、都市、科幻等）",
  "style": "写作风格（如：轻松幽默、严肃沉重等）",
  "tone": "叙事基调",
  "target_audience": "目标读者",
  "one_sentence_summary": "一句话概括（30字以内）",
  "full_synopsis": "完整故事大纲（500-800字）",
  "world_setting": {
    "core_rules": "世界核心规则",
    "key_locations": [{"name": "地点名", "description": "描述"}],
    "factions": [{"name": "阵营名", "description": "描述"}]
  },
  "characters": [
    {
      "name": "角色名",
      "identity": "身份",
      "personality": "性格特点",
      "goals": "目标动机",
      "abilities": "能力特长"
    }
  ],
  "relationships": [
    {
      "character_from": "角色A",
      "character_to": "角色B",
      "description": "关系描述"
    }
  ]
}
```

## 分析原则
1. 从文本中提取，不虚构
2. 角色只包含主要人物（出场频繁的）
3. 世界观提取需有文本依据
4. 关系描述要具体
```

#### 3.4.3 `reverse_outline.md` - 大纲标准化

```markdown
# 角色：结构化大纲编辑

根据章节摘要，生成标准格式的章节大纲。

## 输入
```json
{
  "summaries": [
    {"chapter_number": 1, "title": "原标题", "summary": "摘要内容"},
    ...
  ]
}
```

## 输出
```json
{
  "outlines": [
    {
      "chapter_number": 1,
      "title": "标题（保留或优化）",
      "summary": "50-100字的标准化大纲摘要"
    }
  ]
}
```
```

#### 3.4.4 `reverse_part_outline.md` - 分部大纲反推

```markdown
# 角色：长篇小说结构分析师

根据章节大纲，将长篇小说划分为多个部分并生成分部大纲。

## 输入
- total_chapters: 总章节数
- chapter_outlines: 所有章节大纲

## 输出
```json
{
  "parts": [
    {
      "part_number": 1,
      "title": "部分标题",
      "start_chapter": 1,
      "end_chapter": 25,
      "summary": "本部分主要内容概述",
      "theme": "本部分主题",
      "key_events": ["关键事件1", "关键事件2"]
    }
  ]
}
```

## 划分原则
1. 每部分约25章（可根据剧情调整）
2. 以重要剧情转折点为分界
3. 每部分应有完整的小主题
```

### 3.5 依赖注入配置

**文件**: `backend/app/core/dependencies.py`

```python
async def get_import_analysis_service(
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
) -> ImportAnalysisService:
    from ..services.import_analysis import ImportAnalysisService
    return ImportAnalysisService(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )
```

### 3.6 路由注册

**文件**: `backend/app/api/routers/novels/__init__.py`

```python
from .import_analysis import router as import_analysis_router

# 在主路由中包含
router.include_router(import_analysis_router, tags=["import-analysis"])
```

---

## 四、前端实现

### 4.1 修改创建模式对话框

**文件**: `frontend/components/dialogs/create_mode_dialog.py`

添加第三个选项卡片：

```python
# 返回值常量
MODE_AI = 1       # AI辅助创作
MODE_FREE = 2     # 自由创作
MODE_IMPORT = 3   # 导入外部小说（新增）

# 在_setup_ui中添加导入卡片
self.import_card = self._create_mode_card(
    title="导入外部小说",
    description="上传已有的TXT小说文件，AI自动分析并提取蓝图、角色、大纲等信息",
    icon_text="TXT",
    is_recommended=False
)
self.import_card.mousePressEvent = lambda e: self._on_card_clicked(self.MODE_IMPORT)
cards_layout.addWidget(self.import_card)
```

### 4.2 新增API客户端Mixin

**文件**: `frontend/api/client/import_mixin.py` (新建)

```python
from typing import Dict, Any, Optional
import os


class ImportMixin:
    """导入分析 API Mixin"""

    def import_txt(
        self,
        project_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        上传TXT文件

        Args:
            project_id: 项目ID
            file_path: 本地文件路径

        Returns:
            {
                "total_chapters": 50,
                "chapters": [...],
                "parse_info": {...}
            }
        """
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/plain')}
            return self._request(
                'POST',
                f'/api/novels/{project_id}/import-txt',
                files=files,
                timeout=60,
            )

    def start_analysis(self, project_id: str) -> Dict[str, Any]:
        """启动分析"""
        return self._request('POST', f'/api/novels/{project_id}/analyze')

    def get_analysis_status(self, project_id: str) -> Dict[str, Any]:
        """获取分析状态"""
        return self._request('GET', f'/api/novels/{project_id}/analyze/status')

    def cancel_analysis(self, project_id: str) -> Dict[str, Any]:
        """取消分析"""
        return self._request('POST', f'/api/novels/{project_id}/analyze/cancel')
```

**文件**: `frontend/api/client/core.py`

```python
from .import_mixin import ImportMixin

class AFNAPIClient(
    NovelMixin,
    InspirationMixin,
    BlueprintMixin,
    OutlineMixin,
    ChapterMixin,
    OptimizationMixin,
    MangaMixin,
    ConfigMixin,
    ImageMixin,
    QueueMixin,
    PortraitMixin,
    ImportMixin,  # 新增
):
    ...
```

### 4.3 新增导入相关对话框

**文件**: `frontend/components/dialogs/import_dialogs.py` (新建)

```python
class ImportProgressDialog(QDialog):
    """TXT导入进度对话框 - 显示解析结果"""

    def __init__(self, parse_result: dict, parent=None):
        super().__init__(parent)
        self.parse_result = parse_result
        self._setup_ui()

    def _setup_ui(self):
        # 显示：
        # - 文件编码
        # - 识别到的章节数
        # - 章节列表预览（前10章）
        # - 确认/取消按钮
        pass


class AnalysisProgressDialog(QDialog):
    """分析进度对话框 - 显示各阶段进度"""

    progress_updated = pyqtSignal(dict)
    completed = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, project_id: str, client, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.client = client
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        # 显示5个阶段的进度条：
        # 1. 分析章节内容
        # 2. 生成章节大纲
        # 3. 生成分部大纲（长篇）
        # 4. 提取蓝图信息
        # 5. 生成分析数据
        pass

    def _start_polling(self):
        """启动轮询获取进度"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_status)
        self.timer.start(2000)  # 每2秒轮询

    def _poll_status(self):
        """轮询分析状态"""
        try:
            status = self.client.get_analysis_status(self.project_id)
            self.progress_updated.emit(status)

            if status['status'] == 'completed':
                self.timer.stop()
                self.completed.emit()
            elif status['status'] == 'failed':
                self.timer.stop()
                self.failed.emit(status.get('error', '分析失败'))
        except Exception as e:
            pass  # 忽略网络错误，继续轮询
```

### 4.4 修改首页处理导入流程

**文件**: `frontend/pages/home_page.py`

在创建项目流程中添加导入模式处理：

```python
def _on_create_project(self):
    """创建项目按钮点击"""
    dialog = CreateModeDialog(parent=self)
    result = dialog.exec()

    if result == CreateModeDialog.MODE_AI:
        self._create_ai_project()
    elif result == CreateModeDialog.MODE_FREE:
        self._create_free_project()
    elif result == CreateModeDialog.MODE_IMPORT:
        self._import_external_novel()  # 新增

def _import_external_novel(self):
    """导入外部小说"""
    # 1. 选择文件
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "选择小说文件",
        "",
        "文本文件 (*.txt);;所有文件 (*.*)"
    )
    if not file_path:
        return

    # 2. 输入项目名称
    title, ok = QInputDialog.getText(
        self, "项目名称", "请输入项目名称:",
        text=os.path.splitext(os.path.basename(file_path))[0]
    )
    if not ok or not title.strip():
        return

    # 3. 创建项目并上传文件
    self._do_import(title.strip(), file_path)

def _do_import(self, title: str, file_path: str):
    """执行导入"""
    # 显示加载对话框
    loading = LoadingDialog("正在解析文件...", self)
    loading.show()

    def do_work():
        # 创建项目
        project = self.client.create_novel(title=title, initial_prompt="")
        # 上传并解析TXT
        parse_result = self.client.import_txt(project['id'], file_path)
        return project, parse_result

    worker = AsyncWorker(do_work)
    worker.success.connect(lambda r: self._on_import_success(r, loading))
    worker.error.connect(lambda e: self._on_import_error(e, loading))
    worker.start()

def _on_import_success(self, result, loading):
    """导入成功"""
    loading.close()
    project, parse_result = result

    # 显示解析结果确认对话框
    dialog = ImportProgressDialog(parse_result, parent=self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # 跳转到项目详情页
        self.window().navigateTo('DETAIL', project_id=project['id'])
```

### 4.5 修改项目详情页

**文件**: `frontend/windows/novel_detail/main.py`

在概览Section添加分析按钮：

```python
def _setup_overview_section(self):
    # ... 现有代码 ...

    # 如果是导入项目且未分析，显示分析按钮
    if self.project.get('is_imported') and \
       self.project.get('import_analysis_status') == 'pending':
        self._add_analysis_button()

def _add_analysis_button(self):
    """添加分析按钮"""
    self.analyze_btn = QPushButton("开始分析")
    self.analyze_btn.setObjectName("primary_btn")
    self.analyze_btn.clicked.connect(self._on_start_analysis)
    # 添加到概览区域

def _on_start_analysis(self):
    """开始分析"""
    # 启动分析
    self.client.start_analysis(self.project_id)

    # 显示进度对话框
    dialog = AnalysisProgressDialog(
        project_id=self.project_id,
        client=self.client,
        parent=self
    )
    dialog.completed.connect(self._on_analysis_completed)
    dialog.failed.connect(self._on_analysis_failed)
    dialog.exec()

def _on_analysis_completed(self):
    """分析完成"""
    # 刷新页面
    self.refresh(project_id=self.project_id)
    # 显示成功消息
    QMessageBox.information(self, "完成", "项目分析完成！")
```

---

## 五、关键技术细节

### 5.1 章节分隔识别算法

```python
def detect_chapters(self, content: str) -> List[ChapterMatch]:
    """
    检测章节分隔

    策略:
    1. 尝试所有模式，统计匹配数量
    2. 选择匹配数量最多的模式
    3. 验证章节编号连续性
    4. 处理异常情况（无法识别时按固定字数分割）
    """
    results = []
    for pattern, name in self.CHAPTER_PATTERNS:
        matches = re.findall(pattern, content, re.MULTILINE)
        if matches:
            results.append({
                'pattern': name,
                'count': len(matches),
                'matches': matches
            })

    # 选择最佳模式（匹配数>=3）
    best = max(results, key=lambda x: x['count']) if results else None

    if not best or best['count'] < 3:
        # 无法识别，按固定字数分割（每5000字一章）
        return self._split_by_length(content, 5000)

    return self._extract_chapters_by_pattern(content, best['pattern'])
```

### 5.2 分批处理策略

```python
async def _analyze_in_batches(
    self,
    chapters: List[Chapter],
    batch_size: int = 5,
    max_retries: int = 2,
) -> List[ChapterSummary]:
    """
    分批处理章节分析

    策略:
    1. 每批5章，控制单次LLM调用的输入长度
    2. 每章内容截取前8000字（约12000 tokens）
    3. 失败重试2次，使用指数退避
    4. 单批超时3分钟
    """
    results = []
    total = len(chapters)

    for i in range(0, total, batch_size):
        batch = chapters[i:i+batch_size]

        for attempt in range(max_retries + 1):
            try:
                batch_results = await self._process_batch(batch)
                results.extend(batch_results)

                # 更新进度
                await self.progress.update(
                    self.project_id,
                    stage='analyzing_chapters',
                    completed=min(i + batch_size, total),
                    total=total,
                    message=f"正在分析第{i+1}-{min(i+batch_size, total)}/{total}章"
                )
                break

            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"批次处理失败: {e}")
                    # 使用降级摘要
                    results.extend(self._create_fallback_summaries(batch))
                else:
                    await asyncio.sleep(2 ** attempt)

    return results
```

### 5.3 蓝图反推策略

```python
async def _extract_blueprint(
    self,
    chapters: List[Chapter],
    summaries: List[ChapterSummary],
    part_outlines: Optional[List[PartOutline]],
) -> Blueprint:
    """
    从章节内容反推蓝图

    策略:
    1. 抽样章节：首章 + 每10章抽1章 + 末章
    2. 分步提取，每步独立LLM调用（提高成功率）
    3. 合并结果生成完整蓝图
    """
    # 1. 抽样章节
    sample_indices = self._select_sample_chapters(len(chapters))
    sample_content = [
        {"chapter_number": chapters[i].chapter_number,
         "content": chapters[i].selected_version.content[:10000]}
        for i in sample_indices
    ]

    # 2. 构建输入数据
    input_data = {
        "novel_title": self.project.title,
        "total_chapters": len(chapters),
        "chapter_summaries": [s.model_dump() for s in summaries],
        "sample_chapters": sample_content,
    }
    if part_outlines:
        input_data["part_outlines"] = [p.model_dump() for p in part_outlines]

    # 3. 调用LLM生成蓝图
    prompt = await self.prompt_service.get_prompt("reverse_blueprint")
    response = await call_llm_json(
        self.llm_service,
        LLMProfile.BLUEPRINT,
        system_prompt=prompt,
        user_content=json.dumps(input_data, ensure_ascii=False),
        user_id=self.user_id,
    )

    # 4. 解析并返回
    blueprint_data = parse_llm_json_or_fail(response, "蓝图提取失败")
    return Blueprint(**blueprint_data)
```

### 5.4 analysis_data生成（不入库RAG）

```python
async def _generate_analysis_data_batch(
    self,
    chapters: List[Chapter],
    user_id: int,
) -> None:
    """
    批量生成章节分析数据

    与正常流程区别:
    - 只生成analysis_data，存入chapter.analysis_data
    - 不调用VectorStoreService入库
    - 不更新CharacterStateIndex和ForeshadowingIndex
    """
    analysis_service = ChapterAnalysisService(self.session)
    total = len(chapters)

    for i, chapter in enumerate(chapters):
        try:
            # 获取章节内容
            content = chapter.selected_version.content

            # 调用分析服务
            analysis_data = await analysis_service.analyze_chapter(
                content=content,
                title=self._get_chapter_title(chapter),
                chapter_number=chapter.chapter_number,
                novel_title=self.project.title,
                user_id=user_id,
                timeout=120.0,  # 单章2分钟超时
            )

            # 只保存到chapter.analysis_data
            if analysis_data:
                chapter.analysis_data = analysis_data.model_dump()

            # 更新进度
            await self.progress.update(
                self.project_id,
                stage='generating_analysis_data',
                completed=i + 1,
                total=total,
            )

        except Exception as e:
            logger.warning(f"章节{chapter.chapter_number}分析失败: {e}")
            # 继续处理下一章

    await self.session.commit()
```

---

## 六、错误处理

### 6.1 可恢复错误
- **单个章节分析失败**：跳过，使用降级摘要
- **批次超时**：重试2次后使用降级结果
- **LLM返回格式错误**：尝试宽松解析

### 6.2 不可恢复错误
- **文件编码无法识别**：返回错误，提示用户转换编码
- **无法识别任何章节**：返回错误，建议手动分割或检查格式
- **项目不存在**：返回404

### 6.3 取消处理
- 在每个批次处理前检查取消标志
- 取消时保存已完成的进度

---

## 七、实现顺序

### 阶段1：基础导入功能（2-3天）
1. 添加NovelProject模型字段
2. 实现TXT解析器(txt_parser.py)
3. 实现导入API端点(import-txt)
4. 前端：修改CreateModeDialog，添加导入选项
5. 前端：实现文件选择和上传流程

### 阶段2：分析服务核心（3-4天）
1. 添加提示词模板（4个）
2. 实现进度跟踪(progress_tracker.py)
3. 实现批量摘要生成(chapter_summarizer.py)
4. 实现大纲生成(outline_generator.py)
5. 实现蓝图反推(blueprint_extractor.py)
6. 实现主分析服务(service.py)

### 阶段3：前端进度展示（2天）
1. 实现ImportProgressDialog（解析结果确认）
2. 实现AnalysisProgressDialog（分析进度）
3. 修改项目详情页，添加分析按钮
4. 实现进度轮询逻辑

### 阶段4：完善和测试（1-2天）
1. analysis_data批量生成
2. 取消功能
3. 错误处理完善
4. 边界情况测试

---

## 八、文件变更清单

### 新建文件
```
backend/app/services/import_analysis/
├── __init__.py
├── service.py
├── txt_parser.py
├── chapter_summarizer.py
├── outline_generator.py
├── blueprint_extractor.py
└── progress_tracker.py

backend/app/api/routers/novels/import_analysis.py
backend/prompts/chapter_summary_batch.md
backend/prompts/reverse_blueprint.md
backend/prompts/reverse_outline.md
backend/prompts/reverse_part_outline.md

frontend/api/client/import_mixin.py
frontend/components/dialogs/import_dialogs.py
```

### 修改文件
```
backend/app/models/novel.py                    # 添加导入相关字段
backend/app/core/dependencies.py               # 添加依赖注入
backend/app/api/routers/novels/__init__.py     # 注册新路由

frontend/api/client/core.py                    # 添加ImportMixin
frontend/components/dialogs/create_mode_dialog.py  # 添加导入选项
frontend/components/dialogs/__init__.py        # 导出新对话框
frontend/pages/home_page.py                    # 添加导入流程
frontend/windows/novel_detail/main.py          # 添加分析按钮
```
