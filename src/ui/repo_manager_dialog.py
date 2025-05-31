# -*- coding: utf-8 -*-
"""
创建时间: 2024-11-22
作者: Evil0ctal

中文介绍:
软件源管理器对话框模块，提供软件源管理功能。
支持添加、编辑、删除软件源，以及批量导入导出。
实现了软件源刷新、启用/禁用和双击浏览等功能。

英文介绍:
Repository manager dialog module providing software repository management functionality.
Supports adding, editing, deleting repositories, as well as batch import/export.
Implements repository refresh, enable/disable, and double-click browsing features.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog,
    QCheckBox, QLabel, QProgressBar, QDialogButtonBox,
    QLineEdit, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from typing import Optional, List
import os


class AddRepoDialog(QDialog):
    """添加软件源对话框"""
    
    def __init__(self, parent=None, lang_mgr=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.setWindowTitle(self.lang_mgr.get_text("add_repository") if lang_mgr else "Add Repository")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel(f"{self.lang_mgr.get_text('name') if self.lang_mgr else 'Name'}:")
        name_label.setFixedWidth(80)
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # URL输入
        url_layout = QHBoxLayout()
        url_label = QLabel(f"{self.lang_mgr.get_text('url') if self.lang_mgr else 'URL'}:")
        url_label.setFixedWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/repo/")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 描述输入（可选）
        desc_layout = QHBoxLayout()
        desc_label = QLabel(f"{self.lang_mgr.get_text('description') if self.lang_mgr else 'Description'}:")
        desc_label.setFixedWidth(80)
        self.desc_input = QLineEdit()
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_repo_info(self):
        """获取输入的源信息"""
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'description': self.desc_input.text().strip()
        }


class EditRepoDialog(QDialog):
    """编辑软件源对话框"""
    
    def __init__(self, parent=None, lang_mgr=None, repo=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.repo = repo
        self.setWindowTitle(self.lang_mgr.get_text("edit_repository") if lang_mgr else "Edit Repository")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.init_ui()
        
        # 填充现有数据
        if repo:
            self.name_input.setText(repo.name)
            self.url_input.setText(repo.url)
            self.desc_input.setText(repo.description or "")
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 名称输入
        name_layout = QHBoxLayout()
        name_label = QLabel(f"{self.lang_mgr.get_text('name') if self.lang_mgr else 'Name'}:")
        name_label.setFixedWidth(80)
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # URL输入
        url_layout = QHBoxLayout()
        url_label = QLabel(f"{self.lang_mgr.get_text('url') if self.lang_mgr else 'URL'}:")
        url_label.setFixedWidth(80)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/repo/")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 描述输入
        desc_layout = QHBoxLayout()
        desc_label = QLabel(f"{self.lang_mgr.get_text('description') if self.lang_mgr else 'Description'}:")
        desc_label.setFixedWidth(80)
        self.desc_input = QLineEdit()
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_data(self):
        """获取编辑数据"""
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'description': self.desc_input.text().strip()
        }


class BatchImportDialog(QDialog):
    """批量导入软件源对话框"""
    
    def __init__(self, parent=None, lang_mgr=None):
        super().__init__(parent)
        self.lang_mgr = lang_mgr
        self.setWindowTitle(self.lang_mgr.get_text("batch_import_repos") if lang_mgr else "Batch Import Repositories")
        self.setModal(True)
        self.resize(600, 400)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 说明文本
        info_label = QLabel(self.lang_mgr.get_text("batch_import_info") if self.lang_mgr else 
                           "Enter repository URLs, one per line. Format: Name|URL|Description (optional)")
        layout.addWidget(info_label)
        
        # 文本编辑器
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("BigBoss|http://apt.thebigboss.org/repofiles/cydia/|The biggest repository\n"
                                         "Chariz|https://repo.chariz.com/|Premium tweaks")
        layout.addWidget(self.text_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 导入文件按钮
        import_file_btn = QPushButton(self.lang_mgr.get_text("import_from_file") if self.lang_mgr else "Import from File")
        import_file_btn.clicked.connect(self.import_from_file)
        button_layout.addWidget(import_file_btn)
        
        button_layout.addStretch()
        
        # 确定/取消按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def import_from_file(self):
        """从文件导入"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.lang_mgr.get_text("select_repo_file") if self.lang_mgr else "Select Repository File",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_edit.setPlainText(content)
            except Exception as e:
                QMessageBox.warning(self, 
                                  self.lang_mgr.get_text("error") if self.lang_mgr else "Error",
                                  str(e))
    
    def get_repositories(self) -> List[dict]:
        """解析并返回软件源列表"""
        repos = []
        content = self.text_edit.toPlainText()
        
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过空行和注释
                continue
            
            parts = line.split('|')
            if len(parts) >= 2:
                repo = {
                    'name': parts[0].strip(),
                    'url': parts[1].strip(),
                    'description': parts[2].strip() if len(parts) > 2 else ''
                }
                if repo['name'] and repo['url']:
                    repos.append(repo)
        
        return repos


