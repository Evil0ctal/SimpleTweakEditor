# -*- coding: utf-8 -*-
"""
主窗口UI模块
包含应用程序的主用户界面
"""

import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QTextCursor, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QSplitter, QStatusBar, QComboBox, QFileDialog
)

from .styles import StyleManager
from .control_editor import ControlEditorDialog
from src.workers.command_thread import CommandThread
from src.utils.system_utils import open_folder, is_valid_deb_file, is_valid_package_folder


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self, app_core):
        super().__init__()
        self.app_core = app_core
        self.lang_mgr = app_core.lang_mgr
        self.config_mgr = app_core.config_mgr
        self.style_mgr = StyleManager()

        # 当前运行的命令线程
        self.current_command_thread = None

        # 初始化UI
        self.setupUI()
        self.setup_menu_bar()
        self.restore_window_state()

        # 应用样式
        self.apply_styles()

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

        # 创建UI组件
        self.create_info_section(main_layout)
        self.create_button_section(main_layout)
        self.create_drop_zone(main_layout)
        self.create_main_content(main_layout)
        self.create_status_bar()

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

        self.drop_label = QLabel(self.lang_mgr.get_text("drop_zone"))
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setMinimumHeight(100)
        self.drop_label.setProperty("dropZone", True)
        drop_layout.addWidget(self.drop_label)

        layout.addWidget(self.drop_group)

    def create_main_content(self, layout):
        """创建主要内容区域"""
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 日志区域
        self.create_log_section(splitter)

        # 命令行区域
        self.create_command_section(splitter)

        # 设置分隔器大小
        sizes = self.config_mgr.get_splitter_sizes()
        splitter.setSizes(sizes)

        # 保存分隔器状态
        splitter.splitterMoved.connect(
            lambda pos, index: self.config_mgr.set_splitter_sizes(splitter.sizes())
        )

        layout.addWidget(splitter)

    def create_log_section(self, parent):
        """创建日志区域"""
        self.log_group = QGroupBox(self.lang_mgr.get_text("operation_log"))
        log_layout = QVBoxLayout(self.log_group)

        # 日志工具栏
        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()

        self.clear_log_btn = QPushButton(self.lang_mgr.get_text("clear_log"))
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_toolbar.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_toolbar)

        # 日志文本区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)

        parent.addWidget(self.log_group)

    def create_command_section(self, parent):
        """创建命令行区域"""
        self.cmd_group = QGroupBox(self.lang_mgr.get_text("command_line"))
        cmd_layout = QVBoxLayout(self.cmd_group)

        # 快捷命令工具栏
        self.create_command_toolbar(cmd_layout)

        # 命令输入区域
        self.create_command_input(cmd_layout)

        parent.addWidget(self.cmd_group)

    def create_command_toolbar(self, layout):
        """创建命令工具栏"""
        # 第一行：目标选择
        target_toolbar = QHBoxLayout()
        
        # 目标选择按钮
        self.select_target_btn = QPushButton(self.lang_mgr.get_text("select_target_file"))
        # self.select_target_btn.setMaximumWidth(120)
        self.select_target_btn.clicked.connect(self.select_target)
        target_toolbar.addWidget(self.select_target_btn)
        
        # 当前选择的目标显示
        target_text = self.lang_mgr.get_text("no_target_selected") or "No target selected"
        self.target_label = QLabel(target_text)
        self.target_label.setStyleSheet("color: gray; font-style: italic; padding: 4px; border: 1px solid #ddd; border-radius: 3px;")
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
        self.clear_target_btn.setStyleSheet("""
            QPushButton { 
                font-weight: bold; 
                color: #d32f2f;
                border: 1px solid #d32f2f;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
            QPushButton:pressed {
                background-color: #ffcdd2;
            }
        """)
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

        # 语言切换子菜单
        self.create_language_menu(settings_menu)

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
        version_action = QAction("Version 1.0.0", self)
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
        if index > 0:  # 跳过标题项
            command = self.cmd_presets.itemData(index)
            if command:
                self.cmd_entry.setText(command)
            self.cmd_presets.setCurrentIndex(0)  # 重置到默认选项

    def clear_command(self):
        """清除命令输入"""
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
        self.target_label.setStyleSheet("color: #1976d2; font-weight: bold; padding: 4px; border: 1px solid #1976d2; border-radius: 3px; background-color: #e3f2fd;")
        
        # 更新快捷命令
        self.update_command_presets()
        
        self.log(f"Target selected: {target_path}", "info")
    
    def clear_target(self):
        """清除目标选择"""
        self.current_target_path = None
        target_text = self.lang_mgr.get_text("no_target_selected") or "No target selected"
        self.target_label.setText(target_text)
        self.target_label.setStyleSheet("color: gray; font-style: italic; padding: 4px; border: 1px solid #ddd; border-radius: 3px;")
        self.target_label.setToolTip("")
        self.update_command_presets()

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

        self.log(f"{self.lang_mgr.get_text('execute')}: {command}", "info")

        # 停止之前的命令
        if self.current_command_thread and self.current_command_thread.isRunning():
            self.current_command_thread.stop()
            self.current_command_thread.wait()

        # 创建并启动新的命令线程
        self.current_command_thread = CommandThread(command, self.lang_mgr)
        self.current_command_thread.output_received.connect(self.handle_command_output)
        self.current_command_thread.command_finished.connect(self.handle_command_finished)
        self.current_command_thread.start()

    def handle_special_commands(self, command):
        """处理特殊命令"""
        if command.startswith("open ") or command.startswith("cd "):
            path = command.split(" ", 1)[1].strip('"').strip("'")
            if os.path.exists(path):
                if os.path.isdir(path):
                    self.log(f"Opening folder: {path}", "info")
                    if open_folder(path):
                        self.log("Folder opened successfully", "success")
                    else:
                        self.log("Failed to open folder", "error")
                    return True
                elif os.path.isfile(path):
                    self.log(f"Opening file: {path}", "info")
                    return True
            else:
                self.log(f"Path not found: {path}", "error")
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

    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.log(self.lang_mgr.get_text("clear_log"), "info")

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

    def update_ui_language(self):
        """更新界面语言"""
        # 更新窗口标题
        self.setWindowTitle(self.lang_mgr.get_text("app_title"))

        # 更新标签文本
        self.info_label.setText(self.lang_mgr.get_text("tip_drag_drop"))
        self.drop_label.setText(self.lang_mgr.get_text("drop_zone"))

        # 更新按钮文本
        self.unpack_btn.setText(self.lang_mgr.get_text("unpack_deb"))
        self.repack_btn.setText(self.lang_mgr.get_text("repack_folder"))
        self.clear_log_btn.setText(self.lang_mgr.get_text("clear_log"))
        self.cmd_btn.setText(self.lang_mgr.get_text("execute"))
        self.clear_cmd_btn.setText(self.lang_mgr.get_text("clear"))
        self.clear_cmd_btn.setToolTip(self.lang_mgr.get_text("clear_command"))
        self.browse_btn.setText(self.lang_mgr.get_text("browse"))
        self.select_target_btn.setText(self.lang_mgr.get_text("select_target_file"))
        self.clear_target_btn.setText(self.lang_mgr.get_text("clear"))
        self.clear_target_btn.setToolTip(self.lang_mgr.get_text("clear_target_selection"))
        
        # 更新目标标签（如果没有选择目标）
        if not self.current_target_path:
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
        self.cmd_entry.setPlaceholderText(self.lang_mgr.get_text("cmd_placeholder"))

        # 更新快捷命令
        self.update_command_presets()

        # 重建菜单栏
        self.setup_menu_bar()
        

        # 更新状态栏
        self.status_bar.showMessage(self.lang_mgr.get_text("ready"))

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
        if maximized:
            self.showMaximized()

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

        # 保存窗口状态
        self.save_window_state()

        event.accept()
