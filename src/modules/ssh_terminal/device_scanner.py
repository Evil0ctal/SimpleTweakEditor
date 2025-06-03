# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
设备扫描器 - 扫描USB和WiFi连接的iOS设备

英文介绍:
Device scanner - Scans for iOS devices connected via USB and WiFi
"""

import logging
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DeviceScanner(QThread):
    """设备扫描线程"""
    device_found = pyqtSignal(dict)  # 发现设备信号
    scan_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        
    def run(self):
        """扫描设备"""
        self._is_running = True
        
        # 扫描USB设备
        try:
            from pymobiledevice3.usbmux import list_devices
            devices = list_devices()
            
            # 去重：基于设备的实际标识符
            seen_devices = set()
            
            for device in devices:
                if not self._is_running:
                    break
                
                # 获取设备的真实标识符
                # device可能有serial、identifier、udid等属性
                device_id = None
                device_name = None
                
                # 尝试不同的属性获取设备ID
                if hasattr(device, 'serial') and device.serial:
                    device_id = device.serial
                elif hasattr(device, 'identifier') and device.identifier:
                    device_id = device.identifier
                elif hasattr(device, 'udid') and device.udid:
                    device_id = device.udid
                else:
                    # 如果都没有，使用对象的字符串表示
                    device_id = str(device)
                
                # 获取设备名称
                if hasattr(device, 'name') and device.name:
                    device_name = device.name
                elif hasattr(device, 'device_name') and device.device_name:
                    device_name = device.device_name
                else:
                    device_name = f"iOS Device ({device_id[:8] if len(device_id) > 8 else device_id})"
                
                # 检查是否已经发现过这个设备
                # 使用设备名称作为去重的关键字，因为同一设备可能有不同的标识符
                if device_name in seen_devices:
                    logger.debug(f"跳过重复设备: {device_name} (ID: {device_id})")
                    continue
                    
                seen_devices.add(device_name)
                
                device_info = {
                    'identifier': device_id,
                    'name': device_name,
                    'connection_type': 'usb',
                    'host': 'localhost',
                    'port': 2222
                }
                
                logger.info(f"发现设备: {device_name} (ID: {device_id})")
                self.device_found.emit(device_info)
                
        except Exception as e:
            logger.error(f"扫描USB设备失败: {str(e)}")
            
        self.scan_finished.emit()
        
    def stop(self):
        """停止扫描"""
        self._is_running = False