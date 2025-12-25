# 主题配置功能实现计划

## 一、需求概述

将项目中所有主题常量（200+个）配置到设置页面，让用户可以自定义。

### 主题结构

```
主题系统
├── 浅色主题 (Light)
│   ├── 子主题1: "书香浅色" ★ (激活)
│   ├── 子主题2: "我的浅色"
│   └── ...
└── 深色主题 (Dark)
    ├── 子主题1: "书香深色" ★ (激活)
    ├── 子主题2: "护眼深色"
    └── ...
```

- 顶级主题固定两个：浅色(Light)、深色(Dark)
- 每个顶级主题下可创建多个子主题
- 每个顶级主题下只能有一个激活的子主题
- 切换顶级主题时，自动应用该顶级下激活的子主题

---

## 二、常量分组设计

将200+常量按功能分为以下8个组：

### 1. 主色调组 (Primary Colors) - 5个
| 常量 | 类型 | 说明 |
|------|------|------|
| PRIMARY | color | 主色 |
| PRIMARY_LIGHT | color | 浅主色 |
| PRIMARY_DARK | color | 深主色 |
| PRIMARY_PALE | color | 极浅主色 |
| PRIMARY_GRADIENT | gradient | 主色渐变 |

### 2. 强调色组 (Accent Colors) - 5个
| 常量 | 类型 | 说明 |
|------|------|------|
| ACCENT | color | 强调色 |
| ACCENT_LIGHT | color | 浅强调色 |
| ACCENT_DARK | color | 深强调色 |
| ACCENT_PALE | color | 极浅强调色 |
| ACCENT_GRADIENT | gradient | 强调色渐变 |

### 3. 语义色组 (Semantic Colors) - 20个
| 常量 | 类型 | 说明 |
|------|------|------|
| SUCCESS / SUCCESS_LIGHT / SUCCESS_DARK / SUCCESS_BG / SUCCESS_GRADIENT | color/gradient | 成功色系 |
| ERROR / ERROR_LIGHT / ERROR_DARK / ERROR_BG / ERROR_GRADIENT | color/gradient | 错误色系 |
| WARNING / WARNING_LIGHT / WARNING_DARK / WARNING_BG / WARNING_GRADIENT | color/gradient | 警告色系 |
| INFO / INFO_LIGHT / INFO_DARK / INFO_BG / INFO_GRADIENT | color/gradient | 信息色系 |

### 4. 文字色组 (Text Colors) - 5个
| 常量 | 类型 | 说明 |
|------|------|------|
| TEXT_PRIMARY | color | 主文字色 |
| TEXT_SECONDARY | color | 次文字色 |
| TEXT_TERTIARY | color | 三级文字色 |
| TEXT_PLACEHOLDER | color | 占位符色 |
| TEXT_DISABLED | color | 禁用文字色 |

### 5. 背景色组 (Background Colors) - 9个
| 常量 | 类型 | 说明 |
|------|------|------|
| BG_PRIMARY | color | 主背景色 |
| BG_SECONDARY | color | 次背景色 |
| BG_TERTIARY | color | 三级背景色 |
| BG_CARD | color | 卡片背景 |
| BG_CARD_HOVER | color | 卡片悬浮背景 |
| BG_GRADIENT | gradient | 背景渐变 |
| BG_MUTED | color | 柔和背景 |
| BG_ACCENT | color | 强调背景 |
| GLASS_BG | color | 玻璃态背景 |

### 6. 边框与特效组 (Borders & Effects) - 8个
| 常量 | 类型 | 说明 |
|------|------|------|
| BORDER_DEFAULT | color | 默认边框 |
| BORDER_LIGHT | color | 浅边框 |
| BORDER_DARK | color | 深边框 |
| SHADOW_COLOR | color | 阴影颜色 |
| OVERLAY_COLOR | color | 遮罩颜色 |
| SHADOW_CARD | shadow | 卡片阴影 |
| SHADOW_CARD_HOVER | shadow | 卡片悬浮阴影 |
| SHADOW_SIENNA / SHADOW_SIENNA_HOVER | shadow | 书香阴影 |

### 7. 按钮文字组 (Button Text) - 2个
| 常量 | 类型 | 说明 |
|------|------|------|
| BUTTON_TEXT | color | 按钮主文字 |
| BUTTON_TEXT_SECONDARY | color | 按钮次文字 |

### 8. 字体配置组 (Typography) - 25个
| 常量 | 类型 | 说明 |
|------|------|------|
| FONT_HEADING | font-family | 标题字体 |
| FONT_BODY | font-family | 正文字体 |
| FONT_DISPLAY | font-family | 展示字体 |
| FONT_UI | font-family | UI字体 |
| FONT_SIZE_XS ~ FONT_SIZE_3XL | size | 字体大小（8个） |
| FONT_WEIGHT_NORMAL ~ FONT_WEIGHT_BOLD | number | 字体粗细（4个） |
| LINE_HEIGHT_TIGHT ~ LINE_HEIGHT_LOOSE | number | 行高（4个） |
| LETTER_SPACING_TIGHT ~ LETTER_SPACING_WIDEST | size | 字间距（5个） |

