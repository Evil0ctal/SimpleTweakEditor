# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
iOS 设备面板组件，显示连接的设备信息并提供设备操作功能

英文介绍:
iOS device panel widget, displays connected device information and provides device operation features
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QTextEdit, QFileDialog,
                             QMessageBox, QProgressBar, QComboBox)

from ..core.device_manager import DeviceManager, iOSDevice
from ..localization.language_manager import LanguageManager


class DeviceInstallThread(QThread):
    """设备安装线程"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, device_manager, device, deb_path):
        super().__init__()
        self.device_manager = device_manager
        self.device = device
        self.deb_path = deb_path
    
    def run(self):
        """执行安装"""
        try:
            def progress_callback(percent, message):
                self.progress.emit(percent, message)
            
            success = self.device_manager.install_deb(
                self.device, 
                self.deb_path, 
                progress_callback
            )
            
            if success:
                self.finished.emit(True, f"Successfully uploaded to device: {os.path.basename(self.deb_path)}")
            else:
                self.finished.emit(False, "Failed to upload package")
                
        except Exception as e:
            self.finished.emit(False, str(e))


class DeviceMonitorThread(QThread):
    """设备监控线程"""
    device_event = pyqtSignal(str, object)  # event_type, device
    
    def __init__(self, device_manager):
        super().__init__()
        self.device_manager = device_manager
        self.running = True
    
    def run(self):
        """在后台线程中运行设备监控"""
        def callback(event_type, device):
            # 通过信号发送事件到主线程
            self.device_event.emit(event_type, device)
        
        if self.device_manager:
            self.device_manager.start_monitoring(callback)
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.device_manager:
            self.device_manager.stop_monitoring()


class DevicePanel(QWidget):
    """iOS 设备面板"""
    
    device_connected = pyqtSignal(iOSDevice)
    device_disconnected = pyqtSignal()
    
    def __init__(self, language_manager: LanguageManager, style_mgr=None, parent=None):
        super().__init__(parent)
        self.lang_mgr = language_manager
        self.style_mgr = style_mgr
        self.device_manager = DeviceManager()
        self.current_device = None
        self.connected_devices = {}  # UDID -> iOSDevice mapping
        self.install_thread = None
        self.monitor_thread = None
        
        self.init_ui()
        
        # 延迟开始监控设备，避免初始化冲突
        QTimer.singleShot(1000, self.start_device_monitoring)
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 设备信息组
        self.device_group = QGroupBox(self.lang_mgr.get_text("ios_device"))
        device_layout = QVBoxLayout()
        
        # 设备选择下拉框（多设备支持）
        device_select_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self.on_device_selected)
        self.device_combo.setEnabled(False)
        device_select_layout.addWidget(QLabel(self.lang_mgr.get_text("select_device") or "Select Device:"))
        device_select_layout.addWidget(self.device_combo)
        device_select_layout.addStretch()
        device_layout.addLayout(device_select_layout)
        
        # 设备状态
        self.status_label = QLabel(self.lang_mgr.get_text("no_device_connected"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        device_layout.addWidget(self.status_label)
        
        # 设备详情（初始隐藏）
        self.device_info_widget = QWidget()
        self.device_info_widget.setVisible(False)
        info_layout = QVBoxLayout()
        
        # 设备名称
        self.name_label = QLabel()
        info_layout.addWidget(self.name_label)
        
        # 设备型号和系统版本
        self.model_label = QLabel()
        info_layout.addWidget(self.model_label)
        
        # 越狱状态
        self.jailbreak_label = QLabel()
        info_layout.addWidget(self.jailbreak_label)
        
        # 添加更多设备信息展示
        self.device_details_button = QPushButton(self.lang_mgr.get_text("show_details"))
        self.device_details_button.clicked.connect(self.show_device_details)
        info_layout.addWidget(self.device_details_button)
        
        self.device_info_widget.setLayout(info_layout)
        device_layout.addWidget(self.device_info_widget)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        # 根据设备状态设置按钮文本
        install_text = self.lang_mgr.get_text("upload_to_device") or "Upload to Device"
        self.install_button = QPushButton(install_text)
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.install_deb_to_device)
        button_layout.addWidget(self.install_button)
        
        # 文件管理器按钮
        self.file_manager_button = QPushButton(self.lang_mgr.get_text("file_manager") or "File Manager")
        self.file_manager_button.setEnabled(False)
        self.file_manager_button.clicked.connect(self.open_file_manager)
        button_layout.addWidget(self.file_manager_button)
        
        # 刷新按钮
        self.refresh_button = QPushButton(self.lang_mgr.get_text("refresh_devices"))
        self.refresh_button.clicked.connect(self.refresh_devices)
        button_layout.addWidget(self.refresh_button)
        
        device_layout.addLayout(button_layout)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        device_layout.addWidget(self.progress_bar)
        
        self.device_group.setLayout(device_layout)
        layout.addWidget(self.device_group)
        
        # 日志区域
        log_group = QGroupBox("Device Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def start_device_monitoring(self):
        """开始设备监控"""
        if self.device_manager.is_available():
            self.log_text.append("[INFO] Starting device monitoring...")
            
            # 创建并启动监控线程
            self.monitor_thread = DeviceMonitorThread(self.device_manager)
            self.monitor_thread.device_event.connect(self.on_device_event_safe)
            self.monitor_thread.start()
            
            # 注释掉立即刷新，因为监控线程会自动检测设备
            # 只有在监控线程启动失败时才需要手动刷新
            # QTimer.singleShot(500, self.refresh_devices)
        else:
            self.show_pymobiledevice3_error()
            # Disable the device manager to prevent errors
            self.device_manager = None
    
    def show_pymobiledevice3_error(self):
        """显示 pymobiledevice3 相关错误"""
        self.status_label.setText("Limited device detection mode")
        self.status_label.setStyleSheet("color: orange;")
        self.log_text.append("[INFO] Using system tools for basic device detection")
        self.log_text.append("[INFO] Device information will be limited (UDID only)")
        self.log_text.append("[INFO] ")
        self.log_text.append("[INFO] For full device info (iOS version, storage, etc.):")
        self.log_text.append("[INFO] 1. Install pymobiledevice3: pip install pymobiledevice3")
        self.log_text.append("[INFO] 2. Ensure device is unlocked and trusted")
        self.log_text.append("[INFO] 3. Try 'sudo killall usbmuxd' and reconnect (macOS)")
        self.log_text.append("[INFO] ")
        self.log_text.append("[INFO] Current features available:")
        self.log_text.append("[INFO] ✓ Device connection detection")
        self.log_text.append("[INFO] ✓ Basic device identification")
        self.log_text.append("[INFO] ✗ Detailed device information")
        self.log_text.append("[INFO] ✗ Jailbreak detection")
        self.log_text.append("[INFO] ✗ File transfer features")
    
    def on_device_event_safe(self, event_type: str, device):
        """安全地处理设备事件（在主线程中）"""
        # 这个方法由信号调用，确保在主线程中执行
        if event_type == 'connected' and device:
            self.on_device_connected(device)
        elif event_type == 'disconnected' and device:
            self.on_device_disconnected(device)
        elif event_type == 'error':
            self.on_monitoring_error()
    
    def on_device_event(self, event_type: str, device: iOSDevice):
        """处理设备事件（保留以兼容）"""
        self.on_device_event_safe(event_type, device)
    
    def on_device_selected(self, index):
        """处理设备选择"""
        if index < 0:
            return
        
        udid = self.device_combo.itemData(index)
        if udid and udid in self.connected_devices:
            self.current_device = self.connected_devices[udid]
            self.update_device_info(self.current_device)
            self.install_button.setEnabled(True)
            self.file_manager_button.setEnabled(True)
            self.log_text.append(f"[SELECTED] {self.current_device.name} ({self.current_device.model})")
            
            # 更新应用程序的当前设备
            try:
                from src.core.app import TweakEditorApp
                app_instance = TweakEditorApp.get_instance()
                if app_instance:
                    app_instance.current_device = self.current_device
                    self.log_text.append(f"[INFO] Device architecture: {self.current_device.cpu_architecture}")
            except Exception as e:
                self.log_text.append(f"[DEBUG] Failed to update app device: {e}")
    
    def update_device_info(self, device: iOSDevice):
        """更新设备信息显示"""
        if device:
            # 更新状态标签
            self.status_label.setText(f"{len(self.connected_devices)} device(s) connected")
            self.status_label.setStyleSheet("color: green;")
            
            # 显示设备信息
            self.device_info_widget.setVisible(True)
            self.name_label.setText(f"<b>{self.lang_mgr.get_text('device_name')}:</b> {device.name}")
            self.model_label.setText(f"<b>{self.lang_mgr.get_text('device_model')}:</b> {device.model} (iOS {device.ios_version})")
            
            # 越狱状态
            if device.is_jailbroken:
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_status') or 'Jailbreak Status'}:</b> {device.jailbreak_type}"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: green;")
            elif "Manual Check Required" in device.jailbreak_type:
                # 显示手动确认按钮
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_status') or 'Jailbreak Status'}:</b> {self.lang_mgr.get_text('unknown') or 'Unknown'} <a href='#confirm'>{self.lang_mgr.get_text('click_to_confirm') or 'Click to confirm if jailbroken'}</a>"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: orange;")
                self.jailbreak_label.linkActivated.connect(self.manual_jailbreak_confirm)
            else:
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_status') or 'Jailbreak Status'}:</b> {self.lang_mgr.get_text('not_jailbroken') or 'Not Jailbroken'} ({self.lang_mgr.get_text('stock_ios') or 'Stock iOS'})"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: red;")
    
    def on_device_connected(self, device: iOSDevice):
        """设备连接时的处理"""
        # Check if this device is already connected to avoid duplicate notifications
        if device.udid in self.connected_devices:
            return
        
        # 添加到已连接设备列表
        self.connected_devices[device.udid] = device
        
        # 更新下拉框
        self.device_combo.addItem(
            f"{device.name} ({device.model})",
            device.udid
        )
        
        # 如果是第一个设备，自动选择
        if len(self.connected_devices) == 1:
            self.device_combo.setEnabled(True)
            self.device_combo.setCurrentIndex(0)
            self.current_device = device
            self.update_device_info(device)
            self.install_button.setEnabled(True)
            self.file_manager_button.setEnabled(True)
        else:
            # 多设备时，只更新状态标签
            self.status_label.setText(f"{len(self.connected_devices)} device(s) connected")
            self.status_label.setStyleSheet("color: green;")
        
        # 更新应用程序的当前设备（用于架构检查）
        try:
            from src.core.app import TweakEditorApp
            app_instance = TweakEditorApp.get_instance()
            if app_instance and self.current_device:
                app_instance.current_device = self.current_device
                self.log_text.append(f"[INFO] Device architecture: {self.current_device.cpu_architecture}")
        except Exception as e:
            self.log_text.append(f"[DEBUG] Failed to update app device: {e}")
        
        # 记录日志
        self.log_text.append(f"[CONNECTED] {device.name} ({device.model}) iOS {device.ios_version}")
        if device.is_jailbroken:
            self.log_text.append(f"[JAILBREAK] {device.jailbreak_type} mode detected")
        
        # Check if we're using limited info
        if hasattr(device, '_info_source') and 'Limited Info' in device._info_source:
            self.log_text.append("[INFO] Limited device information available")
            self.log_text.append("[INFO] To get full device details, install pymobiledevice3:")
            self.log_text.append("[INFO] pip install pymobiledevice3")
        
        # 发出信号
        self.device_connected.emit(device)
    
    def on_device_disconnected(self, device=None):
        """设备断开时的处理"""
        if device and device.udid in self.connected_devices:
            # 从设备列表中移除
            del self.connected_devices[device.udid]
            
            # 从下拉框中移除
            for i in range(self.device_combo.count()):
                if self.device_combo.itemData(i) == device.udid:
                    self.device_combo.removeItem(i)
                    break
            
            # 记录日志
            self.log_text.append(f"[DISCONNECTED] {device.name} ({device.model}) disconnected")
            
            # 如果是当前设备，需要处理
            if self.current_device and self.current_device.udid == device.udid:
                self.current_device = None
                
                # 如果还有其他设备，选择第一个
                if self.device_combo.count() > 0:
                    self.device_combo.setCurrentIndex(0)
                else:
                    # 没有设备了
                    self.status_label.setText(self.lang_mgr.get_text("no_device_connected"))
                    self.status_label.setStyleSheet("color: gray;")
                    self.device_info_widget.setVisible(False)
                    self.install_button.setEnabled(False)
                    self.file_manager_button.setEnabled(False)
                    self.device_combo.setEnabled(False)
        else:
            # 兼容旧代码
            self.current_device = None
            self.status_label.setText(self.lang_mgr.get_text("device_disconnected"))
            self.status_label.setStyleSheet("color: gray;")
            self.device_info_widget.setVisible(False)
            self.install_button.setEnabled(False)
            self.file_manager_button.setEnabled(False)
            self.log_text.append("[DISCONNECTED] Device disconnected")
        
        # 发出信号
        self.device_disconnected.emit()
    
    def on_monitoring_error(self):
        """监控错误时的处理"""
        self.status_label.setText("Device monitoring error - Click 'Refresh' to retry")
        self.status_label.setStyleSheet("color: orange;")
        self.log_text.append("[ERROR] Device monitoring stopped due to errors")
        self.log_text.append("[INFO] Common solutions:")
        self.log_text.append("[INFO] 1. Reconnect your iOS device")
        self.log_text.append("[INFO] 2. Make sure you clicked 'Trust' on the device")
        self.log_text.append("[INFO] 3. Install iTunes or Apple Devices for drivers")
        self.log_text.append("[INFO] 4. Try 'sudo killall usbmuxd' and reconnect (macOS)")
        self.log_text.append("[INFO] 5. Click 'Refresh' button to manually check")
    
    def install_deb_to_device(self):
        """安装 deb 到设备"""
        if not self.current_device:
            return
        
        # 检查设备越狱状态
        if not self.current_device.is_jailbroken:
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("jailbreak_required"),
                self.lang_mgr.get_text("jailbreak_required_message")
            )
            self.log_text.append("[ERROR] Device must be jailbroken to install .deb packages")
            self.log_text.append("[INFO] .deb packages are for jailbroken devices only")
            self.log_text.append("[INFO] For non-jailbroken devices:")
            self.log_text.append("[INFO] - Use App Store for official apps")
            self.log_text.append("[INFO] - Use TestFlight for beta apps")
            self.log_text.append("[INFO] - Use developer certificates for development")
            return
        
        # 检查是否有 lockdown client（完整功能需要）
        if not self.current_device.lockdown_client:
            reply = QMessageBox.question(
                self,
                "Limited Functionality",
                "Device communication is limited without pymobiledevice3.\n"
                "File transfer may not work properly.\n\n"
                "Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 选择 deb 文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .deb file to install",
            "",
            "Debian Package (*.deb)"
        )
        
        if not file_path:
            return
        
        # 分析 deb 文件的越狱兼容性
        from ..utils.deb_analyzer import DebAnalyzer
        success, deb_compat = DebAnalyzer.analyze_jailbreak_compatibility(file_path)
        
        # 获取设备的越狱类型
        device_jb_type = "Unknown"
        if self.current_device.is_jailbroken:
            if "Rootless" in self.current_device.jailbreak_type:
                device_jb_type = "Rootless"
            else:
                device_jb_type = "Rootful"
        
        # 检查兼容性
        compatibility_warning = None
        if success and deb_compat != "Unknown" and deb_compat != "Both":
            if device_jb_type != "Unknown" and device_jb_type != deb_compat:
                # 不兼容
                compatibility_warning = (
                    self.lang_mgr.get_text("jailbreak_mismatch_warning") or
                    f"⚠️ Warning: This package is designed for {deb_compat} jailbreak, "
                    f"but your device has {device_jb_type} jailbreak.\n\n"
                    f"The package may not work correctly.\n\n"
                    f"Do you want to continue?"
                )
        
        # 如果有兼容性警告，先显示警告
        if compatibility_warning:
            reply = QMessageBox.warning(
                self,
                self.lang_mgr.get_text("compatibility_warning") or "Compatibility Warning",
                compatibility_warning,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 原有的确认对话框（手动安装）
        message = f"{self.lang_mgr.get_text('upload_to_device') or 'Upload'} {os.path.basename(file_path)} to {self.current_device.name}?\n\n"
        if self.current_device.is_jailbroken:
            message += self.lang_mgr.get_text('auto_install_note') or "The app will attempt automatic installation after upload.\nIf auto-install fails, you can manually install from:\n"
            if "Rootless" in self.current_device.jailbreak_type:
                message += "/var/jb/var/mobile/Downloads/"
            else:
                message += "/var/mobile/Downloads/"
        else:
            message += self.lang_mgr.get_text('manual_install_note') or "You'll need to install it manually using a package manager."
        
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm"),
            message
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 开始安装
        self.install_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动安装线程
        self.install_thread = DeviceInstallThread(
            self.device_manager,
            self.current_device,
            file_path
        )
        
        self.install_thread.progress.connect(self.on_install_progress)
        self.install_thread.finished.connect(self.on_install_finished)
        self.install_thread.start()
        
        self.log_text.append(f"[INSTALL] Starting upload of {os.path.basename(file_path)}")
    
    
    
    def on_install_progress(self, percent: int, message: str):
        """安装进度更新"""
        self.progress_bar.setValue(percent)
        if message:
            self.log_text.append(f"[PROGRESS] {message}")
    
    def on_install_finished(self, success: bool, message: str):
        """安装完成"""
        self.install_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.log_text.append(f"[SUCCESS] {message}")
            QMessageBox.information(self, self.lang_mgr.get_text("success"), message)
        else:
            self.log_text.append(f"[ERROR] {message}")
            QMessageBox.critical(self, self.lang_mgr.get_text("error"), message)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止监控线程
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait(1000)  # 等待最多1秒
        
        # 停止设备监控
        if self.device_manager:
            self.device_manager.stop_monitoring()
        
        # 停止安装线程
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.wait()
        
        super().closeEvent(event)
    
    def refresh_devices(self):
        """手动刷新设备列表"""
        self.log_text.append("[INFO] Manually refreshing device list...")
        
        if not self.device_manager:
            self.log_text.append("[ERROR] Device manager not available")
            return
        
        # 尝试获取设备列表
        try:
            devices = self.device_manager.list_device_udids()
            self.log_text.append(f"[INFO] Found {len(devices)} device(s)")
            
            if devices:
                # 清除当前设备列表
                self.connected_devices.clear()
                self.device_combo.clear()
                
                # 获取所有设备的详细信息
                for udid in devices:
                    self.log_text.append(f"[INFO] Getting info for device: {udid}")
                    device_info = self.device_manager.get_device_info(udid)
                    if device_info:
                        self.log_text.append(f"[INFO] Device info retrieved: {device_info.name}")
                        self.on_device_connected(device_info)
                    else:
                        self.log_text.append(f"[ERROR] Could not get device information for {udid}")
            else:
                self.log_text.append("[INFO] No iOS devices detected")
                self.log_text.append("[INFO] Make sure your device is connected and unlocked")
                # 清空设备列表
                self.connected_devices.clear()
                self.device_combo.clear()
                self.on_device_disconnected()
                
        except Exception as e:
            self.log_text.append(f"[ERROR] Refresh failed: {str(e)}")
            self.log_text.append("[INFO] Try the troubleshooting steps mentioned above")
    
    def show_device_details(self):
        """显示设备详细信息"""
        if not self.current_device:
            return
        
        device = self.current_device
        
        # Format capacity values
        def format_bytes(bytes_value):
            if isinstance(bytes_value, (int, float)) and bytes_value > 0:
                gb = bytes_value / (1024 ** 3)
                return f"{gb:.2f} GB"
            return "Unknown"
        
        # Build detailed info text
        details = f"""
