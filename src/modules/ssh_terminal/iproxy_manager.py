# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
统一的端口转发管理器，使用单例模式管理所有USB设备的端口转发。
使用 pymobiledevice3 的 TcpForwarder 替代外部 iproxy 工具。
自动分配端口，管理转发器生命周期，避免端口冲突。

英文介绍:
Unified port forwarding manager using singleton pattern to manage port forwarding for all USB devices.
Uses pymobiledevice3's TcpForwarder instead of external iproxy tool.
Automatic port allocation, forwarder lifecycle management, and port conflict avoidance.
"""

import socket
import threading
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Try to import pymobiledevice3 components
try:
    from pymobiledevice3.tcp_forwarder import TcpForwarder
    from pymobiledevice3.lockdown import LockdownClient
    from pymobiledevice3.exceptions import *
    PYMOBILEDEVICE3_AVAILABLE = True
except ImportError:
    PYMOBILEDEVICE3_AVAILABLE = False
    logger.error("pymobiledevice3 not available for port forwarding")
    TcpForwarder = None
    LockdownClient = None


class IProxyManager:
    """端口转发管理器 - 单例模式"""
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
        self._forwarders: Dict[str, TcpForwarder] = {}  # device_id -> TcpForwarder
        self._ports: Dict[str, int] = {}  # device_id -> port
        self._lockdown_clients: Dict[str, LockdownClient] = {}  # device_id -> LockdownClient
        self._lock = threading.Lock()
        self._base_port = 2222
        self._max_port = 2250
        
        # Check if pymobiledevice3 is available
        if not PYMOBILEDEVICE3_AVAILABLE:
            logger.error("pymobiledevice3 is not available. Port forwarding will not work.")
            logger.error("Please install with: pip install pymobiledevice3")
    
    @property
    def active_proxies(self):
        """获取活动的代理列表"""
        with self._lock:
            # 清理已停止的转发器
            dead_devices = []
            for device_id, forwarder in self._forwarders.items():
                if not self._is_forwarder_alive(forwarder):
                    dead_devices.append(device_id)
            
            for device_id in dead_devices:
                self._cleanup_device(device_id)
            
            return self._forwarders
    
    def _is_forwarder_alive(self, forwarder: 'TcpForwarder') -> bool:
        """检查转发器是否仍在运行"""
        if not forwarder:
            return False
        # TcpForwarder runs in a thread, check if it's still active
        if hasattr(forwarder, '_thread') and forwarder._thread:
            return forwarder._thread.is_alive()
        return False
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # 连接失败说明端口可用
        except Exception:
            return False
    
    def _find_available_port(self) -> Optional[int]:
        """找到一个可用的端口"""
        for port in range(self._base_port, self._max_port):
            if port not in self._ports.values() and self._is_port_available(port):
                return port
        return None
    
    def start_proxy(self, device_id: str) -> Optional[int]:
        """为设备启动端口转发并返回端口"""
        if not PYMOBILEDEVICE3_AVAILABLE:
            logger.error("pymobiledevice3 not available, cannot start port forwarding")
            return None
            
        with self._lock:
            # 如果已有转发器在运行，返回现有端口
            if device_id in self._forwarders:
                forwarder = self._forwarders[device_id]
                if self._is_forwarder_alive(forwarder):
                    logger.info(f"Reusing existing port forwarding for {device_id} on port {self._ports[device_id]}")
                    return self._ports[device_id]
                else:
                    # 转发器已停止，清理
                    self._cleanup_device(device_id)
            
            # 找一个可用端口
            port = self._find_available_port()
            if not port:
                logger.error("No available ports")
                return None
            
            # 创建端口转发
            try:
                # 创建或重用 LockdownClient
                if device_id not in self._lockdown_clients:
                    try:
                        # 如果 device_id 是 'any' 或无效，让 LockdownClient 自动选择
                        if device_id == 'any':
                            lockdown = LockdownClient()
                        else:
                            lockdown = LockdownClient(serial=device_id)
                        self._lockdown_clients[device_id] = lockdown
                    except Exception as e:
                        logger.error(f"Failed to create LockdownClient for device {device_id}: {e}")
                        return None
                else:
                    lockdown = self._lockdown_clients[device_id]
                
                # 创建 TcpForwarder
                logger.info(f"Starting port forwarding: localhost:{port} -> device:22")
                forwarder = TcpForwarder(
                    lockdown=lockdown,
                    src_port=port,
                    dst_port=22,  # SSH port
                    enable_ssl=False
                )
                
                # 启动转发器
                forwarder.start(address='127.0.0.1')  # 只监听本地连接
                
                # 等待端口就绪
                time.sleep(0.5)  # 给转发器一点时间启动
                
                # 验证端口是否真的在监听
                if self._wait_for_port(port, timeout=5):
                    self._forwarders[device_id] = forwarder
                    self._ports[device_id] = port
                    logger.info(f"Port forwarding started successfully on port {port}")
                    return port
                else:
                    logger.error(f"Port {port} not ready after starting forwarder")
                    try:
                        forwarder.stop()
                    except Exception:
                        pass
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to start port forwarding: {str(e)}", exc_info=True)
                # 清理失败的资源
                if device_id in self._lockdown_clients:
                    del self._lockdown_clients[device_id]
                return None
    
    def _wait_for_port(self, port: int, timeout: int = 10) -> bool:
        """等待端口可达"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
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
            
            time.sleep(0.2)
        
        logger.error(f"Timeout waiting for port {port}")
        return False
    
    def stop_proxy(self, device_id: str):
        """停止设备的端口转发"""
        with self._lock:
            self._cleanup_device(device_id)
    
    def _cleanup_device(self, device_id: str):
        """清理设备相关资源"""
        # 停止转发器
        if device_id in self._forwarders:
            forwarder = self._forwarders[device_id]
            try:
                forwarder.stop()
                logger.info(f"Stopped port forwarding for device {device_id}")
            except Exception as e:
                logger.error(f"Error stopping forwarder: {e}")
            del self._forwarders[device_id]
        
        # 清理端口记录
        if device_id in self._ports:
            del self._ports[device_id]
        
        # 清理 LockdownClient
        if device_id in self._lockdown_clients:
            try:
                # LockdownClient doesn't need explicit cleanup
                pass
            except Exception:
                pass
            del self._lockdown_clients[device_id]
            
        logger.info(f"Cleaned up resources for device {device_id}")
    
    def cleanup_all(self):
        """清理所有端口转发"""
        with self._lock:
            device_ids = list(self._forwarders.keys())
            for device_id in device_ids:
                self._cleanup_device(device_id)
    
    def get_device_port(self, device_id: str) -> Optional[int]:
        """获取设备的端口"""
        with self._lock:
            return self._ports.get(device_id)
    
    def __del__(self):
        """析构时清理所有资源"""
        try:
            self.cleanup_all()
        except Exception:
            pass