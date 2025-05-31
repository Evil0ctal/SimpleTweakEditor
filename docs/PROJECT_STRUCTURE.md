# SimpleTweakEditor 项目结构说明

*最后更新: 2025-05-31*

## 📁 目录结构

```
SimpleTweakEditor/
├── 📄 main.py                    # 程序主入口
├── 📄 requirements.txt           # Python依赖
├── 📄 README.md                 # 项目说明（中文）
├── 📄 README_EN.md             # 项目说明（英文）
├── 📄 LICENSE                   # Apache 2.0许可证
├── 📄 RELEASE_NOTES.md          # 发布说明（中文）
├── 📄 RELEASE_NOTES_EN.md       # 发布说明（英文）
│
├── 📂 src/                      # 源代码目录
│   ├── 📄 __init__.py          # 包初始化文件
│   ├── 📄 version.py           # 版本管理模块
│   │
│   ├── 📂 core/                 # 核心功能模块
│   │   ├── 📄 __init__.py      
│   │   ├── 📄 app.py           # 应用程序主逻辑
│   │   ├── 📄 config.py        # 配置管理
│   │   ├── 📄 events.py        # 事件定义
│   │   └── 📄 repo_manager.py  # 仓库管理器
│   │
│   ├── 📂 ui/                   # 用户界面模块
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main_window.py   # 主窗口
│   │   ├── 📄 control_editor.py # Control文件编辑器
│   │   ├── 📄 about_dialog_improved.py # 关于对话框
│   │   ├── 📄 interactive_terminal.py # 交互式终端
│   │   ├── 📄 interactive_terminal_improved.py # 改进版终端(实验性)
│   │   ├── 📄 package_browser_dialog.py # 软件包浏览器
│   │   ├── 📄 package_manager_widget.py # 软件包管理器
│   │   ├── 📄 repo_manager_dialog.py # 仓库管理对话框
│   │   └── 📄 styles.py        # 样式管理（20+主题）
│   │
│   ├── 📂 workers/              # 后台任务模块
│   │   ├── 📄 __init__.py
│   │   ├── 📄 command_thread.py # 命令执行线程
│   │   └── 📄 download_thread.py # 下载任务线程
│   │
│   ├── 📂 utils/                # 工具函数模块
│   │   ├── 📄 __init__.py
│   │   ├── 📄 file_operations.py # 文件操作（安全增强）
│   │   ├── 📄 dpkg_deb.py       # 跨平台dpkg实现 🆕
│   │   ├── 📄 terminal_dpkg_wrapper.py # 终端dpkg命令包装器 🆕
│   │   └── 📄 system_utils.py  # 系统工具
│   │
│   ├── 📂 localization/         # 多语言支持
│   │   ├── 📄 __init__.py
│   │   ├── 📄 language_manager.py # 语言管理器
│   │   └── 📄 translations.py  # 翻译文本（中/英）
│   │
│   └── 📂 resources/            # 资源文件
│       ├── 📄 __init__.py
│       └── 📄 default_repositories.json # 默认软件源配置
│
├── 📂 docs/                     # 文档目录
│   ├── 📄 FEATURE_ROADMAP.md   # 功能路线图
│   ├── 📄 PROJECT_STRUCTURE.md # 项目结构（本文件）
│   ├── 📄 QUICK_START.md       # 快速开始指南
│   ├── 📄 REPO_MANAGER_GUIDE.md # 仓库管理指南
│   └── 📄 THEMES.md            # 主题说明文档
│
├── 📂 screenshots/              # 截图目录
│   ├── 📄 SCREENSHOT_GUIDE.md  # 截图指南
│   ├── 📂 zh/                  # 中文界面截图
│   └── 📂 en/                  # 英文界面截图
│
├── 📂 icons/                    # 应用图标资源
│   ├── 📄 app_icon.icns        # macOS图标
│   ├── 📄 app_icon.ico         # Windows图标
│   ├── 📄 app_icon.png         # 通用PNG图标
│   ├── 📂 app_icon.iconset/    # macOS图标集
│   └── 📄 icon_*.png           # 各种尺寸的图标
│
├── 📄 build.py                 # 通用构建脚本 🆕
├── 📂 build_scripts/          # 构建脚本目录（已弃用）
│
└── 📂 releases/                 # 发布文件目录
    └── 📂 v1.0.*/              # 各版本发布文件
```

## 🏗️ 架构设计

### 核心模块说明

#### 1. **core/** - 核心业务逻辑
- `app.py`: 应用程序主类，管理生命周期
- `config.py`: 配置管理，处理用户设置持久化
- `events.py`: 自定义事件定义，用于组件通信
- `repo_manager.py`: 软件源管理，处理包下载和解析

