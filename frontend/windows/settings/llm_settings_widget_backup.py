"""
LLM配置管理主Widget
"""

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFileDialog, QMessageBox, QDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from api.client import ArborisAPIClient
from themes.theme_manager import theme_manager
from themes.svg_icons import SVGIcons
from utils.dpi_utils import dpi_helper, dp, sp
from .config_dialog import LLMConfigDialog
from .test_result_dialog import TestResultDialog
import json


class LLMSettingsWidget(QWidget):
    """LLM配置管理组件 - 禅意风格（对应LLMSettings.vue）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = ArborisAPIClient()
        self.configs = []
        self.testing_config_id = None
        self.setupUI()
        self.loadConfigs()

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        # 顶部：标题和操作按钮（简单卡片）
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(20)}px;
            }}
        """)
        header_layout = QHBoxLayout(header)

        # 标题
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(dp(4))

        title = QLabel("LLM 配置管理")
        title.setStyleSheet(f"""
            font-size: {sp(20)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("管理您的 AI 模型配置，支持多个配置切换")
        subtitle.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            opacity: 0.8;
        """)
        title_layout.addWidget(subtitle)

        header_layout.addWidget(title_widget, stretch=1)

        # 按钮组（渐变背景和现代效果）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))

        # 导入按钮（简单样式）
        import_btn = QPushButton("导入配置")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.SUCCESS};
            }}
        """)
        import_btn.clicked.connect(self.importConfigs)
        btn_layout.addWidget(import_btn)

        # 导出按钮（简单样式）
        export_all_btn = QPushButton("导出所有")
        export_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.INFO};
            }}
        """)
        export_all_btn.clicked.connect(self.exportAll)
        btn_layout.addWidget(export_all_btn)

        # 新增配置按钮（主按钮渐变）
        create_btn = QPushButton("新增配置")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(8)}px;
                padding: {dp(12)}px {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
                min-height: {dp(40)}px;
                min-width: {dp(120)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)
        create_btn.clicked.connect(self.createConfig)
        btn_layout.addWidget(create_btn)

        header_layout.addLayout(btn_layout)

        layout.addWidget(header)

        # 配置说明（简单的提示栏）
        info = QFrame()
        info.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: {dp(12)}px;
            }}
        """)
        info_layout = QHBoxLayout(info)
        info_layout.setSpacing(dp(12))

        # 简化为一行提示（普通文字颜色）
        tip_label = QLabel("可创建多个配置并切换 • 点击测试验证连接 • 激活的配置不可删除")
        tip_label.setWordWrap(False)
        tip_label.setStyleSheet(f"""
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)
        info_layout.addWidget(tip_label)

        layout.addWidget(info)

        # 配置列表（滚动区域）- 增加最小高度确保可见
        self.config_scroll = QScrollArea()
        self.config_scroll.setWidgetResizable(True)
        self.config_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.config_scroll.setMinimumHeight(dp(400))  # 设置最小高度
        self.config_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        self.config_container = QWidget()
        self.config_layout = QVBoxLayout(self.config_container)
        self.config_layout.setSpacing(16)
        self.config_layout.addStretch()

        self.config_scroll.setWidget(self.config_container)
        layout.addWidget(self.config_scroll, stretch=1)

    def loadConfigs(self):
        """加载配置列表"""
        try:
            self.configs = self.api_client.get_llm_configs()
            self.renderConfigs()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载配置失败：{str(e)}")

    def renderConfigs(self):
        """渲染配置列表"""
        # 清空现有卡片
        while self.config_layout.count() > 1:
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.configs:
            # 空状态
            empty = QLabel("您还没有配置 LLM，点击上方 \"新增配置\" 按钮创建")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"font-size: 14px; color: {theme_manager.TEXT_SECONDARY}; padding: 60px;")
            self.config_layout.insertWidget(0, empty)
        else:
            for config in self.configs:
                card = self.createConfigCard(config)
                self.config_layout.insertWidget(self.config_layout.count() - 1, card)

    def createConfigCard(self, config):
        """创建配置卡片 - 极简设计"""
        card = QFrame()
        is_active = config.get('is_active', False)

        # 使用简单的边框区分激活状态
        if is_active:
            # 激活状态使用主色边框
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme_manager.BG_CARD};
                    border: 2px solid {theme_manager.PRIMARY};
                    border-radius: {dp(8)}px;
                    padding: {dp(20)}px;
                }}
            """)
        else:
            # 非激活状态使用普通边框
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(8)}px;
                    padding: {dp(20)}px;
                }}
            """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(dp(20))

        # 标题行
        header = QHBoxLayout()

        # 名称和标签
        name_widget = QWidget()
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(dp(12))

        name = QLabel(config.get('config_name', ''))
        name.setStyleSheet(f"""
            font-size: {sp(18)}px;
            font-weight: 700;
            color: {theme_manager.TEXT_PRIMARY};
            letter-spacing: 0.02em;
        """)
        name_layout.addWidget(name)

        if is_active:
            active_badge = QLabel("当前激活")
            active_badge.setStyleSheet(f"""
                background-color: {theme_manager.SUCCESS};
                color: white;
                padding: {dp(4)}px {dp(10)}px;
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
                font-weight: 600;
            """)
            name_layout.addWidget(active_badge)

        name_layout.addStretch()

        header.addWidget(name_widget, stretch=1)
        card_layout.addLayout(header)

        # 配置信息（增大字体）
        info_layout = QVBoxLayout()
        info_layout.setSpacing(dp(8))

        # 使用SVG图标美化信息展示
        url = config.get('llm_provider_url', '(默认)')
        url_label = QLabel(f"API URL: {url}")
        url_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding-left: {dp(4)}px;
        """)
        info_layout.addWidget(url_label)

        key_masked = config.get('llm_provider_api_key_masked', '(未设置)')
        key_label = QLabel(f"API Key: {key_masked}")
        key_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding-left: {dp(4)}px;
        """)
        info_layout.addWidget(key_label)

        model = config.get('llm_provider_model', '(默认)')
        model_label = QLabel(f"模型: {model}")
        model_label.setStyleSheet(f"""
            font-size: {sp(14)}px;
            color: {theme_manager.TEXT_SECONDARY};
            padding-left: {dp(4)}px;
        """)
        info_layout.addWidget(model_label)

        card_layout.addLayout(info_layout)

        # 操作按钮（现代渐变设计）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))

        config_id = config.get('id')

        # 测试按钮（简单样式）
        test_btn = QPushButton("测试中..." if self.testing_config_id == config_id else "测试连接")
        test_btn.setEnabled(self.testing_config_id != config_id)
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor if test_btn.isEnabled() else Qt.CursorShape.WaitCursor)
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.INFO};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.INFO_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """)
        test_btn.clicked.connect(lambda: self.testConfig(config))
        btn_layout.addWidget(test_btn)

        # 激活按钮（简单样式）
        if not is_active:
            activate_btn = QPushButton("激活配置")
            activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            activate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.SUCCESS};
                    color: white;
                    border: none;
                    border-radius: {dp(6)}px;
                    padding: {dp(10)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 500;
                    min-height: {dp(32)}px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.SUCCESS_DARK};
                }}
            """)
            activate_btn.clicked.connect(lambda: self.activateConfig(config))
            btn_layout.addWidget(activate_btn)

        # 编辑按钮（简单样式）
        edit_btn = QPushButton("编辑")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.editConfig(config))
        btn_layout.addWidget(edit_btn)

        # 导出按钮（简单样式）
        export_btn = QPushButton("导出")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.WARNING};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.WARNING_DARK};
            }}
        """)
        export_btn.clicked.connect(lambda: self.exportConfig(config))
        btn_layout.addWidget(export_btn)

        # 删除按钮（简单样式）
        delete_btn = QPushButton("删除")
        delete_btn.setEnabled(not is_active)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor if not is_active else Qt.CursorShape.ForbiddenCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme_manager.ERROR};
                color: white;
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(10)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
                min-height: {dp(32)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.ERROR_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
            }}
        """)
        if not is_active:
            delete_btn.clicked.connect(lambda: self.deleteConfig(config))
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        card_layout.addLayout(btn_layout)

        return card

    def createConfig(self):
        """创建配置"""
        dialog = LLMConfigDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                QMessageBox.warning(self, "提示", "配置名称不能为空")
                return

            try:
                self.api_client.create_llm_config(data)
                QMessageBox.information(self, "成功", "配置创建成功")
                self.loadConfigs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败：{str(e)}")

    def editConfig(self, config):
        """编辑配置"""
        dialog = LLMConfigDialog(config=config, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                QMessageBox.warning(self, "提示", "配置名称不能为空")
                return

            try:
                self.api_client.update_llm_config(config['id'], data)
                QMessageBox.information(self, "成功", "配置更新成功")
                self.loadConfigs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def activateConfig(self, config):
        """激活配置"""
        try:
            self.api_client.activate_llm_config(config['id'])
            QMessageBox.information(self, "成功", f"已激活配置：{config['config_name']}")
            self.loadConfigs()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"激活失败：{str(e)}")

    def deleteConfig(self, config):
        """删除配置"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除配置 \"{config['config_name']}\" 吗？此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.api_client.delete_llm_config(config['id'])
                QMessageBox.information(self, "成功", "配置已删除")
                self.loadConfigs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")

    def testConfig(self, config):
        """测试配置"""
        self.testing_config_id = config['id']
        self.renderConfigs()

        try:
            # 调用API测试连接
            result = self.api_client.test_llm_config(config['id'])

            # 解析测试结果
            success = result.get('success', False)
            message = result.get('message', '')
            details = result.get('details', {})

            # 显示测试结果对话框
            dialog = TestResultDialog(success, message, details, parent=self)
            dialog.exec()

        except Exception as e:
            # 测试失败
            TestResultDialog(False, f"连接失败：{str(e)}", parent=self).exec()

        finally:
            self.testing_config_id = None
            self.renderConfigs()

    def exportConfig(self, config):
        """导出单个配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            f"{config['config_name']}.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                # 调用后端导出API，返回LLMConfigExportData格式
                export_data = self.api_client.export_llm_config(config['id'])

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(self, "成功", f"已导出到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

    def exportAll(self):
        """导出所有配置"""
        if not self.configs:
            QMessageBox.warning(self, "提示", "没有可导出的配置")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出所有配置",
            "llm_configs.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                # 后端返回 LLMConfigExportData 格式
                export_data = self.api_client.export_llm_configs()

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                # 显示导出的配置数量
                config_count = len(export_data.get('configs', []))
                QMessageBox.information(self, "成功", f"已导出 {config_count} 个配置到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：{str(e)}")

    def importConfigs(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            "",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                # 验证导入数据格式
                # 后端期望接收 LLMConfigExportData 格式：
                # {"version": "1.0", "export_time": "...", "export_type": "...", "configs": [...]}
                if not isinstance(import_data, dict):
                    QMessageBox.warning(self, "格式错误", "导入文件格式不正确，应为JSON对象")
                    return

                if 'configs' not in import_data:
                    QMessageBox.warning(self, "格式错误", "导入文件缺少 'configs' 字段")
                    return

                result = self.api_client.import_llm_configs(import_data)

                QMessageBox.information(self, "成功", f"成功导入配置")
                self.loadConfigs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")


