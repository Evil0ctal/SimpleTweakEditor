# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-31
作者: Evil0ctal

中文介绍:
SimpleTweakEditor 改进版Plist编辑器
提供树形视图和文本编辑两种模式，支持语法高亮、拖放、撤销/恢复和现代化UI设计

英文介绍:
SimpleTweakEditor Improved Plist Editor
Provides tree view and text editing modes with syntax highlighting, drag-drop, undo/redo and modern UI design
"""

import json
import os
import plistlib
import re
import xml.dom.minidom
from datetime import datetime
from typing import Any, Optional, Union

# 导入安全模块
try:
    from ..utils.security import validate_path, PathTraversalError, validate_file_size
except ImportError:
    # 如果安全模块不可用，使用基本验证
    def validate_path(path):
        return os.path.abspath(path)
    
    class PathTraversalError(Exception):
        pass
    
    def validate_file_size(path, max_size):
        if os.path.getsize(path) > max_size:
            raise ValueError(f"File too large")

from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, pyqtBoundSignal, QRegularExpression
)
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent, QAction,
    QSyntaxHighlighter, QTextCharFormat, QColor, QFontDatabase, QKeySequence, QUndoStack,
    QUndoCommand, QTextCursor, QFont
)
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QFileDialog, QMenu, QInputDialog,
    QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QDateTimeEdit, QTextEdit, QWidget, QLabel, QHeaderView, QTabWidget, QPlainTextEdit,
    QTreeWidgetItemIterator, QStatusBar, QDockWidget, QMainWindow,
    QStyle
)


class PlistSyntaxHighlighter(QSyntaxHighlighter):
    """Plist 语法高亮器 - 支持主题切换和更精确的匹配"""
    
    def __init__(self, document, style_manager=None):
        super().__init__(document)
        self.style_manager = style_manager
        self.setup_colors()
        
    def setup_colors(self):
        """根据主题设置颜色"""
        self.highlighting_rules = []
        
        # 从样式管理器获取当前主题
        is_dark = True
        if self.style_manager:
            is_dark = self.style_manager.is_dark_mode()
        
        if is_dark:
            # 暗色主题颜色
            self.colors = {
                'tag': "#E06C75",      # 红色
                'key': "#98C379",      # 绿色
                'string': "#E5C07B",   # 黄色
                'number': "#D19A66",   # 橙色
                'bool': "#56B6C2",     # 青色
                'comment': "#5C6370",  # 灰色
                'declaration': "#C678DD", # 紫色
                'data': "#61AFEF",     # 蓝色
                'date': "#C678DD"      # 紫色
            }
        else:
            # 浅色主题颜色
            self.colors = {
                'tag': "#e01e48",      # 深红色
                'key': "#50a14f",      # 深绿色
                'string': "#c18401",   # 深黄色
                'number': "#986801",   # 深橙色
                'bool': "#0184bc",     # 深青色
                'comment': "#a0a1a7",  # 深灰色
                'declaration': "#a626a4", # 深紫色
                'data': "#4078f2",     # 深蓝色
                'date': "#a626a4"      # 深紫色
            }
        
        # 更精确的正则表达式
        # XML 声明
        declaration_format = QTextCharFormat()
        declaration_format.setForeground(QColor(self.colors['declaration']))
        self.highlighting_rules.append((r'<\?xml[^>]*\?>', declaration_format))
        
        # DOCTYPE
        doctype_format = QTextCharFormat()
        doctype_format.setForeground(QColor(self.colors['declaration']))
        self.highlighting_rules.append((r'<!DOCTYPE[^>]*>', doctype_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(self.colors['comment']))
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r'<!--[\s\S]*?-->', comment_format))
        
        # 键名（在 <key> 标签中）
        key_format = QTextCharFormat()
        key_format.setForeground(QColor(self.colors['key']))
        key_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r'(?<=<key>)[^<]+(?=</key>)', key_format))
        
        # 字符串值
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(self.colors['string']))
        self.highlighting_rules.append((r'(?<=<string>)[^<]*(?=</string>)', string_format))
        
        # 整数
        integer_format = QTextCharFormat()
        integer_format.setForeground(QColor(self.colors['number']))
        self.highlighting_rules.append((r'(?<=<integer>)[^<]+(?=</integer>)', integer_format))
        
        # 实数
        real_format = QTextCharFormat()
        real_format.setForeground(QColor(self.colors['number']))
        self.highlighting_rules.append((r'(?<=<real>)[^<]+(?=</real>)', real_format))
        
        # 布尔值
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor(self.colors['bool']))
        bool_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r'<(true|false)/>', bool_format))
        
        # 日期
        date_format = QTextCharFormat()
        date_format.setForeground(QColor(self.colors['date']))
        self.highlighting_rules.append((r'(?<=<date>)[^<]+(?=</date>)', date_format))
        
        # 数据
        data_format = QTextCharFormat()
        data_format.setForeground(QColor(self.colors['data']))
        self.highlighting_rules.append((r'(?<=<data>)[^<]+(?=</data>)', data_format))
        
        # XML 标签（最后匹配）
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor(self.colors['tag']))
        self.highlighting_rules.append((r'</?[^>]+/?>', tag_format))
        
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)
                
    def refresh_theme(self) -> None:
        """刷新主题"""
        self.setup_colors()
        self.rehighlight()


class PlistTreeItem(QTreeWidgetItem):
    """Plist树形项目，增强数据类型支持"""
    
    # 支持的数据类型
    TYPE_MAP = {
        bool: "Boolean",
        int: "Integer", 
        float: "Real",
        str: "String",
        bytes: "Data",
        datetime: "Date",
        dict: "Dictionary",
        list: "Array"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_type = None  # 存储数据类型
        self.key = None  # 存储字典的键
        
    def get_type(self) -> Optional[str]:
        """获取数据类型"""
        return self.data_type
        
    def to_dict(self) -> Any:
        """将树形结构转换为字典"""
        value = self.data(0, Qt.ItemDataRole.UserRole)
        
        if self.data_type == "Dictionary":
            result = {}
            for i in range(self.childCount()):
                child = self.child(i)
                result[child.key] = child.to_dict()
            return result
        elif self.data_type == "Array":
            result = []
            for i in range(self.childCount()):
                child = self.child(i)
                result.append(child.to_dict())
            return result
        else:
            return value


class TreeEditCommand(QUndoCommand):
    """树形编辑撤销命令"""
    
    def __init__(self, editor, action_type, item=None, key=None, value=None, old_value=None):
        super().__init__()
        self.editor = editor
        self.action_type = action_type
        self.item = item
        self.key = key
        self.value = value
        self.old_value = old_value
        
    def undo(self) -> None:
        """撤销操作"""
        if self.action_type == "edit":
            self.item.setData(0, Qt.ItemDataRole.UserRole, self.old_value)
            self.item.setText(2, self.editor.get_display_value(self.old_value))
            self.editor.update_parent_data(self.item)
        elif self.action_type == "add":
            parent = self.item.parent()
            if parent:
                parent.removeChild(self.item)
                self.editor.update_parent_data(parent)
        elif self.action_type == "delete":
            # 恢复删除的项
            pass
            
    def redo(self) -> None:
        """重做操作"""
        if self.action_type == "edit":
            self.item.setData(0, Qt.ItemDataRole.UserRole, self.value)
            self.item.setText(2, self.editor.get_display_value(self.value))
            self.editor.update_parent_data(self.item)
        elif self.action_type == "add":
            # 重新添加项
            pass
        elif self.action_type == "delete":
            parent = self.item.parent()
            if parent:
                parent.removeChild(self.item)
                self.editor.update_parent_data(parent)


class ImprovedPlistEditor(QMainWindow):
    """改进版Plist文件编辑器 - 使用QMainWindow支持更多功能"""
    
    # 信号定义
    file_modified: pyqtBoundSignal = pyqtSignal(bool)  # 文件是否被修改
    
    def __init__(self, parent=None, language_manager=None, style_manager=None):
        super().__init__(parent)
        self.language_manager = language_manager
        self.style_manager = style_manager
        self.current_file = None
        self.is_modified = False
        self.plist_data = None
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(100)  # 限制撤销栈大小，防止内存泄漏
        
        # 设置窗口属性
        self.setWindowTitle(self.tr("Plist Editor"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.resize(1200, 800)
        
        # 设置窗口独立性，使其在任务栏中显示
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        
        self.init_ui()
        self.setup_shortcuts()
        self.apply_theme()
        self.setAcceptDrops(True)
        
    def init_ui(self) -> None:
        """初始化用户界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(10, 10, 10, 0)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # 树形视图标签页
        self.tree_view_widget = self.create_tree_view()
        self.tab_widget.addTab(self.tree_view_widget, self.tr("Tree View"))
        
        # 文本编辑标签页
        self.text_edit_widget = self.create_text_view()
        self.tab_widget.addTab(self.text_edit_widget, self.tr("Text Editor"))
        
        # 连接标签切换事件
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        content_layout.addWidget(self.tab_widget)
        main_layout.addWidget(content_widget)
        
        # 创建状态栏
        self.create_status_bar()
        
        # 创建搜索dock
        self.create_search_dock()
        
    def create_menu_bar(self) -> None:
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(self.tr("&File"))
        
        new_action = QAction(self.tr("&New"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction(self.tr("&Open..."), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction(self.tr("&Save"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(self.tr("Save &As..."), self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # 导入/导出
        import_json_action = QAction(self.tr("Import from JSON..."), self)
        import_json_action.triggered.connect(self.import_from_json)
        file_menu.addAction(import_json_action)
        
        export_json_action = QAction(self.tr("Export to JSON..."), self)
        export_json_action.triggered.connect(self.export_to_json)
        file_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        close_action = QAction(self.tr("&Close"), self)
        close_action.setShortcut(QKeySequence.StandardKey.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu(self.tr("&Edit"))
        
        self.undo_action = QAction(self.tr("&Undo"), self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo_stack.undo)
        edit_menu.addAction(self.undo_action)
        
        self.redo_action = QAction(self.tr("&Redo"), self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.undo_stack.redo)
        edit_menu.addAction(self.redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction(self.tr("&Find..."), self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.show_search_dock)
        edit_menu.addAction(find_action)
        
        # 视图菜单
        view_menu = menubar.addMenu(self.tr("&View"))
        
        expand_all_action = QAction(self.tr("&Expand All"), self)
        expand_all_action.triggered.connect(self.expand_all)
        view_menu.addAction(expand_all_action)
        
        collapse_all_action = QAction(self.tr("&Collapse All"), self)
        collapse_all_action.triggered.connect(self.collapse_all)
        view_menu.addAction(collapse_all_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu(self.tr("&Tools"))
        
        format_action = QAction(self.tr("&Format XML"), self)
        format_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        format_action.triggered.connect(self.format_xml)
        tools_menu.addAction(format_action)
        
        validate_action = QAction(self.tr("&Validate Plist"), self)
        validate_action.triggered.connect(self.validate_plist)
        tools_menu.addAction(validate_action)
        
    def create_toolbar(self) -> None:
        """创建工具栏"""
        toolbar = self.addToolBar(self.tr("Main Toolbar"))
        toolbar.setMovable(False)
        
        # 文件操作
        new_action = toolbar.addAction(self.tr("New"))
        new_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        new_action.triggered.connect(self.new_file)
        
        open_action = toolbar.addAction(self.tr("Open"))
        open_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        open_action.triggered.connect(self.open_file)
        
        save_action = toolbar.addAction(self.tr("Save"))
        save_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        save_action.triggered.connect(self.save_file)
        
        toolbar.addSeparator()
        
        # 编辑操作
        self.add_dict_action = toolbar.addAction(self.tr("Add Dict"))
        self.add_dict_action.triggered.connect(lambda: self.add_item('dict'))
        
        self.add_array_action = toolbar.addAction(self.tr("Add Array"))
        self.add_array_action.triggered.connect(lambda: self.add_item('array'))
        
        self.delete_action = toolbar.addAction(self.tr("Delete"))
        self.delete_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_action.triggered.connect(self.delete_selected_item)
        
        toolbar.addSeparator()
        
        # 视图操作
        expand_action = toolbar.addAction(self.tr("Expand All"))
        expand_action.triggered.connect(self.expand_all)
        
        collapse_action = toolbar.addAction(self.tr("Collapse All"))
        collapse_action.triggered.connect(self.collapse_all)
        
        toolbar.addSeparator()
        
        # 格式化
        self.format_action = toolbar.addAction(self.tr("Format"))
        self.format_action.triggered.connect(self.format_xml)
        
    def create_tree_view(self) -> QWidget:
        """创建树形视图"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建拖放提示标签（初始显示）
        self.drop_hint_label = QLabel()
        hint_text = self.tr("Drag and drop files here to open\nSupported formats: .plist, .mobileconfig")
        if self.language_manager and self.language_manager.current_language == "zh":
            hint_text = "拖拽文件到此处可打开文件\n支持的格式：.plist, .mobileconfig"
        self.drop_hint_label.setText(hint_text)
        self.drop_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint_label.setWordWrap(True)
        
        # 设置提示标签样式
        if self.style_manager and self.style_manager.is_dark_mode():
            self.drop_hint_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 14px;
                    padding: 40px;
                    background-color: transparent;
                    border: 2px dashed #3e3e42;
                    border-radius: 8px;
                    margin: 20px;
                }
            """)
        else:
            self.drop_hint_label.setStyleSheet("""
                QLabel {
                    color: #999999;
                    font-size: 14px;
                    padding: 40px;
                    background-color: transparent;
                    border: 2px dashed #d0d0d0;
                    border-radius: 8px;
                    margin: 20px;
                }
            """)
        
        # 创建树形控件
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels([self.tr("Key"), self.tr("Type"), self.tr("Value")])
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self.edit_item)
        self.tree_widget.itemChanged.connect(self.on_item_changed)
        
        # 设置列宽
        header = self.tree_widget.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.resizeSection(1, 100)
        
        # 初始隐藏树形控件
        self.tree_widget.hide()
        
        layout.addWidget(self.drop_hint_label)
        layout.addWidget(self.tree_widget)
        
        return widget
        
    def create_text_view(self) -> QWidget:
        """创建文本视图"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建文本编辑器
        self.text_editor = QPlainTextEdit()
        self.text_editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        
        # 设置语法高亮
        self.syntax_highlighter = PlistSyntaxHighlighter(
            self.text_editor.document(), 
            self.style_manager
        )
        
        # 连接文本变化事件
        self.text_editor.textChanged.connect(self.on_text_changed)
        
        layout.addWidget(self.text_editor)
        
        return widget
        
    def create_status_bar(self) -> None:
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 文件路径标签
        self.file_label = QLabel(self.tr("No file loaded"))
        self.status_bar.addWidget(self.file_label)
        
        # 修改状态标签
        self.modified_label = QLabel()
        self.status_bar.addPermanentWidget(self.modified_label)
        
        # 项目数量标签
        self.item_count_label = QLabel()
        self.status_bar.addPermanentWidget(self.item_count_label)
        
    def create_search_dock(self) -> None:
        """创建搜索停靠窗口"""
        self.search_dock = QDockWidget(self.tr("Search and Replace"), self)
        self.search_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(8, 8, 8, 8)
        
        # 搜索行
        search_row = QHBoxLayout()
        search_label = QLabel(self.tr("Find:"))
        search_row.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.tr("Enter search text..."))
        self.search_input.textChanged.connect(self.on_search)
        self.search_input.returnPressed.connect(self.find_next)
        search_row.addWidget(self.search_input)
        
        self.find_next_btn = QPushButton(self.tr("Find Next"))
        self.find_next_btn.clicked.connect(self.find_next)
        search_row.addWidget(self.find_next_btn)
        
        self.find_prev_btn = QPushButton(self.tr("Find Previous"))
        self.find_prev_btn.clicked.connect(self.find_previous)
        search_row.addWidget(self.find_prev_btn)
        
        search_layout.addLayout(search_row)
        
        # 替换行（仅在文本编辑模式下显示）
        self.replace_widget = QWidget()
        replace_row = QHBoxLayout(self.replace_widget)
        replace_row.setContentsMargins(0, 0, 0, 0)
        
        replace_label = QLabel(self.tr("Replace:"))
        replace_row.addWidget(replace_label)
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText(self.tr("Replace with..."))
        replace_row.addWidget(self.replace_input)
        
        self.replace_btn = QPushButton(self.tr("Replace"))
        self.replace_btn.clicked.connect(self.replace_current)
        replace_row.addWidget(self.replace_btn)
        
        self.replace_all_btn = QPushButton(self.tr("Replace All"))
        self.replace_all_btn.clicked.connect(self.replace_all)
        replace_row.addWidget(self.replace_all_btn)
        
        search_layout.addWidget(self.replace_widget)
        
        # 选项行
        options_row = QHBoxLayout()
        
        self.case_sensitive_cb = QCheckBox(self.tr("Case sensitive"))
        options_row.addWidget(self.case_sensitive_cb)
        
        self.whole_word_cb = QCheckBox(self.tr("Whole word"))
        options_row.addWidget(self.whole_word_cb)
        
        options_row.addStretch()
        
        close_button = QPushButton(self.tr("Close"))
        close_button.clicked.connect(self.search_dock.hide)
        options_row.addWidget(close_button)
        
        search_layout.addLayout(options_row)
        
        self.search_dock.setWidget(search_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.search_dock)
        self.search_dock.hide()
        
        # 初始化搜索相关变量
        self.current_search_pos = 0
        self.search_matches = []
        self.current_match_index = -1
        
    def setup_shortcuts(self) -> None:
        """设置快捷键"""
        # 已在菜单中设置
        pass
        
    def apply_theme(self) -> None:
        """应用主题样式"""
        if self.style_manager:
            # 获取当前是否为暗色模式
            is_dark = self.style_manager.is_dark_mode()
            
            # 应用主窗口样式
            if is_dark:
                # 暗色主题样式
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                    }
                    QMenuBar {
                        background-color: #2d2d30;
                        color: #cccccc;
                    }
                    QMenuBar::item:selected {
                        background-color: #094771;
                    }
                    QMenu {
                        background-color: #252526;
                        color: #cccccc;
                        border: 1px solid #3e3e42;
                    }
                    QMenu::item:selected {
                        background-color: #094771;
                    }
                    QToolBar {
                        background-color: #2d2d30;
                        border: none;
                        spacing: 3px;
                    }
                    QToolButton {
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 3px;
                        padding: 4px;
                        margin: 2px;
                        color: #cccccc;
                    }
                    QToolButton:hover {
                        background-color: #3e3e42;
                        border: 1px solid #555555;
                    }
                    QToolButton:pressed {
                        background-color: #094771;
                    }
                    QTabWidget::pane {
                        background-color: #1e1e1e;
                        border: 1px solid #3e3e42;
                    }
                    QTabBar::tab {
                        background-color: #2d2d30;
                        color: #cccccc;
                        padding: 8px 16px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background-color: #1e1e1e;
                        border-bottom: 2px solid #007acc;
                    }
                    QTabBar::tab:hover {
                        background-color: #3e3e42;
                    }
                    QTreeWidget {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                        border: 1px solid #3e3e42;
                        selection-background-color: #094771;
                    }
                    QTreeWidget::item {
                        padding: 2px;
                    }
                    QTreeWidget::item:hover {
                        background-color: #2a2d2e;
                    }
                    QTreeWidget::item:selected {
                        background-color: #094771;
                    }
                    QHeaderView::section {
                        background-color: #2d2d30;
                        color: #cccccc;
                        padding: 5px;
                        border: none;
                        border-right: 1px solid #3e3e42;
                        border-bottom: 1px solid #3e3e42;
                    }
                    QPlainTextEdit {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                        border: 1px solid #3e3e42;
                        selection-background-color: #264f78;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    }
                    QStatusBar {
                        background-color: #007acc;
                        color: white;
                    }
                    QDockWidget {
                        color: #cccccc;
                    }
                    QDockWidget::title {
                        background-color: #2d2d30;
                        padding: 5px;
                    }
                    QLineEdit {
                        background-color: #3c3c3c;
                        border: 1px solid #3e3e42;
                        color: #cccccc;
                        padding: 5px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #007acc;
                    }
                """)
            else:
                # 浅色主题样式
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #f3f3f3;
                        color: #000000;
                    }
                    QMenuBar {
                        background-color: #f0f0f0;
                        color: #000000;
                    }
                    QMenuBar::item:selected {
                        background-color: #0078d4;
                        color: white;
                    }
                    QMenu {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #d0d0d0;
                    }
                    QMenu::item:selected {
                        background-color: #e3f2fd;
                    }
                    QToolBar {
                        background-color: #f0f0f0;
                        border: none;
                        spacing: 3px;
                    }
                    QToolButton {
                        background-color: transparent;
                        border: 1px solid transparent;
                        border-radius: 3px;
                        padding: 4px;
                        margin: 2px;
                        color: #000000;
                    }
                    QToolButton:hover {
                        background-color: #e0e0e0;
                        border: 1px solid #cccccc;
                    }
                    QToolButton:pressed {
                        background-color: #c0c0c0;
                    }
                    QTabWidget::pane {
                        background-color: #ffffff;
                        border: 1px solid #d0d0d0;
                    }
                    QTabBar::tab {
                        background-color: #f0f0f0;
                        color: #000000;
                        padding: 8px 16px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background-color: #ffffff;
                        border-bottom: 2px solid #0078d4;
                    }
                    QTabBar::tab:hover {
                        background-color: #e0e0e0;
                    }
                    QTreeWidget {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #d0d0d0;
                        selection-background-color: #e3f2fd;
                    }
                    QTreeWidget::item {
                        padding: 2px;
                    }
                    QTreeWidget::item:hover {
                        background-color: #f5f5f5;
                    }
                    QTreeWidget::item:selected {
                        background-color: #e3f2fd;
                        color: #000000;
                    }
                    QHeaderView::section {
                        background-color: #f0f0f0;
                        color: #000000;
                        padding: 5px;
                        border: none;
                        border-right: 1px solid #d0d0d0;
                        border-bottom: 1px solid #d0d0d0;
                    }
                    QPlainTextEdit {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #d0d0d0;
                        selection-background-color: #add6ff;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    }
                    QStatusBar {
                        background-color: #0078d4;
                        color: white;
                    }
                    QDockWidget {
                        color: #000000;
                    }
                    QDockWidget::title {
                        background-color: #f0f0f0;
                        padding: 5px;
                    }
                    QLineEdit {
                        background-color: #ffffff;
                        border: 1px solid #d0d0d0;
                        color: #000000;
                        padding: 5px;
                    }
                    QLineEdit:focus {
                        border: 1px solid #0078d4;
                    }
                """)
            
            # 更新语法高亮器
            if hasattr(self, 'syntax_highlighter'):
                self.syntax_highlighter.refresh_theme()
    
    def show_search_dock(self) -> None:
        """显示搜索停靠窗口"""
        # 根据当前标签页决定是否显示替换功能
        if self.tab_widget.currentIndex() == 1:  # 文本编辑模式
            self.replace_widget.show()
        else:  # 树形视图模式
            self.replace_widget.hide()
            
        self.search_dock.show()
        self.search_input.setFocus()
        self.search_input.selectAll()
        
    def validate_plist(self) -> None:
        """验证Plist格式"""
        try:
            if self.tab_widget.currentIndex() == 1:  # 文本编辑模式
                text = self.text_editor.toPlainText()
                plistlib.loads(text.encode('utf-8'))
                self.status_bar.showMessage(self.tr("Plist validation successful"), 3000)
                QMessageBox.information(self, self.tr("Validation"), self.tr("The plist is valid!"))
            else:
                self.status_bar.showMessage(self.tr("Plist is valid"), 3000)
        except Exception as e:
            error_msg = str(e)
            
            # 尝试从错误消息中提取行号和列号
            import re
            line_match = re.search(r'line (\d+)', error_msg, re.IGNORECASE)
            col_match = re.search(r'column (\d+)', error_msg, re.IGNORECASE)
            
            if line_match and self.tab_widget.currentIndex() == 1:
                line_num = int(line_match.group(1))
                col_num = int(col_match.group(1)) if col_match else 1
                
                # 移动光标到错误位置
                cursor = self.text_editor.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                
                # 移动到指定行
                for _ in range(line_num - 1):
                    cursor.movePosition(QTextCursor.MoveOperation.Down)
                    
                # 移动到指定列
                for _ in range(col_num - 1):
                    cursor.movePosition(QTextCursor.MoveOperation.Right)
                    
                # 设置光标并确保可见
                self.text_editor.setTextCursor(cursor)
                self.text_editor.ensureCursorVisible()
                
                # 高亮错误行
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                format = cursor.charFormat()
                format.setBackground(QColor("#FF6B6B") if self.style_manager and self.style_manager.is_dark_mode() else QColor("#FFE0E0"))
                cursor.setCharFormat(format)
                
                # 显示详细错误信息
                error_detail = self.tr("Error at line {}, column {}:\n{}").format(
                    line_num, col_num if col_match else "?", error_msg
                )
                QMessageBox.critical(self, self.tr("Validation Error"), error_detail)
            else:
                QMessageBox.critical(self, self.tr("Validation Error"), 
                                   self.tr("Invalid plist format:\n{}").format(error_msg))
            
    def import_from_json(self) -> None:
        """从JSON导入"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Import from JSON"),
            "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                # 安全检查：验证文件大小
                MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE:
                    raise ValueError(f"File too large: {file_size / 1024 / 1024:.1f}MB. Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024}MB")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                self.plist_data = json_data
                self.refresh_tree()
                self.update_text_from_tree()
                self.set_modified(True)
                self.status_bar.showMessage(self.tr("Imported from JSON successfully"), 3000)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Import Error"), str(e))
                
    def export_to_json(self) -> None:
        """导出为JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Export to JSON"),
            "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                if self.tab_widget.currentIndex() == 1:
                    self.update_tree_from_text()
                    
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.plist_data, f, indent=2, default=str)
                    
                self.status_bar.showMessage(self.tr("Exported to JSON successfully"), 3000)
            except Exception as e:
                QMessageBox.critical(self, self.tr("Export Error"), str(e))
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """处理拖入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.endswith(('.plist', '.mobileconfig')):
                    event.acceptProposedAction()
                    return
                    
    def dropEvent(self, event: QDropEvent) -> None:
        """处理放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.exists(file_path) and file_path.endswith(('.plist', '.mobileconfig')):
                self.load_file(file_path)
                break
                
    def update_toolbar_state(self) -> None:
        """更新工具栏按钮状态"""
        if self.plist_data is None:
            # 如果没有数据，允许创建根结构
            self.add_dict_action.setEnabled(True)
            self.add_array_action.setEnabled(True)
            self.add_dict_action.setText(self.tr("Create Dict"))
            self.add_array_action.setText(self.tr("Create Array"))
            self.add_dict_action.setToolTip(self.tr("Create a new dictionary as root"))
            self.add_array_action.setToolTip(self.tr("Create a new array as root"))
        elif isinstance(self.plist_data, (dict, list)):
            # 如果是容器类型，允许添加子项
            self.add_dict_action.setEnabled(True)
            self.add_array_action.setEnabled(True)
            self.add_dict_action.setText(self.tr("Add Dict"))
            self.add_array_action.setText(self.tr("Add Array"))
            if isinstance(self.plist_data, dict):
                self.add_dict_action.setToolTip(self.tr("Add a new dictionary item"))
                self.add_array_action.setToolTip(self.tr("Add a new array item"))
            else:
                self.add_dict_action.setToolTip(self.tr("Append a new dictionary to array"))
                self.add_array_action.setToolTip(self.tr("Append a new array to array"))
        else:
            # 如果是基本类型，禁用添加按钮
            self.add_dict_action.setEnabled(False)
            self.add_array_action.setEnabled(False)
            self.add_dict_action.setText(self.tr("Add Dict"))
            self.add_array_action.setText(self.tr("Add Array"))
            self.add_dict_action.setToolTip(self.tr("Cannot add to non-container type"))
            self.add_array_action.setToolTip(self.tr("Cannot add to non-container type"))
    
    def on_tab_changed(self, index: int) -> None:
        """标签页切换事件"""
        if index == 0:  # 树形视图
            # 从文本更新到树形视图
            if self.is_modified:
                self.update_tree_from_text()
            # 更新工具栏状态
            self.update_toolbar_state()
            self.delete_action.setEnabled(True)
            self.format_action.setEnabled(False)
        else:  # 文本编辑
            # 从树形视图更新到文本
            self.update_text_from_tree()
            # 更新工具栏状态
            self.add_dict_action.setEnabled(False)
            self.add_array_action.setEnabled(False)
            self.delete_action.setEnabled(False)
            self.format_action.setEnabled(True)
            
    def update_tree_from_text(self) -> None:
        """从文本更新树形视图"""
        try:
            # 解析文本内容
            text = self.text_editor.toPlainText()
            self.plist_data = plistlib.loads(text.encode('utf-8'))
            self.refresh_tree()
        except Exception as e:
            self.status_bar.showMessage(f"Parse error: {str(e)}", 5000)
            
    def update_text_from_tree(self) -> None:
        """从树形视图更新文本"""
        try:
            if self.plist_data is not None:
                # 转换为XML格式
                plist_bytes = plistlib.dumps(self.plist_data, fmt=plistlib.FMT_XML)
                text = plist_bytes.decode('utf-8')
                self.text_editor.setPlainText(text)
        except Exception as e:
            self.status_bar.showMessage(f"Convert error: {str(e)}", 5000)
            
    def on_text_changed(self) -> None:
        """文本变化事件"""
        if self.tab_widget.currentIndex() == 1:  # 仅在文本编辑模式下
            self.set_modified(True)
            
    def on_search(self, text: str) -> None:
        """搜索功能"""
        if self.tab_widget.currentIndex() == 0:  # 树形视图
            self.search_in_tree(text)
        else:  # 文本视图
            self.search_in_text(text)
            
    def search_in_tree(self, text: str) -> None:
        """在树形视图中搜索"""
        if not text:
            # 显示所有项目
            iterator = QTreeWidgetItemIterator(self.tree_widget)
            while iterator.value():
                iterator.value().setHidden(False)
                iterator += 1
            return
            
        # 隐藏不匹配的项目
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        match_count = 0
        while iterator.value():
            item = iterator.value()
            matches = False
            
            # 检查所有列
            for col in range(item.columnCount()):
                if text.lower() in item.text(col).lower():
                    matches = True
                    match_count += 1
                    break
                    
            item.setHidden(not matches)
            
            # 如果子项匹配，显示父项
            if not matches and item.childCount() > 0:
                for i in range(item.childCount()):
                    if not item.child(i).isHidden():
                        item.setHidden(False)
                        break
                        
            iterator += 1
            
        self.status_bar.showMessage(self.tr("{} matches found").format(match_count), 3000)
            
    def search_in_text(self, text: str) -> None:
        """在文本中搜索"""
        
        if not text:
            # 清除所有高亮
            self.text_editor.moveCursor(QTextCursor.MoveOperation.Start)
            return
            
        # 获取搜索选项
        case_sensitive = self.case_sensitive_cb.isChecked() if hasattr(self, 'case_sensitive_cb') else False
        whole_word = self.whole_word_cb.isChecked() if hasattr(self, 'whole_word_cb') else False
        
        # 防止ReDoS攻击 - 限制搜索模式长度和复杂度
        if len(text) > 1000:
            self.status_bar.showMessage(self.tr("Search pattern too long (max 1000 chars)"), 3000)
            return
            
        # 检查潜在的ReDoS模式
        dangerous_patterns = [
            r'(\w+\+)+',     # 重复的量词
            r'(\w+\*)+',     # 重复的星号
            r'(\w+\?)+',     # 重复的问号
            r'(\.\*)+',      # 重复的.*
            r'(\w+){1000,}', # 过大的重复次数
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text):
                self.status_bar.showMessage(self.tr("Search pattern too complex"), 3000)
                return
        
        if whole_word:
            text = r'\b' + re.escape(text) + r'\b'
        else:
            # 转义特殊字符以防止regex注入
            text = re.escape(text)
            
        # 创建正则表达式
        options = QRegularExpression.PatternOption.NoPatternOption
        if not case_sensitive:
            options = QRegularExpression.PatternOption.CaseInsensitiveOption
            
        regex = QRegularExpression(text, options)
        
        # 验证正则表达式有效性
        if not regex.isValid():
            self.status_bar.showMessage(self.tr("Invalid search pattern"), 3000)
            return
        
        # 清除之前的高亮
        cursor = self.text_editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        format = cursor.charFormat()
        format.setBackground(Qt.GlobalColor.transparent)
        cursor.setCharFormat(format)
        
        # 搜索所有匹配并高亮
        self.search_matches = []
        cursor = self.text_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # 高亮格式
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#FFFF00") if not self.style_manager or not self.style_manager.is_dark_mode() else QColor("#5A5A00"))
        
        document = self.text_editor.document()
        cursor = document.find(regex)
        
        while not cursor.isNull():
            self.search_matches.append(cursor)
            cursor.mergeCharFormat(highlight_format)
            cursor = document.find(regex, cursor)
            
        # 更新状态栏
        match_count = len(self.search_matches)
        self.status_bar.showMessage(self.tr("{} matches found").format(match_count), 3000)
        
        # 跳转到第一个匹配
        if self.search_matches:
            self.current_match_index = 0
            self.text_editor.setTextCursor(self.search_matches[0])
            self.text_editor.ensureCursorVisible()
    
    def find_next(self) -> None:
        """查找下一个匹配"""
        if not self.search_matches:
            self.on_search(self.search_input.text())
            return
            
        if self.search_matches:
            self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
            self.text_editor.setTextCursor(self.search_matches[self.current_match_index])
            self.text_editor.ensureCursorVisible()
            self.status_bar.showMessage(
                self.tr("Match {} of {}").format(self.current_match_index + 1, len(self.search_matches)), 
                2000
            )
    
    def find_previous(self) -> None:
        """查找上一个匹配"""
        if not self.search_matches:
            self.on_search(self.search_input.text())
            return
            
        if self.search_matches:
            self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
            self.text_editor.setTextCursor(self.search_matches[self.current_match_index])
            self.text_editor.ensureCursorVisible()
            self.status_bar.showMessage(
                self.tr("Match {} of {}").format(self.current_match_index + 1, len(self.search_matches)), 
                2000
            )
    
    def replace_current(self) -> None:
        """替换当前匹配"""
        if self.tab_widget.currentIndex() != 1:  # 仅在文本编辑模式下
            return
            
        if not self.search_matches or self.current_match_index == -1:
            self.find_next()
            return
            
        if self.current_match_index < len(self.search_matches):
            cursor = self.search_matches[self.current_match_index]
            replacement = self.replace_input.text()
            
            # 执行替换
            cursor.insertText(replacement)
            
            # 重新搜索
            self.on_search(self.search_input.text())
            self.set_modified(True)
    
    def replace_all(self) -> None:
        """替换所有匹配"""
        if self.tab_widget.currentIndex() != 1:  # 仅在文本编辑模式下
            return
            
        search_text = self.search_input.text()
        if not search_text:
            return
            
        replacement = self.replace_input.text()
        
        # 获取搜索选项
        case_sensitive = self.case_sensitive_cb.isChecked()
        whole_word = self.whole_word_cb.isChecked()
        
        # 构建正则表达式 - QRegularExpression 已在文件顶部导入
        
        if whole_word:
            search_text = r'\b' + search_text + r'\b'
            
        options = QRegularExpression.PatternOption.NoPatternOption
        if not case_sensitive:
            options = QRegularExpression.PatternOption.CaseInsensitiveOption
            
        regex = QRegularExpression(search_text, options)
        
        # 执行替换
        document = self.text_editor.document()
        cursor = self.text_editor.textCursor()
        cursor.beginEditBlock()
        
        count = 0
        cursor = document.find(regex)
        while not cursor.isNull():
            cursor.insertText(replacement)
            count += 1
            cursor = document.find(regex, cursor)
            
        cursor.endEditBlock()
        
        # 更新状态
        self.set_modified(True)
        self.status_bar.showMessage(self.tr("{} replacements made").format(count), 3000)
        
        # 清除搜索高亮
        self.search_matches = []
        self.current_match_index = -1
        
    def expand_all(self) -> None:
        """展开所有节点"""
        self.tree_widget.expandAll()
        
    def collapse_all(self) -> None:
        """折叠所有节点"""
        self.tree_widget.collapseAll()
        
    def delete_selected_item(self) -> None:
        """删除选中的项目"""
        current_item = self.tree_widget.currentItem()
        if current_item and current_item.parent():
            self.delete_item(current_item)
    
    def format_xml(self) -> None:
        """格式化XML文本"""
        try:
            # 获取当前文本
            text = self.text_editor.toPlainText()
            
            # 解析plist数据
            plist_data = plistlib.loads(text.encode('utf-8'))
            
            # 重新格式化为XML
            formatted_bytes = plistlib.dumps(plist_data, fmt=plistlib.FMT_XML, sort_keys=False)
            formatted_text = formatted_bytes.decode('utf-8')
            
            # 进一步美化XML格式
            dom = xml.dom.minidom.parseString(formatted_text)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # 移除空行
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(lines)
            
            # 更新文本编辑器
            self.text_editor.setPlainText(pretty_xml)
            self.status_bar.showMessage(self.tr("XML formatted successfully"), 3000)
            
        except Exception as e:
            self.status_bar.showMessage(f"Format error: {str(e)}", 5000)
            QMessageBox.warning(
                self,
                self.tr("Format Error"),
                self.tr("Failed to format XML: {}").format(str(e))
            )
    
    def tr(self, text: str) -> str:
        """翻译文本（简化版）"""
        translations = {
            # 窗口和标签
            "Plist Editor": "Plist 编辑器" if self.language_manager and self.language_manager.current_language == "zh" else "Plist Editor",
            "Tree View": "树形视图" if self.language_manager and self.language_manager.current_language == "zh" else "Tree View",
            "Text Editor": "文本编辑" if self.language_manager and self.language_manager.current_language == "zh" else "Text Editor",
            "Ready": "就绪" if self.language_manager and self.language_manager.current_language == "zh" else "Ready",
            "No file loaded": "未加载文件" if self.language_manager and self.language_manager.current_language == "zh" else "No file loaded",
            
            # 菜单
            "&File": "文件(&F)" if self.language_manager and self.language_manager.current_language == "zh" else "&File",
            "&Edit": "编辑(&E)" if self.language_manager and self.language_manager.current_language == "zh" else "&Edit",
            "&View": "视图(&V)" if self.language_manager and self.language_manager.current_language == "zh" else "&View",
            "&Tools": "工具(&T)" if self.language_manager and self.language_manager.current_language == "zh" else "&Tools",
            
            # 文件菜单
            "&New": "新建(&N)" if self.language_manager and self.language_manager.current_language == "zh" else "&New",
            "&Open...": "打开(&O)..." if self.language_manager and self.language_manager.current_language == "zh" else "&Open...",
            "&Save": "保存(&S)" if self.language_manager and self.language_manager.current_language == "zh" else "&Save",
            "Save &As...": "另存为(&A)..." if self.language_manager and self.language_manager.current_language == "zh" else "Save &As...",
            "&Close": "关闭(&C)" if self.language_manager and self.language_manager.current_language == "zh" else "&Close",
            "Import from JSON...": "从JSON导入..." if self.language_manager and self.language_manager.current_language == "zh" else "Import from JSON...",
            "Export to JSON...": "导出为JSON..." if self.language_manager and self.language_manager.current_language == "zh" else "Export to JSON...",
            
            # 编辑菜单
            "&Undo": "撤销(&U)" if self.language_manager and self.language_manager.current_language == "zh" else "&Undo",
            "&Redo": "重做(&R)" if self.language_manager and self.language_manager.current_language == "zh" else "&Redo",
            "&Find...": "查找(&F)..." if self.language_manager and self.language_manager.current_language == "zh" else "&Find...",
            
            # 视图菜单
            "&Expand All": "全部展开(&E)" if self.language_manager and self.language_manager.current_language == "zh" else "&Expand All",
            "&Collapse All": "全部折叠(&C)" if self.language_manager and self.language_manager.current_language == "zh" else "&Collapse All",
            
            # 工具菜单
            "&Format XML": "格式化XML(&F)" if self.language_manager and self.language_manager.current_language == "zh" else "&Format XML",
            "&Validate Plist": "验证Plist(&V)" if self.language_manager and self.language_manager.current_language == "zh" else "&Validate Plist",
            
            # 工具栏
            "New": "新建" if self.language_manager and self.language_manager.current_language == "zh" else "New",
            "Open": "打开" if self.language_manager and self.language_manager.current_language == "zh" else "Open",
            "Save": "保存" if self.language_manager and self.language_manager.current_language == "zh" else "Save",
            "Save As": "另存为" if self.language_manager and self.language_manager.current_language == "zh" else "Save As",
            "Add Dict": "添加字典" if self.language_manager and self.language_manager.current_language == "zh" else "Add Dict",
            "Add Array": "添加数组" if self.language_manager and self.language_manager.current_language == "zh" else "Add Array",
            "Delete": "删除" if self.language_manager and self.language_manager.current_language == "zh" else "Delete",
            "Expand All": "全部展开" if self.language_manager and self.language_manager.current_language == "zh" else "Expand All",
            "Collapse All": "全部折叠" if self.language_manager and self.language_manager.current_language == "zh" else "Collapse All",
            "Format": "格式化" if self.language_manager and self.language_manager.current_language == "zh" else "Format",
            "Main Toolbar": "主工具栏" if self.language_manager and self.language_manager.current_language == "zh" else "Main Toolbar",
            
            # 搜索
            "Search": "搜索" if self.language_manager and self.language_manager.current_language == "zh" else "Search",
            "Search and Replace": "搜索和替换" if self.language_manager and self.language_manager.current_language == "zh" else "Search and Replace",
            "Find:": "查找:" if self.language_manager and self.language_manager.current_language == "zh" else "Find:",
            "Enter search text...": "输入搜索文本..." if self.language_manager and self.language_manager.current_language == "zh" else "Enter search text...",
            "Find Next": "查找下一个" if self.language_manager and self.language_manager.current_language == "zh" else "Find Next",
            "Find Previous": "查找上一个" if self.language_manager and self.language_manager.current_language == "zh" else "Find Previous",
            "Replace:": "替换:" if self.language_manager and self.language_manager.current_language == "zh" else "Replace:",
            "Replace with...": "替换为..." if self.language_manager and self.language_manager.current_language == "zh" else "Replace with...",
            "Replace": "替换" if self.language_manager and self.language_manager.current_language == "zh" else "Replace",
            "Replace All": "全部替换" if self.language_manager and self.language_manager.current_language == "zh" else "Replace All",
            "Case sensitive": "区分大小写" if self.language_manager and self.language_manager.current_language == "zh" else "Case sensitive",
            "Whole word": "全字匹配" if self.language_manager and self.language_manager.current_language == "zh" else "Whole word",
            "Close": "关闭" if self.language_manager and self.language_manager.current_language == "zh" else "Close",
            "{} matches found": "找到 {} 个匹配项" if self.language_manager and self.language_manager.current_language == "zh" else "{} matches found",
            "Match {} of {}": "第 {} 个匹配，共 {} 个" if self.language_manager and self.language_manager.current_language == "zh" else "Match {} of {}",
            "{} replacements made": "已替换 {} 处" if self.language_manager and self.language_manager.current_language == "zh" else "{} replacements made",
            "Drag and drop files here to open\nSupported formats: .plist, .mobileconfig": "拖拽文件到此处可打开文件\n支持的格式：.plist, .mobileconfig" if self.language_manager and self.language_manager.current_language == "zh" else "Drag and drop files here to open\nSupported formats: .plist, .mobileconfig",
            
            # 表头
            "Key": "键" if self.language_manager and self.language_manager.current_language == "zh" else "Key",
            "Type": "类型" if self.language_manager and self.language_manager.current_language == "zh" else "Type",
            "Value": "值" if self.language_manager and self.language_manager.current_language == "zh" else "Value",
            
            # 状态消息
            "XML formatted successfully": "XML格式化成功" if self.language_manager and self.language_manager.current_language == "zh" else "XML formatted successfully",
            "Plist validation successful": "Plist验证成功" if self.language_manager and self.language_manager.current_language == "zh" else "Plist validation successful",
            "The plist is valid!": "Plist格式有效！" if self.language_manager and self.language_manager.current_language == "zh" else "The plist is valid!",
            "Plist is valid": "Plist有效" if self.language_manager and self.language_manager.current_language == "zh" else "Plist is valid",
            "Imported from JSON successfully": "从JSON导入成功" if self.language_manager and self.language_manager.current_language == "zh" else "Imported from JSON successfully",
            "Exported to JSON successfully": "导出为JSON成功" if self.language_manager and self.language_manager.current_language == "zh" else "Exported to JSON successfully",
            
            # 对话框
            "Add Item": "添加项目" if self.language_manager and self.language_manager.current_language == "zh" else "Add Item",
            "Enter key name:": "输入键名:" if self.language_manager and self.language_manager.current_language == "zh" else "Enter key name:",
            "Delete Item": "删除项目" if self.language_manager and self.language_manager.current_language == "zh" else "Delete Item",
            "Are you sure you want to delete this item?": "确定要删除这个项目吗？" if self.language_manager and self.language_manager.current_language == "zh" else "Are you sure you want to delete this item?",
            "Error": "错误" if self.language_manager and self.language_manager.current_language == "zh" else "Error",
            "Save Changes": "保存更改" if self.language_manager and self.language_manager.current_language == "zh" else "Save Changes",
            "Do you want to save changes before creating a new file?": "在创建新文件之前要保存更改吗？" if self.language_manager and self.language_manager.current_language == "zh" else "Do you want to save changes before creating a new file?",
            "Do you want to save changes before closing?": "在关闭之前要保存更改吗？" if self.language_manager and self.language_manager.current_language == "zh" else "Do you want to save changes before closing?",
            "Open Plist File": "打开Plist文件" if self.language_manager and self.language_manager.current_language == "zh" else "Open Plist File",
            "Save Plist File": "保存Plist文件" if self.language_manager and self.language_manager.current_language == "zh" else "Save Plist File",
            "Import from JSON": "从JSON导入" if self.language_manager and self.language_manager.current_language == "zh" else "Import from JSON",
            "Export to JSON": "导出为JSON" if self.language_manager and self.language_manager.current_language == "zh" else "Export to JSON",
            "Validation": "验证" if self.language_manager and self.language_manager.current_language == "zh" else "Validation",
            "Validation Error": "验证错误" if self.language_manager and self.language_manager.current_language == "zh" else "Validation Error",
            "Invalid plist format:\n{}": "无效的plist格式:\n{}" if self.language_manager and self.language_manager.current_language == "zh" else "Invalid plist format:\n{}",
            "Error at line {}, column {}:\n{}": "错误位置：第 {} 行，第 {} 列:\n{}" if self.language_manager and self.language_manager.current_language == "zh" else "Error at line {}, column {}:\n{}",
            "Import Error": "导入错误" if self.language_manager and self.language_manager.current_language == "zh" else "Import Error",
            "Export Error": "导出错误" if self.language_manager and self.language_manager.current_language == "zh" else "Export Error",
            "Format Error": "格式化错误" if self.language_manager and self.language_manager.current_language == "zh" else "Format Error",
            "Failed to format XML: {}": "格式化XML失败: {}" if self.language_manager and self.language_manager.current_language == "zh" else "Failed to format XML: {}",
            "Info": "提示" if self.language_manager and self.language_manager.current_language == "zh" else "Info",
            "Cannot add items to a non-container type. Please use the context menu on dictionary or array items.": "无法向非容器类型添加项目。请使用字典或数组项目的右键菜单。" if self.language_manager and self.language_manager.current_language == "zh" else "Cannot add items to a non-container type. Please use the context menu on dictionary or array items.",
            "Create Dict": "创建字典" if self.language_manager and self.language_manager.current_language == "zh" else "Create Dict",
            "Create Array": "创建数组" if self.language_manager and self.language_manager.current_language == "zh" else "Create Array",
            "Create a new dictionary as root": "创建新的字典作为根元素" if self.language_manager and self.language_manager.current_language == "zh" else "Create a new dictionary as root",
            "Create a new array as root": "创建新的数组作为根元素" if self.language_manager and self.language_manager.current_language == "zh" else "Create a new array as root",
            "Add a new dictionary item": "添加新的字典项" if self.language_manager and self.language_manager.current_language == "zh" else "Add a new dictionary item",
            "Add a new array item": "添加新的数组项" if self.language_manager and self.language_manager.current_language == "zh" else "Add a new array item",
            "Append a new dictionary to array": "向数组追加新的字典" if self.language_manager and self.language_manager.current_language == "zh" else "Append a new dictionary to array",
            "Append a new array to array": "向数组追加新的数组" if self.language_manager and self.language_manager.current_language == "zh" else "Append a new array to array",
            "Cannot add to non-container type": "无法向非容器类型添加项目" if self.language_manager and self.language_manager.current_language == "zh" else "Cannot add to non-container type",
        }
        return translations.get(text, text)
        
    # 以下方法从原 PlistEditor 复制并适配
    def new_file(self) -> None:
        """新建文件"""
        if self.is_modified:
            ret = QMessageBox.question(
                self, self.tr("Save Changes"),
                self.tr("Do you want to save changes before creating a new file?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.save_file()
            elif ret == QMessageBox.StandardButton.Cancel:
                return
                
        self.current_file = None
        self.plist_data = {}
        self.refresh_tree()
        self.update_text_from_tree()
        self.set_modified(False)
        self.file_label.setText(self.tr("No file loaded"))
        self.undo_stack.clear()
        
    def open_file(self) -> None:
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open Plist File"),
            "", "Property List Files (*.plist);;Mobile Config Files (*.mobileconfig);;All Files (*)"
        )
        if file_path:
            self.load_file(file_path)
            
    def load_file(self, file_path: str) -> None:
        """加载plist文件"""
        try:
            # 安全检查：验证文件大小
            MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE:
                raise ValueError(f"File too large: {file_size / 1024 / 1024:.1f}MB. Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024}MB")
            
            # 安全检查：验证文件路径
            try:
                # 使用安全的路径验证
                real_path = validate_path(file_path)
            except PathTraversalError as e:
                raise ValueError(f"Unsafe file path: {str(e)}")
            
            if not os.path.exists(real_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(real_path, 'rb') as f:
                self.plist_data = plistlib.load(f)
                
            self.current_file = file_path
            self.refresh_tree()
            self.update_text_from_tree()
            self.set_modified(False)
            
            # 更新文件路径显示
            self.file_label.setText(os.path.basename(file_path))
            self.status_bar.showMessage(f"Loaded: {file_path}", 3000)
            self.undo_stack.clear()
            
            # 更新工具栏状态
            if self.tab_widget.currentIndex() == 0:
                self.update_toolbar_state()
            
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                f"Failed to load plist file: {str(e)}"
            )
            
    def save_file(self) -> None:
        """保存文件"""
        if not self.current_file:
            self.save_file_as()
            return
            
        try:
            # 如果在文本编辑模式，先验证并更新数据
            if self.tab_widget.currentIndex() == 1:
                text = self.text_editor.toPlainText()
                # 验证plist格式
                try:
                    self.plist_data = plistlib.loads(text.encode('utf-8'))
                except Exception as e:
                    # 显示验证错误
                    self.validate_plist()
                    return
            else:
                # 在树形视图模式下，需要从树重建plist_data
                try:
                    self.plist_data = self.build_plist_from_tree()
                except Exception as e:
                    QMessageBox.critical(
                        self, self.tr("Error"),
                        f"Failed to build plist from tree: {str(e)}"
                    )
                    return
                
            with open(self.current_file, 'wb') as f:
                plistlib.dump(self.plist_data, f)
                
            self.set_modified(False)
            self.status_bar.showMessage(f"Saved: {self.current_file}", 3000)
            
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("Error"),
                f"Failed to save file: {str(e)}"
            )
            
    def save_file_as(self) -> None:
        """另存为"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Plist File"),
            "", "Property List Files (*.plist)"
        )
        if file_path:
            if not file_path.endswith('.plist'):
                file_path += '.plist'
                
            self.current_file = file_path
            self.save_file()
            self.file_label.setText(os.path.basename(file_path))
            
    def set_modified(self, modified: bool) -> None:
        """设置修改状态"""
        self.is_modified = modified
        self.file_modified.emit(modified)
        
        # 更新窗口标题
        title = "Plist Editor"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
        if modified:
            title += " *"
        self.setWindowTitle(title)
        
        # 更新状态栏
        self.modified_label.setText("Modified" if modified else "")
        
    def refresh_tree(self) -> None:
        """刷新树形视图"""
        if not hasattr(self, 'tree_widget'):
            return
            
        self.tree_widget.clear()
        
        if self.plist_data is None:
            # 显示提示标签，隐藏树形控件
            if hasattr(self, 'drop_hint_label'):
                self.drop_hint_label.show()
                self.tree_widget.hide()
            return
            
        # 隐藏提示标签，显示树形控件
        if hasattr(self, 'drop_hint_label'):
            self.drop_hint_label.hide()
            self.tree_widget.show()
            
        # 根据数据类型创建根节点
        if isinstance(self.plist_data, dict):
            self.populate_dict(self.tree_widget.invisibleRootItem(), self.plist_data)
        elif isinstance(self.plist_data, list):
            self.populate_array(self.tree_widget.invisibleRootItem(), self.plist_data)
        else:
            # 单个值
            item = self.create_tree_item(None, "Root", self.plist_data)
            self.tree_widget.addTopLevelItem(item)
            
        self.tree_widget.expandAll()
        self.update_item_count()
        
    def populate_dict(self, parent_item: Union[QTreeWidget, QTreeWidgetItem], data: dict, parent_key: Optional[str] = None) -> None:
        """填充字典数据"""
        for key, value in data.items():
            item = self.create_tree_item(parent_item, key, value)
            
            if isinstance(value, dict):
                self.populate_dict(item, value, key)
            elif isinstance(value, list):
                self.populate_array(item, value, key)
                
    def populate_array(self, parent_item: Union[QTreeWidget, QTreeWidgetItem], data: list, parent_key: Optional[str] = None) -> None:
        """填充数组数据"""
        for i, value in enumerate(data):
            key = f"Item {i}"
            item = self.create_tree_item(parent_item, key, value, is_array_item=True)
            
            if isinstance(value, dict):
                self.populate_dict(item, value, key)
            elif isinstance(value, list):
                self.populate_array(item, value, key)
                
    def create_tree_item(self, parent: Optional[Union[QTreeWidget, QTreeWidgetItem]], key: str, value: Any, is_array_item: bool = False) -> PlistTreeItem:
        """创建树形项目"""
        if parent is None:
            item = PlistTreeItem()
        else:
            item = PlistTreeItem(parent)
            
        item.key = key
        item.setText(0, str(key))
        
        # 设置类型和值
        value_type = self.get_value_type(value)
        item.data_type = value_type
        item.setText(1, value_type)
        
        # 设置显示值
        display_value = self.get_display_value(value)
        item.setText(2, display_value)
        
        # 存储原始值
        item.setData(0, Qt.ItemDataRole.UserRole, value)
        item.setData(1, Qt.ItemDataRole.UserRole, is_array_item)
        
        # 设置可编辑性
        if not isinstance(value, (dict, list)):
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            
        return item
        
    def get_value_type(self, value: Any) -> str:
        """获取值的类型"""
        for type_class, type_name in PlistTreeItem.TYPE_MAP.items():
            if isinstance(value, type_class):
                return type_name
        return "Unknown"
            
    def get_display_value(self, value: Any) -> str:
        """获取显示值"""
        if isinstance(value, bool):
            return "YES" if value else "NO"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return value[:100] + "..." if len(value) > 100 else value
        elif isinstance(value, bytes):
            return f"<{len(value)} bytes>"
        elif isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, dict):
            return f"({len(value)} items)"
        elif isinstance(value, list):
            return f"({len(value)} items)"
        else:
            return str(value)
            
    def update_item_count(self) -> None:
        """更新项目计数"""
        total_items = 0
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            total_items += 1
            iterator += 1
        self.item_count_label.setText(f"Items: {total_items}")
            
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.tree_widget.itemAt(position)
        if not item or not isinstance(item, PlistTreeItem):
            return
            
        menu = QMenu(self)
        
        # 添加子项
        if item.data_type in ["Dictionary", "Array"]:
            add_menu = menu.addMenu("➕ " + self.tr("Add"))
            
            types = ["String", "Integer", "Real", "Boolean", "Date", "Data", "Dictionary", "Array"]
            for type_name in types:
                if item.data_type == "Dictionary":
                    action = add_menu.addAction(type_name)
                    action.triggered.connect(lambda checked, t=type_name, i=item: self.add_child_item(i, t))
                else:  # Array
                    action = add_menu.addAction(type_name)
                    action.triggered.connect(lambda checked, t=type_name, i=item: self.add_array_item(i, t))
                    
            menu.addSeparator()
            
        # 编辑
        if item.data_type not in ["Dictionary", "Array"]:
            edit_action = menu.addAction("✏️ " + self.tr("Edit"))
            edit_action.triggered.connect(lambda: self.edit_item(item))
            menu.addSeparator()
            
        # 删除
        if item.parent() is not None:  # 不能删除根节点
            delete_action = menu.addAction("🗑️ " + self.tr("Delete"))
            delete_action.triggered.connect(lambda: self.delete_item(item))
            
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
        
    def add_item(self, item_type: str):
        """添加根项目"""
        # 只有在plist_data为None或为空时才创建新的根结构
        if self.plist_data is None:
            if item_type == 'dict':
                self.plist_data = {}
            else:  # array
                self.plist_data = []
            
            self.refresh_tree()
            self.update_text_from_tree()
            self.set_modified(True)
        else:
            # 如果已有数据，应该添加到现有结构中
            if isinstance(self.plist_data, dict):
                # 对于字典，添加新的键值对
                key, ok = QInputDialog.getText(
                    self, self.tr("Add Item"),
                    self.tr("Enter key name:")
                )
                if ok and key:
                    # 检查键是否已存在
                    if key in self.plist_data:
                        reply = QMessageBox.question(
                            self, self.tr("Confirm Overwrite"),
                            self.tr("Key '{}' already exists. Overwrite?").format(key.replace("'", "''")),
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply != QMessageBox.StandardButton.Yes:
                            return
                    
                    if item_type == 'dict':
                        self.plist_data[key] = {}
                    else:  # array
                        self.plist_data[key] = []
                    self.refresh_tree()
                    self.update_text_from_tree()
                    self.set_modified(True)
            elif isinstance(self.plist_data, list):
                # 对于数组，添加新元素
                if item_type == 'dict':
                    self.plist_data.append({})
                else:  # array
                    self.plist_data.append([])
                self.refresh_tree()
                self.update_text_from_tree()
                self.set_modified(True)
            else:
                # 如果是其他类型，提示用户
                QMessageBox.information(
                    self, 
                    self.tr("Info"),
                    self.tr("Cannot add items to a non-container type. Please use the context menu on dictionary or array items.")
                )
        
    def add_child_item(self, parent_item: PlistTreeItem, value_type: str):
        """添加子项目（字典）"""
        if not isinstance(parent_item, PlistTreeItem):
            return
            
        # 获取新键名
        key, ok = QInputDialog.getText(
            self, self.tr("Add Item"),
            self.tr("Enter key name:")
        )
        if not ok or not key:
            return
            
        # 创建默认值
        default_value = self.get_default_value(value_type)
        
        # 更新数据
        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(parent_data, dict):
            # 检查键是否已存在
            if key in parent_data:
                reply = QMessageBox.question(
                    self, self.tr("Confirm Overwrite"),
                    self.tr("Key '{}' already exists. Overwrite?").format(key.replace("'", "''")),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            parent_data[key] = default_value
            
            # 创建树形项
            new_item = self.create_tree_item(parent_item, key, default_value)
            parent_item.setExpanded(True)
            
            # 添加到撤销栈
            command = TreeEditCommand(self, "add", new_item, key, default_value)
            self.undo_stack.push(command)
            
            self.set_modified(True)
            # 确保更新到根级别
            self.update_parent_data(parent_item)
            # 重建plist_data
            self.plist_data = self.build_plist_from_tree()
            self.update_text_from_tree()
            self.update_item_count()
        
    def add_array_item(self, parent_item: PlistTreeItem, value_type: str):
        """添加数组项目"""
        if not isinstance(parent_item, PlistTreeItem):
            return
            
        # 创建默认值
        default_value = self.get_default_value(value_type)
        
        # 直接创建新的子项，不依赖于UserRole中的数据
        key = f"Item {parent_item.childCount()}"
        new_item = self.create_tree_item(parent_item, key, default_value, is_array_item=True)
        parent_item.setExpanded(True)
        
        # 添加到撤销栈
        command = TreeEditCommand(self, "add", new_item, key, default_value)
        self.undo_stack.push(command)
        
        self.set_modified(True)
        # 重建plist_data
        self.plist_data = self.build_plist_from_tree()
        self.update_text_from_tree()
        self.update_item_count()
        
    def get_default_value(self, value_type: str) -> Any:
        """获取默认值"""
        defaults = {
            "String": "",
            "Integer": 0,
            "Real": 0.0,
            "Boolean": False,
            "Date": datetime.now(),
            "Data": b"",
            "Dictionary": {},
            "Array": []
        }
        return defaults.get(value_type, "")
        
    def edit_item(self, item: PlistTreeItem, column=0):
        """编辑项目"""
        if item.data_type in ["Dictionary", "Array"]:
            return
            
        # 显示编辑对话框
        current_value = item.data(0, Qt.ItemDataRole.UserRole)
        dialog = ValueEditDialog(self, item.data_type, current_value, self.style_manager)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_value = dialog.get_value()
            
            # 添加到撤销栈
            command = TreeEditCommand(self, "edit", item, item.key, new_value, current_value)
            self.undo_stack.push(command)
            
            # 更新树形项
            item.setData(0, Qt.ItemDataRole.UserRole, new_value)
            item.setText(2, self.get_display_value(new_value))
            
            # 更新数据模型
            self.update_parent_data(item)
            self.set_modified(True)
            self.update_text_from_tree()
            
    def delete_item(self, item: PlistTreeItem):
        """删除项目"""
        ret = QMessageBox.question(
            self, self.tr("Delete Item"),
            self.tr("Are you sure you want to delete this item?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if ret != QMessageBox.StandardButton.Yes:
            return
            
        parent_item = item.parent()
        if parent_item is None:
            return
            
        # 添加到撤销栈
        command = TreeEditCommand(self, "delete", item)
        self.undo_stack.push(command)
            
        # 更新父数据
        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        is_array_item = item.data(1, Qt.ItemDataRole.UserRole)
        
        if isinstance(parent_data, dict) and not is_array_item:
            del parent_data[item.key]
            parent_item.removeChild(item)
        elif isinstance(parent_data, list):
            index = parent_item.indexOfChild(item)
            parent_data.pop(index)
            self.refresh_array_items(parent_item)
            
        self.set_modified(True)
        self.update_text_from_tree()
        self.update_item_count()
        
    def refresh_array_items(self, array_item: PlistTreeItem, array_data=None):
        """刷新数组项目"""
        # 清除所有子项
        array_item.takeChildren()
        
        # 如果没有提供array_data，则从item获取
        if array_data is None:
            array_data = array_item.data(0, Qt.ItemDataRole.UserRole)
        
        # 重新添加
        self.populate_array(array_item, array_data, array_item.key)
        
    def update_parent_data(self, item: PlistTreeItem):
        """更新父节点的数据"""
        # 从叶子节点向上更新到根节点
        current = item
        
        while current.parent() is not None:
            parent = current.parent()
            parent_data = parent.data(0, Qt.ItemDataRole.UserRole)
            
            if isinstance(parent_data, dict):
                # 更新字典
                parent_data.clear()
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    child_key = child.key
                    child_value = child.data(0, Qt.ItemDataRole.UserRole)
                    parent_data[child_key] = child_value
                    
            elif isinstance(parent_data, list):
                # 更新数组
                parent_data.clear()
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    child_value = child.data(0, Qt.ItemDataRole.UserRole)
                    parent_data.append(child_value)
                    
            current = parent
    
    def build_plist_from_tree(self) -> Union[dict, list, Any]:
        """从树形视图构建plist数据"""
        if self.tree_widget.topLevelItemCount() == 0:
            # 保持原始数据类型
            if isinstance(self.plist_data, list):
                return []
            else:
                return {}
        
        # 如果plist_data是字典或列表，从根节点重建
        if isinstance(self.plist_data, dict):
            result = {}
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if isinstance(item, PlistTreeItem):
                    result[item.key] = self.get_item_value(item)
            return result
        elif isinstance(self.plist_data, list):
            result = []
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if isinstance(item, PlistTreeItem):
                    result.append(self.get_item_value(item))
            return result
        else:
            # 单个值
            item = self.tree_widget.topLevelItem(0)
            if isinstance(item, PlistTreeItem):
                return item.data(0, Qt.ItemDataRole.UserRole)
            return None
    
    def get_item_value(self, item: PlistTreeItem) -> Any:
        """递归获取树形项的值"""
        if item.data_type == "Dictionary":
            result = {}
            for i in range(item.childCount()):
                child = item.child(i)
                if isinstance(child, PlistTreeItem):
                    result[child.key] = self.get_item_value(child)
            return result
        elif item.data_type == "Array":
            result = []
            for i in range(item.childCount()):
                child = item.child(i)
                if isinstance(child, PlistTreeItem):
                    result.append(self.get_item_value(child))
            return result
        else:
            return item.data(0, Qt.ItemDataRole.UserRole)
            
    def on_item_changed(self, item: PlistTreeItem, column: int):
        """处理项目更改"""
        if column == 0 and not item.data(1, Qt.ItemDataRole.UserRole):
            # 键名被修改（非数组项）
            new_key = item.text(0)
            if new_key != item.key:
                item.key = new_key
                self.update_parent_data(item)
                self.set_modified(True)
                self.update_text_from_tree()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_modified:
            ret = QMessageBox.question(
                self, self.tr("Save Changes"),
                self.tr("Do you want to save changes before closing?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.save_file()
                event.accept()
            elif ret == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class ValueEditDialog(QDialog):
    """值编辑对话框 - 增强版本"""
    
    def __init__(self, parent, value_type: str, current_value: Any, style_manager=None):
        super().__init__(parent)
        self.value_type = value_type
        self.current_value = current_value
        self.style_manager = style_manager
        self.init_ui()
        self.apply_theme()
        
    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle(f"Edit {self.value_type}")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 标签
        label = QLabel(f"Enter {self.value_type} value:")
        label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        # 根据类型创建编辑器
        if self.value_type == "String":
            self.editor = QTextEdit()
            self.editor.setPlainText(str(self.current_value))
            self.editor.setMaximumHeight(150)
            
        elif self.value_type == "Integer":
            self.editor = QSpinBox()
            # 使用Python的sys.maxsize来支持64位系统
            import sys
            # QSpinBox仍然限制在32位范围内，这是Qt的限制
            # 但我们至少应该使用常量而不是魔数
            INT32_MIN = -(2**31)
            INT32_MAX = 2**31 - 1
            self.editor.setRange(INT32_MIN, INT32_MAX)
            self.editor.setValue(int(self.current_value))
            
        elif self.value_type == "Real":
            self.editor = QDoubleSpinBox()
            self.editor.setRange(-float('inf'), float('inf'))
            self.editor.setDecimals(6)
            self.editor.setValue(float(self.current_value))
            
        elif self.value_type == "Boolean":
            self.editor = QCheckBox("Value")
            self.editor.setChecked(bool(self.current_value))
            
        elif self.value_type == "Date":
            self.editor = QDateTimeEdit()
            if isinstance(self.current_value, datetime):
                self.editor.setDateTime(self.current_value)
            else:
                self.editor.setDateTime(datetime.now())
            self.editor.setCalendarPopup(True)
            self.editor.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
                
        elif self.value_type == "Data":
            self.editor = QTextEdit()
            self.editor.setPlainText(self.current_value.hex() if isinstance(self.current_value, bytes) else "")
            self.editor.setMaximumHeight(150)
            label.setText("Enter hexadecimal data:")
            # 添加提示
            hint_label = QLabel("Format: pairs of hex digits (e.g., 48656C6C6F)")
            hint_label.setStyleSheet("color: gray; font-size: 12px;")
            layout.addWidget(hint_label)
            
        else:
            self.editor = QLineEdit()
            self.editor.setText(str(self.current_value))
            
        layout.addWidget(self.editor)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.validate_and_accept)
        ok_button.setDefault(True)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # 设置焦点
        if hasattr(self.editor, 'setFocus'):
            self.editor.setFocus()
            if hasattr(self.editor, 'selectAll'):
                self.editor.selectAll()
                
    def apply_theme(self):
        """应用主题"""
        if self.style_manager and self.style_manager.is_dark_mode():
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d2d30;
                    color: #cccccc;
                }
                QLabel {
                    color: #cccccc;
                }
                QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #3e3e42;
                    color: #d4d4d4;
                    padding: 5px;
                }
                QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
                QDoubleSpinBox:focus, QDateTimeEdit:focus {
                    border: 1px solid #007acc;
                }
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    padding: 6px 14px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #0d5a8f;
                }
                QCheckBox {
                    color: #cccccc;
                }
            """)
            
    def validate_and_accept(self):
        """验证输入并接受"""
        try:
            # 验证输入
            if self.value_type == "Integer":
                _ = self.editor.value()
            elif self.value_type == "Real":
                _ = self.editor.value()
            elif self.value_type == "Data":
                hex_str = self.editor.toPlainText().strip()
                if hex_str:
                    # 移除空格
                    hex_str = hex_str.replace(" ", "")
                    # 限制长度以防止内存消耗
                    MAX_HEX_LENGTH = 1024 * 1024  # 1MB of hex chars = 512KB of data
                    if len(hex_str) > MAX_HEX_LENGTH:
                        raise ValueError(f"Hex data too large: {len(hex_str)} chars. Maximum allowed: {MAX_HEX_LENGTH}")
                    # 验证是否为有效的十六进制
                    bytes.fromhex(hex_str)
                    
            self.accept()
        except ValueError as e:
            # 显示错误边框
            if hasattr(self.editor, 'setStyleSheet'):
                current_style = self.editor.styleSheet()
                self.editor.setStyleSheet(current_style + " border: 2px solid red;")
                # 2秒后恢复
                QTimer.singleShot(2000, lambda: self.editor.setStyleSheet(current_style))
            
            QMessageBox.warning(self, "Invalid Input", f"Invalid value for {self.value_type}: {str(e)}")
            
    def get_value(self) -> Any:
        """获取编辑后的值"""
        if self.value_type == "String":
            return self.editor.toPlainText()
            
        elif self.value_type == "Integer":
            return self.editor.value()
            
        elif self.value_type == "Real":
            return self.editor.value()
            
        elif self.value_type == "Boolean":
            return self.editor.isChecked()
            
        elif self.value_type == "Date":
            return self.editor.dateTime().toPyDateTime()
            
        elif self.value_type == "Data":
            hex_str = self.editor.toPlainText().strip()
            if hex_str:
                hex_str = hex_str.replace(" ", "")
                # 限制长度
                MAX_HEX_LENGTH = 1024 * 1024
                if len(hex_str) > MAX_HEX_LENGTH:
                    return b""  # Return empty bytes for oversized data
                try:
                    return bytes.fromhex(hex_str)
                except ValueError:
                    return b""
            return b""
                
        else:
            return self.editor.text()