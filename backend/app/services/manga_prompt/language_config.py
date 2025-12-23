"""
漫画提示词语言配置

集中管理所有与语言相关的配置，包括：
- 语言提示映射
- 各语言的音效示例
- 禁止使用的非目标语言模式

如需添加新语言支持：
1. 在 LANGUAGE_HINTS 中添加语言标识和显示名称
2. 在 SOUND_EFFECT_EXAMPLES 中添加该语言的音效词示例
3. 在 FORBIDDEN_SFX_PATTERNS 中定义该语言需要排除的外语模式
"""

from typing import Dict, List


# ==================== 语言提示映射 ====================

# 语言标识 -> 显示名称（用于LLM提示词）
LANGUAGE_HINTS: Dict[str, str] = {
    "chinese": "中文",
    "japanese": "日语",
    "english": "英文",
    "korean": "韩语",
}


# ==================== 音效词示例 ====================

# 各语言的音效示例（详细版）
# 用于指导LLM生成符合目标语言的音效词
SOUND_EFFECT_EXAMPLES: Dict[str, str] = {
    "chinese": """
常用音效词（必须使用这些中文音效，禁止使用日语或英语）：
- 撞击/爆炸: 砰、嘭、轰、咚、啪
- 快速移动: 嗖、呼、唰、嗒嗒
- 水/液体: 哗、滴答、咕嘟
- 心跳: 咚咚、扑通扑通
- 脚步: 哒哒、咚咚
- 风声: 呼呼、飒飒
- 碎裂: 咔嚓、哗啦
- 其他: 嘶、咔、吱呀""",

    "japanese": """
常用音效词：
- 衝撃/爆発: ドン、バン、ドカン、ガン
- 高速移動: シュッ、ビュン、ヒュー
- 水/液体: ザザ、ポタポタ、ゴボゴボ
- 心臓の鼓動: ドキドキ、バクバク
- 足音: タッタッ、ドタドタ
- 風: ヒュー、ビュービュー
- 破壊: バキ、ガシャン
- その他: シーン、ゴゴゴ、ザワザワ""",

    "english": """
Common sound effects:
- Impact/Explosion: BANG, BOOM, THUD, CRASH, SLAM
- Fast movement: WHOOSH, ZOOM, SWOOSH, DASH
- Water/Liquid: SPLASH, DRIP, GURGLE
- Heartbeat: THUMP THUMP, BA-DUM
- Footsteps: TAP TAP, STOMP
- Wind: WHOOO, RUSTLE
- Breaking: CRACK, SHATTER, CRUNCH
- Others: SILENCE, RUMBLE, BUZZ""",

    "korean": """
자주 사용하는 효과음:
- 충격/폭발: 쾅, 펑, 쿵, 탕
- 빠른 이동: 슉, 휙, 쓩
- 물/액체: 철퍼덕, 똑똑, 꼴깍
- 심장박동: 두근두근, 쿵쾅쿵쾅
- 발소리: 타닥타닥, 쿵쿵
- 바람: 휘이익, 살랑살랑
- 파괴: 쩍, 와장창
- 기타: 조용, 우르릉, 윙윙""",
}


# ==================== 禁止音效模式 ====================

# 禁止使用的非目标语言音效词（用于后处理检测）
# 格式：目标语言 -> 需要排除的正则模式列表
FORBIDDEN_SFX_PATTERNS: Dict[str, List[str]] = {
    "chinese": [
        # 日语音效词
        r"[ァ-ヶー]+",  # 片假名
        r"[ぁ-ん]+",    # 平假名
        # 英语音效词
        r"\b(BANG|BOOM|WHOOSH|THUD|CRASH|SLAM|SPLASH|CRACK|THUMP|RUSTLE)\b",
    ],
    "japanese": [
        # 中文音效词
        r"[砰嘭轰咚啪嗖呼唰哗咕咔嚓吱呀]+",
        # 英语音效词
        r"\b(BANG|BOOM|WHOOSH|THUD|CRASH|SLAM|SPLASH|CRACK|THUMP|RUSTLE)\b",
    ],
    "english": [
        # 日语音效词
        r"[ァ-ヶー]+",
        r"[ぁ-ん]+",
        # 中文音效词
        r"[砰嘭轰咚啪嗖呼唰哗咕咔嚓吱呀]+",
    ],
    "korean": [
        # 日语音效词
        r"[ァ-ヶー]+",
        r"[ぁ-ん]+",
        # 中文音效词
        r"[砰嘭轰咚啪嗖呼唰哗咕咔嚓吱呀]+",
        # 英语音效词
        r"\b(BANG|BOOM|WHOOSH|THUD|CRASH|SLAM|SPLASH|CRACK|THUMP|RUSTLE)\b",
    ],
}


