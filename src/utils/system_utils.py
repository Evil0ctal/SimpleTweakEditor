# -*- coding: utf-8 -*-
"""
创建时间: 2025-05-24
作者: Evil0ctal

中文介绍:
系统工具模块，提供与操作系统相关的实用函数。
包含文件和文件夹操作、权限设置、dpkg 检测、包信息提取等功能。
支持跨平台操作，在 Windows、macOS 和 Linux 上提供统一的接口。

英文介绍:
System utilities module providing operating system related utility functions.
Includes file and folder operations, permission settings, dpkg detection,
package information extraction and other features.
Supports cross-platform operations with unified interface on Windows, macOS and Linux.
"""

import os
import platform
import subprocess

# Windows subprocess flags to prevent console windows
if platform.system() == 'Windows':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


def open_folder(path):
    """在文件管理器中打开文件夹"""
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", path])
        return True
    except Exception as e:
        print(f"Error opening folder: {e}")
        return False


def open_file(path):
    """使用默认应用程序打开文件"""
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", path])
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", path])
        return True
    except Exception as e:
        print(f"Error opening file: {e}")
        return False


def check_dpkg_available():
    """检查dpkg-deb工具是否可用"""
    try:
        kwargs = {"capture_output": True, "text": True}
        if platform.system() == "Windows":
            kwargs["creationflags"] = CREATE_NO_WINDOW
        result = subprocess.run(["dpkg-deb", "--version"], **kwargs)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def get_system_info():
    """获取系统信息"""
    return {
        "system": platform.system(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "dpkg_available": check_dpkg_available()
    }


def set_file_permissions(file_path, permissions):
    """设置文件权限（Unix-like系统）"""
    try:
        if platform.system() != "Windows":
            os.chmod(file_path, permissions)
            return True
    except Exception as e:
        print(f"Error setting permissions for {file_path}: {e}")
        return False
    return True  # Windows doesn't need chmod


def set_debian_permissions(debian_dir):
    """设置DEBIAN目录的标准权限"""
    """
    标准权限：
    - DEBIAN目录: 755
    - control文件: 644
    - 脚本文件(postinst, preinst, postrm, prerm): 755
    - 其他文件: 644
    """
    permissions_set = []
    errors = []

    try:
        # 设置DEBIAN目录权限
        if set_file_permissions(debian_dir, 0o755):
            permissions_set.append(f"Set 755 permission for DEBIAN directory")

        # 可执行脚本文件
        executable_scripts = ["postinst", "preinst", "postrm", "prerm"]

        # 遍历DEBIAN目录中的所有文件
        if os.path.isdir(debian_dir):
            for filename in os.listdir(debian_dir):
                file_path = os.path.join(debian_dir, filename)
                if os.path.isfile(file_path):
                    if filename in executable_scripts:
                        # 脚本文件设置为可执行
                        if set_file_permissions(file_path, 0o755):
                            permissions_set.append(f"Set 755 permission for {filename}")
                        else:
                            errors.append(f"Failed to set 755 permission for {filename}")
                    else:
                        # 其他文件设置为普通权限
                        if set_file_permissions(file_path, 0o644):
                            permissions_set.append(f"Set 644 permission for {filename}")
                        else:
                            errors.append(f"Failed to set 644 permission for {filename}")

    except Exception as e:
        errors.append(f"Error processing DEBIAN directory: {e}")

    return permissions_set, errors


def is_valid_deb_file(file_path):
    """检查是否为有效的.deb文件"""
    if not os.path.isfile(file_path):
        return False

    if not file_path.lower().endswith('.deb'):
        return False

    try:
        # 尝试使用dpkg-deb检查文件
        kwargs = {"capture_output": True, "text": True}
        if platform.system() == "Windows":
            kwargs["creationflags"] = CREATE_NO_WINDOW
        result = subprocess.run(["dpkg-deb", "--info", file_path], **kwargs)
        return result.returncode == 0
    except Exception:
        # 如果dpkg-deb不可用，只检查文件扩展名
        return True


def is_valid_package_folder(folder_path):
    """检查是否为有效的包文件夹（包含DEBIAN/control）"""
    if not os.path.isdir(folder_path):
        return False

    debian_dir = os.path.join(folder_path, "DEBIAN")
    control_file = os.path.join(debian_dir, "control")

    return os.path.isdir(debian_dir) and os.path.isfile(control_file)


def get_package_info_from_control(control_path):
    """从control文件中提取包信息"""
    package_info = {}

    try:
        with open(control_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ':' in line and not line.startswith(' '):
                    key, value = line.split(':', 1)
                    package_info[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading control file: {e}")

    return package_info


def suggest_output_filename(package_info):
    """根据包信息建议输出文件名"""
    package_name = package_info.get('Package', 'package')
    version = package_info.get('Version', '1.0')
    architecture = package_info.get('Architecture', 'all')

    return f"{package_name}_{version}_{architecture}.deb"
