"""
段落分析器

负责段落分割和内容分析，提取角色、场景、时间等关键元素。
"""

import logging
import re
from typing import List, Optional, Tuple

from .schemas import ParagraphAnalysis

logger = logging.getLogger(__name__)

# 最小段落长度（字符）
MIN_PARAGRAPH_LENGTH = 50
# 最大段落长度（字符），超过此长度会尝试拆分
MAX_PARAGRAPH_LENGTH = 800


class ParagraphAnalyzer:
    """段落分析器"""

    def __init__(self, known_characters: Optional[List[str]] = None):
        """
        初始化段落分析器

        Args:
            known_characters: 已知角色名列表（用于角色识别）
        """
        self.known_characters = known_characters or []

    def split_paragraphs(self, content: str) -> List[str]:
        """
        将正文分割为段落

        分割策略：
        1. 按换行符分割
        2. 合并过短的段落
        3. 拆分过长的段落

        Args:
            content: 正文内容

        Returns:
            段落列表
        """
        if not content or not content.strip():
            return []

        # 按换行符分割（支持多种换行符）
        raw_paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n|\r\s*\r', content)

        # 清理和过滤
        paragraphs = []
        for p in raw_paragraphs:
            p = p.strip()
            if not p:
                continue

            # 如果段落过长，尝试按句子拆分
            if len(p) > MAX_PARAGRAPH_LENGTH:
                sub_paragraphs = self._split_long_paragraph(p)
                paragraphs.extend(sub_paragraphs)
            else:
                paragraphs.append(p)

        # 合并过短的段落
        merged_paragraphs = self._merge_short_paragraphs(paragraphs)

        logger.info(
            "段落分割完成: 原始%d段 -> 最终%d段",
            len(raw_paragraphs),
            len(merged_paragraphs)
        )

        return merged_paragraphs

    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """
        拆分过长的段落

        按句号、问号、感叹号等句末标点拆分

        Args:
            paragraph: 长段落

        Returns:
            拆分后的段落列表
        """
        # 按句末标点拆分
        sentences = re.split(r'([。！？.!?]+)', paragraph)

        # 重新组合（保留标点）
        result = []
        current = ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            # 添加标点（如果存在）
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]

            if len(current) + len(sentence) > MAX_PARAGRAPH_LENGTH and current:
                result.append(current.strip())
                current = sentence
            else:
                current += sentence

        if current.strip():
            result.append(current.strip())

        return result if result else [paragraph]

    def _merge_short_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        合并过短的段落

        Args:
            paragraphs: 段落列表

        Returns:
            合并后的段落列表
        """
        if not paragraphs:
            return []

        result = []
        current = ""

        for p in paragraphs:
            if len(current) + len(p) < MIN_PARAGRAPH_LENGTH * 2:
                # 可以合并
                current = (current + "\n" + p).strip() if current else p
            else:
                if current:
                    result.append(current)
                current = p

        if current:
            result.append(current)

        return result

    def analyze_paragraph(
        self,
        paragraph: str,
        index: int,
        prev_paragraph: Optional[str] = None
    ) -> ParagraphAnalysis:
        """
        分析单个段落

        提取：
        - 涉及的角色
        - 场景/地点
        - 时间标记
        - 情感基调
        - 关键动作

        Args:
            paragraph: 段落文本
            index: 段落索引
            prev_paragraph: 前一段落（用于上下文分析）

        Returns:
            段落分析结果
        """
        # 提取角色
        characters = self._extract_characters(paragraph)

        # 提取场景
        scene = self._extract_scene(paragraph)

        # 提取时间标记
        time_marker = self._extract_time_marker(paragraph)

        # 提取情感基调
        emotion_tone = self._analyze_emotion_tone(paragraph)

        # 提取关键动作
        key_actions = self._extract_key_actions(paragraph)

        return ParagraphAnalysis(
            index=index,
            text=paragraph,
            characters=characters,
            scene=scene,
            time_marker=time_marker,
            emotion_tone=emotion_tone,
            key_actions=key_actions,
        )

    def _extract_characters(self, text: str) -> List[str]:
        """
        从文本中提取角色

        优先匹配已知角色，然后尝试提取常见的角色称谓模式

        Args:
            text: 文本内容

        Returns:
            角色名列表
        """
        found = []

        # 匹配已知角色
        for char in self.known_characters:
            if char in text:
                found.append(char)

        # 如果没有匹配到已知角色，尝试提取常见模式
        if not found:
            # 匹配常见的人物称谓模式（两字或三字名）
            # 注意：这是一个简化的实现，实际使用中可能需要NER
            patterns = [
                r'([A-Z][a-z]+)',  # 英文名
                r'([\u4e00-\u9fa5]{2,4})(?:道|说|想|看|走|笑|哭|问|答)',  # 动作前的名字
            ]
            for pattern in patterns:
                matches = re.findall(pattern, text)
                found.extend(matches[:3])  # 限制数量

        return list(set(found))[:5]  # 去重并限制数量

    def _extract_scene(self, text: str) -> Optional[str]:
        """
        提取场景/地点

        Args:
            text: 文本内容

        Returns:
            场景描述
        """
        # 常见的场景关键词
        scene_patterns = [
            r'在([\u4e00-\u9fa5]{2,8}(?:里|中|内|外|上|下|旁|边))',
            r'([\u4e00-\u9fa5]{2,6}(?:殿|宫|府|院|室|房|堂|阁|楼|亭|园|山|河|湖|海))',
            r'来到([\u4e00-\u9fa5]{2,8})',
            r'走进([\u4e00-\u9fa5]{2,8})',
        ]

        for pattern in scene_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_time_marker(self, text: str) -> Optional[str]:
        """
        提取时间标记

        Args:
            text: 文本内容

        Returns:
            时间标记
        """
        # 时间相关的关键词模式
        time_patterns = [
            r'(清晨|早上|上午|中午|下午|傍晚|黄昏|夜晚|深夜|凌晨|午时|子时|丑时|寅时|卯时|辰时|巳时|午时|未时|申时|酉时|戌时|亥时)',
            r'(第[一二三四五六七八九十百千]+[天日年月])',
            r'([一二三四五六七八九十]+[天日年月](?:后|前|之后|之前))',
            r'(次日|翌日|当天|那天|今日|明日|昨日)',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _analyze_emotion_tone(self, text: str) -> Optional[str]:
        """
        分析情感基调

        Args:
            text: 文本内容

        Returns:
            情感基调描述
        """
        # 情感词汇分类
        emotion_words = {
            "紧张": ["紧张", "焦虑", "不安", "惶恐", "慌张", "忐忑"],
            "悲伤": ["悲伤", "难过", "伤心", "哀伤", "痛苦", "悲痛", "哭泣", "泪"],
            "愤怒": ["愤怒", "生气", "恼怒", "暴怒", "怒火", "恨"],
            "喜悦": ["高兴", "开心", "欣喜", "快乐", "欢乐", "喜悦", "笑"],
            "平静": ["平静", "淡然", "从容", "镇定", "沉稳"],
            "惊讶": ["惊讶", "震惊", "吃惊", "愕然", "诧异"],
            "恐惧": ["恐惧", "害怕", "惊恐", "畏惧", "胆寒"],
        }

        # 统计各情感词出现次数
        emotion_counts = {}
        for emotion, words in emotion_words.items():
            count = sum(1 for word in words if word in text)
            if count > 0:
                emotion_counts[emotion] = count

        if emotion_counts:
            # 返回出现次数最多的情感
            return max(emotion_counts, key=emotion_counts.get)

        return None

    def _extract_key_actions(self, text: str) -> List[str]:
        """
        提取关键动作

        Args:
            text: 文本内容

        Returns:
            关键动作列表
        """
        # 动作动词模式
        action_patterns = [
            r'([他她它](?:们)?[一]?(?:把|将)?[\u4e00-\u9fa5]{0,4}(?:拿起|放下|抬起|举起|挥动|刺向|砍向|推开|拉住|抱住|握住|挡住|躲开|跳起|冲向|逃离|追赶|攻击|防御|躲避))',
            r'((?:猛然|突然|缓缓|急忙|连忙)[\u4e00-\u9fa5]{2,6})',
        ]

        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            actions.extend(matches[:3])

        return list(set(actions))[:5]

    def detect_scene_change(
        self,
        current_paragraph: str,
        prev_paragraph: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        检测场景是否发生变化

        Args:
            current_paragraph: 当前段落
            prev_paragraph: 前一段落

        Returns:
            (是否变化, 变化描述)
        """
        if not prev_paragraph:
            return False, None

        # 提取两个段落的场景
        current_scene = self._extract_scene(current_paragraph)
        prev_scene = self._extract_scene(prev_paragraph)

        # 检测场景转换关键词
        transition_keywords = [
            "来到", "走进", "进入", "离开", "回到", "转身",
            "另一边", "与此同时", "此时", "这时", "那边"
        ]

        has_transition = any(kw in current_paragraph[:50] for kw in transition_keywords)

        if current_scene and prev_scene and current_scene != prev_scene:
            return True, f"场景从'{prev_scene}'转换到'{current_scene}'"

        if has_transition:
            return True, "可能存在场景转换"

        return False, None
