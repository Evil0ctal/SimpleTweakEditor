# SimpleTweakEditor 快速启动指南

## 🚀 对于用户

### macOS 用户

#### 最简单的方式 - 使用独立版 .app （推荐）
1. 从 `releases/v1.0.0/macOS/` 下载 `SimpleTweakEditor.app` （独立版）
2. 将 SimpleTweakEditor.app 拖到 Applications 文件夹
3. 首次运行时，右键点击应用并选择"打开"
4. 这个版本已包含所有Python依赖，但仍需要安装 dpkg：
   ```bash
   brew install dpkg
   ```

#### 使用标准版 .app 包
位置：`releases/v1.0.0/SimpleTweakEditor.app` （标准版）
- 可以直接双击运行
- 需要预先安装 Python 3.8+ 和依赖：
   ```bash
   pip3 install PyQt6 Pillow
   brew install dpkg
   ```

### Linux 用户
1. 下载 `SimpleTweakEditor-1.0.0-Linux.tar.gz` 或使用源代码包
2. 解压并运行
3. 确保安装了 dpkg：
   ```bash
   sudo apt-get install dpkg
   ```

## 🛠️ 对于开发者

### 运行源代码
```bash
# 克隆或下载项目
cd SimpleTweakEditor

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

### 构建新版本
```bash
# 进入构建脚本目录
cd build_scripts

# macOS: 构建独立版 .app 包（推荐）
python3 build_macos_app_standalone.py

# macOS: 构建标准版 .app 包
python3 build_macos_app.py

# 或一键构建所有版本
./prepare_release.sh

# 清理所有构建文件
./clean_all.sh
```

## 📁 项目结构

- **源代码**：`src/` 目录包含所有Python源文件
- **主程序**：`main.py` 是程序入口
- **构建脚本**：`build_scripts/` 目录包含所有构建相关脚本
- **发布文件**：`releases/v1.0.0/` 包含所有可分发的文件

## ⚠️ 常见问题

### Q: 提示找不到 dpkg-deb
A: 应用会自动在多个路径查找dpkg-deb，如果仍然找不到，请安装 dpkg：
- macOS: `brew install dpkg`
- Linux: `sudo apt-get install dpkg`
- 应用会查找的路径包括：/usr/bin, /usr/local/bin, /opt/homebrew/bin 等

### Q: 提示找不到 PyQt6
A: 安装 Python 依赖：`pip3 install PyQt6 Pillow`

### Q: macOS 提示"无法打开...因为它来自身份不明的开发者"
A: 右键点击应用，选择"打开"，然后在弹出的对话框中再次点击"打开"

## 📞 支持

- GitHub Issues: https://github.com/Evil0ctal/SimpleTweakEditor/issues
- 项目主页: https://github.com/Evil0ctal/SimpleTweakEditor