class RepoManagerDialog(QDialog):
    """软件源管理器主对话框"""
    
    # 信号
    repo_selected = pyqtSignal(str)  # 选中软件源URL
    
    def __init__(self, parent=None, repo_manager=None, lang_mgr=None):
        super().__init__(parent)
        self.repo_manager = repo_manager
        self.lang_mgr = lang_mgr
        self.setWindowTitle(self.lang_mgr.get_text("repo_manager") if lang_mgr else "Repository Manager")
        self.setModal(False)  # 改为非模态，允许与其他窗口交互
        self.resize(900, 600)
        
        self.refresh_worker = None
        self.init_ui()
        self.load_repos()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_btn = QPushButton(self.lang_mgr.get_text("add_source") if self.lang_mgr else "Add Source")
        self.add_btn.clicked.connect(self.add_repo)
        toolbar_layout.addWidget(self.add_btn)
        
        self.batch_import_btn = QPushButton(self.lang_mgr.get_text("batch_import") if self.lang_mgr else "Batch Import")
        self.batch_import_btn.clicked.connect(self.batch_import_repos)
        toolbar_layout.addWidget(self.batch_import_btn)
        
        self.batch_export_btn = QPushButton(self.lang_mgr.get_text("batch_export") if self.lang_mgr else "Batch Export")
        self.batch_export_btn.clicked.connect(self.batch_export_repos)
        toolbar_layout.addWidget(self.batch_export_btn)
        
        self.edit_btn = QPushButton(self.lang_mgr.get_text("edit") if self.lang_mgr else "Edit")
        self.edit_btn.clicked.connect(self.edit_repo)
        self.edit_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_btn)
        
        self.remove_btn = QPushButton(self.lang_mgr.get_text("remove") if self.lang_mgr else "Remove")
        self.remove_btn.clicked.connect(self.remove_repo)
        self.remove_btn.setEnabled(False)
        toolbar_layout.addWidget(self.remove_btn)
        
        toolbar_layout.addSpacing(20)
        
        self.refresh_btn = QPushButton(self.lang_mgr.get_text("refresh") if self.lang_mgr else "Refresh")
        self.refresh_btn.clicked.connect(self.refresh_repos)
        toolbar_layout.addWidget(self.refresh_btn)
        
        self.refresh_all_btn = QPushButton(self.lang_mgr.get_text("refresh_all") if self.lang_mgr else "Refresh All")
        self.refresh_all_btn.clicked.connect(self.refresh_all_repos)
        toolbar_layout.addWidget(self.refresh_all_btn)
        
        toolbar_layout.addSpacing(20)
        
        self.enable_all_btn = QPushButton(self.lang_mgr.get_text("enable_all") if self.lang_mgr else "Enable All")
        self.enable_all_btn.clicked.connect(self.enable_all_repos)
        toolbar_layout.addWidget(self.enable_all_btn)
        
        self.disable_all_btn = QPushButton(self.lang_mgr.get_text("disable_all") if self.lang_mgr else "Disable All")
        self.disable_all_btn.clicked.connect(self.disable_all_repos)
        toolbar_layout.addWidget(self.disable_all_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # 软件源列表
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        headers = [
            self.lang_mgr.get_text("enable") if self.lang_mgr else "Enable",
            self.lang_mgr.get_text("name") if self.lang_mgr else "Name",
            self.lang_mgr.get_text("url") if self.lang_mgr else "URL",
            self.lang_mgr.get_text("packages") if self.lang_mgr else "Packages",
            self.lang_mgr.get_text("last_update") if self.lang_mgr else "Last Update",
            self.lang_mgr.get_text("description") if self.lang_mgr else "Description"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50)
        
        # 选择行为
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)  # 允许多选
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 禁止编辑
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.cellDoubleClicked.connect(self.on_double_click)
        
        layout.addWidget(self.table)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # 底部说明文本
        info_label = QLabel(self.lang_mgr.get_text("repo_manager_info") if self.lang_mgr else 
                           "Double-click a repository to browse its packages")
        info_label.setProperty("class", "secondary")
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def update_language(self, lang_mgr):
        """更新语言"""
        self.lang_mgr = lang_mgr
        
        # 更新窗口标题
        self.setWindowTitle(lang_mgr.get_text("manage_sources") if lang_mgr else "Repository Manager")
        
        # 更新表格头
        headers = [
            lang_mgr.get_text("enabled") if lang_mgr else "Enabled",
            lang_mgr.get_text("name") if lang_mgr else "Name", 
            lang_mgr.get_text("url") if lang_mgr else "URL",
            lang_mgr.get_text("package_count") if lang_mgr else "Packages",
            lang_mgr.get_text("last_update") if lang_mgr else "Last Update"
        ]
        self.table.setHorizontalHeaderLabels(headers)
        
        # 更新按钮文本
        self.add_btn.setText(lang_mgr.get_text("add") if lang_mgr else "Add")
        self.edit_btn.setText(lang_mgr.get_text("edit") if lang_mgr else "Edit")
        self.remove_btn.setText(lang_mgr.get_text("remove") if lang_mgr else "Remove")
        self.refresh_btn.setText(lang_mgr.get_text("refresh") if lang_mgr else "Refresh")
        self.batch_export_btn.setText(lang_mgr.get_text("batch_export") if lang_mgr else "Batch Export")
        self.batch_import_btn.setText(lang_mgr.get_text("batch_import") if lang_mgr else "Batch Import")
        
        # 更新说明文本
        info_label = self.findChild(QLabel)
        if info_label:
            info_label.setText(lang_mgr.get_text("repo_manager_info") if lang_mgr else 
                             "Double-click a repository to browse its packages")
    
    def load_repos(self):
        """加载软件源列表"""
        self.table.setRowCount(0)
        
        for repo in self.repo_manager.repositories:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # 启用复选框
            checkbox = QCheckBox()
            checkbox.setChecked(repo.enabled)
            checkbox.stateChanged.connect(lambda state, url=repo.url: 
                                        self.toggle_repo(url, state == Qt.CheckState.Checked.value))
            self.table.setCellWidget(row, 0, checkbox)
            
            # 其他信息
            self.table.setItem(row, 1, QTableWidgetItem(repo.name))
            self.table.setItem(row, 2, QTableWidgetItem(repo.url))
            self.table.setItem(row, 3, QTableWidgetItem(str(repo.packages_count)))
            last_update_text = repo.last_updated or (self.lang_mgr.get_text("not_refreshed") if self.lang_mgr else "Not refreshed")
            self.table.setItem(row, 4, QTableWidgetItem(last_update_text))
            self.table.setItem(row, 5, QTableWidgetItem(repo.description or ""))
        
        status_text = self.lang_mgr.format_text("total_repos", len(self.repo_manager.repositories)) if self.lang_mgr else \
                     f"Total {len(self.repo_manager.repositories)} repositories"
        self.status_label.setText(status_text)
    
    def on_selection_changed(self):
        """选择改变时"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        has_selection = len(selected_rows) > 0
        single_selection = len(selected_rows) == 1
        
        # 编辑按钮只在单选时启用
        self.edit_btn.setEnabled(single_selection)
        # 删除按钮在有选择时都启用
        self.remove_btn.setEnabled(has_selection)
    
    def on_double_click(self, row, col):
        """双击时触发 - 打开该软件源的包浏览器"""
        print(f"[DEBUG] on_double_click called: row={row}, col={col}")
        
        repo_url = self.get_selected_repo_url()
        print(f"[DEBUG] Selected repo URL: {repo_url}")
        if not repo_url:
            print("[DEBUG] No repo URL selected, returning")
            return
        
        repo = self.repo_manager.get_repository(repo_url)
        print(f"[DEBUG] Repository object: {repo}")
        if not repo:
            print("[DEBUG] Repository not found, returning")
            return
        
        # 检查软件源是否启用
        print(f"[DEBUG] Repository enabled: {repo.enabled}")
        if not repo.enabled:
            print("[DEBUG] Repository is disabled, showing warning")
            QMessageBox.warning(self, 
                              self.lang_mgr.get_text("warning") if self.lang_mgr else "Warning",
                              self.lang_mgr.get_text("repo_disabled") if self.lang_mgr else "Repository is disabled")
            return
        
        # 打开包管理器并筛选该软件源
        try:
            print("[DEBUG] Checking for main window...")
            # 获取主窗口
            main_window = self.parent()
            if hasattr(main_window, 'open_package_manager') and hasattr(main_window, 'dialogs'):
                print("[DEBUG] Using main window's package manager...")
                # 使用主窗口的包管理器
                main_window.open_package_manager()
                
                # 设置筛选
                if main_window.dialogs['package_manager'] and hasattr(main_window.dialogs['package_manager'], 'set_source_filter'):
                    print(f"[DEBUG] Setting source filter to: {repo.name}")
                    main_window.dialogs['package_manager'].set_source_filter(repo.name)
            else:
                print("[DEBUG] Fallback to creating new dialog...")
                # 兼容旧的方式
                from src.ui.package_manager_widget import PackageManagerWidget
                
                dialog = PackageManagerWidget(self, self.repo_manager, self.lang_mgr)
                
                if hasattr(dialog, 'set_source_filter'):
                    dialog.set_source_filter(repo.name)
                
                dialog.exec()
        except Exception as e:
            print(f"[DEBUG] ERROR in on_double_click: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 
                               self.lang_mgr.get_text("error") if self.lang_mgr else "Error",
                               str(e))
    
    def get_selected_repo_url(self) -> Optional[str]:
        """获取选中的源URL"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            return self.table.item(current_row, 2).text()
        return None
    
    def add_repo(self):
        """添加软件源"""
        dialog = AddRepoDialog(self, self.lang_mgr)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            info = dialog.get_repo_info()
            if not info['name'] or not info['url']:
                QMessageBox.warning(self, 
                                  self.lang_mgr.get_text("warning") if self.lang_mgr else "Warning",
                                  self.lang_mgr.get_text("fill_name_url") if self.lang_mgr else "Please enter name and URL")
                return
            
            if self.repo_manager.add_repository(info['name'], info['url'], 
                                              description=info.get('description')):
                self.load_repos()
                QMessageBox.information(self, 
                                      self.lang_mgr.get_text("success") if self.lang_mgr else "Success",
                                      self.lang_mgr.get_text("repository_added") if self.lang_mgr else "Repository added successfully")
            else:
                QMessageBox.warning(self, 
                                  self.lang_mgr.get_text("error") if self.lang_mgr else "Error",
                                  self.lang_mgr.get_text("repository_exists") if self.lang_mgr else "Repository already exists")
    
    def batch_import_repos(self):
        """批量导入软件源"""
        dialog = BatchImportDialog(self, self.lang_mgr)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            repos = dialog.get_repositories()
            if not repos:
                QMessageBox.warning(self,
                                  self.lang_mgr.get_text("warning") if self.lang_mgr else "Warning",
                                  self.lang_mgr.get_text("no_repos_to_import") if self.lang_mgr else "No repositories to import")
                return
            
            success_count = 0
            failed_count = 0
            
            for repo in repos:
                if self.repo_manager.add_repository(repo['name'], repo['url'], 
                                                  description=repo.get('description')):
                    success_count += 1
                else:
                    failed_count += 1
            
            self.load_repos()
            
            message = self.lang_mgr.format_text("batch_import_result", success_count, failed_count) if self.lang_mgr else \
                     f"Import complete! Success: {success_count}, Failed: {failed_count}"
            
            QMessageBox.information(self,
                                  self.lang_mgr.get_text("info") if self.lang_mgr else "Information",
                                  message)
    
    def batch_export_repos(self):
        """批量导出软件源"""
        # 选择保存文件
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.lang_mgr.get_text("select_export_file") if self.lang_mgr else "Select Export File",
            "repositories.txt",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            # 收集所有启用的软件源
            export_lines = []
            for repo in self.repo_manager.repositories:
                if repo.enabled:
                    # 格式: Name|URL|Description
                    line = f"{repo.name}|{repo.url}"
                    if repo.description:
                        line += f"|{repo.description}"
                    export_lines.append(line)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(export_lines))
            
            QMessageBox.information(
                self,
                self.lang_mgr.get_text("success") if self.lang_mgr else "Success",
                self.lang_mgr.format_text("export_success", len(export_lines)) if self.lang_mgr else 
                f"Successfully exported {len(export_lines)} repositories"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                self.lang_mgr.get_text("error") if self.lang_mgr else "Error",
                str(e)
            )
    
    def edit_repo(self):
        """编辑软件源"""
        repo_url = self.get_selected_repo_url()
        if not repo_url:
            return
        
        repo = self.repo_manager.get_repository(repo_url)
        if not repo:
            return
        
        # 使用新的编辑对话框
        dialog = EditRepoDialog(self, self.lang_mgr, repo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data['name'] and data['url']:
                # 如果URL改变了，需要先删除旧的，再添加新的
                if data['url'] != repo_url:
                    # 删除旧的
                    self.repo_manager.remove_repository(repo_url)
                    # 添加新的
                    self.repo_manager.add_repository(
                        data['name'], 
                        data['url'], 
                        description=data['description'],
                        enabled=repo.enabled
                    )
                else:
                    # URL没变，只更新其他信息
                    self.repo_manager.update_repository(
                        repo_url, 
                        name=data['name'],
                        description=data['description']
                    )
                self.load_repos()
    
    def remove_repo(self):
        """删除软件源（支持批量删除）"""
        # 获取所有选中的行
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        # 收集要删除的软件源信息
        repos_to_remove = []
        for row in selected_rows:
            url_item = self.table.item(row, 2)
            if url_item:
                repo_url = url_item.text()
                repo = self.repo_manager.get_repository(repo_url)
                if repo:
                    repos_to_remove.append((repo_url, repo.name))
        
        if not repos_to_remove:
            return
        
        # 确认消息
        if len(repos_to_remove) == 1:
            message = self.lang_mgr.format_text("delete_repo_question", repos_to_remove[0][1]) if self.lang_mgr else \
                     f"Are you sure you want to delete repository '{repos_to_remove[0][1]}'?"
        else:
            message = self.lang_mgr.format_text("delete_repos_question", len(repos_to_remove)) if self.lang_mgr else \
                     f"Are you sure you want to delete {len(repos_to_remove)} repositories?"
        
        reply = QMessageBox.question(self, 
                                   self.lang_mgr.get_text("confirm_delete") if self.lang_mgr else "Confirm Delete",
                                   message)
        
        if reply == QMessageBox.StandardButton.Yes:
            # 批量删除
            success_count = 0
            for repo_url, repo_name in repos_to_remove:
                if self.repo_manager.remove_repository(repo_url):
                    success_count += 1
            
            self.load_repos()
            
            if len(repos_to_remove) == 1:
                QMessageBox.information(self, 
                                      self.lang_mgr.get_text("success") if self.lang_mgr else "Success",
                                      self.lang_mgr.get_text("repository_removed") if self.lang_mgr else "Repository removed")
            else:
                message = self.lang_mgr.format_text("repositories_removed", success_count) if self.lang_mgr else \
                         f"{success_count} repositories removed"
                QMessageBox.information(self, 
                                      self.lang_mgr.get_text("success") if self.lang_mgr else "Success",
                                      message)
    
    def toggle_repo(self, repo_url: str, enabled: bool):
        """切换软件源启用状态"""
        self.repo_manager.update_repository(repo_url, enabled=enabled)
        print(f"[DEBUG] Repository {repo_url} enabled: {enabled}")
    
    def refresh_repos(self):
        """刷新选中的软件源"""
        repo_url = self.get_selected_repo_url()
        if not repo_url:
            return
        
        self._start_refresh([repo_url])
    
    def refresh_all_repos(self):
        """刷新所有软件源"""
        self._start_refresh(None)
    
    def _start_refresh(self, repos_to_refresh):
        """开始刷新任务"""
        if self.refresh_worker and self.refresh_worker.isRunning():
            QMessageBox.warning(self, 
                              self.lang_mgr.get_text("warning") if self.lang_mgr else "Warning",
                              self.lang_mgr.get_text("refresh_in_progress") if self.lang_mgr else "Refresh in progress, please wait")
            return
        
        # 禁用按钮
        self.refresh_btn.setEnabled(False)
        self.refresh_all_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # 导入并创建工作线程
        from src.workers.download_thread import RepoRefreshWorker
        self.refresh_worker = RepoRefreshWorker(self.repo_manager, repos_to_refresh)
        self.refresh_worker.status.connect(self.on_refresh_status)
        self.refresh_worker.finished.connect(self.on_refresh_finished)
        self.refresh_worker.start()
    
    def on_refresh_status(self, msg: str, current: int, total: int):
        """刷新状态更新"""
        self.status_label.setText(msg)
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
    
    def on_refresh_finished(self, success: bool, msg: str):
        """刷新完成"""
        self.refresh_btn.setEnabled(True)
        self.refresh_all_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.load_repos()
            QMessageBox.information(self, 
                                  self.lang_mgr.get_text("success") if self.lang_mgr else "Success", 
                                  msg)
        else:
            QMessageBox.warning(self, 
                               self.lang_mgr.get_text("error") if self.lang_mgr else "Error", 
                               msg)
        
        self.refresh_worker = None
    
    def enable_all_repos(self):
        """启用所有软件源"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, QCheckBox):
                checkbox_widget.setChecked(True)
    
    def disable_all_repos(self):
        """禁用所有软件源"""
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget and isinstance(checkbox_widget, QCheckBox):
                checkbox_widget.setChecked(False)
    
