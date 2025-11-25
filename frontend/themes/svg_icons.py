"""
SVG图标系统 - 提供优雅的矢量图标

替代emoji，提供专业的SVG图标
"""

from typing import Optional


class SVGIcons:
    """SVG图标库"""

    # ==================== 基础图标 ====================

    @staticmethod
    def sparkles(size: int = 24, color: str = "currentColor") -> str:
        """✨ 灵感/创意图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L13.09 8.26L19 9L13.09 9.74L12 16L10.91 9.74L5 9L10.91 8.26L12 2Z" fill="{color}" opacity="0.9"/>
            <path d="M6 4L6.45 6.22L8.5 6.5L6.45 6.78L6 9L5.55 6.78L3.5 6.5L5.55 6.22L6 4Z" fill="{color}" opacity="0.7"/>
            <path d="M18 14L18.45 16.22L20.5 16.5L18.45 16.78L18 19L17.55 16.78L15.5 16.5L17.55 16.22L18 14Z" fill="{color}" opacity="0.7"/>
        </svg>"""

    @staticmethod
    def book(size: int = 24, color: str = "currentColor") -> str:
        """📖 书籍/小说图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 19.5C4 18.837 4.26339 18.2011 4.73223 17.7322C5.20108 17.2634 5.83696 17 6.5 17H20" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6.5 2H20V22H6.5C5.83696 22 5.20108 21.7366 4.73223 21.2678C4.26339 20.7989 4 20.163 4 19.5V4.5C4 3.83696 4.26339 3.20108 4.73223 2.73223C5.20108 2.26339 5.83696 2 6.5 2Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M8 7H16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <path d="M8 11H16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>"""

    @staticmethod
    def pen(size: int = 24, color: str = "currentColor") -> str:
        """✏️ 写作/编辑图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 20H21" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16.5 3.5C17.0304 2.96957 17.7348 2.67 18.5 2.67C19.2652 2.67 19.9696 2.96957 20.5 3.5C21.0304 4.03043 21.33 4.73478 21.33 5.5C21.33 6.26522 21.0304 6.96957 20.5 7.5L7 21L3 22L4 18L16.5 3.5Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M15 5L19 9" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def settings(size: int = 24, color: str = "currentColor") -> str:
        """⚙️ 设置图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 1V6M12 18V23" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M4.22 4.22L7.76 7.76M16.24 16.24L19.78 19.78" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M1 12H6M18 12H23" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M4.22 19.78L7.76 16.24M16.24 7.76L19.78 4.22" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def moon(size: int = 24, color: str = "currentColor") -> str:
        """🌙 月亮/深色模式图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 12.79C20.8427 14.4922 20.2039 16.1144 19.1582 17.4668C18.1126 18.8192 16.7035 19.8458 15.0957 20.4265C13.4879 21.0073 11.748 21.1181 10.0795 20.7461C8.41101 20.3741 6.88301 19.5345 5.67423 18.3258C4.46545 17.117 3.62594 15.589 3.25393 13.9205C2.88192 12.252 2.99273 10.5121 3.57348 8.9043C4.15423 7.29651 5.18077 5.88737 6.53321 4.84175C7.88564 3.79614 9.50779 3.15731 11.21 3C10.2134 4.34827 9.73387 6.00945 9.85853 7.68141C9.98319 9.35338 10.7038 10.9251 11.8893 12.1107C13.0749 13.2962 14.6466 14.0168 16.3186 14.1415C17.9906 14.2661 19.6517 13.7866 21 12.79Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="{color}" opacity="0.1"/>
        </svg>"""

    @staticmethod
    def sun(size: int = 24, color: str = "currentColor") -> str:
        """☀️ 太阳/亮色模式图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="{color}" opacity="0.2"/>
            <line x1="12" y1="1" x2="12" y2="3" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="12" y1="21" x2="12" y2="23" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="1" y1="12" x2="3" y2="12" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="21" y1="12" x2="23" y2="12" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>"""

    @staticmethod
    def close(size: int = 24, color: str = "currentColor") -> str:
        """❌ 关闭图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6 6L18 18" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def arrow_left(size: int = 24, color: str = "currentColor") -> str:
        """← 返回箭头"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 12H5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M12 19L5 12L12 5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def check(size: int = 24, color: str = "currentColor") -> str:
        """✓ 勾选图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polyline points="20 6 9 17 4 12" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def plus(size: int = 24, color: str = "currentColor") -> str:
        """+ 添加图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="12" y1="5" x2="12" y2="19" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="5" y1="12" x2="19" y2="12" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def save(size: int = 24, color: str = "currentColor") -> str:
        """💾 保存图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H16L21 8V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M17 21V13H7V21" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 3V8H15" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def home(size: int = 24, color: str = "currentColor") -> str:
        """🏠 主页图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 9L12 2L21 9V20C21 20.5304 20.7893 21.0391 20.4142 21.4142C20.0391 21.7893 19.5304 22 19 22H5C4.46957 22 3.96086 21.7893 3.58579 21.4142C3.21071 21.0391 3 20.5304 3 20V9Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M9 22V12H15V22" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def refresh(size: int = 24, color: str = "currentColor") -> str:
        """🔄 刷新图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21.5 2V8H15.5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2.5 22V16H8.5" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M21.34 9C20.74 6.64 19.26 4.59 17.18 3.28C15.1 1.97 12.58 1.52 9.67 2.03C6.76 2.54 4.15 3.96 2.32 6.01" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2.66 15C3.26 17.36 4.74 19.41 6.82 20.72C8.9 22.03 11.42 22.48 14.33 21.97C17.24 21.46 19.85 20.04 21.68 17.99" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    # ==================== 动画加载图标 ====================

    @staticmethod
    def loading_spinner(size: int = 24, color: str = "currentColor") -> str:
        """加载动画图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="animate-spin">
            <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="2" stroke-dasharray="31.4" stroke-dashoffset="10" stroke-linecap="round" opacity="0.25"/>
            <path d="M12 2C6.48 2 2 6.48 2 12" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>"""

    @staticmethod
    def loading_dots(size: int = 24, color: str = "currentColor") -> str:
        """点状加载动画"""
        return f"""<svg width="{size*3}" height="{size}" viewBox="0 0 72 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="6" fill="{color}" opacity="0.3">
                <animate attributeName="opacity" values="0.3;1;0.3" dur="1.2s" repeatCount="indefinite" begin="0s"/>
            </circle>
            <circle cx="36" cy="12" r="6" fill="{color}" opacity="0.3">
                <animate attributeName="opacity" values="0.3;1;0.3" dur="1.2s" repeatCount="indefinite" begin="0.4s"/>
            </circle>
            <circle cx="60" cy="12" r="6" fill="{color}" opacity="0.3">
                <animate attributeName="opacity" values="0.3;1;0.3" dur="1.2s" repeatCount="indefinite" begin="0.8s"/>
            </circle>
        </svg>"""

    # ==================== 状态图标 ====================

    @staticmethod
    def success(size: int = 24, color: str = "#10B981") -> str:
        """成功状态图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="2" fill="{color}" opacity="0.1"/>
            <path d="M8 12L11 15L16 9" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>"""

    @staticmethod
    def error(size: int = 24, color: str = "#EF4444") -> str:
        """错误状态图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="2" fill="{color}" opacity="0.1"/>
            <line x1="15" y1="9" x2="9" y2="15" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <line x1="9" y1="9" x2="15" y2="15" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>"""

    @staticmethod
    def warning(size: int = 24, color: str = "#F59E0B") -> str:
        """警告状态图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10.29 3.86L1.82 18C1.64 18.34 1.54 18.72 1.54 19.11C1.54 20.15 2.39 21 3.43 21H20.57C20.96 21 21.34 20.9 21.68 20.72C22.65 20.23 23.03 19.03 22.54 18.06L14.07 3.86C13.89 3.52 13.62 3.24 13.29 3.05C12.32 2.56 11.12 2.94 10.63 3.91L10.29 3.86Z" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="{color}" opacity="0.1"/>
            <line x1="12" y1="9" x2="12" y2="13" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="17" r="1" fill="{color}"/>
        </svg>"""

    @staticmethod
    def info(size: int = 24, color: str = "#3B82F6") -> str:
        """信息状态图标"""
        return f"""<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="2" fill="{color}" opacity="0.1"/>
            <line x1="12" y1="16" x2="12" y2="12" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
            <circle cx="12" cy="8" r="1" fill="{color}"/>
        </svg>"""


class SVGIconWidget:
    """
    SVG图标PyQt组件包装器

    用法：
        icon_widget = SVGIconWidget(SVGIcons.sparkles(24, "#4A90E2"))
        layout.addWidget(icon_widget)
    """

    @staticmethod
    def create_icon_label(svg_content: str) -> 'QLabel':
        """
        创建包含SVG图标的QLabel

        Args:
            svg_content: SVG内容字符串

        Returns:
            QLabel组件
        """
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt

        label = QLabel()
        label.setText(svg_content)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def create_icon_pixmap(svg_content: str, size: int = 24) -> 'QPixmap':
        """
        创建SVG图标的QPixmap

        Args:
            svg_content: SVG内容字符串
            size: 图标大小

        Returns:
            QPixmap对象
        """
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import QByteArray
        from PyQt6.QtSvgWidgets import QSvgWidget

        # 将SVG字符串转换为字节数组
        svg_bytes = QByteArray(svg_content.encode('utf-8'))

        # 创建Pixmap
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # 使用SVG渲染器绘制到Pixmap
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPainter

        renderer = QSvgRenderer(svg_bytes)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return pixmap


# 导出便捷函数
def icon(name: str, size: int = 24, color: str = "currentColor") -> str:
    """
    获取SVG图标

    Args:
        name: 图标名称
        size: 图标大小
        color: 图标颜色

    Returns:
        SVG字符串
    """
    icon_map = {
        "sparkles": SVGIcons.sparkles,
        "book": SVGIcons.book,
        "pen": SVGIcons.pen,
        "settings": SVGIcons.settings,
        "moon": SVGIcons.moon,
        "sun": SVGIcons.sun,
        "close": SVGIcons.close,
        "arrow_left": SVGIcons.arrow_left,
        "check": SVGIcons.check,
        "plus": SVGIcons.plus,
        "save": SVGIcons.save,
        "home": SVGIcons.home,
        "refresh": SVGIcons.refresh,
        "loading": SVGIcons.loading_spinner,
        "loading_dots": SVGIcons.loading_dots,
        "success": SVGIcons.success,
        "error": SVGIcons.error,
        "warning": SVGIcons.warning,
        "info": SVGIcons.info,
    }

    icon_func = icon_map.get(name)
    if icon_func:
        return icon_func(size, color)
    return ""