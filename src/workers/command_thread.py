# -*- coding: utf-8 -*-
"""
命令执行线程模块
负责在后台执行命令行操作
"""

import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtCore import pyqtSignal as Signal
else:
    Signal = pyqtSignal


class CommandThread(QThread):
    """
    执行命令的后台线程
    """
    output_received: Signal = pyqtSignal(str, str)  # 信号: (文本, 标签)
    command_finished: Signal = pyqtSignal(int)  # 信号: 返回码
    error_message: Signal = pyqtSignal(str)  # 信号: 错误消息

    def __init__(self, command, lang_mgr=None):
        super().__init__()
        self.command = command
        self.lang_mgr = lang_mgr
        self._should_stop = False

    def stop(self):
        """停止命令执行"""
        self._should_stop = True
        if hasattr(self, 'process'):
            try:
                self.process.terminate()
            except Exception:
                pass

    def get_error_text(self, error):
        """获取错误文本（本地化）"""
        if self.lang_mgr:
            return self.lang_mgr.format_text("cmd_exec_error", error)
        return f"Error executing command: {error}"

    def run(self):
        """运行命令"""
        try:
            # 创建子进程
            self.process = subprocess.Popen(
                self.command,
                shell=True if isinstance(self.command, str) else False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )

            # 等待进程完成并获取所有输出
            stdout, stderr = self.process.communicate()
            
            # 发送标准输出
            if stdout:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        self.output_received.emit(line, "normal")
            
            # 发送标准错误输出
            if stderr:
                for line in stderr.strip().split('\n'):
                    if line.strip():
                        self.output_received.emit(line, "error")

            # 获取返回码
            return_code = self.process.returncode

            if not self._should_stop:
                self.command_finished.emit(return_code)

        except FileNotFoundError:
            error_msg = "Command not found"
            if self.lang_mgr:
                error_msg = self.lang_mgr.get_text("cmd_exec_error")
            self.output_received.emit(error_msg, "error")
            self.command_finished.emit(1)

        except Exception as e:
            error_msg = self.get_error_text(str(e))
            self.output_received.emit(error_msg, "error")
            self.command_finished.emit(1)


class PackageOperationThread(QThread):
    """
    包操作线程的基类
    """
    progress_message: Signal = pyqtSignal(str, str)  # 信号: (消息, 标签)
    operation_finished: Signal = pyqtSignal(bool, str, str)  # 信号: (成功, 消息, 路径)

    def __init__(self):
        super().__init__()
        self._should_stop = False

    def stop(self):
        """停止操作"""
        self._should_stop = True
        self.quit()
        self.wait(3000)  # 等待最多3秒

    def emit_progress(self, message, tag="info"):
        """发送进度消息"""
        self.progress_message.emit(message, tag)
    
    def __del__(self):
        """析构函数 - 确保线程正确退出"""
        if self.isRunning():
            self.stop()


class UnpackThread(PackageOperationThread):
    """解包操作线程"""

    def __init__(self, deb_path, output_dir, unpack_function):
        super().__init__()
        self.deb_path = deb_path
        self.output_dir = output_dir
        self.unpack_function = unpack_function

    def run(self):
        """执行解包操作"""
        try:
            if self._should_stop:
                return

            self.emit_progress("Starting unpack operation...", "info")

            # 执行解包函数
            success, message, target_dir = self.unpack_function(self.deb_path, self.output_dir)

            if not self._should_stop:
                self.operation_finished.emit(success, message, target_dir or "")

        except Exception as e:
            if not self._should_stop:
                self.operation_finished.emit(False, str(e), "")


class PackThread(PackageOperationThread):
    """打包操作线程"""

    def __init__(self, folder_path, output_path, pack_function):
        super().__init__()
        self.folder_path = folder_path
        self.output_path = output_path
        self.pack_function = pack_function

    def run(self):
        """执行打包操作"""
        try:
            if self._should_stop:
                return

            self.emit_progress("Starting pack operation...", "info")

            # 执行打包函数
            success, message = self.pack_function(self.folder_path, self.output_path)

            if not self._should_stop:
                self.operation_finished.emit(success, message, self.output_path)

        except Exception as e:
            if not self._should_stop:
                self.operation_finished.emit(False, str(e), "")
