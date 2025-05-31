#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取版本号的脚本
供shell脚本调用
"""

import sys
import os

# 获取项目根目录
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# 添加src目录到路径
sys.path.insert(0, os.path.join(project_root, 'src'))

try:
    from version import APP_VERSION
    print(APP_VERSION)
except ImportError as e:
    print(f"Error importing version: {e}", file=sys.stderr)
    print("1.0.2")  # 默认版本号作为后备