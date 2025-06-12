# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
统一的iproxy进程管理器，使用单例模式管理所有USB设备的端口转发。
自动分配端口，管理进程生命周期，避免端口冲突。

英文介绍:
Unified iproxy process manager using singleton pattern to manage port forwarding for all USB devices.
Automatic port allocation, process lifecycle management, and port conflict avoidance.
"""

import subprocess
import socket
import threading
import time
import logging
import platform
from typing import Dict, Optional, Tuple

# Windows subprocess flags to prevent console windows
if platform.system() == 'Windows':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

logger = logging.getLogger(__name__)


class IProxyManager:
    """iproxy进程管理器 - 单例模式"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._processes: Dict[str, subprocess.Popen] = {}  # device_id -> process
        self._ports: Dict[str, int] = {}  # device_id -> port
        self._lock = threading.Lock()
        self._base_port = 2222
        self._max_port = 2250
        
        # 检查iproxy是否可用
        self._check_iproxy_available()
    
    @property
    def active_proxies(self):
        """获取活动的代理列表"""
        with self._lock:
            # 清理已结束的进程
            dead_devices = []
            for device_id, process in self._processes.items():
                if process.poll() is not None:
                    dead_devices.append(device_id)
            
            for device_id in dead_devices:
                self._cleanup_device(device_id)
            
            return self._processes
    
    def _check_iproxy_available(self) -> bool:
        """检查iproxy是否可用"""
        try:
            # On Windows, use 'where' instead of 'which'
            cmd = 'where' if platform.system() == 'Windows' else 'which'
            kwargs = {'capture_output': True, 'text': True}
            if platform.system() == 'Windows':
                kwargs['creationflags'] = CREATE_NO_WINDOW
            
            result = subprocess.run([cmd, 'iproxy'], **kwargs)
            if result.returncode == 0:
                logger.info("iproxy is available")
                return True
            else:
                logger.warning("iproxy not found, please install libimobiledevice")
                return False
        except Exception as e:
            logger.error(f"Failed to check iproxy: {str(e)}")
            return False
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # 连接失败说明端口可用
        except:
            return False
    
    def _find_available_port(self) -> Optional[int]:
        """找到一个可用的端口"""
        for port in range(self._base_port, self._max_port):
            if port not in self._ports.values() and self._is_port_available(port):
                return port
        return None
    
    def start_proxy(self, device_id: str) -> Optional[int]:
        """为设备启动iproxy并返回端口"""
        with self._lock:
            # 如果已有进程在运行，返回现有端口
            if device_id in self._processes:
                process = self._processes[device_id]
                if process.poll() is None:  # 进程仍在运行
                    logger.info(f"Reusing existing iproxy for {device_id} on port {self._ports[device_id]}")
                    return self._ports[device_id]
                else:
                    # 进程已结束，清理
                    self._cleanup_device(device_id)
            
            # 找一个可用端口
            port = self._find_available_port()
            if not port:
                logger.error("No available ports")
                return None
            
            # 启动iproxy
            try:
                cmd = ['iproxy', str(port), '22']
                # 注意：如果设备ID不存在，iproxy会卡住
                # 所以先不指定设备ID，让iproxy自动选择
                # if device_id and device_id != 'any':
                #     cmd.extend(['-u', device_id])
                
                logger.info(f"Starting iproxy: {' '.join(cmd)}")
                
                kwargs = {
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.PIPE,
                    'stdin': subprocess.PIPE
                }
                if platform.system() == 'Windows':
                    kwargs['creationflags'] = CREATE_NO_WINDOW
                
                process = subprocess.Popen(cmd, **kwargs)
                
                # 等待进程启动
                time.sleep(3.0)  # 增加等待时间到SSH直接测试中使用的值
                
                # 检查进程是否仍在运行
                if process.poll() is None:
                    self._processes[device_id] = process
                    self._ports[device_id] = port
                    logger.info(f"iproxy started successfully on port {port}")
                    
                    # 等待端口就绪，增加超时时间
                    if self._wait_for_port(port, timeout=10):
                        # 额外等待确保iproxy完全就绪
                        time.sleep(1.0)
                        return port
                    else:
                        logger.error(f"Port {port} not ready after starting iproxy")
                        self._cleanup_device(device_id)
                        return None
                else:
                    stderr = process.stderr.read().decode() if process.stderr else ""
                    logger.error(f"iproxy failed to start: {stderr}")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to start iproxy: {str(e)}", exc_info=True)
                return None
    
    def _wait_for_port(self, port: int, timeout: int = 10) -> bool:
        """等待端口可达"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 检查iproxy进程是否还在运行
                if hasattr(self, '_processes') and port in self._ports.values():
                    for device_id, p in self._processes.items():
                        if self._ports.get(device_id) == port and p.poll() is not None:
                            logger.error(f"iproxy process died for port {port}")
                            return False
                
                # 尝试连接端口
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    if result == 0:
                        logger.debug(f"Port {port} is reachable")
                        return True
                    else:
                        logger.debug(f"Port {port} not ready yet (error: {result})")
            except Exception as e:
                logger.debug(f"Port check exception: {str(e)}")
            
            time.sleep(0.5)  # 增加等待时间
        
        logger.error(f"Timeout waiting for port {port}")
        return False
    
    def stop_proxy(self, device_id: str):
        """停止设备的iproxy进程"""
        with self._lock:
            self._cleanup_device(device_id)
    
    def _cleanup_device(self, device_id: str):
        """清理设备相关资源"""
        if device_id in self._processes:
            process = self._processes[device_id]
            try:
                process.terminate()
                process.wait(timeout=3)
            except:
                try:
                    process.kill()
                except:
                    pass
            del self._processes[device_id]
        
        if device_id in self._ports:
            del self._ports[device_id]
            
        logger.info(f"Cleaned up iproxy for device {device_id}")
    
    def cleanup_all(self):
        """清理所有iproxy进程"""
        with self._lock:
            device_ids = list(self._processes.keys())
            for device_id in device_ids:
                self._cleanup_device(device_id)
    
    def get_device_port(self, device_id: str) -> Optional[int]:
        """获取设备的端口"""
        with self._lock:
            return self._ports.get(device_id)
    
    def __del__(self):
        """析构时清理所有进程"""
        self.cleanup_all()