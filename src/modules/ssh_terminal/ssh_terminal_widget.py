# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
简化的SSH终端Widget，直接集成SSH客户端和终端模拟器。
提供完整的终端体验，包括命令历史、自动补全、ANSI颜色支持等。

英文介绍:
Simplified SSH terminal widget with direct integration of SSH client and terminal emulator.
Provides complete terminal experience including command history, auto-completion, ANSI color support, etc.
"""

import logging
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QLineEdit, QLabel, QPushButton, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QKeyEvent, QTextCharFormat, QColor

from .ssh_client import SSHClient, ConnectionInfo
from .terminal_emulator import TerminalEmulator
from .iproxy_manager import IProxyManager

logger = logging.getLogger(__name__)


class SSHTerminalWidget(QWidget):
    """SSH终端Widget"""
    
    # 信号
    connection_established = pyqtSignal(str)  # device_name
    connection_lost = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ssh_client = SSHClient()
        self.terminal = None
        self.iproxy_manager = IProxyManager()
        self.device_id = None
        self.device_name = "Unknown Device"
        
        self._setup_ui()
        self._setup_connections()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 终端输出区域
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
            }
        """)
        layout.addWidget(self.output_area)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        # 提示符标签
        self.prompt_label = QLabel("$ ")
        self.prompt_label.setFont(QFont("Consolas", 10))
        self.prompt_label.setStyleSheet("color: #569cd6; background-color: #1e1e1e; padding: 5px;")
        input_layout.addWidget(self.prompt_label)
        
        # 命令输入框
        self.input_line = QLineEdit()
        self.input_line.setFont(QFont("Consolas", 10))
        self.input_line.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 5px;
            }
        """)
        self.input_line.returnPressed.connect(self._on_command_entered)
        input_layout.addWidget(self.input_line)
        
        layout.addLayout(input_layout)
        
    def _setup_connections(self):
        """设置信号连接"""
        self.ssh_client.connected.connect(self._on_connected)
        self.ssh_client.disconnected.connect(self._on_disconnected)
        self.ssh_client.connection_error.connect(self._on_connection_error)
        # 移除command_output信号连接，避免重复输出
        # self.ssh_client.command_output.connect(self._on_command_output)
        
    def connect_device(self, device_info: dict, username: str, password: str) -> bool:
        """连接设备"""
        self.device_id = device_info.get('identifier')
        self.device_name = device_info.get('name', 'Unknown Device')
        
        # 构建连接信息
        if device_info.get('connection_type') == 'usb':
            # USB连接，启动iproxy
            port = self.iproxy_manager.start_proxy(self.device_id)
            if not port:
                self._append_output("Failed to start port forwarding\n", error=True)
                return False
                
            conn_info = ConnectionInfo(
                host='localhost',
                port=port,
                username=username,
                password=password,
                device_id=self.device_id,
                connection_type='usb'
            )
        else:
            # WiFi连接
            conn_info = ConnectionInfo(
                host=device_info.get('host'),
                port=device_info.get('port', 22),
                username=username,
                password=password,
                device_id=self.device_id,
                connection_type='wifi'
            )
        
        # 显示连接信息
        self._append_output(f"Connecting to {self.device_name}...\n")
        
        # 连接
        return self.ssh_client.connect(conn_info)
    
    def disconnect(self):
        """断开连接"""
        if self.ssh_client:
            self.ssh_client.disconnect()
            
        if self.device_id:
            self.iproxy_manager.stop_proxy(self.device_id)
            
    def _on_connected(self):
        """连接成功"""
        self._append_output("Connected successfully!\n", color="#4ec9b0")
        
        # 创建终端模拟器
        self.terminal = TerminalEmulator(self.ssh_client)
        
        # 获取真实的设备名称
        self._update_device_name()
        
        # 更新提示符
        self._update_prompt()
        
        # 显示欢迎信息
        self._show_welcome_message()
        
        # 启用输入
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        
        self.connection_established.emit(self.device_name)
        
    def _on_disconnected(self):
        """连接断开"""
        self._append_output("\nDisconnected\n", color="#f48771")
        self.input_line.setEnabled(False)
        self.terminal = None
        self.connection_lost.emit()
        
    def _on_connection_error(self, error: str):
        """连接错误"""
        self._append_output(f"Connection error: {error}\n", error=True)
        
    # 移除了_on_command_output方法，因为命令输出现在直接在_on_command_entered中处理
            
    def _on_command_entered(self):
        """处理命令输入"""
        command = self.input_line.text().strip()
        if not command:
            return
            
        # 清空输入框
        self.input_line.clear()
        
        # 显示命令
        prompt = self.prompt_label.text()
        self._append_output(f"{prompt}{command}\n", color="#569cd6")
        
        # 处理特殊命令
        if command.lower() in ['exit', 'quit']:
            self.disconnect()
            return
            
        if command == 'clear':
            self.output_area.clear()
            return
            
        # 执行命令
        if self.terminal:
            stdout, stderr, is_internal = self.terminal.execute_command(command)
            
            if not is_internal:
                if stdout:
                    self._append_output(stdout)
                if stderr:
                    self._append_output(stderr, error=True)
                    
            # 更新提示符
            self._update_prompt()
            
    def _update_prompt(self):
        """更新命令提示符"""
        if self.terminal:
            prompt = self.terminal.get_prompt()
            self.prompt_label.setText(prompt)
        else:
            self.prompt_label.setText("$ ")
    
    def _update_device_name(self):
        """从设备获取真实的设备名称"""
        if not self.ssh_client.is_connected:
            return
            
        # 尝试从uname获取设备名称
        stdout, _ = self.ssh_client.execute_command("uname -n")
        if stdout and stdout.strip():
            hostname = stdout.strip()
            # 某些设备可能返回类似 "Evil0ctal-iPhone-SE.local" 的格式
            if hostname.endswith('.local'):
                hostname = hostname[:-6]  # 移除.local后缀
            
            # 更新设备名称
            if hostname and hostname != 'iPhone':  # 如果不是通用名称
                self.device_name = hostname
                logger.info(f"Updated device name to: {self.device_name}")
            
    def _show_welcome_message(self):
        """显示欢迎信息"""
        if self.terminal:
            # 获取系统信息
            stdout, _ = self.ssh_client.execute_command("uname -a")
            if stdout:
                self._append_output(stdout)
                
            # 获取当前目录
            stdout, _ = self.ssh_client.execute_command("pwd")
            if stdout:
                self._append_output(f"Current directory: {stdout}")
                
            self._append_output("\n")
            
    def _append_output(self, text: str, color: str = None, error: bool = False):
        """添加输出文本"""
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 设置文本格式
        format = QTextCharFormat()
        if error:
            format.setForeground(QColor("#f48771"))  # 红色
        elif color:
            format.setForeground(QColor(color))
        else:
            format.setForeground(QColor("#d4d4d4"))  # 默认颜色
            
        cursor.insertText(text, format)
        
        # 滚动到底部
        self.output_area.setTextCursor(cursor)
        self.output_area.ensureCursorVisible()
        
    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        # 确保焦点在输入框时才处理特殊键
        if self.input_line.hasFocus():
            if not self.terminal:
                return super().keyPressEvent(event)
                
            # 处理Tab键自动补全
            if event.key() == Qt.Key.Key_Tab:
                self._handle_tab_completion()
                return
                
            # 处理历史命令
            if event.key() == Qt.Key.Key_Up:
                history_cmd = self.terminal.get_history_prev()
                if history_cmd is not None:
                    self.input_line.setText(history_cmd)
                    self.input_line.setCursorPosition(len(history_cmd))
                return
            elif event.key() == Qt.Key.Key_Down:
                history_cmd = self.terminal.get_history_next()
                if history_cmd is not None:
                    self.input_line.setText(history_cmd)
                    self.input_line.setCursorPosition(len(history_cmd))
                return
        
        super().keyPressEvent(event)
    
    def _handle_tab_completion(self):
        """处理Tab补全"""
        current_text = self.input_line.text()
        if not current_text:
            return
        
        # 获取补全建议
        completions = self.terminal.get_completions(current_text)
        
        if not completions:
            return
        
        if len(completions) == 1:
            # 只有一个补全，直接应用
            self.input_line.setText(completions[0])
            self.input_line.setCursorPosition(len(completions[0]))
        else:
            # 多个补全，显示选项
            self._show_completions(completions)
            
            # 找出公共前缀
            common_prefix = self._find_common_prefix(completions)
            if common_prefix and len(common_prefix) > len(current_text):
                self.input_line.setText(common_prefix)
                self.input_line.setCursorPosition(len(common_prefix))
    
    def _show_completions(self, completions: List[str]):
        """显示补全选项"""
        # 在输出区域显示补全选项
        self._append_output("\n", color="#ffffff")
        
        # 格式化显示
        max_width = max(len(c) for c in completions) + 2
        columns = max(1, 80 // max_width)  # 假设终端宽度为80
        
        for i in range(0, len(completions), columns):
            row = completions[i:i+columns]
            row_text = "".join(c.ljust(max_width) for c in row)
            self._append_output(row_text + "\n", color="#98c379")
        
        # 重新显示提示符和当前输入
        prompt = self.prompt_label.text()
        current = self.input_line.text()
        self._append_output(f"{prompt}{current}", color="#569cd6")
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """找出字符串列表的公共前缀"""
        if not strings:
            return ""
        
        # 使用第一个字符串作为基准
        prefix = strings[0]
        
        for s in strings[1:]:
            # 逐字符比较，找出公共前缀
            i = 0
            while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
                i += 1
            prefix = prefix[:i]
            
            if not prefix:
                break
        
        return prefix
            
    def execute_command(self, command: str):
        """执行命令（供外部调用）"""
        if self.ssh_client.is_connected and self.terminal:
            # 显示命令
            prompt = self.prompt_label.text()
            self._append_output(f"{prompt}{command}\n", color="#569cd6")
            
            # 执行命令
            stdout, stderr, is_internal = self.terminal.execute_command(command)
            
            if not is_internal:
                if stdout:
                    self._append_output(stdout)
                if stderr:
                    self._append_output(stderr, error=True)
                    
            # 更新提示符
            self._update_prompt()
            
    def closeEvent(self, event):
        """关闭事件"""
        self.disconnect()
        super().closeEvent(event)
