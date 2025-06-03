# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
iOS 文件管理器界面组件，提供可视化的文件浏览、上传、下载和管理功能。

英文介绍:
iOS file manager UI widget providing visual file browsing, upload, download and management capabilities.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QUrl, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QDragEnterEvent, QDropEvent, QPixmap, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLabel, QLineEdit,
                             QMessageBox, QFileDialog, QMenu, QSplitter,
                             QTextEdit, QProgressBar, QToolBar, QDialog,
                             QDialogButtonBox, QComboBox, QCheckBox,
                             QHeaderView, QStyle, QFrame, QScrollArea,
                             QStackedWidget, QToolButton)

from ..core.ios_filesystem import iOSFileSystem, AccessLevel, FileInfo
from ..localization.language_manager import LanguageManager
from ..utils.debug_logger import debug
from .styles import StyleManager

# 自定义数据角色
FileInfoRole = Qt.ItemDataRole.UserRole + 1


class SearchThread(QThread):
    """递归搜索线程"""
    result_found = pyqtSignal(FileInfo)
    search_complete = pyqtSignal(int)
    
    def __init__(self, filesystem, start_path, search_text):
        super().__init__()
        self.filesystem = filesystem
        self.start_path = start_path
        self.search_text = search_text.lower()
        self.result_count = 0
        self._is_cancelled = False
    
    def run(self):
        """执行搜索"""
        try:
            self._search_directory(self.start_path)
        except Exception as e:
            debug(f"Search error: {e}")
        finally:
            self.search_complete.emit(self.result_count)
    
    def _search_directory(self, path: str):
        """递归搜索目录"""
        if self._is_cancelled:
            return
        
        try:
            files = self.filesystem.list_directory(path)
            for file_info in files:
                if self._is_cancelled:
                    return
                
                # 检查文件名是否匹配
                if self.search_text in file_info.name.lower():
                    self.result_found.emit(file_info)
                    self.result_count += 1
                
                # 如果是目录，递归搜索
                if file_info.is_directory and not self.filesystem.is_path_dangerous(file_info.path):
                    self._search_directory(file_info.path)
        except Exception as e:
            debug(f"Error searching directory {path}: {e}")
    
    def cancel(self):
        """取消搜索"""
        self._is_cancelled = True


