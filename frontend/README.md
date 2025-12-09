# AFN (Agents for Novel) - PyQt Desktop Frontend

AFN 的 PyQt 桌面版前端，提供完整的小说创作界面。

## 特性

- 开箱即用，无需登录
- 项目管理（创建、删除、浏览）
- 概念对话（AI辅助构思）
- 蓝图编辑（世界观、角色、章节纲要）
- 章节生成与管理
- LLM配置管理

## 系统要求

- Windows 10/11
- Python 3.10+
- 后端服务已启动（`pyqt项目迁移/backend`）

## 快速启动

### 方式一：使用启动脚本（推荐）

双击运行 `start.bat`，脚本会自动：
1. 创建虚拟环境（首次运行）
2. 安装依赖（首次运行）
3. 检查后端服务
4. 启动应用

### 方式二：手动启动

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 激活虚拟环境
.venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动应用
python main.py
```

## 使用流程

### 1. 创建项目
- 点击"项目列表"页面的"创建项目"按钮
- 输入项目标题和初始创作方向
- 确认创建

### 2. 概念对话
- 选择项目后，点击"概念对话"
- 与AI进行多轮对话，梳理小说创意
- 至少进行3轮对话后可生成蓝图

### 3. 生成蓝图
- 在概念对话页面点击"生成蓝图"
- 等待蓝图生成（约2-5分钟）
- 自动跳转到蓝图页面

### 4. 编辑蓝图
- 在蓝图页面查看和编辑：
  - 概览（标题、主题、核心冲突）
  - 世界观设定
  - 角色档案
  - 章节纲要
- 点击"保存修改"保存更改

### 5. 生成章节
- 点击"章节写作"进入写作台
- 首次需要点击"生成章节大纲"
- 选择章节号，点击"生成本章"
- 查看多个版本，选择最佳版本
- 可评审所有版本
- 可手动编辑章节内容

### 6. 导出作品
- 在写作台页面点击"导出章节"
- 选择保存位置
- 导出为TXT格式

## 目录结构

```
frontend/
├── main.py              # 应用入口
├── start.bat            # Windows启动脚本
├── requirements.txt     # Python依赖
├── api/
│   ├── __init__.py
│   └── client.py        # API客户端封装
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # 主窗口
│   ├── project_list_widget.py   # 项目列表
│   ├── concept_dialogue_widget.py # 概念对话
│   ├── blueprint_widget.py      # 蓝图编辑
│   ├── writing_desk_widget.py   # 写作台
│   └── settings_widget.py       # LLM配置
└── README.md
```

## API客户端

所有API调用通过 `api/client.py` 中的 `AFNAPIClient` 类完成：

```python
from api.client import AFNAPIClient

# 创建客户端（无需认证）
client = AFNAPIClient()

# 创建项目
project = client.create_novel(
    title="我的小说",
    initial_prompt="科幻冒险故事"
)

# 灵感对话
response = client.inspiration_converse(
    project_id=project['id'],
    user_input='我想写一个关于时间旅行的故事'
)

# 生成蓝图
blueprint = client.generate_blueprint(
    project_id=project['id']
)

# 生成章节
chapter = client.generate_chapter(
    project_id=project['id'],
    chapter_number=1
)
```

## UI组件

### MainWindow
主窗口，包含：
- 左侧导航栏（项目列表、概念对话、蓝图编辑、章节写作、LLM配置）
- 右侧内容区域（堆栈式页面切换）

### ProjectListWidget
项目列表页面，功能：
- 显示所有项目
- 创建新项目
- 删除项目
- 打开项目

### ConceptDialogueWidget
概念对话页面，功能：
- 显示对话历史（气泡式）
- 发送消息给AI
- 生成蓝图

### BlueprintWidget
蓝图编辑页面，功能：
- 标签页显示（概览、世界观、角色、章节纲要）
- 编辑蓝图内容
- 保存修改
- 重新生成蓝图

### WritingDeskWidget
写作台页面，功能：
- 左侧：章节列表、生成控制
- 右侧：版本选择、正文显示、评审结果
- 生成章节大纲
- 生成章节（多版本）
- 版本选择
- 评审章节
- 编辑章节
- 导出章节

### SettingsWidget
LLM配置页面，功能：
- 配置列表显示
- 创建/编辑/删除配置
- 激活配置
- 导入/导出配置

## 注意事项

1. **后端依赖**: 前端必须在后端服务启动后才能正常工作
2. **网络连接**: 默认连接到 `http://127.0.0.1:8000`
3. **API密钥**: 需要在后端配置LLM API密钥
4. **生成时间**:
   - 概念对话: 10-30秒
   - 蓝图生成: 2-5分钟
   - 章节生成: 1-3分钟

## 故障排查

### 应用无法启动
- 检查Python版本（需要3.10+）
- 检查虚拟环境是否正确创建
- 查看 `afn_frontend.log` 日志文件

### 无法连接后端
- 确认后端服务已启动
- 访问 http://127.0.0.1:8000/health 测试
- 检查防火墙设置

### 依赖安装失败
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --no-cache-dir
```

### UI显示异常
- 检查PyQt6是否正确安装
- 尝试重新安装PyQt6:
```bash
pip uninstall PyQt6
pip install PyQt6
```

## 开发说明

### 添加新页面

1. 在 `ui/` 创建新的Widget类
2. 在 `main_window.py` 中导入并添加到 `content_stack`
3. 添加导航按钮和切换逻辑

### 调用新API

在 `api/client.py` 中添加方法：

```python
def new_api_method(self, param1: str) -> Dict[str, Any]:
    """新API方法"""
    return self._request('POST', '/api/new-endpoint', {'param1': param1})
```

## 许可

与主项目相同
