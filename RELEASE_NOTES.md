# SimpleTweakEditor 发布日志

<div align="center">

[English](RELEASE_NOTES_EN.md) | 中文

</div>

## 🪟 v1.0.2 (2025-05-30)

### Windows平台支持与跨平台增强

本版本的主要亮点是添加了完整的Windows平台支持，通过纯Python实现解决了Windows环境下缺少dpkg依赖的问题。

#### 🆕 重大新功能
- **完整Windows支持** - 在Windows平台上提供与macOS/Linux相同的完整功能
- **纯Python dpkg实现** - 完全重写.deb文件处理逻辑，无需依赖系统dpkg工具
- **跨平台权限处理** - 智能处理Unix文件权限在Windows环境下的映射
- **多压缩格式支持** - 支持处理gz、xz、lzma等多种压缩格式的.deb文件

#### 🔧 技术改进
- **AR归档格式处理** - 实现完整的AR归档读写功能
- **安全路径验证** - 增强防止路径遍历攻击的安全措施
- **权限智能映射** - Windows环境下自动为DEBIAN脚本和bin目录文件设置可执行权限
- **文件完整性验证** - 增强.deb包的验证和测试功能

#### 📦 兼容性增强
- **向后兼容** - 保持与现有代码的完全兼容性
- **多平台构建** - 更新构建脚本以支持跨平台发布
- **文档更新** - 更新README和发布说明以反映Windows支持

### 技术实现细节
- 实现了完整的`dpkg_deb.py`模块，提供与dpkg-deb相同的API
- 支持解包(extract)、重新打包(build)、信息查看(info)、内容列表(contents)和验证(verify)
- 在Windows环境下自动检测并设置合适的Unix权限（755用于可执行文件，644用于普通文件）
- 支持lzma压缩格式，兼容较老的iOS包格式

---

## 🔧 v1.0.1 (2025-05-28)

### Bug修复与改进

本版本专注于稳定性改进、UI布局修复和基于v1.0.0反馈的用户体验增强。

#### 🐛 关键Bug修复
- **语言切换稳定性** - 修复由于缺少UI组件检查导致的语言切换时崩溃问题
- **UI布局问题** - 解决主窗口和交互式终端中的组件重叠问题
- **字体兼容性** - 通过实现合适的字体回退机制修复macOS字体警告
- **终端显示** - 修正终端界面的高度限制和分割器方向问题

#### ✨ 功能增强
- **动态布局系统** - 改进窗口大小适配和组件自动调整
- **窗口管理** - 增强自动窗口居中和状态持久化
- **交互式终端** - 真正的PTY终端支持，改进多标签页功能
- **软件包管理** - 增强内置软件包浏览器和仓库管理
- **文档整理** - 重新组织项目结构，使用专用docs文件夹

#### 🔧 技术改进
- 修复更新命令预设时的AttributeError错误
- 改进跨平台字体处理
- 增强UI组件交互的错误处理
- 优化不同屏幕尺寸的布局计算

### 自v1.0.0以来的新特性
- 更稳定的语言切换，无崩溃
- 更好的终端体验，支持真正的PTY
- 改进的UI响应性和布局管理
- 增强的软件包管理功能
- 更清晰的项目文档结构

---

## 🎉 v1.0.0 (2025-05-24)

### 首次正式发布

我们很高兴宣布SimpleTweakEditor首次正式发布 - 一个具有现代GUI界面的专业iOS .deb软件包编辑器。

#### 🆕 新功能
- **完整GUI界面** - 基于PyQt6的现代界面，设计直观
- **多语言支持** - 英文和中文界面，自动检测系统语言
- **软件包管理** - 内置软件包浏览器和仓库管理
- **交互式终端** - 真正的终端体验，支持命令执行
- **智能工具检测** - 在多个系统路径中自动查找dpkg-deb
- **独立macOS应用** - 包含所有Python依赖的自包含构建版本（约31MB）

#### 🔐 安全特性
- **路径验证** - 防止路径遍历攻击
- **文件大小限制** - 最大500MB，防止资源耗尽
- **安全文件操作** - 使用适当权限的原子操作
- **安全配置** - 安全权限管理（0600）

