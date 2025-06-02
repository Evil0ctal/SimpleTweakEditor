# -*- coding: utf-8 -*-
"""
创建时间: 2024-11-22
作者: Evil0ctal

中文介绍:
主窗口UI模块，包含应用程序的主用户界面。
实现了选项卡式界面，包括deb工具、插件管理器、软件源管理和命令工具。
支持多语言、主题切换、拖放操作等核心功能。

英文介绍:
Main window UI module containing the application's main user interface.
Implements a tabbed interface including deb tools, package manager, repository manager, and command tools.
Supports multi-language, theme switching, drag-and-drop operations, and other core features.
"""

import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QTextCursor, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QSplitter, QStatusBar, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QFrame, QStyle
)

from .styles import StyleManager
from .control_editor import ControlEditorDialog
from .package_manager_widget import PackageManagerWidget
from .repo_manager_dialog import RepoManagerDialog
from src.workers.command_thread import CommandThread
from src.ui.interactive_terminal import InteractiveTerminal
from src.utils.system_utils import open_folder, is_valid_deb_file, is_valid_package_folder


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self, app_core):
        super().__init__()
        self.app_core = app_core
        self.lang_mgr = app_core.lang_mgr
        self.config_mgr = app_core.config_mgr
        self.style_mgr = StyleManager(self.config_mgr)
        
        # 保存当前主题供子窗口使用
        self.current_theme = self.style_mgr.get_theme()

        # 当前运行的命令线程
        self.current_command_thread = None
        
        # 窗口管理器 - 存储打开的对话框实例
        self.dialogs = {
            'package_manager': None,
            'repo_manager': None
        }

        # 初始化UI
        self.setupUI()
        self.setup_menu_bar()
        self.restore_window_state()

        # 应用样式（延迟执行以确保所有组件都已创建）
        QTimer.singleShot(0, self.apply_styles)
        
        # 延迟居中窗口以确保布局完成
        QTimer.singleShot(50, self.center_window)

        # 延迟加载欢迎消息
        if self.config_mgr.get_show_welcome_message():
            QTimer.singleShot(100, self.show_welcome_message)

    def setupUI(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle(self.lang_mgr.get_text("app_title"))
        self.setAcceptDrops(True)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建选项卡界面
        self.create_tabbed_interface(main_layout)
        self.create_status_bar()

    def create_tabbed_interface(self, layout):
        """创建选项卡界面"""
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        
        # 创建各个选项卡
        self.create_deb_tools_tab()
        self.create_package_manager_tab()
        self.create_repo_manager_tab()
        self.create_command_tools_tab()
        self.create_device_tab()
        
        layout.addWidget(self.tab_widget)

    def create_deb_tools_tab(self):
        """创建deb工具选项卡（原始功能）"""
        deb_widget = QWidget()
        deb_layout = QVBoxLayout(deb_widget)
        deb_layout.setContentsMargins(10, 10, 10, 10)
        deb_layout.setSpacing(10)

        # 创建原有的UI组件
        self.create_info_section(deb_layout)
        self.create_button_section(deb_layout)
        self.create_drop_zone(deb_layout)
        self.create_main_content(deb_layout)

        # 添加选项卡
        self.tab_widget.addTab(deb_widget, self.lang_mgr.get_text("deb_tools"))

    def create_package_manager_tab(self):
        """创建插件管理器选项卡"""
        # 创建包装器容器
        package_widget = QWidget()
        package_layout = QVBoxLayout(package_widget)
        package_layout.setContentsMargins(0, 0, 0, 0)
        package_layout.setSpacing(0)
        
        # 创建插件管理器实例 - 传入必要的参数
        self.package_manager = PackageManagerWidget(
            parent=self, 
            repo_manager=self.app_core.repo_mgr,
            lang_mgr=self.lang_mgr
        )
        
        # 隐藏对话框的标题栏和边框，让它看起来像嵌入式组件
        self.package_manager.setWindowFlags(Qt.WindowType.Widget)
        self.package_manager.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        
        # 将插件管理器添加到布局中
        package_layout.addWidget(self.package_manager)
        
        self.tab_widget.addTab(package_widget, self.lang_mgr.get_text("package_manager"))

    def create_repo_manager_tab(self):
        """创建软件源管理选项卡"""
        # 创建包装器容器
        repo_widget = QWidget()
        repo_layout = QVBoxLayout(repo_widget)
        repo_layout.setContentsMargins(0, 0, 0, 0)
        repo_layout.setSpacing(0)
        
        # 创建软件源管理器实例
        self.repo_manager_widget = RepoManagerDialog(
            parent=self,
            repo_manager=self.app_core.repo_mgr,
            lang_mgr=self.lang_mgr
        )
        
        # 隐藏对话框的标题栏和边框，让它看起来像嵌入式组件
        self.repo_manager_widget.setWindowFlags(Qt.WindowType.Widget)
        self.repo_manager_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        
        # 将软件源管理器添加到布局中
        repo_layout.addWidget(self.repo_manager_widget)
        
        self.tab_widget.addTab(repo_widget, self.lang_mgr.get_text("manage_sources"))

    def create_command_tools_tab(self):
        """创建命令工具选项卡"""
        # 使用新的交互式终端
        self.terminal_widget = InteractiveTerminal(self.lang_mgr)
        self.tab_widget.addTab(self.terminal_widget, self.lang_mgr.get_text("command_tools"))
    
    def create_device_tab(self):
        """创建设备选项卡"""
        try:
            from src.ui.device_panel import DevicePanel
            
            # 创建设备面板
            self.device_panel = DevicePanel(self.lang_mgr, self.style_mgr)
            
            # 连接信号
            self.device_panel.device_connected.connect(self.on_device_connected)
            self.device_panel.device_disconnected.connect(self.on_device_disconnected)
            
            # 添加到选项卡
            self.tab_widget.addTab(self.device_panel, self.lang_mgr.get_text("ios_device"))
            
        except ImportError as e:
            print(f"[WARNING] Could not import device panel: {e}")
            # 创建占位符
            placeholder = QLabel("iOS Device features not available.\nInstall pymobiledevice3 to enable.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tab_widget.addTab(placeholder, self.lang_mgr.get_text("ios_device"))

    def create_info_section(self, layout):
        """创建信息区域"""
        self.info_label = QLabel(self.lang_mgr.get_text("tip_drag_drop"))
        self.info_label.setProperty("infoLabel", True)
        layout.addWidget(self.info_label)

    def create_button_section(self, layout):
        """创建按钮区域"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 解包按钮
        self.unpack_btn = QPushButton(self.lang_mgr.get_text("unpack_deb"))
        self.unpack_btn.clicked.connect(self.app_core.unpack_deb_dialog)
        self.unpack_btn.setMinimumWidth(150)
        button_layout.addWidget(self.unpack_btn)

        # 打包按钮
        self.repack_btn = QPushButton(self.lang_mgr.get_text("repack_folder"))
        self.repack_btn.clicked.connect(self.app_core.repack_folder_dialog)
        self.repack_btn.setMinimumWidth(150)
        button_layout.addWidget(self.repack_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def create_drop_zone(self, layout):
        """创建拖放区域"""
        self.drop_group = QGroupBox(self.lang_mgr.get_text("drop_zone"))
        drop_layout = QVBoxLayout(self.drop_group)

        # Create drop zone hint text
        self.drop_label = QLabel(self.lang_mgr.get_text("drop_zone_hint"))
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(100)
        # Set appropriate font size
        font = self.drop_label.font()
        font.setPointSize(14)
        self.drop_label.setFont(font)
        # Add some styling
        self.drop_label.setStyleSheet("""
            QLabel {
                color: palette(text);
                padding: 20px;
                line-height: 1.5;
            }
        """)
        self.drop_label.setProperty("dropZone", True)
        drop_layout.addWidget(self.drop_label)

        layout.addWidget(self.drop_group)

    def create_main_content(self, layout):
        """创建主要内容区域（仅日志区域）"""
        # 创建日志区域作为容器
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加日志区域
        self.create_log_section(log_layout)
        
        layout.addWidget(log_container)

    def create_log_section(self, layout):
        """创建日志区域"""
        # 创建标题栏
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 5)
        
        # 日志标题
        self.log_title = QLabel(self.lang_mgr.get_text("operation_log"))
        title_layout.addWidget(self.log_title)
        
        title_layout.addStretch()
        
        # 清除日志按钮 - 使用更小的按钮
        self.clear_log_btn = QPushButton(self.lang_mgr.get_text("clear_log"))
        self.clear_log_btn.setMaximumHeight(30)
        self.clear_log_btn.setMinimumHeight(30)
        self.clear_log_btn.clicked.connect(self.clear_log)
        title_layout.addWidget(self.clear_log_btn)
        
        layout.addLayout(title_layout)
        
        # 日志文本区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)
        layout.addWidget(self.log_text)

    def create_command_log_section(self, layout):
        """创建命令工具独立的日志区域"""
        # 创建标题栏
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 5)
        
        # 命令日志标题
        self.cmd_log_title = QLabel(self.lang_mgr.get_text("command_output"))
        title_layout.addWidget(self.cmd_log_title)
        
        title_layout.addStretch()
        
        # 清除命令日志按钮
        self.clear_cmd_log_btn = QPushButton(self.lang_mgr.get_text("clear_log"))
        self.clear_cmd_log_btn.setMaximumHeight(30)
        self.clear_cmd_log_btn.setMinimumHeight(30)
        self.clear_cmd_log_btn.clicked.connect(self.clear_command_log)
        title_layout.addWidget(self.clear_cmd_log_btn)
        
        layout.addLayout(title_layout)
        
        # 命令日志文本区域
        self.cmd_log_text = QTextEdit()
        self.cmd_log_text.setReadOnly(True)
        self.cmd_log_text.document().setMaximumBlockCount(2000)
        # 设置等宽字体，适合显示命令输出
        font = self.cmd_log_text.font()
        font.setFamily("Monaco, Menlo, 'DejaVu Sans Mono', monospace")
        self.cmd_log_text.setFont(font)
        layout.addWidget(self.cmd_log_text)

    def create_command_section(self, layout):
        """创建命令行区域"""
        # 创建标题
        self.cmd_title = QLabel(self.lang_mgr.get_text("command_line"))
        layout.addWidget(self.cmd_title)

        # 快捷命令工具栏
        self.create_command_toolbar(layout)

        # 命令输入区域
        self.create_command_input(layout)

    def create_command_toolbar(self, layout):
        """创建命令工具栏"""
        # 第一行：目标选择
        target_toolbar = QHBoxLayout()
        
        # 目标选择按钮
        self.select_target_btn = QPushButton(self.lang_mgr.get_text("select_target_file"))
        self.select_target_btn.clicked.connect(self.select_target)
        target_toolbar.addWidget(self.select_target_btn)
        
        # 当前选择的目标显示
        target_text = self.lang_mgr.get_text("no_target_selected") or "No target selected"
        self.target_label = QLabel(target_text)
        # 让qt-material处理样式
        self.target_label.setProperty("class", "info-label")
        self.target_label.setMinimumHeight(25)
        self.target_label.setWordWrap(False)  # 防止换行
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        target_toolbar.addWidget(self.target_label, 1)  # stretch factor = 1，占据剩余空间
        
        # 清除目标按钮
        clear_text = self.lang_mgr.get_text("clear") or "Clear"
        self.clear_target_btn = QPushButton(clear_text)
        self.clear_target_btn.setMaximumWidth(60)
        clear_tooltip = self.lang_mgr.get_text("clear_target_selection") or "Clear target selection"
        self.clear_target_btn.setToolTip(clear_tooltip)
        self.clear_target_btn.clicked.connect(self.clear_target)
        target_toolbar.addWidget(self.clear_target_btn)
        
        layout.addLayout(target_toolbar)

        # 第二行：快捷命令和控制按钮
        cmd_toolbar = QHBoxLayout()

        # 快捷命令下拉菜单
        self.cmd_presets = QComboBox()
        self.cmd_presets.setEditable(False)
        self.current_target_path = None
        self.update_command_presets()
        self.cmd_presets.currentIndexChanged.connect(self.load_command_preset)
        cmd_toolbar.addWidget(self.cmd_presets)

        # 清除命令输入框按钮
        self.clear_cmd_btn = QPushButton(self.lang_mgr.get_text("clear"))
        self.clear_cmd_btn.setMaximumWidth(80)
        self.clear_cmd_btn.setMinimumHeight(30)
        self.clear_cmd_btn.setToolTip(self.lang_mgr.get_text("clear_command"))
        self.clear_cmd_btn.clicked.connect(self.clear_command)
        cmd_toolbar.addWidget(self.clear_cmd_btn)

        # 文件浏览按钮
        self.browse_btn = QPushButton(self.lang_mgr.get_text("browse"))
        self.browse_btn.setMaximumWidth(100)
        self.browse_btn.setToolTip(self.lang_mgr.get_text("browse"))
        self.browse_btn.clicked.connect(self.browse_file_for_command)
        cmd_toolbar.addWidget(self.browse_btn)

        layout.addLayout(cmd_toolbar)

    def create_command_input(self, layout):
        """创建命令输入区域"""
        cmd_input_layout = QHBoxLayout()

        self.cmd_entry = QLineEdit()
        self.cmd_entry.setPlaceholderText(self.lang_mgr.get_text("cmd_placeholder"))
        self.cmd_entry.returnPressed.connect(self.execute_command)
        # 设置输入框样式
        cmd_input_layout.addWidget(self.cmd_entry)

        self.cmd_btn = QPushButton(self.lang_mgr.get_text("execute"))
        self.cmd_btn.clicked.connect(self.execute_command)
        cmd_input_layout.addWidget(self.cmd_btn)

        layout.addLayout(cmd_input_layout)

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(self.lang_mgr.get_text("ready"))

    def setup_menu_bar(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        menubar.clear()  # 清除现有菜单

        # 文件菜单
        self.create_file_menu(menubar)

        # 设置菜单
        self.create_settings_menu(menubar)

        # 帮助菜单
        self.create_help_menu(menubar)
        
        # 调试：检查菜单数量
        if self.app_core.debug_mode:
            self._debug_menu_structure(menubar)

    def create_file_menu(self, menubar):
        """创建文件菜单"""
        file_menu = menubar.addMenu(self.lang_mgr.get_text("file"))

        # 解包选项
        unpack_action = QAction(self.lang_mgr.get_text("unpack_deb"), self)
        unpack_action.triggered.connect(self.app_core.unpack_deb_dialog)
        file_menu.addAction(unpack_action)

        # 打包选项
        repack_action = QAction(self.lang_mgr.get_text("repack_folder"), self)
        repack_action.triggered.connect(self.app_core.repack_folder_dialog)
        file_menu.addAction(repack_action)

        file_menu.addSeparator()
        
        # Plist编辑器
        plist_editor_action = QAction(self.lang_mgr.get_text("plist_editor"), self)
        plist_editor_action.triggered.connect(self.open_plist_editor)
        file_menu.addAction(plist_editor_action)
        
        file_menu.addSeparator()
        
        # 插件管理器（主要功能）
        package_manager_action = QAction(self.lang_mgr.get_text("package_manager"), self)
        package_manager_action.triggered.connect(self.open_package_manager)
        file_menu.addAction(package_manager_action)
        
        # 管理软件源（源管理）
        manage_sources_action = QAction(self.lang_mgr.get_text("manage_sources"), self)
        manage_sources_action.triggered.connect(self.open_repo_manager)
        file_menu.addAction(manage_sources_action)

        file_menu.addSeparator()

        # 退出选项
        exit_action = QAction(self.lang_mgr.get_text("exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_settings_menu(self, menubar):
        """创建设置菜单"""
        settings_menu = menubar.addMenu(self.lang_mgr.get_text("settings"))

        # 调试模式切换
        debug_action = QAction(self.lang_mgr.get_text("debug_mode"), self)
        debug_action.setCheckable(True)
        debug_action.setChecked(self.app_core.debug_mode)
        debug_action.triggered.connect(self.app_core.toggle_debug_mode)
        settings_menu.addAction(debug_action)

        settings_menu.addSeparator()

        # 语言切换子菜单
        self.create_language_menu(settings_menu)
        
        # 主题切换子菜单
        self.create_theme_menu(settings_menu)

    def create_language_menu(self, parent_menu):
        """创建语言菜单"""
        language_menu = parent_menu.addMenu(self.lang_mgr.get_text("language"))

        # 创建语言动作组
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)

        # 添加支持的语言
        current_lang = self.lang_mgr.get_current_language()
        language_names = self.lang_mgr.language_names

        for lang_code, lang_name in language_names.items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setChecked(current_lang == lang_code)
            action.setData(lang_code)
            action.triggered.connect(lambda checked, code=lang_code: self.app_core.switch_language(code))

            self.lang_group.addAction(action)
            language_menu.addAction(action)

    def create_theme_menu(self, parent_menu):
        """创建主题菜单"""
        theme_menu = parent_menu.addMenu(self.lang_mgr.get_text("theme"))

        # 创建主题动作组
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        # 获取当前语言
        current_lang = self.lang_mgr.get_current_language()
        lang_for_theme = "zh" if current_lang == "zh" else "en"
        
        # 获取当前主题
        current_theme = self.style_mgr.get_theme()
        self.current_theme = current_theme  # 保存当前主题供子窗口使用
        
        # 获取所有可用主题
        all_themes = self.style_mgr.get_all_theme_names(lang_for_theme)
        
        # 添加自动选项
        auto_action = QAction(self.lang_mgr.get_text("follow_system"), self)
        auto_action.setCheckable(True)
        auto_action.setChecked(current_theme == "auto")
        auto_action.setData("auto")
        auto_action.triggered.connect(lambda checked: self.change_theme("auto"))
        self.theme_group.addAction(auto_action)
        theme_menu.addAction(auto_action)
        
        theme_menu.addSeparator()
        
        # 按深色/浅色分组
        dark_themes = []
        light_themes = []
        
        for theme_code, theme_name in all_themes:
            if theme_code == "auto":
                continue
            if theme_code.startswith("dark_"):
                dark_themes.append((theme_code, theme_name))
            else:
                light_themes.append((theme_code, theme_name))
        
        # 添加深色主题
        if dark_themes:
            dark_label = QAction("--- " + (self.lang_mgr.get_text("dark_theme") or "Dark Themes") + " ---", self)
            dark_label.setEnabled(False)
            theme_menu.addAction(dark_label)
            
            for theme_code, theme_name in sorted(dark_themes, key=lambda x: x[1]):
                action = QAction(theme_name, self)
                action.setCheckable(True)
                action.setChecked(current_theme == theme_code)
                action.setData(theme_code)
                action.triggered.connect(lambda checked, code=theme_code: self.change_theme(code))
                self.theme_group.addAction(action)
                theme_menu.addAction(action)
        
        # 添加浅色主题
        if light_themes:
            theme_menu.addSeparator()
            light_label = QAction("--- " + (self.lang_mgr.get_text("light_theme") or "Light Themes") + " ---", self)
            light_label.setEnabled(False)
            theme_menu.addAction(light_label)
            
            for theme_code, theme_name in sorted(light_themes, key=lambda x: x[1]):
                action = QAction(theme_name, self)
                action.setCheckable(True)
                action.setChecked(current_theme == theme_code)
                action.setData(theme_code)
                action.triggered.connect(lambda checked, code=theme_code: self.change_theme(code))
                self.theme_group.addAction(action)
                theme_menu.addAction(action)

    def change_theme(self, theme_code):
        """切换主题"""
        # 设置并应用新主题
        self.style_mgr.set_theme(theme_code)
        self.current_theme = theme_code  # 更新当前主题
        
        # qt-material会全局应用主题，所以不需要单独为每个组件设置
        # 只需要应用自定义样式补充
        self.apply_styles()
        
        # 更新日志颜色
        if hasattr(self, 'log_text'):
            self.log_text.viewport().update()
        if hasattr(self, 'cmd_log_text'):
            self.cmd_log_text.viewport().update()

    def create_help_menu(self, menubar):
        """创建帮助菜单"""
        help_text = self.lang_mgr.get_text("help")
        about_text = self.lang_mgr.get_text("about")
        
        # 调试输出
        if self.app_core.debug_mode:
            print(f"DEBUG: Creating help menu - help_text: '{help_text}', about_text: '{about_text}'")
            print(f"DEBUG: Current language: {self.lang_mgr.get_current_language()}")
        
        # 在 macOS 上的特殊处理
        import platform
        if platform.system() == "Darwin":
            if help_text.lower() == "help":
                # 英文 Help 菜单添加不可见字符
                help_text = help_text + "\u200b"
            
            # macOS 会自动将 "About" 菜单项移到应用菜单
            # 解决方案：在英文时使用 "About..." (带省略号)
            if self.lang_mgr.get_current_language() == "en" and about_text.lower() == "about":
                about_text = "About..."
        
        help_menu = menubar.addMenu(help_text)

        # 关于选项
        about_action = QAction(about_text, self)
        about_action.triggered.connect(self.app_core.show_about_dialog)
        
        # 在 macOS 上防止 About 菜单项被移动到应用菜单
        if platform.system() == "Darwin":
            about_action.setMenuRole(QAction.MenuRole.NoRole)
            
        help_menu.addAction(about_action)
        
        # 添加分隔符
        help_menu.addSeparator()
        
        # 文档链接
        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self.open_documentation)
        help_menu.addAction(docs_action)
        
        # GitHub 链接
        github_action = QAction("GitHub", self)
        github_action.triggered.connect(self.open_github)
        help_menu.addAction(github_action)
        
        help_menu.addSeparator()
        
        # 版本信息
        from ..version import APP_VERSION
        version_action = QAction(f"Version {APP_VERSION}", self)
        version_action.setEnabled(False)
        help_menu.addAction(version_action)
        
        # 在 macOS 上，还需要手动设置应用菜单中的 About 项
        if platform.system() == "Darwin":
            # 使用 QApplication 设置标准的 About 菜单项
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.setApplicationName(self.lang_mgr.get_text("app_title"))
                # 注意：这会创建系统标准的 About 菜单项，但可能不会触发我们的自定义对话框

    def update_command_presets(self):
        """更新快捷命令预设"""
        if not hasattr(self, 'cmd_presets'):
            return
            
        self.cmd_presets.clear()
        presets = self.lang_mgr.get_command_presets(self.current_target_path)

        for preset in presets:
            if isinstance(preset, tuple):
                # (命令, 描述)
                self.cmd_presets.addItem(preset[1], preset[0])
            else:
                # 标题项
                self.cmd_presets.addItem(preset)

    def load_command_preset(self, index):
        """加载预设命令"""
        if not hasattr(self, 'cmd_presets') or not hasattr(self, 'cmd_entry'):
            return
            
        if index > 0:  # 跳过标题项
            command = self.cmd_presets.itemData(index)
            if command:
                self.cmd_entry.setText(command)
            self.cmd_presets.setCurrentIndex(0)  # 重置到默认选项

    def clear_command(self):
        """清除命令输入"""
        if hasattr(self, 'cmd_entry'):
            self.cmd_entry.clear()
    
    def select_target(self):
        """选择目标文件或文件夹"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        # 弹出选择对话框
        dialog = QMessageBox()
        dialog.setWindowTitle("Select Target Type")
        dialog.setText("What type of target do you want to select?")
        
        file_btn = dialog.addButton(self.lang_mgr.get_text("select_target_file"), QMessageBox.ButtonRole.AcceptRole)
        folder_btn = dialog.addButton(self.lang_mgr.get_text("select_target_folder"), QMessageBox.ButtonRole.ActionRole)
        cancel_btn = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        dialog.exec()
        
        if dialog.clickedButton() == file_btn:
            # 选择文件
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.lang_mgr.get_text("select_target_file"),
                os.getcwd(),
                "All files (*.*)"
            )
            if file_path:
                self.set_target(file_path)
                
        elif dialog.clickedButton() == folder_btn:
            # 选择文件夹
            folder_path = QFileDialog.getExistingDirectory(
                self,
                self.lang_mgr.get_text("select_target_folder"),
                os.getcwd()
            )
            if folder_path:
                self.set_target(folder_path)
    
    def set_target(self, target_path):
        """设置目标路径"""
        self.current_target_path = target_path
        
        # 更新显示 - 显示完整文件名，让标签自动处理显示
        import os
        display_name = os.path.basename(target_path)
        
        self.target_label.setText(display_name)
        self.target_label.setToolTip(f"Full path: {target_path}")
        # 让qt-material处理样式
        self.target_label.setProperty("class", "success-label")
        self.target_label.style().unpolish(self.target_label)
        self.target_label.style().polish(self.target_label)
        
        # 更新快捷命令
        self.update_command_presets()
        
        self.log(f"Target selected: {target_path}", "info")
    
    def clear_target(self):
        """清除目标选择"""
        self.current_target_path = None
        target_text = self.lang_mgr.get_text("no_target_selected") or "No target selected"
        self.target_label.setText(target_text)
        # 让qt-material处理样式
        self.target_label.setProperty("class", "info-label")
        self.target_label.style().unpolish(self.target_label)
        self.target_label.style().polish(self.target_label)
        self.target_label.setToolTip("")
        self.update_command_presets()

    def _update_target_label_style(self, has_target):
        """更新目标标签样式（使用qt-material主题）"""
        if has_target:
            self.target_label.setProperty("class", "success-label")
        else:
            self.target_label.setProperty("class", "info-label")
        # 强制更新样式
        self.target_label.style().unpolish(self.target_label)
        self.target_label.style().polish(self.target_label)
    
    def browse_file_for_command(self):
        """浏览文件并添加到命令行"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            self.config_mgr.get_path("last_deb_dir") or os.getcwd()
        )

        if file_path:
            # 将路径添加到当前命令
            current_cmd = self.cmd_entry.text()
            if current_cmd and not current_cmd.endswith(" "):
                current_cmd += " "

            self.cmd_entry.setText(current_cmd + f'"{file_path}"')
            self.cmd_entry.setFocus()

    def execute_command(self):
        """执行命令"""
        command = self.cmd_entry.text().strip()
        if not command:
            return

        # 处理特殊命令
        if self.handle_special_commands(command):
            return

        # 输出到命令工具日志
        self.log_to_command(f"{self.lang_mgr.get_text('execute')}: {command}", "info")

        # 停止之前的命令
        if self.current_command_thread and self.current_command_thread.isRunning():
            self.current_command_thread.stop()
            self.current_command_thread.wait()

        # 创建并启动新的命令线程
        self.current_command_thread = CommandThread(command, self.lang_mgr)
        self.current_command_thread.output_received.connect(self.handle_command_output_to_cmd_log)
        self.current_command_thread.command_finished.connect(self.handle_command_finished_to_cmd_log)
        self.current_command_thread.start()

    def handle_special_commands(self, command):
        """处理特殊命令"""
        if command.startswith("open ") or command.startswith("cd "):
            path = command.split(" ", 1)[1].strip('"').strip("'")
            if os.path.exists(path):
                if os.path.isdir(path):
                    self.log_to_command(f"Opening folder: {path}", "info")
                    if open_folder(path):
                        self.log_to_command("Folder opened successfully", "success")
                    else:
                        self.log_to_command("Failed to open folder", "error")
                    return True
                elif os.path.isfile(path):
                    self.log_to_command(f"Opening file: {path}", "info")
                    return True
            else:
                self.log_to_command(f"Path not found: {path}", "error")
                return True
        return False

    def handle_command_output(self, text, tag):
        """处理命令输出"""
        self.log(text.rstrip(), "error" if tag == "error" else None)

    def handle_command_finished(self, return_code):
        """处理命令执行完成"""
        if return_code == 0:
            self.log(self.lang_mgr.get_text("cmd_complete"), "success")
        else:
            self.log(self.lang_mgr.format_text("cmd_return_error", return_code), "error")

    def handle_command_output_to_cmd_log(self, text, tag):
        """处理命令输出到命令工具日志"""
        self.log_to_command(text.rstrip(), "error" if tag == "error" else None)

    def handle_command_finished_to_cmd_log(self, return_code):
        """处理命令执行完成到命令工具日志"""
        if return_code == 0:
            self.log_to_command(self.lang_mgr.get_text("cmd_complete"), "success")
        else:
            self.log_to_command(self.lang_mgr.format_text("cmd_return_error", return_code), "error")

    def log(self, message, tag=None):
        """添加日志消息"""
        # 确保消息是字符串
        message = str(message)
        
        # 移动光标到末尾
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

        # 获取颜色
        colors = self.style_mgr.get_log_colors()
        color = colors.get(tag, colors["normal"])

        # 设置文本格式
        char_format = cursor.charFormat()
        char_format.setForeground(color)
        cursor.setCharFormat(char_format)

        # 插入文本
        cursor.insertText(message + "\n")

        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 更新状态栏
        self.status_bar.showMessage(message)

    def log_to_command(self, message, tag=None):
        """输出日志到命令工具日志区域"""
        if not hasattr(self, 'cmd_log_text'):
            return
            
        # 获取当前时间
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据标签选择颜色
        color_map = self.style_mgr.get_log_colors()
        color = color_map.get(tag, color_map.get("normal"))
        
        # 格式化消息
        formatted_message = f"[{timestamp}] {message}"
        
        # 移动到文档末尾
        cursor = self.cmd_log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 设置文本颜色
        char_format = cursor.charFormat()
        char_format.setForeground(color)
        cursor.setCharFormat(char_format)
        
        # 插入文本
        cursor.insertText(formatted_message + "\n")
        
        # 滚动到底部
        scrollbar = self.cmd_log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.log(self.lang_mgr.get_text("clear_log"), "info")

    def clear_command_log(self):
        """清除命令日志"""
        if hasattr(self, 'cmd_log_text'):
            self.cmd_log_text.clear()
            self.log_to_command(self.lang_mgr.get_text("clear_log"), "info")

    def show_welcome_message(self):
        """显示欢迎消息"""
        welcome_messages = [
            (self.lang_mgr.get_text("welcome"), "info"),
            ("", None),
            (self.lang_mgr.get_text("intro_title"), "info"),
            (self.lang_mgr.get_text("intro_text"), None),
            ("", None),
            (self.lang_mgr.get_text("features_title"), "info"),
            (self.lang_mgr.get_text("feature_1"), None),
            (self.lang_mgr.get_text("feature_2"), None),
            (self.lang_mgr.get_text("feature_3"), None),
            (self.lang_mgr.get_text("feature_4"), None),
            ("", None),
            (self.lang_mgr.get_text("usage_title"), "info"),
            (self.lang_mgr.get_text("usage_unpack_title"), None),
            (self.lang_mgr.get_text("usage_unpack_1"), None),
            (self.lang_mgr.get_text("usage_unpack_2"), None),
            ("", None),
            (self.lang_mgr.get_text("usage_repack_title"), None),
            (self.lang_mgr.get_text("usage_repack_1"), None),
            (self.lang_mgr.get_text("usage_repack_2"), None),
            ("", None),
            (self.lang_mgr.get_text("copyright_title"), "info"),
            (self.lang_mgr.get_text("copyright_text"), None),
            (self.lang_mgr.get_text("project_url"), None),
            (self.lang_mgr.get_text("license"), None),
            ("", None),
            (self.lang_mgr.get_text("ready_to_go"), "success")
        ]

        for message, tag in welcome_messages:
            self.log(message, tag)

    def apply_styles(self):
        """应用样式"""
        # 应用全局样式
        self.style_mgr.apply_global_style(self)

        # 设置拖放区域样式
        self.style_mgr.update_drop_zone_style(self.drop_label, False)

        # 为主要按钮设置样式
        self.unpack_btn.setStyleSheet(self.style_mgr.get_button_style("primary"))
        self.repack_btn.setStyleSheet(self.style_mgr.get_button_style("success"))
        
        # 应用其他组件的主题样式
        self._apply_theme_aware_styles()
        
        # 为集成的组件应用样式
        self._apply_integrated_components_styles()

    def _apply_theme_aware_styles(self):
        """应用主题感知的样式"""
        is_dark = self.style_mgr.is_dark_mode()
        
        # 标题样式
        title_style = """
            font-weight: bold; 
            font-size: 14px;
            margin-bottom: 8px;
        """
        if hasattr(self, 'log_title'):
            self.log_title.setStyleSheet(title_style)
        if hasattr(self, 'cmd_title'):
            self.cmd_title.setStyleSheet(title_style)
        if hasattr(self, 'cmd_log_title'):
            self.cmd_log_title.setStyleSheet(title_style)
        
        # 清除日志按钮
        if hasattr(self, 'clear_log_btn'):
            self.clear_log_btn.setStyleSheet(self.style_mgr.get_button_style("warning"))
        if hasattr(self, 'clear_cmd_log_btn'):
            self.clear_cmd_log_btn.setStyleSheet(self.style_mgr.get_button_style("warning"))
        
        # 日志文本区域样式 - 使用最小化的自定义样式
        if hasattr(self, 'log_text'):
            log_style = """
                QTextEdit {
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                    border-radius: 4px;
                    padding: 4px;
                }
            """
            self.log_text.setStyleSheet(log_style)
        
        # 命令工具日志文本区域样式 - 使用最小化的自定义样式
        if hasattr(self, 'cmd_log_text'):
            cmd_log_style = """
                QTextEdit {
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                    border-radius: 4px;
                    padding: 8px;
                }
            """
            self.cmd_log_text.setStyleSheet(cmd_log_style)
        
        # 选择目标按钮
        if hasattr(self, 'select_target_btn'):
            self.select_target_btn.setStyleSheet(self.style_mgr.get_button_style())
        
        # 清除目标按钮
        if hasattr(self, 'clear_target_btn'):
            self.clear_target_btn.setStyleSheet(self.style_mgr.get_button_style("danger"))
        
        # 清除命令按钮
        if hasattr(self, 'clear_cmd_btn'):
            self.clear_cmd_btn.setStyleSheet(self.style_mgr.get_button_style())
        
        # 浏览按钮
        if hasattr(self, 'browse_btn'):
            self.browse_btn.setStyleSheet(self.style_mgr.get_button_style())
        
        # 命令输入框 - 使用最小化的自定义样式
        if hasattr(self, 'cmd_entry'):
            cmd_entry_style = """
                QLineEdit {
                    padding: 8px;
                    border-radius: 4px;
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                }
            """
            self.cmd_entry.setStyleSheet(cmd_entry_style)
        
        # 执行命令按钮
        if hasattr(self, 'cmd_btn'):
            self.cmd_btn.setStyleSheet(self.style_mgr.get_button_style("primary"))
        
        # 更新目标标签样式
        if hasattr(self, 'target_label') and not self.current_target_path:
            self._update_target_label_style(False)

    def _apply_integrated_components_styles(self):
        """为集成的组件应用样式"""
        # 为插件管理器应用样式
        if hasattr(self, 'package_manager') and self.package_manager:
            if hasattr(self.package_manager, 'style_mgr'):
                self.package_manager.style_mgr = self.style_mgr
            # 为插件管理器应用全局样式
            self.style_mgr.apply_global_style(self.package_manager)
        
        # 为软件源管理器应用样式
        if hasattr(self, 'repo_manager_widget') and self.repo_manager_widget:
            if hasattr(self.repo_manager_widget, 'style_mgr'):
                self.repo_manager_widget.style_mgr = self.style_mgr
            # 为软件源管理器应用全局样式
            self.style_mgr.apply_global_style(self.repo_manager_widget)

    def update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.setWindowTitle(self.lang_mgr.get_text("app_title"))

        # 更新标签文本
        if hasattr(self, 'info_label'):
            self.info_label.setText(self.lang_mgr.get_text("tip_drag_drop"))
        if hasattr(self, 'drop_label'):
            self.drop_label.setText(self.lang_mgr.get_text("drop_zone_hint"))

        # 更新按钮文本
        if hasattr(self, 'unpack_btn'):
            self.unpack_btn.setText(self.lang_mgr.get_text("unpack_deb"))
        if hasattr(self, 'repack_btn'):
            self.repack_btn.setText(self.lang_mgr.get_text("repack_folder"))
        if hasattr(self, 'clear_log_btn'):
            self.clear_log_btn.setText(self.lang_mgr.get_text("clear_log"))
        if hasattr(self, 'cmd_btn'):
            self.cmd_btn.setText(self.lang_mgr.get_text("execute"))
        if hasattr(self, 'clear_cmd_btn'):
            self.clear_cmd_btn.setText(self.lang_mgr.get_text("clear"))
            self.clear_cmd_btn.setToolTip(self.lang_mgr.get_text("clear_command"))
        if hasattr(self, 'browse_btn'):
            self.browse_btn.setText(self.lang_mgr.get_text("browse"))
        if hasattr(self, 'select_target_btn'):
            self.select_target_btn.setText(self.lang_mgr.get_text("select_target_file"))
        if hasattr(self, 'clear_target_btn'):
            self.clear_target_btn.setText(self.lang_mgr.get_text("clear"))
            self.clear_target_btn.setToolTip(self.lang_mgr.get_text("clear_target_selection"))
        
        # 更新目标标签（如果没有选择目标）
        if hasattr(self, 'target_label') and not self.current_target_path:
            self.target_label.setText(self.lang_mgr.get_text("no_target_selected"))

        # 更新组框标题
        # 直接更新已知的组框，避免复杂的字符串匹配
        if hasattr(self, 'log_group'):
            self.log_group.setTitle(self.lang_mgr.get_text("operation_log"))
        if hasattr(self, 'cmd_group'):
            self.cmd_group.setTitle(self.lang_mgr.get_text("command_line"))
        if hasattr(self, 'drop_group'):
            self.drop_group.setTitle(self.lang_mgr.get_text("drop_zone"))

        # 更新占位符文本
        if hasattr(self, 'cmd_entry'):
            self.cmd_entry.setPlaceholderText(self.lang_mgr.get_text("cmd_placeholder"))

        # 更新快捷命令
        self.update_command_presets()

        # 重建菜单栏
        self.setup_menu_bar()
        

        # 更新状态栏
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(self.lang_mgr.get_text("ready"))

        # 更新集成组件的语言
        if hasattr(self, 'package_manager') and self.package_manager:
            if hasattr(self.package_manager, 'update_language'):
                self.package_manager.update_language(self.lang_mgr)
        
        if hasattr(self, 'repo_manager_widget') and self.repo_manager_widget:
            if hasattr(self.repo_manager_widget, 'update_language'):
                self.repo_manager_widget.update_language(self.lang_mgr)
        
        if hasattr(self, 'terminal_widget') and self.terminal_widget:
            if hasattr(self.terminal_widget, 'update_language'):
                self.terminal_widget.update_language(self.lang_mgr)
        
        # 更新选项卡标题
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setTabText(0, self.lang_mgr.get_text("deb_tools"))
            self.tab_widget.setTabText(1, self.lang_mgr.get_text("package_manager"))
            self.tab_widget.setTabText(2, self.lang_mgr.get_text("manage_sources"))
            self.tab_widget.setTabText(3, self.lang_mgr.get_text("command_tools"))
        
        # 重新应用样式
        self.apply_styles()

        self.log(f"Language switched to: {self.lang_mgr.get_language_name()}", "info")
        
    def _debug_menu_structure(self, menubar):
        """调试菜单结构"""
        print(f"DEBUG: Total menus created: {len(menubar.actions())}")
        for action in menubar.actions():
            menu = action.menu()
            if menu:
                print(f"DEBUG: Menu '{action.text()}' with {len(menu.actions())} actions")
                # 显示 Help 菜单的详细内容
                if "help" in action.text().lower() or "帮助" in action.text():
                    print(f"DEBUG: Help menu items:")
                    for i, item in enumerate(menu.actions()):
                        if item.isSeparator():
                            print(f"  {i}: --- separator ---")
                        else:
                            print(f"  {i}: '{item.text()}' (enabled: {item.isEnabled()})")
        
    def open_documentation(self):
        """打开文档链接"""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://github.com/Evil0ctal/SimpleTweakEditor/wiki"))
        
    def open_github(self):
        """打开 GitHub 链接"""
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl("https://github.com/Evil0ctal/SimpleTweakEditor"))

    # 拖放事件处理
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.style_mgr.update_drop_zone_style(self.drop_label, True)

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.style_mgr.update_drop_zone_style(self.drop_label, False)

    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        self.style_mgr.update_drop_zone_style(self.drop_label, False)

        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    self.app_core.process_dropped_item(file_path)
            event.acceptProposedAction()

    def restore_window_state(self):
        """恢复窗口状态"""
        window_config = self.config_mgr.get_window_config()
        width = window_config.get("width", 800)
        height = window_config.get("height", 600)
        maximized = window_config.get("maximized", False)

        self.resize(width, height)
        
        # 将窗口居中显示
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)
        
        if maximized:
            self.showMaximized()
    
    def center_window(self):
        """强制居中窗口"""
        if self.isMaximized():
            return
            
        # 获取屏幕几何
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        
        # 获取当前窗口大小
        window_rect = self.frameGeometry()
        
        # 计算居中位置
        x = (screen.width() - window_rect.width()) // 2 + screen.x()
        y = (screen.height() - window_rect.height()) // 2 + screen.y()
        
        # 确保窗口不会超出屏幕边界
        x = max(screen.x(), min(x, screen.x() + screen.width() - window_rect.width()))
        y = max(screen.y(), min(y, screen.y() + screen.height() - window_rect.height()))
        
        self.move(x, y)
    
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        # 动态调整布局
        QTimer.singleShot(0, self.adjust_dynamic_layout)
    
    def adjust_dynamic_layout(self):
        """动态调整布局以适应窗口大小"""
        if not hasattr(self, 'tab_widget'):
            return
            
        window_width = self.width()
        window_height = self.height()
        
        # 根据窗口大小调整组件
        if window_width < 800:
            # 窄屏模式：隐藏一些不必要的标签
            self.optimize_for_narrow_screen()
        else:
            # 宽屏模式：恢复正常布局
            self.optimize_for_wide_screen()
        
        # 调整终端分割器比例
        if hasattr(self, 'terminal_widget') and hasattr(self.terminal_widget, 'splitter'):
            if window_height < 600:
                # 矮屏：减少快捷面板高度
                self.terminal_widget.splitter.setSizes([window_height - 200, 100])
            else:
                # 正常高度：恢复默认比例
                self.terminal_widget.splitter.setSizes([window_height - 250, 200])
    
    def optimize_for_narrow_screen(self):
        """为窄屏优化布局"""
        if hasattr(self, 'info_label'):
            self.info_label.setWordWrap(True)
        
        # 如果有工具栏，隐藏一些不重要的按钮文本
        if hasattr(self, 'terminal_widget'):
            terminal = self.terminal_widget
            if hasattr(terminal, 'clear_btn'):
                terminal.clear_btn.setText("Clear")
            if hasattr(terminal, 'stop_btn'):
                terminal.stop_btn.setText("Stop")
            if hasattr(terminal, 'cd_btn'):
                terminal.cd_btn.setText("CD")
    
    def optimize_for_wide_screen(self):
        """为宽屏恢复正常布局"""
        if hasattr(self, 'info_label'):
            self.info_label.setWordWrap(True)
        
        # 恢复完整的按钮文本
        if hasattr(self, 'terminal_widget'):
            terminal = self.terminal_widget
            if hasattr(terminal, 'clear_btn') and hasattr(terminal, 'lang_mgr'):
                terminal.clear_btn.setText(terminal.lang_mgr.get_text("clear"))
            if hasattr(terminal, 'stop_btn') and hasattr(terminal, 'lang_mgr'):
                terminal.stop_btn.setText(terminal.lang_mgr.get_text("stop"))
            if hasattr(terminal, 'cd_btn') and hasattr(terminal, 'lang_mgr'):
                terminal.cd_btn.setText(terminal.lang_mgr.get_text("change_directory"))

    def save_window_state(self):
        """保存窗口状态"""
        if not self.isMaximized():
            self.config_mgr.set_window_config(
                self.width(),
                self.height(),
                self.isMaximized()
            )

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止正在运行的命令
        if self.current_command_thread and self.current_command_thread.isRunning():
            self.current_command_thread.stop()
            self.current_command_thread.wait()

        # 停止应用核心的操作
        if hasattr(self, 'app_core') and self.app_core:
            self.app_core.stop_current_operation()
        
        # 停止设备面板
        if hasattr(self, 'device_panel') and self.device_panel:
            # 触发设备面板的关闭事件以清理线程
            self.device_panel.close()

        # 保存窗口状态
        self.save_window_state()
    
    
    def open_repo_manager(self):
        """打开软件源管理器"""
        try:
            # 检查是否已有实例
            if self.dialogs['repo_manager'] and self.dialogs['repo_manager'].isVisible():
                # 如果窗口已存在且可见，激活它
                self.dialogs['repo_manager'].raise_()
                self.dialogs['repo_manager'].activateWindow()
                return
            
            from src.ui.repo_manager_dialog import RepoManagerDialog
            
            # 获取或创建 repo_manager
            if not hasattr(self.app_core, 'repo_manager'):
                from src.core.repo_manager import RepoManager
                app_dir = self.app_core.config_mgr.config_dir
                self.app_core.repo_manager = RepoManager(app_dir)
            
            # 创建并显示源管理器
            dialog = RepoManagerDialog(self, self.app_core.repo_manager, self.lang_mgr)
            
            # 连接关闭信号，清理引用
            dialog.finished.connect(lambda: self.on_dialog_closed('repo_manager'))
            
            # 如果包管理器已打开，在关闭源管理器时更新它
            if self.dialogs['package_manager'] and self.dialogs['package_manager'].isVisible():
                dialog.finished.connect(lambda: self.update_package_manager())
            
            # 保存引用
            self.dialogs['repo_manager'] = dialog
            
            dialog.show()  # 使用 show() 而不是 exec()，允许非模态显示
        except ImportError as e:
            self.log(f"Error: Repository manager module not found: {e}", "error")
            QMessageBox.critical(self, "Error", "Repository manager feature is not available.")
        except Exception as e:
            self.log(f"Error opening repository manager: {e}", "error")
            QMessageBox.critical(self, "Error", f"Failed to open repository manager: {str(e)}")
    
    def on_package_downloaded(self, file_path):
        """处理下载完成的包"""
        self.log(f"[DEBUG] Downloaded package: {file_path}")
        
        # 询问是否解包
        reply = QMessageBox.question(self,
                                   self.lang_mgr.get_text("unpack_confirm"),
                                   self.lang_mgr.get_text("unpack_question").format(os.path.basename(file_path)))
        
        if reply == QMessageBox.StandardButton.Yes:
            self.app_core.process_dropped_item(file_path)
    
    def unpack_deb(self):
        """解包deb文件"""
        self.app_core.unpack_deb_dialog()
    
    def repack_deb(self):
        """重打包为deb文件"""
        self.app_core.repack_folder_dialog()
    
    def open_control_editor(self):
        """打开Control编辑器"""
        try:
            from src.ui.control_editor import ControlEditorDialog
            dialog = ControlEditorDialog(self, self.lang_mgr)
            dialog.exec()
        except Exception as e:
            self.log(f"Error opening Control Editor: {str(e)}", "error")
            QMessageBox.critical(self, self.lang_mgr.get_text("error"), str(e))
    
    def open_plist_editor(self):
        """打开Plist编辑器"""
        try:
            # 检查是否已有实例
            if hasattr(self, 'plist_editor') and self.plist_editor:
                try:
                    if self.plist_editor.isVisible():
                        # 如果窗口已存在且可见，激活它
                        self.plist_editor.raise_()
                        self.plist_editor.activateWindow()
                        return
                except RuntimeError:
                    # 窗口已被销毁，清理引用
                    self.plist_editor = None
            
            from src.ui.plist_editor import ImprovedPlistEditor
            
            # 创建并显示Plist编辑器，传递语言管理器和样式管理器
            self.plist_editor = ImprovedPlistEditor(self, self.lang_mgr, self.style_mgr)
            
            # 连接关闭信号，清理引用
            # 当窗口被销毁时清理引用
            self.plist_editor.destroyed.connect(lambda: setattr(self, 'plist_editor', None))
            
            self.plist_editor.show()
            
        except ImportError as e:
            self.log(f"Failed to import Plist Editor: {str(e)}", "error")
            QMessageBox.critical(self, self.lang_mgr.get_text("error"), str(e))
        except Exception as e:
            self.log(f"Error opening Plist Editor: {str(e)}", "error")
            QMessageBox.critical(self, self.lang_mgr.get_text("error"), str(e))
    
    def open_package_manager(self):
        """打开插件管理器（新的整合界面）"""
        try:
            # 检查是否已有实例
            if self.dialogs['package_manager'] and self.dialogs['package_manager'].isVisible():
                # 如果窗口已存在且可见，激活它
                self.dialogs['package_manager'].raise_()
                self.dialogs['package_manager'].activateWindow()
                return
            
            from src.ui.package_manager_widget import PackageManagerWidget
            
            # 获取或创建 repo_manager
            if not hasattr(self.app_core, 'repo_manager'):
                from src.core.repo_manager import RepoManager
                app_dir = self.app_core.config_mgr.config_dir
                self.app_core.repo_manager = RepoManager(app_dir)
            
            # 创建并显示插件管理器
            dialog = PackageManagerWidget(self, self.app_core.repo_manager, self.lang_mgr)
            dialog.package_downloaded.connect(self.on_package_downloaded)
            
            # 连接关闭信号，清理引用
            dialog.finished.connect(lambda: self.on_dialog_closed('package_manager'))
            
            # 保存引用
            self.dialogs['package_manager'] = dialog
            
            dialog.show()
        except ImportError as e:
            self.log(f"Error: Package manager module not found: {e}", "error")
            QMessageBox.critical(self, "Error", "Package manager feature is not available.")
        except Exception as e:
            self.log(f"Error opening package manager: {e}", "error")
            QMessageBox.critical(self, "Error", f"Failed to open package manager: {str(e)}")
    
    def open_source_manager(self):
        """打开软件源管理器（保留以兼容）"""
        self.open_package_manager()
    
    def on_dialog_closed(self, dialog_name):
        """对话框关闭时的处理"""
        self.dialogs[dialog_name] = None
    
    def update_package_manager(self):
        """更新包管理器（当源管理器修改后）"""
        if self.dialogs['package_manager'] and hasattr(self.dialogs['package_manager'], 'update_source_menu'):
            self.dialogs['package_manager'].update_source_menu()
            self.dialogs['package_manager'].load_all_packages()
    
        
        # 如果包管理器已打开，刷新显示
        if self.dialogs['package_manager'] and self.dialogs['package_manager'].isVisible():
            self.dialogs['package_manager'].load_all_packages()
    
    def on_device_connected(self, device):
        """设备连接时的处理"""
        self.log(f"iOS device connected: {device.name} ({device.model})")
        self.status_bar.showMessage(f"Device connected: {device.name}", 5000)
    
    def on_device_disconnected(self):
        """设备断开时的处理"""
        self.log("iOS device disconnected")
        self.status_bar.showMessage("Device disconnected", 5000)
