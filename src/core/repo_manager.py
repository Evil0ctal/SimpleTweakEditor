# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-27
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 软件源管理器
管理 Cydia/Sileo 插件源，解析 Packages 文件，提供 deb 包下载功能

英文介绍:
SimpleTweakEditor Repository Manager
Manages Cydia/Sileo repositories, parses Packages files, provides deb package download functionality
"""

import os
import json
import gzip
import bz2
import lzma
import httpx
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field
from datetime import datetime
import re
from pathlib import Path
import sys
from .jailbreak_config import JailbreakConfigManager
from ..utils.debug_logger import debug, info, warning, error, critical


@dataclass
class Package:
    """表示一个deb包的信息"""
    package: str = ""  # 包名
    version: str = ""  # 版本
    section: str = ""  # 分类
    description: str = ""  # 描述
    name: str = ""  # 显示名称
    author: str = ""  # 作者
    maintainer: str = ""  # 维护者
    depends: str = ""  # 依赖
    filename: str = ""  # 文件路径
    size: str = ""  # 文件大小
    md5sum: str = ""  # MD5校验
    sha256: str = ""  # SHA256校验
    icon: str = ""  # 图标URL
    depiction: str = ""  # 详情页URL (Cydia style)
    tag: str = ""  # 标签
    installed_size: str = ""  # 安装大小
    # Sileo-specific fields
    sileodepiction: str = ""  # Sileo详情页URL (JSON format)
    native_depiction: str = ""  # Native详情页URL
    rootless: str = ""  # Rootless compatibility flag
    commercial: str = ""  # Commercial package flag
    payment_link: str = ""  # Payment link for commercial packages
    architecture: str = ""  # Package architecture (iphoneos-arm, iphoneos-arm64, etc.)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if v}
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return self.name or self.package
    
    def get_display_version(self) -> str:
        """获取显示版本"""
        return self.version or "未知版本"
    
    def get_display_author(self) -> str:
        """获取显示作者"""
        return self.author or self.maintainer or "未知作者"
    
    def get_display_size(self) -> str:
        """获取友好的文件大小显示"""
        try:
            size_bytes = int(self.size)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} TB"
        except:
            return self.size or "未知大小"
    
    def is_architecture_compatible(self, device_arch: str) -> bool:
        """检查包架构是否兼容设备"""
        if not self.architecture:
            # 如果没有指定架构，假设兼容
            return True
        
        # 标准化架构名称
        package_arch = self.architecture.lower()
        device_arch = device_arch.lower()
        
        # 架构兼容性映射
        compatibility = {
            'arm64': ['iphoneos-arm64', 'iphoneos-arm', 'all', 'any', 'darwin-arm64', 'darwin-arm'],
            'arm64e': ['iphoneos-arm64e', 'iphoneos-arm64', 'iphoneos-arm', 'all', 'any', 'darwin-arm64e', 'darwin-arm64', 'darwin-arm'],
            'armv7': ['iphoneos-arm', 'all', 'any', 'darwin-arm'],
            'armv7s': ['iphoneos-arm', 'all', 'any', 'darwin-arm'],
        }
        
        # 获取兼容的架构列表
        compatible_archs = compatibility.get(device_arch, [device_arch])
        
        # 检查包架构是否在兼容列表中
        return any(arch in package_arch for arch in compatible_archs)
    
    def is_rootless_compatible(self) -> bool:
        """检查包是否兼容 Rootless 模式"""
        # 如果包明确标记了 rootless 字段
        if self.rootless.lower() in ['yes', 'true', '1']:
            return True
        # 检查架构是否包含 arm64e (通常表示现代包)
        if 'arm64e' in self.architecture.lower():
            return True
        # 默认认为兼容（让用户决定）
        return True
    
    def is_commercial(self) -> bool:
        """检查是否为商业包"""
        return self.commercial.lower() in ['yes', 'true', '1']
    
    def get_depiction_url(self) -> Optional[str]:
        """获取详情页URL（优先返回Sileo格式）"""
        return self.sileodepiction or self.native_depiction or self.depiction
    
    def get_jailbreak_compatibility(self) -> str:
        """
        获取越狱兼容性
        返回: 'Rootful', 'Rootless', 'Both', 'Unknown'
        """
        # 优先级1: 检查 rootless 标记
        if self.rootless.lower() in ['yes', 'true', '1']:
            return 'Rootless'
        
        # 优先级2: 检查文件名中的线索（最可靠）
        filename_lower = self.filename.lower()
        if 'rootless' in filename_lower:
            return 'Rootless'
        if 'rootful' in filename_lower:
            return 'Rootful'
        
        # 优先级3: 检查包名中的线索
        package_lower = self.package.lower()
        if 'rootless' in package_lower:
            return 'Rootless'
        if 'rootful' in package_lower:
            return 'Rootful'
        
        # 优先级4: 检查路径和描述中的线索
        desc_lower = self.description.lower()
        name_lower = self.name.lower()
        
        # Rootless 强指示符
        if any(text in desc_lower or text in name_lower for text in ['/var/jb', 'rootless', '无根']):
            return 'Rootless'
        
        # 优先级5: 检查架构 - arm64/arm64e 配合现代依赖通常是 Rootless
        arch_lower = self.architecture.lower()
        is_modern_arch = 'arm64' in arch_lower or 'arm64e' in arch_lower
        
        # 优先级6: 检查依赖中的线索
        depends_lower = self.depends.lower()
        
        # Rootless 特有依赖（强指示）
        rootless_only_indicators = [
            'ellekit', 'libhooker', 'com.ex.substitute',
            'org.coolstar.libhooker', 'com.opa334.altlist'
        ]
        
        # 如果有 Rootless 特有依赖，直接判定为 Rootless
        if any(indicator in depends_lower for indicator in rootless_only_indicators):
            return 'Rootless'
        
        # 现在 Rootless 也会依赖 mobilesubstrate（通过兼容层）
        # 所以不能仅凭 mobilesubstrate 判断是 Rootful
        has_mobilesubstrate = 'mobilesubstrate' in depends_lower
        
        # 如果是现代架构 + mobilesubstrate，很可能是 Rootless
        if is_modern_arch and has_mobilesubstrate:
            # 检查是否有其他 Rootful 特征
            rootful_strong_indicators = ['cydia', 'com.saurik', 'substrate.safemode']
            if not any(indicator in depends_lower for indicator in rootful_strong_indicators):
                return 'Rootless'
        
        # 传统架构（armv7/armv7s）通常是 Rootful
        if self.architecture and 'arm' in arch_lower and 'arm64' not in arch_lower:
            return 'Rootful'
        
        # 如果只有 mobilesubstrate 依赖，无法确定
        if has_mobilesubstrate:
            return 'Unknown'
        
        # 默认返回未知
        return 'Unknown'


@dataclass
class Repository:
    """表示一个软件源"""
    name: str
    url: str
    enabled: bool = True
    last_updated: Optional[str] = None
    packages_count: int = 0
    icon: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Repository':
        """从字典创建"""
        return cls(**data)


class RepoManager:
    """软件源管理器"""
    
    def __init__(self, app_dir: str):
        """初始化源管理器"""
        self.app_dir = Path(app_dir)
        self.repos_file = self.app_dir / "repositories.json"
        self.cache_dir = self.app_dir / "repo_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.repositories: List[Repository] = []
        self.packages_cache: Dict[str, List[Package]] = {}
        
        # 初始化越狱配置管理器
        self.jailbreak_config = JailbreakConfigManager(app_dir)
        
        # 加载已保存的源
        self.load_repositories()
        
        # 检查是否有自定义请求头
        custom_headers = self._load_custom_headers()
        if custom_headers:
            headers = custom_headers
            debug(f"Using custom headers: {len(headers)} headers loaded")
        else:
            headers = self.jailbreak_config.config.get_http_headers()
        
        # HTTP 客户端配置 - 使用越狱配置的请求头或自定义请求头
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=headers
        )
        
        debug(f"RepoManager initialized with app_dir: {app_dir}")
        debug(f"Loaded {len(self.repositories)} repositories")
        debug(f"Using {'Sileo' if self.jailbreak_config.config.use_sileo_headers else 'Cydia'} headers")
        debug(f"HTTP Client headers: {dict(self.client.headers)}")
    
    def _get_default_repositories(self) -> List[Dict]:
        """获取默认软件源列表"""
        # 尝试多个可能的路径
        possible_paths = [
            # 开发环境路径
            Path(__file__).parent.parent / "resources" / "default_repositories.json",
            # 打包后的路径（macOS .app）
            Path(sys.executable).parent.parent / "Resources" / "default_repositories.json",
            # 打包后的路径（Linux/Windows）
            Path(sys.executable).parent / "resources" / "default_repositories.json",
            # 相对于当前工作目录
            Path("src/resources/default_repositories.json"),
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('repositories', [])
                except Exception as e:
                    error(f"Failed to load default repositories from {path}: {e}")
        
        # 如果找不到文件，返回硬编码的默认值
        warning("Could not find default_repositories.json, using hardcoded defaults")
        return [
            {
                "name": "BigBoss",
                "url": "http://apt.thebigboss.org/repofiles/cydia/",
                "description": "The biggest repository of iOS tweaks and apps"
            },
            {
                "name": "Chariz",
                "url": "https://repo.chariz.com/",
                "description": "Premium tweaks and themes for jailbroken iOS devices"
            },
            {
                "name": "Packix",
                "url": "https://repo.packix.com/",
                "description": "Modern repository with premium and free tweaks"
            },
            {
                "name": "Havoc",
                "url": "https://havoc.app/",
                "description": "Repository for popular iOS tweaks"
            },
            {
                "name": "Zebra",
                "url": "https://getzbra.com/repo/",
                "description": "Repository for Zebra package manager"
            },
            {
                "name": "Evelyn's Collection",
                "url": "https://evynw.github.io/",
                "description": "Curated collection of useful iOS tweaks and utilities"
            },
            {
                "name": "PoomSmart's Repo",
                "url": "https://poomsmart.github.io/repo/",
                "description": "Technical tweaks and system modifications"
            },
            {
                "name": "Ryan Petrich's Repo",
                "url": "https://rpetri.ch/repo/",
                "description": "High-quality system tweaks and development tools"
            },
            {
                "name": "Spark Dev",
                "url": "https://sparkdev.me/",
                "description": "Modern tweaks and enhancements for iOS devices"
            },
            {
                "name": "ElleKit",
                "url": "https://ellekit.space/",
                "description": "Modern hooking library and rootless jailbreak packages"
            }
        ]
    
    def load_repositories(self):
        """加载保存的软件源"""
        if self.repos_file.exists():
            try:
                with open(self.repos_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.repositories = [Repository.from_dict(repo) for repo in data]
                debug(f"Loaded {len(self.repositories)} repositories from file")
            except Exception as e:
                error(f"Failed to load repositories: {e}")
                self.repositories = []
        else:
            # 首次使用，添加默认源
            debug("First run, adding default repositories")
            for repo_data in self._get_default_repositories():
                self.add_repository(repo_data['name'], repo_data['url'], 
                                  description=repo_data.get('description'))
    
    def save_repositories(self):
        """保存软件源列表"""
        try:
            data = [repo.to_dict() for repo in self.repositories]
            with open(self.repos_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            debug(f"Saved {len(self.repositories)} repositories")
        except Exception as e:
            error(f"Failed to save repositories: {e}")
    
    def add_repository(self, name: str, url: str, **kwargs) -> bool:
        """添加软件源"""
        # 规范化URL
        if not url.endswith('/'):
            url += '/'
        
        # 检查是否已存在
        for repo in self.repositories:
            if repo.url == url:
                warning(f"Repository already exists: {url}")
                return False
        
        repo = Repository(name=name, url=url, **kwargs)
        self.repositories.append(repo)
        self.save_repositories()
        debug(f"Added repository: {name} ({url})")
        return True
    
    def remove_repository(self, url: str) -> bool:
        """删除软件源"""
        for i, repo in enumerate(self.repositories):
            if repo.url == url:
                del self.repositories[i]
                # 清除缓存
                if url in self.packages_cache:
                    del self.packages_cache[url]
                self.save_repositories()
                debug(f"Removed repository: {repo.name} ({url})")
                return True
        return False
    
    def update_repository(self, url: str, **kwargs) -> bool:
        """更新软件源信息"""
        for repo in self.repositories:
            if repo.url == url:
                for key, value in kwargs.items():
                    if hasattr(repo, key):
                        setattr(repo, key, value)
                self.save_repositories()
                debug(f"Updated repository: {repo.name}")
                return True
        return False
    
    def get_repository(self, url: str) -> Optional[Repository]:
        """获取指定软件源"""
        for repo in self.repositories:
            if repo.url == url:
                return repo
        return None
    
    def parse_packages_data(self, data: str) -> List[Package]:
        """解析Packages文件内容"""
        packages = []
        current_package = Package()
        
        # Debug info for problematic repos
        debug_repos = ["apt.procurs.us", "repo.twickd.com"]
        is_debug_repo = any(repo in str(getattr(self, '_current_parsing_repo', '')) for repo in debug_repos)
        
        if is_debug_repo:
            debug(f"Parsing packages data, total chars: {len(data)}")
            debug(f"Number of lines: {len(data.split(chr(10)))}")
        
        for line in data.split('\n'):
            line = line.strip()
            
            if not line:
                # 空行表示一个包信息结束
                if current_package.package:
                    packages.append(current_package)
                    if is_debug_repo and len(packages) <= 3:
                        debug(f"Package {len(packages)}: {current_package.package} - {current_package.name}")
                    current_package = Package()
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace('-', '_')
                value = value.strip()
                
                # 映射字段名
                field_map = {
                    'package': 'package',
                    'version': 'version',
                    'section': 'section',
                    'description': 'description',
                    'name': 'name',
                    'author': 'author',
                    'maintainer': 'maintainer',
                    'depends': 'depends',
                    'filename': 'filename',
                    'size': 'size',
                    'md5sum': 'md5sum',
                    'sha256': 'sha256',
                    'icon': 'icon',
                    'depiction': 'depiction',
                    'tag': 'tag',
                    'installed_size': 'installed_size',
                    # Sileo-specific fields
                    'sileodepiction': 'sileodepiction',
                    'native_depiction': 'native_depiction',
                    'rootless': 'rootless',
                    'commercial': 'commercial',
                    'payment_link': 'payment_link',
                    'architecture': 'architecture'
                }
                
                if key in field_map:
                    setattr(current_package, field_map[key], value)
        
        # 处理最后一个包
        if current_package.package:
            packages.append(current_package)
        
        debug(f"Parsed {len(packages)} packages")
        if is_debug_repo and len(packages) == 0:
            debug("WARNING: No packages parsed! Check data format")
        
        return packages
    
    def _fetch_packages_multiarch(self, repo_url: str) -> Tuple[bool, List[Package]]:
        """获取仓库的多架构包"""
        debug(f"Fetching multi-arch packages from {repo_url}")
        
        package_files = [
            ('Packages.xz', lzma.decompress),
            ('Packages.bz2', bz2.decompress),
            ('Packages.gz', gzip.decompress),
            ('Packages', None)
        ]
        
        # 定义要尝试的架构路径
        arch_configs = [
            # (路径, 架构标签)
            ('dists/stable/main/binary-iphoneos-arm64/', 'iphoneos-arm64'),
            ('dists/stable/main/binary-iphoneos-arm64e/', 'iphoneos-arm64e'),
            ('dists/stable/main/binary-iphoneos-arm/', 'iphoneos-arm'),
            ('dists/./main/binary-iphoneos-arm64/', 'iphoneos-arm64'),  # 一些仓库使用 ./ 
            ('', None),  # 根目录（兼容旧仓库）
        ]
        
        all_packages = []
        found_architectures = []
        
        for arch_path, arch_label in arch_configs:
            for filename, decompress_func in package_files:
                if arch_path:
                    url = urljoin(repo_url, arch_path + filename)
                else:
                    url = urljoin(repo_url, filename)
                
                try:
                    response = self.client.get(url, timeout=15)
                    if response.status_code == 200:
                        # 检查内容类型
                        content_type = response.headers.get('content-type', '')
                        if 'text/html' in content_type:
                            continue
                        
                        # 解压数据
                        if decompress_func:
                            data = decompress_func(response.content).decode('utf-8', errors='ignore')
                        else:
                            data = response.text
                        
                        # 解析包
                        self._current_parsing_repo = repo_url
                        packages = self.parse_packages_data(data)
                        self._current_parsing_repo = None
                        
                        # 为包添加架构信息
                        if arch_label:
                            for pkg in packages:
                                if not pkg.architecture:
                                    pkg.architecture = arch_label
                        
                        all_packages.extend(packages)
                        found_architectures.append(arch_label or "root")
                        debug(f"Found {len(packages)} packages in {arch_label or 'root'}")
                        break  # 找到了就跳出内层循环
                        
                except Exception as e:
                    debug(f"Failed {url}: {str(e)[:100]}")
                    continue
        
        if not all_packages:
            return False, []
        
        debug(f"Total packages found: {len(all_packages)} from architectures: {found_architectures}")
        
        # 去重：如果同一个包有多个架构版本，保留所有不同架构的版本
        unique_packages = {}
        for pkg in all_packages:
            # 使用包名+版本+架构作为唯一键
            key = f"{pkg.package}_{pkg.version}_{pkg.architecture}"
            unique_packages[key] = pkg
        
        final_packages = list(unique_packages.values())
        debug(f"After deduplication: {len(final_packages)} packages")
        
        return True, final_packages
    
    def fetch_packages(self, repo_url: str, force_refresh: bool = False) -> Tuple[bool, List[Package]]:
        """获取软件源的包列表"""
        # 检查内存缓存
        if not force_refresh and repo_url in self.packages_cache:
            debug(f"Using memory cached packages for {repo_url}")
            return True, self.packages_cache[repo_url]
        
        # 检查磁盘缓存
        cache_file = self._get_cache_file_path(repo_url)
        if not force_refresh and cache_file.exists():
            # 检查缓存是否过期（24小时）
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() < 86400:  # 24小时
                try:
                    debug(f"Loading disk cached packages for {repo_url}")
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    packages = [Package(**pkg_data) for pkg_data in cached_data]
                    self.packages_cache[repo_url] = packages
                    return True, packages
                except Exception as e:
                    debug(f"Failed to load cache: {e}")
        
        debug(f"Fetching packages from {repo_url}")
        
        # 使用新的多架构获取方法
        success, packages = self._fetch_packages_multiarch(repo_url)
        if success:
            # 更新缓存
            self.packages_cache[repo_url] = packages
            
            # 保存到磁盘缓存
            self._save_packages_cache(repo_url, packages)
            
            # 更新源信息
            repo = self.get_repository(repo_url)
            if repo:
                repo.packages_count = len(packages)
                repo.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.save_repositories()
            
            return True, packages
        
        # 如果多架构方法失败，继续使用原有逻辑作为后备
        debug(f"Multi-arch fetch failed, trying legacy method...")
        
        # Enhanced debugging for problematic repos
        if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
            debug(f"*** Special debugging for problematic repo: {repo_url} ***")
        
        # 可能的Packages文件位置和压缩格式
        package_files = [
            ('Packages.xz', lzma.decompress),
            ('Packages.bz2', bz2.decompress),
            ('Packages.gz', gzip.decompress),
            ('Packages', None)  # None 表示不需要解压
        ]
        
        # 架构特定的路径
        architectures = [
            ('dists/stable/main/binary-iphoneos-arm64/', 'iphoneos-arm64'),
            ('dists/stable/main/binary-iphoneos-arm/', 'iphoneos-arm'),
            ('', None),  # 根目录
        ]
        
        all_packages = []
        packages_by_id = {}  # 用于合并相同包的不同架构版本
        
        for arch_path, arch_label in architectures:
            for filename, decompress_func in package_files:
                if arch_path:
                    url = urljoin(repo_url, f'{arch_path}{filename}')
                else:
                    url = urljoin(repo_url, filename)
                    
                debug(f"Trying {url}")
            
            try:
                response = self.client.get(url)
                debug(f"Response status: {response.status_code}")
                
                if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                    debug(f"Response headers: {dict(response.headers)}")
                    if response.status_code != 200:
                        debug(f"Response content preview: {response.text[:500]}")
                
                if response.status_code == 200:
                    debug(f"Successfully downloaded {filename}")
                    debug(f"Content length: {len(response.content)} bytes")
                    
                    # Check if response is HTML (error page)
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' in content_type:
                        warning("Server returned HTML instead of package data")
                        if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                            debug(f"HTML content: {response.text[:500]}")
                        continue
                    
                    # 解压数据
                    if decompress_func is None:
                        data = response.text
                    else:
                        data = decompress_func(response.content).decode('utf-8', errors='ignore')
                    
                    debug(f"Decompressed data length: {len(data)} chars")
                    if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                        debug(f"First 500 chars of data: {data[:500]}")
                    
                    # 解析包列表
                    self._current_parsing_repo = repo_url
                    packages = self.parse_packages_data(data)
                    self._current_parsing_repo = None
                    
                    # 更新缓存
                    self.packages_cache[repo_url] = packages
                    
                    # 保存到磁盘缓存
                    self._save_packages_cache(repo_url, packages)
                    
                    # 更新源信息
                    repo = self.get_repository(repo_url)
                    if repo:
                        repo.packages_count = len(packages)
                        repo.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.save_repositories()
                    
                    return True, packages
            except Exception as e:
                debug(f"Failed to fetch {url}: {e}")
                if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                    debug(f"Exception type: {type(e).__name__}")
                    debug(f"Full exception: {repr(e)}")
                continue
        
        # 尝试直接从根目录获取
        debug(f"Trying root directory approach for {repo_url}")
        for filename, decompress_func in package_files:
            url = urljoin(repo_url, filename)
            debug(f"Trying root directory: {url}")
            
            try:
                response = self.client.get(url)
                debug(f"Response status: {response.status_code}")
                
                if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                    debug(f"Response headers: {dict(response.headers)}")
                    if response.status_code != 200:
                        debug(f"Response content preview: {response.text[:500]}")
                
                if response.status_code == 200:
                    debug(f"Successfully downloaded {filename} from root")
                    debug(f"Content length: {len(response.content)} bytes")
                    
                    # Check if response is HTML (error page)
                    content_type = response.headers.get('content-type', '')
                    if 'text/html' in content_type:
                        warning("Server returned HTML instead of package data")
                        if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                            debug(f"HTML content: {response.text[:500]}")
                        continue
                    
                    if decompress_func is None:
                        data = response.text
                    else:
                        data = decompress_func(response.content).decode('utf-8', errors='ignore')
                    
                    debug(f"Decompressed data length: {len(data)} chars")
                    if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                        debug(f"First 500 chars of data: {data[:500]}")
                    
                    self._current_parsing_repo = repo_url
                    packages = self.parse_packages_data(data)
                    self._current_parsing_repo = None
                    self.packages_cache[repo_url] = packages
                    
                    # 保存到磁盘缓存
                    self._save_packages_cache(repo_url, packages)
                    
                    repo = self.get_repository(repo_url)
                    if repo:
                        repo.packages_count = len(packages)
                        repo.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self.save_repositories()
                    
                    return True, packages
            except Exception as e:
                debug(f"Failed to fetch {url}: {e}")
                if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
                    debug(f"Exception type: {type(e).__name__}")
                    debug(f"Full exception: {repr(e)}")
                continue
        
        # Try some alternative paths for specific repos
        if "apt.procurs.us" in repo_url or "repo.twickd.com" in repo_url:
            debug(f"Trying alternative paths for {repo_url}")
            alternative_paths = [
                "dists/stable/main/binary-iphoneos-arm64/Packages",
                "dists/stable/main/binary-iphoneos-arm64/Packages.bz2", 
                "./%C4%A1/Packages",  # Some repos use encoded paths
                "./%C4%A1/Packages.bz2",
                "stable/Packages",
                "stable/Packages.bz2",
                "./Packages",
                "./Packages.bz2"
            ]
            
            for path in alternative_paths:
                url = urljoin(repo_url, path)
                debug(f"Trying alternative: {url}")
                
                try:
                    response = self.client.get(url)
                    debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        debug("Success with alternative path!")
                        
                        # Check if response is HTML (error page)
                        content_type = response.headers.get('content-type', '')
                        if 'text/html' in content_type:
                            warning("Server returned HTML instead of package data")
                            continue
                        
                        if path.endswith('.bz2'):
                            data = bz2.decompress(response.content).decode('utf-8', errors='ignore')
                        elif path.endswith('.gz'):
                            data = gzip.decompress(response.content).decode('utf-8', errors='ignore')
                        elif path.endswith('.xz'):
                            data = lzma.decompress(response.content).decode('utf-8', errors='ignore')
                        else:
                            data = response.text
                        
                        self._current_parsing_repo = repo_url
                        packages = self.parse_packages_data(data)
                        self._current_parsing_repo = None
                        
                        if packages:
                            self.packages_cache[repo_url] = packages
                            self._save_packages_cache(repo_url, packages)
                            
                            repo = self.get_repository(repo_url)
                            if repo:
                                repo.packages_count = len(packages)
                                repo.last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                self.save_repositories()
                            
                            return True, packages
                except Exception as e:
                    debug(f"Alternative path failed: {e}")
        
        error(f"Failed to fetch packages from {repo_url}")
        if "apt.procurs.us" in repo_url:
            warning("apt.procurs.us appears to be offline (all requests return 404)")
            info("This repository may have been shut down or moved to a new location")
        elif "repo.twickd.com" in repo_url:
            warning("repo.twickd.com returns HTML error pages instead of package data")
            info("This repository may require authentication or special headers")
            info("Try using the Custom Headers button to add authentication headers")
            info("Example: Authorization: Bearer YOUR_TOKEN")
        return False, []
    
    def search_packages(self, query: str, repo_url: Optional[str] = None) -> List[Tuple[Repository, Package]]:
        """搜索包"""
        results = []
        query_lower = query.lower()
        
        repos_to_search = [self.get_repository(repo_url)] if repo_url else self.repositories
        
        for repo in repos_to_search:
            if not repo or not repo.enabled:
                continue
            
            success, packages = self.fetch_packages(repo.url)
            if success:
                for package in packages:
                    # 搜索包名、显示名称、描述
                    if (query_lower in package.package.lower() or
                        query_lower in package.name.lower() or
                        query_lower in package.description.lower()):
                        results.append((repo, package))
        
        debug(f"Found {len(results)} packages matching '{query}'")
        return results
    
    def download_package(self, repo_url: str, package: Package, download_path: str,
                        progress_callback=None) -> Tuple[bool, str]:
        """下载deb包"""
        if not package.filename:
            return False, "包信息中没有文件名"
        
        # 构建下载URL
        download_url = urljoin(repo_url, package.filename)
        debug(f"Downloading package from {download_url}")
        
        try:
            # 获取文件名
            filename = os.path.basename(package.filename)
            if not filename.endswith('.deb'):
                filename = f"{package.package}_{package.version}.deb"
            
            filepath = os.path.join(download_path, filename)
            
            # 下载文件
            with self.client.stream('GET', download_url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if progress_callback and total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                progress_callback(progress, downloaded, total_size)
            
            debug(f"Successfully downloaded to {filepath}")
            return True, filepath
            
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            error(error_msg)
            return False, error_msg
    
    def get_all_packages(self) -> List[Tuple[Repository, Package]]:
        """获取所有启用源的所有包"""
        all_packages = []
        
        for repo in self.repositories:
            if repo.enabled:
                success, packages = self.fetch_packages(repo.url)
                if success:
                    for package in packages:
                        all_packages.append((repo, package))
        
        debug(f"Total packages from all repos: {len(all_packages)}")
        return all_packages
    
    def get_packages_by_section(self, section: str) -> List[Tuple[Repository, Package]]:
        """按分类获取包"""
        results = []
        section_lower = section.lower()
        
        for repo in self.repositories:
            if repo.enabled:
                success, packages = self.fetch_packages(repo.url)
                if success:
                    for package in packages:
                        if package.section.lower() == section_lower:
                            results.append((repo, package))
        
        return results
    
    def refresh_all_repos(self, progress_callback=None):
        """刷新所有软件源"""
        total = len([r for r in self.repositories if r.enabled])
        current = 0
        
        for repo in self.repositories:
            if repo.enabled:
                current += 1
                if progress_callback:
                    progress_callback(f"正在刷新 {repo.name}...", current, total)
                
                self.fetch_packages(repo.url, force_refresh=True)
        
        debug(f"Refreshed all {total} repositories")
    
    def __del__(self):
        """析构函数，关闭 HTTP 客户端"""
        if hasattr(self, 'client'):
            self.client.close()
    
    def _get_cache_file_path(self, repo_url: str) -> Path:
        """获取缓存文件路径"""
        # 使用URL的哈希值作为文件名，避免特殊字符问题
        import hashlib
        url_hash = hashlib.md5(repo_url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"
    
    def _save_packages_cache(self, repo_url: str, packages: List[Package]):
        """保存包列表到磁盘缓存"""
        cache_file = self._get_cache_file_path(repo_url)
        try:
            # 将包列表转换为可JSON序列化的格式
            cache_data = [pkg.to_dict() for pkg in packages]
            
            # 写入缓存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            debug(f"Saved {len(packages)} packages to cache for {repo_url}")
        except Exception as e:
            error(f"Failed to save cache for {repo_url}: {e}")
    
    def clear_cache(self, repo_url: str = None):
        """清除缓存"""
        if repo_url:
            # 清除特定源的缓存
            cache_file = self._get_cache_file_path(repo_url)
            if cache_file.exists():
                cache_file.unlink()
                debug(f"Cleared cache for {repo_url}")
            if repo_url in self.packages_cache:
                del self.packages_cache[repo_url]
        else:
            # 清除所有缓存
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.packages_cache.clear()
            debug("Cleared all cache")
    
    def refresh_http_headers(self):
        """刷新HTTP客户端请求头（当越狱配置改变时调用）"""
        # 关闭旧客户端
        if hasattr(self, 'client'):
            self.client.close()
        
        # 创建新客户端使用更新的请求头
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=self.jailbreak_config.config.get_http_headers()
        )
        debug(f"HTTP headers refreshed - using {'Sileo' if self.jailbreak_config.config.use_sileo_headers else 'Cydia'} headers")
    
    def filter_packages_by_mode(self, packages: List[Package]) -> List[Package]:
        """根据当前越狱模式过滤包列表"""
        from .jailbreak_config import JailbreakMode
        
        if self.jailbreak_config.config.mode == JailbreakMode.ROOTLESS:
            # Rootless 模式下，只显示兼容的包
            filtered = [pkg for pkg in packages if pkg.is_rootless_compatible()]
            debug(f"Filtered {len(packages)} packages to {len(filtered)} for Rootless mode")
            return filtered
        else:
            # Rootful 模式下，显示所有包
            debug(f"Showing all {len(packages)} packages for Rootful mode")
            return packages
    
    def _load_custom_headers(self) -> Optional[Dict[str, str]]:
        """加载自定义请求头"""
        import json
        config_file = self.app_dir / "custom_headers.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    headers = json.load(f)
                    return headers
            except Exception as e:
                error(f"Failed to load custom headers: {e}")
        
        return None
