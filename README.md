# SimpleTweakEditor

<div align="center">

![SimpleTweakEditor Logo](https://img.shields.io/badge/SimpleTweakEditor-v1.0.2-blue?style=for-the-badge&logo=apple&logoColor=white)

[![License](https://img.shields.io/github/license/Evil0ctal/SimpleTweakEditor?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green?style=flat-square&logo=qt&logoColor=white)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor)
[![GitHub Stars](https://img.shields.io/github/stars/Evil0ctal/SimpleTweakEditor?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/stargazers)
[![Downloads](https://img.shields.io/github/downloads/Evil0ctal/SimpleTweakEditor/total?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/releases)
[![Release](https://img.shields.io/github/v/release/Evil0ctal/SimpleTweakEditor?style=flat-square)](https://github.com/Evil0ctal/SimpleTweakEditor/releases/latest)

**专业的iOS .deb文件编辑工具 / Professional iOS .deb Package Editor**

[English](README_EN.md) | [快速开始](docs/QUICK_START.md) | [下载](https://github.com/Evil0ctal/SimpleTweakEditor/releases)

</div>

## 📸 界面预览 / Screenshots

<div align="center">
<table>
  <tr>
    <td align="center">
      <img src="screenshots/zh/main_window_dark.png" width="400" alt="主界面-深色主题">
      <br>
      <sub><b>主界面</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/zh/package_manager.png" width="400" alt="软件包管理器">
      <br>
      <sub><b>软件包管理器</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/zh/interactive_terminal.png" width="400" alt="交互式终端">
      <br>
      <sub><b>交互式终端</b></sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="screenshots/zh/control_editor.png" width="400" alt="Control文件编辑器">
      <br>
      <sub><b>Control文件编辑器</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/zh/package_history.png" width="400" alt="软件包版本选择">
      <br>
      <sub><b>软件包版本选择</b></sub>
    </td>
    <td align="center">
      <img src="screenshots/zh/repo_manager.png" width="400" alt="软件源管理器">
      <br>
      <sub><b>仓库管理器</b></sub>
    </td>
  </tr>
</table>
</div>

## 功能特性 / Features

### 🔐 安全性 / Security
- **路径验证** - 防止路径遍历攻击
- **文件大小限制** - 防止资源耗尽（最大500MB）
- **安全的文件操作** - 使用原子操作和临时文件
- **权限管理** - 配置文件使用安全权限（0600）

### 🎯 核心功能 / Core Features
- **解包.deb文件** - 将.deb文件解压到文件夹
- **重新打包** - 将修改后的文件夹打包为.deb
- **跨平台.deb处理** - 纯Python实现，Windows下无需dpkg依赖
- **拖放支持** - 直接拖放文件进行操作
- **Control文件编辑** - 内置编辑器和验证
- **批处理模式** - 支持命令行批量操作
- **软件包管理** - 内置软件包浏览器和仓库管理
- **交互式终端** - 真正的PTY终端支持多标签页

### 🌍 用户体验 / User Experience
- **多语言支持** - 中文/英文界面，自动检测系统语言
- **多主题支持** - 暗色模式、亮色模式、彩色主题
- **状态保存** - 记住窗口大小和设置
- **智能提示** - 操作引导和错误提示
- **智能查找** - 自动在多个路径查找dpkg-deb工具
- **动态布局** - 智能适配不同屏幕尺寸
- **窗口居中** - 自动窗口居中功能

## 安装 / Installation

### 系统要求 / System Requirements
- Python 3.8+
- PyQt6
- dpkg-deb（Linux/macOS，Windows下使用内置纯Python实现）

### 安装步骤 / Setup

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor

# 创建虚拟环境 / Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# macOS用户安装dpkg / macOS users install dpkg
brew install dpkg

# Linux用户安装dpkg / Linux users install dpkg
sudo apt-get install dpkg

# Windows用户无需额外安装 / Windows users need no additional setup
# 程序自动使用内置纯Python dpkg实现
```

## 下载和使用 / Download and Usage

### 🚀 快速开始 / Quick Start

#### 下载预构建版本 / Download Pre-built Releases
- **macOS**: 
  - **推荐**: 下载独立版 `SimpleTweakEditor.app` (包含所有依赖，约31MB)
  - **备选**: 下载标准版 `.app` 或 `.dmg` 安装包 (需要Python环境)
- **Linux**: 下载对应的可执行文件
- 从 [Releases](https://github.com/Evil0ctal/SimpleTweakEditor/releases) 页面下载

#### 从源代码运行 / Run from Source
```bash
python main.py
```

### 命令行模式 / Command Line Mode
```bash
# 查看帮助 / Show help
python main.py --help

# 解包.deb文件 / Unpack .deb file
python main.py --unpack package.deb --output ./unpacked/

# 重新打包 / Repack folder
python main.py --repack ./package_folder/ --output package.deb

# 批处理模式 / Batch mode
python main.py --batch --unpack "*.deb"

# 设置语言 / Set language
python main.py --lang zh  # 中文
python main.py --lang en  # English
```

## 构建应用 / Building the Application

### 🔨 构建 macOS .app / Build macOS .app

```bash
# 进入构建脚本目录 / Enter build scripts directory
cd build_scripts

# 构建独立版应用包（推荐）/ Build standalone app bundle (recommended)
# 包含所有Python依赖，用户无需安装Python或PyQt6
python3 build_macos_app_standalone.py

# 或构建标准版应用包 / Or build standard app bundle
# 需要用户系统有Python和依赖
python3 build_macos_app.py

# 应用将生成在 / App will be created at:
# dist/SimpleTweakEditor.app
```

### 🐧 构建 Linux 版本 / Build for Linux

```bash
# 创建 AppImage 结构 / Create AppImage structure
./build_scripts/build_linux_appimage.sh

# 使用 PyInstaller 构建单文件版本 / Build single file with PyInstaller
python3 build_scripts/build_release.py
```

### 📦 一键构建所有版本 / Build All Versions

```bash
# 自动构建所有平台版本 / Auto build for all platforms
./build_scripts/prepare_release.sh

# 构建产物将整理在 / Builds will be organized in:
# releases/v1.0.0/
#   ├── macOS/
#   │   ├── SimpleTweakEditor.app
#   │   └── SimpleTweakEditor-1.0.0-macOS.dmg
#   └── Linux/
#       └── SimpleTweakEditor-1.0.0-Linux
```

## 项目结构 / Project Structure

```
SimpleTweakEditor/
├── main.py                    # 程序入口 / Main entry
├── requirements.txt           # 依赖列表 / Dependencies
├── README.md                 # 本文件 / This file
├── README_EN.md             # 英文文档 / English docs
├── RELEASE_NOTES.md         # 发布日志 / Release notes
├── LICENSE                   # 许可证 / License
├── docs/                     # 文档目录 / Documentation
│   ├── PROJECT_STRUCTURE.md  # 详细架构文档 / Architecture docs
│   ├── QUICK_START.md        # 快速开始指南 / Quick start guide
│   ├── FEATURE_ROADMAP.md    # 功能路线图 / Feature roadmap
│   ├── REPO_MANAGER_GUIDE.md # 仓库管理指南 / Repo manager guide
│   └── THEMES.md             # 主题说明 / Theme documentation
│
├── src/                      # 源代码 / Source code
    ├── core/                 # 核心模块 / Core modules
    │   ├── app.py           # 主应用逻辑 / Main app logic
    │   ├── config.py        # 配置管理 / Config management
    │   ├── events.py        # 事件定义 / Event definitions
    │   └── repo_manager.py  # 仓库管理 / Repository management
    │
    ├── ui/                   # 用户界面 / User interface
    │   ├── main_window.py   # 主窗口 / Main window
    │   ├── control_editor.py # Control编辑器 / Control editor
    │   ├── about_dialog_improved.py # 关于对话框 / About dialog
    │   ├── interactive_terminal.py # 交互式终端 / Interactive terminal
    │   ├── package_browser_dialog.py # 软件包浏览器 / Package browser
    │   ├── package_manager_widget.py # 软件包管理器 / Package manager
    │   ├── repo_manager_dialog.py # 仓库管理对话框 / Repo manager dialog
    │   └── styles.py        # 样式管理 / Style management
    │
    ├── workers/              # 后台任务 / Background tasks
    │   ├── command_thread.py # 命令执行 / Command execution
    │   └── download_thread.py # 下载任务 / Download tasks
    │
    ├── utils/                # 工具函数 / Utilities
    │   ├── file_operations.py # 文件操作 / File operations
    │   ├── dpkg_deb.py      # 跨平台dpkg实现 / Cross-platform dpkg
    │   └── system_utils.py  # 系统工具 / System utilities
    │
    ├── localization/        # 多语言 / Localization
    │   ├── language_manager.py # 语言管理 / Language manager
    │   └── translations.py  # 翻译数据 / Translation data
    │
    ├── resources/           # 资源文件 / Resources
    │   └── default_repositories.json # 默认软件源 / Default repositories
    │
    └── utils/               # 工具函数 / Utilities
        ├── file_operations.py # 文件操作 / File operations
        └── system_utils.py  # 系统工具 / System utilities
│
├── build_scripts/            # 构建脚本 / Build scripts
│   ├── build_macos_app.py   # macOS 标准版 .app 构建脚本
│   ├── build_macos_app_standalone.py # macOS 独立版 .app 构建脚本
│   ├── build_linux_appimage.sh # Linux AppImage 脚本
│   ├── prepare_release.sh   # 发布准备脚本
│   └── clean_all.sh        # 清理所有构建文件
│
└── releases/                # 发布文件 / Release files
    └── v1.0.0/             # 版本发布目录
```

## 开发指南 / Development Guide

### 代码质量 / Code Quality
- 遵循PEP 8规范
- 使用类型提示（准备中）
- 完整的错误处理
- 安全第一的设计理念

### 添加新功能 / Adding Features
1. 文件操作添加到 `utils/file_operations.py`
2. UI组件添加到 `ui/` 目录
3. 后台任务继承 `CommandThread` 类
4. 翻译添加到 `translations.py`

### 贡献指南 / Contributing
1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 更新日志 / Changelog

### v1.0.2 (2025-05-30)
- 🪟 **Windows支持** - 添加完整的Windows平台支持
- 🔧 **纯Python dpkg实现** - 无需依赖系统dpkg，支持所有.deb操作
- 🔐 **Windows权限处理** - 智能处理Unix权限在Windows环境下的映射
- 📦 **多压缩格式支持** - 支持gz/xz/lzma压缩格式的.deb文件
- ⚡ **性能优化** - 改进文件处理和内存使用效率
- 🛡️ **安全增强** - 增强路径遍历保护和文件验证

### v1.0.1 (2025-05-28)
- 🔧 **UI布局优化** - 修复交互式终端组件重叠和显示问题
- 🌍 **语言切换稳定性** - 解决切换语言时的崩溃问题
- 🎨 **字体兼容性** - 改进跨平台字体处理，解决macOS字体警告
- 📐 **动态布局** - 优化窗口大小适配和组件自动调整
- 🖥️ **终端改进** - 真正的PTY终端支持，多标签页功能
- 📦 **软件包管理** - 内置软件包浏览器和仓库管理功能
- 🎯 **窗口居中** - 自动窗口定位和状态保存
- 🗂️ **文档整理** - 重新组织项目文档结构

### v1.0.0 (2025-05-24)
- ✨ 首次正式发布
- 🔐 安全性增强和路径验证
- 🌍 中英文支持，自动检测系统语言
- 🎨 多主题支持（暗色、亮色、彩色）
- 📦 模块化重构，提升代码质量
- 🚀 独立版.app构建，包含所有依赖
- 🔍 智能查找dpkg-deb工具路径

详细更新日志请查看 [RELEASE_NOTES.md](RELEASE_NOTES.md)

## 许可证 / License

本项目采用 Apache License 2.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details

## 致谢 / Acknowledgments

- PyQt6 开发团队
- dpkg 维护者
- 所有贡献者

## 联系方式 / Contact

- 作者 / Author: Evil0ctal
- GitHub: https://github.com/Evil0ctal
- 项目主页 / Project: https://github.com/Evil0ctal/SimpleTweakEditor

---

<div align="center">

**注意 / Note**: 本工具仅用于合法的iOS开发和调试目的。请遵守相关法律法规。

**Note**: This tool is for legitimate iOS development and debugging purposes only. Please comply with relevant laws and regulations.

---

Made with ❤️ by [Evil0ctal](https://github.com/Evil0ctal)

⭐ 如果觉得有帮助，请给项目一个Star！/ Star this project if you find it helpful!

</div>