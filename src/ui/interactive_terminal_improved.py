# -*- coding: utf-8 -*-
"""
改进的交互式终端组件
提供真正的终端交互体验，类似于 macOS Terminal 或 SSH 工具
"""

import os
import sys
import pty
import select
import subprocess
import shlex
import fcntl
import termios
import struct
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QByteArray
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QComboBox, QLabel, QToolButton, QSplitter,
    QFileDialog, QApplication, QTabWidget, QMenu
)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QKeyEvent, QPalette


class PtyThread(QThread):
    """PTY 线程，用于运行真正的终端"""
    data_ready = pyqtSignal(bytes)
    process_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.master_fd = None
        self.slave_fd = None
        self.shell_pid = None
        self.running = False
        
    def run(self):
        """运行终端"""
        try:
            # 创建伪终端
            self.master_fd, self.slave_fd = pty.openpty()
            
            # 设置终端大小
            self.set_terminal_size(80, 24)
            
            # 获取 shell
            shell = os.environ.get('SHELL', '/bin/bash')
            
            # Fork 进程
            self.shell_pid = os.fork()
            
            if self.shell_pid == 0:
                # 子进程
                os.close(self.master_fd)
                
                # 设置为会话领导
                os.setsid()
                
                # 设置控制终端
                fcntl.ioctl(self.slave_fd, termios.TIOCSCTTY)
                
                # 重定向标准输入输出到伪终端
                os.dup2(self.slave_fd, 0)
                os.dup2(self.slave_fd, 1)
                os.dup2(self.slave_fd, 2)
                
                # 关闭原始文件描述符
                if self.slave_fd > 2:
                    os.close(self.slave_fd)
                
                # 执行 shell
                os.execv(shell, [shell, '-i'])
            else:
                # 父进程
                os.close(self.slave_fd)
                self.running = True
                
                # 读取终端输出
                while self.running:
                    try:
                        r, _, _ = select.select([self.master_fd], [], [], 0.1)
                        if r:
                            data = os.read(self.master_fd, 1024)
                            if data:
                                self.data_ready.emit(data)
                            else:
                                break
                    except OSError:
                        break
                        
        except Exception as e:
            print(f"PTY error: {e}")
        finally:
            self.cleanup()
            self.process_finished.emit()
    
    def write(self, data):
        """写入数据到终端"""
        if self.master_fd and self.running:
            try:
                os.write(self.master_fd, data)
            except OSError:
                pass
    
    def set_terminal_size(self, cols, rows):
        """设置终端大小"""
        if self.master_fd:
            size = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
    
    def stop(self):
        """停止终端"""
        self.running = False
        if self.shell_pid:
            try:
                os.kill(self.shell_pid, 9)
            except ProcessLookupError:
                pass
    
    def cleanup(self):
        """清理资源"""
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
        self.master_fd = None