### 9. 圆角配置组 (Border Radius) - 11个
| 常量 | 类型 | 说明 |
|------|------|------|
| RADIUS_XS | size | 超小圆角 |
| RADIUS_SM | size | 小圆角 |
| RADIUS_MD | size | 中等圆角 |
| RADIUS_LG | size | 大圆角 |
| RADIUS_XL | size | 超大圆角 |
| RADIUS_2XL | size | 特大圆角 |
| RADIUS_3XL | size | 超特大圆角 |
| RADIUS_ROUND | size | 圆形 |
| RADIUS_ORGANIC | string | 有机圆角 |
| RADIUS_PILL | size | 药丸形 |

### 10. 间距配置组 (Spacing) - 6个
| 常量 | 类型 | 说明 |
|------|------|------|
| SPACING_XS | size | 超小间距 |
| SPACING_SM | size | 小间距 |
| SPACING_MD | size | 中等间距 |
| SPACING_LG | size | 大间距 |
| SPACING_XL | size | 超大间距 |
| SPACING_XXL | size | 特大间距 |

### 11. 动画配置组 (Animation) - 5个
| 常量 | 类型 | 说明 |
|------|------|------|
| TRANSITION_FAST | time | 快速过渡 |
| TRANSITION_BASE | time | 标准过渡 |
| TRANSITION_SLOW | time | 缓慢过渡 |
| TRANSITION_DRAMATIC | time | 戏剧性过渡 |
| EASING_DEFAULT | string | 默认缓动函数 |

### 12. 按钮尺寸组 (Button Sizes) - 6个
| 常量 | 类型 | 说明 |
|------|------|------|
| BUTTON_HEIGHT_SM | size | 小按钮高度 |
| BUTTON_HEIGHT_DEFAULT | size | 默认按钮高度 |
| BUTTON_HEIGHT_LG | size | 大按钮高度 |
| BUTTON_PADDING_SM | size | 小按钮内边距 |
| BUTTON_PADDING_DEFAULT | size | 默认按钮内边距 |
| BUTTON_PADDING_LG | size | 大按钮内边距 |

---

## 三、数据库设计

### ThemeConfig 模型

```python
class ThemeConfig(Base):
    __tablename__ = "theme_configs"

    id: int                    # 主键
    user_id: int               # 用户ID（外键）
    config_name: str           # 子主题名称，如"我的书香主题"
    parent_mode: str           # "light" 或 "dark"
    is_active: bool            # 是否激活（每个parent_mode下只能有一个）

    # JSON存储各组配置
    primary_colors: JSON       # 主色调组
    accent_colors: JSON        # 强调色组
    semantic_colors: JSON      # 语义色组
    text_colors: JSON          # 文字色组
    background_colors: JSON    # 背景色组
    border_effects: JSON       # 边框与特效组
    button_colors: JSON        # 按钮文字组
    typography: JSON           # 字体配置组
    border_radius: JSON        # 圆角配置组
    spacing: JSON              # 间距配置组
    animation: JSON            # 动画配置组
    button_sizes: JSON         # 按钮尺寸组

    created_at: datetime
    updated_at: datetime
```

---

## 四、API设计

### 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/theme-configs | 获取用户所有主题配置 |
| GET | /api/theme-configs/{id} | 获取单个配置详情 |
| POST | /api/theme-configs | 创建新子主题 |
| PUT | /api/theme-configs/{id} | 更新子主题配置 |
| DELETE | /api/theme-configs/{id} | 删除子主题 |
| POST | /api/theme-configs/{id}/activate | 激活子主题 |
| POST | /api/theme-configs/{id}/duplicate | 复制子主题 |
| GET | /api/theme-configs/defaults/{mode} | 获取指定模式的默认值 |
| POST | /api/theme-configs/{id}/reset | 重置为默认值 |
| GET | /api/theme-configs/{id}/export | 导出配置 |
| POST | /api/theme-configs/import | 导入配置 |

---

## 五、前端实现

### 1. 新建UI组件

#### ColorPickerWidget (`frontend/components/inputs/color_picker.py`)
```
┌─────────────────────────────────────┐
│ [#8B4513] [████████] [选择颜色...] │
└─────────────────────────────────────┘
```
- 16进制颜色输入框
- 颜色预览块
- 点击弹出QColorDialog

