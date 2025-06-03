# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-03
作者: Evil0ctal

中文介绍:
SSH终端面板 - 主题感知版本，支持亮色和暗色主题，与应用程序主题系统集成

英文介绍:
SSH Terminal Panel - Theme-aware version with light/dark theme support, integrated with app theme system
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QDialog, QMessageBox, QTabWidget,
    QListWidget, QListWidgetItem, QComboBox, QToolButton,
    QHeaderView, QFrame, QGraphicsDropShadowEffect, QToolBar,
    QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QAction

# 导入SSH实现
from .ssh_terminal_widget import SSHTerminalWidget
from .iproxy_manager import IProxyManager
from .credential_store import CredentialStore
from .device_scanner import DeviceScanner
from .connection_dialog import ConnectionDialog

logger = logging.getLogger(__name__)


class SSHTerminalPanel(QWidget):
    """SSH终端控制面板 - 主题感知版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 获取管理器
        self.lang_mgr = parent.lang_mgr if parent and hasattr(parent, 'lang_mgr') else None
        self.config_mgr = parent.config_mgr if parent and hasattr(parent, 'config_mgr') else None
        self.style_mgr = parent.style_mgr if parent and hasattr(parent, 'style_mgr') else None
        
        # 初始化组件
        self.credential_store = CredentialStore()
        self.iproxy_manager = IProxyManager()
        
        # 设备扫描器
        self.device_scanner = DeviceScanner()
        
        # 活动会话字典
        self.active_sessions = {}  # device_id -> terminal_widget
        
        # 初始化UI
        self.setup_ui()
        
        # 应用主题样式
        self.apply_theme_styles()
        
        # 连接信号
        self.setup_connections()
        
        # Debug - verify style manager
        logger.info(f"Style manager available: {self.style_mgr is not None}")
        if self.style_mgr:
            logger.info(f"Current theme: {self.style_mgr.get_theme()}")
            logger.info(f"Is dark mode: {self.style_mgr.is_dark_mode()}")
        
        # 启动设备扫描
        QTimer.singleShot(100, self.scan_devices)
    
    def get_text(self, key: str, *args) -> str:
        """获取本地化文本"""
        if self.lang_mgr:
            if args:
                return self.lang_mgr.format_text(key, *args)
            return self.lang_mgr.get_text(key)
        return key
        
    def setup_ui(self):
        """设置用户界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建工具栏
        self.create_toolbar(main_layout)
        
        # 创建主内容区域
        content_widget = QWidget()
        content_widget.setObjectName("sshContent")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_layout.addWidget(main_splitter)
        
        # 左侧面板
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # 右侧面板（终端区域）
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例
        main_splitter.setSizes([350, 650])
        main_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(content_widget)
        
        # 状态栏
        self.create_status_bar(main_layout)
        
    def create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setObjectName("sshToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        # 扫描设备
        scan_action = QAction(self.get_text('scan_devices'), self)
        scan_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        scan_action.triggered.connect(self.scan_devices)
        toolbar.addAction(scan_action)
        
        # 添加Wi-Fi设备
        add_wifi_action = QAction(self.get_text('add_wifi_device'), self)
        add_wifi_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        add_wifi_action.triggered.connect(self.add_wifi_device)
        toolbar.addAction(add_wifi_action)
        
        toolbar.addSeparator()
        
        # 快速操作
        # quick_action = QAction(self.get_text('quick_actions'), self)
        # quick_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        # toolbar.addAction(quick_action)
        #
        # toolbar.addSeparator()
        
        # 凭据管理器
        credential_action = QAction(self.get_text('credential_manager'), self)
        credential_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        credential_action.triggered.connect(self.open_credential_manager)
        toolbar.addAction(credential_action)
        
        parent_layout.addWidget(toolbar)
        
    def create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QFrame()
        panel.setObjectName("sshLeftPanel")
        panel.setFrameStyle(QFrame.Shape.Box)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 设备列表
        device_group = self.create_device_group()
        layout.addWidget(device_group)
        
        # 快速操作面板
        quick_actions = self.create_quick_actions()
        layout.addWidget(quick_actions)
        
        layout.addStretch()
        
        return panel
    
    def create_device_group(self) -> QGroupBox:
        """创建设备组"""
        device_group = QGroupBox(self.get_text('device_list'))
        device_group.setObjectName("deviceGroup")
        
        device_layout = QVBoxLayout()
        device_layout.setContentsMargins(10, 10, 10, 10)
        
        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setObjectName("deviceTree")
        self.device_tree.setHeaderLabels([self.get_text("device_name"), self.get_text("status")])
        self.device_tree.setRootIsDecorated(False)
        self.device_tree.setAlternatingRowColors(True)
        self.device_tree.itemDoubleClicked.connect(self.on_device_double_clicked)
        
        # 设置列宽
        header = self.device_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 120)
        
        # 设置右键菜单
        self.device_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.device_tree.customContextMenuRequested.connect(self.show_device_context_menu)
        
        device_layout.addWidget(self.device_tree)
        device_group.setLayout(device_layout)
        
        return device_group
    
    def create_quick_actions(self) -> QGroupBox:
        """创建快速操作组"""
        actions_group = QGroupBox(self.get_text('quick_actions'))
        actions_group.setObjectName("quickActionsGroup")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 常用命令列表
        self.quick_commands = QListWidget()
        self.quick_commands.setObjectName("quickCommandsList")
        self.quick_commands.setMaximumHeight(120)
        
        # 添加常用命令
        commands = [
            ("uname -a", self.get_text('system_info')),
            ("ls -la", self.get_text('list_files')),
            ("ps aux", self.get_text('process_list'))
        ]
        
        for cmd, desc in commands:
            item = QListWidgetItem(desc)
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            self.quick_commands.addItem(item)
            
        self.quick_commands.itemDoubleClicked.connect(self.execute_quick_command)
        
        layout.addWidget(self.quick_commands)
        actions_group.setLayout(layout)
        
        return actions_group
        
    def create_right_panel(self) -> QWidget:
        """创建右侧面板（终端区域）"""
        panel = QFrame()
        panel.setObjectName("sshRightPanel")
        panel.setFrameStyle(QFrame.Shape.Box)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 会话标签页
        self.session_tabs = QTabWidget()
        self.session_tabs.setObjectName("sessionTabs")
        self.session_tabs.setTabsClosable(True)
        self.session_tabs.tabCloseRequested.connect(self.close_session_tab)
        self.session_tabs.setDocumentMode(True)
        self.session_tabs.setMovable(True)
        
        layout.addWidget(self.session_tabs)
        
        # 添加欢迎页面
        welcome_widget = self.create_welcome_widget()
        self.session_tabs.addTab(welcome_widget, self.get_text('welcome'))
        self.session_tabs.setTabToolTip(0, self.get_text("welcome_tip"))
        
        return panel
        
    def create_welcome_widget(self) -> QWidget:
        """创建欢迎页面"""
        widget = QWidget()
        widget.setObjectName("welcomeWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建居中的容器
        center_widget = QWidget()
        center_widget.setMaximumWidth(400)
        center_widget.setObjectName("welcomeContainer")
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(20)
        
        # SSH图标和标题
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon
        ).pixmap(48, 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(icon_label)
        
        # 欢迎标题
        title_label = QLabel(self.get_text('ssh_terminal'))
        title_label.setObjectName("welcomeTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel(self.get_text('ssh_subtitle', 'Secure Shell Connection Manager'))
        subtitle_label.setObjectName("welcomeSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(subtitle_label)
        
        # 功能介绍卡片
        features_card = QWidget()
        features_card.setObjectName("featuresCard")
        features_layout = QVBoxLayout(features_card)
        features_layout.setContentsMargins(20, 15, 20, 15)
        features_layout.setSpacing(10)
        
        # 功能标题
        features_title = QLabel(self.get_text('ssh_features_title', 'Features'))
        features_title.setObjectName("featuresTitle")
        features_layout.addWidget(features_title)
        
        features = [
            ("🔍", self.get_text('auto_device_discovery')),
            ("🔒", self.get_text('secure_credential_storage')),
            ("📱", self.get_text('multi_session_support')),
            ("⚡", self.get_text('fast_command_execution'))
        ]
        
        for icon, text in features:
            feature_layout = QHBoxLayout()
            feature_layout.setSpacing(10)
            
            icon_label = QLabel(icon)
            icon_label.setFixedWidth(25)
            feature_layout.addWidget(icon_label)
            
            feature_label = QLabel(text)
            feature_label.setObjectName("featureLabel")
            feature_label.setWordWrap(True)
            feature_layout.addWidget(feature_label, 1)
            
            features_layout.addLayout(feature_layout)
            
        center_layout.addWidget(features_card)
        
        # 快速开始提示
        tip_card = QWidget()
        tip_card.setObjectName("tipCard")
        tip_layout = QVBoxLayout(tip_card)
        tip_layout.setContentsMargins(15, 10, 15, 10)
        
        tip_icon_label = QLabel("💡")
        tip_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_layout.addWidget(tip_icon_label)
        
        tip_label = QLabel(self.get_text('ssh_welcome_tip'))
        tip_label.setObjectName("tipLabel")
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label)
        
        center_layout.addWidget(tip_card)
        center_layout.addStretch()
        
        # 将居中容器添加到主布局
        layout.addStretch()
        layout.addWidget(center_widget, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        return widget
        
    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setObjectName("sshStatusBar")
        status_widget.setFixedHeight(35)
        
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(10, 0, 10, 0)
        
        # 状态标签
        self.status_label = QLabel(self.get_text('ready'))
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 连接计数
        self.connection_count_label = QLabel(f"0 {self.get_text('active_connections', 'connections')}")
        self.connection_count_label.setObjectName("connectionCountLabel")
        status_layout.addWidget(self.connection_count_label)
        
        parent_layout.addWidget(status_widget)
        
    def apply_theme_styles(self):
        """应用主题样式"""
        if not self.style_mgr:
            return
            
        # 获取当前是否为暗色主题
        is_dark = self.style_mgr.is_dark_mode()
        
        # 应用SSH终端特定的样式
        ssh_styles = f"""
        /* SSH终端内容区域 */
        #sshContent {{
            background-color: palette(window);
        }}
        
        /* 工具栏样式 */
        #sshToolbar {{
            background-color: palette(window);
            border-bottom: 1px solid palette(mid);
            padding: 5px;
        }}
        
        #sshToolbar QToolButton {{
            border: none;
            padding: 5px;
            border-radius: 4px;
        }}
        
        #sshToolbar QToolButton:hover {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}
        
        /* 左侧面板 */
        #sshLeftPanel {{
            background-color: palette(base);
            border-radius: 8px;
            border: 1px solid palette(mid);
        }}
        
        /* 设备组 */
        #deviceGroup {{
            font-weight: bold;
            border: 1px solid palette(mid);
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
        }}
        
        #deviceGroup::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 5px 0 5px;
            background-color: palette(base);
        }}
        
        /* 设备树 */
        #deviceTree {{
            border: 1px solid palette(mid);
            border-radius: 4px;
            background-color: palette(base);
            selection-background-color: palette(highlight);
            selection-color: palette(highlighted-text);
        }}
        
        #deviceTree::item {{
            padding: 4px;
            border-radius: 2px;
        }}
        
        #deviceTree::item:hover {{
            background-color: palette(alternate-base);
        }}
        
        #deviceTree::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}
        
        /* 快速操作 */
        #quickActionsGroup {{
            font-weight: bold;
            border: 1px solid palette(mid);
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
        }}
        
        #quickCommandsList {{
            border: 1px solid palette(mid);
            border-radius: 4px;
            background-color: palette(base);
        }}
        
        #quickCommandsList::item {{
            padding: 6px;
            border-bottom: 1px solid palette(alternate-base);
        }}
        
        #quickCommandsList::item:hover {{
            background-color: palette(alternate-base);
        }}
        
        #quickCommandsList::item:selected {{
            background-color: palette(highlight);
            color: palette(highlighted-text);
        }}
        
        /* 右侧面板 */
        #sshRightPanel {{
            background-color: palette(base);
            border-radius: 8px;
            border: 1px solid palette(mid);
        }}
        
        /* 会话标签页 */
        #sessionTabs {{
            background-color: transparent;
        }}
        
        #sessionTabs::pane {{
            border: none;
            background-color: palette(base);
        }}
        
        #sessionTabs::tab-bar {{
            left: 5px;
        }}
        
        #sessionTabs QTabBar::tab {{
            background-color: palette(button);
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border: 1px solid palette(mid);
            border-bottom: none;
        }}
        
        #sessionTabs QTabBar::tab:selected {{
            background-color: palette(base);
            border-color: palette(highlight);
            color: palette(highlighted-text);
        }}
        
        #sessionTabs QTabBar::tab:hover {{
            background-color: palette(alternate-base);
        }}
        
        /* 欢迎页面 */
        #welcomeWidget {{
            background-color: palette(base);
        }}
        
        #welcomeContainer {{
            background-color: transparent;
        }}
        
        #welcomeTitle {{
            font-size: 24px;
            font-weight: bold;
            color: palette(text);
            margin: 0;
        }}
        
        #welcomeSubtitle {{
            font-size: 14px;
            color: palette(mid);
            margin: 0;
        }}
        
        #featuresCard {{
            background-color: palette(alternate-base);
            border-radius: 8px;
            border: 1px solid palette(mid);
        }}
        
        #featuresTitle {{
            font-size: 16px;
            font-weight: bold;
            color: palette(text);
            margin-bottom: 8px;
        }}
        
        #featureLabel {{
            font-size: 14px;
            color: palette(text);
        }}
        
        #tipCard {{
            background-color: palette(alternate-base);
            border-radius: 8px;
            border: 1px solid palette(highlight);
        }}
        
        #tipLabel {{
            font-size: 14px;
            color: palette(text);
            margin: 0;
        }}
        
        /* 状态栏 */
        #sshStatusBar {{
            background-color: palette(window);
            border-top: 1px solid palette(mid);
        }}
        
        #statusLabel, #connectionCountLabel {{
            color: palette(text);
            font-size: 13px;
        }}
        """
        
        # 设备状态颜色（适应主题）
        if is_dark:
            ssh_styles += """
            /* 暗色主题特定样式 */
            .connected-status {
                color: #4CAF50;
            }
            .disconnected-status {
                color: #F44336;
            }
            """
        else:
            ssh_styles += """
            /* 亮色主题特定样式 */
            .connected-status {
                color: #2E7D32;
            }
            .disconnected-status {
                color: #C62828;
            }
            """
        
        # 应用样式
        self.setStyleSheet(ssh_styles)
        
    def setup_connections(self):
        """设置信号连接"""
        # 设备扫描器信号
        self.device_scanner.device_found.connect(self.add_device_to_list)
        self.device_scanner.scan_finished.connect(self.on_scan_finished)
        
        # 定时更新连接计数
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_connection_count)
        self.update_timer.start(1000)
        
    def scan_devices(self):
        """扫描设备"""
        self.status_label.setText(self.get_text('scanning_devices'))
        
        # 清空现有设备列表（除了已连接的）
        root = self.device_tree.invisibleRootItem()
        for i in range(root.childCount() - 1, -1, -1):
            item = root.child(i)
            if not self.is_device_connected(item):
                root.removeChild(item)
                
        # 启动扫描
        self.device_scanner.start()
        
    def is_device_connected(self, item: QTreeWidgetItem) -> bool:
        """检查设备是否已连接"""
        device_info = item.data(1, Qt.ItemDataRole.UserRole)
        if device_info and device_info.get('identifier') in self.active_sessions:
            return True
        return False
        
    def add_device_to_list(self, device_info: dict):
        """添加设备到列表"""
        # 检查是否已存在（基于设备名称去重）
        root = self.device_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            existing_info = item.data(1, Qt.ItemDataRole.UserRole)
            if existing_info and existing_info.get('name') == device_info['name']:
                # 更新现有设备的identifier（使用最新的）
                logger.debug(f"更新设备 {device_info['name']} 的标识符: {device_info['identifier']}")
                item.setData(0, Qt.ItemDataRole.UserRole, device_info['identifier'])
                item.setData(1, Qt.ItemDataRole.UserRole, device_info)
                return
                
        # 添加新设备
        item = QTreeWidgetItem()
        item.setText(0, device_info['name'])
        item.setData(0, Qt.ItemDataRole.UserRole, device_info['identifier'])
        item.setData(1, Qt.ItemDataRole.UserRole, device_info)
        
        # 设置图标
        item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        # 设置初始状态
        self.update_device_status(item, "disconnected")
        
        self.device_tree.addTopLevelItem(item)
        
    def update_device_status(self, item: QTreeWidgetItem, status: str):
        """更新设备状态"""
        if status == "connected":
            item.setText(1, self.get_text('connected'))
            item.setData(2, Qt.ItemDataRole.UserRole, "connected")
            # 使用主题感知的颜色
            if self.style_mgr and self.style_mgr.is_dark_mode():
                item.setForeground(1, QColor(76, 175, 80))  # 亮绿色
            else:
                item.setForeground(1, QColor(46, 125, 50))  # 深绿色
            font = item.font(1)
            font.setBold(True)
            item.setFont(1, font)
        else:
            item.setText(1, self.get_text('disconnected'))
            item.setData(2, Qt.ItemDataRole.UserRole, "disconnected")
            # 使用主题感知的颜色
            if self.style_mgr and self.style_mgr.is_dark_mode():
                item.setForeground(1, QColor(244, 67, 54))  # 亮红色
            else:
                item.setForeground(1, QColor(198, 40, 40))  # 深红色
            font = item.font(1)
            font.setBold(False)
            item.setFont(1, font)
        
    def on_scan_finished(self):
        """扫描完成"""
        self.status_label.setText(self.get_text('scan_complete'))
        
    def add_wifi_device(self):
        """添加Wi-Fi设备"""
        # TODO: 实现Wi-Fi设备添加对话框
        device_info = {
            'identifier': 'wifi_device',
            'name': 'Wi-Fi Device',
            'connection_type': 'wifi',
            'host': '192.168.1.100',
            'port': 22
        }
        self.add_device_to_list(device_info)
        
    def on_device_double_clicked(self, item: QTreeWidgetItem, column: int):
        """设备双击事件"""
        device_info = item.data(1, Qt.ItemDataRole.UserRole)
        if device_info:
            status = item.data(2, Qt.ItemDataRole.UserRole)
            if status == "connected":
                # 切换到对应的会话标签
                self.activate_session(device_info['identifier'])
            else:
                # 显示连接对话框
                self.show_connection_dialog(device_info)
                
    def show_connection_dialog(self, device_info: dict):
        """显示连接对话框"""
        dialog = ConnectionDialog(self, device_info, self.credential_store)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_connection_params()
            self.connect_device(device_info, params)
            
    def connect_device(self, device_info: dict, params: dict):
        """连接设备"""
        logger.info(f"Connecting to device: {device_info['name']}")
        
        # 更新状态
        self.status_label.setText(self.get_text('connecting_to', device_info['name']))
        
        # 创建新的终端widget
        terminal = SSHTerminalWidget()
        
        # 连接信号
        terminal.connection_established.connect(
            lambda name: self.on_connection_established(device_info, terminal)
        )
        terminal.connection_lost.connect(
            lambda: self.on_connection_lost(device_info)
        )
        
        # 添加到标签页
        tab_index = self.session_tabs.addTab(
            terminal,
            device_info['name']
        )
        self.session_tabs.setCurrentIndex(tab_index)
        self.session_tabs.setTabIcon(
            tab_index, 
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
        
        # 保存引用
        self.active_sessions[device_info['identifier']] = terminal
        
        # 连接设备
        success = terminal.connect_device(
            device_info,
            params['username'],
            params['password']
        )
        
        if not success:
            # 连接失败，移除标签页
            self.session_tabs.removeTab(tab_index)
            del self.active_sessions[device_info['identifier']]
            self.status_label.setText(self.get_text('connection_failed'))
        else:
            # 保存凭据
            if params.get('save_password'):
                self.credential_store.save_credential(
                    device_id=device_info['identifier'],
                    username=params['username'],
                    password=params['password'],
                    host=params.get('host', 'localhost'),
                    port=params.get('port', 2222),
                    connection_type=params['connection_type'],
                    device_name=device_info['name']
                )
            
    def on_connection_established(self, device_info: dict, terminal: SSHTerminalWidget):
        """连接建立"""
        logger.info(f"Connection established to {device_info['name']}")
        
        # 更新设备状态
        root = self.device_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == device_info['identifier']:
                self.update_device_status(item, "connected")
                break
                
        self.status_label.setText(self.get_text('connected_to', device_info['name']))
        
    def on_connection_lost(self, device_info: dict):
        """连接断开"""
        logger.info(f"Connection lost to {device_info['name']}")
        
        # 更新设备状态
        root = self.device_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == device_info['identifier']:
                self.update_device_status(item, "disconnected")
                break
                
        self.status_label.setText(self.get_text('disconnected'))
        
    def activate_session(self, device_id: str):
        """激活会话"""
        if device_id in self.active_sessions:
            terminal = self.active_sessions[device_id]
            # 查找并切换到对应标签页
            for i in range(self.session_tabs.count()):
                if self.session_tabs.widget(i) == terminal:
                    self.session_tabs.setCurrentIndex(i)
                    break
                    
    def execute_quick_command(self, item: QListWidgetItem):
        """执行快速命令"""
        current_widget = self.session_tabs.currentWidget()
        if isinstance(current_widget, SSHTerminalWidget):
            command = item.data(Qt.ItemDataRole.UserRole)
            if command and current_widget.ssh_client.is_connected:
                current_widget.execute_command(command)
                
    def close_session_tab(self, index: int):
        """关闭会话标签页"""
        if index == 0:  # 欢迎页面不能关闭
            return
            
        widget = self.session_tabs.widget(index)
        
        # 查找对应的设备
        device_id = None
        device_info = None
        for did, terminal in self.active_sessions.items():
            if terminal == widget:
                device_id = did
                # 获取设备信息
                root = self.device_tree.invisibleRootItem()
                for i in range(root.childCount()):
                    item = root.child(i)
                    if item.data(0, Qt.ItemDataRole.UserRole) == did:
                        device_info = item.data(1, Qt.ItemDataRole.UserRole)
                        break
                break
                
        if device_id:
            # 确认关闭
            reply = QMessageBox.question(
                self,
                self.get_text("close_session"),
                self.get_text("close_session_msg", "Close this SSH session?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 断开连接
                terminal = self.active_sessions[device_id]
                terminal.disconnect()
                
                # 移除标签页
                self.session_tabs.removeTab(index)
                
                # 清理引用
                del self.active_sessions[device_id]
                
                # 触发连接断开事件
                if device_info:
                    self.on_connection_lost(device_info)
                    
    def update_connection_count(self):
        """更新连接计数"""
        count = len(self.active_sessions)
        self.connection_count_label.setText(f"{count} {self.get_text('active_connections', 'connections')}")
                
    def show_device_context_menu(self, pos):
        """显示设备右键菜单"""
        # TODO: 实现右键菜单功能
        pass
    
    def open_credential_manager(self):
        """打开凭据管理器"""
        try:
            from .credential_manager_dialog import CredentialManagerDialog
            
            # 创建并显示凭据管理器，传递当前的凭据存储实例
            dialog = CredentialManagerDialog(self, self.credential_store)
            
            # 连接信号，当凭据发生变化时刷新界面
            dialog.credentials_changed.connect(self.on_credentials_changed)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Failed to open credential manager: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.get_text("error"), str(e))
    
    def on_credentials_changed(self):
        """凭据发生变化时的处理"""
        # 可以在这里刷新设备列表或更新UI
        logger.info("Credentials changed, refreshing UI...")
        
    def closeEvent(self, event):
        """关闭事件"""
        # 断开所有连接
        for terminal in self.active_sessions.values():
            terminal.disconnect()
        event.accept()