class TerminalWidget(QTextEdit):
    """终端显示组件，支持 ANSI 转义序列"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(False)
        font = QFont()
        font.setFamily("Monaco, Menlo, 'DejaVu Sans Mono', monospace")
        font.setPointSize(10)
        self.setFont(font)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                font-size: 13px;
                padding: 10px;
                border: none;
            }
        """)
        
        # ANSI 颜色映射
        self.ansi_colors = {
            30: '#2e3436',  # 黑
            31: '#cc0000',  # 红
            32: '#4e9a06',  # 绿
            33: '#c4a000',  # 黄
            34: '#3465a4',  # 蓝
            35: '#75507b',  # 品红
            36: '#06989a',  # 青
            37: '#d3d7cf',  # 白
            90: '#555753',  # 亮黑
            91: '#ef2929',  # 亮红
            92: '#8ae234',  # 亮绿
            93: '#fce94f',  # 亮黄
            94: '#729fcf',  # 亮蓝
            95: '#ad7fa8',  # 亮品红
            96: '#34e2e2',  # 亮青
            97: '#eeeeec',  # 亮白
        }
        
        self.cursor_position = 0
        self.input_buffer = ""
        
    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘输入"""
        # 获取按键文本
        text = event.text()
        key = event.key()
        
        # 处理特殊按键
        if key == Qt.Key.Key_Return:
            self.parent().send_input(b'\n')
        elif key == Qt.Key.Key_Backspace:
            self.parent().send_input(b'\x7f')
        elif key == Qt.Key.Key_Tab:
            self.parent().send_input(b'\t')
        elif key == Qt.Key.Key_Up:
            self.parent().send_input(b'\x1b[A')
        elif key == Qt.Key.Key_Down:
            self.parent().send_input(b'\x1b[B')
        elif key == Qt.Key.Key_Left:
            self.parent().send_input(b'\x1b[D')
        elif key == Qt.Key.Key_Right:
            self.parent().send_input(b'\x1b[C')
        elif key == Qt.Key.Key_Home:
            self.parent().send_input(b'\x1b[H')
        elif key == Qt.Key.Key_End:
            self.parent().send_input(b'\x1b[F')
        elif key == Qt.Key.Key_Delete:
            self.parent().send_input(b'\x1b[3~')
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C, Ctrl+D 等
            if key >= Qt.Key.Key_A and key <= Qt.Key.Key_Z:
                ctrl_char = chr(key - Qt.Key.Key_A + 1).encode()
                self.parent().send_input(ctrl_char)
        elif text:
            # 普通字符
            self.parent().send_input(text.encode('utf-8'))
        else:
            super().keyPressEvent(event)
    
    def append_data(self, data: bytes):
        """添加数据到终端"""
        try:
            text = data.decode('utf-8', errors='replace')
            
            # 简单处理 ANSI 转义序列
            # 这里只处理最基本的，完整的 ANSI 处理需要更复杂的解析
            text = self.process_ansi_escapes(text)
            
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            
        except Exception as e:
            print(f"Error appending data: {e}")
    
    def process_ansi_escapes(self, text):
        """处理 ANSI 转义序列（简化版）"""
        # 移除一些常见的控制序列
        import re
        
        # 清除屏幕
        text = re.sub(r'\x1b\[2J', '', text)
        # 光标位置
        text = re.sub(r'\x1b\[\d+;\d+H', '', text)
        # 颜色（暂时移除）
        text = re.sub(r'\x1b\[\d+(;\d+)*m', '', text)
        # 其他转义序列
        text = re.sub(r'\x1b\[[^m]*m', '', text)
        
        return text


class InteractiveTerminalImproved(QWidget):
    """改进的交互式终端组件"""
    
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.pty_thread = None
        self.terminals = []  # 存储多个终端标签
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建标签页组件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_terminal_tab)
        
        # 添加新建终端按钮
        new_term_btn = QToolButton()
        new_term_btn.setText("+")
        new_term_btn.setToolTip(self.lang_mgr.get_text("new_terminal") if self.lang_mgr else "New Terminal")
        new_term_btn.clicked.connect(self.create_new_terminal)
        self.tab_widget.setCornerWidget(new_term_btn, Qt.Corner.TopRightCorner)
        
        layout.addWidget(self.tab_widget)
        
        # 创建底部工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        self.setLayout(layout)
        
        # 创建第一个终端
        self.create_new_terminal()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QWidget()
        toolbar.setMaximumHeight(35)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 0, 5, 0)
        
        # 快捷命令菜单
        quick_cmd_btn = QPushButton(self.lang_mgr.get_text("quick_commands") if self.lang_mgr else "Quick Commands")
        quick_cmd_menu = QMenu()
        
        # 添加常用命令
        commands = [
            ("Clear Screen", "clear"),
            ("List Files", "ls -la"),
            ("Show Path", "pwd"),
            ("System Info", "uname -a"),
            ("Network Info", "ifconfig" if sys.platform != "win32" else "ipconfig"),
            ("Process List", "ps aux" if sys.platform != "win32" else "tasklist"),
            ("Disk Usage", "df -h" if sys.platform != "win32" else "wmic logicaldisk get size,freespace,caption"),
        ]
        
        for name, cmd in commands:
            action = quick_cmd_menu.addAction(name)
            action.triggered.connect(lambda checked, c=cmd: self.execute_quick_command(c))
        
        quick_cmd_btn.setMenu(quick_cmd_menu)
        toolbar_layout.addWidget(quick_cmd_btn)
        
        # 分割终端按钮
        split_btn = QPushButton(self.lang_mgr.get_text("split_terminal") if self.lang_mgr else "Split")
        split_menu = QMenu()
        split_menu.addAction("Split Horizontal").triggered.connect(lambda: self.split_terminal('horizontal'))
        split_menu.addAction("Split Vertical").triggered.connect(lambda: self.split_terminal('vertical'))
        split_btn.setMenu(split_menu)
        toolbar_layout.addWidget(split_btn)
        
        # 字体大小调整
        font_label = QLabel(self.lang_mgr.get_text("font_size") if self.lang_mgr else "Font Size:")
        toolbar_layout.addWidget(font_label)
        
        self.font_size_spin = QComboBox()
        self.font_size_spin.addItems(['10', '11', '12', '13', '14', '16', '18', '20'])
        self.font_size_spin.setCurrentText('13')
        self.font_size_spin.setEditable(True)
        self.font_size_spin.setMaximumWidth(60)
        self.font_size_spin.currentTextChanged.connect(self.change_font_size)
        toolbar_layout.addWidget(self.font_size_spin)
        
        toolbar_layout.addStretch()
        
        # 主题选择
        theme_label = QLabel(self.lang_mgr.get_text("theme") if self.lang_mgr else "Theme:")
        toolbar_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Dark', 'Light', 'Matrix', 'Ocean', 'Solarized'])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        toolbar_layout.addWidget(self.theme_combo)
        
        return toolbar
    
    def create_new_terminal(self):
        """创建新终端标签"""
        # 创建终端容器
        terminal_container = QWidget()
        layout = QVBoxLayout(terminal_container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建终端组件
        terminal = TerminalWidget(self)
        layout.addWidget(terminal)
        
        # 创建 PTY 线程
        pty_thread = PtyThread()
        pty_thread.data_ready.connect(terminal.append_data)
        pty_thread.process_finished.connect(lambda: self.on_terminal_closed(terminal_container))
        
        # 保存引用
        terminal_container.terminal = terminal
        terminal_container.pty_thread = pty_thread
        
        # 添加到标签页
        tab_index = self.tab_widget.addTab(
            terminal_container, 
            f"Terminal {self.tab_widget.count() + 1}"
        )
        self.tab_widget.setCurrentIndex(tab_index)
        
        # 启动终端
        pty_thread.start()
        
        # 设置焦点
        terminal.setFocus()
        
        return terminal_container
    
    def close_terminal_tab(self, index):
        """关闭终端标签"""
        if self.tab_widget.count() > 1:
            terminal_container = self.tab_widget.widget(index)
            if hasattr(terminal_container, 'pty_thread'):
                terminal_container.pty_thread.stop()
                terminal_container.pty_thread.wait()
            self.tab_widget.removeTab(index)
    
    def on_terminal_closed(self, terminal_container):
        """终端关闭时的处理"""
        index = self.tab_widget.indexOf(terminal_container)
        if index >= 0:
            self.close_terminal_tab(index)
    
    def send_input(self, data: bytes):
        """发送输入到当前终端"""
        current_terminal = self.get_current_terminal()
        if current_terminal and hasattr(current_terminal, 'pty_thread'):
            current_terminal.pty_thread.write(data)
    
    def get_current_terminal(self):
        """获取当前活动的终端"""
        current_widget = self.tab_widget.currentWidget()
        return current_widget
    
    def execute_quick_command(self, command):
        """执行快捷命令"""
        self.send_input(command.encode('utf-8') + b'\n')
    
    def split_terminal(self, direction):
        """分割终端（未来功能）"""
        # TODO: 实现终端分割功能
        pass
    
    def change_font_size(self, size_str):
        """改变字体大小"""
        try:
            size = int(size_str)
            for i in range(self.tab_widget.count()):
                container = self.tab_widget.widget(i)
                if hasattr(container, 'terminal'):
                    font = container.terminal.font()
                    font.setPointSize(size)
                    container.terminal.setFont(font)
        except ValueError:
            pass
    
    def change_theme(self, theme):
        """改变主题"""
        themes = {
            'Dark': {
                'bg': '#1e1e1e',
                'fg': '#d4d4d4',
                'cursor': '#ffffff',
                'selection': '#264f78'
            },
            'Light': {
                'bg': '#ffffff',
                'fg': '#000000',
                'cursor': '#000000',
                'selection': '#add6ff'
            },
            'Matrix': {
                'bg': '#000000',
                'fg': '#00ff00',
                'cursor': '#00ff00',
                'selection': '#003300'
            },
            'Ocean': {
                'bg': '#002b36',
                'fg': '#839496',
                'cursor': '#839496',
                'selection': '#073642'
            },
            'Solarized': {
                'bg': '#fdf6e3',
                'fg': '#657b83',
                'cursor': '#657b83',
                'selection': '#eee8d5'
            }
        }
        
        if theme in themes:
            colors = themes[theme]
            style = f"""
                QTextEdit {{
                    background-color: {colors['bg']};
                    color: {colors['fg']};
                    font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
                    padding: 10px;
                    border: none;
                    selection-background-color: {colors['selection']};
                }}
            """
            
            for i in range(self.tab_widget.count()):
                container = self.tab_widget.widget(i)
                if hasattr(container, 'terminal'):
                    container.terminal.setStyleSheet(style)
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        # 更新界面文本
        # TODO: 实现语言更新逻辑