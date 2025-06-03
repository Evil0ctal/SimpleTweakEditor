# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
连接对话框 - 用于输入SSH连接凭据

英文介绍:
Connection dialog - For entering SSH connection credentials
"""

from typing import Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QDialogButtonBox, QGroupBox, QRadioButton,
    QSpinBox
)
from PyQt6.QtCore import Qt


class ConnectionDialog(QDialog):
    """连接对话框"""
    def __init__(self, parent=None, device_info=None, credential_store=None):
        super().__init__(parent)
        self.device_info = device_info
        self.credential_store = credential_store
        self.parent_panel = parent
        self.setup_ui()
        
        # 如果有保存的凭据，自动填充
        if device_info and credential_store:
            cred = credential_store.get_credential(device_info['identifier'])
            if cred:
                self.username_edit.setText(cred.get('username', ''))
                if cred.get('password'):
                    self.password_edit.setText(cred['password'])
                    self.save_password_check.setChecked(True)
    
    def get_text(self, key: str, *args) -> str:
        """获取本地化文本"""
        if self.parent_panel and hasattr(self.parent_panel, 'get_text'):
            return self.parent_panel.get_text(key, *args)
        return key
                    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(self.get_text("ssh_connection", "SSH Connection"))
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 设备信息
        if self.device_info:
            device_name = self.device_info.get('name', 'Unknown Device')
            info_label = QLabel(f"{self.get_text('connecting_to', 'Connecting to')}: {device_name}")
            info_label.setStyleSheet("font-weight: bold; padding: 10px;")
            layout.addWidget(info_label)
            
        # 连接类型
        if self.device_info and self.device_info.get('connection_type') == 'wifi':
            # Wi-Fi设置
            wifi_group = QGroupBox(self.get_text("wifi_settings", "Wi-Fi Settings"))
            wifi_layout = QHBoxLayout()
            
            wifi_layout.addWidget(QLabel(self.get_text("ip_address", "IP Address") + ":"))
            self.ip_edit = QLineEdit(self.device_info.get('host', ''))
            wifi_layout.addWidget(self.ip_edit)
            
            wifi_layout.addWidget(QLabel(self.get_text("port", "Port") + ":"))
            self.port_spin = QSpinBox()
            self.port_spin.setRange(1, 65535)
            self.port_spin.setValue(self.device_info.get('port', 22))
            wifi_layout.addWidget(self.port_spin)
            
            wifi_group.setLayout(wifi_layout)
            layout.addWidget(wifi_group)
        
        # 认证信息
        auth_group = QGroupBox(self.get_text("authentication", "Authentication"))
        auth_layout = QVBoxLayout()
        
        # 用户名
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel(self.get_text("username", "Username") + ":"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("mobile")
        username_layout.addWidget(self.username_edit)
        auth_layout.addLayout(username_layout)
        
        # 密码
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel(self.get_text("password", "Password") + ":"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("alpine")
        password_layout.addWidget(self.password_edit)
        auth_layout.addLayout(password_layout)
        
        # 保存密码选项
        self.save_password_check = QCheckBox(self.get_text("save_password", "Save password"))
        auth_layout.addWidget(self.save_password_check)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_connection_params(self) -> Dict:
        """获取连接参数"""
        params = {
            'username': self.username_edit.text() or 'mobile',
            'password': self.password_edit.text() or 'alpine',
            'save_password': self.save_password_check.isChecked()
        }
        
        if self.device_info:
            params['connection_type'] = self.device_info.get('connection_type', 'usb')
            if hasattr(self, 'ip_edit'):
                params['host'] = self.ip_edit.text()
                params['port'] = self.port_spin.value()
            else:
                params['host'] = 'localhost'
                params['port'] = 2222
        else:
            params['connection_type'] = 'usb'
            params['host'] = 'localhost'
            params['port'] = 2222
            
        return params