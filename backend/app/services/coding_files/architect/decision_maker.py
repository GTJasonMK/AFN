"""
架构决策制定器

阶段二：基于项目画像选择/确认架构模式，生成架构决策。
支持用户干预（指定架构偏好）。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    ArchitectureDecision,
    ArchitecturePattern,
    LayerDefinition,
    ModulePlacement,
    ModuleSummary,
    ProjectProfile,
    SharedModuleStrategy,
)
from .patterns import get_pattern_template, PatternTemplate

logger = logging.getLogger(__name__)


class ArchitectureDecisionMaker:
    """
    架构决策制定器

    基于项目画像和架构模式模板，生成完整的架构决策：
    - 选择架构模式（用户指定或自动推荐）
    - 生成层级定义
    - 生成模块放置计划
    - 确定共享模块策略
    """

    def __init__(
        self,
        profile: ProjectProfile,
        user_preference: Optional[ArchitecturePattern] = None,
        custom_constraints: Optional[List[str]] = None,
    ):
        """
        初始化架构决策器

        Args:
            profile: 项目画像
            user_preference: 用户指定的架构模式（可选）
            custom_constraints: 用户自定义约束（可选）
        """
        self.profile = profile
        self.user_preference = user_preference
        self.custom_constraints = custom_constraints or []

    def make_decision(self) -> ArchitectureDecision:
        """
        制定架构决策

        Returns:
            ArchitectureDecision: 完整的架构决策
        """
        logger.info("开始制定架构决策: %s", self.profile.project_id)

        # 1. 确定架构模式
        pattern, pattern_rationale = self._determine_pattern()
        logger.info("选定架构模式: %s - %s", pattern.value, pattern_rationale)

        # 2. 获取模式模板
        template = get_pattern_template(pattern)

        # 3. 生成层级定义
        layers = self._generate_layers(template)

        # 4. 生成模块放置计划
        module_placements = self._generate_module_placements(template)

        # 5. 确定共享模块策略
        shared_strategy = self._determine_shared_strategy(template)

        # 6. 确定命名约定
        naming_convention = template.get_naming_convention(self.profile.primary_language)

        decision = ArchitectureDecision(
            pattern=pattern,
            pattern_rationale=pattern_rationale,
            layers=layers,
            module_placements=module_placements,
            shared_strategy=shared_strategy,
            naming_convention=naming_convention,
            root_path=template.root_path,
            create_init_files=self.profile.primary_language.lower() == "python",
            custom_constraints=self.custom_constraints,
        )

        logger.info(
            "架构决策完成: 模式=%s, 层级=%d, 模块放置=%d",
            pattern.value,
            len(layers),
            len(module_placements),
        )

        return decision

    def _determine_pattern(self) -> Tuple[ArchitecturePattern, str]:
        """
        确定架构模式

        优先级：用户指定 > 自动推荐

        Returns:
            (架构模式, 选择理由)
        """
        if self.user_preference:
            return (
                self.user_preference,
                f"用户指定使用{self.user_preference.value}架构模式"
            )

        # 使用画像中的推荐
        if self.profile.recommended_pattern:
            return (
                self.profile.recommended_pattern,
                self.profile.recommendation_reason
            )

        # 默认使用SIMPLE
        return (
            ArchitecturePattern.SIMPLE,
            "默认使用简单架构"
        )

    def _generate_layers(self, template: PatternTemplate) -> List[LayerDefinition]:
        """
        生成层级定义

        Args:
            template: 架构模式模板

        Returns:
            层级定义列表
        """
        # 对于FEATURE_BASED模式，需要为每个系统创建特征目录
        if template.pattern == ArchitecturePattern.FEATURE_BASED:
            return self._generate_feature_based_layers(template)

        # 其他模式直接使用模板定义
        return template.layers.copy()

    def _generate_feature_based_layers(
        self,
        template: PatternTemplate,
    ) -> List[LayerDefinition]:
        """
        为FEATURE_BASED模式生成层级定义

        每个系统作为一个独立的功能模块
        """
        layers = []

        # 添加基础层级（shared, core）
        for layer in template.layers:
            if layer.name in ["shared", "core"]:
                layers.append(layer)

        # 为每个系统创建功能模块层级
        for system in self.profile.systems:
            system_name = self._normalize_name(system.name)
            layer = LayerDefinition(
                name=f"feature_{system_name}",
                path=f"src/features/{system_name}",
                description=f"功能模块: {system.name} - {system.description[:50]}",
                allowed_dependencies=["shared", "core"],
            )
            layers.append(layer)

        return layers

    def _generate_module_placements(
        self,
        template: PatternTemplate,
    ) -> List[ModulePlacement]:
        """
        生成模块放置计划

        Args:
            template: 架构模式模板

        Returns:
            模块放置计划列表
        """
        placements = []

        # 获取所有模块
        all_modules = self.profile.get_all_modules()

        for module in all_modules:
            placement = self._place_module(module, template)
            if placement:
                placements.append(placement)

        return placements

    def _place_module(
        self,
        module: ModuleSummary,
        template: PatternTemplate,
    ) -> Optional[ModulePlacement]:
        """
        确定单个模块的放置位置

        Args:
            module: 模块摘要
            template: 架构模式模板

        Returns:
            模块放置计划
        """
        module_type = module.module_type.lower()
        module_name = self._normalize_name(module.name)

        # 根据模式确定目标层级
        if template.pattern == ArchitecturePattern.FEATURE_BASED:
            # FEATURE_BASED: 放在对应系统的功能模块下
            target_layer = self._get_feature_layer_for_module(module)
            if target_layer:
                target_path = f"{target_layer}/{module_name}"
            else:
                target_path = f"src/features/{module_name}"
        else:
            # LAYERED/SIMPLE: 根据模块类型确定层级
            target_layer = template.get_layer_for_module_type(module_type)
            if target_layer:
                layer_path = template.get_layer_path(target_layer)
                target_path = f"{layer_path}/{module_name}"
            else:
                # 默认放在services目录
                target_path = f"{template.root_path}/services/{module_name}"
                target_layer = "services"

        # 确定需要创建的文件
        files_to_create = self._determine_files_for_module(module, template)

        # 生成放置理由
        rationale = self._generate_placement_rationale(module, target_layer, template)

        return ModulePlacement(
            module_number=module.module_number,
            module_name=module.name,
            target_layer=target_layer or "default",
            target_path=target_path,
            files_to_create=files_to_create,
            rationale=rationale,
        )

    def _get_feature_layer_for_module(self, module: ModuleSummary) -> Optional[str]:
        """
        获取模块对应的功能层级路径

        对于FEATURE_BASED模式，根据模块所属系统确定
        """
        # 查找模块所属的系统
        for system in self.profile.systems:
            if system.system_number == module.system_number:
                system_name = self._normalize_name(system.name)
                return f"src/features/{system_name}"
        return None

    def _determine_files_for_module(
        self,
        module: ModuleSummary,
        template: PatternTemplate,
    ) -> List[str]:
        """
        确定模块需要创建的文件列表
        """
        files = []
        module_type = module.module_type.lower()
        naming = template.get_naming_convention(self.profile.primary_language)
        ext = self._get_file_extension()

        # 根据模块类型确定文件
        if module_type in ["service", "use_case", "usecase", "application_service"]:
            files.append(f"service{ext}")
            if module.interface:
                files.append(f"interface{ext}")
        elif module_type in ["repository"]:
            files.append(f"repository{ext}")
            files.append(f"models{ext}")
        elif module_type in ["controller", "handler", "api"]:
            files.append(f"controller{ext}")
            files.append(f"routes{ext}")
        elif module_type in ["entity", "domain_service", "aggregate"]:
            files.append(f"entity{ext}")
            files.append(f"value_objects{ext}")
        else:
            # 默认
            files.append(f"{module_type}{ext}")

        return files

    def _get_file_extension(self) -> str:
        """获取文件扩展名"""
        lang = self.profile.primary_language.lower()
        extensions = {
            "python": ".py",
            "typescript": ".ts",
            "javascript": ".js",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
            "kotlin": ".kt",
            "swift": ".swift",
        }
        return extensions.get(lang, ".py")

    def _generate_placement_rationale(
        self,
        module: ModuleSummary,
        target_layer: str,
        template: PatternTemplate,
    ) -> str:
        """生成放置理由"""
        pattern_name = template.pattern.value
        return (
            f"模块类型为{module.module_type}，"
            f"在{pattern_name}架构中属于{target_layer}层"
        )

    def _determine_shared_strategy(
        self,
        template: PatternTemplate,
    ) -> SharedModuleStrategy:
        """
        确定共享模块策略

        识别哪些模块应该被提取为共享模块
        """
        strategy = SharedModuleStrategy(
            shared_path=template.shared_strategy.shared_path,
            criteria=template.shared_strategy.criteria.copy(),
            candidates=[],
        )

        # 识别候选共享模块
        # 1. 高依赖模块（被3+模块依赖）
        for module_name in self.profile.dependency_graph.high_dependency_modules:
            if module_name not in strategy.candidates:
                strategy.candidates.append(module_name)

        # 2. 工具类模块
        all_modules = self.profile.get_all_modules()
        for module in all_modules:
            if module.module_type.lower() in ["utility", "util", "helper", "common"]:
                if module.name not in strategy.candidates:
                    strategy.candidates.append(module.name)

        return strategy

    def _normalize_name(self, name: str) -> str:
        """
        规范化名称（用于路径）

        转换为snake_case
        """
        # 移除特殊字符，转为小写，用下划线分隔
        import re
        # 先处理驼峰命名
        name = re.sub(r'([A-Z])', r'_\1', name)
        # 替换非字母数字为下划线
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # 转小写并去除连续下划线
        name = re.sub(r'_+', '_', name.lower())
        # 去除首尾下划线
        return name.strip('_')
