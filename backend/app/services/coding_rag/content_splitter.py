"""
内容分割器

按格式智能分割长内容，保留来源追踪信息。
支持Markdown标题分割、Q&A对话合并等功能。
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .data_types import CodingDataType


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
    """内容分割器 - 按格式智能分割长内容"""

    # 最小chunk长度，太短的内容不分割
    MIN_CHUNK_LENGTH = 100
    # 最大chunk长度，超过需要强制分割
    MAX_CHUNK_LENGTH = 2000

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
        分割功能Prompt内容

        按Markdown标题分割，为每个section添加来源追踪信息。

        Args:
            content: 功能Prompt内容
            feature_number: 功能编号
            feature_title: 功能标题
            source_id: 来源章节ID
            project_id: 项目ID（用于生成唯一chunk_id）

        Returns:
            入库记录列表
        """
        records: List[IngestionRecord] = []

        # 按标题分割
        sections = self.split_by_markdown_headers(content)

        if not sections:
            # 没有标题，整体作为一条记录
            if content and content.strip():
                records.append(IngestionRecord(
                    content=content.strip(),
                    data_type=CodingDataType.FEATURE_PROMPT,
                    source_id=source_id,
                    metadata={
                        'feature_number': feature_number,
                        'parent_title': feature_title,
                        'section_title': '',
                        'section_index': 0,
                        'total_sections': 1,
                    },
                    project_id=project_id
                ))
            return records

        total_sections = len(sections)
        for section in sections:
            # 构建带上下文的内容
            section_content = f"## {section.title}\n\n{section.content}" if section.title else section.content

            records.append(IngestionRecord(
                content=section_content,
                data_type=CodingDataType.FEATURE_PROMPT,
                source_id=source_id,
                metadata={
                    'feature_number': feature_number,
                    'parent_title': feature_title,
                    'section_title': section.title,
                    'section_index': section.index,
                    'total_sections': total_sections,
                },
                project_id=project_id
            ))

        return records

    def split_architecture(
        self,
        content: str,
        source_id: str,
        data_type: CodingDataType = CodingDataType.ARCHITECTURE,
        project_id: str = ""
    ) -> List[IngestionRecord]:
        """
        分割架构设计内容

        Args:
            content: 架构设计内容
            source_id: 来源蓝图ID
            data_type: 数据类型
            project_id: 项目ID（用于生成唯一chunk_id）

        Returns:
            入库记录列表
        """
        records: List[IngestionRecord] = []

        if not content or not content.strip():
            return records

        # 尝试按标题分割
        sections = self.split_by_markdown_headers(content)

        if not sections or len(content) < self.MIN_CHUNK_LENGTH:
            # 内容较短或无标题，整体入库
            records.append(IngestionRecord(
                content=content.strip(),
                data_type=data_type,
                source_id=source_id,
                metadata={
                    'section_title': '',
                    'section_index': 0,
                    'total_sections': 1,
                },
                project_id=project_id
            ))
            return records

        total_sections = len(sections)
        for section in sections:
            section_content = f"## {section.title}\n\n{section.content}" if section.title else section.content

            records.append(IngestionRecord(
                content=section_content,
                data_type=data_type,
                source_id=source_id,
                metadata={
                    'section_title': section.title,
                    'section_index': section.index,
                    'total_sections': total_sections,
                },
                project_id=project_id
            ))

        return records

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
            project_id: 项目ID（用于生成唯一chunk_id）
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
        project_id: str
    ) -> List[IngestionRecord]:
        """
        合并Q&A对话轮次

        将相邻的user消息+assistant回复合并为一条记录。

        Args:
            conversations: 对话记录列表，每条包含role和content
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        records: List[IngestionRecord] = []

        if not conversations:
            return records

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
                        current_round, project_id, round_number
                    )
                    if record:
                        records.append(record)
                        round_number += 1
                current_round = [conv]
            elif role == 'assistant' and current_round:
                # 添加到当前轮次
                current_round.append(conv)

        # 保存最后一轮
        if current_round:
            record = self._create_round_record(
                current_round, project_id, round_number
            )
            if record:
                records.append(record)

        return records

    def _create_round_record(
        self,
        round_convs: List[Dict[str, Any]],
        project_id: str,
        round_number: int
    ) -> Optional[IngestionRecord]:
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
