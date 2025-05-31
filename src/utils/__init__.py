# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
工具包初始化文件，包含SimpleTweakEditor的辅助工具函数和实用功能模块。
提供文件操作、系统工具、dpkg处理等核心功能的导入接口。

英文介绍:
Utilities package initialization file for SimpleTweakEditor.
Provides import interface for core utility functions including file operations,
system tools, dpkg handling and other helper functions.
"""

from .file_operations import *
from .system_utils import *
from .dpkg_deb import dpkg_deb, deb_handler  # deb_handler for backward compatibility
