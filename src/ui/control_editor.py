# -*- coding: utf-8 -*-
"""
Control文件编辑器模块
提供DEBIAN/control文件的编辑和验证功能
"""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QDialogButtonBox, QMessageBox
)

from src.utils.file_operations import validate_control_file


class ControlEditorDialog(QDialog):
    """
    DEBIAN/control文件编辑器对话框
    """

    def __init__(self, parent=None, control_content="", control_path=""):
        super().__init__(parent)
        self.control_path = control_path
        self.control_content = control_content

        # 获取父窗口的语言管理器
        self.lang_mgr = parent.lang_mgr if parent and hasattr(parent, 'lang_mgr') else None

        self.setupUI()

    def setupUI(self):
        """设置用户界面"""
        self.setWindowTitle(self._get_text("edit_control"))
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # 提示标签
        info_label = QLabel(self._get_text("control_check_label"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 文本编辑器
        self.editor = QPlainTextEdit()
        self.editor.setPlainText(self.control_content)

        # 设置等宽字体
        font = QFont()
        font.setFamily("Monaco, Menlo, 'DejaVu Sans Mono', monospace")
        font.setPointSize(10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)
            if not font.exactMatch():
                font = QFont("Courier New", 10)
        self.editor.setFont(font)

        # 设置制表符宽度
        font_metrics = self.editor.fontMetrics()
        tab_width = font_metrics.horizontalAdvance(' ') * 4
        self.editor.setTabStopDistance(tab_width)

        layout.addWidget(self.editor)

        # 底部提示标签
        tip_label = QLabel(self._get_text("control_tip"))
        tip_label.setProperty("class", "secondary")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)

        # 验证按钮
        self.validate_btn = QPushButton(self._get_text("check_control"))
        self.validate_btn.clicked.connect(self.validate_control)  # type: ignore
        layout.addWidget(self.validate_btn)

        # 按钮框
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )

        # 设置按钮文本
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)

        if save_button:
            save_button.setText(self._get_text("save"))
        if cancel_button:
            cancel_button.setText(self._get_text("cancel"))

        self.button_box.accepted.connect(self.accept)  # type: ignore
        self.button_box.rejected.connect(self.reject)  # type: ignore
        layout.addWidget(self.button_box)

    def apply_theme(self):
        """应用主题样式"""
        # qt-material会自动处理主题，只需要设置字体
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                font-family: Monaco, Menlo, 'DejaVu Sans Mono', monospace;
            }
        """)

    def _get_text(self, key):
        """获取本地化文本"""
        if self.lang_mgr:
            return self.lang_mgr.get_text(key)

        # 备用翻译
        fallback_texts = {
            "edit_control": "Edit Control File",
            "control_check_label": "Check or edit DEBIAN/control metadata:",
            "control_tip": "Tip: Ensure all fields are in the correct format, with each field ending with a newline. Packages must include at least Package, Version, Architecture, and Description fields.",
            "check_control": "Check Control File Format",
            "save": "Save",
            "cancel": "Cancel",
            "control_format_error": "Control File Format Error",
            "control_valid": "Control File Format Valid",
            "control_valid_msg": "Control file format validation passed!",
            "missing_required_fields": "Missing required fields: {0}\n\nA valid control file must include at least these fields:\nPackage: package name\nVersion: version number\nArchitecture: architecture (e.g., iphoneos-arm64)\nDescription: package description",
            "field_format_error": "Field format error on line {0}: '{1}'\n\nFields should be in 'Field: Value' format, or continuation lines for multi-line fields (starting with a space).",
        }
        return fallback_texts.get(key, key)

    def validate_control(self):
        """验证control文件格式"""
        content = self.editor.toPlainText()

        # 使用工具函数验证
        is_valid, errors = validate_control_file(content)

        if not is_valid:
            # 显示错误信息
            error_message = "\n".join(errors)
            QMessageBox.warning(
                self,
                self._get_text("control_format_error"),
                error_message
            )
            return False
        else:
            # 验证通过
            QMessageBox.information(
                self,
                self._get_text("control_valid"),
                self._get_text("control_valid_msg")
            )
            return True

    def getContent(self):
        """获取编辑器内容"""
        content = self.editor.toPlainText()
        # 确保以换行符结束
        if not content.endswith("\n"):
            content += "\n"
        return content

    def setContent(self, content):
        """设置编辑器内容"""
        self.editor.setPlainText(content)

    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr

        # 更新界面文本
        self.setWindowTitle(self._get_text("edit_control"))

        # 更新按钮文本
        self.validate_btn.setText(self._get_text("check_control"))

        # 更新按钮框按钮文本
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)

        if save_button:
            save_button.setText(self._get_text("save"))
        if cancel_button:
            cancel_button.setText(self._get_text("cancel"))

    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        # qt-material会自动处理主题
