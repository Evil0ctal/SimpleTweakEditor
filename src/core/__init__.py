# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 核心功能包
包含应用程序的核心功能模块，包括主应用、配置管理和事件系统

英文介绍:
SimpleTweakEditor Core Package
Contains core functionality modules including main app, config management and event system
"""

from .app import TweakEditorApp
from .config import ConfigManager
from .events import *

__all__ = ['TweakEditorApp', 'ConfigManager']
