"""
编程项目RAG入库服务

处理11种数据类型的向量化入库、完整性检查和增量更新。
支持可配置的分块策略。
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .data_types import CodingDataType, BLUEPRINT_INGESTION_TYPES
from .content_splitter import ContentSplitter, IngestionRecord
from .chunk_strategy import ChunkMethod, get_strategy_manager
from ..rag_common.ingestion_base import (
    BaseProjectIngestionService,
    IngestionResult,
    CompletenessReport,
)

# 导入ORM模型 - 使用编程项目的模型
from ...models.coding import (
    CodingProject,
    CodingBlueprint,
    CodingConversation,
    CodingSystem,
    CodingModule,
)
from ...models.coding_files import CodingSourceFile, CodingFileVersion

logger = logging.getLogger(__name__)


class CodingProjectIngestionService(BaseProjectIngestionService):
    """
    编程项目向量入库服务

    支持12种数据类型的入库：
    - inspiration: 灵感对话
    - architecture: 架构设计
    - tech_stack: 技术栈
    - requirement: 核心需求
    - challenge: 技术挑战
    - system: 系统划分
    - module: 模块定义
    - dependency: 依赖关系
    - file_prompt: 文件实现Prompt
    - review_prompt: 审查/测试Prompt
    """

    def __init__(
        self,
        session: AsyncSession,
        vector_store: Any,  # VectorStoreService
        llm_service: Any,   # LLMService
        user_id: str
    ):
        super().__init__(
            session=session,
            vector_store=vector_store,
            llm_service=llm_service,
            user_id=user_id,
            data_type_enum=CodingDataType,
            splitter=ContentSplitter(),
            log_title="开始入库",
            logger_obj=logger,
        )

    def _get_ingest_method_map(self) -> Dict[CodingDataType, Any]:
        """获取数据类型到入库方法的映射"""
        return {
            CodingDataType.INSPIRATION: self._ingest_inspiration,
            CodingDataType.ARCHITECTURE: self._ingest_architecture,
            CodingDataType.TECH_STACK: self._ingest_tech_stack,
            CodingDataType.REQUIREMENT: self._ingest_requirements,
            CodingDataType.CHALLENGE: self._ingest_challenges,
            CodingDataType.SYSTEM: self._ingest_systems,
            CodingDataType.MODULE: self._ingest_modules,
            CodingDataType.DEPENDENCY: self._ingest_dependencies,
            CodingDataType.REVIEW_PROMPT: self._ingest_review_prompts,
            CodingDataType.FILE_PROMPT: self._ingest_file_prompts,
        }

    async def _generate_records_for_type(
        self,
        project_id: str,
        data_type: CodingDataType
    ) -> List[IngestionRecord]:
        """
        为指定数据类型生成入库记录（不实际入库，只用于哈希计算）

        复用各类型的入库逻辑，但不执行embedding和写入操作。

        Args:
            project_id: 项目ID
            data_type: 数据类型

        Returns:
            入库记录列表
        """
        # 根据类型调用对应的记录生成方法
        if data_type == CodingDataType.INSPIRATION:
            return await self._generate_inspiration_records(project_id)
        elif data_type == CodingDataType.ARCHITECTURE:
            return await self._generate_architecture_records(project_id)
        elif data_type == CodingDataType.TECH_STACK:
            return await self._generate_tech_stack_records(project_id)
        elif data_type == CodingDataType.REQUIREMENT:
            return await self._generate_requirement_records(project_id)
        elif data_type == CodingDataType.CHALLENGE:
            return await self._generate_challenge_records(project_id)
        elif data_type == CodingDataType.SYSTEM:
            return await self._generate_system_records(project_id)
        elif data_type == CodingDataType.MODULE:
            return await self._generate_module_records(project_id)
        elif data_type == CodingDataType.DEPENDENCY:
            return await self._generate_dependency_records(project_id)
        elif data_type == CodingDataType.REVIEW_PROMPT:
            return await self._generate_review_prompt_records(project_id)
        elif data_type == CodingDataType.FILE_PROMPT:
            return await self._generate_file_prompt_records(project_id)
        return []

    async def _generate_inspiration_records(self, project_id: str) -> List[IngestionRecord]:
        """生成灵感对话记录"""
        stmt = select(CodingConversation).where(
            CodingConversation.project_id == project_id
        ).order_by(CodingConversation.seq)
        conversations = (await self.session.execute(stmt)).scalars().all()

        if not conversations:
            return []

        conv_dicts = [
            {"role": conv.role, "content": conv.content, "seq": conv.seq}
            for conv in conversations
        ]
        return self.splitter.merge_qa_rounds(conv_dicts, project_id)

    async def _generate_architecture_records(self, project_id: str) -> List[IngestionRecord]:
        """生成架构设计记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.architecture_synopsis:
            return []

        return self.splitter.split_architecture(
            content=blueprint.architecture_synopsis,
            source_id=project_id,
            data_type=CodingDataType.ARCHITECTURE,
            project_id=project_id
        )

    async def _generate_tech_stack_records(self, project_id: str) -> List[IngestionRecord]:
        """生成技术栈记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.tech_stack:
            return []

        tech_stack = blueprint.tech_stack
        if isinstance(tech_stack, str):
            try:
                tech_stack = json.loads(tech_stack)
            except json.JSONDecodeError:
                return []

        records: List[IngestionRecord] = []

        for idx, comp in enumerate(tech_stack.get("components", [])):
            content = self._format_tech_component(comp)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    project_id=project_id,
                    component_index=idx,
                    component_name=comp.get("name", "")
                )
                if record:
                    records.append(record)

        for idx, domain in enumerate(tech_stack.get("domains", [])):
            content = self._format_tech_domain(domain)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    project_id=project_id,
                    domain_index=idx,
                    domain_name=domain.get("name", "")
                )
                if record:
                    records.append(record)

        return records

    async def _generate_requirement_records(self, project_id: str) -> List[IngestionRecord]:
        """生成核心需求记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.core_requirements:
            return []

        requirements = blueprint.core_requirements
        if isinstance(requirements, str):
            try:
                requirements = json.loads(requirements)
            except json.JSONDecodeError:
                return []

        records: List[IngestionRecord] = []
        for idx, req in enumerate(requirements):
            content = self._format_requirement(req)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.REQUIREMENT,
                    source_id=project_id,
                    project_id=project_id,
                    requirement_index=idx
                )
                if record:
                    records.append(record)
        return records

    async def _generate_challenge_records(self, project_id: str) -> List[IngestionRecord]:
        """生成技术挑战记录"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.technical_challenges:
            return []

        challenges = blueprint.technical_challenges
        if isinstance(challenges, str):
            try:
                challenges = json.loads(challenges)
            except json.JSONDecodeError:
                return []

        records: List[IngestionRecord] = []
        for idx, challenge in enumerate(challenges):
            content = self._format_challenge(challenge)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.CHALLENGE,
                    source_id=project_id,
                    project_id=project_id,
                    challenge_index=idx
                )
                if record:
                    records.append(record)
        return records

    async def _generate_system_records(self, project_id: str) -> List[IngestionRecord]:
        """生成系统划分记录"""
        stmt = select(CodingSystem).where(
            CodingSystem.project_id == project_id
        ).order_by(CodingSystem.system_number)
        systems = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for system in systems:
            content = self._format_system(system)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.SYSTEM,
                    source_id=str(system.id),
                    project_id=project_id,
                    system_number=system.system_number
                )
                if record:
                    records.append(record)
        return records

    async def _generate_module_records(self, project_id: str) -> List[IngestionRecord]:
        """生成模块定义记录"""
        stmt = select(CodingModule).where(
            CodingModule.project_id == project_id
        ).order_by(CodingModule.module_number)
        modules = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for module in modules:
            content = self._format_module(module)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.MODULE,
                    source_id=str(module.id),
                    project_id=project_id,
                    module_number=module.module_number,
                    system_number=module.system_number
                )
                if record:
                    records.append(record)
        return records

    async def _generate_dependency_records(self, project_id: str) -> List[IngestionRecord]:
        """生成依赖关系记录 - 支持简单模式和模块聚合模式"""
        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.dependencies:
            return []

        dependencies = blueprint.dependencies
        if isinstance(dependencies, str):
            try:
                dependencies = json.loads(dependencies)
            except json.JSONDecodeError:
                return []

        # 检查策略配置
        config = get_strategy_manager().get_config(CodingDataType.DEPENDENCY)

        if config.method == ChunkMethod.MODULE_AGGREGATE:
            # 按模块聚合依赖
            return self._generate_aggregated_dependency_records(dependencies, project_id)
        else:
            # 简单模式：每条依赖一个chunk
            return self._generate_simple_dependency_records(dependencies, project_id)

    def _generate_simple_dependency_records(
        self,
        dependencies: List[Dict],
        project_id: str
    ) -> List[IngestionRecord]:
        """生成简单依赖记录（每条依赖一个chunk）"""
        records: List[IngestionRecord] = []
        for idx, dep in enumerate(dependencies):
            content = self._format_dependency(dep)
            if content:
                from_mod = dep.get("from", dep.get("from_module", ""))
                to_mod = dep.get("to", dep.get("to_module", ""))
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.DEPENDENCY,
                    source_id=f"{project_id}_dep_{idx}",
                    project_id=project_id,
                    from_module=from_mod,
                    to_module=to_mod
                )
                if record:
                    records.append(record)
        return records

    def _generate_aggregated_dependency_records(
        self,
        dependencies: List[Dict],
        project_id: str
    ) -> List[IngestionRecord]:
        """生成聚合依赖记录（按模块聚合）"""
        # 按模块聚合依赖关系
        module_deps: Dict[str, Dict[str, List]] = {}  # {module_name: {outgoing: [], incoming: []}}

        for dep in dependencies:
            from_mod = dep.get("from", dep.get("from_module", ""))
            to_mod = dep.get("to", dep.get("to_module", ""))
            desc = dep.get("description", "")

            # 记录出向依赖
            if from_mod:
                if from_mod not in module_deps:
                    module_deps[from_mod] = {"outgoing": [], "incoming": []}
                module_deps[from_mod]["outgoing"].append({"to": to_mod, "desc": desc})

            # 记录入向依赖
            if to_mod:
                if to_mod not in module_deps:
                    module_deps[to_mod] = {"outgoing": [], "incoming": []}
                module_deps[to_mod]["incoming"].append({"from": from_mod, "desc": desc})

        # 生成每个模块的依赖chunk
        records: List[IngestionRecord] = []
        for idx, (module_name, deps) in enumerate(module_deps.items()):
            content = self._format_module_dependencies(module_name, deps)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.DEPENDENCY,
                    source_id=f"{project_id}_moddep_{idx}",
                    project_id=project_id,
                    module_name=module_name,
                    aggregated=True
                )
                if record:
                    records.append(record)

        return records

    def _format_module_dependencies(self, module_name: str, deps: Dict[str, List]) -> str:
        """格式化模块依赖（聚合模式）"""
        parts = [f"模块: {module_name}"]

        if deps.get("outgoing"):
            parts.append("依赖:")
            for d in deps["outgoing"]:
                desc_part = f": {d['desc']}" if d.get('desc') else ""
                parts.append(f"  -> {d['to']}{desc_part}")

        if deps.get("incoming"):
            parts.append("被依赖:")
            for d in deps["incoming"]:
                desc_part = f": {d['desc']}" if d.get('desc') else ""
                parts.append(f"  <- {d['from']}{desc_part}")

        return "\n".join(parts) if len(parts) > 1 else ""

    async def _generate_review_prompt_records(self, project_id: str) -> List[IngestionRecord]:
        """生成审查/测试Prompt记录

        从CodingSourceFile表读取review_prompt字段，生成入库记录。
        """
        # 检查策略配置
        config = get_strategy_manager().get_config(CodingDataType.REVIEW_PROMPT)
        use_semantic = config.method == ChunkMethod.SEMANTIC_DP

        stmt = select(CodingSourceFile).where(
            CodingSourceFile.project_id == project_id,
            CodingSourceFile.review_prompt.isnot(None),
            CodingSourceFile.review_prompt != ""
        ).order_by(CodingSourceFile.sort_order)
        files = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for file in files:
            content = file.review_prompt
            if not content or not content.strip():
                continue

            file_title = file.filename or f"文件 {file.id}"

            if use_semantic:
                # 使用语义分块
                try:
                    review_records = await self.splitter.split_content_semantic_async(
                        content=content,
                        data_type=CodingDataType.REVIEW_PROMPT,
                        source_id=str(file.id),
                        project_id=project_id,
                        embedding_func=self._get_sentence_embeddings,
                        config=config,
                        module_number=file.module_number,
                        parent_title=file_title
                    )
                    records.extend(review_records)
                except Exception as e:
                    logger.warning(
                        "审查Prompt语义分块失败，降级为传统分块: file=%s error=%s",
                        file.filename, str(e)
                    )
                    # 降级为传统分块
                    review_records = self.splitter.split_review_prompt(
                        content=content,
                        module_number=file.module_number or 0,
                        file_title=file_title,
                        source_id=str(file.id),
                        project_id=project_id
                    )
                    records.extend(review_records)
            else:
                # 使用传统分块
                review_records = self.splitter.split_review_prompt(
                    content=content,
                    module_number=file.module_number or 0,
                    file_title=file_title,
                    source_id=str(file.id),
                    project_id=project_id
                )
                records.extend(review_records)

        return records

    async def _generate_file_prompt_records(self, project_id: str) -> List[IngestionRecord]:
        """生成文件实现Prompt记录（新系统）

        遍历所有有选中版本的源文件，为每个文件的Prompt内容生成入库记录。
        """
        from sqlalchemy.orm import selectinload

        stmt = select(CodingSourceFile).where(
            CodingSourceFile.project_id == project_id,
            CodingSourceFile.selected_version_id.isnot(None)
        ).options(
            selectinload(CodingSourceFile.selected_version)
        ).order_by(CodingSourceFile.sort_order)
        files = (await self.session.execute(stmt)).scalars().all()

        records: List[IngestionRecord] = []
        for file in files:
            if not file.selected_version or not file.selected_version.content:
                continue

            content = file.selected_version.content
            if not content.strip():
                continue

            # 使用分割器分块
            file_records = self.splitter.split_file_prompt(
                content=content,
                file_id=str(file.id),
                filename=file.filename,
                file_path=file.file_path,
                project_id=project_id,
                module_number=file.module_number,
                system_number=file.system_number,
                file_type=file.file_type,
                language=file.language,
            )
            records.extend(file_records)

        return records

    async def _get_sentence_embeddings(self, sentences: List[str]) -> List[List[float]]:
        """获取句子列表的嵌入向量

        为语义分块器提供的嵌入函数，批量获取句子的嵌入向量。

        Args:
            sentences: 句子列表

        Returns:
            嵌入向量列表（numpy数组形式）
        """
        import numpy as np

        embeddings = []
        for sentence in sentences:
            try:
                embedding = await self.llm_service.get_embedding(
                    sentence,
                    user_id=self.user_id
                )
                if embedding:
                    embeddings.append(embedding)
                else:
                    # 返回零向量作为占位
                    embeddings.append([0.0] * 1536)  # 默认维度
            except Exception as e:
                logger.warning("获取句子嵌入失败: %s", str(e))
                embeddings.append([0.0] * 1536)

        return np.array(embeddings)

    # ==================== 私有方法：各类型入库 ====================

    async def _ingest_inspiration(self, project_id: str) -> IngestionResult:
        """入库灵感对话"""
        result = IngestionResult(success=True, data_type=CodingDataType.INSPIRATION)

        # 获取对话记录
        stmt = select(CodingConversation).where(
            CodingConversation.project_id == project_id
        ).order_by(CodingConversation.seq)
        conversations = (await self.session.execute(stmt)).scalars().all()

        if not conversations:
            return result

        # 转换为字典列表
        conv_dicts = [
            {
                "role": conv.role,
                "content": conv.content,
                "seq": conv.seq
            }
            for conv in conversations
        ]

        # 合并Q&A轮次
        records = self.splitter.merge_qa_rounds(conv_dicts, project_id)
        result.total_records = len(records)

        # 入库
        return await self._ingest_records(records, result, project_id)

    async def _ingest_architecture(self, project_id: str) -> IngestionResult:
        """入库架构设计"""
        result = IngestionResult(success=True, data_type=CodingDataType.ARCHITECTURE)

        blueprint = await self._get_blueprint(project_id)
        # 编程项目架构描述存储在 architecture_synopsis 字段
        if not blueprint or not blueprint.architecture_synopsis:
            return result

        records = self.splitter.split_architecture(
            content=blueprint.architecture_synopsis,
            source_id=project_id,
            data_type=CodingDataType.ARCHITECTURE,
            project_id=project_id
        )
        result.total_records = len(records)

        return await self._ingest_records(records, result, project_id)

    async def _ingest_tech_stack(self, project_id: str) -> IngestionResult:
        """入库技术栈"""
        result = IngestionResult(success=True, data_type=CodingDataType.TECH_STACK)

        blueprint = await self._get_blueprint(project_id)
        # 编程项目技术栈直接存储在 tech_stack 字段
        if not blueprint or not blueprint.tech_stack:
            return result

        tech_stack = blueprint.tech_stack
        if isinstance(tech_stack, str):
            try:
                tech_stack = json.loads(tech_stack)
            except json.JSONDecodeError:
                return result

        records: List[IngestionRecord] = []

        # 处理components
        components = tech_stack.get("components", [])
        for idx, comp in enumerate(components):
            content = self._format_tech_component(comp)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    project_id=project_id,
                    component_index=idx,
                    component_name=comp.get("name", "")
                )
                if record:
                    records.append(record)

        # 处理domains
        domains = tech_stack.get("domains", [])
        for idx, domain in enumerate(domains):
            content = self._format_tech_domain(domain)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.TECH_STACK,
                    source_id=project_id,
                    project_id=project_id,
                    domain_index=idx,
                    domain_name=domain.get("name", "")
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_requirements(self, project_id: str) -> IngestionResult:
        """入库核心需求"""
        result = IngestionResult(success=True, data_type=CodingDataType.REQUIREMENT)

        blueprint = await self._get_blueprint(project_id)
        # 编程项目核心需求直接存储在 core_requirements 字段
        if not blueprint or not blueprint.core_requirements:
            logger.info("入库核心需求: 无蓝图或core_requirements为空")
            return result

        requirements = blueprint.core_requirements
        if isinstance(requirements, str):
            try:
                requirements = json.loads(requirements)
            except json.JSONDecodeError:
                logger.warning("入库核心需求: core_requirements JSON解析失败")
                return result

        logger.info("入库核心需求: 找到 %d 条需求", len(requirements))

        records: List[IngestionRecord] = []
        for idx, req in enumerate(requirements):
            content = self._format_requirement(req)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.REQUIREMENT,
                    source_id=project_id,
                    project_id=project_id,
                    requirement_index=idx
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_challenges(self, project_id: str) -> IngestionResult:
        """入库技术挑战"""
        result = IngestionResult(success=True, data_type=CodingDataType.CHALLENGE)

        blueprint = await self._get_blueprint(project_id)
        # 编程项目技术挑战直接存储在 technical_challenges 字段
        if not blueprint or not blueprint.technical_challenges:
            logger.info("入库技术挑战: 无蓝图或technical_challenges为空")
            return result

        challenges = blueprint.technical_challenges
        if isinstance(challenges, str):
            try:
                challenges = json.loads(challenges)
            except json.JSONDecodeError:
                logger.warning("入库技术挑战: technical_challenges JSON解析失败")
                return result

        logger.info("入库技术挑战: 找到 %d 条挑战", len(challenges))

        records: List[IngestionRecord] = []
        for idx, challenge in enumerate(challenges):
            content = self._format_challenge(challenge)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.CHALLENGE,
                    source_id=project_id,
                    project_id=project_id,
                    challenge_index=idx
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_systems(self, project_id: str) -> IngestionResult:
        """入库系统划分"""
        result = IngestionResult(success=True, data_type=CodingDataType.SYSTEM)

        # 系统存储在 coding_systems 表
        stmt = select(CodingSystem).where(
            CodingSystem.project_id == project_id
        ).order_by(CodingSystem.system_number)
        systems = (await self.session.execute(stmt)).scalars().all()

        if not systems:
            return result

        records: List[IngestionRecord] = []
        for system in systems:
            content = self._format_system(system)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.SYSTEM,
                    source_id=str(system.id),
                    project_id=project_id,
                    system_number=system.system_number
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_modules(self, project_id: str) -> IngestionResult:
        """入库模块定义"""
        result = IngestionResult(success=True, data_type=CodingDataType.MODULE)

        # 模块存储在 coding_modules 表
        stmt = select(CodingModule).where(
            CodingModule.project_id == project_id
        ).order_by(CodingModule.module_number)
        modules = (await self.session.execute(stmt)).scalars().all()

        if not modules:
            return result

        records: List[IngestionRecord] = []
        for module in modules:
            content = self._format_module(module)
            if content:
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.MODULE,
                    source_id=str(module.id),
                    project_id=project_id,
                    module_number=module.module_number,
                    system_number=module.system_number
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_dependencies(self, project_id: str) -> IngestionResult:
        """入库依赖关系 - 从蓝图的dependencies字段获取"""
        result = IngestionResult(success=True, data_type=CodingDataType.DEPENDENCY)

        blueprint = await self._get_blueprint(project_id)
        if not blueprint or not blueprint.dependencies:
            return result

        dependencies = blueprint.dependencies
        if isinstance(dependencies, str):
            try:
                dependencies = json.loads(dependencies)
            except json.JSONDecodeError:
                return result

        records: List[IngestionRecord] = []
        for idx, dep in enumerate(dependencies):
            content = self._format_dependency(dep)
            if content:
                # dep 是字典格式: {"from": "模块名", "to": "模块名", "description": "..."}
                from_mod = dep.get("from", dep.get("from_module", ""))
                to_mod = dep.get("to", dep.get("to_module", ""))
                record = self.splitter.create_simple_record(
                    content=content,
                    data_type=CodingDataType.DEPENDENCY,
                    source_id=f"{project_id}_dep_{idx}",
                    project_id=project_id,
                    from_module=from_mod,
                    to_module=to_mod
                )
                if record:
                    records.append(record)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_review_prompts(self, project_id: str) -> IngestionResult:
        """入库审查/测试Prompt"""
        result = IngestionResult(success=True, data_type=CodingDataType.REVIEW_PROMPT)

        # 审查Prompt存储在 coding_source_files.review_prompt 字段
        stmt = select(CodingSourceFile).where(
            CodingSourceFile.project_id == project_id,
            CodingSourceFile.review_prompt.isnot(None),
            CodingSourceFile.review_prompt != ""
        ).order_by(CodingSourceFile.sort_order)
        files = (await self.session.execute(stmt)).scalars().all()

        if not files:
            return result

        records: List[IngestionRecord] = []
        for file in files:
            content = file.review_prompt
            if not content or not content.strip():
                continue

            # 审查Prompt分割
            review_records = self.splitter.split_review_prompt(
                content=content,
                module_number=file.module_number or 0,
                file_title=file.filename or f"文件 {file.id}",
                source_id=str(file.id),
                project_id=project_id
            )
            records.extend(review_records)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    async def _ingest_file_prompts(self, project_id: str) -> IngestionResult:
        """入库文件实现Prompt（新系统）

        遍历所有有选中版本的源文件，将Prompt内容入库到向量库。
        """
        result = IngestionResult(success=True, data_type=CodingDataType.FILE_PROMPT)

        # 获取有选中版本的源文件
        from sqlalchemy.orm import selectinload
        stmt = select(CodingSourceFile).where(
            CodingSourceFile.project_id == project_id,
            CodingSourceFile.selected_version_id.isnot(None)
        ).options(
            selectinload(CodingSourceFile.selected_version)
        ).order_by(CodingSourceFile.sort_order)
        files = (await self.session.execute(stmt)).scalars().all()

        if not files:
            return result

        records: List[IngestionRecord] = []
        for file in files:
            if not file.selected_version or not file.selected_version.content:
                continue

            content = file.selected_version.content
            if not content.strip():
                continue

            # 使用分割器分块
            file_records = self.splitter.split_file_prompt(
                content=content,
                file_id=str(file.id),
                filename=file.filename,
                file_path=file.file_path,
                project_id=project_id,
                module_number=file.module_number,
                system_number=file.system_number,
                file_type=file.file_type,
                language=file.language,
            )
            records.extend(file_records)

        result.total_records = len(records)
        return await self._ingest_records(records, result, project_id)

    # ==================== 私有方法：辅助函数 ====================

    async def _get_blueprint(self, project_id: str) -> Optional[CodingBlueprint]:
        """获取项目蓝图"""
        stmt = select(CodingBlueprint).where(CodingBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_db_count(self, project_id: str, data_type: CodingDataType) -> int:
        """获取数据库中某类型的记录数"""
        # 根据数据类型查询对应的编程项目表
        if data_type == CodingDataType.INSPIRATION:
            stmt = select(func.count()).select_from(CodingConversation).where(
                CodingConversation.project_id == project_id
            )
            # 对话按轮次计算，大约是记录数/2
            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            return (count + 1) // 2  # 估算轮次数

        elif data_type == CodingDataType.ARCHITECTURE:
            blueprint = await self._get_blueprint(project_id)
            return 1 if blueprint and blueprint.architecture_synopsis else 0

        elif data_type == CodingDataType.TECH_STACK:
            blueprint = await self._get_blueprint(project_id)
            if not blueprint or not blueprint.tech_stack:
                return 0
            tech_stack = blueprint.tech_stack
            if isinstance(tech_stack, str):
                try:
                    tech_stack = json.loads(tech_stack)
                except json.JSONDecodeError:
                    return 0
            return len(tech_stack.get("components", [])) + len(tech_stack.get("domains", []))

        elif data_type == CodingDataType.REQUIREMENT:
            blueprint = await self._get_blueprint(project_id)
            if not blueprint or not blueprint.core_requirements:
                return 0
            reqs = blueprint.core_requirements
            if isinstance(reqs, str):
                try:
                    reqs = json.loads(reqs)
                except json.JSONDecodeError:
                    return 0
            return len(reqs) if isinstance(reqs, list) else 0

        elif data_type == CodingDataType.CHALLENGE:
            blueprint = await self._get_blueprint(project_id)
            if not blueprint or not blueprint.technical_challenges:
                return 0
            challenges = blueprint.technical_challenges
            if isinstance(challenges, str):
                try:
                    challenges = json.loads(challenges)
                except json.JSONDecodeError:
                    return 0
            return len(challenges) if isinstance(challenges, list) else 0

        elif data_type == CodingDataType.SYSTEM:
            stmt = select(func.count()).select_from(CodingSystem).where(
                CodingSystem.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif data_type == CodingDataType.MODULE:
            stmt = select(func.count()).select_from(CodingModule).where(
                CodingModule.project_id == project_id
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif data_type == CodingDataType.DEPENDENCY:
            blueprint = await self._get_blueprint(project_id)
            if not blueprint or not blueprint.dependencies:
                return 0
            deps = blueprint.dependencies
            if isinstance(deps, str):
                try:
                    deps = json.loads(deps)
                except json.JSONDecodeError:
                    return 0
            return len(deps) if isinstance(deps, list) else 0

        elif data_type == CodingDataType.REVIEW_PROMPT:
            # 审查Prompt检查有review_prompt内容的源文件数
            stmt = select(func.count()).select_from(CodingSourceFile).where(
                CodingSourceFile.project_id == project_id,
                CodingSourceFile.review_prompt.isnot(None),
                CodingSourceFile.review_prompt != ""
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        elif data_type == CodingDataType.FILE_PROMPT:
            # 文件Prompt检查有选中版本的源文件数
            stmt = select(func.count()).select_from(CodingSourceFile).where(
                CodingSourceFile.project_id == project_id,
                CodingSourceFile.selected_version_id.isnot(None)
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0

        return 0

    async def _get_vector_count(self, project_id: str, data_type: CodingDataType) -> int:
        """获取向量库中某类型的记录数"""
        if not self.vector_store or not self.vector_store._client:
            return 0

        try:
            await self.vector_store.ensure_schema()
            sql = """
            SELECT COUNT(*) as cnt FROM rag_chunks
            WHERE project_id = :project_id
            AND json_extract(metadata, '$.data_type') = :data_type
            """
            result = await self.vector_store._client.execute(
                sql,
                {"project_id": project_id, "data_type": data_type.value}
            )
            rows = list(self.vector_store._iter_rows(result))
            if rows:
                return rows[0].get("cnt", 0)
        except Exception as e:
            logger.warning(
                "获取向量库记录数失败: project=%s type=%s error=%s",
                project_id, data_type.value, str(e)
            )
        return 0

    async def _ingest_records(
        self,
        records: List[IngestionRecord],
        result: IngestionResult,
        project_id: str
    ) -> IngestionResult:
        """
        将记录入库到向量库

        Args:
            records: 入库记录列表
            result: 结果对象（会被修改）
            project_id: 项目ID（用于向量库的project_id字段）

        Returns:
            更新后的结果对象
        """
        if not records:
            return result

        if not self.vector_store:
            result.success = False
            result.error_message = "向量库未启用"
            return result

        # 批量生成embedding
        embeddings = await self._batch_get_embeddings([r.content for r in records])

        if len(embeddings) != len(records):
            result.success = False
            result.error_message = "生成embedding数量不匹配"
            return result

        # 构建入库数据
        chunk_records = []
        for idx, (record, embedding) in enumerate(zip(records, embeddings)):
            if not embedding:
                result.failed_count += 1
                continue

            chunk_id = record.get_chunk_id()
            metadata = {
                **record.metadata,
                "data_type": record.data_type.value,
                "paragraph_hash": record.get_content_hash(),
                "length": len(record.content),
                "source_id": record.source_id,  # 保存原始source_id到metadata
            }

            # 根据数据类型生成有意义的来源信息
            chapter_number, chapter_title = self._get_source_info(record)

            chunk_records.append({
                "id": chunk_id,
                "project_id": project_id,  # 始终使用传入的project_id
                "chapter_number": chapter_number,
                "chunk_index": record.metadata.get("section_index", idx),
                "chapter_title": chapter_title,
                "content": record.content,
                "embedding": embedding,
                "metadata": metadata,
            })

        # 写入向量库
        try:
            # 记录入库数据的详细信息
            if chunk_records:
                sample = chunk_records[0]
                logger.info(
                    "入库数据样本: type=%s id=%s chapter_title=%s metadata_keys=%s data_type_in_meta=%s",
                    result.data_type.value,
                    sample.get("id", "")[:30],
                    sample.get("chapter_title", ""),
                    list(sample.get("metadata", {}).keys()),
                    sample.get("metadata", {}).get("data_type", "MISSING!")
                )

            await self.vector_store.upsert_chunks(records=chunk_records)
            result.added_count = len(chunk_records)
            logger.info(
                "入库完成: type=%s count=%d",
                result.data_type.value, result.added_count
            )
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(
                "入库失败: type=%s error=%s",
                result.data_type.value, str(e)
            )

        return result

    def _get_source_info(self, record: IngestionRecord) -> tuple:
        """
        根据数据类型获取来源信息

        返回 (chapter_number, chapter_title) 元组，用于在前端显示来源。

        Args:
            record: 入库记录

        Returns:
            (chapter_number, chapter_title) 元组
        """
        data_type = record.data_type
        metadata = record.metadata

        # 调试日志：记录每条记录的数据类型
        logger.debug(
            "获取来源信息: data_type=%s metadata_keys=%s",
            data_type, list(metadata.keys()) if metadata else []
        )

        # 数据类型到来源信息的映射
        if data_type == CodingDataType.SYSTEM:
            # 系统: S{system_number}
            num = metadata.get("system_number", 0)
            return (num, f"系统{num}")

        elif data_type == CodingDataType.MODULE:
            # 模块: M{module_number}
            num = metadata.get("module_number", 0)
            sys_num = metadata.get("system_number", 0)
            return (num, f"系统{sys_num}-模块{num}")

        elif data_type == CodingDataType.INSPIRATION:
            # 灵感对话: 轮次{round_number}
            round_num = metadata.get("round_number", 0) + 1  # 从1开始显示
            return (round_num, f"对话轮次{round_num}")

        elif data_type == CodingDataType.ARCHITECTURE:
            # 架构设计: 按section显示
            section = metadata.get("section_title", "")
            section_idx = metadata.get("section_index", 0) + 1
            return (section_idx, section or f"架构设计{section_idx}")

        elif data_type == CodingDataType.TECH_STACK:
            # 技术栈: 组件/领域名称
            comp_name = metadata.get("component_name", "")
            domain_name = metadata.get("domain_name", "")
            name = comp_name or domain_name
            idx = metadata.get("component_index", metadata.get("domain_index", 0)) + 1
            return (idx, name or f"技术栈{idx}")

        elif data_type == CodingDataType.REQUIREMENT:
            # 核心需求
            idx = metadata.get("requirement_index", 0) + 1
            return (idx, f"核心需求{idx}")

        elif data_type == CodingDataType.CHALLENGE:
            # 技术挑战
            idx = metadata.get("challenge_index", 0) + 1
            return (idx, f"技术挑战{idx}")

        elif data_type == CodingDataType.DEPENDENCY:
            # 依赖关系
            from_mod = metadata.get("from_module", "")
            to_mod = metadata.get("to_module", "")
            return (0, f"{from_mod} -> {to_mod}" if from_mod and to_mod else "模块依赖")

        elif data_type == CodingDataType.REVIEW_PROMPT:
            # 测试Prompt: M{module_number} - {parent_title}
            num = metadata.get("module_number", 0)
            title = metadata.get("parent_title", "")
            section = metadata.get("section_title", "")
            if section:
                title = f"{title} > {section}" if title else section
            return (num, title or f"测试{num}")

        elif data_type == CodingDataType.FILE_PROMPT:
            # 文件Prompt: 文件路径
            filename = metadata.get("filename", "")
            file_path = metadata.get("file_path", "")
            module_num = metadata.get("module_number")
            section = metadata.get("section_title", "")
            # 优先显示文件路径，其次文件名
            title = file_path or filename
            if section:
                title = f"{title} > {section}" if title else section
            return (module_num or 0, title or "文件Prompt")

        # 默认
        return (0, CodingDataType.get_display_name(data_type.value))

    async def _batch_get_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[Optional[List[float]]]:
        """
        批量获取embedding

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            embedding列表（与texts顺序对应）
        """
        embeddings: List[Optional[List[float]]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                try:
                    embedding = await self.llm_service.get_embedding(
                        text,
                        user_id=self.user_id
                    )
                    embeddings.append(embedding)
                except Exception as e:
                    logger.warning("生成embedding失败: %s", str(e))
                    embeddings.append(None)

        return embeddings

    # ==================== 私有方法：格式化函数 ====================

    def _format_tech_component(self, comp: Dict[str, Any]) -> str:
        """格式化技术组件"""
        parts = []
        name = comp.get("name", "")
        if name:
            parts.append(f"技术组件: {name}")
        category = comp.get("category", "")
        if category:
            parts.append(f"分类: {category}")
        version = comp.get("version", "")
        if version:
            parts.append(f"版本: {version}")
        purpose = comp.get("purpose", "")
        if purpose:
            parts.append(f"用途: {purpose}")
        return "\n".join(parts)

    def _format_tech_domain(self, domain: Dict[str, Any]) -> str:
        """格式化技术领域"""
        parts = []
        name = domain.get("name", "")
        if name:
            parts.append(f"技术领域: {name}")
        description = domain.get("description", "")
        if description:
            parts.append(f"描述: {description}")
        techs = domain.get("technologies", [])
        if techs:
            parts.append(f"技术栈: {', '.join(techs)}")
        return "\n".join(parts)

    def _format_requirement(self, req: Any) -> str:
        """格式化核心需求"""
        if isinstance(req, str):
            return f"核心需求: {req}"
        if isinstance(req, dict):
            parts = []
            # 支持两种格式：
            # 新格式: category, requirement, priority
            # 旧格式: title/name, description, priority
            category = req.get("category", "")
            requirement = req.get("requirement", "")
            title = req.get("title", req.get("name", ""))
            desc = req.get("description", "")
            priority = req.get("priority", "")

            if category:
                parts.append(f"分类: {category}")
            if requirement:
                parts.append(f"需求: {requirement}")
            elif title:
                parts.append(f"需求: {title}")
            if desc:
                parts.append(f"描述: {desc}")
            if priority:
                parts.append(f"优先级: {priority}")

            return "\n".join(parts) if parts else ""
        return str(req) if req else ""

    def _format_challenge(self, challenge: Any) -> str:
        """格式化技术挑战"""
        if isinstance(challenge, str):
            return f"技术挑战: {challenge}"
        if isinstance(challenge, dict):
            parts = []
            # 支持两种格式：
            # 新格式: challenge, impact, solution_direction
            # 旧格式: title/name, description, solution
            challenge_text = challenge.get("challenge", "")
            title = challenge.get("title", challenge.get("name", ""))
            impact = challenge.get("impact", "")
            desc = challenge.get("description", "")
            solution_direction = challenge.get("solution_direction", "")
            solution = challenge.get("solution", "")

            if challenge_text:
                parts.append(f"挑战: {challenge_text}")
            elif title:
                parts.append(f"挑战: {title}")
            if impact:
                parts.append(f"影响: {impact}")
            if desc:
                parts.append(f"描述: {desc}")
            if solution_direction:
                parts.append(f"解决方向: {solution_direction}")
            elif solution:
                parts.append(f"解决方案: {solution}")

            return "\n".join(parts) if parts else ""
        return str(challenge) if challenge else ""

    def _format_system(self, system: CodingSystem) -> str:
        """
        格式化系统划分

        Args:
            system: CodingSystem模型实例

        Returns:
            格式化的系统描述文本
        """
        parts = [f"系统 {system.system_number}: {system.name or ''}"]
        if system.description:
            parts.append(f"描述: {system.description}")
        # 职责存储在 responsibilities 字段 (JSON列表)
        if system.responsibilities:
            responsibilities = system.responsibilities
            if isinstance(responsibilities, list):
                parts.append(f"职责: {', '.join(str(r) for r in responsibilities)}")
            else:
                parts.append(f"职责: {responsibilities}")
        # 技术要求存储在 tech_requirements 字段
        if system.tech_requirements:
            parts.append(f"技术要求: {system.tech_requirements}")
        return "\n".join(parts)

    def _format_module(self, module: CodingModule) -> str:
        """
        格式化模块定义

        Args:
            module: CodingModule模型实例

        Returns:
            格式化的模块描述文本
        """
        parts = [f"模块: {module.name or ''}"]
        if module.module_type:
            parts.append(f"类型: {module.module_type}")
        if module.description:
            parts.append(f"描述: {module.description}")
        if module.interface:
            parts.append(f"接口: {module.interface}")
        # 依赖存储在 dependencies 字段 (JSON列表)
        if module.dependencies:
            deps = module.dependencies
            if isinstance(deps, list):
                parts.append(f"依赖: {', '.join(str(d) for d in deps)}")
            else:
                parts.append(f"依赖: {deps}")
        return "\n".join(parts)

    def _format_dependency(self, dep: Dict[str, Any]) -> str:
        """
        格式化依赖关系

        Args:
            dep: 依赖关系字典，包含 from/from_module, to/to_module, description 等字段

        Returns:
            格式化的依赖关系文本
        """
        parts = []
        # 支持多种字段名格式
        from_mod = dep.get("from", dep.get("from_module", ""))
        to_mod = dep.get("to", dep.get("to_module", ""))
        description = dep.get("description", "")

        if from_mod and to_mod:
            parts.append(f"依赖关系: {from_mod} -> {to_mod}")
        if description:
            parts.append(f"描述: {description}")
        return "\n".join(parts) if parts else "模块依赖关系"


__all__ = [
    "CodingProjectIngestionService",
    "IngestionResult",
    "CompletenessReport",
]
