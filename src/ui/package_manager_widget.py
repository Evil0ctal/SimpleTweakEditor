# -*- coding: utf-8 -*-
"""
创建时间: 2024-11-22
作者: Evil0ctal

中文介绍:
插件管理器模块，提供整合的包管理界面。
集成了包浏览、搜索、分类、批量下载和源管理功能。
采用虚拟化渲染和多线程加载，支持大量包数据的高效显示。

英文介绍:
Package manager module providing an integrated package management interface.
Integrates package browsing, search, categorization, batch download, and repository management.
Uses virtualized rendering and multi-threaded loading for efficient display of large package datasets.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QTabWidget, QWidget,
    QSplitter, QTextEdit, QProgressBar, QMessageBox,
    QFileDialog, QGroupBox, QToolButton, QMenu,
    QAbstractItemView, QFrame, QCheckBox, QListView, QApplication,
    QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QAbstractListModel, QModelIndex
from PyQt6.QtGui import QFont, QAction
from typing import List, Dict, Optional
import os
import sys
from pathlib import Path
from src.ui.repo_manager_dialog import RepoManagerDialog


class PackageListItemWidget(QWidget):
    """自定义的包列表项控件"""
    
    checkbox_toggled = pyqtSignal(bool)  # 勾选状态改变
    item_clicked = pyqtSignal()  # 项目被点击
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo = None
        self.package = None
        self.package_key = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)
        
        # 勾选框
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        layout.addWidget(self.checkbox)
        
        # 包名和版本标签
        self.label = QLabel("")
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.label, 1)
        
        # 工具提示将在设置包数据时设置
    
    def on_checkbox_changed(self, state):
        """勾选框状态改变"""
        self.checkbox_toggled.emit(self.checkbox.isChecked())
    
    def mousePressEvent(self, event):
        """鼠标单击事件"""
        # 如果点击的不是勾选框，则触发项目单击事件（查看信息）
        if event.button() == Qt.MouseButton.LeftButton:
            checkbox_rect = self.checkbox.geometry()
            if not checkbox_rect.contains(event.pos()):
                self.item_clicked.emit()
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        # 双击切换勾选状态（除非点击的是勾选框）
        if event.button() == Qt.MouseButton.LeftButton:
            checkbox_rect = self.checkbox.geometry()
            if not checkbox_rect.contains(event.pos()):
                # 切换勾选状态
                new_state = not self.checkbox.isChecked()
                self.checkbox.setChecked(new_state)
                self.checkbox_toggled.emit(new_state)
    
    def is_checked(self):
        """获取勾选状态"""
        return self.checkbox.isChecked()
    
    def set_checked(self, checked):
        """设置勾选状态"""
        self.checkbox.setChecked(checked)
    
    def set_package_data(self, repo, package, package_key):
        """设置包数据"""
        try:
            if not repo or not package:
                print(f"[ERROR] set_package_data 收到空参数: repo={repo}, package={package}")
                return
            
            self.repo = repo
            self.package = package
            self.package_key = package_key
            
            # 更新显示文本
            if hasattr(package, 'get_display_name'):
                display_text = package.get_display_name()
                if hasattr(package, 'version') and package.version:
                    display_text += f" ({package.version})"
                self.label.setText(display_text)
            else:
                print(f"[ERROR] package对象没有get_display_name方法: {type(package)}")
                self.label.setText(f"Unknown package: {package}")
            
            # 设置工具提示
            tooltip_parts = [f"包名: {package.package}"]
            if hasattr(package, 'author') and package.author:
                tooltip_parts.append(f"作者: {package.author}")
            if hasattr(package, 'size') and package.size:
                tooltip_parts.append(f"大小: {package.get_display_size()}")
            self.setToolTip("\n".join(tooltip_parts))
                
        except Exception as e:
            print(f"[ERROR] set_package_data 出错: {e}")
            import traceback
            traceback.print_exc()
    
    def set_text(self, text):
        """设置显示文本"""
        self.label.setText(text)


class PackageDetailWidget(QWidget):
    """包详情显示组件"""
    
    download_requested = pyqtSignal(object, object)  # repo, package
    
    def __init__(self, lang_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.current_package = None
        self.current_repo = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 包信息卡片
        info_title = self.lang_mgr.get_text("package_info") if self.lang_mgr else "Package Information"
        info_group = QGroupBox(info_title)
        info_layout = QVBoxLayout()
        
        # 包名和版本
        self.name_label = QLabel()
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.name_label.setFont(font)
        info_layout.addWidget(self.name_label)
        
        # 作者和大小
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)  # 启用自动换行
        info_layout.addWidget(self.info_label)
        
        # 描述
        self.desc_text = QTextEdit()
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(80)
        info_layout.addWidget(self.desc_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 详细信息
        details_title = self.lang_mgr.get_text("details") if self.lang_mgr else "Details"
        details_group = QGroupBox(details_title)
        details_layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        details_layout.addWidget(self.details_text)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        download_text = self.lang_mgr.get_text("download") if self.lang_mgr else "Download"
        self.download_btn = QPushButton(download_text)
        self.download_btn.setMinimumHeight(35)
        self.download_btn.clicked.connect(self._on_download)
        btn_layout.addWidget(self.download_btn)
        
        # 查看历史版本按钮
        versions_text = self.lang_mgr.get_text("view_versions") if self.lang_mgr else "View Versions"
        self.versions_btn = QPushButton(versions_text)
        self.versions_btn.setMinimumHeight(35)
        self.versions_btn.clicked.connect(self._on_view_versions)
        self.versions_btn.setVisible(False)  # 默认隐藏
        btn_layout.addWidget(self.versions_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def show_package(self, repo, package, package_versions=None):
        """显示包信息"""
        self.current_repo = repo
        self.current_package = package
        self.package_versions = package_versions
        
        # 包名和版本
        self.name_label.setText(f"{package.get_display_name()} - {package.get_display_version()}")
        
        # 显示/隐藏版本按钮
        if package_versions and len(package_versions) > 1:
            self.versions_btn.setVisible(True)
            version_count = len(package_versions)
            versions_text = f"View {version_count} Versions" if not self.lang_mgr else f"查看 {version_count} 个版本"
            self.versions_btn.setText(versions_text)
        else:
            self.versions_btn.setVisible(False)
        
        # 基本信息
        info_parts = []
        if package.get_display_author():
            author_text = self.lang_mgr.get_text("author") if self.lang_mgr else "Author"
            info_parts.append(f"{author_text}: {package.get_display_author()}")
        if package.get_display_size():
            size_text = self.lang_mgr.get_text("size") if self.lang_mgr else "Size"
            info_parts.append(f"{size_text}: {package.get_display_size()}")
        if repo:
            source_text = self.lang_mgr.get_text("source") if self.lang_mgr else "Source"
            info_parts.append(f"{source_text}: {repo.name}")
        self.info_label.setText(" | ".join(info_parts))
        
        # 描述
        no_desc_text = self.lang_mgr.get_text("no_description") if self.lang_mgr else "No description"
        desc = package.description or no_desc_text
        self.desc_text.setPlainText(desc)
        
        # 详细信息
        details = []
        package_text = self.lang_mgr.get_text("package_name") if self.lang_mgr else "Package"
        details.append(f"{package_text}: {package.package}")
        if package.section:
            section_text = self.lang_mgr.get_text("section") if self.lang_mgr else "Section"
            details.append(f"{section_text}: {package.section}")
        if package.depends:
            depends = package.depends
            if len(depends) > 100:
                depends = depends[:100] + "..."
            depends_text = self.lang_mgr.get_text("depends") if self.lang_mgr else "Depends"
            details.append(f"{depends_text}: {depends}")
        if package.filename:
            filename_text = self.lang_mgr.get_text("filename") if self.lang_mgr else "Filename"
            details.append(f"{filename_text}: {os.path.basename(package.filename)}")
        
        self.details_text.setPlainText("\n".join(details))
        
        # 更新按钮状态
        self.download_btn.setEnabled(bool(package.filename))
    
    def _on_download(self):
        """下载按钮点击"""
        if self.current_package and self.current_repo:
            self.download_requested.emit(self.current_repo, self.current_package)
    
    def _on_view_versions(self):
        """查看历史版本"""
        if not self.package_versions:
            return
            
        # 创建版本选择对话框
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("选择版本" if self.lang_mgr else "Select Version")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel(f"{self.current_package.get_display_name()} - 所有版本")
        title.setProperty("class", "heading")
        layout.addWidget(title)
        
        # 版本列表
        version_list = QListWidget()
        for repo, pkg in sorted(self.package_versions, key=lambda x: x[1].version if x[1].version else "", reverse=True):
            item_text = f"{pkg.version} - {repo.name}"
            if pkg.size:
                item_text += f" ({pkg.size})"
            version_list.addItem(item_text)
        
        # 默认选中当前版本
        for i in range(version_list.count()):
            if self.current_package.version in version_list.item(i).text():
                version_list.setCurrentRow(i)
                break
                
        layout.addWidget(version_list)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_index = version_list.currentRow()
            if selected_index >= 0:
                # 切换到选中的版本
                selected_repo, selected_pkg = sorted(self.package_versions, 
                                                   key=lambda x: x[1].version if x[1].version else "", 
                                                   reverse=True)[selected_index]
                self.show_package(selected_repo, selected_pkg, self.package_versions)
    
    def _on_change_path(self):
        """更改路径按钮点击"""
        # 获取PackageManagerWidget实例
        parent = self.parent()
        while parent and not isinstance(parent, PackageManagerWidget):
            parent = parent.parent()
        if parent:
            parent.change_download_path()
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        
        # 更新组框标题
        if hasattr(self, 'parent') and self.parent():
            info_group = self.findChild(QGroupBox)
            if info_group:
                info_title = lang_mgr.get_text("package_info") if lang_mgr else "Package Information"
                info_group.setTitle(info_title)
        
        # 更新按钮文本
        download_text = lang_mgr.get_text("download") if lang_mgr else "Download"
        self.download_btn.setText(download_text)
        
        versions_text = lang_mgr.get_text("view_versions") if lang_mgr else "View Versions"
        self.versions_btn.setText(versions_text)
        
        # 如果有当前包，重新显示
        if self.current_package and self.current_repo:
            self.show_package(self.current_repo, self.current_package, self.package_versions)


class PackageLoadWorker(QThread):
    """包加载工作线程"""
    progress_update = pyqtSignal(int, int, str)  # current, total, message
    batch_ready = pyqtSignal(list)  # List of (item_data, package_key)
    finished_loading = pyqtSignal()
    
    def __init__(self, packages, checked_items):
        super().__init__()
        self.packages = packages
        self.checked_items = checked_items
        self.is_canceled = False
        
    def run(self):
        """在后台线程中准备包数据"""
        batch_size = 1000  # 每批准备1000个包数据
        total_packages = len(self.packages)
        current_index = 0
        
        while current_index < total_packages and not self.is_canceled:
            batch_data = []
            end_index = min(current_index + batch_size, total_packages)
            
            # 准备批量数据（不创建UI组件）
            for i in range(current_index, end_index):
                if self.is_canceled:
                    break
                    
                repo, package = self.packages[i]
                if repo and package:
                    package_key = f"{repo.url}:{package.package}"
                    is_checked = self.checked_items.get(package_key, False)
                    
                    # 准备数据而不是创建widget
                    item_data = {
                        'repo': repo,
                        'package': package,
                        'package_key': package_key,
                        'is_checked': is_checked,
                        'index': i
                    }
                    batch_data.append(item_data)
            
            # 发送批量数据到主线程
            if batch_data and not self.is_canceled:
                self.batch_ready.emit(batch_data)
            
            # 更新进度
            current_index = end_index
            if not self.is_canceled:
                self.progress_update.emit(current_index, total_packages, 
                                        f"Loading packages... ({current_index}/{total_packages})")
            
            # 给其他线程一点时间
            self.msleep(1)
        
        if not self.is_canceled:
            self.finished_loading.emit()
    
    def cancel(self):
        """取消加载"""
        self.is_canceled = True


class PackageListModel(QAbstractListModel):
    """包列表数据模型 - 用于虚拟化渲染"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.packages = []  # [(repo, package), ...]
        self.checked_items = {}  # {package_key: bool}
        
    def rowCount(self, parent=QModelIndex()):
        """返回行数"""
        return len(self.packages)
    
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """返回指定索引的数据"""
        if not index.isValid() or index.row() >= len(self.packages):
            return None
            
        repo, package = self.packages[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            # 返回显示文本
            display_text = package.get_display_name()
            if hasattr(package, 'version') and package.version:
                display_text += f" ({package.version})"
            return display_text
        elif role == Qt.ItemDataRole.CheckStateRole:
            # 返回勾选状态
            package_key = f"{repo.url}:{package.package}"
            return Qt.CheckState.Checked if self.checked_items.get(package_key, False) else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.UserRole:
            # 返回完整数据
            return (repo, package)
        elif role == Qt.ItemDataRole.UserRole + 1:
            # 返回package_key
            return f"{repo.url}:{package.package}"
        elif role == Qt.ItemDataRole.ToolTipRole:
            # 返回工具提示
            tooltip = f"{package.get_display_name()}"
            if hasattr(package, 'version') and package.version:
                tooltip += f"\nVersion: {package.version}"
            if hasattr(package, 'author') and package.author:
                tooltip += f"\nAuthor: {package.author}"
            if hasattr(package, 'description') and package.description:
                tooltip += f"\n{package.description[:100]}..."
            return tooltip
            
        return None
    
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """设置数据"""
        if not index.isValid() or index.row() >= len(self.packages):
            return False
            
        if role == Qt.ItemDataRole.CheckStateRole:
            repo, package = self.packages[index.row()]
            package_key = f"{repo.url}:{package.package}"
            self.checked_items[package_key] = (value == Qt.CheckState.Checked)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            
            # 通知父widget更新全局checked_items
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, 'on_model_checkbox_toggled'):
                    parent_widget.on_model_checkbox_toggled(package_key, value == Qt.CheckState.Checked)
                    break
                parent_widget = parent_widget.parent()
            
            return True
            
        return False
    
    def flags(self, index):
        """返回项目标志"""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
            
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
    
    def add_packages(self, packages):
        """批量添加包"""
        if not packages:
            return
            
        first = len(self.packages)
        last = first + len(packages) - 1
        
        self.beginInsertRows(QModelIndex(), first, last)
        self.packages.extend(packages)
        self.endInsertRows()
    
    def clear(self):
        """清空所有包"""
        if not self.packages:
            return
            
        self.beginResetModel()
        self.packages.clear()
        self.checked_items.clear()
        self.endResetModel()
    
    def get_checked_packages(self):
        """获取所有勾选的包"""
        checked = []
        for repo, package in self.packages:
            package_key = f"{repo.url}:{package.package}"
            if self.checked_items.get(package_key, False):
                checked.append((repo, package))
        return checked
    
    def set_packages(self, packages):
        """设置包列表"""
        self.beginResetModel()
        self.packages = packages
        self.endResetModel()