class FileTransferThread(QThread):
    """文件传输线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, filesystem, operation, source, destination=None):
        super().__init__()
        self.filesystem = filesystem
        self.operation = operation  # 'download', 'upload', 'delete', 'delete_multiple'
        self.source = source  # For delete_multiple, this is a list of paths
        self.destination = destination
        self._is_cancelled = False
    
    def run(self):
        """执行文件操作"""
        try:
            if self.operation == 'download':
                self._download_file()
            elif self.operation == 'upload':
                self._upload_file()
            elif self.operation == 'delete':
                self._delete_file()
            elif self.operation == 'delete_multiple':
                self._delete_multiple_files()
            else:
                self.finished.emit(False, f"Unknown operation: {self.operation}")
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def _download_file(self):
        """下载文件到本地"""
        try:
            filename = os.path.basename(self.source)
            self.progress.emit(0, f"Preparing to download {filename}...")
            
            # 获取文件大小
            try:
                file_info = self.filesystem.afc_client.stat(self.source)
                file_size = int(file_info.get('st_size', 0))
                size_mb = file_size / (1024 * 1024)
                self.progress.emit(10, f"Downloading {filename} ({size_mb:.1f} MB)...")
            except:
                self.progress.emit(10, f"Downloading {filename}...")
            
            # 定义进度回调
            def progress_callback(src, dst):
                self.progress.emit(50, f"Transferring {filename}...")
            
            # 使用新的 download_file 方法（使用 AFC 的 pull）
            self.filesystem.download_file(self.source, self.destination, callback=progress_callback)
            
            if self._is_cancelled:
                self.finished.emit(False, "Cancelled")
                return
            
            self.progress.emit(100, f"Download complete: {filename}")
            self.finished.emit(True, f"Downloaded to {self.destination}")
            
        except Exception as e:
            self.finished.emit(False, f"Download failed: {str(e)}")
    
    def _upload_file(self):
        """上传文件到设备"""
        try:
            filename = os.path.basename(self.source)
            self.progress.emit(0, f"Preparing to upload {filename}...")
            
            # 获取文件大小
            try:
                file_size = os.path.getsize(self.source)
                size_mb = file_size / (1024 * 1024)
                self.progress.emit(10, f"Uploading {filename} ({size_mb:.1f} MB)...")
            except:
                self.progress.emit(10, f"Uploading {filename}...")
            
            # 定义进度回调
            def progress_callback(src, dst):
                self.progress.emit(50, f"Transferring {filename}...")
            
            # 使用新的 upload_file 方法（使用 AFC 的 push）
            self.filesystem.upload_file(self.source, self.destination, callback=progress_callback)
            
            if self._is_cancelled:
                self.finished.emit(False, "Cancelled")
                return
            
            self.progress.emit(100, f"Upload complete: {filename}")
            self.finished.emit(True, f"Uploaded to {self.destination}")
            
        except Exception as e:
            self.finished.emit(False, f"Upload failed: {str(e)}")
    
    def _delete_file(self):
        """删除文件"""
        try:
            self.progress.emit(50, f"Deleting {os.path.basename(self.source)}...")
            self.filesystem.delete(self.source)
            self.progress.emit(100, "Delete complete")
            self.finished.emit(True, "File deleted successfully")
        except Exception as e:
            self.finished.emit(False, f"Delete failed: {str(e)}")
    
    def _delete_multiple_files(self):
        """删除多个文件"""
        try:
            total_files = len(self.source)
            deleted_count = 0
            failed_files = []
            
            for i, path in enumerate(self.source):
                if self._is_cancelled:
                    self.finished.emit(False, f"Cancelled after deleting {deleted_count} of {total_files} files")
                    return
                
                filename = os.path.basename(path)
                progress = int((i / total_files) * 100)
                self.progress.emit(progress, f"Deleting {filename}... ({i+1}/{total_files})")
                
                try:
                    self.filesystem.delete(path)
                    deleted_count += 1
                except Exception as e:
                    failed_files.append((filename, str(e)))
                    debug(f"Failed to delete {filename}: {e}")
            
            self.progress.emit(100, "Delete operation complete")
            
            if failed_files:
                error_msg = f"Deleted {deleted_count} files successfully.\nFailed to delete {len(failed_files)} files:"
                for filename, error in failed_files[:5]:  # Show first 5 errors
                    error_msg += f"\n- {filename}: {error}"
                if len(failed_files) > 5:
                    error_msg += f"\n... and {len(failed_files) - 5} more"
                self.finished.emit(False, error_msg)
            else:
                self.finished.emit(True, f"Successfully deleted {deleted_count} files")
        except Exception as e:
            self.finished.emit(False, f"Delete operation failed: {str(e)}")
    
    def cancel(self):
        """取消操作"""
        self._is_cancelled = True


class FileManagerWidget(QDialog):
    """文件管理器主窗口"""
    
    file_double_clicked = pyqtSignal(str)  # 双击文件信号
    
    def __init__(self, device, lang_mgr: LanguageManager, style_mgr: StyleManager = None, parent=None):
        super().__init__(parent)
        self.device = device
        self.lang_mgr = lang_mgr
        self.style_mgr = style_mgr
        self.filesystem = None
        self.current_path = "/"
        self.transfer_thread = None
        self.file_icons = {}
        
        # 导航历史
        self.history = []
        self.history_index = -1
        
        # 收藏夹路径
        self.favorites = self.load_favorites()
        
        # 搜索相关
        self.search_results = []
        self.is_searching = False
        
        self.init_ui()
        self.init_filesystem()
        self.load_directory(self.current_path)
        
        # 应用样式
        if self.style_mgr:
            self.style_mgr.apply_global_style(self)
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"{self.device.name} - {self.lang_mgr.get_text('file_manager') or 'File Manager'}")
        self.setModal(False)  # 非模态对话框
        self.resize(900, 600)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)  # 设置组件间距
        layout.setContentsMargins(5, 5, 5, 5)  # 设置边距
        
        # 工具栏
        self.create_toolbar(layout)
        
        # 路径栏
        self.create_path_bar(layout)
        
        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 文件列表
        self.create_file_list(splitter)
        
        # 预览面板
        self.create_preview_panel(splitter)
        
        splitter.setSizes([600, 300])
        layout.addWidget(splitter, 1)  # 让分割器占用剩余空间
        
        # 状态栏
        self.create_status_bar(layout)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # 启用拖放
        self.setAcceptDrops(True)
        
        # 设置键盘快捷键
        self.setup_shortcuts()
    
    def create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        
        # 获取系统样式
        style = self.style()
        
        # 后退按钮
        self.back_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowLeft),
            self.lang_mgr.get_text("back") or "Back", self)
        self.back_action.setShortcut("Alt+Left")
        self.back_action.triggered.connect(self.go_back)
        self.back_action.setEnabled(False)  # 初始禁用
        toolbar.addAction(self.back_action)
        
        # 前进按钮
        self.forward_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight),
            self.lang_mgr.get_text("forward") or "Forward", self)
        self.forward_action.setShortcut("Alt+Right")
        self.forward_action.triggered.connect(self.go_forward)
        self.forward_action.setEnabled(False)  # 初始禁用
        toolbar.addAction(self.forward_action)
        
        # 上级目录
        self.up_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
            self.lang_mgr.get_text("parent_directory") or "Up", self)
        self.up_action.triggered.connect(self.go_up)
        toolbar.addAction(self.up_action)
        
        toolbar.addSeparator()
        
        # 主目录
        self.home_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon),
            self.lang_mgr.get_text("home") or "Home", self)
        self.home_action.triggered.connect(self.go_home)
        toolbar.addAction(self.home_action)
        
        # 刷新
        self.refresh_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            self.lang_mgr.get_text("refresh") or "Refresh", self)
        self.refresh_action.setShortcut("F5")
        self.refresh_action.triggered.connect(self.refresh_current)
        toolbar.addAction(self.refresh_action)
        
        toolbar.addSeparator()
        
        # 新建文件夹
        self.mkdir_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            self.lang_mgr.get_text("new_folder") or "New Folder", self)
        self.mkdir_action.setShortcut("Ctrl+Shift+N")
        self.mkdir_action.triggered.connect(self.create_folder)
        toolbar.addAction(self.mkdir_action)
        
        # 上传文件
        self.upload_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
            self.lang_mgr.get_text("upload") or "Upload", self)
        self.upload_action.setShortcut("Ctrl+U")
        self.upload_action.triggered.connect(self.upload_file)
        toolbar.addAction(self.upload_action)
        
        # 下载文件
        self.download_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown),
            self.lang_mgr.get_text("download") or "Download", self)
        self.download_action.setShortcut("Ctrl+D")
        self.download_action.triggered.connect(self.download_selected_items)
        toolbar.addAction(self.download_action)
        
        toolbar.addSeparator()
        
        # 收藏夹按钮
        self.favorites_button = QToolButton()
        self.favorites_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.favorites_button.setText(self.lang_mgr.get_text("favorites") or "Favorites")
        self.favorites_button.setToolTip("Ctrl+B")
        self.favorites_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.favorites_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        self.favorites_menu = QMenu()
        self.favorites_button.setMenu(self.favorites_menu)
        self.update_favorites_menu()
        toolbar.addWidget(self.favorites_button)
        
        # 添加当前路径到收藏夹
        self.add_favorite_action = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            self.lang_mgr.get_text("add_to_favorites") or "Add to Favorites", self)
        self.add_favorite_action.setShortcut("Ctrl+Shift+B")
        self.add_favorite_action.triggered.connect(self.add_current_to_favorites)
        toolbar.addAction(self.add_favorite_action)
        
        toolbar.addSeparator()
        
        # 搜索模式选择
        self.search_mode = QComboBox()
        self.search_mode.addItems([
            self.lang_mgr.get_text("search_current") or "Current Directory",
            self.lang_mgr.get_text("search_recursive") or "Include Subdirectories"
        ])
        self.search_mode.setCurrentIndex(0)
        self.search_mode.setMaximumWidth(150)
        self.search_mode.currentIndexChanged.connect(self.on_search_mode_changed)
        toolbar.addWidget(self.search_mode)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.lang_mgr.get_text("search") or "Search...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.filter_files)
        self.search_input.setClearButtonEnabled(True)
        toolbar.addWidget(self.search_input)
        
        parent_layout.addWidget(toolbar)
    
    def create_path_bar(self, parent_layout):
        """创建路径栏"""
        path_frame = QFrame()
        path_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        path_frame.setMaximumHeight(50)  # 限制路径栏最大高度
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(5, 5, 5, 5)
        path_layout.setSpacing(5)
        
        # 面包屑导航容器
        self.breadcrumb_scroll = QScrollArea()
        self.breadcrumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.breadcrumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.breadcrumb_scroll.setMaximumHeight(40)
        self.breadcrumb_scroll.setWidgetResizable(True)
        
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_widget)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(0)
        
        self.breadcrumb_scroll.setWidget(self.breadcrumb_widget)
        self.breadcrumb_scroll.setFrameShape(QFrame.Shape.NoFrame)
        path_layout.addWidget(self.breadcrumb_scroll)
        
        # 访问级别指示器
        self.access_label = QLabel()
        self.update_access_indicator()
        path_layout.addWidget(self.access_label)
        
        # 路径输入按钮 - 使用终端风格的提示符
        self.edit_path_button = QPushButton("›_")
        self.edit_path_button.setToolTip(self.lang_mgr.get_text("edit_path") or "Edit path (Ctrl+L)")
        self.edit_path_button.setMaximumWidth(35)
        self.edit_path_button.setStyleSheet("""
            QPushButton {
                font-family: Monaco, Consolas, monospace;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid palette(mid);
                border-radius: 3px;
                padding: 2px 4px;
                background: palette(button);
            }
            QPushButton:hover {
                background: palette(midlight);
                border-color: palette(highlight);
            }
            QPushButton:pressed {
                background: palette(mid);
            }
        """)
        self.edit_path_button.clicked.connect(self.show_path_input)
        path_layout.addWidget(self.edit_path_button)
        
        parent_layout.addWidget(path_frame)
        
        # 路径输入框（单独一行，初始隐藏）
        self.path_input_widget = QWidget()
        self.path_input_widget.setVisible(False)
        self.path_input_widget.setMaximumHeight(40)  # 限制输入框高度
        path_input_layout = QHBoxLayout(self.path_input_widget)
        path_input_layout.setContentsMargins(5, 0, 5, 5)
        
        self.path_input = QLineEdit()
        self.path_input.setText(self.current_path)
        self.path_input.returnPressed.connect(self.navigate_to_path)
        
        # 取消按钮
        cancel_button = QPushButton(self.lang_mgr.get_text("cancel") or "Cancel")
        cancel_button.clicked.connect(self.hide_path_input)
        cancel_button.setMaximumWidth(80)
        
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(cancel_button)
        
        parent_layout.addWidget(self.path_input_widget)
        
        # 初始化面包屑
        self.update_breadcrumbs()
    
    def create_file_list(self, parent):
        """创建文件列表"""
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels([
            self.lang_mgr.get_text("name") or "Name",
            self.lang_mgr.get_text("size") or "Size",
            self.lang_mgr.get_text("modified") or "Modified",
            self.lang_mgr.get_text("permissions") or "Permissions"
        ])
        
        # 设置列宽
        header = self.file_tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 启用多选
        self.file_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # 启用交替行颜色
        self.file_tree.setAlternatingRowColors(True)
        
        # 启用排序
        self.file_tree.setSortingEnabled(True)
        self.file_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # 连接信号
        self.file_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_tree.customContextMenuRequested.connect(self.show_context_menu)
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.itemSelectionChanged.connect(self.on_selection_changed)
        
        parent.addWidget(self.file_tree)
    
    def create_preview_panel(self, parent):
        """创建预览面板"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(5, 5, 5, 5)
        
        # 预览标题栏
        preview_header = QHBoxLayout()
        
        self.preview_label = QLabel(self.lang_mgr.get_text("preview") or "Preview")
        self.preview_label.setStyleSheet("font-weight: bold;")
        preview_header.addWidget(self.preview_label)
        
        preview_header.addStretch()
        
        # 编辑按钮（初始隐藏）
        self.edit_file_button = QPushButton(self.lang_mgr.get_text("edit") or "Edit")
        self.edit_file_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.edit_file_button.setVisible(False)
        self.edit_file_button.clicked.connect(self.toggle_edit_mode)
        preview_header.addWidget(self.edit_file_button)
        
        # 保存按钮（初始隐藏）
        self.save_file_button = QPushButton(self.lang_mgr.get_text("save") or "Save")
        self.save_file_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_file_button.setVisible(False)
        self.save_file_button.clicked.connect(self.save_edited_file)
        preview_header.addWidget(self.save_file_button)
        
        preview_layout.addLayout(preview_header)
        
        # 堆叠窗口用于切换不同的预览类型
        self.preview_stack = QStackedWidget()
        
        # 文本预览/编辑器
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_stack.addWidget(self.preview_text)
        
        # 图片预览
        self.preview_image_scroll = QScrollArea()
        self.preview_image_label = QLabel()
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setScaledContents(False)
        self.preview_image_scroll.setWidget(self.preview_image_label)
        self.preview_image_scroll.setWidgetResizable(True)
        self.preview_stack.addWidget(self.preview_image_scroll)
        
        # 空预览提示
        self.empty_preview = QLabel(self.lang_mgr.get_text("select_file_to_preview") or 
                                   "Select a file to preview")
        self.empty_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_preview.setStyleSheet("color: gray;")
        self.preview_stack.addWidget(self.empty_preview)
        
        # 设置默认显示空预览
        self.preview_stack.setCurrentWidget(self.empty_preview)
        
        preview_layout.addWidget(self.preview_stack)
        
        # 存储当前预览的文件信息
        self.current_preview_file = None
        self.is_edit_mode = False
        
        preview_widget.setLayout(preview_layout)
        parent.addWidget(preview_widget)
    
    def create_status_bar(self, parent_layout):
        """创建状态栏"""
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.items_label = QLabel()
        status_layout.addWidget(self.items_label)
        
        parent_layout.addLayout(status_layout)
    
    def init_filesystem(self):
        """初始化文件系统"""
        # 根据设备越狱状态确定访问级别
        if not self.device.is_jailbroken:
            access_level = AccessLevel.NONE
        elif "Rootless" in self.device.jailbreak_type:
            access_level = AccessLevel.ROOTLESS
        else:
            access_level = AccessLevel.ROOTFUL
        
        self.filesystem = iOSFileSystem(self.device, access_level)
        self.current_path = self.filesystem.get_home_directory()
        self.path_input.setText(self.current_path)
        
        debug(f"File manager initialized with access level: {access_level.value}")
        
        # 检查 AFC 客户端状态
        if not self.filesystem.afc_client:
            self.status_label.setText("AFC not available - Limited functionality")
            self.status_label.setStyleSheet("color: orange;")
            debug("AFC client not available, using fallback mode")
    
    def update_access_indicator(self):
        """更新访问级别指示器"""
        if not self.filesystem:
            return
        
        access_text = {
            AccessLevel.NONE: self.lang_mgr.get_text("limited_access") or "Limited Access",
            AccessLevel.ROOTLESS: "Rootless Access",
            AccessLevel.ROOTFUL: self.lang_mgr.get_text("full_access") or "Full Access"
        }
        
        access_color = {
            AccessLevel.NONE: "orange",
            AccessLevel.ROOTLESS: "blue",
            AccessLevel.ROOTFUL: "green"
        }
        
        level = self.filesystem.access_level
        self.access_label.setText(f"[{access_text.get(level, 'Unknown')}]")
        self.access_label.setStyleSheet(f"color: {access_color.get(level, 'gray')};")
    
    def load_directory(self, path: str, from_history: bool = False):
        """加载目录内容"""
        try:
            self.file_tree.clear()
            self.status_label.setText(self.lang_mgr.get_text("loading") or "Loading...")
            
            # 如果不是根目录，添加父目录项
            if path != "/":
                parent_item = QTreeWidgetItem(self.file_tree)
                parent_item.setText(0, "..")
                parent_item.setData(0, Qt.ItemDataRole.UserRole, os.path.dirname(path))
                parent_item.setIcon(0, self.get_file_icon("directory"))
            
            # 获取文件列表
            files = self.filesystem.list_directory(path)
            
            # 添加文件项
            for file_info in files:
                item = QTreeWidgetItem(self.file_tree)
                item.setText(0, file_info.name)
                item.setText(1, file_info.display_size)
                item.setText(2, file_info.display_time)
                item.setText(3, file_info.permissions)
                item.setData(0, Qt.ItemDataRole.UserRole, file_info.path)
                item.setData(0, FileInfoRole, file_info)
                
                # 设置图标
                icon = self.get_file_icon(file_info.file_type)
                item.setIcon(0, icon)
                
                # 危险路径标记为红色
                if self.filesystem.is_path_dangerous(file_info.path):
                    item.setForeground(0, Qt.GlobalColor.red)
            
            # 更新当前路径
            self.current_path = path
            self.path_input.setText(path)
            self.update_breadcrumbs()
            
            # 更新历史记录（如果不是从历史导航来的）
            if not from_history:
                self._add_to_history(path)
            
            # 更新导航按钮状态
            self._update_navigation_state()
            
            # 更新状态
            item_count = len(files)
            self.items_label.setText(f"{item_count} items")
            self.status_label.setText("Ready")
            
        except PermissionError as e:
            QMessageBox.warning(self, self.lang_mgr.get_text("error") or "Error", str(e))
            self.status_label.setText("Access denied")
        except Exception as e:
            QMessageBox.critical(self, self.lang_mgr.get_text("error") or "Error",
                                 f"Failed to load directory: {str(e)}")
            self.status_label.setText("Error")
    
    def get_file_icon(self, file_type: str) -> QIcon:
        """获取文件图标"""
        if file_type in self.file_icons:
            return self.file_icons[file_type]
        
        # 使用系统图标
        style = self.style()
        icon_map = {
            'directory': QStyle.StandardPixmap.SP_DirIcon,
            'file': QStyle.StandardPixmap.SP_FileIcon,
            'package': QStyle.StandardPixmap.SP_ComputerIcon,
            'config': QStyle.StandardPixmap.SP_FileDialogDetailedView,
            'text': QStyle.StandardPixmap.SP_FileDialogContentsView,
            'image': QStyle.StandardPixmap.SP_FileDialogInfoView,
        }
        
        pixmap = icon_map.get(file_type, QStyle.StandardPixmap.SP_FileIcon)
        icon = style.standardIcon(pixmap)
        self.file_icons[file_type] = icon
        
        return icon
    
    def on_item_double_clicked(self, item, column):
        """处理双击事件"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        file_info = item.data(0, FileInfoRole)
        
        if not path:
            return
        
        # 如果是父目录项
        if item.text(0) == "..":
            self.load_directory(path)
            return
        
        # 如果是目录
        if file_info and file_info.is_directory:
            self.load_directory(path)
        else:
            # 如果是文件，尝试预览
            self.preview_file(path, file_info)
            
            # 如果是 .deb 文件，发出信号
            if path.endswith('.deb'):
                self.file_double_clicked.emit(path)
    
    def preview_file(self, path: str, file_info: FileInfo):
        """预览文件"""
        self.current_preview_file = (path, file_info)
        self.preview_label.setText(f"{self.lang_mgr.get_text('preview') or 'Preview'}: {file_info.name}")
        
        # 文件大小限制
        MAX_PREVIEW_SIZE = 5 * 1024 * 1024  # 5MB for images, 1MB for text
        MAX_TEXT_SIZE = 1024 * 1024  # 1MB
        
        # 图片文件类型
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg']
        if any(path.lower().endswith(ext) for ext in image_extensions):
            if file_info.size > MAX_PREVIEW_SIZE:
                self.show_empty_preview(f"Image too large to preview ({file_info.display_size})")
                return
            
            try:
                # 下载图片数据
                image_data = self.filesystem.read_file(path, binary=True)
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    # 获取预览面板的实际大小
                    preview_size = self.preview_stack.size()
                    # 留出一些边距
                    max_width = preview_size.width() - 20
                    max_height = preview_size.height() - 20
                    
                    # 只有当图片大于预览区域时才缩放
                    if pixmap.width() > max_width or pixmap.height() > max_height:
                        pixmap = pixmap.scaled(max_width, max_height, 
                                             Qt.AspectRatioMode.KeepAspectRatio, 
                                             Qt.TransformationMode.SmoothTransformation)
                    
                    self.preview_image_label.setPixmap(pixmap)
                    self.preview_stack.setCurrentWidget(self.preview_image_scroll)
                    self.edit_file_button.setVisible(False)
                else:
                    self.show_empty_preview("Failed to load image")
            except Exception as e:
                self.show_empty_preview(f"Failed to preview image: {str(e)}")
            return
        
        # 文本文件类型
        text_extensions = ['.txt', '.log', '.plist', '.xml', '.json', '.md', '.py', '.sh',
                           '.conf', '.cfg', '.ini', '.yaml', '.yml', '.js', '.css', '.html',
                           '.cpp', '.h', '.swift', '.m', '.mm']
        
        if any(path.lower().endswith(ext) for ext in text_extensions):
            if file_info.size > MAX_TEXT_SIZE:
                self.show_empty_preview(f"File too large to preview ({file_info.display_size})")
                return
            
            try:
                # 特殊处理 plist 文件
                if path.lower().endswith('.plist'):
                    try:
                        # 先尝试读取二进制格式
                        binary_content = self.filesystem.read_file(path, binary=True)
                        import plistlib
                        plist_data = plistlib.loads(binary_content)
                        # 转换为可读的 XML 格式
                        content = plistlib.dumps(plist_data, fmt=plistlib.FMT_XML).decode('utf-8')
                        # 更新预览标题，显示这是二进制 plist
                        self.preview_label.setText(f"{self.lang_mgr.get_text('preview') or 'Preview'}: {file_info.name} (Binary plist → XML)")
                    except plistlib.InvalidFileException:
                        # 如果不是有效的 plist 格式，可能是文本格式或损坏的文件
                        try:
                            content = self.filesystem.read_file(path, binary=False)
                        except UnicodeDecodeError:
                            # 如果无法解码为文本，显示错误
                            self.show_empty_preview("Binary plist file appears corrupted")
                            return
                    except Exception as e:
                        # 其他错误，尝试作为文本读取
                        try:
                            content = self.filesystem.read_file(path, binary=False)
                        except:
                            self.show_empty_preview(f"Failed to read plist: {str(e)}")
                            return
                else:
                    content = self.filesystem.read_file(path, binary=False)
                
                self.preview_text.setPlainText(content)
                self.preview_stack.setCurrentWidget(self.preview_text)
                
                # 显示编辑按钮（对于某些文件类型）
                editable_extensions = ['.txt', '.log', '.json', '.xml', '.plist', '.ini', '.cfg']
                if any(path.lower().endswith(ext) for ext in editable_extensions):
                    self.edit_file_button.setVisible(True)
                else:
                    self.edit_file_button.setVisible(False)
                    
            except Exception as e:
                self.show_empty_preview(f"Failed to preview: {str(e)}")
        else:
            # 二进制文件
            self.show_empty_preview(f"Binary file ({file_info.file_type})\nSize: {file_info.display_size}")
    
    def show_empty_preview(self, message: str = None):
        """显示空预览"""
        if message:
            self.empty_preview.setText(message)
        else:
            self.empty_preview.setText(self.lang_mgr.get_text("select_file_to_preview") or 
                                     "Select a file to preview")
        self.preview_stack.setCurrentWidget(self.empty_preview)
        self.edit_file_button.setVisible(False)
        self.save_file_button.setVisible(False)
        self.current_preview_file = None
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.file_tree.itemAt(position)
        menu = QMenu()
        
        # 如果点击在空白处，显示目录菜单
        if not item:
            # 在当前目录上传
            upload_here_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
                self.lang_mgr.get_text("upload_here") or "Upload Here")
            upload_here_action.triggered.connect(self.upload_file)
            
            # 新建文件夹
            new_folder_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
                self.lang_mgr.get_text("new_folder") or "New Folder")
            new_folder_action.triggered.connect(self.create_folder)
            
            menu.addSeparator()
            
            # 刷新
            refresh_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
                self.lang_mgr.get_text("refresh") or "Refresh")
            refresh_action.triggered.connect(self.refresh_current)
            
            # 复制当前路径
            copy_path_action = menu.addAction(
                self.lang_mgr.get_text("copy_path") or "Copy Path")
            copy_path_action.triggered.connect(lambda: self._copy_to_clipboard(self.current_path))
            
            menu.exec(self.file_tree.mapToGlobal(position))
            return
        
        # 项目菜单
        if item.text(0) == "..":
            return
        
        file_info = item.data(0, FileInfoRole)
        if not file_info:
            return
        
        # 打开/查看
        if file_info.is_directory:
            open_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
                self.lang_mgr.get_text("open") or "Open")
            open_action.triggered.connect(lambda: self.load_directory(file_info.path))
            
            menu.addSeparator()
            
            # 在此处上传
            upload_here_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp),
                self.lang_mgr.get_text("upload_to_folder") or "Upload to this folder")
            upload_here_action.triggered.connect(lambda: self._upload_to_folder(file_info.path))
        else:
            view_action = menu.addAction(
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
                self.lang_mgr.get_text("view") or "View")
            view_action.triggered.connect(lambda: self.preview_file(file_info.path, file_info))
        
        menu.addSeparator()
        
        # 下载
        download_action = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown),
            self.lang_mgr.get_text("download") or "Download")
        download_action.triggered.connect(lambda: self.download_file(file_info.path))
        
        # 下载并打开
        if not file_info.is_directory:
            download_open_action = menu.addAction(
                self.lang_mgr.get_text("download_and_open") or "Download and Open")
            download_open_action.triggered.connect(lambda: self._download_and_open(file_info.path))
        
        menu.addSeparator()
        
        # 重命名
        rename_action = menu.addAction(self.lang_mgr.get_text("rename") or "Rename")
        rename_action.setShortcut("F2")
        rename_action.triggered.connect(lambda: self.rename_file(file_info.path))
        
        # 删除
        delete_action = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            self.lang_mgr.get_text("delete") or "Delete")
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(lambda: self.delete_file(file_info.path))
        
        # 如果是危险路径，禁用某些操作
        if self.filesystem.is_path_dangerous(file_info.path):
            rename_action.setEnabled(False)
            delete_action.setEnabled(False)
        
        menu.addSeparator()
        
        # 复制路径
        copy_path_action = menu.addAction(
            self.lang_mgr.get_text("copy_path") or "Copy Path")
        copy_path_action.triggered.connect(lambda: self._copy_to_clipboard(file_info.path))
        
        # 特殊操作
        if file_info.path.endswith('.deb'):
            menu.addSeparator()
            install_action = menu.addAction(
                self.lang_mgr.get_text("install_package") or "Install Package")
            install_action.triggered.connect(lambda: self.file_double_clicked.emit(file_info.path))
        
        menu.addSeparator()
        
        # 属性
        props_action = menu.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView),
            self.lang_mgr.get_text("properties") or "Properties")
        props_action.triggered.connect(lambda: self.show_properties(file_info))
        
        menu.exec(self.file_tree.mapToGlobal(position))
    
    def download_file(self, path: str):
        """下载文件到本地"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        filename = os.path.basename(path)
        
        # 获取默认下载目录
        default_download_dir = self._get_download_directory()
        default_path = os.path.join(default_download_dir, filename)
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            self.lang_mgr.get_text("save_file") or "Save File",
            default_path
        )
        
        if not save_path:
            return
        
        # 显示下载开始提示
        self.status_label.setText(
            self.lang_mgr.format_text("downloading_file", filename) or f"Downloading {filename}..."
        )
        
        # 创建并启动传输线程
        self.transfer_thread = FileTransferThread(
            self.filesystem,
            'download',
            path,
            save_path
        )
        
        self.transfer_thread.progress.connect(self.update_progress)
        self.transfer_thread.finished.connect(self.on_transfer_finished)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.transfer_thread.start()
    
    def upload_file(self):
        """上传文件到设备"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.lang_mgr.get_text("select_file") or "Select File"
        )
        
        if not file_path:
            return
        
        filename = os.path.basename(file_path)
        dest_path = os.path.join(self.current_path, filename)
        
        # 检查是否已存在
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.text(0) == filename:
                reply = QMessageBox.question(
                    self,
                    self.lang_mgr.get_text("confirm") or "Confirm",
                    f"{filename} already exists. Overwrite?"
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                break
        
        # 显示上传开始提示
        self.status_label.setText(
            self.lang_mgr.format_text("uploading_file", filename) or f"Uploading {filename}..."
        )
        
        # 创建并启动传输线程
        self.transfer_thread = FileTransferThread(
            self.filesystem,
            'upload',
            file_path,
            dest_path
        )
        
        self.transfer_thread.progress.connect(self.update_progress)
        self.transfer_thread.finished.connect(self.on_transfer_finished)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.transfer_thread.start()
    
    def delete_file(self, path: str):
        """删除文件"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        filename = os.path.basename(path)
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm") or "Confirm",
            f"Delete {filename}?"
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 创建并启动传输线程
        self.transfer_thread = FileTransferThread(
            self.filesystem,
            'delete',
            path
        )
        
        self.transfer_thread.progress.connect(self.update_progress)
        self.transfer_thread.finished.connect(self.on_transfer_finished)
        
        self.progress_bar.setVisible(True)
        self.transfer_thread.start()
    
    def rename_file(self, path: str):
        """重命名文件"""
        old_name = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        
        # 输入新名称
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            self.lang_mgr.get_text("rename") or "Rename",
            self.lang_mgr.get_text("new_name") or "New name:",
            text=old_name
        )
        
        if not ok or not new_name or new_name == old_name:
            return
        
        new_path = os.path.join(parent_dir, new_name)
        
        try:
            self.filesystem.rename(path, new_path)
            self.refresh_current()
            self.status_label.setText("Renamed successfully")
        except Exception as e:
            QMessageBox.critical(self, self.lang_mgr.get_text("error") or "Error", str(e))
    
    def create_folder(self):
        """创建新文件夹"""
        from PyQt6.QtWidgets import QInputDialog
        folder_name, ok = QInputDialog.getText(
            self,
            self.lang_mgr.get_text("new_folder") or "New Folder",
            self.lang_mgr.get_text("folder_name") or "Folder name:"
        )
        
        if not ok or not folder_name:
            return
        
        folder_path = os.path.join(self.current_path, folder_name)
        
        try:
            self.filesystem.create_directory(folder_path)
            self.refresh_current()
            self.status_label.setText("Folder created successfully")
        except Exception as e:
            QMessageBox.critical(self, self.lang_mgr.get_text("error") or "Error", str(e))
    
    def show_properties(self, file_info: FileInfo):
        """显示文件属性"""
        props = f"""
<b>{self.lang_mgr.get_text("file_properties") or "File Properties"}</b><br><br>
<b>{self.lang_mgr.get_text("name") or "Name"}:</b> {file_info.name}<br>
<b>{self.lang_mgr.get_text("path") or "Path"}:</b> {file_info.path}<br>
<b>{self.lang_mgr.get_text("type") or "Type"}:</b> {file_info.file_type}<br>
<b>{self.lang_mgr.get_text("size") or "Size"}:</b> {file_info.display_size} ({file_info.size} bytes)<br>
<b>{self.lang_mgr.get_text("modified") or "Modified"}:</b> {file_info.display_time}<br>
<b>{self.lang_mgr.get_text("permissions") or "Permissions"}:</b> {file_info.permissions}<br>
<b>{self.lang_mgr.get_text("owner") or "Owner"}:</b> {file_info.owner}<br>
<b>{self.lang_mgr.get_text("group") or "Group"}:</b> {file_info.group}<br>
"""
        
        QMessageBox.information(self, self.lang_mgr.get_text("properties") or "Properties", props)
    
    def update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_transfer_finished(self, success: bool, message: str):
        """传输完成"""
        self.progress_bar.setVisible(False)
        self.transfer_thread = None
        
        if success:
            self.status_label.setText(message)
            
            # 根据操作类型显示不同的通知
            if "Downloaded" in message:
                # 下载成功提示
                download_path = message.split("to ")[-1]
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle(self.lang_mgr.get_text("download_complete") or "Download Complete")
                msg_box.setText(self.lang_mgr.format_text("file_downloaded_to", download_path) or message)
                
                # 添加按钮
                open_folder_btn = msg_box.addButton(
                    self.lang_mgr.get_text("open_folder") or "Open Folder", 
                    QMessageBox.ButtonRole.ActionRole
                )
                msg_box.addButton(QMessageBox.StandardButton.Ok)
                
                msg_box.exec()
                
                # 如果用户点击了打开文件夹
                if msg_box.clickedButton() == open_folder_btn:
                    import platform
                    import subprocess
                    folder_path = os.path.dirname(download_path)
                    try:
                        if platform.system() == 'Darwin':  # macOS
                            subprocess.run(['open', folder_path])
                        elif platform.system() == 'Windows':
                            os.startfile(folder_path)
                        else:  # Linux
                            subprocess.run(['xdg-open', folder_path])
                    except Exception as e:
                        debug(f"Failed to open folder: {e}")
            elif "Uploaded" in message:
                # 上传成功提示
                QMessageBox.information(
                    self,
                    self.lang_mgr.get_text("upload_complete") or "Upload Complete",
                    self.lang_mgr.get_text("file_uploaded_successfully") or "File uploaded successfully!"
                )
                self.refresh_current()
            elif "delete" in message:
                # 删除成功，刷新目录
                self.refresh_current()
        else:
            QMessageBox.critical(self, self.lang_mgr.get_text("error") or "Error", message)
            self.status_label.setText("Operation failed")
    
    def _add_to_history(self, path: str):
        """添加路径到历史记录"""
        # 如果当前不是历史的末尾，删除后面的记录
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        # 避免重复添加相同路径
        if not self.history or self.history[-1] != path:
            self.history.append(path)
            self.history_index = len(self.history) - 1
    
    def _update_navigation_state(self):
        """更新导航按钮状态"""
        self.back_action.setEnabled(self.history_index > 0)
        self.forward_action.setEnabled(self.history_index < len(self.history) - 1)
        
        # 更新上级目录按钮
        self.up_action.setEnabled(self.current_path != "/")
    
    def go_back(self):
        """后退"""
        if self.history_index > 0:
            self.history_index -= 1
            self.load_directory(self.history[self.history_index], from_history=True)
    
    def go_forward(self):
        """前进"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.load_directory(self.history[self.history_index], from_history=True)
    
    def go_up(self):
        """上级目录"""
        if self.current_path != "/":
            parent = os.path.dirname(self.current_path)
            self.load_directory(parent)
    
    def go_home(self):
        """主目录"""
        home = self.filesystem.get_home_directory()
        self.load_directory(home)
    
    def refresh_current(self):
        """刷新当前目录"""
        self.load_directory(self.current_path)
    
    
    def navigate_to_path(self):
        """导航到输入的路径"""
        path = self.path_input.text()
        if path:
            self.load_directory(path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def update_breadcrumbs(self):
        """更新面包屑导航"""
        # 清除现有的面包屑
        while self.breadcrumb_layout.count():
            child = self.breadcrumb_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 分解路径
        parts = []
        path = self.current_path
        while path and path != '/':
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            if basename:
                parts.insert(0, (basename, path))
            path = dirname
        
        # 添加根目录按钮
        root_btn = QPushButton("/")
        root_btn.setFlat(True)
        root_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        root_btn.setStyleSheet("""
            QPushButton {
                border: none;
                padding: 4px 8px;
                background: transparent;
            }
            QPushButton:hover {
                background: palette(midlight);
                border-radius: 4px;
            }
        """)
        root_btn.clicked.connect(lambda: self.load_directory("/"))
        self.breadcrumb_layout.addWidget(root_btn)
        
        # 添加路径部分
        for name, full_path in parts:
            # 添加分隔符
            separator = QLabel(" › ")
            separator.setStyleSheet("color: palette(mid);")
            self.breadcrumb_layout.addWidget(separator)
            
            # 添加路径按钮
            path_btn = QPushButton(name)
            path_btn.setFlat(True)
            path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            path_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    padding: 4px 8px;
                    background: transparent;
                }
                QPushButton:hover {
                    background: palette(midlight);
                    border-radius: 4px;
                }
            """)
            # 使用默认参数捕获当前路径
            path_btn.clicked.connect(lambda checked=False, p=full_path: self.load_directory(p))
            self.breadcrumb_layout.addWidget(path_btn)
        
        # 添加弹性空间，防止按钮拉伸
        self.breadcrumb_layout.addStretch()
    
    def setup_shortcuts(self):
        """设置键盘快捷键"""
        # Enter - 打开文件或目录
        enter_shortcut = QShortcut(Qt.Key.Key_Return, self)
        enter_shortcut.activated.connect(self.open_selected_item)
        
        # Backspace - 返回上级目录
        back_shortcut = QShortcut(Qt.Key.Key_Backspace, self)
        back_shortcut.activated.connect(self.go_up)
        
        # F2 - 重命名
        rename_shortcut = QShortcut(Qt.Key.Key_F2, self)
        rename_shortcut.activated.connect(self.rename_selected_item)
        
        # Delete - 删除
        delete_shortcut = QShortcut(Qt.Key.Key_Delete, self)
        delete_shortcut.activated.connect(self.delete_selected_items)
        
        # Ctrl+L - 聚焦到路径输入
        path_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        path_shortcut.activated.connect(self.show_path_input)
        
        # Ctrl+F - 聚焦到搜索框
        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(lambda: self.search_input.setFocus())
        
        # Ctrl+N - 新建文件夹
        new_folder_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_folder_shortcut.activated.connect(self.create_folder)
        
        # Ctrl+R / F5 - 刷新
        refresh_shortcut1 = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut1.activated.connect(self.refresh_current)
        refresh_shortcut2 = QShortcut(Qt.Key.Key_F5, self)
        refresh_shortcut2.activated.connect(self.refresh_current)
        
        # Ctrl+D - 下载
        download_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        download_shortcut.activated.connect(self.download_selected_items)
        
        # Ctrl+U - 上传
        upload_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        upload_shortcut.activated.connect(self.upload_file)
    
    def open_selected_item(self):
        """打开选中的项目"""
        current_item = self.file_tree.currentItem()
        if current_item:
            self.on_item_double_clicked(current_item, 0)
    
    def rename_selected_item(self):
        """重命名选中的项目"""
        current_item = self.file_tree.currentItem()
        if current_item and current_item.text(0) != "..":
            file_info = current_item.data(0, FileInfoRole)
            if file_info:
                self.rename_file(file_info.path)
    
    def delete_selected_items(self):
        """删除选中的项目"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
        
        # 过滤掉 ".." 项
        items_to_delete = []
        for item in selected_items:
            if item.text(0) != "..":
                file_info = item.data(0, FileInfoRole)
                if file_info:
                    items_to_delete.append(file_info)
        
        if not items_to_delete:
            return
        
        # 确认删除
        if len(items_to_delete) == 1:
            message = f"Delete {items_to_delete[0].name}?"
        else:
            message = f"Delete {len(items_to_delete)} items?"
        
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm") or "Confirm",
            message
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if len(items_to_delete) == 1:
                # 单个文件，使用原有的 delete_file 方法
                self.delete_file(items_to_delete[0].path)
            else:
                # 多个文件，使用批量删除
                paths = [file_info.path for file_info in items_to_delete]
                
                # 创建并启动传输线程
                self.transfer_thread = FileTransferThread(
                    self.filesystem,
                    'delete_multiple',
                    paths  # 传递路径列表
                )
                
                self.transfer_thread.progress.connect(self.update_progress)
                self.transfer_thread.finished.connect(self.on_transfer_finished)
                
                self.progress_bar.setVisible(True)
                self.transfer_thread.start()
    
    def download_selected_items(self):
        """下载选中的项目"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
        
        # 如果只有一个文件，使用文件对话框
        if len(selected_items) == 1:
            item = selected_items[0]
            if item.text(0) != "..":
                file_info = item.data(0, FileInfoRole)
                if file_info and not file_info.is_directory:
                    self.download_file(file_info.path)
                    return
        
        # 多个文件或包含目录，选择目标文件夹
        folder = QFileDialog.getExistingDirectory(
            self,
            self.lang_mgr.get_text("select_folder") or "Select Folder"
        )
        
        if folder:
            # TODO: 实现批量下载
            QMessageBox.information(
                self,
                "Info",
                "Batch download not implemented yet"
            )
    
    def toggle_path_input(self):
        """切换路径输入框显示状态"""
        if self.path_input_widget.isVisible():
            self.hide_path_input()
        else:
            self.show_path_input()
    
    def show_path_input(self):
        """显示路径输入框"""
        self.path_input_widget.setVisible(True)
        self.path_input.setText(self.current_path)
        self.path_input.setFocus()
        self.path_input.selectAll()
    
    def on_selection_changed(self):
        """处理选择变化"""
        selected_items = self.file_tree.selectedItems()
        
        if not selected_items:
            self.items_label.setText(f"{self.file_tree.topLevelItemCount()} items")
            return
        
        # 计算选中项目的总大小
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in selected_items:
            if item.text(0) == "..":
                continue
            
            file_info = item.data(0, FileInfoRole)
            if file_info:
                if file_info.is_directory:
                    dir_count += 1
                else:
                    file_count += 1
                    total_size += file_info.size
        
        # 更新状态栏
        parts = []
        if file_count > 0:
            parts.append(f"{file_count} file(s)")
        if dir_count > 0:
            parts.append(f"{dir_count} folder(s)")
        
        if parts:
            status_text = ", ".join(parts)
            if total_size > 0:
                # 格式化大小
                size_str = self._format_size(total_size)
                status_text += f" ({size_str})"
            self.items_label.setText(f"Selected: {status_text}")
        else:
            self.items_label.setText(f"{self.file_tree.topLevelItemCount()} items")
    
    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def hide_path_input(self):
        """隐藏路径输入框"""
        self.path_input_widget.setVisible(False)
        # 恢复当前路径到输入框（如果用户取消）
        self.path_input.setText(self.current_path)
    
    def _copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.status_label.setText(f"Copied: {text}")
    
    def _get_download_directory(self) -> str:
        """获取默认下载目录"""
        # 使用应用程序的下载目录
        if hasattr(self, 'style_mgr') and self.style_mgr and self.style_mgr.config_manager:
            app_dir = self.style_mgr.config_manager.config_dir
            download_dir = app_dir / "downloads"
            download_dir.mkdir(exist_ok=True)
            return str(download_dir)
        else:
            # 如果没有配置管理器，使用用户的下载目录
            return str(Path.home() / "Downloads" / "SimpleTweakEditor")
    
    def load_favorites(self) -> List[Tuple[str, str]]:
        """加载收藏夹"""
        # 从配置中加载收藏夹
        if hasattr(self, 'style_mgr') and self.style_mgr and self.style_mgr.config_manager:
            favorites_data = self.style_mgr.config_manager.get('file_manager_favorites', [])
            return [(item['name'], item['path']) for item in favorites_data]
        return []
    
    def save_favorites(self):
        """保存收藏夹"""
        if hasattr(self, 'style_mgr') and self.style_mgr and self.style_mgr.config_manager:
            favorites_data = [{'name': name, 'path': path} for name, path in self.favorites]
            self.style_mgr.config_manager.set('file_manager_favorites', favorites_data)
            self.style_mgr.config_manager.save_config()
    
    def update_favorites_menu(self):
        """更新收藏夹菜单"""
        if not hasattr(self, 'favorites_menu'):
            return
        
        menu = self.favorites_menu
        menu.clear()
        
        # 添加默认收藏夹
        default_favorites = [
            ("/", self.lang_mgr.get_text("root_directory") or "Root Directory"),
            ("/var/mobile", self.lang_mgr.get_text("mobile_home") or "Mobile Home"),
            ("/var/mobile/Library/Preferences", self.lang_mgr.get_text("preferences") or "Preferences"),
            ("/Applications", self.lang_mgr.get_text("applications") or "Applications"),
        ]
        
        for path, name in default_favorites:
            action = menu.addAction(f"{name} ({path})")
            action.triggered.connect(lambda checked, p=path: self.load_directory(p))
        
        if self.favorites:
            menu.addSeparator()
            menu.addAction(self.lang_mgr.get_text("user_favorites") or "User Favorites").setEnabled(False)
            
            for name, path in self.favorites:
                action = menu.addAction(f"{name}")
                action.setToolTip(path)
                action.triggered.connect(lambda checked, p=path: self.load_directory(p))
        
        menu.addSeparator()
        manage_action = menu.addAction(self.lang_mgr.get_text("manage_favorites") or "Manage Favorites...")
        manage_action.triggered.connect(self.manage_favorites)
    
    def add_current_to_favorites(self):
        """添加当前路径到收藏夹"""
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(
            self,
            self.lang_mgr.get_text("add_to_favorites") or "Add to Favorites",
            self.lang_mgr.get_text("favorite_name") or "Name for this favorite:",
            text=os.path.basename(self.current_path) or "Root"
        )
        
        if ok and name:
            # 检查是否已存在
            for existing_name, existing_path in self.favorites:
                if existing_path == self.current_path:
                    QMessageBox.information(
                        self,
                        self.lang_mgr.get_text("info") or "Information",
                        self.lang_mgr.get_text("path_already_favorite") or "This path is already in favorites!"
                    )
                    return
            
            self.favorites.append((name, self.current_path))
            self.save_favorites()
            self.update_favorites_menu()
            self.status_label.setText(f"Added to favorites: {name}")
    
    
    def remove_favorite(self, name: str, path: str):
        """移除收藏夹项"""
        self.favorites = [(n, p) for n, p in self.favorites if p != path]
        self.save_favorites()
        self.update_favorites_menu()
    
    def manage_favorites(self):
        """管理收藏夹对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.lang_mgr.get_text("manage_favorites") or "Manage Favorites")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 收藏夹列表
        list_widget = QTreeWidget()
        list_widget.setHeaderLabels([
            self.lang_mgr.get_text("name") or "Name",
            self.lang_mgr.get_text("path") or "Path"
        ])
        list_widget.setRootIsDecorated(False)
        
        # 添加现有收藏夹
        for name, path in self.favorites:
            item = QTreeWidgetItem(list_widget)
            item.setText(0, name)
            item.setText(1, path)
            item.setData(0, Qt.ItemDataRole.UserRole, (name, path))
        
        layout.addWidget(list_widget)
        
        # 按钮栏
        button_layout = QHBoxLayout()
        
        # 编辑按钮
        edit_btn = QPushButton(self.lang_mgr.get_text("edit") or "Edit")
        edit_btn.clicked.connect(lambda: self._edit_favorite_item(list_widget))
        button_layout.addWidget(edit_btn)
        
        # 删除按钮
        remove_btn = QPushButton(self.lang_mgr.get_text("remove") or "Remove")
        remove_btn.clicked.connect(lambda: self._remove_favorite_item(list_widget))
        button_layout.addWidget(remove_btn)
        
        button_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton(self.lang_mgr.get_text("close") or "Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # 显示对话框
        dialog.exec()
        
        # 更新收藏夹菜单
        self.update_favorites_menu()
    
    def _edit_favorite_item(self, list_widget):
        """编辑收藏夹项"""
        current_item = list_widget.currentItem()
        if not current_item:
            return
        
        old_name, path = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self,
            self.lang_mgr.get_text("edit") or "Edit",
            self.lang_mgr.get_text("favorite_name") or "Name for this favorite:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            # 更新收藏夹
            self.favorites = [(new_name if n == old_name and p == path else n, p) 
                            for n, p in self.favorites]
            self.save_favorites()
            
            # 更新列表项
            current_item.setText(0, new_name)
            current_item.setData(0, Qt.ItemDataRole.UserRole, (new_name, path))
    
    def _remove_favorite_item(self, list_widget):
        """从列表中移除收藏夹项"""
        current_item = list_widget.currentItem()
        if not current_item:
            return
        
        name, path = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm") or "Confirm",
            self.lang_mgr.format_text("remove_favorite_confirm", name) or f"Remove '{name}' from favorites?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 移除收藏夹
            self.favorites = [(n, p) for n, p in self.favorites if not (n == name and p == path)]
            self.save_favorites()
            
            # 从列表中移除
            list_widget.takeTopLevelItem(list_widget.indexOfTopLevelItem(current_item))
    
    def on_search_mode_changed(self, index):
        """搜索模式改变"""
        if self.search_input.text():
            self.filter_files(self.search_input.text())
    
    def filter_files(self, text: str):
        """过滤文件列表"""
        search_text = text.lower()
        
        if self.search_mode.currentIndex() == 0:
            # 当前目录搜索
            self._filter_current_directory(search_text)
        else:
            # 递归搜索
            if search_text:
                self._search_recursive(search_text)
            else:
                # 清空搜索时恢复正常显示
                self.is_searching = False
                self.load_directory(self.current_path)
    
    def _filter_current_directory(self, search_text: str):
        """过滤当前目录的文件"""
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item_name = item.text(0).lower()
            
            # 始终显示 ".." 项
            if item.text(0) == "..":
                item.setHidden(False)
            else:
                # 根据搜索文本显示或隐藏项目
                item.setHidden(search_text not in item_name)
    
    def _search_recursive(self, search_text: str):
        """递归搜索文件"""
        if not search_text:
            return
        
        # 显示搜索中状态
        self.status_label.setText(self.lang_mgr.get_text("searching") or "Searching...")
        self.file_tree.clear()
        self.is_searching = True
        
        # 创建搜索线程
        self.search_thread = SearchThread(
            self.filesystem,
            self.current_path,
            search_text
        )
        self.search_thread.result_found.connect(self._add_search_result)
        self.search_thread.search_complete.connect(self._on_search_complete)
        self.search_thread.start()
    
    def _add_search_result(self, file_info: FileInfo):
        """添加搜索结果到列表"""
        item = QTreeWidgetItem(self.file_tree)
        item.setText(0, file_info.name)
        item.setText(1, file_info.display_size)
        item.setText(2, file_info.display_time)
        item.setText(3, file_info.permissions)
        item.setData(0, Qt.ItemDataRole.UserRole, file_info.path)
        item.setData(0, FileInfoRole, file_info)
        
        # 设置图标
        icon = self.get_file_icon(file_info.file_type)
        item.setIcon(0, icon)
        
        # 显示完整路径作为提示
        item.setToolTip(0, file_info.path)
    
    def _on_search_complete(self, count: int):
        """搜索完成"""
        self.status_label.setText(
            self.lang_mgr.format_text("search_results_count", count) or f"Found {count} items"
        )
    
    def _upload_to_folder(self, folder_path: str):
        """上传文件到指定文件夹"""
        # 临时切换到目标文件夹
        old_path = self.current_path
        self.current_path = folder_path
        self.upload_file()
        self.current_path = old_path
    
    def _download_and_open(self, path: str):
        """下载并打开文件"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        import tempfile
        import subprocess
        import platform
        
        filename = os.path.basename(path)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        # 创建下载线程
        self.transfer_thread = FileTransferThread(
            self.filesystem,
            'download',
            path,
            temp_path
        )
        
        # 下载完成后打开文件
        def on_download_complete(success, message):
            if success:
                try:
                    if platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', temp_path])
                    elif platform.system() == 'Windows':
                        os.startfile(temp_path)
                    else:  # Linux
                        subprocess.run(['xdg-open', temp_path])
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to open file: {e}")
            else:
                QMessageBox.critical(self, "Error", message)
        
        self.transfer_thread.finished.connect(on_download_complete)
        self.transfer_thread.progress.connect(self.update_progress)
        
        self.progress_bar.setVisible(True)
        self.transfer_thread.start()
    
    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        # 检查是否有正在运行的传输
        if self.transfer_thread and self.transfer_thread.isRunning():
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("warning") or "Warning",
                self.lang_mgr.get_text("transfer_in_progress") or "A file transfer is already in progress. Please wait for it to complete."
            )
            return
        
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path and os.path.exists(file_path):
                # 上传文件
                filename = os.path.basename(file_path)
                dest_path = os.path.join(self.current_path, filename)
                
                # 检查文件是否已存在
                for i in range(self.file_tree.topLevelItemCount()):
                    item = self.file_tree.topLevelItem(i)
                    if item.text(0) == filename:
                        reply = QMessageBox.question(
                            self,
                            self.lang_mgr.get_text("confirm") or "Confirm",
                            f"{filename} already exists. Overwrite?"
                        )
                        if reply != QMessageBox.StandardButton.Yes:
                            return
                        break
                
                # 显示上传开始提示
                self.status_label.setText(
                    self.lang_mgr.format_text("uploading_file", filename) or f"Uploading {filename}..."
                )
                
                self.transfer_thread = FileTransferThread(
                    self.filesystem,
                    'upload',
                    file_path,
                    dest_path
                )
                
                self.transfer_thread.progress.connect(self.update_progress)
                self.transfer_thread.finished.connect(self.on_transfer_finished)
                
                self.progress_bar.setVisible(True)
                self.transfer_thread.start()
                
                break  # 一次只处理一个文件
    
    def toggle_edit_mode(self):
        """切换编辑模式"""
        if not self.current_preview_file:
            return
        
        if self.is_edit_mode:
            # 退出编辑模式
            self.preview_text.setReadOnly(True)
            self.edit_file_button.setText(self.lang_mgr.get_text("edit") or "Edit")
            self.save_file_button.setVisible(False)
            self.is_edit_mode = False
        else:
            # 进入编辑模式
            self.preview_text.setReadOnly(False)
            self.edit_file_button.setText(self.lang_mgr.get_text("cancel") or "Cancel")
            self.save_file_button.setVisible(True)
            self.is_edit_mode = True
            self.preview_text.setFocus()
    
    def save_edited_file(self):
        """保存编辑的文件"""
        if not self.current_preview_file or not self.is_edit_mode:
            return
        
        path, file_info = self.current_preview_file
        content = self.preview_text.toPlainText()
        
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm") or "Confirm",
            self.lang_mgr.get_text("save_changes") or f"Save changes to {file_info.name}?"
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 特殊处理 plist 文件
            if path.lower().endswith('.plist'):
                try:
                    # 尝试将 XML 格式转换回二进制格式
                    import plistlib
                    plist_data = plistlib.loads(content.encode('utf-8'))
                    # 检查原文件是否是二进制格式
                    try:
                        original_binary = self.filesystem.read_file(path, binary=True)
                        original_data = plistlib.loads(original_binary)
                        # 如果原文件是二进制格式，保存为二进制
                        binary_content = plistlib.dumps(plist_data, fmt=plistlib.FMT_BINARY)
                        self.filesystem.write_file(path, binary_content)
                    except:
                        # 如果原文件不是二进制格式，保存为 XML
                        self.filesystem.write_file(path, content)
                except Exception as e:
                    # 如果转换失败，显示具体错误
                    raise Exception(f"Invalid plist format: {str(e)}")
            else:
                # 写入文件
                self.filesystem.write_file(path, content)
            
            # 退出编辑模式
            self.toggle_edit_mode()
            
            # 刷新文件列表
            self.refresh_current()
            
            # 更新状态
            self.status_label.setText(self.lang_mgr.get_text("file_saved") or "File saved successfully")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.lang_mgr.get_text("error") or "Error",
                self.lang_mgr.get_text("save_failed") or f"Failed to save file: {str(e)}"
            )
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止并等待传输线程
        if self.transfer_thread and self.transfer_thread.isRunning():
            self.transfer_thread.cancel()
            self.transfer_thread.wait(2000)  # 等待最多2秒
            if self.transfer_thread.isRunning():
                self.transfer_thread.terminate()  # 强制终止
                self.transfer_thread.wait()
        
        # 停止搜索线程
        if hasattr(self, 'search_thread') and self.search_thread and self.search_thread.isRunning():
            self.search_thread.cancel()
            self.search_thread.wait(1000)
            if self.search_thread.isRunning():
                self.search_thread.terminate()
                self.search_thread.wait()
        
        event.accept()
