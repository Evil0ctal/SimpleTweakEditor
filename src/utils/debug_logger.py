# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
调试日志工具模块，提供统一的调试日志输出接口，支持根据调试模式开关控制日志输出。

英文介绍:
Debug logging utility module, provides unified debug logging interface with support for controlling log output based on debug mode.
"""

import sys
from typing import Optional


class DebugLogger:
    """调试日志管理器"""
    
    _instance = None
    _debug_mode = False
    _config_manager = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_config_manager(cls, config_manager):
        """设置配置管理器"""
        cls._config_manager = config_manager
        cls._debug_mode = config_manager.get_debug_mode() if config_manager else False
    
    @classmethod
    def set_debug_mode(cls, enabled: bool):
        """设置调试模式"""
        cls._debug_mode = enabled
    
    @classmethod
    def is_debug_mode(cls) -> bool:
        """检查是否处于调试模式"""
        if cls._config_manager:
            cls._debug_mode = cls._config_manager.get_debug_mode()
        return cls._debug_mode
    
    @classmethod
    def debug(cls, message: str, force: bool = False):
        """输出调试信息（仅在调试模式下）"""
        if force or cls.is_debug_mode():
            print(f"[DEBUG] {message}")
    
    @classmethod
    def info(cls, message: str, force: bool = False):
        """输出信息（仅在调试模式下）"""
        if force or cls.is_debug_mode():
            print(f"[INFO] {message}")
    
    @classmethod
    def warning(cls, message: str, always: bool = True):
        """输出警告（默认总是显示）"""
        if always or cls.is_debug_mode():
            print(f"[WARNING] {message}", file=sys.stderr)
    
    @classmethod
    def error(cls, message: str, always: bool = True):
        """输出错误（默认总是显示）"""
        if always or cls.is_debug_mode():
            print(f"[ERROR] {message}", file=sys.stderr)
    
    @classmethod
    def critical(cls, message: str):
        """输出严重错误（总是显示）"""
        print(f"[CRITICAL] {message}", file=sys.stderr)


# 便捷函数
def debug(message: str, force: bool = False):
    """输出调试信息"""
    DebugLogger.debug(message, force)


def info(message: str, force: bool = False):
    """输出信息"""
    DebugLogger.info(message, force)


def warning(message: str, always: bool = True):
    """输出警告"""
    DebugLogger.warning(message, always)


def error(message: str, always: bool = True):
    """输出错误"""
    DebugLogger.error(message, always)


def critical(message: str):
    """输出严重错误"""
    DebugLogger.critical(message)


def set_debug_mode(enabled: bool):
    """设置调试模式"""
    DebugLogger.set_debug_mode(enabled)


def set_config_manager(config_manager):
    """设置配置管理器"""
    DebugLogger.set_config_manager(config_manager)