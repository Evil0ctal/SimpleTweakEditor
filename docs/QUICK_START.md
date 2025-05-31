# SimpleTweakEditor 快速开始指南

*最后更新: 2025-05-30*

## 🚀 对于用户

### Windows 用户 🆕

#### 最简单的方式 - 下载即用
1. 从 [Releases](https://github.com/Evil0ctal/SimpleTweakEditor/releases) 下载最新版本
2. 下载 `SimpleTweakEditor-v1.0.2-Windows-x64.zip`
3. 解压到任意文件夹
4. 双击 `SimpleTweakEditor.exe` 运行
5. **无需安装dpkg或任何Linux工具！**

### macOS 用户

#### 最简单的方式 - 使用预构建版
1. 从 [Releases](https://github.com/Evil0ctal/SimpleTweakEditor/releases) 下载最新版本
2. Intel Mac: 下载 `SimpleTweakEditor-v1.0.2-macOS-x64.zip`
3. Apple Silicon Mac: 下载 `SimpleTweakEditor-v1.0.2-macOS-Apple-Silicon.zip`
4. 解压后将 SimpleTweakEditor.app 拖到 Applications 文件夹
5. 首次运行时，右键点击应用并选择"打开"
6. 安装 dpkg（可选，macOS上仍建议安装）：
   ```bash
   brew install dpkg
   ```

#### 从源码运行
```bash
# 克隆仓库
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

### Linux 用户

#### 使用 AppImage（推荐）
1. 下载 `SimpleTweakEditor-x86_64.AppImage`
2. 添加执行权限：
   ```bash
   chmod +x SimpleTweakEditor-x86_64.AppImage
   ```
3. 运行：
   ```bash
   ./SimpleTweakEditor-x86_64.AppImage
   ```

#### 从源码运行
```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install python3 python3-pip dpkg

# 克隆并运行
git clone https://github.com/Evil0ctal/SimpleTweakEditor.git
cd SimpleTweakEditor
pip3 install -r requirements.txt
python3 main.py
```

## 📱 基本使用

### 1. 解包 .deb 文件

#### 方法一：拖放操作
- 直接将 .deb 文件拖到主界面的拖放区域
- 自动开始解包过程

#### 方法二：使用按钮
1. 点击"解包 .deb 文件"按钮
2. 选择要解包的 .deb 文件
3. 选择输出目录
4. 等待解包完成

### 2. 编辑软件包内容

#### 编辑 Control 文件
1. 工具 → 编辑Control文件
2. 在编辑器中修改包信息
3. 保存更改

#### 浏览和修改文件
1. 使用文件管理器打开解包后的文件夹
2. 修改需要的文件
3. 确保不要删除 DEBIAN 目录

### 3. 重新打包

#### 方法一：拖放文件夹
- 将包含 DEBIAN 目录的文件夹拖到主界面

#### 方法二：使用按钮
1. 点击"重新打包文件夹"按钮
2. 选择要打包的文件夹（必须包含 DEBIAN 目录）
3. 选择输出文件名和位置
4. 等待打包完成

## 🎯 高级功能

### 软件包管理器
1. 工具 → 软件包管理器
2. 浏览和搜索软件包
3. 查看包详情和版本历史
4. 下载软件包到本地

### 仓库管理
1. 工具 → 软件源管理
2. 添加新的软件源
3. 编辑或删除现有源
4. 刷新源列表

### 交互式终端
1. 切换到"交互式终端"标签
2. 执行各种命令
3. 支持多标签页操作
4. 使用快速命令菜单

### 主题切换
1. 视图 → 主题
2. 选择喜欢的主题
3. 支持深色、浅色和彩色主题

### 语言切换
1. 语言 → 选择语言
2. 支持中文和英文
3. 自动保存语言设置

## 🔧 命令行模式

SimpleTweakEditor 也支持命令行操作：

```bash
# 查看帮助
python main.py --help

# 解包 .deb 文件
python main.py --unpack package.deb --output ./unpacked/

# 重新打包文件夹
python main.py --repack ./package_folder/ --output new_package.deb

# 批处理模式
python main.py --batch --unpack "*.deb"

# 设置语言
python main.py --lang zh  # 中文
python main.py --lang en  # English
```

## ❓ 常见问题

### Q: 提示找不到 dpkg-deb
**A:** 
- **Windows**: 无需安装！程序已内置纯Python实现
- **macOS**: `brew install dpkg`
- **Linux**: `sudo apt-get install dpkg`

### Q: 首次打开 macOS 应用提示无法验证
**A:** 右键点击应用，选择"打开"，然后在弹出的对话框中再次点击"打开"

### Q: 打包失败提示权限错误
**A:** 
- **Windows**: 程序会自动处理权限，无需手动设置
- **macOS/Linux**: 确保 DEBIAN 目录中的脚本文件有正确的执行权限：
  ```bash
  chmod 755 DEBIAN/postinst
  chmod 755 DEBIAN/prerm
  ```

### Q: 如何查看更详细的错误信息
**A:** 切换到"命令行"标签页查看详细的命令输出

## 🪟 Windows平台特色功能

### 无需依赖
- 内置纯Python dpkg实现，无需安装WSL、Cygwin或任何Linux工具
- 支持所有.deb压缩格式（gz/xz/lzma）
- 完整的AR归档格式支持

### 智能权限处理
Windows下创建的.deb包会自动设置正确的Unix权限：
- DEBIAN目录下的脚本（preinst/postinst等）自动设为755
- bin/sbin目录下的文件自动设为755
- 带有shebang（#!）的脚本自动设为755
- 普通文件设为644，目录设为755

### 路径处理
- 自动转换Windows路径分隔符
- 支持长路径名（超过260字符）
- 正确处理符号链接和特殊字符

## 🎨 提示和技巧

1. **批量操作**: 使用命令行模式可以批量处理多个文件
2. **快速访问**: 将常用的 .deb 文件拖到 Dock/任务栏旁边方便拖放
3. **备份原文件**: 修改前建议备份原始 .deb 文件
4. **测试修改**: 在测试设备上验证修改后的包是否正常工作
5. **Windows用户注意**: 在Windows上编辑文本文件时，注意使用Unix换行符（LF）而非Windows换行符（CRLF）

## 📚 更多资源

- [项目主页](https://github.com/Evil0ctal/SimpleTweakEditor)
- [问题反馈](https://github.com/Evil0ctal/SimpleTweakEditor/issues)
- [功能路线图](FEATURE_ROADMAP.md)
- [项目结构](PROJECT_STRUCTURE.md)

---

*享受使用 SimpleTweakEditor！如有问题，欢迎提交 Issue。*