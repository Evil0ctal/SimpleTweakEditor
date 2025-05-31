# -*- coding: utf-8 -*-
"""
终端dpkg命令包装器
为交互式终端提供跨平台的dpkg命令支持
"""

import os
import platform
import shutil
import tempfile

from .dpkg_deb import dpkg_deb
from .system_utils import check_dpkg_available


def is_dpkg_command(command):
    """检查是否是dpkg相关命令"""
    if not command:
        return False
    
    # 分割命令
    parts = command.strip().split()
    if not parts:
        return False
    
    # 检查是否是dpkg-deb命令
    cmd = parts[0]
    return cmd in ['dpkg-deb', 'dpkg']


def handle_dpkg_command(command, current_dir):
    """
    处理dpkg命令，在Windows上使用Python实现
    
    Args:
        command: 要执行的命令
        current_dir: 当前工作目录
        
    Returns:
        tuple: (handled, output, error) - handled表示是否处理了命令
    """
    # 检查是否是dpkg命令
    if not is_dpkg_command(command):
        return False, None, None
    
    # 在非Windows平台上，如果dpkg可用，则不处理
    if platform.system() != "Windows" and check_dpkg_available():
        return False, None, None
    
    # 解析命令
    parts = command.strip().split()
    cmd = parts[0]
    
    # 切换到指定目录
    old_dir = os.getcwd()
    try:
        os.chdir(current_dir)
        
        # 处理dpkg-deb命令
        if cmd == 'dpkg-deb' or (cmd == 'dpkg' and len(parts) > 1 and parts[1] == '-deb'):
            return handle_dpkg_deb_command(parts[1:] if cmd == 'dpkg-deb' else parts[2:], current_dir)
        
        # 其他dpkg命令暂不支持
        return True, None, f"Command '{cmd}' is not supported on this platform without dpkg installed.\n"
        
    finally:
        os.chdir(old_dir)


