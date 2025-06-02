# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
iOS 文件系统抽象层，提供统一的文件操作接口，支持非越狱、无根越狱和有根越狱三种模式。

英文介绍:
iOS filesystem abstraction layer providing unified file operations interface, 
supporting non-jailbroken, rootless jailbreak, and rootful jailbreak modes.
"""

import os
import stat
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..utils.debug_logger import debug


class AccessLevel(Enum):
    """访问级别枚举"""
    NONE = "none"  # 未越狱
    ROOTLESS = "rootless"  # 无根越狱
    ROOTFUL = "rootful"  # 有根越狱


@dataclass
class FileInfo:
    """文件信息"""
    name: str
    path: str
    is_directory: bool
    size: int
    modified_time: datetime
    permissions: str
    owner: str = "mobile"
    group: str = "mobile"
    is_readable: bool = True
    is_writable: bool = True
    is_executable: bool = False
    
    @property
    def display_size(self) -> str:
        """获取显示用的文件大小"""
        if self.is_directory:
            return ""
        
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    @property
    def display_time(self) -> str:
        """获取显示用的修改时间"""
        return self.modified_time.strftime("%Y-%m-%d %H:%M")
    
    @property
    def file_type(self) -> str:
        """获取文件类型"""
        if self.is_directory:
            return "directory"
        
        ext = Path(self.name).suffix.lower()
        type_map = {
            '.deb': 'package',
            '.ipa': 'package',
            '.dylib': 'library',
            '.plist': 'config',
            '.xml': 'config',
            '.json': 'config',
            '.txt': 'text',
            '.log': 'text',
            '.md': 'text',
            '.py': 'code',
            '.sh': 'code',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.gif': 'image',
            '.mp3': 'audio',
            '.mp4': 'video',
            '.mov': 'video',
        }
        return type_map.get(ext, 'file')


class iOSFileSystem:
    """iOS 文件系统抽象类"""
    
    # 不同越狱级别的访问路径限制
    ACCESS_PATHS = {
        AccessLevel.NONE: [
            "/DCIM",
            "/Downloads", 
            "/Documents",
            "/Library/Preferences",
        ],
        AccessLevel.ROOTLESS: [
            "/",  # Rootless 越狱也应该能访问根目录，但某些系统目录是只读的
            "/var/jb",
            "/var/mobile",
            "/var/containers",
            "/private/var/mobile/Library",
        ],
        AccessLevel.ROOTFUL: [
            "/"  # 完全访问
        ]
    }
    
    # 危险路径（需要警告）
    DANGEROUS_PATHS = [
        "/System",
        "/private/etc",
        "/usr/libexec",
        "/sbin",
        "/bin",
    ]
    
    def __init__(self, device, access_level: AccessLevel):
        """初始化文件系统"""
        self.device = device
        self.access_level = access_level
        self.afc_client = None
        self._init_afc_client()
        
    def _init_afc_client(self):
        """初始化 AFC 客户端"""
        if not self.device or not hasattr(self.device, 'lockdown_client'):
            debug("No lockdown client available for file access")
            return
            
        try:
            from pymobiledevice3.services.afc import AfcService
            
            # 尝试使用 AFC2 (越狱设备)
            if self.access_level in [AccessLevel.ROOTLESS, AccessLevel.ROOTFUL]:
                try:
                    # 尝试 AFC2 服务
                    self.afc_client = AfcService(self.device.lockdown_client, service_name="com.apple.afc2")
                    debug("Successfully connected using AFC2 service for jailbroken device")
                    # 测试连接
                    self.afc_client.listdir("/")
                    return
                except Exception as e:
                    debug(f"AFC2 not available: {e}, falling back to AFC")
            
            # 使用标准 AFC
            self.afc_client = AfcService(self.device.lockdown_client)
            debug("Using standard AFC service")
            # 测试连接
            try:
                self.afc_client.listdir("/")
            except Exception as e:
                debug(f"AFC service test failed: {e}")
                # 尝试 House Arrest 服务作为备选
                try:
                    from pymobiledevice3.services.house_arrest import HouseArrestService
                    # House Arrest 可以访问应用沙盒
                    debug("Trying HouseArrest service as fallback")
                    # 注意：HouseArrest 需要指定应用 bundle ID
                    # 这里暂时不使用，只是记录
                except ImportError:
                    pass
            
        except Exception as e:
            debug(f"Failed to initialize AFC client: {e}")
            self.afc_client = None
    
    def is_path_allowed(self, path: str) -> bool:
        """检查路径是否允许访问"""
        path = os.path.normpath(path)
        allowed_paths = self.ACCESS_PATHS[self.access_level]
        
        # 完全访问模式
        if "/" in allowed_paths:
            return True
        
        # 检查路径是否在允许列表中
        for allowed in allowed_paths:
            if path.startswith(allowed):
                return True
        
        return False
    
    def is_path_dangerous(self, path: str) -> bool:
        """检查路径是否危险"""
        path = os.path.normpath(path)
        for dangerous in self.DANGEROUS_PATHS:
            if path.startswith(dangerous):
                return True
        return False
    
    def list_directory(self, path: str) -> List[FileInfo]:
        """列出目录内容"""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if not self.afc_client:
            debug(f"No AFC client, using fallback for path: {path}")
            return self._list_directory_fallback(path)
        
        try:
            files = []
            entries = self.afc_client.listdir(path)
            
            for entry in entries:
                if entry in ['.', '..']:
                    continue
                
                full_path = os.path.join(path, entry)
                try:
                    # 获取文件信息
                    info = self._get_file_info(full_path, entry)
                    if info:
                        files.append(info)
                except Exception as e:
                    debug(f"Error getting info for {full_path}: {e}")
                    # 创建基本信息
                    files.append(FileInfo(
                        name=entry,
                        path=full_path,
                        is_directory=False,
                        size=0,
                        modified_time=datetime.now(),
                        permissions="?????????",
                    ))
            
            # 排序：目录在前，然后按名称
            files.sort(key=lambda x: (not x.is_directory, x.name.lower()))
            return files
            
        except Exception as e:
            debug(f"Error listing directory {path}: {e}")
            debug(f"Falling back to directory structure for path: {path}")
            # 如果 AFC 失败，尝试使用备用方法
            return self._list_directory_fallback(path)
    
    def _get_file_info(self, path: str, name: str) -> Optional[FileInfo]:
        """获取文件信息"""
        try:
            if not self.afc_client:
                return None
                
            stat_info = self.afc_client.stat(path)
            
            # 解析文件信息 - AFC 返回的是字典格式
            # 检查是否是目录或链接
            is_dir = False
            is_link = False
            link_target = None
            
            if 'st_ifmt' in stat_info:
                ifmt = stat_info['st_ifmt']
                is_dir = ifmt == 'S_IFDIR'
                is_link = ifmt == 'S_IFLNK'
                
                # 如果是符号链接，尝试判断目标类型
                if is_link:
                    link_target = stat_info.get('LinkTarget', '')
                    # 大多数情况下，符号链接指向的都是目录
                    # 特别是在 iOS 文件系统中，/var -> /private/var 这种
                    is_dir = True  # 默认认为链接是目录
            
            size = int(stat_info.get('st_size', 0))
            
            # AFC 时间戳处理
            mtime = stat_info.get('st_mtime', None)
            if mtime:
                if hasattr(mtime, 'timestamp'):
                    # 已经是 datetime 对象
                    modified = mtime
                elif isinstance(mtime, (int, float)):
                    # 纳秒时间戳
                    modified = datetime.fromtimestamp(mtime / 1000000000)
                else:
                    modified = datetime.now()
            else:
                modified = datetime.now()
            
            # 构建权限字符串
            mode = stat_info.get('st_mode', None)
            if mode is None:
                # 如果没有 st_mode，根据类型设置默认权限
                if is_dir:
                    perms = "drwxr-xr-x"
                else:
                    perms = "-rw-r--r--"
            else:
                if isinstance(mode, str):
                    mode = int(mode, 8) if mode.isdigit() else 0o755
                else:
                    mode = int(mode)
                perms = self._mode_to_permissions(mode)
            
            return FileInfo(
                name=name,
                path=path,
                is_directory=is_dir,
                size=size,
                modified_time=modified,
                permissions=perms,
            )
        except Exception as e:
            debug(f"Error getting file info for {path}: {e}")
            # 返回基本信息
            return FileInfo(
                name=name,
                path=path,
                is_directory=path.endswith('/'),
                size=0,
                modified_time=datetime.now(),
                permissions="?????????",
            )
    
    @staticmethod
    def _mode_to_permissions(mode: int) -> str:
        """将文件模式转换为权限字符串"""
        perms = []
        
        # 文件类型
        if stat.S_ISDIR(mode):
            perms.append('d')
        elif stat.S_ISLNK(mode):
            perms.append('l')
        else:
            perms.append('-')
        
        # 权限位
        for who in [stat.S_IRUSR, stat.S_IRGRP, stat.S_IROTH]:
            for perm in [(who, 'r'), (who >> 1, 'w'), (who >> 2, 'x')]:
                perms.append(perm[1] if mode & perm[0] else '-')
        
        return ''.join(perms)
    
    def _list_directory_fallback(self, path: str) -> List[FileInfo]:
        """备用的目录列表方法（当 AFC 不可用时）"""
        # 规范化路径
        path = os.path.normpath(path)
        
        # 定义不同访问级别的目录结构
        filesystem_structure = {
            AccessLevel.NONE: {
                "/": [("DCIM", True), ("Downloads", True), ("Documents", True), ("Library", True)],
                "/DCIM": [("100APPLE", True), ("Camera", True)],
                "/Downloads": [],
                "/Documents": [],
                "/Library": [("Preferences", True)],
                "/Library/Preferences": [],
            },
            AccessLevel.ROOTLESS: {
                "/": [("var", True)],
                "/var": [("jb", True), ("mobile", True), ("containers", True)],
                "/var/jb": [("Applications", True), ("Library", True), ("usr", True)],
                "/var/mobile": [("Documents", True), ("Downloads", True), ("Library", True)],
                "/var/containers": [("Bundle", True), ("Data", True)],
            },
            AccessLevel.ROOTFUL: {
                "/": [
                    ("Applications", True), ("Library", True), ("System", True),
                    ("User", True), ("bin", True), ("etc", True), ("private", True),
                    ("usr", True), ("var", True)
                ],
                "/Applications": [],
                "/Library": [("MobileSubstrate", True), ("PreferenceBundles", True)],
                "/System": [("Library", True)],
                "/private": [("var", True), ("etc", True)],
                "/var": [("mobile", True), ("root", True), ("containers", True)],
                "/var/mobile": [("Documents", True), ("Downloads", True), ("Library", True)],
            }
        }
        
        # 获取当前访问级别的目录结构
        structure = filesystem_structure.get(self.access_level, {})
        
        # 获取指定路径的内容
        entries = structure.get(path, [])
        
        return [
            FileInfo(
                name=name,
                path=os.path.join(path, name),
                is_directory=is_dir,
                size=0,
                modified_time=datetime.now(),
                permissions="drwxr-xr-x" if is_dir else "-rw-r--r--",
            ) for name, is_dir in entries
        ]
    
    def read_file(self, path: str, binary: bool = True) -> Union[bytes, str]:
        """读取文件内容"""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if not self.afc_client:
            debug(f"AFC client not available for reading file: {path}")
            raise RuntimeError("AFC client not available. File reading requires device connection.")
        
        try:
            # 使用 get_file_contents 方法读取文件
            content = self.afc_client.get_file_contents(path)
                
            if binary:
                return content
            else:
                return content.decode('utf-8', errors='replace')
                
        except Exception as e:
            debug(f"Failed to read file {path}: {e}")
            raise IOError(f"Failed to read file {path}: {e}")
    
    def write_file(self, path: str, content: Union[bytes, str]):
        """写入文件"""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if self.is_path_dangerous(path):
            raise PermissionError(f"Writing to dangerous path: {path}")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            # 使用 set_file_contents 方法写入文件
            self.afc_client.set_file_contents(path, content)
                
        except Exception as e:
            raise IOError(f"Failed to write file {path}: {e}")
    
    def delete(self, path: str):
        """删除文件或目录"""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if self.is_path_dangerous(path):
            raise PermissionError(f"Cannot delete dangerous path: {path}")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            # 使用 rm 方法删除文件或目录
            self.afc_client.rm(path, force=True)
        except Exception as e:
            raise IOError(f"Failed to delete {path}: {e}")
    
    def create_directory(self, path: str):
        """创建目录"""
        if not self.is_path_allowed(path):
            raise PermissionError(f"Access denied to path: {path}")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            # 使用 makedirs 方法创建目录
            self.afc_client.makedirs(path)
        except Exception as e:
            raise IOError(f"Failed to create directory {path}: {e}")
    
    def rename(self, old_path: str, new_path: str):
        """重命名文件或目录"""
        if not self.is_path_allowed(old_path) or not self.is_path_allowed(new_path):
            raise PermissionError("Access denied")
        
        if self.is_path_dangerous(old_path) or self.is_path_dangerous(new_path):
            raise PermissionError("Cannot rename dangerous paths")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            self.afc_client.rename(old_path, new_path)
        except Exception as e:
            raise IOError(f"Failed to rename {old_path} to {new_path}: {e}")
    
    def get_home_directory(self) -> str:
        """获取主目录"""
        home_dirs = {
            AccessLevel.NONE: "/Documents",
            AccessLevel.ROOTLESS: "/var/mobile",
            AccessLevel.ROOTFUL: "/var/mobile"
        }
        return home_dirs.get(self.access_level, "/")
    
    def download_file(self, remote_path: str, local_path: str, callback=None):
        """从设备下载文件到本地"""
        if not self.is_path_allowed(remote_path):
            raise PermissionError(f"Access denied to path: {remote_path}")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            # 使用 pull 方法下载文件
            self.afc_client.pull(remote_path, local_path, callback=callback)
        except Exception as e:
            raise IOError(f"Failed to download file {remote_path}: {e}")
    
    def upload_file(self, local_path: str, remote_path: str, callback=None):
        """从本地上传文件到设备"""
        if not self.is_path_allowed(remote_path):
            raise PermissionError(f"Access denied to path: {remote_path}")
        
        if self.is_path_dangerous(remote_path):
            raise PermissionError(f"Uploading to dangerous path: {remote_path}")
        
        if not self.afc_client:
            raise RuntimeError("AFC client not available")
        
        try:
            # 使用 push 方法上传文件
            self.afc_client.push(local_path, remote_path, callback=callback)
        except Exception as e:
            raise IOError(f"Failed to upload file to {remote_path}: {e}")