#### SizeInputWidget (`frontend/components/inputs/size_input.py`)
```
┌─────────────────────────┐
│ [24] [px ▼]            │
└─────────────────────────┘
```
- 数值输入
- 单位选择（px, em, %, ms）

#### FontFamilySelector (`frontend/components/inputs/font_selector.py`)
```
┌─────────────────────────────────────┐
│ [Georgia, Times New Roman ▼]       │
└─────────────────────────────────────┘
```
- 下拉选择常用字体族
- 支持手动输入

#### GradientEditor (`frontend/components/inputs/gradient_editor.py`)
```
┌─────────────────────────────────────┐
│ 渐变预览条                          │
├─────────────────────────────────────┤
│ 色标1: [#xxx] 位置: [0%]  [×]      │
│ 色标2: [#xxx] 位置: [100%] [×]     │
│ [+ 添加色标]                        │
└─────────────────────────────────────┘
```

#### ShadowEditor (`frontend/components/inputs/shadow_editor.py`)
```
┌─────────────────────────────────────┐
│ X偏移: [0]  Y偏移: [4]             │
│ 模糊: [20]  扩展: [-2]             │
│ 颜色: [#xxx] [████]                │
│ 预览: ┌─────┐                       │
│       │     │                       │
│       └─────┘                       │
└─────────────────────────────────────┘
```

### 2. 主题设置Widget (`frontend/windows/settings/theme_settings_widget.py`)

```
┌──────────────────────────────────────────────────────────────────┐
│ [浅色主题] [深色主题]                              顶部Tab切换    │
├────────────────┬─────────────────────────────────────────────────┤
│ 子主题列表     │ 配置编辑区（可滚动）                            │
│ ┌────────────┐ │ ┌─────────────────────────────────────────────┐ │
│ │ + 新建     │ │ │ ▼ 主色调                                    │ │
│ ├────────────┤ │ │   PRIMARY        [#8B4513] [████]           │ │
│ │ 书香浅色 ★ │ │ │   PRIMARY_LIGHT  [#A0522D] [████]           │ │
│ │ 我的主题   │ │ │   PRIMARY_DARK   [#6B3410] [████]           │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ ├─────────────────────────────────────────────┤ │
│ │            │ │ │ ▼ 强调色                                    │ │
│ │            │ │ │   ACCENT         [#A0522D] [████]           │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ ├─────────────────────────────────────────────┤ │
│ │            │ │ │ ▼ 文字色                                    │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ ├─────────────────────────────────────────────┤ │
│ │            │ │ │ ▼ 背景色                                    │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ ├─────────────────────────────────────────────┤ │
│ │            │ │ │ ▼ 字体配置                                  │ │
│ │            │ │ │   FONT_HEADING   [Georgia, serif ▼]         │ │
│ │            │ │ │   FONT_SIZE_BASE [14] [px]                  │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ ├─────────────────────────────────────────────┤ │
│ │            │ │ │ ▼ 圆角配置                                  │ │
│ │            │ │ │   RADIUS_SM      [4] [px]                   │ │
│ │            │ │ │   ...                                       │ │
│ │            │ │ └─────────────────────────────────────────────┘ │
│ └────────────┘ │                                                 │
├────────────────┴─────────────────────────────────────────────────┤
│ [重置为默认]                    [预览] [保存] [激活]             │
└──────────────────────────────────────────────────────────────────┘
```

### 3. 修改theme_manager支持自定义主题

```python
# frontend/themes/theme_manager/core.py

class ThemeManager:
    def __init__(self):
        self._current_mode = ThemeMode.LIGHT
        self._current_theme = LightTheme  # 默认使用内置主题
        self._custom_theme_config = None  # 自定义配置
        self._use_custom = False          # 是否使用自定义

    def apply_custom_theme(self, config: dict, save: bool = True):
        """应用自定义主题配置"""
        self._custom_theme_config = config
        self._use_custom = True
        # 创建动态主题类
        self._current_theme = self._create_theme_from_config(config)
        self.theme_changed.emit(self._current_mode.value)

    def reset_to_default(self):
        """重置为默认主题"""
        self._use_custom = False
        self._custom_theme_config = None
        self._current_theme = DarkTheme if self._current_mode == ThemeMode.DARK else LightTheme
        self.theme_changed.emit(self._current_mode.value)

    def _create_theme_from_config(self, config: dict):
        """从配置创建动态主题类"""
        # 创建一个动态类，包含所有配置的属性
        class CustomTheme:
            pass

        # 设置所有属性
        for key, value in config.items():
            setattr(CustomTheme, key, value)

        return CustomTheme
```

### 4. API客户端Mixin

