"""
DPI感知和响应式布局工具

提供DPI缩放、响应式断点和动态尺寸计算功能
"""

from typing import Union, Tuple, Optional
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QScreen, QFont
import logging

logger = logging.getLogger(__name__)


class DPIHelper:
    """DPI感知助手类

    提供统一的DPI缩放和响应式布局支持
    """

    # 标准DPI（Windows默认）
    STANDARD_DPI = 96

    # 响应式断点（像素）
    BREAKPOINTS = {
        'xs': 576,   # 手机
        'sm': 768,   # 平板
        'md': 992,   # 小屏幕笔记本
        'lg': 1200,  # 桌面
        'xl': 1920,  # 大屏幕
        'xxl': 2560  # 4K屏幕
    }

    # 最小窗口尺寸（根据屏幕大小动态调整）
    MIN_WINDOW_SIZES = {
        'xs': (600, 400),
        'sm': (700, 500),
        'md': (800, 600),
        'lg': (900, 650),
        'xl': (1000, 700),
        'xxl': (1200, 800)
    }

    # 字体缩放比例
    FONT_SCALES = {
        'xs': 0.85,   # 小屏幕字体略小
        'sm': 0.9,
        'md': 1.0,    # 标准
        'lg': 1.0,
        'xl': 1.1,    # 大屏幕字体略大
        'xxl': 1.2    # 4K屏幕字体更大
    }

    def __init__(self):
        """初始化DPI助手"""
        self._screen: Optional[QScreen] = None
        self._dpi: float = self.STANDARD_DPI
        self._scale_factor: float = 1.0
        self._breakpoint: str = 'md'
        self.update_screen_info()

    def update_screen_info(self, widget: Optional[QWidget] = None):
        """更新屏幕信息

        Args:
            widget: 参考widget，用于获取所在屏幕
        """
        app = QApplication.instance()
        if not app:
            logger.warning("QApplication未初始化，使用默认DPI")
            return

        if widget and widget.window():
            # 获取widget所在屏幕
            self._screen = widget.window().screen()
        else:
            # 使用主屏幕
            self._screen = app.primaryScreen()

        if self._screen:
            # 获取逻辑DPI（考虑系统缩放）
            self._dpi = self._screen.logicalDotsPerInch()
            self._scale_factor = self._dpi / self.STANDARD_DPI

            # 获取屏幕尺寸确定断点
            size = self._screen.size()
            self._breakpoint = self.get_breakpoint(size.width())

            logger.info(f"屏幕信息更新 - DPI: {self._dpi:.1f}, "
                       f"缩放: {self._scale_factor:.2f}, "
                       f"断点: {self._breakpoint}, "
                       f"分辨率: {size.width()}x{size.height()}")

    @property
    def dpi(self) -> float:
        """获取当前DPI"""
        return self._dpi

    @property
    def scale_factor(self) -> float:
        """获取缩放因子"""
        return self._scale_factor

    @property
    def breakpoint(self) -> str:
        """获取当前响应式断点"""
        return self._breakpoint

    def get_breakpoint(self, width: int) -> str:
        """根据宽度获取响应式断点

        Args:
            width: 屏幕或窗口宽度（像素）

        Returns:
            断点名称（xs, sm, md, lg, xl, xxl）
        """
        if width < self.BREAKPOINTS['xs']:
            return 'xs'
        elif width < self.BREAKPOINTS['sm']:
            return 'sm'
        elif width < self.BREAKPOINTS['md']:
            return 'md'
        elif width < self.BREAKPOINTS['lg']:
            return 'lg'
        elif width < self.BREAKPOINTS['xl']:
            return 'xl'
        elif width < self.BREAKPOINTS['xxl']:
            return 'xxl'
        else:
            return 'xxl'

    def dp(self, pixels: Union[int, float]) -> int:
        """将像素值转换为DPI感知的设备像素

        Args:
            pixels: 原始像素值

        Returns:
            缩放后的像素值
        """
        return int(pixels * self._scale_factor)

    def sp(self, pixels: Union[int, float]) -> int:
        """将像素值转换为缩放像素（用于字体）

        考虑DPI和响应式断点的字体缩放

        Args:
            pixels: 原始像素值

        Returns:
            缩放后的像素值
        """
        font_scale = self.FONT_SCALES.get(self._breakpoint, 1.0)
        return int(pixels * self._scale_factor * font_scale)

    def size(self, width: Union[int, float], height: Union[int, float]) -> QSize:
        """创建DPI感知的QSize对象

        Args:
            width: 宽度（像素）
            height: 高度（像素）

        Returns:
            缩放后的QSize
        """
        return QSize(self.dp(width), self.dp(height))

    def min_window_size(self) -> Tuple[int, int]:
        """获取当前断点的最小窗口尺寸

        Returns:
            (宽度, 高度)元组
        """
        base_size = self.MIN_WINDOW_SIZES.get(self._breakpoint, (800, 600))
        return (self.dp(base_size[0]), self.dp(base_size[1]))

    def font(self, base_size: int, weight: Optional[int] = None) -> QFont:
        """创建DPI感知的字体

        Args:
            base_size: 基础字体大小（像素）
            weight: 字体粗细（可选）

        Returns:
            配置好的QFont对象
        """
        font = QFont()
        font.setPixelSize(self.sp(base_size))
        if weight:
            font.setWeight(weight)
        return font

    def responsive_value(self,
                        xs: Union[int, float] = None,
                        sm: Union[int, float] = None,
                        md: Union[int, float] = None,
                        lg: Union[int, float] = None,
                        xl: Union[int, float] = None,
                        xxl: Union[int, float] = None,
                        default: Union[int, float] = 0) -> int:
        """根据当前断点返回对应的值

        Args:
            xs-xxl: 各断点对应的值
            default: 默认值

        Returns:
            当前断点的值（经过DPI缩放）
        """
        values = {
            'xs': xs, 'sm': sm, 'md': md,
            'lg': lg, 'xl': xl, 'xxl': xxl
        }

        # 向下查找最近的定义值
        breakpoint_order = ['xs', 'sm', 'md', 'lg', 'xl', 'xxl']
        current_idx = breakpoint_order.index(self._breakpoint)

        for i in range(current_idx, -1, -1):
            bp = breakpoint_order[i]
            if values[bp] is not None:
                return self.dp(values[bp])

        return self.dp(default)

    def is_mobile(self) -> bool:
        """判断是否为移动设备尺寸"""
        return self._breakpoint in ('xs', 'sm')

    def is_tablet(self) -> bool:
        """判断是否为平板尺寸"""
        return self._breakpoint in ('sm', 'md')

    def is_desktop(self) -> bool:
        """判断是否为桌面尺寸"""
        return self._breakpoint in ('lg', 'xl', 'xxl')

    def is_high_dpi(self) -> bool:
        """判断是否为高DPI屏幕"""
        return self._scale_factor > 1.5

    def create_icon(self, svg_content: str, size: int = 24) -> 'QIcon':
        """
        从SVG字符串创建QIcon

        Args:
            svg_content: SVG内容字符串
            size: 图标基础大小（会自动根据DPI缩放）

        Returns:
            QIcon对象
        """
        from PyQt6.QtGui import QIcon, QPixmap, QPainter
        from PyQt6.QtCore import QByteArray, Qt
        from PyQt6.QtSvg import QSvgRenderer

        # 计算实际大小
        actual_size = self.dp(size)
        
        # 创建Pixmap
        pixmap = QPixmap(actual_size, actual_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # 渲染SVG
        svg_bytes = QByteArray(svg_content.encode('utf-8'))
        renderer = QSvgRenderer(svg_bytes)
        
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)


# 全局DPI助手实例
dpi_helper = DPIHelper()


def dp(pixels: Union[int, float]) -> int:
    """便捷函数：DPI感知像素

    Args:
        pixels: 原始像素值

    Returns:
        缩放后的像素值
    """
    return dpi_helper.dp(pixels)


def sp(pixels: Union[int, float]) -> int:
    """便捷函数：缩放像素（字体）

    Args:
        pixels: 原始像素值

    Returns:
        缩放后的像素值
    """
    return dpi_helper.sp(pixels)


def responsive(*args, **kwargs) -> int:
    """便捷函数：响应式值

    示例：
        width = responsive(xs=300, md=400, lg=500)
        padding = responsive(8, 12, 16, 20)  # xs, sm, md, lg

    Returns:
        当前断点的值
    """
    if args:
        # 位置参数模式
        breakpoints = ['xs', 'sm', 'md', 'lg', 'xl', 'xxl']
        kwargs = {}
        for i, value in enumerate(args[:len(breakpoints)]):
            kwargs[breakpoints[i]] = value

    return dpi_helper.responsive_value(**kwargs)