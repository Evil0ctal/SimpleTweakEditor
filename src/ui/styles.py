# -*- coding: utf-8 -*-
"""
样式管理模块
负责管理应用程序的样式和主题
"""

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication
from typing import TYPE_CHECKING, Optional
try:
    from qt_material import apply_stylesheet, list_themes
    HAS_QT_MATERIAL = True
except ImportError:
    HAS_QT_MATERIAL = False

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication as QApp
else:
    QApp = QApplication


class StyleManager:
    """样式管理器"""
    
    # Material Design主题映射 - 支持所有可用主题
    MATERIAL_THEMES = {
        # 自动模式
        "auto": None,
        # 深色主题
        "dark_amber": "dark_amber.xml",
        "dark_blue": "dark_blue.xml",
        "dark_cyan": "dark_cyan.xml",
        "dark_lightgreen": "dark_lightgreen.xml",
        "dark_pink": "dark_pink.xml",
        "dark_purple": "dark_purple.xml",
        "dark_red": "dark_red.xml",
        "dark_teal": "dark_teal.xml",
        "dark_yellow": "dark_yellow.xml",
        # 浅色主题
        "light_amber": "light_amber.xml",
        "light_blue": "light_blue.xml",
        "light_cyan": "light_cyan.xml",
        "light_cyan_500": "light_cyan_500.xml",
        "light_lightgreen": "light_lightgreen.xml",
        "light_pink": "light_pink.xml",
        "light_purple": "light_purple.xml",
        "light_red": "light_red.xml",
        "light_teal": "light_teal.xml",
        "light_yellow": "light_yellow.xml"
    }
    
    # 主题显示名称（用于UI）
    THEME_DISPLAY_NAMES = {
        "auto": ("自动", "Auto"),
        # 深色主题
        "dark_amber": ("深色 - 琥珀", "Dark - Amber"),
        "dark_blue": ("深色 - 蓝色", "Dark - Blue"),
        "dark_cyan": ("深色 - 青色", "Dark - Cyan"),
        "dark_lightgreen": ("深色 - 浅绿", "Dark - Light Green"),
        "dark_pink": ("深色 - 粉红", "Dark - Pink"),
        "dark_purple": ("深色 - 紫色", "Dark - Purple"),
        "dark_red": ("深色 - 红色", "Dark - Red"),
        "dark_teal": ("深色 - 青绿", "Dark - Teal"),
        "dark_yellow": ("深色 - 黄色", "Dark - Yellow"),
        # 浅色主题
        "light_amber": ("浅色 - 琥珀", "Light - Amber"),
        "light_blue": ("浅色 - 蓝色", "Light - Blue"),
        "light_cyan": ("浅色 - 青色", "Light - Cyan"),
        "light_cyan_500": ("浅色 - 青色500", "Light - Cyan 500"),
        "light_lightgreen": ("浅色 - 浅绿", "Light - Light Green"),
        "light_pink": ("浅色 - 粉红", "Light - Pink"),
        "light_purple": ("浅色 - 紫色", "Light - Purple"),
        "light_red": ("浅色 - 红色", "Light - Red"),
        "light_teal": ("浅色 - 青绿", "Light - Teal"),
        "light_yellow": ("浅色 - 黄色", "Light - Yellow")
    }
    
    # 默认主题（用于自动模式）
    DEFAULT_DARK_THEME = "dark_amber"
    DEFAULT_LIGHT_THEME = "light_amber"

    def __init__(self, config_manager=None):
        self.app: Optional[QApp] = QApplication.instance()
        self.config_manager = config_manager
        self._user_theme = None  # 主题代码
        self._current_material_theme = None
        
        # 如果qt-material可用，初始化主题
        if HAS_QT_MATERIAL and self.app:
            self.apply_initial_theme()

    def apply_initial_theme(self):
        """应用初始主题"""
        theme = self.get_theme()
        self.apply_theme(theme)

    def set_theme(self, theme):
        """设置主题偏好"""
        self._user_theme = theme
        if self.config_manager:
            self.config_manager.set("theme", theme)
            self.config_manager.save_config()
        
        # 应用新主题
        self.apply_theme(theme)

    def get_theme(self):
        """获取当前主题偏好"""
        if self._user_theme is None and self.config_manager:
            self._user_theme = self.config_manager.get("theme", "auto")
        return self._user_theme or "auto"
    
    def apply_theme(self, theme):
        """应用指定的主题"""
        if not HAS_QT_MATERIAL or not self.app:
            return
            
        # 确定实际要使用的主题
        if theme == "auto":
            # 自动模式：根据系统选择默认主题
            actual_theme = self.DEFAULT_DARK_THEME if self._is_system_dark_mode() else self.DEFAULT_LIGHT_THEME
            material_theme = self.MATERIAL_THEMES[actual_theme]
        else:
            # 直接使用指定的主题
            material_theme = self.MATERIAL_THEMES.get(theme)
            if not material_theme:
                # 如果主题不存在，使用默认
                print(f"Warning: Unknown theme '{theme}', using default")
                material_theme = self.MATERIAL_THEMES[self.DEFAULT_DARK_THEME]
        
        # 只有在主题真正改变时才应用
        if material_theme != self._current_material_theme:
            self._current_material_theme = material_theme
            apply_stylesheet(self.app, theme=material_theme)
            
            # 应用自定义样式补丁
            self._apply_custom_styles()
    
    def _is_system_dark_mode(self):
        """检测系统是否为暗色模式"""
        try:
            if self.app is not None:
                palette = self.app.palette()
                window_color = palette.color(QPalette.ColorRole.Window)
                return window_color.lightness() < 128
        except (AttributeError, RuntimeError):
            pass
        return False

    def is_dark_mode(self):
        """检测是否为暗色模式"""
        theme = self.get_theme()
        
        if theme == "auto":
            return self._is_system_dark_mode()
        else:
            # 根据主题名称判断
            return theme.startswith("dark_")
    
    def get_available_themes(self):
        """获取所有可用的主题列表"""
        return list(self.MATERIAL_THEMES.keys())
    
    def get_theme_display_name(self, theme_code, lang="zh"):
        """获取主题的显示名称"""
        if theme_code in self.THEME_DISPLAY_NAMES:
            names = self.THEME_DISPLAY_NAMES[theme_code]
            return names[0] if lang == "zh" else names[1]
        return theme_code
    
    def get_all_theme_names(self, lang="zh"):
        """获取所有主题的显示名称"""
        return [(code, self.get_theme_display_name(code, lang)) 
                for code in self.get_available_themes()]
    
    def _apply_custom_styles(self):
        """应用自定义样式补丁"""
        if not self.app:
            return
            
        # 获取当前样式表
        current_style = self.app.styleSheet()
        
        # 添加自定义样式
        custom_styles = self._get_custom_styles()
        
        # 合并样式
        self.app.setStyleSheet(current_style + "\n" + custom_styles)
    
    def _get_custom_styles(self):
        """获取自定义样式"""
        
        # 自定义样式，补充qt-material没有覆盖的部分
        custom = """
        /* 自定义选项卡样式 */
        QTabWidget::pane {
            border-top: 2px solid palette(highlight);
        }
        
        /* 命令输出日志特殊样式 */
        QTextEdit#cmdLogText {
            font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
        }
        
        /* 状态栏样式 */
        QStatusBar {
            font-size: 12px;
        }
        
        /* 信息标签样式 */
        QLabel.info-label {
            color: palette(mid);
            font-style: italic;
        }
        
        QLabel.success-label {
            color: palette(highlight);
            font-weight: bold;
        }
        
        QLabel.heading {
            font-weight: bold;
            font-size: 14px;
        }
        
        QLabel.secondary {
            color: palette(text);
        }
        
        /* 拖放区域改进 */
        QLabel[dropZone="true"] {
            background-color: palette(base);
            border: 2px dashed palette(mid);
            border-radius: 8px;
            padding: 30px;
            font-size: 14px;
            color: palette(text);
        }
        
        QLabel[dropZone="true"][active="true"] {
            background-color: palette(highlight);
            border: 2px solid palette(highlighted-text);
            color: palette(highlighted-text);
        }
        """
        
        return custom

    def get_text_color(self):
        """获取当前主题的文本颜色"""
        if HAS_QT_MATERIAL:
            # qt-material会自动处理颜色
            return QColor(255, 255, 255) if self.is_dark_mode() else QColor(0, 0, 0)
        
        try:
            if self.app is not None:
                palette = self.app.palette()
                return palette.color(QPalette.ColorRole.WindowText)
        except (AttributeError, RuntimeError):
            pass
        return QColor(0, 0, 0)

    def get_background_color(self):
        """获取当前主题的背景颜色"""
        if HAS_QT_MATERIAL:
            # qt-material会自动处理颜色
            return QColor(48, 48, 48) if self.is_dark_mode() else QColor(250, 250, 250)
            
        try:
            if self.app is not None:
                palette = self.app.palette()
                return palette.color(QPalette.ColorRole.Window)
        except (AttributeError, RuntimeError):
            pass
        return QColor(255, 255, 255)

    def get_drop_zone_style(self, active=False):
        """获取拖放区域样式"""
        if HAS_QT_MATERIAL:
            # 使用Material Design风格
            if active:
                return """
                    QLabel {
                        background-color: palette(highlight);
                        border: 2px solid palette(highlight-text);
                        border-radius: 8px;
                        padding: 20px;
                        font-size: 14px;
                        color: palette(highlighted-text);
                    }
                """
            else:
                return """
                    QLabel {
                        background-color: palette(alternate-base);
                        border: 2px dashed palette(mid);
                        border-radius: 8px;
                        padding: 20px;
                        font-size: 14px;
                        color: palette(text);
                    }
                """
        
        # 回退到原来的样式
        is_dark = self.is_dark_mode()
        if active:
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
        if HAS_QT_MATERIAL:
            return """
                QLabel[infoLabel="true"] {
                    color: palette(highlight);
                    font-weight: bold;
                }
            """
        
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
        # qt-material处理全局样式，只返回自定义补充
        return self._get_custom_styles()

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
        if HAS_QT_MATERIAL:
            # qt-material已经应用了全局样式，只需要补充自定义样式
            if widget and hasattr(widget, 'setStyleSheet'):
                current = widget.styleSheet()
                custom = self._get_custom_styles()
                if custom and custom not in current:
                    widget.setStyleSheet(current + "\n" + custom)
        else:
            # 使用原来的方式
            if widget:
                widget.setStyleSheet(self.get_global_style())

    def update_drop_zone_style(self, drop_label, active=False):
        """更新拖放区域样式"""
        if drop_label:
            drop_label.setProperty("active", "true" if active else "false")
            # 强制刷新样式
            drop_label.style().unpolish(drop_label)
            drop_label.style().polish(drop_label)

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
