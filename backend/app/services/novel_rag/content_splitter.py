"""
小说内容分割器

按格式智能分割长内容，保留来源追踪信息。
支持Markdown标题分割、Q&A对话合并、按段落分割等功能。
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .data_types import NovelDataType


@dataclass
class Section:
    """分割后的内容片段"""
    title: str                    # 小标题
    content: str                  # 内容
    index: int                    # 在原文中的顺序（从0开始）
    level: int = 2                # 标题级别（## = 2, ### = 3）


@dataclass
class NovelIngestionRecord:
    """小说入库记录"""
    content: str                  # 要入库的内容
    data_type: NovelDataType      # 数据类型
    source_id: str                # 来源记录ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    # 可选的章节信息（用于时序检索）
    chapter_number: Optional[int] = None

    def get_content_hash(self) -> str:
        """计算内容哈希，用于增量更新"""
        return hashlib.md5(self.content.encode('utf-8')).hexdigest()[:16]

    def get_chunk_id(self) -> str:
        """生成唯一的chunk ID"""
        type_prefix = self.data_type.value[:4]
        source_suffix = self.source_id[-8:] if len(self.source_id) > 8 else self.source_id
        content_hash = self.get_content_hash()
        section_idx = self.metadata.get('section_index', 0)
        return f"{type_prefix}_{source_suffix}_{section_idx}_{content_hash}"


class NovelContentSplitter:
    """小说内容分割器 - 按格式智能分割长内容"""

    # 最小chunk长度，太短的内容不分割
    MIN_CHUNK_LENGTH = 80
    # 最大chunk长度，超过需要强制分割（从2000降低到800，提高检索精度）
    MAX_CHUNK_LENGTH = 800
    # 重叠长度，相邻chunk之间的重叠字符数，保持上下文连贯性
    OVERLAP_LENGTH = 100
    # 长字段阈值，超过此长度的字段需要分割
    LONG_FIELD_THRESHOLD = 300

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

    def split_by_paragraphs(
        self,
        content: str,
        min_length: int = None,
        max_length: int = None,
        with_overlap: bool = True
    ) -> List[str]:
        """
        按段落分割内容

        Args:
            content: 原始内容
            min_length: 最小段落长度，默认使用类常量
            max_length: 最大段落长度，默认使用类常量
            with_overlap: 是否添加重叠，默认True

        Returns:
            段落列表
        """
        if not content or not content.strip():
            return []

        min_length = min_length or self.MIN_CHUNK_LENGTH
        max_length = max_length or self.MAX_CHUNK_LENGTH

        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        result: List[str] = []
        current_paragraph = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前段落加上新段落不超过max_length，合并
            if current_paragraph:
                combined = current_paragraph + "\n\n" + para
                if len(combined) <= max_length:
                    current_paragraph = combined
                else:
                    # 保存当前段落，开始新段落
                    if len(current_paragraph) >= min_length:
                        result.append(current_paragraph)
                    current_paragraph = para
            else:
                current_paragraph = para

            # 如果段落超过max_length，强制分割
            while len(current_paragraph) > max_length:
                # 尝试在句号处分割
                split_pos = self._find_split_position(current_paragraph, max_length)
                result.append(current_paragraph[:split_pos].strip())
                current_paragraph = current_paragraph[split_pos:].strip()

        # 保存最后一个段落
        if current_paragraph and len(current_paragraph) >= min_length:
            result.append(current_paragraph)

        # 添加重叠
        if with_overlap and len(result) > 1:
            result = self._add_overlap(result)

        return result

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        为分块列表添加重叠

        在每个块的开头添加上一块结尾的部分内容，保持上下文连贯性。

        Args:
            chunks: 原始分块列表

        Returns:
            添加重叠后的分块列表
        """
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]  # 第一块保持不变

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # 从上一块取重叠部分
            overlap_text = ""
            if len(prev_chunk) > self.OVERLAP_LENGTH:
                # 尝试在句号处截取重叠
                overlap_start = len(prev_chunk) - self.OVERLAP_LENGTH
                # 找到重叠区域内的第一个句号后的位置
                for punct in ['。', '！', '？', '.', '!', '?']:
                    pos = prev_chunk.find(punct, overlap_start)
                    if pos != -1 and pos < len(prev_chunk) - 10:
                        overlap_text = prev_chunk[pos + 1:].strip()
                        break

                # 如果没找到句号，直接从overlap_start截取
                if not overlap_text:
                    overlap_text = prev_chunk[overlap_start:].strip()

            # 组合重叠内容和当前块
            if overlap_text:
                result.append(f"[...] {overlap_text}\n\n{current_chunk}")
            else:
                result.append(current_chunk)

        return result

    def _find_split_position(self, text: str, max_pos: int) -> int:
        """
        找到合适的分割位置

        优先在句号、问号、感叹号处分割，其次在逗号处分割。

        Args:
            text: 要分割的文本
            max_pos: 最大位置

        Returns:
            分割位置
        """
        # 优先在句号、问号、感叹号处分割
        for punct in ['。', '！', '？', '.', '!', '?']:
            pos = text.rfind(punct, 0, max_pos)
            if pos > max_pos // 2:
                return pos + 1

        # 其次在逗号处分割
        for punct in ['，', ',', '；', ';']:
            pos = text.rfind(punct, 0, max_pos)
            if pos > max_pos // 2:
                return pos + 1

        # 最后在空格处分割
        pos = text.rfind(' ', 0, max_pos)
        if pos > max_pos // 2:
            return pos + 1

        # 强制在max_pos处分割
        return max_pos

    def merge_qa_rounds(
        self,
        conversations: List[Dict[str, Any]],
        project_id: str
    ) -> List[NovelIngestionRecord]:
        """
        合并Q&A对话轮次

        将相邻的user消息+assistant回复合并为一条记录。

        Args:
            conversations: 对话记录列表，每条包含role和content
            project_id: 项目ID

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

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
    ) -> Optional[NovelIngestionRecord]:
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

        return NovelIngestionRecord(
            content=merged_content,
            data_type=NovelDataType.INSPIRATION,
            source_id=project_id,
            metadata={
                'round_number': round_number,
                'start_seq': start_seq,
                'message_count': len(round_convs),
            }
        )

    def split_synopsis(
        self,
        content: str,
        source_id: str
    ) -> List[NovelIngestionRecord]:
        """
        分割故事概述

        Args:
            content: 故事概述内容
            source_id: 来源蓝图ID

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not content or not content.strip():
            return records

        # 尝试按标题分割
        sections = self.split_by_markdown_headers(content)

        if not sections or len(content) < self.MIN_CHUNK_LENGTH:
            # 内容较短或无标题，整体入库
            records.append(NovelIngestionRecord(
                content=content.strip(),
                data_type=NovelDataType.SYNOPSIS,
                source_id=source_id,
                metadata={
                    'section_title': '',
                    'section_index': 0,
                    'total_sections': 1,
                }
            ))
            return records

        total_sections = len(sections)
        for section in sections:
            section_content = f"## {section.title}\n\n{section.content}" if section.title else section.content

            records.append(NovelIngestionRecord(
                content=section_content,
                data_type=NovelDataType.SYNOPSIS,
                source_id=source_id,
                metadata={
                    'section_title': section.title,
                    'section_index': section.index,
                    'total_sections': total_sections,
                }
            ))

        return records

    def split_chapter_content(
        self,
        content: str,
        chapter_number: int,
        chapter_title: str,
        source_id: str
    ) -> List[NovelIngestionRecord]:
        """
        分割章节正文内容

        按段落分割，为每个片段添加来源追踪信息。

        Args:
            content: 章节正文内容
            chapter_number: 章节编号
            chapter_title: 章节标题
            source_id: 来源版本ID

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not content or not content.strip():
            return records

        # 按段落分割
        paragraphs = self.split_by_paragraphs(content)

        if not paragraphs:
            # 内容较短，整体入库
            if content.strip():
                records.append(NovelIngestionRecord(
                    content=content.strip(),
                    data_type=NovelDataType.CHAPTER_CONTENT,
                    source_id=source_id,
                    chapter_number=chapter_number,
                    metadata={
                        'chapter_number': chapter_number,
                        'chapter_title': chapter_title,
                        'section_index': 0,
                        'total_sections': 1,
                    }
                ))
            return records

        total_sections = len(paragraphs)
        for idx, para in enumerate(paragraphs):
            records.append(NovelIngestionRecord(
                content=para,
                data_type=NovelDataType.CHAPTER_CONTENT,
                source_id=source_id,
                chapter_number=chapter_number,
                metadata={
                    'chapter_number': chapter_number,
                    'chapter_title': chapter_title,
                    'section_index': idx,
                    'total_sections': total_sections,
                }
            ))

        return records

    def create_simple_record(
        self,
        content: str,
        data_type: NovelDataType,
        source_id: str,
        chapter_number: Optional[int] = None,
        **extra_metadata
    ) -> Optional[NovelIngestionRecord]:
        """
        创建简单的入库记录（不分割）

        用于内容较短的数据类型，如角色设定、章节大纲等。

        Args:
            content: 内容
            data_type: 数据类型
            source_id: 来源ID
            chapter_number: 章节编号（可选）
            **extra_metadata: 额外元数据

        Returns:
            入库记录，内容为空时返回None
        """
        if not content or not content.strip():
            return None

        return NovelIngestionRecord(
            content=content.strip(),
            data_type=data_type,
            source_id=source_id,
            chapter_number=chapter_number,
            metadata={
                'section_index': 0,
                'total_sections': 1,
                **extra_metadata
            }
        )

    def split_world_setting(
        self,
        world_setting: Dict[str, Any],
        source_id: str
    ) -> List[NovelIngestionRecord]:
        """
        分割世界观设置

        对于长字段（超过LONG_FIELD_THRESHOLD），按段落分割。
        短字段直接入库。

        Args:
            world_setting: 世界观设置字典
            source_id: 来源蓝图ID

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not world_setting:
            return records

        # 字段中文名映射
        field_names = {
            'era': '时代背景',
            'time_period': '时代背景',
            'location': '故事地点',
            'setting': '故事地点',
            'society': '社会背景',
            'social_context': '社会背景',
            'special_elements': '特殊设定',
            'unique_elements': '特殊设定',
            'core_rules': '核心规则',
            'magic_system': '魔法体系',
            'technology_level': '科技水平',
            'political_system': '政治体系',
            'culture': '文化背景',
            'history': '历史背景',
            'geography': '地理环境',
        }

        section_index = 0
        for key, value in world_setting.items():
            if not value:
                continue

            field_name = field_names.get(key, key.replace('_', ' ').title())

            if isinstance(value, str):
                # 长字段分割
                if len(value) > self.LONG_FIELD_THRESHOLD:
                    paragraphs = self.split_by_paragraphs(value, with_overlap=True)
                    for idx, para in enumerate(paragraphs):
                        content = f"[世界观-{field_name}]\n{para}"
                        records.append(NovelIngestionRecord(
                            content=content,
                            data_type=NovelDataType.WORLD_SETTING,
                            source_id=source_id,
                            metadata={
                                'field': key,
                                'field_name': field_name,
                                'section_index': section_index,
                                'sub_index': idx,
                            }
                        ))
                        section_index += 1
                else:
                    content = f"[世界观-{field_name}]\n{value}"
                    records.append(NovelIngestionRecord(
                        content=content,
                        data_type=NovelDataType.WORLD_SETTING,
                        source_id=source_id,
                        metadata={
                            'field': key,
                            'field_name': field_name,
                            'section_index': section_index,
                        }
                    ))
                    section_index += 1

            elif isinstance(value, list):
                # 列表字段，每个元素单独入库
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        item_content = self._format_dict_item(item)
                    else:
                        item_content = str(item)

                    if item_content:
                        content = f"[世界观-{field_name}]\n{item_content}"
                        records.append(NovelIngestionRecord(
                            content=content,
                            data_type=NovelDataType.WORLD_SETTING,
                            source_id=source_id,
                            metadata={
                                'field': key,
                                'field_name': field_name,
                                'section_index': section_index,
                                'list_index': idx,
                            }
                        ))
                        section_index += 1

            elif isinstance(value, dict):
                # 嵌套字典，递归处理
                nested_content = self._format_nested_dict(value)
                if nested_content:
                    content = f"[世界观-{field_name}]\n{nested_content}"
                    records.append(NovelIngestionRecord(
                        content=content,
                        data_type=NovelDataType.WORLD_SETTING,
                        source_id=source_id,
                        metadata={
                            'field': key,
                            'field_name': field_name,
                            'section_index': section_index,
                        }
                    ))
                    section_index += 1

        return records

    def split_character(
        self,
        character: Dict[str, Any],
        source_id: str,
        char_index: int = 0
    ) -> List[NovelIngestionRecord]:
        """
        按属性维度分割角色信息

        将角色拆分为多个维度：基本信息、外貌、性格、目标、能力、关系等。

        Args:
            character: 角色信息字典
            source_id: 来源蓝图ID
            char_index: 角色在列表中的索引

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not character:
            return records

        char_name = character.get('name', '未知角色')

        # 维度分组
        dimensions = {
            'basic': {
                'name': '基本信息',
                'fields': ['name', 'identity', 'role', 'age', 'gender', 'occupation']
            },
            'appearance': {
                'name': '外貌特征',
                'fields': ['appearance', 'physical_description', 'looks']
            },
            'personality': {
                'name': '性格特点',
                'fields': ['personality', 'traits', 'character', 'temperament']
            },
            'goals': {
                'name': '目标动机',
                'fields': ['goals', 'motivation', 'objectives', 'desires']
            },
            'abilities': {
                'name': '能力特长',
                'fields': ['abilities', 'skills', 'powers', 'talents']
            },
            'background': {
                'name': '背景经历',
                'fields': ['background', 'history', 'backstory', 'past']
            },
            'relationships': {
                'name': '人物关系',
                'fields': ['relationships', 'relationship_to_protagonist', 'connections']
            },
        }

        section_index = 0
        for dim_key, dim_info in dimensions.items():
            dim_content_parts = []

            for field in dim_info['fields']:
                value = character.get(field)
                if value:
                    if isinstance(value, str):
                        dim_content_parts.append(f"{field}: {value}")
                    elif isinstance(value, list):
                        dim_content_parts.append(f"{field}: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        dim_content_parts.append(f"{field}: {self._format_dict_item(value)}")

            if dim_content_parts:
                content = f"[角色-{char_name}-{dim_info['name']}]\n" + "\n".join(dim_content_parts)
                records.append(NovelIngestionRecord(
                    content=content,
                    data_type=NovelDataType.CHARACTER,
                    source_id=source_id,
                    metadata={
                        'character_name': char_name,
                        'dimension': dim_key,
                        'dimension_name': dim_info['name'],
                        'char_index': char_index,
                        'section_index': section_index,
                    }
                ))
                section_index += 1

        # 处理未归类的字段
        classified_fields = set()
        for dim_info in dimensions.values():
            classified_fields.update(dim_info['fields'])

        other_parts = []
        for key, value in character.items():
            if key not in classified_fields and value:
                if isinstance(value, str):
                    other_parts.append(f"{key}: {value}")
                elif isinstance(value, (list, dict)):
                    other_parts.append(f"{key}: {self._format_dict_item(value) if isinstance(value, dict) else ', '.join(str(v) for v in value)}")

        if other_parts:
            content = f"[角色-{char_name}-其他信息]\n" + "\n".join(other_parts)
            records.append(NovelIngestionRecord(
                content=content,
                data_type=NovelDataType.CHARACTER,
                source_id=source_id,
                metadata={
                    'character_name': char_name,
                    'dimension': 'other',
                    'dimension_name': '其他信息',
                    'char_index': char_index,
                    'section_index': section_index,
                }
            ))

        return records

    def split_protagonist(
        self,
        protagonist_profile: Dict[str, Any],
        source_id: str
    ) -> List[NovelIngestionRecord]:
        """
        按维度分割主角档案

        将主角档案拆分为：显式属性、隐式属性、社会属性、成长轨迹等。

        Args:
            protagonist_profile: 主角档案数据
            source_id: 主角档案ID

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not protagonist_profile:
            return records

        protagonist_name = protagonist_profile.get('name', '主角')

        # 维度定义
        dimensions = {
            'explicit': {
                'name': '显式属性',
                'fields': ['name', 'age', 'gender', 'appearance', 'occupation',
                          'identity', 'abilities', 'equipment', 'status']
            },
            'implicit': {
                'name': '隐式属性',
                'fields': ['personality', 'values', 'beliefs', 'fears', 'desires',
                          'motivations', 'goals', 'secrets', 'inner_conflict']
            },
            'social': {
                'name': '社会属性',
                'fields': ['relationships', 'family', 'friends', 'enemies',
                          'factions', 'social_status', 'reputation']
            },
            'growth': {
                'name': '成长轨迹',
                'fields': ['arc', 'development', 'changes', 'milestones',
                          'lessons_learned', 'transformation']
            },
            'background': {
                'name': '背景故事',
                'fields': ['backstory', 'origin', 'history', 'past_events',
                          'trauma', 'formative_experiences']
            },
        }

        section_index = 0
        for dim_key, dim_info in dimensions.items():
            dim_content_parts = []

            for field in dim_info['fields']:
                value = protagonist_profile.get(field)
                if value:
                    if isinstance(value, str):
                        # 长内容需要分割
                        if len(value) > self.LONG_FIELD_THRESHOLD:
                            paragraphs = self.split_by_paragraphs(value, with_overlap=False)
                            for idx, para in enumerate(paragraphs):
                                content = f"[主角-{protagonist_name}-{dim_info['name']}-{field}]\n{para}"
                                records.append(NovelIngestionRecord(
                                    content=content,
                                    data_type=NovelDataType.PROTAGONIST,
                                    source_id=source_id,
                                    metadata={
                                        'protagonist_name': protagonist_name,
                                        'dimension': dim_key,
                                        'dimension_name': dim_info['name'],
                                        'field': field,
                                        'section_index': section_index,
                                        'sub_index': idx,
                                    }
                                ))
                                section_index += 1
                        else:
                            dim_content_parts.append(f"{field}: {value}")
                    elif isinstance(value, list):
                        dim_content_parts.append(f"{field}: {', '.join(str(v) for v in value)}")
                    elif isinstance(value, dict):
                        dim_content_parts.append(f"{field}: {self._format_dict_item(value)}")

            if dim_content_parts:
                content = f"[主角-{protagonist_name}-{dim_info['name']}]\n" + "\n".join(dim_content_parts)
                records.append(NovelIngestionRecord(
                    content=content,
                    data_type=NovelDataType.PROTAGONIST,
                    source_id=source_id,
                    metadata={
                        'protagonist_name': protagonist_name,
                        'dimension': dim_key,
                        'dimension_name': dim_info['name'],
                        'section_index': section_index,
                    }
                ))
                section_index += 1

        return records

    def split_part_outline(
        self,
        part_outline: Dict[str, Any],
        source_id: str,
        part_number: int
    ) -> List[NovelIngestionRecord]:
        """
        分割分部大纲

        将分部大纲拆分为：主题、摘要、关键事件等。

        Args:
            part_outline: 分部大纲数据
            source_id: 分部大纲ID
            part_number: 分部编号

        Returns:
            入库记录列表
        """
        records: List[NovelIngestionRecord] = []

        if not part_outline:
            return records

        part_title = part_outline.get('title', f'第{part_number}部')

        # 定义要提取的字段
        fields_config = {
            'theme': '主题',
            'summary': '摘要',
            'description': '描述',
            'key_events': '关键事件',
            'arc': '故事弧',
            'conflicts': '冲突',
            'resolution': '解决',
            'character_development': '角色发展',
        }

        section_index = 0
        for field, field_name in fields_config.items():
            value = part_outline.get(field)
            if not value:
                continue

            if isinstance(value, str):
                # 长内容分割
                if len(value) > self.LONG_FIELD_THRESHOLD:
                    paragraphs = self.split_by_paragraphs(value, with_overlap=True)
                    for idx, para in enumerate(paragraphs):
                        content = f"[分部大纲-{part_title}-{field_name}]\n{para}"
                        records.append(NovelIngestionRecord(
                            content=content,
                            data_type=NovelDataType.PART_OUTLINE,
                            source_id=source_id,
                            metadata={
                                'part_number': part_number,
                                'part_title': part_title,
                                'field': field,
                                'field_name': field_name,
                                'section_index': section_index,
                                'sub_index': idx,
                            }
                        ))
                        section_index += 1
                else:
                    content = f"[分部大纲-{part_title}-{field_name}]\n{value}"
                    records.append(NovelIngestionRecord(
                        content=content,
                        data_type=NovelDataType.PART_OUTLINE,
                        source_id=source_id,
                        metadata={
                            'part_number': part_number,
                            'part_title': part_title,
                            'field': field,
                            'field_name': field_name,
                            'section_index': section_index,
                        }
                    ))
                    section_index += 1

            elif isinstance(value, list):
                # 列表类型，每个元素单独入库
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        item_content = self._format_dict_item(item)
                    else:
                        item_content = str(item)

                    if item_content:
                        content = f"[分部大纲-{part_title}-{field_name}]\n{item_content}"
                        records.append(NovelIngestionRecord(
                            content=content,
                            data_type=NovelDataType.PART_OUTLINE,
                            source_id=source_id,
                            metadata={
                                'part_number': part_number,
                                'part_title': part_title,
                                'field': field,
                                'field_name': field_name,
                                'section_index': section_index,
                                'list_index': idx,
                            }
                        ))
                        section_index += 1

        return records

    def _format_dict_item(self, item: Dict[str, Any]) -> str:
        """格式化字典项为字符串"""
        if not item:
            return ""

        parts = []
        for key, value in item.items():
            if value:
                if isinstance(value, str):
                    parts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    parts.append(f"{key}: {', '.join(str(v) for v in value)}")

        return "; ".join(parts)

    def _format_nested_dict(self, data: Dict[str, Any]) -> str:
        """格式化嵌套字典"""
        if not data:
            return ""

        parts = []
        for key, value in data.items():
            if value:
                if isinstance(value, str):
                    parts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    parts.append(f"{key}: {', '.join(str(v) for v in value)}")
                elif isinstance(value, dict):
                    nested = self._format_dict_item(value)
                    if nested:
                        parts.append(f"{key}: {nested}")

        return "\n".join(parts)


__all__ = [
    "Section",
    "NovelIngestionRecord",
    "NovelContentSplitter",
]
