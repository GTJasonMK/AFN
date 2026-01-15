"""
粒子系统常量配置

集中管理首页粒子背景的所有可配置参数。
"""

import math


class ParticleConfig:
    """粒子系统配置"""

    # ==================== 动画配置 ====================
    ANIMATION_INTERVAL_MS = 33  # 动画定时器间隔（毫秒），约30fps
    INITIAL_SPAWN_WIDTH = 1200  # 粒子初始生成区域宽度
    INITIAL_SPAWN_HEIGHT = 800  # 粒子初始生成区域高度

    # ==================== 粒子数量配置 ====================
    INK_PARTICLE_COUNT = 15      # 墨滴粒子数量
    PAPER_PARTICLE_COUNT = 8     # 纸片粒子数量
    SPARKLE_PARTICLE_COUNT = 20  # 星光粒子数量
    STROKE_PARTICLE_COUNT = 5    # 书法笔触数量

    # ==================== 星座连线配置 ====================
    CONSTELLATION_MAX_DISTANCE = 150  # 最大连线距离
    CONSTELLATION_ALPHA_FACTOR = 20   # 连线透明度系数
    CONSTELLATION_LINE_WIDTH = 0.5    # 连线宽度


class BaseParticleConfig:
    """基础粒子配置"""

    # 透明度范围
    OPACITY_MIN = 0.3
    OPACITY_MAX = 0.7

    # 相位范围（用于呼吸效果）
    PHASE_MIN = 0
    PHASE_MAX = math.pi * 2

    # 旋转配置
    ROTATION_MIN = 0
    ROTATION_MAX = 360
    ROTATION_SPEED_MIN = -1
    ROTATION_SPEED_MAX = 1

    # 脉冲速度范围
    PULSE_SPEED_MIN = 0.02
    PULSE_SPEED_MAX = 0.05

    # 呼吸效果参数
    BREATH_BASE = 0.3
    BREATH_AMPLITUDE = 0.2


class InkParticleConfig:
    """墨滴粒子配置"""

    # 速度范围
    VX_MIN = -0.15
    VX_MAX = 0.15
    VY_MIN = -0.1
    VY_MAX = 0.2

    # 大小范围
    SIZE_MIN = 3
    SIZE_MAX = 8

    # 扩散配置
    MAX_SPREAD_MIN = 0
    MAX_SPREAD_MAX = 3
    SPREAD_SPEED = 0.01

    # 渲染配置
    COLOR_ALT_PROBABILITY = 0.3  # 使用备选颜色的概率
    OPACITY_FACTOR = 100         # 透明度系数
    HALO_OPACITY_FACTOR = 25     # 墨晕透明度系数
    HALO_SIZE_MULTIPLIER = 1.8   # 墨晕大小倍数


class PaperParticleConfig:
    """纸片粒子配置"""

    # 速度范围
    VX_MIN = -0.3
    VX_MAX = 0.3
    VY_MIN = -0.2
    VY_MAX = 0.1

    # 大小范围
    SIZE_MIN = 8
    SIZE_MAX = 15

    # 形状配置
    WIDTH_RATIO_MIN = 0.4
    WIDTH_RATIO_MAX = 0.8

    # 飘动配置
    FLUTTER_MIN = 0.5
    FLUTTER_MAX = 1.5
    FLUTTER_FACTOR = 0.1

    # 渲染配置
    OPACITY_FACTOR = 70       # 透明度系数
    EDGE_OPACITY_FACTOR = 20  # 边缘高光透明度系数
    EDGE_LINE_WIDTH = 0.5     # 边缘线宽


class SparkleParticleConfig:
    """星光粒子配置"""

    # 速度范围
    VX_MIN = -0.05
    VX_MAX = 0.05
    VY_MIN = -0.05
    VY_MAX = 0.05

    # 大小范围
    SIZE_MIN = 1
    SIZE_MAX = 3

    # 闪烁配置
    TWINKLE_SPEED_MIN = 0.05
    TWINKLE_SPEED_MAX = 0.15
    TWINKLE_BASE = 0.2
    TWINKLE_AMPLITUDE = 0.8
    TWINKLE_FREQUENCY = 3  # 闪烁频率倍数

    # 渲染配置
    OPACITY_FACTOR = 180       # 核心透明度系数
    GLOW_OPACITY_FACTOR = 30   # 光晕透明度系数
    GLOW_SIZE_MULTIPLIER = 3   # 光晕大小倍数
    STAR_OPACITY_THRESHOLD = 0.5  # 显示星芒的透明度阈值
    STAR_OPACITY_FACTOR = 100  # 星芒透明度系数
    STAR_LINE_WIDTH = 0.5      # 星芒线宽
    STAR_LENGTH_MULTIPLIER = 4 # 星芒长度倍数


class StrokeParticleConfig:
    """书法笔触粒子配置"""

    # 速度范围
    VX_MIN = -0.1
    VX_MAX = 0.1
    VY_MIN = -0.1
    VY_MAX = 0.1

    # 大小范围（笔触长度）
    SIZE_MIN = 20
    SIZE_MAX = 40

    # 形状配置
    CURVE_AMOUNT_MIN = 0.2
    CURVE_AMOUNT_MAX = 0.5
    THICKNESS_MIN = 1
    THICKNESS_MAX = 2.5

    # 渲染配置
    OPACITY_FACTOR = 60  # 透明度系数


class HomeAnimationConfig:
    """首页入场动画配置"""

    # 标题动画
    TITLE_DURATION_MS = 600       # 标题淡入时长（毫秒）
    TITLE_START_OPACITY = 0.0     # 标题起始透明度
    TITLE_END_OPACITY = 1.0       # 标题结束透明度

    # 副标题动画
    SUBTITLE_DURATION_MS = 600    # 副标题淡入时长（毫秒）
    SUBTITLE_DELAY_MS = 150       # 副标题延迟时间（毫秒）
    SUBTITLE_START_OPACITY = 0.0  # 副标题起始透明度
    SUBTITLE_END_OPACITY = 1.0    # 副标题结束透明度

    # 引言动画
    QUOTE_DURATION_MS = 800       # 引言淡入时长（毫秒）
    QUOTE_DELAY_MS = 400          # 引言延迟时间（毫秒）
    QUOTE_START_OPACITY = 0.0     # 引言起始透明度
    QUOTE_END_OPACITY = 0.85      # 引言结束透明度（略低于1.0增加诗意感）
