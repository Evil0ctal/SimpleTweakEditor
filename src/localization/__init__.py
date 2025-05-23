# localization/__init__.py
# -*- coding: utf-8 -*-
"""
Localization package for SimpleTweakEditor
包含多语言支持相关功能
"""

from .language_manager import LanguageManager
from .translations import Translations

__all__ = ['LanguageManager', 'Translations']
