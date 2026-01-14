"""
基于架构决策的目录结构生成器

阶段三（前半）：按架构决策生成完整的目录结构。
输出BruteForceOutput格式，保持与现有系统兼容。
支持LLM增强的文件描述生成。
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple

from ....utils.json_utils import parse_llm_json_safe
from ..directory_generator.schemas import (
    BruteForceOutput,
    DirectorySpec,
    FileSpec,
)
from .schemas import (
    ArchitectureDecision,
    ArchitecturePattern,
    ModulePlacement,
    ProjectProfile,
)
from .patterns import get_pattern_template

logger = logging.getLogger(__name__)

# 提示词Key
FILE_DESCRIPTION_PROMPT_KEY = "file_description_generation"


class ArchitectureBasedGenerator:
    """
    基于架构决策的目录结构生成器

    根据架构决策和模块放置计划，生成完整的目录结构。
    可选地调用LLM来增强文件描述。
    """

    def __init__(
        self,
        profile: ProjectProfile,
        decision: ArchitectureDecision,
        llm_service=None,
        user_id: int = 1,
        prompt_service=None,
    ):
        """
        初始化生成器

        Args:
            profile: 项目画像
            decision: 架构决策
            llm_service: LLM服务（可选，用于增强描述）
            user_id: 用户ID
            prompt_service: 提示词服务
        """
        self.profile = profile
        self.decision = decision
        self.llm_service = llm_service
        self.user_id = user_id
        self.prompt_service = prompt_service

        # 内部状态
        self._directories: List[DirectorySpec] = []
        self._files: List[FileSpec] = []
        self._created_paths: Set[str] = set()

    def generate(self) -> BruteForceOutput:
        """
        生成目录结构

        Returns:
            BruteForceOutput: 生成的目录结构
        """
        logger.info(
            "开始生成目录结构: 模式=%s, 模块数=%d",
            self.decision.pattern.value,
            len(self.decision.module_placements),
        )

        # 重置状态
        self._directories = []
        self._files = []
        self._created_paths = set()

        # 1. 创建基础层级目录
        self._create_layer_directories()

        # 2. 放置模块
        self._place_all_modules()

        # 3. 创建共享模块
        self._create_shared_modules()

        # 4. 添加Python __init__.py文件（如果需要）
        if self.decision.create_init_files:
            self._add_init_files()

        # 5. 生成输出
        output = BruteForceOutput(
            root_path=self.decision.root_path,
            directories=self._directories,
            files=self._files,
            shared_modules=[self.decision.shared_strategy.shared_path],
            architecture_notes=self._generate_architecture_notes(),
        )

        logger.info(
            "目录结构生成完成: 目录=%d, 文件=%d",
            len(self._directories),
            len(self._files),
        )

        return output

    async def generate_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成目录结构

        Yields:
            SSE事件
        """
        yield {
            "event": "progress",
            "data": {
                "stage": "generating",
                "message": f"按{self.decision.pattern.value}架构生成目录结构...",
            }
        }

        # 重置状态
        self._directories = []
        self._files = []
        self._created_paths = set()

        # 1. 创建基础层级目录
        yield {
            "event": "progress",
            "data": {
                "stage": "creating_layers",
                "message": f"创建{len(self.decision.layers)}个架构层级...",
            }
        }
        self._create_layer_directories()

        # 2. 放置模块
        total_modules = len(self.decision.module_placements)
        for i, placement in enumerate(self.decision.module_placements):
            self._place_module(placement)
            if (i + 1) % 5 == 0 or i == total_modules - 1:
                yield {
                    "event": "progress",
                    "data": {
                        "stage": "placing_modules",
                        "message": f"放置模块 {i + 1}/{total_modules}...",
                        "progress": (i + 1) / total_modules,
                    }
                }

        # 3. 创建共享模块
        yield {
            "event": "progress",
            "data": {
                "stage": "creating_shared",
                "message": "创建共享模块...",
            }
        }
        self._create_shared_modules()

        # 4. 添加__init__.py
        if self.decision.create_init_files:
            self._add_init_files()

        # 5. 使用LLM增强文件描述（如果提供了LLM服务）
        if self.llm_service and self.prompt_service:
            # 过滤出需要增强的文件（排除__init__.py等）
            files_to_enhance = [
                f for f in self._files
                if not f.filename.startswith("__") and f.module_number > 0
            ]
            async for event in self._enhance_file_descriptions_with_llm(files_to_enhance):
                yield event

        # 6. 生成输出
        output = BruteForceOutput(
            root_path=self.decision.root_path,
            directories=self._directories,
            files=self._files,
            shared_modules=[self.decision.shared_strategy.shared_path],
            architecture_notes=self._generate_architecture_notes(),
        )

        yield {
            "event": "structure",
            "data": {
                "directories": [d.model_dump() for d in self._directories],
                "files": [f.model_dump() for f in self._files],
                "shared_modules": output.shared_modules,
                "architecture_notes": output.architecture_notes,
            }
        }

        yield {
            "event": "complete",
            "data": {
                "success": True,
                "total_directories": len(self._directories),
                "total_files": len(self._files),
            }
        }

    def _create_layer_directories(self) -> None:
        """创建架构层级目录"""
        for layer in self.decision.layers:
            self._ensure_directory(
                path=layer.path,
                description=layer.description,
                module_numbers=[],
            )

    def _place_all_modules(self) -> None:
        """放置所有模块"""
        for placement in self.decision.module_placements:
            self._place_module(placement)

    def _place_module(self, placement: ModulePlacement) -> None:
        """
        放置单个模块

        Args:
            placement: 模块放置计划
        """
        # 获取模块详细信息
        module = self.profile.get_module_by_number(placement.module_number)
        if not module:
            logger.warning("模块不存在: %d", placement.module_number)
            return

        # 创建模块目录
        self._ensure_directory(
            path=placement.target_path,
            description=f"{module.name}: {module.description[:100]}",
            module_numbers=[placement.module_number],
        )

        # 创建模块文件
        for filename in placement.files_to_create:
            file_path = f"{placement.target_path}/{filename}"
            self._create_file(
                path=file_path,
                filename=filename,
                module=module,
                placement=placement,
            )

    def _create_file(
        self,
        path: str,
        filename: str,
        module,
        placement: ModulePlacement,
    ) -> None:
        """
        创建文件规格

        Args:
            path: 文件路径
            filename: 文件名
            module: 模块摘要
            placement: 放置计划
        """
        if path in self._created_paths:
            return

        # 确定文件类型
        file_type = self._determine_file_type(filename)

        # 确定语言
        language = self.profile.primary_language

        # 生成描述
        description = self._generate_file_description(filename, module)

        # 生成存在理由
        purpose = self._generate_file_purpose(filename, module, placement)

        # 解析依赖
        dependencies = self._parse_dependencies(module)
        dependency_reasons = self._generate_dependency_reasons(module)

        # 生成实现备注
        implementation_notes = self._generate_implementation_notes(filename, module)

        file_spec = FileSpec(
            path=path,
            filename=filename,
            file_type=file_type,
            language=language,
            description=description,
            purpose=purpose,
            module_number=module.module_number,
            priority=self._determine_priority(filename, module),
            dependencies=dependencies,
            dependency_reasons=dependency_reasons,
            implementation_notes=implementation_notes,
        )

        self._files.append(file_spec)
        self._created_paths.add(path)

    def _determine_file_type(self, filename: str) -> str:
        """确定文件类型"""
        filename_lower = filename.lower()

        if "test" in filename_lower or filename_lower.startswith("test_"):
            return "test"
        elif "config" in filename_lower:
            return "config"
        elif filename_lower.endswith((".md", ".rst", ".txt")):
            return "doc"
        elif "interface" in filename_lower or "types" in filename_lower:
            return "interface"
        elif "model" in filename_lower or "entity" in filename_lower:
            return "model"
        else:
            return "source"

    def _generate_file_description(self, filename: str, module) -> str:
        """生成文件功能描述"""
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        descriptions = {
            "service": f"实现{module.name}模块的核心业务逻辑",
            "repository": f"实现{module.name}模块的数据访问层",
            "controller": f"实现{module.name}模块的API接口处理",
            "routes": f"定义{module.name}模块的路由配置",
            "models": f"定义{module.name}模块的数据模型",
            "entity": f"定义{module.name}模块的领域实体",
            "interface": f"定义{module.name}模块的接口规范",
            "value_objects": f"定义{module.name}模块的值对象",
        }

        return descriptions.get(base_name, f"实现{module.name}模块的{base_name}功能")

    def _generate_file_purpose(
        self,
        filename: str,
        module,
        placement: ModulePlacement,
    ) -> str:
        """生成文件存在理由"""
        layer = placement.target_layer

        purposes = {
            "service": f"封装{module.name}的业务逻辑，提供统一的服务接口",
            "repository": f"隔离数据访问细节，为{module.name}提供数据持久化能力",
            "controller": f"处理HTTP请求，将请求转发给{module.name}服务",
            "routes": f"组织{module.name}模块的API路由，保持路由清晰",
            "models": f"定义{module.name}使用的数据结构，保证类型安全",
            "entity": f"表达{module.name}的核心业务概念",
            "interface": f"定义{module.name}的契约，支持依赖注入和测试",
        }

        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
        default_purpose = f"支持{module.name}模块在{layer}层的功能实现"

        return purposes.get(base_name, default_purpose)

    def _parse_dependencies(self, module) -> List[int]:
        """解析模块依赖为模块编号列表"""
        dependencies = []

        for dep_name in module.dependencies:
            # 在画像中查找依赖模块的编号
            for modules in self.profile.modules_by_type.values():
                for m in modules:
                    if m.name == dep_name:
                        dependencies.append(m.module_number)
                        break

        return dependencies

    def _generate_dependency_reasons(self, module) -> str:
        """生成依赖原因说明"""
        if not module.dependencies:
            return ""

        reasons = []
        for dep_name in module.dependencies[:5]:  # 最多5个
            reasons.append(f"依赖{dep_name}提供的功能")

        return "; ".join(reasons)

    def _generate_implementation_notes(self, filename: str, module) -> str:
        """生成实现备注"""
        notes = []

        # 根据文件类型添加实现建议
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        if base_name == "service":
            notes.append("使用依赖注入获取所需的Repository和其他Service")
            notes.append("业务逻辑应该在这里实现，不要泄漏到Controller")
        elif base_name == "repository":
            notes.append("使用异步数据库操作")
            notes.append("只负责数据访问，不包含业务逻辑")
        elif base_name == "controller":
            notes.append("只负责请求解析和响应格式化")
            notes.append("业务逻辑委托给Service层")

        # 添加模块接口相关备注
        if module.interface:
            notes.append(f"需实现接口: {module.interface[:100]}")

        return "; ".join(notes) if notes else ""

    def _determine_priority(self, filename: str, module) -> str:
        """确定文件优先级"""
        # 高优先级：核心服务文件
        high_priority_keywords = ["service", "repository", "entity"]
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

        if any(kw in base_name.lower() for kw in high_priority_keywords):
            return "high"

        # 中优先级：接口、控制器
        medium_priority_keywords = ["controller", "interface", "routes"]
        if any(kw in base_name.lower() for kw in medium_priority_keywords):
            return "medium"

        # 低优先级：其他
        return "low"

    def _ensure_directory(
        self,
        path: str,
        description: str,
        module_numbers: List[int],
    ) -> None:
        """
        确保目录存在（幂等）

        Args:
            path: 目录路径
            description: 目录描述
            module_numbers: 关联的模块编号
        """
        if path in self._created_paths:
            # 如果目录已存在，更新模块编号
            for d in self._directories:
                if d.path == path:
                    existing_modules = set(d.module_numbers)
                    existing_modules.update(module_numbers)
                    d.module_numbers = sorted(existing_modules)
                    return
            return

        # 确保父目录存在
        if "/" in path:
            parent_path = "/".join(path.split("/")[:-1])
            if parent_path and parent_path not in self._created_paths:
                self._ensure_directory(parent_path, "自动创建的父目录", [])

        # 创建目录
        dir_spec = DirectorySpec(
            path=path,
            description=description,
            module_numbers=module_numbers,
        )
        self._directories.append(dir_spec)
        self._created_paths.add(path)

    def _create_shared_modules(self) -> None:
        """创建共享模块目录和文件"""
        shared_path = self.decision.shared_strategy.shared_path

        # 创建共享目录
        self._ensure_directory(
            path=shared_path,
            description="共享模块：跨模块复用的工具、常量、类型定义",
            module_numbers=[],
        )

        # 创建基础共享文件
        ext = self._get_file_extension()

        shared_files = [
            (f"{shared_path}/constants{ext}", "constants", "全局常量定义"),
            (f"{shared_path}/types{ext}", "types", "通用类型定义"),
            (f"{shared_path}/utils{ext}", "utils", "通用工具函数"),
            (f"{shared_path}/exceptions{ext}", "exceptions", "自定义异常类"),
        ]

        for file_path, base_name, desc in shared_files:
            if file_path not in self._created_paths:
                file_spec = FileSpec(
                    path=file_path,
                    filename=f"{base_name}{ext}",
                    file_type="source",
                    language=self.profile.primary_language,
                    description=desc,
                    purpose=f"提供{desc}，供各模块复用",
                    module_number=0,  # 共享模块没有特定模块编号
                    priority="high",
                    dependencies=[],
                    dependency_reasons="",
                    implementation_notes="",
                )
                self._files.append(file_spec)
                self._created_paths.add(file_path)

    def _add_init_files(self) -> None:
        """为所有目录添加__init__.py文件（Python项目）"""
        for directory in self._directories:
            init_path = f"{directory.path}/__init__.py"
            if init_path not in self._created_paths:
                file_spec = FileSpec(
                    path=init_path,
                    filename="__init__.py",
                    file_type="source",
                    language="python",
                    description=f"Python包初始化文件: {directory.path.split('/')[-1]}",
                    purpose="标记目录为Python包，可选择性导出模块接口",
                    module_number=directory.module_numbers[0] if directory.module_numbers else 0,
                    priority="low",
                    dependencies=[],
                    dependency_reasons="",
                    implementation_notes="可以在这里定义__all__来控制导出",
                )
                self._files.append(file_spec)
                self._created_paths.add(init_path)

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
        }
        return extensions.get(lang, ".py")

    def _generate_architecture_notes(self) -> str:
        """生成架构说明"""
        pattern = self.decision.pattern
        template = get_pattern_template(pattern)

        notes = [
            f"架构模式: {pattern.value}",
            f"描述: {template.description}",
            "",
            "层级结构:",
        ]

        for layer in self.decision.layers:
            notes.append(f"  - {layer.name}: {layer.path}")
            notes.append(f"    {layer.description}")

        notes.extend([
            "",
            f"共享模块: {self.decision.shared_strategy.shared_path}",
            f"命名约定: {self.decision.naming_convention}",
        ])

        if self.decision.custom_constraints:
            notes.append("")
            notes.append("自定义约束:")
            for constraint in self.decision.custom_constraints:
                notes.append(f"  - {constraint}")

        return "\n".join(notes)

    async def _enhance_file_descriptions_with_llm(
        self,
        files: List[FileSpec],
        batch_size: int = 5,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        使用LLM增强文件描述

        批量处理文件，为每个文件生成更详细的描述、存在理由和实现备注。

        Args:
            files: 待增强的文件列表
            batch_size: 每批处理的文件数量

        Yields:
            SSE事件
        """
        if not self.llm_service or not self.prompt_service:
            logger.warning("未提供LLM服务，跳过文件描述增强")
            return

        # 获取提示词模板
        prompt_template = await self.prompt_service.get_prompt(FILE_DESCRIPTION_PROMPT_KEY)
        if not prompt_template:
            logger.warning("未找到文件描述生成提示词，跳过增强")
            return

        total_files = len(files)
        enhanced_count = 0

        yield {
            "event": "progress",
            "data": {
                "stage": "enhancing_descriptions",
                "message": f"使用LLM增强{total_files}个文件的描述...",
            }
        }

        # 按批次处理
        for i in range(0, total_files, batch_size):
            batch = files[i:i + batch_size]

            for file_spec in batch:
                try:
                    # 获取模块信息
                    module = self.profile.get_module_by_number(file_spec.module_number)
                    if not module:
                        continue

                    # 获取放置信息
                    placement = self.decision.get_placement_by_module(file_spec.module_number)
                    target_layer = placement.target_layer if placement else "unknown"

                    # 构建提示词变量
                    variables = {
                        "project_name": self.profile.project_name,
                        "project_description": self.profile.project_description[:500],
                        "tech_stack": ", ".join(self.profile.tech_stack),
                        "architecture_pattern": self.decision.pattern.value,
                        "module_name": module.name,
                        "module_description": module.description[:300],
                        "module_type": module.module_type,
                        "module_interface": module.interface[:200] if module.interface else "无",
                        "module_dependencies": ", ".join(module.dependencies[:5]) if module.dependencies else "无",
                        "file_path": file_spec.path,
                        "filename": file_spec.filename,
                        "target_layer": target_layer,
                        "file_type": file_spec.file_type,
                    }

                    # 填充模板
                    user_prompt = prompt_template
                    for key, value in variables.items():
                        user_prompt = user_prompt.replace(f"{{{{{key}}}}}", str(value))

                    # 调用LLM
                    system_prompt = "你是一个专业的软件架构师，需要为项目中的源文件生成详细的描述信息。请严格按照JSON格式输出。"

                    response = await self.llm_service.get_llm_response(
                        user_id=self.user_id,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        payload={},
                    )

                    # 解析响应
                    result = parse_llm_json_safe(response)
                    if result:
                        if result.get("description"):
                            file_spec.description = result["description"]
                        if result.get("purpose"):
                            file_spec.purpose = result["purpose"]
                        if result.get("implementation_notes"):
                            file_spec.implementation_notes = result["implementation_notes"]

                        enhanced_count += 1

                except Exception as e:
                    logger.warning("增强文件描述失败: %s, 错误: %s", file_spec.path, e)
                    continue

            # 发送进度更新
            progress = min(i + batch_size, total_files) / total_files
            yield {
                "event": "progress",
                "data": {
                    "stage": "enhancing_descriptions",
                    "message": f"已增强 {min(i + batch_size, total_files)}/{total_files} 个文件描述",
                    "progress": progress,
                    "enhanced_count": enhanced_count,
                }
            }

        yield {
            "event": "progress",
            "data": {
                "stage": "enhancement_complete",
                "message": f"文件描述增强完成，共增强{enhanced_count}个文件",
                "enhanced_count": enhanced_count,
            }
        }

