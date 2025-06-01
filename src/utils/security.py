# -*- coding: utf-8 -*-
"""
Security utilities for SimpleTweakEditor

提供安全相关的工具函数，包括路径验证、输入清理等
Provides security-related utility functions including path validation, input sanitization, etc.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional, List, Union


class SecurityError(Exception):
    """安全相关错误的基类"""
    pass


class PathTraversalError(SecurityError):
    """路径遍历攻击错误"""
    pass


def validate_path(path: str, allowed_dirs: Optional[List[str]] = None) -> str:
    """
    验证路径安全性，防止路径遍历攻击
    
    Args:
        path: 要验证的路径
        allowed_dirs: 允许的目录列表。如果为None，默认允许用户目录和临时目录
        
    Returns:
        规范化后的安全路径
        
    Raises:
        PathTraversalError: 如果路径不安全
    """
    # 规范化路径
    normalized_path = os.path.normpath(os.path.abspath(path))
    
    # 检查路径中是否包含危险模式
    dangerous_patterns = [
        '..',  # 父目录引用
        '~',   # Home目录扩展
        '$',   # 环境变量
        '%',   # Windows环境变量
    ]
    
    for pattern in dangerous_patterns:
        if pattern in path:
            raise PathTraversalError(f"Dangerous pattern '{pattern}' found in path")
    
    # 如果没有指定允许的目录，使用默认值
    if allowed_dirs is None:
        allowed_dirs = [
            os.path.expanduser("~"),  # 用户主目录
            tempfile.gettempdir(),    # 系统临时目录
            os.getcwd(),              # 当前工作目录
        ]
    
    # 确保路径在允许的目录内
    is_allowed = False
    for allowed_dir in allowed_dirs:
        allowed_dir = os.path.normpath(os.path.abspath(allowed_dir))
        try:
            # 使用os.path.commonpath来检查路径是否在允许的目录内
            common_path = os.path.commonpath([normalized_path, allowed_dir])
            if common_path == allowed_dir:
                is_allowed = True
                break
        except ValueError:
            # 在Windows上，如果路径在不同的驱动器上，会抛出ValueError
            continue
    
    if not is_allowed:
        raise PathTraversalError(f"Path '{normalized_path}' is outside allowed directories")
    
    return normalized_path


def secure_path_join(base_path: str, *paths: str) -> str:
    """
    安全地连接路径，防止路径遍历
    
    Args:
        base_path: 基础路径
        *paths: 要连接的路径部分
        
    Returns:
        安全的连接后路径
        
    Raises:
        PathTraversalError: 如果结果路径在基础路径之外
    """
    # 规范化基础路径
    base_path = os.path.normpath(os.path.abspath(base_path))
    
    # 连接路径
    joined_path = os.path.join(base_path, *paths)
    
    # 规范化连接后的路径
    normalized_path = os.path.normpath(os.path.abspath(joined_path))
    
    # 确保结果路径在基础路径内
    try:
        common_path = os.path.commonpath([normalized_path, base_path])
        if common_path != base_path:
            raise PathTraversalError(f"Path traversal detected: '{normalized_path}' escapes base path")
    except ValueError:
        # 不同驱动器
        raise PathTraversalError(f"Path traversal detected: paths on different drives")
    
    return normalized_path


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    清理文件名，移除危险字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度限制
        
    Returns:
        清理后的安全文件名
    """
    # 移除路径分隔符和其他危险字符
    dangerous_chars = ['/', '\\', '..', '~', '$', '%', ':', '*', '?', '"', '<', '>', '|', '\0']
    
    safe_filename = filename
    for char in dangerous_chars:
        safe_filename = safe_filename.replace(char, '_')
    
    # 移除控制字符
    safe_filename = ''.join(char for char in safe_filename if ord(char) >= 32)
    
    # 限制长度
    if len(safe_filename) > max_length:
        # 保留文件扩展名
        name, ext = os.path.splitext(safe_filename)
        max_name_length = max_length - len(ext)
        safe_filename = name[:max_name_length] + ext
    
    # 确保文件名不为空
    if not safe_filename or safe_filename.isspace():
        safe_filename = "unnamed_file"
    
    return safe_filename


def validate_command_args(args: List[str]) -> List[str]:
    """
    验证命令行参数，防止注入攻击
    
    Args:
        args: 命令行参数列表
        
    Returns:
        验证后的参数列表
        
    Raises:
        ValueError: 如果参数包含危险字符
    """
    # 危险字符模式
    dangerous_patterns = [
        r'[;&|]',  # Shell命令分隔符
        r'[$`]',   # 命令替换
        r'[<>]',   # 重定向
        r'[()]',   # 子shell
        r'[{}]',   # 代码块
        r'\\n',    # 换行符
        r'\\r',    # 回车符
    ]
    
    validated_args = []
    for arg in args:
        # 检查每个参数是否包含危险模式
        for pattern in dangerous_patterns:
            if re.search(pattern, arg):
                raise ValueError(f"Dangerous pattern found in argument: {arg}")
        
        validated_args.append(arg)
    
    return validated_args


def create_secure_temp_dir() -> str:
    """
    创建一个安全的临时目录
    
    Returns:
        临时目录路径
    """
    # 使用tempfile创建安全的临时目录
    temp_dir = tempfile.mkdtemp(prefix="ste_", suffix="_tmp")
    
    # 设置严格的权限 (仅所有者可读写执行)
    os.chmod(temp_dir, 0o700)
    
    return temp_dir


def validate_file_size(file_path: str, max_size: int = 100 * 1024 * 1024) -> None:
    """
    验证文件大小
    
    Args:
        file_path: 文件路径
        max_size: 最大允许大小（字节），默认100MB
        
    Raises:
        ValueError: 如果文件太大
        FileNotFoundError: 如果文件不存在
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    file_size = os.path.getsize(file_path)
    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max: {max_size / 1024 / 1024:.1f}MB)"
        )


def is_safe_archive_member(member_name: str, extract_to: str) -> bool:
    """
    检查压缩包成员是否安全
    
    Args:
        member_name: 成员文件名
        extract_to: 解压目标目录
        
    Returns:
        如果安全返回True，否则返回False
    """
    # 检查是否包含路径遍历
    if '..' in member_name or member_name.startswith('/'):
        return False
    
    # 检查解压后的完整路径
    try:
        full_path = secure_path_join(extract_to, member_name)
        return True
    except PathTraversalError:
        return False
