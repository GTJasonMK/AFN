"""
画格提示词映射表

包含所有用于提示词生成的映射表和常量。
这些映射表将各种漫画元素（构图、镜头、情绪、音效等）
转换为AI图像生成可理解的英文描述。
"""

from ..page_templates import (
    SceneMood,
    DialogueBubbleType,
    SoundEffectType,
    SoundEffectIntensity,
)


# 构图描述映射
COMPOSITION_MAP = {
    "wide shot": "wide shot, full scene view, establishing shot",
    "medium shot": "medium shot, waist-up view, conversational framing",
    "medium close-up": "medium close-up, chest-up view, intimate framing",
    "close-up": "close-up shot, face focus, emotional emphasis",
    "extreme close-up": "extreme close-up, eye or detail focus, intense emotion",
    "dynamic wide shot": "dynamic wide shot, action framing, motion blur",
    "dynamic composition": "dynamic composition, diagonal lines, movement emphasis",
}

# 镜头角度映射
ANGLE_MAP = {
    "eye level": "eye level shot, neutral perspective",
    "low angle": "low angle shot, looking up, heroic perspective",
    "high angle": "high angle shot, looking down, vulnerable perspective",
    "bird's eye": "bird's eye view, overhead shot, god's perspective",
    "dutch angle": "dutch angle, tilted frame, tension and unease",
    "dynamic": "dynamic angle, action perspective, dramatic viewpoint",
    "dramatic": "dramatic angle, cinematic framing, high contrast",
}

# 情感到视觉风格的映射
MOOD_STYLE_MAP = {
    SceneMood.CALM: "soft lighting, peaceful atmosphere, warm tones",
    SceneMood.TENSION: "high contrast, sharp shadows, cold tones",
    SceneMood.ACTION: "motion lines, dynamic lighting, speed effects",
    SceneMood.EMOTIONAL: "soft focus, dramatic lighting, emotional depth",
    SceneMood.MYSTERY: "low key lighting, shadows, mysterious atmosphere",
    SceneMood.COMEDY: "bright lighting, exaggerated expressions, cheerful",
    SceneMood.DRAMATIC: "chiaroscuro lighting, dramatic shadows, cinematic",
    SceneMood.ROMANTIC: "soft glow, warm colors, dreamy atmosphere",
    SceneMood.HORROR: "dark shadows, unsettling lighting, ominous",
    SceneMood.FLASHBACK: "desaturated, soft edges, nostalgic filter",
}

# 基础负向提示词
BASE_NEGATIVE = (
    "low quality, blurry, distorted face, plastic skin, waxy appearance, "
    "extra limbs, bad anatomy, deformed, ugly, amateur, "
    "empty background, plain white background, "
    "text, watermark, signature, logo"
)

# 对话气泡类型到提示词的映射
BUBBLE_TYPE_MAP = {
    DialogueBubbleType.NORMAL: "speech bubble, dialogue balloon, round border",
    DialogueBubbleType.SHOUT: "jagged speech bubble, explosion bubble, spiky border, excited shout",
    DialogueBubbleType.WHISPER: "dotted speech bubble, soft bubble, dashed border, whisper",
    DialogueBubbleType.THOUGHT: "thought bubble, cloud bubble, thought balloon, fluffy cloud shape",
    DialogueBubbleType.NARRATION: "rectangular text box, caption box, narration box",
    DialogueBubbleType.ELECTRONIC: "wavy speech bubble, digital text bubble, electronic device speech",
}

# 音效类型到视觉效果的映射
SOUND_EFFECT_VISUAL_MAP = {
    SoundEffectType.ACTION: "speed lines, motion lines, action lines",
    SoundEffectType.IMPACT: "impact lines, radial lines, shockwave effect, explosion effect",
    SoundEffectType.AMBIENT: "ambient particles, environmental effect",
    SoundEffectType.EMOTIONAL: "emotion symbols, manga emotion effects",
    SoundEffectType.VOCAL: "vocal expression marks",
}

# 音效强度到视觉效果的映射
SOUND_INTENSITY_MAP = {
    SoundEffectIntensity.SMALL: "subtle effect, small text",
    SoundEffectIntensity.MEDIUM: "moderate effect, medium emphasis",
    SoundEffectIntensity.LARGE: "dramatic effect, large bold text, screen-filling effect",
}

# 各语言音效到视觉效果的映射
SOUND_VISUAL_MAP_BY_LANGUAGE = {
    "chinese": {
        "砰": "explosion effect, impact burst",
        "嗖": "speed lines, motion blur",
        "咚": "impact vibration, ground shake",
        "嘭": "explosion effect, dust cloud",
        "哗": "splash effect, water spray",
        "轰": "massive explosion, shockwave",
        "咚咚": "heartbeat rhythm effect",
        "沙沙": "subtle particle effect",
        "嘶": "sharp sound effect, hiss",
        "呼": "wind effect, breath",
    },
    "japanese": {
        "ドン": "explosion effect, impact burst",
        "シュッ": "speed lines, motion blur",
        "バン": "impact effect, bang",
        "ゴゴゴ": "rumbling effect, menacing aura",
        "ドキドキ": "heartbeat rhythm effect",
        "サラサラ": "flowing effect, gentle movement",
        "ザザ": "rough texture effect, static",
        "ガッ": "sudden grab effect, sharp motion",
        "ヒュー": "wind whistle effect, swoosh",
    },
    "english": {
        "BANG": "explosion effect, impact burst",
        "WHOOSH": "speed lines, motion blur",
        "THUD": "impact vibration, ground shake",
        "SPLASH": "splash effect, water spray",
        "BOOM": "massive explosion, shockwave",
        "CRACK": "breaking effect, sharp impact",
        "RUSTLE": "subtle particle effect, leaves",
        "CRASH": "destruction effect, debris",
        "SLAM": "door impact effect, sudden close",
    },
    "korean": {
        "쾅": "explosion effect, impact burst",
        "슉": "speed lines, motion blur",
        "쿵": "impact vibration, ground shake",
        "콰광": "massive explosion, shockwave",
        "두근두근": "heartbeat rhythm effect",
        "사각사각": "subtle particle effect",
        "펑": "burst effect, pop",
        "찰칵": "click effect, mechanical sound",
    },
}