#### 🎨 用户体验
- **多主题** - 暗色模式、亮色模式和彩色主题
- **拖放支持** - 简单地将文件/文件夹拖到应用程序
- **命令行界面** - 执行自定义dpkg命令
- **批处理操作** - 用于自动化的命令行模式
- **状态持久化** - 记住窗口大小和设置

---

## 📋 系统要求

### macOS
- macOS 10.13 或更高版本
- Python 3.8+（用于源码构建）
- Homebrew（用于安装dpkg）

### Linux
- Ubuntu 18.04+ 或同等版本
- Python 3.8+（用于源码构建）
- 已安装dpkg软件包

### 依赖项
- PyQt6（GUI框架）
- Pillow（图像处理）
- dpkg-deb（.deb操作必需）

---

## 📦 安装

### macOS

#### 选项1：独立应用（推荐）
1. 从发布页面下载 `SimpleTweakEditor.app`
2. 将SimpleTweakEditor.app拖到应用程序文件夹
3. 首次启动：右键点击并选择"打开"
4. 安装dpkg：`brew install dpkg`

#### 选项2：源码包
```bash
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Linux

#### 选项1：AppImage
1. 下载 `SimpleTweakEditor-x86_64.AppImage`
2. 添加执行权限：`chmod +x SimpleTweakEditor-*.AppImage`
3. 运行：`./SimpleTweakEditor-*.AppImage`

#### 选项2：源码构建
```bash
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor
pip3 install -r requirements.txt
python3 main.py
```

---

## 🚀 快速开始

1. **启动应用程序**
   - 双击应用图标或从终端运行

2. **解包.deb文件**
   - 将.deb文件拖放到应用程序上
   - 或使用 文件 → 解包.deb软件包

3. **编辑软件包**
   - 导航到解包的文件夹
   - 根据需要编辑文件
   - 使用内置的control文件编辑器

4. **重新打包文件夹**
   - 将修改后的文件夹拖回应用程序
   - 或使用 文件 → 重新打包文件夹
   - 选择输出位置和文件名

---

## 🐛 已知问题

### v1.0.1
- 终端功能需要主机系统的适当PTY支持
- 出于安全考虑，拒绝大型.deb文件（>500MB）

### v1.0.0（已在v1.0.1中修复）
- ~~语言切换可能导致应用程序崩溃~~
- ~~UI组件在某些窗口大小下可能重叠~~
- ~~macOS上的字体兼容性问题~~

---

## 📁 文档

有关功能和使用的详细信息：
- [快速开始指南](docs/QUICK_START.md)
- [项目结构](docs/PROJECT_STRUCTURE.md)
- [功能路线图](docs/FEATURE_ROADMAP.md)
- [仓库管理指南](docs/REPO_MANAGER_GUIDE.md)
- [主题文档](docs/THEMES.md)

---

## 🔒 安全说明

此工具实现了多项安全措施：
- 路径遍历保护
- 文件大小限制（最大500MB）
- 安全文件权限（配置文件0600）
- 无需网络访问
- 安全的临时文件操作

---

## 📝 许可证

SimpleTweakEditor采用Apache License 2.0发布

---

## 🙏 致谢

- PyQt6开发团队
- dpkg维护者
- 所有beta测试者和贡献者

---

## 📞 支持

- **GitHub Issues**: https://github.com/Evil0ctal/SimpleTweakEditor/issues
- **文档**: https://github.com/Evil0ctal/SimpleTweakEditor/wiki

---

## 👨‍💻 作者

**Evil0ctal**
- GitHub: https://github.com/Evil0ctal
- 项目主页: https://github.com/Evil0ctal/SimpleTweakEditor

---

<div align="center">

**感谢使用SimpleTweakEditor！**

⭐ 如果您觉得这个项目有帮助，请在GitHub上给它一个星星！

**注意**：本工具仅用于合法的iOS开发和调试目的。请遵守相关法律法规。

Made with ❤️ by [Evil0ctal](https://github.com/Evil0ctal)

</div>