```python
# frontend/api/client/theme_config_mixin.py

class ThemeConfigMixin:
    """主题配置API方法"""

    def get_theme_configs(self) -> List[dict]:
        """获取所有主题配置"""
        return self._request('GET', '/api/theme-configs')

    def get_theme_config(self, config_id: int) -> dict:
        """获取单个配置"""
        return self._request('GET', f'/api/theme-configs/{config_id}')

    def create_theme_config(self, data: dict) -> dict:
        """创建新子主题"""
        return self._request('POST', '/api/theme-configs', data)

    def update_theme_config(self, config_id: int, data: dict) -> dict:
        """更新配置"""
        return self._request('PUT', f'/api/theme-configs/{config_id}', data)

    def delete_theme_config(self, config_id: int) -> None:
        """删除配置"""
        return self._request('DELETE', f'/api/theme-configs/{config_id}')

    def activate_theme_config(self, config_id: int) -> dict:
        """激活配置"""
        return self._request('POST', f'/api/theme-configs/{config_id}/activate')

    def get_theme_defaults(self, mode: str) -> dict:
        """获取默认值"""
        return self._request('GET', f'/api/theme-configs/defaults/{mode}')

    def reset_theme_config(self, config_id: int) -> dict:
        """重置为默认"""
        return self._request('POST', f'/api/theme-configs/{config_id}/reset')

    def duplicate_theme_config(self, config_id: int) -> dict:
        """复制配置"""
        return self._request('POST', f'/api/theme-configs/{config_id}/duplicate')

    def export_theme_config(self, config_id: int) -> dict:
        """导出配置"""
        return self._request('GET', f'/api/theme-configs/{config_id}/export')

    def import_theme_configs(self, data: dict) -> dict:
        """导入配置"""
        return self._request('POST', '/api/theme-configs/import', data)
```

---

## 六、实现文件清单

### 后端新建文件（6个）
1. `backend/app/models/theme_config.py` - 数据模型
2. `backend/app/schemas/theme_config.py` - Pydantic schemas
3. `backend/app/repositories/theme_config_repository.py` - Repository
4. `backend/app/services/theme_config_service.py` - Service
5. `backend/app/api/routers/theme_config.py` - API路由

### 后端修改文件（2个）
1. `backend/app/core/dependencies.py` - 注册依赖注入
2. `backend/app/api/routers/__init__.py` - 注册路由

### 前端新建文件（7个）
1. `frontend/components/inputs/__init__.py` - 输入组件包
2. `frontend/components/inputs/color_picker.py` - 颜色选择器
3. `frontend/components/inputs/size_input.py` - 尺寸输入
4. `frontend/components/inputs/font_selector.py` - 字体选择器
5. `frontend/components/inputs/gradient_editor.py` - 渐变编辑器
6. `frontend/components/inputs/shadow_editor.py` - 阴影编辑器
7. `frontend/windows/settings/theme_settings_widget.py` - 主题设置Widget
8. `frontend/api/client/theme_config_mixin.py` - API Mixin

### 前端修改文件（4个）
1. `frontend/api/client/core.py` - 添加ThemeConfigMixin
2. `frontend/windows/settings/view.py` - 添加主题设置导航项
3. `frontend/themes/theme_manager/core.py` - 支持自定义主题
4. `frontend/themes/theme_manager/themes.py` - 导出默认值字典

---

## 七、实现顺序

### 第一阶段：后端基础设施
1. 创建ThemeConfig模型和Schema
2. 创建Repository和Service
3. 创建API路由
4. 注册依赖注入
5. 测试API端点

### 第二阶段：前端输入组件
1. 创建ColorPickerWidget
2. 创建SizeInputWidget
3. 创建FontFamilySelector
4. 创建GradientEditor（可简化）
5. 创建ShadowEditor（可简化）

### 第三阶段：主题设置页面
1. 创建ThemeSettingsWidget
2. 实现子主题列表管理
3. 实现配置分组编辑区
4. 实现预览功能
5. 集成到设置页面

### 第四阶段：主题管理器改造
1. 修改theme_manager支持自定义配置
2. 实现启动时加载用户配置
3. 实现实时预览和应用
4. 导出默认值供API使用

### 第五阶段：导入导出与完善
1. 实现配置导入导出
2. 添加错误处理
3. 性能优化
4. 文档更新

---

## 八、注意事项

1. **默认配置自动创建**：用户首次使用时，自动基于内置主题创建默认的浅色和深色子主题

2. **渐变和阴影简化**：初版可以将渐变和阴影作为字符串直接编辑，后续再开发可视化编辑器

3. **预览机制**：预览时临时应用配置但不保存，用户确认后再保存

4. **性能考虑**：配置较多时使用懒加载，只加载当前可见的配置组

5. **配置验证**：后端需验证配置值的格式（颜色格式、尺寸格式等）

6. **兼容性**：保证旧版本（无自定义配置）的兼容性，自动使用内置主题