# ==================== 禁止语言提示 ====================

# 生成禁止使用的语言提示（用于LLM指导）
# 目标语言 -> 禁止语言提示文本
FORBIDDEN_LANGUAGE_HINTS: Dict[str, str] = {
    "chinese": """
- 禁止使用日语（如：ドン、バン、ゴゴゴ、ドキドキ等片假名/平假名）
- 禁止使用英语（如：BANG、BOOM、WHOOSH等）
- 禁止使用韩语（如：쾅、슉、두근두근等）
- 只能使用中文拟声词（如：砰、嘭、轰、咚、嗖等）""",

    "japanese": """
- 禁止使用中文（如：砰、嘭、轰、咚、嗖等汉字拟声词）
- 禁止使用英语（如：BANG、BOOM、WHOOSH等）
- 禁止使用韩语（如：쾅、슉、두근두근等）
- 只能使用日语拟声词（如：ドン、バン、シュッ等片假名）""",

    "english": """
- 禁止使用日语（如：ドン、バン、ゴゴゴ等片假名/平假名）
- 禁止使用中文（如：砰、嘭、轰、咚、嗖等汉字拟声词）
- 禁止使用韩语（如：쾅、슉、두근두근等）
- 只能使用英语（如：BANG、BOOM、WHOOSH、THUD等）""",

    "korean": """
- 禁止使用日语（如：ドン、バン、ゴゴゴ等片假名/平假名）
- 禁止使用中文（如：砰、嘭、轰、咚、嗖等汉字拟声词）
- 禁止使用英语（如：BANG、BOOM、WHOOSH等）
- 只能使用韩语（如：쾅、슉、두근두근等）""",
}


# ==================== 辅助函数 ====================

def get_language_hint(language: str) -> str:
    """
    获取语言的显示名称

    Args:
        language: 语言标识（如 "chinese"）

    Returns:
        语言显示名称（如 "中文"），未知语言返回 "中文"
    """
    return LANGUAGE_HINTS.get(language, "中文")


def get_sfx_examples(language: str) -> str:
    """
    获取指定语言的音效词示例

    Args:
        language: 语言标识

    Returns:
        音效词示例文本，未知语言返回中文示例
    """
    return SOUND_EFFECT_EXAMPLES.get(language, SOUND_EFFECT_EXAMPLES["chinese"])


def get_forbidden_patterns(language: str) -> List[str]:
    """
    获取指定语言需要排除的外语模式

    Args:
        language: 目标语言标识

    Returns:
        正则模式列表，未知语言返回空列表
    """
    return FORBIDDEN_SFX_PATTERNS.get(language, [])


def get_forbidden_hint(language: str) -> str:
    """
    获取禁止语言提示文本

    Args:
        language: 目标语言标识

    Returns:
        禁止语言提示文本，未知语言返回中文提示
    """
    return FORBIDDEN_LANGUAGE_HINTS.get(language, FORBIDDEN_LANGUAGE_HINTS["chinese"])


__all__ = [
    "LANGUAGE_HINTS",
    "SOUND_EFFECT_EXAMPLES",
    "FORBIDDEN_SFX_PATTERNS",
    "FORBIDDEN_LANGUAGE_HINTS",
    "get_language_hint",
    "get_sfx_examples",
    "get_forbidden_patterns",
    "get_forbidden_hint",
]