class PackageManagerWidget(QDialog):
    """插件管理器主窗口"""
    
    package_downloaded = pyqtSignal(str)  # 下载完成的文件路径
    
    def __init__(self, parent=None, repo_manager=None, lang_mgr=None):
        super().__init__(parent)
        self.repo_manager = repo_manager
        self.lang_mgr = lang_mgr
        
        window_title = "Package Manager"
        if self.lang_mgr:
            try:
                window_title = self.lang_mgr.get_text("package_manager")
            except Exception as e:
                print(f"[WARNING] 获取窗口标题失败: {e}")
        
        self.setWindowTitle(window_title)
        self.setModal(False)
        self.resize(1000, 700)
        
        self.all_packages = []  # 所有包数据
        self.filtered_packages = []  # 筛选后的包
        self.package_versions = {}  # 存储每个包的所有版本 {repo_url:package_name: [(repo, package)...]}
        self.download_worker = None
        self.load_worker = None  # 包加载工作线程
        self.current_repo_filter = None  # 当前选中的源筛选
        self.batch_download_queue = []  # 批量下载队列
        self.batch_download_total = 0
        self.batch_download_current = 0
        
        # 默认下载路径
        self.download_path = str(Path.home() / "Downloads" / "SimpleTweakEditor")
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        
        self.init_ui()
        # 默认加载所有源的包
        self.load_all_packages()
    
    def set_source_filter(self, source_name: str):
        """设置源筛选 - 从Manage Sources调用时使用"""
        # 找到对应的repo对象
        target_repo = None
        for repo in self.repo_manager.repositories:
            if repo.name == source_name:
                target_repo = repo
                break
        
        if target_repo:
            # 加载该源的包
            self.filter_by_source(target_repo)
    
    def init_ui(self):
        """初始化界面"""
        try:
            layout = QVBoxLayout()
            
            # 顶部工具栏
            toolbar = QHBoxLayout()
            
            # 源选择器
            source_text = "Source:" if not self.lang_mgr else self.lang_mgr.get_text('source') + ":"
            toolbar.addWidget(QLabel(source_text))
            
            self.source_btn = QToolButton()
            all_sources_text = "All Sources" if not self.lang_mgr else self.lang_mgr.get_text("all_sources")
            self.source_btn.setText(all_sources_text)
            self.source_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            self.source_menu = QMenu()
            self.source_btn.setMenu(self.source_menu)
            # 设置按钮的最小宽度
            self.source_btn.setMinimumWidth(120)
            # 设置统一的按钮样式
            # 让qt-material处理按钮样式
            self.source_btn.setMinimumHeight(28)
            self.source_btn.setMaximumHeight(28)
            self.update_source_menu()
            toolbar.addWidget(self.source_btn)
            
            # 管理源按钮
            manage_sources_text = "Manage Sources" if not self.lang_mgr else self.lang_mgr.get_text("manage_sources")
            self.manage_sources_btn = QPushButton(manage_sources_text)
            self.manage_sources_btn.setMinimumHeight(28)
            self.manage_sources_btn.setMaximumHeight(28)
            self.manage_sources_btn.clicked.connect(self.open_repo_manager)
            toolbar.addWidget(self.manage_sources_btn)
        
            
            toolbar.addSpacing(20)
            
            # 搜索框
            search_text = "Search:" if not self.lang_mgr else self.lang_mgr.get_text('search') + ":"
            toolbar.addWidget(QLabel(search_text))
            
            self.search_input = QLineEdit()
            search_placeholder = "Search in all repositories..." if not self.lang_mgr else "在所有软件源中搜索..."
            self.search_input.setPlaceholderText(search_placeholder)
            # 实时搜索 - 当文本改变时触发
            self.search_input.textChanged.connect(self.on_search_text_changed)
            # 同时保留回车键搜索功能
            self.search_input.returnPressed.connect(self.perform_search)
            toolbar.addWidget(self.search_input, 1)
            
            # 搜索延迟定时器
            self.search_timer = QTimer()
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self.perform_search)
            
            # 刷新按钮
            refresh_text = "Refresh" if not self.lang_mgr else self.lang_mgr.get_text("refresh")
            self.refresh_btn = QPushButton(refresh_text)
            self.refresh_btn.clicked.connect(self.refresh_packages)
            toolbar.addWidget(self.refresh_btn)
            
            # 全选/取消全选按钮
            select_all_text = "Select All" if not self.lang_mgr else self.lang_mgr.get_text("select_all")
            self.select_all_btn = QPushButton(select_all_text)
            self.select_all_btn.clicked.connect(self.toggle_select_all)
            toolbar.addWidget(self.select_all_btn)
            
            # 批量下载按钮
            batch_download_text = "Batch Download" if not self.lang_mgr else self.lang_mgr.get_text("batch_download")
            self.batch_download_btn = QPushButton(batch_download_text)
            self.batch_download_btn.clicked.connect(self.batch_download)
            self.batch_download_btn.setEnabled(False)
            toolbar.addWidget(self.batch_download_btn)
            
            layout.addLayout(toolbar)
        
            # 主内容区域
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # 左侧：分类和包列表
            left_widget = QWidget()
            left_widget.setMinimumWidth(400)  # 设置最小宽度
            left_widget.setMaximumWidth(600)  # 设置最大宽度
            left_layout = QVBoxLayout(left_widget)
            left_layout.setContentsMargins(0, 0, 0, 0)
            
            # 分类标签
            self.tabs = QTabWidget()
            self.tabs.setUsesScrollButtons(True)  # 启用滚动按钮
            self.tabs.setElideMode(Qt.TextElideMode.ElideNone)  # 不省略标签文本
            
            # 移除标签栏的鼠标滚轮事件处理
            # self.tabs.tabBar().installEventFilter(self)
            
            # 添加标签页切换事件处理
            self.tabs.currentChanged.connect(self.on_tab_changed)
            
            # 初始化空的分类列表（将在加载包后动态生成）
            self.categories = []
            self.list_widgets = {}
            self.selected_packages = []  # 存储选中的包（使用列表而不是集合）
            self.checked_items = {}  # 存储勾选状态
            
            # 先创建"全部"分类
            all_widget = QListView()
            all_model = PackageListModel(self)  # 设置父对象
            all_widget.setModel(all_model)
            all_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            # 连接点击事件
            all_widget.clicked.connect(self.on_list_item_clicked)
            all_text = "All" if not self.lang_mgr else self.lang_mgr.get_text("all")
            self.tabs.addTab(all_widget, all_text)
            self.list_widgets["all"] = all_widget
            self.list_models = {"all": all_model}  # 存储模型引用
            
            left_layout.addWidget(self.tabs)
            
            # 右侧：包详情
            self.detail_widget = PackageDetailWidget(self.lang_mgr)
            self.detail_widget.download_requested.connect(self.download_package)
            self.detail_widget.setMinimumWidth(400)
            
            splitter.addWidget(left_widget)
            splitter.addWidget(self.detail_widget)
            splitter.setSizes([500, 500])
            splitter.setStretchFactor(0, 0)  # 左侧不拉伸
            splitter.setStretchFactor(1, 1)  # 右侧可拉伸
            
            layout.addWidget(splitter)
        
            # 底部区域 - 使用垂直布局
            bottom_widget = QWidget()
            bottom_widget.setMaximumHeight(150)
            bottom_layout = QVBoxLayout(bottom_widget)
            bottom_layout.setContentsMargins(0, 5, 0, 0)
            
            # 第一行：统计信息
            stats_layout = QHBoxLayout()
            
            # 包统计信息
            self.stats_label = QLabel()
            self.stats_label.setProperty("class", "heading")
            stats_layout.addWidget(self.stats_label)
            
            stats_layout.addSpacing(20)
            
            # 选中统计
            self.selection_stats_label = QLabel()
            self.selection_stats_label.setProperty("class", "info")
            stats_layout.addWidget(self.selection_stats_label)
            
            stats_layout.addStretch()
            
            # 当前筛选信息
            self.filter_info_label = QLabel()
            self.filter_info_label.setProperty("class", "secondary")
            stats_layout.addWidget(self.filter_info_label)
            
            bottom_layout.addLayout(stats_layout)
            
            # 分隔线
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            bottom_layout.addWidget(line)
            
            # 第二行：进度条和状态
            progress_layout = QHBoxLayout()
            
            # 状态信息
            loading_text = "Loading..." if not self.lang_mgr else self.lang_mgr.get_text("loading")
            self.status_label = QLabel(loading_text)
            progress_layout.addWidget(self.status_label)
            
            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMaximumWidth(300)
            progress_layout.addWidget(self.progress_bar)
            
            progress_layout.addStretch()
            
            bottom_layout.addLayout(progress_layout)
            
            # 第三行：下载路径和操作按钮
            path_layout = QHBoxLayout()
            
            # 下载路径显示
            download_path_text = "Download Path:" if not self.lang_mgr else self.lang_mgr.get_text('download_path')
            path_label = QLabel(download_path_text)
            path_label.setProperty("class", "secondary")
            path_layout.addWidget(path_label)
            
            self.path_label = QLabel(self.download_path)
            self.path_label.setProperty("class", "secondary")
            self.path_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.path_label.mousePressEvent = lambda e: self.open_download_folder()
            path_layout.addWidget(self.path_label)
            
            # 更改路径按钮
            change_path_text = "Change Path" if not self.lang_mgr else self.lang_mgr.get_text("change_path")
            change_path_btn = QPushButton(change_path_text)
            change_path_btn.clicked.connect(self.change_download_path)
            path_layout.addWidget(change_path_btn)
            
            path_layout.addStretch()
            
            # 快捷操作按钮
            clear_selection_text = "Clear Selection" if not self.lang_mgr else self.lang_mgr.get_text("clear_selection")
            clear_selection_btn = QPushButton(clear_selection_text)
            clear_selection_btn.clicked.connect(self.clear_all_selections)
            path_layout.addWidget(clear_selection_btn)
            
            bottom_layout.addLayout(path_layout)
        
            layout.addWidget(bottom_widget)
            
            self.setLayout(layout)
            
        except Exception as e:
            print(f"[ERROR] init_ui 出错: {e}")
            import traceback
            traceback.print_exc()
    
    def update_source_menu(self):
        """更新源选择菜单"""
        self.source_menu.clear()
        
        # 所有源选项
        all_action = QAction(self.lang_mgr.get_text("all_sources"), self)
        all_action.triggered.connect(lambda: self.filter_by_source(None))
        self.source_menu.addAction(all_action)
        
        self.source_menu.addSeparator()
        
        # 各个源选项
        for repo in self.repo_manager.repositories:
            if repo.enabled:
                action = QAction(f"{repo.name} ({repo.packages_count})", self)
                action.triggered.connect(lambda checked, r=repo: self.filter_by_source(r))
                self.source_menu.addAction(action)
    
    def filter_by_source(self, repo):
        """按源筛选 - 现在会加载指定源的包"""
        if repo:
            # 选择了特定源
            self.current_repo_filter = repo.name
            self.source_btn.setText(repo.name)
            
            # 清空当前包列表
            self.all_packages.clear()
            self.filtered_packages.clear()
            
            # 加载该源的包
            self.load_repo_packages(repo)
        else:
            # 选择了"所有源" - 加载所有源的包
            self.current_repo_filter = None
            self.source_btn.setText(self.lang_mgr.get_text("all_sources"))
            
            # 加载所有源的包
            self.load_all_packages()
    
    def update_categories(self):
        """动态更新分类标签（基于所有包）"""
        self._update_categories_internal(self.all_packages)
    
    def update_categories_for_filtered_packages(self):
        """动态更新分类标签（基于筛选后的包）"""
        self._update_categories_internal(self.filtered_packages)
    
    def _update_categories_internal(self, packages_list):
        """内部方法：更新分类标签"""
        # 收集所有不同的section
        sections = set()
        for _, package in packages_list:
            if package.section:
                # 提取主分类（有些section可能是 "Tweaks (Themes)" 这种格式）
                section = package.section.split('(')[0].strip()
                if section:
                    sections.add(section)
        
        # 保存当前选中的标签索引
        current_index = self.tabs.currentIndex()
        current_tab_text = self.tabs.tabText(current_index) if current_index >= 0 else ""
        
        # 清除现有的分类标签（除了"全部"）
        while self.tabs.count() > 1:
            self.tabs.removeTab(1)
        
        # 清理list_widgets和list_models中的旧分类
        old_categories = list(self.list_widgets.keys())
        for cat in old_categories:
            if cat != "all":
                del self.list_widgets[cat]
                if cat in self.list_models:
                    del self.list_models[cat]
        
        # 添加新的分类标签
        self.categories = [("all", "all")]
        
        # 对sections排序并创建标签
        for section in sorted(sections):
            # 获取该分类的包数量
            count = sum(1 for _, pkg in packages_list 
                       if pkg.section and section in pkg.section)
            
            if count > 0:  # 只添加有包的分类
                # 尝试获取翻译，如果没有就使用原文
                display_name = section
                section_lower = section.lower()
                
                # 尝试映射到已知的翻译
                if section_lower == "system":
                    display_name = self.lang_mgr.get_text("system")
                elif section_lower == "tweaks":
                    display_name = self.lang_mgr.get_text("tweaks")
                elif section_lower == "utilities":
                    display_name = self.lang_mgr.get_text("utilities")
                elif section_lower == "themes":
                    display_name = self.lang_mgr.get_text("themes")
                elif section_lower == "development":
                    display_name = self.lang_mgr.get_text("development")
                
                # 创建列表控件和模型
                list_widget = QListView()
                list_model = PackageListModel(self)  # 设置父对象
                list_widget.setModel(list_model)
                list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
                # 连接点击事件
                list_widget.clicked.connect(self.on_list_item_clicked)
                
                # 添加到标签页
                tab_text = f"{display_name} ({count})"
                self.tabs.addTab(list_widget, tab_text)
                self.list_widgets[section] = list_widget
                self.list_models[section] = list_model
                self.categories.append((section, section))
        
        # 尝试恢复之前选中的标签
        restored = False
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).split(' (')[0] == current_tab_text.split(' (')[0]:
                self.tabs.setCurrentIndex(i)
                restored = True
                break
        
        # 如果没能恢复，选择第一个标签
        if not restored and self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)
    
    def load_first_repository(self):
        """加载第一个启用的源"""
        # 找到第一个启用的源
        first_repo = None
        for repo in self.repo_manager.repositories:
            if repo.enabled:
                first_repo = repo
                break
        
        if first_repo:
            # 加载第一个源
            self.filter_by_source(first_repo)
        else:
            # 没有启用的源，显示欢迎信息
            self.show_welcome_message()
    
    def show_welcome_message(self):
        """显示欢迎信息"""
        # 清空所有模型
        for model in self.list_models.values():
            model.clear()
        
        # 更新状态栏
        if hasattr(self, 'status_label'):
            self.status_label.setText(self.lang_mgr.get_text("select_source_to_start") if self.lang_mgr else "Select a repository to start")
    
    def show_select_source_message(self):
        """显示选择源的提示信息"""
        self.show_welcome_message()
    
    def load_repo_packages(self, repo):
        """加载单个源的包"""
        try:
            # 显示加载进度
            loading_text = self.lang_mgr.get_text("loading_packages") if self.lang_mgr else "Loading packages..."
            self.status_label.setText(f"{loading_text} ({repo.name})")
            
            # 清空模型数据
            for model in self.list_models.values():
                model.clear()
            
            # 加载包
            success, packages = self.repo_manager.fetch_packages(repo.url)
            if success and packages:
                # 处理包数据
                for package in packages:
                    if package:
                        self.all_packages.append((repo, package))
                
                # 去重处理
                self._deduplicate_packages()
                
                # 排序
                self.all_packages.sort(key=lambda x: x[1].get_display_name().lower() if x[1] and hasattr(x[1], 'get_display_name') else "")
                
                # 设置筛选后的包
                self.filtered_packages = self.all_packages.copy()
                
                # 更新分类和显示
                self.update_categories_for_filtered_packages()
                self.filter_packages()
                
                # 更新状态
                packages_text = self.lang_mgr.get_text("packages") if self.lang_mgr else "packages"
                msg = f"{repo.name} - {len(self.all_packages)} {packages_text}"
                self.status_label.setText(msg)
            else:
                failed_text = self.lang_mgr.get_text("refresh_failed") if self.lang_mgr else "Failed to load"
                self.status_label.setText(f"{failed_text}: {repo.name}")
                
        except Exception as e:
            print(f"[ERROR] 加载源包时出错: {e}")
            error_text = self.lang_mgr.get_text("error") if self.lang_mgr else "Error"
            self.status_label.setText(f"{error_text}: {str(e)}")
    
    def load_all_packages(self):
        """加载所有包"""
        try:
            if self.lang_mgr:
                loading_text = self.lang_mgr.get_text("loading_packages")
            else:
                loading_text = "Loading packages..."
            
            self.status_label.setText(loading_text)
            QTimer.singleShot(100, self._load_packages_async)
        except Exception as e:
            print(f"[ERROR] load_all_packages 出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_packages_async(self):
        """异步加载包"""
        try:
            self.all_packages = []
            
            if not self.repo_manager:
                print("[ERROR] repo_manager 为 None")
                self.status_label.setText("错误: 软件源管理器未初始化")
                return
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            enabled_repos = [repo for repo in self.repo_manager.repositories if repo and repo.enabled]
            total_repos = len(enabled_repos)
            
            if total_repos == 0:
                self.status_label.setText("没有启用的软件源")
                self.progress_bar.setVisible(False)
                return
            
            self.progress_bar.setMaximum(total_repos)
            self.progress_bar.setValue(0)
            
            # 逐个处理软件源，避免界面卡死
            self.current_repo_index = 0
            self.enabled_repos = enabled_repos
            self._load_next_repo()
            
        except Exception as e:
            print(f"[ERROR] _load_packages_async 出现异常: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = f"错误: {str(e)}" if not self.lang_mgr else f"{self.lang_mgr.get_text('error')}: {str(e)}"
            self.status_label.setText(error_msg)
            self.progress_bar.setVisible(False)
    
    def _load_next_repo(self):
        """加载下一个软件源"""
        try:
            if self.current_repo_index >= len(self.enabled_repos):
                # 所有软件源加载完成
                self._finish_initial_loading()
                return
            
            repo = self.enabled_repos[self.current_repo_index]
            loading_text = self.lang_mgr.get_text("loading_packages") if self.lang_mgr else "Loading packages..."
            self.status_label.setText(f"{loading_text} ({repo.name})")
            self.progress_bar.setValue(self.current_repo_index)
            
            # 使用QTimer让界面有机会更新
            QTimer.singleShot(10, lambda: self._process_repo(repo))
            
        except Exception as e:
            print(f"[ERROR] _load_next_repo 出错: {e}")
            self.current_repo_index += 1
            QTimer.singleShot(10, self._load_next_repo)
    
    def _process_repo(self, repo):
        """处理单个软件源"""
        try:
            success, packages = self.repo_manager.fetch_packages(repo.url)
            if success and packages:
                for package in packages:
                    if package:
                        self.all_packages.append((repo, package))
                    else:
                        print(f"[WARNING] 软件源 {repo.name} 中发现空包对象")
        except Exception as repo_error:
            print(f"[ERROR] 处理软件源 {repo.name} 时出错: {repo_error}")
        
        # 继续处理下一个软件源
        self.current_repo_index += 1
        QTimer.singleShot(10, self._load_next_repo)
    
    def _finish_initial_loading(self):
        """完成初始加载"""
        try:
            # 先进行去重处理
            optimizing_text = self.lang_mgr.get_text("optimizing_packages") if self.lang_mgr else "Optimizing package list..."
            self.status_label.setText(optimizing_text)
            self._deduplicate_packages()
            
            # 按包名排序
            sorting_text = self.lang_mgr.get_text("sorting_packages") if self.lang_mgr else "Sorting package list..."
            self.status_label.setText(sorting_text)
            QTimer.singleShot(10, self._sort_and_display)
            
        except Exception as e:
            print(f"[ERROR] _finish_initial_loading 出错: {e}")
            self.progress_bar.setVisible(False)
    
    def _deduplicate_packages(self):
        """去重包列表，只保留每个包的最新版本"""
        print(f"[DEBUG] 去重前包数量: {len(self.all_packages)}")
        
        # 清空版本历史
        self.package_versions.clear()
        
        # 按照 repo_url:package_name 分组
        package_groups = {}
        for repo, package in self.all_packages:
            if not package or not hasattr(package, 'package'):
                continue
                
            key = f"{repo.url}:{package.package}"
            if key not in package_groups:
                package_groups[key] = []
            package_groups[key].append((repo, package))
        
        # 对每组包进行版本比较，只保留最新版本
        deduplicated = []
        for key, versions in package_groups.items():
            if len(versions) == 1:
                # 只有一个版本，直接添加
                deduplicated.append(versions[0])
            else:
                # 多个版本，需要比较
                # 存储所有版本供后续查看
                self.package_versions[key] = versions
                
                # 找出最新版本
                latest = self._find_latest_version(versions)
                deduplicated.append(latest)
                
                # 调试信息
                if len(versions) > 5:  # 超过5个版本的包才输出
                    repo, pkg = latest
                    print(f"[DEBUG] 包 {pkg.package} 有 {len(versions)} 个版本，保留最新版本: {pkg.version}")
        
        original_count = len(self.all_packages)
        self.all_packages = deduplicated
        print(f"[DEBUG] 去重后包数量: {len(self.all_packages)}")
        print(f"[DEBUG] 减少了 {original_count - len(deduplicated)} 个重复包")
    
    def _find_latest_version(self, versions):
        """从版本列表中找出最新版本"""
        # 尝试按版本号排序
        try:
            # 使用版本字符串比较，简单实现
            # TODO: 可以使用更复杂的版本比较库
            sorted_versions = sorted(versions, 
                                   key=lambda x: x[1].version if x[1].version else "0",
                                   reverse=True)
            return sorted_versions[0]
        except:
            # 如果排序失败，返回第一个
            return versions[0]
    
    def _sort_and_display(self):
        """排序并显示包"""
        try:
            # 排序
            self.all_packages.sort(key=lambda x: x[1].get_display_name().lower() if x[1] and hasattr(x[1], 'get_display_name') else "")
            
            # 更新显示
            if self.lang_mgr:
                msg = self.lang_mgr.format_text("total_packages", len(self.all_packages))
            else:
                msg = f"Total {len(self.all_packages)} packages"
            self.status_label.setText(msg)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 更新界面
            self.update_source_menu()
            self.update_categories()
            self.filter_packages()
            
        except Exception as e:
            print(f"[ERROR] _sort_and_display 出错: {e}")
            import traceback
            traceback.print_exc()
            
            error_msg = f"错误: {str(e)}" if not self.lang_mgr else f"{self.lang_mgr.get_text('error')}: {str(e)}"
            self.status_label.setText(error_msg)
            self.progress_bar.setVisible(False)
    
    def filter_packages(self):
        """筛选包"""
        search_text = self.search_input.text().lower()
        
        # 筛选
        self.filtered_packages = []
        for repo, pkg in self.all_packages:
            # 源筛选
            if self.current_repo_filter and repo.name != self.current_repo_filter:
                continue
            
            # 搜索筛选
            if search_text:
                if not (search_text in pkg.package.lower() or
                       search_text in pkg.get_display_name().lower() or
                       search_text in (pkg.description or "").lower()):
                    continue
            
            self.filtered_packages.append((repo, pkg))
        
        # 基于筛选后的包更新分类
        self.update_categories_for_filtered_packages()
        
        # 只更新当前可见的标签页（通常是"All"分类）
        current_tab = self.tabs.currentIndex()
        if current_tab < len(self.categories):
            category = self.categories[current_tab][1] 
            list_widget = self.list_widgets[category]
            self.update_list(list_widget, category)
        elif "all" in self.list_widgets:
            # 确保"All"分类总是更新
            self.update_list(self.list_widgets["all"], "all")
        
        # 更新状态和统计信息
        self.update_statistics()
    
    def update_list(self, list_widget, category):
        """更新列表显示 - 使用模型更新"""
        # 获取对应的模型
        model = self.list_models.get(category)
        if not model:
            return
            
        # 筛选分类
        if category == "all":
            packages = self.filtered_packages
        else:
            packages = [
                (repo, pkg) for repo, pkg in self.filtered_packages
                if pkg and pkg.section and category in pkg.section
            ]
        
        # 设置模型数据
        model.set_packages(packages)
        
        # 更新勾选状态
        model.checked_items = self.checked_items.copy()
    
    def _show_loading_dialog_and_load(self, list_widget, packages, category):
        """使用线程显示加载对话框并加载所有包"""
        # 创建进度对话框
        if self.lang_mgr:
            title = "加载包列表"
            label = f"正在加载 {len(packages)} 个包，请稍候..."
            cancel_text = "取消"
        else:
            title = "Loading Packages"
            label = f"Loading {len(packages)} packages, please wait..."
            cancel_text = "Cancel"
        
        progress_dialog = QProgressDialog(label, cancel_text, 0, len(packages), self)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)  # 立即显示
        progress_dialog.setValue(0)
        
        # 停止之前的加载线程
        if self.load_worker and self.load_worker.isRunning():
            self.load_worker.cancel()
            self.load_worker.wait()
        
        # 创建新的加载线程
        self.load_worker = PackageLoadWorker(packages, self.checked_items)
        
        # 连接信号
        self.load_worker.progress_update.connect(
            lambda current, total, msg: self._update_progress(progress_dialog, current, total, msg)
        )
        self.load_worker.batch_ready.connect(
            lambda batch: self._process_batch(list_widget, batch)
        )
        self.load_worker.finished_loading.connect(
            lambda: self._finish_loading(progress_dialog, list_widget, len(packages))
        )
        
        # 处理取消
        progress_dialog.canceled.connect(lambda: self._cancel_thread_loading(progress_dialog))
        
        # 启动线程
        self.load_worker.start()
    
    def _update_progress(self, progress_dialog, current, total, message):
        """更新进度对话框"""
        progress_dialog.setValue(current)
        progress_dialog.setLabelText(message)
    
    def _process_batch(self, list_widget, batch_data):
        """处理一批数据 - 在主线程中创建UI组件"""
        # 禁用更新以提升性能
        list_widget.setUpdatesEnabled(False)
        
        for data in batch_data:
            # 创建列表项
            item = QListWidgetItem()
            list_widget.addItem(item)
            
            # 创建widget
            widget = PackageListItemWidget()
            widget.set_package_data(data['repo'], data['package'], data['package_key'])
            widget.set_checked(data['is_checked'])
            
            # 连接信号（使用闭包变量避免引用问题）
            package_key = data['package_key']
            repo = data['repo']
            package = data['package']
            widget.checkbox_toggled.connect(
                lambda checked, k=package_key, w=widget: self.on_checkbox_toggled(k, checked, w)
            )
            widget.item_clicked.connect(
                lambda r=repo, p=package: self.on_package_info_clicked(r, p)
            )
            
            # 设置item大小
            item.setSizeHint(widget.sizeHint())
            list_widget.setItemWidget(item, widget)
        
        # 重新启用更新
        list_widget.setUpdatesEnabled(True)
    
    def _finish_loading(self, progress_dialog, list_widget, total_packages):
        """完成加载"""
        progress_dialog.close()
        if hasattr(self, 'status_label'):
            if self.lang_mgr:
                msg = self.lang_mgr.format_text("total_packages", total_packages)
            else:
                msg = f"Total {total_packages} packages"
            self.status_label.setText(msg)
    
    def _cancel_thread_loading(self, progress_dialog):
        """取消线程加载"""
        if self.load_worker:
            self.load_worker.cancel()
        progress_dialog.close()
        if hasattr(self, 'status_label'):
            self.status_label.setText("加载已取消")
    
    def _cancel_loading(self, progress_dialog):
        """取消加载（旧方法）"""
        self.loading_canceled = True
        progress_dialog.close()
        if hasattr(self, 'status_label'):
            self.status_label.setText("加载已取消")
    
    def _load_packages_with_progress(self, list_widget, packages, progress_dialog):
        """带进度的包加载 - 极速优化版"""
        batch_size = 5000  # 每批处理5000个包，极速加载
        current_index = 0
        total_packages = len(packages)
        update_interval = max(500, total_packages // 10)  # 每10%更新一次进度文本
        
        def load_batch():
            nonlocal current_index
            
            if self.loading_canceled or current_index >= total_packages:
                list_widget.setUpdatesEnabled(True)
                progress_dialog.close()
                if not self.loading_canceled:
                    # 加载完成
                    if hasattr(self, 'status_label'):
                        if self.lang_mgr:
                            msg = self.lang_mgr.format_text("total_packages", total_packages)
                        else:
                            msg = f"Total {total_packages} packages"
                        self.status_label.setText(msg)
                return
            
            # 禁用更新以提升性能
            list_widget.setUpdatesEnabled(False)
            
            # 处理当前批次
            end_index = min(current_index + batch_size, total_packages)
            
            # 批量创建widgets
            items_to_add = []
            for i in range(current_index, end_index):
                if self.loading_canceled:
                    break
                repo, package = packages[i]
                if repo and package:
                    item_data = self._create_package_item(repo, package, i)
                    if item_data:
                        items_to_add.append(item_data)
            
            # 批量添加到列表
            for item, widget in items_to_add:
                list_widget.addItem(item)
                list_widget.setItemWidget(item, widget)
            
            # 重新启用更新
            list_widget.setUpdatesEnabled(True)
            
            # 更新进度
            current_index = end_index
            progress_dialog.setValue(current_index)
            
            # 更新进度文本（减少更新频率）
            if current_index % update_interval == 0 or current_index >= total_packages:
                if self.lang_mgr:
                    label = f"正在加载包列表... ({current_index}/{total_packages})"
                else:
                    label = f"Loading packages... ({current_index}/{total_packages})"
                progress_dialog.setLabelText(label)
            
            # 处理事件保持界面响应
            QApplication.processEvents()
            
            # 继续下一批（减少延迟）
            if not self.loading_canceled:
                QTimer.singleShot(1, load_batch)
        
        # 开始加载
        QTimer.singleShot(1, load_batch)
    
    def _load_packages_directly(self, list_widget, packages):
        """直接加载少量包（无对话框）- 优化版"""
        # 禁用更新
        list_widget.setUpdatesEnabled(False)
        
        # 批量创建和添加
        items_to_add = []
        for i, (repo, package) in enumerate(packages):
            item_data = self._create_package_item(repo, package, i)
            if item_data:
                items_to_add.append(item_data)
            
            # 每100个处理一次事件，避免UI冻结
            if i % 100 == 0:
                QApplication.processEvents()
        
        # 批量添加到列表
        for item, widget in items_to_add:
            list_widget.addItem(item)
            list_widget.setItemWidget(item, widget)
        
        # 重新启用更新
        list_widget.setUpdatesEnabled(True)
        
        # 更新状态
        if hasattr(self, 'status_label'):
            if self.lang_mgr:
                msg = self.lang_mgr.format_text("total_packages", len(packages))
            else:
                msg = f"Total {len(packages)} packages"
            self.status_label.setText(msg)
    
    
    def _create_package_item(self, repo, package, index):
        """创建包列表项（优化版，不直接添加到列表）"""
        try:
            if not repo or not package:
                return None
            
            # 创建列表项
            item = QListWidgetItem()
            
            # 创建自定义widget
            widget = PackageListItemWidget()
            
            # 设置包数据
            package_key = f"{repo.url}:{package.package}"
            widget.set_package_data(repo, package, package_key)
            
            # 设置勾选状态
            is_checked = self.checked_items.get(package_key, False)
            widget.set_checked(is_checked)
            
            # 连接信号
            widget.checkbox_toggled.connect(
                lambda checked, key=package_key, w=widget: self.on_checkbox_toggled(key, checked, w)
            )
            widget.item_clicked.connect(
                lambda r=repo, p=package: self.on_package_info_clicked(r, p)
            )
            
            # 设置item大小以适应widget
            item.setSizeHint(widget.sizeHint())
            
            return (item, widget)
            
        except Exception as widget_error:
            print(f"[ERROR] 创建包widget时出错 (索引 {index}): {widget_error}")
            return None
    
    def _add_package_to_list(self, list_widget, repo, package, index):
        """添加单个包到列表（保留原方法用于直接加载）"""
        item_data = self._create_package_item(repo, package, index)
        if item_data:
            item, widget = item_data
            list_widget.addItem(item)
            list_widget.setItemWidget(item, widget)
    
    def on_checkbox_toggled(self, package_key, checked, widget):
        """复选框状态改变时"""
        # 更新勾选状态
        self.checked_items[package_key] = checked
        
        # 更新选中的包列表
        self.update_selected_packages()
    
    def on_model_checkbox_toggled(self, package_key, checked):
        """模型复选框状态改变时"""
        # 更新全局勾选状态
        self.checked_items[package_key] = checked
        
        # 同步到所有模型
        for model in self.list_models.values():
            if package_key in model.checked_items:
                model.checked_items[package_key] = checked
        
        # 更新选中的包列表
        self.update_selected_packages()
    
    def on_list_item_clicked(self, index):
        """列表项点击事件处理"""
        if not index.isValid():
            return
            
        # 获取数据
        model = index.model()
        repo, package = model.data(index, Qt.ItemDataRole.UserRole)
        
        # 如果点击的是复选框区域，切换勾选状态
        check_state = model.data(index, Qt.ItemDataRole.CheckStateRole)
        if check_state == Qt.CheckState.Checked:
            model.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        else:
            model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
            
        # 更新包信息显示
        self.on_package_info_clicked(repo, package)
        
        # 更新选中的包列表
        self.update_selected_packages()
    
    def on_package_info_clicked(self, repo, package):
        """点击包信息时 - 显示详情并高亮选中行"""
        # 获取该包的所有版本
        package_key = f"{repo.url}:{package.package}"
        package_versions = self.package_versions.get(package_key, None)
        
        # 显示包详情
        self.detail_widget.show_package(repo, package, package_versions)
        
        # 高亮当前选中的包
        self.highlight_package_item(repo, package)
    
    def highlight_package_item(self, repo, package):
        """高亮指定的包项"""
        package_key = f"{repo.url}:{package.package}"
        current_tab = self.tabs.currentIndex()
        
        if current_tab < len(self.categories):
            category = self.categories[current_tab][1]
            list_widget = self.list_widgets[category]
            model = self.list_models.get(category)
            
            if model:
                # 清除所有现有选择
                list_widget.clearSelection()
                
                # 找到并高亮对应的item
                for i, (repo, pkg) in enumerate(model.packages):
                    if f"{repo.url}:{pkg.package}" == package_key:
                        index = model.index(i, 0)
                        list_widget.setCurrentIndex(index)
                        list_widget.scrollTo(index)
                        break
    
    
    def on_package_clicked(self, list_widget, item):
        """单击包时 - 此方法现已被替代，但保留以兼容旧代码"""
        pass
    
    def update_selected_packages(self):
        """更新选中的包列表"""
        self.selected_packages = []
        seen_keys = set()  # 用于去重
        
        # 从所有模型中获取勾选的包
        for category, model in self.list_models.items():
            checked = model.get_checked_packages()
            for repo, package in checked:
                package_key = f"{repo.url}:{package.package}"
                if package_key not in seen_keys:
                    seen_keys.add(package_key)
                    self.selected_packages.append((repo, package))
        
        # 更新批量下载按钮状态
        self.batch_download_btn.setEnabled(len(self.selected_packages) > 0)
        if len(self.selected_packages) > 0:
            self.batch_download_btn.setText(f"{self.lang_mgr.get_text('batch_download')} ({len(self.selected_packages)})")
        else:
            self.batch_download_btn.setText(self.lang_mgr.get_text("batch_download"))
        
        # 更新统计信息
        self.update_statistics()
    
    def download_package(self, repo, package):
        """下载包"""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, self.lang_mgr.get_text("warning"), self.lang_mgr.get_text("download_in_progress"))
            return
        
        # 创建下载任务
        from src.workers.download_thread import DownloadWorker
        self.download_worker = DownloadWorker(
            self.repo_manager, repo.url, package, self.download_path
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.status.connect(self.on_download_status)
        self.download_worker.finished.connect(self.on_download_finished)
        
        self.progress_bar.setVisible(True)
        self.download_worker.start()
    
    def on_download_progress(self, percent, downloaded, total):
        """下载进度"""
        self.progress_bar.setValue(percent)
    
    def on_download_status(self, status):
        """下载状态"""
        # 临时显示下载状态
        self.status_label.setText(status)
    
    def on_download_finished(self, success, result):
        """下载完成"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.package_downloaded.emit(result)
            # 使用简单的成功消息
            filename = os.path.basename(result)
            msg = f"下载成功: {filename}" if self.lang_mgr and self.lang_mgr.get_current_language() == "zh" else f"Download successful: {filename}"
            QMessageBox.information(self, 
                                  self.lang_mgr.get_text("success"), 
                                  msg)
        else:
            QMessageBox.warning(self, 
                               self.lang_mgr.get_text("error"), 
                               result)
        
        self.download_worker = None
        
        # 恢复状态显示
        self.filter_packages()
    
    def refresh_packages(self):
        """刷新包列表"""
        if self.current_repo_filter:
            # 刷新当前选中的源
            for repo in self.repo_manager.repositories:
                if repo.name == self.current_repo_filter:
                    # 使用翻译文本
                    refreshing_text = self.lang_mgr.get_text("refreshing_repo") if self.lang_mgr else "Refreshing {0}..."
                    self.status_label.setText(refreshing_text.format(repo.name) if "{0}" in refreshing_text else f"Refreshing {repo.name}...")
                    
                    # 刷新包数据
                    success, packages = self.repo_manager.fetch_packages(repo.url, force_refresh=True)
                    
                    if success:
                        # 加载刷新后的包
                        self.load_repo_packages(repo)
                        # 显示成功提示
                        refresh_complete_text = self.lang_mgr.get_text("refresh_complete") if self.lang_mgr else "Refresh complete"
                        QMessageBox.information(self,
                                              self.lang_mgr.get_text("success"),
                                              f"{refresh_complete_text}: {repo.name} ({len(packages)} {self.lang_mgr.get_text('packages') if self.lang_mgr else 'packages'})")
                    else:
                        # 显示失败提示
                        refresh_failed_text = self.lang_mgr.get_text("refresh_failed") if self.lang_mgr else "Refresh failed"
                        QMessageBox.warning(self,
                                          self.lang_mgr.get_text("error"),
                                          f"{refresh_failed_text}: {repo.name}")
                    break
        else:
            # 刷新所有源
            refresh_all_text = self.lang_mgr.get_text("refresh_all_confirm") if self.lang_mgr else "Refresh all repositories?"
            refresh_all_title = self.lang_mgr.get_text("refresh_all") if self.lang_mgr else "Refresh All"
            
            reply = QMessageBox.question(self, refresh_all_title, refresh_all_text)
            if reply == QMessageBox.StandardButton.Yes:
                # 执行全部刷新
                self.status_label.setText(self.lang_mgr.get_text("refreshing_all") if self.lang_mgr else "Refreshing all repositories...")
                self.load_all_packages()
    
    def open_repo_manager(self):
        """打开源管理器"""
        # 获取主窗口
        main_window = self.parent()
        if hasattr(main_window, 'open_repo_manager'):
            # 使用主窗口的方法来管理窗口
            main_window.open_repo_manager()
        else:
            # 兼容旧的方式
            dialog = RepoManagerDialog(self, self.repo_manager, self.lang_mgr)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 更新源菜单
                self.update_source_menu()
                # 重新加载包
                self.load_all_packages()
    
    def on_search_text_changed(self, text):
        """搜索文本改变时触发"""
        # 停止之前的定时器
        self.search_timer.stop()
        
        # 如果文本为空，立即显示所有包
        if not text.strip():
            self.filter_packages()
        else:
            # 延迟300ms执行搜索，避免频繁搜索
            self.search_timer.start(300)
    
    def perform_search(self):
        """执行搜索（实时搜索）"""
        search_text = self.search_input.text().strip()
        
        # 如果搜索文本为空，显示当前源或所有源的包
        if not search_text:
            self.filter_packages()
            return
        
        # 执行搜索过滤
        self.filter_packages()
    
    def perform_global_search(self):
        """执行全局搜索（搜索所有源）"""
        search_text = self.search_input.text().strip()
        if not search_text:
            return  # 空搜索不提示，直接返回
        
        # 如果当前没有选择特定源，则执行全局搜索
        if not self.current_repo_filter:
            # 已经在所有源中，只需要过滤即可
            self.filter_packages()
            return
        
        # 显示搜索进度对话框
        progress = QProgressDialog(
            f"正在搜索 '{search_text}'..." if self.lang_mgr else f"Searching for '{search_text}'...",
            "取消" if self.lang_mgr else "Cancel",
            0, len(self.repo_manager.repositories),
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        
        # 清空当前列表
        self.all_packages.clear()
        self.filtered_packages.clear()
        
        # 搜索所有启用的源
        found_count = 0
        for i, repo in enumerate(self.repo_manager.repositories):
            if progress.wasCanceled():
                break
                
            progress.setValue(i)
            QApplication.processEvents()
            
            if repo.enabled:
                success, packages = self.repo_manager.fetch_packages(repo.url)
                if success and packages:
                    for package in packages:
                        if package and search_text.lower() in (
                            package.package.lower() + " " + 
                            package.get_display_name().lower() + " " + 
                            (package.description or "").lower()
                        ):
                            self.all_packages.append((repo, package))
                            found_count += 1
        
        progress.close()
        
        # 处理搜索结果
        if found_count > 0:
            # 去重
            self._deduplicate_packages()
            
            # 排序
            self.all_packages.sort(key=lambda x: x[1].get_display_name().lower() if x[1] and hasattr(x[1], 'get_display_name') else "")
            
            # 设置筛选结果
            self.filtered_packages = self.all_packages.copy()
            
            # 更新显示
            self.update_categories_for_filtered_packages()
            self.filter_packages()
            
            # 更新状态
            msg = f"找到 {len(self.all_packages)} 个匹配的包" if self.lang_mgr else f"Found {len(self.all_packages)} matching packages"
            self.status_label.setText(msg)
            
            # 清空源筛选
            self.current_repo_filter = None
            self.source_btn.setText(self.lang_mgr.get_text("all_sources") if self.lang_mgr else "All Sources")
        else:
            # 没有找到结果
            QMessageBox.information(self,
                                  "搜索结果" if self.lang_mgr else "Search Results",
                                  f"未找到包含 '{search_text}' 的包" if self.lang_mgr else f"No packages found containing '{search_text}'")
            self.show_welcome_message()
    
    def update_statistics(self):
        """更新统计信息"""
        # 更新包统计
        total_text = self.lang_mgr.format_text("showing_packages", len(self.filtered_packages))
        self.stats_label.setText(total_text)
        
        # 更新选中统计
        selected_count = len([item for item in self.checked_items.values() if item])
        if selected_count > 0:
            selection_text = self.lang_mgr.format_text("packages_selected", len(self.filtered_packages), selected_count)
            self.selection_stats_label.setText(selection_text)
        else:
            self.selection_stats_label.setText("")
        
        # 更新筛选信息
        filter_parts = []
        if self.current_repo_filter:
            filter_parts.append(self.lang_mgr.format_text('from_source', self.current_repo_filter))
        if self.search_input.text():
            filter_parts.append(f"{self.lang_mgr.get_text('search')}: {self.search_input.text()}")
        
        if filter_parts:
            self.filter_info_label.setText(" | ".join(filter_parts))
        else:
            self.filter_info_label.setText(self.lang_mgr.get_text("all_packages"))
        
        # 更新状态标签
        self.status_label.setText(self.lang_mgr.get_text("ready"))
    
    def open_download_folder(self):
        """打开下载文件夹"""
        if os.path.exists(self.download_path):
            if sys.platform == "win32":
                os.startfile(self.download_path)
            elif sys.platform == "darwin":
                os.system(f"open '{self.download_path}'")
            else:
                os.system(f"xdg-open '{self.download_path}'")
    
    def clear_all_selections(self):
        """清除所有选择"""
        self.checked_items.clear()
        self.selected_packages.clear()
        
        # 清除所有模型的勾选状态
        for model in self.list_models.values():
            model.checked_items.clear()
            # 触发模型更新
            if model.packages:
                model.dataChanged.emit(
                    model.index(0, 0),
                    model.index(len(model.packages) - 1, 0),
                    [Qt.ItemDataRole.CheckStateRole]
                )
        
        # 更新按钮状态
        self.batch_download_btn.setEnabled(False)
        self.batch_download_btn.setText(self.lang_mgr.get_text("batch_download"))
        self.select_all_btn.setText(self.lang_mgr.get_text("select_all"))
        
        # 更新统计信息
        self.update_statistics()
    
    def change_download_path(self):
        """更改下载路径"""
        path = QFileDialog.getExistingDirectory(self, 
                                               self.lang_mgr.get_text("select_download_directory"),
                                               self.download_path)
        if path:
            self.download_path = path
            self.path_label.setText(path)
    
    def toggle_select_all(self):
        """全选或取消全选"""
        # 获取当前标签页的列表和模型
        current_tab = self.tabs.currentIndex()
        current_category = self.categories[current_tab][1]
        model = self.list_models.get(current_category)
        
        if not model or not model.packages:
            return
            
        # 检查是否有未勾选的项
        has_unchecked = False
        for repo, package in model.packages:
            package_key = f"{repo.url}:{package.package}"
            if not model.checked_items.get(package_key, False):
                has_unchecked = True
                break
        
        # 如果有未勾选的，则全选；否则取消全选
        for repo, package in model.packages:
            package_key = f"{repo.url}:{package.package}"
            model.checked_items[package_key] = has_unchecked
            self.checked_items[package_key] = has_unchecked
        
        # 触发模型更新
        model.dataChanged.emit(
            model.index(0, 0),
            model.index(len(model.packages) - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )
        
        # 更新选中的包列表
        self.update_selected_packages()
        
        # 更新按钮文本
        if has_unchecked:
            self.select_all_btn.setText(self.lang_mgr.get_text("deselect_all"))
        else:
            self.select_all_btn.setText(self.lang_mgr.get_text("select_all"))
    
    def batch_download(self):
        """批量下载选中的包"""
        if not self.selected_packages:
            return
        
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, self.lang_mgr.get_text("warning"), self.lang_mgr.get_text("download_in_progress"))
            return
        
        # 确认批量下载
        reply = QMessageBox.question(self, 
                                   self.lang_mgr.get_text("confirm_download"),
                                   self.lang_mgr.format_text("download_packages_question", len(self.selected_packages)),
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 创建批量下载任务
            self.batch_download_queue = list(self.selected_packages)
            self.batch_download_total = len(self.batch_download_queue)
            self.batch_download_current = 0
            self._start_next_download()
    
    def _start_next_download(self):
        """开始下一个下载"""
        if not self.batch_download_queue:
            # 批量下载完成
            QMessageBox.information(self, 
                                  self.lang_mgr.get_text("success"),
                                  self.lang_mgr.format_text("batch_download_complete", self.batch_download_total))
            return
        
        # 取出下一个包
        repo, package = self.batch_download_queue.pop(0)
        self.batch_download_current += 1
        
        # 更新状态
        self.status_label.setText(f"批量下载中 ({self.batch_download_current}/{self.batch_download_total}): {package.get_display_name()}")
        
        # 创建下载任务
        from src.workers.download_thread import DownloadWorker
        self.download_worker = DownloadWorker(
            self.repo_manager, repo.url, package, self.download_path
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.status.connect(self.on_download_status)
        self.download_worker.finished.connect(self._on_batch_download_finished)
        
        self.progress_bar.setVisible(True)
        self.download_worker.start()
    
    def _on_batch_download_finished(self, success, result):
        """批量下载中单个文件完成"""
        if success:
            self.package_downloaded.emit(result)
        
        self.download_worker = None
        
        # 继续下一个
        QTimer.singleShot(100, self._start_next_download)
    
    def eventFilter(self, obj, event):
        """事件过滤器"""
        # 移除了标签栏的鼠标滚轮事件处理
        return super().eventFilter(obj, event)
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        
        # 更新窗口标题
        self.setWindowTitle(lang_mgr.get_text("package_manager"))
        
        # 更新详情组件的语言
        if hasattr(self, 'detail_widget') and self.detail_widget:
            self.detail_widget.update_language(lang_mgr)
        
        # 更新按钮文本
        if hasattr(self, 'manage_sources_btn'):
            self.manage_sources_btn.setText(lang_mgr.get_text("manage_sources"))
        
        # 更新搜索框占位符
        if hasattr(self, 'search_input'):
            self.search_input.setPlaceholderText(lang_mgr.get_text("search_placeholder"))
        
        # 更新源菜单
        if hasattr(self, 'source_menu'):
            self.update_source_menu()
        
        # 更新状态标签
        self.update_statistics()
        
        # 重新加载以更新显示
        if hasattr(self, 'filtered_packages'):
            self.filter_packages()
    
    def on_tab_changed(self, index):
        """标签页切换时"""
        if index < 0 or index >= len(self.categories):
            return
        
        category = self.categories[index][1]
        list_widget = self.list_widgets[category]
        model = self.list_models.get(category)
        
        # 如果该分类还没有显示包，则现在显示
        if model and model.rowCount() == 0 and hasattr(self, 'filtered_packages'):
            self.update_list(list_widget, category)