"""
TXT文件解析器

提供基类和默认实现，用户可继承基类实现自定义解析逻辑。

使用方式：
    1. 使用默认解析器：
        parser = DefaultTxtParser()
        result = parser.parse(file_bytes)

    2. 自定义解析器：
        class MyParser(BaseTxtParser):
            def parse_chapters(self, content: str) -> List[ParsedChapter]:
                # 实现自定义解析逻辑
                chapters = []
                # ... 解析content，生成ParsedChapter列表
                return chapters

        parser = MyParser()
        result = parser.parse(file_bytes)
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def count_chinese_characters(text: str) -> int:
    """统计中文字符数（包括中文标点）"""
    count = 0
    for char in text:
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f' or '\uff00' <= char <= '\uffef':
            count += 1
    return count


@dataclass
class ParsedChapter:
    """解析后的章节"""
    chapter_number: int
    title: str
    content: str
    start_pos: int = 0  # 在原文中的起始位置
    word_count: int = 0

    def __post_init__(self):
        if self.word_count == 0:
            self.word_count = count_chinese_characters(self.content)


@dataclass
class ParseResult:
    """解析结果"""
    chapters: List[ParsedChapter]
    encoding: str
    pattern_name: str  # 使用的模式名称
    total_characters: int = 0
    warnings: List[str] = field(default_factory=list)

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class BaseTxtParser(ABC):
    """TXT解析器基类

    用户可以继承此类实现自定义的章节解析逻辑。
    只需实现 parse_chapters() 方法即可。

    示例：
        class MyCustomParser(BaseTxtParser):
            def parse_chapters(self, content: str) -> Tuple[List[ParsedChapter], str, List[str]]:
                chapters = []
                # 自定义解析逻辑...
                # 例如：按特定分隔符分割
                parts = content.split('===CHAPTER===')
                for i, part in enumerate(parts, 1):
                    if part.strip():
                        chapters.append(ParsedChapter(
                            chapter_number=i,
                            title=f"第{i}章",
                            content=part.strip()
                        ))
                return chapters, "custom_split", []
    """

    def detect_encoding(self, file_bytes: bytes) -> str:
        """
        检测文件编码

        优先使用chardet，失败时使用启发式方法。
        """
        try:
            import chardet
            result = chardet.detect(file_bytes[:10000])  # 只检测前10KB
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)

            # 编码映射（处理常见的别名）
            encoding_map = {
                'GB2312': 'GBK',
                'gb2312': 'GBK',
                'GB18030': 'GB18030',
                'ascii': 'utf-8',  # ASCII是UTF-8的子集
            }
            encoding = encoding_map.get(encoding, encoding)

            # 置信度过低时尝试常见编码
            if confidence < 0.7:
                for try_encoding in ['utf-8', 'GBK', 'GB18030']:
                    try:
                        file_bytes.decode(try_encoding)
                        return try_encoding
                    except (UnicodeDecodeError, LookupError):
                        continue

            return encoding or 'utf-8'

        except ImportError:
            # chardet未安装，使用启发式方法
            for encoding in ['utf-8', 'GBK', 'GB18030', 'utf-16']:
                try:
                    file_bytes.decode(encoding)
                    return encoding
                except (UnicodeDecodeError, LookupError):
                    continue
            return 'utf-8'

    def preprocess_content(self, content: str) -> str:
        """预处理文本内容

        子类可以覆盖此方法添加额外的预处理逻辑。
        """
        # 移除BOM，统一换行符
        content = content.lstrip('\ufeff')
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content

    @abstractmethod
    def parse_chapters(self, content: str) -> Tuple[List[ParsedChapter], str, List[str]]:
        """
        解析文本内容，返回章节列表

        这是子类必须实现的核心方法。

        Args:
            content: 已解码并预处理的文本内容

        Returns:
            Tuple[List[ParsedChapter], str, List[str]]:
                - chapters: 解析后的章节列表
                - pattern_name: 使用的解析模式名称（用于日志/调试）
                - warnings: 解析过程中的警告信息列表
        """
        pass

    def parse(self, file_bytes: bytes, encoding: Optional[str] = None) -> ParseResult:
        """
        解析TXT文件内容（公共入口）

        此方法处理编码检测和预处理，然后调用parse_chapters()进行章节解析。

        Args:
            file_bytes: 文件字节内容
            encoding: 指定编码，如果为None则自动检测

        Returns:
            ParseResult: 解析结果
        """
        # 1. 检测或使用指定编码
        if encoding is None:
            encoding = self.detect_encoding(file_bytes)

        try:
            content = file_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError) as e:
            # 尝试其他编码
            for fallback_encoding in ['utf-8', 'GBK', 'GB18030']:
                try:
                    content = file_bytes.decode(fallback_encoding)
                    encoding = fallback_encoding
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                raise ValueError(f"无法解码文件内容: {e}")

        # 2. 预处理
        content = self.preprocess_content(content)

        # 3. 调用子类实现的章节解析方法
        chapters, pattern_name, warnings = self.parse_chapters(content)

        # 4. 重新编号确保连续
        for i, chapter in enumerate(chapters, 1):
            chapter.chapter_number = i

        return ParseResult(
            chapters=chapters,
            encoding=encoding,
            pattern_name=pattern_name,
            total_characters=count_chinese_characters(content),
            warnings=warnings,
        )


# ============================================================================
# 默认实现
# ============================================================================

# 中文数字映射
CN_NUM_MAP = {
    '零': 0, '〇': 0,
    '一': 1, '壹': 1,
    '二': 2, '贰': 2, '两': 2,
    '三': 3, '叁': 3,
    '四': 4, '肆': 4,
    '五': 5, '伍': 5,
    '六': 6, '陆': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '十': 10, '拾': 10,
    '百': 100, '佰': 100,
    '千': 1000, '仟': 1000,
    '万': 10000,
}


def cn_to_arabic(cn_str: str) -> int:
    """
    中文数字转阿拉伯数字

    支持：一、二、三、...、九、十、百、千、万
    示例：
        一 -> 1
        十 -> 10
        十五 -> 15
        二十 -> 20
        一百二十三 -> 123
        三千五百 -> 3500
    """
    if not cn_str:
        return 0

    # 先尝试直接转换纯数字
    if cn_str.isdigit():
        return int(cn_str)

    result = 0
    temp = 0
    last_unit = 1

    for char in cn_str:
        if char in CN_NUM_MAP:
            value = CN_NUM_MAP[char]
            if value >= 10:  # 是单位（十、百、千、万）
                if temp == 0:
                    temp = 1  # 处理"十五"这种省略"一"的情况
                if value == 10000:  # 万
                    result = (result + temp) * value
                    temp = 0
                else:
                    temp *= value
                    if value >= last_unit:
                        result += temp
                        temp = 0
                    last_unit = value
            else:  # 是数字
                temp = value
        elif char.isdigit():
            temp = temp * 10 + int(char)

    return result + temp


class DefaultTxtParser(BaseTxtParser):
    """默认TXT解析器

    支持常见的章节格式：
    - 第X章 标题（中文数字或阿拉伯数字）
    - 第X回 标题
    - 第X节 标题
    - 【第X章】标题
    - Chapter X 标题
    - 数字. 标题（如：1. 开始）

    如果无法识别章节格式，会按固定字数（5000字）自动分割。
    """

    # 章节分隔正则表达式（按优先级排列）
    # 每个元素是 (pattern, name, extract_number_group, extract_title_group)
    CHAPTER_PATTERNS = [
        # 中文"第X章"格式
        (r'^第([一二三四五六七八九十百千万零〇两\d]+)章[\s：:·]*(.*)$', 'cn_chapter', 1, 2),
        # 中文"第X回"格式
        (r'^第([一二三四五六七八九十百千万零〇两\d]+)回[\s：:·]*(.*)$', 'cn_hui', 1, 2),
        # 中文"第X节"格式
        (r'^第([一二三四五六七八九十百千万零〇两\d]+)节[\s：:·]*(.*)$', 'cn_jie', 1, 2),
        # 【第X章】格式
        (r'^【第([一二三四五六七八九十百千万零〇两\d]+)章】[\s]*(.*)$', 'cn_bracket', 1, 2),
        # 英文 Chapter X 格式
        (r'^[Cc]hapter\s*(\d+)[\.:\s]*(.*)$', 'en_chapter', 1, 2),
        # 数字编号格式: 1. 标题 或 1、标题
        (r'^(\d+)[\.、]\s*(.+)$', 'numbered', 1, 2),
    ]

    # 最小章节字数（过滤过短的误识别）
    MIN_CHAPTER_CHARS = 100

    def __init__(self):
        self._compiled_patterns = [
            (re.compile(pattern, re.MULTILINE), name, num_group, title_group)
            for pattern, name, num_group, title_group in self.CHAPTER_PATTERNS
        ]

    def parse_chapters(self, content: str) -> Tuple[List[ParsedChapter], str, List[str]]:
        """解析章节"""
        warnings = []

        # 检测最佳章节模式
        best_pattern, pattern_name, matches = self._detect_best_pattern(content)

        if not matches or len(matches) < 2:
            # 无法识别章节，按固定字数分割
            chapters = self._split_by_length(content, 5000)
            pattern_name = "auto_split"
            warnings.append("无法识别章节分隔，已按5000字自动分割")
        else:
            # 根据匹配结果分割章节
            chapters = self._split_by_matches(content, matches, best_pattern)

        # 过滤过短的章节并合并
        valid_chapters = []
        for chapter in chapters:
            if chapter.word_count >= self.MIN_CHAPTER_CHARS:
                valid_chapters.append(chapter)
            else:
                # 将过短的章节合并到前一章
                if valid_chapters:
                    prev = valid_chapters[-1]
                    prev.content += "\n\n" + chapter.content
                    prev.word_count = count_chinese_characters(prev.content)

        return valid_chapters, pattern_name, warnings

    def _detect_best_pattern(self, content: str) -> Tuple[Optional[re.Pattern], str, List]:
        """
        检测最佳章节模式

        返回匹配数量最多的模式。
        """
        best_pattern = None
        best_name = ""
        best_matches = []
        max_count = 0

        for pattern, name, num_group, title_group in self._compiled_patterns:
            matches = list(pattern.finditer(content))
            if len(matches) > max_count:
                max_count = len(matches)
                best_pattern = pattern
                best_name = name
                best_matches = matches

        return best_pattern, best_name, best_matches

    def _split_by_matches(
        self,
        content: str,
        matches: List[re.Match],
        pattern: re.Pattern,
    ) -> List[ParsedChapter]:
        """根据正则匹配分割章节"""
        chapters = []

        # 获取模式信息
        pattern_info = None
        for p, name, num_group, title_group in self._compiled_patterns:
            if p.pattern == pattern.pattern:
                pattern_info = (num_group, title_group)
                break

        if pattern_info is None:
            pattern_info = (1, 2)

        num_group, title_group = pattern_info

        for i, match in enumerate(matches):
            # 提取章节号
            try:
                num_str = match.group(num_group)
                if num_str.isdigit():
                    chapter_number = int(num_str)
                else:
                    chapter_number = cn_to_arabic(num_str)
            except (IndexError, ValueError):
                chapter_number = i + 1

            # 提取标题
            try:
                title = match.group(title_group).strip() if title_group else ""
            except (IndexError, AttributeError):
                title = ""

            if not title:
                title = f"第{chapter_number}章"

            # 计算内容范围
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            chapter_content = content[start_pos:end_pos].strip()

            chapters.append(ParsedChapter(
                chapter_number=chapter_number,
                title=title,
                content=chapter_content,
                start_pos=start_pos,
            ))

        return chapters

    def _split_by_length(self, content: str, target_length: int = 5000) -> List[ParsedChapter]:
        """按固定字数分割"""
        chapters = []
        lines = content.split('\n')

        current_content = []
        current_length = 0
        chapter_number = 1

        for line in lines:
            line_length = count_chinese_characters(line)

            if current_length + line_length > target_length and current_content:
                # 当前章节已满，保存并开始新章节
                chapter_text = '\n'.join(current_content)
                chapters.append(ParsedChapter(
                    chapter_number=chapter_number,
                    title=f"第{chapter_number}章",
                    content=chapter_text,
                ))
                chapter_number += 1
                current_content = [line]
                current_length = line_length
            else:
                current_content.append(line)
                current_length += line_length

        # 处理最后一个章节
        if current_content:
            chapter_text = '\n'.join(current_content)
            chapters.append(ParsedChapter(
                chapter_number=chapter_number,
                title=f"第{chapter_number}章",
                content=chapter_text,
            ))

        return chapters


# ============================================================================
# 简单分隔符解析器示例（供用户参考）
# ============================================================================

class SimpleSplitParser(BaseTxtParser):
    """简单分隔符解析器示例

    按指定分隔符分割章节，适合格式统一的文本。

    使用示例：
        # 按"---"分隔
        parser = SimpleSplitParser(separator="---")
        result = parser.parse(file_bytes)

        # 按空行分隔
        parser = SimpleSplitParser(separator="\n\n\n")
        result = parser.parse(file_bytes)
    """

    def __init__(self, separator: str = "---"):
        """
        Args:
            separator: 章节分隔符
        """
        self.separator = separator

    def parse_chapters(self, content: str) -> Tuple[List[ParsedChapter], str, List[str]]:
        """按分隔符分割章节"""
        chapters = []
        warnings = []

        parts = content.split(self.separator)

        for i, part in enumerate(parts, 1):
            part = part.strip()
            if not part:
                continue

            # 尝试从第一行提取标题
            lines = part.split('\n', 1)
            if len(lines) > 1:
                title = lines[0].strip() or f"第{i}章"
                chapter_content = lines[1].strip()
            else:
                title = f"第{i}章"
                chapter_content = part

            chapters.append(ParsedChapter(
                chapter_number=i,
                title=title,
                content=chapter_content,
            ))

        if not chapters:
            warnings.append("未找到有效章节")

        return chapters, "simple_split", warnings


# 为了向后兼容，保留TxtParser别名
TxtParser = DefaultTxtParser
