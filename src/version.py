# -*- coding: utf-8 -*-
"""
版本管理模块
统一管理应用程序版本号
"""

# 应用程序版本号 - 修改此处即可更新所有相关版本显示
APP_VERSION = "1.0.1"


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
