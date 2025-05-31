# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 配置管理模块
负责保存和加载用户配置，管理应用程序偏好设置

英文介绍:
SimpleTweakEditor Configuration Management Module
Handles saving and loading user configurations, manages application preferences
"""

import os
import json
from pathlib import Path


class ConfigManager:
    """配置管理器"""

    def __init__(self, app_name="SimpleTweakEditor"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"

        # 默认配置
        self.default_config = {
            "language": "auto",  # auto, en, zh
            "theme": "auto",  # auto, light, dark
            "debug_mode": False,  # 生产环境默认关闭
            "window": {
                "width": 800,
                "height": 600,
                "maximized": False
            },
            "paths": {
                "last_deb_dir": "",
                "last_output_dir": "",
                "last_folder_dir": "",
                "last_save_dir": ""
            },
            "ui": {
                "splitter_sizes": [400, 100],
                "show_welcome_message": True
            }
        }

        self.config = self.load_config()

    def _get_config_dir(self):
        """获取配置目录"""
        # 统一使用 Downloads/SimpleTweakEditor 作为配置目录
        config_dir = Path.home() / "Downloads" / self.app_name
        
        # 确保配置目录存在
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def load_config(self):
        """加载配置文件"""
        if not self.config_file.exists():
            return self.default_config.copy()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # 合并默认配置和加载的配置
            config = self.default_config.copy()
            self._deep_update(config, loaded_config)
            return config

        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self):
        """保存配置文件"""
        try:
            # 使用临时文件确保原子操作
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='utf-8',
                dir=self.config_file.parent,
                delete=False
            ) as tmp:
                json.dump(self.config, tmp, indent=2, ensure_ascii=False)
                tmp_path = tmp.name
            
            # 设置安全权限（仅用户可读写）
            os.chmod(tmp_path, 0o600)
            
            # 原子替换
            Path(tmp_path).replace(self.config_file)
            
        except Exception as e:
            # 配置保存失败不应影响程序运行
            if self.config.get('debug_mode', False):
                print(f"Error saving config: {e}")

    def _deep_update(self, base_dict, update_dict):
        """深度更新字典"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def get(self, key, default=None):
        """获取配置值（支持点号分隔的键）"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key, value):
        """设置配置值（支持点号分隔的键）"""
        keys = key.split('.')
        target = self.config

        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    def get_language(self):
        """获取语言设置"""
        return self.get("language", "auto")

    def set_language(self, language):
        """设置语言"""
        self.set("language", language)
        self.save_config()

    def get_debug_mode(self):
        """获取调试模式设置"""
        return self.get("debug_mode", False)

    def set_debug_mode(self, debug_mode):
        """设置调试模式"""
        self.set("debug_mode", debug_mode)
        self.save_config()

    def get_window_config(self):
        """获取窗口配置"""
        return self.get("window", {})

    def set_window_config(self, width, height, maximized=False):
        """设置窗口配置"""
        self.set("window.width", width)
        self.set("window.height", height)
        self.set("window.maximized", maximized)
        self.save_config()

    def get_path(self, path_type):
        """获取路径配置"""
        return self.get(f"paths.{path_type}", "")

    def set_path(self, path_type, path):
        """设置路径配置"""
        self.set(f"paths.{path_type}", path)
        self.save_config()

    def get_splitter_sizes(self):
        """获取分割器大小"""
        return self.get("ui.splitter_sizes", [400, 100])

    def set_splitter_sizes(self, sizes):
        """设置分割器大小"""
        self.set("ui.splitter_sizes", sizes)
        self.save_config()

    def get_show_welcome_message(self):
        """获取是否显示欢迎消息"""
        return self.get("ui.show_welcome_message", True)

    def set_show_welcome_message(self, show):
        """设置是否显示欢迎消息"""
        self.set("ui.show_welcome_message", show)
        self.save_config()
    
    def get_app_data_dir(self):
        """获取应用数据目录（与配置目录相同）"""
        return self.config_dir