<h3>{self.lang_mgr.get_text('device_details')}</h3>

<b>{self.lang_mgr.get_text('basic_info')}:</b><br>
• {self.lang_mgr.get_text('device_name')}: {device.name}<br>
• {self.lang_mgr.get_text('model')}: {device.model}<br>
• {self.lang_mgr.get_text('ios_version')}: {device.ios_version}<br>
• {self.lang_mgr.get_text('build_version')}: {device.build_version}<br>
• {self.lang_mgr.get_text('serial_number')}: {device.serial_number}<br>
• UDID: {device.udid}<br>
<br>
<b>{self.lang_mgr.get_text('hardware_info')}:</b><br>
• {self.lang_mgr.get_text('device_class')}: {device.device_class}<br>
• {self.lang_mgr.get_text('hardware_model')}: {device.hardware_model}<br>
• {self.lang_mgr.get_text('cpu_architecture')}: {device.cpu_architecture}<br>
• {self.lang_mgr.get_text('chip_id')}: {device.chip_id}<br>
• {self.lang_mgr.get_text('product_name')}: {device.product_name}<br>
• {self.lang_mgr.get_text('model_number')}: {device.model_number}<br>
<br>
<b>{self.lang_mgr.get_text('network_info')}:</b><br>
• WiFi {self.lang_mgr.get_text('address')}: {device.wifi_address}<br>
• Bluetooth {self.lang_mgr.get_text('address')}: {device.bluetooth_address}<br>
• {self.lang_mgr.get_text('phone_number')}: {device.phone_number}<br>
• {self.lang_mgr.get_text('mobile_subscriber')}: {device.mobile_subscriber}<br>
<br>
<b>{self.lang_mgr.get_text('storage_info')}:</b><br>
• {self.lang_mgr.get_text('total_capacity')}: {format_bytes(device.total_disk_capacity)}<br>
• {self.lang_mgr.get_text('system_capacity')}: {format_bytes(device.total_system_capacity)}<br>
• {self.lang_mgr.get_text('data_capacity')}: {format_bytes(device.total_data_capacity)}<br>
<br>
<b>{self.lang_mgr.get_text('status_info')}:</b><br>
• {self.lang_mgr.get_text('activation_state')}: {device.activation_state}<br>
• {self.lang_mgr.get_text('battery_level')}: {device.battery_current_capacity}%<br>
• {self.lang_mgr.get_text('charging')}: {self.lang_mgr.get_text('yes') if device.battery_is_charging else self.lang_mgr.get_text('no')}<br>
• {self.lang_mgr.get_text('password_protected')}: {self.lang_mgr.get_text('yes') if device.password_protected else self.lang_mgr.get_text('no')}<br>
• {self.lang_mgr.get_text('paired')}: {self.lang_mgr.get_text('yes') if device.is_paired else self.lang_mgr.get_text('no')}<br>
<br>
<b>{self.lang_mgr.get_text('other_info')}:</b><br>
• {self.lang_mgr.get_text('device_color')}: {device.device_color}<br>
• {self.lang_mgr.get_text('enclosure_color')}: {device.device_enclosure_color}<br>
• {self.lang_mgr.get_text('region')}: {device.region_info}<br>
• {self.lang_mgr.get_text('baseband_version')}: {device.baseband_version}<br>
• {self.lang_mgr.get_text('firmware_version')}: {device.firmware_version}<br>
• MLB {self.lang_mgr.get_text('serial_number')}: {device.mlb_serial_number}<br>
• {self.lang_mgr.get_text('supports_app_install')}: {self.lang_mgr.get_text('yes') if device.supports_ios_app_installs else self.lang_mgr.get_text('no')}<br>
• {self.lang_mgr.get_text('device_certificate')}: {self.lang_mgr.get_text('yes') if device.device_certificate else self.lang_mgr.get_text('no')}<br>
"""
        
        # Add jailbreak details if available
        if device.is_jailbroken:
            details += f"""
