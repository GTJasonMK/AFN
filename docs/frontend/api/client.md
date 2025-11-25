
# frontend/api/client.py

## 模块概述

Arboris Novel API 客户端封装模块，提供与后端 FastAPI 服务交互的所有方法。该客户端使用 `requests` 库进行 HTTP 通信，无需认证，专为 PyQt 桌面应用设计。

**核心功能：**
- 小说项目管理（CRUD操作）
- 概念对话（灵感模式）
- 蓝图生成与优化
- 章节大纲生成
- 章节内容生成与评审
- LLM配置管理
- 异步任务管理
- 文件导出功能

**技术特点：**
- 统一的错误处理
- 可配置的超时时间
- 静默状态码支持
- Session复用提高性能

## 主要类

### ArborisAPIClient

Arboris Novel API 客户端类，封装所有后端API调用。

#### 初始化

```python
def __init__(self, base_url: str = "http://127.0.0.1:8123"):
    """
    初始化API客户端

    Args:
        base_url: 后端服务地址
    """
    self.base_url = base_url.rstrip('/')
    self.session = requests.Session()
    self.session.headers.update({
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    })
```

#### 内部方法

**_request() - 发送HTTP请求（内部方法）**

```python
def _request(
    self,
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    timeout: int = 300,
    silent_status_codes: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    发送HTTP请求

    Args:
        method: HTTP方法
        endpoint: API端点
        data: 请求体数据
        params: URL参数
        timeout: 超时时间（秒）
        silent_status_codes: 静默处理的状态码列表（不记录错误日志）

    Returns:
        响应JSON数据

    Raises:
        requests.RequestException: 请求失败
    """
```

**设计特点：**
- 统一的请求处理逻辑
- 自动JSON序列化和反序列化
- 可配置的静默错误处理
- 详细的日志记录

## API方法分类

### 1. 健康检查

**health_check() - 健康检查**

```python
def health_check(self) -> Dict[str, Any]:
    """健康检查"""
    return self._request('GET', '/health')
```

**返回示例：**
```json
{
    "status": "healthy",
    "app": "Arboris Novel",
    "version": "1.0.0-pyqt",
    "edition": "Desktop (PyQt)"
}
```

### 2. 小说项目管理

**create_novel() - 创建小说项目**

```python
def create_novel(self, title: str, initial_prompt: str) -> Dict[str, Any]:
    """
    创建小说项目

    Args:
        title: 小说标题
        initial_prompt: 初始提示词

    Returns:
        项目信息
    """
    return self._request('POST', '/api/novels', {
        'title': title,
        'initial_prompt': initial_prompt
    })
```

**get_novels() - 获取项目列表**

```python
def get_novels(self) -> List[Dict[str, Any]]:
    """获取项目列表"""
    return self._request('GET', '/api/novels')
```

**get_novel() - 获取项目详情**

```python
def get_novel(self, project_id: str) -> Dict[str, Any]:
    """
    获取项目详情

    Args:
        project_id: 项目ID

    Returns:
        项目详细信息
    """
    return self._request('GET', f'/api/novels/{project_id}')
```

**update_project() - 更新项目信息**

```python
def update_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新项目信息

    Args:
        project_id: 项目ID
        data: 更新数据

    Returns:
        更新后的项目信息
    """
    return self._request('PATCH', f'/api/novels/{project_id}', data)
```

**delete_novels() - 删除项目**

```python
def delete_novels(self, project_ids: List[str]) -> Dict[str, Any]:
    """
    删除项目

    Args:
        project_ids: 项目ID列表

    Returns:
        删除结果
    """
    return self._request('DELETE', '/api/novels', project_ids)
```

**export_novel() - 导出整本小说**

```python
def export_novel(self, project_id: str, format_type: str = 'txt') -> str:
    """
    导出整本小说

    Args:
        project_id: 项目ID
        format_type: 导出格式（txt或markdown）

    Returns:
        导出的文本内容
    """
    url = f"{self.base_url}/api/novels/{project_id}/export"
    response = self.session.get(url, params={'format': format_type}, timeout=60)
    response.raise_for_status()
    return response.text
```

### 3. 概念对话（灵感模式）

**novel_concept_converse() - 灵感模式概念对话**

