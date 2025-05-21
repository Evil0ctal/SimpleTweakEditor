import os
import sys
import shutil
import subprocess
import platform
import threading
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QAction, QTextCursor, QColor, QPalette
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QGroupBox, QFileDialog, QMessageBox,
    QSplitter, QStatusBar, QDialog,
    QDialogButtonBox, QPlainTextEdit
)

# 定义自定义事件类型的基础ID
_CUSTOM_EVENT_TYPE = QEvent.Type(QEvent.Type.User.value + 1)


class _LogEvent(QEvent):
    """日志事件"""

    def __init__(self, message, tag=None):
        super().__init__(_CUSTOM_EVENT_TYPE)
        self.message = message
        self.tag = tag


class _UnpackResultEvent(QEvent):
    """解包结果事件"""

    def __init__(self, success, message, target_dir):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 1))
        self.success = success
        self.message = message
        self.target_dir = target_dir


class _PackResultEvent(QEvent):
    """打包结果事件"""

    def __init__(self, success, message, out_path):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 2))
        self.success = success
        self.message = message
        self.out_path = out_path


class _ThreadExceptionEvent(QEvent):
    """线程异常事件"""

    def __init__(self, error_msg, operation_type):
        super().__init__(QEvent.Type(_CUSTOM_EVENT_TYPE.value + 3))
        self.error_msg = error_msg
        self.operation_type = operation_type


class CommandThread(QThread):
    """
    执行命令的后台线程
    """
    output_received = pyqtSignal(str, str)  # 信号: (文本, 标签)
    command_finished = pyqtSignal(int)  # 信号: 返回码

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                shell=True if isinstance(self.command, str) else False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 读取输出
            for line in process.stdout:
                self.output_received.emit(line, "normal")

            # 读取错误
            for line in process.stderr:
                self.output_received.emit(line, "error")

            # 等待进程完成
            return_code = process.wait()
            self.command_finished.emit(return_code)
        except Exception as e:
            self.output_received.emit(f"执行命令时出错: {e}", "error")
            self.command_finished.emit(1)


class ControlEditorDialog(QDialog):
    """
    DEBIAN/control文件编辑器对话框
    """

    def __init__(self, parent=None, control_content="", control_path=""):
        super().__init__(parent)
        self.control_path = control_path
        self.control_content = control_content
        self.setupUI()

    def setupUI(self):
        self.setWindowTitle("编辑Control文件")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 提示标签
        info_label = QLabel("检查或编辑DEBIAN/control元数据:")
        layout.addWidget(info_label)

        # 文本编辑器
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(self.control_content)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(' ') * 4)
        layout.addWidget(self.editor)

        # 底部提示标签
        tip_label = QLabel(
            "提示: 确保所有字段格式正确，每个字段以换行符结束。包必须至少包含Package、Version、Architecture和Description字段。")
        tip_label.setStyleSheet("color: gray;")
        layout.addWidget(tip_label)

        # 检查按钮
        validate_btn = QPushButton("检查Control文件格式")
        validate_btn.clicked.connect(self.validate_control)
        layout.addWidget(validate_btn)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def validate_control(self):
        """检查control文件格式"""
        content = self.editor.toPlainText()

        # 检查必填字段
        required_fields = ["Package", "Version", "Architecture", "Description"]
        missing_fields = []

        for field in required_fields:
            if not any(line.startswith(f"{field}:") for line in content.splitlines()):
                missing_fields.append(field)

        if missing_fields:
            QMessageBox.warning(
                self,
                "Control文件格式错误",
                f"缺少必填字段: {', '.join(missing_fields)}\n\n"
                f"一个有效的control文件必须至少包含以下字段:\n"
                f"Package: 软件包名称\n"
                f"Version: 版本号\n"
                f"Architecture: 架构（如iphoneos-arm64）\n"
                f"Description: 软件包描述"
            )
            return False

        # 检查字段格式
        for line in content.splitlines():
            if line and not line.startswith(" ") and ":" not in line:
                QMessageBox.warning(
                    self,
                    "Control文件格式错误",
                    f"字段格式不正确: '{line}'\n\n"
                    f"字段应该采用 'Field: Value' 格式，或者是多行字段的延续行（以空格开头）。"
                )
                return False

        QMessageBox.information(
            self,
            "Control文件格式正确",
            "Control文件格式验证通过！"
        )
        return True

    def getContent(self):
        content = self.editor.toPlainText()
        # 确保以换行符结束
        if not content.endswith("\n"):
            content += "\n"
        return content


class DebPackageGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iOS .deb Tweak编辑器")
        self.resize(800, 600)
        self.setMinimumSize(600, 500)
        self.setAcceptDrops(True)

        # 应用程序路径
        self.app_dir = os.getcwd()

        # 存储上次访问的目录路径
        self.last_deb_dir = self.app_dir
        self.last_output_dir = self.app_dir
        self.last_folder_dir = self.app_dir
        self.last_save_dir = self.app_dir

        # 初始化状态标志
        self.is_operation_running = False  # 操作运行状态标志

        # 调试设置
        self.debug_mode = True  # 默认开启调试模式

        # 创建UI
        self.setupUI()

        # 添加全局样式表，处理亮色/暗色模式
        self.updateGlobalStyle()

        # 打印调试信息
        self.debug_print("应用程序初始化完成")

        # 延迟加载欢迎消息（确保UI先加载完成）
        QTimer.singleShot(100, self.log_welcome_message)

    def debug_print(self, message):
        """根据调试模式输出调试信息"""
        if self.debug_mode:
            print(f"DEBUG: {message}")

    def toggle_debug_mode(self):
        """切换调试模式"""
        self.debug_mode = not self.debug_mode
        self.debug_print(f"调试模式已{'开启' if self.debug_mode else '关闭'}")
        self.log(f"调试模式已{'开启' if self.debug_mode else '关闭'}", "info")

    def start_operation(self):
        """标记操作开始"""
        self.is_operation_running = True
        self.debug_print("操作开始")

    def end_operation(self):
        """标记操作结束并清理资源"""
        self.is_operation_running = False
        self.debug_print("操作结束")

    def on_progress_canceled(self):
        """用户取消了进度对话框"""
        self.debug_print("用户取消了进度操作")
        self.end_operation()

    def setupUI(self):
        """创建用户界面"""
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 设置菜单栏
        self.createMenus()

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 顶部信息区域
        info_label = QLabel("提示: 将.deb文件拖放到窗口可直接解包，将文件夹拖放可直接打包。")
        info_label.setProperty("infoLabel", True)  # 使用属性选择器
        main_layout.addWidget(info_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.unpack_btn = QPushButton("解包 .deb 文件")
        self.unpack_btn.clicked.connect(self.unpack_deb)
        self.unpack_btn.setIcon(QIcon.fromTheme("package"))
        self.unpack_btn.setMinimumWidth(150)
        button_layout.addWidget(self.unpack_btn)

        self.repack_btn = QPushButton("重新打包文件夹")
        self.repack_btn.clicked.connect(self.repack_folder)
        self.repack_btn.setIcon(QIcon.fromTheme("package"))
        self.repack_btn.setMinimumWidth(150)
        button_layout.addWidget(self.repack_btn)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # 拖放区域
        drop_group = QGroupBox("拖放区域")
        drop_layout = QVBoxLayout(drop_group)

        self.drop_label = QLabel("将.deb文件或包含DEBIAN目录的文件夹拖放到此处")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setProperty("dropZone", True)  # 使用属性选择器而不是直接设置样式
        self.drop_label.setMinimumHeight(100)
        drop_layout.addWidget(self.drop_label)

        # 设置拖放区域样式
        self.updateDropZoneStyle(False)

        main_layout.addWidget(drop_group)

        # 分隔线
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)

        log_toolbar = QHBoxLayout()
        log_toolbar.addStretch()

        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_toolbar.addWidget(clear_log_btn)

        log_layout.addLayout(log_toolbar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)  # 限制最大行数
        log_layout.addWidget(self.log_text)

        splitter.addWidget(log_group)

        # 命令行区域
        cmd_group = QGroupBox("命令行")
        cmd_layout = QHBoxLayout(cmd_group)

        self.cmd_entry = QLineEdit()
        self.cmd_entry.returnPressed.connect(self.execute_command)
        cmd_layout.addWidget(self.cmd_entry)

        cmd_btn = QPushButton("执行")
        cmd_btn.clicked.connect(self.execute_command)
        cmd_layout.addWidget(cmd_btn)

        splitter.addWidget(cmd_group)

        # 设置分隔线的默认大小
        splitter.setSizes([400, 100])

        main_layout.addWidget(splitter)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def createMenus(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        # 解包选项
        unpack_action = QAction("解包 .deb 文件", self)
        unpack_action.triggered.connect(self.unpack_deb)
        file_menu.addAction(unpack_action)

        # 打包选项
        repack_action = QAction("重新打包文件夹", self)
        repack_action.triggered.connect(self.repack_folder)
        file_menu.addAction(repack_action)

        file_menu.addSeparator()

        # 退出选项
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")

        # 调试模式切换
        debug_action = QAction("调试模式", self)
        debug_action.setCheckable(True)
        debug_action.setChecked(self.debug_mode)
        debug_action.triggered.connect(self.toggle_debug_mode)
        settings_menu.addAction(debug_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        # 关于选项
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def updateDropZoneStyle(self, active=False):
        """更新拖放区域样式，适配亮色/暗色模式"""
        palette = self.palette()
        is_dark_mode = palette.color(QPalette.ColorRole.Window).lightness() < 128

        if active:
            # 激活状态 - 被拖拽悬停
            if is_dark_mode:
                # 暗色模式下的高亮颜色
                self.drop_label.setStyleSheet("""
                    background-color: #1a5276;
                    border: 2px dashed #3498db;
                    border-radius: 5px;
                    padding: 20px;
                    font-size: 14px;
                    color: #ffffff;
                """)
            else:
                # 亮色模式下的高亮颜色
                self.drop_label.setStyleSheet("""
                    background-color: #d6eaf8;
                    border: 2px dashed #3498db;
                    border-radius: 5px;
                    padding: 20px;
                    font-size: 14px;
                """)
        else:
            # 普通状态
            if is_dark_mode:
                # 暗色模式下的普通颜色
                self.drop_label.setStyleSheet("""
                    background-color: #2c3e50;
                    border: 2px dashed #7f8c8d;
                    border-radius: 5px;
                    padding: 20px;
                    font-size: 14px;
                    color: #ecf0f1;
                """)
            else:
                # 亮色模式下的普通颜色
                self.drop_label.setStyleSheet("""
                    background-color: #f0f0f0;
                    border: 2px dashed #aaaaaa;
                    border-radius: 5px;
                    padding: 20px;
                    font-size: 14px;
                """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """当用户拖拽文件到窗口时触发"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.updateDropZoneStyle(True)  # 激活状态

    def dragLeaveEvent(self, event):
        """当用户拖拽离开窗口时触发"""
        self.updateDropZoneStyle(False)  # 返回普通状态

    def dropEvent(self, event: QDropEvent):
        """当用户放下拖拽的文件时触发"""
        # 重置拖放区域样式
        self.updateDropZoneStyle(False)  # 返回普通状态

        # 处理拖放的文件
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    self.process_dropped_item(file_path)

            event.acceptProposedAction()

    def process_dropped_item(self, path):
        """处理拖放的文件或文件夹"""
        self.status_bar.showMessage(f"处理: {path}")
        self.log(f"接收到拖放项目: {path}", "info")

        if os.path.isfile(path) and path.lower().endswith('.deb'):
            self.process_deb_file(path)
        elif os.path.isdir(path):
            if os.path.isdir(os.path.join(path, "DEBIAN")):
                self.process_folder(path)
            else:
                self.log(f"拖放的文件夹不是有效的deb包结构（缺少DEBIAN目录）: {path}", "error")
                QMessageBox.critical(self, "无效文件夹", "所选文件夹不是有效的deb包结构（缺少DEBIAN目录）")
        else:
            self.log(f"不支持的文件类型: {path}", "error")
            QMessageBox.warning(self, "不支持的文件", "请拖放.deb文件或包含DEBIAN目录的文件夹")

    def process_deb_file(self, deb_path):
        """处理.deb文件 - 提示解包"""
        self.log(f"准备解包: {deb_path}", "info")

        # 更新上次访问的目录
        self.last_deb_dir = os.path.dirname(deb_path)

        # 获取.deb文件名（不含扩展名）和自动生成的输出目录
        deb_name = os.path.splitext(os.path.basename(deb_path))[0]
        auto_output_dir = os.path.join(self.last_output_dir, deb_name)

        # 询问用户解包选项
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("解包确认")
        msg_box.setText(f"是否解包文件: {os.path.basename(deb_path)}?")
        msg_box.setInformativeText(f"选择解包选项:")

        # 添加按钮
        auto_btn = msg_box.addButton("自动解包", QMessageBox.ButtonRole.AcceptRole)
        manual_btn = msg_box.addButton("手动选择目录", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.ButtonRole.RejectRole)

        # 设置默认按钮
        msg_box.setDefaultButton(auto_btn)

        # 显示对话框
        msg_box.exec()

        # 处理选择结果
        if msg_box.clickedButton() == auto_btn:
            # 自动解包 - 使用默认输出目录
            self.log(f"使用自动生成的输出目录: {auto_output_dir}", "info")
            self.last_output_dir = os.path.dirname(auto_output_dir)
            self.unpack_deb_file(deb_path, self.last_output_dir)
        elif msg_box.clickedButton() == manual_btn:
            # 手动选择输出目录
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "选择解包输出目录",
                self.last_output_dir
            )

            if output_dir:
                self.last_output_dir = output_dir
                self.unpack_deb_file(deb_path, output_dir)

    def process_folder(self, folder_path):
        """处理文件夹 - 提示打包"""
        self.log(f"准备打包文件夹: {folder_path}", "info")

        # 更新上次访问的文件夹目录
        self.last_folder_dir = folder_path

        # 询问用户是否打包
        result = QMessageBox.question(
            self,
            "打包确认",
            f"是否将文件夹打包为.deb?\n{folder_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            self.start_repack_process(folder_path)

    def log(self, message, tag=None):
        """添加消息到日志文本区域"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = self.log_text.currentCharFormat()
        palette = self.palette()
        is_dark_mode = palette.color(QPalette.ColorRole.Window).lightness() < 128

        if tag == "error":
            format.setForeground(QColor(255, 0, 0))  # 红色在亮/暗模式下都明显
        elif tag == "success":
            format.setForeground(QColor(0, 200, 0) if is_dark_mode else QColor(0, 128, 0))  # 绿色
        elif tag == "info":
            format.setForeground(QColor(0, 191, 255) if is_dark_mode else QColor(0, 0, 255))  # 蓝色
        else:
            # 使用默认文本颜色
            format.setForeground(palette.color(QPalette.ColorRole.Text))

        self.log_text.setTextCursor(cursor)
        self.log_text.setCurrentCharFormat(format)
        self.log_text.insertPlainText(message + "\n")

        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

        # 同时更新状态栏
        self.status_bar.showMessage(message)

    def clear_log(self):
        """清除日志内容"""
        self.log_text.clear()
        self.log("日志已清除", "info")

    def execute_command(self):
        """执行命令行输入的命令"""
        command = self.cmd_entry.text()
        if not command:
            return

        self.log(f"执行命令: {command}", "info")
        self.cmd_entry.clear()

        self.command_thread = CommandThread(command)
        self.command_thread.output_received.connect(self.handle_command_output)
        self.command_thread.command_finished.connect(self.handle_command_finished)
        self.command_thread.start()

    def handle_command_output(self, text, tag):
        """处理命令输出"""
        self.log(text.rstrip(), "error" if tag == "error" else None)

    def handle_command_finished(self, return_code):
        """处理命令执行完成"""
        if return_code == 0:
            self.log("命令执行完成", "success")
        else:
            self.log(f"命令返回错误代码: {return_code}", "error")

    def unpack_deb(self):
        """通过按钮触发解包操作"""
        deb_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要解包的.deb文件",
            self.last_deb_dir,
            "Debian包 (*.deb);;所有文件 (*.*)"
        )

        if not deb_path:
            return

        self.last_deb_dir = os.path.dirname(deb_path)

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "选择解包输出目录",
            self.last_output_dir
        )

        if not output_dir:
            return

        self.last_output_dir = output_dir
        self.unpack_deb_file(deb_path, output_dir)

    def unpack_deb_file(self, deb_path, output_dir):
        """执行.deb文件解包过程"""
        # 如果已经有操作在运行，则不执行新操作
        if self.is_operation_running:
            self.log("有操作正在进行中，请稍后再试。", "error")
            return

        # 标记操作开始
        self.start_operation()

        # 准备目标目录（以.deb文件命名的文件夹）
        deb_name = os.path.splitext(os.path.basename(deb_path))[0]
        target_dir = os.path.join(output_dir, deb_name)

        if os.path.isdir(target_dir):
            # 询问确认是否覆盖现有文件夹
            result = QMessageBox.question(
                self,
                "覆盖目录",
                f"目录 '{target_dir}' 已存在。\n是否删除其内容并重新解包?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.No:
                self.log(f"解包取消: 目录 '{target_dir}' 已存在。", "info")
                self.end_operation()
                return

            # 删除现有目录
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法删除现有目录:\n{e}")
                self.log(f"错误: 无法删除目录 '{target_dir}': {e}", "error")
                self.end_operation()
                return

        os.makedirs(target_dir, exist_ok=True)

        # 运行dpkg-deb命令解包
        self.log(f"正在解包 '{os.path.basename(deb_path)}' 到文件夹: {target_dir}", "info")
        self.status_bar.showMessage(f"正在解包 '{os.path.basename(deb_path)}'...")

        try:
            # 执行解包命令
            def unpack_thread():
                try:
                    self.debug_print("开始解包处理")

                    # 提取文件系统内容
                    self.debug_print("运行dpkg-deb -x命令")
                    result1 = subprocess.run(
                        ["dpkg-deb", "-x", deb_path, target_dir],
                        capture_output=True, text=True
                    )

                    # 提取control文件到DEBIAN/
                    self.debug_print("运行dpkg-deb -e命令")
                    debian_dir = os.path.join(target_dir, "DEBIAN")
                    os.makedirs(debian_dir, exist_ok=True)
                    result2 = subprocess.run(
                        ["dpkg-deb", "-e", deb_path, debian_dir],
                        capture_output=True, text=True
                    )

                    # 设置DEBIAN目录权限
                    try:
                        os.chmod(debian_dir, 0o755)

                        # 设置control文件权限
                        control_path = os.path.join(debian_dir, "control")
                        if os.path.exists(control_path):
                            os.chmod(control_path, 0o644)

                        # 设置脚本文件权限
                        executable_scripts = ["postinst", "prerm", "postrm", "preinst"]
                        for script in executable_scripts:
                            script_path = os.path.join(debian_dir, script)
                            if os.path.exists(script_path):
                                os.chmod(script_path, 0o755)
                    except Exception as e:
                        self.debug_print(f"设置权限时出错: {e}")

                    # 检查解包过程中的错误
                    if result1.returncode != 0 or result2.returncode != 0:
                        error_msg = ""
                        if result1.stdout: error_msg += result1.stdout.strip() + "\n"
                        if result1.stderr: error_msg += result1.stderr.strip() + "\n"
                        if result2.stdout: error_msg += result2.stdout.strip() + "\n"
                        if result2.stderr: error_msg += result2.stderr.strip() + "\n"

                        return False, error_msg

                    # 记录dpkg-deb的输出或警告
                    output_msg = ""
                    if result1.stdout: output_msg += result1.stdout.strip() + "\n"
                    if result1.stderr: output_msg += result1.stderr.strip() + "\n"
                    if result2.stdout: output_msg += result2.stdout.strip() + "\n"
                    if result2.stderr: output_msg += result2.stderr.strip() + "\n"

                    return True, output_msg

                except FileNotFoundError:
                    return False, "未安装'dpkg-deb'工具或其不在PATH中。\n请安装dpkg以使用此功能。"
                except Exception as e:
                    return False, f"解包过程中出错: {str(e)}"

            # 创建线程执行解包
            self.debug_print("启动解包后台线程")
            thread = threading.Thread(target=lambda: self._unpack_thread_worker(unpack_thread, target_dir))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.end_operation()
            QMessageBox.critical(self, "错误", f"启动解包过程时出错:\n{e}")
            self.log(f"错误: 无法启动解包过程: {e}", "error")

    def _unpack_thread_worker(self, unpack_func, target_dir):
        """解包线程工作函数"""
        try:
            # 在日志中显示进度 - 使用更直接的方式同步更新日志
            self.log_from_thread("正在解包文件...", "info")

            # 执行解包
            self.debug_print("正在调用解包函数...")
            success, message = unpack_func()
            self.debug_print(f"解包函数返回结果: 成功={success}, 信息长度={len(message) if message else 0}")

            # 直接在主线程中处理结果，不使用QTimer
            self.handle_thread_result(success, message, target_dir, "unpack")
        except Exception as e:
            # 确保在出现异常时也能结束操作
            error_msg = str(e)
            self.debug_print(f"解包线程异常: {error_msg}")
            self.handle_thread_exception(error_msg, "unpack")

    def log_from_thread(self, message, tag=None):
        """从线程中安全地更新日志"""
        # 使用invokeMethod方式在主线程中更新UI
        QApplication.instance().postEvent(self, _LogEvent(message, tag))

    def handle_thread_result(self, success, message, path, operation_type):
        """处理线程操作结果 - 从线程中调用"""
        # 使用线程安全的方式调用主线程处理函数
        if operation_type == "unpack":
            QApplication.instance().postEvent(self, _UnpackResultEvent(success, message, path))
        elif operation_type == "pack":
            QApplication.instance().postEvent(self, _PackResultEvent(success, message, path))

    def handle_thread_exception(self, error_msg, operation_type):
        """处理线程异常 - 从线程中调用"""
        # 使用线程安全的方式调用主线程处理函数
        QApplication.instance().postEvent(self, _ThreadExceptionEvent(error_msg, operation_type))

    def event(self, event):
        """处理自定义事件"""
        if isinstance(event, _LogEvent):
            self.log(event.message, event.tag)
            return True
        elif isinstance(event, _UnpackResultEvent):
            self._handle_unpack_result(event.success, event.message, event.target_dir)
            return True
        elif isinstance(event, _PackResultEvent):
            self._handle_pack_result(event.success, event.message, event.out_path)
            return True
        elif isinstance(event, _ThreadExceptionEvent):
            if event.operation_type == "unpack":
                self._handle_unpack_exception(event.error_msg)
            elif event.operation_type == "pack":
                self._handle_pack_exception(event.error_msg)
            return True
        return super().event(event)

    def _handle_unpack_result(self, success, message, target_dir):
        """处理解包结果"""
        self.debug_print(f"_handle_unpack_result被调用: 成功={success}, 目标={target_dir}")

        # 结束操作状态
        self.end_operation()

        if success:
            if message:
                self.log(message)
            success_msg = f"成功解包到: {target_dir}"
            self.log(success_msg, "success")
            self.status_bar.showMessage("解包完成")

            # 显示成功消息框
            result = QMessageBox.question(
                self,
                "解包完成",
                f"成功解包到:\n{target_dir}\n\n是否打开解包后的文件夹?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                self.open_folder(target_dir)
        else:
            self.log(f"错误: 解包失败", "error")
            if message:
                self.log(message, "error")
            self.status_bar.showMessage("解包失败")

            # 显示错误消息
            QMessageBox.critical(self, "解包失败", f"无法解包。详细信息:\n{message}")

    def _handle_unpack_exception(self, error_msg):
        """处理解包过程中的异常"""
        self.debug_print(f"_handle_unpack_exception被调用: {error_msg}")
        self.end_operation()
        self.log(f"解包过程中出现异常: {error_msg}", "error")
        self.status_bar.showMessage("解包出错")
        QMessageBox.critical(self, "解包错误", f"解包过程中出现异常:\n{error_msg}")

    def open_folder(self, path):
        """打开文件夹在文件管理器中"""
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
        except Exception as e:
            self.log(f"无法打开文件夹: {e}", "error")

    def repack_folder(self):
        """通过按钮触发重新打包操作"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择要重新打包的文件夹(必须包含DEBIAN/control)",
            self.last_folder_dir
        )

        if not folder_path:
            return

        # 更新上次访问的文件夹目录
        self.last_folder_dir = folder_path
        self.start_repack_process(folder_path)

    def start_repack_process(self, folder_path):
        """开始重新打包过程"""
        # 如果已经有操作在运行，则不执行新操作
        if self.is_operation_running:
            self.log("有操作正在进行中，请稍后再试。", "error")
            return

        control_path = os.path.join(folder_path, "DEBIAN", "control")
        if not os.path.isfile(control_path):
            QMessageBox.critical(
                self,
                "无效文件夹",
                "所选文件夹不是有效的软件包目录(缺少DEBIAN/control)。"
            )
            self.log(f"重新打包取消: '{folder_path}' 没有DEBIAN/control文件。", "error")
            return

        # 读取control文件内容
        try:
            with open(control_path, "r") as cf:
                control_content = cf.read()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取control文件:\n{e}")
            self.log(f"错误: 无法读取 '{control_path}': {e}", "error")
            return

        # 询问用户输出.deb文件路径
        folder_basename = os.path.basename(folder_path.rstrip("/\\")) or "package"

        # 智能文件命名，避免.deb.deb情况
        if folder_basename.lower().endswith(".deb"):
            default_name = folder_basename[:-4] + "-repack.deb"
        else:
            default_name = folder_basename + ".deb"

        # 打开control编辑器
        dialog = ControlEditorDialog(self, control_content, control_path)
        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            self.log("用户取消重新打包。", "info")
            return

        # 获取并保存编辑后的control内容
        new_content = dialog.getContent()
        try:
            with open(control_path, "w") as cf:
                cf.write(new_content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法写入control文件:\n{e}")
            self.log(f"错误: 无法写入 '{control_path}': {e}", "error")
            return

        # 询问保存位置
        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "将重新打包的.deb保存为",
            os.path.join(self.last_save_dir, default_name),
            "Debian包 (*.deb);;所有文件 (*.*)"
        )

        if not out_path:
            self.log("用户取消了保存路径选择，重新打包已终止。", "info")
            return

        # 标记操作开始
        self.start_operation()

        # 更新上次保存目录
        self.last_save_dir = os.path.dirname(out_path)

        # 设置DEBIAN文件权限
        self.log("正在设置DEBIAN目录中的文件权限...", "info")
        debian_dir = os.path.join(folder_path, "DEBIAN")
        executable_scripts = ["postinst", "prerm", "postrm", "preinst"]

        try:
            # 设置DEBIAN目录权限
            os.chmod(debian_dir, 0o755)
            self.log(f"为DEBIAN目录设置755权限")

            for script_name in os.listdir(debian_dir):
                script_path = os.path.join(debian_dir, script_name)
                if os.path.isfile(script_path):
                    if script_name in executable_scripts:
                        os.chmod(script_path, 0o755)
                        self.log(f"为 {script_name} 设置755权限")
                    else:
                        os.chmod(script_path, 0o644)
                        self.log(f"为 {script_name} 设置644权限")
        except Exception as e:
            self.log(f"设置文件权限时出错: {e}", "error")
            QMessageBox.warning(
                self,
                "权限警告",
                f"设置某些文件权限时出错，这可能会影响打包结果。"
            )

        # 运行dpkg-deb构建软件包
        self.log(f"正在将文件夹 '{folder_path}' 打包为 '{os.path.basename(out_path)}'...", "info")
        self.status_bar.showMessage(f"正在打包 '{os.path.basename(out_path)}'...")

        try:
            # 使用更通用的打包命令，添加--root-owner-group参数解决所有权警告
            build_cmd = ["dpkg-deb", "--root-owner-group", "-b", folder_path, out_path]
            self.log(f"执行命令: {' '.join(build_cmd)}")

            # 在后台线程中执行打包
            def pack_thread():
                try:
                    self.debug_print("开始打包处理")
                    result = subprocess.run(build_cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        error_msg = ""
                        if result.stdout: error_msg += result.stdout.strip() + "\n"
                        if result.stderr: error_msg += result.stderr.strip() + "\n"
                        return False, error_msg

                    # 记录任何输出或警告
                    output_msg = ""
                    if result.stdout: output_msg += result.stdout.strip() + "\n"
                    if result.stderr: output_msg += result.stderr.strip() + "\n"

                    return True, output_msg

                except FileNotFoundError:
                    return False, "未安装'dpkg-deb'工具或其不在PATH中。\n请安装dpkg以使用此功能。"
                except Exception as e:
                    return False, f"打包过程中出错: {str(e)}"

            # 创建线程执行打包
            self.debug_print("启动打包后台线程")
            thread = threading.Thread(target=lambda: self._pack_thread_worker(pack_thread, out_path))
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.end_operation()
            QMessageBox.critical(self, "错误", f"启动打包过程时出错:\n{e}")
            self.log(f"错误: 无法启动打包过程: {e}", "error")

    def _pack_thread_worker(self, pack_func, out_path):
        """打包线程工作函数"""
        try:
            # 在日志中显示进度 - 使用更直接的方式同步更新日志
            self.log_from_thread("正在打包文件...", "info")

            # 执行打包
            self.debug_print("正在调用打包函数...")
            success, message = pack_func()
            self.debug_print(f"打包函数返回结果: 成功={success}, 信息长度={len(message) if message else 0}")

            # 直接在主线程中处理结果，不使用QTimer
            self.handle_thread_result(success, message, out_path, "pack")
        except Exception as e:
            # 确保在出现异常时也能结束操作
            error_msg = str(e)
            self.debug_print(f"打包线程异常: {error_msg}")
            self.handle_thread_exception(error_msg, "pack")

    def _handle_pack_result(self, success, message, out_path):
        """处理打包结果"""
        self.debug_print(f"_handle_pack_result被调用: 成功={success}, 输出路径={out_path}")

        # 结束操作状态
        self.end_operation()

        if success:
            if message:
                self.log(message)
            success_msg = f"成功创建软件包: {out_path}"
            self.log(success_msg, "success")
            self.status_bar.showMessage("打包完成")

            # 显示成功消息框
            result = QMessageBox.question(
                self,
                "打包完成",
                f"成功创建.deb软件包:\n{out_path}\n\n是否打开包含该文件的文件夹?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                self.open_folder(os.path.dirname(out_path))
        else:
            self.log(f"错误: 打包失败", "error")
            if message:
                self.log(message, "error")
            self.status_bar.showMessage("打包失败")

            # 显示错误消息
            QMessageBox.critical(self, "打包失败", f"无法打包。详细信息:\n{message}")

    def _handle_pack_exception(self, error_msg):
        """处理打包过程中的异常"""
        self.debug_print(f"_handle_pack_exception被调用: {error_msg}")
        self.end_operation()
        self.log(f"打包过程中出现异常: {error_msg}", "error")
        self.status_bar.showMessage("打包出错")
        QMessageBox.critical(self, "打包错误", f"打包过程中出现异常:\n{error_msg}")

    def log_welcome_message(self):
        """显示欢迎消息和使用教程"""
        welcome_messages = [
            "欢迎使用iOS .deb Tweak编辑器! 程序已准备就绪。", "info",
            "", None,
            "=== 软件简介 ===", "info",
            "这是一个用于解包和重新打包iOS .deb文件的工具，特别适合iOS越狱插件开发者和修改者。", None,
            "", None,
            "=== 主要功能 ===", "info",
            "1. 解包.deb文件：将.deb文件解压缩到文件夹中，方便查看和修改", None,
            "2. 重新打包文件夹：将修改后的文件夹重新打包为.deb文件", None,
            "3. 支持文件拖放：直接拖放.deb文件到窗口即可开始解包", None,
            "4. 支持命令行：可以执行自定义命令", None,
            "", None,
            "=== 使用方法 ===", "info",
            "解包.deb文件:", None,
            "- 方法1: 点击\"解包.deb文件\"按钮，选择文件和输出目录", None,
            "- 方法2: 直接将.deb文件拖放到应用窗口中", None,
            "", None,
            "重新打包文件夹:", None,
            "- 方法1: 点击\"重新打包文件夹\"按钮，选择含有DEBIAN目录的文件夹", None,
            "- 方法2: 直接将含有DEBIAN目录的文件夹拖放到应用窗口中", None,
            "", None,
            "=== 版权信息 ===", "info",
            "© 2025 Evil0ctal", None,
            "项目地址: https://github.com/Evil0ctal/SimpleTweakEditor", None,
            "许可证: Apache License 2.0", None,
            "", None,
            "准备就绪！请开始操作...", "success"
        ]

        # 批量显示消息
        for i in range(0, len(welcome_messages), 2):
            message = welcome_messages[i]
            tag = welcome_messages[i + 1] if i + 1 < len(welcome_messages) else None
            self.log(message, tag)

    def updateGlobalStyle(self):
        """更新全局样式，适配亮色/暗色模式"""
        palette = self.palette()
        is_dark_mode = palette.color(QPalette.ColorRole.Window).lightness() < 128

        # 创建全局样式表
        if is_dark_mode:
            # 暗色模式下的样式
            self.setStyleSheet("""
                QLabel[infoLabel="true"] {
                    color: #3498db;
                    font-weight: bold;
                }
            """)
        else:
            # 亮色模式下的样式
            self.setStyleSheet("""
                QLabel[infoLabel="true"] {
                    color: #2980b9;
                    font-weight: bold;
                }
            """)

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
        <h3>iOS .deb Tweak编辑器</h3>
        <p>版本: 1.0.0</p>
        <p>一个用于解包和重新打包iOS .deb文件的工具。</p>
        <p>© 2025 Evil0ctal</p>
        <p>项目地址: <a href="https://github.com/Evil0ctal/SimpleTweakEditor">https://github.com/Evil0ctal/SimpleTweakEditor</a></p>
        <p>许可证: Apache License 2.0</p>
        """

        QMessageBox.about(self, "关于", about_text)


# 忽略macOS上的NSOpenPanel警告
os.environ['QT_MAC_WANTS_LAYER'] = '1'

if __name__ == "__main__":
    # 忽略macOS上的NSOpenPanel警告
    if platform.system() == "Darwin":
        # 禁用Qt调试输出
        from PyQt6.QtCore import QLoggingCategory

        QLoggingCategory.setFilterRules("*.debug=false")

    # 创建应用程序
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle("Fusion")

    # 创建并显示主窗口
    main_window = DebPackageGUI()

    # 处理通过命令行参数打开的文件
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.isfile(file_path) and file_path.lower().endswith('.deb'):
            QTimer.singleShot(500, lambda: main_window.process_deb_file(file_path))
        elif os.path.isdir(file_path):
            if os.path.isdir(os.path.join(file_path, "DEBIAN")):
                QTimer.singleShot(500, lambda: main_window.process_folder(file_path))

    main_window.show()

    # 启动应用程序事件循环
    sys.exit(app.exec())