#### 2. **ui/** - 用户界面
- `main_window.py`: 主窗口，包含所有主要功能入口
- `control_editor.py`: Control文件编辑器，支持语法高亮
- `interactive_terminal.py`: 交互式终端，真正的PTY实现
- `package_manager_widget.py`: 软件包管理界面
- `styles.py`: 样式管理器，支持20+主题切换

#### 3. **workers/** - 异步任务
- `command_thread.py`: 执行dpkg等系统命令
- `download_thread.py`: 处理软件包下载任务

#### 4. **utils/** - 工具函数
- `file_operations.py`: 安全的文件操作，防止路径遍历
- `dpkg_deb.py`: 纯Python实现的dpkg功能，支持Windows 🆕
- `terminal_dpkg_wrapper.py`: 终端dpkg命令包装器，解决跨平台问题 🆕
- `system_utils.py`: 系统相关工具，如dpkg-deb检测

#### 5. **localization/** - 国际化
- `language_manager.py`: 语言切换管理
- `translations.py`: 所有UI文本的翻译

## 🔧 技术栈

### 核心技术
- **Python 3.8+**: 主要开发语言
- **PyQt6**: 跨平台GUI框架
- **qt-material**: Material Design主题
- **httpx**: 异步HTTP客户端
- **Pillow**: 图像处理

### 开发工具
- **PyInstaller**: 打包独立可执行文件
- **pylint**: 代码质量检查
- **black**: 代码格式化

### 平台支持
- **macOS**: 10.13+
- **Linux**: Ubuntu 18.04+
- **Windows**: Windows 10+ (完整支持) 🆕

## 🔐 安全特性

### 文件操作安全
- 路径验证防止目录遍历攻击
- 文件大小限制（最大500MB）
- 原子操作确保数据完整性
- 临时文件安全清理

### 网络安全
- HTTPS连接到软件源
- 下载文件完整性校验
- 超时和重试机制

### 配置安全
- 配置文件权限0600
- 敏感信息不存储
- 安全的默认设置

## 🚀 构建和部署

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

### 构建发布版本
```bash
# 通用构建命令（v1.0.2新增）
python build.py
```

## 🪟 跨平台支持实现 (v1.0.2增强)

### 1. dpkg_deb.py 模块
纯Python实现的dpkg功能，解决Windows平台依赖问题：

#### 核心类
- `ARArchive`: 处理.deb文件的AR归档格式
- `DpkgDeb`: 主功能类，提供dpkg-deb兼容的API

#### 支持的功能
- ✅ 解包.deb文件 (`extract`/`unpack`)
- ✅ 构建.deb文件 (`build`/`pack`)
- ✅ 查看包信息 (`info`)
- ✅ 列出包内容 (`contents`)
- ✅ 验证包结构 (`verify`)

#### 智能权限处理
Windows环境下自动设置正确的Unix权限：
- DEBIAN脚本: 0755
- 可执行文件: 0755
- 普通文件: 0644
- 目录: 0755

### 2. terminal_dpkg_wrapper.py 模块
交互式终端的dpkg命令包装器：

#### 主要功能
- ✅ 自动检测dpkg可用性
- ✅ Windows上自动调用Python实现
- ✅ 处理which dpkg命令
- ✅ 统一命令输出格式

#### 支持的命令
- `dpkg -l`: 列出已安装包
- `dpkg-deb -x`: 解压.deb文件
- `dpkg-deb -b`: 构建.deb文件
- `dpkg-deb -I`: 查看包信息
- `dpkg-deb -c`: 列出包内容

## 📝 编码规范

### Python代码规范
- 遵循PEP 8
- 使用类型提示（准备中）
- 完整的docstring文档
- 异常处理和日志记录

### 文件头部格式 (v1.0.2统一)
所有Python文件都使用统一的头部格式：
```python
# -*- coding: utf-8 -*-
"""
创建时间: YYYY-MM-DD
作者: Evil0ctal

中文介绍:
[模块的中文说明]

英文介绍:
[Module description in English]
"""
```

### 命名规范
- 类名：PascalCase
- 函数/方法：snake_case
- 常量：UPPER_CASE
- 私有成员：_leading_underscore

### 文件组织
- 每个模块一个目录
- 相关功能放在一起
- 清晰的导入结构
- 避免循环依赖

## 🤝 贡献指南

### 如何贡献
1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

### 代码审查标准
- 代码质量和可读性
- 安全性考虑
- 性能影响
- 文档完整性

## 📚 相关文档

- [功能路线图](FEATURE_ROADMAP.md)
- [快速开始指南](QUICK_START.md)
- [仓库管理指南](REPO_MANAGER_GUIDE.md)
- [主题说明](THEMES.md)

---

*持续更新中，欢迎贡献！*