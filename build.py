#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleTweakEditor Universal Build Script
通用构建脚本 - 自动检测平台并构建对应格式

支持平台:
- Windows: PyInstaller 可执行文件 (.exe)
- macOS: PyInstaller 可执行文件 + .app bundle
- Linux: PyInstaller 可执行文件 + AppImage

Author: Evil0ctal
Version: 1.0.0
"""

import os
import sys
import platform
import shutil
import subprocess
import json
import plistlib
import tempfile
import zipfile
from pathlib import Path


class UniversalBuilder:
    """通用构建器类"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir
        self.app_name = "SimpleTweakEditor"
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # 获取版本号
        sys.path.insert(0, str(self.project_root / 'src'))
        try:
            from version import APP_VERSION
            self.version = APP_VERSION
        except ImportError:
            self.version = "1.0.2"
        
        # 平台特定配置
        self.platform_configs = {
            'windows': {
                'extension': '.exe',
                'icon': 'icons/app_icon.ico',
                'separator': ';',
                'executable_name': f'{self.app_name}.exe'
            },
            'darwin': {
                'extension': '',
                'icon': 'icons/app_icon.icns',
                'separator': ':',
                'executable_name': self.app_name
            },
            'linux': {
                'extension': '',
                'icon': 'icons/app_icon.png',
                'separator': ':',
                'executable_name': self.app_name
            }
        }
        
        self.config = self.platform_configs.get(self.system, self.platform_configs['linux'])
        
    def log(self, message, emoji="ℹ️"):
        """带表情符号的日志输出"""
        print(f"{emoji} {message}")
        
    def run_command(self, cmd, cwd=None, check=True):
        """执行命令并处理错误"""
        self.log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}", "🔨")
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout:
                print(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "❌")
            if e.stderr:
                print(f"Error: {e.stderr}")
            if check:
                sys.exit(1)
            return e
            
    def clean_build(self):
        """清理构建文件"""
        self.log("Cleaning previous builds...", "🧹")
        
        # 要清理的目录和文件
        clean_targets = [
            "build", "dist", "__pycache__",
            f"{self.app_name}.spec"
        ]
        
        for target in clean_targets:
            target_path = self.project_root / target
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
                    
        # 递归清理 __pycache__
        for pycache in self.project_root.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
                
        self.log("Cleanup completed", "✅")
        
    def check_dependencies(self):
        """检查构建依赖"""
        self.log("Checking dependencies...", "📦")
        
        required_packages = ["pyinstaller", "PyQt6", "Pillow"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.lower().replace("-", "_"))
                self.log(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)
                self.log(f"✗ {package}", "❌")
                
        if missing_packages:
            self.log("Installing missing dependencies...", "📥")
            for package in missing_packages:
                self.run_command([sys.executable, "-m", "pip", "install", package])
                
        self.log("Dependencies check completed", "✅")
        
    def build_executable(self):
        """构建可执行文件"""
        self.log(f"Building executable for {self.system}...", "🔨")
        
        # PyInstaller 命令基础参数
        cmd = [
            "pyinstaller",
            "--name", self.app_name,
            "--onefile",
            "--clean",
            "--noconfirm",
            "--add-data", f"icons{self.config['separator']}icons",
            "--add-data", f"src{self.config['separator']}src",
            "--hidden-import", "PyQt6.QtCore",
            "--hidden-import", "PyQt6.QtGui", 
            "--hidden-import", "PyQt6.QtWidgets",
            "--hidden-import", "PIL",
            "--hidden-import", "PIL.Image",
        ]
        
        # 添加图标
        icon_path = self.project_root / self.config['icon']
        if icon_path.exists():
            cmd.extend(["--icon", str(icon_path)])
            
        # Windows 特定参数
        if self.system == "windows":
            cmd.append("--windowed")  # 隐藏控制台窗口
            
        # macOS 特定参数  
        elif self.system == "darwin":
            cmd.append("--windowed")
            
        cmd.append("main.py")
        
        # 执行构建
        self.run_command(cmd)
        
        # 检查生成的可执行文件
        exe_path = self.project_root / "dist" / self.config['executable_name']
        if not exe_path.exists():
            self.log(f"Executable not found at {exe_path}", "❌")
            return False
            
        self.log("Executable built successfully", "✅")
        return True
        
    def create_macos_app(self):
        """创建 macOS .app bundle"""
        if self.system != "darwin":
            return
            
        self.log("Creating macOS .app bundle...", "🍎")
        
        app_path = self.project_root / "dist" / f"{self.app_name}.app"
        contents_path = app_path / "Contents"
        macos_path = contents_path / "MacOS"
        resources_path = contents_path / "Resources"
        
        # 创建目录结构
        macos_path.mkdir(parents=True, exist_ok=True)
        resources_path.mkdir(parents=True, exist_ok=True)
        
        # 移动可执行文件
        exe_src = self.project_root / "dist" / self.app_name
        exe_dst = macos_path / self.app_name
        if exe_src.exists():
            shutil.move(str(exe_src), str(exe_dst))
            os.chmod(exe_dst, 0o755)
            
        # 复制图标
        icon_src = self.project_root / "icons" / "app_icon.icns"
        if icon_src.exists():
            icon_dst = resources_path / f"{self.app_name}.icns"
            shutil.copy2(icon_src, icon_dst)
            
        # 创建 Info.plist
        info_plist = {
            "CFBundleDevelopmentRegion": "en",
            "CFBundleExecutable": self.app_name,
            "CFBundleIconFile": f"{self.app_name}.icns",
            "CFBundleIdentifier": f"com.evil0ctal.{self.app_name}",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": self.app_name,
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": self.version,
            "CFBundleVersion": self.version,
            "LSMinimumSystemVersion": "10.13",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "CFBundleDisplayName": "SimpleTweakEditor",
            "CFBundleDocumentTypes": [
                {
                    "CFBundleTypeExtensions": ["deb"],
                    "CFBundleTypeName": "Debian Package",
                    "CFBundleTypeRole": "Editor",
                    "LSHandlerRank": "Owner"
                }
            ]
        }
        
        plist_path = contents_path / "Info.plist"
        with open(plist_path, 'wb') as f:
            plistlib.dump(info_plist, f)
            
        self.log("macOS .app bundle created", "✅")
        
    def create_linux_appimage(self):
        """创建 Linux AppImage"""
        if self.system != "linux":
            return
            
        self.log("Creating Linux AppImage...", "🐧")
        
        appdir = self.project_root / "dist" / f"{self.app_name}.AppDir"
        
        # 创建 AppDir 结构
        (appdir / "usr" / "bin").mkdir(parents=True, exist_ok=True)
        (appdir / "usr" / "share" / "applications").mkdir(parents=True, exist_ok=True)
        (appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True, exist_ok=True)
        
        # 复制可执行文件
        exe_src = self.project_root / "dist" / self.app_name
        exe_dst = appdir / "usr" / "bin" / self.app_name
        if exe_src.exists():
            shutil.copy2(exe_src, exe_dst)
            os.chmod(exe_dst, 0o755)
            
        # 复制图标
        icon_src = self.project_root / "icons" / "app_icon.png"
        if icon_src.exists():
            icon_dst = appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{self.app_name.lower()}.png"
            shutil.copy2(icon_src, icon_dst)
            
        # 创建 .desktop 文件
        desktop_content = f"""[Desktop Entry]
Type=Application
Name={self.app_name}
GenericName=iOS .deb Package Editor
Comment=Professional iOS .deb package editor with modern GUI
Exec={self.app_name}
Icon={self.app_name.lower()}
Categories=Development;Utility;
Terminal=false
MimeType=application/vnd.debian.binary-package;
Keywords=deb;package;ios;tweak;editor;
"""
        
        desktop_path = appdir / "usr" / "share" / "applications" / f"{self.app_name.lower()}.desktop"
        desktop_path.write_text(desktop_content)
        
        # 创建 AppRun
        apprun_content = f"""#!/bin/bash
# SimpleTweakEditor AppImage Launcher

HERE="$(dirname "$(readlink -f "${{BASH_SOURCE[0]}}")")"
export PATH="${{HERE}}/usr/bin:${{PATH}}"
exec "${{HERE}}/usr/bin/{self.app_name}" "$@"
"""
        
        apprun_path = appdir / "AppRun"
        apprun_path.write_text(apprun_content)
        os.chmod(apprun_path, 0o755)
        
        # 创建顶级 .desktop 文件
        shutil.copy2(desktop_path, appdir / f"{self.app_name.lower()}.desktop")
        
        # 创建顶级图标链接
        if icon_src.exists():
            shutil.copy2(icon_src, appdir / f"{self.app_name.lower()}.png")
            
        self.log("Linux AppImage structure created", "✅")
        
    def create_windows_installer(self):
        """为 Windows 创建简单的批处理启动器"""
        if self.system != "windows":
            return
            
        self.log("Creating Windows launcher...", "🪟")
        
        # 创建批处理启动器
        launcher_content = f"""@echo off
REM SimpleTweakEditor Windows Launcher
REM Version {self.version}

echo Starting SimpleTweakEditor v{self.version}...
echo.

REM 检查可执行文件是否存在
if not exist "%~dp0{self.app_name}.exe" (
    echo Error: {self.app_name}.exe not found!
    echo Please make sure the executable is in the same directory as this launcher.
    pause
    exit /b 1
)

REM 启动程序
start "" "%~dp0{self.app_name}.exe" %*

REM 如果需要保持窗口打开，取消下面一行的注释
REM pause
"""
        
        launcher_path = self.project_root / "dist" / f"{self.app_name}_launcher.bat"
        launcher_path.write_text(launcher_content, encoding='utf-8')
        
        self.log("Windows launcher created", "✅")
        
    def organize_release_files(self):
        """整理发布文件"""
        self.log("Organizing release files...", "📁")
        
        release_dir = self.project_root / "releases" / f"v{self.version}"
        platform_dir = release_dir / self.system.title()
        
        # 创建发布目录
        platform_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制文件到发布目录
        dist_dir = self.project_root / "dist"
        
        if self.system == "windows":
            # Windows: 复制 .exe 和启动器
            exe_files = list(dist_dir.glob("*.exe"))
            bat_files = list(dist_dir.glob("*.bat"))
            
            for file in exe_files + bat_files:
                shutil.copy2(file, platform_dir)
                
        elif self.system == "darwin":
            # macOS: 复制 .app bundle
            app_bundle = dist_dir / f"{self.app_name}.app"
            if app_bundle.exists():
                dest_app = platform_dir / f"{self.app_name}.app"
                if dest_app.exists():
                    shutil.rmtree(dest_app)
                shutil.copytree(app_bundle, dest_app)
                
        elif self.system == "linux":
            # Linux: 复制可执行文件和 AppDir
            exe_file = dist_dir / self.app_name
            appdir = dist_dir / f"{self.app_name}.AppDir"
            
            if exe_file.exists():
                shutil.copy2(exe_file, platform_dir)
                
            if appdir.exists():
                dest_appdir = platform_dir / f"{self.app_name}.AppDir"
                if dest_appdir.exists():
                    shutil.rmtree(dest_appdir)
                shutil.copytree(appdir, dest_appdir)
                
        # 复制文档文件
        docs = ["README.md", "README_EN.md", "LICENSE", "RELEASE_NOTES.md", "RELEASE_NOTES_EN.md"]
        for doc in docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                shutil.copy2(doc_path, platform_dir)
                
        self.log(f"Release files organized in {platform_dir}", "✅")
        return platform_dir
        
    def create_release_archive(self, platform_dir):
        """创建带版本号的压缩文件"""
        self.log("Creating release archive...", "📦")
        
        # 生成压缩文件名
        platform_name = self.system.title()
        if self.system == "darwin":
            platform_name = "macOS"
        
        archive_name = f"{self.app_name}-v{self.version}-{platform_name}"
        if self.arch == "arm64" and self.system == "darwin":
            archive_name += "-Apple-Silicon"
        elif self.arch == "x86_64":
            archive_name += "-x64"
        elif "arm" in self.arch.lower():
            archive_name += "-ARM"
            
        archive_path = platform_dir.parent / f"{archive_name}.zip"
        
        # 创建ZIP文件
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            # 添加平台目录中的所有文件
            for file_path in platform_dir.rglob("*"):
                if file_path.is_file():
                    # 计算相对路径，确保在ZIP中有正确的结构
                    arcname = file_path.relative_to(platform_dir)
                    zipf.write(file_path, arcname)
                    
        # 计算压缩比
        original_size = sum(f.stat().st_size for f in platform_dir.rglob("*") if f.is_file())
        compressed_size = archive_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        self.log(f"Archive created: {archive_path.name}", "✅")
        self.log(f"Original size: {original_size:,} bytes", "📏")
        self.log(f"Compressed size: {compressed_size:,} bytes", "📏")
        self.log(f"Compression ratio: {compression_ratio:.1f}%", "📊")
        
        return archive_path
    
    def cleanup_after_build(self):
        """构建完成后清理临时文件"""
        self.log("Cleaning up temporary build files...", "🧹")
        
        # 清理dist目录（保留releases目录）
        dist_dir = self.project_root / "dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
            
        # 清理build目录
        build_dir = self.project_root / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
            
        # 清理.spec文件
        spec_file = self.project_root / f"{self.app_name}.spec"
        if spec_file.exists():
            spec_file.unlink()
            
        # 清理Python缓存
        for pycache in self.project_root.rglob("__pycache__"):
            if pycache.is_dir():
                try:
                    shutil.rmtree(pycache)
                except (OSError, PermissionError):
                    pass  # 忽略无法删除的缓存
                    
        self.log("Temporary files cleaned up", "✅")
        
    def show_build_info(self):
        """显示构建信息"""
        self.log("Build Information", "📋")
        print(f"  App Name: {self.app_name}")
        print(f"  Version: {self.version}")
        print(f"  Platform: {self.system.title()}")
        print(f"  Architecture: {self.arch}")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Project Root: {self.project_root}")
        print()
        
    def build(self):
        """执行完整构建过程"""
        self.log(f"Starting universal build for {self.system.title()}...", "🚀")
        print("=" * 60)
        
        # 显示构建信息
        self.show_build_info()
        
        try:
            # 1. 清理构建文件
            self.clean_build()
            
            # 2. 检查依赖
            self.check_dependencies()
            
            # 3. 构建可执行文件
            if not self.build_executable():
                return False
                
            # 4. 平台特定处理
            if self.system == "darwin":
                self.create_macos_app()
            elif self.system == "linux":
                self.create_linux_appimage()
            elif self.system == "windows":
                self.create_windows_installer()
                
            # 5. 整理发布文件
            platform_dir = self.organize_release_files()
            
            # 6. 创建压缩文件
            archive_path = self.create_release_archive(platform_dir)
            
            self.log("Build completed successfully!", "🎉")
            print("=" * 60)
            
            # 显示输出位置
            self.log(f"Release files available at: {platform_dir}", "📁")
            self.log(f"Archive created at: {archive_path}", "📦")
            
            # 列出生成的文件
            print("\nRelease contents:")
            if platform_dir.exists():
                for file in sorted(platform_dir.rglob("*")):
                    if file.is_file():
                        size = file.stat().st_size
                        print(f"  📄 {file.name} ({size:,} bytes)")
                        
            print(f"\nCompressed archive:")
            if archive_path.exists():
                size = archive_path.stat().st_size
                print(f"  📦 {archive_path.name} ({size:,} bytes)")
            
            # 7. 清理临时构建文件
            self.cleanup_after_build()
                        
            return True
            
        except Exception as e:
            self.log(f"Build failed: {e}", "❌")
            return False


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("""
SimpleTweakEditor Universal Build Script

Usage:
    python build.py [options]

Options:
    -h, --help    Show this help message

This script automatically detects your platform and builds the appropriate format:
- Windows: PyInstaller executable (.exe) + launcher
- macOS: PyInstaller executable + .app bundle  
- Linux: PyInstaller executable + AppImage structure

The script will:
1. Clean previous builds
2. Check and install dependencies
3. Build platform-specific executable
4. Create platform-specific packages
5. Organize files in releases/vX.X.X/ directory
""")
        return
        
    builder = UniversalBuilder()
    success = builder.build()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
