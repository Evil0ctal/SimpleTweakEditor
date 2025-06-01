# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-30
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 版本管理模块
统一管理应用程序版本号，提供版本信息查询接口

英文介绍:
SimpleTweakEditor Version Management Module
Centralized version number management with version information query interface
"""

# 应用程序版本号 - 修改此处即可更新所有相关版本显示
APP_VERSION = "1.0.3"


# 获取版本号的函数
def get_version():
    """获取当前应用程序版本号"""
    return APP_VERSION


# 获取完整版本信息
def get_version_info():
    """获取完整版本信息"""
    return {
        "version": APP_VERSION,
        "name": "SimpleTweakEditor",
        "author": "Evil0ctal",
        "license": "Apache 2.0"
    }
