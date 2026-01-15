"""
启动动画模块

包含:
- print_banner() - 打印静态Logo
- StartupProgress - 启动进度管理器（旋转动画）
- startup_progress - 全局进度实例
"""

import os
import sys
import math
import time
import random
import threading
from pathlib import Path

from .config import BASE_DIR
from .logging_setup import logger
from .animation_config import AnimationConfig

# Logo文件路径（位于当前模块目录下）
LOGO_FILE = Path(__file__).parent / 'logo.txt'


def print_banner():
    """打印静态 Logo（从 logo.txt 加载，彩虹色）"""
    R = "\033[0m"
    GOLD = "\033[38;5;220m"
    PEACH = "\033[38;5;223m"
    ROSE = "\033[38;5;204m"

    # 彩虹色
    RAINBOW = [
        "\033[38;5;196m",   # 红
        "\033[38;5;208m",   # 橙
        "\033[38;5;220m",   # 黄
        "\033[38;5;46m",    # 绿
        "\033[38;5;51m",    # 青
        "\033[38;5;21m",    # 蓝
        "\033[38;5;129m",   # 紫
    ]

    # 从文件加载 Logo
    logo_file = LOGO_FILE
    front_view = []

    if logo_file.exists():
        try:
            with open(logo_file, 'r', encoding='utf-8') as f:
                content = f.read()
            current_section = None
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped == '[FRONT_VIEW]':
                    current_section = 'front'
                    continue
                elif stripped.startswith('[') and stripped.endswith(']'):
                    current_section = None
                    continue
                if stripped.startswith('#'):
                    continue
                if current_section == 'front':
                    front_view.append(line.rstrip())
            # 移除首尾空行
            while front_view and not front_view[0].strip():
                front_view.pop(0)
            while front_view and not front_view[-1].strip():
                front_view.pop()
        except Exception:
            pass

    print()
    if front_view:
        for i, line in enumerate(front_view):
            color = RAINBOW[i % len(RAINBOW)]
            print(f"{color}{line}{R}")
    else:
        # 备用简单文本
        print(f"{GOLD}  AFN - Agents for Novel{R}")

    print()
    print(f"{GOLD}              Agents for Novel  {ROSE}<3{R}")
    print(f"{PEACH}            AI 辅助长篇小说创作工具{R}")
    print(flush=True)
    logger.info("AFN (Agents for Novel) 启动中...")


