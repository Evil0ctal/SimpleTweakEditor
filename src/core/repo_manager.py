"""
Cydia/Sileo Repository Manager
管理插件源，解析Packages文件，下载deb包
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
    depiction: str = ""  # 详情页URL
    tag: str = ""  # 标签
    installed_size: str = ""  # 安装大小
    
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
        
        # 加载已保存的源
        self.load_repositories()
        
        # HTTP 客户端配置
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                'User-Agent': 'Cydia/1.1.32 CFNetwork/978.0.7 Darwin/18.7.0',
                'X-Machine': 'iPhone10,1',
                'X-Unique-ID': 'SimpleTweakEditor',
                'X-Firmware': '14.0'
            }
        )
        
        print(f"[DEBUG] RepoManager initialized with app_dir: {app_dir}")
        print(f"[DEBUG] Loaded {len(self.repositories)} repositories")
    
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
                    print(f"[ERROR] Failed to load default repositories from {path}: {e}")
        
        # 如果找不到文件，返回硬编码的默认值
        print("[WARNING] Could not find default_repositories.json, using hardcoded defaults")
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
            }
        ]
    
    def load_repositories(self):
        """加载保存的软件源"""
        if self.repos_file.exists():
            try:
                with open(self.repos_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.repositories = [Repository.from_dict(repo) for repo in data]
                print(f"[DEBUG] Loaded {len(self.repositories)} repositories from file")
            except Exception as e:
                print(f"[ERROR] Failed to load repositories: {e}")
                self.repositories = []
        else:
            # 首次使用，添加默认源
            print("[DEBUG] First run, adding default repositories")
            for repo_data in self._get_default_repositories():
                self.add_repository(repo_data['name'], repo_data['url'], 
                                  description=repo_data.get('description'))
    
    def save_repositories(self):
        """保存软件源列表"""
        try:
            data = [repo.to_dict() for repo in self.repositories]
            with open(self.repos_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] Saved {len(self.repositories)} repositories")
        except Exception as e:
            print(f"[ERROR] Failed to save repositories: {e}")
    
    def add_repository(self, name: str, url: str, **kwargs) -> bool:
        """添加软件源"""
        # 规范化URL
        if not url.endswith('/'):
            url += '/'
        
        # 检查是否已存在
        for repo in self.repositories:
            if repo.url == url:
                print(f"[WARNING] Repository already exists: {url}")
                return False
        
        repo = Repository(name=name, url=url, **kwargs)
        self.repositories.append(repo)
        self.save_repositories()
        print(f"[DEBUG] Added repository: {name} ({url})")
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
                print(f"[DEBUG] Removed repository: {repo.name} ({url})")
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
                print(f"[DEBUG] Updated repository: {repo.name}")
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
        
        for line in data.split('\n'):
            line = line.strip()
            
            if not line:
                # 空行表示一个包信息结束
                if current_package.package:
                    packages.append(current_package)
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
                    'installed_size': 'installed_size'
                }
                
                if key in field_map:
                    setattr(current_package, field_map[key], value)
        
        # 处理最后一个包
        if current_package.package:
            packages.append(current_package)
        
        print(f"[DEBUG] Parsed {len(packages)} packages")
        return packages
    
    def fetch_packages(self, repo_url: str, force_refresh: bool = False) -> Tuple[bool, List[Package]]:
        """获取软件源的包列表"""
        # 检查内存缓存
        if not force_refresh and repo_url in self.packages_cache:
            print(f"[DEBUG] Using memory cached packages for {repo_url}")
            return True, self.packages_cache[repo_url]
        
        # 检查磁盘缓存
        cache_file = self._get_cache_file_path(repo_url)
        if not force_refresh and cache_file.exists():
            # 检查缓存是否过期（24小时）
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age.total_seconds() < 86400:  # 24小时
                try:
                    print(f"[DEBUG] Loading disk cached packages for {repo_url}")
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    packages = [Package(**pkg_data) for pkg_data in cached_data]
                    self.packages_cache[repo_url] = packages
                    return True, packages
                except Exception as e:
                    print(f"[DEBUG] Failed to load cache: {e}")
        
        print(f"[DEBUG] Fetching packages from {repo_url}")
        
        # 可能的Packages文件位置和压缩格式
        package_files = [
            ('Packages.xz', lzma.decompress),
            ('Packages.bz2', bz2.decompress),
            ('Packages.gz', gzip.decompress),
            ('Packages', None)  # None 表示不需要解压
        ]
        
        for filename, decompress_func in package_files:
            url = urljoin(repo_url, f'dists/stable/main/binary-iphoneos-arm/{filename}')
            print(f"[DEBUG] Trying {url}")
            
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    print(f"[DEBUG] Successfully downloaded {filename}")
                    
                    # 解压数据
                    if decompress_func is None:
                        data = response.text
                    else:
                        data = decompress_func(response.content).decode('utf-8', errors='ignore')
                    
                    # 解析包列表
                    packages = self.parse_packages_data(data)
                    
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
                print(f"[DEBUG] Failed to fetch {url}: {e}")
                continue
        
        # 尝试直接从根目录获取
        for filename, decompress_func in package_files:
            url = urljoin(repo_url, filename)
            print(f"[DEBUG] Trying root directory: {url}")
            
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    print(f"[DEBUG] Successfully downloaded {filename} from root")
                    
                    if decompress_func is None:
                        data = response.text
                    else:
                        data = decompress_func(response.content).decode('utf-8', errors='ignore')
                    
                    packages = self.parse_packages_data(data)
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
                print(f"[DEBUG] Failed to fetch {url}: {e}")
                continue
        
        print(f"[ERROR] Failed to fetch packages from {repo_url}")
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
        
        print(f"[DEBUG] Found {len(results)} packages matching '{query}'")
        return results
    
    def download_package(self, repo_url: str, package: Package, download_path: str,
                        progress_callback=None) -> Tuple[bool, str]:
        """下载deb包"""
        if not package.filename:
            return False, "包信息中没有文件名"
        
        # 构建下载URL
        download_url = urljoin(repo_url, package.filename)
        print(f"[DEBUG] Downloading package from {download_url}")
        
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
            
            print(f"[DEBUG] Successfully downloaded to {filepath}")
            return True, filepath
            
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
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
        
        print(f"[DEBUG] Total packages from all repos: {len(all_packages)}")
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
        
        print(f"[DEBUG] Refreshed all {total} repositories")
    
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
            
            print(f"[DEBUG] Saved {len(packages)} packages to cache for {repo_url}")
        except Exception as e:
            print(f"[ERROR] Failed to save cache for {repo_url}: {e}")
    
    def clear_cache(self, repo_url: str = None):
        """清除缓存"""
        if repo_url:
            # 清除特定源的缓存
            cache_file = self._get_cache_file_path(repo_url)
            if cache_file.exists():
                cache_file.unlink()
                print(f"[DEBUG] Cleared cache for {repo_url}")
            if repo_url in self.packages_cache:
                del self.packages_cache[repo_url]
        else:
            # 清除所有缓存
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.packages_cache.clear()
            print("[DEBUG] Cleared all cache")
