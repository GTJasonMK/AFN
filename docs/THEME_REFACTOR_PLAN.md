# 主题配置系统重构计划

## 一、重构目标

1. **从"面向常量"改为"面向组件"** - 用户直接编辑按钮、卡片、侧边栏等组件的样式
2. **将透明配置融入主题配置** - 透明度成为组件属性，随主题切换

## 二、当前架构问题

```
当前结构（面向常量）:
├── primary_colors: { PRIMARY, PRIMARY_LIGHT, PRIMARY_DARK... }
├── text_colors: { TEXT_PRIMARY, TEXT_SECONDARY... }
├── background_colors: { BG_PRIMARY, BG_CARD... }
├── border_effects: { BORDER_DEFAULT, SHADOW_COLOR... }
└── 透明配置: 单独存储在 QSettings
```

问题：
- 用户编辑 PRIMARY 不知道影响哪些组件
- 透明配置与主题分离，无法随主题切换
- 配置结构与使用场景不匹配

## 三、目标架构

```
新结构（面向组件 + 设计令牌）:
├── tokens (设计令牌 - 高级用户)
│   ├── colors: { brand, accent, background, text, border... }
│   ├── typography: { fonts, sizes, weights... }
│   ├── spacing: { xs, sm, md, lg... }
│   └── radius: { sm, md, lg, full... }
├── components (组件配置 - 普通用户)
│   ├── button: { primary, secondary, ghost, danger }
│   ├── card: { bg, border, radius, shadow }
│   ├── input: { bg, border, text, placeholder }
│   ├── sidebar: { bg, opacity, blur }  ← 透明融入
│   ├── header: { bg, opacity, blur }   ← 透明融入
│   ├── dialog: { bg, opacity, overlay } ← 透明融入
│   └── ...
└── effects (效果配置)
    ├── transparency_enabled: bool
    ├── blur_enabled: bool
    └── animation_speed: string
```

## 四、实施阶段

### Phase 1: 后端模型重构 [已完成]
- [x] 1.1 创建新的数据库模型 (ThemeConfigV2)
- [x] 1.2 定义新的默认主题配置
- [x] 1.3 创建新的 Pydantic schemas
- [x] 1.4 更新 Repository
- [x] 1.5 更新 Service（支持新格式）
- [x] 1.6 更新 API 路由

### Phase 2: 前端 ThemeManager 重构 [已完成]
- [x] 2.1 添加 Token 解析器
- [x] 2.2 添加组件配置访问方法
- [x] 2.3 实现向后兼容层
- [x] 2.4 更新样式生成方法
- [x] 2.5 迁移透明配置到主题系统

### Phase 3: UI 编辑器重构 [已完成]
- [x] 3.1 重新设计设置界面布局
- [x] 3.2 实现组件级编辑器
- [x] 3.3 添加实时预览
- [x] 3.4 实现效果配置面板

### Phase 4: 清理与优化 [已完成]
- [x] 4.1 修复FastAPI路由顺序问题
- [x] 4.2 更新settings模块导出和文档
- [x] 4.3 添加透明效果V2集成提示
- [x] 4.4 代码语法验证

### Phase 5: 透明效果融合与启动优化 [已完成]
- [x] 5.1 从设置导航中移除独立的"透明效果"项
- [x] 5.2 透明效果配置已融入V2组件配置（sidebar、header、dialog的transparency字段）
- [x] 5.3 修复启动时加载激活的主题配置（V2）
- [x] 5.4 更新settings模块文档

## 五、数据结构定义

### 5.1 设计令牌 (token_colors)

```python
{
    # 品牌色
    "brand": "#8B4513",
    "brand_light": "#A0522D",
    "brand_dark": "#6B3410",
    "accent": "#A0522D",
    "accent_light": "#B8653D",

    # 背景色
    "background": "#F9F5F0",
    "surface": "#FFFBF0",
    "surface_alt": "#F0EBE5",

    # 文本色
    "text": "#2C1810",
    "text_muted": "#5D4037",
    "text_subtle": "#6D6560",
    "text_disabled": "#B0A8A0",

    # 边框色
    "border": "#D7CCC8",
    "border_light": "#E8E4DF",
    "border_dark": "#C4C0BC",
}
```

