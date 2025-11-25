
# settings_view.py - 设置窗口

## 文件路径
`frontend/windows/settings_view.py`

## 功能概述
设置窗口，用于管理LLM配置，支持创建、编辑、激活、删除、测试、导入导出配置。

**对应Web组件**: `src/views/SettingsView.vue` + `src/components/LLMSettings.vue`

## 主要组件

### 1. LLMConfigDialog - 配置编辑对话框
**行数**: 24-141

用于创建或编辑LLM配置的模态对话框。

#### 表单字段
```python
# 必填字段
config_name: str  # 配置名称

# 可选字段
llm_provider_url: str  # API Base URL
llm_provider_api_key: str  # API Key（编辑时留空表示不修改）
llm_provider_model: str  # 模型名称
```

#### 样式特点
- 使用 `QFormLayout` 右对齐标签
- 输入框有焦点时高亮边框
- API Key 字段使用密码模式
- 编辑模式下显示提示："留空表示保持原有 API Key 不变"

#### 数据获取
```python
def getData(self):
    data = {'config_name': self.name_input.text().strip()}
    
    # 只添加非空字段
    if self.url_input.text().strip():
        data['llm_provider_url'] = self.url_input.text().strip()
    if self.key_input.text().strip():
        data['llm_provider_api_key'] = self.key_input.text().strip()
    if self.model_input.text().strip():
        data['llm_provider_model'] = self.model_input.text().strip()
    
    return data
```

### 2. TestResultDialog - 测试结果对话框
**行数**: 143-245

显示LLM配置测试结果。

#### 显示内容
- **成功时**:
  - ✓ 图标（绿色圆形背景）
  - "连接成功"标题
  - 响应时间（毫秒）
  - 模型信息
  
- **失败时**:
  - ✗ 图标（红色圆形背景）
  - "连接失败"标题
  - 错误信息

#### 详细信息显示
```python
if self.success and self.details:
    # 响应时间
    f"{self.details['response_time_ms']:.2f} ms"
    
    # 模型信息
    str(self.details['model_info'])
```

### 3. LLMSettingsWidget - 配置管理组件
**行数**: 247-796

**核心组件**，管理所有LLM配置。

#### UI结构
```
┌─────────────────────────────────────────┐
│ Header (标题、导入、导出、新增按钮)      │
├─────────────────────────────────────────┤
│ Info (配置说明提示框)                    │
├─────────────────────────────────────────┤
│                                         │
│ Config List (滚动区域)                  │
│  ├─ Config Card 1                       │
│  ├─ Config Card 2                       │
│  └─ ...                                 │
│                                         │
└─────────────────────────────────────────┘
```

#### 顶部Header
**行数**: 264-362

- **标题**: "LLM 配置管理"
- **副标题**: "管理您的 AI 模型配置，支持多个配置切换"
- **操作按钮**:
  - 导入配置（半透明绿色）
  - 导出所有（半透明灰绿色）
  - 新增配置（灰绿色渐变）

**按钮样式特点**:
```python
# 柔和的半透明背景
background-color: rgba(139, 186, 139, 0.3)  # 导入按钮
background-color: rgba(155, 170, 153, 0.3)  # 导出按钮
background: qlineargradient(...)  # 新增按钮
```

#### 配置说明
**行数**: 365-386

压缩版横向布局：
```
◐ 提示：可创建多个配置并切换 • 点击测试验证连接 • 激活的配置不可删除
```

#### 配置卡片
**行数**: 434-631

**增大尺寸、更亮配色的卡片**：

**激活配置样式**:
```python
background-color: rgba(245, 250, 245, 0.95)  # 浅绿色背景
border: 2px solid rgba(139, 154, 138, 0.5)  # 绿色边框
```

**普通配置样式**:
```python
background-color: rgba(255, 255, 255, 0.9)  # 白色背景
border: 2px solid rgba(139, 154, 138, 0.2)  # 浅绿色边框
```

**卡片内容**:
```
┌───────────────────────────────────┐
│ 配置名称  [当前激活]               │
│                                   │
│ API URL: ...                      │
│ API Key: sk-***...                │
│ 模型: gpt-4                       │
│                                   │
│ [测试连接] [激活配置] [编辑]       │
│ [导出] [删除]                     │
└───────────────────────────────────┘
```

**操作按钮**（更柔和配色）:
1. **测试连接**: 半透明灰绿色
2. **激活配置**: 半透明绿色（仅非激活配置）
3. **编辑**: 半透明灰色
4. **导出**: 半透明蓝绿色
5. **删除**: 半透明粉红色（激活配置禁用）

#### 核心方法

**加载配置**:
```python
def loadConfigs(self):
    self.configs = self.api_client.get_llm_configs()
    self.renderConfigs()
```

**创建配置**:
```python
def createConfig(self):
    dialog = LLMConfigDialog(parent=self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.getData()
        self.api_client.create_llm_config(data)
        self.loadConfigs()
```

