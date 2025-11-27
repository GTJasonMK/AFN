"""
主程序入口 - 完全按照Web应用重建

对应Web应用：frontend/src/main.ts

启动 Arboris Novel 桌面版（1:1照抄Web应用）
"""

import sys
import logging
import traceback
import faulthandler
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 启用faulthandler来捕获段错误（C层面的崩溃）
# 这会在发生段错误时打印Python调用栈
faulthandler.enable(file=sys.stderr, all_threads=True)

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from windows.main_window import MainWindow
from themes.theme_manager import theme_manager
from themes.accessibility import AccessibilityTheme
from utils.config_manager import ConfigManager


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理器 - 捕获未处理的异常并记录"""
    logger = logging.getLogger(__name__)

    # 忽略KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 记录异常详情
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"未捕获的异常导致程序崩溃:\n{error_msg}")

    # 尝试显示错误对话框（如果Qt应用还在运行）
    try:
        app = QApplication.instance()
        if app:
            from PyQt6.QtWidgets import QMessageBox
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("程序错误")
            msg_box.setText("程序发生未处理的错误，即将退出。")
            msg_box.setDetailedText(error_msg)
            msg_box.exec()
    except Exception:
        pass  # 如果无法显示对话框，至少日志已经记录了

    # 调用默认异常处理
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


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
    # 配置日志系统 - 同时输出到控制台和文件
    log_file = Path(__file__).parent / "frontend_debug.log"
    logging.basicConfig(
        level=logging.DEBUG,  # 使用DEBUG级别获取更多信息
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8', mode='a')
        ]
    )
    logger = logging.getLogger(__name__)

    # 强制刷新日志
    for handler in logging.root.handlers:
        handler.flush()

    # 安装全局异常处理器
    sys.excepthook = global_exception_handler

    logger.info("=" * 80)
    logger.info("Arboris Novel 前端应用启动")
    logger.info("Python版本: %s", sys.version)
    logger.info("日志文件: %s", log_file)
    logger.info("faulthandler已启用，段错误将被捕获")
    logger.info("=" * 80)

    # 强制刷新
    sys.stdout.flush()
    for handler in logging.root.handlers:
        handler.flush()

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
