# SimpleTweakEditor

iOS .deb Tweak Editor - 专业的iOS .deb文件编辑工具 / Professional iOS .deb Package Editor

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.0%2B-green)](https://pypi.org/project/PyQt6/)

## 功能特性 / Features

### 🔐 安全性 / Security
- **路径验证** - 防止路径遍历攻击
- **文件大小限制** - 防止资源耗尽（最大500MB）
- **安全的文件操作** - 使用原子操作和临时文件
- **权限管理** - 配置文件使用安全权限（0600）

### 🎯 核心功能 / Core Features
- **解包.deb文件** - 将.deb文件解压到文件夹
- **重新打包** - 将修改后的文件夹打包为.deb
- **拖放支持** - 直接拖放文件进行操作
- **Control文件编辑** - 内置编辑器和验证
- **批处理模式** - 支持命令行批量操作

### 🌍 用户体验 / User Experience
- **多语言支持** - 中文/英文界面
- **暗色模式** - 自动适配系统主题
- **状态保存** - 记住窗口大小和设置
- **智能提示** - 操作引导和错误提示

## 安装 / Installation

### 系统要求 / System Requirements
- Python 3.8+
- PyQt6
- dpkg-deb（Linux/macOS）

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
```

## 使用方法 / Usage

### GUI模式 / GUI Mode
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

## 项目结构 / Project Structure

```
SimpleTweakEditor/
├── main.py                    # 程序入口 / Main entry
├── requirements.txt           # 依赖列表 / Dependencies
├── README.md                 # 本文件 / This file
├── LICENSE                   # 许可证 / License
├── project_structure.md      # 详细架构文档 / Architecture docs
│
└── src/                      # 源代码 / Source code
    ├── core/                 # 核心模块 / Core modules
    │   ├── app.py           # 主应用逻辑 / Main app logic
    │   ├── config.py        # 配置管理 / Config management
    │   └── events.py        # 事件定义 / Event definitions
    │
    ├── ui/                   # 用户界面 / User interface
    │   ├── main_window.py   # 主窗口 / Main window
    │   ├── control_editor.py # Control编辑器 / Control editor
    │   ├── about_dialog_improved.py # 关于对话框 / About dialog
    │   └── styles.py        # 样式管理 / Style management
    │
    ├── workers/              # 后台任务 / Background tasks
    │   └── command_thread.py # 命令执行 / Command execution
    │
    ├── utils/                # 工具函数 / Utilities
    │   ├── file_operations.py # 文件操作 / File operations
    │   └── system_utils.py  # 系统工具 / System utilities
    │
    └── localization/        # 多语言 / Localization
        ├── language_manager.py # 语言管理 / Language manager
        └── translations.py  # 翻译数据 / Translation data
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

### v1.0.0 (2025-01)
- ✨ 完整的GUI界面
- 🔐 安全性增强
- 🌍 中英文支持
- 🎨 暗色模式支持
- 📦 模块化重构
- 🐛 修复已知问题

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

**注意 / Note**: 本工具仅用于合法的iOS开发和调试目的。请遵守相关法律法规。

**Note**: This tool is for legitimate iOS development and debugging purposes only. Please comply with relevant laws and regulations.