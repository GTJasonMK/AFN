
# Arboris-Novel 代码文档阅读指南

本文档提供了 Arboris-Novel PyQt 项目代码文档的推荐阅读顺序，帮助开发者快速理解项目架构和核心功能。

## 📚 文档概览

本项目包含 **70+ 个详细的代码文档**，涵盖前后端所有核心模块。文档采用中文撰写，包含完整的代码示例、设计模式讲解和最佳实践。

## 🎯 快速开始（15分钟）

如果你想快速了解项目，建议按以下顺序阅读：

1. **项目入口**
   - [`backend/app/main.md`](backend/app/main.md) - 后端应用入口
   - [`frontend/main.md`](frontend/main.md) - 前端应用入口

2. **核心配置**
   - [`backend/app/core/config.md`](backend/app/core/config.md) - 后端配置系统
   - [`frontend/utils/config_manager.md`](frontend/utils/config_manager.md) - 前端配置管理

3. **数据模型**
   - [`backend/app/models/novel.md`](backend/app/models/novel.md) - 小说数据模型
   - [`frontend/models/project_status.md`](frontend/models/project_status.md) - 项目状态管理

## 🏗️ 架构理解（30分钟）

### 后端架构路径

```
1. 入口层 → 2. 路由层 → 3. 服务层 → 4. 仓储层 → 5. 数据层
```

#### 第一步：理解入口和核心配置
1. [`backend/app/main.md`](backend/app/main.md) - FastAPI应用入口
2. [`backend/app/core/config.md`](backend/app/core/config.md) - 配置系统
3. [`backend/app/core/constants.md`](backend/app/core/constants.md) - 常量定义

#### 第二步：理解数据层
4. [`backend/app/db/base.md`](backend/app/db/base.md) - 数据库基础
5. [`backend/app/db/session.md`](backend/app/db/session.md) - 会话管理
6. [`backend/app/models/novel.md`](backend/app/models/novel.md) - 核心数据模型

#### 第三步：理解业务逻辑
7. [`backend/app/services/novel_service.md`](backend/app/services/novel_service.md) - 小说服务
8. [`backend/app/services/llm_service.md`](backend/app/services/llm_service.md) - LLM服务
9. [`backend/app/core/state_machine.md`](backend/app/core/state_machine.md) - 状态机

#### 第四步：理解API层
10. [`backend/app/api/routers/novels.md`](backend/app/api/routers/novels.md) - 小说路由
11. [`backend/app/api/routers/writer.md`](backend/app/api/routers/writer.md) - 写作路由

### 前端架构路径

```
1. 入口 → 2. 主窗口 → 3. 页面 → 4. 组件 → 5. 工具
```

#### 第一步：理解应用结构
1. [`frontend/main.md`](frontend/main.md) - 应用入口
2. [`frontend/windows/main_window.md`](frontend/windows/main_window.md) - 主窗口
3. [`frontend/pages/base_page.md`](frontend/pages/base_page.md) - 页面基类

#### 第二步：理解核心窗口
4. [`frontend/pages/home_page.md`](frontend/pages/home_page.md) - 首页
5. [`frontend/windows/novel_workspace.md`](frontend/windows/novel_workspace.md) - 工作台
6. [`frontend/windows/writing_desk.md`](frontend/windows/writing_desk.md) - 写作台

#### 第三步：理解设计系统
7. [`frontend/themes/zen_theme.md`](frontend/themes/zen_theme.md) - 禅意主题
8. [`frontend/themes/accessibility.md`](frontend/themes/accessibility.md) - 可访问性

#### 第四步：理解工具模块
9. [`frontend/api/client.md`](frontend/api/client.md) - API客户端
10. [`frontend/utils/async_worker.md`](frontend/utils/async_worker.md) - 异步任务

## 📖 按功能模块阅读

### 功能1：小说项目管理

**后端部分：**
1. [`backend/app/models/novel.md`](backend/app/models/novel.md) - 数据模型
2. [`backend/app/repositories/novel_repository.md`](backend/app/repositories/novel_repository.md) - 数据访问
3. [`backend/app/services/novel_service.md`](backend/app/services/novel_service.md) - 业务逻辑
4. [`backend/app/api/routers/novels.md`](backend/app/api/routers/novels.md) - API接口

