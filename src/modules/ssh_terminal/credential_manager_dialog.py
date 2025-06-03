# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
SSH凭据管理对话框 - 允许用户查看、删除和管理保存的SSH凭据

英文介绍:
SSH Credential Manager Dialog - Allows users to view, delete and manage saved SSH credentials
"""

import logging
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QMessageBox, QHeaderView, QCheckBox, QGroupBox,
    QDialogButtonBox, QToolBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction

from .credential_store import CredentialStore

logger = logging.getLogger(__name__)


class CredentialManagerDialog(QDialog):
    """SSH凭据管理对话框"""

    # 信号
    credentials_changed = pyqtSignal()

    def __init__(self, parent=None, credential_store: Optional[CredentialStore] = None):
        super().__init__(parent)
        self.parent_window = parent
        self.credential_store = credential_store or CredentialStore()

        self.setup_ui()
        self.load_credentials()

    def get_text(self, key: str, *args) -> str:
        """获取本地化文本"""
        if self.parent_window and hasattr(self.parent_window, 'lang_mgr'):
            if args:
                return self.parent_window.lang_mgr.format_text(key, *args)
            return self.parent_window.lang_mgr.get_text(key)
        return key

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.get_text("credential_manager", "Credential Manager"))
        self.setModal(True)
        self.resize(800, 500)

        layout = QVBoxLayout(self)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))

        # 刷新按钮
        refresh_action = QAction(self.get_text("refresh", "Refresh"), self)
        refresh_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_BrowserReload))
        refresh_action.triggered.connect(self.load_credentials)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 删除选中按钮
        delete_action = QAction(self.get_text("delete_selected", "Delete Selected"), self)
        delete_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_TrashIcon))
        delete_action.triggered.connect(self.delete_selected)
        toolbar.addAction(delete_action)

        # 清除所有按钮
        clear_all_action = QAction(self.get_text("clear_all_credentials", "Clear All"), self)
        clear_all_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogResetButton))
        clear_all_action.triggered.connect(self.clear_all_credentials)
        toolbar.addAction(clear_all_action)

        toolbar.addSeparator()

        # 导出按钮
        export_action = QAction(self.get_text("export", "Export"), self)
        export_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogSaveButton))
        export_action.triggered.connect(self.export_credentials)
        toolbar.addAction(export_action)

        # 导入按钮
        import_action = QAction(self.get_text("import", "Import"), self)
        import_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton))
        import_action.triggered.connect(self.import_credentials)
        toolbar.addAction(import_action)

        layout.addWidget(toolbar)

        # 信息标签
        info_text = self.get_text("credential_info",
                                  "Manage your saved SSH credentials. Passwords are securely encrypted.")
        # 添加更详细的说明
        detailed_info = "\n\n" + self.get_text("credential_info_detail",
                                               "• Credentials are stored locally in an encrypted format\n"
                                               "• System keyring provides additional security when available\n"
                                               "• Export/Import allows backup and transfer of credentials\n"
                                               "• Passwords are never stored in plain text")

        info_label = QLabel(info_text + detailed_info)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: palette(alternate-base);")
        layout.addWidget(info_label)

        # 凭据表格
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)

        # 设置列
        columns = [
            self.get_text("device_name", "Device Name"),
            self.get_text("device_id", "Device ID"),
            self.get_text("username", "Username"),
            self.get_text("connection_type", "Connection Type"),
            self.get_text("host", "Host"),
            self.get_text("port", "Port"),
            self.get_text("password_saved", "Password Saved"),
            self.get_text("last_used", "Last Used"),
            self.get_text("created_at", "Created")
        ]

        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        # 右键菜单
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        # 选项组
        options_group = QGroupBox(self.get_text("options", "Options"))
        options_layout = QVBoxLayout()
        options_layout.setSpacing(5)  # 减少间距

        # 系统密钥环选项
        keyring_layout = QHBoxLayout()
        keyring_layout.setSpacing(5)  # 设置控件间距

        self.use_keyring_check = QCheckBox(
            self.get_text("use_system_keyring",
                          "Use system keyring for new passwords (if available)"))
        self.use_keyring_check.setChecked(self.credential_store.use_keyring)
        self.use_keyring_check.toggled.connect(self.on_keyring_option_changed)
        keyring_layout.addWidget(self.use_keyring_check)

        # 添加帮助按钮
        help_btn = QPushButton()
        help_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxInformation))
        help_btn.setFixedSize(24, 24)  # 使用固定大小
        help_btn.setToolTip(self.get_text("keyring_help",
                                          "System keyring provides OS-level password encryption.\n"
                                          "When enabled, passwords are stored in:\n"
                                          "• macOS: Keychain\n"
                                          "• Windows: Credential Manager\n"
                                          "• Linux: Secret Service (GNOME Keyring, KWallet)"))
        help_btn.clicked.connect(self.show_keyring_help)
        keyring_layout.addWidget(help_btn)

        # 添加迁移按钮（如果密钥环可用且启用）
        keyring_status = self.credential_store.get_keyring_status()
        if keyring_status['available'] and keyring_status['enabled']:
            migrate_btn = QPushButton(self.get_text("migrate_to_keyring", "Migrate to Keyring"))
            migrate_btn.setToolTip(self.get_text("migrate_to_keyring_tooltip",
                                                 "Move existing passwords from encrypted files to system keyring"))
            migrate_btn.clicked.connect(self.migrate_to_keyring)
            keyring_layout.addWidget(migrate_btn)

        keyring_layout.addStretch()
        options_layout.addLayout(keyring_layout)

        # 密钥环状态信息
        status_info = self.get_keyring_status_text()
        status_label = QLabel(status_info)
        status_label.setObjectName("keyringStatusLabel")
        status_label.setStyleSheet("color: palette(mid); font-size: 12px; margin-left: 25px;")
        options_layout.addWidget(status_label)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def load_credentials(self):
        """加载凭据列表"""
        credentials = self.credential_store.get_all_credentials()

        self.table.setRowCount(len(credentials))

        for row, cred in enumerate(credentials):
            # 设备名称
            self.table.setItem(row, 0, QTableWidgetItem(cred.get('device_name', '')))

            # 设备ID
            self.table.setItem(row, 1, QTableWidgetItem(cred.get('device_id', '')))

            # 用户名
            self.table.setItem(row, 2, QTableWidgetItem(cred.get('username', '')))

            # 连接类型
            conn_type = cred.get('connection_type', 'usb').upper()
            self.table.setItem(row, 3, QTableWidgetItem(conn_type))

            # 主机
            self.table.setItem(row, 4, QTableWidgetItem(cred.get('host', '')))

            # 端口
            self.table.setItem(row, 5, QTableWidgetItem(str(cred.get('port', ''))))

            # 密码保存状态
            has_password = cred.get('has_password', False)
            in_keyring = cred.get('password_in_keyring', False)
            if has_password:
                if in_keyring:
                    status = self.get_text("in_keyring", "In Keyring")
                else:
                    status = self.get_text("encrypted", "Encrypted")
            else:
                status = self.get_text("not_saved", "Not Saved")
            self.table.setItem(row, 6, QTableWidgetItem(status))

            # 最后使用时间
            last_used = cred.get('last_used', '')
            if last_used:
                try:
                    dt = datetime.fromisoformat(last_used)
                    last_used = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    pass
            self.table.setItem(row, 7, QTableWidgetItem(last_used))

            # 创建时间
            created_at = cred.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    created_at = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    pass
            self.table.setItem(row, 8, QTableWidgetItem(created_at))

    def show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.table.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        # 删除操作
        delete_action = menu.addAction(self.get_text("delete", "Delete"))
        delete_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_TrashIcon))
        delete_action.triggered.connect(lambda: self.delete_credential(item.row()))

        menu.exec(self.table.mapToGlobal(pos))

    def delete_credential(self, row: int):
        """删除单个凭据"""
        device_id = self.table.item(row, 1).text()
        device_name = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            self.get_text("confirm_delete", "Confirm Delete"),
            self.get_text("delete_credential_msg", "Delete credential for {0}?").format(device_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.credential_store.delete_credential(device_id):
                self.load_credentials()
                self.credentials_changed.emit()
                QMessageBox.information(
                    self,
                    self.get_text("success", "Success"),
                    self.get_text("credential_deleted", "Credential deleted successfully")
                )

    def delete_selected(self):
        """删除选中的凭据"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self,
                self.get_text("no_selection", "No Selection"),
                self.get_text("select_credentials_to_delete", "Please select credentials to delete")
            )
            return

        reply = QMessageBox.question(
            self,
            self.get_text("confirm_delete", "Confirm Delete"),
            self.get_text("delete_selected_msg", "Delete {0} selected credential(s)?").format(len(selected_rows)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted = 0
            for row in sorted(selected_rows, reverse=True):
                device_id = self.table.item(row, 1).text()
                if self.credential_store.delete_credential(device_id):
                    deleted += 1

            self.load_credentials()
            self.credentials_changed.emit()

            QMessageBox.information(
                self,
                self.get_text("success", "Success"),
                self.get_text("credentials_deleted", "{0} credential(s) deleted").format(deleted)
            )

    def clear_all_credentials(self):
        """清除所有凭据"""
        reply = QMessageBox.warning(
            self,
            self.get_text("confirm_clear_all", "Confirm Clear All"),
            self.get_text("clear_all_msg",
                          "This will delete ALL saved credentials.\n\nThis action cannot be undone. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 二次确认
            reply2 = QMessageBox.critical(
                self,
                self.get_text("final_confirmation", "Final Confirmation"),
                self.get_text("final_clear_msg", "Are you absolutely sure?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply2 == QMessageBox.StandardButton.Yes:
                # 清除所有凭据
                all_credentials = self.credential_store.get_all_credentials()
                deleted = 0

                for cred in all_credentials:
                    if self.credential_store.delete_credential(cred['device_id']):
                        deleted += 1

                self.load_credentials()
                self.credentials_changed.emit()

                QMessageBox.information(
                    self,
                    self.get_text("success", "Success"),
                    self.get_text("all_credentials_cleared", "All credentials have been cleared")
                )

    def export_credentials(self):
        """导出凭据"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.get_text("export_credentials", "Export Credentials"),
            "ssh_credentials_backup.json",
            "JSON Files (*.json)"
        )

        if file_path:
            # 询问是否包含密码
            reply = QMessageBox.question(
                self,
                self.get_text("export_options", "Export Options"),
                self.get_text("include_passwords_msg",
                              "Include passwords in export?\n\n"
                              "Note: Passwords will be exported in encrypted form using AES encryption. "
                              "They can only be decrypted with the same encryption key. "
                              "For maximum security, consider not including passwords."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            include_passwords = (reply == QMessageBox.StandardButton.Yes)

            try:
                from pathlib import Path
                self.credential_store.export_credentials(Path(file_path), include_passwords)

                QMessageBox.information(
                    self,
                    self.get_text("success", "Success"),
                    self.get_text("export_success", "Credentials exported successfully")
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.get_text("error", "Error"),
                    self.get_text("export_failed", "Export failed: {0}").format(str(e))
                )

    def import_credentials(self):
        """导入凭据"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.get_text("import_credentials", "Import Credentials"),
            "",
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                from pathlib import Path
                self.credential_store.import_credentials(Path(file_path))

                self.load_credentials()
                self.credentials_changed.emit()

                QMessageBox.information(
                    self,
                    self.get_text("success", "Success"),
                    self.get_text("import_success", "Credentials imported successfully")
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.get_text("error", "Error"),
                    self.get_text("import_failed", "Import failed: {0}").format(str(e))
                )

    def on_keyring_option_changed(self, checked: bool):
        """密钥环选项变更"""
        self.credential_store.use_keyring = checked

        QMessageBox.information(
            self,
            self.get_text("info", "Information"),
            self.get_text("keyring_option_msg",
                          "This setting will apply to new credentials only.\n"
                          "Existing credentials will not be affected.")
        )

    def get_keyring_status_text(self) -> str:
        """获取密钥环状态文本"""
        keyring_status = self.credential_store.get_keyring_status()

        if not keyring_status['available']:
            return self.get_text("keyring_unavailable_detail",
                                 "System keyring is not available. Passwords will be stored in encrypted files.")

        backend = keyring_status.get('backend', 'Unknown')
        if keyring_status['enabled']:
            return self.get_text("keyring_enabled_detail",
                                 "System keyring is enabled. Using: {0}").format(backend)
        else:
            return self.get_text("keyring_disabled_detail",
                                 "System keyring is available ({0}) but disabled.").format(backend)

    def show_keyring_help(self):
        """显示密钥环帮助信息"""
        from PyQt6.QtWidgets import QMessageBox

        help_text = self.get_text(
            "keyring_help_detail",
            "System Keyring provides enhanced security for password storage:\n\n"
            "Benefits:\n"
            "• OS-level encryption and access control\n"
            "• Integration with system authentication\n"
            "• Passwords persist across application updates\n"
            "• No master password required\n\n"
            "Limitations:\n"
            "• Passwords cannot be exported directly\n"
            "• Tied to user account on this computer\n"
            "• May require additional setup on Linux\n\n"
            "When disabled, passwords are stored in encrypted files within the application directory.")

        QMessageBox.information(
            self,
            self.get_text("keyring_help_title", "About System Keyring"),
            help_text)

    def migrate_to_keyring(self):
        """迁移密码到系统密钥环"""
        reply = QMessageBox.question(
            self,
            self.get_text("confirm_migrate", "Confirm Migration"),
            self.get_text("migrate_confirm_msg",
                          "This will move all passwords from encrypted files to the system keyring.\n\n"
                          "Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count, fail_count = self.credential_store.migrate_to_keyring()

            if success_count > 0 or fail_count > 0:
                QMessageBox.information(
                    self,
                    self.get_text("migration_complete", "Migration Complete"),
                    self.get_text("migration_result",
                                  "Successfully migrated: {0}\nFailed: {1}").format(success_count, fail_count)
                )
                self.load_credentials()  # 刷新显示
            else:
                QMessageBox.information(
                    self,
                    self.get_text("info", "Information"),
                    self.get_text("no_passwords_to_migrate", "No passwords to migrate.")
                )
