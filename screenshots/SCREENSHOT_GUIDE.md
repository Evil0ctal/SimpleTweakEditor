# 截图指南 / Screenshot Guide

## 需要的截图 / Required Screenshots

### 中文界面 (存放在 screenshots/zh/)
1. **main_window_dark.png** - 主界面深色主题
   - 切换到深色主题（如 dark_blue）
   - 显示主界面，包含拖放区域和按钮
   - 确保界面是中文

2. **main_window_light.png** - 主界面浅色主题  
   - 切换到浅色主题（如 light_blue）
   - 显示主界面，包含拖放区域和按钮
   - 确保界面是中文

3. **package_manager.png** - 软件包管理器
   - 打开软件包管理器（工具 → 软件包管理器）
   - 显示软件源列表和一些软件包
   - 确保界面是中文

4. **interactive_terminal.png** - 交互式终端
   - 切换到"交互式终端"标签页
   - 执行一些命令（如 ls, pwd 等）
   - 显示终端输出
   - 确保界面是中文

5. **control_editor.png** - Control文件编辑器
   - 打开Control文件编辑器（工具 → 编辑Control文件）
   - 显示编辑器界面和一些示例内容
   - 确保界面是中文

6. **theme_menu.png** - 主题菜单
   - 打开视图 → 主题菜单
   - 显示所有可用的主题选项
   - 确保界面是中文

7. **repo_manager.png** - 仓库管理器
   - 打开工具 → 软件源管理
   - 显示软件源列表界面
   - 确保界面是中文

8. **drag_drop.png** - 拖放操作
   - 显示主界面
   - 正在拖放一个.deb文件到拖放区域
   - 显示拖放时的视觉反馈（虚线边框等）
   - 确保界面是中文

### 英文界面 (存放在 screenshots/en/)
重复上述所有截图，但需要：
- 切换语言到英文（语言 → English）
- 文件名相同，但存放在 screenshots/en/ 目录
- 确保所有界面文字都是英文

## 截图建议 / Screenshot Tips

### 尺寸建议
- 建议使用 1200x800 或类似的分辨率
- 确保文字清晰可读
- 裁剪掉不必要的系统UI（如macOS的顶部菜单栏）

### 内容建议
- 主界面可以拖入一个示例.deb文件显示状态
- 终端可以执行一些简单命令展示功能
- Control编辑器可以显示一些示例包信息

### 主题建议
- 深色主题推荐：dark_blue 或 dark_cyan
- 浅色主题推荐：light_blue 或 light_amber

## 文件命名 / File Naming
确保文件名完全匹配：
- main_window_dark.png
- main_window_light.png
- package_manager.png
- interactive_terminal.png
- control_editor.png
- theme_menu.png
- repo_manager.png
- drag_drop.png

## 截图示例命令 / Screenshot Commands

### macOS 截图
```bash
# 选择区域截图（推荐）
Command + Shift + 4

# 截取整个窗口（点击空格键后点击窗口）
Command + Shift + 4, 然后按空格键
```

### Linux 截图
```bash
# 使用 gnome-screenshot
gnome-screenshot -a  # 选择区域

# 使用 scrot
scrot -s  # 选择区域
```