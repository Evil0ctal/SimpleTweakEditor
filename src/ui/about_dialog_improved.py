# -*- coding: utf-8 -*-
"""
改进的关于对话框模块
支持暗色模式的交互式关于信息展示
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
        """检测是否为暗色模式 - qt-material会处理这个"""
        # qt-material会自动处理主题，这里只是为了HTML内容
        app: Optional[QApplication] = QApplication.instance()
        if app is None:
            return False
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        return window_color.lightness() < 128
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.translator.get_text("about"))
        self.setFixedSize(550, 450)
        
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
        
        # 应用最小化的样式
        self.apply_theme()
        
        layout.addWidget(self.info_browser)
        
    def update_content(self):
        """更新内容（根据主题）"""
        # 检测当前主题
        self.is_dark_mode = self.detect_dark_mode()
        
        # 使用更通用的颜色，让qt-material处理大部分样式
        if self.is_dark_mode:
            bg_color = "transparent"
            text_color = "inherit"
            link_color = "#4dabf7"
            heading_color = "#74c0fc"
            secondary_color = "#999"
        else:
            bg_color = "transparent"
            text_color = "inherit"
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
                    margin-top: 15px;
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                a {{
                    color: {link_color};
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                ul {{
                    margin: 10px 0;
                    padding-left: 25px;
                }}
                li {{
                    margin: 5px 0;
                }}
                .section {{
                    margin-bottom: 15px;
                }}
                .secondary {{
                    color: {secondary_color};
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
                </ul>
            </div>
            
            <div class="section">
                <h3>{self.translator.get_text("copyright_title").replace("=", "").strip()}</h3>
                <p class="secondary">{self.translator.get_text("copyright_text")}</p>
                <p>
                    <a href="https://github.com/Evil0ctal/SimpleTweakEditor">
                        {self.translator.get_text("project_url")}
                    </a>
                </p>
                <p class="secondary">{self.translator.get_text("license")}</p>
            </div>
            
            <div class="section">
                <h3>{"联系方式" if self.translator.get_current_language() == "zh" else "Contact"}</h3>
                <p>
                    <a href="https://github.com/Evil0ctal/SimpleTweakEditor/issues">
                        {"报告问题" if self.translator.get_current_language() == "zh" else "Report Issues"}
                    </a> | 
                    <a href="https://github.com/Evil0ctal">
                        {"作者主页" if self.translator.get_current_language() == "zh" else "Author's Profile"}
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
        
    def apply_theme(self):
        """应用主题样式"""
        # qt-material会处理大部分样式
        # 只设置最少的必要样式
        self.info_browser.setStyleSheet("""
            QTextBrowser {
                border: none;
            }
        """)
        
        # 版本标签使用secondary类
        self.version_label.setProperty("class", "secondary")
        
        # 图标样式 - 只有在没有图标时才应用背景
        if self.icon_label.pixmap() is None:
            self.icon_label.setStyleSheet("""
                QLabel {
                    background-color: palette(highlight);
                    border-radius: 12px;
                    color: palette(highlighted-text);
                    font-size: 24px;
                    font-weight: bold;
                }
            """)
        
    def open_github(self):
        """打开 GitHub 页面"""
        QDesktopServices.openUrl(QUrl("https://github.com/Evil0ctal/SimpleTweakEditor"))