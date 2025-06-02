# -*- coding: utf-8 -*-
"""
创建时间: 2024-11-22
作者: Evil0ctal

中文介绍:
包浏览器对话框模块，用于浏览软件源中的包。
支持搜索、筛选、批量选择和下载功能。
提供详细的包信息显示和进度跟踪。

英文介绍:
Package browser dialog module for browsing packages in software repositories.
Supports search, filtering, batch selection, and download functionality.
Provides detailed package information display and progress tracking.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLineEdit,
    QComboBox, QLabel, QProgressBar, QCheckBox, QSplitter,
    QTextEdit, QFileDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from typing import List, Tuple
import os
from pathlib import Path
from ..utils.debug_logger import debug


class PackageDetailsWidget(QTextEdit):
    """包详情显示组件"""
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(150)
    
    def show_package(self, package):
        """显示包详情"""
        # 使用更通用的颜色，兼容深色和浅色主题
        html = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    color: palette(text);
                    background-color: transparent;
                }}
                .title {{ 
                    font-size: 16px; 
                    font-weight: bold; 
                    margin-bottom: 5px;
                    color: palette(text);
                }}
                .info {{ 
                    margin: 4px 0;
                    color: palette(text);
                }}
                .label {{ 
                    color: palette(mid);
                    font-weight: 600;
                }}
            </style>
        </head>
        <body>
            <div class="title">{package.get_display_name()} - {package.get_display_version()}</div>
            <div class="info"><span class="label">包名:</span> {package.package}</div>
            <div class="info"><span class="label">作者:</span> {package.get_display_author()}</div>
            <div class="info"><span class="label">大小:</span> {package.get_display_size()}</div>
            <div class="info"><span class="label">分类:</span> {package.section or '未分类'}</div>
            <div class="info"><span class="label">描述:</span> {package.description or '无描述'}</div>
            {f'<div class="info"><span class="label">依赖:</span> {package.depends}</div>' if package.depends else ''}
            {f'<div class="info"><span class="label" style="color: #4CAF50;">✓ Rootless</span></div>' if package.is_rootless_compatible() else ''}
            {f'<div class="info"><span class="label" style="color: #FF9800;">💰 商业插件</span></div>' if package.is_commercial() else ''}
        </body>
        </html>
        """
        self.setHtml(html)


