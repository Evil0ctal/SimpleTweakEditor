# -*- coding: utf-8 -*-
"""
应用程序核心模块
包含主要的业务逻辑和事件处理
"""

import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.localization.language_manager import LanguageManager
from src.ui.control_editor import ControlEditorDialog
from src.ui.main_window import MainWindow
from src.utils.file_operations import (
    unpack_deb_file, pack_folder_to_deb, read_control_file, write_control_file
)
from src.utils.system_utils import (
    open_folder, is_valid_deb_file, is_valid_package_folder,
    get_package_info_from_control, suggest_output_filename
)
from src.workers.command_thread import UnpackThread, PackThread
from .config import ConfigManager


class TweakEditorApp:
    """Tweak编辑器应用程序核心类"""

    def __init__(self):
        # 初始化管理器
        self.config_mgr = ConfigManager()
        self.lang_mgr = LanguageManager()

        # 设置语言
        config_lang = self.config_mgr.get_language()
        if config_lang != "auto":
            self.lang_mgr.set_language(config_lang)

        # 调试模式
        self.debug_mode = self.config_mgr.get_debug_mode()

        # 操作状态
        self.is_operation_running = False
        self.current_operation_thread = None

        # 创建主窗口
        self.main_window = MainWindow(self)

        self.debug_print("Application core initialized")

    def debug_print(self, message):
        """调试输出"""
        if self.debug_mode:
            print(f"DEBUG: {message}")

    def show(self):
        """显示主窗口"""
        self.main_window.show()

    def close(self):
        """关闭应用程序"""
        self.stop_current_operation()
        self.main_window.close()
    
    def __del__(self):
        """析构函数 - 确保线程正确清理"""
        self.stop_current_operation()

    def log(self, message, tag=None):
        """记录日志"""
        if self.main_window:
            self.main_window.log(message, tag)

    def process_input_path(self, path):
        """处理输入的文件或文件夹路径"""
        if os.path.isfile(path) and is_valid_deb_file(path):
            self.process_deb_file(path)
        elif os.path.isdir(path) and is_valid_package_folder(path):
            self.process_folder(path)
        else:
            self.log(f"Invalid input: {path}", "error")

    def process_dropped_item(self, path):
        """处理拖放的项目"""
        self.main_window.status_bar.showMessage(f"Processing: {path}")
        self.log(f"Received dropped item: {path}", "info")

        if os.path.isfile(path):
            if is_valid_deb_file(path):
                self.process_deb_file(path)
            else:
                error_msg = self.lang_mgr.format_text("unsupported_file", path)
                self.log(error_msg, "error")
                QMessageBox.warning(
                    self.main_window,
                    self.lang_mgr.get_text("unsupported_file"),
                    self.lang_mgr.get_text("unsupported_file_msg")
                )
        elif os.path.isdir(path):
            if is_valid_package_folder(path):
                self.process_folder(path)
            else:
                error_msg = self.lang_mgr.format_text("invalid_dropfolder", path)
                self.log(error_msg, "error")
                QMessageBox.critical(
                    self.main_window,
                    self.lang_mgr.get_text("repack_invalid_folder"),
                    self.lang_mgr.get_text("repack_missing_debian")
                )
        else:
            self.log(self.lang_mgr.format_text("unsupported_file", path), "error")

    def process_deb_file(self, deb_path):
        """处理.deb文件 - 提示解包"""
        self.log(f"Preparing to unpack: {deb_path}", "info")

        # 更新配置中的路径
        self.config_mgr.set_path("last_deb_dir", os.path.dirname(deb_path))

        # 获取默认输出目录
        deb_name = os.path.splitext(os.path.basename(deb_path))[0]
        last_output_dir = self.config_mgr.get_path("last_output_dir") or os.path.dirname(deb_path)
        auto_output_dir = os.path.join(last_output_dir, deb_name)

        # 询问用户解包选项
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle(self.lang_mgr.get_text("unpack_confirm"))
        msg_box.setText(self.lang_mgr.format_text("unpack_question", os.path.basename(deb_path)))
        msg_box.setInformativeText(self.lang_mgr.get_text("unpack_options"))

        auto_btn = msg_box.addButton(self.lang_mgr.get_text("auto_unpack"), QMessageBox.ButtonRole.AcceptRole)
        manual_btn = msg_box.addButton(self.lang_mgr.get_text("manual_select_dir"), QMessageBox.ButtonRole.ActionRole)
        _ = msg_box.addButton(self.lang_mgr.get_text("cancel"), QMessageBox.ButtonRole.RejectRole)  # cancel_btn unused

        msg_box.setDefaultButton(auto_btn)
        msg_box.exec()

        if msg_box.clickedButton() == auto_btn:
            self.log(f"Using auto-generated output directory: {auto_output_dir}", "info")
            self.config_mgr.set_path("last_output_dir", os.path.dirname(auto_output_dir))
            self.unpack_deb_file(deb_path, os.path.dirname(auto_output_dir))
        elif msg_box.clickedButton() == manual_btn:
            output_dir = QFileDialog.getExistingDirectory(
                self.main_window,
                self.lang_mgr.get_text("select_unpack_output"),
                last_output_dir
            )
            if output_dir:
                self.config_mgr.set_path("last_output_dir", output_dir)
                self.unpack_deb_file(deb_path, output_dir)

    def process_folder(self, folder_path):
        """处理文件夹 - 提示打包"""
        self.log(f"Preparing to pack folder: {folder_path}", "info")

        # 更新配置中的路径
        self.config_mgr.set_path("last_folder_dir", folder_path)

        # 询问用户是否打包
        result = QMessageBox.question(
            self.main_window,
            self.lang_mgr.get_text("repack_confirm"),
            self.lang_mgr.format_text("repack_question", folder_path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            self.start_repack_process(folder_path)

    def unpack_deb_dialog(self):
        """解包对话框"""
        last_deb_dir = self.config_mgr.get_path("last_deb_dir") or os.getcwd()

        deb_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            self.lang_mgr.get_text("unpack_deb"),
            last_deb_dir,
            "Debian packages (*.deb);;All files (*.*)"
        )

        if not deb_path:
            return

        self.config_mgr.set_path("last_deb_dir", os.path.dirname(deb_path))

        last_output_dir = self.config_mgr.get_path("last_output_dir") or os.path.dirname(deb_path)
        output_dir = QFileDialog.getExistingDirectory(
            self.main_window,
            self.lang_mgr.get_text("select_unpack_output"),
            last_output_dir
        )

        if not output_dir:
            return

        self.config_mgr.set_path("last_output_dir", output_dir)
        self.unpack_deb_file(deb_path, output_dir)

    def repack_folder_dialog(self):
        """重新打包对话框"""
        last_folder_dir = self.config_mgr.get_path("last_folder_dir") or os.getcwd()

        folder_path = QFileDialog.getExistingDirectory(
            self.main_window,
            self.lang_mgr.get_text("repack_folder"),
            last_folder_dir
        )

        if not folder_path:
            return

        self.config_mgr.set_path("last_folder_dir", folder_path)

        if not is_valid_package_folder(folder_path):
            QMessageBox.critical(
                self.main_window,
                self.lang_mgr.get_text("repack_invalid_folder"),
                self.lang_mgr.get_text("repack_missing_debian")
            )
            return

        self.start_repack_process(folder_path)

    def unpack_deb_file(self, deb_path, output_dir):
        """执行解包操作"""
        if self.is_operation_running:
            self.log(self.lang_mgr.get_text("operation_in_progress"), "error")
            return

        self.start_operation()
        self.log(f"Starting unpack: {os.path.basename(deb_path)}", "info")
        self.main_window.status_bar.showMessage(self.lang_mgr.format_text("unpacking", os.path.basename(deb_path)))

        # 创建解包线程
        self.current_operation_thread = UnpackThread(deb_path, output_dir, unpack_deb_file)
        self.current_operation_thread.progress_message.connect(self.log)
        self.current_operation_thread.operation_finished.connect(self.handle_unpack_result)
        self.current_operation_thread.start()

    def start_repack_process(self, folder_path):
        """开始重新打包过程"""
        if self.is_operation_running:
            self.log(self.lang_mgr.get_text("operation_in_progress"), "error")
            return

        control_path = os.path.join(folder_path, "DEBIAN", "control")

        # 读取control文件
        success, content = read_control_file(control_path)
        if not success:
            QMessageBox.critical(
                self.main_window,
                self.lang_mgr.get_text("error"),
                self.lang_mgr.format_text("cannot_read_control", content)
            )
            return

        # 打开control编辑器
        dialog = ControlEditorDialog(self.main_window, content, control_path)
        if dialog.exec() != dialog.DialogCode.Accepted:
            self.log("User cancelled repack operation.", "info")
            return

        # 保存编辑后的control内容
        new_content = dialog.getContent()
        success, error = write_control_file(control_path, new_content)
        if not success:
            QMessageBox.critical(
                self.main_window,
                self.lang_mgr.get_text("error"),
                self.lang_mgr.format_text("cannot_write_control", error)
            )
            return

        # 生成建议的文件名
        package_info = get_package_info_from_control(control_path)
        suggested_name = suggest_output_filename(package_info)

        last_save_dir = self.config_mgr.get_path("last_save_dir") or os.path.dirname(folder_path)

        # 询问保存位置
        out_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            self.lang_mgr.get_text("save_repacked_deb"),
            os.path.join(last_save_dir, suggested_name),
            "Debian packages (*.deb);;All files (*.*)"
        )

        if not out_path:
            self.log("User cancelled save dialog.", "info")
            return

        self.config_mgr.set_path("last_save_dir", os.path.dirname(out_path))
        self.pack_folder_to_deb(folder_path, out_path)

    def pack_folder_to_deb(self, folder_path, output_path):
        """执行打包操作"""
        if self.is_operation_running:
            self.log(self.lang_mgr.get_text("operation_in_progress"), "error")
            return

        self.start_operation()
        self.log(f"Starting pack: {os.path.basename(folder_path)}", "info")
        self.main_window.status_bar.showMessage(self.lang_mgr.format_text("packing", os.path.basename(folder_path)))

        # 创建打包线程
        self.current_operation_thread = PackThread(folder_path, output_path, pack_folder_to_deb)
        self.current_operation_thread.progress_message.connect(self.log)
        self.current_operation_thread.operation_finished.connect(self.handle_pack_result)
        self.current_operation_thread.start()

    def handle_unpack_result(self, success, message, target_dir):
        """处理解包结果"""
        self.end_operation()

        if success:
            if message:
                self.log(message, "info")

            success_msg = f"Successfully unpacked to: {target_dir}"
            self.log(success_msg, "success")
            self.main_window.status_bar.showMessage(self.lang_mgr.get_text("unpack_complete"))

            # 询问是否生成目录结构或打开文件夹
            msg_box = QMessageBox(self.main_window)
            msg_box.setWindowTitle(self.lang_mgr.get_text("unpack_complete"))
            msg_box.setText(self.lang_mgr.format_text("unpack_with_structure", target_dir))
            
            structure_btn = msg_box.addButton(self.lang_mgr.get_text("generate_structure"), QMessageBox.ButtonRole.AcceptRole)
            open_btn = msg_box.addButton(self.lang_mgr.get_text("open_folder"), QMessageBox.ButtonRole.ActionRole)
            _ = msg_box.addButton(self.lang_mgr.get_text("cancel"), QMessageBox.ButtonRole.RejectRole)
            
            msg_box.setDefaultButton(structure_btn)
            msg_box.exec()
            
            if msg_box.clickedButton() == structure_btn:
                # 生成目录结构文件
                from src.utils.file_operations import generate_directory_structure
                success_struct, result_path = generate_directory_structure(target_dir)
                
                if success_struct:
                    self.log(self.lang_mgr.format_text("structure_generated", result_path), "success")
                    # 生成成功后询问是否打开文件夹
                    open_result = QMessageBox.question(
                        self.main_window,
                        self.lang_mgr.get_text("unpack_complete"),
                        self.lang_mgr.get_text("open_folder") + "?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if open_result == QMessageBox.StandardButton.Yes:
                        open_folder(target_dir)
                else:
                    self.log(self.lang_mgr.format_text("structure_generation_failed", result_path), "error")
                    
            elif msg_box.clickedButton() == open_btn:
                open_folder(target_dir)
        else:
            self.log("Unpack failed", "error")
            if message:
                self.log(message, "error")

            self.main_window.status_bar.showMessage(self.lang_mgr.get_text("unpack_error"))
            QMessageBox.critical(
                self.main_window,
                self.lang_mgr.get_text("unpack_error"),
                self.lang_mgr.format_text("unpack_failed", message)
            )

    def handle_pack_result(self, success, message, out_path):
        """处理打包结果"""
        self.end_operation()

        if success:
            if message:
                self.log(message, "info")

            success_msg = f"Successfully created package: {out_path}"
            self.log(success_msg, "success")
            self.main_window.status_bar.showMessage(self.lang_mgr.get_text("pack_complete"))

            # 询问是否打开包含文件夹
            result = QMessageBox.question(
                self.main_window,
                self.lang_mgr.get_text("pack_complete"),
                self.lang_mgr.format_text("pack_success", out_path),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                open_folder(os.path.dirname(out_path))
        else:
            self.log("Pack failed", "error")
            if message:
                self.log(message, "error")

            self.main_window.status_bar.showMessage(self.lang_mgr.get_text("pack_error"))
            QMessageBox.critical(
                self.main_window,
                self.lang_mgr.get_text("pack_error"),
                self.lang_mgr.format_text("pack_failed", message)
            )

    def start_operation(self):
        """开始操作"""
        self.is_operation_running = True
        self.debug_print("Operation started")

    def end_operation(self):
        """结束操作"""
        self.is_operation_running = False
        self.current_operation_thread = None
        self.debug_print("Operation ended")

    def stop_current_operation(self):
        """停止当前操作"""
        if self.current_operation_thread and self.current_operation_thread.isRunning():
            self.current_operation_thread.stop()
            self.current_operation_thread.wait()
            self.end_operation()

    def toggle_debug_mode(self):
        """切换调试模式"""
        self.debug_mode = not self.debug_mode
        self.config_mgr.set_debug_mode(self.debug_mode)

        status = self.lang_mgr.get_text("debug_enabled" if self.debug_mode else "debug_disabled")
        self.debug_print(status)
        self.log(status, "info")

    def switch_language(self, lang_code):
        """切换语言"""
        if self.lang_mgr.set_language(lang_code):
            self.config_mgr.set_language(lang_code)
            self.debug_print(f"Language switched to {lang_code}")

            # 更新主窗口UI
            self.main_window.update_ui_language()

    def show_about_dialog(self):
        """显示关于对话框"""
        from src.ui.about_dialog_improved import ImprovedAboutDialog
        dialog = ImprovedAboutDialog(self.main_window, self.lang_mgr)
        dialog.exec()