# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-25
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 本地化功能包
包含多语言支持相关功能，提供界面国际化支持

英文介绍:
SimpleTweakEditor Localization Package
Contains multi-language support functionality, provides UI internationalization
"""

from .language_manager import LanguageManager
from .translations import Translations

__all__ = ['LanguageManager', 'Translations']
