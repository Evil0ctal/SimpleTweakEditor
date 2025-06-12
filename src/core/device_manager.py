# -*- coding: utf-8 -*-
"""
创建时间: 2025-01-06
作者: Evil0ctal

中文介绍:
iOS 设备管理器，使用 pymobiledevice3 与 iOS 设备通信，支持设备检测、文件传输和包安装

英文介绍:
iOS device manager, uses pymobiledevice3 to communicate with iOS devices, supports device detection, file transfer and package installation
"""

import os
import sys
import subprocess
import platform
from typing import Optional, List, Dict, Callable, TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass, field
import threading
import queue
from ..utils.debug_logger import debug

# Windows subprocess flags to prevent console windows
if platform.system() == 'Windows':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

# Import pymobiledevice3 modules
try:
    from pymobiledevice3.lockdown import LockdownClient
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    from pymobiledevice3.services.afc import AfcService
    from pymobiledevice3.services.diagnostics import DiagnosticsService
    from pymobiledevice3 import usbmux
    from pymobiledevice3.exceptions import *
    PYMOBILEDEVICE3_AVAILABLE = True
except ImportError:
    PYMOBILEDEVICE3_AVAILABLE = False
    print("[WARNING] pymobiledevice3 not installed. iOS device features will be disabled.")
    print("[WARNING] Install with: pip install pymobiledevice3")
    
    # Define dummy classes for type hints when pymobiledevice3 is not available
    if TYPE_CHECKING:
        LockdownClient = object
    else:
        class LockdownClient:
            pass


@dataclass
class iOSDevice:
    """iOS 设备信息"""
    udid: str
    name: str
    model: str
    ios_version: str
    is_jailbroken: bool = False
    jailbreak_type: str = "Unknown"  # Rootless or Rootful
    lockdown_client: Optional[object] = None
    
    # 越狱详细信息
    jailbreak_manager: str = "None"  # Cydia, Sileo, Zebra, etc.
    has_trollstore: bool = False
    has_roothide: bool = False
    detected_jailbreak_paths: List[str] = field(default_factory=list)  # 检测到的越狱路径
    
    # Extended device information
    device_class: str = "Unknown"
    hardware_model: str = "Unknown"
    cpu_architecture: str = "Unknown"
    product_name: str = "Unknown"
    build_version: str = "Unknown"
    serial_number: str = "Unknown"
    wifi_address: str = "Unknown"
    bluetooth_address: str = "Unknown"
    unique_device_id: str = "Unknown"
    region_info: str = "Unknown"
    model_number: str = "Unknown"
    phone_number: str = "Not Available"
    baseband_version: str = "Unknown"
    firmware_version: str = "Unknown"
    activation_state: str = "Unknown"
    device_color: str = "Unknown"
    device_enclosure_color: str = "Unknown"
    mlb_serial_number: str = "Unknown"
    total_disk_capacity: int = 0
    total_system_capacity: int = 0
    total_data_capacity: int = 0
    mobile_subscriber: str = "Unknown"
    battery_current_capacity: int = 0
    battery_is_charging: bool = False
    chip_id: str = "Unknown"
    device_certificate: bool = False
    supports_ios_app_installs: bool = True
    is_paired: bool = True
    password_protected: bool = False