<br>
<b>{self.lang_mgr.get_text('jailbreak_details') or 'Jailbreak Details'}:</b><br>
• {self.lang_mgr.get_text('jailbreak_type') or 'Type'}: {device.jailbreak_type}<br>
• {self.lang_mgr.get_text('package_manager') or 'Package Manager'}: {device.jailbreak_manager}<br>
• TrollStore: {self.lang_mgr.get_text('installed') if device.has_trollstore else self.lang_mgr.get_text('not_installed')}<br>
• RootHide: {self.lang_mgr.get_text('active') if device.has_roothide else self.lang_mgr.get_text('inactive')}<br>
"""
            if device.detected_jailbreak_paths:
                details += f"• {self.lang_mgr.get_text('detected_paths') or 'Detected Paths'}: {len(device.detected_jailbreak_paths)}<br>"
                details += "<small>"
                for path in device.detected_jailbreak_paths[:5]:  # Show first 5 paths
                    details += f"  - {path}<br>"
                if len(device.detected_jailbreak_paths) > 5:
                    details += f"  ... and {len(device.detected_jailbreak_paths) - 5} more<br>"
                details += "</small>"
        else:
            details += f"""
<br>
<b>{self.lang_mgr.get_text('jailbreak_details') or 'Jailbreak Details'}:</b><br>
• {self.lang_mgr.get_text('status')}: {self.lang_mgr.get_text('not_jailbroken')}<br>
"""
            if hasattr(device, 'has_trollstore') and device.has_trollstore:
                details += f"• TrollStore: {self.lang_mgr.get_text('installed')}<br>"
        
        details += """
