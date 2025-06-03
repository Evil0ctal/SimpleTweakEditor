# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
简化的SSH客户端实现，使用exec_command模式提供可靠的命令执行。
支持USB和WiFi连接，自动重连，以及完整的错误处理。

英文介绍:
Simplified SSH client implementation using exec_command mode for reliable command execution.
Supports USB and WiFi connections, automatic reconnection, and comprehensive error handling.
"""

import logging
import paramiko
import threading
import time
import socket
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    host: str
    port: int
    username: str
    password: str
    device_id: Optional[str] = None
    connection_type: str = 'usb'  # 'usb' or 'wifi'


class SSHClient(QObject):
    """简化的SSH客户端"""
    
    # 信号定义
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)
    command_output = pyqtSignal(str, str, str)  # command, stdout, stderr
    
    def __init__(self):
        super().__init__()
        self._client: Optional[paramiko.SSHClient] = None
        self._connection_info: Optional[ConnectionInfo] = None
        self._connected = False
        self._lock = threading.Lock()
        self._reconnect_timer = None
        
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._client is not None
        
    def connect(self, connection_info: ConnectionInfo) -> bool:
        """建立SSH连接"""
        with self._lock:
            # 断开现有连接
            if self._client:
                self.disconnect()
            
            # 重试机制
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt + 1}/{max_retries}")
                        time.sleep(retry_delay * attempt)  # 指数退避
                    
                    logger.info(f"Connecting to {connection_info.host}:{connection_info.port} (attempt {attempt + 1})")
                    
                    # 检查端口是否可达
                    if not self._check_port_reachable(connection_info.host, connection_info.port):
                        logger.warning(f"Port {connection_info.port} not reachable")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            raise Exception(f"Port {connection_info.port} not reachable after {max_retries} attempts")
                    
                    # 创建新客户端
                    self._client = paramiko.SSHClient()
                    self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    # 连接
                    self._client.connect(
                        hostname=connection_info.host,
                        port=connection_info.port,
                        username=connection_info.username,
                        password=connection_info.password,
                        timeout=15,  # 增加超时
                        banner_timeout=60,  # 增加banner超时
                        auth_timeout=60,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    
                    self._connection_info = connection_info
                    self._connected = True
                    
                    logger.info("SSH connection established")
                    self.connected.emit()
                    return True
                    
                except paramiko.AuthenticationException:
                    error_msg = "Authentication failed"
                    logger.error(error_msg)
                    self.connection_error.emit(error_msg)
                    return False  # 认证失败不重试
                    
                except paramiko.SSHException as e:
                    if "Error reading SSH protocol banner" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"SSH banner error, will retry: {str(e)}")
                        continue
                    error_msg = f"SSH error: {str(e)}"
                    logger.error(error_msg)
                    self.connection_error.emit(error_msg)
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Connection attempt failed: {str(e)}")
                        continue
                    error_msg = f"Connection failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self.connection_error.emit(error_msg)
            
            return False
    
    def disconnect(self):
        """断开连接"""
        with self._lock:
            if self._client:
                try:
                    self._client.close()
                except:
                    pass
                self._client = None
                
            self._connected = False
            self.disconnected.emit()
            logger.info("SSH connection closed")
    
    def execute_command(self, command: str, timeout: float = 30) -> Tuple[str, str]:
        """执行命令并返回输出"""
        if not self.is_connected:
            logger.error("Not connected")
            return "", "Not connected"
            
        try:
            logger.debug(f"Executing command: {command}")
            
            # 执行命令
            stdin, stdout, stderr = self._client.exec_command(
                command, 
                timeout=timeout
            )
            
            # 读取输出
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            
            # 获取退出状态
            exit_status = stdout.channel.recv_exit_status()
            
            logger.debug(f"Command exit status: {exit_status}")
            logger.debug(f"stdout: {stdout_data[:100]}...")
            logger.debug(f"stderr: {stderr_data[:100]}...")
            
            # 注释掉信号发送，避免重复输出
            # 命令输出会在调用方处理
            # self.command_output.emit(command, stdout_data, stderr_data)
            
            return stdout_data, stderr_data
            
        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return "", error_msg
    
    def execute_command_async(self, command: str, 
                            callback: Optional[Callable[[str, str], None]] = None,
                            timeout: float = 30):
        """异步执行命令"""
        def _execute():
            stdout, stderr = self.execute_command(command, timeout)
            if callback:
                callback(stdout, stderr)
                
        thread = threading.Thread(target=_execute)
        thread.daemon = True
        thread.start()
    
    def test_connection(self) -> bool:
        """测试连接是否正常"""
        if not self.is_connected:
            return False
            
        stdout, stderr = self.execute_command("echo 'connection test'", timeout=5)
        return "connection test" in stdout
    
    def get_transport(self) -> Optional[paramiko.Transport]:
        """获取传输层对象（用于SFTP等）"""
        if self._client:
            return self._client.get_transport()
        return None
    
    def _check_port_reachable(self, host: str, port: int, timeout: float = 3) -> bool:
        """检查端口是否可达"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            logger.error(f"Port check failed: {str(e)}")
            return False