**前端部分：**
1. [`frontend/api/client.md`](frontend/api/client.md) - API调用
2. [`frontend/models/project_status.md`](frontend/models/project_status.md) - 状态管理
3. [`frontend/windows/novel_workspace.md`](frontend/windows/novel_workspace.md) - 项目列表
4. [`frontend/windows/novel_detail.md`](frontend/windows/novel_detail.md) - 项目详情

### 功能2：AI内容生成

**后端部分：**
1. [`backend/app/core/state_machine.md`](backend/app/core/state_machine.md) - 状态机
2. [`backend/app/services/llm_service.md`](backend/app/services/llm_service.md) - LLM服务
3. [`backend/app/utils/llm_tool.md`](backend/app/utils/llm_tool.md) - LLM工具
4. [`backend/app/services/prompt_service.md`](backend/app/services/prompt_service.md) - 提示词服务

**前端部分：**
1. [`frontend/windows/inspiration_mode.md`](frontend/windows/inspiration_mode.md) - 灵感模式
2. [`frontend/windows/writing_desk.md`](frontend/windows/writing_desk.md) - 写作台
3. [`frontend/utils/task_monitor.md`](frontend/utils/task_monitor.md) - 任务监控
4. [`frontend/components/task_progress_dialog.md`](frontend/components/task_progress_dialog.md) - 进度对话框

### 功能3：LLM配置管理

**后端部分：**
1. [`backend/app/models/llm_config.md`](backend/app/models/llm_config.md) - 配置模型
2. [`backend/app/repositories/llm_config_repository.md`](backend/app/repositories/llm_config_repository.md) - 配置仓储
3. [`backend/app/services/llm_config_service.md`](backend/app/services/llm_config_service.md) - 配置服务
4. [`backend/app/api/routers/llm_config.md`](backend/app/api/routers/llm_config.md) - 配置路由

**前端部分：**
1. [`frontend/windows/settings_view.md`](frontend/windows/settings_view.md) - 设置页面
2. [`frontend/utils/config_manager.md`](frontend/utils/config_manager.md) - 配置管理

### 功能4：向量存储与RAG

**后端部分：**
1. [`backend/app/services/vector_store_service.md`](backend/app/services/vector_store_service.md) - 向量存储服务
2. [`backend/app/services/chapter_context_service.md`](backend/app/services/chapter_context_service.md) - 章节上下文
3. [`backend/app/services/chapter_ingest_service.md`](backend/app/services/chapter_ingest_service.md) - 章节摄入

## 🎨 UI/UX设计理解

### 设计系统
1. [`frontend/themes/zen_theme.md`](frontend/themes/zen_theme.md) - 新中式禅意主题
   - 颜色系统
   - 字体系统
   - 圆角系统
   - 阴影系统

2. [`frontend/themes/accessibility.md`](frontend/themes/accessibility.md) - 可访问性
   - 焦点指示器
   - 键盘导航
   - ARIA标签
   - 快捷键定义

### UI组件
1. [`frontend/components/loading_spinner.md`](frontend/components/loading_spinner.md) - 加载动画
2. [`frontend/components/skeleton.md`](frontend/components/skeleton.md) - 骨架屏
3. [`frontend/components/toast.md`](frontend/components/toast.md) - 提示消息
4. [`frontend/components/empty_state.md`](frontend/components/empty_state.md) - 空状态

## 🔧 技术专题

### 专题1：异步编程
1. [`frontend/utils/async_worker.md`](frontend/utils/async_worker.md) - 异步任务封装
2. [`frontend/utils/task_monitor.md`](frontend/utils/task_monitor.md) - 任务监控
3. [`frontend/components/task_progress_dialog.md`](frontend/components/task_progress_dialog.md) - 进度显示

### 专题2：数据库设计
1. [`backend/app/db/base.md`](backend/app/db/base.md) - 数据库基础
2. [`backend/app/db/session.md`](backend/app/db/session.md) - 会话管理
3. [`backend/app/db/init_db.md`](backend/app/db/init_db.md) - 数据库初始化
4. [`backend/app/repositories/base.md`](backend/app/repositories/base.md) - 仓储基类