class DeviceManager:
    """iOS 设备管理器"""
    
    def __init__(self):
        """初始化设备管理器"""
        self.current_device: Optional[iOSDevice] = None
        self.device_callback: Optional[Callable] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_running = False
        self.event_queue = queue.Queue()
        self._use_system_tools = False  # Flag to use system tools as fallback
        
        if not PYMOBILEDEVICE3_AVAILABLE:
            print("[ERROR] DeviceManager: pymobiledevice3 is not available")
        else:
            # Test if pymobiledevice3 works properly
            self._test_pymobiledevice3()
    
    def is_available(self) -> bool:
        """检查 pymobiledevice3 是否可用"""
        return PYMOBILEDEVICE3_AVAILABLE or self._check_system_tools()
    
    def _test_pymobiledevice3(self):
        """测试 pymobiledevice3 是否正常工作"""
        try:
            # Try to list devices
            devices = usbmux.list_devices()
            debug(f"pymobiledevice3 is working properly, found {len(devices)} device(s)")
            # Don't force system tools if pymobiledevice3 works
            self._use_system_tools = False
        except Exception as e:
            error_msg = str(e)
            if "stream.tell() failed" in error_msg:
                print(f"[WARNING] pymobiledevice3 has a known issue with construct library")
                print("[INFO] This is a common problem. The app will use system tools instead.")
                print("[INFO] To fix, try:")
                print("[INFO] 1. pip install 'construct==2.10.68' --force-reinstall")
                print("[INFO] 2. Restart the application")
            else:
                print(f"[WARNING] pymobiledevice3 connection test failed: {e}")
            print("[INFO] Will use system tools as fallback")
            self._use_system_tools = True
    
    def _check_system_tools(self) -> bool:
        """检查系统工具是否可用"""
        system = platform.system()
        
        if system == 'Darwin':
            # macOS: Check for system_profiler
            try:
                result = subprocess.run(['which', 'system_profiler'], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False
        
        elif system == 'Windows':
            # Windows: Check for PowerShell availability
            try:
                result = subprocess.run(['powershell', '-Command', 'echo test'], 
                                      capture_output=True, text=True,
                                      creationflags=CREATE_NO_WINDOW)
                return result.returncode == 0
            except:
                return False
                
        elif system == 'Linux':
            # Linux: Check for lsusb
            try:
                result = subprocess.run(['which', 'lsusb'], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False
        
        return False
    
    def start_monitoring(self, callback: Callable):
        """开始监控设备连接状态"""
        if not PYMOBILEDEVICE3_AVAILABLE:
            print("[INFO] Device monitoring disabled - pymobiledevice3 not available")
            return
        
        self.device_callback = callback
        self.monitor_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_devices)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        debug("Device monitoring started")
    
    def stop_monitoring(self):
        """停止监控设备"""
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        debug("Device monitoring stopped")
    
    def _monitor_devices(self):
        """监控设备连接状态（在后台线程运行）"""
        last_devices = set()
        error_count = 0
        max_errors = 5
        connected_devices = {}  # Track connected devices to avoid duplicates
        
        while self.monitor_running:
            try:
                current_devices = set(self.list_device_udids())
                
                # Reset error count on success
                error_count = 0
                
                # 检查新连接的设备
                new_devices = current_devices - last_devices
                for udid in new_devices:
                    # Skip if already connected
                    if udid in connected_devices:
                        continue
                        
                    device_info = self.get_device_info(udid)
                    if device_info:
                        self.current_device = device_info
                        connected_devices[udid] = device_info
                        if self.device_callback:
                            self.device_callback('connected', device_info)
                
                # 检查断开的设备
                disconnected = last_devices - current_devices
                for udid in disconnected:
                    if udid in connected_devices:
                        device = connected_devices.pop(udid)
                        if self.current_device and self.current_device.udid == udid:
                            if self.device_callback:
                                self.device_callback('disconnected', device)
                            self.current_device = None
                
                last_devices = current_devices
                
            except Exception as e:
                error_count += 1
                if error_count == 1:
                    print(f"[ERROR] Device monitoring error: {e}")
                
                # Stop monitoring after too many errors
                if error_count >= max_errors:
                    print(f"[ERROR] Device monitoring stopped after {max_errors} consecutive errors")
                    self.monitor_running = False
                    if self.device_callback:
                        self.device_callback('error', None)
                    break
            
            # 每秒检查一次
            import time
            time.sleep(1)
    
    def list_device_udids(self) -> List[str]:
        """列出所有连接的设备 UDID"""
        # Always try pymobiledevice3 first if available
        if PYMOBILEDEVICE3_AVAILABLE and not self._use_system_tools:
            try:
                # Use the usbmux module to list devices
                devices = usbmux.list_devices()
                if devices:
                    # Get UDIDs from device objects
                    udids = []
                    for device in devices:
                        # device might be a dict or object, handle both
                        if hasattr(device, 'identifier'):
                            udids.append(device.identifier)
                        elif hasattr(device, 'udid'):
                            udids.append(device.udid)
                        elif hasattr(device, 'serial'):
                            udids.append(device.serial)
                        elif isinstance(device, dict):
                            # Try different key names
                            udid = device.get('Identifier') or device.get('SerialNumber') or device.get('UDID')
                            if udid:
                                udids.append(udid)
                    
                    if udids:
                        debug(f"Found {len(udids)} device(s) via pymobiledevice3")
                        return udids
                    
            except Exception as e:
                error_msg = str(e)
                # Only print error once to avoid spam
                if not hasattr(self, '_device_error_shown'):
                    if "stream.tell() failed" in error_msg:
                        print(f"[INFO] pymobiledevice3 construct library issue detected")
                        print("[INFO] This is a known compatibility issue")
                        print("[INFO] Falling back to system tools for device detection")
                    else:
                        print(f"[ERROR] pymobiledevice3 failed to list devices: {e}")
                        print("[INFO] Falling back to system tools...")
                    self._device_error_shown = True
        
        # Fallback to system tools
        return self._list_devices_system()
    
    def _list_devices_system(self) -> List[str]:
        """使用系统工具列出设备"""
        system = platform.system()
        
        if system == 'Darwin':
            return self._list_devices_macos()
        elif system == 'Windows':
            return self._list_devices_windows()
        elif system == 'Linux':
            return self._list_devices_linux()
        else:
            return []
    
    def _list_devices_macos(self) -> List[str]:
        """macOS specific device listing"""
        
        # Try multiple methods
        devices = []
        seen_devices = set()  # Track unique devices
        
        # Method 1: Use ioreg to find iOS devices
        try:
            result = subprocess.run(
                ['ioreg', '-p', 'IOUSB', '-l', '-w', '0'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                import re
                # Look for iOS device entries
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'iPhone' in line or 'iPad' in line or 'iPod' in line:
                        # Look for USB Serial Number in nearby lines
                        for j in range(max(0, i-10), min(len(lines), i+10)):
                            # Try different patterns for serial number
                            patterns = [
                                r'"USB Serial Number"\s*=\s*"([^"]+)"',
                                r'"kUSBSerialNumberString"\s*=\s*"([^"]+)"',
                                r'"Serial Number"\s*=\s*"([^"]+)"'
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, lines[j])
                                if match:
                                    serial = match.group(1)
                                    # iOS device serials can be 24 or 40 chars
                                    if serial and (len(serial) == 24 or len(serial) == 40) and serial not in seen_devices:
                                        devices.append(serial)
                                        seen_devices.add(serial)
                                        debug(f"Found device via ioreg: {serial}")
                                        break
                            else:
                                continue
                            break
        except Exception as e:
            debug(f"ioreg method failed: {e}")
        
        # Method 2: Try system_profiler as backup
        if not devices:
            try:
                result = subprocess.run(
                    ['system_profiler', 'SPUSBDataType', '-json'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    import json
                    data = json.loads(result.stdout)
                    
                    # Parse USB data to find iOS devices
                    def find_ios_devices(items):
                        for item in items:
                            if isinstance(item, dict):
                                # Check if it's an Apple device
                                vendor = item.get('manufacturer', '').lower()
                                name = item.get('_name', '').lower()
                                
                                if 'apple' in vendor and any(ios in name for ios in ['iphone', 'ipad', 'ipod']):
                                    # Try to get serial number
                                    serial = item.get('serial_num', '')
                                    # iOS device serials can be 24 or 40 chars
                                    if serial and (len(serial) == 24 or len(serial) == 40) and serial not in seen_devices:
                                        devices.append(serial)
                                        seen_devices.add(serial)
                                        debug(f"Found device via system_profiler: {serial}")
                                
                                # Recursively check nested items
                                if '_items' in item:
                                    find_ios_devices(item['_items'])
                    
                    for usb_data in data.get('SPUSBDataType', []):
                        if '_items' in usb_data:
                            find_ios_devices(usb_data['_items'])
                            
            except Exception as e:
                debug(f"system_profiler method failed: {e}")
        
        if devices:
            print(f"[INFO] Found {len(devices)} device(s) using system tools")
        
        return devices
    
    def _list_devices_windows(self) -> List[str]:
        """Windows specific device listing"""
        devices = []
        seen_devices = set()
        
        # Try using PowerShell to find iOS devices
        try:
            # Get USB devices via WMI
            ps_script = '''
            Get-WmiObject Win32_PnPEntity | Where-Object {
                $_.Name -match "Apple" -or $_.Name -match "iPhone" -or 
                $_.Name -match "iPad" -or $_.Name -match "iPod"
            } | Select-Object Name, DeviceID, Manufacturer
            '''
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'USB\\VID_05AC' in line:  # Apple Vendor ID
                        # Extract serial from DeviceID if possible
                        import re
                        match = re.search(r'\\([A-F0-9]{24,40})(?:\\|$)', line)
                        if match:
                            serial = match.group(1)
                            if serial not in seen_devices:
                                devices.append(serial)
                                seen_devices.add(serial)
                                debug(f"Found device via PowerShell: {serial}")
        except Exception as e:
            debug(f"PowerShell method failed: {e}")
        
        # Alternative: Try using wmic
        if not devices:
            try:
                result = subprocess.run(
                    ['wmic', 'path', 'Win32_PnPEntity', 'where', 
                     'Name like "%Apple%" or Name like "%iPhone%" or Name like "%iPad%"',
                     'get', 'Name,DeviceID', '/format:list'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    # Parse output to find devices
                    for line in result.stdout.split('\n'):
                        if 'DeviceID=' in line and 'USB' in line:
                            # Try to extract useful info
                            debug(f"Found USB device: {line.strip()}")
            except Exception as e:
                debug(f"WMIC method failed: {e}")
        
        if devices:
            print(f"[INFO] Found {len(devices)} device(s) using Windows tools")
        
        return devices
    
    def _list_devices_linux(self) -> List[str]:
        """Linux specific device listing"""
        devices = []
        seen_devices = set()
        
        # Try using lsusb
        try:
            result = subprocess.run(
                ['lsusb', '-v'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                apple_device = False
                
                for line in lines:
                    # Look for Apple vendor ID
                    if 'idVendor' in line and '0x05ac Apple' in line:
                        apple_device = True
                    elif apple_device and 'iSerial' in line:
                        # Extract serial number
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            serial = parts[2]
                            if len(serial) in [24, 40] and serial not in seen_devices:
                                devices.append(serial)
                                seen_devices.add(serial)
                                debug(f"Found device via lsusb: {serial}")
                        apple_device = False
                    elif 'Bus' in line:
                        apple_device = False
        except Exception as e:
            debug(f"lsusb method failed: {e}")
        
        # Alternative: Check /sys/bus/usb/devices/
        if not devices:
            try:
                import glob
                for device_path in glob.glob('/sys/bus/usb/devices/*/serial'):
                    try:
                        # Check if it's an Apple device
                        vendor_path = device_path.replace('/serial', '/idVendor')
                        if os.path.exists(vendor_path):
                            with open(vendor_path, 'r') as f:
                                vendor = f.read().strip()
                            
                            if vendor == '05ac':  # Apple vendor ID
                                with open(device_path, 'r') as f:
                                    serial = f.read().strip()
                                
                                if len(serial) in [24, 40] and serial not in seen_devices:
                                    devices.append(serial)
                                    seen_devices.add(serial)
                                    debug(f"Found device via sysfs: {serial}")
                    except:
                        pass
            except Exception as e:
                debug(f"sysfs method failed: {e}")
        
        if devices:
            print(f"[INFO] Found {len(devices)} device(s) using Linux tools")
        
        return devices
    
    def _get_device_info_from_ioreg(self, udid: str) -> Dict[str, str]:
        """尝试从 ioreg 获取设备信息"""
        info = {
            'name': 'iPhone',
            'model': 'iPhone',
            'version': 'Unknown'
        }
        
        if platform.system() != 'Darwin':
            return info
        
        try:
            # First try to get more detailed info from ioreg
            result = subprocess.run(
                ['ioreg', '-p', 'IOUSB', '-l', '-w', '0'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                import re
                lines = result.stdout.split('\n')
                device_found = False
                device_block = []
                
                for i, line in enumerate(lines):
                    # Look for our device by serial number
                    if udid in line:
                        device_found = True
                        # Look backwards to find the start of this device block
                        for j in range(i, max(0, i-20), -1):
                            if 'class IOUSBHostDevice' in lines[j]:
                                device_block = lines[j:i+30]  # Get context around device
                                break
                    
                    if device_found and device_block:
                        # Extract all available info from device block
                        for block_line in device_block:
                            # Product name
                            match = re.search(r'"USB Product Name"\s*=\s*"([^"]+)"', block_line)
                            if match:
                                info['name'] = match.group(1)
                            
                            # Serial number verification
                            match = re.search(r'"USB Serial Number"\s*=\s*"([^"]+)"', block_line)
                            if match and match.group(1) == udid:
                                info['serial_verified'] = True
                            
                            # Vendor/Product IDs for model detection
                            match = re.search(r'"idProduct"\s*=\s*(\d+)', block_line)
                            if match:
                                product_id = int(match.group(1))
                                info['model'] = self._get_model_from_product_id(product_id)
                            
                            # Firmware version from location ID
                            match = re.search(r'"USB Address"\s*=\s*(\d+)', block_line)
                            if match:
                                info['usb_address'] = match.group(1)
                        
                        break
                
                # Try system_profiler for more info
                result2 = subprocess.run(
                    ['system_profiler', 'SPUSBDataType', '-detailLevel', 'full'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=CREATE_NO_WINDOW
                )
                
                if result2.returncode == 0 and udid in result2.stdout:
                    # Parse additional info
                    lines2 = result2.stdout.split('\n')
                    for i, line in enumerate(lines2):
                        if udid in line:
                            # Look for device info in surrounding lines
                            for j in range(max(0, i-10), min(len(lines2), i+10)):
                                if 'Version:' in lines2[j]:
                                    match = re.search(r'Version:\s*(.+)', lines2[j])
                                    if match:
                                        info['version'] = match.group(1).strip()
                                elif 'Manufacturer:' in lines2[j]:
                                    match = re.search(r'Manufacturer:\s*(.+)', lines2[j])
                                    if match:
                                        info['manufacturer'] = match.group(1).strip()
                
                debug(f"Enhanced device info from ioreg: {info}")
                
        except Exception as e:
            debug(f"Failed to get device info from ioreg: {e}")
        
        return info
    
    def _get_model_from_product_id(self, product_id: int) -> str:
        """根据 USB Product ID 获取设备型号"""
        # Apple USB Product IDs (incomplete list)
        product_map = {
            0x12a8: "iPhone",  # iPhone (various models)
            0x12a0: "iPhone",  # iPhone 4
            0x12a2: "iPhone",  # iPhone 4S
            0x12a4: "iPhone",  # iPhone 5
            0x12a6: "iPhone",  # iPhone 5C/5S
            0x12aa: "iPhone",  # iPhone 6/6 Plus
            0x12ab: "iPhone",  # iPhone 6S/6S Plus
            0x12ac: "iPhone",  # iPhone SE
            0x12ad: "iPhone",  # iPhone 7/7 Plus
            0x12ae: "iPhone",  # iPhone 8/8 Plus/X
            0x12af: "iPhone",  # iPhone XS/XS Max/XR
            0x12b0: "iPhone",  # iPhone 11 series
            0x12b1: "iPhone",  # iPhone 12 series
            0x12b2: "iPhone",  # iPhone 13 series
            0x12b3: "iPhone",  # iPhone 14 series
            0x12b4: "iPhone",  # iPhone 15 series
            0x129a: "iPad",    # iPad (various models)
            0x129c: "iPad",    # iPad Mini
            0x129e: "iPad",    # iPad Air
            0x129f: "iPad",    # iPad Pro
        }
        
        return product_map.get(product_id, "iPhone")
    
    def get_device_info(self, udid: str) -> Optional[iOSDevice]:
        """获取设备详细信息"""
        # Always try pymobiledevice3 first if available
        if PYMOBILEDEVICE3_AVAILABLE and not self._use_system_tools:
            try:
                # Use LockdownClient directly with UDID
                lockdown = LockdownClient(serial=udid)
                
                # 获取设备所有信息
                device_info = lockdown.all_values
                
                # Get more device information
                device = iOSDevice(
                    udid=udid,
                    name=device_info.get('DeviceName', 'Unknown'),
                    model=device_info.get('ProductType', 'Unknown'),
                    ios_version=device_info.get('ProductVersion', 'Unknown'),
                    lockdown_client=lockdown
                )
                
                # Store additional device info
                device.device_class = device_info.get('DeviceClass', 'Unknown')
                device.hardware_model = device_info.get('HardwareModel', 'Unknown')
                device.cpu_architecture = device_info.get('CPUArchitecture', 'Unknown')
                device.product_name = device_info.get('ProductName', 'Unknown')
                device.build_version = device_info.get('BuildVersion', 'Unknown')
                device.serial_number = device_info.get('SerialNumber', udid[:12] + '...')
                device.wifi_address = device_info.get('WiFiAddress', 'Unknown')
                device.bluetooth_address = device_info.get('BluetoothAddress', 'Unknown')
                device.unique_device_id = device_info.get('UniqueDeviceID', udid)
                device.region_info = device_info.get('RegionInfo', 'Unknown')
                device.model_number = device_info.get('ModelNumber', 'Unknown')
                device.phone_number = device_info.get('PhoneNumber', 'Not Available')
                device.baseband_version = device_info.get('BasebandVersion', 'Unknown')
                device.firmware_version = device_info.get('FirmwareVersion', 'Unknown')
                device.activation_state = device_info.get('ActivationState', 'Unknown')
                # 设备颜色处理
                device_color = device_info.get('DeviceColor', 'Unknown')
                if device_color == '1':
                    device.device_color = 'Black'
                elif device_color == '2':
                    device.device_color = 'White'
                elif device_color == '3':
                    device.device_color = 'Red'
                elif device_color == '4':
                    device.device_color = 'Pink'
                elif device_color == '5':
                    device.device_color = 'Yellow'
                elif device_color == '6':
                    device.device_color = 'Blue'
                elif device_color == '7':
                    device.device_color = 'Green'
                elif device_color.startswith('#'):
                    device.device_color = f'Hex: {device_color}'
                else:
                    device.device_color = device_color
                    
                device.device_enclosure_color = device_info.get('DeviceEnclosureColor', device.device_color)
                device.mlb_serial_number = device_info.get('MLBSerialNumber', 'Unknown')
                device.total_disk_capacity = device_info.get('TotalDiskCapacity', 0)
                device.total_system_capacity = device_info.get('TotalSystemCapacity', 0)
                device.total_data_capacity = device_info.get('TotalDataCapacity', 0)
                device.mobile_subscriber = device_info.get('MobileSubscriberCountryCode', 'Unknown')
                
                # 尝试获取电池信息和 MobileGestalt 信息
                try:
                    from pymobiledevice3.services.diagnostics import DiagnosticsService
                    diag = DiagnosticsService(lockdown)
                    
                    # 获取电池信息
                    battery_info = diag.get_battery()
                    if battery_info:
                        # 使用正确的键名
                        device.battery_current_capacity = battery_info.get('CurrentCapacity', 0)
                        device.battery_is_charging = battery_info.get('IsCharging', False)
                        debug(f"Battery info: {device.battery_current_capacity}%, Charging: {device.battery_is_charging}")
                    else:
                        device.battery_current_capacity = 0
                        device.battery_is_charging = False
                        
                    # 尝试从 MobileGestalt 获取额外信息（包括存储信息）
                    try:
                        mg_info = diag.mobilegestalt(['DiskUsage', 'DeviceCapacity', 'DeviceCapacityString'])
                        if mg_info:
                            debug(f"MobileGestalt info: {mg_info}")
                            if 'DiskUsage' in mg_info and mg_info['DiskUsage']:
                                disk_usage = mg_info['DiskUsage']
                                if isinstance(disk_usage, dict):
                                    # 如果 DiskUsage 是字典，尝试获取存储信息
                                    if disk_usage.get('TotalDiskCapacity', 0) > 0:
                                        device.total_disk_capacity = disk_usage.get('TotalDiskCapacity', device.total_disk_capacity)
                                    if disk_usage.get('TotalSystemCapacity', 0) > 0:
                                        device.total_system_capacity = disk_usage.get('TotalSystemCapacity', device.total_system_capacity)
                                    if disk_usage.get('TotalDataCapacity', 0) > 0:
                                        device.total_data_capacity = disk_usage.get('TotalDataCapacity', device.total_data_capacity)
                                    debug(f"Got storage info from MobileGestalt: {device.total_disk_capacity} bytes")
                    except Exception as e:
                        debug(f"Failed to get MobileGestalt info: {e}")
                        
                except Exception as e:
                    debug(f"Failed to get diagnostics info: {e}")
                    device.battery_current_capacity = 0
                    device.battery_is_charging = False
                device.chip_id = device_info.get('ChipID', 'Unknown')
                device.device_certificate = bool(device_info.get('DeviceCertificate', False))
                device.supports_ios_app_installs = device_info.get('SupportsIOSAppInstalls', True)
                device.is_paired = device_info.get('IsPaired', True)
                device.password_protected = device_info.get('PasswordProtected', False)
                
                # 检测越狱状态
                debug(f"Starting jailbreak detection for device: {device.name}")
                jb_result = self._detect_jailbreak_detailed(lockdown)
                device.is_jailbroken = jb_result["jailbroken"]
                device.jailbreak_type = jb_result["jailbreak_type"]
                device.jailbreak_manager = jb_result.get("manager", "None")
                device.has_trollstore = jb_result.get("has_trollstore", False)
                device.has_roothide = jb_result.get("has_roothide", False)
                device.detected_jailbreak_paths = jb_result.get("detected_flags", [])
                debug(f"Jailbreak detection result: {jb_result}")
                
                debug(f"Device info: {device.name} ({device.model}) iOS {device.ios_version}")
                debug(f"Jailbreak status: {device.is_jailbroken} ({device.jailbreak_type})")
                
                return device
                
            except Exception as e:
                print(f"[WARNING] pymobiledevice3 failed to get device info: {e}")
                # Fall through to basic info
        
        # Return basic device info when pymobiledevice3 fails
        print(f"[INFO] Using basic device info for UDID: {udid}")
        
        # Try to get more info from ioreg
        ioreg_info = self._get_device_info_from_ioreg(udid)
        
        # Create device with enhanced basic info
        device = iOSDevice(
            udid=udid,
            name=ioreg_info.get('name', 'iPhone'),
            model=ioreg_info.get('model', 'iPhone'),
            ios_version=ioreg_info.get('version', 'Unknown'),
            is_jailbroken=False,
            jailbreak_type="Unknown",
            lockdown_client=None
        )
        
        # Set additional fields with reasonable defaults or from ioreg
        device.device_class = "iPhone"
        device.hardware_model = ioreg_info.get('model', 'Unknown')
        device.cpu_architecture = "arm64"  # Most modern iOS devices
        device.product_name = ioreg_info.get('name', 'iPhone')
        device.build_version = "Unknown"
        device.serial_number = udid[:12] + '...' if len(udid) > 12 else udid
        device.wifi_address = "Unknown"
        device.bluetooth_address = "Unknown"
        device.unique_device_id = udid
        device.region_info = "Unknown"
        device.model_number = "Unknown"
        device.phone_number = "Not Available"
        device.baseband_version = "Unknown"
        device.firmware_version = "Unknown"
        device.activation_state = "Activated"  # Assume activated if connected
        device.device_color = "Unknown"
        device.device_enclosure_color = "Unknown"
        device.mlb_serial_number = "Unknown"
        device.total_disk_capacity = 0
        device.total_system_capacity = 0
        device.total_data_capacity = 0
        device.mobile_subscriber = "Unknown"
        device.battery_current_capacity = 0
        device.battery_is_charging = False
        device.chip_id = "Unknown"
        device.device_certificate = False
        device.supports_ios_app_installs = True
        device.is_paired = True  # Must be paired if we can see it
        device.password_protected = True  # Assume protected for security
        
        # Try to detect jailbreak even without full pymobiledevice3
        device.is_jailbroken, device.jailbreak_type = self._detect_jailbreak_system_tools(udid)
        
        # Add note about limited info
        device._info_source = "System Tools (Limited Info)"
        
        print(f"[INFO] Basic device info created with defaults")
        
        return device
    
    def _detect_jailbreak_system_tools(self, udid: str) -> tuple[bool, str]:
        """使用系统工具检测越狱状态"""
        # 注意：系统工具无法直接访问设备文件系统
        # 但可以通过其他方式推断越狱状态
        
        try:
            # 方法1：检查 iTunes 备份中的越狱指标
            # 方法2：检查设备安装的应用列表
            # 方法3：根据系统版本和已知越狱工具推断
            
            # 暂时返回假定的越狱状态
            # 在实际使用中，用户可以通过界面手动确认
            print(f"[INFO] Cannot detect jailbreak status without pymobiledevice3")
            print(f"[INFO] Please manually verify if device is jailbroken")
            
            # 返回未知状态，让用户在界面中手动确认
            return False, "Unknown - Manual Check Required"
            
        except Exception as e:
            debug(f"System tools jailbreak detection failed: {e}")
            return False, "Unknown"
    
    def _detect_jailbreak_detailed(self, lockdown: 'LockdownClient') -> dict:
        """检测设备是否越狱及越狱类型 - 全面统一方案"""
        try:
            # 首先尝试使用 AFC2 服务（越狱设备才有）
            afc = None
            try:
                # AFC2 服务允许访问整个文件系统
                debug("Trying to connect to AFC2 service (com.apple.afc2)...")
                afc = AfcService(lockdown, service_name="com.apple.afc2")
                debug("✅ AFC2 service connected - device might be jailbroken")
            except Exception as e:
                debug(f"AFC2 service not available: {str(e)[:50]}")
                # 退回到普通 AFC 服务
                try:
                    debug("Falling back to regular AFC service...")
                    afc = AfcService(lockdown)
                    debug("Using regular AFC service (limited access)")
                except Exception as e2:
                    debug(f"Failed to connect to any AFC service: {e2}")
                    raise
            
            # 完整的检测结果
            result = {
                "jailbroken": False,
                "jailbreak_type": "None",
                "manager": "None",
                "detected_flags": [],
                "has_roothide": False,
                "has_trollstore": False
            }
            
            # Legacy / Rootful 越狱检测路径（包括 Cydia, Substrate）
            ROOTFUL_PATHS = [
                "/Applications/Cydia.app",              # 传统越狱 Cydia
                "/Applications/Sileo.app",              # 传统越狱 Sileo
                "/Applications/Zebra.app",              # 传统越狱 Zebra
                "/Library/MobileSubstrate/MobileSubstrate.dylib",  # Substrate
                "/usr/libexec/substitute-inserter",    # Substitute
                "/usr/sbin/sshd",                       # SSH 守护进程
                "/etc/apt",                             # APT 配置
                "/var/lib/cydia",                       # Cydia 数据
                "/var/lib/dpkg/info/com.saurik.cydia.list",  # Cydia 包信息
                "/usr/libexec/cydia",                   # Cydia 核心
                "/usr/bin/dpkg",                        # dpkg 命令
                "/var/lib/dpkg",                        # dpkg 数据库
                "/usr/lib/libsubstrate.dylib",         # Substrate 库
                "/usr/bin/cycript",                     # Cycript
                "/usr/lib/libcycript.dylib",            # Cycript 库
                "/private/var/lib/apt",                 # APT 包管理器
            ]
            
            # Rootless 越狱检测路径（包括 Dopamine, Ellekit）
            ROOTLESS_PATHS = [
                "/var/jb/",                             # 标准 Rootless 路径
                "/var/jb/Applications/Sileo.app",       # Rootless Sileo
                "/var/jb/Applications/Cydia.app",       # Rootless Cydia
                "/var/jb/Applications/Zebra.app",       # Rootless Zebra
                "/var/jb/usr/libexec/ellekit",         # Ellekit
                "/var/jb/usr/lib/TweakInject",         # 插件注入目录
                "/var/jb/etc/apt",                      # Rootless APT
                "/var/jb/var/mobile/Library/Sileo/",   # Sileo 数据
                "/var/jb/Library/MobileSubstrate/DynamicLibraries",  # Rootless MS
                "/var/jb/usr/bin/dpkg",                 # Rootless dpkg
                "/var/jb/Library/LaunchDaemons",        # Rootless 守护进程
                "/var/containers/Bundle/Application/.jbroot",  # 另一种 Rootless
                "/jb",                                  # 简短 Rootless 路径
            ]
            
            # Dopamine 特定路径
            DOPAMINE_PATHS = [
                "/var/jb/usr/libexec/dopamine",         # Dopamine 主程序
                "/var/jb/Applications/Dopamine.app",    # Dopamine 应用
                "/var/jb/.installed_dopamine",          # Dopamine 安装标记
                "/var/jb/basebin",                      # Dopamine basebin
            ]
            
            # TrollStore 检测路径（伪越狱）
            TROLLSTORE_PATHS = [
                "/var/mobile/Library/TrollStore/",      # TrollStore 主目录
                "/private/var/mobile/Library/TrollStore/installed_apps.plist",  # 已安装应用
                "/var/mobile/Containers/Data/SystemGroup/TrollStore/",  # TrollStore 数据
                "/Applications/TrollStore.app",         # TrollStore 应用（某些版本）
            ]
            
            # RootHide 检测路径
            ROOTHIDE_PATHS = [
                "/etc/roothide",                        # RootHide 配置
                "/var/jb/etc/roothide",                 # Rootless RootHide
                "/var/roothide_hook_status",            # RootHide 状态
                "/usr/lib/roothide",                    # RootHide 库
                "/var/mobile/Library/RootHide",         # RootHide 用户数据
            ]
            
            # 管理器和插件识别关键词（包含 Cydia）
            MANAGER_PATTERNS = {
                "Cydia": ["Cydia.app", "lib/cydia", "var/lib/cydia", "cydia"],
                "Sileo": ["Sileo.app", "Library/Sileo", "sileo"],
                "Zebra": ["Zebra.app", "zebra"],
                "Installer": ["Installer.app", "installer"],
                "Ellekit": ["ellekit", "libellkit"],
                "Substitute": ["substitute-inserter", "substitute"],
                "Substrate": ["MobileSubstrate", "substrate.dylib"],
                "AppSync": ["AppSync Unified", "lib/AppSyncUnified", "appsync"],
            }
            
            # 检测函数
            def check_paths(paths: list, type_label: str):
                debug(f"Checking {type_label} paths...")
                for path in paths:
                    try:
                        afc.stat(path)
                        result["jailbroken"] = True
                        if result["jailbreak_type"] == "None":
                            result["jailbreak_type"] = type_label
                        result["detected_flags"].append(path)
                        debug(f"✅ Found {type_label} indicator: {path}")
                    except Exception as e:
                        debug(f"❌ Not found: {path} - {str(e)[:50]}")
            
            # 执行检测
            check_paths(ROOTFUL_PATHS, "Rootful")
            check_paths(ROOTLESS_PATHS, "Rootless")
            
            # 检测 Dopamine
            debug("Checking Dopamine-specific paths...")
            for path in DOPAMINE_PATHS:
                try:
                    afc.stat(path)
                    result["jailbroken"] = True
                    result["jailbreak_type"] = "Rootless (Dopamine)"
                    result["detected_flags"].append(path)
                    debug(f"✅ Found Dopamine indicator: {path}")
                except Exception as e:
                    debug(f"❌ Dopamine path not found: {path} - {str(e)[:50]}")
            
            # 检测 TrollStore
            for path in TROLLSTORE_PATHS:
                try:
                    afc.stat(path)
                    result["has_trollstore"] = True
                    result["detected_flags"].append(path)
                    debug(f"Found TrollStore indicator: {path}")
                    # TrollStore 不算真正的越狱
                    if not result["jailbroken"]:
                        result["jailbreak_type"] = "TrollStore Only"
                except:
                    pass
            
            # 检测 RootHide
            for path in ROOTHIDE_PATHS:
                try:
                    afc.stat(path)
                    result["has_roothide"] = True
                    result["detected_flags"].append(path)
                    debug(f"Found RootHide indicator: {path}")
                    if result["jailbreak_type"] != "None" and result["jailbreak_type"] != "TrollStore Only":
                        result["jailbreak_type"] += " + RootHide"
                except:
                    pass
            
            # 检测管理器/插件
            for manager, keywords in MANAGER_PATTERNS.items():
                if any(any(keyword in flag for keyword in keywords) for flag in result["detected_flags"]):
                    result["manager"] = manager
                    break
            
            # 构建最终结果
            jailbreak_type = result["jailbreak_type"]
            
            # 添加管理器信息到类型描述
            if result["manager"] != "None" and result["manager"] not in jailbreak_type:
                jailbreak_type = f"{jailbreak_type} ({result['manager']})"
            
            # 如果文件系统检测没有发现越狱，尝试通过应用列表检测
            if not result["jailbroken"]:
                debug("No jailbreak detected via filesystem, checking installed apps...")
                try:
                    from pymobiledevice3.services.installation_proxy import InstallationProxyService
                    installation = InstallationProxyService(lockdown)
                    
                    # 获取用户安装的应用
                    apps = installation.get_apps(app_types=["User"])
                    jb_apps = {
                        "com.saurik.Cydia": ("Cydia", "Rootful"),
                        "org.coolstar.SileoStore": ("Sileo", "Unknown"),
                        "com.opa334.trollstorehelper": ("TrollStore", "TrollStore"),
                        "com.opa334.TrollStore": ("TrollStore", "TrollStore"),
                        "xyz.willy.Zebra": ("Zebra", "Unknown"),
                        "me.apptapp.installer": ("Installer", "Unknown"),
                        "com.saurik.WinterBoard": ("WinterBoard", "Rootful"),
                        "com.exile90.icleanerpro": ("iCleaner Pro", "Unknown"),
                        "com.tigisoftware.Filza": ("Filza", "Unknown"),
                        "net.angelxwind.appsyncunified": ("AppSync", "Unknown"),
                    }
                    
                    for bundle_id, (app_name, jb_type) in jb_apps.items():
                        if bundle_id in apps:
                            debug(f"✅ Found jailbreak app: {app_name} ({bundle_id})")
                            result["jailbroken"] = True
                            result["manager"] = app_name
                            if result["jailbreak_type"] == "None" and jb_type != "Unknown":
                                result["jailbreak_type"] = jb_type
                            elif result["jailbreak_type"] == "None":
                                result["jailbreak_type"] = "Unknown (App-based detection)"
                            result["detected_flags"].append(f"App: {app_name}")
                            
                except Exception as e:
                    debug(f"Failed to check installed apps: {e}")
            
            # 记录详细检测结果
            if result["jailbroken"]:
                debug(f"Jailbreak detected: {jailbreak_type}")
                debug(f"Manager: {result['manager']}")
                debug(f"Detected paths: {result['detected_flags']}")
            else:
                debug("No jailbreak detected")
            
            # 更新结果中的最终越狱类型
            result["jailbreak_type"] = jailbreak_type
            
            # 返回完整结果
            return result
                
        except Exception as e:
            debug(f"Jailbreak detection failed: {e}")
            return {
                "jailbroken": False,
                "jailbreak_type": "Unknown",
                "manager": "None",
                "detected_flags": [],
                "has_roothide": False,
                "has_trollstore": False
            }
    
    def _detect_jailbreak(self, lockdown: 'LockdownClient') -> tuple[bool, str]:
        """检测设备是否越狱及越狱类型（向后兼容）"""
        result = self._detect_jailbreak_detailed(lockdown)
        return result["jailbroken"], result["jailbreak_type"]
    
    def _try_ssh_install(self, device: iOSDevice, deb_path: str, install_cmd: str) -> bool:
        """尝试通过 SSH 安装（需要设备安装 OpenSSH）"""
        try:
            # 获取设备 IP
            device_ip = device.wifi_address
            if device_ip == "Unknown" or not device_ip:
                debug("Cannot get device IP for SSH")
                return False
            
            # 尝试通过 USB 端口转发（更可靠）
            try:
                from pymobiledevice3.services.os_trace import OsTraceService
                # 这里我们实际上不能直接 SSH，但可以尝试其他方法
                debug("Direct SSH not available through pymobiledevice3")
                return False
            except:
                return False
                
        except Exception as e:
            debug(f"SSH installation failed: {e}")
            return False
    
    def _auto_install_deb(self, device: iOSDevice, deb_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """尝试自动安装 deb 包"""
        try:
            # 根据越狱类型确定 dpkg 路径
            if "Rootless" in device.jailbreak_type or "Dopamine" in device.jailbreak_type:
                dpkg_path = "/var/jb/usr/bin/dpkg"
                # 对于 Rootless，需要特殊处理
                install_cmd = f"{dpkg_path} -i {deb_path}"
            else:
                dpkg_path = "/usr/bin/dpkg"
                install_cmd = f"{dpkg_path} -i {deb_path}"
            
            debug(f"Attempting to install with command: {install_cmd}")
            
            # 尝试使用 com.apple.mobile.installation_proxy 服务
            # 注意：这通常需要特殊权限或越狱工具的支持
            
            # 方法1：尝试通过 SSH（如果已安装 OpenSSH）
            ssh_success = self._try_ssh_install(device, deb_path, install_cmd)
            if ssh_success:
                return True
            
            # 方法2：创建安装脚本
            try:
                afc = AfcService(device.lockdown_client, service_name="com.apple.afc2")
                
                # 创建一个安装脚本
                script_content = f"""#!/bin/sh
# Auto-install script created by SimpleTweakEditor
echo "Installing {os.path.basename(deb_path)}..."
{install_cmd}
echo "Installation complete!"
rm -f "$0"  # 删除脚本自身
"""
                
                script_path = "/var/mobile/install_deb.sh"
                if "Rootless" in device.jailbreak_type:
                    script_path = "/var/jb/var/mobile/install_deb.sh"
                
                # 写入脚本
                afc.set_file_contents(script_path, script_content.encode('utf-8'))
                
                debug(f"Created install script at: {script_path}")
                debug("Note: You need to execute this script on device to complete installation")
                
                if progress_callback:
                    progress_callback(95, f"Install script created at {script_path}")
                
                return False  # 仍然需要手动执行
                
            except Exception as e:
                debug(f"Failed to create install script: {e}")
                return False
                
        except Exception as e:
            debug(f"Auto-installation failed: {e}")
            return False
    
    def install_deb(self, device: iOSDevice, deb_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """安装 deb 包到设备"""
        if not PYMOBILEDEVICE3_AVAILABLE:
            if progress_callback:
                progress_callback(-1, "pymobiledevice3 not available")
            print("[ERROR] pymobiledevice3 not available for file transfer")
            return False
        
        # Check if device is jailbroken
        if not device.is_jailbroken:
            if progress_callback:
                progress_callback(-1, "Device must be jailbroken to install .deb packages")
            print("[ERROR] Cannot install .deb packages on non-jailbroken device")
            return False
        
        try:
            if not device.lockdown_client:
                if progress_callback:
                    progress_callback(-1, "No device connection available")
                print("[ERROR] No lockdown client available")
                return False
            
            # 获取 AFC 服务（优先使用 AFC2）
            afc = None
            try:
                # 尝试 AFC2 服务（越狱设备）
                afc = AfcService(device.lockdown_client, service_name="com.apple.afc2")
                debug("Using AFC2 service for file transfer")
            except:
                # 退回到普通 AFC
                afc = AfcService(device.lockdown_client)
                debug("Using regular AFC service")
            
            # 确定安装路径（根据越狱类型）
            if "Rootless" in device.jailbreak_type or "Dopamine" in device.jailbreak_type:
                install_path = "/var/jb/var/mobile/Downloads/"
            else:
                install_path = "/var/mobile/Downloads/"
            
            if progress_callback:
                progress_callback(10, "Connecting to device...")
            
            # 创建目录（如果不存在）
            try:
                afc.makedirs(install_path)
            except:
                pass
            
            if progress_callback:
                progress_callback(30, "Preparing file transfer...")
            
            # 上传文件
            filename = os.path.basename(deb_path)
            remote_path = install_path + filename
            
            debug(f"Uploading {filename} to {remote_path}")
            
            if progress_callback:
                progress_callback(50, f"Uploading {filename}...")
            
            # 读取本地文件
            with open(deb_path, 'rb') as f:
                file_data = f.read()
                
            # 写入到设备
            afc.push(deb_path, remote_path)
            
            debug(f"Upload complete. File at: {remote_path}")
            
            if progress_callback:
                progress_callback(80, f"Upload complete: {remote_path}")
            
            # 尝试自动安装
            if progress_callback:
                progress_callback(90, "Attempting automatic installation...")
            
            install_success = self._auto_install_deb(device, remote_path, progress_callback)
            
            if install_success:
                if progress_callback:
                    progress_callback(100, f"Installation complete!")
                return True
            else:
                if progress_callback:
                    progress_callback(100, f"Upload complete. Manual installation required: {remote_path}")
                return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to upload deb: {e}")
            if progress_callback:
                progress_callback(-1, f"Upload failed: {error_msg}")
            return False
    
    def list_installed_packages(self, device: iOSDevice) -> List[Dict[str, str]]:
        """列出设备上已安装的包"""
        if not PYMOBILEDEVICE3_AVAILABLE:
            return []
        
        try:
            if not device.lockdown_client:
                return []
            
            # 使用 InstallationProxy 服务列出应用
            installation = InstallationProxyService(device.lockdown_client)
            
            # 获取所有应用（包括系统应用）
            apps = installation.get_apps()
            
            packages = []
            for app_id, app_info in apps.items():
                # 过滤出越狱相关的包
                if any(keyword in app_id.lower() for keyword in ['cydia', 'sileo', 'zebra', 'installer']):
                    packages.append({
                        'package': app_id,
                        'name': app_info.get('CFBundleDisplayName', app_id),
                        'version': app_info.get('CFBundleShortVersionString', 'Unknown'),
                        'path': app_info.get('Path', '')
                    })
            
            debug(f"Found {len(packages)} jailbreak-related packages")
            return packages
            
        except Exception as e:
            print(f"[ERROR] Failed to list packages: {e}")
            return []
    
    def get_device_logs(self, device: iOSDevice, lines: int = 100) -> str:
        """获取设备日志"""
        if not PYMOBILEDEVICE3_AVAILABLE:
            return "pymobiledevice3 not available"
        
        try:
            if not device.lockdown_client:
                return "No device connected"
            
            # 这里可以实现系统日志读取
            # 但需要更复杂的实现
            return "Device log reading not implemented yet"
            
        except Exception as e:
            return f"Error reading logs: {str(e)}"