```python
def novel_concept_converse(
    self,
    project_id: str,
    user_input: Optional[Dict] = None,
    conversation_state: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    灵感模式概念对话（便捷方法）

    Args:
        project_id: 项目ID
        user_input: 用户输入对象，格式为 { id: str, value: str } 或 None
        conversation_state: 对话状态

    Returns:
        AI响应
    """
    data = {
        'user_input': user_input if user_input else {},
        'conversation_state': conversation_state if conversation_state is not None else {}
    }

    return self._request(
        'POST',
        f'/api/novels/{project_id}/concept/converse',
        data,
        timeout=240
    )
```

**使用示例：**
```python
# 开始对话
response = client.novel_concept_converse(
    project_id="proj_123",
    user_input={"id": "title", "value": "修仙世界的奇幻冒险"}
)

# 继续对话
response = client.novel_concept_converse(
    project_id="proj_123",
    user_input={"id": "genre", "value": "玄幻"},
    conversation_state=response.get("conversation_state")
)
```

### 4. 蓝图生成

**generate_blueprint() - 生成蓝图**

```python
def generate_blueprint(
    self,
    project_id: str,
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """
    生成蓝图

    Args:
        project_id: 项目ID
        force_regenerate: 是否强制重新生成

    Returns:
        蓝图数据
    """
    return self._request(
        'POST',
        f'/api/novels/{project_id}/blueprint/generate',
        params={'force_regenerate': force_regenerate},
        timeout=480
    )
```

**generate_blueprint_async() - 异步生成蓝图**

```python
def generate_blueprint_async(
    self,
    project_id: str,
    force_regenerate: bool = False,
    async_mode: bool = True
) -> Dict[str, Any]:
    """
    异步生成蓝图

    Args:
        project_id: 项目ID
        force_regenerate: 是否强制重新生成
        async_mode: 是否使用异步模式（默认True）

    Returns:
        异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        同步模式：完整蓝图数据
    """
    params = {
        'force_regenerate': force_regenerate,
        'async_mode': async_mode
    }
    return self._request(
        'POST',
        f'/api/novels/{project_id}/blueprint/generate',
        params=params,
        timeout=600 if not async_mode else 30
    )
```

**update_blueprint() - 更新蓝图**

```python
def update_blueprint(
    self,
    project_id: str,
    blueprint_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    更新蓝图

    Args:
        project_id: 项目ID
        blueprint_data: 蓝图数据

    Returns:
        更新结果
    """
    return self._request(
        'PATCH',
        f'/api/novels/{project_id}/blueprint',
        blueprint_data
    )
```

**refine_blueprint() - 优化蓝图**

```python
def refine_blueprint(
    self,
    project_id: str,
    prompt: str
) -> Dict[str, Any]:
    """
    优化蓝图

    Args:
        project_id: 项目ID
        prompt: 优化提示

    Returns:
        优化后的蓝图
    """
    return self._request(
        'POST',
        f'/api/novels/{project_id}/blueprint/refine',
        {'prompt': prompt},
        timeout=480
    )
```

### 5. 章节大纲

**generate_part_outlines() - 生成部分大纲**

```python
def generate_part_outlines(
    self,
    project_id: str,
    total_chapters: int,
    chapters_per_part: int = 25
) -> Dict[str, Any]:
    """
    生成部分大纲

    Args:
        project_id: 项目ID
        total_chapters: 小说总章节数
        chapters_per_part: 每个部分的章节数（默认25）

    Returns:
        大纲数据
    """
    data = {
        'total_chapters': total_chapters,
        'chapters_per_part': chapters_per_part
    }
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/parts/generate',
        data=data,
        timeout=300
    )
```

**get_part_outline_generation_status() - 查询部分大纲生成状态**

```python
def get_part_outline_generation_status(self, project_id: str) -> Dict[str, Any]:
    """
    查询部分大纲生成状态

    Args:
        project_id: 项目ID

    Returns:
        状态数据：
        {
            "status": "idle|generating|completed|failed",
            "progress": 0-100,
            "error": "错误信息",
            "has_part_outlines": bool,
            "part_count": int
        }
    """
    try:
        return self._request(
            'GET',
            f'/api/writer/novels/{project_id}/parts/generation-status',
            silent_status_codes=[404]
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {
                "status": "idle",
                "progress": 0,
                "error": None,
                "has_part_outlines": False,
                "part_count": 0
            }
        raise
```

