# core/__init__.py
# -*- coding: utf-8 -*-
"""
Core package for SimpleTweakEditor
包含应用程序的核心功能
"""

from .app import TweakEditorApp
from .config import ConfigManager
from .events import *

__all__ = ['TweakEditorApp', 'ConfigManager']
