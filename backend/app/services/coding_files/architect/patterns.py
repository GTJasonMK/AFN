"""
架构模式模板定义

预定义3种核心架构模式：
1. LAYERED - 分层架构
2. FEATURE_BASED - 功能模块架构
3. SIMPLE - 简单架构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .schemas import ArchitecturePattern, LayerDefinition, SharedModuleStrategy


@dataclass
class PatternTemplate:
    """
    架构模式模板

    定义一个架构模式的完整规范，包括：
    - 层级结构
    - 模块类型到层级的映射
    - 命名约定
    - 依赖规则
    """
    pattern: ArchitecturePattern
    description: str
    suitable_for: List[str]  # 适用场景

    # 层级定义
    layers: List[LayerDefinition]

    # 模块类型到层级的映射规则
    module_type_mapping: Dict[str, str]

    # 共享模块策略
    shared_strategy: SharedModuleStrategy

    # 语言特定的命名约定
    naming_conventions: Dict[str, str]

    # 根目录
    root_path: str = "src"

    # 最大推荐深度
    max_recommended_depth: int = 4

    def get_layer_for_module_type(self, module_type: str) -> Optional[str]:
        """根据模块类型获取目标层级"""
        # 先精确匹配
        if module_type in self.module_type_mapping:
            return self.module_type_mapping[module_type]
        # 再模糊匹配
        module_type_lower = module_type.lower()
        for key, layer in self.module_type_mapping.items():
            if key.lower() in module_type_lower or module_type_lower in key.lower():
                return layer
        return None

    def get_layer_path(self, layer_name: str) -> Optional[str]:
        """根据层级名称获取路径"""
        for layer in self.layers:
            if layer.name == layer_name:
                return layer.path
        return None

    def get_naming_convention(self, language: str) -> str:
        """根据语言获取命名约定"""
        lang_lower = language.lower()
        if lang_lower in self.naming_conventions:
            return self.naming_conventions[lang_lower]
        # 默认根据语言类型推断
        if lang_lower in ["python", "ruby", "rust", "go"]:
            return "snake_case"
        elif lang_lower in ["typescript", "javascript", "java", "kotlin", "swift"]:
            return "kebab-case"
        return "snake_case"


# ==================== LAYERED: 分层架构 ====================

LAYERED_TEMPLATE = PatternTemplate(
    pattern=ArchitecturePattern.LAYERED,
    description="经典分层架构：表现层、应用层、领域层、基础设施层",
    suitable_for=[
        "中大型Web应用",
        "企业级API服务",
        "需要清晰职责分离的项目",
        "多人协作的团队项目",
    ],
    layers=[
        LayerDefinition(
            name="presentation",
            path="src/presentation",
            description="表现层：API路由、控制器、请求/响应处理",
            allowed_dependencies=["application", "shared"],
        ),
        LayerDefinition(
            name="application",
            path="src/application",
            description="应用层：用例、服务编排、业务流程",
            allowed_dependencies=["domain", "infrastructure", "shared"],
        ),
        LayerDefinition(
            name="domain",
            path="src/domain",
            description="领域层：核心业务逻辑、实体、领域服务",
            allowed_dependencies=["shared"],
        ),
        LayerDefinition(
            name="infrastructure",
            path="src/infrastructure",
            description="基础设施层：数据库、外部服务、技术实现",
            allowed_dependencies=["domain", "shared"],
        ),
        LayerDefinition(
            name="shared",
            path="src/shared",
            description="共享模块：工具类、常量、通用类型",
            allowed_dependencies=[],
        ),
    ],
    module_type_mapping={
        # 表现层
        "controller": "presentation",
        "handler": "presentation",
        "router": "presentation",
        "api": "presentation",
        "view": "presentation",
        # 应用层
        "service": "application",
        "use_case": "application",
        "usecase": "application",
        "application_service": "application",
        "orchestrator": "application",
        # 领域层
        "entity": "domain",
        "domain_service": "domain",
        "aggregate": "domain",
        "value_object": "domain",
        "domain_event": "domain",
        # 基础设施层
        "repository": "infrastructure",
        "adapter": "infrastructure",
        "gateway": "infrastructure",
        "client": "infrastructure",
        "provider": "infrastructure",
        # 共享
        "utility": "shared",
        "util": "shared",
        "helper": "shared",
        "common": "shared",
        "config": "shared",
    },
    shared_strategy=SharedModuleStrategy(
        shared_path="src/shared",
        criteria=["被3个以上模块依赖", "纯工具类/常量", "无业务逻辑"],
        candidates=[],
    ),
    naming_conventions={
        "python": "snake_case",
        "typescript": "kebab-case",
        "javascript": "kebab-case",
        "go": "snake_case",
        "java": "camelCase",
    },
    root_path="src",
    max_recommended_depth=4,
)


# ==================== FEATURE_BASED: 功能模块架构 ====================

FEATURE_BASED_TEMPLATE = PatternTemplate(
    pattern=ArchitecturePattern.FEATURE_BASED,
    description="按功能模块划分：每个功能模块包含自己的所有层级",
    suitable_for=[
        "微服务架构",
        "模块化单体应用",
        "功能独立性强的项目",
        "需要独立部署的子模块",
    ],
    layers=[
        LayerDefinition(
            name="features",
            path="src/features",
            description="功能模块目录：每个子目录是一个完整的功能模块",
            allowed_dependencies=["shared", "core"],
        ),
        LayerDefinition(
            name="shared",
            path="src/shared",
            description="跨功能共享的代码：工具、类型、常量",
            allowed_dependencies=[],
        ),
        LayerDefinition(
            name="core",
            path="src/core",
            description="核心基础设施：数据库连接、认证、配置",
            allowed_dependencies=["shared"],
        ),
    ],
    module_type_mapping={
        # 所有业务相关的模块类型都放在features下
        "controller": "features",
        "handler": "features",
        "service": "features",
        "repository": "features",
        "entity": "features",
        "use_case": "features",
        "usecase": "features",
        "api": "features",
        "model": "features",
        # 核心基础设施
        "adapter": "core",
        "gateway": "core",
        "client": "core",
        "provider": "core",
        "middleware": "core",
        # 共享
        "utility": "shared",
        "util": "shared",
        "helper": "shared",
        "common": "shared",
        "config": "shared",
    },
    shared_strategy=SharedModuleStrategy(
        shared_path="src/shared",
        criteria=["被2个以上功能模块依赖", "无业务逻辑", "通用工具"],
        candidates=[],
    ),
    naming_conventions={
        "python": "snake_case",
        "typescript": "kebab-case",
        "javascript": "kebab-case",
        "go": "snake_case",
        "java": "camelCase",
    },
    root_path="src",
    max_recommended_depth=4,
)


# ==================== SIMPLE: 简单架构 ====================

SIMPLE_TEMPLATE = PatternTemplate(
    pattern=ArchitecturePattern.SIMPLE,
    description="简单架构：适合小型项目，按职责简单划分",
    suitable_for=[
        "小型项目（<10个模块）",
        "原型/MVP",
        "脚本工具",
        "学习项目",
    ],
    layers=[
        LayerDefinition(
            name="components",
            path="src/components",
            description="业务组件：主要业务逻辑",
            allowed_dependencies=["services", "utils"],
        ),
        LayerDefinition(
            name="services",
            path="src/services",
            description="服务层：核心服务实现",
            allowed_dependencies=["utils"],
        ),
        LayerDefinition(
            name="utils",
            path="src/utils",
            description="工具层：通用工具和辅助函数",
            allowed_dependencies=[],
        ),
    ],
    module_type_mapping={
        # 组件
        "controller": "components",
        "handler": "components",
        "api": "components",
        "view": "components",
        "model": "components",
        # 服务
        "service": "services",
        "repository": "services",
        "use_case": "services",
        "usecase": "services",
        "adapter": "services",
        "client": "services",
        # 工具
        "utility": "utils",
        "util": "utils",
        "helper": "utils",
        "common": "utils",
        "config": "utils",
    },
    shared_strategy=SharedModuleStrategy(
        shared_path="src/utils",
        criteria=["被多个模块依赖"],
        candidates=[],
    ),
    naming_conventions={
        "python": "snake_case",
        "typescript": "kebab-case",
        "javascript": "kebab-case",
        "go": "snake_case",
        "java": "camelCase",
    },
    root_path="src",
    max_recommended_depth=3,
)


# ==================== 模板注册表 ====================

PATTERN_TEMPLATES: Dict[ArchitecturePattern, PatternTemplate] = {
    ArchitecturePattern.LAYERED: LAYERED_TEMPLATE,
    ArchitecturePattern.FEATURE_BASED: FEATURE_BASED_TEMPLATE,
    ArchitecturePattern.SIMPLE: SIMPLE_TEMPLATE,
}


def get_pattern_template(pattern: ArchitecturePattern) -> PatternTemplate:
    """获取架构模式模板"""
    if pattern not in PATTERN_TEMPLATES:
        # 默认返回SIMPLE
        return PATTERN_TEMPLATES[ArchitecturePattern.SIMPLE]
    return PATTERN_TEMPLATES[pattern]


def recommend_pattern(
    total_modules: int,
    total_systems: int,
    project_type: str,
    tech_style: str,
) -> tuple[ArchitecturePattern, str]:
    """
    根据项目特征推荐架构模式

    Args:
        total_modules: 模块总数
        total_systems: 系统总数
        project_type: 项目类型
        tech_style: 技术风格

    Returns:
        (推荐模式, 推荐理由)
    """
    # 规则1：小型项目（<10模块）使用SIMPLE
    if total_modules < 10:
        return (
            ArchitecturePattern.SIMPLE,
            f"项目规模较小（{total_modules}个模块），推荐使用简单架构以降低复杂度"
        )

    # 规则2：微服务风格使用FEATURE_BASED
    if "微服务" in tech_style or "modular" in tech_style.lower():
        return (
            ArchitecturePattern.FEATURE_BASED,
            f"项目采用{tech_style}风格，推荐使用功能模块架构便于独立部署"
        )

    # 规则3：多系统（>3）使用FEATURE_BASED
    if total_systems > 3:
        return (
            ArchitecturePattern.FEATURE_BASED,
            f"项目包含{total_systems}个系统，推荐使用功能模块架构便于按系统组织代码"
        )

    # 规则4：Web应用/API服务使用LAYERED
    if any(kw in project_type.lower() for kw in ["web", "api", "服务", "应用"]):
        return (
            ArchitecturePattern.LAYERED,
            f"项目是{project_type}类型，推荐使用分层架构实现清晰的职责分离"
        )

    # 规则5：中型项目（10-30模块）默认LAYERED
    if 10 <= total_modules <= 30:
        return (
            ArchitecturePattern.LAYERED,
            f"项目规模中等（{total_modules}个模块），推荐使用分层架构"
        )

    # 规则6：大型项目（>30模块）使用FEATURE_BASED
    if total_modules > 30:
        return (
            ArchitecturePattern.FEATURE_BASED,
            f"项目规模较大（{total_modules}个模块），推荐使用功能模块架构便于团队协作"
        )

    # 默认使用LAYERED
    return (
        ArchitecturePattern.LAYERED,
        "默认推荐使用分层架构，适用于大多数项目"
    )