**generate_chapter_outlines_by_count() - 生成指定数量的章节大纲**

```python
def generate_chapter_outlines_by_count(
    self,
    project_id: str,
    count: int
) -> Dict[str, Any]:
    """
    灵活生成指定数量的章节大纲

    Args:
        project_id: 项目ID
        count: 生成数量

    Returns:
        生成结果
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapter-outlines/generate-by-count',
        {'count': count},
        timeout=600
    )
```

**regenerate_chapter_outline() - 重新生成指定章节大纲**

```python
def regenerate_chapter_outline(
    self,
    project_id: str,
    chapter_number: int,
    prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    重新生成指定章节大纲

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        prompt: 优化提示（可选）

    Returns:
        新的章节大纲
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapter-outlines/{chapter_number}/regenerate',
        {'prompt': prompt} if prompt else {},
        timeout=180
    )
```

**delete_chapter_outlines() - 删除最新的N章大纲**

```python
def delete_chapter_outlines(
    self,
    project_id: str,
    count: int
) -> Dict[str, Any]:
    """
    删除最新的N章大纲

    Args:
        project_id: 项目ID
        count: 删除数量

    Returns:
        删除结果
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapter-outlines/delete',
        {'count': count}
    )
```

### 6. 章节生成

**generate_chapter() - 生成章节**

```python
def generate_chapter(
    self,
    project_id: str,
    chapter_number: int
) -> Dict[str, Any]:
    """
    生成章节

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        生成结果（包含多个版本）
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapters/generate',
        {'chapter_number': chapter_number},
        timeout=600
    )
```

**select_chapter_version() - 选择章节版本**

```python
def select_chapter_version(
    self,
    project_id: str,
    chapter_number: int,
    version_index: int
) -> Dict[str, Any]:
    """
    选择章节版本

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        version_index: 版本索引

    Returns:
        选择结果
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapters/select',
        {
            'chapter_number': chapter_number,
            'version_index': version_index
        }
    )
```

**evaluate_chapter() - 评审章节**

```python
def evaluate_chapter(
    self,
    project_id: str,
    chapter_number: int
) -> Dict[str, Any]:
    """
    评审章节

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        评审结果
    """
    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapters/evaluate',
        {'chapter_number': chapter_number},
        timeout=300
    )
```

**retry_chapter_version() - 重新生成指定版本**

```python
def retry_chapter_version(
    self,
    project_id: str,
    chapter_number: int,
    version_index: int,
    custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    重新生成指定章节的某个版本

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        version_index: 版本索引
        custom_prompt: 自定义优化提示词（可选）

    Returns:
        更新后的项目数据
    """
    data = {
        'chapter_number': chapter_number,
        'version_index': version_index
    }
    if custom_prompt:
        data['custom_prompt'] = custom_prompt

    return self._request(
        'POST',
        f'/api/writer/novels/{project_id}/chapters/retry-version',
        data,
        timeout=600
    )
```

**update_chapter() - 更新章节内容**

```python
def update_chapter(
    self,
    project_id: str,
    chapter_number: int,
    content: str
) -> Dict[str, Any]:
    """
    更新章节内容

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        content: 新内容

    Returns:
        更新结果
    """
    return self._request(
        'PUT',
        f'/api/writer/novels/{project_id}/chapters/{chapter_number}',
        {'content': content}
    )
```

**export_chapters() - 导出章节为TXT文件**

```python
def export_chapters(
    self,
    project_id: str,
    start: Optional[int] = None,
    end: Optional[int] = None
) -> bytes:
    """
    导出章节为TXT文件

    Args:
        project_id: 项目ID
        start: 起始章节号
        end: 结束章节号

    Returns:
        文件内容（字节）
    """
    params = {}
    if start is not None:
        params['start'] = start
    if end is not None:
        params['end'] = end

    url = f"{self.base_url}/api/writer/novels/{project_id}/chapters/export"
    response = self.session.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.content
```

### 7. LLM配置管理

**get_llm_configs() - 获取LLM配置列表**

```python
def get_llm_configs(self) -> List[Dict[str, Any]]:
    """获取LLM配置列表"""
    return self._request('GET', '/api/llm-configs')
```

**create_llm_config() - 创建LLM配置**

```python
def create_llm_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建LLM配置

    Args:
        config_data: 配置数据

    Returns:
        创建的配置
    """
    return self._request('POST', 