### 5.2 组件配置示例 (comp_button)

```python
{
    "primary": {
        "bg": "#8B4513",
        "bg_hover": "#A0522D",
        "bg_pressed": "#6B3410",
        "text": "#FFFBF0",
        "border": "none",
        "radius": "24px",
        "shadow": "none",
    },
    "secondary": {
        "bg": "transparent",
        "bg_hover": "#8B4513",
        "text": "#8B4513",
        "text_hover": "#FFFBF0",
        "border": "2px solid #8B4513",
        "radius": "24px",
    },
    "ghost": {
        "bg": "transparent",
        "bg_hover": "#F0EBE5",
        "text": "#2C1810",
        "border": "none",
        "radius": "6px",
    },
    "danger": {
        "bg": "#A85448",
        "bg_hover": "#C4706A",
        "text": "#FFFBF0",
        "border": "none",
        "radius": "24px",
    },
}
```

### 5.3 侧边栏配置 (comp_sidebar) - 含透明

```python
{
    "bg": "#F9F5F0",
    "border": "1px solid #E8E4DF",
    "item_bg_hover": "#F0EBE5",
    "item_bg_active": "#FFFBF0",
    "item_text": "#5D4037",
    "item_text_active": "#8B4513",
    # 透明效果
    "opacity": 0.85,
    "blur_radius": 20,
    "use_transparency": true,
}
```

### 5.4 效果配置 (effects)

```python
{
    "transparency_enabled": true,
    "blur_enabled": true,
    "system_blur": false,
    "animation_speed": "normal",  # "none" | "slow" | "normal" | "fast"
    "hover_effects": true,
    "focus_ring": true,
}
```

## 六、向后兼容策略

1. **保留旧属性访问** - `theme_manager.PRIMARY` 仍然可用
2. **属性映射** - 旧属性从新配置中动态获取
3. **渐进式迁移** - 组件可以逐步切换到新 API

```python
# 兼容层示例
@property
def PRIMARY(self):
    return self._resolved_config.get("token_colors", {}).get("brand", "#8B4513")

@property
def TEXT_PRIMARY(self):
    return self._resolved_config.get("token_colors", {}).get("text", "#2C1810")
```

## 七、文件变更清单

### 后端
- `backend/app/models/theme_config.py` - 添加V2字段（config_version, token_*, comp_*, effects）
- `backend/app/schemas/theme_config.py` - 添加V2 schemas
- `backend/app/services/theme_config_service.py` - 添加V2默认值和服务方法
- `backend/app/api/routers/theme_config.py` - 添加V2 API路由

### 前端 - ThemeManager
- `frontend/themes/theme_manager/core.py` - 集成V2ConfigMixin
- `frontend/themes/theme_manager/v2_config_mixin.py` - 新增V2配置访问Mixin
- `frontend/themes/theme_manager/__init__.py` - 更新导出

### 前端 - API客户端
- `frontend/api/client/theme_config_mixin.py` - 添加V2 API方法

### 前端 - UI编辑器
- `frontend/windows/settings/theme_settings/v2_config_groups.py` - 新增V2组件配置组定义
- `frontend/windows/settings/theme_settings/v2_editor_widget.py` - 新增V2主题编辑器
- `frontend/windows/settings/theme_settings/unified_widget.py` - 新增统一主题设置Widget
- `frontend/windows/settings/theme_settings/__init__.py` - 更新导出
- `frontend/windows/settings/view.py` - 使用UnifiedThemeSettingsWidget

## 八、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 破坏现有功能 | 向后兼容层保持旧 API |
| 数据迁移失败 | 保留旧字段，渐进迁移 |
| 性能下降 | Token 解析结果缓存 |
| 用户学习成本 | 保持简单的默认视图 |

---

创建时间: 2024年
更新时间: 2025年12月
状态: 全部Phase已完成（Phase 1-5）

## 最新更新记录

### Phase 5 更新（2025年12月）
- 透明效果不再作为独立设置项，已完全融入主题配置的V2组件模式
- 在sidebar、header、dialog组件中配置透明度和模糊效果
- 启动时自动加载用户激活的主题配置（如果后端可用）
- 导航项从8个减少到7个（移除了"透明效果"）