def handle_dpkg_deb_command(args, current_dir):
    """处理dpkg-deb命令"""
    if not args:
        return True, get_dpkg_deb_help(), None
    
    # 解析选项
    option = args[0]
    
    try:
        # -I, --info: 显示包信息
        if option in ['-I', '--info']:
            if len(args) < 2:
                return True, None, "dpkg-deb: error: -I needs a .deb filename\n"
            
            deb_file = resolve_path(args[1], current_dir)
            if not os.path.exists(deb_file):
                return True, None, f"dpkg-deb: error: failed to read archive '{args[1]}': No such file or directory\n"
            
            try:
                info = dpkg_deb.info(deb_file)
                return True, info + '\n', None
            except Exception as e:
                return True, None, f"dpkg-deb: error: {str(e)}\n"
        
        # -c, --contents: 列出包内容
        elif option in ['-c', '--contents']:
            if len(args) < 2:
                return True, None, "dpkg-deb: error: -c needs a .deb filename\n"
            
            deb_file = resolve_path(args[1], current_dir)
            if not os.path.exists(deb_file):
                return True, None, f"dpkg-deb: error: failed to read archive '{args[1]}': No such file or directory\n"
            
            try:
                contents = dpkg_deb.contents(deb_file)
                return True, contents + '\n', None
            except Exception as e:
                return True, None, f"dpkg-deb: error: {str(e)}\n"
        
        # -x, --extract: 解压包
        elif option in ['-x', '--extract']:
            if len(args) < 3:
                return True, None, "dpkg-deb: error: -x needs a .deb filename and target directory\n"
            
            deb_file = resolve_path(args[1], current_dir)
            target_dir = resolve_path(args[2], current_dir)
            
            if not os.path.exists(deb_file):
                return True, None, f"dpkg-deb: error: failed to read archive '{args[1]}': No such file or directory\n"
            
            try:
                # 确保目标目录存在
                os.makedirs(target_dir, exist_ok=True)
                
                success = dpkg_deb.extract(deb_file, target_dir)
                if success:
                    return True, f"Extracted '{args[1]}' to '{args[2]}'\n", None
                else:
                    return True, None, "dpkg-deb: error: extraction failed\n"
            except Exception as e:
                return True, None, f"dpkg-deb: error: {str(e)}\n"
        
        # -e, --control: 解压控制文件
        elif option in ['-e', '--control']:
            if len(args) < 2:
                return True, None, "dpkg-deb: error: -e needs a .deb filename\n"
            
            deb_file = resolve_path(args[1], current_dir)
            target_dir = resolve_path(args[2] if len(args) > 2 else 'DEBIAN', current_dir)
            
            if not os.path.exists(deb_file):
                return True, None, f"dpkg-deb: error: failed to read archive '{args[1]}': No such file or directory\n"
            
            try:
                # 临时目录
                with tempfile.TemporaryDirectory() as temp_dir:
                    # 解压整个包
                    success = dpkg_deb.extract(deb_file, temp_dir)
                    if not success:
                        return True, None, "dpkg-deb: error: extraction failed\n"
                    
                    # 复制DEBIAN目录
                    debian_src = os.path.join(temp_dir, 'DEBIAN')
                    if os.path.exists(debian_src):
                        # 如果目标已存在，先删除
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir)
                        shutil.copytree(debian_src, target_dir)
                        return True, f"Extracted control files to '{target_dir}'\n", None
                    else:
                        return True, None, "dpkg-deb: error: no DEBIAN directory found\n"
                        
            except Exception as e:
                return True, None, f"dpkg-deb: error: {str(e)}\n"
        
        # -b, --build: 构建包
        elif option in ['-b', '--build']:
            if len(args) < 2:
                return True, None, "dpkg-deb: error: -b needs a directory\n"
            
            source_dir = resolve_path(args[1], current_dir)
            output_file = resolve_path(args[2] if len(args) > 2 else args[1] + '.deb', current_dir)
            
            if not os.path.exists(source_dir):
                return True, None, f"dpkg-deb: error: failed to read directory '{args[1]}': No such file or directory\n"
            
            try:
                success = dpkg_deb.build(source_dir, output_file)
                if success:
                    return True, f"dpkg-deb: building package in '{output_file}'\n", None
                else:
                    return True, None, "dpkg-deb: error: build failed\n"
            except Exception as e:
                return True, None, f"dpkg-deb: error: {str(e)}\n"
        
        # --version: 显示版本
        elif option == '--version':
            return True, get_dpkg_deb_version(), None
        
        # --help: 显示帮助
        elif option in ['-h', '--help']:
            return True, get_dpkg_deb_help(), None
        
        else:
            return True, None, f"dpkg-deb: error: unknown option '{option}'\n"
            
    except Exception as e:
        return True, None, f"dpkg-deb: error: {str(e)}\n"


def resolve_path(path, base_dir):
    """解析路径，处理相对路径"""
    if os.path.isabs(path):
        return path
    return os.path.join(base_dir, path)


def get_dpkg_deb_version():
    """获取dpkg-deb版本信息"""
    return """dpkg-deb (SimpleTweakEditor Python Implementation) 1.0.2
Copyright (C) 2025 Evil0ctal.
This is free software; see the source for copying conditions.
There is NO warranty; not even for MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.

This is a Python implementation of dpkg-deb for cross-platform compatibility.
"""


def get_dpkg_deb_help():
    """获取dpkg-deb帮助信息"""
    return """Usage: dpkg-deb [<option> ...] <command>

Commands:
  -b|--build <directory> [<deb>]    Build an archive.
  -c|--contents <deb>               List contents.
  -e|--control <deb> [<directory>]  Extract control info.
  -x|--extract <deb> <directory>    Extract files.
  -I|--info <deb>                   Show info.
  --version                         Show version.
  -h|--help                         Show this help message.

This is a Python implementation of dpkg-deb for cross-platform compatibility.
"""


# 为which命令提供响应
def handle_which_dpkg():
    """处理which dpkg-deb命令"""
    if platform.system() == "Windows":
        return True, "dpkg-deb: Python implementation (built-in)\n", None
    return False, None, None
