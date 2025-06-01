# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
命令执行线程模块。实现了用于在后台执行命令行操作的线程类，包括CommandThread（通用命令执行）、
UnpackThread（解包操作）和PackThread（打包操作）。这些线程类使用PyQt的信号机制与主UI线程
通信，提供实时输出反馈和操作结果通知。

英文介绍:
Command execution thread module. Implements thread classes for executing command-line operations 
in the background, including CommandThread (general command execution), UnpackThread (unpack 
operations), and PackThread (pack operations). These thread classes use PyQt's signal mechanism 
to communicate with the main UI thread, providing real-time output feedback and operation result 
notifications.
"""

import subprocess
import shlex
from PyQt6.QtCore import QThread, pyqtSignal
from typing import TYPE_CHECKING, Union, List

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

    def __init__(self, command: Union[str, List[str]], lang_mgr=None):
        super().__init__()
        # 安全处理命令输入
        if isinstance(command, str):
            # 如果是字符串，使用shlex.split安全地解析为列表
            try:
                self.command = shlex.split(command)
            except ValueError as e:
                # 如果解析失败，抛出异常
                raise ValueError(f"Invalid command format: {e}")
        elif isinstance(command, list):
            # 如果已经是列表，验证每个元素都是字符串
            if not all(isinstance(arg, str) for arg in command):
                raise ValueError("All command arguments must be strings")
            self.command = command
        else:
            raise TypeError("Command must be a string or list of strings")
        
        self.lang_mgr = lang_mgr
        self._should_stop = False

    def stop(self):
        """停止命令执行"""
        import os
        import signal
        import time
        
        self._should_stop = True
        if hasattr(self, 'process') and self.process.poll() is None:
            try:
                # 首先尝试优雅地终止进程
                self.process.terminate()
                
                # 等待最多5秒让进程自行退出
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 如果进程仍未退出，强制杀死它
                    if os.name == 'posix':
                        # Unix/Linux/Mac: 使用kill信号
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        # Windows: 使用kill
                        self.process.kill()
                    
                    # 再次等待确保进程已死亡
                    self.process.wait(timeout=1)
                    
            except (ProcessLookupError, OSError):
                # 进程可能已经退出
                pass
            except Exception as e:
                # 记录其他错误但不抛出
                print(f"Error stopping process: {e}")

    def get_error_text(self, error):
        """获取错误文本（本地化）"""
        if self.lang_mgr:
            return self.lang_mgr.format_text("cmd_exec_error", error)
        return f"Error executing command: {error}"

    def run(self):
        """运行命令"""
        try:
            # 安全创建子进程 - 永远不使用shell=True
            # command已经在__init__中被安全地转换为列表
            self.process = subprocess.Popen(
                self.command,
                shell=False,  # 永远不使用shell=True，防止命令注入
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True,
                # 添加安全限制
                start_new_session=True  # 在新的会话中运行，便于清理
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