**编辑配置**:
```python
def editConfig(self, config):
    dialog = LLMConfigDialog(config=config, parent=self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.getData()
        self.api_client.update_llm_config(config['id'], data)
        self.loadConfigs()
```

**激活配置**:
```python
def activateConfig(self, config):
    self.api_client.activate_llm_config(config['id'])
    QMessageBox.information(self, "成功", f"已激活配置：{config['config_name']}")
    self.loadConfigs()
```

**删除配置**:
```python
def deleteConfig(self, config):
    reply = QMessageBox.question(...)
    if reply == QMessageBox.StandardButton.Yes:
        self.api_client.delete_llm_config(config['id'])
        self.loadConfigs()
```

**测试配置**:
```python
def testConfig(self, config):
    # 标记正在测试
    self.testing_config_id = config['id']
    self.renderConfigs()
    
    try:
        result = self.api_client.test_llm_config(config['id'])
        success = result.get('success', False)
        message = result.get('message', '')
        details = result.get('details', {})
        
        # 显示测试结果对话框
        dialog = TestResultDialog(success, message, details, parent=self)
        dialog.exec()
    finally:
        self.testing_config_id = None
        self.renderConfigs()
```

**导出单个配置**:
```python
def exportConfig(self, config):
    file_path, _ = QFileDialog.getSaveFileName(
        self,
        "导出配置",
        f"{config['config_name']}.json",
        "JSON文件 (*.json)"
    )
    
    if file_path:
        export_data = self.api_client.export_llm_config(config['id'])
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
```

**导出所有配置**:
```python
def exportAll(self):
    export_data = self.api_client.export_llm_configs()
    # export_data 格式: LLMConfigExportData
    # {"version": "1.0", "export_time": "...", "configs": [...]}
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    config_count = len(export_data.get('configs', []))
    QMessageBox.information(self, "成功", f"已导出 {config_count} 个配置")
```

**导入配置**:
```python
def importConfigs(self):
    file_path, _ = QFileDialog.getOpenFileName(...)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        import_data = json.load(f)
    
    # 验证格式
    if 'configs' not in import_data:
        QMessageBox.warning(self, "格式错误", "导入文件缺少 'configs' 字段")
        return
    
    result = self.api_client.import_llm_configs(import_data)
    self.loadConfigs()
```

### 4. SettingsView - 主页面类
**行数**: 798-896

#### UI结构
```
┌─────────────────────────────────────────┐
│ [← 返回]                                 │
├────────────┬────────────────────────────┤
│            │                            │
│  Sidebar   │  LLMSettingsWidget         │
│  (导航栏)  │  (配置管理组件)            │
│            │                            │
│  ├ 设置    │                            │
│  └ LLM配置 │                            │
│            │                            │
└────────────┴────────────────────────────┘
```

#### 背景样式
与首页一致的禅意渐变：
```python
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #FAF7F0,
    stop:0.3 #F5F1E8,
    stop:0.6 #F0ECE3,
    stop:1 #EBE7DD
)
```

#### 侧边栏
**行数**: 856-885

- 固定宽度：280px
- 半透明白色卡片
- 标题："设置"
- 当前激活项："LLM 配置"（柔和灰绿色背景）

## 数据流

### 页面初始化
```
__init__()
  → setupUI()
    → 创建返回按钮
    → 创建Sidebar
    → 创建LLMSettingsWidget
      → loadConfigs()
        → api_client.get_llm_configs()
        → renderConfigs()
          → createConfigCard() × N
```

### 配置测试流程
```
用户点击"测试连接"
  → testConfig(config)
    → 标记 testing_config_id
    → renderConfigs()  # 更新按钮文字为"测试中..."
    → api_client.test_llm_config(config['id'])
    → TestResultDialog.exec()  # 显示结果
    → testing_config_id = None
    → renderConfigs()  # 恢复按钮文字
```

### 导入导出流程
```
导出单个:
  → exportConfig()
    → QFileDialog.getSaveFileName()
    → api_client.export_llm_config(id)
    → 保存JSON文件

导出所有:
  → exportAll()
    → QFileDialog.getSaveFileName()
    → api_client.export_llm_configs()
    → 保存JSON文件（包含所有配置）

导入:
  → importConfigs()
    → QFileDialog.getOpenFileName()
    → 读取JSON文件
    → 验证格式
    → api_client.import_llm_configs(data)
    → loadConfigs()
```

## 样式系统

### 卡片渐变和透明度
使用rgba颜色实现柔和的半透明效果：

**按钮渐变**:
```python
# 导入按钮（绿色系）
background-color: rgba(139, 186, 139, 0.3)
border: 1px solid rgba(139, 186, 139, 0.5)

# 导出按钮（灰绿系）
background-color: rgba(155, 170, 153, 0.3)
border: 1px solid rgba(139, 154, 138, 0.5)

# 新增按钮（渐变）
background: qlineargradient(
    stop:0 rgba(139, 154, 138, 0.4),
    stop:1 rgba(155, 170, 153, 0.4)
)
```

### 配置卡片样式
```python
# 