class PackageBrowserDialog(QDialog):
    """包浏览器主对话框"""
    
    # 信号
    package_downloaded = pyqtSignal(str)  # 下载完成的文件路径
    
    def __init__(self, parent=None, repo_manager=None, lang_mgr=None, default_repo=None):
        super().__init__(parent)
        self.repo_manager = repo_manager
        self.lang_mgr = lang_mgr
        self.is_chinese = not lang_mgr or lang_mgr.get_current_language() == 'zh'
        self.default_repo = default_repo
        
        self.setWindowTitle("浏览插件" if self.is_chinese else "Browse Packages")
        self.setModal(False)  # 非模态对话框
        self.resize(1000, 700)
        
        self.current_packages = []  # 当前显示的包列表
        self.selected_packages = []  # 选中要下载的包
        self.download_worker = None
        
        # 默认下载路径
        self.download_path = str(Path.home() / "Downloads" / "SimpleTweakEditor")
        
        self.init_ui()
        self.load_repos()
        
        # 如果有默认源，选择它
        if default_repo:
            self.select_repo(default_repo)
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        # 软件源选择
        toolbar_layout.addWidget(QLabel("软件源:" if self.is_chinese else "Source:"))
        self.repo_combo = QComboBox()
        self.repo_combo.setMinimumWidth(200)
        self.repo_combo.currentIndexChanged.connect(self.on_repo_changed)
        toolbar_layout.addWidget(self.repo_combo)
        
        # 管理源按钮
        self.manage_repos_btn = QPushButton("管理源" if self.is_chinese else "Manage")
        self.manage_repos_btn.clicked.connect(self.open_repo_manager)
        toolbar_layout.addWidget(self.manage_repos_btn)
        
        # 分隔符
        toolbar_layout.addWidget(QLabel(" | "))
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索包名、描述..." if self.is_chinese else "Search packages...")
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        toolbar_layout.addWidget(self.search_input)
        
        # 分类筛选
        toolbar_layout.addWidget(QLabel("分类:" if self.is_chinese else "Section:"))
        self.section_combo = QComboBox()
        self.section_combo.addItem("全部" if self.is_chinese else "All")
        self.section_combo.currentIndexChanged.connect(self.on_filter_changed)
        toolbar_layout.addWidget(self.section_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新" if self.is_chinese else "Refresh")
        self.refresh_btn.clicked.connect(self.refresh_current_repo)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addStretch()
        
        # 下载路径
        toolbar_layout.addWidget(QLabel("下载到:" if self.is_chinese else "Download to:"))
        self.path_label = QLabel(self.download_path)
        self.path_label.setMaximumWidth(200)
        toolbar_layout.addWidget(self.path_label)
        self.browse_btn = QPushButton("浏览" if self.is_chinese else "Browse")
        self.browse_btn.clicked.connect(self.browse_download_path)
        toolbar_layout.addWidget(self.browse_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 主内容区域 - 使用分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 包列表
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        headers = ["选择", "名称", "版本", "作者", "大小", "分类", "描述"] if self.is_chinese else \
                 ["Select", "Name", "Version", "Author", "Size", "Section", "Description"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        
        # 选择行为
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        
        splitter.addWidget(self.table)
        
        # 包详情
        self.details_widget = PackageDetailsWidget()
        splitter.addWidget(self.details_widget)
        
        # 设置分割比例
        splitter.setSizes([500, 150])
        
        layout.addWidget(splitter)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 底部状态栏和按钮
        bottom_layout = QHBoxLayout()
        
        # 状态信息
        self.status_label = QLabel("")
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        # 全选/取消全选
        self.select_all_btn = QPushButton("全选" if self.is_chinese else "Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        bottom_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("取消全选" if self.is_chinese else "Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        bottom_layout.addWidget(self.deselect_all_btn)
        
        # 下载按钮
        self.download_btn = QPushButton("下载选中" if self.is_chinese else "Download Selected")
        self.download_btn.clicked.connect(self.download_selected)
        self.download_btn.setEnabled(False)
        bottom_layout.addWidget(self.download_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭" if self.is_chinese else "Close")
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def load_repos(self):
        """加载软件源列表到下拉框"""
        self.repo_combo.clear()
        self.repo_combo.addItem("所有软件源" if self.is_chinese else "All Sources", None)
        
        for repo in self.repo_manager.repositories:
            if repo.enabled:
                display_text = f"{repo.name} ({repo.packages_count} 个包)" if self.is_chinese else \
                              f"{repo.name} ({repo.packages_count} packages)"
                self.repo_combo.addItem(display_text, repo.url)
    
    def select_repo(self, repo_url: str):
        """选择指定的软件源"""
        for i in range(self.repo_combo.count()):
            if self.repo_combo.itemData(i) == repo_url:
                self.repo_combo.setCurrentIndex(i)
                break
    
    def on_repo_changed(self):
        """软件源选择改变"""
        self.load_packages()
    
    def on_search_changed(self):
        """搜索内容改变"""
        self.filter_packages()
    
    def on_filter_changed(self):
        """筛选条件改变"""
        self.filter_packages()
    
    def on_selection_changed(self):
        """选择改变时更新详情"""
        current_row = self.table.currentRow()
        if 0 <= current_row < len(self.current_packages):
            _, package = self.current_packages[current_row]
            self.details_widget.show_package(package)
    
    def load_packages(self):
        """加载包列表"""
        repo_url = self.repo_combo.currentData()
        
        self.current_packages = []
        self.table.setRowCount(0)
        self.section_combo.clear()
        self.section_combo.addItem("全部" if self.is_chinese else "All")
        
        sections = set()
        
        if repo_url:
            # 加载单个源的包
            success, packages = self.repo_manager.fetch_packages(repo_url)
            if success:
                repo = self.repo_manager.get_repository(repo_url)
                for package in packages:
                    self.current_packages.append((repo, package))
                    if package.section:
                        sections.add(package.section)
        else:
            # 加载所有源的包
            self.current_packages = self.repo_manager.get_all_packages()
            for _, package in self.current_packages:
                if package.section:
                    sections.add(package.section)
        
        # 添加分类到下拉框
        for section in sorted(sections):
            self.section_combo.addItem(section)
        
        # 显示包
        self.display_packages(self.current_packages)
        
        # 更新状态
        self.update_status()
    
    def filter_packages(self):
        """筛选包"""
        search_text = self.search_input.text().lower()
        selected_section = self.section_combo.currentText()
        
        filtered = []
        for repo, package in self.current_packages:
            # 搜索筛选
            if search_text:
                if not (search_text in package.package.lower() or
                       search_text in package.name.lower() or
                       search_text in package.description.lower()):
                    continue
            
            # 分类筛选
            if selected_section and selected_section not in ["全部", "All"]:
                if package.section != selected_section:
                    continue
            
            filtered.append((repo, package))
        
        self.display_packages(filtered)
    
    def display_packages(self, packages: List[Tuple]):
        """显示包列表"""
        self.table.setRowCount(0)
        
        for repo, package in packages:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_download_button)
            self.table.setCellWidget(row, 0, checkbox)
            
            # 包信息
            self.table.setItem(row, 1, QTableWidgetItem(package.get_display_name()))
            self.table.setItem(row, 2, QTableWidgetItem(package.get_display_version()))
            self.table.setItem(row, 3, QTableWidgetItem(package.get_display_author()))
            self.table.setItem(row, 4, QTableWidgetItem(package.get_display_size()))
            self.table.setItem(row, 5, QTableWidgetItem(package.section or ""))
            self.table.setItem(row, 6, QTableWidgetItem(package.description or ""))
            
            # 存储包数据
            self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, (repo, package))
        
        self.update_status()
    
    def update_status(self):
        """更新状态栏"""
        total = self.table.rowCount()
        selected = len(self.get_selected_packages())
        
        if selected > 0:
            status = f"共 {total} 个包，已选择 {selected} 个" if self.is_chinese else \
                    f"Total {total} packages, {selected} selected"
        else:
            status = f"共 {total} 个包" if self.is_chinese else f"Total {total} packages"
        
        self.status_label.setText(status)
    
    def update_download_button(self):
        """更新下载按钮状态"""
        selected = self.get_selected_packages()
        self.download_btn.setEnabled(len(selected) > 0)
        self.update_status()
    
    def get_selected_packages(self) -> List[Tuple]:
        """获取选中的包"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                item = self.table.item(row, 1)
                if item:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if data:
                        selected.append(data)
        return selected
    
    def select_all(self):
        """全选"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def deselect_all(self):
        """取消全选"""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def browse_download_path(self):
        """选择下载路径"""
        path = QFileDialog.getExistingDirectory(self, 
                                               "选择下载目录" if self.is_chinese else "Select Download Directory",
                                               self.download_path)
        if path:
            self.download_path = path
            self.path_label.setText(path)
            self.path_label.setToolTip(path)
    
    def download_selected(self):
        """下载选中的包"""
        selected = self.get_selected_packages()
        if not selected:
            return
        
        # 确认下载
        reply = QMessageBox.question(self,
                                   "确认下载" if self.is_chinese else "Confirm Download",
                                   f"确定要下载 {len(selected)} 个插件吗？" if self.is_chinese else
                                   f"Download {len(selected)} packages?")
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始下载
        self.start_download(selected)
    
    def start_download(self, packages: List[Tuple]):
        """开始下载任务"""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "警告" if self.is_chinese else "Warning",
                              "正在下载中，请稍候" if self.is_chinese else "Download in progress")
            return
        
        # 禁用界面
        self.download_btn.setEnabled(False)
        self.table.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # 创建下载任务
        from src.workers.download_thread import BatchDownloadWorker
        self.download_worker = BatchDownloadWorker(self.repo_manager, packages, self.download_path, self.lang_mgr)
        self.download_worker.package_started.connect(self.on_package_started)
        self.download_worker.package_progress.connect(self.on_package_progress)
        self.download_worker.package_finished.connect(self.on_package_finished)
        self.download_worker.all_finished.connect(self.on_all_finished)
        self.download_worker.start()
    
    def on_package_started(self, name: str, current: int, total: int):
        """包开始下载"""
        self.status_label.setText(f"正在下载 {name} ({current}/{total})..." if self.is_chinese else
                                 f"Downloading {name} ({current}/{total})...")
    
    def on_package_progress(self, name: str, progress: int):
        """包下载进度"""
        self.progress_bar.setValue(progress)
    
    def on_package_finished(self, name: str, success: bool, result: str):
        """包下载完成"""
        if success:
            debug(f"Downloaded {name} to {result}")
            self.package_downloaded.emit(result)
        else:
            print(f"[ERROR] Failed to download {name}: {result}")
    
    def on_all_finished(self, success_count: int, failed_count: int):
        """所有下载完成"""
        self.download_btn.setEnabled(True)
        self.table.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        msg = f"下载完成！成功: {success_count}, 失败: {failed_count}" if self.is_chinese else \
              f"Download complete! Success: {success_count}, Failed: {failed_count}"
        
        QMessageBox.information(self, "完成" if self.is_chinese else "Complete", msg)
        
        # 清除选择
        self.deselect_all()
        self.download_worker = None
    
    def refresh_current_repo(self):
        """刷新当前软件源"""
        repo_url = self.repo_combo.currentData()
        if not repo_url:
            # 刷新所有源
            from src.ui.repo_manager_dialog import RepoManagerDialog
            dialog = RepoManagerDialog(self, self.repo_manager, self.lang_mgr)
            dialog.refresh_all_repos()
            dialog.exec()
        else:
            # 刷新单个源
            self.repo_manager.fetch_packages(repo_url, force_refresh=True)
        
        # 重新加载
        self.load_repos()
        self.load_packages()
    
    def open_repo_manager(self):
        """打开软件源管理器"""
        from src.ui.repo_manager_dialog import RepoManagerDialog
        dialog = RepoManagerDialog(self, self.repo_manager, self.lang_mgr)
        dialog.repo_selected.connect(self.select_repo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 重新加载源列表
            self.load_repos()
            self.load_packages()
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        self.is_chinese = not lang_mgr or lang_mgr.get_current_language() == 'zh'
        
        # 重新初始化UI以更新所有文本
        self.setupUI()