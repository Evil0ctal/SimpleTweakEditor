# SimpleTweakEditor 项目结构说明

## 📁 目录结构

```
SimpleTweakEditor/
├── 📄 main.py                    # 程序主入口
├── 📄 requirements.txt           # Python依赖
├── 📄 README.md                 # 项目说明
├── 📄 LICENSE                   # Apache 2.0许可证
├── 📄 RELEASE_NOTES.md          # v1.0.0发布说明
├── 📄 PROJECT_STRUCTURE.md      # 本文件
│
├── 📂 src/                      # 源代码目录
│   ├── 📂 core/                 # 核心功能模块
│   │   ├── app.py              # 应用程序主逻辑
│   │   ├── config.py           # 配置管理
│   │   └── events.py           # 事件定义
│   │
│   ├── 📂 ui/                   # 用户界面模块
│   │   ├── main_window.py      # 主窗口
│   │   ├── control_editor.py   # Control文件编辑器
│   │   ├── about_dialog_improved.py  # 关于对话框
│   │   └── styles.py           # 样式管理
│   │
│   ├── 📂 workers/              # 后台任务模块
│   │   └── command_thread.py   # 命令执行线程
│   │
│   ├── 📂 utils/                # 工具函数模块
│   │   ├── file_operations.py  # 文件操作
│   │   └── system_utils.py     # 系统工具
│   │
│   └── 📂 localization/         # 多语言支持
│       ├── language_manager.py  # 语言管理器
│       └── translations.py      # 翻译文本
│
├── 📂 icons/                    # 应用图标资源
│   ├── app_icon.icns           # macOS图标
│   ├── app_icon.ico            # Windows图标
│   ├── app_icon.png            # 通用PNG图标
│   └── ...                     # 各种尺寸的图标
│
├── 📂 build_scripts/            # 构建脚本
│   ├── 🔧 build_release.py      # PyInstaller构建脚本
│   ├── 🔧 build_release.sh      # 构建包装脚本
│   ├── 🔧 build_macos_app.py   # macOS .app构建脚本
│   ├── 🔧 build_linux_appimage.sh  # Linux AppImage构建脚本
│   ├── 🔧 prepare_release.sh    # 发布准备脚本
│   └── 🔧 clean_project.sh      # 项目清理脚本
│
└── 📂 releases/                 # 发布文件目录
    └── 📂 v1.0.0/              # 1.0.0版本发布文件
        ├── 📦 SimpleTweakEditor.app/     # macOS应用包
        ├── 📦 SimpleTweakEditor-1.0.0-macOS.dmg  # macOS安装包
        ├── 📦 SimpleTweakEditor-1.0.0-Darwin.tar.gz  # macOS压缩包
        ├── 📦 SimpleTweakEditor-1.0.0-source.tar.gz  # 源代码包
        └── 📄 SHA256SUMS        # 文件校验和
```

## 🚀 快速开始

### 开发环境运行
```bash
# 安装依赖
pip3 install -r requirements.txt

# 运行程序
python3 main.py
```

### 构建发布版本
```bash
# 一键构建所有版本
./prepare_release.sh

# 或单独构建macOS应用
python3 build_macos_app.py

# 清理构建文件
./clean_project.sh
```

## 📦 发布文件说明

### macOS版本

1. **SimpleTweakEditor.app** - 独立应用包
   - 可直接双击运行
   - 包含所有项目文件
   - 需要用户安装Python和PyQt6

2. **SimpleTweakEditor-1.0.0-macOS.dmg** - DMG安装包
   - 包含.app和说明文档
   - 用户友好的安装方式

3. **SimpleTweakEditor-1.0.0-Darwin.tar.gz** - 压缩包版本
   - 包含PyInstaller打包的单文件可执行程序
   - 已包含所有Python依赖

### 跨平台版本

4. **SimpleTweakEditor-1.0.0-source.tar.gz** - 源代码包
   - 完整的项目源代码
   - 可在任何支持Python的系统上运行

## 🛠️ 维护说明

### 添加新功能
1. 在相应的模块目录中添加代码
2. 更新 `translations.py` 添加新的界面文本
3. 测试功能
4. 更新版本号和发布说明

### 发布新版本
1. 更新版本号（在构建脚本中）
2. 编写 RELEASE_NOTES.md
3. 运行 `./prepare_release.sh`
4. 测试所有发布包
5. 创建Git标签并发布到GitHub

## ⚠️ 注意事项

1. **依赖要求**：
   - Python 3.8+
   - PyQt6
   - dpkg-deb（用于.deb文件操作）

2. **平台支持**：
   - ✅ macOS 10.13+
   - ✅ Linux (Ubuntu 18.04+)
   - ❌ Windows（不支持dpkg-deb）

3. **安全考虑**：
   - 文件大小限制500MB
   - 路径验证防止遍历攻击
   - 安全的文件权限设置