class StartupProgress:
    """启动进度管理器 - AFN合体字Z轴旋转+星辰背景动画"""

    # 颜色定义
    R = "\033[0m"           # 重置
    BOLD = "\033[1m"        # 粗体
    DIM = "\033[2m"         # 暗淡

    # 彩虹色（从红到紫的渐变）
    RAINBOW = [
        "\033[38;5;196m",   # 红
        "\033[38;5;208m",   # 橙
        "\033[38;5;220m",   # 黄
        "\033[38;5;46m",    # 绿
        "\033[38;5;51m",    # 青
        "\033[38;5;21m",    # 蓝
        "\033[38;5;129m",   # 紫
    ]

    # 星星颜色（暗淡的白色和浅色）
    STAR_COLORS = [
        "\033[38;5;240m",   # 暗灰
        "\033[38;5;244m",   # 灰
        "\033[38;5;248m",   # 浅灰
        "\033[38;5;255m",   # 白
        "\033[38;5;229m",   # 浅黄
        "\033[38;5;153m",   # 浅蓝
    ]

    # 星星字符
    STAR_CHARS = ['.', '*', '+', '.', '.', '.']  # 多个点让星空更自然

    # 主题色（保留用于标题等）
    PINK_LIGHT = "\033[38;5;225m"
    PINK = "\033[38;5;218m"
    ROSE = "\033[38;5;204m"
    CORAL = "\033[38;5;210m"
    GOLD = "\033[38;5;220m"
    PEACH = "\033[38;5;223m"
    LAVENDER = "\033[38;5;183m"
    CYAN = "\033[38;5;159m"
    WHITE = "\033[38;5;255m"

    # 动画配置（从 AnimationConfig 读取）
    NUM_FRAMES = AnimationConfig.NUM_FRAMES
    FRAME_INTERVAL = AnimationConfig.FRAME_INTERVAL
    CANVAS_WIDTH = AnimationConfig.CANVAS_WIDTH
    CANVAS_HEIGHT = AnimationConfig.CANVAS_HEIGHT

    def __init__(self):
        self._current_stage_name = ""
        self._original_stdout = None
        # 循环动画相关
        self._animation_thread = None
        self._stop_animation = False
        self._animation_complete = False
        self._frame_idx = 0
        # 从文件加载Logo
        self._front_view, self._side_view = self._load_logo_from_file()
        # 动态生成旋转帧
        self._frames = self._generate_rotation_frames()
        # 生成随机星辰背景（每次启动不同）
        self._stars = self._generate_starfield()

    def _generate_starfield(self):
        """生成随机星辰背景"""
        stars = []
        # 生成随机数量的星星
        num_stars = random.randint(
            AnimationConfig.STAR_COUNT_MIN,
            AnimationConfig.STAR_COUNT_MAX
        )

        # 计算logo区域（避免星星覆盖logo）
        max_width = max(len(line) for line in self._front_view) if self._front_view else 40
        logo_start_col = (self.CANVAS_WIDTH - max_width) // 2
        logo_end_col = logo_start_col + max_width
        logo_start_row = AnimationConfig.LOGO_START_ROW
        logo_end_row = logo_start_row + len(self._front_view)

        for _ in range(num_stars):
            # 随机位置
            row = random.randint(0, self.CANVAS_HEIGHT - 1)
            col = random.randint(0, self.CANVAS_WIDTH - 1)

            # 检查是否在logo区域内，如果是则跳过
            if logo_start_row <= row < logo_end_row and logo_start_col <= col < logo_end_col:
                continue

            # 随机选择星星字符和颜色
            char = random.choice(self.STAR_CHARS)
            color = random.choice(self.STAR_COLORS)
            # 添加闪烁概率（某些星星会闪烁）
            twinkle = random.random() < AnimationConfig.STAR_TWINKLE_PROB

            stars.append({
                'row': row,
                'col': col,
                'char': char,
                'color': color,
                'twinkle': twinkle
            })

        return stars

    def _render_starfield(self, frame_idx=0):
        """渲染星辰背景到画布"""
        # 创建空画布
        canvas = [[' ' for _ in range(self.CANVAS_WIDTH)] for _ in range(self.CANVAS_HEIGHT)]
        color_map = [[None for _ in range(self.CANVAS_WIDTH)] for _ in range(self.CANVAS_HEIGHT)]

        for star in self._stars:
            row, col = star['row'], star['col']
            if 0 <= row < self.CANVAS_HEIGHT and 0 <= col < self.CANVAS_WIDTH:
                # 闪烁效果：某些星星在特定帧不显示
                if star['twinkle'] and (frame_idx + hash(f"{row}{col}")) % AnimationConfig.STAR_TWINKLE_CYCLE == 0:
                    continue
                canvas[row][col] = star['char']
                color_map[row][col] = star['color']

        return canvas, color_map

    def _load_logo_from_file(self):
        """从 logo.txt 加载正面和侧面视角

        文件格式：
        [FRONT_VIEW]
        （正面视角ASCII艺术）

        [SIDE_VIEW]
        （侧面视角ASCII艺术）
        """
        front_view = []
        side_view = []

        if not LOGO_FILE.exists():
            logger.warning(f"Logo文件不存在: {LOGO_FILE}，使用默认占位符")
            # 返回简单的占位符
            placeholder = ["  AFN  "] * 5
            return placeholder, placeholder

        try:
            with open(LOGO_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            current_section = None
            for line in content.split('\n'):
                stripped = line.strip()

                # 检测段落标记
                if stripped == '[FRONT_VIEW]':
                    current_section = 'front'
                    continue
                elif stripped == '[SIDE_VIEW]':
                    current_section = 'side'
                    continue
                elif stripped.startswith('[') and stripped.endswith(']'):
                    # 其他段落标记，忽略
                    current_section = None
                    continue

                # 跳过注释行
                if stripped.startswith('#'):
                    continue

                # 添加到对应段落（保留原始行，包括空格）
                if current_section == 'front':
                    front_view.append(line.rstrip())
                elif current_section == 'side':
                    side_view.append(line.rstrip())

            # 移除首尾空行
            while front_view and not front_view[0].strip():
                front_view.pop(0)
            while front_view and not front_view[-1].strip():
                front_view.pop()
            while side_view and not side_view[0].strip():
                side_view.pop(0)
            while side_view and not side_view[-1].strip():
                side_view.pop()

            # 将每行填充到相同宽度（确保绕中心轴旋转）
            if front_view:
                max_width = max(len(line) for line in front_view)
                front_view = [line.ljust(max_width) for line in front_view]
            if side_view:
                max_width = max(len(line) for line in side_view)
                side_view = [line.ljust(max_width) for line in side_view]

            if not front_view:
                logger.warning("Logo文件中没有找到 [FRONT_VIEW] 段落")
                front_view = ["  AFN  "] * 5
            if not side_view:
                logger.warning("Logo文件中没有找到 [SIDE_VIEW] 段落")
                side_view = ["  |  |  "] * len(front_view)

            logger.info(f"Logo加载成功: 正面{len(front_view)}行, 侧面{len(side_view)}行")
            return front_view, side_view

        except Exception as e:
            logger.error(f"加载Logo文件失败: {e}")
            placeholder = ["  AFN  "] * 5
            return placeholder, placeholder

    def _generate_rotation_frames(self):
        """动态生成旋转帧（使用3D投影公式）"""
        frames = []
        max_width = max(len(line) for line in self._front_view)
        side_max_width = max(len(line) for line in self._side_view)

        for i in range(self.NUM_FRAMES):
            angle = (i * 360) / self.NUM_FRAMES
            ratio = abs(math.cos(math.radians(angle)))
            side_threshold = AnimationConfig.SIDE_VIEW_THRESHOLD

            if ratio < side_threshold:
                # 侧视图模式
                side_ratio = 1.0 - (ratio / side_threshold)
                side_ratio = max(AnimationConfig.MIN_COMPRESS_RATIO, side_ratio)
                frame = []
                for line in self._side_view:
                    padded = line.ljust(side_max_width)
                    compressed = self._compress_line(padded, side_ratio)
                    frame.append(compressed)
                # 居中对齐
                frame_width = max(len(line) for line in frame) if frame else 0
                centered_frame = []
                for line in frame:
                    padding = (max_width - len(line)) // 2
                    centered_frame.append(' ' * padding + line)
                frames.append(centered_frame)
            else:
                # 正面视图模式
                ratio = max(AnimationConfig.MIN_COMPRESS_RATIO, ratio)
                frame = []
                for line in self._front_view:
                    padded = line.ljust(max_width)
                    compressed = self._compress_line(padded, ratio)
                    frame.append(compressed)
                # 居中对齐
                centered_frame = []
                for line in frame:
                    padding = (max_width - len(line)) // 2
                    centered_frame.append(' ' * padding + line)
                frames.append(centered_frame)

        return frames

    def _compress_line(self, line: str, ratio: float) -> str:
        """水平压缩一行文字（使用加权采样）"""
        if ratio >= AnimationConfig.FULL_RATIO_THRESHOLD:
            return line

        original_width = len(line)
        target_width = max(1, int(original_width * ratio))

        if target_width >= original_width:
            return line

        result = []
        for i in range(target_width):
            start = i * original_width / target_width
            end = (i + 1) * original_width / target_width
            best_char = ' '
            best_priority = -1

            for j in range(int(start), min(int(end) + 1, original_width)):
                char = line[j]
                if char in '/\\|_-':
                    priority = 3
                elif char.isalnum():
                    priority = 2
                elif char != ' ':
                    priority = 1
                else:
                    priority = 0

                if priority > best_priority:
                    best_priority = priority
                    best_char = char

            result.append(best_char)

        return ''.join(result)

    def _get_stdout(self):
        """获取原始 stdout"""
        if self._original_stdout is None:
            self._original_stdout = sys.__stdout__
        return self._original_stdout

    def start_loop_animation(self, stage_name: str = "启动中"):
        """启动循环动画（后台线程）"""
        self._current_stage_name = stage_name
        self._stop_animation = False
        self._animation_complete = False
        self._frame_idx = 0

        def animate():
            while True:
                self._draw_rotating_frame(self._frame_idx, self._current_stage_name)
                time.sleep(self.FRAME_INTERVAL)
                self._frame_idx = (self._frame_idx + 1) % self.NUM_FRAMES

                # 如果收到停止信号且刚好完成一轮，则退出
                if self._stop_animation and self._frame_idx == 0:
                    self._animation_complete = True
                    break

        self._animation_thread = threading.Thread(target=animate, daemon=True)
        self._animation_thread.start()

    def update_stage_name(self, stage_name: str):
        """更新当前阶段名称"""
        self._current_stage_name = stage_name

    def stop_loop_animation(self):
        """停止循环动画（等待当前循环完成）"""
        self._stop_animation = True

        if self._animation_thread:
            # 等待动画完成
            for _ in range(AnimationConfig.STOP_WAIT_ITERATIONS):
                if self._animation_complete:
                    break
                time.sleep(AnimationConfig.STOP_WAIT_INTERVAL)
            self._animation_thread = None

    def _draw_rotating_frame(self, frame_idx, stage_text):
        """绘制Z轴旋转帧（带星辰背景和彩虹色Logo）"""
        self.clear_screen()
        out = self._get_stdout()

        # 获取当前帧（使用动态生成的帧）
        current_frame = self._frames[frame_idx % len(self._frames)]

        # 渲染星辰背景
        canvas, star_colors = self._render_starfield(frame_idx)

        # 计算Logo居中位置
        max_width = max(len(line) for line in self._front_view)
        frame_width = max(len(line) for line in current_frame)
        logo_start_col = (self.CANVAS_WIDTH - max_width) // 2
        # 压缩帧需要额外的内部居中
        inner_padding = (max_width - frame_width) // 2
        logo_start_row = AnimationConfig.LOGO_START_ROW

        # 将Logo叠加到画布上
        for line_idx, line in enumerate(current_frame):
            row = logo_start_row + line_idx
            if row >= self.CANVAS_HEIGHT:
                break
            for char_idx, char in enumerate(line):
                col = logo_start_col + inner_padding + char_idx
                if col < self.CANVAS_WIDTH and char != ' ':
                    canvas[row][col] = char
                    # 使用彩虹色：根据行号选择颜色
                    color_idx = line_idx % len(self.RAINBOW)
                    star_colors[row][col] = self.RAINBOW[color_idx]

        # 输出画布
        for row_idx, row in enumerate(canvas):
            line_output = ""
            for col_idx, char in enumerate(row):
                color = star_colors[row_idx][col_idx]
                if color:
                    line_output += f"{color}{char}{self.R}"
                else:
                    line_output += char
            out.write(line_output + "\n")

        # 输出阶段信息
        hint_padding = (self.CANVAS_WIDTH - len(stage_text) - 8) // 2
        out.write(f"{' ' * hint_padding}{self.DIM}>>> {stage_text}...{self.R}\n")
        out.flush()

    def clear_screen(self):
        """清屏"""
        if sys.platform == 'win32':
            os.system('cls')
        else:
            os.system('clear')
        sys.stdout.write("\033[H")
        sys.stdout.flush()

    def complete_all(self):
        """全部完成 - 平滑展开到最终Logo"""
        # 播放展开动画（从压缩到完整）
        self._play_expand_animation()

        # 淡入装饰元素
        self._play_decoration_fade_in()

    def _play_expand_animation(self):
        """播放展开动画 - 从当前压缩状态平滑展开到完整logo（带星辰背景）"""
        out = self._get_stdout()

        # 展开动画参数
        total_frames = AnimationConfig.EXPAND_TOTAL_FRAMES
        # 从当前帧索引获取起始压缩比例
        start_ratio = abs(math.cos(math.radians((self._frame_idx * 360) / self.NUM_FRAMES)))
        start_ratio = max(AnimationConfig.MIN_COMPRESS_RATIO, start_ratio)

        max_width = max(len(line) for line in self._front_view)
        logo_start_col = (self.CANVAS_WIDTH - max_width) // 2
        logo_start_row = AnimationConfig.LOGO_START_ROW

        for frame in range(total_frames):
            self.clear_screen()

            # 使用缓动函数让展开更自然 (ease-out)
            t = frame / (total_frames - 1)
            eased_t = 1 - (1 - t) ** 3  # ease-out cubic

            # 从起始比例平滑过渡到1.0
            current_ratio = start_ratio + (1.0 - start_ratio) * eased_t

            # 渲染星辰背景
            canvas, color_map = self._render_starfield(frame)

            # 生成当前帧并叠加到画布
            for line_idx, line in enumerate(self._front_view):
                padded = line.ljust(max_width)
                if current_ratio < AnimationConfig.FULL_RATIO_THRESHOLD:
                    compressed = self._compress_line(padded, current_ratio)
                    inner_padding = (max_width - len(compressed)) // 2
                    content = compressed
                    col_offset = inner_padding
                else:
                    content = padded
                    col_offset = 0

                row = logo_start_row + line_idx
                if row >= self.CANVAS_HEIGHT:
                    break

                # 彩虹色：根据行号选择颜色
                rainbow_color = self.RAINBOW[line_idx % len(self.RAINBOW)]

                for char_idx, char in enumerate(content):
                    col = logo_start_col + col_offset + char_idx
                    if col < self.CANVAS_WIDTH and char != ' ':
                        canvas[row][col] = char
                        color_map[row][col] = rainbow_color

            # 输出画布
            for row_idx, row in enumerate(canvas):
                line_output = ""
                for col_idx, char in enumerate(row):
                    color = color_map[row_idx][col_idx]
                    if color:
                        line_output += f"{color}{char}{self.R}"
                    else:
                        line_output += char
                out.write(line_output + "\n")

            # 显示"完成"提示
            hint_text = ">>> 启动完成"
            hint_padding = (self.CANVAS_WIDTH - len(hint_text)) // 2
            out.write(f"{' ' * hint_padding}{self.DIM}{hint_text}{self.R}\n")
            out.flush()

            time.sleep(AnimationConfig.EXPAND_FRAME_INTERVAL)

    def _play_decoration_fade_in(self):
        """淡入标题（带星辰背景，无装饰线）"""
        out = self._get_stdout()

        # 标题
        title_line1 = "Agents for Novel  <3"
        title_line2 = "AI 辅助长篇小说创作工具"

        # 淡入帧数
        total_frames = AnimationConfig.FADE_IN_TOTAL_FRAMES

        max_width = max(len(line) for line in self._front_view)
        logo_start_col = (self.CANVAS_WIDTH - max_width) // 2
        logo_start_row = AnimationConfig.LOGO_START_ROW

        # 计算标题居中位置
        title1_padding = (self.CANVAS_WIDTH - len(title_line1)) // 2
        title2_padding = (self.CANVAS_WIDTH - len(title_line2)) // 2

        for frame in range(total_frames):
            self.clear_screen()

            # 计算淡入进度
            t = frame / (total_frames - 1)

            # 渲染星辰背景
            canvas, color_map = self._render_starfield(frame)

            # 将Logo叠加到画布（彩虹色）
            for line_idx, line in enumerate(self._front_view):
                row = logo_start_row + line_idx
                if row >= self.CANVAS_HEIGHT:
                    break
                rainbow_color = self.RAINBOW[line_idx % len(self.RAINBOW)]
                for char_idx, char in enumerate(line):
                    col = logo_start_col + char_idx
                    if col < self.CANVAS_WIDTH and char != ' ':
                        canvas[row][col] = char
                        color_map[row][col] = rainbow_color

            # 输出画布
            for row_idx, row in enumerate(canvas):
                line_output = ""
                for col_idx, char in enumerate(row):
                    color = color_map[row_idx][col_idx]
                    if color:
                        line_output += f"{color}{char}{self.R}"
                    else:
                        line_output += char
                out.write(line_output + "\n")

            # 标题（逐字显示）
            title_chars1 = int(len(title_line1) * t)
            title_chars2 = int(len(title_line2) * t)

            visible_title1 = title_line1[:title_chars1]
            visible_title2 = title_line2[:title_chars2]

            # 解析标题1中的<3并着色
            if "<3" in visible_title1:
                parts = visible_title1.split("<3")
                out.write(f"{' ' * title1_padding}{self.GOLD}{parts[0]}{self.ROSE}<3{self.R}\n")
            else:
                out.write(f"{' ' * title1_padding}{self.GOLD}{visible_title1}{self.R}\n")

            out.write(f"{' ' * title2_padding}{self.PEACH}{visible_title2}{self.R}\n")
            out.flush()
            time.sleep(AnimationConfig.FADE_IN_FRAME_INTERVAL)

        # 最后暂停一下让用户看清
        time.sleep(AnimationConfig.FADE_IN_FINAL_PAUSE)

    def _show_final_logo(self):
        """显示最终Logo - 星辰背景+彩虹色"""
        out = self._get_stdout()
        self.clear_screen()

        max_width = max(len(line) for line in self._front_view)
        logo_start_col = (self.CANVAS_WIDTH - max_width) // 2
        logo_start_row = AnimationConfig.LOGO_START_ROW

        # 标题
        title_line1 = "Agents for Novel  <3"
        title_line2 = "AI 辅助长篇小说创作工具"
        title1_padding = (self.CANVAS_WIDTH - len(title_line1)) // 2
        title2_padding = (self.CANVAS_WIDTH - len(title_line2)) // 2

        # 渲染星辰背景
        canvas, color_map = self._render_starfield(0)

        # 将Logo叠加到画布（彩虹色）
        for line_idx, line in enumerate(self._front_view):
            row = logo_start_row + line_idx
            if row >= self.CANVAS_HEIGHT:
                break
            rainbow_color = self.RAINBOW[line_idx % len(self.RAINBOW)]
            for char_idx, char in enumerate(line):
                col = logo_start_col + char_idx
                if col < self.CANVAS_WIDTH and char != ' ':
                    canvas[row][col] = char
                    color_map[row][col] = rainbow_color

        # 输出画布
        for row_idx, row in enumerate(canvas):
            line_output = ""
            for col_idx, char in enumerate(row):
                color = color_map[row_idx][col_idx]
                if color:
                    line_output += f"{color}{char}{self.R}"
                else:
                    line_output += char
            out.write(line_output + "\n")

        # 输出标题
        out.write(f"{' ' * title1_padding}{self.GOLD}Agents for Novel  {self.ROSE}<3{self.R}\n")
        out.write(f"{' ' * title2_padding}{self.PEACH}AI 辅助长篇小说创作工具{self.R}\n\n")
        out.flush()

    def show_error(self, message: str):
        """显示错误"""
        RED = "\033[38;5;203m"
        print(f"\n  {RED}[错误] {message}{self.R}\n")
        sys.stdout.flush()


# 全局进度实例
startup_progress = StartupProgress()
