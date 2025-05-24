#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleTweakEditor macOS App Builder - Standalone Version
Creates a .app bundle that uses PyInstaller executable

Author: Evil0ctal
Version: 1.0.0
"""

import os
import sys
import shutil
import subprocess
import plistlib


def create_standalone_app():
    """创建使用PyInstaller可执行文件的.app包"""
    print("🍎 Building SimpleTweakEditor.app (Standalone)...")
    
    # 项目路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    app_name = "SimpleTweakEditor"
    version = "1.0.0"
    
    # 首先使用PyInstaller构建独立可执行文件
    print("🔨 Building standalone executable with PyInstaller...")
    os.chdir(project_root)
    
    pyinstaller_cmd = [
        "pyinstaller",
        "--name", app_name,
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--add-data", "icons:icons",
        "--add-data", "src:src",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui", 
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "main.py"
    ]
    
    if os.path.exists("dist/SimpleTweakEditor.app"):
        shutil.rmtree("dist/SimpleTweakEditor.app")
    
    result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ PyInstaller failed: {result.stderr}")
        return None
        
    # 检查生成的可执行文件
    exe_path = os.path.join(project_root, "dist", app_name)
    if not os.path.exists(exe_path):
        print(f"❌ Executable not found at {exe_path}")
        return None
        
    print("✅ Standalone executable created")
    
    # 创建.app目录结构
    app_path = os.path.join(project_root, "dist", f"{app_name}.app")
    contents_path = os.path.join(app_path, "Contents")
    macos_path = os.path.join(contents_path, "MacOS")
    resources_path = os.path.join(contents_path, "Resources")
    
    # 清理旧的.app
    if os.path.exists(app_path):
        shutil.rmtree(app_path)
    
    # 创建目录
    os.makedirs(macos_path, exist_ok=True)
    os.makedirs(resources_path, exist_ok=True)
    
    # 复制可执行文件到.app
    shutil.copy2(exe_path, os.path.join(macos_path, app_name))
    
    # 复制图标
    icns_src = os.path.join(project_root, "icons", "app_icon.icns")
    if os.path.exists(icns_src):
        icns_dst = os.path.join(resources_path, f"{app_name}.icns")
        shutil.copy2(icns_src, icns_dst)
    
    # 创建Info.plist
    info_plist = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": app_name,
        "CFBundleIconFile": f"{app_name}.icns",
        "CFBundleIdentifier": f"com.evil0ctal.{app_name}",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": app_name,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": "10.13",
        "NSHighResolutionCapable": True,
        "NSSupportsAutomaticGraphicsSwitching": True,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeExtensions": ["deb"],
                "CFBundleTypeName": "Debian Package",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Default"
            }
        ],
        "NSRequiresAquaSystemAppearance": False,
    }
    
    plist_path = os.path.join(contents_path, "Info.plist")
    with open(plist_path, "wb") as f:
        plistlib.dump(info_plist, f)
    
    # 清理PyInstaller临时文件
    shutil.rmtree(os.path.join(project_root, "build"), ignore_errors=True)
    os.remove(os.path.join(project_root, f"{app_name}.spec")) if os.path.exists(f"{app_name}.spec") else None
    
    print(f"✅ {app_name}.app (Standalone) created successfully!")
    print(f"📍 Location: {app_path}")
    print(f"📦 This version includes all dependencies")
    
    return app_path


def main():
    """主函数"""
    print("🚀 SimpleTweakEditor Standalone App Builder")
    print("="*50)
    
    # 检查系统
    if sys.platform != "darwin":
        print("❌ This script is for macOS only!")
        return
    
    # 构建应用
    create_standalone_app()
    
    print("\n✨ Build completed!")
    print("\n📌 This standalone version:")
    print("- Includes all Python dependencies")
    print("- No need to install PyQt6 or Python")
    print("- Larger file size (~31MB)")
    print("- dpkg still needs to be installed separately")


if __name__ == "__main__":
    main()