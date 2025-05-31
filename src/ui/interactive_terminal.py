# -*- coding: utf-8 -*-
"""
交互式终端组件
提供完整的终端功能和快捷命令支持
"""

import os
import sys
import subprocess
import shlex
from pathlib import Path
from PyQt6.QtCore import Qt, QProcess, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QToolButton,
    QMenu, QFileDialog, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QApplication
)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QAction

# Import our dpkg wrapper for cross-platform support
from ..utils.terminal_dpkg_wrapper import handle_dpkg_command, handle_which_dpkg


class InteractiveTerminal(QWidget):
    """交互式终端组件"""
    
    command_executed = pyqtSignal(str)  # 命令执行信号
    
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.process = None
        self.current_dir = os.getcwd()
        self.command_history = []
        self.history_index = -1
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部：终端区域（主要部分）
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        terminal_layout.setContentsMargins(5, 5, 5, 5)
        terminal_layout.setSpacing(5)
        
        # 工具栏
        self.create_toolbar(terminal_layout)
        
        # 终端输出
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        # Terminal will use theme colors
        self.terminal_output.setObjectName("terminalOutput")
        # Apply custom selection style to fix highlight visibility
        self.terminal_output.setStyleSheet("""
            QTextEdit#terminalOutput {
                font-family: Monaco, Menlo, 'DejaVu Sans Mono', 'Courier New', monospace;
                font-size: 13px;
                padding: 10px;
                selection-background-color: #4a86e8;
                selection-color: #ffffff;
                border: none;
            }
        """)
        terminal_layout.addWidget(self.terminal_output)
        
        # 命令输入区域
        input_widget = QWidget()
        input_widget.setStyleSheet("""
            QWidget {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 5px;
                padding: 5px;
            }
        """)
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(5)
        
        # 当前目录标签
        self.dir_label = QLabel(f"{os.path.basename(self.current_dir)}>")
        self.dir_label.setProperty("class", "success-label")
        self.dir_label.setToolTip(self.current_dir)
        # 使用系统中可用的等宽字体
        font = QFont()
        font.setFamily("Monaco, Menlo, Consolas, 'DejaVu Sans Mono', monospace")
        font.setPointSize(11)
        font.setBold(True)
        self.dir_label.setFont(font)
        self.dir_label.setMinimumWidth(80)
        input_layout.addWidget(self.dir_label)
        
        # 命令输入框
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background-color: transparent;
                font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                font-size: 13px;
                padding: 2px;
            }
        """)
        self.command_input.setPlaceholderText("Enter command...")
        input_layout.addWidget(self.command_input)
        
        # 执行按钮
        exec_text = self.lang_mgr.get_text("execute") if self.lang_mgr else "Run"
        self.exec_btn = QPushButton(exec_text)
        self.exec_btn.clicked.connect(self.execute_command)
        self.exec_btn.setProperty("class", "primary")
        self.exec_btn.setMinimumSize(70, 32)
        self.exec_btn.setMaximumHeight(32)
        input_layout.addWidget(self.exec_btn)
        
        terminal_layout.addWidget(input_widget)
        
        splitter.addWidget(terminal_widget)
        
        # 下部：快捷操作面板（可折叠）
        quick_panel = self.create_quick_panel()
        quick_panel.setMinimumHeight(150)  # 设置最小高度确保内容显示完整
        splitter.addWidget(quick_panel)
        
        # 设置分割比例 - 终端占主要空间
        splitter.setStretchFactor(0, 3)  # 终端区域
        splitter.setStretchFactor(1, 1)  # 快捷面板
        splitter.setSizes([500, 200])  # 设置初始大小，给快捷面板更多空间
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 显示欢迎信息
        self.show_welcome()
    
    def create_quick_panel(self):
        """创建快捷操作面板"""
        panel = QWidget()
        # 使用水平布局，让面板更紧凑
        main_layout = QHBoxLayout(panel)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 左侧：目标选择
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)
        
        # 移除标题，节省空间
        
        # 目标选择组（不使用 GroupBox 节省空间）
        target_label = QLabel(self.lang_mgr.get_text("target_selection") if self.lang_mgr else "Target:")
        target_label.setProperty("class", "secondary")
        left_layout.addWidget(target_label)
        
        target_layout = QVBoxLayout()
        target_layout.setSpacing(3)
        
        # 选择文件按钮
        select_file_text = self.lang_mgr.get_text("select_file") if self.lang_mgr else "Select File"
        self.select_file_btn = QPushButton(select_file_text)
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setMinimumHeight(32)
        target_layout.addWidget(self.select_file_btn)
        
        # 选择目录按钮
        select_dir_text = self.lang_mgr.get_text("select_directory") if self.lang_mgr else "Select Directory"
        self.select_dir_btn = QPushButton(select_dir_text)
        self.select_dir_btn.clicked.connect(self.select_directory)
        self.select_dir_btn.setMinimumHeight(32)
        target_layout.addWidget(self.select_dir_btn)
        
        # 当前目标显示
        self.target_label = QLabel(self.lang_mgr.get_text("no_target_selected") if self.lang_mgr else "No target selected")
        self.target_label.setWordWrap(True)
        self.target_label.setProperty("class", "secondary")
        # 移除高度限制，改为自适应
        self.target_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 3px;
            }
        """)
        target_layout.addWidget(self.target_label)
        
        # 将目标选择布局添加到左侧布局
        left_layout.addLayout(target_layout)
        left_layout.addStretch()
        
        # 右侧：快捷命令
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        
        cmd_label = QLabel(self.lang_mgr.get_text("preset_commands") if self.lang_mgr else "Quick Commands:")
        cmd_label.setProperty("class", "secondary")
        right_layout.addWidget(cmd_label)
        
        # 命令列表
        self.cmd_list = QListWidget()
        self.cmd_list.itemDoubleClicked.connect(self.execute_preset_command)
        self.cmd_list.setAlternatingRowColors(True)
        # 移除高度限制，使用最小高度代替
        self.cmd_list.setMinimumHeight(100)
        right_layout.addWidget(self.cmd_list)
        
        # 更新命令列表
        self.update_command_list()
        
        # 将左右布局添加到主布局
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        
        return panel
    
    def create_toolbar(self, layout):
        """创建工具栏"""
        toolbar_widget = QWidget()
        toolbar_widget.setMaximumHeight(50)
        toolbar_widget.setMinimumHeight(50)
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: palette(window);
                border: 1px solid palette(mid);
                border-radius: 5px;
                margin: 2px;
            }
            QPushButton {
                padding: 5px 10px;
                border: 1px solid palette(mid);
                border-radius: 3px;
                background-color: palette(button);
            }
            QPushButton:hover {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            QPushButton:pressed {
                background-color: palette(dark);
            }
        """)
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(8, 8, 8, 8)
        toolbar.setSpacing(10)
        
        # 清除按钮
        clear_text = self.lang_mgr.get_text("clear") if self.lang_mgr else "Clear"
        self.clear_btn = QPushButton(clear_text)
        self.clear_btn.clicked.connect(self.clear_terminal)
        self.clear_btn.setMinimumSize(80, 32)
        self.clear_btn.setMaximumHeight(32)
        toolbar.addWidget(self.clear_btn)
        
        # 停止按钮
        stop_text = self.lang_mgr.get_text("stop") if self.lang_mgr else "Stop"
        self.stop_btn = QPushButton(stop_text)
        self.stop_btn.clicked.connect(self.stop_process)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumSize(80, 32)
        self.stop_btn.setMaximumHeight(32)
        self.stop_btn.setProperty("class", "danger")
        toolbar.addWidget(self.stop_btn)
        
        # 切换目录按钮
        cd_text = self.lang_mgr.get_text("change_directory") if self.lang_mgr else "Change Directory"
        self.cd_btn = QPushButton(cd_text)
        self.cd_btn.clicked.connect(self.change_directory)
        self.cd_btn.setMinimumSize(140, 32)
        self.cd_btn.setMaximumHeight(32)
        toolbar.addWidget(self.cd_btn)
        
        toolbar.addStretch()
        
        # 主题切换（终端颜色）
        theme_text = self.lang_mgr.get_text("terminal_theme") if self.lang_mgr else "Theme:"
        theme_label = QLabel(theme_text)
        theme_label.setMinimumWidth(50)
        toolbar.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Default", "Dark", "Light", "Matrix", "Ocean"])
        self.theme_combo.currentTextChanged.connect(self.change_terminal_theme)
        self.theme_combo.setMinimumWidth(100)
        self.theme_combo.setMaximumWidth(120)
        toolbar.addWidget(self.theme_combo)
        
        layout.addWidget(toolbar_widget)
    
    def show_welcome(self):
        """显示欢迎信息"""
        welcome_text = self.lang_mgr.get_text("terminal_welcome") if self.lang_mgr else "Interactive Terminal Ready"
        self.append_output(f"{'='*60}\n{welcome_text}\n{'='*60}\n", "info")
        self.append_output(f"Current Directory: {self.current_dir}\n\n", "success")
        
        # Add usage hints
        if self.lang_mgr and self.lang_mgr.current_language == "zh":
            hints = [
                "💡 使用提示:",
                "  • 双击左侧命令列表快速执行",
                "  • 选择文件/目录后会显示相关命令",
                "  • 使用 ↑/↓ 键浏览命令历史",
                "  • 支持所有系统 shell 命令",
                "  • DEB 相关命令已加粗显示\n"
            ]
        else:
            hints = [
                "💡 Usage Tips:",
                "  • Double-click commands on the left for quick execution",
                "  • Select a file/directory to see related commands",
                "  • Use ↑/↓ keys to browse command history",
                "  • All system shell commands are supported",
                "  • DEB-related commands are shown in bold\n"
            ]
        
        for hint in hints:
            self.append_output(hint + "\n", "normal")
    
    def update_command_list(self):
        """更新命令列表"""
        self.cmd_list.clear()
        
        # 根据当前目标更新命令
        if hasattr(self, 'current_target') and self.current_target:
            commands = self.get_target_commands()
        else:
            commands = self.get_general_commands()
        
        for cmd_name, cmd_template in commands:
            item = QListWidgetItem(cmd_name)
            item.setData(Qt.ItemDataRole.UserRole, cmd_template)
            item.setToolTip(cmd_template)  # Show command as tooltip
            # Make deb-related commands stand out
            if any(keyword in cmd_name.lower() or keyword in cmd_template.lower() 
                   for keyword in ['deb', 'dpkg', 'package', 'control', 'debian']):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.cmd_list.addItem(item)
    
    def get_general_commands(self):
        """获取通用命令"""
        # Windows 平台特殊命令
        if sys.platform == "win32":
            if self.lang_mgr:
                return [
                    # 文件系统命令
                    (self.lang_mgr.get_text("cmd_list_files"), "dir /a"),
                    (self.lang_mgr.get_text("cmd_show_pwd"), "cd"),
                    (self.lang_mgr.get_text("cmd_disk_usage"), "wmic logicaldisk get size,freespace,caption"),
                    (self.lang_mgr.get_text("cmd_system_info"), "systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\""),
                    # DEB 包管理命令
                    (self.lang_mgr.get_text("cmd_find_deb_files"), "dir /s /b *.deb"),
                    ("List .deb in current dir", "dir *.deb 2>nul || echo No .deb files found"),
                    ("Check dpkg-deb (Python)", "which dpkg-deb"),
                    # DEB 构建命令
                    (self.lang_mgr.get_text("cmd_validate_control"), "type DEBIAN\\control 2>nul || echo No control file found"),
                    ("Show directory tree", "tree /F"),
                ]
            else:
                return [
                    # File system commands
                    ("List files", "dir /a"),
                    ("Show current directory", "cd"),
                    ("Disk usage", "wmic logicaldisk get size,freespace,caption"),
                    ("System info", "systeminfo | findstr /B /C:\"OS Name\" /C:\"OS Version\""),
                    # DEB package management
                    ("Find .deb files", "dir /s /b *.deb"),
                    ("List .deb in current dir", "dir *.deb 2>nul || echo No .deb files found"),
                    ("Check dpkg-deb (Python)", "which dpkg-deb"),
                    # DEB building commands
                    ("Validate control file", "type DEBIAN\\control 2>nul || echo No control file found"),
                    ("Show directory tree", "tree /F"),
                ]
        # Unix/Linux/macOS 平台命令
        else:
            if self.lang_mgr:
                return [
                    # 文件系统命令
                    (self.lang_mgr.get_text("cmd_list_files"), "ls -la"),
                    (self.lang_mgr.get_text("cmd_show_pwd"), "pwd"),
                    (self.lang_mgr.get_text("cmd_disk_usage"), "df -h"),
                    (self.lang_mgr.get_text("cmd_system_info"), "uname -a"),
                    # DEB 包管理命令
                    (self.lang_mgr.get_text("cmd_find_deb_files"), "find . -name '*.deb'"),
                    (self.lang_mgr.get_text("cmd_list_packages"), "dpkg -l | grep -E '^ii'"),
                    (self.lang_mgr.get_text("cmd_check_architecture"), "dpkg --print-architecture"),
                    (self.lang_mgr.get_text("cmd_list_repos"), "ls -la /etc/apt/sources.list.d/"),
                    # DEB 构建命令
                    (self.lang_mgr.get_text("cmd_check_dpkg_deb"), "which dpkg-deb"),
                    (self.lang_mgr.get_text("cmd_validate_control"), "cat DEBIAN/control 2>/dev/null || echo 'No control file found'"),
                ]
            else:
                return [
                    # File system commands
                    ("List files", "ls -la"),
                    ("Show current directory", "pwd"),
                    ("Disk usage", "df -h"),
                    ("System info", "uname -a"),
                    # DEB package management
                    ("Find .deb files", "find . -name '*.deb'"),
                    ("List installed packages", "dpkg -l | grep -E '^ii'"),
                    ("Check architecture", "dpkg --print-architecture"),
                    ("List APT repositories", "ls -la /etc/apt/sources.list.d/"),
                    # DEB building commands
                    ("Check dpkg-deb", "which dpkg-deb"),
                    ("Validate control file", "cat DEBIAN/control 2>/dev/null || echo 'No control file found'"),
                ]
    
    def get_target_commands(self):
        """获取目标相关命令"""
        target = self.current_target
        is_file = os.path.isfile(target)
        is_deb = target.lower().endswith('.deb')
        
        commands = []
        
        # Windows 平台特殊处理
        if sys.platform == "win32":
            if is_file:
                if is_deb:
                    # .deb 文件命令 - 在Windows上使用Python实现
                    if self.lang_mgr:
                        commands.extend([
                            (self.lang_mgr.get_text("cmd_view_deb_info"), f'dpkg-deb -I "{target}"'),
                            (self.lang_mgr.get_text("cmd_list_deb_contents"), f'dpkg-deb -c "{target}"'),
                            (self.lang_mgr.get_text("cmd_extract_deb"), f'dpkg-deb -x "{target}" .'),
                            (self.lang_mgr.get_text("cmd_extract_control"), f'dpkg-deb -e "{target}" DEBIAN'),
                        ])
                    else:
                        commands.extend([
                            ("View package info", f'dpkg-deb -I "{target}"'),
                            ("List package contents", f'dpkg-deb -c "{target}"'),
                            ("Extract package", f'dpkg-deb -x "{target}" .'),
                            ("Extract control files", f'dpkg-deb -e "{target}" DEBIAN'),
                        ])
                else:
                    # 普通文件命令
                    if self.lang_mgr:
                        commands.extend([
                            (self.lang_mgr.get_text("cmd_view_file"), f'type "{target}"'),
                            ("File size", f'dir "{target}"'),
                        ])
                    else:
                        commands.extend([
                            ("View file", f'type "{target}"'),
                            ("File size", f'dir "{target}"'),
                        ])
            else:
                # 目录命令
                if self.lang_mgr:
                    commands.extend([
                        (self.lang_mgr.get_text("cmd_list_directory"), f'dir "{target}" /a'),
                        ("Directory tree", f'tree "{target}" /F'),
                        ("Find control file", f'dir /s /b "{target}\\*control*"'),
                        (self.lang_mgr.get_text("cmd_pack_deb"), f'dpkg-deb -b "{target}" output.deb'),
                    ])
                else:
                    commands.extend([
                        ("List directory", f'dir "{target}" /a'),
                        ("Directory tree", f'tree "{target}" /F'),
                        ("Find control file", f'dir /s /b "{target}\\*control*"'),
                        ("Pack as .deb", f'dpkg-deb -b "{target}" output.deb'),
                    ])
        # Unix/Linux/macOS 平台
        else:
            if is_file:
                if is_deb:
                    # .deb 文件命令
                    if self.lang_mgr:
                        commands.extend([
                            (self.lang_mgr.get_text("cmd_view_deb_info"), f"dpkg-deb -I '{target}'"),
                            (self.lang_mgr.get_text("cmd_list_deb_contents"), f"dpkg-deb -c '{target}'"),
                            (self.lang_mgr.get_text("cmd_extract_deb"), f"dpkg-deb -x '{target}' ."),
                            (self.lang_mgr.get_text("cmd_extract_control"), f"dpkg-deb -e '{target}' DEBIAN"),
                        ])
                    else:
                        commands.extend([
                            ("View package info", f"dpkg-deb -I '{target}'"),
                            ("List package contents", f"dpkg-deb -c '{target}'"),
                            ("Extract package", f"dpkg-deb -x '{target}' ."),
                            ("Extract control files", f"dpkg-deb -e '{target}' DEBIAN"),
                        ])
                else:
                    # 普通文件命令
                    if self.lang_mgr:
                        commands.extend([
                            (self.lang_mgr.get_text("cmd_view_file"), f"cat '{target}'"),
                            (self.lang_mgr.get_text("cmd_file_info"), f"file '{target}'"),
                            (self.lang_mgr.get_text("cmd_file_size"), f"ls -lh '{target}'"),
                        ])
                    else:
                        commands.extend([
                            ("View file", f"cat '{target}'"),
                            ("File info", f"file '{target}'"),
                            ("File size", f"ls -lh '{target}'"),
                        ])
            else:
                # 目录命令
                if self.lang_mgr:
                    commands.extend([
                        (self.lang_mgr.get_text("cmd_list_directory"), f"ls -la '{target}'"),
                        (self.lang_mgr.get_text("cmd_directory_size"), f"du -sh '{target}'"),
                        (self.lang_mgr.get_text("cmd_find_control"), f"find '{target}' -name control"),
                        (self.lang_mgr.get_text("cmd_pack_deb"), f"dpkg-deb -b '{target}' output.deb"),
                    ])
                else:
                    commands.extend([
                        ("List directory", f"ls -la '{target}'"),
                        ("Directory size", f"du -sh '{target}'"),
                        ("Find control file", f"find '{target}' -name control"),
                        ("Pack as .deb", f"dpkg-deb -b '{target}' output.deb"),
                    ])
        
        return commands
    
    def select_file(self):
        """选择文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.lang_mgr.get_text("select_file") if self.lang_mgr else "Select File",
            self.current_dir
        )
        if file_path:
            self.current_target = file_path
            self.target_label.setText(os.path.basename(file_path))
            self.update_command_list()
    
    def select_directory(self):
        """选择目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            self.lang_mgr.get_text("select_directory") if self.lang_mgr else "Select Directory",
            self.current_dir
        )
        if dir_path:
            self.current_target = dir_path
            self.target_label.setText(os.path.basename(dir_path))
            self.update_command_list()
    
    def execute_preset_command(self, item):
        """执行预设命令"""
        command = item.data(Qt.ItemDataRole.UserRole)
        if command:
            self.command_input.setText(command)
            self.execute_command()
    
    def execute_command(self):
        """执行命令"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        # 添加到历史
        self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # 显示命令
        self.append_output(f"\n{self.current_dir}> {command}\n", "command")
        
        # 清空输入
        self.command_input.clear()
        
        # 处理内置命令
        if self.handle_builtin_command(command):
            return
        
        # 执行外部命令
        self.run_external_command(command)
    
    def handle_builtin_command(self, command):
        """处理内置命令"""
        parts = shlex.split(command)
        if not parts:
            return False
        
        cmd = parts[0].lower()
        
        # cd 命令
        if cmd == "cd":
            if len(parts) > 1:
                try:
                    new_dir = os.path.expanduser(parts[1])
                    if not os.path.isabs(new_dir):
                        new_dir = os.path.join(self.current_dir, new_dir)
                    new_dir = os.path.normpath(new_dir)
                    
                    if os.path.isdir(new_dir):
                        self.current_dir = new_dir
                        os.chdir(self.current_dir)
                        self.dir_label.setText(f"{os.path.basename(self.current_dir)}>")
                        self.dir_label.setToolTip(self.current_dir)
                        self.append_output(f"Changed directory to: {self.current_dir}\n", "success")
                    else:
                        self.append_output(f"Directory not found: {new_dir}\n", "error")
                except Exception as e:
                    self.append_output(f"Error: {str(e)}\n", "error")
            else:
                self.append_output(f"Current directory: {self.current_dir}\n", "info")
            return True
        
        # clear 命令
        elif cmd in ["clear", "cls"]:
            self.clear_terminal()
            return True
        
        # exit 命令
        elif cmd == "exit":
            self.append_output("Use the close button to exit the terminal.\n", "info")
            return True
        
        return False
    
    def run_external_command(self, command):
        """运行外部命令"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.append_output("A command is already running. Please wait or stop it.\n", "error")
            return
        
        # 检查是否是which dpkg-deb命令
        if command.strip() in ['which dpkg-deb', 'which dpkg', 'where dpkg-deb', 'where dpkg']:
            handled, output, error = handle_which_dpkg()
            if handled:
                if output:
                    self.append_output(output, "normal")
                if error:
                    self.append_output(error, "error")
                return
        
        # 尝试处理dpkg命令
        handled, output, error = handle_dpkg_command(command, self.current_dir)
        if handled:
            if output:
                self.append_output(output, "normal")
            if error:
                self.append_output(error, "error")
            return
        
        self.process = QProcess()
        self.process.setWorkingDirectory(self.current_dir)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.command_finished)
        self.process.started.connect(self.command_started)
        
        # 使用系统环境变量
        # QProcess 默认继承父进程的环境变量，所以不需要显式设置
        
        # 根据平台选择 shell
        if sys.platform == "win32":
            # Windows: 设置正确的编码
            self.process.setProcessEnvironment(self.setup_windows_environment())
            self.process.start("cmd", ["/c", command])
        else:
            self.process.start("sh", ["-c", command])
    
    def command_started(self):
        """命令开始执行"""
        self.stop_btn.setEnabled(True)
        self.exec_btn.setEnabled(False)
    
    def command_finished(self, exit_code, exit_status):
        """命令执行完成"""
        self.stop_btn.setEnabled(False)
        self.exec_btn.setEnabled(True)
        
        if exit_code != 0:
            self.append_output(f"\nCommand exited with code: {exit_code}\n", "error")
        else:
            self.append_output(f"\nCommand completed successfully.\n", "success")
    
    def handle_stdout(self):
        """处理标准输出"""
        if self.process:
            data = self.process.readAllStandardOutput()
            # Windows 中文编码处理
            if sys.platform == "win32":
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                    try:
                        text = bytes(data).decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    text = bytes(data).decode('utf-8', errors='replace')
            else:
                text = bytes(data).decode('utf-8', errors='replace')
            self.append_output(text, "normal")
    
    def handle_stderr(self):
        """处理标准错误"""
        if self.process:
            data = self.process.readAllStandardError()
            # Windows 中文编码处理
            if sys.platform == "win32":
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'cp936']:
                    try:
                        text = bytes(data).decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    text = bytes(data).decode('utf-8', errors='replace')
            else:
                text = bytes(data).decode('utf-8', errors='replace')
            self.append_output(text, "error")
    
    def append_output(self, text, style="normal"):
        """添加输出到终端"""
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 设置文本格式
        format = QTextCharFormat()
        
        # Use palette colors that adapt to theme
        palette = self.terminal_output.palette()
        
        if style == "command":
            format.setForeground(palette.highlight().color())
            format.setFontWeight(QFont.Weight.Bold)
        elif style == "error":
            format.setForeground(QColor("#ff6666"))
        elif style == "success":
            format.setForeground(QColor("#66bb66"))
        elif style == "info":
            format.setForeground(palette.link().color())
        else:
            # Use default text color from palette
            format.setForeground(palette.text().color())
        
        cursor.insertText(text, format)
        
        # 滚动到底部
        self.terminal_output.setTextCursor(cursor)
        self.terminal_output.ensureCursorVisible()
    
    def stop_process(self):
        """停止当前进程"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.terminate()
            QTimer.singleShot(2000, self.force_kill_process)
    
    def force_kill_process(self):
        """强制杀死进程"""
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
    
    def clear_terminal(self):
        """清除终端"""
        self.terminal_output.clear()
        self.show_welcome()
    
    def change_directory(self):
        """改变工作目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            self.lang_mgr.get_text("select_directory") if self.lang_mgr else "Select Directory",
            self.current_dir
        )
        if dir_path:
            self.current_dir = dir_path
            os.chdir(self.current_dir)
            self.dir_label.setText(f"{os.path.basename(self.current_dir)}>")
            self.dir_label.setToolTip(self.current_dir)
            self.append_output(f"Changed directory to: {self.current_dir}\n", "success")
    
    def setup_windows_environment(self):
        """设置 Windows 环境变量"""
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        
        # 设置 UTF-8 编码
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("CHCP", "65001")  # UTF-8 code page
        
        return env
    
    def change_terminal_theme(self, theme):
        """改变终端主题"""
        # Keep the default theme from qt-material
        if theme == "Default":
            self.terminal_output.setStyleSheet("""
                QTextEdit#terminalOutput {
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                    font-size: 13px;
                    padding: 10px;
                    selection-background-color: #4a86e8;
                    selection-color: #ffffff;
                    border: none;
                }
            """)
            return
            
        themes = {
            "Dark": {
                "bg": "#1e1e1e",
                "fg": "#ffffff",
                "selection_bg": "#4a86e8",
                "selection_fg": "#ffffff"
            },
            "Light": {
                "bg": "#ffffff",
                "fg": "#000000",
                "selection_bg": "#0066cc",
                "selection_fg": "#ffffff"
            },
            "Matrix": {
                "bg": "#000000",
                "fg": "#00ff00",
                "selection_bg": "#00aa00",
                "selection_fg": "#000000"
            },
            "Ocean": {
                "bg": "#0c1f2c",
                "fg": "#b7c5d3",
                "selection_bg": "#2e6da4",
                "selection_fg": "#ffffff"
            }
        }
        
        if theme in themes:
            colors = themes[theme]
            self.terminal_output.setStyleSheet(f"""
                QTextEdit#terminalOutput {{
                    background-color: {colors['bg']};
                    color: {colors['fg']};
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                    font-size: 13px;
                    padding: 10px;
                    selection-background-color: {colors['selection_bg']};
                    selection-color: {colors['selection_fg']};
                    border: none;
                }}
            """)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key.Key_Up:
            # 历史命令 - 上一条
            if self.history_index > 0:
                self.history_index -= 1
                self.command_input.setText(self.command_history[self.history_index])
        elif event.key() == Qt.Key.Key_Down:
            # 历史命令 - 下一条
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_input.setText(self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.command_input.clear()
        else:
            super().keyPressEvent(event)
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        
        # 更新按钮文本
        self.exec_btn.setText(lang_mgr.get_text("execute"))
        self.clear_btn.setText(lang_mgr.get_text("clear"))
        self.stop_btn.setText(lang_mgr.get_text("stop"))
        self.cd_btn.setText(lang_mgr.get_text("change_directory"))
        self.select_file_btn.setText(lang_mgr.get_text("select_file"))
        self.select_dir_btn.setText(lang_mgr.get_text("select_directory"))
        
        # 更新命令列表
        self.update_command_list()
    
    def optimize_layout_for_size(self, width, height):
        """根据容器大小优化布局"""
        if not hasattr(self, 'splitter'):
            return
            
        if width < 600:
            # 窄屏模式：减少快捷面板高度
            self.splitter.setSizes([height - 150, 100])
        else:
            # 宽屏模式：恢复正常比例
            self.splitter.setSizes([height - 200, 150])
    
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        # 动态优化布局
        QTimer.singleShot(0, lambda: self.optimize_layout_for_size(self.width(), self.height()))