# 镜头过渡描述映射（从什么到什么）
SHOT_TRANSITION_MAP = {
    # 从远到近
    ("wide shot", "medium shot"): "smooth transition from establishing shot, maintaining scene context",
    ("wide shot", "close-up"): "dramatic cut-in from wide view, focusing attention",
    ("wide shot", "extreme close-up"): "stark contrast jump, dramatic emphasis shift",
    ("medium shot", "close-up"): "gentle push-in, increasing intimacy",
    ("medium shot", "extreme close-up"): "dramatic zoom to detail",
    # 从近到远
    ("close-up", "medium shot"): "pulling back to show context",
    ("close-up", "wide shot"): "reveal shot, expanding view",
    ("extreme close-up", "medium shot"): "releasing tension, showing reaction",
    ("extreme close-up", "wide shot"): "dramatic reveal of full scene",
    # 相同镜头
    ("wide shot", "wide shot"): "consistent wide framing, scene continuity",
    ("medium shot", "medium shot"): "matched framing, conversational flow",
    ("close-up", "close-up"): "maintained intimacy, emotional continuity",
}

# 角度过渡描述
ANGLE_TRANSITION_MAP = {
    ("eye level", "low angle"): "shifting to heroic perspective",
    ("eye level", "high angle"): "moving to vulnerable viewpoint",
    ("low angle", "eye level"): "returning to neutral perspective",
    ("high angle", "eye level"): "leveling the perspective",
    ("eye level", "dutch angle"): "adding visual tension",
    ("dutch angle", "eye level"): "stabilizing the frame",
}

# 风格基础提示词
STYLE_PROMPTS = {
    "manga": (
        "manga style, Japanese comic art, clean bold ink lines, "
        "screentone shading, black and white, high contrast, "
        "professional manga panel, detailed linework"
    ),
    "anime": (
        "anime style, clean line art, cel shading, vibrant colors, "
        "expressive eyes, Japanese animation aesthetic, "
        "digital illustration, smooth coloring"
    ),
    "comic": (
        "Western comic book style, bold black outlines, "
        "flat colors, graphic novel art, dynamic composition, "
        "American comic aesthetic, strong shadows"
    ),
    "webtoon": (
        "Korean webtoon style, clean digital lines, "
        "soft cel shading, pastel colors, modern illustration, "
        "vertical scroll format optimized"
    ),
}

# 构图中文映射
COMPOSITION_ZH_MAP = {
    "wide shot": "全景",
    "medium shot": "中景",
    "medium close-up": "中近景",
    "close-up": "特写",
    "extreme close-up": "大特写",
    "dynamic wide shot": "动态全景",
    "dynamic composition": "动态构图",
}

# 说话动作映射
SPEAKING_ACTION_MAP = {
    DialogueBubbleType.NORMAL: "open mouth, talking",
    DialogueBubbleType.SHOUT: "shouting, wide open mouth, intense expression",
    DialogueBubbleType.WHISPER: "whispering, leaning close, subtle lip movement",
    DialogueBubbleType.THOUGHT: "thoughtful expression, inner monologue",
    DialogueBubbleType.NARRATION: "",  # 旁白不需要说话动作
    DialogueBubbleType.ELECTRONIC: "looking at device, phone conversation",
}

# 气泡位置映射
BUBBLE_POSITION_MAP = {
    "top-right": "at top right corner",
    "top-left": "at top left corner",
    "top-center": "at top center",
    "bottom-right": "at bottom right corner",
    "bottom-left": "at bottom left corner",
    "bottom-center": "at bottom center",
    "middle-right": "at middle right",
    "middle-left": "at middle left",
}

# 情绪效果映射
EMOTION_EFFECTS_MAP = {
    "angry": "anger vein, intense expression, furrowed brows",
    "happy": "sparkle effect, bright smile, joyful expression",
    "sad": "tear drop, melancholic expression, downcast eyes",
    "surprised": "shock lines, wide eyes, open mouth",
    "scared": "sweat drops, trembling, fearful expression",
    "excited": "sparkle eyes, energetic pose, enthusiastic",
    "shy": "blush lines, embarrassed expression, looking away",
    "determined": "focused eyes, firm expression, confident stance",
    "confused": "question mark effect, puzzled expression",
    "nervous": "sweat drop, anxious expression",
}

# 旁白位置映射
NARRATION_POSITION_MAP = {
    "top": "at top of panel",
    "bottom": "at bottom of panel",
    "left": "on left side",
    "right": "on right side",
}
