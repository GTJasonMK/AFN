"""
内容分割器

按格式智能分割长内容，保留来源追踪信息。
支持Markdown标题分割、Q&A对话合并等功能。
支持可配置的分块策略。
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .data_types import CodingDataType
from .chunk_strategy import ChunkMethod, ChunkConfig, get_strategy_manager

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


class ContentSplitter:
    """内容分割器 - 按格式智能分割长内容，支持策略配置"""

    # 默认参数（可被配置覆盖）
    MIN_CHUNK_LENGTH = 100
    MAX_CHUNK_LENGTH = 2000

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
        content = content.strip()

        # 添加上下文前缀（如果配置了）
        if config.add_context_prefix and extra_metadata.get('parent_title'):
            content = f"[{extra_metadata['parent_title']}]\n\n{content}"

        return [IngestionRecord(
            content=content,
            data_type=data_type,
            source_id=source_id,
            metadata={
                'section_index': 0,
                'total_sections': 1,
                **extra_metadata
            },
            project_id=project_id
        )]

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

        records = []
        total_sections = len(sections)

        for section in sections:
            section_content = f"## {section.title}\n\n{section.content}" if section.title else section.content

            # 添加上下文前缀
            if config.add_context_prefix and extra_metadata.get('parent_title'):
                section_content = f"[{extra_metadata['parent_title']}]\n\n{section_content}"

            records.append(IngestionRecord(
                content=section_content,
                data_type=data_type,
                source_id=source_id,
                metadata={
                    'section_title': section.title,
                    'section_index': section.index,
                    'total_sections': total_sections,
                    **extra_metadata
                },
                project_id=project_id
            ))

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
        # 按连续空行分割段落
        paragraphs = re.split(r'\n\s*\n', content.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return []

        # 合并过短的段落
        merged = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) < config.min_chunk_length:
                current = f"{current}\n\n{para}" if current else para
            else:
                if current:
                    merged.append(current)
                current = para

        if current:
            merged.append(current)

        # 如果合并后只有一段，整体入库
        if len(merged) <= 1:
            return self._split_whole(content, data_type, source_id, project_id, config, **extra_metadata)

        records = []
        for idx, para in enumerate(merged):
            para_content = para

            # 添加上下文前缀
            if config.add_context_prefix and extra_metadata.get('parent_title'):
                para_content = f"[{extra_metadata['parent_title']}]\n\n{para_content}"

            records.append(IngestionRecord(
                content=para_content,
                data_type=data_type,
                source_id=source_id,
                metadata={
                    'section_index': idx,
                    'total_sections': len(merged),
                    **extra_metadata
                },
                project_id=project_id
            ))

        return records

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
        content = content.strip()

        if len(content) <= chunk_size:
            return self._split_whole(content, data_type, source_id, project_id, config, **extra_metadata)

        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]

            # 尝试在句子边界截断
            if end < len(content):
                # 查找最后一个句号、问号、感叹号
                last_sentence_end = max(
                    chunk.rfind('。'),
                    chunk.rfind('？'),
                    chunk.rfind('！'),
                    chunk.rfind('.'),
                    chunk.rfind('?'),
                    chunk.rfind('!')
                )
                if last_sentence_end > chunk_size * 0.5:
                    chunk = chunk[:last_sentence_end + 1]
                    end = start + last_sentence_end + 1

            chunks.append(chunk.strip())
            start = end - overlap if end < len(content) else end

        records = []
        for idx, chunk in enumerate(chunks):
            chunk_content = chunk

            # 添加上下文前缀
            if config.add_context_prefix and extra_metadata.get('parent_title'):
                chunk_content = f"[{extra_metadata['parent_title']}]\n\n{chunk_content}"

            records.append(IngestionRecord(
                content=chunk_content,
                data_type=data_type,
                source_id=source_id,
                metadata={
                    'section_index': idx,
                    'total_sections': len(chunks),
                    **extra_metadata
                },
                project_id=project_id
            ))

        return records

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
            # 延迟导入语义分块器，避免循环依赖
            from ..rag_common.semantic_chunker import (
                SemanticChunker,
                SemanticChunkConfig,
            )

            # 构建语义分块配置
            semantic_config = SemanticChunkConfig(
                gate_threshold=config.semantic_gate_threshold,
                alpha=config.semantic_alpha,
                gamma=config.semantic_gamma,
                min_chunk_sentences=config.semantic_min_sentences,
                max_chunk_sentences=config.semantic_max_sentences,
                min_chunk_chars=config.min_chunk_length,
                max_chunk_chars=config.max_chunk_length,
                with_overlap=False,  # 编程项目一般不需要重叠
                overlap_sentences=0,
            )

            # 创建语义分块器并执行分块
            chunker = SemanticChunker(config=semantic_config)
            chunk_results = await chunker.chunk_text_async(
                text=content,
                embedding_func=embedding_func,
                config=semantic_config
            )

            # 转换为IngestionRecord
            records = []
            for idx, chunk in enumerate(chunk_results):
                chunk_content = chunk.content

                # 添加上下文前缀
                if config.add_context_prefix and extra_metadata.get('parent_title'):
                    chunk_content = f"[{extra_metadata['parent_title']}]\n\n{chunk_content}"

                records.append(IngestionRecord(
                    content=chunk_content,
                    data_type=data_type,
                    source_id=source_id,
                    project_id=project_id,
                    metadata={
                        'section_index': idx,
                        'total_sections': len(chunk_results),
                        'sentence_count': chunk.sentence_count,
                        'density_score': chunk.density_score,
                        'semantic_chunked': True,
                        **extra_metadata
                    }
                ))

            return records

        except Exception as e:
            logger.warning("语义分块失败: %s，降级为段落分割", str(e))
            return self._split_paragraph(
                content, data_type, source_id, project_id, config, **extra_metadata
            )

    # ==================== 原有方法（保持向后兼容） ====================

    def split_by_markdown_headers(
        self,
        content: str,
        min_level: int = 2,
        max_level: int = 3
    ) -> List[Section]:
        """
        按Markdown标题分割内容

        Args:
            content: 原始Markdown内容
            min_level: 最小标题级别（2 = ##）
            max_level: 最大标题级别（3 = ###）

        Returns:
            分割后的Section列表
        """
        if not content or not content.strip():
            return []

        # 构建标题匹配正则：匹配 ## 到 ### 级别的标题
        header_pattern = r'^(#{' + str(min_level) + ',' + str(max_level) + r'})\s+(.+)$'
        lines = content.split('\n')

        sections: List[Section] = []
        current_title = ""
        current_level = min_level
        current_lines: List[str] = []
        section_index = 0

        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # 保存之前的section
                if current_lines:
                    section_content = '\n'.join(current_lines).strip()
                    if section_content:
                        sections.append(Section(
                            title=current_title,
                            content=section_content,
                            index=section_index,
                            level=current_level
                        ))
                        section_index += 1

                # 开始新section
                current_level = len(match.group(1))
                current_title = match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        # 保存最后一个section
        if current_lines:
            section_content = '\n'.join(current_lines).strip()
            if section_content:
                sections.append(Section(
                    title=current_title,
                    content=section_content,
                    index=section_index,
                    level=current_level
                ))

        return sections

    def split_feature_prompt(
        self,
        content: str,
        feature_number: int,
        feature_title: str,
        source_id: str,
        project_id: str = ""
    ) -> List[IngestionRecord]:
        """
        分割功能Prompt内容（使用策略配置）

        Args:
            content: 功能Prompt内容
            feature_number: 功能编号
            feature_title: 功能标题
            source_id: 来源章节ID
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        return self.split_content(
            content=content,
            data_type=CodingDataType.FEATURE_PROMPT,
            source_id=source_id,
            project_id=project_id,
            feature_number=feature_number,
            parent_title=feature_title,
        )

    def split_review_prompt(
        self,
        content: str,
        feature_number: int,
        feature_title: str,
        source_id: str,
        project_id: str = ""
    ) -> List[IngestionRecord]:
        """
        分割审查/测试Prompt内容（使用策略配置）

        Args:
            content: 审查Prompt内容
            feature_number: 功能编号
            feature_title: 功能标题
            source_id: 来源功能ID
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        return self.split_content(
            content=content,
            data_type=CodingDataType.REVIEW_PROMPT,
            source_id=source_id,
            project_id=project_id,
            feature_number=feature_number,
            parent_title=feature_title,
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

        # 按轮次合并
        current_round: List[Dict[str, Any]] = []
        round_number = 0

        for conv in conversations:
            role = conv.get('role', '')
            content = conv.get('content', '')
            seq = conv.get('seq', 0)

            if role == 'user':
                # 新轮次开始，保存上一轮
                if current_round:
                    record = self._create_round_record(
                        current_round, project_id, round_number, max_length
                    )
                    if record:
                        records.extend(record) if isinstance(record, list) else records.append(record)
                        round_number += len(record) if isinstance(record, list) else 1
                current_round = [conv]
            elif role == 'assistant' and current_round:
                # 添加到当前轮次
                current_round.append(conv)

        # 保存最后一轮
        if current_round:
            record = self._create_round_record(
                current_round, project_id, round_number, max_length
            )
            if record:
                records.extend(record) if isinstance(record, list) else records.append(record)

        return records

    def _create_round_record(
        self,
        round_convs: List[Dict[str, Any]],
        project_id: str,
        round_number: int,
        max_length: int = 2000
    ) -> Optional[IngestionRecord | List[IngestionRecord]]:
        """创建一轮对话的入库记录"""
        if not round_convs:
            return None

        # 构建对话内容
        parts = []
        start_seq = round_convs[0].get('seq', 0)

        for conv in round_convs:
            role = conv.get('role', '')
            content = conv.get('content', '')
            if role == 'user':
                parts.append(f"用户: {content}")
            elif role == 'assistant':
                parts.append(f"助手: {content}")

        if not parts:
            return None

        merged_content = '\n\n'.join(parts)

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
                message_count=len(round_convs),
            )

        return IngestionRecord(
            content=merged_content,
            data_type=CodingDataType.INSPIRATION,
            source_id=project_id,
            metadata={
                'round_number': round_number,
                'start_seq': start_seq,
                'message_count': len(round_convs),
            },
            project_id=project_id
        )


__all__ = [
    "Section",
    "IngestionRecord",
    "ContentSplitter",
]
