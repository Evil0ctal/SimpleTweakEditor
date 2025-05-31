# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-26
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 关于对话框
支持暗色模式的交互式关于信息展示，包含版本信息和项目链接

英文介绍:
SimpleTweakEditor About Dialog
Interactive about dialog with dark mode support, contains version info and project links
"""

import os
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QPalette, QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QApplication
)


class ImprovedAboutDialog(QDialog):
    """支持暗色模式的交互式关于对话框"""
    
    def __init__(self, parent=None, translator=None):
        super().__init__(parent)
        self.translator = translator
        self.setup_ui()
        
    def detect_dark_mode(self):
        """检测是否为暗色模式"""
        # 检查是否有主窗口，从主窗口获取主题信息
        if hasattr(self.parent(), 'current_theme'):
            current_theme = self.parent().current_theme
            if current_theme and current_theme != 'auto':
                return current_theme.startswith('dark_')
        
        # 如果没有主题信息，使用调色板检测
        app: Optional[QApplication] = QApplication.instance()
        if app is None:
            return False
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.translator.get_text("about"))
        self.setFixedSize(600, 500)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 20)
        
        # 标题区域
        self.create_header(layout)
        
        # 信息区域
        self.create_info_area(layout)
        
        # 按钮区域
        self.create_buttons(layout)
        
    def create_header(self, layout):
        """创建标题区域"""
        header_layout = QHBoxLayout()
        
        # 应用图标
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(80, 80)
        
        # 尝试加载应用图标
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                'icons', 'app_icon.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.setText("DEB")
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(self.icon_label)
        
        # 标题和版本
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        self.title_label = QLabel(self.translator.get_text("about_title"))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)
        
        self.version_label = QLabel(self.translator.get_text("about_version"))
        title_layout.addWidget(self.version_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
    def create_info_area(self, layout):
        """创建信息区域"""
        # 使用 QTextBrowser 支持超链接
        self.info_browser = QTextBrowser()
        self.info_browser.setOpenExternalLinks(True)
        self.info_browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        
        # 根据主题设置内容
        self.update_content()
        
        # 应用主题样式
        self.apply_theme()
        
        layout.addWidget(self.info_browser)
        
    def update_content(self):
        """更新内容（根据主题）"""
        # 检测当前主题
        self.is_dark_mode = self.detect_dark_mode()
        
        # 根据主题设置HTML内容的颜色
        if self.is_dark_mode:
            bg_color = "transparent"
            text_color = "#e0e0e0"
            link_color = "#4dabf7"
            heading_color = "#74c0fc"
            secondary_color = "#999999"
        else:
            bg_color = "transparent"
            text_color = "#333333"
            link_color = "#1976d2"
            heading_color = "#1565c0"
            secondary_color = "#666666"
        
        # 构建 HTML 内容
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 14px;
                    line-height: 1.6;
                    color: {text_color};
                    background-color: {bg_color};
                    margin: 0;
                    padding: 10px;
                }}
                h3 {{
                    color: {heading_color};
                    margin-top: 12px;
                    margin-bottom: 8px;
                    font-size: 15px;
                    font-weight: 600;
                }}
                a {{
                    color: {link_color};
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                ul {{
                    margin: 8px 0;
                    padding-left: 20px;
                    list-style-type: none;
                }}
                li {{
                    margin: 4px 0;
                    padding-left: 20px;
                    position: relative;
                }}
                li:before {{
                    content: "▸";
                    position: absolute;
                    left: 0;
                    color: {link_color};
                }}
                .section {{
                    margin-bottom: 12px;
                }}
                .secondary {{
                    color: {secondary_color};
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            <div class="section">
                <p>{self.translator.get_text("about_description")}</p>
            </div>
            
            <div class="section">
                <h3>{self.translator.get_text("features_title").replace("=", "").strip()}</h3>
                <ul>
                    <li>{self.translator.get_text("feature_1").replace("1. ", "")}</li>
                    <li>{self.translator.get_text("feature_2").replace("2. ", "")}</li>
                    <li>{self.translator.get_text("feature_3").replace("3. ", "")}</li>
                    <li>{self.translator.get_text("feature_4").replace("4. ", "")}</li>
                    <li>{self.translator.get_text("feature_5").replace("5. ", "")}</li>
                    <li>{self.translator.get_text("feature_6").replace("6. ", "")}</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>{"项目信息" if self.translator.get_current_language() == "zh" else "Project Info"}</h3>
                <p class="secondary">{self.translator.get_text("copyright_text")}</p>
                <p class="secondary">{self.translator.get_text("license")}</p>
                <p>
                    <a href="https://github.com/Evil0ctal/SimpleTweakEditor">
                        GitHub
                    </a> | 
                    <a href="https://github.com/Evil0ctal/SimpleTweakEditor/issues">
                        {"问题反馈" if self.translator.get_current_language() == "zh" else "Issues"}
                    </a> | 
                    <a href="https://github.com/Evil0ctal/SimpleTweakEditor/releases">
                        {"下载" if self.translator.get_current_language() == "zh" else "Releases"}
                    </a>
                </p>
            </div>
        </body>
        </html>
        """
        
        self.info_browser.setHtml(html_content)
        
    def create_buttons(self, layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # GitHub 按钮
        self.github_btn = QPushButton("GitHub")
        self.github_btn.clicked.connect(self.open_github)  # type: ignore
        self.github_btn.setFixedWidth(100)
        button_layout.addWidget(self.github_btn)
        
        button_layout.addStretch()
        
        # 关闭按钮
        self.close_btn = QPushButton(self.translator.get_text("ok"))
        self.close_btn.setDefault(True)
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setFixedWidth(100)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def update_language(self, translator):
        """更新语言"""
        self.translator = translator
        # 重建UI以更新所有文本
        self.setup_ui()
    
    def showEvent(self, event):
        """显示事件，确保主题正确应用"""
        super().showEvent(event)
        # 刷新内容和主题
        self.update_content()
        self.apply_theme()
        
    def apply_theme(self):
        """应用主题样式"""
        # 获取当前主题的颜色
        is_dark = self.detect_dark_mode()
        
        # 为QTextBrowser设置合适的背景色
        if is_dark:
            # 深色主题：使用稍微亮一点的背景
            browser_bg = "#2e2e2e"
            border_color = "#404040"
        else:
            # 浅色主题：使用稍微暗一点的背景
            browser_bg = "#f5f5f5"
            border_color = "#e0e0e0"
        
        self.info_browser.setStyleSheet(f"""
            QTextBrowser {{
                border: 1px solid {border_color};
                border-radius: 4px;
                background-color: {browser_bg};
                padding: 5px;
            }}
        """)
        
        # 版本标签使用次要颜色
        version_color = "#999999" if is_dark else "#666666"
        self.version_label.setStyleSheet(f"color: {version_color};")
        
        # 图标样式 - 只有在没有图标时才应用背景
        if self.icon_label.pixmap() is None:
            # 使用主题色作为背景
            if is_dark:
                icon_bg = "#4dabf7"  # 蓝色
                icon_color = "#ffffff"
            else:
                icon_bg = "#1976d2"  # 蓝色
                icon_color = "#ffffff"
                
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {icon_bg};
                    border-radius: 12px;
                    color: {icon_color};
                    font-size: 24px;
                    font-weight: bold;
                }}
            """)
        
    def open_github(self):
        """打开 GitHub 页面"""
        QDesktopServices.openUrl(QUrl("https://github.com/Evil0ctal/SimpleTweakEditor"))