### 专题3：设计模式应用
1. **仓储模式**: [`backend/app/repositories/base.md`](backend/app/repositories/base.md)
2. **服务层模式**: [`backend/app/services/novel_service.md`](backend/app/services/novel_service.md)
3. **状态机模式**: [`backend/app/core/state_machine.md`](backend/app/core/state_machine.md)
4. **观察者模式**: [`frontend/utils/async_worker.md`](frontend/utils/async_worker.md)
5. **模板方法模式**: [`frontend/pages/base_page.md`](frontend/pages/base_page.md)

### 专题4：安全与认证
1. [`backend/app/core/security.md`](backend/app/core/security.md) - 安全工具
2. [`backend/app/core/dependencies.md`](backend/app/core/dependencies.md) - 依赖注入
3. [`backend/app/services/auth_service.md`](backend/app/services/auth_service.md) - 认证服务

## 📝 完整文档清单

### 后端文档（48个）

#### 核心入口
- [`backend/app/main.md`](backend/app/main.md)

#### API路由层（3个）
- [`backend/app/api/routers/llm_config.md`](backend/app/api/routers/llm_config.md)
- [`backend/app/api/routers/novels.md`](backend/app/api/routers/novels.md)
- [`backend/app/api/routers/writer.md`](backend/app/api/routers/writer.md)

#### 服务层（12个）
- [`backend/app/services/admin_setting_service.md`](backend/app/services/admin_setting_service.md)
- [`backend/app/services/auth_service.md`](backend/app/services/auth_service.md)
- [`backend/app/services/chapter_context_service.md`](backend/app/services/chapter_context_service.md)
- [`backend/app/services/chapter_ingest_service.md`](backend/app/services/chapter_ingest_service.md)
- [`backend/app/services/config_service.md`](backend/app/services/config_service.md)
- [`backend/app/services/llm_config_service.md`](backend/app/services/llm_config_service.md)
- [`backend/app/services/llm_service.md`](backend/app/services/llm_service.md)
- [`backend/app/services/novel_service.md`](backend/app/services/novel_service.md)
- [`backend/app/services/part_outline_service.md`](backend/app/services/part_outline_service.md)
- [`backend/app/services/prompt_service.md`](backend/app/services/prompt_service.md)
- [`backend/app/services/update_log_service.md`](backend/app/services/update_log_service.md)
- [`backend/app/services/usage_service.md`](backend/app/services/usage_service.md)
- [`backend/app/services/user_service.md`](backend/app/services/user_service.md)
- [`backend/app/services/vector_store_service.md`](backend/app/services/vector_store_service.md)

#### 仓储层（9个）
- [`backend/app/repositories/admin_setting_repository.md`](backend/app/repositories/admin_setting_repository.md)
- [`backend/app/repositories/base.md`](backend/app/repositories/base.md)
- [`backend/app/repositories/llm_config_repository.md`](backend/app/repositories/llm_config_repository.md)
- [`backend/app/repositories/novel_repository.md`](backend/app/repositories/novel_repository.md)
- [`backend/app/repositories/part_outline_repository.md`](backend/app/repositories/part_outline_repository.md)
- [`backend/app/repositories/prompt_repository.md`](backend/app/repositories/prompt_repository.md)
- [`backend/app/repositories/system_config_repository.md`](backend/app/repositories/system_config_repository.md)
- [`backend/app/repositories/update_log_repository.md`](backend/app/repositories/update_log_repository.md)
- [`backend/app/repositories/usage_metric_repository.md`](backend/app/repositories/usage_metric_repository.md)
- [`backend/app/repositories/user_repository.md`](backend/app/repositories/user_repository.md)

#### 核心模块（5个）
- [`backend/app/core/config.md`](backend/app/core/config.md)
- [`backend/app/core/constants.md`](backend/app/core/constants.md)
- [`backend/app/core/dependencies.md`](backend/app/core/dependencies.md)
- [`backend/app/core/security.md`](backend/app/core/security.md)
- [`backend/app/core/state_machine.md`](backend/app/core/state_machine.md)

#### 数据库模块（4个）
- [`backend/app/db/base.md`](backend/app/db/base.md)
- [`backend/app/db/session.md`](backend/app/db/session.md)
- [`backend/app/db/init_db.md`](backend/app/db/init_db.md)
- [`backend/app/db/system_config_defaults.md`](backend/app/db/system_config_defaults.md)

#### 数据模型（10个）
- [`backend/app/models/admin_setting.md`](backend/app/models/admin_setting.md)
- [`backend/app/models/llm_config.md`](backend/app/models/llm_config.md)
- [`backend/app/models/novel.md`](backend/app/models/novel.md)
- [`backend/app/models/part_outline.md`](backend/app/models/part_outline.md)
- [`backend/app/models/prompt.md`](backend/app/models/prompt.md)
- [`backend/app/models/system_config.md`](backend/app/models/system_config.md)
- [`backend/app/models/update_log.md`](backend/app/models/update_log.md)
- [`backend/app/models/usage_metric.md`](backend/app/models/usage_metric.md)
- [`backend/app/models/user_daily_request.md`](backend/app/models/user_daily_request.md)
- [`backend/app/models/user.md`](backend/app/models/user.md)

#### Schema层（5个）
- [`backend/app/schemas/config.md`](backend/app/schemas/config.md)
- [`backend/app/schemas/llm_config.md`](backend/app/schemas/llm_config.md)
- [`backend/app/schemas/novel.md`](backend/app/schemas/novel.md)
- [`backend/app/schemas/prompt.md`](backend/app/schemas/prompt.md)
- [`backend/app/schemas/user.md`](backend/app/schemas/user.md)

#### 工具模块（2个）
- [`backend/app/utils/json_utils.md`](backend/app/utils/json_utils.md)
- [`backend/app/utils/llm_tool.md`](backend/app/utils/llm_tool.md)

### 前端文档（22个）

#### 核心入口
- [`frontend/main.md`](frontend/main.md)

#### 窗口层（6个）
- [`frontend/windows/main_window.md`](frontend/windows/main_window.md)
- [`frontend/windows/novel_workspace.md`](frontend/windows/novel_workspace.md)
- [`frontend/windows/novel_detail.md`](frontend/windows/novel_detail.md)
- [`frontend/windows/writing_desk.md`](frontend/windows/writing_desk.md)
- [`frontend/windows/inspiration_mode.md`](frontend/windows/inspiration_mode.md)
- [`frontend/windows/settings_view.md`](frontend/windows/settings_view.md)

#### 组件层（6个）
- [`frontend/components/loading_spinner.md`](frontend/components/loading_spinner.md)
- [`frontend/components/skeleton.md`](frontend/components/skeleton.md)
- [`frontend/components/toast.md`](frontend/components/toast.md)
- [`frontend/components/task_progress_dialog.md`](frontend/components/task_progress_dialog.md)
- [`frontend/components/writing_desk_modals.md`](frontend/components/writing_desk_modals.md)
- [`frontend/components/empty_state.md`](frontend/components/empty_state.md)

#### 工具模块（3个）
- [`frontend/utils/async_worker.md`](frontend/utils/async_worker.md)
- [`frontend/utils/config_manager.md`](frontend/utils/config_manager.md)
- [`frontend/utils/task_monitor.md`](frontend/utils/task_monitor.md)

#### 主题模块（2个）
- [`frontend/themes/zen_theme.md`](frontend/themes/zen_theme.md)
- [`frontend/themes/accessibility.md`](frontend/themes/accessibility.md)

#### API客户端
- [`frontend/api/client.md`](frontend/api/client.md)

#### 页面模块（2个）
- [`frontend/pages/base_page.md`](frontend/pages/base_page.md)
- [`frontend/pages/home_page.md`](frontend/pages/home_page.md)

#### 数据模型
- [`frontend/models/project_status.md`](frontend/models/project_status.md)

## 💡 学习建议

### 新手开发者
1. 先阅读"快速开始"部分（3个文档）
2. 然后按"架构理解"路径学习
3. 选择感兴趣的功能模块深入学习
4. 最后阅读技术专题部分

### 后端开发者
1. 