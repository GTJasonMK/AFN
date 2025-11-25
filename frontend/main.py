"""
主程序入口 - 完全按照Web应用重建

对应Web应用：frontend/src/main.ts

启动 Arboris Novel 桌面版（1:1照抄Web应用）
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from windows.main_window import MainWindow
from themes.theme_manager import theme_manager
from themes.accessibility import AccessibilityTheme
from utils.config_manager import ConfigManager


def apply_global_theme():
    """应用全局主题样式（动态响应主题切换）"""
    app = QApplication.instance()
    if not app:
        return

    # 根据当前主题动态设置全局样式
    is_dark = theme_manager.is_dark_mode()

    # 系统对话框背景色
    dialog_bg = theme_manager.BG_CARD
    dialog_text = theme_manager.TEXT_PRIMARY
    input_bg = theme_manager.BG_PRIMARY
    input_border = theme_manager.BORDER_DEFAULT

    base_style = f"""
        QMessageBox {{
            background-color: {dialog_bg};
            color: {dialog_text};
        }}
        QMessageBox QLabel {{
            color: {dialog_text};
            font-size: 14px;
            background-color: transparent;
        }}
        QMessageBox QTextEdit {{
            color: {dialog_text};
            background-color: {input_bg};
            border: 1px solid {input_border};
        }}
        QMessageBox QPushButton,
        QDialogButtonBox QPushButton {{
            background-color: {theme_manager.PRIMARY};
            color: {theme_manager.BUTTON_TEXT};
            border: none;
            border-radius: {theme_manager.RADIUS_SM};
            padding: 8px 20px;
            font-size: 14px;
            font-weight: 500;
            min-width: 70px;
        }}
        QMessageBox QPushButton:hover,
        QDialogButtonBox QPushButton:hover {{
            background-color: {theme_manager.PRIMARY_LIGHT};
        }}
        QMessageBox QPushButton:pressed,
        QDialogButtonBox QPushButton:pressed {{
            background-color: {theme_manager.PRIMARY_DARK};
        }}
        QMessageBox QPushButton:default,
        QDialogButtonBox QPushButton:default {{
            background-color: {theme_manager.PRIMARY};
            font-weight: 600;
        }}
        QInputDialog {{
            background-color: {dialog_bg};
            color: {dialog_text};
        }}
        QInputDialog QLabel {{
            color: {dialog_text};
            font-size: 14px;
            background-color: transparent;
        }}
        QInputDialog QLineEdit {{
            color: {dialog_text};
            background-color: {input_bg};
            border: 1px solid {input_border};
            border-radius: {theme_manager.RADIUS_SM};
            padding: 8px;
        }}
        QInputDialog QTextEdit {{
            color: {dialog_text};
            background-color: {input_bg};
            border: 1px solid {input_border};
        }}
        QInputDialog QPushButton,
        QInputDialog QDialogButtonBox QPushButton {{
            background-color: {theme_manager.PRIMARY};
            color: {theme_manager.BUTTON_TEXT};
            border: none;
            border-radius: {theme_manager.RADIUS_SM};
            padding: 8px 20px;
            font-size: 14px;
            font-weight: 500;
            min-width: 70px;
        }}
    """

    # 添加可访问性增强样式
    accessibility_style = AccessibilityTheme.get_all_accessibility_styles()

    # 应用合并样式
    app.setStyleSheet(base_style + "\n" + accessibility_style)


def main():
    """主函数"""
    # 配置日志系统 - 输出到控制台
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Arboris Novel 前端应用启动")
    logger.info("=" * 80)

    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("Arboris Novel")
    app.setOrganizationName("Arboris")

    # 初始化配置管理器
    config_manager = ConfigManager()

    # 设置主题管理器的配置管理器
    theme_manager.set_config_manager(config_manager)

    # 从配置文件加载主题
    theme_manager.load_theme_from_config()

    # 连接主题切换信号，实时更新全局样式
    theme_manager.theme_changed.connect(lambda: apply_global_theme())

    # 应用初始全局主题样式
    apply_global_theme()

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
