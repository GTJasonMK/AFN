"""
启动动画配置常量

集中管理启动动画相关的所有可配置参数，便于调整和维护。
"""


class AnimationConfig:
    """启动动画配置"""

    # ==================== 画布配置 ====================
    CANVAS_WIDTH = 100       # 画布宽度（字符）
    CANVAS_HEIGHT = 22       # 画布高度（行）
    LOGO_START_ROW = 2       # Logo起始行

    # ==================== 旋转动画配置 ====================
    NUM_FRAMES = 16          # 旋转动画帧数（越多越细腻）
    FRAME_INTERVAL = 0.12    # 每帧间隔（秒），越大越慢

    # 3D旋转参数
    SIDE_VIEW_THRESHOLD = 0.3    # 侧视图切换阈值（cos值）
    MIN_COMPRESS_RATIO = 0.15    # 最小压缩比例
    FULL_RATIO_THRESHOLD = 0.99  # 视为完整显示的阈值

    # ==================== 星辰背景配置 ====================
    STAR_COUNT_MIN = 50      # 最少星星数量
    STAR_COUNT_MAX = 80      # 最多星星数量
    STAR_TWINKLE_PROB = 0.3  # 星星闪烁概率
    STAR_TWINKLE_CYCLE = 4   # 闪烁周期（帧数）

    # ==================== 展开动画配置 ====================
    EXPAND_TOTAL_FRAMES = 20     # 展开动画总帧数
    EXPAND_FRAME_INTERVAL = 0.035  # 展开动画帧间隔（秒）

    # ==================== 淡入动画配置 ====================
    FADE_IN_TOTAL_FRAMES = 12    # 淡入动画总帧数
    FADE_IN_FRAME_INTERVAL = 0.05  # 淡入动画帧间隔（秒）
    FADE_IN_FINAL_PAUSE = 0.3    # 淡入完成后暂停时间（秒）

    # ==================== 停止动画配置 ====================
    STOP_WAIT_ITERATIONS = 30    # 停止动画等待循环次数
    STOP_WAIT_INTERVAL = 0.1     # 停止动画等待间隔（秒）
