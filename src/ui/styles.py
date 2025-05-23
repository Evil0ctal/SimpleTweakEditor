# -*- coding: utf-8 -*-
"""
样式管理模块
负责管理应用程序的样式和主题
"""

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication as QApp
else:
    QApp = QApplication


class StyleManager:
    """样式管理器"""

    def __init__(self):
        self.app: Optional[QApp] = QApplication.instance()

    def is_dark_mode(self):
        """检测是否为暗色模式"""
        if self.app:
            palette = self.app.palette()
            window_color = palette.color(QPalette.ColorRole.Window)
            return window_color.lightness() < 128
        return False

    def get_text_color(self):
        """获取当前主题的文本颜色"""
        if self.app is not None:
            palette = self.app.palette()
            return palette.color(QPalette.ColorRole.WindowText)
        return QColor(0, 0, 0)

    def get_background_color(self):
        """获取当前主题的背景颜色"""
        if self.app is not None:
            palette = self.app.palette()
            return palette.color(QPalette.ColorRole.Window)
        return QColor(255, 255, 255)

    def get_drop_zone_style(self, active=False):
        """获取拖放区域样式"""
        is_dark = self.is_dark_mode()

        if active:
            # 激活状态 - 被拖拽悬停
            if is_dark:
                return """
                    QLabel {
                        background-color: #1a5276;
                        border: 2px dashed #3498db;
                        border-radius: 5px;
                        padding: 20px;
                        font-size: 14px;
                        color: #ffffff;
                    }
                """
            else:
                return """
                    QLabel {
                        background-color: #d6eaf8;
                        border: 2px dashed #3498db;
                        border-radius: 5px;
                        padding: 20px;
                        font-size: 14px;
                        color: #2c3e50;
                    }
                """
        else:
            # 普通状态
            if is_dark:
                return """
                    QLabel {
                        background-color: #2c3e50;
                        border: 2px dashed #7f8c8d;
                        border-radius: 5px;
                        padding: 20px;
                        font-size: 14px;
                        color: #ecf0f1;
                    }
                """
            else:
                return """
                    QLabel {
                        background-color: #f0f0f0;
                        border: 2px dashed #aaaaaa;
                        border-radius: 5px;
                        padding: 20px;
                        font-size: 14px;
                        color: #2c3e50;
                    }
                """

    def get_info_label_style(self):
        """获取信息标签样式"""
        is_dark = self.is_dark_mode()

        if is_dark:
            return """
                QLabel[infoLabel="true"] {
                    color: #3498db;
                    font-weight: bold;
                }
            """
        else:
            return """
                QLabel[infoLabel="true"] {
                    color: #2980b9;
                    font-weight: bold;
                }
            """

    def get_global_style(self):
        """获取全局样式表"""
        is_dark = self.is_dark_mode()

        if is_dark:
            return """
                QLabel[infoLabel="true"] {
                    color: #3498db;
                    font-weight: bold;
                }

                QTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555555;
                }

                QPlainTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #555555;
                }

                QLineEdit {
                    padding: 5px;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    background-color: #2d2d30;
                    color: #ffffff;
                }

                QPushButton {
                    padding: 8px 16px;
                    border-radius: 4px;
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                    color: #ffffff;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #777777;
                }

                QPushButton:pressed {
                    background-color: #2a2a2a;
                }

                QComboBox {
                    padding: 5px;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    background-color: #2d2d30;
                    color: #ffffff;
                }

                QComboBox::drop-down {
                    border: none;
                    background-color: #3c3c3c;
                }

                QComboBox::down-arrow {
                    border: none;
                    background-color: transparent;
                }

                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #ffffff;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }

                QStatusBar {
                    background-color: #2d2d30;
                    color: #ffffff;
                    border-top: 1px solid #555555;
                }

                QMenuBar {
                    background-color: #2d2d30;
                    color: #ffffff;
                }

                QMenuBar::item:selected {
                    background-color: #3c3c3c;
                }

                QMenu {
                    background-color: #2d2d30;
                    color: #ffffff;
                    border: 1px solid #555555;
                }

                QMenu::item:selected {
                    background-color: #3c3c3c;
                }
            """
        else:
            return """
                QLabel[infoLabel="true"] {
                    color: #2980b9;
                    font-weight: bold;
                }

                QTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }

                QPlainTextEdit {
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }

                QLineEdit {
                    padding: 5px;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    background-color: #ffffff;
                    color: #000000;
                }

                QPushButton {
                    padding: 8px 16px;
                    border-radius: 4px;
                    border: 1px solid #cccccc;
                    background-color: #f0f0f0;
                    color: #000000;
                    font-weight: bold;
                }

                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #999999;
                }

                QPushButton:pressed {
                    background-color: #d0d0d0;
                }

                QComboBox {
                    padding: 5px;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    background-color: #ffffff;
                    color: #000000;
                }

                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #000000;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """

    def get_log_colors(self):
        """获取日志颜色"""
        is_dark = self.is_dark_mode()

        if is_dark:
            return {
                "error": QColor(255, 102, 102),  # 亮红色
                "success": QColor(102, 255, 102),  # 亮绿色
                "info": QColor(102, 178, 255),  # 亮蓝色
                "warning": QColor(255, 204, 102),  # 亮橙色
                "normal": QColor(255, 255, 255)  # 白色
            }
        else:
            return {
                "error": QColor(220, 20, 60),  # 深红色
                "success": QColor(34, 139, 34),  # 深绿色
                "info": QColor(30, 144, 255),  # 深蓝色
                "warning": QColor(255, 140, 0),  # 橙色
                "normal": QColor(0, 0, 0)  # 黑色
            }

    def apply_global_style(self, widget):
        """应用全局样式到指定窗口部件"""
        if widget:
            widget.setStyleSheet(self.get_global_style())

    def update_drop_zone_style(self, drop_label, active=False):
        """更新拖放区域样式"""
        if drop_label:
            drop_label.setStyleSheet(self.get_drop_zone_style(active))

    def get_button_style(self, button_type="normal"):
        """获取特定类型按钮的样式"""
        is_dark = self.is_dark_mode()

        base_colors = {
            "primary": ("#3498db", "#2980b9", "#21618c"),
            "success": ("#27ae60", "#229954", "#1e8449"),
            "warning": ("#f39c12", "#e67e22", "#d35400"),
            "danger": ("#e74c3c", "#c0392b", "#a93226"),
        }

        if button_type in base_colors:
            normal, hover, pressed = base_colors[button_type]
            return f"""
                QPushButton {{
                    background-color: {normal};
                    color: white;
                    border: 1px solid {hover};
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {hover};
                }}
                QPushButton:pressed {{
                    background-color: {pressed};
                }}
            """

        # Normal button with theme support
        if is_dark:
            return """
                QPushButton {
                    background-color: #3c3c3c;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border-color: #777777;
                }
                QPushButton:pressed {
                    background-color: #2a2a2a;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #999999;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """
