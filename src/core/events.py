# -*- coding: utf-8 -*-
"""
自定义事件类模块
定义应用程序中使用的各种自定义事件
"""

from PyQt6.QtCore import QEvent


# 定义自定义事件类型的基础ID
_CUSTOM_EVENT_TYPE = QEvent.Type(QEvent.Type.User.value + 1)


class LogEvent(QEvent):
    """日志事件 - 用于线程安全的日志更新"""

    def __init__(self, message, tag=None):
        super().__init__(_CUSTOM_EVENT_TYPE)
        self.message = message
        self.tag = tag


class UnpackResultEvent(QEvent):
    """解包结果事件 - 用于通知解包操作完成"""

    def __init__(self, success, message, target_dir):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 1))
        self.success = success
        self.message = message
        self.target_dir = target_dir


class PackResultEvent(QEvent):
    """打包结果事件 - 用于通知打包操作完成"""

    def __init__(self, success, message, out_path):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 2))
        self.success = success
        self.message = message
        self.out_path = out_path


class ThreadExceptionEvent(QEvent):
    """线程异常事件 - 用于处理后台线程异常"""

    def __init__(self, error_msg, operation_type):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 3))
        self.error_msg = error_msg
        self.operation_type = operation_type


class LanguageChangedEvent(QEvent):
    """语言更改事件 - 用于通知UI更新语言"""

    def __init__(self, new_language):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 4))
        self.new_language = new_language
