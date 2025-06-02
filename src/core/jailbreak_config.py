# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
越狱配置管理器，支持 Rootless 和 Rootful 模式，管理 Sileo 兼容性设置

英文介绍:
Jailbreak configuration manager, supports Rootless and Rootful modes, manages Sileo compatibility settings
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
import json
from pathlib import Path
from ..utils.debug_logger import debug


class JailbreakMode(Enum):
    """越狱模式枚举"""
    ROOTLESS = "rootless"  # 现代越狱模式（沙盒化）
    ROOTFUL = "rootful"    # 传统越狱模式（完全访问）


@dataclass
class JailbreakConfig:
    """越狱配置"""
    mode: JailbreakMode = JailbreakMode.ROOTLESS
    device_model: str = "iPhone14,2"  # iPhone 13 Pro
    firmware_version: str = "16.0"
    unique_id: str = "SimpleTweakEditor"
    use_sileo_headers: bool = True
    
    def get_http_headers(self) -> Dict[str, str]:
        """获取HTTP请求头"""
        if self.use_sileo_headers:
            # Sileo-compatible headers
            return {
                'User-Agent': 'Sileo/2.4 CFNetwork/1410.0.3 Darwin/22.6.0',
                'X-Machine': self.device_model,
                'X-Firmware': self.firmware_version,
                'X-Unique-ID': self.unique_id,
                'X-Device-Model': self.device_model,
                'X-Device-Version': self.firmware_version,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'X-Sileo-Version': '2.4',
                'X-Jailbreak-Mode': self.mode.value
            }
        else:
            # Legacy Cydia headers
            return {
                'User-Agent': 'Cydia/1.1.32 CFNetwork/978.0.7 Darwin/18.7.0',
                'X-Machine': self.device_model,
                'X-Unique-ID': self.unique_id,
                'X-Firmware': self.firmware_version
            }
    
    def get_path_prefix(self) -> str:
        """获取路径前缀（用于 Rootless 路径映射）"""
        if self.mode == JailbreakMode.ROOTLESS:
            return "/var/jb"
        return ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'mode': self.mode.value,
            'device_model': self.device_model,
            'firmware_version': self.firmware_version,
            'unique_id': self.unique_id,
            'use_sileo_headers': self.use_sileo_headers
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JailbreakConfig':
        """从字典创建"""
        mode = JailbreakMode(data.get('mode', JailbreakMode.ROOTLESS.value))
        return cls(
            mode=mode,
            device_model=data.get('device_model', 'iPhone14,2'),
            firmware_version=data.get('firmware_version', '16.0'),
            unique_id=data.get('unique_id', 'SimpleTweakEditor'),
            use_sileo_headers=data.get('use_sileo_headers', True)
        )


class JailbreakConfigManager:
    """越狱配置管理器"""
    
    def __init__(self, app_dir: str):
        """初始化配置管理器"""
        self.app_dir = Path(app_dir)
        self.config_file = self.app_dir / "jailbreak_config.json"
        self.config = self.load_config()
        debug(f"JailbreakConfig initialized: mode={self.config.mode.value}, sileo_headers={self.config.use_sileo_headers}")
    
    def load_config(self) -> JailbreakConfig:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return JailbreakConfig.from_dict(data)
            except Exception as e:
                print(f"[ERROR] Failed to load jailbreak config: {e}")
        
        # 返回默认配置
        return JailbreakConfig()
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
            debug(f"Saved jailbreak config: {self.config.to_dict()}")
        except Exception as e:
            print(f"[ERROR] Failed to save jailbreak config: {e}")
    
    def set_mode(self, mode: JailbreakMode):
        """设置越狱模式"""
        self.config.mode = mode
        self.save_config()
        debug(f"Jailbreak mode set to: {mode.value}")
    
    def set_device_info(self, model: str, firmware: str):
        """设置设备信息"""
        self.config.device_model = model
        self.config.firmware_version = firmware
        self.save_config()
        debug(f"Device info set: model={model}, firmware={firmware}")
    
    def toggle_sileo_headers(self, enabled: bool):
        """切换 Sileo 请求头"""
        self.config.use_sileo_headers = enabled
        self.save_config()
        debug(f"Sileo headers {'enabled' if enabled else 'disabled'}")