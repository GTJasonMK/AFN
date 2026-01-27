"""
内容分割器

按格式智能分割长内容，保留来源追踪信息。
支持Markdown标题分割、Q&A对话合并等功能。
支持可配置的分块策略。
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .data_types import CodingDataType
from .chunk_strategy import ChunkMethod, ChunkConfig, get_strategy_manager
from ..rag_common.markdown_split_mixin import MarkdownHeaderSplitMixin
from ..rag_common.content_splitter_utils import (
    build_qa_round_text,
    build_paragraph_chunk_records,
    build_fixed_length_chunk_records,
    build_markdown_section_records,
    build_semantic_chunk_records_async,
    build_whole_chunk_records,
    iter_qa_rounds,
)

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """分割后的内容片段"""
    title: str                    # 小标题
    content: str                  # 内容
    index: int                    # 在原文中的顺序（从0开始）
    level: int = 2                # 标题级别（## = 2, ### = 3）


@dataclass
class IngestionRecord:
    """入库记录"""
    content: str                  # 要入库的内容
    data_type: CodingDataType     # 数据类型
    source_id: str                # 来源记录ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    project_id: str = ""          # 项目ID，用于生成唯一chunk_id

    def get_content_hash(self) -> str:
        """计算内容哈希，用于增量更新"""
        return hashlib.md5(self.content.encode('utf-8')).hexdigest()[:16]

    def get_chunk_id(self) -> str:
        """
        生成唯一的chunk ID

        格式: {project_prefix}_{type}_{source_suffix}_{section}_{hash}
        包含project_id前缀以避免跨项目碰撞。
        """
        # 使用完整的数据类型名（避免inspiration和其他以insp开头的类型冲突）
        type_name = self.data_type.value
        # 项目ID前8位（如果有）
        project_prefix = self.project_id[:8] if self.project_id else "global"
        # 来源ID后8位
        source_suffix = self.source_id[-8:] if len(self.source_id) > 8 else self.source_id
        # 内容哈希
        content_hash = self.get_content_hash()
        # 分段索引
        section_idx = self.metadata.get('section_index', 0)
        return f"{project_prefix}_{type_name}_{source_suffix}_{section_idx}_{content_hash}"


class ContentSplitter(MarkdownHeaderSplitMixin):
    """内容分割器 - 按格式智能分割长内容，支持策略配置"""

    # 默认参数（可被配置覆盖）
    MIN_CHUNK_LENGTH = 100
    MAX_CHUNK_LENGTH = 2000
    SECTION_FACTORY = Section

    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        初始化分割器

        Args:
            config: 分块配置（可选，用于设置默认参数）
        """
        self._default_config = config

    # ==================== 核心分割方法（基于策略配置） ====================

    def split_content(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str = "",
        config: Optional[ChunkConfig] = None,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """
        根据策略配置分割内容

        这是主入口方法，根据配置的分块方法调用对应的分割逻辑。

        Args:
            content: 要分割的内容
            data_type: 数据类型
            source_id: 来源ID
            project_id: 项目ID
            config: 分块配置（可选，默认从全局策略管理器获取）
            **extra_metadata: 额外元数据

        Returns:
            入库记录列表
        """
        if not content or not content.strip():
            return []

        # 获取配置
        if config is None:
            config = get_strategy_manager().get_config(data_type)

        # 根据分块方法调用对应处理
        method = config.method

        if method == ChunkMethod.WHOLE:
            return self._split_whole(content, data_type, source_id, project_id, config, **extra_metadata)

        elif method == ChunkMethod.MARKDOWN_HEADER:
            return self._split_markdown(content, data_type, source_id, project_id, config, **extra_metadata)

        elif method == ChunkMethod.PARAGRAPH:
            return self._split_paragraph(content, data_type, source_id, project_id, config, **extra_metadata)

        elif method == ChunkMethod.FIXED_LENGTH:
            return self._split_fixed_length(content, data_type, source_id, project_id, config, **extra_metadata)

        elif method == ChunkMethod.SIMPLE:
            return self._split_simple(content, data_type, source_id, project_id, config, **extra_metadata)

        elif method == ChunkMethod.SEMANTIC_DP:
            # 语义分块需要异步调用，这里返回降级结果
            # 实际使用时应调用 split_content_semantic_async
            logger.warning("SEMANTIC_DP方法在同步调用中不可用，降级为段落分割")
            return self._split_paragraph(content, data_type, source_id, project_id, config, **extra_metadata)

        else:
            # 默认使用简单分割
            return self._split_simple(content, data_type, source_id, project_id, config, **extra_metadata)

    def _split_whole(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        config: ChunkConfig,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """整体入库，不分割"""
        records: List[IngestionRecord] = []
        for chunk_content, metadata in build_whole_chunk_records(
            content=content,
            add_context_prefix=config.add_context_prefix,
            parent_title=extra_metadata.get("parent_title"),
            extra_metadata=extra_metadata,
        ):
            records.append(
                IngestionRecord(
                    content=chunk_content,
                    data_type=data_type,
                    source_id=source_id,
                    metadata=metadata,
                    project_id=project_id,
                )
            )
        return records

    def _split_markdown(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        config: ChunkConfig,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """按Markdown标题分割"""
        sections = self.split_by_markdown_headers(
            content,
            min_level=config.md_min_level,
            max_level=config.md_max_level
        )

        # 如果没有标题或内容太短，整体入库
        if not sections or len(content) < config.min_chunk_length:
            return self._split_whole(content, data_type, source_id, project_id, config, **extra_metadata)

        records: List[IngestionRecord] = []
        for chunk_content, metadata in build_markdown_section_records(
            sections=sections,
            add_context_prefix=config.add_context_prefix,
            parent_title=extra_metadata.get("parent_title"),
            extra_metadata=extra_metadata,
        ):
            records.append(
                IngestionRecord(
                    content=chunk_content,
                    data_type=data_type,
                    source_id=source_id,
                    metadata=metadata,
                    project_id=project_id,
                )
            )

        return records

    def _split_paragraph(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        config: ChunkConfig,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """按段落分割"""
        chunk_records = build_paragraph_chunk_records(
            content=content,
            min_length=config.min_chunk_length,
            max_length=config.max_chunk_length,
            with_overlap=False,
            overlap_length=0,
            add_context_prefix=config.add_context_prefix,
            parent_title=extra_metadata.get("parent_title"),
            extra_metadata=extra_metadata,
        )

        return [
            IngestionRecord(
                content=chunk_content,
                data_type=data_type,
                source_id=source_id,
                metadata=metadata,
                project_id=project_id,
            )
            for chunk_content, metadata in chunk_records
        ]

    def _split_fixed_length(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        config: ChunkConfig,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """按固定长度分割（带重叠）"""
        chunk_size = config.fixed_chunk_size
        overlap = config.chunk_overlap
        normalized = content.strip()

        if len(normalized) <= chunk_size:
            return self._split_whole(normalized, data_type, source_id, project_id, config, **extra_metadata)

        chunk_records = build_fixed_length_chunk_records(
            content=normalized,
            chunk_size=chunk_size,
            overlap=overlap,
            add_context_prefix=config.add_context_prefix,
            parent_title=extra_metadata.get("parent_title"),
            extra_metadata=extra_metadata,
        )

        return [
            IngestionRecord(
                content=chunk_content,
                data_type=data_type,
                source_id=source_id,
                metadata=metadata,
                project_id=project_id,
            )
            for chunk_content, metadata in chunk_records
        ]

    def _split_simple(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        config: ChunkConfig,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """简单分割（整体作为一条记录）"""
        return self._split_whole(content, data_type, source_id, project_id, config, **extra_metadata)

    # ==================== 语义分块方法（异步） ====================

    async def split_content_semantic_async(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str,
        embedding_func: Callable[[List[str]], Any],
        config: Optional[ChunkConfig] = None,
        **extra_metadata
    ) -> List[IngestionRecord]:
        """
        使用语义动态规划进行分块（异步）

        基于句子嵌入和DP算法找到最优切分点，
        最大化块内语义相关度，最小化块间相关度。

        Args:
            content: 要分割的内容
            data_type: 数据类型
            source_id: 来源ID
            project_id: 项目ID
            embedding_func: 异步嵌入函数，接受句子列表返回嵌入矩阵
            config: 分块配置
            **extra_metadata: 额外元数据

        Returns:
            入库记录列表
        """
        if not content or not content.strip():
            return []

        # 获取配置
        if config is None:
            config = get_strategy_manager().get_config(data_type)

        try:
            chunk_records = await build_semantic_chunk_records_async(
                content=content,
                embedding_func=embedding_func,
                strategy_config=config,
                with_overlap=False,  # 编程项目一般不需要重叠
                overlap_sentences=0,
                add_context_prefix=config.add_context_prefix,
                parent_title=extra_metadata.get("parent_title"),
                extra_metadata=extra_metadata,
            )

            return [
                IngestionRecord(
                    content=chunk_content,
                    data_type=data_type,
                    source_id=source_id,
                    project_id=project_id,
                    metadata=metadata,
                )
                for chunk_content, metadata in chunk_records
            ]

        except Exception as e:
            logger.warning("语义分块失败: %s，降级为段落分割", str(e))
            return self._split_paragraph(
                content, data_type, source_id, project_id, config, **extra_metadata
            )

    # ==================== 原有方法（保持向后兼容） ====================

    def split_review_prompt(
        self,
        content: str,
        module_number: int,
        file_title: str,
        source_id: str,
        project_id: str = ""
    ) -> List[IngestionRecord]:
        """
        分割审查/测试Prompt内容（使用策略配置）

        Args:
            content: 审查Prompt内容
            module_number: 模块编号
            file_title: 文件标题
            source_id: 来源文件ID
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        return self.split_content(
            content=content,
            data_type=CodingDataType.REVIEW_PROMPT,
            source_id=source_id,
            project_id=project_id,
            module_number=module_number,
            parent_title=file_title,
        )

    def split_file_prompt(
        self,
        content: str,
        file_id: str,
        filename: str,
        file_path: str,
        project_id: str,
        module_number: Optional[int] = None,
        system_number: Optional[int] = None,
        file_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[IngestionRecord]:
        """
        分割文件实现Prompt内容（新系统）

        按Markdown标题或段落分割文件Prompt，为RAG检索做准备。
        用于文件驱动的Prompt生成系统。

        Args:
            content: 文件Prompt内容
            file_id: 源文件ID
            filename: 文件名
            file_path: 文件完整路径
            project_id: 项目ID
            module_number: 所属模块编号（可选）
            system_number: 所属系统编号（可选）
            file_type: 文件类型（可选，如 component, service 等）
            language: 编程语言（可选）

        Returns:
            入库记录列表
        """
        # 构建元数据
        extra_metadata = {
            'filename': filename,
            'file_path': file_path,
            'parent_title': f"{file_path}",  # 用于上下文前缀
        }

        if module_number is not None:
            extra_metadata['module_number'] = module_number
        if system_number is not None:
            extra_metadata['system_number'] = system_number
        if file_type:
            extra_metadata['file_type'] = file_type
        if language:
            extra_metadata['language'] = language

        return self.split_content(
            content=content,
            data_type=CodingDataType.FILE_PROMPT,
            source_id=file_id,
            project_id=project_id,
            **extra_metadata,
        )

    def split_architecture(
        self,
        content: str,
        source_id: str,
        data_type: CodingDataType = CodingDataType.ARCHITECTURE,
        project_id: str = ""
    ) -> List[IngestionRecord]:
        """
        分割架构设计内容（使用策略配置）

        Args:
            content: 架构设计内容
            source_id: 来源蓝图ID
            data_type: 数据类型
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        return self.split_content(
            content=content,
            data_type=data_type,
            source_id=source_id,
            project_id=project_id,
        )

    def create_simple_record(
        self,
        content: str,
        data_type: CodingDataType,
        source_id: str,
        project_id: str = "",
        **extra_metadata
    ) -> Optional[IngestionRecord]:
        """
        创建简单的入库记录（不分割）

        用于内容较短的数据类型，如系统划分、模块定义等。

        Args:
            content: 内容
            data_type: 数据类型
            source_id: 来源ID
            project_id: 项目ID
            **extra_metadata: 额外元数据

        Returns:
            入库记录，内容为空时返回None
        """
        if not content or not content.strip():
            return None

        return IngestionRecord(
            content=content.strip(),
            data_type=data_type,
            source_id=source_id,
            metadata={
                'section_index': 0,
                'total_sections': 1,
                **extra_metadata
            },
            project_id=project_id
        )

    def merge_qa_rounds(
        self,
        conversations: List[Dict[str, Any]],
        project_id: str,
        config: Optional[ChunkConfig] = None
    ) -> List[IngestionRecord]:
        """
        合并Q&A对话轮次

        将相邻的user消息+assistant回复合并为一条记录。

        Args:
            conversations: 对话记录列表，每条包含role和content
            project_id: 项目ID
            config: 分块配置（可选）

        Returns:
            入库记录列表
        """
        records: List[IngestionRecord] = []

        if not conversations:
            return records

        # 获取配置
        if config is None:
            config = get_strategy_manager().get_config(CodingDataType.INSPIRATION)

        max_length = config.max_chunk_length

        round_number = 0

        for round_convs in iter_qa_rounds(conversations):
            record = self._create_round_record(
                round_convs, project_id, round_number, max_length
            )
            if record:
                records.extend(record) if isinstance(record, list) else records.append(record)
                round_number += len(record) if isinstance(record, list) else 1

        return records

    def _create_round_record(
        self,
        round_convs: List[Dict[str, Any]],
        project_id: str,
        round_number: int,
        max_length: int = 2000
    ) -> Optional[IngestionRecord | List[IngestionRecord]]:
        """创建一轮对话的入库记录"""
        merged_content, start_seq, message_count = build_qa_round_text(round_convs)
        if not merged_content:
            return None

        # 如果内容过长，按段落分割
        if len(merged_content) > max_length:
            config = ChunkConfig(
                method=ChunkMethod.PARAGRAPH,
                min_chunk_length=200,
                max_chunk_length=max_length
            )
            splitter = ContentSplitter()
            return splitter.split_content(
                content=merged_content,
                data_type=CodingDataType.INSPIRATION,
                source_id=project_id,
                project_id=project_id,
                config=config,
                round_number=round_number,
                start_seq=start_seq,
                message_count=message_count,
            )

        return IngestionRecord(
            content=merged_content,
            data_type=CodingDataType.INSPIRATION,
            source_id=project_id,
            metadata={
                'round_number': round_number,
                'start_seq': start_seq,
                'message_count': message_count,
            },
            project_id=project_id
        )


__all__ = [
    "Section",
    "IngestionRecord",
    "ContentSplitter",
]