"""
        
        # Create a dialog to show the details
        from PyQt6.QtWidgets import QDialog, QTextEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle(self.lang_mgr.get_text('device_details'))
        dialog.resize(600, 700)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(details)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def manual_jailbreak_confirm(self):
        """手动确认设备越狱状态"""
        if not self.current_device:
            return
        
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                    QRadioButton, QButtonGroup, QPushButton, 
                                    QTextEdit, QGroupBox)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manual Jailbreak Confirmation")
        dialog.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Information text
        info_label = QLabel(
            f"Device: {self.current_device.name}\n"
            f"Model: {self.current_device.model}\n"
            f"iOS: {self.current_device.ios_version}\n\n"
            "Automatic jailbreak detection failed. Please manually confirm "
            "your device's jailbreak status:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Jailbreak status group
        jb_group = QGroupBox("Jailbreak Status")
        jb_layout = QVBoxLayout()
        
        self.jb_button_group = QButtonGroup()
        
        # Not jailbroken option
        self.not_jb_radio = QRadioButton("Not Jailbroken")
        self.not_jb_radio.setChecked(True)  # Default selection
        self.jb_button_group.addButton(self.not_jb_radio, 0)
        jb_layout.addWidget(self.not_jb_radio)
        
        # Rootful jailbreak option
        self.rootful_radio = QRadioButton("Rootful Jailbreak (Traditional)")
        self.jb_button_group.addButton(self.rootful_radio, 1)
        jb_layout.addWidget(self.rootful_radio)
        
        # Rootless jailbreak option  
        self.rootless_radio = QRadioButton("Rootless Jailbreak (Modern)")
        self.jb_button_group.addButton(self.rootless_radio, 2)
        jb_layout.addWidget(self.rootless_radio)
        
        # Dopamine specific option
        self.dopamine_radio = QRadioButton("Dopamine Rootless Jailbreak")
        self.jb_button_group.addButton(self.dopamine_radio, 3)
        jb_layout.addWidget(self.dopamine_radio)
        
        jb_group.setLayout(jb_layout)
        layout.addWidget(jb_group)
        
        # Help text
        help_group = QGroupBox("How to Check")
        help_layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(120)
        help_text.setHtml(
            "<b>To verify your jailbreak status:</b><br><br>"
            "• <b>Not Jailbroken:</b> No jailbreak apps installed<br>"
            "• <b>Rootful:</b> Cydia/Sileo in /Applications/, system files writable<br>"
            "• <b>Rootless:</b> Jailbreak apps in /var/jb/, limited system access<br>"
            "• <b>Dopamine:</b> If you used Dopamine jailbreak tool specifically<br><br>"
            "<i>Check your home screen for Cydia, Sileo, Zebra, or other jailbreak apps.</i>"
        )
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("Confirm")
        confirm_btn.clicked.connect(dialog.accept)
        confirm_btn.setDefault(True)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Show dialog and process result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = self.jb_button_group.checkedId()
            
            if selected_id == 0:  # Not jailbroken
                self.current_device.is_jailbroken = False
                self.current_device.jailbreak_type = "None"
                self.jailbreak_label.setText("Not Jailbroken")
                self.jailbreak_label.setStyleSheet("color: orange;")
                self.log_text.append("[MANUAL] User confirmed: Device is not jailbroken")
                
            elif selected_id == 1:  # Rootful
                self.current_device.is_jailbroken = True
                self.current_device.jailbreak_type = "Rootful"
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_mode')}:</b> Rootful (Manual)"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: green;")
                self.log_text.append("[MANUAL] User confirmed: Rootful jailbreak")
                
            elif selected_id == 2:  # Rootless
                self.current_device.is_jailbroken = True
                self.current_device.jailbreak_type = "Rootless"
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_mode')}:</b> Rootless (Manual)"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: green;")
                self.log_text.append("[MANUAL] User confirmed: Rootless jailbreak")
                
            elif selected_id == 3:  # Dopamine
                self.current_device.is_jailbroken = True
                self.current_device.jailbreak_type = "Rootless (Dopamine)"
                jailbreak_text = f"<b>{self.lang_mgr.get_text('jailbreak_mode')}:</b> Rootless (Dopamine - Manual)"
                self.jailbreak_label.setText(jailbreak_text)
                self.jailbreak_label.setStyleSheet("color: green;")
                self.log_text.append("[MANUAL] User confirmed: Dopamine rootless jailbreak")
            
            # Disconnect the link handler to prevent re-triggering
            try:
                self.jailbreak_label.linkActivated.disconnect()
            except:
                pass
                
            # Re-emit device connected signal with updated info
            self.device_connected.emit(self.current_device)
            
            self.log_text.append("[INFO] Manual jailbreak confirmation completed")
            self.log_text.append("[INFO] You can now use device features based on confirmed status")
    
    def open_file_manager(self):
        """打开文件管理器"""
        if not self.current_device:
            QMessageBox.warning(
                self,
                self.lang_mgr.get_text("error") or "Error",
                self.lang_mgr.get_text("no_device_selected") or "No device selected"
            )
            return
        
        # 检查是否有 lockdown client
        if not self.current_device.lockdown_client:
            reply = QMessageBox.question(
                self,
                "Limited Functionality",
                "File Manager requires pymobiledevice3 for full functionality.\n"
                "Without it, file access will be very limited.\n\n"
                "Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            from .file_manager_widget import FileManagerWidget
            
            # 创建文件管理器窗口
            self.file_manager = FileManagerWidget(self.current_device, self.lang_mgr, self.style_mgr, self)
            
            # 连接文件双击信号（用于安装 .deb 文件）
            self.file_manager.file_double_clicked.connect(self.on_file_manager_deb_selected)
            
            # 显示窗口
            self.file_manager.show()
            
            self.log_text.append(f"[FILE MANAGER] Opened for {self.current_device.name}")
            
        except ImportError as e:
            self.log_text.append(f"[ERROR] Failed to import file manager: {e}")
            QMessageBox.critical(
                self,
                self.lang_mgr.get_text("error") or "Error",
                "File Manager module not available.\nPlease check the installation."
            )
        except Exception as e:
            self.log_text.append(f"[ERROR] Failed to open file manager: {e}")
            QMessageBox.critical(
                self,
                self.lang_mgr.get_text("error") or "Error",
                f"Failed to open file manager: {str(e)}"
            )
    
    def on_file_manager_deb_selected(self, deb_path: str):
        """处理文件管理器中选择的 .deb 文件"""
        self.log_text.append(f"[FILE MANAGER] Selected .deb file: {deb_path}")
        
        # 询问是否安装
        reply = QMessageBox.question(
            self,
            self.lang_mgr.get_text("confirm") or "Confirm",
            f"Install {os.path.basename(deb_path)} on device?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: 实现从设备路径直接安装的功能
            QMessageBox.information(
                self,
                "Info",
                "Direct installation from device path is not yet implemented.\n"
                "Please download the file first, then use the Upload button."
            )