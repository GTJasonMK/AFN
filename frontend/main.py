"""
主程序入口 - 完全按照Web应用重建

对应Web应用：frontend/src/main.ts

启动 AFN (Agents for Novel) 桌面版
"""

import sys
import logging
import traceback
import faulthandler
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtCore import Qt

# 启用faulthandler来捕获段错误（C层面的崩溃）
# 这会在发生段错误时打印Python调用栈
faulthandler.enable(file=sys.stderr, all_threads=True)

# 注意：不在此处初始化COM
# - 主线程：让Qt通过OleInitialize自动初始化（STA模式）
# - 工作线程：在sse_worker.py中使用MTA模式初始化
# 这样可以避免COM线程模式冲突（0x80010106错误）

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
    except (RuntimeError, ImportError) as dialog_error:
        # Qt 运行时错误或导入错误，无法显示对话框
        logger.warning("无法显示错误对话框: %s", type(dialog_error).__name__)

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


def load_active_theme_config(logger):
    """尝试从后端加载激活的主题配置

    在后端可用时，加载用户激活的主题配置并应用。
    支持V1和V2两种配置格式，优先使用V2。
    如果后端不可用或没有激活的配置，则使用默认主题。
    """
    try:
        from api.manager import APIClientManager

        # 获取当前主题模式
        mode = theme_manager.current_mode.value  # "light" 或 "dark"

        # 尝试获取激活的统一格式主题配置（支持V1和V2）
        api_client = APIClientManager.get_client()
        active_config = api_client.get_active_unified_theme_config(mode)

        if active_config:
            config_version = active_config.get('config_version', 1)
            config_name = active_config.get('config_name', '未命名')
            logger.info(f"加载激活的主题配置: {config_name} (V{config_version})")

            if config_version == 2 and active_config.get('effects'):
                # V2配置：使用面向组件的配置
                theme_manager.apply_v2_config(active_config)
            elif any(active_config.get(k) for k in ['primary_colors', 'text_colors', 'background_colors']):
                # V1配置：合并为平面字典
                flat_config = {}
                v1_groups = [
                    'primary_colors', 'accent_colors', 'semantic_colors',
                    'text_colors', 'background_colors', 'border_effects',
                    'button_colors', 'typography', 'border_radius',
                    'spacing', 'animation', 'button_sizes'
                ]
                for group in v1_groups:
                    group_values = active_config.get(group, {}) or {}
                    flat_config.update(group_values)
                if flat_config:
                    theme_manager.apply_custom_theme(flat_config)
            else:
                logger.info(f"配置 {config_name} 没有有效的配置数据，使用默认主题")
        else:
            logger.info(f"没有激活的{mode}主题配置，使用默认主题")

    except Exception as e:
        # 后端不可用或其他错误，使用默认主题
        logger.warning(f"无法加载激活的主题配置（后端可能未启动）: {e}")


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
    logger.info("AFN (Agents for Novel) 前端应用启动")
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
    app.setApplicationName("AFN")
    app.setOrganizationName("AFN")

    # 设置 Fusion 样式 - 确保 QSS 样式表在 Windows 上正确工作
    # Windows 原生样式会覆盖 QSS 边框设置，Fusion 样式提供一致的跨平台行为
    app.setStyle(QStyleFactory.create('Fusion'))

    # 初始化配置管理器
    config_manager = ConfigManager()

    # 设置主题管理器的配置管理器
    theme_manager.set_config_manager(config_manager)

    # 从配置文件加载主题模式（light/dark）
    theme_manager.load_theme_from_config()

    # 尝试从后端加载激活的主题配置（V2）
    load_active_theme_config(logger)

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
